"""Single-worker budget reservations. Persisted holds survive runtime/API failure."""

import asyncio
import math
from datetime import datetime, timezone
from decimal import Decimal
from uuid import uuid4

from sqlmodel import Session, select

from .models import Organization, SpendLedger

budget_lock = asyncio.Lock()


class BudgetError(Exception):
    pass


def month_start():
    return datetime.now(timezone.utc).replace(day=1, hour=0, minute=0, second=0, microsecond=0)


def charged(row):
    if row.state == "released":
        return Decimal(0)
    if row.state == "settled":
        return Decimal(row.cost_usd)
    return Decimal(row.reserved_usd)


def spend_summary(session, agent_id=None):
    query = select(SpendLedger).where(SpendLedger.created_at >= month_start())
    if agent_id is not None:
        query = query.where(SpendLedger.agent_id == agent_id)
    rows = session.exec(query.order_by(SpendLedger.id.desc())).all()
    settled = sum((charged(row) for row in rows if row.state == "settled"), Decimal(0))
    held = sum(
        (charged(row) for row in rows if row.state in {"reserved", "unresolved"}), Decimal(0)
    )
    return {
        "month": month_start().strftime("%Y-%m"),
        "settled_usd": str(settled),
        "held_usd": str(held),
        "total_usd": str(settled + held),
        "recent": rows[:20],
    }


def validate_price(model):
    if model is None:
        raise BudgetError("Unknown model price; add validated pricing before running this model.")
    if not model.get("price_verified", True):
        raise BudgetError(
            "Unknown relay tariff; verify the relay's prices in the catalog before running."
        )


def estimate_input_tokens(context_tokens, message, system_prompt):
    if context_tokens is None:
        return None
    # Include exactly the new RPC prompt, its system text, framing, and a 25% margin.
    # Existing context may already include system text: double counting is conservative.
    added = math.ceil(len(message) / 3) + math.ceil(len(system_prompt) / 3) + 256
    return math.ceil((context_tokens + added) * 1.25)


def reservation_quote(model, max_output_tokens, input_tokens=None):
    validate_price(model)
    if not 1 <= max_output_tokens <= model["max_output"]:
        raise BudgetError("Maximum output tokens exceeds this model's output limit.")
    unknown = input_tokens is None
    input_tokens = model["context"] if unknown else input_tokens
    input_rate = model["worst_input"] if unknown else model["reserve_input"]
    output_rate = model["worst_output"] if unknown else model["output"]
    if not unknown:
        for tier in model["pricing_tiers"]:
            if input_tokens > tier["above"]:
                input_rate, output_rate = tier["input"], tier["output"]
    amount = (
        Decimal(input_rate) * input_tokens + Decimal(output_rate) * max_output_tokens
    ) / 1_000_000
    return {
        "input_tokens": input_tokens,
        "max_output_tokens": max_output_tokens,
        "input_rate": input_rate,
        "output_rate": output_rate,
        "unknown_context": unknown,
        "reserved_usd": str(amount),
    }


async def reserve(bind, agent, channel_id, model, input_tokens=None):
    quote = reservation_quote(model, agent.max_output_tokens, input_tokens)
    amount = Decimal(quote["reserved_usd"])
    async with budget_lock:
        with Session(bind) as session:
            org = session.exec(select(Organization)).one()
            agent_spend = Decimal(spend_summary(session, agent.id)["total_usd"])
            org_spend = Decimal(spend_summary(session)["total_usd"])
            if agent_spend + amount > Decimal(agent.monthly_budget_usd):
                raise BudgetError(
                    "Monthly salary exhausted or insufficient for this reply's reservation."
                )
            if org_spend + amount > Decimal(org.org_monthly_budget_usd):
                raise BudgetError(
                    "Organization monthly budget exhausted or insufficient for reservation."
                )
            row = SpendLedger(
                agent_id=agent.id,
                channel_id=channel_id,
                run_id=uuid4().hex,
                provider=agent.provider,
                model_id=agent.model_id,
                reserved_usd=str(amount),
                pricing={"model": model, "reservation": quote},
            )
            session.add(row)
            session.commit()
            session.refresh(row)
            return row.id


def finish(bind, ledger_id, usage=None, started=True):
    with Session(bind) as session:
        row = session.get(SpendLedger, ledger_id)
        if row.state != "reserved":
            return
        if usage is not None:
            row.state = "settled"
            row.usage = usage
            row.cost_usd = str(Decimal(str(usage["cost"]["total"])))
        else:
            row.state = "unresolved" if started else "released"
        session.add(row)
        session.commit()


def recover_reservations(session):
    for row in session.exec(select(SpendLedger).where(SpendLedger.state == "reserved")).all():
        row.state = "unresolved"
        session.add(row)
    session.commit()
