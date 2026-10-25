import pytest
from sqlalchemy import inspect
from sqlmodel import Session, create_engine, select

from app import db
from app.models import Agent, Channel, ChannelMember, Department, Message, Task


def test_catalog_and_department_crud_broadcasts(client):
    catalog = client.get("/api/departments/catalog").json()
    assert len(catalog) == 13
    assert len([item for item in catalog if item["core"]]) == 8
    assert {item["name"] for item in catalog if item["core"]} == {
        "Leadership",
        "Operations",
        "Finance",
        "People (HR)",
        "Product",
        "Engineering",
        "Marketing",
        "Sales",
    }
    assert all(item["description"] for item in catalog)
    with client.websocket_connect("/ws") as socket:
        response = client.post(
            "/api/departments",
            json={
                "name": "Facilities",
                "description": "Offices and equipment",
                "color": "#56d4dd",
                "sort_order": 9,
            },
        )
        assert response.status_code == 201
        department = response.json()
        assert department["slug"] == "facilities"
        assert socket.receive_json()["type"] == "channel.updated"
        assert socket.receive_json()["type"] == "department.updated"
        response = client.patch(
            f"/api/departments/{department['id']}",
            json={"name": "Workplace", "color": "#ffb000", "sort_order": 0},
        )
        assert response.status_code == 200
        assert response.json()["slug"] == "workplace"
        assert socket.receive_json()["type"] == "department.updated"
        assert socket.receive_json()["data"]["name"] == "workplace"
    assert client.get(f"/api/channels/{department['channel_id']}").json()["name"] == "workplace"
    assert client.delete(f"/api/departments/{department['id']}").status_code == 204
    assert client.get(f"/api/channels/{department['channel_id']}").status_code == 404
    assert client.delete(f"/api/departments/{department['id']}").status_code == 404


@pytest.mark.parametrize("color", ["#8b5cf6", "#4f46e5", "#800080", "invalid"])
def test_department_color_validation(client, color):
    assert (
        client.post("/api/departments", json={"name": "Color test", "color": color}).status_code
        == 422
    )
    assert client.patch("/api/departments/1", json={"color": color}).status_code == 422


def test_conflicts_and_protected_channels(client):
    assert client.post("/api/departments", json={"name": "engineering"}).status_code == 409
    assert client.post("/api/departments", json={"name": "General"}).status_code == 409
    assert client.patch("/api/departments/1", json={"slug": "general"}).status_code == 409
    assert client.patch("/api/departments/1", json={"name": "Finance"}).status_code == 409
    assert client.patch("/api/departments/999", json={"name": "Other"}).status_code == 404
    assert client.delete("/api/channels/1").status_code == 422
    department = client.get("/api/departments").json()[0]
    assert client.delete(f"/api/channels/{department['channel_id']}").status_code == 409
    assert (
        client.patch(
            f"/api/channels/{department['channel_id']}", json={"name": "renamed"}
        ).status_code
        == 409
    )


def test_assignment_unassignment_and_department_delete(client, db_engine):
    departments = client.get("/api/departments").json()
    leadership, operations = departments[:2]
    attached_task = client.post(
        "/api/tasks",
        json={
            "title": "Department task",
            "assignee_agent_id": 2,
            "channel_id": operations["channel_id"],
        },
    ).json()
    assert (
        client.patch("/api/agents/1", json={"department_id": operations["id"]}).status_code == 200
    )
    with Session(db_engine) as session:
        assert session.get(ChannelMember, (leadership["channel_id"], 1)) is None
        assert session.get(ChannelMember, (operations["channel_id"], 1)) is not None
    cleared = client.patch("/api/agents/1", json={"department_id": None}).json()
    assert cleared["department_id"] is None and "role" not in cleared
    assert client.patch("/api/agents/1", json={"department_id": 999}).status_code == 404
    with client.websocket_connect("/ws") as socket:
        assert client.delete(f"/api/departments/{operations['id']}").status_code == 204
        events = [socket.receive_json() for _ in range(3)]
        assert [event["type"] for event in events] == [
            "agent.updated",
            "channel.deleted",
            "department.deleted",
        ]
        assert events[0]["data"]["department_id"] is None
    assert client.get("/api/agents/2").json()["department_id"] is None
    with Session(db_engine) as session:
        assert session.get(Channel, operations["channel_id"]) is None
        assert session.get(Agent, 2) is not None
        assert session.get(Task, 2) is not None
        assert session.get(Task, attached_task["id"]).channel_id is None
        assert (
            session.exec(
                select(ChannelMember).where(ChannelMember.channel_id == operations["channel_id"])
            ).all()
            == []
        )
    client.post("/api/channels/1/messages", json={"body": "@omar help"})
    assert "identify the next steps" in client.get("/api/channels/1/messages").json()[-1]["body"]


def test_stub_uses_current_department_and_free_text_title(client):
    assert (
        client.patch("/api/agents/6", json={"title": "Systems Reliability Partner"}).status_code
        == 200
    )
    client.post("/api/channels/1/messages", json={"body": "@evan help"})
    assert (
        "systems, implementation, and reliability"
        in client.get("/api/channels/1/messages").json()[-1]["body"]
    )
    assert client.patch("/api/departments/6", json={"name": "Platform"}).status_code == 200
    client.post("/api/channels/1/messages", json={"body": "@evan help again"})
    assert "Platform team" in client.get("/api/channels/1/messages").json()[-1]["body"]
    assert client.get("/api/agents/6").json()["title"] == "Systems Reliability Partner"


@pytest.mark.parametrize("db_engine", [False], indirect=True)
@pytest.mark.parametrize("sample_team", [False, True])
def test_onboarding_selected_and_custom_departments(client, sample_team):
    selected = [
        {
            "name": "Engineering",
            "color": "#70a7d8",
            "description": "Build systems",
            "sort_order": 0,
        },
        {
            "name": "Facilities",
            "color": "#ffb000",
            "description": "Manage offices",
            "sort_order": 1,
        },
    ]
    result = client.post(
        "/api/onboarding",
        json={
            "name": "Example",
            "display_name": "Sam",
            "handle": "@sam",
            "sample_team": sample_team,
            "departments": selected,
        },
    )
    assert result.status_code == 200
    departments = client.get("/api/departments").json()
    assert [department["name"] for department in departments] == ["Engineering", "Facilities"]
    assert {channel["name"] for channel in client.get("/api/channels").json()} == {
        "general",
        "announcements",
        "standup",
        "requests",
        "random",
        "engineering",
        "facilities",
    }
    agents = client.get("/api/agents").json()
    assert len(agents) == (1 if sample_team else 0)
    assert len(client.get("/api/tasks").json()) == (1 if sample_team else 0)
    if sample_team:
        assert agents[0]["title"] == "Software Engineer"
        assert agents[0]["department_id"] == departments[0]["id"]


@pytest.mark.parametrize("db_engine", [False], indirect=True)
def test_onboarding_without_departments(client):
    result = client.post(
        "/api/onboarding",
        json={
            "name": "Solo",
            "display_name": "Sam",
            "handle": "@sam",
            "departments": [],
            "sample_team": False,
        },
    )
    assert result.status_code == 200
    assert client.get("/api/departments").json() == []
    assert len(client.get("/api/channels").json()) == 5


def test_role_migration_preserves_agents_messages_tasks_and_members(tmp_path, monkeypatch):
    engine = create_engine(f"sqlite:///{tmp_path / 'legacy.db'}")
    with engine.begin() as connection:
        connection.exec_driver_sql("PRAGMA foreign_keys=ON")
        connection.exec_driver_sql(
            "CREATE TABLE organization (id INTEGER PRIMARY KEY, name VARCHAR)"
        )
        connection.exec_driver_sql("INSERT INTO organization VALUES (1, 'Legacy')")
        connection.exec_driver_sql(
            "CREATE TABLE agent (id INTEGER PRIMARY KEY, handle VARCHAR UNIQUE, name VARCHAR, "
            "role VARCHAR NOT NULL, title VARCHAR, avatar_color VARCHAR, status VARCHAR, level INTEGER, "
            "xp INTEGER, skills JSON, bio VARCHAR, runtime VARCHAR, created_at DATETIME)"
        )
        for index, role in enumerate(
            ["frontend", "backend", "design", "research", "ops", "finance"], 1
        ):
            connection.exec_driver_sql(
                "INSERT INTO agent VALUES (?, ?, ?, ?, 'Specialist', '#3ddc84', 'online', 1, 0, "
                "'[]', '', 'stub', '2026-10-25 12:00:00')",
                (index, f"@agent{index}", f"Agent {index}", role),
            )
    # Create the remaining legacy-compatible tables before adding a history to move.
    from sqlmodel import SQLModel

    SQLModel.metadata.create_all(engine)
    with Session(engine) as session:
        channel = Channel(name="frontend", topic="Existing work")
        session.add(channel)
        session.flush()
        session.add(ChannelMember(channel_id=channel.id, agent_id=1))
        session.add(
            Message(
                channel_id=channel.id, author_type="agent", author_id=1, body="Keep this history"
            )
        )
        session.add(Task(title="Keep this task", assignee_agent_id=1, channel_id=channel.id))
        session.commit()
    monkeypatch.setattr(db, "engine", engine)
    db.create_all()
    db.create_all()
    assert "role" not in {column["name"] for column in inspect(engine).get_columns("agent")}
    with Session(engine) as session:
        departments = {item.slug: item for item in session.exec(select(Department)).all()}
        assert set(departments) == {"engineering", "design", "research", "operations", "finance"}
        assert (
            session.get(Agent, 1).department_id
            == session.get(Agent, 2).department_id
            == departments["engineering"].id
        )
        assert session.get(Agent, 3).department_id == departments["design"].id
        assert session.get(Agent, 4).department_id == departments["research"].id
        assert session.get(Agent, 5).department_id == departments["operations"].id
        assert session.get(Agent, 6).department_id == departments["finance"].id
        channel_id = departments["engineering"].channel_id
        assert session.exec(select(Message)).one().channel_id == channel_id
        assert session.exec(select(Task)).one().channel_id == channel_id
        assert session.get(ChannelMember, (channel_id, 1)) is not None
        assert session.exec(select(Channel).where(Channel.name == "frontend")).first() is None
        assert len(session.exec(select(Agent)).all()) == 6
    engine.dispose()
