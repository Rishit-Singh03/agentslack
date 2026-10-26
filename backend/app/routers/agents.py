from fastapi import APIRouter, Depends, HTTPException, Response
from sqlalchemy import delete, update
from sqlmodel import Session, select

from ..budget import spend_summary
from ..db import get_session
from ..departments import sync_agent_membership
from ..model_catalog import find_model, preset
from ..models import (
    Agent,
    Channel,
    ChannelMember,
    Department,
    MemoryEntry,
    Message,
    Organization,
    Task,
)
from ..realtime import manager
from ..schemas import AgentCreate, AgentPatch

router = APIRouter(prefix="/api/agents", tags=["agents"])


def require(session, model, identifier):
    item = session.get(model, identifier)
    if item is None:
        raise HTTPException(404, f"{model.__name__} not found")
    return item


@router.get("", response_model=list[Agent])
def list_agents(session: Session = Depends(get_session)):
    return session.exec(select(Agent).order_by(Agent.id)).all()


@router.post("", response_model=Agent, status_code=201)
async def create_agent(data: AgentCreate, session: Session = Depends(get_session)):
    if session.exec(select(Agent).where(Agent.handle == data.handle)).first():
        raise HTTPException(409, "Handle already exists")
    if data.department_id is not None:
        require(session, Department, data.department_id)
    department = session.get(Department, data.department_id) if data.department_id else None
    org = session.exec(select(Organization)).one()
    provider, model = preset(department.slug if department else None, org)
    fields = data.model_dump(exclude_none=True)
    fields.setdefault("provider", provider)
    fields.setdefault("model_id", model)
    agent = Agent(**fields, runtime=data.harness)
    validate_model(agent.provider, agent.model_id, agent.thinking_level, agent.max_output_tokens)
    session.add(agent)
    session.flush()
    sync_agent_membership(session, agent)
    session.commit()
    session.refresh(agent)
    await manager.broadcast("agent.updated", agent)
    return agent


@router.get("/{agent_id}", response_model=Agent)
def get_agent(agent_id: int, session: Session = Depends(get_session)):
    return require(session, Agent, agent_id)


@router.patch("/{agent_id}", response_model=Agent)
async def patch_agent(agent_id: int, data: AgentPatch, session: Session = Depends(get_session)):
    agent = require(session, Agent, agent_id)
    previous_department_id = agent.department_id
    changes = data.model_dump(exclude_unset=True, exclude_none=True)
    if any(
        key in changes
        for key in (
            "harness",
            "provider",
            "model_id",
            "thinking_level",
            "max_output_tokens",
            "monthly_budget_usd",
        )
    ):
        from .messages import pending

        if pending.get(agent_id):
            raise HTTPException(409, "Wait for queued replies before changing employment settings")
        validate_model(
            changes.get("provider", agent.provider),
            changes.get("model_id", agent.model_id),
            changes.get("thinking_level", agent.thinking_level),
            changes.get("max_output_tokens", agent.max_output_tokens),
        )
    if "harness" in changes:
        changes["runtime"] = changes["harness"]
    if "department_id" in data.model_fields_set:
        if data.department_id is not None:
            require(session, Department, data.department_id)
        changes["department_id"] = data.department_id
    agent.sqlmodel_update(changes)
    session.add(agent)
    sync_agent_membership(session, agent, previous_department_id)
    dm = session.exec(select(Channel).where(Channel.dm_agent_id == agent_id)).first()
    if dm is not None and data.name is not None:
        dm.name = agent.name
        dm.topic = f"Direct conversation with {agent.name}"
        session.add(dm)
    session.commit()
    session.refresh(agent)
    await manager.broadcast("agent.updated", agent)
    if dm is not None and data.name is not None:
        session.refresh(dm)
        await manager.broadcast("channel.updated", dm)
    return agent


def validate_model(provider, model_id, thinking, max_output_tokens=4096):
    model = find_model(provider, model_id)
    allowed = model["thinking_levels"] if model else ["off"]
    if thinking not in allowed:
        raise HTTPException(422, "Thinking level is not supported by this model")
    if model and max_output_tokens > model["max_output"]:
        raise HTTPException(422, "Maximum output tokens exceeds this model's output limit")


@router.get("/{agent_id}/spend")
def agent_spend(agent_id: int, session: Session = Depends(get_session)):
    agent = require(session, Agent, agent_id)
    return {**spend_summary(session, agent_id), "budget_usd": str(agent.monthly_budget_usd)}


@router.post("/{agent_id}/abort")
async def abort_agent(agent_id: int, session: Session = Depends(get_session)):
    from ..runtime.pi import supervisor

    require(session, Agent, agent_id)
    await supervisor.abort(agent_id)
    return {"status": "aborted"}


@router.get("/{agent_id}/memory", response_model=list[MemoryEntry])
def memory(agent_id: int, session: Session = Depends(get_session)):
    require(session, Agent, agent_id)
    return session.exec(select(MemoryEntry).where(MemoryEntry.agent_id == agent_id)).all()


@router.delete("/{agent_id}", status_code=204)
async def dismiss_agent(agent_id: int, session: Session = Depends(get_session)):
    from .channels import purge_channel
    from .messages import pending

    agent = require(session, Agent, agent_id)
    if pending.get(agent_id):
        raise HTTPException(409, "Wait for the active reply before dismissing this agent")
    dms = session.exec(select(Channel).where(Channel.dm_agent_id == agent_id)).all()
    deleted_tasks = session.exec(select(Task).where(Task.assignee_agent_id == agent_id)).all()
    for channel in dms:
        purge_channel(session, channel.id)
    session.exec(delete(Task).where(Task.assignee_agent_id == agent_id))
    session.exec(delete(MemoryEntry).where(MemoryEntry.agent_id == agent_id))
    session.exec(delete(ChannelMember).where(ChannelMember.agent_id == agent_id))
    session.exec(update(Message).where(Message.author_id == agent_id).values(author_id=None))
    session.delete(agent)
    session.commit()
    for channel in dms:
        await manager.broadcast("channel.deleted", {"id": channel.id})
    for task in deleted_tasks:
        await manager.broadcast("task.deleted", {"id": task.id})
    await manager.broadcast("agent.deleted", {"id": agent_id})
    return Response(status_code=204)
