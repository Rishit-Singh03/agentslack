import re

from fastapi import APIRouter, Depends, HTTPException
from sqlmodel import Session, select

from ..catalog import DEPARTMENT_CATALOG
from ..db import get_session
from ..departments import create_department, ensure_org_channels
from ..models import Channel, Department, Organization, UserProfile
from ..realtime import manager
from ..schemas import DepartmentCreate, OnboardingCreate, OrgPatch, ProfilePatch
from ..seed import seed

router = APIRouter(prefix="/api", tags=["settings"])


def slugify(name: str) -> str:
    return re.sub(r"[^a-z0-9]+", "-", name.lower()).strip("-") or "workspace"


def ensure_settings(session: Session):
    if session.exec(select(Organization)).first() is None:
        session.add(Organization())
    if session.exec(select(UserProfile)).first() is None:
        session.add(UserProfile())
    session.commit()


@router.get("/org", response_model=Organization)
def org(session: Session = Depends(get_session)):
    return session.exec(select(Organization)).first()


@router.patch("/org", response_model=Organization)
async def update_org(data: OrgPatch, session: Session = Depends(get_session)):
    item = session.exec(select(Organization)).one()
    item.sqlmodel_update(data.model_dump(exclude_none=True, exclude_unset=True))
    if data.name is not None:
        item.slug = slugify(item.name)
    session.add(item)
    session.commit()
    session.refresh(item)
    await manager.broadcast("org.updated", item)
    return item


@router.get("/me", response_model=UserProfile)
def me(session: Session = Depends(get_session)):
    return session.exec(select(UserProfile)).one()


@router.patch("/me", response_model=UserProfile)
async def update_me(data: ProfilePatch, session: Session = Depends(get_session)):
    item = session.exec(select(UserProfile)).one()
    item.sqlmodel_update(data.model_dump(exclude_none=True, exclude_unset=True))
    session.add(item)
    session.commit()
    session.refresh(item)
    await manager.broadcast("profile.updated", item)
    return item


@router.post("/onboarding", response_model=Organization)
async def onboard(data: OnboardingCreate, session: Session = Depends(get_session)):
    item = session.exec(select(Organization)).one()
    if item.initialized:
        raise HTTPException(409, "Workspace is already initialized")
    item.name = data.name
    item.slug = slugify(data.name)
    item.accent = data.accent
    item.initialized = True
    profile = session.exec(select(UserProfile)).one()
    profile.display_name = data.display_name
    profile.handle = data.handle
    session.add(item)
    session.add(profile)
    ensure_org_channels(session)
    selected = (
        data.departments
        if data.departments is not None
        else [
            DepartmentCreate(**template, sort_order=index)
            for index, template in enumerate(DEPARTMENT_CATALOG)
            if template["core"]
        ]
    )
    for department in selected:
        create_department(session, department)
    if data.sample_team:
        seed(session, commit=False)
    session.commit()
    session.refresh(item)
    session.refresh(profile)
    await manager.broadcast("org.updated", item)
    await manager.broadcast("profile.updated", profile)
    for channel in session.exec(select(Channel)).all():
        await manager.broadcast("channel.updated", channel)
    for department in session.exec(select(Department)).all():
        await manager.broadcast("department.updated", department)
    return item
