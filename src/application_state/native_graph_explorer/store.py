"""Bounded, principal- and managed-World-scoped publication journal.

DungeonMind owns graph records and publication receipts. APP-STATE stores only
the exact submitted intent, WK preparation and recovery state. A session-level
advisory lock survives transaction checkpoints before native dispatch.
"""

from __future__ import annotations

import hashlib
import json
import threading
from contextlib import contextmanager
from typing import Any, Iterator

import psycopg
from psycopg.rows import dict_row

from application_state.engine import connect
from application_state.errors import ApplicationStateUnavailableError


MAX_OPERATIONS = 512


def canonical_json(value: object) -> str:
    return json.dumps(
        value,
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
        allow_nan=False,
    )


def sha256_text(value: str) -> str:
    return hashlib.sha256(value.encode("utf-8")).hexdigest()


class NativeGraphExplorerStoreUnavailable(RuntimeError):
    """APP-STATE could not safely access the selected operation journal."""


class NativeGraphExplorerStore:
    """Synchronous operation journal for one authenticated World selection."""

    _locks_guard = threading.Lock()
    _locks: dict[tuple[str, str], threading.RLock] = {}

    def __init__(
        self,
        principal_subject: str,
        managed_world_id: str,
        *,
        max_operations: int = MAX_OPERATIONS,
    ) -> None:
        if not isinstance(principal_subject, str) or not principal_subject.strip():
            raise ValueError("principal subject is required")
        if not isinstance(managed_world_id, str) or not managed_world_id.strip():
            raise ValueError("managed World identity is required")
        self.principal_subject = principal_subject
        self.managed_world_id = managed_world_id
        self.max_operations = max_operations
        self._lock = self._process_lock(principal_subject, managed_world_id)
        try:
            self._connection = connect()
            self._connection.autocommit = True
            self._connection.row_factory = dict_row
        except (ApplicationStateUnavailableError, psycopg.Error) as exc:
            raise NativeGraphExplorerStoreUnavailable(
                "Buddy application state is unavailable."
            ) from exc
        self._transaction_depth = 0
        self._session_lock_held = False

    @classmethod
    def _process_lock(cls, subject: str, managed_world_id: str) -> threading.RLock:
        key = subject, managed_world_id
        with cls._locks_guard:
            return cls._locks.setdefault(key, threading.RLock())

    def _advisory_key(self) -> tuple[int, int]:
        payload = (self.principal_subject + "\0" + self.managed_world_id).encode(
            "utf-8"
        )
        value = int.from_bytes(hashlib.sha256(payload).digest()[:8], "big")
        high, low = (value >> 32) & 0xFFFFFFFF, value & 0xFFFFFFFF
        return (
            high - 0x100000000 if high >= 0x80000000 else high,
            low - 0x100000000 if low >= 0x80000000 else low,
        )

    @contextmanager
    def atomic(self) -> Iterator[NativeGraphExplorerStore]:
        """Serialize a principal/World pair across processes and checkpoints."""
        with self._lock:
            if self._transaction_depth:
                self._transaction_depth += 1
                try:
                    yield self
                finally:
                    self._transaction_depth -= 1
                return
            try:
                self._connection.execute(
                    "SELECT pg_advisory_lock(%s, %s)", self._advisory_key()
                )
                self._session_lock_held = True
                self._connection.execute("BEGIN")
            except (ApplicationStateUnavailableError, psycopg.Error) as exc:
                self._release_lock()
                raise NativeGraphExplorerStoreUnavailable(
                    "Buddy application state could not lock this graph operation."
                ) from exc
            self._transaction_depth = 1
            try:
                yield self
            except BaseException:
                self._transaction_depth = 0
                self._rollback()
                raise
            else:
                self._transaction_depth = 0
                try:
                    self._connection.execute("COMMIT")
                except psycopg.Error as exc:
                    raise NativeGraphExplorerStoreUnavailable(
                        "Buddy application state could not commit this graph operation."
                    ) from exc
            finally:
                self._release_lock()

    def checkpoint(self) -> None:
        """Commit a durable state transition without releasing the advisory lock."""
        if self._transaction_depth != 1 or not self._session_lock_held:
            raise RuntimeError("checkpoint requires the outermost locked transaction")
        try:
            self._connection.execute("COMMIT")
            self._connection.execute("BEGIN")
        except psycopg.Error as exc:
            raise NativeGraphExplorerStoreUnavailable(
                "Buddy application state could not checkpoint this graph operation."
            ) from exc

    def operation_count(self) -> int:
        row = self._execute(
            "SELECT count(*) AS count FROM application_state.native_graph_explorer_operations "
            "WHERE principal_subject = %s AND managed_world_id = %s",
            (self.principal_subject, self.managed_world_id),
        ).fetchone()
        return int(row["count"])

    def get_operation(self, operation_id: str) -> dict[str, Any] | None:
        row = self._execute(
            "SELECT * FROM application_state.native_graph_explorer_operations "
            "WHERE principal_subject = %s AND managed_world_id = %s AND operation_id = %s",
            (self.principal_subject, self.managed_world_id, operation_id),
        ).fetchone()
        if row is None:
            return None
        record = dict(row)
        request_json = str(record["request_json"])
        if sha256_text(request_json) != record["request_sha256"]:
            raise ValueError("operation request journal integrity check failed")
        record["request"] = json.loads(request_json)
        for field, json_field in (
            ("source_receipt", "source_receipt_json"),
            ("prepared", "prepared_json"),
            ("committed", "committed_json"),
            ("rejected", "rejected_json"),
        ):
            raw = record[json_field]
            if raw is None:
                record[field] = None
                continue
            raw = str(raw)
            digest_key = {
                "source_receipt": "source_receipt_sha256",
                "prepared": "prepared_sha256",
                "committed": "committed_sha256",
                "rejected": "rejected_sha256",
            }[field]
            if sha256_text(raw) != record[digest_key]:
                raise ValueError(f"{field} operation journal integrity check failed")
            record[field] = json.loads(raw)
        return record

    def reserve_operation(
        self,
        *,
        operation_id: str,
        native_world_id: str,
        binding_version: int,
        expected_revision_id: str,
        request_json: str,
        updated_at: str,
    ) -> None:
        if self.operation_count() >= self.max_operations:
            raise OverflowError("native graph operation journal is full")
        self._execute(
            "INSERT INTO application_state.native_graph_explorer_operations "
            "(principal_subject, managed_world_id, operation_id, native_world_id, binding_version, "
            "expected_revision_id, request_json, request_sha256, status, created_at, updated_at) "
            "VALUES (%s, %s, %s, %s, %s, %s, %s, %s, 'reserved', %s, %s)",
            (
                self.principal_subject,
                self.managed_world_id,
                operation_id,
                native_world_id,
                binding_version,
                expected_revision_id,
                request_json,
                sha256_text(request_json),
                updated_at,
                updated_at,
            ),
        )

    def mark_unknown(self, operation_id: str, *, updated_at: str) -> None:
        self._execute(
            "UPDATE application_state.native_graph_explorer_operations "
            "SET status = 'unknown', updated_at = %s "
            "WHERE principal_subject = %s AND managed_world_id = %s AND operation_id = %s",
            (updated_at, self.principal_subject, self.managed_world_id, operation_id),
        )

    def mark_prepared(
        self,
        operation_id: str,
        *,
        source_admission_id: str,
        source_receipt_json: str,
        parent_revision_id: str,
        prepared_json: str,
        updated_at: str,
    ) -> None:
        self._execute(
            "UPDATE application_state.native_graph_explorer_operations SET "
            "status = 'prepared', source_admission_id = %s, source_receipt_json = %s, "
            "source_receipt_sha256 = %s, parent_revision_id = %s, prepared_json = %s, "
            "prepared_sha256 = %s, rejected_json = NULL, rejected_sha256 = NULL, updated_at = %s "
            "WHERE principal_subject = %s AND managed_world_id = %s AND operation_id = %s",
            (
                source_admission_id,
                source_receipt_json,
                sha256_text(source_receipt_json),
                parent_revision_id,
                prepared_json,
                sha256_text(prepared_json),
                updated_at,
                self.principal_subject,
                self.managed_world_id,
                operation_id,
            ),
        )

    def mark_committed(
        self, operation_id: str, *, committed_json: str, updated_at: str
    ) -> None:
        self._execute(
            "UPDATE application_state.native_graph_explorer_operations SET "
            "status = 'committed', committed_json = %s, committed_sha256 = %s, "
            "rejected_json = NULL, rejected_sha256 = NULL, updated_at = %s "
            "WHERE principal_subject = %s AND managed_world_id = %s AND operation_id = %s",
            (
                committed_json,
                sha256_text(committed_json),
                updated_at,
                self.principal_subject,
                self.managed_world_id,
                operation_id,
            ),
        )

    def mark_rejected(
        self,
        operation_id: str,
        *,
        code: str,
        error: str,
        updated_at: str,
    ) -> None:
        rejected_json = canonical_json({"code": code, "error": error})
        self._execute(
            "UPDATE application_state.native_graph_explorer_operations SET "
            "status = 'rejected', rejected_json = %s, rejected_sha256 = %s, "
            "committed_json = NULL, committed_sha256 = NULL, updated_at = %s "
            "WHERE principal_subject = %s AND managed_world_id = %s AND operation_id = %s",
            (
                rejected_json,
                sha256_text(rejected_json),
                updated_at,
                self.principal_subject,
                self.managed_world_id,
                operation_id,
            ),
        )

    def _execute(self, query: str, params: tuple[Any, ...] = ()) -> Any:
        try:
            return self._connection.execute(query, params)
        except psycopg.Error as exc:
            raise NativeGraphExplorerStoreUnavailable(
                "Buddy application state could not read or update this graph operation."
            ) from exc

    def _rollback(self) -> None:
        try:
            self._connection.execute("ROLLBACK")
        except psycopg.Error:
            pass

    def _release_lock(self) -> None:
        if not self._session_lock_held:
            return
        try:
            result = self._connection.execute(
                "SELECT pg_advisory_unlock(%s, %s)", self._advisory_key()
            ).fetchone()
            if not result or not result["pg_advisory_unlock"]:
                raise NativeGraphExplorerStoreUnavailable(
                    "The graph operation lock could not be released."
                )
        except psycopg.Error as exc:
            raise NativeGraphExplorerStoreUnavailable(
                "The graph operation lock could not be released."
            ) from exc
        finally:
            self._session_lock_held = False

    def close(self) -> None:
        with self._lock:
            if self._connection.closed:
                return
            if (
                self._connection.info.transaction_status
                != psycopg.pq.TransactionStatus.IDLE
            ):
                self._rollback()
            self._release_lock()
            self._connection.close()
