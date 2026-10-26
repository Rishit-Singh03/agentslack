from sqlalchemy import event, inspect, text
from sqlmodel import Session, SQLModel, create_engine, select

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
            "default_provider": "VARCHAR NOT NULL DEFAULT 'openai'",
            "default_model_id": "VARCHAR NOT NULL DEFAULT 'gpt-6-luna'",
            "org_monthly_budget_usd": "VARCHAR NOT NULL DEFAULT '100'",
        },
        "message": {
            "is_streaming": "BOOLEAN NOT NULL DEFAULT 0",
            "model_id": "VARCHAR",
            "usage": "JSON",
            "cost_usd": "VARCHAR",
        },
        "agent": {
            "department_id": "INTEGER REFERENCES department(id)",
            "harness": "VARCHAR NOT NULL DEFAULT 'pi'",
            "provider": "VARCHAR NOT NULL DEFAULT 'openai'",
            "model_id": "VARCHAR NOT NULL DEFAULT 'gpt-6-luna'",
            "thinking_level": "VARCHAR NOT NULL DEFAULT 'off'",
            "max_output_tokens": "INTEGER NOT NULL DEFAULT 4096",
            "monthly_budget_usd": "VARCHAR NOT NULL DEFAULT '10'",
        },
    }
    with engine.begin() as connection:
        migrate_models = "harness" not in {
            column["name"] for column in inspect(connection).get_columns("agent")
        }
        for table, columns in additions.items():
            existing = {column["name"] for column in inspect(connection).get_columns(table)}
            for name, definition in columns.items():
                if name not in existing:
                    connection.execute(
                        text(f'ALTER TABLE "{table}" ADD COLUMN "{name}" {definition}')
                    )
        from .migrations import migrate_departments

        migrate_departments(connection)
        if migrate_models:
            from .model_catalog import preset
            from .models import Agent, Department, Organization

            with Session(bind=connection) as session:
                org = session.exec(select(Organization)).first() or Organization()
                for agent in session.exec(select(Agent)).all():
                    department = (
                        session.get(Department, agent.department_id)
                        if agent.department_id
                        else None
                    )
                    agent.provider, agent.model_id = preset(
                        department.slug if department else None, org
                    )
                    agent.runtime = "pi"
                    session.add(agent)
                session.flush()


def get_session():
    with Session(engine) as session:
        yield session
