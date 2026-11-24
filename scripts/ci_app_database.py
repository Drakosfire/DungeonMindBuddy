"""One explicitly owned App database for serial CI fixture states.

Local callers borrow a pinned workstream owner. GitHub jobs may own one clone
from their disposable App seed for the complete aggregate command. No product
runtime imports this module and no fixture creates per-case databases.
"""
from __future__ import annotations

from collections.abc import Iterator, Callable
from contextlib import contextmanager
from dataclasses import dataclass, field
from hashlib import sha256
import json
from io import open as _OPEN
import os
from pathlib import Path
import subprocess
import sys
import time
from urllib.parse import urlsplit

import psycopg
from psycopg.conninfo import conninfo_to_dict
from psycopg import sql

OWNER_ENV = "DMB_CI_APP_OWNER_FILE"
DATABASE_ENV = "DMB_CI_APP_DATABASE_URL"
TEMPLATE_ENV = "DMB_CI_APP_TEMPLATE_DATABASE"
ADMIN_ENV = "DMB_APPLICATION_STATE_TEST_DATABASE_URL"
ROOT_ENV = "DMB_CI_WORKSTREAM_ROOT"
_CONNECT = psycopg.connect
_RUN = subprocess.run


@dataclass(frozen=True)
class AppAssignment:
    dsn: str = field(repr=False)
    admin_dsn: str = field(repr=False)
    locator: dict[str, str | int]
    receipt: Path


def replace_database(dsn: str, database: str) -> str:
    parsed = urlsplit(dsn)
    if parsed.scheme not in {"postgres", "postgresql"}:
        raise ValueError("CI requires an explicit PostgreSQL URL")
    return parsed._replace(path="/" + database).geturl()


def _endpoint(dsn: str) -> dict[str, str]:
    parts = conninfo_to_dict(dsn)
    if parts.get("host") not in {"127.0.0.1", "::1"} or parts.get("hostaddr") or parts.get("service"):
        raise ValueError("CI App ownership requires a directly pinned loopback endpoint")
    if not parts.get("port") or not parts.get("user"):
        raise ValueError("CI App ownership requires an explicit port and principal")
    return parts


def _identity(connection, name: str):
    return connection.execute(
        "SELECT oid::text,(SELECT system_identifier::text FROM pg_control_system()) "
        "FROM pg_database WHERE datname=%s", (name,),
    ).fetchone()


def verify_assignment(assignment: AppAssignment, *, idle: bool = False) -> None:
    pin = assignment.locator
    with _OPEN(assignment.receipt, encoding="utf-8") as stream:
        record = json.load(stream)
    if (record.get("database") != pin or record.get("cleanup_complete")
            or not record.get("owner")
            or not str(record.get("role", "")).startswith("per-run App")):
        raise ValueError("CI assignment differs from its active owner receipt")
    parts = _endpoint(assignment.dsn)
    if not str(pin["database"]).startswith("benchmark_run_"):
        raise ValueError("CI reset requires an explicitly owned workstream clone")
    if (parts["host"], parts["port"], parts.get("dbname")) != (
        pin["host"], str(pin["port"]), pin["database"],
    ):
        raise ValueError("CI database URL differs from its owner receipt")
    if assignment.admin_dsn != replace_database(assignment.dsn, "postgres"):
        raise ValueError("CI administrator differs from the bound App endpoint")
    with _CONNECT(assignment.admin_dsn, autocommit=True, hostaddr=str(pin["host"])) as connection:
        if _identity(connection, str(pin["database"])) != (str(pin["oid"]), str(pin["system_identifier"])):
            raise ValueError("CI App identity differs from its owner receipt")
        if idle:
            # A closed libpq socket can remain visible briefly while PostgreSQL
            # finishes its rollback. Wait only for natural closure; never cancel
            # or terminate a connection to make a reset succeed.
            deadline = time.monotonic() + 5
            while connection.execute(
                "SELECT count(*) FROM pg_stat_activity WHERE datname=%s", (pin["database"],),
            ).fetchone()[0]:
                if time.monotonic() >= deadline:
                    remaining = connection.execute(
                        "SELECT pid,backend_type,state,application_name FROM pg_stat_activity WHERE datname=%s",
                        (pin["database"],),
                    ).fetchall()
                    raise RuntimeError("CI App workers/connections must close before fixture reset; "
                                       f"remaining backend metadata: {remaining!r}")
                time.sleep(0.02)


def existing_assignment() -> AppAssignment:
    receipt = Path(os.environ[OWNER_ENV]).resolve()
    with _OPEN(receipt, encoding="utf-8") as stream:
        record = json.load(stream)
    if (not record.get("owner") or record.get("cleanup_complete")
            or not str(record.get("role", "")).startswith("per-run App")):
        raise ValueError("CI needs a current explicitly owned App workstream")
    pin = record["database"]
    dsn = os.environ[DATABASE_ENV]
    assignment = AppAssignment(dsn, replace_database(dsn, "postgres"), pin, receipt)
    verify_assignment(assignment)
    return assignment


def _write(path: Path, value: dict) -> None:
    temporary = path.with_suffix(".tmp")
    temporary.write_text(json.dumps(value, indent=2) + "\n")
    temporary.chmod(0o600)
    temporary.replace(path)


@contextmanager
def app_workstream(*, accepted: Callable[[], bool] | None = None) -> Iterator[AppAssignment]:
    """Borrow a retained local owner, or own one GitHub-job clone until completion."""
    if os.environ.get(OWNER_ENV):
        yield existing_assignment()
        return
    if os.environ.get("GITHUB_ACTIONS") != "true":
        raise RuntimeError("Assign a retained CI App owner; local CI never falls back to an operator database")
    admin = os.environ[ADMIN_ENV]
    parts = _endpoint(admin)
    if parts.get("dbname") != "postgres":
        raise ValueError("CI admin endpoint must name postgres")
    template = os.environ[TEMPLATE_ENV]
    if not template.startswith("dungeonbuddy_app_state_test_"):
        raise ValueError("GitHub CI requires its disposable job-owned App seed")
    work = Path(os.environ[ROOT_ENV]).resolve()
    work.mkdir(mode=0o700, parents=True, exist_ok=True)
    receipt = work / "app-owner.json"
    try:
        claim = receipt.open("x")
    except FileExistsError as error:
        raise RuntimeError("Inspect the existing CI workstream receipt before allocating another clone") from error
    with claim:
        receipt.chmod(0o600)
        json.dump({"owner": "CI aggregate job", "pid": os.getpid(),
                   "stage": "claiming", "cleanup_complete": False}, claim)
    # Exclusive durable claim precedes all clone allocation. An interrupted claim
    # remains visible and requires inspection rather than silent replacement.
    with _CONNECT(admin, autocommit=True, hostaddr=parts["host"]) as connection:
        identity = _identity(connection, template)
    if identity is None:
        raise ValueError("Declared App seed is missing")
    pin = {"host": parts["host"], "port": int(parts["port"]), "database": template,
           "oid": identity[0], "system_identifier": identity[1]}
    from evals.buddy_benchmark.disposable_database import disposable_benchmark_database
    record = {"owner": "CI aggregate job", "role": "per-run App", "pid": os.getpid(), "stage": "allocating", "cleanup_complete": False}
    _write(receipt, record)
    clone = None
    try:
        with disposable_benchmark_database(admin, pin) as owned:
            clone = owned
            assignment = AppAssignment(replace_database(admin, owned["database"]), admin, owned, receipt)
            record.update(database=owned, stage="running")
            _write(receipt, record)
            failure = None
            try:
                yield assignment
            except BaseException as error:
                failure = error
                record["stage"] = "job_abandoned"
                raise
            else:
                record["stage"] = "job_accepted" if accepted is None or accepted() else "job_abandoned"
            finally:
                try:
                    verify_assignment(assignment, idle=True)
                except Exception as cleanup:
                    record["stage"] = "job_abandoned"
                    record["connection_closure_error"] = type(cleanup).__name__
                    if failure is not None:
                        failure.add_note("CI App connection closure failed: " + type(cleanup).__name__)
                    else:
                        raise
                finally:
                    _write(receipt, record)
    finally:
        if clone is not None:
            primary = sys.exception()
            try:
                with _CONNECT(admin, autocommit=True, hostaddr=parts["host"]) as connection:
                    current = _identity(connection, str(clone["database"]))
                    cluster = connection.execute("SELECT system_identifier::text FROM pg_control_system()").fetchone()[0]
                record["cleanup_complete"] = current is None and cluster == clone["system_identifier"]
                _write(receipt, record)
                if not record["cleanup_complete"]:
                    raise RuntimeError("Exact CI clone remains; retain its receipt for cleanup")
            except Exception as cleanup:
                record.update(cleanup_complete=False, cleanup_error=type(cleanup).__name__)
                _write(receipt, record)
                if primary is not None:
                    primary.add_note("CI App teardown verification failed: " + type(cleanup).__name__)
                else:
                    raise


@contextmanager
def assignment_environment(assignment: AppAssignment) -> Iterator[None]:
    values = {OWNER_ENV: str(assignment.receipt), DATABASE_ENV: assignment.dsn,
              ADMIN_ENV: assignment.admin_dsn}
    previous = {key: os.environ.get(key) for key in values}
    os.environ.update(values)
    try:
        yield
    finally:
        for key, value in previous.items():
            if value is None:
                os.environ.pop(key, None)
            else:
                os.environ[key] = value


def clear_fixture_state(assignment: AppAssignment) -> None:
    """Empty only the exact owned database, after every other connection closes."""
    verify_assignment(assignment, idle=True)
    with _CONNECT(assignment.dsn, autocommit=True, hostaddr=str(assignment.locator["host"])) as connection:
        if _identity(connection, str(assignment.locator["database"])) != (
            str(assignment.locator["oid"]), str(assignment.locator["system_identifier"]),
        ):
            raise ValueError("Owned target changed before fixture reset")
        with connection.transaction():
            schemas = connection.execute(
                "SELECT nspname FROM pg_namespace WHERE nspname !~ '^pg_' "
                "AND nspname<>'information_schema' ORDER BY nspname"
            ).fetchall()
            for (schema,) in schemas:
                connection.execute(sql.SQL("DROP SCHEMA {} CASCADE").format(sql.Identifier(schema)))
            connection.execute("CREATE SCHEMA public")


def postgres_client(command: str, assignment: AppAssignment, arguments: list[str], *, output=None) -> None:
    """Run real pg clients with passwords only in their environment."""
    if command not in {"pg_dump", "pg_restore"}:
        raise ValueError("Unsupported CI PostgreSQL client")
    verify_assignment(assignment)
    parts = conninfo_to_dict(assignment.dsn)
    env = {key: value for key, value in os.environ.items() if not key.startswith("PG")}
    env.update({"PGHOST": parts["host"], "PGPORT": parts["port"],
                       "PGDATABASE": parts["dbname"], "PGUSER": parts["user"]})
    if parts.get("password"):
        env["PGPASSWORD"] = parts["password"]
    result = _RUN([command, "--dbname", parts["dbname"], *arguments], env=env, stdout=output or subprocess.PIPE,
                  stderr=subprocess.PIPE)
    if result.returncode:
        detail = result.stderr.decode(errors="replace")
        if parts.get("password"):
            detail = detail.replace(parts["password"], "[redacted]")
        raise RuntimeError(f"CI {command} failed with exit {result.returncode}: {detail}")


def snapshot_digest(path: Path) -> str:
    with _OPEN(path, "rb") as stream:
        return sha256(stream.read()).hexdigest()
