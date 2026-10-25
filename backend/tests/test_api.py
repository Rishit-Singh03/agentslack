import asyncio

import pytest
from sqlalchemy.pool import StaticPool
from sqlmodel import Session, SQLModel, create_engine, select

from app.models import Agent, Message, Organization
from app.routers.messages import original_status, pending, reply
from app.runtime import get_runtime
from app.runtime.registry import RUNTIMES
from app.runtime.stub import StubRuntime
from app.seed import seed


def test_health_seed_and_idempotence(client):
    assert client.get("/api/health").json()["status"] == "ok"
    assert len(client.get("/api/agents").json()) == 8
    assert len(client.get("/api/channels").json()) == 13
    tasks = client.get("/api/tasks").json()
    assert len(tasks) == 8
    assert len({task["description"] for task in tasks}) == 8
    agents = {agent["id"]: agent for agent in client.get("/api/agents").json()}
    channels = {channel["id"]: channel for channel in client.get("/api/channels").json()}
    departments = {item["id"]: item for item in client.get("/api/departments").json()}
    for task in tasks:
        department = departments[agents[task["assignee_agent_id"]]["department_id"]]
        assert channels[task["channel_id"]]["name"] in {department["slug"], "requests"}
    engine = create_engine("sqlite://", poolclass=StaticPool)
    SQLModel.metadata.create_all(engine)
    with Session(engine) as session:
        seed(session)
        seed(session)
        assert len(session.exec(select(Agent)).all()) == 8
        assert len(session.exec(select(Organization)).all()) == 1
    engine.dispose()


def test_agent_crud_and_validation(client):
    data = {
        "name": "Alex",
        "handle": "@alex",
        "department_id": 2,
        "title": "Coordinator",
        "skills": ["Planning"],
    }
    created = client.post("/api/agents", json=data)
    assert created.status_code == 201
    agent_id = created.json()["id"]
    assert client.get(f"/api/agents/{agent_id}").json()["level"] == 1
    assert (
        client.patch(f"/api/agents/{agent_id}", json={"status": "idle"}).json()["status"] == "idle"
    )
    assert client.get(f"/api/agents/{agent_id}/memory").json() == []
    assert client.post("/api/agents", json=data).status_code == 409
    assert (
        client.post(
            "/api/agents", json={**data, "handle": "@invalid", "department_id": 999}
        ).status_code
        == 404
    )
    assert client.get("/api/agents/9999").status_code == 404


def test_channels_dm_and_pagination(client):
    created = client.post("/api/channels", json={"name": "project-alpha", "topic": "Launch"})
    assert created.status_code == 201
    cid = created.json()["id"]
    assert client.post("/api/channels", json={"name": "project-alpha"}).status_code == 409
    assert client.get(f"/api/channels/{cid}").json()["topic"] == "Launch"
    assert client.get("/api/channels/1").json()["member_ids"] == [1, 2, 3, 4, 5, 6, 7, 8]
    dm = client.post("/api/dms/2").json()
    assert client.post("/api/dms/2").json()["id"] == dm["id"]
    client.post(f"/api/channels/{dm['id']}/messages", json={"body": "hello"})
    assert client.get(f"/api/channels/{dm['id']}/messages").json()[-1]["author_id"] == 2
    for body in ["one", "two", "three"]:
        assert client.post(f"/api/channels/{cid}/messages", json={"body": body}).status_code == 201
    page = client.get(f"/api/channels/{cid}/messages?limit=2").json()
    assert [m["body"] for m in page] == ["two", "three"]
    assert (
        client.get(f"/api/channels/{cid}/messages?before={page[0]['id']}").json()[0]["body"]
        == "one"
    )
    assert client.get(f"/api/channels/{cid}/messages?limit=201").status_code == 422
    assert client.post(f"/api/channels/{cid}/messages", json={"body": "   "}).status_code == 422
    assert client.post("/api/dms/999").status_code == 404


def test_live_mention_reply_and_status(client):
    with client.websocket_connect("/ws") as ws:
        posted = client.post("/api/channels/7/messages", json={"body": "@omar hi"})
        assert posted.status_code == 201
        events = []
        while True:
            event = ws.receive_json()
            events.append(event)
            if event["type"] == "agent.updated" and event["data"]["status"] == "online":
                break
        assert [event["type"] for event in events[:3]] == [
            "message.created",
            "agent.updated",
            "message.created",
        ]
        assert events[1]["data"]["status"] == "busy"
        assert events[2]["data"]["author_id"] == 2
        assert events[2]["data"]["is_streaming"] is True
        deltas = [event["data"] for event in events if event["type"] == "message.delta"]
        assert len(deltas) > 1
        final = events[-2]["data"]
        assert final["is_streaming"] is False
        assert final["id"] == events[2]["data"]["id"]
        assert all(delta["id"] == final["id"] and delta["channel_id"] == 7 for delta in deltas)
        assert "".join(delta["delta"] for delta in deltas) == final["body"]
        assert "stub reply" in final["body"]
        assert client.get("/api/channels/7/messages").json()[-1]["body"] == final["body"]


def test_task_completion_awards_xp_once_and_broadcasts(client):
    before = client.get("/api/agents/1").json()
    task = client.post(
        "/api/tasks",
        json={"title": "Ship it", "assignee_agent_id": 1, "channel_id": 1, "xp_reward": 70},
    ).json()
    with client.websocket_connect("/ws") as ws:
        assert client.patch(f"/api/tasks/{task['id']}", json={"status": "done"}).status_code == 200
        events = [ws.receive_json() for _ in range(3)]
        assert [e["type"] for e in events] == ["task.updated", "agent.updated", "message.created"]
    after = client.get("/api/agents/1").json()
    assert after["xp"] == before["xp"] + 70
    assert after["level"] == 1 + after["xp"] // 100
    client.patch(f"/api/tasks/{task['id']}", json={"status": "todo"})
    client.patch(f"/api/tasks/{task['id']}", json={"status": "done"})
    assert client.get("/api/agents/1").json()["xp"] == after["xp"]
    assert (
        client.post("/api/tasks", json={"title": "Oops", "assignee_agent_id": 999}).status_code
        == 404
    )
    assert client.patch(f"/api/tasks/{task['id']}", json={"status": "unknown"}).status_code == 422
    assert client.patch("/api/tasks/999", json={"status": "done"}).status_code == 404


def test_thread_validation_and_exact_mentions(client):
    parent = client.get("/api/channels/1/messages").json()[0]
    assert (
        client.post(
            "/api/channels/2/messages", json={"body": "reply", "thread_parent_id": parent["id"]}
        ).status_code
        == 422
    )
    before = len(client.get("/api/channels/7/messages").json())
    client.post("/api/channels/7/messages", json={"body": "@omarx should not ping Omar"})
    assert len(client.get("/api/channels/7/messages").json()) == before + 1


def test_overlapping_replies_restore_original_status():
    engine = create_engine(
        "sqlite://", connect_args={"check_same_thread": False}, poolclass=StaticPool
    )
    SQLModel.metadata.create_all(engine)
    with Session(engine) as session:
        seed(session)
        message = Message(channel_id=1, body="@leo hello")
        session.add(message)
        session.commit()
        session.refresh(message)
        message_id = message.id

    async def run():
        await asyncio.gather(reply(engine, [5], message_id), reply(engine, [5], message_id))

    asyncio.run(run())
    with Session(engine) as session:
        assert session.get(Agent, 5).status == "idle"
        replies = session.exec(select(Message).where(Message.author_id == 5)).all()
        assert len([message for message in replies if "stub reply" in message.body]) == 2
    assert not pending
    assert not original_status
    engine.dispose()


def test_runtime_registry_fallback(caplog):
    assert isinstance(get_runtime("stub"), StubRuntime)
    assert isinstance(get_runtime("unregistered-harness"), StubRuntime)
    assert "Unknown agent runtime 'unregistered-harness'; falling back to stub" in caplog.text


@pytest.mark.parametrize("runtime_name", ["test-harness", "unknown-harness"])
def test_messages_select_agent_runtime(client, db_engine, monkeypatch, caplog, runtime_name):
    class TestRuntime:
        async def respond(self, agent, message, context):
            assert message.id in {item.id for item in context}
            return f"Custom harness reply from {agent.name}"

    monkeypatch.setitem(RUNTIMES, "test-harness", TestRuntime)
    with Session(db_engine) as session:
        agent = session.get(Agent, 2)
        agent.runtime = runtime_name
        session.add(agent)
        session.commit()

    assert client.post("/api/channels/7/messages", json={"body": "@omar hi"}).status_code == 201
    response = client.get("/api/channels/7/messages").json()[-1]
    assert response["author_id"] == 2
    if runtime_name == "test-harness":
        assert response["body"] == "Custom harness reply from Omar"
        assert "Unknown agent runtime" not in caplog.text
    else:
        assert "stub reply from Omar" in response["body"]
        assert "Unknown agent runtime 'unknown-harness'; falling back to stub" in caplog.text
