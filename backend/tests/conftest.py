import os

import pytest
from fastapi.testclient import TestClient
from sqlalchemy.pool import StaticPool
from sqlmodel import Session, SQLModel, create_engine, select

from app.config import settings
from app.db import get_session
from app.main import app
from app.models import Agent
from app.realtime import manager
from app.seed import seed


@pytest.fixture(autouse=True)
def offline_credentials(request, monkeypatch):
    if request.node.get_closest_marker("live") and os.environ.get("AGENTSLACK_LIVE") == "1":
        return

    def no_network(*args, **kwargs):
        raise OSError("Network disabled in unit tests")

    monkeypatch.setattr("app.relay.urllib.request.urlopen", no_network)
    for name in (
        "relay_key",
        "relay_base_url",
        "relay_reserve_url",
        "openai_api_key",
        "anthropic_api_key",
        "deepseek_api_key",
        "openrouter_api_key",
    ):
        monkeypatch.setattr(settings, name, None)


@pytest.fixture
def db_engine(request):
    engine = create_engine(
        "sqlite://", connect_args={"check_same_thread": False}, poolclass=StaticPool
    )
    SQLModel.metadata.create_all(engine)
    with engine.connect() as connection:
        connection.exec_driver_sql("PRAGMA foreign_keys=ON")
    if getattr(request, "param", True):
        with Session(engine) as session:
            seed(session)
            # Existing API behavior tests explicitly exercise the offline demo harness.
            for agent in session.exec(select(Agent)).all():
                agent.harness = "stub"
                agent.runtime = "stub"
                session.add(agent)
            session.commit()
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
    try:
        with TestClient(app) as test_client:
            yield test_client
    finally:
        app.dependency_overrides.clear()
        manager.connections.clear()
