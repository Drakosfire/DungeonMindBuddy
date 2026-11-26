"""Fixture for the derived HTTP witness inside a verified workstream App clone.

Never creates, resets, terminates, or drops a database. A separate reviewed
owner must hold the clone for the workstream and close it after acceptance or
abandonment. This fixture is not a substitute for a live-provider evaluation.
"""
from pathlib import Path
import json
import os
import subprocess

import pytest

OWNER = "RETRIEVAL negative-intent benchmark"
DERIVED_TEST = "tests/test_negative_retrieval_http_witness.py"


def _start_ticks(pid):
    fields = (Path("/proc") / str(pid) / "stat").read_text().split(") ", 1)[1].split()
    return fields[19]


def validate_lease(ledger, *, head, git_status, pgid, owner_start_ticks):
    """Fail closed on a stale owner, wrong source, worker or clone identity."""
    if (not isinstance(ledger, dict) or ledger.get("owner") != OWNER
            or ledger.get("cleanup_complete") is not False or ledger.get("stage") != "running"
            or ledger.get("source_sha") != head
            or type(ledger.get("pid")) is not int or ledger["pid"] <= 0
            or ledger.get("owner_start_ticks") != owner_start_ticks):
        raise ValueError("A live owner for this exact benchmark source is required")
    if git_status not in ("", f"?? {DERIVED_TEST}\n"):
        raise ValueError("Benchmark checkout has unexpected modifications")
    runs = ledger.get("runs")
    if not isinstance(runs, list) or not runs or not isinstance(runs[-1], dict):
        raise ValueError("The owned worker is not recorded")
    current = runs[-1]
    if (current.get("process_group") != pgid or current.get("workers_closed") is not False
            or current.get("exit_code") is not None or current.get("path") != ledger.get("current_run")):
        raise ValueError("The current process is not the active owned worker group")
    clone = ledger.get("database")
    if not isinstance(clone, dict):
        raise ValueError("Owned clone identity is unavailable")
    name = clone.get("database", "")
    suffix = name.removeprefix("benchmark_run_") if isinstance(name, str) else ""
    if (not isinstance(name, str) or not name.startswith("benchmark_run_") or len(suffix) != 32
            or any(c not in "0123456789abcdef" for c in suffix)
            or clone.get("host") not in {"127.0.0.1", "::1"}
            or type(clone.get("port")) is not int or not clone.get("oid")
            or not clone.get("system_identifier")):
        raise ValueError("A pinned disposable App clone is required")
    return clone


def checked_owned_dsn():
    """Return a verified owner-bound DSN without creating or modifying a database."""
    import psycopg
    from psycopg.conninfo import conninfo_to_dict
    from application_state.config import APPLICATION_STATE_DSN_ENV

    root = Path(__file__).resolve().parents[2]
    if Path.cwd().resolve() != root:
        raise ValueError("Owned App checks require the evaluator checkout as the working directory")
    ledger_path = Path(os.environ["DMB_NEGATIVE_RETRIEVAL_OWNER_LEDGER"]).resolve(strict=True)
    ledger = json.loads(ledger_path.read_text())
    head = subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=root, text=True).strip()
    status = subprocess.check_output(["git", "status", "--porcelain"], cwd=root, text=True)
    clone = validate_lease(ledger, head=head, git_status=status, pgid=os.getpgrp(),
                           owner_start_ticks=_start_ticks(ledger["pid"]))
    dsn = os.environ[APPLICATION_STATE_DSN_ENV]
    endpoint = conninfo_to_dict(dsn)
    if (endpoint.get("hostaddr") or endpoint.get("service")
            or (endpoint.get("host"), endpoint.get("port"), endpoint.get("dbname"))
            != (clone["host"], str(clone["port"]), clone["database"])):
        raise ValueError("App connection does not match the owned clone")
    with psycopg.connect(dsn, options="-c default_transaction_read_only=on") as connection:
        actual = connection.execute("""SELECT current_database(),
            (SELECT oid::text FROM pg_database WHERE datname=current_database()),
            (SELECT system_identifier::text FROM pg_control_system())""").fetchone()
    if actual != (clone["database"], str(clone["oid"]), str(clone["system_identifier"])):
        raise ValueError("Owned App clone identity changed")
    return dsn


@pytest.fixture
def application_state_dsn(monkeypatch):
    """Use the manager-owned App clone without invoking raw CREATE DATABASE."""
    from application_state.config import APPLICATION_STATE_DSN_ENV

    dsn = checked_owned_dsn()
    monkeypatch.setenv(APPLICATION_STATE_DSN_ENV, dsn)
    return dsn
