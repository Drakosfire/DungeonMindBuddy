"""Durable Threat/statblock publication-operation journal (SBW09a)."""
from __future__ import annotations

import fcntl
from collections.abc import Callable
from contextlib import contextmanager
from datetime import UTC, datetime
from pathlib import Path
from typing import Iterator, Literal

from apps.live_control_server.models.threat_statblock_publication import (
    PUBLICATION_OPERATION_SCHEMA,
    ThreatPublicationSourceSnapshotV1,
    ThreatStatblockPublicationOperationV1,
    source_snapshot_digest_for,
    validate_publication_operation_id,
)
from apps.live_control_server.models.threat_draft import require_draft_id
from src.live_play.live_store import load_json, write_json

DEFAULT_PUBLICATION_REL = "out/threat_statblock_publication_operations"
MAX_PUBLICATION_OPERATION_RECORDS_PER_DRAFT = 32
LOCK_NAME = ".publication.lock"

_ACTIVE_PRE_PUBLICATION = frozenset(
    {
        "awaiting_identity_resolution",
        "identity_resolved",
        "prepared",
        "confirming",
        "committed_unverified",
    }
)

ClaimPublicationOutcome = Literal[
    "claimed",
    "resume",
    "input_conflict",
    "publication_busy",
    "publication_history_full",
    "version_mismatch",
]


class ThreatStatblockPublicationStoreError(ValueError):
    status_code: int = 500

    def __init__(self, message: str, *, status_code: int = 500) -> None:
        super().__init__(message)
        self.status_code = status_code


def publication_root(repo_root: Path) -> Path:
    return repo_root / DEFAULT_PUBLICATION_REL


def _utc_now_iso() -> str:
    return datetime.now(UTC).isoformat().replace("+00:00", "Z")


def _storage_unavailable() -> ThreatStatblockPublicationStoreError:
    return ThreatStatblockPublicationStoreError(
        "publication storage unavailable",
        status_code=500,
    )


def _corrupt_record(message: str = "corrupt publication operation record") -> ThreatStatblockPublicationStoreError:
    return ThreatStatblockPublicationStoreError(message, status_code=500)


def _invalid_request(message: str) -> ThreatStatblockPublicationStoreError:
    return ThreatStatblockPublicationStoreError(message, status_code=422)


def _validated_draft_id(draft_id: str) -> str:
    try:
        return require_draft_id(draft_id)
    except ValueError as exc:
        raise _invalid_request(str(exc)) from exc


def _validated_operation_id(operation_id: str) -> str:
    try:
        return validate_publication_operation_id(operation_id)
    except ValueError as exc:
        raise _invalid_request(str(exc)) from exc


def _draft_directory(root: Path, draft_id: str) -> Path:
    safe = _validated_draft_id(draft_id)
    store_root = publication_root(root).resolve()
    directory = (store_root / safe).resolve()
    if directory.parent != store_root:
        raise _corrupt_record()
    return directory


def _record_path(root: Path, *, draft_id: str, operation_id: str) -> Path:
    safe_draft = _validated_draft_id(draft_id)
    safe_op = _validated_operation_id(operation_id)
    directory = _draft_directory(root, safe_draft)
    path = (directory / f"{safe_op}.json").resolve()
    if path.parent != directory:
        raise _corrupt_record()
    return path


@contextmanager
def _draft_publication_lock(root: Path, draft_id: str) -> Iterator[None]:
    """Draft-scoped exclusive lock for publication journal mutations.

    Lock order when both stores are needed: acquire this lock before the
    ThreatDraft store lock. Do not call DungeonMindServer while holding this lock.
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
    except ThreatStatblockPublicationStoreError:
        raise
    except OSError:
        raise _storage_unavailable() from None


def _write_operation_unlocked(
    root: Path, record: ThreatStatblockPublicationOperationV1
) -> ThreatStatblockPublicationOperationV1:
    draft_id = record.source_snapshot.source_draft_id
    path = _record_path(root, draft_id=draft_id, operation_id=record.operation_id)
    try:
        path.parent.mkdir(parents=True, exist_ok=True)
        write_json(path, record.model_dump(mode="json", by_alias=True))
    except OSError:
        raise _storage_unavailable() from None
    return record


def _read_operation_unlocked(
    root: Path, *, draft_id: str, operation_id: str
) -> ThreatStatblockPublicationOperationV1 | None:
    path = _record_path(root, draft_id=draft_id, operation_id=operation_id)
    try:
        if not path.is_file():
            return None
        payload = load_json(path)
    except OSError:
        raise _storage_unavailable() from None
    except Exception:
        raise _corrupt_record() from None
    if payload.get("schema") != PUBLICATION_OPERATION_SCHEMA:
        raise _corrupt_record()
    try:
        record = ThreatStatblockPublicationOperationV1.model_validate(payload)
    except Exception as exc:
        raise _corrupt_record() from exc
    safe_draft = _validated_draft_id(draft_id)
    safe_op = _validated_operation_id(operation_id)
    if record.source_snapshot.source_draft_id != safe_draft:
        raise _corrupt_record()
    if record.operation_id != safe_op:
        raise _corrupt_record()
    recomputed = source_snapshot_digest_for(record.source_snapshot)
    if recomputed != record.source_snapshot_digest:
        raise _corrupt_record()
    return record


def _list_operations_unlocked(
    root: Path, *, draft_id: str
) -> list[ThreatStatblockPublicationOperationV1]:
    directory = _draft_directory(root, draft_id)
    if not directory.is_dir():
        return []
    records: list[ThreatStatblockPublicationOperationV1] = []
    try:
        paths = sorted(p for p in directory.glob("*.json"))
    except OSError:
        raise _storage_unavailable() from None
    safe_draft = _validated_draft_id(draft_id)
    for path in paths:
        op_id = path.stem
        try:
            _validated_operation_id(op_id)
        except ThreatStatblockPublicationStoreError as exc:
            if exc.status_code == 422:
                raise _corrupt_record() from exc
            raise
        record = _read_operation_unlocked(root, draft_id=safe_draft, operation_id=op_id)
        if record is not None:
            records.append(record)
    if len(records) > MAX_PUBLICATION_OPERATION_RECORDS_PER_DRAFT:
        raise ThreatStatblockPublicationStoreError(
            "publication operation storage bound exceeded",
            status_code=500,
        )
    return records


def _has_active_pre_publication_slot(records: list[ThreatStatblockPublicationOperationV1]) -> bool:
    return any(r.authority_state in _ACTIVE_PRE_PUBLICATION for r in records)


def _validate_builder_result(
    record: ThreatStatblockPublicationOperationV1,
    *,
    draft_id: str,
    operation_id: str,
    claim_request_digest: str,
) -> None:
    if record.operation_id != operation_id:
        raise _corrupt_record("publication operation builder identity mismatch")
    if record.source_snapshot.source_draft_id != draft_id:
        raise _corrupt_record("publication operation builder identity mismatch")
    if record.claim_request_digest != claim_request_digest:
        raise _corrupt_record("publication operation builder digest mismatch")


def claim_publication_operation(
    root: Path,
    *,
    draft_id: str,
    operation_id: str,
    claim_request_digest: str,
    build_new_record: Callable[[], ThreatStatblockPublicationOperationV1] | None = None,
) -> tuple[ClaimPublicationOutcome, ThreatStatblockPublicationOperationV1 | None]:
    """Resolve existing operation or claim a new slot under the publication lock.

    When no operation exists, ``build_new_record`` is invoked only after the lock is
    acquired and slot/history checks pass. The builder may read ThreatDraft and the
    Kernel World Graph head under the documented lock order; it must not call
    DungeonMindServer.
    """
    safe_draft = _validated_draft_id(draft_id)
    safe_op = _validated_operation_id(operation_id)

    with _draft_publication_lock(root, safe_draft):
        existing = _read_operation_unlocked(root, draft_id=safe_draft, operation_id=safe_op)
        if existing is not None:
            if existing.claim_request_digest != claim_request_digest:
                return "input_conflict", existing
            return "resume", existing

        records = _list_operations_unlocked(root, draft_id=safe_draft)
        if len(records) >= MAX_PUBLICATION_OPERATION_RECORDS_PER_DRAFT:
            return "publication_history_full", None
        if _has_active_pre_publication_slot(records):
            return "publication_busy", None

        if build_new_record is None:
            raise ThreatStatblockPublicationStoreError(
                "missing publication operation claim builder",
                status_code=500,
            )

        new_record = build_new_record()
        _validate_builder_result(
            new_record,
            draft_id=safe_draft,
            operation_id=safe_op,
            claim_request_digest=claim_request_digest,
        )
        _write_operation_unlocked(root, new_record)
        return "claimed", new_record


def atomic_claim_publication_operation(
    root: Path,
    *,
    draft_id: str,
    operation_id: str,
    claim_request_digest: str,
    new_record: ThreatStatblockPublicationOperationV1 | None = None,
    build_new_record: Callable[[], ThreatStatblockPublicationOperationV1] | None = None,
) -> tuple[ClaimPublicationOutcome, ThreatStatblockPublicationOperationV1 | None]:
    """Backward-compatible claim entrypoint for tests with a prebuilt record."""
    if new_record is not None:
        if build_new_record is not None:
            raise ThreatStatblockPublicationStoreError(
                "cannot supply both new_record and build_new_record",
                status_code=500,
            )

        def _prebuilt() -> ThreatStatblockPublicationOperationV1:
            return new_record

        build_new_record = _prebuilt

    return claim_publication_operation(
        root,
        draft_id=draft_id,
        operation_id=operation_id,
        claim_request_digest=claim_request_digest,
        build_new_record=build_new_record,
    )


def get_publication_operation(
    root: Path, *, draft_id: str, operation_id: str
) -> ThreatStatblockPublicationOperationV1 | None:
    with _draft_publication_lock(root, draft_id):
        return _read_operation_unlocked(root, draft_id=draft_id, operation_id=operation_id)


def cas_transition_publication_stale(
    root: Path,
    *,
    draft_id: str,
    operation_id: str,
    expected_operation_version: int,
    last_observed_head_revision_id: str,
) -> ThreatStatblockPublicationOperationV1:
    with _draft_publication_lock(root, draft_id):
        existing = _read_operation_unlocked(root, draft_id=draft_id, operation_id=operation_id)
        if existing is None:
            raise ThreatStatblockPublicationStoreError(
                "publication operation not found",
                status_code=404,
            )
        if existing.authority_state == "cancelled":
            return existing
        if existing.authority_state == "stale":
            return existing
        if existing.authority_state != "awaiting_identity_resolution":
            raise ThreatStatblockPublicationStoreError(
                "publication operation not stale-transitionable",
                status_code=409,
            )
        if existing.operation_version != expected_operation_version:
            raise ThreatStatblockPublicationStoreError(
                "publication operation version mismatch",
                status_code=409,
            )
        updated = existing.model_copy(
            update={
                "authority_state": "stale",
                "operation_version": existing.operation_version + 1,
                "last_observed_head_revision_id": last_observed_head_revision_id,
                "updated_at": _utc_now_iso(),
            }
        )
        return _write_operation_unlocked(root, updated)


def cas_transition_publication_cancelled(
    root: Path,
    *,
    draft_id: str,
    operation_id: str,
    expected_operation_version: int,
) -> ThreatStatblockPublicationOperationV1:
    with _draft_publication_lock(root, draft_id):
        existing = _read_operation_unlocked(root, draft_id=draft_id, operation_id=operation_id)
        if existing is None:
            raise ThreatStatblockPublicationStoreError(
                "publication operation not found",
                status_code=404,
            )
        if existing.authority_state == "cancelled":
            return existing
        if existing.authority_state == "stale":
            return existing
        if existing.authority_state != "awaiting_identity_resolution":
            raise ThreatStatblockPublicationStoreError(
                "publication operation not cancellable",
                status_code=409,
            )
        if existing.operation_version != expected_operation_version:
            raise ThreatStatblockPublicationStoreError(
                "publication operation version mismatch",
                status_code=409,
            )
        updated = existing.model_copy(
            update={
                "authority_state": "cancelled",
                "operation_version": existing.operation_version + 1,
                "updated_at": _utc_now_iso(),
            }
        )
        return _write_operation_unlocked(root, updated)


def build_new_publication_operation(
    *,
    operation_id: str,
    claim_request_digest: str,
    source_snapshot: ThreatPublicationSourceSnapshotV1,
    expected_parent_revision_id: str,
    last_observed_head_revision_id: str,
) -> ThreatStatblockPublicationOperationV1:
    now = _utc_now_iso()
    digest = source_snapshot_digest_for(source_snapshot)
    return ThreatStatblockPublicationOperationV1(
        operation_id=validate_publication_operation_id(operation_id),
        operation_version=1,
        claim_request_digest=claim_request_digest,
        source_snapshot=source_snapshot,
        source_snapshot_digest=digest,
        world_id=source_snapshot.world_id,
        campaign_id=source_snapshot.campaign_id,
        expected_parent_revision_id=expected_parent_revision_id,
        last_observed_head_revision_id=last_observed_head_revision_id,
        authority_state="awaiting_identity_resolution",
        phase_artifacts=[],
        created_at=now,
        updated_at=now,
    )
