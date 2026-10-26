import asyncio
import io
import json
import os
import shutil
import subprocess
import sys
from decimal import Decimal
from pathlib import Path

import pytest
from sqlmodel import Session, select

from app import relay
from app.config import Settings, settings
from app.model_catalog import find_model
from app.models import SpendLedger
from app.relay import list_price_usage, may_failover, parse_pricing, resolve_route
from app.runtime import pi


def test_env_aliases_and_primary_precedence(monkeypatch):
    for name in (
        "RELAY_BASE_URL",
        "RELAY_BASE_URL_V1",
        "RELAY_RESERVE_URL",
        "RELAY_RESERVE_URL_V1",
    ):
        monkeypatch.delenv(name, raising=False)
    monkeypatch.setenv("RELAY_BASE_URL_V1", "https://example.test/primary")
    monkeypatch.setenv("RELAY_RESERVE_URL_V1", "https://example.test/reserve")
    value = Settings(_env_file=None)
    assert value.relay_base_url.endswith("/primary") and value.relay_reserve_url.endswith(
        "/reserve"
    )
    monkeypatch.setenv("RELAY_BASE_URL", "https://example.test/override")
    assert Settings(_env_file=None).relay_base_url.endswith("/override")
    monkeypatch.setenv("RELAY_BASE_URL", "")
    assert Settings(_env_file=None).relay_base_url.endswith("/primary")


def test_direct_route_preferred_then_same_model_via_relay(monkeypatch):
    monkeypatch.setattr(settings, "relay_key", "test-placeholder")
    monkeypatch.setattr(settings, "relay_base_url", "https://example.test/primary")
    route = resolve_route("deepseek", "deepseek-flash")
    assert route["provider"] == "relay" and route["model_id"] == "deepseek-v4.1-flash-1017"
    assert resolve_route("anthropic", "claude-haiku-5-5")["model_id"] == "claude-haiku-5-5"
    monkeypatch.setattr(settings, "deepseek_api_key", "native-test-placeholder")
    assert resolve_route("deepseek", "deepseek-flash")["provider"] == "deepseek"
    assert resolve_route("openai", "unknown-model")["configured"] is False


def test_real_pricing_shape_ignores_group_discount_and_credit_multipliers():
    payload = json.loads(
        Path(__file__).with_name("fixtures").joinpath("relay-pricing.json").read_text()
    )
    rows = parse_pricing(payload)
    assert Decimal(rows["deepseek-v4.1-flash-1017"]["input"]) == Decimal("0.30")
    assert Decimal(rows["deepseek-v4.1-flash-1017"]["output"]) == Decimal("1.20")
    assert Decimal(rows["gpt-6-luna"]["input"]) == Decimal("0.10")
    assert Decimal(rows["claude-haiku-5-5"]["output"]) == Decimal("0.50")
    assert rows["gpt-6-luna"]["context"] == 1050000
    assert parse_pricing({"data": [{"model_name": "gpt-6-luna", "model_ratio": "NaN"}]}) == {}
    usage = {"input": 86, "output": 20, "cacheRead": 0, "cacheWrite": 0, "totalTokens": 106}
    priced = list_price_usage(usage, find_model("relay", "deepseek-v4.1-flash-1017"))
    assert Decimal(str(priced["cost"]["total"])) == Decimal("0.0000498")
    assert priced["price_basis"] == "list"


def test_pricing_refresh_is_cached_and_failure_keeps_verified_catalog(monkeypatch):
    payload = Path(__file__).with_name("fixtures").joinpath("relay-pricing.json").read_bytes()
    monkeypatch.setattr(settings, "relay_base_url", "https://example.test/v1")
    monkeypatch.setattr(relay, "_cached_for", None)
    monkeypatch.setattr(relay, "_prices", {})
    monkeypatch.setattr(relay, "_refresh_at", 0)
    calls = []

    def fetch(*args, **kwargs):
        calls.append(kwargs["timeout"])
        return io.BytesIO(payload)

    monkeypatch.setattr(relay.urllib.request, "urlopen", fetch)
    asyncio.run(relay.refresh_pricing())
    asyncio.run(relay.refresh_pricing())
    assert calls == [3]
    assert find_model("relay", "gpt-6-luna")["context"] == 1050000

    def unavailable(*args, **kwargs):
        raise TimeoutError("offline")

    monkeypatch.setattr(relay.urllib.request, "urlopen", unavailable)
    monkeypatch.setattr(relay, "_refresh_at", 0)
    asyncio.run(relay.refresh_pricing())
    assert find_model("relay", "gpt-6-luna")["context"] == 1050000
    monkeypatch.setattr(settings, "relay_base_url", "https://other.test/v1")
    asyncio.run(relay.refresh_pricing())
    assert find_model("relay", "gpt-6-luna")["price_verified"] is True
    assert find_model("relay", "gpt-6-luna")["context"] == 272000


@pytest.mark.parametrize(
    "failure,streamed,usage,allowed",
    [
        ({"status": 503}, False, False, True),
        ({"kind": "connection"}, False, False, True),
        ({"kind": "timeout"}, False, False, True),
        ({"status": 401}, False, False, False),
        ({"status": 429}, False, False, False),
        ({"status": 503}, True, False, False),
        ({"status": 503}, False, True, False),
        ({}, False, False, False),
    ],
)
def test_failover_rules(failure, streamed, usage, allowed):
    assert may_failover(failure, streamed, usage) is allowed


@pytest.mark.parametrize(
    "mode,states",
    [
        ("primary", ["released", "settled"]),
        ("both", ["released", "released"]),
        ("partial", ["unresolved"]),
        ("usage", ["unresolved"]),
        ("auth", ["unresolved"]),
    ],
)
def test_fake_relay_failover_reserves_again_without_swapping(
    client, db_engine, monkeypatch, tmp_path, mode, states
):
    async def no_refresh():
        pass

    monkeypatch.setattr(pi, "refresh_pricing", no_refresh)
    monkeypatch.setattr(settings, "relay_key", "test-placeholder")
    monkeypatch.setattr(settings, "relay_base_url", "https://example.test/primary")
    monkeypatch.setattr(settings, "relay_reserve_url", "https://example.test/reserve")
    monkeypatch.setattr(settings, "runtime_data_dir", str(tmp_path / "runtime"))
    fake = str(Path(__file__).with_name("fake_pi.py"))
    monkeypatch.setattr(
        pi, "runtime_command", lambda: [sys.executable, "-u", fake, "--relay-failure", mode]
    )
    assert (
        client.patch(
            "/api/agents/2", json={"harness": "pi", "provider": "openai", "model_id": "gpt-6-luna"}
        ).status_code
        == 200
    )
    client.post("/api/channels/1/messages", json={"body": "@omar hello"})
    with Session(db_engine) as session:
        rows = session.exec(select(SpendLedger).order_by(SpendLedger.id)).all()
        assert [row.state for row in rows] == states
        assert all(row.provider == "relay" and row.model_id == "gpt-6-luna" for row in rows)
    if mode == "both":
        body = client.get("/api/channels/1/messages").json()[-1]["body"]
        assert "gpt-6-luna" in body and "temporarily unavailable" in body
    if mode == "auth":
        assert "authentication failed" in client.get("/api/channels/1/messages").json()[-1]["body"]


def test_sse_usage_is_normalized_before_pi_accounting():
    node = shutil.which("node")
    if not node:
        pytest.skip("Node required")
    module = json.dumps((pi.RUNTIME_NODE / "relay-fetch.mjs").as_uri())
    script = f"""
      import assert from 'node:assert/strict';
      import {{normalizeUsage, createRelayFetch}} from {module};
      const odd = {{prompt_tokens:27,prompt_cache_miss_tokens:86,total_tokens:106,completion_tokens:20}};
      assert.equal(normalizeUsage(odd).prompt_tokens,86);
      assert.equal(normalizeUsage({{...odd,total_tokens:120}}).prompt_tokens,100);
      const events=[];
      const fetcher=createRelayFetch(async()=>new Response('data: '+JSON.stringify({{usage:odd}})+'\\n\\ndata: [DONE]\\n\\n'),e=>events.push(e));
      const response=await fetcher('https://example.test');
      assert.match(await response.text(), /"prompt_tokens":86/);
      assert.equal(events[0].type,'relay.usage');
    """
    result = subprocess.run(
        [node, "--input-type=module", "-e", script],
        capture_output=True,
        text=True,
        timeout=10,
        creationflags=subprocess.CREATE_NO_WINDOW if os.name == "nt" else 0,
    )
    assert result.returncode == 0, result.stderr
