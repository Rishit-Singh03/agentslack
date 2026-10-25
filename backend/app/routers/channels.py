from fastapi import APIRouter, Depends, HTTPException, Response
from sqlalchemy import delete, update
from sqlmodel import Session, select

from ..db import get_session
from ..models import Agent, Channel, ChannelMember, Department, Message, Task
from ..realtime import manager
from ..schemas import ChannelCreate, ChannelPatch
from .agents import require

router = APIRouter(prefix="/api", tags=["channels"])


@router.get("/channels", response_model=list[Channel])
def channels(session: Session = Depends(get_session)):
    return session.exec(select(Channel).order_by(Channel.id)).all()


@router.post("/channels", response_model=Channel, status_code=201)
async def create_channel(data: ChannelCreate, session: Session = Depends(get_session)):
    if session.exec(
        select(Channel).where(Channel.name == data.name, Channel.is_dm.is_(False))
    ).first():
        raise HTTPException(409, "Channel already exists")
    channel = Channel(**data.model_dump())
    session.add(channel)
    session.commit()
    session.refresh(channel)
    await manager.broadcast("channel.updated", channel)
    return channel


@router.patch("/channels/{channel_id}", response_model=Channel)
async def patch_channel(
    channel_id: int, data: ChannelPatch, session: Session = Depends(get_session)
):
    item = require(session, Channel, channel_id)
    if item.is_dm:
        raise HTTPException(422, "Direct message channels cannot be edited")
    if data.name and data.name != item.name:
        if session.exec(select(Department).where(Department.channel_id == channel_id)).first():
            raise HTTPException(409, "Rename department channels through department settings")
        if item.name == "general":
            raise HTTPException(422, "The general channel cannot be renamed")
        if session.exec(select(Channel).where(Channel.name == data.name)).first():
            raise HTTPException(409, "Channel already exists")
    item.sqlmodel_update(data.model_dump(exclude_none=True, exclude_unset=True))
    session.add(item)
    session.commit()
    session.refresh(item)
    await manager.broadcast("channel.updated", item)
    return item


def purge_channel(session: Session, channel_id: int):
    from .messages import active_channels

    channel = require(session, Channel, channel_id)
    if channel.name == "general" and not channel.is_dm:
        raise HTTPException(422, "The general channel cannot be deleted")

    if active_channels.get(channel_id):
        raise HTTPException(409, "Wait for the active reply before deleting this channel")
    if session.exec(
        select(Message).where(Message.channel_id == channel_id, Message.is_streaming.is_(True))
    ).first():
        raise HTTPException(409, "Wait for the active reply before deleting this channel")
    session.exec(
        update(Message).where(Message.channel_id == channel_id).values(thread_parent_id=None)
    )
    session.exec(delete(Message).where(Message.channel_id == channel_id))
    session.exec(delete(ChannelMember).where(ChannelMember.channel_id == channel_id))
    session.exec(update(Task).where(Task.channel_id == channel_id).values(channel_id=None))
    session.delete(require(session, Channel, channel_id))


@router.delete("/channels/{channel_id}", status_code=204)
async def delete_channel(channel_id: int, session: Session = Depends(get_session)):
    item = require(session, Channel, channel_id)
    if item.name == "general" and not item.is_dm:
        raise HTTPException(422, "The general channel cannot be deleted")
    if session.exec(select(Department).where(Department.channel_id == channel_id)).first():
        raise HTTPException(409, "Remove the department through department settings")
    purge_channel(session, channel_id)
    session.commit()
    await manager.broadcast("channel.deleted", {"id": channel_id})
    return Response(status_code=204)


@router.get("/channels/{channel_id}")
def channel(channel_id: int, session: Session = Depends(get_session)):
    item = require(session, Channel, channel_id)
    members = session.exec(
        select(ChannelMember.agent_id).where(ChannelMember.channel_id == channel_id)
    ).all()
    return {**item.model_dump(), "member_ids": members}


@router.post("/dms/{agent_id}", response_model=Channel)
async def dm(agent_id: int, session: Session = Depends(get_session)):
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
        await manager.broadcast("channel.updated", channel)
    return channel
