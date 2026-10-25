from fastapi import APIRouter, Depends, HTTPException
from sqlmodel import Session, select

from ..db import get_session
from ..models import Agent, Channel, ChannelMember
from ..schemas import ChannelCreate
from .agents import require

router = APIRouter(prefix="/api", tags=["channels"])


@router.get("/channels", response_model=list[Channel])
def channels(session: Session = Depends(get_session)):
    return session.exec(select(Channel).order_by(Channel.id)).all()


@router.post("/channels", response_model=Channel, status_code=201)
def create_channel(data: ChannelCreate, session: Session = Depends(get_session)):
    if session.exec(
        select(Channel).where(Channel.name == data.name, Channel.is_dm.is_(False))
    ).first():
        raise HTTPException(409, "Channel already exists")
    channel = Channel(**data.model_dump())
    session.add(channel)
    session.commit()
    session.refresh(channel)
    return channel


@router.get("/channels/{channel_id}")
def channel(channel_id: int, session: Session = Depends(get_session)):
    item = require(session, Channel, channel_id)
    members = session.exec(
        select(ChannelMember.agent_id).where(ChannelMember.channel_id == channel_id)
    ).all()
    return {**item.model_dump(), "member_ids": members}


@router.post("/dms/{agent_id}", response_model=Channel)
def dm(agent_id: int, session: Session = Depends(get_session)):
    agent = require(session, Agent, agent_id)
    channel = session.exec(select(Channel).where(Channel.dm_agent_id == agent_id)).first()
    if channel is None:
        channel = Channel(
            name=agent.name,
            topic=f"Your direct conversation with {agent.name}",
            is_dm=True,
            dm_agent_id=agent_id,
        )
        session.add(channel)
        session.flush()
        session.add(ChannelMember(channel_id=channel.id, agent_id=agent_id))
        session.commit()
        session.refresh(channel)
    return channel
