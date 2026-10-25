import asyncio

from ..models import Agent, Message


class StubRuntime:
    async def respond(self, agent: Agent, message: Message, context: list[Message]) -> str:
        department = agent.department
        voices = {
            "leadership": "I'll summarize the priorities, decisions, and accountable owners.",
            "operations": "I'll map the process, resources, and delivery steps.",
            "finance": "I'll check the assumptions, budget, and financial implications.",
            "people": "I'll review the people needs, onboarding, and policy implications.",
            "product": "I'll clarify customer needs, priorities, and expected outcomes.",
            "engineering": "I'll review the systems, implementation, and reliability risks.",
            "marketing": "I'll outline the audience, message, campaign, and success metrics.",
            "sales": "I'll review account context, customer needs, and next steps.",
            "design": "I'll review usability, customer journeys, and visual consistency.",
            "legal": "I'll outline the obligations, contract questions, and review steps.",
            "customer-support": "I'll check the customer issue, troubleshooting steps, and resolution.",
            "research": "I'll gather evidence and summarize the findings for a decision.",
            "data-analytics": "I'll check the metrics, data quality, and analysis approach.",
        }
        voice = (
            voices.get(department.slug, f"I'll review this with the {department.name} team.")
            if department
            else "I'll review the request and identify the next steps."
        )
        return (
            f"{voice}\n\n"
            f"*This is a Phase 1 stub reply from {agent.name}; "
            "no AI service is connected yet.*"
        )

    async def stream(self, agent: Agent, message: Message, context: list[Message]):
        await asyncio.sleep(0.3)
        body = await self.respond(agent, message, context)
        for start in range(0, len(body), 12):
            await asyncio.sleep(0.05)
            yield body[start : start + 12]
