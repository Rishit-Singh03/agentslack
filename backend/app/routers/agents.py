from fastapi import APIRouter, Depends, HTTPException, Response
from sqlalchemy import delete, update
from sqlmodel import Session, select

from ..db import get_session
from ..departments import sync_agent_membership
from ..models import Agent, Channel, ChannelMember, Department, MemoryEntry, Message, Task
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
    agent = Agent(**data.model_dump())
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
