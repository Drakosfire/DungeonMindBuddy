"""Ephemeral Buddy application-state PostgreSQL for AS1 tests."""

from __future__ import annotations

import os
import uuid
from collections.abc import Iterator
from contextlib import ExitStack, contextmanager
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
def _migrated_test_template(
    admin: str, *, revision: str | None = None
) -> Iterator[MigratedTestTemplate]:
    """Migrate a new owned database once; never expose it as test work storage."""
    from application_state import cli

    expected = _template_revision(revision)

    name = f"dungeonbuddy_app_state_test_template_{uuid.uuid4().hex[:12]}"
    _create_database(admin, name)
    try:
        dsn = _replace_database(admin, name)
        # Session setup must not leave the shared seed bound in the process env.
        with pytest.MonkeyPatch.context() as patch:
            patch.setenv(APPLICATION_STATE_DSN_ENV, dsn)
            if revision is None:
                cli.upgrade_to_head(dsn=dsn)
                cli.assert_at_head(dsn=dsn)
            else:
                from alembic import command

                command.upgrade(cli.alembic_config(), expected)
                if cli._read_current_revision(dsn) != expected:
                    raise RuntimeError(
                        "Historical template did not reach its exact revision"
                    )
        yield MigratedTestTemplate(admin, name, expected)
    finally:
        _drop_database(admin, name)


def _template_revision(revision: str | None) -> str:
    from alembic.script import ScriptDirectory
    from application_state import cli

    if revision is None:
        return cli._alembic_head()
    script = ScriptDirectory.from_config(cli.alembic_config()).get_revision(revision)
    if script is None or script.revision != revision:
        raise ValueError("Historical templates require an exact installed revision")
    return revision


@contextmanager
def _cloned_test_database(
    template: MigratedTestTemplate, *, revision: str | None = None
) -> Iterator[str]:
    """A physical independent copy per test, with no schema replay or fallback."""
    from application_state import cli

    if _admin_dsn() != template.admin_dsn:
        raise RuntimeError("Disposable test server changed after template creation")
    if not template.name.startswith("dungeonbuddy_app_state_test_template_"):
        raise ValueError("Database clone requires its owned migrated test template")
    if template.revision != _template_revision(revision):
        raise RuntimeError("Test template belongs to another installed schema head")
    name = f"dungeonbuddy_app_state_test_{uuid.uuid4().hex[:12]}"
    _create_database(template.admin_dsn, name, template=template.name)
    try:
        dsn = _replace_database(template.admin_dsn, name)
        # Do not repair a stale/changed seed by replaying migrations per test.
        if revision is None:
            cli.assert_at_head(dsn=dsn)
        elif cli._read_current_revision(dsn) != template.revision:
            raise RuntimeError(
                "Historical clone differs from its pinned template revision"
            )
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


@pytest.fixture(scope="session")
def historical_templates():
    admin = _admin_dsn()
    with ExitStack() as stack:
        cache = {}

        def template(revision):
            # Resolve/validate before allocating anything, even on a cache hit.
            if _admin_dsn() != admin:
                raise RuntimeError("Historical test server changed during the session")
            if not isinstance(revision, str):
                raise ValueError(
                    "Historical templates require an exact installed revision"
                )
            _template_revision(revision)
            if revision not in cache:
                cache[revision] = stack.enter_context(
                    _migrated_test_template(admin, revision=revision)
                )
            return cache[revision]

        yield template


@pytest.fixture
def historical_database(historical_templates):
    @contextmanager
    def database(revision, *, source_dsn=None, expected_omissions=None):
        with _cloned_test_database(
            historical_templates(revision), revision=revision
        ) as dsn:
            if source_dsn is not None:
                from tests.application_state.historical_migrations import (
                    _project_owned_rows,
                )

                _project_owned_rows(
                    source_dsn, dsn, expected_omissions=expected_omissions or {}
                )
            with pytest.MonkeyPatch.context() as patch:
                patch.setenv(APPLICATION_STATE_DSN_ENV, dsn)
                yield dsn

    return database
