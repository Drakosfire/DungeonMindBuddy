"""Own a local benchmark database from clone creation through teardown."""

from contextlib import contextmanager
from hashlib import sha256
from pathlib import Path
import errno
import fcntl
import json
import os
import re
import stat
import tempfile
from uuid import uuid4

import psycopg
from psycopg import sql
from psycopg.conninfo import conninfo_to_dict


def _identity(connection, database):
    return connection.execute("""
        SELECT oid::text, (SELECT system_identifier::text FROM pg_control_system())
        FROM pg_database WHERE datname = %s
    """, (database,)).fetchone()


@contextmanager
def disposable_benchmark_database(admin_dsn, template, *, recovery=None):
    """Own a newly cloned or explicitly recovered disposable database.

    The caller owns its workers and connections and must close them before
    leaving the context. The template is a pinned disposable evaluator fixture.
    New clones are dropped on exit. Recovery retains the clone on error and
    requires a current-owner acceptance or abandonment receipt before teardown.
    """
    endpoint = conninfo_to_dict(admin_dsn)
    if (endpoint.get("host") not in {"127.0.0.1", "::1"} or endpoint.get("hostaddr")
            or endpoint.get("service") or endpoint.get("dbname") != "postgres"
            or (endpoint["host"], endpoint.get("port")) != (template["host"], str(template["port"]))
            or template["database"] in {"postgres", "template0", "template1"}):
        raise ValueError("Benchmark clone requires the pinned local evaluator endpoint")

    if recovery is not None:
        with _recover_benchmark_database(admin_dsn, template, recovery) as clone:
            yield clone
        return

    name = "benchmark_run_" + uuid4().hex
    with psycopg.connect(admin_dsn, autocommit=True, connect_timeout=5) as connection:
        if _identity(connection, template["database"]) != (template["oid"], template["system_identifier"]):
            raise ValueError("Benchmark template identity differs from its pin")
        connection.execute(sql.SQL("CREATE DATABASE {} TEMPLATE {}").format(
            sql.Identifier(name), sql.Identifier(template["database"])
        ))
        identity = None
        failure = None
        try:
            identity = _identity(connection, name)
            if identity is None or identity[1] != template["system_identifier"]:
                raise RuntimeError(f"Could not verify created benchmark database {name}")
            yield {**template, "database": name, "oid": identity[0]}
        except BaseException as error:
            failure = error
            raise
        finally:
            try:
                if identity is None or identity[1] != template["system_identifier"]:
                    raise RuntimeError("Clone identity could not be pinned")
                with psycopg.connect(admin_dsn, autocommit=True, connect_timeout=5) as cleanup:
                    if _identity(cleanup, name) != identity:
                        raise RuntimeError("Clone identity changed before teardown")
                    cleanup.execute("SET lock_timeout = '5s'")
                    cleanup.execute(sql.SQL("DROP DATABASE {}").format(sql.Identifier(name)))
                    if _identity(cleanup, name) is not None:
                        raise RuntimeError("Clone is still present after teardown")
            except Exception as cleanup_error:
                detail = f"Benchmark database {name} teardown failed: {type(cleanup_error).__name__}"
                if failure is None:
                    raise RuntimeError(detail) from cleanup_error
                failure.add_note(detail)


def _process_absent(pid, *, group=False):
    if type(pid) is not int or pid <= 1:
        raise ValueError("Invalid retained process identity")
    try:
        (os.killpg if group else os.kill)(pid, 0)
    except OSError as exc:
        if exc.errno == errno.ESRCH:
            return
        raise RuntimeError("Cannot prove retained process is absent") from exc
    raise RuntimeError("Retained owner or worker is still present")


@contextmanager
def _recover_benchmark_database(admin_dsn, template, recovery):
    """Adopt an interrupted owner under its cooperative lock, then own teardown.

    The caller supplies the retained receipt and its independently pinned digest,
    exact owner and clone locator, and the original owner's existing lock file.
    This guard cannot coordinate owners that ignore that lock. The caller must
    keep this context open for all work and close all workers before exit.
    """
    if not isinstance(recovery, dict) or set(recovery) != {
        "ledger", "ledger_sha256", "lock", "lock_device", "lock_inode", "owner", "clone"
    }:
        raise ValueError("Recovery requires the exact owner receipt, digest, lock and clone")
    expected = recovery["clone"]
    if (not isinstance(expected, dict) or set(expected) != {"host", "port", "database", "oid", "system_identifier"}
            or expected["host"] != template["host"] or expected["port"] != template["port"]
            or expected["system_identifier"] != template["system_identifier"]
            or expected["database"] == template["database"] or expected["oid"] == template["oid"]
            or type(recovery["lock_device"]) is not int or type(recovery["lock_inode"]) is not int
            or not isinstance(expected["database"], str)
            or re.fullmatch(r"benchmark_run_[0-9a-f]{32}", expected["database"]) is None
            or not isinstance(expected["oid"], str) or not expected["oid"].isdigit()
            or not isinstance(recovery["owner"], str) or not recovery["owner"].strip()
            or not isinstance(recovery["ledger_sha256"], str)
            or re.fullmatch(r"[0-9a-f]{64}", recovery["ledger_sha256"]) is None):
        raise ValueError("Invalid pinned recovery identity")
    # Open the existing original lock without following a replacement symlink.
    fd = os.open(os.fspath(recovery["lock"]), os.O_RDWR | os.O_NOFOLLOW)
    try:
        def verify_lock():
            opened, current = os.fstat(fd), os.lstat(recovery["lock"])
            expected_lock = (recovery["lock_device"], recovery["lock_inode"])
            if (not stat.S_ISREG(opened.st_mode) or opened.st_uid != os.getuid() or opened.st_nlink != 1
                    or (opened.st_dev, opened.st_ino) != expected_lock
                    or (current.st_dev, current.st_ino) != expected_lock):
                raise ValueError("Original owner lock identity changed")
        fcntl.flock(fd, fcntl.LOCK_EX | fcntl.LOCK_NB)
        verify_lock()
        def read_receipt():
            receipt_fd = os.open(os.fspath(recovery["ledger"]), os.O_RDONLY | os.O_NOFOLLOW)
            with os.fdopen(receipt_fd, "rb") as stream:
                info = os.fstat(stream.fileno())
                if not stat.S_ISREG(info.st_mode) or info.st_uid != os.getuid() or info.st_nlink != 1:
                    raise ValueError("Invalid retained owner receipt")
                return stream.read()
        def object_without_duplicates(pairs):
            result = {}
            for key, value in pairs:
                if key in result:
                    raise ValueError("Duplicate receipt field")
                result[key] = value
            return result
        def parse_receipt(raw):
            return json.loads(raw, object_pairs_hook=object_without_duplicates)
        raw = read_receipt()
        if sha256(raw).hexdigest() != recovery["ledger_sha256"]:
            raise ValueError("Retained owner receipt differs from its pin")
        ledger = parse_receipt(raw)
        if (not isinstance(ledger, dict) or ledger.get("owner") != recovery["owner"]
                or ledger.get("database") != expected or ledger.get("cleanup_complete") is not False
                or ledger.get("stage") not in {"ready", "awaiting_review", "awaiting_retry", "paused"}):
            raise ValueError("Retained owner receipt is not recoverable")
        _process_absent(ledger.get("pid"))
        runs = ledger.get("runs")
        if not isinstance(runs, list):
            raise ValueError("Retained worker records are missing")
        for run in runs:
            if not isinstance(run, dict) or run.get("workers_closed") is not True:
                raise ValueError("A retained worker has not been closed")
            if run.get("process_group") is not None:
                _process_absent(run["process_group"], group=True)
        with psycopg.connect(admin_dsn, autocommit=True, connect_timeout=5) as connection:
            if _identity(connection, template["database"]) != (template["oid"], template["system_identifier"]):
                raise ValueError("Benchmark template identity differs from its pin")
            identity = (expected["oid"], expected["system_identifier"])
            if _identity(connection, expected["database"]) != identity:
                raise ValueError("Retained clone identity differs from its pin")
            sessions = connection.execute(
                "SELECT count(*) FROM pg_stat_activity WHERE datname = %s", (expected["database"],)
            ).fetchone()[0]
            if sessions:
                raise RuntimeError("Retained clone still has active connections")
        # Invalidate the old receipt before yielding. If this owner dies while
        # workers remain, its predecessor receipt must never authorize another
        # takeover. A new owner must maintain its own current worker ledger.
        ledger_path = Path(recovery["ledger"])
        claimed = {**ledger, "stage": "recovery_claimed", "recovery_pid": os.getpid()}
        temp_fd, temp_name = tempfile.mkstemp(prefix=".recovery-", dir=ledger_path.parent)
        try:
            with os.fdopen(temp_fd, "w", encoding="utf-8") as stream:
                json.dump(claimed, stream, sort_keys=True)
                stream.flush()
                os.fsync(stream.fileno())
            verify_lock()
            os.replace(temp_name, ledger_path)
            directory_fd = os.open(ledger_path.parent, os.O_RDONLY | os.O_DIRECTORY)
            try:
                os.fsync(directory_fd)
            finally:
                os.close(directory_fd)
        finally:
            if os.path.exists(temp_name):
                os.unlink(temp_name)
        try:
            yield dict(expected)
        except BaseException:
            # A failed or interrupted run retains its database for inspection.
            raise
        else:
            verify_lock()
            current = parse_receipt(read_receipt())
            if (not isinstance(current, dict) or current.get("owner") != recovery["owner"]
                    or current.get("database") != expected or current.get("pid") != os.getpid()
                    or current.get("cleanup_complete") is not False
                    or current.get("stage") not in {"accept", "abandon"}):
                raise RuntimeError("Explicit current-owner acceptance or abandonment is required; clone retained")
            runs = current.get("runs")
            if not isinstance(runs, list):
                raise RuntimeError("Current worker records are missing; clone retained")
            for run in runs:
                if not isinstance(run, dict) or run.get("workers_closed") is not True:
                    raise RuntimeError("Current worker remains open; clone retained")
                if run.get("process_group") is not None:
                    _process_absent(run["process_group"], group=True)
            with psycopg.connect(admin_dsn, autocommit=True, connect_timeout=5) as cleanup:
                if _identity(cleanup, expected["database"]) != identity:
                    raise RuntimeError("Clone identity changed before teardown")
                if cleanup.execute("SELECT count(*) FROM pg_stat_activity WHERE datname = %s",
                                   (expected["database"],)).fetchone()[0]:
                    raise RuntimeError("Clone still has active connections")
                verify_lock()
                cleanup.execute("SET lock_timeout = '5s'")
                cleanup.execute(sql.SQL("DROP DATABASE {}").format(sql.Identifier(expected["database"])))
                if _identity(cleanup, expected["database"]) is not None:
                    raise RuntimeError("Clone is still present after teardown")
    finally:
        os.close(fd)
