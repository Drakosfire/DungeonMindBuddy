"""Installed discovery can be reused; database schema authority cannot."""

from __future__ import annotations

import subprocess
import sys
from types import SimpleNamespace
from unittest.mock import Mock

import psycopg
import pytest

from application_state import cli
from application_state.errors import ApplicationStateMigrationError, ApplicationStateUnavailableError


@pytest.fixture(autouse=True)
def isolated_head_cache():
    cli._alembic_head.cache_clear()
    yield
    cli._alembic_head.cache_clear()


def discovery(monkeypatch, heads):
    reader = Mock(side_effect=heads)
    factory = Mock(return_value=SimpleNamespace(get_heads=reader))
    monkeypatch.setattr(cli.ScriptDirectory, "from_config", factory)
    return factory


def test_each_database_and_revision_is_checked_after_discovery(monkeypatch):
    factory = discovery(monkeypatch, [["installed"]])
    read = Mock(side_effect=["installed", "installed", "older", "newer", None,
                            ApplicationStateUnavailableError("offline"), "installed"])
    monkeypatch.setattr(cli, "_read_current_revision", read)
    cli.assert_at_head(dsn="first")
    cli.assert_at_head(dsn="second")
    for dsn in ("old", "new", "missing"):
        with pytest.raises(ApplicationStateMigrationError):
            cli.assert_at_head(dsn=dsn)
    with pytest.raises(ApplicationStateUnavailableError):
        cli.assert_at_head(dsn="offline")
    cli.assert_at_head(dsn="recovered")
    assert [call.args[0] for call in read.call_args_list] == [
        "first", "second", "old", "new", "missing", "offline", "recovered"
    ]
    assert factory.call_count == 1


@pytest.mark.parametrize("failure", [[], ["one", "two"], RuntimeError("malformed tree")])
def test_failed_installed_discovery_is_not_cached(monkeypatch, failure):
    factory = discovery(monkeypatch, [failure, ["installed"]])
    with pytest.raises((ApplicationStateMigrationError, RuntimeError)):
        cli._alembic_head()
    assert cli._alembic_head() == "installed"
    assert cli._alembic_head() == "installed"
    assert factory.call_count == 2


def test_upgrade_still_executes_and_verifies_actual_revision(monkeypatch):
    discovery(monkeypatch, [["installed"]])
    assert cli._alembic_head() == "installed"
    monkeypatch.setattr(cli, "load_runtime_dsn", lambda: "database")
    upgrade = Mock()
    monkeypatch.setattr(cli.command, "upgrade", upgrade)
    read = Mock(side_effect=["older", "installed"])
    monkeypatch.setattr(cli, "_read_current_revision", read)
    with pytest.raises(ApplicationStateMigrationError, match="did not reach head"):
        cli.upgrade_to_head()
    cli.upgrade_to_head()
    assert upgrade.call_count == 2
    assert read.call_count == 2


def test_new_process_discovers_its_own_installed_head(monkeypatch):
    real_head = cli._alembic_head()
    cli._alembic_head.cache_clear()
    discovery(monkeypatch, [["parent-only"]])
    assert cli._alembic_head() == "parent-only"
    child = subprocess.run(
        [sys.executable, "-B", "-c",
         "from application_state.cli import _alembic_head; print(_alembic_head())"],
        capture_output=True, text=True, check=True, timeout=30,
    )
    assert child.stdout.strip() == real_head
    assert cli._alembic_head() == "parent-only"


def test_actual_postgres_drift_is_refused(application_state_dsn):
    # The fixture owns and destroys this disposable database.
    head = cli._alembic_head()
    cli.assert_at_head(dsn=application_state_dsn)
    with psycopg.connect(application_state_dsn, autocommit=True) as conn:
        for revision in ("older", "newer"):
            conn.execute(
                "UPDATE application_state.schema_migrations SET version_num = %s",
                (revision,),
            )
            with pytest.raises(ApplicationStateMigrationError):
                cli.assert_at_head(dsn=application_state_dsn)
        conn.execute("DELETE FROM application_state.schema_migrations")
        with pytest.raises(ApplicationStateMigrationError):
            cli.assert_at_head(dsn=application_state_dsn)
        conn.execute(
            "INSERT INTO application_state.schema_migrations (version_num) VALUES (%s)",
            (head,),
        )
    cli.assert_at_head(dsn=application_state_dsn)
