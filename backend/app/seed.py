from sqlmodel import Session, select

from .catalog import DEPARTMENT_CATALOG
from .departments import create_department, ensure_org_channels, sync_agent_membership
from .model_catalog import preset
from .models import Agent, Channel, Department, Message, Organization, Task
from .schemas import DepartmentCreate

SAMPLE_TEAM = [
    ("Alice", "leadership", "Chief of Staff", ["Strategy", "Planning", "Decision briefs"], 245),
    (
        "Omar",
        "operations",
        "Operations Manager",
        ["Processes", "Delivery", "Resource planning"],
        380,
    ),
    ("Nina", "finance", "Finance Analyst", ["Forecasting", "Budgets", "Financial reporting"], 170),
    ("Maya", "people", "People Partner", ["Hiring", "Onboarding", "People policies"], 290),
    ("Leo", "product", "Product Manager", ["Discovery", "Prioritization", "Roadmaps"], 125),
    ("Evan", "engineering", "Software Engineer", ["Software systems", "APIs", "Testing"], 420),
    ("Zoe", "marketing", "Marketing Lead", ["Positioning", "Campaigns", "Content"], 220),
    ("Ben", "sales", "Account Executive", ["Accounts", "Proposals", "Negotiation"], 80),
]

SAMPLE_TASKS = [
    (
        "Prepare the weekly decision brief",
        "Summarize priorities, open decisions, and owners for leadership review.",
        "leadership",
        "review",
        "high",
    ),
    (
        "Document the request intake process",
        "Define triage, ownership, and response expectations for shared requests.",
        "operations",
        "in_progress",
        "high",
    ),
    (
        "Update the quarterly forecast",
        "Review spending assumptions and provide a forecast with risks and scenarios.",
        "finance",
        "todo",
        "med",
    ),
    (
        "Review the new-hire checklist",
        "Confirm access, introductions, and first-week responsibilities for new hires.",
        "people",
        "review",
        "med",
    ),
    (
        "Prioritize customer requests",
        "Group incoming feedback by impact and recommend the next product priorities.",
        "product",
        "todo",
        "high",
    ),
    (
        "Review service reliability",
        "Check error trends, test coverage, and the next reliability improvements.",
        "engineering",
        "in_progress",
        "med",
    ),
    (
        "Draft the campaign brief",
        "Outline the audience, message, channels, and success metrics for the next campaign.",
        "marketing",
        "todo",
        "med",
    ),
    (
        "Update account next steps",
        "Record owners, customer questions, and follow-up dates for active opportunities.",
        "sales",
        "done",
        "med",
    ),
]


def seed(session: Session, commit: bool = True):
    if session.exec(select(Agent)).first():
        return
    if not session.exec(select(Organization)).first():
        session.add(Organization(name="Acme Agents", slug="acme-agents", initialized=True))
        ensure_org_channels(session)
        for index, template in enumerate(DEPARTMENT_CATALOG):
            if template["core"]:
                create_department(session, DepartmentCreate(**template, sort_order=index))
    ensure_org_channels(session)
    departments = {item.slug: item for item in session.exec(select(Department)).all()}
    channels = {item.name: item for item in session.exec(select(Channel)).all()}
    people = {}
    org = session.exec(select(Organization)).one()
    for name, slug, title, skills, xp in SAMPLE_TEAM:
        department = departments.get(slug)
        if department is None:
            continue
        agent = Agent(
            name=name,
            handle=f"@{name.lower()}",
            department_id=department.id,
            title=title,
            skills=skills,
            xp=xp,
            level=1 + xp // 100,
            status="idle" if slug == "product" else "online",
            bio=f"{title}. Handles {department.name.lower()} work and shared requests.",
            provider=preset(slug, org)[0],
            model_id=preset(slug, org)[1],
            runtime="pi",
        )
        session.add(agent)
        session.flush()
        sync_agent_membership(session, agent)
        people[slug] = agent
        session.add(
            Message(
                channel_id=department.channel_id,
                author_type="agent",
                author_id=agent.id,
                body=(
                    f"{department.name}: {department.description} "
                    f"Mention {agent.handle} to request a response."
                ),
            )
        )
    session.add(
        Message(
            channel_id=channels["general"].id,
            author_type="system",
            body="Workspace initialized. Use #requests for cross-department work.",
        )
    )
    for slug in ("leadership", "operations", "product", "engineering"):
        agent = people.get(slug)
        if agent:
            session.add(
                Message(
                    channel_id=channels["general"].id,
                    author_type="agent",
                    author_id=agent.id,
                    body=(
                        f"{agent.title} here. Department updates are in #{departments[slug].slug}; "
                        "shared work goes in #requests."
                    ),
                )
            )
    for index, (title, description, slug, status, priority) in enumerate(SAMPLE_TASKS):
        agent = people.get(slug)
        if agent is None:
            continue
        channel_id = channels["requests"].id if index in (1, 4, 7) else departments[slug].channel_id
        session.add(
            Task(
                title=title,
                description=description,
                assignee_agent_id=agent.id,
                channel_id=channel_id,
                status=status,
                priority=priority,
                xp_awarded=status == "done",
            )
        )
    if commit:
        session.commit()
