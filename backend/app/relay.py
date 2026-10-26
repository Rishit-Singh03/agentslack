"""Relay routes and cached, unauthenticated new-api list pricing. No credit conversion."""

import asyncio
import json
import time
import urllib.request
from decimal import Decimal, InvalidOperation
from urllib.parse import urlsplit, urlunsplit

from .config import settings

_prices = {}
_cached_for = None
_refresh_at = 0
_lock = asyncio.Lock()


def parse_pricing(payload):
    from .model_catalog import CATALOG

    known = {item["model_id"] for item in CATALOG if item["provider"] == "relay"}
    parsed = {}
    for row in payload.get("data", []):
        if row.get("model_name") not in known or row.get("quota_type", 0) != 0:
            continue
        try:
            ratio = Decimal(str(row["model_ratio"]))
            completion = Decimal(str(row["completion_ratio"]))
            cache = Decimal(str(row["cache_ratio"]))
            if (
                not all(value.is_finite() and value >= 0 for value in (ratio, completion, cache))
                or ratio == 0
            ):
                continue
            item = {
                "input": str(ratio * 2),
                "output": str(ratio * 2 * completion),
                "cached": str(ratio * 2 * cache),
            }
            context = row.get("context_length")
            if isinstance(context, int) and 4096 <= context <= 2_000_000:
                item["context"] = context
            parsed[row["model_name"]] = item
        except (KeyError, InvalidOperation, TypeError, ValueError):
            continue
    return parsed


def cached_models():
    from .model_catalog import CATALOG

    models = []
    for item in CATALOG:
        prices = (
            _prices.get(item["model_id"], {})
            if item["provider"] == "relay" and _cached_for == settings.relay_base_url
            else {}
        )
        if not prices:
            models.append(dict(item))
            continue
        scale = Decimal(prices["input"]) / Decimal(item["input"])
        updated = {**item, **prices}
        for name in ("reserve_input", "cache_write", "worst_input", "worst_output"):
            updated[name] = str(Decimal(item[name]) * scale)
        updated["pricing_tiers"] = [
            {
                **tier,
                "input": str(Decimal(tier["input"]) * scale),
                "output": str(Decimal(tier["output"]) * scale),
            }
            for tier in item["pricing_tiers"]
        ]
        models.append(updated)
    return models


async def refresh_pricing():
    global _prices, _cached_for, _refresh_at
    if not settings.relay_base_url:
        return
    async with _lock:
        if _cached_for == settings.relay_base_url and time.monotonic() < _refresh_at:
            return
        base = settings.relay_base_url
        if _cached_for != base:
            _prices = {}

        def fetch():
            url = urlsplit(base)
            target = urlunsplit((url.scheme, url.netloc, "/api/pricing", "", ""))
            with urllib.request.urlopen(target, timeout=3) as response:
                return parse_pricing(json.loads(response.read(2_000_000)))

        try:
            prices = await asyncio.wait_for(asyncio.to_thread(fetch), 4)
            if prices:
                _prices = prices
        except Exception:
            pass  # Retain the last successful price snapshot for this endpoint.
        _cached_for, _refresh_at = base, time.monotonic() + 3600


def resolve_route(provider, model_id):
    from .model_catalog import DEFAULTS, provider_key

    selected = next(
        (
            item
            for item in DEFAULTS
            if item["provider"] == provider and item["model_id"] == model_id
        ),
        None,
    )
    relay_ready = bool(settings.relay_key and settings.relay_base_url)
    if provider_key(provider) and provider != "relay":
        return {"provider": provider, "model_id": model_id, "label": "direct", "configured": True}
    if selected and relay_ready:
        return {
            "provider": "relay",
            "model_id": selected["relay_model_id"],
            "label": "via relay",
            "configured": True,
        }
    return {
        "provider": provider,
        "model_id": model_id,
        "label": "via relay" if provider == "relay" else "direct",
        "configured": relay_ready if provider == "relay" else False,
    }


def list_price_usage(usage, model):
    """Reprice normalized Pi tokens; reasoning is already included in output."""
    total_input = usage["input"] + usage["cacheRead"] + usage["cacheWrite"]
    multiplier = Decimal(1)
    output_rate = Decimal(model["output"])
    for tier in model["pricing_tiers"]:
        if total_input > tier["above"]:
            multiplier = Decimal(tier["input"]) / Decimal(model["reserve_input"])
            output_rate = Decimal(tier["output"])
    rates = {
        "input": Decimal(model["input"]) * multiplier,
        "cacheRead": Decimal(model["cached"]) * multiplier,
        "cacheWrite": Decimal(model["cache_write"]) * multiplier,
        "output": output_rate,
    }
    costs = {key: Decimal(str(usage[key])) * rate / 1_000_000 for key, rate in rates.items()}
    return {
        **usage,
        "cost": {
            **{key: float(value) for key, value in costs.items()},
            "total": float(sum(costs.values())),
        },
        "route": "relay",
        "price_basis": "list",
    }


def may_failover(failure, streamed, usage_reported):
    return (
        not streamed
        and not usage_reported
        and (
            failure.get("kind") in {"connection", "timeout"}
            or 500 <= failure.get("status", 0) <= 599
        )
    )
