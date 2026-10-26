import asyncio
import json
import os
import shutil
import subprocess
import sys
from decimal import Decimal
from pathlib import Path

import pytest
from sqlmodel import Session, select

from app import budget, db
from app.config import settings
from app.model_catalog import find_model, preset
from app.models import Agent, Department, Organization, SpendLedger
from app.runtime import pi


@pytest.fixture
def fake_pi(monkeypatch, tmp_path):
    monkeypatch.setattr(
        pi,
        "runtime_command",
        lambda: [sys.executable, "-u", str(Path(__file__).with_name("fake_pi.py"))],
    )
    monkeypatch.setattr(settings, "openai_api_key", "offline-test-placeholder")
    monkeypatch.setattr(settings, "runtime_data_dir", str(tmp_path / "runtime"))
    monkeypatch.setattr(settings, "pi_timeout", 2)


def enable_pi(client, **changes):
    response = client.patch(
        "/api/agents/2",
        json={
            "harness": "pi",
            "provider": "openai",
            "model_id": "gpt-6-luna",
            "thinking_level": "off",
            **changes,
        },
    )
    assert response.status_code == 200, response.text


def ledger(db_engine):
    with Session(db_engine) as session:
        return session.exec(select(SpendLedger).order_by(SpendLedger.id)).all()


def test_fake_rpc_stream_final_usage_and_socket(client, db_engine, fake_pi):
    enable_pi(client)
    with client.websocket_connect("/ws") as socket:
        assert client.post("/api/channels/1/messages", json={"body": "@omar hi"}).status_code == 201
        events = []
        while True:
            event = socket.receive_json()
            events.append(event)
            if event["type"] == "agent.updated" and event["data"]["status"] == "online":
                break
    deltas = [event["data"]["delta"] for event in events if event["type"] == "message.delta"]
    assert "".join(deltas) == "Hello from the fake."
    final = client.get("/api/channels/1/messages").json()[-1]
    assert final["body"] == "Hello from the fake (final)."
    assert final["model_id"] == "gpt-6-luna"
    assert final["usage"]["totalTokens"] == 125
    assert Decimal(final["cost_usd"]) == Decimal("0.00002")
    assert ledger(db_engine)[0].state == "settled"
    assert any(event["type"] == "spend.updated" for event in events)
    assert client.get("/api/agents/2/spend").json()["total_usd"] == "0.00002"


@pytest.mark.parametrize(
    "marker,state",
    [
        ("FAKE_MISSING", "unresolved"),
        ("FAKE_EXIT", "unresolved"),
        ("FAKE_ERROR", "unresolved"),
        ("FAKE_STATS", "settled"),
    ],
)
def test_terminal_paths_and_stats_delta(client, db_engine, fake_pi, marker, state):
    enable_pi(client)
    # Successful first call proves stats fallback is a delta, not the session total.
    client.post("/api/channels/1/messages", json={"body": "@omar baseline"})
    client.post("/api/channels/1/messages", json={"body": f"@omar {marker}"})
    rows = ledger(db_engine)
    assert rows[-1].state == state
    if marker == "FAKE_STATS":
        assert Decimal(rows[-1].cost_usd) == Decimal("0.00002")
    if marker in {"FAKE_EXIT", "FAKE_ERROR"}:
        assert client.get("/api/channels/1/messages").json()[-1]["author_type"] == "system"
    assert client.get("/api/agents/2").json()["status"] == "online"


def test_missing_key_and_unknown_price_are_visible(client, db_engine, fake_pi, monkeypatch):
    enable_pi(client)
    monkeypatch.setattr(settings, "openai_api_key", None)
    client.post("/api/channels/1/messages", json={"body": "@omar hi"})
    message = client.get("/api/channels/1/messages").json()[-1]
    assert message["author_type"] == "system" and "OPENAI_API_KEY" in message["body"]
    assert ledger(db_engine) == []
    monkeypatch.setattr(settings, "openai_api_key", "offline-test-placeholder")
    enable_pi(client, model_id="unknown-custom")
    client.post("/api/channels/1/messages", json={"body": "@omar hi"})
    assert "Unknown model price" in client.get("/api/channels/1/messages").json()[-1]["body"]
    assert ledger(db_engine) == []


def test_budget_refusal_and_config_validation(client, db_engine, fake_pi):
    enable_pi(client, monthly_budget_usd="0")
    client.post("/api/channels/1/messages", json={"body": "@omar hi"})
    assert "salary exhausted" in client.get("/api/channels/1/messages").json()[-1]["body"]
    assert ledger(db_engine) == []
    assert client.patch("/api/agents/2", json={"monthly_budget_usd": "-1"}).status_code == 422
    assert client.patch("/api/agents/2", json={"monthly_budget_usd": "NaN"}).status_code == 422
    assert client.patch("/api/agents/2", json={"thinking_level": "invented"}).status_code == 422
    assert client.patch("/api/org", json={"org_monthly_budget_usd": "Infinity"}).status_code == 422


def test_concurrent_reservations_and_restart_holds(db_engine):
    with Session(db_engine) as session:
        agents = session.exec(select(Agent).limit(2)).all()
        for agent in agents:
            agent.monthly_budget_usd = Decimal("10")
        org = session.exec(select(Organization)).one()
        org.org_monthly_budget_usd = Decimal("0.25")
        session.add(org)
        session.commit()
        for agent in agents:
            session.refresh(agent)

    async def run():
        return await asyncio.gather(
            *(
                budget.reserve(db_engine, agent, 1, find_model("openai", "gpt-6-luna"))
                for agent in agents
            ),
            return_exceptions=True,
        )

    results = asyncio.run(run())
    assert sum(isinstance(result, int) for result in results) == 1
    assert sum(isinstance(result, budget.BudgetError) for result in results) == 1
    with Session(db_engine) as session:
        budget.recover_reservations(session)
        assert session.exec(select(SpendLedger)).one().state == "unresolved"
        assert Decimal(budget.spend_summary(session)["held_usd"]) > 0


def test_abort_kills_process_and_keeps_unresolved(db_engine, fake_pi, monkeypatch):
    from app.models import Message

    async def run():
        instance = pi.PiSupervisor()
        monkeypatch.setattr(pi, "supervisor", instance)
        with Session(db_engine) as session:
            agent = session.get(Agent, 2)
            message = Message(id=999, channel_id=1, body="FAKE_HANG")

        async def consume():
            async for _ in pi.PiRuntime().events(db_engine, agent, message, [message]):
                pass

        task = asyncio.create_task(consume())
        for _ in range(100):
            slot = instance.slots.get(2)
            if slot and slot.process and ledger(db_engine):
                await asyncio.sleep(0.05)
                break
            await asyncio.sleep(0.01)
        process = instance.slots[2].process
        await instance.abort(2)
        with pytest.raises(pi.RuntimeFailure):
            await task
        assert process.process.returncode is not None
        await instance.close()

    asyncio.run(run())
    assert ledger(db_engine)[0].state == "unresolved"


def test_catalog_redacts_keys_and_migration(client, db_engine, monkeypatch):
    monkeypatch.setattr(settings, "relay_key", "never-return-this-secret")
    monkeypatch.setattr(
        settings, "relay_base_url", "https://user:secret@example.test/v1?key=secret"
    )
    response = client.get("/api/models")
    assert "never-return" not in response.text and "secret" not in response.text
    assert response.json()["relay_base_url"] == "https://example.test/v1"
    assert len(response.json()["models"]) == 9
    assert client.get("/api/org/spend").status_code == 200
    with db_engine.begin() as connection:
        for column in (
            "harness",
            "provider",
            "model_id",
            "thinking_level",
            "max_output_tokens",
            "monthly_budget_usd",
        ):
            connection.exec_driver_sql(f'ALTER TABLE agent DROP COLUMN "{column}"')
    monkeypatch.setattr(db, "engine", db_engine)
    db.create_all()
    db.create_all()
    with Session(db_engine) as session:
        org = session.exec(select(Organization)).one()
        for agent in session.exec(select(Agent)).all():
            department = session.get(Department, agent.department_id)
            assert agent.harness == "pi"
            assert agent.max_output_tokens == 4096
            assert (agent.provider, agent.model_id) == preset(department.slug, org)


def test_missing_install_does_not_reserve(client, db_engine, fake_pi, monkeypatch):
    def unavailable():
        raise pi.RuntimeFailure("Pi is not installed. Run npm ci in backend/runtime-node.")

    monkeypatch.setattr(pi, "runtime_command", unavailable)
    enable_pi(client)
    client.post("/api/channels/1/messages", json={"body": "@omar hi"})
    assert "Pi is not installed" in client.get("/api/channels/1/messages").json()[-1]["body"]
    assert ledger(db_engine) == []
    assert client.get("/api/agents/2/spend").json()["total_usd"] == "0"


def test_queue_serialization_bound_and_idle_expiry(monkeypatch):
    monkeypatch.setattr(settings, "pi_queue_size", 2)
    monkeypatch.setattr(settings, "pi_idle_ttl", 0.02)

    async def run():
        instance = pi.PiSupervisor()
        entered, release = asyncio.Event(), asyncio.Event()
        order = []

        class Process:
            closed = False

            async def close(self):
                self.closed = True

        process = Process()

        async def first():
            async with instance.acquire(7) as slot:
                slot.process = process
                order.append("first")
                entered.set()
                await release.wait()
                order.append("first done")

        async def second():
            async with instance.acquire(7):
                order.append("second")

        first_task = asyncio.create_task(first())
        await entered.wait()
        second_task = asyncio.create_task(second())
        await asyncio.sleep(0)
        with pytest.raises(pi.RuntimeFailure, match="queue is full"):
            async with instance.acquire(7):
                pass
        release.set()
        await asyncio.gather(first_task, second_task)
        assert order == ["first", "first done", "second"]
        await asyncio.sleep(0.05)
        assert process.closed
        await instance.close()

    asyncio.run(run())


@pytest.mark.parametrize(
    "provider,model_id",
    [
        ("deepseek", "deepseek-flash"),
        ("anthropic", "claude-haiku-5-5"),
        ("openai", "gpt-6-luna"),
    ],
)
def test_small_salary_can_reply_and_output_cap_is_saved(
    client, db_engine, fake_pi, monkeypatch, provider, model_id
):
    monkeypatch.setattr(settings, pi.PROVIDERS[provider].lower(), "offline-test-placeholder")
    enable_pi(
        client, provider=provider, model_id=model_id, monthly_budget_usd="1", max_output_tokens=4096
    )
    client.post("/api/channels/1/messages", json={"body": "@omar hello"})
    row = ledger(db_engine)[0]
    assert row.state == "settled"
    assert Decimal(row.reserved_usd) < Decimal("0.01")
    assert row.pricing["reservation"]["max_output_tokens"] == 4096
    assert row.pricing["reservation"]["input_tokens"] < 3000
    assert client.get("/api/agents/2").json()["max_output_tokens"] == 4096
    assert client.patch("/api/agents/2", json={"max_output_tokens": 0}).status_code == 422
    assert client.patch("/api/agents/2", json={"max_output_tokens": 4096.5}).status_code == 422
    assert (
        client.patch(
            "/api/agents/2",
            json={
                "model_id": "claude-haiku-5-5",
                "provider": "anthropic",
                "max_output_tokens": 128001,
            },
        ).status_code
        == 422
    )


def test_reservation_scales_with_context_and_unknown_is_conservative():
    model = find_model("anthropic", "claude-haiku-5-5")
    small_input = budget.estimate_input_tokens(0, "hello", "system")
    large_input = budget.estimate_input_tokens(40_000, "hello", "system")
    small = budget.reservation_quote(model, 4096, small_input)
    large = budget.reservation_quote(model, 4096, large_input)
    unknown = budget.reservation_quote(model, 4096, None)
    assert small_input == 325
    assert large_input == small_input + 50_000
    assert (
        Decimal(small["reserved_usd"])
        < Decimal(large["reserved_usd"])
        < Decimal(unknown["reserved_usd"])
    )
    assert unknown["unknown_context"] and unknown["input_tokens"] == model["context"]
    assert pi.current_context_tokens({"contextUsage": {"tokens": None}, "userMessages": 2}) is None
    assert pi.current_context_tokens({"assistantMessages": 0, "userMessages": 0}) == 0
    assert pi.current_context_tokens({"contextUsage": {"tokens": 1234}}) == 1234


@pytest.mark.parametrize(
    "provider,model_id,threshold,base_input,long_input,base_output,long_output",
    [
        ("anthropic", "claude-haiku-5-5", 100000, "0.20", "1.00", "0.50", "2.50"),
        ("openai", "gpt-6-luna", 272000, "0.25", "0.50", "0.50", "0.75"),
    ],
)
def test_reservation_price_tier_switches_only_above_threshold(
    provider, model_id, threshold, base_input, long_input, base_output, long_output
):
    model = find_model(provider, model_id)
    at = budget.reservation_quote(model, 4096, threshold)
    above = budget.reservation_quote(model, 4096, threshold + 1)
    assert (at["input_rate"], at["output_rate"]) == (base_input, base_output)
    assert (above["input_rate"], above["output_rate"]) == (long_input, long_output)


def test_near_full_context_starts_fresh_session_with_notice(
    client, db_engine, fake_pi, monkeypatch
):
    command = pi.runtime_command()
    monkeypatch.setattr(pi, "runtime_command", lambda: [*command, "--initial-context", "260000"])
    enable_pi(client, monthly_budget_usd="1")
    client.post("/api/channels/1/messages", json={"body": "@omar continue"})
    messages = client.get("/api/channels/1/messages").json()
    assert any(
        "Started a fresh session" in item["body"] and item["author_type"] == "system"
        for item in messages
    )
    assert any(item["body"] == "Hello from the fake (final)." for item in messages)
    row = ledger(db_engine)[0]
    assert row.state == "settled"
    assert row.pricing["reservation"]["input_tokens"] < 3000
    assert row.pricing["reservation"]["unknown_context"] is False


def test_guard_passes_enforced_output_cap_to_provider_stream():
    node = shutil.which("node")
    if not node or not (pi.RUNTIME_NODE / "node_modules").exists():
        pytest.skip("Install the pinned local Pi runtime to check the trusted preload")
    guard = json.dumps((pi.RUNTIME_NODE / "guard.mjs").as_uri())
    script = f"""
        import assert from 'node:assert/strict';
        import {{ withOutputLimit }} from {guard};
        let sent;
        const provider = (model, context, options) => {{ sent = options; return 'stream'; }};
        const stream = withOutputLimit(provider, 512);
        assert.equal(stream({{maxTokens: 128000}}, {{}}, {{maxTokens: 999999}}), 'stream');
        assert.equal(sent.maxTokens, 512);
        assert.equal(sent.maxRetries, 0);
        stream({{maxTokens: 100}}, {{}}, {{}});
        assert.equal(sent.maxTokens, 100);
        assert.throws(() => withOutputLimit(provider, 0));
        console.log('provider output cap enforced');
    """
    result = subprocess.run(
        [node, "--input-type=module", "-e", script],
        capture_output=True,
        text=True,
        timeout=20,
        creationflags=subprocess.CREATE_NO_WINDOW if os.name == "nt" else 0,
    )
    assert result.returncode == 0, result.stderr
    assert "provider output cap enforced" in result.stdout


def test_private_environment_and_relay_unknown_price(db_engine, monkeypatch, tmp_path):
    monkeypatch.setenv("OTHER_SECRET", "must-not-leak")
    monkeypatch.setenv("OPENAI_API_KEY", "host-key-must-not-leak")
    monkeypatch.setattr(settings, "deepseek_api_key", "test-deepseek")
    env = pi.private_environment(tmp_path, "deepseek", 512)
    assert env["DEEPSEEK_API_KEY"] == "test-deepseek"
    assert "OPENAI_API_KEY" not in env and "OTHER_SECRET" not in env
    assert env["PI_CODING_AGENT_DIR"] == str(tmp_path / "config")
    assert env["AGENTSLACK_MAX_OUTPUT_TOKENS"] == "512"
    with Session(db_engine) as session:
        agent = session.get(Agent, 2)
    with pytest.raises(budget.BudgetError, match="Unknown model price"):
        asyncio.run(budget.reserve(db_engine, agent, 1, find_model("relay", "unverified-model")))


def test_cleanup_terminates_descendants_holding_rpc_pipes(fake_pi, tmp_path):
    async def run():
        process = pi.PiProcess()
        await process.start(
            [*pi.runtime_command(), "--child"], tmp_path, pi.private_environment(tmp_path, "openai")
        )
        event = await asyncio.wait_for(process.events.get(), 2)
        assert event["type"] == "runtime.child"
        await asyncio.wait_for(process.close(), 2)
        assert process.process.returncode is not None
        assert process.process.stdout.at_eof()
        assert process.process.stderr.at_eof()

    asyncio.run(run())
