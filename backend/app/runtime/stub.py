import asyncio

from ..models import Agent, Message


class StubRuntime:
    async def respond(self, agent: Agent, message: Message, context: list[Message]) -> str:
        await asyncio.sleep(0.8)
        voices = {
            "frontend": "I'll think through the components, accessibility, and responsive details.",
            "backend": "I'll map out the API contracts, data model, and edge cases.",
            "finance": "I'll check the numbers, assumptions, and budget implications.",
            "design": "I'll explore the visual hierarchy and make the experience feel cohesive.",
            "research": "I'll gather sources and turn the findings into a clear recommendation.",
            "ops": "I'll break this into practical steps and keep the team moving.",
        }
        return (
            f"Got it! {voices[agent.role]}\n\n"
            f"*This is a Phase 1 stub reply from {agent.name}; "
            "no AI service is connected yet.*"
        )
