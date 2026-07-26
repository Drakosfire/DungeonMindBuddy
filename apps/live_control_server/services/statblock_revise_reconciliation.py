"""Durable revise-operation journal (§12 sibling to generation / acceptance)."""
from __future__ import annotations

import fcntl
from contextlib import contextmanager
from datetime import UTC, datetime
from pathlib import Path
from typing import Any, Iterator, Literal

from apps.live_control_server.models.statblock_candidate_revision import (
    REVISE_OPERATION_SCHEMA,
    ClaimReviseOutcome,
    ReviseMaterializationV1,
    ReviseOperationV1,
    revise_request_digest_for_server_body,
)
from apps.live_control_server.models.threat_draft import MAX_CANDIDATE_REFS, require_draft_id
from apps.live_control_server.services.statblock_candidate_capacity import (
    CandidateCapacityError,
    draft_candidate_capacity_lock,
    total_candidate_capacity_usage,
)
from apps.live_control_server.services.statblock_generation_reconciliation import (
    GenerationReconciliationError,
    validate_request_id,
)
from apps.live_control_server.services.threat_draft_store import (
    ThreatDraftStoreError,
    read_committed_draft_version,
)
from src.live_play.live_store import load_json, write_json

DEFAULT_REVISE_REL = "out/statblock_revise_operations"
LOCK_NAME = ".revise.lock"
_UNRESOLVED = frozenset(
    {
        "claimed",
        "dispatched_unknown",
        "candidate_received",
        "cache_stored_ref_pending",
    }
)


class ReviseReconciliationError(ValueError):
    status_code: int = 500

    def __init__(self, message: str, *, status_code: int = 500) -> None:
        super().__init__(message)
        self.status_code = status_code


def revise_root(repo_root: Path) -> Path:
    return repo_root / DEFAULT_REVISE_REL


def _utc_now_iso() -> str:
    return datetime.now(UTC).isoformat().replace("+00:00", "Z")


def _storage_unavailable() -> ReviseReconciliationError:
    return ReviseReconciliationError(
        "revise reconciliation storage unavailable",
        status_code=500,
    )


def _draft_directory(root: Path, draft_id: str) -> Path:
    safe = require_draft_id(draft_id)
    store_root = revise_root(root).resolve()
    directory = (store_root / safe).resolve()
    if directory.parent != store_root:
        raise ReviseReconciliationError("revise path escape", status_code=500)
    return directory


def _record_path(root: Path, *, draft_id: str, request_id: str) -> Path:
    safe_draft = require_draft_id(draft_id)
    safe_request = validate_request_id(request_id)
    directory = _draft_directory(root, safe_draft)
    path = (directory / f"{safe_request}.json").resolve()
    if path.parent != directory:
        raise ReviseReconciliationError("revise path escape", status_code=500)
    return path


@contextmanager
def _draft_revise_lock(root: Path, draft_id: str) -> Iterator[None]:
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
    except ReviseReconciliationError:
        raise
    except OSError:
        raise _storage_unavailable() from None


def _write_operation_unlocked(root: Path, record: ReviseOperationV1) -> ReviseOperationV1:
    path = _record_path(root, draft_id=record.draft_id, request_id=record.request_id)
    try:
        path.parent.mkdir(parents=True, exist_ok=True)
        write_json(path, record.model_dump(mode="json", by_alias=True))
    except OSError:
        raise _storage_unavailable() from None
    return record


def _read_operation_unlocked(
    root: Path, *, draft_id: str, request_id: str
) -> ReviseOperationV1 | None:
    path = _record_path(root, draft_id=draft_id, request_id=request_id)
    try:
        if not path.is_file():
            return None
        payload = load_json(path)
    except OSError:
        raise _storage_unavailable() from None
    if payload.get("schema") != REVISE_OPERATION_SCHEMA:
        raise ReviseReconciliationError(
            "corrupt revise operation record",
            status_code=500,
        )
    try:
        record = ReviseOperationV1.model_validate(payload)
    except Exception as exc:
        raise ReviseReconciliationError(
            "corrupt revise operation record",
            status_code=500,
        ) from exc
    safe_draft = require_draft_id(draft_id)
    safe_request = validate_request_id(request_id)
    if record.draft_id != safe_draft or record.request_id != safe_request:
        raise ReviseReconciliationError(
            "corrupt revise operation record",
            status_code=500,
        )
    return record


def _list_operations_unlocked(root: Path, *, draft_id: str) -> list[ReviseOperationV1]:
    directory = _draft_directory(root, draft_id)
    if not directory.is_dir():
        return []
    records: list[ReviseOperationV1] = []
    try:
        paths = sorted(p for p in directory.glob("*.json") if p.name != LOCK_NAME)
    except OSError:
        raise _storage_unavailable() from None
    safe_draft = require_draft_id(draft_id)
    for path in paths:
        request_id = path.stem
        record = _read_operation_unlocked(
            root, draft_id=safe_draft, request_id=request_id
        )
        if record is not None:
            records.append(record)
    return records


def _has_unresolved_revise(
    records: list[ReviseOperationV1], *, excluding_request_id: str | None = None
) -> bool:
    for record in records:
        if excluding_request_id and record.request_id == excluding_request_id:
            continue
        if record.status in _UNRESOLVED:
            return True
    return False


def _revise_reservation_count(
    records: list[ReviseOperationV1],
    *,
    ref_candidate_ids: set[str],
) -> int:
    count = 0
    for record in records:
        if record.status not in _UNRESOLVED:
            continue
        if record.candidate_id is None or record.candidate_id not in ref_candidate_ids:
            count += 1
    return count


def count_revise_capacity_reservations(
    root: Path,
    *,
    draft_id: str,
    ref_candidate_ids: set[str],
) -> int:
    """Unbound revise reservations (excludes candidates already on the draft).

    Safe under ``draft_candidate_capacity_lock`` without nesting the revise lock:
    new revise claims also require the capacity lock, so concurrent admission
    cannot race this read. Callers that already hold the revise lock may also
    use this helper.
    """
    safe_draft = require_draft_id(draft_id)
    records = _list_operations_unlocked(root, draft_id=safe_draft)
    return _revise_reservation_count(records, ref_candidate_ids=ref_candidate_ids)


def claim_revise_operation(
    root: Path,
    *,
    draft_id: str,
    expected_draft_version: int,
    request_id: str,
    request_digest: str,
    request_body: dict[str, Any],
    editor_state_revision: str,
    source_definition_digest: str,
    instruction_options_digest: str,
    ref_candidate_ids: set[str],
) -> tuple[ClaimReviseOutcome, ReviseOperationV1 | None]:
    body_digest = revise_request_digest_for_server_body(request_body)
    if body_digest != request_digest:
        raise ReviseReconciliationError(
            "revise request body digest mismatch",
            status_code=500,
        )

    safe_draft = require_draft_id(draft_id)
    safe_request = validate_request_id(request_id)

    # Existing-operation authority before draft version / capacity gates.
    with _draft_revise_lock(root, safe_draft):
        existing = _read_operation_unlocked(
            root, draft_id=safe_draft, request_id=safe_request
        )
        if existing is not None:
            if (
                existing.request_digest != request_digest
                or existing.request_body != request_body
            ):
                return "revise_input_conflict", existing
            return "resume", existing

    # New claim: shared capacity boundary then revise journal write.
    try:
        with draft_candidate_capacity_lock(root, safe_draft):
            with _draft_revise_lock(root, safe_draft):
                existing = _read_operation_unlocked(
                    root, draft_id=safe_draft, request_id=safe_request
                )
                if existing is not None:
                    if (
                        existing.request_digest != request_digest
                        or existing.request_body != request_body
                    ):
                        return "revise_input_conflict", existing
                    return "resume", existing

                try:
                    current_version = read_committed_draft_version(root, safe_draft)
                except ThreatDraftStoreError as exc:
                    raise ReviseReconciliationError(
                        str(exc), status_code=exc.status_code
                    ) from exc
                if current_version != expected_draft_version:
                    return "version_mismatch", None

                records = _list_operations_unlocked(root, draft_id=safe_draft)
                if _has_unresolved_revise(records):
                    return "revise_busy", None

                try:
                    usage = total_candidate_capacity_usage(
                        root,
                        draft_id=safe_draft,
                        ref_candidate_ids=ref_candidate_ids,
                    )
                except (CandidateCapacityError, GenerationReconciliationError) as exc:
                    status = getattr(exc, "status_code", 500)
                    raise ReviseReconciliationError(
                        str(exc), status_code=status
                    ) from exc

                if usage + 1 > MAX_CANDIDATE_REFS:
                    return "revise_history_full", None

                now = _utc_now_iso()
                record = ReviseOperationV1(
                    request_id=safe_request,
                    request_digest=request_digest,
                    request_body=request_body,
                    draft_id=safe_draft,
                    source_draft_version=expected_draft_version,
                    editor_state_revision=editor_state_revision,
                    source_definition_digest=source_definition_digest,
                    instruction_options_digest=instruction_options_digest,
                    status="claimed",
                    candidate_id=None,
                    materialization=ReviseMaterializationV1(
                        cache="missing", draft_ref="missing"
                    ),
                    created_at=now,
                    updated_at=now,
                )
                _write_operation_unlocked(root, record)
                return "claimed", record
    except CandidateCapacityError as exc:
        raise ReviseReconciliationError(str(exc), status_code=exc.status_code) from exc


def write_ahead_dispatched_unknown(
    root: Path,
    *,
    draft_id: str,
    request_id: str,
    request_digest: str,
) -> ReviseOperationV1:
    with _draft_revise_lock(root, draft_id):
        existing = _read_operation_unlocked(
            root, draft_id=draft_id, request_id=request_id
        )
        if existing is None:
            raise ReviseReconciliationError(
                "missing revise operation claim",
                status_code=500,
            )
        if existing.request_digest != request_digest:
            raise ReviseReconciliationError("revise operation conflict", status_code=409)
        if existing.status == "dispatched_unknown":
            return existing
        if existing.status != "claimed":
            raise ReviseReconciliationError("revise operation conflict", status_code=409)
        updated = existing.model_copy(
            update={"status": "dispatched_unknown", "updated_at": _utc_now_iso()}
        )
        return _write_operation_unlocked(root, updated)


def record_candidate_received(
    root: Path,
    *,
    draft_id: str,
    request_id: str,
    request_digest: str,
    candidate_id: str,
    cache_state: Literal["missing", "stored", "failed"] = "missing",
) -> ReviseOperationV1:
    with _draft_revise_lock(root, draft_id):
        existing = _read_operation_unlocked(
            root, draft_id=draft_id, request_id=request_id
        )
        if existing is None:
            raise ReviseReconciliationError(
                "missing revise operation claim",
                status_code=500,
            )
        if existing.request_digest != request_digest:
            raise ReviseReconciliationError("revise operation conflict", status_code=409)
        if existing.status == "candidate_received" and existing.candidate_id == candidate_id:
            return existing
        if existing.status == "cache_stored_ref_pending" and existing.candidate_id == candidate_id:
            return existing
        if existing.status not in {"dispatched_unknown", "candidate_received"}:
            raise ReviseReconciliationError("revise operation conflict", status_code=409)
        updated = existing.model_copy(
            update={
                "status": "candidate_received",
                "candidate_id": candidate_id,
                "materialization": ReviseMaterializationV1(
                    cache=cache_state,
                    draft_ref=existing.materialization.draft_ref,
                ),
                "updated_at": _utc_now_iso(),
            }
        )
        return _write_operation_unlocked(root, updated)


def mark_cache_stored_ref_pending(
    root: Path,
    *,
    draft_id: str,
    request_id: str,
    request_digest: str,
    candidate_id: str,
) -> ReviseOperationV1:
    with _draft_revise_lock(root, draft_id):
        existing = _read_operation_unlocked(
            root, draft_id=draft_id, request_id=request_id
        )
        if existing is None:
            raise ReviseReconciliationError(
                "missing revise operation claim",
                status_code=500,
            )
        if existing.request_digest != request_digest:
            raise ReviseReconciliationError("revise operation conflict", status_code=409)
        if existing.status == "cache_stored_ref_pending" and existing.candidate_id == candidate_id:
            return existing
        if existing.status not in {"candidate_received", "cache_stored_ref_pending"}:
            raise ReviseReconciliationError("revise operation conflict", status_code=409)
        if existing.candidate_id != candidate_id:
            raise ReviseReconciliationError("revise operation conflict", status_code=409)
        updated = existing.model_copy(
            update={
                "status": "cache_stored_ref_pending",
                "materialization": ReviseMaterializationV1(
                    cache="stored",
                    draft_ref=existing.materialization.draft_ref,
                ),
                "updated_at": _utc_now_iso(),
            }
        )
        return _write_operation_unlocked(root, updated)


def record_terminal_failure(
    root: Path,
    *,
    draft_id: str,
    request_id: str,
    request_digest: str,
    terminal_code: str,
    failure_category: str,
    http_status: int,
    terminal_details: dict[str, Any] | None = None,
) -> ReviseOperationV1:
    with _draft_revise_lock(root, draft_id):
        existing = _read_operation_unlocked(
            root, draft_id=draft_id, request_id=request_id
        )
        if existing is None:
            raise ReviseReconciliationError(
                "missing revise operation claim",
                status_code=500,
            )
        if existing.request_digest != request_digest:
            raise ReviseReconciliationError("revise operation conflict", status_code=409)
        if existing.status == "terminal_failure":
            return existing
        if existing.status not in {"claimed", "dispatched_unknown"}:
            raise ReviseReconciliationError("revise operation conflict", status_code=409)
        updated = existing.model_copy(
            update={
                "status": "terminal_failure",
                "candidate_id": None,
                "materialization": ReviseMaterializationV1(cache="missing", draft_ref="missing"),
                "terminal_code": terminal_code,
                "failure_category": failure_category,
                "http_status": http_status,
                "terminal_details": terminal_details,
                "updated_at": _utc_now_iso(),
            }
        )
        return _write_operation_unlocked(root, updated)


def get_revise_operation(
    root: Path, *, draft_id: str, request_id: str
) -> ReviseOperationV1 | None:
    with _draft_revise_lock(root, draft_id):
        return _read_operation_unlocked(root, draft_id=draft_id, request_id=request_id)
