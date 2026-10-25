from datetime import datetime, timezone
from typing import Literal

from sqlalchemy import JSON, Column, String
from sqlmodel import Field, SQLModel


def now() -> datetime:
    return datetime.now(timezone.utc)


Role = Literal["frontend", "backend", "finance", "design", "research", "ops"]
Status = Literal["online", "busy", "idle", "offline"]
TaskStatus = Literal["todo", "in_progress", "review", "done"]
Priority = Literal["low", "med", "high"]


class Organization(SQLModel, table=True):
    id: int | None = Field(default=None, primary_key=True)
    name: str


class Agent(SQLModel, table=True):
    id: int | None = Field(default=None, primary_key=True)
    handle: str = Field(unique=True, index=True)
    name: str
    role: Role = Field(sa_type=String)
    title: str
    avatar_color: str = "#8b5cf6"
    status: Status = Field(default="online", sa_type=String)
    level: int = 1
    xp: int = 0
    skills: list[str] = Field(default_factory=list, sa_column=Column(JSON))
    bio: str = ""
    runtime: str = "stub"
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
