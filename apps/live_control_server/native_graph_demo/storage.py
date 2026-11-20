"""Small durable journal for the native graph demonstration.

DungeonMind remains the only semantic graph store.  This SQLite database keeps
only the demo's single-space binding and operation/recovery metadata so a lost
HTTP response can be reconciled with native publication receipts.
"""

from __future__ import annotations

import hashlib
import json
import sqlite3
import threading
from contextlib import contextmanager
from pathlib import Path
from typing import Any, Iterator


MAX_JOURNAL_OPERATIONS = 512


def canonical_json(value: object) -> str:
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"))


def sha256_text(value: str) -> str:
    return hashlib.sha256(value.encode("utf-8")).hexdigest()


class NativeGraphDemoStore:
    """Single-host SQLite journal with a process-shared lock per database path."""

    _locks_guard = threading.Lock()
    _locks: dict[str, threading.RLock] = {}

    def __init__(
        self, state_dir: str | Path, *, max_operations: int = MAX_JOURNAL_OPERATIONS
    ) -> None:
        directory = Path(state_dir).expanduser().resolve()
        directory.mkdir(parents=True, exist_ok=True)
        self.path = directory / "native_graph_demo.sqlite3"
        self.max_operations = max_operations
        key = str(self.path)
        with self._locks_guard:
            self._lock = self._locks.setdefault(key, threading.RLock())
        self._connection = sqlite3.connect(
            self.path,
            timeout=10.0,
            isolation_level=None,
            check_same_thread=False,
        )
        self._connection.row_factory = sqlite3.Row
        self._connection.execute("PRAGMA busy_timeout = 10000")
        self._connection.execute("PRAGMA journal_mode = WAL")
        self._connection.execute("PRAGMA synchronous = FULL")
        existing_table = self._connection.execute(
            "SELECT sql FROM sqlite_master WHERE type = 'table' AND name = 'demo_operations'"
        ).fetchone()
        if existing_table is not None:
            table_sql = str(existing_table["sql"] or "").lower()
            columns = {
                str(row["name"])
                for row in self._connection.execute(
                    "PRAGMA table_info(demo_operations)"
                ).fetchall()
            }
            if "'rejected'" not in table_sql or "rejected_json" not in columns:
                self._connection.close()
                raise RuntimeError("native graph demo journal schema is unsupported")
        self._connection.executescript(
            """
            CREATE TABLE IF NOT EXISTS demo_metadata (
                key TEXT PRIMARY KEY,
                value TEXT NOT NULL
            );
            CREATE TABLE IF NOT EXISTS demo_operations (
                operation_id TEXT PRIMARY KEY,
                request_json TEXT NOT NULL,
                request_sha256 TEXT NOT NULL,
                parent_revision_id TEXT NOT NULL,
                prepared_json TEXT NOT NULL,
                prepared_sha256 TEXT NOT NULL,
                status TEXT NOT NULL CHECK(status IN ('prepared', 'committed', 'unknown', 'rejected')),
                committed_json TEXT,
                rejected_json TEXT,
                updated_at TEXT NOT NULL
            );
            CREATE INDEX IF NOT EXISTS demo_operations_updated
                ON demo_operations(updated_at);
            CREATE TABLE IF NOT EXISTS demo_operation_reservations (
                operation_id TEXT PRIMARY KEY,
                request_json TEXT NOT NULL,
                request_sha256 TEXT NOT NULL,
                parent_revision_id TEXT NOT NULL,
                updated_at TEXT NOT NULL
            );
            """
        )
        self._transaction_depth = 0

    @contextmanager
    def atomic(self) -> Iterator[NativeGraphDemoStore]:
        """Serialize local callers and make each multi-step service action atomic."""
        with self._lock:
            outer = self._transaction_depth == 0
            if outer:
                self._connection.execute("BEGIN IMMEDIATE")
            self._transaction_depth += 1
            try:
                yield self
            except BaseException:
                self._transaction_depth -= 1
                if outer and self._connection.in_transaction:
                    self._connection.execute("ROLLBACK")
                raise
            else:
                self._transaction_depth -= 1
                if outer and self._connection.in_transaction:
                    self._connection.execute("COMMIT")

    def get_metadata(self, key: str) -> str | None:
        with self._lock:
            row = self._connection.execute(
                "SELECT value FROM demo_metadata WHERE key = ?", (key,)
            ).fetchone()
            return None if row is None else str(row["value"])

    def set_metadata(self, key: str, value: str) -> None:
        with self._lock:
            self._connection.execute(
                "INSERT INTO demo_metadata(key, value) VALUES(?, ?) "
                "ON CONFLICT(key) DO UPDATE SET value = excluded.value",
                (key, value),
            )

    def operation_count(self) -> int:
        with self._lock:
            row = self._connection.execute(
                "SELECT (SELECT COUNT(*) FROM demo_operations) + "
                "(SELECT COUNT(*) FROM demo_operation_reservations) AS count"
            ).fetchone()
            return int(row["count"])

    def get_reservation(self, operation_id: str) -> dict[str, Any] | None:
        with self._lock:
            row = self._connection.execute(
                "SELECT * FROM demo_operation_reservations WHERE operation_id = ?",
                (operation_id,),
            ).fetchone()
            if row is None:
                return None
            record = dict(row)
        request_json = str(record["request_json"])
        if sha256_text(request_json) != record["request_sha256"]:
            raise ValueError("operation reservation integrity check failed")
        record["request"] = json.loads(request_json)
        return record

    def reserve_operation(
        self,
        *,
        operation_id: str,
        request_json: str,
        parent_revision_id: str,
        updated_at: str,
    ) -> None:
        if self.operation_count() >= self.max_operations:
            raise OverflowError("demo operation journal is full")
        with self._lock:
            self._connection.execute(
                "INSERT INTO demo_operation_reservations(operation_id, request_json, request_sha256, parent_revision_id, updated_at) "
                "VALUES(?, ?, ?, ?, ?)",
                (
                    operation_id,
                    request_json,
                    sha256_text(request_json),
                    parent_revision_id,
                    updated_at,
                ),
            )

    def remove_reservation(self, operation_id: str) -> None:
        with self._lock:
            self._connection.execute(
                "DELETE FROM demo_operation_reservations WHERE operation_id = ?",
                (operation_id,),
            )

    def promote_reservation(
        self,
        operation_id: str,
        *,
        parent_revision_id: str,
        prepared_json: str,
        updated_at: str,
    ) -> None:
        reservation = self.get_reservation(operation_id)
        if reservation is None:
            raise ValueError("operation reservation is missing")
        self._connection.execute(
            "INSERT INTO demo_operations(operation_id, request_json, request_sha256, "
            "parent_revision_id, prepared_json, prepared_sha256, status, committed_json, rejected_json, updated_at) "
            "VALUES(?, ?, ?, ?, ?, ?, 'prepared', NULL, NULL, ?)",
            (
                operation_id,
                reservation["request_json"],
                reservation["request_sha256"],
                parent_revision_id,
                prepared_json,
                sha256_text(prepared_json),
                updated_at,
            ),
        )
        self.remove_reservation(operation_id)

    def reject_reservation(
        self,
        operation_id: str,
        *,
        code: str,
        error: str,
        updated_at: str,
    ) -> None:
        reservation = self.get_reservation(operation_id)
        if reservation is None:
            raise ValueError("operation reservation is missing")
        empty_prepared_json = "null"
        rejected_json = canonical_json({"code": code, "error": error})
        self._connection.execute(
            "INSERT INTO demo_operations(operation_id, request_json, request_sha256, "
            "parent_revision_id, prepared_json, prepared_sha256, status, committed_json, rejected_json, updated_at) "
            "VALUES(?, ?, ?, ?, ?, ?, 'rejected', NULL, ?, ?)",
            (
                operation_id,
                reservation["request_json"],
                reservation["request_sha256"],
                reservation["parent_revision_id"],
                empty_prepared_json,
                sha256_text(empty_prepared_json),
                rejected_json,
                updated_at,
            ),
        )
        self.remove_reservation(operation_id)

    @contextmanager
    def checkpoint(self) -> Iterator[None]:
        """Commit a reservation before an external native write, retaining the lock."""
        if self._transaction_depth != 1:
            raise RuntimeError("checkpoint requires the outermost service transaction")
        self._connection.execute("COMMIT")
        self._connection.execute("BEGIN IMMEDIATE")
        yield

    def get_operation(self, operation_id: str) -> dict[str, Any] | None:
        with self._lock:
            row = self._connection.execute(
                "SELECT * FROM demo_operations WHERE operation_id = ?",
                (operation_id,),
            ).fetchone()
            if row is None:
                return None
            record = dict(row)
        request_json = str(record["request_json"])
        prepared_json = str(record["prepared_json"])
        if sha256_text(request_json) != record["request_sha256"]:
            raise ValueError("operation request journal integrity check failed")
        if sha256_text(prepared_json) != record["prepared_sha256"]:
            raise ValueError("prepared operation journal integrity check failed")
        record["request"] = json.loads(request_json)
        record["prepared"] = json.loads(prepared_json)
        record["committed"] = (
            None
            if record["committed_json"] is None
            else json.loads(record["committed_json"])
        )
        record["rejected"] = (
            None
            if record["rejected_json"] is None
            else json.loads(record["rejected_json"])
        )
        return record

    def insert_prepared_operation(
        self,
        *,
        operation_id: str,
        request_json: str,
        parent_revision_id: str,
        prepared_json: str,
        updated_at: str,
        status: str = "prepared",
    ) -> None:
        if self.operation_count() >= self.max_operations:
            raise OverflowError("demo operation journal is full")
        with self._lock:
            self._connection.execute(
                "INSERT INTO demo_operations(operation_id, request_json, request_sha256, "
                "parent_revision_id, prepared_json, prepared_sha256, status, committed_json, rejected_json, updated_at) "
                "VALUES(?, ?, ?, ?, ?, ?, ?, NULL, NULL, ?)",
                (
                    operation_id,
                    request_json,
                    sha256_text(request_json),
                    parent_revision_id,
                    prepared_json,
                    sha256_text(prepared_json),
                    status,
                    updated_at,
                ),
            )

    def mark_operation_unknown(self, operation_id: str, *, updated_at: str) -> None:
        with self._lock:
            self._connection.execute(
                "UPDATE demo_operations SET status = 'unknown', rejected_json = NULL, updated_at = ? WHERE operation_id = ?",
                (updated_at, operation_id),
            )

    def mark_operation_committed(
        self, operation_id: str, *, committed_json: str, updated_at: str
    ) -> None:
        with self._lock:
            self._connection.execute(
                "UPDATE demo_operations SET status = 'committed', committed_json = ?, rejected_json = NULL, updated_at = ? "
                "WHERE operation_id = ?",
                (committed_json, updated_at, operation_id),
            )

    def mark_operation_rejected(
        self,
        operation_id: str,
        *,
        code: str,
        error: str,
        updated_at: str,
    ) -> None:
        rejected_json = canonical_json({"code": code, "error": error})
        with self._lock:
            self._connection.execute(
                "UPDATE demo_operations SET status = 'rejected', rejected_json = ?, committed_json = NULL, updated_at = ? "
                "WHERE operation_id = ?",
                (rejected_json, updated_at, operation_id),
            )

    def close(self) -> None:
        with self._lock:
            self._connection.close()
