"""Operation-authority journal for candidate-generation durability.

Success claim: for every request that may have reached DungeonMindServer, Buddy
retains a valid recovery path, an independently durable candidate locator, or
authoritative proof the operation is terminal. Storage pressure never destroys
unresolved evidence.
"""
from __future__ import annotations

import fcntl
import hashlib
import json
import re
from contextlib import contextmanager
from datetime import UTC, datetime, timedelta
from pathlib import Path
from typing import Any, Iterator, Literal

from pydantic import BaseModel, ConfigDict, Field

from apps.live_control_server.integrations.dungeonmind_statblocks.config import (
    validate_candidate_id,
)
from apps.live_control_server.integrations.dungeonmind_statblocks.generated import (
    GeneratedStatblockCandidateV1,
)
from apps.live_control_server.models.threat_draft import (
    MAX_CANDIDATE_REFS,
    require_draft_id,
)
from src.live_play.live_store import load_json, write_json

DEFAULT_RECONCILIATION_REL = "out/statblock_generation_requests"
OPERATION_SCHEMA = "dmb_statblock_generation_operation_v2"
TOMBSTONE_SCHEMA = "dmb_statblock_generation_tombstone_v1"
LEGACY_SCHEMA = "dmb_statblock_generation_request_v1"
_REQUEST_ID_RE = re.compile(r"^[A-Za-z0-9][A-Za-z0-9_.-]{0,127}$")
LOCK_NAME = ".reconciliation.lock"
CLAIM_TTL = timedelta(minutes=15)
MAX_OPERATION_RECORDS_PER_DRAFT = 128
MAX_TOMBSTONES_PER_DRAFT = 512
# Compatibility aliases used by older tests / callers.
MAX_RECORDS_PER_DRAFT = MAX_OPERATION_RECORDS_PER_DRAFT
MAX_ABANDONED_RECORDS_PER_DRAFT = 0  # removed cohort; admission uses operation bound
PENDING_TTL = CLAIM_TTL

OperationStatus = Literal[
    "dispatched_unknown",
    "candidate_received",
    "reconciled",
    "terminal_failure",
    "terminal_expired",
]
TombstoneOutcome = Literal["reconciled", "terminal_failure", "terminal_expired"]
CompactionProof = Literal["draft_ref_lineage", "operation_terminal"]
MaterializationState = Literal["missing", "stored", "attached", "failed"]

# Public ErrorEnvelope codes from DungeonMindServer's durable generate-operation
# record (PR23). Authentication, transport, and pre-route validation are NOT
# in this set and must never create operation_terminal tombstones.
SERVER_OPERATION_TERMINAL_FAILURE_CODES = frozenset(
    {
        "provider_refused",
        "provider_incomplete",
        "provider_timeout",
        "rate_limited",
        "provider_unavailable",
        "validation_failed",
        "ruleset_mismatch",
        "source_digest_mismatch",
        "idempotency_conflict",
    }
)
SERVER_OPERATION_TERMINAL_EXPIRED_CODES = frozenset(
    {
        "candidate_expired",
        "generation_replay_expired",
    }
)


def server_operation_terminal_outcome(
    error_code: str | None,
) -> Literal["terminal_failure", "terminal_expired"] | None:
    """Map a Server error code to terminal authority, or None if not durable proof."""
    if error_code in SERVER_OPERATION_TERMINAL_EXPIRED_CODES:
        return "terminal_expired"
    if error_code in SERVER_OPERATION_TERMINAL_FAILURE_CODES:
        return "terminal_failure"
    return None
ClaimOutcome = Literal[
    "claimed",
    "dispatched_retry",
    "candidate_received",
    "reconciled",
    "terminal_failure",
    "terminal_expired",
    "tombstone_reconciled",
    "tombstone_terminal_failure",
    "tombstone_terminal_expired",
]


class GenerationReconciliationError(ValueError):
    status_code: int = 500

    def __init__(self, message: str, *, status_code: int = 500) -> None:
        super().__init__(message)
        self.status_code = status_code


class MaterializationV2(BaseModel):
    cache: Literal["missing", "stored", "failed"] = "missing"
    draft_ref: Literal["missing", "attached", "failed"] = "missing"

    model_config = ConfigDict(extra="forbid")


class GenerationOperationV2(BaseModel):
    schema_name: Literal["dmb_statblock_generation_operation_v2"] = Field(
        default=OPERATION_SCHEMA, alias="schema"
    )
    draft_id: str
    draft_version: int = Field(ge=1)
    request_id: str
    request_digest: str
    request_body: dict[str, Any] | None = None
    status: OperationStatus
    candidate_id: str | None = None
    candidate_payload: dict[str, Any] | None = None
    terminal_code: str | None = None
    terminal_message: str | None = None
    failure_category: str | None = None
    http_status: int | None = None
    materialization: MaterializationV2 = Field(default_factory=MaterializationV2)
    created_at: str
    updated_at: str
    claim_expires_at: str | None = None

    model_config = ConfigDict(extra="forbid", populate_by_name=True)


class GenerationTombstoneV1(BaseModel):
    schema_name: Literal["dmb_statblock_generation_tombstone_v1"] = Field(
        default=TOMBSTONE_SCHEMA, alias="schema"
    )
    draft_id: str
    draft_version: int = Field(ge=1)
    request_id: str
    request_digest: str
    outcome: TombstoneOutcome
    candidate_id: str | None = None
    terminal_code: str | None = None
    terminal_message: str | None = None
    failure_category: str | None = None
    http_status: int | None = None
    compaction_proof: CompactionProof
    compacted_at: str

    model_config = ConfigDict(extra="forbid", populate_by_name=True)


# Legacy alias for tests that still construct v1-shaped fixtures via helpers.
GenerationReconciliationRecordV1 = GenerationOperationV2
ClaimStatus = OperationStatus


def _utc_now() -> datetime:
    return datetime.now(UTC)


def _utc_now_iso() -> str:
    return _utc_now().isoformat().replace("+00:00", "Z")


def _parse_iso(value: str) -> datetime:
    cleaned = value.strip()
    if cleaned.endswith("Z"):
        cleaned = cleaned[:-1] + "+00:00"
    parsed = datetime.fromisoformat(cleaned)
    if parsed.tzinfo is None:
        parsed = parsed.replace(tzinfo=UTC)
    return parsed.astimezone(UTC)


def validate_request_id(value: str) -> str:
    cleaned = value.strip()
    if not _REQUEST_ID_RE.fullmatch(cleaned):
        raise GenerationReconciliationError("invalid request_id", status_code=422)
    return cleaned


def request_digest_for_body(body: dict[str, Any]) -> str:
    canonical = json.dumps(body, sort_keys=True, separators=(",", ":"), ensure_ascii=False)
    return "sha256:" + hashlib.sha256(canonical.encode("utf-8")).hexdigest()


def reconciliation_root(repo_root: Path) -> Path:
    return repo_root / DEFAULT_RECONCILIATION_REL


def _storage_unavailable() -> GenerationReconciliationError:
    return GenerationReconciliationError(
        "generation reconciliation storage unavailable",
        status_code=500,
    )


@contextmanager
def _reconciliation_lock(root: Path) -> Iterator[None]:
    """Exclusive lock for generation journal mutations.

    Lock order when ThreatDraft admission is required for a *new* generation
    claim: acquire the ThreatDraft store lock first, then this lock
    (``threat_draft_store._store_lock`` → ``_reconciliation_lock``).

    Do not acquire the ThreatDraft store lock while holding this lock (avoids
    deadlock with new-generation admission). Acceptance journal locking is
    independent; acceptance uses acceptance journal → ThreatDraft store and
    never nests this lock.
    """
    lock_path = reconciliation_root(root) / LOCK_NAME
    try:
        lock_path.parent.mkdir(parents=True, exist_ok=True)
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
    except GenerationReconciliationError:
        raise
    except OSError:
        raise _storage_unavailable() from None


def _record_path(root: Path, *, draft_id: str, draft_version: int, request_id: str) -> Path:
    try:
        safe_draft = require_draft_id(draft_id)
        safe_request = validate_request_id(request_id)
    except ValueError as exc:
        raise GenerationReconciliationError(str(exc), status_code=422) from None
    if draft_version < 1:
        raise GenerationReconciliationError("invalid draft_version", status_code=422)
    store_root = reconciliation_root(root).resolve()
    directory = (store_root / safe_draft).resolve()
    if directory.parent != store_root:
        raise GenerationReconciliationError(
            "reconciliation path escape",
            status_code=500,
        )
    path = (directory / f"v{draft_version}__{safe_request}.json").resolve()
    if path.parent != directory:
        raise GenerationReconciliationError(
            "reconciliation path escape",
            status_code=500,
        )
    return path


def _draft_directory(root: Path, draft_id: str) -> Path:
    try:
        safe_draft = require_draft_id(draft_id)
    except ValueError as exc:
        raise GenerationReconciliationError(str(exc), status_code=422) from None
    store_root = reconciliation_root(root).resolve()
    directory = (store_root / safe_draft).resolve()
    if directory.parent != store_root:
        raise GenerationReconciliationError(
            "reconciliation path escape",
            status_code=500,
        )
    return directory


def _legacy_status_to_v2(
    status: str,
    *,
    candidate_id: str | None,
    ref_candidate_ids: set[str] | None,
) -> tuple[OperationStatus, MaterializationV2]:
    refs = ref_candidate_ids or set()
    if status == "pending":
        return "dispatched_unknown", MaterializationV2()
    if status == "abandoned":
        return "dispatched_unknown", MaterializationV2()
    if status == "received":
        mat = MaterializationV2()
        if candidate_id and candidate_id in refs:
            return "reconciled", MaterializationV2(cache="missing", draft_ref="attached")
        return "candidate_received", mat
    if status == "completed":
        if candidate_id and candidate_id in refs:
            return "reconciled", MaterializationV2(cache="stored", draft_ref="attached")
        return "candidate_received", MaterializationV2(cache="stored", draft_ref="missing")
    raise GenerationReconciliationError(
        "corrupt generation reconciliation record",
        status_code=500,
    )


def _upgrade_legacy_payload(
    payload: dict[str, Any],
    *,
    ref_candidate_ids: set[str] | None = None,
) -> dict[str, Any]:
    status = payload.get("status")
    if not isinstance(status, str):
        raise GenerationReconciliationError(
            "corrupt generation reconciliation record",
            status_code=500,
        )
    candidate_id = payload.get("candidate_id")
    if candidate_id is not None and not isinstance(candidate_id, str):
        raise GenerationReconciliationError(
            "corrupt generation reconciliation record",
            status_code=500,
        )
    v2_status, materialization = _legacy_status_to_v2(
        status,
        candidate_id=candidate_id,
        ref_candidate_ids=ref_candidate_ids,
    )
    return {
        "schema": OPERATION_SCHEMA,
        "draft_id": payload.get("draft_id"),
        "draft_version": payload.get("draft_version"),
        "request_id": payload.get("request_id"),
        "request_digest": payload.get("request_digest"),
        "request_body": payload.get("request_body"),
        "status": v2_status,
        "candidate_id": candidate_id,
        "candidate_payload": payload.get("candidate_payload"),
        "terminal_code": None,
        "terminal_message": None,
        "failure_category": None,
        "http_status": None,
        "materialization": materialization.model_dump(mode="json"),
        "created_at": payload.get("created_at"),
        "updated_at": payload.get("updated_at"),
        "claim_expires_at": payload.get("claim_expires_at")
        if v2_status == "dispatched_unknown"
        else None,
    }


def _parse_stored_payload(
    payload: dict[str, Any],
    *,
    ref_candidate_ids: set[str] | None = None,
) -> GenerationOperationV2 | GenerationTombstoneV1:
    schema = payload.get("schema")
    if schema == TOMBSTONE_SCHEMA:
        return GenerationTombstoneV1.model_validate(payload)
    if schema == OPERATION_SCHEMA:
        return GenerationOperationV2.model_validate(payload)
    if schema == LEGACY_SCHEMA or schema is None and "status" in payload:
        upgraded = _upgrade_legacy_payload(payload, ref_candidate_ids=ref_candidate_ids)
        return GenerationOperationV2.model_validate(upgraded)
    raise GenerationReconciliationError(
        "corrupt generation reconciliation record",
        status_code=500,
    )


def _validate_operation(
    record: GenerationOperationV2,
    *,
    draft_id: str,
    draft_version: int,
    request_id: str,
) -> GenerationOperationV2:
    if (
        record.draft_id != require_draft_id(draft_id)
        or record.draft_version != draft_version
        or record.request_id != validate_request_id(request_id)
    ):
        raise GenerationReconciliationError(
            "generation reconciliation identity mismatch",
            status_code=500,
        )
    if record.request_body is not None:
        try:
            json.dumps(
                record.request_body,
                sort_keys=True,
                separators=(",", ":"),
                ensure_ascii=False,
            )
        except (TypeError, ValueError):
            raise GenerationReconciliationError(
                "corrupt generation reconciliation record",
                status_code=500,
            ) from None

    if record.status == "dispatched_unknown":
        if record.candidate_id is not None or record.candidate_payload is not None:
            raise GenerationReconciliationError(
                "corrupt generation reconciliation record",
                status_code=500,
            )
        if (
            record.terminal_code is not None
            or record.terminal_message is not None
            or record.failure_category is not None
            or record.http_status is not None
        ):
            raise GenerationReconciliationError(
                "corrupt generation reconciliation record",
                status_code=500,
            )
        if record.request_body is None or not record.claim_expires_at:
            raise GenerationReconciliationError(
                "corrupt generation reconciliation record",
                status_code=500,
            )
    elif record.status in {"candidate_received", "reconciled"}:
        if not record.candidate_id or record.candidate_payload is None:
            raise GenerationReconciliationError(
                "corrupt generation reconciliation record",
                status_code=500,
            )
        try:
            validate_candidate_id(record.candidate_id)
        except ValueError as exc:
            raise GenerationReconciliationError(str(exc), status_code=500) from None
        if record.request_body is None:
            raise GenerationReconciliationError(
                "corrupt generation reconciliation record",
                status_code=500,
            )
        if (
            record.terminal_code is not None
            or record.terminal_message is not None
            or record.failure_category is not None
            or record.http_status is not None
        ):
            raise GenerationReconciliationError(
                "corrupt generation reconciliation record",
                status_code=500,
            )
        if record.status == "reconciled" and record.materialization.draft_ref != "attached":
            raise GenerationReconciliationError(
                "corrupt generation reconciliation record",
                status_code=500,
            )
    elif record.status in {"terminal_failure", "terminal_expired"}:
        if record.candidate_payload is not None:
            raise GenerationReconciliationError(
                "corrupt generation reconciliation record",
                status_code=500,
            )
        if (
            not record.terminal_code
            or not record.terminal_message
            or not record.failure_category
            or record.http_status is None
        ):
            raise GenerationReconciliationError(
                "corrupt generation reconciliation record",
                status_code=500,
            )
        expected = server_operation_terminal_outcome(record.terminal_code)
        if expected != record.status:
            raise GenerationReconciliationError(
                "corrupt generation reconciliation record",
                status_code=500,
            )
        if record.request_body is None:
            raise GenerationReconciliationError(
                "corrupt generation reconciliation record",
                status_code=500,
            )
    return record


def _validate_tombstone(
    tombstone: GenerationTombstoneV1,
    *,
    draft_id: str,
    draft_version: int,
    request_id: str,
) -> GenerationTombstoneV1:
    if (
        tombstone.draft_id != require_draft_id(draft_id)
        or tombstone.draft_version != draft_version
        or tombstone.request_id != validate_request_id(request_id)
    ):
        raise GenerationReconciliationError(
            "generation reconciliation identity mismatch",
            status_code=500,
        )
    if tombstone.outcome == "reconciled":
        if not tombstone.candidate_id:
            raise GenerationReconciliationError(
                "corrupt generation reconciliation tombstone",
                status_code=500,
            )
        try:
            validate_candidate_id(tombstone.candidate_id)
        except ValueError as exc:
            raise GenerationReconciliationError(str(exc), status_code=500) from None
        if tombstone.compaction_proof != "draft_ref_lineage":
            raise GenerationReconciliationError(
                "corrupt generation reconciliation tombstone",
                status_code=500,
            )
    elif tombstone.outcome in {"terminal_failure", "terminal_expired"}:
        if (
            not tombstone.terminal_code
            or not tombstone.terminal_message
            or not tombstone.failure_category
            or tombstone.http_status is None
        ):
            raise GenerationReconciliationError(
                "corrupt generation reconciliation tombstone",
                status_code=500,
            )
        expected = server_operation_terminal_outcome(tombstone.terminal_code)
        if expected != tombstone.outcome:
            raise GenerationReconciliationError(
                "corrupt generation reconciliation tombstone",
                status_code=500,
            )
        if tombstone.compaction_proof != "operation_terminal":
            raise GenerationReconciliationError(
                "corrupt generation reconciliation tombstone",
                status_code=500,
            )
    return tombstone


def _write_operation_unlocked(
    root: Path, record: GenerationOperationV2
) -> GenerationOperationV2:
    path = _record_path(
        root,
        draft_id=record.draft_id,
        draft_version=record.draft_version,
        request_id=record.request_id,
    )
    try:
        path.parent.mkdir(parents=True, exist_ok=True)
        write_json(path, record.model_dump(mode="json", by_alias=True))
    except OSError:
        raise _storage_unavailable() from None
    return record


def _write_tombstone_unlocked(
    root: Path, tombstone: GenerationTombstoneV1
) -> GenerationTombstoneV1:
    path = _record_path(
        root,
        draft_id=tombstone.draft_id,
        draft_version=tombstone.draft_version,
        request_id=tombstone.request_id,
    )
    try:
        path.parent.mkdir(parents=True, exist_ok=True)
        write_json(path, tombstone.model_dump(mode="json", by_alias=True))
    except OSError:
        raise _storage_unavailable() from None
    return tombstone


def _parse_record_filename(path: Path) -> tuple[int, str]:
    stem = path.stem
    if not stem.startswith("v") or "__" not in stem[1:]:
        raise GenerationReconciliationError(
            "corrupt generation reconciliation record path",
            status_code=500,
        )
    version_part, request_id = stem.split("__", 1)
    try:
        draft_version = int(version_part[1:])
    except ValueError:
        raise GenerationReconciliationError(
            "corrupt generation reconciliation record path",
            status_code=500,
        ) from None
    if draft_version < 1 or not request_id:
        raise GenerationReconciliationError(
            "corrupt generation reconciliation record path",
            status_code=500,
        )
    return draft_version, request_id


def _read_entry_unlocked(
    root: Path,
    *,
    draft_id: str,
    draft_version: int,
    request_id: str,
    ref_candidate_ids: set[str] | None = None,
    persist_upgrade: bool = False,
) -> GenerationOperationV2 | GenerationTombstoneV1 | None:
    path = _record_path(
        root,
        draft_id=draft_id,
        draft_version=draft_version,
        request_id=request_id,
    )
    try:
        if not path.is_file():
            return None
        payload = load_json(path)
        entry = _parse_stored_payload(payload, ref_candidate_ids=ref_candidate_ids)
    except GenerationReconciliationError:
        raise
    except Exception:
        raise GenerationReconciliationError(
            "corrupt generation reconciliation record",
            status_code=500,
        ) from None
    if isinstance(entry, GenerationTombstoneV1):
        return _validate_tombstone(
            entry,
            draft_id=draft_id,
            draft_version=draft_version,
            request_id=request_id,
        )
    validated = _validate_operation(
        entry,
        draft_id=draft_id,
        draft_version=draft_version,
        request_id=request_id,
    )
    if persist_upgrade and payload.get("schema") == LEGACY_SCHEMA:
        _write_operation_unlocked(root, validated)
    return validated


def _list_draft_entries_unlocked(
    root: Path,
    *,
    draft_id: str,
    ref_candidate_ids: set[str] | None = None,
) -> list[GenerationOperationV2 | GenerationTombstoneV1]:
    directory = _draft_directory(root, draft_id)
    if not directory.is_dir():
        return []
    entries: list[GenerationOperationV2 | GenerationTombstoneV1] = []
    try:
        paths = sorted(directory.glob("v*__*.json"))
    except OSError:
        raise _storage_unavailable() from None
    safe_draft = require_draft_id(draft_id)
    for path in paths:
        draft_version, request_id = _parse_record_filename(path)
        entry = _read_entry_unlocked(
            root,
            draft_id=safe_draft,
            draft_version=draft_version,
            request_id=request_id,
            ref_candidate_ids=ref_candidate_ids,
        )
        if entry is None:
            continue
        entries.append(entry)
    operations = [e for e in entries if isinstance(e, GenerationOperationV2)]
    tombstones = [e for e in entries if isinstance(e, GenerationTombstoneV1)]
    if len(operations) > MAX_OPERATION_RECORDS_PER_DRAFT:
        raise GenerationReconciliationError(
            "generation reconciliation storage bound exceeded",
            status_code=500,
        )
    if len(tombstones) > MAX_TOMBSTONES_PER_DRAFT:
        raise GenerationReconciliationError(
            "generation reconciliation tombstone bound exceeded",
            status_code=500,
        )
    return entries


def _operation_count(entries: list[GenerationOperationV2 | GenerationTombstoneV1]) -> int:
    return sum(1 for entry in entries if isinstance(entry, GenerationOperationV2))


def _tombstone_count(entries: list[GenerationOperationV2 | GenerationTombstoneV1]) -> int:
    return sum(1 for entry in entries if isinstance(entry, GenerationTombstoneV1))


def _capacity_usage(
    entries: list[GenerationOperationV2 | GenerationTombstoneV1],
    *,
    ref_candidate_ids: set[str],
) -> int:
    """Count reserved + unbound slots without double-counting existing refs."""
    used = len(ref_candidate_ids)
    for entry in entries:
        if not isinstance(entry, GenerationOperationV2):
            continue
        if entry.status == "dispatched_unknown":
            used += 1
        elif entry.status in {"candidate_received", "reconciled"}:
            if (
                entry.candidate_id is not None
                and entry.candidate_id not in ref_candidate_ids
            ):
                used += 1
    return used


def count_generation_capacity_usage(
    root: Path,
    *,
    draft_id: str,
    ref_candidate_ids: set[str],
) -> int:
    """Public helper: attached refs plus unbound SBW03 generation reservations."""
    with _reconciliation_lock(root):
        entries = _list_draft_entries_unlocked(
            root,
            draft_id=draft_id,
            ref_candidate_ids=ref_candidate_ids,
        )
        return _capacity_usage(entries, ref_candidate_ids=ref_candidate_ids)


def _draft_has_ref_lineage(
    *,
    ref_entries: list[tuple[str, str]] | None,
    candidate_id: str,
    request_id: str,
) -> bool:
    """True only when draft refs contain exact (candidate_id, request_id) lineage."""
    if not ref_entries:
        return False
    return any(
        cid == candidate_id and rid == request_id for cid, rid in ref_entries
    )


def _is_compactable(
    record: GenerationOperationV2,
    *,
    ref_entries: list[tuple[str, str]] | None,
) -> bool:
    """compactable(op, durable_evidence) — omitted evidence never means trusted."""
    if record.status == "reconciled":
        if record.materialization.draft_ref != "attached" or not record.candidate_id:
            return False
        if ref_entries is None:
            return False
        return _draft_has_ref_lineage(
            ref_entries=ref_entries,
            candidate_id=record.candidate_id,
            request_id=record.request_id,
        )
    if record.status in {"terminal_failure", "terminal_expired"}:
        return bool(
            server_operation_terminal_outcome(record.terminal_code) == record.status
            and record.terminal_message
            and record.failure_category
            and record.http_status is not None
        )
    return False


def _compact_operation_unlocked(
    root: Path,
    record: GenerationOperationV2,
    *,
    ref_entries: list[tuple[str, str]] | None,
) -> GenerationTombstoneV1:
    if not _is_compactable(record, ref_entries=ref_entries):
        raise GenerationReconciliationError(
            "generation operation not compactable",
            status_code=500,
        )
    entries = _list_draft_entries_unlocked(root, draft_id=record.draft_id)
    if _tombstone_count(entries) >= MAX_TOMBSTONES_PER_DRAFT:
        raise GenerationReconciliationError(
            "generation reconciliation tombstone bound exceeded",
            status_code=500,
        )
    if record.status == "reconciled":
        outcome: TombstoneOutcome = "reconciled"
        proof: CompactionProof = "draft_ref_lineage"
    elif record.status == "terminal_failure":
        outcome = "terminal_failure"
        proof = "operation_terminal"
    elif record.status == "terminal_expired":
        outcome = "terminal_expired"
        proof = "operation_terminal"
    else:
        raise GenerationReconciliationError(
            "generation operation not compactable",
            status_code=500,
        )
    tombstone = GenerationTombstoneV1(
        draft_id=record.draft_id,
        draft_version=record.draft_version,
        request_id=record.request_id,
        request_digest=record.request_digest,
        outcome=outcome,
        candidate_id=record.candidate_id if outcome == "reconciled" else None,
        terminal_code=record.terminal_code,
        terminal_message=record.terminal_message,
        failure_category=record.failure_category,
        http_status=record.http_status,
        compaction_proof=proof,
        compacted_at=_utc_now_iso(),
    )
    return _write_tombstone_unlocked(
        root,
        _validate_tombstone(
            tombstone,
            draft_id=record.draft_id,
            draft_version=record.draft_version,
            request_id=record.request_id,
        ),
    )


def _try_compact_unlocked(
    root: Path,
    record: GenerationOperationV2,
    *,
    ref_entries: list[tuple[str, str]] | None,
) -> GenerationOperationV2 | GenerationTombstoneV1:
    """Compact when eligible and within tombstone capacity; otherwise keep full record."""
    if not _is_compactable(record, ref_entries=ref_entries):
        return record
    entries = _list_draft_entries_unlocked(root, draft_id=record.draft_id)
    if _tombstone_count(entries) >= MAX_TOMBSTONES_PER_DRAFT:
        return record
    return _compact_operation_unlocked(root, record, ref_entries=ref_entries)


def _compact_eligible_for_draft_unlocked(
    root: Path,
    *,
    draft_id: str,
    ref_candidate_ids: set[str],
    ref_entries: list[tuple[str, str]] | None,
) -> list[GenerationOperationV2 | GenerationTombstoneV1]:
    entries = _list_draft_entries_unlocked(
        root, draft_id=draft_id, ref_candidate_ids=ref_candidate_ids
    )
    tombstone_n = _tombstone_count(entries)
    for entry in list(entries):
        if not isinstance(entry, GenerationOperationV2):
            continue
        if not _is_compactable(entry, ref_entries=ref_entries):
            continue
        if tombstone_n >= MAX_TOMBSTONES_PER_DRAFT:
            break
        _compact_operation_unlocked(root, entry, ref_entries=ref_entries)
        tombstone_n += 1
    return _list_draft_entries_unlocked(
        root, draft_id=draft_id, ref_candidate_ids=ref_candidate_ids
    )


def _refresh_claim_ttl(record: GenerationOperationV2, *, now: datetime) -> GenerationOperationV2:
    expires_at = (now + CLAIM_TTL).isoformat().replace("+00:00", "Z")
    return record.model_copy(
        update={
            "claim_expires_at": expires_at,
            "updated_at": _utc_now_iso(),
        }
    )


def read_reconciliation(
    root: Path,
    *,
    draft_id: str,
    draft_version: int,
    request_id: str,
    ref_candidate_ids: set[str] | None = None,
) -> GenerationOperationV2 | GenerationTombstoneV1 | None:
    with _reconciliation_lock(root):
        return _read_entry_unlocked(
            root,
            draft_id=draft_id,
            draft_version=draft_version,
            request_id=request_id,
            ref_candidate_ids=ref_candidate_ids,
            persist_upgrade=True,
        )


def _claim_generation_request_unlocked(
    root: Path,
    *,
    draft_id: str,
    draft_version: int,
    request_id: str,
    request_digest: str,
    request_body: dict[str, Any],
    ref_candidate_ids: set[str],
    ref_entries: list[tuple[str, str]] | None = None,
) -> tuple[ClaimOutcome, GenerationOperationV2 | GenerationTombstoneV1]:
    """Claim under an already-held ``_reconciliation_lock``.

    Brand-new generation admission must hold the ThreatDraft store lock as well
    (lock order: store → reconciliation). Callers that already re-read a same-key
    durable entry under those locks may invoke this helper with the *stored*
    request body and digest to classify replay/recovery without applying
    new-generation workflow gates. Genuinely empty keys must still verify
    committed membership, version, and ``workflow_state`` under the store lock
    before constructing a new body and claiming.
    """
    body_digest = request_digest_for_body(request_body)
    if body_digest != request_digest:
        raise GenerationReconciliationError(
            "generation request body digest mismatch",
            status_code=500,
        )

    now = _utc_now()
    # Opportunistic compaction requires independent lineage proof when provided.
    # Never invent empty request_ids — that would fake lineage evidence.
    entries = _compact_eligible_for_draft_unlocked(
        root,
        draft_id=draft_id,
        ref_candidate_ids=ref_candidate_ids,
        ref_entries=ref_entries,
    )

    existing = _read_entry_unlocked(
        root,
        draft_id=draft_id,
        draft_version=draft_version,
        request_id=request_id,
        ref_candidate_ids=ref_candidate_ids,
        persist_upgrade=True,
    )
    if existing is not None:
        if isinstance(existing, GenerationTombstoneV1):
            if existing.request_digest != request_digest:
                raise GenerationReconciliationError(
                    "generation reconciliation conflict",
                    status_code=409,
                )
            if existing.outcome == "reconciled":
                return "tombstone_reconciled", existing
            if existing.outcome == "terminal_failure":
                return "tombstone_terminal_failure", existing
            return "tombstone_terminal_expired", existing

        if existing.request_digest != request_digest:
            raise GenerationReconciliationError(
                "generation reconciliation conflict",
                status_code=409,
            )
        if existing.request_body != request_body:
            raise GenerationReconciliationError(
                "generation reconciliation conflict",
                status_code=409,
            )
        if existing.status == "reconciled":
            return "reconciled", existing
        if existing.status == "candidate_received":
            return "candidate_received", existing
        if existing.status == "terminal_failure":
            return "terminal_failure", existing
        if existing.status == "terminal_expired":
            return "terminal_expired", existing
        if existing.status == "dispatched_unknown":
            refreshed = _refresh_claim_ttl(existing, now=now)
            _write_operation_unlocked(root, refreshed)
            return "dispatched_retry", refreshed

    usage = _capacity_usage(entries, ref_candidate_ids=ref_candidate_ids)
    if usage >= MAX_CANDIDATE_REFS:
        raise GenerationReconciliationError(
            "candidate_refs limit exceeded",
            status_code=422,
        )

    if _operation_count(entries) >= MAX_OPERATION_RECORDS_PER_DRAFT:
        raise GenerationReconciliationError(
            "generation reconciliation storage bound exceeded",
            status_code=500,
        )
    if _tombstone_count(entries) >= MAX_TOMBSTONES_PER_DRAFT:
        raise GenerationReconciliationError(
            "generation reconciliation tombstone bound exceeded",
            status_code=500,
        )

    now_iso = _utc_now_iso()
    expires_at = (now + CLAIM_TTL).isoformat().replace("+00:00", "Z")
    try:
        record = GenerationOperationV2(
            draft_id=require_draft_id(draft_id),
            draft_version=draft_version,
            request_id=validate_request_id(request_id),
            request_digest=request_digest,
            request_body=request_body,
            status="dispatched_unknown",
            candidate_id=None,
            candidate_payload=None,
            materialization=MaterializationV2(),
            created_at=now_iso,
            updated_at=now_iso,
            claim_expires_at=expires_at,
        )
    except GenerationReconciliationError:
        raise
    except ValueError as exc:
        raise GenerationReconciliationError(str(exc), status_code=422) from None
    _write_operation_unlocked(root, record)
    return "claimed", record


def claim_generation_request(
    root: Path,
    *,
    draft_id: str,
    draft_version: int,
    request_id: str,
    request_digest: str,
    request_body: dict[str, Any],
    ref_candidate_ids: set[str],
    ref_entries: list[tuple[str, str]] | None = None,
) -> tuple[ClaimOutcome, GenerationOperationV2 | GenerationTombstoneV1]:
    """Atomically claim capacity and observe prior durable outcomes.

    For brand-new generation against a ThreatDraft that may race acceptance
    Phase 1, prefer ``statblock_candidate_generation``'s store-locked admission
    path so workflow/version checks and this claim share one admission boundary.
    """
    with _reconciliation_lock(root):
        return _claim_generation_request_unlocked(
            root,
            draft_id=draft_id,
            draft_version=draft_version,
            request_id=request_id,
            request_digest=request_digest,
            request_body=request_body,
            ref_candidate_ids=ref_candidate_ids,
            ref_entries=ref_entries,
        )


def record_candidate_received(
    root: Path,
    *,
    draft_id: str,
    draft_version: int,
    request_id: str,
    request_digest: str,
    candidate: GeneratedStatblockCandidateV1,
) -> GenerationOperationV2:
    """Durably bind candidate locator immediately after downstream success."""
    with _reconciliation_lock(root):
        existing = _read_entry_unlocked(
            root,
            draft_id=draft_id,
            draft_version=draft_version,
            request_id=request_id,
            persist_upgrade=True,
        )
        if existing is None or isinstance(existing, GenerationTombstoneV1):
            raise GenerationReconciliationError(
                "missing generation reconciliation claim",
                status_code=500,
            )
        if existing.request_digest != request_digest:
            raise GenerationReconciliationError(
                "generation reconciliation conflict",
                status_code=409,
            )
        payload = candidate.model_dump(mode="json")
        candidate_id = validate_candidate_id(candidate.candidate_id)
        if existing.status in {"candidate_received", "reconciled"}:
            if (
                existing.candidate_id != candidate_id
                or existing.candidate_payload != payload
            ):
                raise GenerationReconciliationError(
                    "generation reconciliation conflict",
                    status_code=409,
                )
            return existing
        if existing.status != "dispatched_unknown":
            raise GenerationReconciliationError(
                "generation reconciliation conflict",
                status_code=409,
            )
        record = existing.model_copy(
            update={
                "status": "candidate_received",
                "candidate_id": candidate_id,
                "candidate_payload": payload,
                "claim_expires_at": None,
                "updated_at": _utc_now_iso(),
                "materialization": MaterializationV2(),
            }
        )
        return _write_operation_unlocked(root, record)


# Compatibility name used by orchestrator / tests during transition.
def record_generation_received(
    root: Path,
    *,
    draft_id: str,
    draft_version: int,
    request_id: str,
    request_digest: str,
    candidate: GeneratedStatblockCandidateV1,
    ref_candidate_ids: set[str] | None = None,
) -> GenerationOperationV2:
    del ref_candidate_ids  # authority bind no longer depends on eviction
    return record_candidate_received(
        root,
        draft_id=draft_id,
        draft_version=draft_version,
        request_id=request_id,
        request_digest=request_digest,
        candidate=candidate,
    )


def update_materialization(
    root: Path,
    *,
    draft_id: str,
    draft_version: int,
    request_id: str,
    request_digest: str,
    cache: Literal["missing", "stored", "failed"] | None = None,
    draft_ref: Literal["missing", "attached", "failed"] | None = None,
    ref_entries: list[tuple[str, str]] | None = None,
    compact_if_eligible: bool = True,
) -> GenerationOperationV2 | GenerationTombstoneV1:
    """Update cache/ref materialization without demoting authority."""
    with _reconciliation_lock(root):
        existing = _read_entry_unlocked(
            root,
            draft_id=draft_id,
            draft_version=draft_version,
            request_id=request_id,
            persist_upgrade=True,
        )
        if existing is None:
            raise GenerationReconciliationError(
                "missing generation reconciliation claim",
                status_code=500,
            )
        if isinstance(existing, GenerationTombstoneV1):
            return existing
        if existing.request_digest != request_digest:
            raise GenerationReconciliationError(
                "generation reconciliation conflict",
                status_code=409,
            )
        if existing.status not in {"candidate_received", "reconciled"}:
            raise GenerationReconciliationError(
                "generation reconciliation conflict",
                status_code=409,
            )
        mat = existing.materialization.model_copy()
        if cache is not None:
            mat.cache = cache
        if draft_ref is not None:
            mat.draft_ref = draft_ref
        status = existing.status
        if mat.draft_ref == "attached" and existing.candidate_id:
            status = "reconciled"
        record = existing.model_copy(
            update={
                "status": status,
                "materialization": mat,
                "updated_at": _utc_now_iso(),
            }
        )
        written = _write_operation_unlocked(root, record)
        if compact_if_eligible:
            return _try_compact_unlocked(root, written, ref_entries=ref_entries)
        return written


def finalize_generation_request(
    root: Path,
    *,
    draft_id: str,
    draft_version: int,
    request_id: str,
    request_digest: str,
    candidate_id: str,
    ref_entries: list[tuple[str, str]] | None = None,
) -> GenerationOperationV2 | GenerationTombstoneV1:
    """Mark draft_ref attached (reconciled) after successful ref append.

    Compaction requires explicit ref_entries lineage proof — omitted evidence
    never means trusted.
    """
    safe_candidate_id = validate_candidate_id(candidate_id)
    with _reconciliation_lock(root):
        existing = _read_entry_unlocked(
            root,
            draft_id=draft_id,
            draft_version=draft_version,
            request_id=request_id,
            persist_upgrade=True,
        )
        if existing is None:
            raise GenerationReconciliationError(
                "missing generation reconciliation claim",
                status_code=500,
            )
        if isinstance(existing, GenerationTombstoneV1):
            if existing.outcome != "reconciled" or existing.candidate_id != safe_candidate_id:
                raise GenerationReconciliationError(
                    "generation reconciliation conflict",
                    status_code=409,
                )
            return existing
        if existing.request_digest != request_digest:
            raise GenerationReconciliationError(
                "generation reconciliation conflict",
                status_code=409,
            )
        if existing.candidate_id != safe_candidate_id:
            raise GenerationReconciliationError(
                "generation reconciliation conflict",
                status_code=409,
            )
        if existing.status not in {"candidate_received", "reconciled"}:
            raise GenerationReconciliationError(
                "generation reconciliation not received",
                status_code=500,
            )
        mat = existing.materialization.model_copy(update={"draft_ref": "attached"})
        record = existing.model_copy(
            update={
                "status": "reconciled",
                "materialization": mat,
                "updated_at": _utc_now_iso(),
            }
        )
        written = _write_operation_unlocked(root, record)
        return _try_compact_unlocked(root, written, ref_entries=ref_entries)


def record_terminal(
    root: Path,
    *,
    draft_id: str,
    draft_version: int,
    request_id: str,
    request_digest: str,
    outcome: Literal["terminal_failure", "terminal_expired"],
    terminal_code: str,
    terminal_message: str,
    failure_category: str,
    http_status: int,
    candidate_id: str | None = None,
    compact: bool = True,
) -> GenerationOperationV2 | GenerationTombstoneV1:
    """Record an authoritative terminal Server outcome with replay semantics."""
    if not failure_category or http_status < 100:
        raise GenerationReconciliationError(
            "terminal outcome requires failure_category and http_status",
            status_code=500,
        )
    if server_operation_terminal_outcome(terminal_code) != outcome:
        raise GenerationReconciliationError(
            "terminal outcome requires a Server durable operation error code",
            status_code=500,
        )
    with _reconciliation_lock(root):
        existing = _read_entry_unlocked(
            root,
            draft_id=draft_id,
            draft_version=draft_version,
            request_id=request_id,
            persist_upgrade=True,
        )
        if existing is None or isinstance(existing, GenerationTombstoneV1):
            raise GenerationReconciliationError(
                "missing generation reconciliation claim",
                status_code=500,
            )
        if existing.request_digest != request_digest:
            raise GenerationReconciliationError(
                "generation reconciliation conflict",
                status_code=409,
            )
        if existing.status in {"candidate_received", "reconciled"} and outcome == "terminal_failure":
            raise GenerationReconciliationError(
                "generation reconciliation conflict",
                status_code=409,
            )
        if existing.status == "reconciled" and outcome == "terminal_expired":
            raise GenerationReconciliationError(
                "generation reconciliation conflict",
                status_code=409,
            )
        if existing.status == outcome:
            if (
                existing.terminal_code != terminal_code
                or existing.terminal_message != terminal_message
                or existing.failure_category != failure_category
                or existing.http_status != http_status
            ):
                raise GenerationReconciliationError(
                    "generation reconciliation conflict",
                    status_code=409,
                )
            return existing
        safe_candidate = (
            validate_candidate_id(candidate_id)
            if candidate_id
            else (existing.candidate_id if outcome == "terminal_expired" else None)
        )
        record = existing.model_copy(
            update={
                "status": outcome,
                "candidate_id": safe_candidate if outcome == "terminal_expired" else None,
                "candidate_payload": None,
                "claim_expires_at": None,
                "terminal_code": terminal_code,
                "terminal_message": terminal_message,
                "failure_category": failure_category,
                "http_status": http_status,
                "updated_at": _utc_now_iso(),
            }
        )
        written = _write_operation_unlocked(root, record)
        if compact:
            # Terminal compaction uses operation_terminal proof (Server durable code).
            return _try_compact_unlocked(root, written, ref_entries=None)
        return written


def record_terminal_failure(
    root: Path,
    *,
    draft_id: str,
    draft_version: int,
    request_id: str,
    request_digest: str,
    terminal_code: str,
    terminal_message: str,
    failure_category: str,
    http_status: int,
    compact: bool = True,
) -> GenerationOperationV2 | GenerationTombstoneV1:
    return record_terminal(
        root,
        draft_id=draft_id,
        draft_version=draft_version,
        request_id=request_id,
        request_digest=request_digest,
        outcome="terminal_failure",
        terminal_code=terminal_code,
        terminal_message=terminal_message,
        failure_category=failure_category,
        http_status=http_status,
        compact=compact,
    )


def record_terminal_expired(
    root: Path,
    *,
    draft_id: str,
    draft_version: int,
    request_id: str,
    request_digest: str,
    terminal_code: str = "candidate_expired",
    terminal_message: str = "candidate expired",
    failure_category: str = "downstream_expired",
    http_status: int = 410,
    candidate_id: str | None = None,
    compact: bool = True,
) -> GenerationOperationV2 | GenerationTombstoneV1:
    return record_terminal(
        root,
        draft_id=draft_id,
        draft_version=draft_version,
        request_id=request_id,
        request_digest=request_digest,
        outcome="terminal_expired",
        terminal_code=terminal_code,
        terminal_message=terminal_message,
        failure_category=failure_category,
        http_status=http_status,
        candidate_id=candidate_id,
        compact=compact,
    )


def load_received_candidate(
    record: GenerationOperationV2,
) -> GeneratedStatblockCandidateV1:
    if record.candidate_payload is None:
        raise GenerationReconciliationError(
            "corrupt generation reconciliation record",
            status_code=500,
        )
    try:
        candidate = GeneratedStatblockCandidateV1.model_validate(record.candidate_payload)
    except Exception:
        raise GenerationReconciliationError(
            "corrupt generation reconciliation candidate payload",
            status_code=500,
        ) from None
    if candidate.candidate_id != record.candidate_id:
        raise GenerationReconciliationError(
            "generation reconciliation identity mismatch",
            status_code=500,
        )
    receipt = candidate.generation_receipt
    if receipt is None or not receipt.request_id:
        raise GenerationReconciliationError(
            "candidate generation_receipt.request_id missing",
            status_code=500,
        )
    if receipt.request_id != record.request_id:
        raise GenerationReconciliationError(
            "candidate generation_receipt.request_id mismatch",
            status_code=500,
        )
    return candidate


def write_reconciliation(
    root: Path,
    *,
    draft_id: str,
    draft_version: int,
    request_id: str,
    request_digest: str,
    candidate_id: str,
) -> GenerationOperationV2 | GenerationTombstoneV1:
    return finalize_generation_request(
        root,
        draft_id=draft_id,
        draft_version=draft_version,
        request_id=request_id,
        request_digest=request_digest,
        candidate_id=candidate_id,
    )


# Test helpers expected by existing suite.
def _list_draft_records_unlocked(
    root: Path, *, draft_id: str
) -> list[GenerationOperationV2]:
    return [
        e
        for e in _list_draft_entries_unlocked(root, draft_id=draft_id)
        if isinstance(e, GenerationOperationV2)
    ]


def _active_record_count(records: list[GenerationOperationV2]) -> int:
    return len(records)


def _abandoned_record_count(records: list[GenerationOperationV2]) -> int:
    # No abandoned cohort in v2; keep helper for transitional tests.
    del records
    return 0
