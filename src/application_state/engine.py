"""psycopg connection factory for Buddy application state."""

from __future__ import annotations

import psycopg

from application_state.config import load_runtime_dsn
from application_state.errors import ApplicationStateUnavailableError


def sqlalchemy_url(dsn: str) -> str:
    if dsn.startswith("postgresql+psycopg://"):
        return dsn
    if dsn.startswith("postgresql://"):
        return "postgresql+psycopg://" + dsn[len("postgresql://") :]
    if dsn.startswith("postgres://"):
        return "postgresql+psycopg://" + dsn[len("postgres://") :]
    return dsn


def connect(dsn: str | None = None) -> psycopg.Connection:
    target = dsn if dsn is not None else load_runtime_dsn()
    try:
        return psycopg.connect(target, autocommit=False)
    except psycopg.Error as exc:
        raise ApplicationStateUnavailableError(
            f"application-state PostgreSQL is unavailable: {exc}"
        ) from exc
