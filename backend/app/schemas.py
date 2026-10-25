from pydantic import BaseModel, Field, field_validator

from .models import Priority, Role, Status, TaskStatus


class AgentCreate(BaseModel):
    handle: str = Field(pattern=r"^@[a-z][a-z0-9_]{0,30}$")
    name: str = Field(min_length=1, max_length=100)
    role: Role
    title: str = Field(min_length=1, max_length=150)
    avatar_color: str = Field(default="#8b5cf6", pattern=r"^#[0-9a-fA-F]{6}$")
    skills: list[str] = Field(default_factory=list)
    bio: str = ""


class AgentPatch(BaseModel):
    name: str | None = Field(default=None, min_length=1, max_length=100)
    title: str | None = Field(default=None, min_length=1, max_length=150)
    role: Role | None = None
    status: Status | None = None
    skills: list[str] | None = None
    bio: str | None = None


class ChannelCreate(BaseModel):
    name: str = Field(pattern=r"^[a-z0-9][a-z0-9-]{0,49}$")
    topic: str = Field(default="", max_length=500)


class MessageCreate(BaseModel):
    body: str = Field(min_length=1, max_length=10000)
    thread_parent_id: int | None = None

    @field_validator("body")
    @classmethod
    def nonempty(cls, value):
        if not value.strip():
            raise ValueError("Message cannot be blank")
        return value.strip()


class TaskCreate(BaseModel):
    title: str = Field(min_length=1, max_length=200)
    description: str = ""
    assignee_agent_id: int
    channel_id: int | None = None
    priority: Priority = "med"
    xp_reward: int = Field(default=25, ge=0, le=1000)


class TaskPatch(BaseModel):
    title: str | None = Field(default=None, min_length=1, max_length=200)
    description: str | None = None
    assignee_agent_id: int | None = None
    status: TaskStatus | None = None
    priority: Priority | None = None
