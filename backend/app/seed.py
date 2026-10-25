from sqlmodel import Session, select

from .models import Agent, Channel, ChannelMember, Message, Organization, Task


def seed(session: Session):
    if session.exec(select(Organization)).first():
        return
    session.add(Organization(name="Acme Agents"))
    people = [
        (
            "Fiona",
            "frontend",
            "Frontend engineer",
            "#a78bfa",
            245,
            ["React", "TypeScript", "Accessibility"],
        ),
        ("Bruno", "backend", "Backend engineer", "#60a5fa", 380, ["Python", "APIs", "Databases"]),
        (
            "Penny",
            "finance",
            "Financial strategist",
            "#fbbf24",
            170,
            ["Forecasting", "Budgets", "Analysis"],
        ),
        (
            "Dex",
            "design",
            "Product designer",
            "#f472b6",
            290,
            ["UI/UX", "Design systems", "Prototyping"],
        ),
        (
            "Remy",
            "research",
            "Research specialist",
            "#34d399",
            125,
            ["Research", "Synthesis", "Strategy"],
        ),
        ("Opal", "ops", "Operations lead", "#fb923c", 420, ["Planning", "Operations", "Delivery"]),
    ]
    agents = []
    for i, (name, role, title, color, xp, skills) in enumerate(people):
        agent = Agent(
            handle=f"@{name.lower()}",
            name=name,
            role=role,
            title=title,
            avatar_color=color,
            xp=xp,
            level=1 + xp // 100,
            skills=skills,
            status="idle" if i == 4 else "online",
            bio=(
                f"Your dedicated {role} teammate. "
                "Here to turn ambitious ideas into thoughtful, useful work."
            ),
        )
        session.add(agent)
        agents.append(agent)
    session.flush()
    channels = []
    for name, topic in [
        ("general", "The big picture, small wins, and everything in between."),
        ("frontend", "Interfaces that feel as good as they work."),
        ("backend", "APIs, architecture, and the engine behind it all."),
        ("finance", "Making every number count."),
    ]:
        channel = Channel(name=name, topic=topic)
        session.add(channel)
        session.flush()
        channels.append(channel)
        for agent in agents:
            if name == "general" or agent.role == name:
                session.add(ChannelMember(channel_id=channel.id, agent_id=agent.id))
    session.add(
        Message(
            channel_id=channels[0].id,
            author_type="system",
            body="Welcome to Acme Agents. Your next great idea starts here.",
        )
    )
    for agent, body in [
        (
            agents[5],
            "Morning, team! 👋 Our workspace is ready. "
            "Share an idea, assign a task, or say hello to your new teammates.",
        ),
        (
            agents[0],
            "Ready to build something great. "
            "I'll be in **#frontend** if you need a hand with the interface.",
        ),
        (agents[1], "Backend is all set. Mention **@bruno** in a channel and I'll jump in."),
        (agents[3], "A little craft goes a long way. Let's make something people love. ✨"),
    ]:
        session.add(
            Message(channel_id=channels[0].id, author_type="agent", author_id=agent.id, body=body)
        )
    for index, channel in enumerate(channels[1:]):
        session.add(
            Message(
                channel_id=channel.id,
                author_type="agent",
                author_id=agents[index].id,
                body=f"Welcome to **#{channel.name}**! What should we work on first?",
            )
        )
    task_seeds = [
        (
            "Build the workspace shell",
            "Implement responsive channel navigation, the conversation layout, and an accessible "
            "message composer in React.",
            0,
            "in_progress",
            "high",
        ),
        (
            "Define the API contracts",
            "Document request and response schemas for agents, channels, messages, and tasks, "
            "including validation errors and pagination.",
            1,
            "review",
            "high",
        ),
        (
            "Draft Q4 budget forecast",
            "Estimate infrastructure and future model costs, compare usage scenarios, and flag "
            "the assumptions with the biggest effect on the budget.",
            2,
            "todo",
            "med",
        ),
        (
            "Explore the visual direction",
            "Propose a cohesive palette, typography, and component treatments for the workspace "
            "with accessible contrast in both themes.",
            3,
            "review",
            "med",
        ),
        (
            "Research collaboration patterns",
            "Compare how teams coordinate work through channels and task boards, then summarize "
            "patterns that could make agent collaboration easier to follow.",
            4,
            "todo",
            "low",
        ),
        (
            "Set up the team workspace",
            "Organize the starter channels, introduce each specialist, and define a simple "
            "routine for assigning tasks and sharing progress.",
            5,
            "done",
            "med",
        ),
    ]
    channels_by_name = {channel.name: channel for channel in channels}
    for title, description, index, status, priority in task_seeds:
        agent = agents[index]
        channel = channels_by_name.get(agent.role, channels_by_name["general"])
        session.add(
            Task(
                title=title,
                description=description,
                assignee_agent_id=agent.id,
                channel_id=channel.id,
                status=status,
                priority=priority,
                xp_awarded=status == "done",
            )
        )
    session.commit()
