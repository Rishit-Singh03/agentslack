import pytest
from fastapi.testclient import TestClient
from sqlalchemy.pool import StaticPool
from sqlmodel import Session, SQLModel, create_engine

from app.db import get_session
from app.main import app
from app.realtime import manager
from app.seed import seed


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
