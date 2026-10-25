from fastapi import APIRouter, Depends, HTTPException
from sqlmodel import Session, select

from ..db import get_session
from ..models import Agent, MemoryEntry
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
    agent = Agent(**data.model_dump())
    session.add(agent)
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
    agent.sqlmodel_update(data.model_dump(exclude_unset=True, exclude_none=True))
    session.add(agent)
    session.commit()
    session.refresh(agent)
    await manager.broadcast("agent.updated", agent)
    return agent


@router.get("/{agent_id}/memory", response_model=list[MemoryEntry])
def memory(agent_id: int, session: Session = Depends(get_session)):
    require(session, Agent, agent_id)
    return session.exec(select(MemoryEntry).where(MemoryEntry.agent_id == agent_id)).all()
