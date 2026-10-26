import logging
import re

from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException, Query
from sqlmodel import Session, select

from ..budget import BudgetError, spend_summary
from ..db import get_session
from ..models import Agent, Channel, Message
from ..realtime import manager
from ..runtime import get_runtime
from ..runtime.pi import PiRuntime, RuntimeFailure
from ..schemas import MessageCreate
from .agents import require

router = APIRouter(prefix="/api/channels", tags=["messages"])
pending: dict[int, int] = {}
original_status: dict[int, str] = {}
active_channels: dict[int, int] = {}
logger = logging.getLogger(__name__)


async def reply(bind, agent_ids: list[int], message_id: int):
    for agent_id in agent_ids:
        with Session(bind) as session:
            agent = session.get(Agent, agent_id)
            message = session.get(Message, message_id)
            if agent is None or message is None:
                continue
            if agent_id not in pending:
                original_status[agent_id] = agent.status
            pending[agent_id] = pending.get(agent_id, 0) + 1
            active_channels[message.channel_id] = active_channels.get(message.channel_id, 0) + 1
            agent.status = "busy"
            session.add(agent)
            session.commit()
            session.refresh(agent)
            await manager.broadcast("agent.updated", agent)
            try:
                context = list(
                    reversed(
                        session.exec(
                            select(Message)
                            .where(Message.channel_id == message.channel_id)
                            .order_by(Message.id.desc())
                            .limit(20)
                        ).all()
                    )
                )
                context = [Message.model_validate(item.model_dump()) for item in context]
                response = Message(
                    channel_id=message.channel_id,
                    author_type="agent",
                    author_id=agent.id,
                    body="",
                    is_streaming=True,
                    model_id=agent.model_id if agent.harness == "pi" else None,
                    thread_parent_id=message.thread_parent_id,
                )
                session.add(response)
                session.commit()
                session.refresh(response)
                await manager.broadcast("message.created", response)
                runtime = None
                failure = None
                try:
                    runtime = get_runtime(agent.harness)
                    if isinstance(runtime, PiRuntime):
                        # Never keep a write transaction open while Pi runs. In particular,
                        # lazy-loading an expired agent must not autoflush partial text.
                        session.refresh(agent)
                        session.refresh(message)
                        session.expunge_all()
                        session.rollback()
                        async for event in runtime.events(bind, agent, message, context):
                            if event["type"] == "text":
                                response.body += event["text"]
                                await manager.broadcast(
                                    "message.delta",
                                    {
                                        "id": response.id,
                                        "channel_id": response.channel_id,
                                        "delta": event["text"],
                                    },
                                )
                            elif event["type"] == "final":
                                response.body = event["text"]
                            elif event["type"] == "usage":
                                response.usage = event["usage"]
                                response.model_id = event["model_id"]
                                response.cost_usd = str(event["usage"]["cost"]["total"])
                            elif event["type"] == "system":
                                notice = Message(
                                    channel_id=message.channel_id,
                                    author_type="system",
                                    body=event["text"],
                                )
                                # A separate short transaction must not attach/flush the
                                # still-streaming response or expire the run's inputs.
                                with Session(bind) as notice_session:
                                    notice_session.add(notice)
                                    notice_session.commit()
                                    notice_session.refresh(notice)
                                    await manager.broadcast("message.created", notice)
                    elif hasattr(runtime, "stream"):
                        async for chunk in runtime.stream(agent, message, context):
                            response.body += chunk
                            await manager.broadcast(
                                "message.delta",
                                {
                                    "id": response.id,
                                    "channel_id": response.channel_id,
                                    "delta": chunk,
                                },
                            )
                    else:
                        # Compatibility with Phase 1 runtimes implementing only respond().
                        response.body = await runtime.respond(agent, message, context)
                        await manager.broadcast(
                            "message.delta",
                            {
                                "id": response.id,
                                "channel_id": response.channel_id,
                                "delta": response.body,
                            },
                        )
                except (RuntimeFailure, BudgetError) as exc:
                    failure = f"{agent.handle}: {exc}"
                except Exception:
                    logger.exception("Runtime failed for agent %s", agent.handle)
                    failure = (
                        f"{agent.handle}: Runtime failed. Check the backend runtime configuration."
                    )
                finally:
                    if isinstance(runtime, PiRuntime) and getattr(runtime, "usage", None):
                        response.usage = runtime.usage
                        response.model_id = getattr(runtime, "model_id", agent.model_id)
                        response.cost_usd = str(runtime.usage["cost"]["total"])
                    if failure and not response.body:
                        response.author_type = "system"
                        response.author_id = None
                        response.body = failure
                        failure = None
                    response.is_streaming = False
                    session.add(response)
                    session.commit()
                    session.refresh(response)
                    await manager.broadcast("message.created", response)
                    if failure:
                        notice = Message(
                            channel_id=message.channel_id, author_type="system", body=failure
                        )
                        session.add(notice)
                        session.commit()
                        session.refresh(notice)
                        await manager.broadcast("message.created", notice)
                    if isinstance(runtime, PiRuntime):
                        await manager.broadcast("spend.updated", spend_summary(session))
            finally:
                active_channels[message.channel_id] -= 1
                if not active_channels[message.channel_id]:
                    del active_channels[message.channel_id]
                pending[agent_id] -= 1
                if not pending[agent_id]:
                    del pending[agent_id]
                    agent = session.get(Agent, agent_id)
                    session.refresh(agent)
                    agent.status = original_status.pop(agent_id)
                    session.add(agent)
                    session.commit()
                    session.refresh(agent)
                    await manager.broadcast("agent.updated", agent)


@router.get("/{channel_id}/messages", response_model=list[Message])
def messages(
    channel_id: int,
    before: int | None = Query(default=None, ge=1),
    limit: int = Query(default=50, ge=1, le=200),
    session: Session = Depends(get_session),
):
    require(session, Channel, channel_id)
    query = select(Message).where(Message.channel_id == channel_id)
    if before:
        query = query.where(Message.id < before)
    return list(reversed(session.exec(query.order_by(Message.id.desc()).limit(limit)).all()))


@router.post("/{channel_id}/messages", response_model=Message, status_code=201)
async def post_message(
    channel_id: int,
    data: MessageCreate,
    background: BackgroundTasks,
    session: Session = Depends(get_session),
):
    channel = require(session, Channel, channel_id)
    if data.thread_parent_id is not None:
        parent = require(session, Message, data.thread_parent_id)
        if parent.channel_id != channel_id:
            raise HTTPException(422, "Thread must belong to this channel")
    message = Message(channel_id=channel_id, **data.model_dump())
    session.add(message)
    session.commit()
    session.refresh(message)
    await manager.broadcast("message.created", message)
    handles = set(re.findall(r"(?<!\w)@[a-z][a-z0-9_]*", data.body.lower()))
    agents = session.exec(select(Agent)).all()
    targets = [a.id for a in agents if a.handle in handles or a.id == channel.dm_agent_id]
    if targets:
        background.add_task(reply, session.get_bind(), targets, message.id)
    return message
