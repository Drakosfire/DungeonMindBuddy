"""Recovery must never create or accidentally drop a different database."""
import errno
import fcntl
import hashlib
import json
import os

import pytest
from evals.buddy_benchmark import disposable_database as owner


@pytest.fixture
def recovery(tmp_path, monkeypatch):
    template = {"host": "127.0.0.1", "port": 5432, "database": "app_template", "oid": "10", "system_identifier": "20"}
    clone = {**template, "database": "benchmark_run_" + "a" * 32, "oid": "11"}
    receipt = tmp_path / "owner.json"
    lock = tmp_path / "owner.lock"
    lock.touch()
    state = {"owner": "benchmark", "pid": 999999, "database": clone,
             "stage": "awaiting_review", "cleanup_complete": False,
             "runs": [{"workers_closed": True, "process_group": 999998}]}
    def save():
        raw = json.dumps(state).encode()
        receipt.write_bytes(raw)
        return {"ledger": str(receipt), "ledger_sha256": hashlib.sha256(raw).hexdigest(),
                "lock": str(lock), "lock_device": lock.stat().st_dev, "lock_inode": lock.stat().st_ino,
                "owner": "benchmark", "clone": dict(clone)}
    control = {"ids": {template["database"]: ("10", "20"), clone["database"]: ("11", "20")},
               "sessions": 0, "statements": []}
    class Cursor:
        def __init__(self, result): self.result = result
        def fetchone(self): return self.result
    class Connection:
        def __enter__(self): return self
        def __exit__(self, *args): pass
        def execute(self, statement, params=None):
            control["statements"].append(str(statement))
            if "FROM pg_database WHERE datname" in str(statement):
                return Cursor(control["ids"].get(params[0]))
            if "pg_stat_activity" in str(statement): return Cursor((control["sessions"],))
            if "DROP DATABASE" in str(statement): control["ids"].pop(clone["database"], None)
            return Cursor(None)
    monkeypatch.setattr(owner.psycopg, "connect", lambda *a, **k: Connection())
    def absent(*args): raise ProcessLookupError(errno.ESRCH, "absent")
    monkeypatch.setattr(owner.os, "kill", absent)
    monkeypatch.setattr(owner.os, "killpg", absent)
    return template, clone, state, save, control, receipt, lock


def invoke(template, recovery):
    return owner.disposable_benchmark_database("host=127.0.0.1 port=5432 dbname=postgres", template, recovery=recovery)


def test_recovery_claims_and_drops_only_pinned_existing_clone(recovery):
    template, clone, state, save, control, receipt, lock = recovery
    with invoke(template, save()) as actual:
        assert actual == clone
        assert json.loads(receipt.read_text())["stage"] == "recovery_claimed"
        assert not any("CREATE DATABASE" in s for s in control["statements"])
        current = json.loads(receipt.read_text())
        current.update(pid=os.getpid(), stage="accept")
        receipt.write_text(json.dumps(current))
    assert clone["database"] not in control["ids"]
    assert template["database"] in control["ids"]
    assert sum("DROP DATABASE" in s for s in control["statements"]) == 1


@pytest.mark.parametrize("fault", ["bad_digest", "wrong_owner", "worker_open", "owner_live", "worker_live", "identity_changed", "sessions", "locked"])
def test_recovery_refuses_without_teardown(recovery, monkeypatch, fault):
    template, clone, state, save, control, receipt, lock = recovery
    if fault == "worker_open": state["runs"][0]["workers_closed"] = False
    pin = save()
    if fault == "bad_digest": pin["ledger_sha256"] = "0" * 64
    if fault == "wrong_owner": pin["owner"] = "someone else"
    if fault == "owner_live": monkeypatch.setattr(owner.os, "kill", lambda *a: None)
    if fault == "worker_live": monkeypatch.setattr(owner.os, "killpg", lambda *a: None)
    if fault == "identity_changed": control["ids"][clone["database"]] = ("12", "20")
    if fault == "sessions": control["sessions"] = 1
    held = open(lock, "r+") if fault == "locked" else None
    if held: fcntl.flock(held, fcntl.LOCK_EX | fcntl.LOCK_NB)
    try:
        with pytest.raises((ValueError, RuntimeError, BlockingIOError)):
            with invoke(template, pin): pytest.fail("unsafe adoption")
    finally:
        if held: held.close()
    assert not any("DROP DATABASE" in s or "CREATE DATABASE" in s for s in control["statements"])
    assert clone["database"] in control["ids"]


def test_changed_clone_is_not_dropped_on_exit(recovery):
    template, clone, state, save, control, receipt, lock = recovery
    with pytest.raises(RuntimeError, match="identity changed"):
        with invoke(template, save()):
            current = json.loads(receipt.read_text())
            current.update(pid=os.getpid(), stage="accept")
            receipt.write_text(json.dumps(current))
            control["ids"][clone["database"]] = ("12", "20")
    assert not any("DROP DATABASE" in s for s in control["statements"])


def test_exception_and_missing_acceptance_leave_clone(recovery):
    template, clone, state, save, control, receipt, lock = recovery
    with pytest.raises(KeyboardInterrupt):
        with invoke(template, save()):
            raise KeyboardInterrupt()
    assert clone["database"] in control["ids"]
    assert not any("DROP DATABASE" in s for s in control["statements"])
    with pytest.raises(RuntimeError, match="acceptance or abandonment"):
        with invoke(template, save()):
            pass
    assert clone["database"] in control["ids"]


def test_recovery_refuses_template_as_clone(recovery):
    template, clone, state, save, control, receipt, lock = recovery
    pin = save()
    pin["clone"] = {**template, "database": "benchmark_run_" + "b" * 32}
    bad_template = dict(template, database=pin["clone"]["database"])
    with pytest.raises(ValueError, match="recovery identity"):
        with invoke(bad_template, pin): pass
    assert not control["statements"]


def test_recovery_refuses_replaced_lock(recovery):
    template, clone, state, save, control, receipt, lock = recovery
    pin = save()
    with pytest.raises(ValueError, match="lock identity"):
        with invoke(template, pin):
            current = json.loads(receipt.read_text())
            current.update(pid=os.getpid(), stage="accept")
            receipt.write_text(json.dumps(current))
            lock.unlink()
            lock.touch()
    assert not any("DROP DATABASE" in s for s in control["statements"])


@pytest.mark.parametrize('fault', ['worker', 'sessions', 'missing_workers'])
def test_current_owner_must_close_workers_and_connections_before_drop(recovery, monkeypatch, fault):
    template, clone, state, save, control, receipt, lock = recovery
    with pytest.raises((ValueError, RuntimeError)):
        with invoke(template, save()):
            current = json.loads(receipt.read_text())
            current.update(pid=os.getpid(), stage='accept')
            if fault == 'worker': monkeypatch.setattr(owner.os, 'killpg', lambda *args: None)
            if fault == 'sessions': control['sessions'] = 1
            if fault == 'missing_workers': current['runs'][0]['workers_closed'] = False
            receipt.write_text(json.dumps(current))
    assert clone['database'] in control['ids']
    assert not any('DROP DATABASE' in s for s in control['statements'])


def test_duplicate_receipt_fields_and_symlinks_are_refused(recovery, tmp_path):
    template, clone, state, save, control, receipt, lock = recovery
    pin = save()
    raw = receipt.read_text().replace('"owner": "benchmark"', '"owner": "benchmark", "owner": "benchmark"')
    receipt.write_text(raw)
    pin['ledger_sha256'] = hashlib.sha256(raw.encode()).hexdigest()
    with pytest.raises(ValueError, match='Duplicate'):
        with invoke(template, pin): pass
    pin = save()
    link = tmp_path / 'receipt-link'
    link.symlink_to(receipt)
    pin['ledger'] = str(link)
    with pytest.raises(OSError):
        with invoke(template, pin): pass
    assert not any('DROP DATABASE' in s for s in control['statements'])
