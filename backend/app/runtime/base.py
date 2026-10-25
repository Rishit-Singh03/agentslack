from typing import Protocol

from ..models import Agent, Message


class AgentRuntime(Protocol):
    async def respond(self, agent: Agent, message: Message, context: list[Message]) -> str: ...
