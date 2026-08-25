"""Alembic environment for Buddy application state."""

from __future__ import annotations

from logging.config import fileConfig

from alembic import context
from sqlalchemy import create_engine, text

from application_state.config import load_runtime_dsn
from application_state.engine import sqlalchemy_url

config = context.config
if config.config_file_name is not None:
    fileConfig(config.config_file_name)

target_metadata = None


def run_migrations_offline() -> None:
    url = sqlalchemy_url(load_runtime_dsn())
    context.configure(
        url=url,
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
        version_table="schema_migrations",
        version_table_schema="application_state",
    )
    with context.begin_transaction():
        context.run_migrations()


def run_migrations_online() -> None:
    engine = create_engine(sqlalchemy_url(load_runtime_dsn()))
    with engine.connect() as connection:
        connection.execute(text("CREATE SCHEMA IF NOT EXISTS application_state"))
        connection.commit()
        context.configure(
            connection=connection,
            target_metadata=target_metadata,
            version_table="schema_migrations",
            version_table_schema="application_state",
        )
        with context.begin_transaction():
            context.run_migrations()


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
