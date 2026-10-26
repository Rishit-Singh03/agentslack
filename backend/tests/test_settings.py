import pytest
from sqlmodel import Session, select

from app.models import ChannelMember, MemoryEntry, Message, Task
from app.routers.messages import pending


def test_org_profile_settings_and_live_events(client):
    org = client.get("/api/org").json()
    assert org["theme"] == "dark" and org["crt_effects"] is False
    with client.websocket_connect("/ws") as socket:
        result = client.patch(
            "/api/org",
            json={
                "name": "Platform Team",
                "tagline": "Local tools",
                "accent": "#ffb000",
                "theme": "paper",
                "density": "comfortable",
                "font_mode": "mono",
                "crt_effects": True,
            },
        )
        assert result.status_code == 200
        assert result.json()["slug"] == "platform-team"
        event = socket.receive_json()
        assert event["type"] == "org.updated"
        assert event["data"]["accent"] == "#ffb000"
        assert (
            client.patch("/api/me", json={"display_name": "Sam", "handle": "@sam"}).status_code
            == 200
        )
        assert socket.receive_json()["type"] == "profile.updated"
    assert client.get("/api/me").json()["handle"] == "@sam"
    assert client.get("/api/org").json()["font_mode"] == "mono"
    for invalid in ({"accent": "red"}, {"theme": "light"}, {"density": "loose"}, {"name": " "}):
        assert client.patch("/api/org", json=invalid).status_code == 422
    assert client.patch("/api/me", json={"handle": "invalid"}).status_code == 422


@pytest.mark.parametrize("db_engine", [False], indirect=True)
@pytest.mark.parametrize("sample_team", [True, False])
def test_first_run_only_seeds_after_choice(client, sample_team):
    assert client.get("/api/org").json()["initialized"] is False
    assert client.get("/api/agents").json() == []
    assert client.get("/api/channels").json() == []
    data = {
        "name": "Terminal Lab",
        "display_name": "Sam",
        "handle": "@sam",
        "sample_team": sample_team,
    }
    assert client.post("/api/onboarding", json=data).status_code == 200
    assert client.get("/api/org").json()["slug"] == "terminal-lab"
    assert client.get("/api/org").json()["initialized"] is True
    assert client.get("/api/me").json()["display_name"] == "Sam"
    assert len(client.get("/api/agents").json()) == (8 if sample_team else 0)
    assert len(client.get("/api/tasks").json()) == (8 if sample_team else 0)
    assert len(client.get("/api/channels").json()) == 13
    assert client.post("/api/onboarding", json=data).status_code == 409


def test_channel_edit_delete_references_and_broadcasts(client, db_engine):
    created = client.post("/api/channels", json={"name": "web"}).json()
    channel_id = created["id"]
    with Session(db_engine) as session:
        session.get(Task, 1).channel_id = channel_id
        session.add(session.get(Task, 1))
        session.commit()
    with client.websocket_connect("/ws") as socket:
        response = client.patch(
            f"/api/channels/{channel_id}", json={"name": "web-updates", "topic": "Browser clients"}
        )
        assert response.status_code == 200
        assert socket.receive_json()["type"] == "channel.updated"
        assert client.delete(f"/api/channels/{channel_id}").status_code == 204
        assert socket.receive_json() == {"type": "channel.deleted", "data": {"id": channel_id}}
    assert client.get(f"/api/channels/{channel_id}").status_code == 404
    with Session(db_engine) as session:
        assert session.exec(select(Message).where(Message.channel_id == channel_id)).all() == []
        assert (
            session.exec(select(ChannelMember).where(ChannelMember.channel_id == channel_id)).all()
            == []
        )
        assert session.get(Task, 1).channel_id is None
    assert client.delete("/api/channels/1").status_code == 422
    assert client.patch("/api/channels/1", json={"name": "elsewhere"}).status_code == 422
    assert client.patch("/api/channels/7", json={"name": "announcements"}).status_code == 409
    assert client.patch("/api/channels/7", json={"topic": "a" * 501}).status_code == 422


def test_agent_edit_and_dismiss_cleanup(client, db_engine):
    dm = client.post("/api/dms/1").json()
    with Session(db_engine) as session:
        session.add(MemoryEntry(agent_id=1, kind="fact", content="Test memory"))
        session.commit()
    response = client.patch(
        "/api/agents/1",
        json={
            "name": "Faye",
            "title": "Web engineer",
            "department_id": 6,
            "bio": "Interface work",
            "skills": ["CSS"],
            "avatar_color": "#ffb000",
        },
    )
    assert response.status_code == 200
    assert response.json()["avatar_color"] == "#ffb000"
    assert client.get(f"/api/channels/{dm['id']}").json()["name"] == "Faye"
    assert client.delete("/api/agents/1").status_code == 204
    assert client.get("/api/agents/1").status_code == 404
    assert client.get(f"/api/channels/{dm['id']}").status_code == 404
    with Session(db_engine) as session:
        assert session.exec(select(Task).where(Task.assignee_agent_id == 1)).all() == []
        assert session.exec(select(MemoryEntry).where(MemoryEntry.agent_id == 1)).all() == []
        assert session.exec(select(Message).where(Message.author_id == 1)).all() == []
    assert any(
        message["author_type"] == "agent" and message["author_id"] is None
        for message in client.get("/api/channels/1/messages").json()
    )


def test_busy_agent_and_streaming_channel_cannot_be_deleted(client, db_engine):
    pending[2] = 1
    try:
        assert client.delete("/api/agents/2").status_code == 409
    finally:
        pending.clear()
    with Session(db_engine) as session:
        session.add(
            Message(channel_id=7, author_type="agent", author_id=2, body="", is_streaming=True)
        )
        session.commit()
    assert client.delete("/api/channels/7").status_code == 409


def test_runtime_failure_finishes_stream_and_restores_status(client, monkeypatch):
    class BrokenRuntime:
        async def stream(self, agent, message, context):
            yield "Partial response"
            raise RuntimeError("Harness failed")

    monkeypatch.setattr("app.routers.messages.get_runtime", lambda name: BrokenRuntime())
    response = client.post("/api/channels/7/messages", json={"body": "@omar test failure"})
    assert response.status_code == 201
    messages = client.get("/api/channels/7/messages").json()
    reply = messages[-2]
    assert reply["body"].startswith("Partial response")
    assert "Runtime failed" in messages[-1]["body"]
    assert reply["is_streaming"] is False
    assert client.get("/api/agents/2").json()["status"] == "online"


def test_level_up_posts_one_system_message(client):
    task = client.post(
        "/api/tasks",
        json={"title": "Level test", "assignee_agent_id": 1, "channel_id": 1, "xp_reward": 70},
    ).json()
    client.patch(f"/api/tasks/{task['id']}", json={"status": "done"})
    messages = client.get("/api/channels/1/messages").json()
    levels = [message for message in messages if message["body"].startswith("@alice level")]
    assert len(levels) == 1
    assert "3 → 4 (+70xp)" in levels[0]["body"]
    client.patch(f"/api/tasks/{task['id']}", json={"status": "todo"})
    client.patch(f"/api/tasks/{task['id']}", json={"status": "done"})
    assert (
        len(
            [
                message
                for message in client.get("/api/channels/1/messages").json()
                if message["body"].startswith("@alice level")
            ]
        )
        == 1
    )
