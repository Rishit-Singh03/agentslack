from sqlalchemy import delete, inspect, text, update
from sqlmodel import Session, select

from .catalog import DEPARTMENT_CATALOG
from .departments import create_department, ensure_org_channels, sync_agent_membership
from .models import Agent, Channel, ChannelMember, Message, Organization, Task
from .schemas import DepartmentCreate

LEGACY_DEPARTMENTS = {
    "frontend": "engineering",
    "backend": "engineering",
    "finance": "finance",
    "design": "design",
    "research": "research",
    "ops": "operations",
}


def migrate_departments(connection):
    columns = {column["name"] for column in inspect(connection).get_columns("agent")}
    with Session(bind=connection) as session:
        org = session.exec(select(Organization)).first()
        if org is not None and org.initialized:
            ensure_org_channels(session)
        if "role" not in columns:
            session.flush()
            return
        legacy = connection.execute(text("SELECT id, role FROM agent")).all()
        departments = {}
        for _, role in legacy:
            slug = LEGACY_DEPARTMENTS.get(role)
            if slug is None or slug in departments:
                continue
            template = next(item for item in DEPARTMENT_CATALOG if item["slug"] == slug)
            department = create_department(
                session,
                DepartmentCreate(**template, sort_order=len(departments)),
                reuse_channel=True,
            )
            departments[slug] = department
        for agent_id, role in legacy:
            agent = session.get(Agent, agent_id)
            department = departments.get(LEGACY_DEPARTMENTS.get(role))
            agent.department_id = department.id if department else None
            session.add(agent)
            sync_agent_membership(session, agent)
        # Merge legacy channel histories into the new department channels without losing IDs.
        for old_name, slug in LEGACY_DEPARTMENTS.items():
            department = departments.get(slug)
            old = session.exec(
                select(Channel).where(Channel.name == old_name, Channel.is_dm.is_(False))
            ).first()
            if department is None or old is None or old.id == department.channel_id:
                continue
            session.exec(
                update(Message)
                .where(Message.channel_id == old.id)
                .values(channel_id=department.channel_id)
            )
            session.exec(
                update(Task)
                .where(Task.channel_id == old.id)
                .values(channel_id=department.channel_id)
            )
            for member in session.exec(
                select(ChannelMember).where(ChannelMember.channel_id == old.id)
            ).all():
                key = (department.channel_id, member.agent_id)
                if session.get(ChannelMember, key) is None:
                    session.add(ChannelMember(channel_id=key[0], agent_id=key[1]))
            session.exec(delete(ChannelMember).where(ChannelMember.channel_id == old.id))
            session.delete(old)
        session.flush()
        connection.execute(text("ALTER TABLE agent DROP COLUMN role"))
