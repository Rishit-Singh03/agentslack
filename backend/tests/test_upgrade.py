from sqlmodel import Session, create_engine, select

from app import db
from app.models import Message, Organization


def test_phase1_sqlite_upgrade_preserves_data(tmp_path, monkeypatch):
    engine = create_engine(f"sqlite:///{tmp_path / 'phase1.db'}")
    with engine.begin() as connection:
        connection.exec_driver_sql(
            "CREATE TABLE organization (id INTEGER PRIMARY KEY, name VARCHAR)"
        )
        connection.exec_driver_sql("INSERT INTO organization VALUES (1, 'Acme Agents')")
        connection.exec_driver_sql(
            "CREATE TABLE message (id INTEGER PRIMARY KEY, channel_id INTEGER, "
            "author_type VARCHAR, author_id INTEGER, body VARCHAR, thread_parent_id INTEGER, "
            "created_at DATETIME)"
        )
        connection.exec_driver_sql(
            "INSERT INTO message VALUES (1, 1, 'human', NULL, 'Preserve this', NULL, "
            "'2026-10-25 12:00:00')"
        )
    monkeypatch.setattr(db, "engine", engine)
    db.create_all()
    db.create_all()
    with Session(engine) as session:
        org = session.exec(select(Organization)).one()
        assert org.name == "Acme Agents"
        assert org.initialized is True
        assert org.accent == "#3ddc84"
        message = session.get(Message, 1)
        assert message.body == "Preserve this"
        assert message.is_streaming is False
    engine.dispose()
