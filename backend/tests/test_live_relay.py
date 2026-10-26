import os
from decimal import Decimal

import pytest

from app.config import settings


@pytest.mark.live
@pytest.mark.skipif(
    os.environ.get("AGENTSLACK_LIVE") != "1",
    reason="Set AGENTSLACK_LIVE=1 to authorize paid relay checks",
)
@pytest.mark.parametrize(
    "provider,model_id", [("deepseek", "deepseek-flash"), ("openai", "gpt-6-luna")]
)
def test_real_pi_relay_short_reply(client, monkeypatch, tmp_path, provider, model_id):
    configured = bool(settings.relay_key and settings.relay_base_url)
    assert configured, "Relay configuration required"
    for key in ("openai_api_key", "deepseek_api_key", "anthropic_api_key"):
        monkeypatch.setattr(settings, key, None)
    monkeypatch.setattr(settings, "runtime_data_dir", str(tmp_path / "live-runtime"))
    assert (
        client.patch(
            "/api/agents/2",
            json={
                "harness": "pi",
                "provider": provider,
                "model_id": model_id,
                "thinking_level": "off",
                "max_output_tokens": 32,
                "monthly_budget_usd": "1",
            },
        ).status_code
        == 200
    )
    with client.websocket_connect("/ws") as socket:
        client.post(
            "/api/channels/1/messages", json={"body": "@omar Reply with exactly: relay connected"}
        )
        events = []
        while True:
            event = socket.receive_json()
            events.append(event)
            if event["type"] == "agent.updated" and event["data"]["status"] == "online":
                break
    deltas = [
        event for event in events if event["type"] == "message.delta" and event["data"]["delta"]
    ]
    assert deltas, "No streamed relay text; inspect the safe system message"
    response = client.get("/api/channels/1/messages").json()[-1]
    assert response["usage"]["totalTokens"] > 0
    assert Decimal(response["cost_usd"]) > 0
    spend = client.get("/api/agents/2/spend").json()
    assert spend["recent"][0]["state"] == "settled"
    print(
        f"LIVE {model_id}: streamed={len(deltas)} chunks, tokens={response['usage']['totalTokens']}, list_cost_usd={response['cost_usd']}, ledger=settled"
    )
