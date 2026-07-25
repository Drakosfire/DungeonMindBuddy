"""Durable acceptance-operation journal (§12 sibling to generation journal)."""
from __future__ import annotations

import fcntl
from contextlib import contextmanager
from datetime import UTC, datetime
from pathlib import Path
from typing import Any, Iterator, Literal

from apps.live_control_server.integrations.dungeonmind_statblocks.mechanics_locator import (
    MechanicsLocatorV1,
)
from apps.live_control_server.models.statblock_mechanics_acceptance import (
    ACCEPTANCE_OPERATION_SCHEMA,
    AcceptanceMaterializationV1,
    AcceptanceOperationV1,
    create_request_digest_for_body,
    idempotency_key_for_operation,
    validate_operation_id,
)
from apps.live_control_server.models.threat_draft import require_draft_id
from apps.live_control_server.services.threat_draft_store import (
    ThreatDraftStoreError,
    read_committed_draft_version,
)
from src.live_play.live_store import load_json, write_json

DEFAULT_ACCEPTANCE_REL = "out/statblock_acceptance_operations"
MAX_ACCEPTANCE_OPERATION_RECORDS_PER_DRAFT = 32
LOCK_NAME = ".acceptance.lock"
_ACTIVE_AUTHORITY = frozenset(
    {"dispatched_unknown", "server_committed", "reconciled"},
)

ClaimAcceptanceOutcome = Literal[
    "claimed",
    "resume",
    "input_conflict",
    "acceptance_busy",
    "acceptance_history_full",
    "version_mismatch",
]


class AcceptanceReconciliationError(ValueError):
    status_code: int = 500

    def __init__(self, message: str, *, status_code: int = 500) -> None:
        super().__init__(message)
        self.status_code = status_code


def acceptance_root(repo_root: Path) -> Path:
    return repo_root / DEFAULT_ACCEPTANCE_REL


def _utc_now_iso() -> str:
    return datetime.now(UTC).isoformat().replace("+00:00", "Z")


# Re-export for callers that historically imported the digest helper from this module.
__all__ = (
    "MAX_ACCEPTANCE_OPERATION_RECORDS_PER_DRAFT",
    "AcceptanceReconciliationError",
    "ClaimAcceptanceOutcome",
    "acceptance_root",
    "claim_acceptance_operation",
    "create_request_digest_for_body",
    "get_acceptance_operation",
    "list_acceptance_operations_for_draft",
    "reconcile_acceptance_operation",
    "record_draft_ref_conflicted",
    "record_draft_ref_failed",
    "record_server_committed",
    "record_terminal_failure",
)


def _storage_unavailable() -> AcceptanceReconciliationError:
    return AcceptanceReconciliationError(
        "acceptance reconciliation storage unavailable",
        status_code=500,
    )


def _draft_directory(root: Path, draft_id: str) -> Path:
    safe = require_draft_id(draft_id)
    store_root = acceptance_root(root).resolve()
    directory = (store_root / safe).resolve()
    if directory.parent != store_root:
        raise AcceptanceReconciliationError("acceptance path escape", status_code=500)
    return directory


def _record_path(root: Path, *, draft_id: str, operation_id: str) -> Path:
    safe_draft = require_draft_id(draft_id)
    safe_op = validate_operation_id(operation_id)
    directory = _draft_directory(root, safe_draft)
    path = (directory / f"{safe_op}.json").resolve()
    if path.parent != directory:
        raise AcceptanceReconciliationError("acceptance path escape", status_code=500)
    return path


@contextmanager
def _draft_acceptance_lock(root: Path, draft_id: str) -> Iterator[None]:
    """Draft-scoped exclusive lock for acceptance journal mutations.

    Lock order when both stores are needed: acquire this lock before the
    ThreatDraft store lock (``threat_draft_store._store_lock``). Generation
    reconciliation locking is independent and must never nest under this lock
    or the store lock in the reverse direction of documented orders.
    """
    directory = _draft_directory(root, draft_id)
    try:
        directory.mkdir(parents=True, exist_ok=True)
        lock_path = directory / LOCK_NAME
        with lock_path.open("a+", encoding="utf-8") as lock_file:
            try:
                fcntl.flock(lock_file.fileno(), fcntl.LOCK_EX)
            except OSError:
                raise _storage_unavailable() from None
            try:
                yield
            finally:
                try:
                    fcntl.flock(lock_file.fileno(), fcntl.LOCK_UN)
                except OSError:
                    pass
    except AcceptanceReconciliationError:
        raise
    except OSError:
        raise _storage_unavailable() from None


def _write_operation_unlocked(
    root: Path, record: AcceptanceOperationV1
) -> AcceptanceOperationV1:
    path = _record_path(
        root,
        draft_id=record.source_draft_id,
        operation_id=record.operation_id,
    )
    try:
        path.parent.mkdir(parents=True, exist_ok=True)
        write_json(path, record.model_dump(mode="json", by_alias=True))
    except OSError:
        raise _storage_unavailable() from None
    return record


def _read_operation_unlocked(
    root: Path, *, draft_id: str, operation_id: str
) -> AcceptanceOperationV1 | None:
    path = _record_path(root, draft_id=draft_id, operation_id=operation_id)
    try:
        if not path.is_file():
            return None
        payload = load_json(path)
    except OSError:
        raise _storage_unavailable() from None
    if payload.get("schema") != ACCEPTANCE_OPERATION_SCHEMA:
        raise AcceptanceReconciliationError(
            "corrupt acceptance operation record",
            status_code=500,
        )
    try:
        record = AcceptanceOperationV1.model_validate(payload)
    except Exception as exc:
        raise AcceptanceReconciliationError(
            "corrupt acceptance operation record",
            status_code=500,
        ) from exc
    safe_draft = require_draft_id(draft_id)
    safe_op = validate_operation_id(operation_id)
    if record.source_draft_id != safe_draft:
        raise AcceptanceReconciliationError(
            "corrupt acceptance operation record",
            status_code=500,
        )
    if record.operation_id != safe_op:
        raise AcceptanceReconciliationError(
            "corrupt acceptance operation record",
            status_code=500,
        )
    return record


def _list_operations_unlocked(root: Path, *, draft_id: str) -> list[AcceptanceOperationV1]:
    directory = _draft_directory(root, draft_id)
    if not directory.is_dir():
        return []
    records: list[AcceptanceOperationV1] = []
    try:
        paths = sorted(p for p in directory.glob("*.json"))
    except OSError:
        raise _storage_unavailable() from None
    safe_draft = require_draft_id(draft_id)
    for path in paths:
        op_id = path.stem
        record = _read_operation_unlocked(root, draft_id=safe_draft, operation_id=op_id)
        if record is not None:
            records.append(record)
    if len(records) > MAX_ACCEPTANCE_OPERATION_RECORDS_PER_DRAFT:
        raise AcceptanceReconciliationError(
            "acceptance operation storage bound exceeded",
            status_code=500,
        )
    return records


def _has_active_slot(records: list[AcceptanceOperationV1]) -> bool:
    return any(r.authority_state in _ACTIVE_AUTHORITY for r in records)


def claim_acceptance_operation(
    root: Path,
    *,
    draft_id: str,
    expected_draft_version: int,
    operation_id: str,
    create_request_digest: str,
    request_body: dict[str, Any],
    validation_receipt_digest: str,
    source_candidate_id: str | None,
) -> tuple[ClaimAcceptanceOutcome, AcceptanceOperationV1 | None]:
    """Atomic singular-slot claim before any Server create (lock released on return).

    Lock order: acceptance journal lock → ThreatDraft store lock.
    Existing-operation resume/conflict is resolved before the current draft-version
    gate so durable operations remain recoverable after unrelated draft edits.
    """
    body_digest = create_request_digest_for_body(request_body)
    if body_digest != create_request_digest:
        raise AcceptanceReconciliationError(
            "acceptance request body digest mismatch",
            status_code=500,
        )

    safe_draft = require_draft_id(draft_id)
    safe_op = validate_operation_id(operation_id)

    with _draft_acceptance_lock(root, safe_draft):
        existing = _read_operation_unlocked(root, draft_id=safe_draft, operation_id=safe_op)
        if existing is not None:
            if (
                existing.create_request_digest != create_request_digest
                or existing.request_body != request_body
            ):
                return "input_conflict", existing
            return "resume", existing

        try:
            current_version = read_committed_draft_version(root, safe_draft)
        except ThreatDraftStoreError as exc:
            raise AcceptanceReconciliationError(
                str(exc), status_code=exc.status_code
            ) from exc
        if current_version != expected_draft_version:
            return "version_mismatch", None

        records = _list_operations_unlocked(root, draft_id=safe_draft)
        if len(records) >= MAX_ACCEPTANCE_OPERATION_RECORDS_PER_DRAFT:
            return "acceptance_history_full", None
        if _has_active_slot(records):
            return "acceptance_busy", None

        now = _utc_now_iso()
        record = AcceptanceOperationV1(
            operation_id=safe_op,
            idempotency_key=idempotency_key_for_operation(safe_op),
            create_request_digest=create_request_digest,
            request_body=request_body,
            source_draft_id=safe_draft,
            source_draft_version=expected_draft_version,
            source_candidate_id=source_candidate_id,
            validation_receipt_digest=validation_receipt_digest,
            authority_state="dispatched_unknown",
            locator=None,
            materialization=AcceptanceMaterializationV1(draft_ref="missing"),
            created_at=now,
            updated_at=now,
        )
        _write_operation_unlocked(root, record)
        return "claimed", record


def get_acceptance_operation(
    root: Path, *, draft_id: str, operation_id: str
) -> AcceptanceOperationV1 | None:
    with _draft_acceptance_lock(root, draft_id):
        return _read_operation_unlocked(root, draft_id=draft_id, operation_id=operation_id)


def list_acceptance_operations_for_draft(
    root: Path, *, draft_id: str
) -> list[AcceptanceOperationV1]:
    with _draft_acceptance_lock(root, draft_id):
        return _list_operations_unlocked(root, draft_id=draft_id)


def record_server_committed(
    root: Path,
    *,
    draft_id: str,
    operation_id: str,
    create_request_digest: str,
    locator: MechanicsLocatorV1,
) -> AcceptanceOperationV1:
    with _draft_acceptance_lock(root, draft_id):
        existing = _read_operation_unlocked(root, draft_id=draft_id, operation_id=operation_id)
        if existing is None:
            raise AcceptanceReconciliationError(
                "missing acceptance operation claim",
                status_code=500,
            )
        if existing.create_request_digest != create_request_digest:
            raise AcceptanceReconciliationError("acceptance operation conflict", status_code=409)
        if existing.authority_state == "reconciled":
            if existing.locator and MechanicsLocatorV1.model_validate(
                existing.locator.model_dump(mode="json")
            ) == locator:
                return existing
            raise AcceptanceReconciliationError("acceptance operation conflict", status_code=409)
        if existing.authority_state == "terminal_failure":
            raise AcceptanceReconciliationError("acceptance operation conflict", status_code=409)
        if existing.authority_state == "server_committed":
            if existing.locator == locator:
                return existing
            raise AcceptanceReconciliationError("acceptance operation conflict", status_code=409)
        if existing.authority_state != "dispatched_unknown":
            raise AcceptanceReconciliationError("acceptance operation conflict", status_code=409)
        updated = existing.model_copy(
            update={
                "authority_state": "server_committed",
                "locator": locator,
                "updated_at": _utc_now_iso(),
            }
        )
        return _write_operation_unlocked(root, updated)


def record_terminal_failure(
    root: Path,
    *,
    draft_id: str,
    operation_id: str,
    create_request_digest: str,
    terminal_code: str,
    failure_category: str,
    http_status: int,
    terminal_details: dict[str, Any] | None = None,
) -> AcceptanceOperationV1:
    with _draft_acceptance_lock(root, draft_id):
        existing = _read_operation_unlocked(root, draft_id=draft_id, operation_id=operation_id)
        if existing is None:
            raise AcceptanceReconciliationError(
                "missing acceptance operation claim",
                status_code=500,
            )
        if existing.create_request_digest != create_request_digest:
            raise AcceptanceReconciliationError("acceptance operation conflict", status_code=409)
        if existing.authority_state == "terminal_failure":
            return existing
        if existing.authority_state != "dispatched_unknown":
            raise AcceptanceReconciliationError("acceptance operation conflict", status_code=409)
        updated = existing.model_copy(
            update={
                "authority_state": "terminal_failure",
                "locator": None,
                "materialization": AcceptanceMaterializationV1(draft_ref="missing"),
                "terminal_code": terminal_code,
                "failure_category": failure_category,
                "http_status": http_status,
                "terminal_details": terminal_details,
                "updated_at": _utc_now_iso(),
            }
        )
        return _write_operation_unlocked(root, updated)


def record_draft_ref_failed(
    root: Path,
    *,
    draft_id: str,
    operation_id: str,
    create_request_digest: str,
) -> AcceptanceOperationV1:
    with _draft_acceptance_lock(root, draft_id):
        existing = _read_operation_unlocked(root, draft_id=draft_id, operation_id=operation_id)
        if existing is None:
            raise AcceptanceReconciliationError(
                "missing acceptance operation claim",
                status_code=500,
            )
        if existing.create_request_digest != create_request_digest:
            raise AcceptanceReconciliationError("acceptance operation conflict", status_code=409)
        if existing.authority_state != "server_committed":
            raise AcceptanceReconciliationError("acceptance operation conflict", status_code=409)
        if existing.materialization.draft_ref == "attached":
            return existing
        mat = existing.materialization.model_copy(update={"draft_ref": "failed"})
        updated = existing.model_copy(
            update={"materialization": mat, "updated_at": _utc_now_iso()}
        )
        return _write_operation_unlocked(root, updated)


def record_draft_ref_conflicted(
    root: Path,
    *,
    draft_id: str,
    operation_id: str,
    create_request_digest: str,
) -> AcceptanceOperationV1:
    with _draft_acceptance_lock(root, draft_id):
        existing = _read_operation_unlocked(root, draft_id=draft_id, operation_id=operation_id)
        if existing is None:
            raise AcceptanceReconciliationError(
                "missing acceptance operation claim",
                status_code=500,
            )
        if existing.create_request_digest != create_request_digest:
            raise AcceptanceReconciliationError("acceptance operation conflict", status_code=409)
        if existing.authority_state != "server_committed":
            raise AcceptanceReconciliationError("acceptance operation conflict", status_code=409)
        mat = existing.materialization.model_copy(update={"draft_ref": "conflicted"})
        updated = existing.model_copy(
            update={"materialization": mat, "updated_at": _utc_now_iso()}
        )
        return _write_operation_unlocked(root, updated)


def reconcile_acceptance_operation(
    root: Path,
    *,
    draft_id: str,
    operation_id: str,
    create_request_digest: str,
) -> AcceptanceOperationV1:
    """Phase 2 journal repair: reconciled + draft_ref=attached."""
    with _draft_acceptance_lock(root, draft_id):
        existing = _read_operation_unlocked(root, draft_id=draft_id, operation_id=operation_id)
        if existing is None:
            raise AcceptanceReconciliationError(
                "missing acceptance operation claim",
                status_code=500,
            )
        if existing.create_request_digest != create_request_digest:
            raise AcceptanceReconciliationError("acceptance operation conflict", status_code=409)
        if existing.authority_state == "reconciled":
            return existing
        if existing.authority_state != "server_committed" or existing.locator is None:
            raise AcceptanceReconciliationError("acceptance operation not committable", status_code=409)
        mat = existing.materialization.model_copy(update={"draft_ref": "attached"})
        updated = existing.model_copy(
            update={
                "authority_state": "reconciled",
                "materialization": mat,
                "updated_at": _utc_now_iso(),
            }
        )
        return _write_operation_unlocked(root, updated)
