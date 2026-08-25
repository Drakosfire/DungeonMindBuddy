"""Explicit application-state schema upgrade and head check. No migrate-on-boot."""

from __future__ import annotations

import argparse
import os
import sys
from pathlib import Path

from alembic import command
from alembic.config import Config
from alembic.runtime.migration import MigrationContext
from alembic.script import ScriptDirectory
from sqlalchemy import create_engine, text

from application_state.config import APPLICATION_STATE_DSN_ENV, load_runtime_dsn
from application_state.engine import sqlalchemy_url
from application_state.errors import ApplicationStateMigrationError, ApplicationStateUnavailableError

PACKAGE_DIR = Path(__file__).resolve().parent


def alembic_config() -> Config:
    cfg = Config(str(PACKAGE_DIR / "alembic.ini"))
    cfg.set_main_option("script_location", str(PACKAGE_DIR / "migrations"))
    return cfg


def _current_and_head(dsn: str) -> tuple[str | None, str | None]:
    cfg = alembic_config()
    script = ScriptDirectory.from_config(cfg)
    heads = script.get_heads()
    head = heads[0] if len(heads) == 1 else None
    if len(heads) != 1:
        raise ApplicationStateMigrationError(
            f"application-state Alembic must have exactly one head, got {heads!r}"
        )
    engine = create_engine(sqlalchemy_url(dsn))
    with engine.connect() as connection:
        connection.execute(text("CREATE SCHEMA IF NOT EXISTS application_state"))
        connection.commit()
        context = MigrationContext.configure(
            connection,
            opts={
                "version_table": "schema_migrations",
                "version_table_schema": "application_state",
            },
        )
        current = context.get_current_revision()
    return current, head


def upgrade_to_head(*, dsn: str | None = None) -> None:
    target = dsn or load_runtime_dsn()
    if dsn is not None:
        os.environ[APPLICATION_STATE_DSN_ENV] = dsn
        load_runtime_dsn()
    command.upgrade(alembic_config(), "head")
    current, head = _current_and_head(target)
    if current != head:
        raise ApplicationStateMigrationError(
            f"upgrade did not reach head: current={current!r} head={head!r}"
        )


def assert_at_head(*, dsn: str | None = None) -> None:
    target = dsn or load_runtime_dsn()
    current, head = _current_and_head(target)
    if current != head:
        raise ApplicationStateMigrationError(
            "application-state schema is behind Alembic head; "
            "run `python -m application_state.cli upgrade` (ordinary boot does not migrate)"
        )


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Buddy application-state schema CLI")
    parser.add_argument("command", choices=("upgrade", "check"))
    args = parser.parse_args(argv)
    try:
        if args.command == "upgrade":
            upgrade_to_head()
        else:
            assert_at_head()
    except (ApplicationStateUnavailableError, ApplicationStateMigrationError) as exc:
        print(str(exc), file=sys.stderr)
        return 2
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
