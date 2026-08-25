"""Ephemeral Buddy application-state PostgreSQL for AS1 tests."""

from __future__ import annotations

import os
import uuid
from collections.abc import Iterator
from urllib.parse import urlparse, urlunparse

import pytest

from application_state.config import APPLICATION_STATE_DSN_ENV, TEST_ADMIN_DSN_ENV
from application_state.naming import assert_safe_application_state_database_name

_DEFAULT_ADMIN_DSN = "postgresql://dungeonmind:dungeonmind-dev@127.0.0.1:54329/postgres"


def _admin_dsn() -> str:
    return os.environ.get(TEST_ADMIN_DSN_ENV, "").strip() or _DEFAULT_ADMIN_DSN


def _replace_database(dsn: str, database: str) -> str:
    parsed = urlparse(dsn)
    return urlunparse(parsed._replace(path=f"/{database}"))


def _create_database(admin_dsn: str, name: str) -> None:
    import psycopg
    from psycopg import sql

    assert_safe_application_state_database_name(name)
    with psycopg.connect(admin_dsn, autocommit=True) as conn:
        conn.execute(sql.SQL("CREATE DATABASE {}").format(sql.Identifier(name)))


def _drop_database(admin_dsn: str, name: str) -> None:
    import psycopg
    from psycopg import sql

    with psycopg.connect(admin_dsn, autocommit=True) as conn:
        conn.execute(
            "SELECT pg_terminate_backend(pid) FROM pg_stat_activity WHERE datname = %s",
            (name,),
        )
        conn.execute(sql.SQL("DROP DATABASE IF EXISTS {}").format(sql.Identifier(name)))


@pytest.fixture
def application_state_dsn(monkeypatch: pytest.MonkeyPatch) -> Iterator[str]:
    admin = _admin_dsn()
    name = f"dungeonbuddy_app_state_test_{uuid.uuid4().hex[:12]}"
    try:
        _create_database(admin, name)
    except Exception as exc:
        pytest.skip(f"cannot create ephemeral application-state database: {exc}")
    dsn = _replace_database(admin, name)
    monkeypatch.setenv(APPLICATION_STATE_DSN_ENV, dsn)
    from application_state.cli import upgrade_to_head

    try:
        upgrade_to_head(dsn=dsn)
        yield dsn
    finally:
        monkeypatch.delenv(APPLICATION_STATE_DSN_ENV, raising=False)
        _drop_database(admin, name)
