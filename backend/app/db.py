from sqlalchemy import event
from sqlmodel import Session, SQLModel, create_engine

from .config import settings

engine = create_engine(
    settings.database_url,
    connect_args={"check_same_thread": False} if settings.database_url.startswith("sqlite") else {},
)

if settings.database_url.startswith("sqlite"):

    @event.listens_for(engine, "connect")
    def enable_foreign_keys(connection, _):
        connection.execute("PRAGMA foreign_keys=ON")


def create_all():
    SQLModel.metadata.create_all(engine)


def get_session():
    with Session(engine) as session:
        yield session
