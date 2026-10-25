from fastapi import APIRouter, Depends, HTTPException, Response
from sqlalchemy import update
from sqlmodel import Session, select

from ..catalog import DEPARTMENT_CATALOG, ORG_CHANNELS
from ..db import get_session
from ..departments import create_department, department_slug
from ..models import Agent, Channel, Department
from ..realtime import manager
from ..schemas import DepartmentCreate, DepartmentPatch
from .agents import require
from .channels import purge_channel

router = APIRouter(prefix="/api/departments", tags=["departments"])


@router.get("/catalog")
def catalog():
    return DEPARTMENT_CATALOG


@router.get("", response_model=list[Department])
def departments(session: Session = Depends(get_session)):
    return session.exec(select(Department).order_by(Department.sort_order, Department.id)).all()


@router.post("", response_model=Department, status_code=201)
async def add_department(data: DepartmentCreate, session: Session = Depends(get_session)):
    item = create_department(session, data)
    session.commit()
    session.refresh(item)
    await manager.broadcast("channel.updated", session.get(Channel, item.channel_id))
    await manager.broadcast("department.updated", item)
    return item


@router.patch("/{department_id}", response_model=Department)
async def edit_department(
    department_id: int, data: DepartmentPatch, session: Session = Depends(get_session)
):
    item = require(session, Department, department_id)
    changes = data.model_dump(exclude_none=True, exclude_unset=True)
    slug = data.slug or (department_slug(data.name) if data.name else item.slug)
    if slug in ORG_CHANNELS:
        raise HTTPException(409, "That slug is reserved for an organization channel")
    others = session.exec(select(Department).where(Department.id != department_id)).all()
    if any(
        other.slug == slug or other.name.casefold() == (data.name or item.name).casefold()
        for other in others
    ):
        raise HTTPException(409, "Department name or slug already exists")
    channel = require(session, Channel, item.channel_id)
    if session.exec(
        select(Channel).where(
            Channel.name == slug, Channel.id != channel.id, Channel.is_dm.is_(False)
        )
    ).first():
        raise HTTPException(409, "A channel with that slug already exists")
    item.sqlmodel_update({**changes, "slug": slug})
    channel.name = slug
    if data.description is not None:
        channel.topic = data.description
    session.add(item)
    session.add(channel)
    session.commit()
    session.refresh(item)
    session.refresh(channel)
    await manager.broadcast("department.updated", item)
    await manager.broadcast("channel.updated", channel)
    return item


@router.delete("/{department_id}", status_code=204)
async def remove_department(department_id: int, session: Session = Depends(get_session)):
    item = require(session, Department, department_id)
    channel_id = item.channel_id
    channel = require(session, Channel, channel_id)
    if channel.name == "general":
        raise HTTPException(422, "The general channel cannot be deleted")
    affected = session.exec(select(Agent).where(Agent.department_id == department_id)).all()
    session.exec(
        update(Agent).where(Agent.department_id == department_id).values(department_id=None)
    )
    session.delete(item)
    session.flush()
    purge_channel(session, channel_id)
    session.commit()
    for agent in affected:
        session.refresh(agent)
        await manager.broadcast("agent.updated", agent)
    await manager.broadcast("channel.deleted", {"id": channel_id})
    await manager.broadcast("department.deleted", {"id": department_id})
    return Response(status_code=204)
