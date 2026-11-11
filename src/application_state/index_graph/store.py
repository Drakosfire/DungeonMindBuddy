"""APP-STATE journal for one browser-owned native graph allocation.

DungeonMind owns semantic graph data. This store contains only allocation
bindings and bounded preparation/recovery metadata. A PostgreSQL session-level
advisory lock spans every transaction checkpoint so another Buddy process cannot
interleave a session's native work after a journal commit.
"""

from __future__ import annotations

import hashlib
import json
import threading
from contextlib import contextmanager
from typing import Any, Iterator
from uuid import UUID

import psycopg
from psycopg.rows import dict_row

from application_state.engine import connect
from application_state.errors import ApplicationStateUnavailableError


MAX_JOURNAL_OPERATIONS = 512


def canonical_json(value: object) -> str:
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"))


def sha256_text(value: str) -> str:
    return hashlib.sha256(value.encode("utf-8")).hexdigest()


class IndexGraphStoreUnavailable(RuntimeError):
    """APP-STATE could not safely read or update this session's journal."""


class IndexGraphStore:
    """Synchronous journal bound to exactly one server-owned session UUID."""

    _locks_guard = threading.Lock()
    _locks: dict[str, threading.RLock] = {}

    def __init__(
        self,
        session_id: str,
        allocation_id: str,
        *,
        max_operations: int = MAX_JOURNAL_OPERATIONS,
    ) -> None:
        try:
            self.session_id = str(UUID(session_id))
        except (ValueError, TypeError, AttributeError) as exc:
            raise ValueError("session_id must be a canonical UUID") from exc
        if self.session_id != session_id:
            raise ValueError("session_id must be a canonical UUID")
        if not isinstance(allocation_id, str) or not allocation_id.startswith(
            "buddy-index-graph:"
        ):
            raise ValueError("allocation_id must be a server-owned index graph id")
        self.allocation_id = allocation_id
        self.max_operations = max_operations
        self._lock = self._process_lock(self.session_id)
        try:
            self._connection = connect()
            self._connection.autocommit = True
            self._connection.row_factory = dict_row
        except (ApplicationStateUnavailableError, psycopg.Error) as exc:
            raise IndexGraphStoreUnavailable(
                "Buddy application state is unavailable."
            ) from exc
        self._transaction_depth = 0
        self._session_lock_held = False

    @classmethod
    def _process_lock(cls, session_id: str) -> threading.RLock:
        with cls._locks_guard:
            return cls._locks.setdefault(session_id, threading.RLock())

    def _advisory_key(self) -> tuple[int, int]:
        digest = hashlib.sha256(self.session_id.encode("ascii")).digest()
        unsigned = int.from_bytes(digest[:8], "big")
        high = (unsigned >> 32) & 0xFFFFFFFF
        low = unsigned & 0xFFFFFFFF
        return (
            high - 0x100000000 if high >= 0x80000000 else high,
            low - 0x100000000 if low >= 0x80000000 else low,
        )

    @contextmanager
    def atomic(self) -> Iterator[IndexGraphStore]:
        """Serialize one session across processes and one multi-step action."""
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
                bound = self._connection.execute(
                    "SELECT allocation_id FROM application_state.index_graph_sessions "
                    "WHERE session_id = %s::uuid",
                    (self.session_id,),
                ).fetchone()
                if bound is None or bound["allocation_id"] != self.allocation_id:
                    raise IndexGraphStoreUnavailable(
                        "The graph session no longer matches its allocation binding."
                    )
            except (ApplicationStateUnavailableError, psycopg.Error) as exc:
                if self._session_lock_held:
                    try:
                        self._connection.execute("ROLLBACK")
                        self._connection.execute(
                            "SELECT pg_advisory_unlock(%s, %s)", self._advisory_key()
                        )
                    except psycopg.Error:
                        pass
                    self._session_lock_held = False
                raise IndexGraphStoreUnavailable(
                    "Buddy application state could not lock this graph session."
                ) from exc
            except BaseException:
                if (
                    self._connection.info.transaction_status
                    != psycopg.pq.TransactionStatus.IDLE
                ):
                    try:
                        self._connection.execute("ROLLBACK")
                    except psycopg.Error:
                        pass
                if self._session_lock_held:
                    try:
                        self._connection.execute(
                            "SELECT pg_advisory_unlock(%s, %s)", self._advisory_key()
                        )
                    except psycopg.Error:
                        pass
                    self._session_lock_held = False
                raise
            self._transaction_depth = 1
            try:
                yield self
            except BaseException:
                self._transaction_depth = 0
                if (
                    self._connection.info.transaction_status
                    != psycopg.pq.TransactionStatus.IDLE
                ):
                    try:
                        self._connection.execute("ROLLBACK")
                    except psycopg.Error:
                        pass
                raise
            else:
                self._transaction_depth = 0
                try:
                    self._connection.execute("COMMIT")
                except psycopg.Error as exc:
                    raise IndexGraphStoreUnavailable(
                        "Buddy application state could not commit this journal update."
                    ) from exc
            finally:
                if self._session_lock_held:
                    try:
                        unlocked = self._connection.execute(
                            "SELECT pg_advisory_unlock(%s, %s)", self._advisory_key()
                        ).fetchone()
                        self._session_lock_held = False
                        if not unlocked or not unlocked["pg_advisory_unlock"]:
                            raise IndexGraphStoreUnavailable(
                                "The graph session lock could not be released."
                            )
                    except psycopg.Error as exc:
                        self._session_lock_held = False
                        raise IndexGraphStoreUnavailable(
                            "The graph session lock could not be released."
                        ) from exc

    def get_metadata(self, key: str) -> str | None:
        with self._lock:
            row = self._execute(
                "SELECT value FROM application_state.index_graph_bindings "
                "WHERE session_id = %s::uuid AND key = %s",
                (self.session_id, key),
            ).fetchone()
            return None if row is None else str(row["value"])

    def set_metadata(self, key: str, value: str) -> None:
        with self._lock:
            self._execute(
                "INSERT INTO application_state.index_graph_bindings(session_id, key, value) "
                "VALUES (%s::uuid, %s, %s) ON CONFLICT (session_id, key) "
                "DO UPDATE SET value = EXCLUDED.value",
                (self.session_id, key, value),
            )

    def operation_count(self) -> int:
        with self._lock:
            row = self._execute(
                "SELECT (SELECT count(*) FROM application_state.index_graph_operations "
                "WHERE session_id = %s::uuid) + (SELECT count(*) FROM "
                "application_state.index_graph_reservations WHERE session_id = %s::uuid) AS count",
                (self.session_id, self.session_id),
            ).fetchone()
            return int(row["count"])

    def get_reservation(self, operation_id: str) -> dict[str, Any] | None:
        with self._lock:
            row = self._execute(
                "SELECT operation_id, request_json, request_sha256, parent_revision_id, updated_at "
                "FROM application_state.index_graph_reservations "
                "WHERE session_id = %s::uuid AND operation_id = %s",
                (self.session_id, operation_id),
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
            raise OverflowError("index graph operation journal is full")
        with self._lock:
            self._execute(
                "INSERT INTO application_state.index_graph_reservations "
                "(session_id, operation_id, request_json, request_sha256, parent_revision_id, updated_at) "
                "VALUES (%s::uuid, %s, %s, %s, %s, %s)",
                (
                    self.session_id,
                    operation_id,
                    request_json,
                    sha256_text(request_json),
                    parent_revision_id,
                    updated_at,
                ),
            )

    def remove_reservation(self, operation_id: str) -> None:
        with self._lock:
            self._execute(
                "DELETE FROM application_state.index_graph_reservations "
                "WHERE session_id = %s::uuid AND operation_id = %s",
                (self.session_id, operation_id),
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
        self._execute(
            "INSERT INTO application_state.index_graph_operations "
            "(session_id, operation_id, request_json, request_sha256, parent_revision_id, "
            "prepared_json, prepared_sha256, status, committed_json, rejected_json, updated_at) "
            "VALUES (%s::uuid, %s, %s, %s, %s, %s, %s, 'prepared', NULL, NULL, %s)",
            (
                self.session_id,
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
        prepared_json = "null"
        rejected_json = canonical_json({"code": code, "error": error})
        self._execute(
            "INSERT INTO application_state.index_graph_operations "
            "(session_id, operation_id, request_json, request_sha256, parent_revision_id, "
            "prepared_json, prepared_sha256, status, committed_json, rejected_json, updated_at) "
            "VALUES (%s::uuid, %s, %s, %s, %s, %s, %s, 'rejected', NULL, %s, %s)",
            (
                self.session_id,
                operation_id,
                reservation["request_json"],
                reservation["request_sha256"],
                reservation["parent_revision_id"],
                prepared_json,
                sha256_text(prepared_json),
                rejected_json,
                updated_at,
            ),
        )
        self.remove_reservation(operation_id)

    @contextmanager
    def checkpoint(self) -> Iterator[None]:
        """Commit before native dispatch without releasing the session lock."""
        if self._transaction_depth != 1:
            raise RuntimeError("checkpoint requires the outermost service transaction")
        try:
            self._connection.execute("COMMIT")
            self._connection.execute("BEGIN")
            yield
        except BaseException:
            if (
                self._connection.info.transaction_status
                != psycopg.pq.TransactionStatus.IDLE
            ):
                try:
                    self._connection.execute("ROLLBACK")
                except psycopg.Error:
                    pass
            raise

    def get_operation(self, operation_id: str) -> dict[str, Any] | None:
        with self._lock:
            row = self._execute(
                "SELECT * FROM application_state.index_graph_operations "
                "WHERE session_id = %s::uuid AND operation_id = %s",
                (self.session_id, operation_id),
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
            raise OverflowError("index graph operation journal is full")
        if status not in {"prepared", "committed", "unknown", "rejected"}:
            raise ValueError("unsupported operation status")
        with self._lock:
            self._execute(
                "INSERT INTO application_state.index_graph_operations "
                "(session_id, operation_id, request_json, request_sha256, parent_revision_id, "
                "prepared_json, prepared_sha256, status, committed_json, rejected_json, updated_at) "
                "VALUES (%s::uuid, %s, %s, %s, %s, %s, %s, %s, NULL, NULL, %s)",
                (
                    self.session_id,
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
        self._execute(
            "UPDATE application_state.index_graph_operations SET status = 'unknown', "
            "rejected_json = NULL, updated_at = %s WHERE session_id = %s::uuid AND operation_id = %s",
            (updated_at, self.session_id, operation_id),
        )

    def mark_operation_committed(
        self, operation_id: str, *, committed_json: str, updated_at: str
    ) -> None:
        self._execute(
            "UPDATE application_state.index_graph_operations SET status = 'committed', "
            "committed_json = %s, rejected_json = NULL, updated_at = %s "
            "WHERE session_id = %s::uuid AND operation_id = %s",
            (committed_json, updated_at, self.session_id, operation_id),
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
        self._execute(
            "UPDATE application_state.index_graph_operations SET status = 'rejected', "
            "rejected_json = %s, committed_json = NULL, updated_at = %s "
            "WHERE session_id = %s::uuid AND operation_id = %s",
            (rejected_json, updated_at, self.session_id, operation_id),
        )

    def close(self) -> None:
        with self._lock:
            if self._connection.closed:
                return
            if (
                self._connection.info.transaction_status
                != psycopg.pq.TransactionStatus.IDLE
            ):
                try:
                    self._connection.execute("ROLLBACK")
                except psycopg.Error:
                    pass
            if self._session_lock_held:
                try:
                    self._connection.execute(
                        "SELECT pg_advisory_unlock(%s, %s)", self._advisory_key()
                    )
                except psycopg.Error:
                    pass
                self._session_lock_held = False
            self._connection.close()

    def _execute(self, query: str, params: tuple[Any, ...] = ()) -> Any:
        try:
            return self._connection.execute(query, params)
        except psycopg.Error as exc:
            raise IndexGraphStoreUnavailable(
                "Buddy application state could not read or update this graph session."
            ) from exc
