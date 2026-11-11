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


def test_captured_source_name_reader_fence_refuses_predecessor(application_state_dsn, monkeypatch):
    from importlib import import_module
    fence = import_module('application_state.migrations.versions.20261110_0148_captured_source_names')
    assert fence.down_revision == '20261109_0147'
    cli.assert_at_head(dsn=application_state_dsn)
    with psycopg.connect(application_state_dsn, autocommit=True) as conn:
        actual = conn.execute('SELECT version_num FROM application_state.schema_migrations').fetchone()[0]
    assert actual == cli._alembic_head()
    # An old binary's installed-head discovery refuses the new database before
    # parsing any stored source/member records. No downgrade or row edits.
    with monkeypatch.context() as old_reader:
        old_reader.setattr(cli, '_alembic_head', lambda: fence.down_revision)
        with pytest.raises(ApplicationStateMigrationError):
            cli.assert_at_head(dsn=application_state_dsn)
    with pytest.raises(RuntimeError, match='forward recovery'):
        fence.downgrade()


def test_installed_migration_revision_ids_are_unique():
    """Inspect source before Alembic can collapse duplicate revision keys."""
    import ast

    owners = {}
    versions = cli.PACKAGE_DIR / "migrations" / "versions"
    for path in sorted(versions.glob("*.py")):
        tree = ast.parse(path.read_text(), filename=str(path))
        for node in tree.body:
            if isinstance(node, ast.Assign) and any(
                isinstance(target, ast.Name) and target.id == "revision"
                for target in node.targets
            ):
                revision = ast.literal_eval(node.value)
                assert revision not in owners, (
                    f"Duplicate migration {revision}: {owners.get(revision)} and {path.name}"
                )
                owners[revision] = path.name
    assert owners


def test_graph_migrations_follow_captured_source_reader_fence():
    script = cli.ScriptDirectory.from_config(cli.alembic_config())
    assert script.get_heads() == ["20261110_0152"]
    fence = script.get_revision("20261110_0148")
    assert fence.path.endswith("20261110_0148_captured_source_names.py")
    assert fence.down_revision == "20261109_0147"
    assert script.get_revision("20261110_0150").down_revision == fence.revision
    assert script.get_revision("20261110_0151").down_revision == "20261110_0150"
    assert script.get_revision("20261110_0152").down_revision == "20261110_0151"
    revisions = list(script.walk_revisions())
    assert len({row.revision for row in revisions}) == len(revisions)
    assert all(not isinstance(row.down_revision, tuple) for row in revisions)
    assert sum(row.down_revision is None for row in revisions) == 1
    # The unpublished prototype's explorer ID is not reused for another schema.
    assert "20261110_0149" not in {row.revision for row in revisions}


@pytest.mark.parametrize("start", ["20261109_0147", "20261110_0148"])
def test_graph_migrations_render_once_after_canonical_reader_fence(monkeypatch, start):
    from io import StringIO
    import sqlalchemy
    from application_state import config

    def no_database(*args, **kwargs):
        pytest.fail("Offline migration verification must not open a database")

    with monkeypatch.context() as patch:
        patch.setattr(psycopg, "connect", no_database)
        patch.setattr(sqlalchemy, "create_engine", no_database)
        patch.setattr(config, "load_runtime_dsn", lambda: (
            "postgresql://offline@127.0.0.1/dungeonbuddy_app_state_test_offline"
        ))
        output = StringIO()
        cfg = cli.alembic_config()
        cfg.output_buffer = output
        cli.command.upgrade(cfg, f"{start}:head", sql=True)
    sql = output.getvalue()
    for table in (
        "index_graph_sessions", "index_graph_bindings", "index_graph_operations",
        "index_graph_reservations", "native_graph_explorer_operations",
    ):
        assert sql.count(f"CREATE TABLE application_state.{table} (") == 1
    assert sql.index("CREATE TABLE application_state.index_graph_sessions") < sql.index(
        "CREATE TABLE application_state.native_graph_explorer_operations"
    )
    assert sql.index("20261110_0151") < sql.index("20261110_0152")
    assert "20261110_0149" not in sql
    if start == "20261109_0147":
        assert sql.index("20261110_0148") < sql.index("20261110_0150")


@pytest.mark.parametrize("prototype", ["20261110_0148", "20261110_0149", "20261110_0151"])
def test_current_graph_head_refuses_retained_prototype_revision(monkeypatch, prototype):
    # This is a serving-head check, not an upgrade or old-schema-shape guarantee.
    assert cli._alembic_head() == "20261110_0152"
    monkeypatch.setattr(cli, "_read_current_revision", lambda _: prototype)
    with pytest.raises(ApplicationStateMigrationError):
        cli.assert_at_head(dsn="retained-prototype-do-not-open")
