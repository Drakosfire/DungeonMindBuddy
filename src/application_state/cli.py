"""Explicit application-state schema upgrade and head check. No migrate-on-boot."""

from __future__ import annotations

import argparse
import os
import sys
from functools import cache
from pathlib import Path

from alembic import command
from alembic.config import Config
from alembic.script import ScriptDirectory

from application_state.config import APPLICATION_STATE_DSN_ENV, load_runtime_dsn
from application_state.errors import ApplicationStateMigrationError, ApplicationStateUnavailableError

PACKAGE_DIR = Path(__file__).resolve().parent


def alembic_config() -> Config:
    cfg = Config(str(PACKAGE_DIR / "alembic.ini"))
    cfg.set_main_option("script_location", str(PACKAGE_DIR / "migrations"))
    return cfg


@cache
def _alembic_head() -> str:
    """Discover the immutable installed package head once per serving process.

    Delivery stops the process before replacing package files. Database revision
    reads and comparisons remain fresh; unsuccessful discovery is not cached.
    """
    cfg = alembic_config()
    script = ScriptDirectory.from_config(cfg)
    heads = script.get_heads()
    if len(heads) != 1:
        raise ApplicationStateMigrationError(
            f"application-state Alembic must have exactly one head, got {heads!r}"
        )
    return heads[0]


def _read_current_revision(dsn: str, *, periodic: bool = False) -> str | None:
    """Read Alembic current revision without creating schema, tables, or rows."""
    import psycopg

    limits = {"connect_timeout": 2, "options": "-c statement_timeout=1000"} if periodic else {}
    try:
        with psycopg.connect(dsn, autocommit=True, **limits) as conn:
            rows = conn.execute(
                "SELECT version_num FROM application_state.schema_migrations LIMIT 2"
            ).fetchall()
            if len(rows) > 1:
                raise ApplicationStateMigrationError(
                    "application-state migration table contains multiple revisions"
                )
            return str(rows[0][0]) if rows else None
    except psycopg.errors.UndefinedTable:
        return None
    except psycopg.Error as exc:
        raise ApplicationStateUnavailableError(
            f"application-state PostgreSQL is unavailable: {exc}"
        ) from exc


def _current_and_head(dsn: str) -> tuple[str | None, str]:
    return _read_current_revision(dsn), _alembic_head()


def upgrade_to_head(*, dsn: str | None = None) -> tuple[str, str]:
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
    return current, head


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
