"""Curated routes and conservative USD/1M rates, verified 2026-10-25.

Budget reservations use estimated prompt size and its applicable tier, including cache writes. Custom IDs
can be saved, but cannot run until their capabilities and pricing are added here.
"""

from .config import settings

PROVIDERS = {
    "deepseek": "DEEPSEEK_API_KEY",
    "anthropic": "ANTHROPIC_API_KEY",
    "openai": "OPENAI_API_KEY",
    "openrouter": "OPENROUTER_API_KEY",
    "relay": "RELAY_KEY",
}

DEFAULTS = [
    {
        "provider": "deepseek",
        "model_id": "deepseek-flash",
        "relay_model_id": "deepseek-v4.1-flash-1017",
        "name": "DeepSeek V4.1 Flash (1017)",
        "api": "openai-completions",
        "context": 1_000_000,
        "max_output": 384_000,
        "thinking_levels": ["off", "high", "max"],
        "input": "0.30",
        "cached": "0.006",
        "output": "1.20",
        "cache_write": "0.30",
        "worst_input": "0.30",
        "worst_output": "1.20",
        "reserve_input": "0.30",
        "pricing_tiers": [],
        "price_note": "Peak rates shown; off-peak is half.",
    },
    {
        "provider": "anthropic",
        "model_id": "claude-haiku-5-5",
        "relay_model_id": "claude-haiku-5-5",
        "name": "Claude Haiku 5.5",
        "api": "anthropic-messages",
        "context": 1_000_000,
        "max_output": 128_000,
        "thinking_levels": ["off", "low", "medium", "high", "max"],
        "input": "0.10",
        "cached": "0.01",
        "output": "0.50",
        "cache_write": "0.20",
        "worst_input": "1.00",
        "worst_output": "2.50",
        "reserve_input": "0.20",
        "pricing_tiers": [{"above": 100_000, "input": "1.00", "output": "2.50"}],
        "price_note": "Above 100K prompt tokens rates are 5x; reserves include 1h cache writes.",
    },
    {
        "provider": "openai",
        "model_id": "gpt-6-luna",
        "relay_model_id": "gpt-6-luna",
        "name": "GPT-6 Luna",
        "api": "openai-responses",
        "context": 272_000,
        "max_output": 128_000,
        "thinking_levels": ["off", "low", "medium", "high", "xhigh", "max"],
        "input": "0.10",
        "cached": "0.01",
        "output": "0.50",
        "cache_write": "0.125",
        "worst_input": "0.50",
        "worst_output": "0.75",
        "reserve_input": "0.25",
        "pricing_tiers": [{"above": 272_000, "input": "0.50", "output": "0.75"}],
        "price_note": "Higher prices apply above 272K input tokens.",
    },
]

ROUTER_IDS = [
    "deepseek/deepseek-v4.1-flash-1017",
    "anthropic/claude-haiku-5.5",
    "openai/gpt-6-luna",
]
CATALOG = list(DEFAULTS)
for index, item in enumerate(DEFAULTS):
    CATALOG.append(
        {
            **item,
            "provider": "openrouter",
            "model_id": ROUTER_IDS[index],
            "api": "openai-completions",
        }
    )
    CATALOG.append(
        {
            **item,
            "provider": "relay",
            "model_id": item["relay_model_id"],
            "api": "openai-completions",
            "thinking_levels": ["off"],
            "price_verified": True,
            "price_basis": "list",
            "price_note": "List prices; relay discounts and credit conversions are excluded.",
        }
    )


def find_model(provider: str, model_id: str):
    from .relay import cached_models

    return next(
        (
            item
            for item in cached_models()
            if item["provider"] == provider and item["model_id"] == model_id
        ),
        None,
    )


def provider_key(provider: str) -> str | None:
    variable = PROVIDERS.get(provider)
    return getattr(settings, variable.lower(), None) if variable else None


def public_catalog():
    from .relay import cached_models, resolve_route

    return {
        "models": [
            {**item, "route": resolve_route(item["provider"], item["model_id"])}
            for item in cached_models()
        ],
        "providers": [
            {
                "id": provider,
                "env_var": variable,
                "configured": bool(provider_key(provider))
                and (provider != "relay" or bool(settings.relay_base_url)),
            }
            for provider, variable in PROVIDERS.items()
        ],
        "relay_base_url": safe_relay_url(),
        "relay_reserve_url": safe_relay_url(settings.relay_reserve_url),
    }


def safe_relay_url(value=None):
    # Strip userinfo/query/fragment: gateways sometimes put secrets in URLs.
    from urllib.parse import urlsplit, urlunsplit

    value = value or settings.relay_base_url
    if not value:
        return None
    url = urlsplit(value)
    host = url.hostname or ""
    if url.port:
        host += f":{url.port}"
    return urlunsplit((url.scheme, host, url.path, "", ""))


def preset(slug: str | None, org):
    if slug in {"leadership", "people", "marketing", "sales", "legal", "customer-support"}:
        return "anthropic", "claude-haiku-5-5"
    if slug in {"engineering", "data-analytics", "research"}:
        return "deepseek", "deepseek-flash"
    if slug in {"product", "operations", "finance", "design"}:
        return "openai", "gpt-6-luna"
    return org.default_provider, org.default_model_id
