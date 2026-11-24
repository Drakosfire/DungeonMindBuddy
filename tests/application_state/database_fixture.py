"""Serial App fixture states inside one explicitly owned workstream database."""
from __future__ import annotations

from collections.abc import Iterator
from contextlib import contextmanager
from dataclasses import dataclass, field
import fcntl
import os
from pathlib import Path
import threading

import pytest

from application_state.config import APPLICATION_STATE_DSN_ENV
from scripts.ci_app_database import (
    AppAssignment, app_workstream, assignment_environment, clear_fixture_state, postgres_client,
    replace_database, snapshot_digest, verify_assignment, _CONNECT,
)


@dataclass
class PreparedTestDatabase:
    assignment: AppAssignment = field(repr=False)
    revision: str
    snapshot: Path
    snapshot_sha256: str
    case_lock: threading.Lock = field(default_factory=threading.Lock, repr=False, compare=False)
    active_thread: int | None = None
    empty_state_active: bool = False

    @property
    def dsn(self) -> str:
        return self.assignment.dsn


# URL manipulation remains available to existing connection/principal tests.
_replace_database = replace_database


def _admin_dsn() -> str:
    from scripts.ci_app_database import existing_assignment
    return existing_assignment().admin_dsn


def _revision(prepared: PreparedTestDatabase) -> list[str]:
    with _CONNECT(prepared.dsn, options="-c default_transaction_read_only=on",
                  hostaddr=str(prepared.assignment.locator["host"])) as connection:
        return [row[0] for row in connection.execute(
            "SELECT version_num FROM application_state.schema_migrations ORDER BY version_num"
        ).fetchall()]


def _restore_prepared(prepared: PreparedTestDatabase) -> None:
    # Reject damaged snapshots before any mutation; never repair one by migrations.
    if snapshot_digest(prepared.snapshot) != prepared.snapshot_sha256:
        raise ValueError("CI pristine snapshot changed")
    verify_assignment(prepared.assignment, idle=True)
    clear_fixture_state(prepared.assignment)
    postgres_client("pg_restore", prepared.assignment,
                    ["--exit-on-error", "--no-owner", "--no-privileges", str(prepared.snapshot)])
    if _revision(prepared) != [prepared.revision]:
        raise RuntimeError("CI snapshot belongs to another schema head")


@contextmanager
def _case_database(prepared: PreparedTestDatabase) -> Iterator[str]:
    from application_state import cli
    if not prepared.case_lock.acquire(blocking=False):
        raise RuntimeError("Concurrent or nested App fixture cases are not allowed")
    entered = False
    started = False
    try:
        if prepared.active_thread is not None:
            raise RuntimeError("Concurrent or nested App fixture cases are not allowed")
        if prepared.revision != cli._alembic_head():
            raise RuntimeError("CI prepared database belongs to another installed schema head")
        prepared.active_thread = threading.get_ident()
        started = True
        _restore_prepared(prepared)
        entered = True
        yield prepared.dsn
    finally:
        try:
            if entered:
                _restore_prepared(prepared)
        finally:
            if started:
                prepared.active_thread = None
            prepared.case_lock.release()


@contextmanager
def empty_app_state(prepared: PreparedTestDatabase) -> Iterator[str]:
    """A serial predecessor/restore phase in the same database, never a new clone."""
    if (not prepared.case_lock.locked()
            or prepared.active_thread != threading.get_ident() or prepared.empty_state_active):
        raise RuntimeError("Empty-state phases require one active serial fixture case")
    prepared.empty_state_active = True
    try:
        clear_fixture_state(prepared.assignment)
        yield prepared.dsn
    finally:
        try:
            _restore_prepared(prepared)
        finally:
            prepared.empty_state_active = False


@pytest.fixture(scope="session")
def application_state_database(tmp_path_factory, request) -> Iterator[PreparedTestDatabase]:
    from application_state import cli
    with app_workstream(accepted=lambda: request.session.testsfailed == 0) as assignment, assignment_environment(assignment):
        pin = assignment.locator
        lock_path = Path("/tmp") / (
            f"dungeonmind-app-fixture-{os.getuid()}-{pin['system_identifier']}-{pin['oid']}.lock"
        )
        with lock_path.open("a+") as lock:
            try:
                fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
            except BlockingIOError as error:
                raise RuntimeError("Another pytest session owns this App workstream") from error
            verify_assignment(assignment, idle=True)
            clear_fixture_state(assignment)
            with pytest.MonkeyPatch.context() as patch:
                patch.setenv(APPLICATION_STATE_DSN_ENV, assignment.dsn)
                cli.upgrade_to_head(dsn=assignment.dsn)
                cli.assert_at_head(dsn=assignment.dsn)
            directory = tmp_path_factory.mktemp("app-pristine")
            snapshot = directory / "pristine.dump"
            with snapshot.open("wb") as output:
                postgres_client("pg_dump", assignment, ["--format=custom", "--no-owner"], output=output)
            prepared = PreparedTestDatabase(assignment, cli._alembic_head(), snapshot, snapshot_digest(snapshot))
            yield prepared
            verify_assignment(assignment, idle=True)


@pytest.fixture
def application_state_dsn(monkeypatch: pytest.MonkeyPatch,
                          application_state_database: PreparedTestDatabase) -> Iterator[str]:
    with _case_database(application_state_database) as dsn:
        monkeypatch.setenv(APPLICATION_STATE_DSN_ENV, dsn)
        yield dsn
