import colorsys
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator

from .models import Priority, Status, TaskStatus


class AgentCreate(BaseModel):
    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)
    handle: str = Field(pattern=r"^@[a-z][a-z0-9_]{0,30}$")
    name: str = Field(min_length=1, max_length=100)
    department_id: int | None = None
    title: str = Field(min_length=1, max_length=150)
    avatar_color: str = Field(default="#3ddc84", pattern=r"^#[0-9a-fA-F]{6}$")
    skills: list[str] = Field(default_factory=list)
    bio: str = ""


class AgentPatch(BaseModel):
    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)
    name: str | None = Field(default=None, min_length=1, max_length=100)
    title: str | None = Field(default=None, min_length=1, max_length=150)
    department_id: int | None = None
    status: Status | None = None
    skills: list[str] | None = None
    bio: str | None = None
    avatar_color: str | None = Field(default=None, pattern=r"^#[0-9a-fA-F]{6}$")


class OrgPatch(BaseModel):
    model_config = ConfigDict(str_strip_whitespace=True)
    name: str | None = Field(default=None, min_length=1, max_length=100)
    tagline: str | None = Field(default=None, max_length=200)
    accent: str | None = Field(default=None, pattern=r"^#[0-9a-fA-F]{6}$")
    theme: Literal["dark", "paper"] | None = None
    density: Literal["compact", "comfortable"] | None = None
    font_mode: Literal["mixed", "mono"] | None = None
    crt_effects: bool | None = None


class ProfilePatch(BaseModel):
    model_config = ConfigDict(str_strip_whitespace=True)
    display_name: str | None = Field(default=None, min_length=1, max_length=100)
    handle: str | None = Field(default=None, pattern=r"^@[a-z][a-z0-9_]{0,30}$")


class DepartmentCreate(BaseModel):
    model_config = ConfigDict(str_strip_whitespace=True)
    name: str = Field(min_length=1, max_length=80)
    slug: str | None = Field(default=None, pattern=r"^[a-z0-9][a-z0-9-]{0,49}$")
    description: str = Field(default="", max_length=500)
    color: str = Field(default="#3ddc84", pattern=r"^#[0-9a-fA-F]{6}$")
    sort_order: int = Field(default=0, ge=0, le=10000)

    @field_validator("color")
    @classmethod
    def allowed_color(cls, value):
        red, green, blue = (int(value[index : index + 2], 16) / 255 for index in (1, 3, 5))
        hue, saturation, _ = colorsys.rgb_to_hsv(red, green, blue)
        if saturation > 0.15 and 230 <= hue * 360 <= 305:
            raise ValueError("Choose a neutral, green, amber, cyan, blue, or warm department color")
        return value.lower()


class DepartmentPatch(BaseModel):
    model_config = ConfigDict(str_strip_whitespace=True)
    name: str | None = Field(default=None, min_length=1, max_length=80)
    slug: str | None = Field(default=None, pattern=r"^[a-z0-9][a-z0-9-]{0,49}$")
    description: str | None = Field(default=None, max_length=500)
    color: str | None = Field(default=None, pattern=r"^#[0-9a-fA-F]{6}$")
    sort_order: int | None = Field(default=None, ge=0, le=10000)

    @field_validator("color")
    @classmethod
    def allowed_color(cls, value):
        return DepartmentCreate.allowed_color(value) if value is not None else None


class OnboardingCreate(BaseModel):
    model_config = ConfigDict(str_strip_whitespace=True)
    name: str = Field(min_length=1, max_length=100)
    display_name: str = Field(min_length=1, max_length=100)
    handle: str = Field(pattern=r"^@[a-z][a-z0-9_]{0,30}$")
    accent: str = Field(default="#3ddc84", pattern=r"^#[0-9a-fA-F]{6}$")
    sample_team: bool = True
    departments: list[DepartmentCreate] | None = Field(default=None, max_length=50)


class ChannelPatch(BaseModel):
    name: str | None = Field(default=None, pattern=r"^[a-z0-9][a-z0-9-]{0,49}$")
    topic: str | None = Field(default=None, max_length=500)


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
