from sqlalchemy import event, inspect, text
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
    # Phase 1 SQLite files predate settings and streaming. Add only missing columns.
    additions = {
        "organization": {
            "slug": "VARCHAR NOT NULL DEFAULT 'acme-agents'",
            "tagline": "VARCHAR NOT NULL DEFAULT ''",
            "accent": "VARCHAR NOT NULL DEFAULT '#3ddc84'",
            "theme": "VARCHAR NOT NULL DEFAULT 'dark'",
            "density": "VARCHAR NOT NULL DEFAULT 'compact'",
            "font_mode": "VARCHAR NOT NULL DEFAULT 'mixed'",
            "crt_effects": "BOOLEAN NOT NULL DEFAULT 0",
            "initialized": "BOOLEAN NOT NULL DEFAULT 1",
        },
        "message": {"is_streaming": "BOOLEAN NOT NULL DEFAULT 0"},
        "agent": {"department_id": "INTEGER REFERENCES department(id)"},
    }
    with engine.begin() as connection:
        for table, columns in additions.items():
            existing = {column["name"] for column in inspect(connection).get_columns(table)}
            for name, definition in columns.items():
                if name not in existing:
                    connection.execute(
                        text(f'ALTER TABLE "{table}" ADD COLUMN "{name}" {definition}')
                    )
        from .migrations import migrate_departments

        migrate_departments(connection)


def get_session():
    with Session(engine) as session:
        yield session
