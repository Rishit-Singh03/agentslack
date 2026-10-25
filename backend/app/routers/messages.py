import re

from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException, Query
from sqlmodel import Session, select

from ..db import get_session
from ..models import Agent, Channel, Message
from ..realtime import manager
from ..runtime import get_runtime
from ..schemas import MessageCreate
from .agents import require

router = APIRouter(prefix="/api/channels", tags=["messages"])
pending: dict[int, int] = {}
original_status: dict[int, str] = {}


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
                body = await get_runtime(agent.runtime).respond(agent, message, context)
                response = Message(
                    channel_id=message.channel_id,
                    author_type="agent",
                    author_id=agent.id,
                    body=body,
                    thread_parent_id=message.thread_parent_id,
                )
                session.add(response)
                session.commit()
                session.refresh(response)
                await manager.broadcast("message.created", response)
            finally:
                pending[agent_id] -= 1
                if not pending[agent_id]:
                    del pending[agent_id]
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
