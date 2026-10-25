import asyncio

import pytest
from fastapi.testclient import TestClient
from sqlalchemy.pool import StaticPool
from sqlmodel import Session, SQLModel, create_engine, select

from app.db import get_session
from app.main import app
from app.models import Agent, Message, Organization
from app.realtime import manager
from app.routers.messages import original_status, pending, reply
from app.runtime import get_runtime
from app.runtime.registry import RUNTIMES
from app.runtime.stub import StubRuntime
from app.seed import seed


@pytest.fixture
def db_engine():
    engine = create_engine(
        "sqlite://", connect_args={"check_same_thread": False}, poolclass=StaticPool
    )
    SQLModel.metadata.create_all(engine)
    with Session(engine) as session:
        seed(session)
    yield engine
    engine.dispose()


@pytest.fixture
def client(monkeypatch, db_engine):

    def override():
        with Session(db_engine) as session:
            yield session

    app.dependency_overrides[get_session] = override
    monkeypatch.setattr("app.main.engine", db_engine)
    monkeypatch.setattr("app.main.create_all", lambda: SQLModel.metadata.create_all(db_engine))
    # Avoid running production startup against a developer's database.
    with TestClient(app) as test_client:
        yield test_client
    app.dependency_overrides.clear()
    manager.connections.clear()


def test_health_seed_and_idempotence(client):
    assert client.get("/api/health").json()["status"] == "ok"
    assert len(client.get("/api/agents").json()) == 6
    assert len(client.get("/api/channels").json()) == 4
    tasks = client.get("/api/tasks").json()
    assert len(tasks) == 6
    assert len({task["description"] for task in tasks}) == 6
    agents = {agent["id"]: agent for agent in client.get("/api/agents").json()}
    channels = {channel["id"]: channel for channel in client.get("/api/channels").json()}
    for task in tasks:
        role = agents[task["assignee_agent_id"]]["role"]
        expected_channel = role if role in {"frontend", "backend", "finance"} else "general"
        assert channels[task["channel_id"]]["name"] == expected_channel
    engine = create_engine("sqlite://", poolclass=StaticPool)
    SQLModel.metadata.create_all(engine)
    with Session(engine) as session:
        seed(session)
        seed(session)
        assert len(session.exec(select(Agent)).all()) == 6
        assert len(session.exec(select(Organization)).all()) == 1
    engine.dispose()


def test_agent_crud_and_validation(client):
    data = {
        "name": "Alex",
        "handle": "@alex",
        "role": "ops",
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
    assert client.post("/api/agents", json={**data, "role": "invalid"}).status_code == 422
    assert client.get("/api/agents/9999").status_code == 404


def test_channels_dm_and_pagination(client):
    created = client.post("/api/channels", json={"name": "project-alpha", "topic": "Launch"})
    assert created.status_code == 201
    cid = created.json()["id"]
    assert client.post("/api/channels", json={"name": "project-alpha"}).status_code == 409
    assert client.get(f"/api/channels/{cid}").json()["topic"] == "Launch"
    assert client.get("/api/channels/1").json()["member_ids"] == [1, 2, 3, 4, 5, 6]
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
        posted = client.post("/api/channels/3/messages", json={"body": "@bruno hi"})
        assert posted.status_code == 201
        events = [ws.receive_json() for _ in range(4)]
        assert [e["type"] for e in events] == [
            "message.created",
            "agent.updated",
            "message.created",
            "agent.updated",
        ]
        assert events[1]["data"]["status"] == "busy"
        assert events[2]["data"]["author_id"] == 2
        assert "stub reply" in events[2]["data"]["body"]
        assert events[3]["data"]["status"] == "online"


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
    before = len(client.get("/api/channels/3/messages").json())
    client.post("/api/channels/3/messages", json={"body": "@brunox should not ping Bruno"})
    assert len(client.get("/api/channels/3/messages").json()) == before + 1


def test_overlapping_replies_restore_original_status():
    engine = create_engine(
        "sqlite://", connect_args={"check_same_thread": False}, poolclass=StaticPool
    )
    SQLModel.metadata.create_all(engine)
    with Session(engine) as session:
        seed(session)
        message = Message(channel_id=1, body="@remy hello")
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
        assert len(replies) == 2
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

    assert client.post("/api/channels/3/messages", json={"body": "@bruno hi"}).status_code == 201
    response = client.get("/api/channels/3/messages").json()[-1]
    assert response["author_id"] == 2
    if runtime_name == "test-harness":
        assert response["body"] == "Custom harness reply from Bruno"
        assert "Unknown agent runtime" not in caplog.text
    else:
        assert "stub reply from Bruno" in response["body"]
        assert "Unknown agent runtime 'unknown-harness'; falling back to stub" in caplog.text
