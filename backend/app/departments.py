import re

from fastapi import HTTPException
from sqlalchemy import delete
from sqlmodel import Session, select

from .catalog import DEPARTMENT_CATALOG, ORG_CHANNELS
from .models import Agent, Channel, ChannelMember, Department
from .schemas import DepartmentCreate


def department_slug(name: str) -> str:
    known = next(
        (item for item in DEPARTMENT_CATALOG if item["name"].lower() == name.lower()), None
    )
    if known:
        return known["slug"]
    slug = re.sub(r"[^a-z0-9]+", "-", name.lower()).strip("-")[:50].rstrip("-")
    if not slug:
        raise HTTPException(422, "Department name needs a usable slug")
    return slug


def ensure_org_channels(session: Session):
    for name, topic in ORG_CHANNELS.items():
        if not session.exec(
            select(Channel).where(Channel.name == name, Channel.is_dm.is_(False))
        ).first():
            session.add(Channel(name=name, topic=topic))
    session.flush()


def create_department(session: Session, data: DepartmentCreate, reuse_channel: bool = False):
    slug = data.slug or department_slug(data.name)
    if slug in ORG_CHANNELS:
        raise HTTPException(409, "That slug is reserved for an organization channel")
    for item in session.exec(select(Department)).all():
        if item.slug == slug or item.name.casefold() == data.name.casefold():
            raise HTTPException(409, "Department name or slug already exists")
    channel = session.exec(
        select(Channel).where(Channel.name == slug, Channel.is_dm.is_(False))
    ).first()
    if channel is not None and not reuse_channel:
        raise HTTPException(409, "A channel with that slug already exists")
    if channel is None:
        channel = Channel(name=slug, topic=data.description)
        session.add(channel)
        session.flush()
    department = Department(**data.model_dump(exclude={"slug"}), slug=slug, channel_id=channel.id)
    session.add(department)
    session.flush()
    return department


def sync_agent_membership(
    session: Session, agent: Agent, previous_department_id: int | None = None
):
    if previous_department_id is not None and previous_department_id != agent.department_id:
        previous = session.get(Department, previous_department_id)
        if previous:
            session.exec(
                delete(ChannelMember).where(
                    ChannelMember.agent_id == agent.id,
                    ChannelMember.channel_id == previous.channel_id,
                )
            )
    channels = session.exec(
        select(Channel).where(Channel.name.in_(list(ORG_CHANNELS)), Channel.is_dm.is_(False))
    ).all()
    channel_ids = {channel.id for channel in channels}
    if agent.department_id:
        department = session.get(Department, agent.department_id)
        if department is None:
            raise HTTPException(404, "Department not found")
        channel_ids.add(department.channel_id)
    for channel_id in channel_ids:
        if session.get(ChannelMember, (channel_id, agent.id)) is None:
            session.add(ChannelMember(channel_id=channel_id, agent_id=agent.id))
