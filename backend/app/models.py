from datetime import datetime, timezone
from decimal import Decimal
from typing import Literal

from sqlalchemy import JSON, Column, String
from sqlalchemy.types import TypeDecorator
from sqlmodel import Field, Relationship, SQLModel


def now() -> datetime:
    return datetime.now(timezone.utc)


Status = Literal["online", "busy", "idle", "offline"]
TaskStatus = Literal["todo", "in_progress", "review", "done"]
Priority = Literal["low", "med", "high"]


class DecimalText(TypeDecorator):
    impl = String
    cache_ok = True

    def process_bind_param(self, value, dialect):
        return str(value) if value is not None else None

    def process_result_value(self, value, dialect):
        return Decimal(value) if value is not None else None


class Organization(SQLModel, table=True):
    id: int | None = Field(default=None, primary_key=True)
    name: str = "unnamed"
    slug: str = "unnamed"
    tagline: str = ""
    accent: str = "#3ddc84"
    theme: str = "dark"
    density: str = "compact"
    font_mode: str = "mixed"
    crt_effects: bool = False
    initialized: bool = False
    default_provider: str = "openai"
    default_model_id: str = "gpt-6-luna"
    org_monthly_budget_usd: Decimal = Field(default=Decimal("100"), sa_type=DecimalText)


class UserProfile(SQLModel, table=True):
    id: int | None = Field(default=None, primary_key=True)
    display_name: str = "You"
    handle: str = "@you"


class Department(SQLModel, table=True):
    id: int | None = Field(default=None, primary_key=True)
    name: str = Field(unique=True)
    slug: str = Field(unique=True)
    description: str = ""
    color: str = "#3ddc84"
    channel_id: int = Field(foreign_key="channel.id", unique=True)
    sort_order: int = 0
    created_at: datetime = Field(default_factory=now)


class Agent(SQLModel, table=True):
    id: int | None = Field(default=None, primary_key=True)
    handle: str = Field(unique=True, index=True)
    name: str
    department_id: int | None = Field(default=None, foreign_key="department.id")
    department: Department | None = Relationship()
    title: str
    avatar_color: str = "#3ddc84"
    status: Status = Field(default="online", sa_type=String)
    level: int = 1
    xp: int = 0
    skills: list[str] = Field(default_factory=list, sa_column=Column(JSON))
    bio: str = ""
    runtime: str = "stub"
    harness: str = "pi"
    provider: str = "openai"
    model_id: str = "gpt-6-luna"
    thinking_level: str = "off"
    max_output_tokens: int = 4096
    monthly_budget_usd: Decimal = Field(default=Decimal("10"), sa_type=DecimalText)
    created_at: datetime = Field(default_factory=now)


class Channel(SQLModel, table=True):
    id: int | None = Field(default=None, primary_key=True)
    name: str
    topic: str = ""
    is_dm: bool = False
    dm_agent_id: int | None = Field(default=None, foreign_key="agent.id", unique=True)
    created_at: datetime = Field(default_factory=now)


class ChannelMember(SQLModel, table=True):
    channel_id: int = Field(foreign_key="channel.id", primary_key=True)
    agent_id: int = Field(foreign_key="agent.id", primary_key=True)


class Message(SQLModel, table=True):
    id: int | None = Field(default=None, primary_key=True)
    channel_id: int = Field(foreign_key="channel.id", index=True)
    author_type: Literal["human", "agent", "system"] = Field(default="human", sa_type=String)
    author_id: int | None = Field(default=None, foreign_key="agent.id")
    body: str
    is_streaming: bool = False
    model_id: str | None = None
    usage: dict | None = Field(default=None, sa_column=Column(JSON))
    cost_usd: str | None = None
    thread_parent_id: int | None = Field(default=None, foreign_key="message.id")
    created_at: datetime = Field(default_factory=now)


class Task(SQLModel, table=True):
    id: int | None = Field(default=None, primary_key=True)
    title: str
    description: str = ""
    assignee_agent_id: int = Field(foreign_key="agent.id")
    channel_id: int | None = Field(default=None, foreign_key="channel.id")
    status: TaskStatus = Field(default="todo", sa_type=String)
    priority: Priority = Field(default="med", sa_type=String)
    xp_reward: int = 25
    xp_awarded: bool = False
    created_at: datetime = Field(default_factory=now)
    updated_at: datetime = Field(default_factory=now)


class MemoryEntry(SQLModel, table=True):
    id: int | None = Field(default=None, primary_key=True)
    agent_id: int = Field(foreign_key="agent.id")
    kind: Literal["fact", "lesson", "preference"] = Field(sa_type=String)
    content: str
    created_at: datetime = Field(default_factory=now)


class SpendLedger(SQLModel, table=True):
    id: int | None = Field(default=None, primary_key=True)
    # Retain accounting when an employee is dismissed.
    agent_id: int = Field(index=True)
    channel_id: int
    run_id: str = Field(unique=True)
    provider: str
    model_id: str
    state: str = "reserved"
    reserved_usd: str
    cost_usd: str | None = None
    usage: dict | None = Field(default=None, sa_column=Column(JSON))
    pricing: dict = Field(default_factory=dict, sa_column=Column(JSON))
    created_at: datetime = Field(default_factory=now, index=True)
