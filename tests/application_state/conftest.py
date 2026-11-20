"""Ephemeral Buddy application-state PostgreSQL for AS1 tests."""

from __future__ import annotations

import os
import uuid
from collections.abc import Iterator
from contextlib import contextmanager
from dataclasses import dataclass, field
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


def _create_database(admin_dsn: str, name: str, *, template: str | None = None) -> None:
    import psycopg
    from psycopg import sql

    assert_safe_application_state_database_name(name)
    with psycopg.connect(admin_dsn, autocommit=True) as conn:
        statement = sql.SQL("CREATE DATABASE {}").format(sql.Identifier(name))
        if template is not None:
            assert_safe_application_state_database_name(template)
            statement += sql.SQL(" TEMPLATE {}").format(sql.Identifier(template))
        conn.execute(statement)


def _drop_database(admin_dsn: str, name: str) -> None:
    import psycopg
    from psycopg import sql

    with psycopg.connect(admin_dsn, autocommit=True) as conn:
        conn.execute(
            "SELECT pg_terminate_backend(pid) FROM pg_stat_activity WHERE datname = %s",
            (name,),
        )
        conn.execute(sql.SQL("DROP DATABASE IF EXISTS {}").format(sql.Identifier(name)))


@dataclass(frozen=True)
class MigratedTestTemplate:
    admin_dsn: str = field(repr=False)
    name: str
    revision: str


@contextmanager
def _migrated_test_template(admin: str) -> Iterator[MigratedTestTemplate]:
    """Migrate a new owned database once; never expose it as test work storage."""
    from application_state import cli

    name = f"dungeonbuddy_app_state_test_template_{uuid.uuid4().hex[:12]}"
    _create_database(admin, name)
    try:
        dsn = _replace_database(admin, name)
        # Session setup must not leave the shared seed bound in the process env.
        with pytest.MonkeyPatch.context() as patch:
            patch.setenv(APPLICATION_STATE_DSN_ENV, dsn)
            cli.upgrade_to_head(dsn=dsn)
            cli.assert_at_head(dsn=dsn)
        yield MigratedTestTemplate(admin, name, cli._alembic_head())
    finally:
        _drop_database(admin, name)


@contextmanager
def _cloned_test_database(template: MigratedTestTemplate) -> Iterator[str]:
    """A physical independent copy per test, with no schema replay or fallback."""
    from application_state import cli

    if _admin_dsn() != template.admin_dsn:
        raise RuntimeError("Disposable test server changed after template creation")
    if not template.name.startswith("dungeonbuddy_app_state_test_template_"):
        raise ValueError("Database clone requires its owned migrated test template")
    if template.revision != cli._alembic_head():
        raise RuntimeError("Test template belongs to another installed schema head")
    name = f"dungeonbuddy_app_state_test_{uuid.uuid4().hex[:12]}"
    _create_database(template.admin_dsn, name, template=template.name)
    try:
        dsn = _replace_database(template.admin_dsn, name)
        # Do not repair a stale/changed seed by replaying migrations per test.
        cli.assert_at_head(dsn=dsn)
        yield dsn
    finally:
        _drop_database(template.admin_dsn, name)


@pytest.fixture(scope="session")
def application_state_template() -> Iterator[MigratedTestTemplate]:
    with _migrated_test_template(_admin_dsn()) as template:
        yield template


@pytest.fixture
def application_state_dsn(
    monkeypatch: pytest.MonkeyPatch,
    application_state_template: MigratedTestTemplate,
) -> Iterator[str]:
    with _cloned_test_database(application_state_template) as dsn:
        monkeypatch.setenv(APPLICATION_STATE_DSN_ENV, dsn)
        try:
            yield dsn
        finally:
            monkeypatch.delenv(APPLICATION_STATE_DSN_ENV, raising=False)
