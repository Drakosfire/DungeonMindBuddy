"""One physical App identity, fresh serial fixture states and fail-closed ownership."""
from dataclasses import replace
from hashlib import sha256
import json
import subprocess
import threading
from urllib.parse import urlsplit

import psycopg
import pytest

from application_state import cli
from application_state.errors import ApplicationStateMigrationError
from scripts import ci_app_database as database
from tests.application_state import database_fixture as owner


def fake_prepared(tmp_path):
    pin = {"host": "127.0.0.1", "port": 54329, "database": "benchmark_run_fixture",
           "oid": "123", "system_identifier": "456"}
    receipt = tmp_path / "owner.json"
    receipt.write_text(json.dumps({"owner": "test", "role": "per-run App", "database": pin,
                                   "cleanup_complete": False}))
    dsn = "postgresql://fixture:private-test-password@127.0.0.1:54329/benchmark_run_fixture"
    assignment = database.AppAssignment(dsn, database.replace_database(dsn, "postgres"), pin, receipt)
    snapshot = tmp_path / "snapshot.dump"
    snapshot.write_bytes(b"owned pristine fixture")
    return owner.PreparedTestDatabase(assignment, cli._alembic_head(), snapshot,
                                      sha256(snapshot.read_bytes()).hexdigest())


def test_fixture_reuses_its_real_owned_database_at_head(application_state_dsn,
                                                       application_state_database):
    prepared = application_state_database
    assert urlsplit(application_state_dsn).path == "/" + prepared.assignment.locator["database"]
    assert cli._read_current_revision(application_state_dsn) == prepared.revision == cli._alembic_head()


def test_serial_cases_keep_identity_but_reset_rows_and_schema(application_state_database):
    prepared = application_state_database
    with owner._case_database(prepared) as first:
        with psycopg.connect(first) as connection:
            connection.execute("CREATE SCHEMA fixture_probe")
            connection.execute("CREATE TABLE fixture_probe.marker(value text)")
            connection.execute("INSERT INTO fixture_probe.marker VALUES ('first state')")
    with owner._case_database(prepared) as second:
        assert first == second
        with psycopg.connect(second) as connection:
            assert connection.execute("SELECT to_regnamespace('fixture_probe')").fetchone() == (None,)
            assert connection.execute("SELECT count(*) FROM content.work_object").fetchone() == (0,)
    database.verify_assignment(prepared.assignment, idle=True)


def test_failed_body_resets_state_without_dropping_database(application_state_database):
    prepared = application_state_database
    with pytest.raises(RuntimeError, match="body failed"):
        with owner._case_database(prepared) as dsn:
            with psycopg.connect(dsn) as connection:
                connection.execute("CREATE SCHEMA failed_case")
            raise RuntimeError("body failed")
    with owner._case_database(prepared) as dsn:
        with psycopg.connect(dsn) as connection:
            assert connection.execute("SELECT to_regnamespace('failed_case')").fetchone() == (None,)
    database.verify_assignment(prepared.assignment, idle=True)


def test_nested_case_refuses_before_reset(tmp_path, monkeypatch):
    prepared = fake_prepared(tmp_path)
    prepared.active_thread = threading.get_ident()
    monkeypatch.setattr(owner, "_restore_prepared", lambda *a: pytest.fail("Nested reset"))
    with pytest.raises(RuntimeError, match="Concurrent or nested"):
        with owner._case_database(prepared):
            pytest.fail("Nested case admitted")


def test_snapshot_corruption_refuses_before_database_io(tmp_path, monkeypatch):
    prepared = replace(fake_prepared(tmp_path), snapshot_sha256="0" * 64)
    monkeypatch.setattr(database, "_CONNECT", lambda *a, **k: pytest.fail("Unbound database IO"))
    with pytest.raises(ValueError, match="snapshot changed"):
        with owner._case_database(prepared):
            pytest.fail("Corrupt snapshot admitted")


@pytest.mark.parametrize("fault", ["url", "admin", "name", "oid", "cluster", "role", "released"])
def test_changed_assignment_refuses_before_database_io(tmp_path, monkeypatch, fault):
    prepared = fake_prepared(tmp_path)
    assignment = prepared.assignment
    if fault == "url":
        assignment = replace(assignment, dsn=database.replace_database(assignment.dsn, "another_database"))
    elif fault == "admin":
        assignment = replace(assignment, admin_dsn=assignment.admin_dsn + "?application_name=changed")
    elif fault in {"name", "oid", "cluster"}:
        key = {"name": "database", "oid": "oid", "cluster": "system_identifier"}[fault]
        assignment = replace(assignment, locator=assignment.locator | {key: "foreign"})
    else:
        record = json.loads(assignment.receipt.read_text())
        record["role" if fault == "role" else "cleanup_complete"] = "read-only Core" if fault == "role" else True
        assignment.receipt.write_text(json.dumps(record))
    monkeypatch.setattr(database, "_CONNECT", lambda *a, **k: pytest.fail("Unbound database IO"))
    with pytest.raises(ValueError):
        database.verify_assignment(assignment)


def test_changed_installed_head_refuses_before_reset(tmp_path, monkeypatch):
    prepared = replace(fake_prepared(tmp_path), revision="different-installed-head")
    monkeypatch.setattr(owner, "_restore_prepared", lambda *a: pytest.fail("Stale source reset"))
    with pytest.raises(RuntimeError, match="installed schema head"):
        with owner._case_database(prepared):
            pytest.fail("Stale source admitted")


def test_local_ci_never_allocates_or_falls_back_without_owner(monkeypatch):
    monkeypatch.delenv(database.OWNER_ENV, raising=False)
    monkeypatch.delenv("GITHUB_ACTIONS", raising=False)
    monkeypatch.setattr(database, "_CONNECT", lambda *a, **k: pytest.fail("Operator database IO"))
    with pytest.raises(RuntimeError, match="never falls back"):
        with database.app_workstream():
            pytest.fail("Unassigned App admitted")


def test_pg_clients_clear_ambient_routing_and_keep_password_out_of_argv(tmp_path, monkeypatch):
    prepared = fake_prepared(tmp_path)
    seen = []
    monkeypatch.setattr(database, "verify_assignment", lambda *a, **k: None)
    monkeypatch.setenv("PGHOSTADDR", "192.0.2.1")
    monkeypatch.setenv("PGSERVICE", "operator")
    monkeypatch.setenv("PGPASSFILE", "/operator/passwords")
    monkeypatch.setenv("PGOPTIONS", "-c default_transaction_read_only=on")
    def run(argv, **kwargs):
        seen.append((argv, kwargs))
        return subprocess.CompletedProcess(argv, 0, b"", b"")
    monkeypatch.setattr(database, "_RUN", run)
    database.postgres_client("pg_dump", prepared.assignment, ["--format=custom"])
    argv, options = seen[0]
    assert "private-test-password" not in repr(argv)
    assert {key for key in options["env"] if key.startswith("PG")} == {
        "PGHOST", "PGPORT", "PGDATABASE", "PGUSER", "PGPASSWORD",
    }
    assert options["env"]["PGDATABASE"] == prepared.assignment.locator["database"]


def test_pg_client_failure_preserves_diagnostic_without_password(tmp_path, monkeypatch):
    prepared = fake_prepared(tmp_path)
    monkeypatch.setattr(database, "verify_assignment", lambda *a, **k: None)
    monkeypatch.setattr(database, "_RUN", lambda *a, **k: subprocess.CompletedProcess(
        a[0], 1, b"", b"SQL failure private-test-password"))
    with pytest.raises(RuntimeError, match="SQL failure") as error:
        database.postgres_client("pg_restore", prepared.assignment, [])
    assert "private-test-password" not in str(error.value)


def test_live_connection_refuses_fixture_reset(application_state_database, monkeypatch):
    prepared = application_state_database
    monkeypatch.setattr(owner, "clear_fixture_state", lambda *a: pytest.fail("Reset with live connection"))
    with psycopg.connect(prepared.dsn):
        with pytest.raises(RuntimeError, match="connections must close"):
            owner._restore_prepared(prepared)


def test_empty_phase_uses_same_database_and_restores_head(application_state_dsn,
                                                         application_state_database):
    prepared = application_state_database
    with owner.empty_app_state(prepared) as empty:
        assert empty == application_state_dsn
        with pytest.raises(ApplicationStateMigrationError):
            cli.assert_at_head(dsn=empty)
    cli.assert_at_head(dsn=application_state_dsn)


def test_empty_phase_requires_one_serial_case(tmp_path):
    prepared = fake_prepared(tmp_path)
    with pytest.raises(RuntimeError, match="one active serial"):
        with owner.empty_app_state(prepared):
            pytest.fail("Unowned empty state")


def test_migration_failure_closes_owned_engine(application_state_dsn,
                                              application_state_database, monkeypatch):
    from alembic.runtime.environment import EnvironmentContext
    prepared = application_state_database
    with owner.empty_app_state(prepared) as dsn:
        def fail(*args, **kwargs):
            raise RuntimeError("injected migration failure")
        with monkeypatch.context() as patch:
            patch.setattr(EnvironmentContext, "run_migrations", fail)
            with pytest.raises(RuntimeError, match="injected migration failure"):
                cli.upgrade_to_head(dsn=dsn)
        database.verify_assignment(prepared.assignment, idle=True)


def test_concurrent_case_refuses_before_reset_during_head_lookup(tmp_path, monkeypatch):
    prepared = fake_prepared(tmp_path)
    reached = threading.Event()
    release = threading.Event()
    resets = []
    failures = []
    def head():
        if threading.current_thread().name == "first-fixture-owner":
            reached.set()
            assert release.wait(3)
        return prepared.revision
    def enter():
        try:
            with owner._case_database(prepared):
                pass
        except BaseException as error:
            failures.append((threading.current_thread().name, error))
    monkeypatch.setattr(cli, "_alembic_head", head)
    monkeypatch.setattr(owner, "_restore_prepared", lambda *a: resets.append(threading.current_thread().name))
    first = threading.Thread(target=enter, name="first-fixture-owner")
    second = threading.Thread(target=enter, name="second-fixture-owner")
    first.start()
    try:
        assert reached.wait(2)
        second.start()
        second.join(2)
        assert not second.is_alive()
        assert not resets
        assert len(failures) == 1 and failures[0][0] == "second-fixture-owner"
        assert isinstance(failures[0][1], RuntimeError)
    finally:
        release.set()
        first.join(3)
        if second.ident is not None:
            second.join(3)
    assert not first.is_alive() and not second.is_alive()
    assert resets == ["first-fixture-owner", "first-fixture-owner"]


@pytest.mark.parametrize("outcome", ["accepted", "abandoned", "error", "interrupt", "drop-error", "closure-error"])
def test_managed_job_owns_one_clone_through_verified_teardown(tmp_path, monkeypatch, outcome):
    from contextlib import contextmanager
    from evals.buddy_benchmark import disposable_database
    events = []
    seed = {"host": "127.0.0.1", "port": 54329,
            "database": "dungeonbuddy_app_state_test_seed", "oid": "1", "system_identifier": "456"}
    clone = {**seed, "database": "benchmark_run_managed", "oid": "2"}
    monkeypatch.delenv(database.OWNER_ENV, raising=False)
    monkeypatch.setenv("GITHUB_ACTIONS", "true")
    monkeypatch.setenv(database.ADMIN_ENV, "postgresql://fixture@127.0.0.1:54329/postgres")
    monkeypatch.setenv(database.TEMPLATE_ENV, seed["database"])
    monkeypatch.setenv(database.ROOT_ENV, str(tmp_path))
    class Connection:
        def __enter__(self): return self
        def __exit__(self, *args): pass
        def execute(self, query, args=None):
            self.query, self.args = query, args
            return self
        def fetchone(self):
            if "WHERE datname" in self.query:
                if self.args[0] == seed["database"]:
                    return ("1", "456")
                return ("2", "456") if outcome == "drop-error" else None
            return ("456",)
    monkeypatch.setattr(database, "_CONNECT", lambda *args, **kwargs: Connection())
    @contextmanager
    def disposable(admin, pin):
        assert pin == seed
        events.append("allocate")
        try:
            yield clone
        finally:
            events.append("drop")
            if outcome == "drop-error":
                raise RuntimeError("exact clone teardown failed")
    monkeypatch.setattr(disposable_database, "disposable_benchmark_database", disposable)
    def verify(assignment, *, idle=False):
        assert assignment.locator == clone
        assert idle
        events.append("closed")
        if outcome == "closure-error":
            raise RuntimeError("connections remain")
    monkeypatch.setattr(database, "verify_assignment", verify)
    def run():
        with database.app_workstream(accepted=lambda: outcome == "accepted") as assignment:
            assert assignment.locator == clone
            with pytest.raises(RuntimeError, match="existing CI workstream receipt"):
                with database.app_workstream():
                    pytest.fail("Concurrent aggregate allocated another clone")
            events.append("body")
            if outcome == "interrupt":
                raise KeyboardInterrupt
            if outcome == "error":
                raise RuntimeError("worker failed")
    if outcome == "interrupt":
        with pytest.raises(KeyboardInterrupt):
            run()
    elif outcome in {"error", "drop-error", "closure-error"}:
        with pytest.raises(RuntimeError):
            run()
    else:
        run()
    receipt = json.loads((tmp_path / "app-owner.json").read_text())
    assert receipt["stage"] == ("job_accepted" if outcome == "accepted" else "job_abandoned")
    assert receipt["cleanup_complete"] is (outcome != "drop-error")
    assert events == ["allocate", "body", "closed", "drop"]


def test_managed_job_refuses_existing_receipt_before_database_io(tmp_path, monkeypatch):
    monkeypatch.delenv(database.OWNER_ENV, raising=False)
    monkeypatch.setenv("GITHUB_ACTIONS", "true")
    monkeypatch.setenv(database.ADMIN_ENV, "postgresql://fixture@127.0.0.1:54329/postgres")
    monkeypatch.setenv(database.TEMPLATE_ENV, "dungeonbuddy_app_state_test_seed")
    monkeypatch.setenv(database.ROOT_ENV, str(tmp_path))
    (tmp_path / "app-owner.json").write_text("{}")
    monkeypatch.setattr(database, "_CONNECT", lambda *a, **k: pytest.fail("Uninspected clone allocation"))
    with pytest.raises(RuntimeError, match="existing CI workstream receipt"):
        with database.app_workstream():
            pytest.fail("Replaced retained owner")
