"""Durable generation request-to-candidate reconciliation for replay recovery."""
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
RECONCILIATION_SCHEMA = "dmb_statblock_generation_request_v1"
_REQUEST_ID_RE = re.compile(r"^[A-Za-z0-9][A-Za-z0-9_.-]{0,127}$")
LOCK_NAME = ".reconciliation.lock"
PENDING_TTL = timedelta(minutes=15)
MAX_RECORDS_PER_DRAFT = 128
ClaimStatus = Literal["pending", "received", "completed", "abandoned"]
ClaimOutcome = Literal[
    "claimed",
    "received",
    "completed",
    "pending_retry",
    "abandoned_retry",
]


class GenerationReconciliationError(ValueError):
    status_code: int = 500

    def __init__(self, message: str, *, status_code: int = 500) -> None:
        super().__init__(message)
        self.status_code = status_code


class GenerationReconciliationRecordV1(BaseModel):
    schema_name: Literal["dmb_statblock_generation_request_v1"] = Field(
        default=RECONCILIATION_SCHEMA, alias="schema"
    )
    draft_id: str
    draft_version: int = Field(ge=1)
    request_id: str
    request_digest: str
    # Exact Server generate body for uncertain-timeout recovery after draft advance.
    request_body: dict[str, Any] | None = None
    status: ClaimStatus
    candidate_id: str | None = None
    candidate_payload: dict[str, Any] | None = None
    created_at: str
    updated_at: str
    claim_expires_at: str | None = None

    model_config = ConfigDict(extra="forbid", populate_by_name=True)


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


def _validate_record(
    record: GenerationReconciliationRecordV1,
    *,
    draft_id: str,
    draft_version: int,
    request_id: str,
) -> GenerationReconciliationRecordV1:
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
            # Ensure the stored body is JSON-serializable for digest computation.
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
        # Digest/body equality is enforced at claim and recovery time as a 409
        # conflict, not as a silent corrupt-record 500 on every read.

    if record.status in {"received", "completed"}:
        if not record.candidate_id:
            raise GenerationReconciliationError(
                "corrupt generation reconciliation record",
                status_code=500,
            )
        try:
            validate_candidate_id(record.candidate_id)
        except ValueError as exc:
            raise GenerationReconciliationError(str(exc), status_code=500) from None
        if record.candidate_payload is None:
            raise GenerationReconciliationError(
                "corrupt generation reconciliation record",
                status_code=500,
            )
        if record.request_body is None:
            raise GenerationReconciliationError(
                "corrupt generation reconciliation record",
                status_code=500,
            )
    elif record.status == "pending":
        if record.candidate_id is not None or record.candidate_payload is not None:
            raise GenerationReconciliationError(
                "corrupt generation reconciliation record",
                status_code=500,
            )
        if not record.claim_expires_at:
            raise GenerationReconciliationError(
                "corrupt generation reconciliation record",
                status_code=500,
            )
        if record.request_body is None:
            raise GenerationReconciliationError(
                "corrupt generation reconciliation record",
                status_code=500,
            )
    elif record.status == "abandoned":
        if (
            record.candidate_id is not None
            or record.candidate_payload is not None
            or record.claim_expires_at is not None
        ):
            raise GenerationReconciliationError(
                "corrupt generation reconciliation record",
                status_code=500,
            )
        # request_body may be retained so the same request_id can recover via
        # Server replay after draft advance; records without a body are pruned.
    return record


def _read_reconciliation_unlocked(
    root: Path,
    *,
    draft_id: str,
    draft_version: int,
    request_id: str,
) -> GenerationReconciliationRecordV1 | None:
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
        record = GenerationReconciliationRecordV1.model_validate(payload)
    except GenerationReconciliationError:
        raise
    except Exception:
        raise GenerationReconciliationError(
            "corrupt generation reconciliation record",
            status_code=500,
        ) from None
    return _validate_record(
        record,
        draft_id=draft_id,
        draft_version=draft_version,
        request_id=request_id,
    )


def _write_record_unlocked(
    root: Path,
    record: GenerationReconciliationRecordV1,
) -> GenerationReconciliationRecordV1:
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


def _list_draft_records_unlocked(
    root: Path, *, draft_id: str
) -> list[GenerationReconciliationRecordV1]:
    directory = _draft_directory(root, draft_id)
    if not directory.is_dir():
        return []
    records: list[GenerationReconciliationRecordV1] = []
    try:
        paths = sorted(directory.glob("v*__*.json"))
    except OSError:
        raise _storage_unavailable() from None
    safe_draft = require_draft_id(draft_id)
    for path in paths:
        draft_version, request_id = _parse_record_filename(path)
        try:
            payload = load_json(path)
            record = GenerationReconciliationRecordV1.model_validate(payload)
        except GenerationReconciliationError:
            raise
        except Exception:
            raise GenerationReconciliationError(
                "corrupt generation reconciliation record",
                status_code=500,
            ) from None
        records.append(
            _validate_record(
                record,
                draft_id=safe_draft,
                draft_version=draft_version,
                request_id=request_id,
            )
        )
    # Abandoned files may temporarily exceed the physical bound; claim prunes them
    # before writing a new active record. Fail closed only when active records alone
    # exceed the bound (corruption / runaway pending).
    if _active_record_count(records) > MAX_RECORDS_PER_DRAFT:
        raise GenerationReconciliationError(
            "generation reconciliation storage bound exceeded",
            status_code=500,
        )
    return records


def _is_pending_expired(record: GenerationReconciliationRecordV1, *, now: datetime) -> bool:
    if record.status != "pending" or not record.claim_expires_at:
        return False
    return _parse_iso(record.claim_expires_at) <= now


def _delete_record_unlocked(
    root: Path,
    *,
    draft_id: str,
    draft_version: int,
    request_id: str,
) -> None:
    path = _record_path(
        root,
        draft_id=draft_id,
        draft_version=draft_version,
        request_id=request_id,
    )
    try:
        if path.is_file():
            path.unlink()
    except OSError:
        raise _storage_unavailable() from None


def _abandon_record_unlocked(
    root: Path, record: GenerationReconciliationRecordV1
) -> GenerationReconciliationRecordV1:
    """Expire a pending claim while retaining the exact request body for replay.

    Abandoned files do not reserve candidate capacity and are never pruned to
    make room for new request IDs — the stored body is the only local material
    that can recover an unresolved Server operation after draft advance.
    """
    abandoned = record.model_copy(
        update={
            "status": "abandoned",
            "candidate_id": None,
            "candidate_payload": None,
            "claim_expires_at": None,
            "updated_at": _utc_now_iso(),
            # request_body + request_digest retained for Server replay recovery
        }
    )
    return _write_record_unlocked(root, abandoned)


def _active_record_count(records: list[GenerationReconciliationRecordV1]) -> int:
    return sum(1 for record in records if record.status != "abandoned")


def _capacity_usage(
    records: list[GenerationReconciliationRecordV1],
    *,
    ref_candidate_ids: set[str],
) -> int:
    """Count reserved + unbound slots without double-counting existing refs.

    Pending claims always reserve one slot (no locator yet). Received and
    completed claims reserve a slot only when their candidate_id is not already
    present in draft refs — otherwise a finalize failure would inflate 63 real
    refs to 64 and block the final slot. Abandoned records never reserve capacity.
    """
    used = len(ref_candidate_ids)
    for record in records:
        if record.status == "pending":
            used += 1
        elif record.status in {"received", "completed"}:
            if (
                record.candidate_id is not None
                and record.candidate_id not in ref_candidate_ids
            ):
                used += 1
    return used


def read_reconciliation(
    root: Path,
    *,
    draft_id: str,
    draft_version: int,
    request_id: str,
) -> GenerationReconciliationRecordV1 | None:
    with _reconciliation_lock(root):
        return _read_reconciliation_unlocked(
            root,
            draft_id=draft_id,
            draft_version=draft_version,
            request_id=request_id,
        )


def claim_generation_request(
    root: Path,
    *,
    draft_id: str,
    draft_version: int,
    request_id: str,
    request_digest: str,
    request_body: dict[str, Any],
    ref_candidate_ids: set[str],
) -> tuple[ClaimOutcome, GenerationReconciliationRecordV1]:
    """Atomically claim capacity and observe prior durable outcomes.

    Reservations are pending/received claims plus completed claims whose
    candidate is not yet present in draft refs — preventing the 63+2 race.

    DungeonMindServer now provides durable generate idempotency (PR23): the
    same request_id may safely re-call generate after an uncertain timeout and
    recover the original candidate. Expired/abandoned local claims retain the
    exact request body so recovery works even after the draft advances. Abandoned
    recovery material is never pruned for new writes; the physical bound applies
    only to active (pending/received/completed) records.
    """
    body_digest = request_digest_for_body(request_body)
    if body_digest != request_digest:
        raise GenerationReconciliationError(
            "generation request body digest mismatch",
            status_code=500,
        )

    with _reconciliation_lock(root):
        now = _utc_now()
        records = _list_draft_records_unlocked(root, draft_id=draft_id)
        for record in records:
            if _is_pending_expired(record, now=now):
                _abandon_record_unlocked(root, record)

        records = _list_draft_records_unlocked(root, draft_id=draft_id)
        existing = _read_reconciliation_unlocked(
            root,
            draft_id=draft_id,
            draft_version=draft_version,
            request_id=request_id,
        )
        if existing is not None:
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
            if existing.status == "completed":
                return "completed", existing
            if existing.status == "received":
                return "received", existing
            if existing.status == "pending":
                # Live local claim: allow Server idempotent probe / recovery.
                return "pending_retry", existing
            if existing.status == "abandoned":
                # Reclaim without capacity gate — recovery must reach Server even
                # when draft refs are full; attach may still return partial_ref.
                now_iso = _utc_now_iso()
                expires_at = (now + PENDING_TTL).isoformat().replace("+00:00", "Z")
                record = existing.model_copy(
                    update={
                        "status": "pending",
                        "candidate_id": None,
                        "candidate_payload": None,
                        "claim_expires_at": expires_at,
                        "updated_at": now_iso,
                        "request_digest": request_digest,
                        "request_body": request_body,
                    }
                )
                _write_record_unlocked(root, record)
                return "abandoned_retry", record

        usage = _capacity_usage(records, ref_candidate_ids=ref_candidate_ids)
        if usage >= MAX_CANDIDATE_REFS:
            raise GenerationReconciliationError(
                "candidate_refs limit exceeded",
                status_code=422,
            )

        # Physical bound applies to active records only. Abandoned recovery
        # material is retained and never deleted to free slots for new IDs.
        if existing is None and _active_record_count(records) >= MAX_RECORDS_PER_DRAFT:
            raise GenerationReconciliationError(
                "generation reconciliation storage bound exceeded",
                status_code=500,
            )

        now_iso = _utc_now_iso()
        expires_at = (now + PENDING_TTL).isoformat().replace("+00:00", "Z")
        try:
            record = GenerationReconciliationRecordV1(
                draft_id=require_draft_id(draft_id),
                draft_version=draft_version,
                request_id=validate_request_id(request_id),
                request_digest=request_digest,
                request_body=request_body,
                status="pending",
                candidate_id=None,
                candidate_payload=None,
                created_at=now_iso,
                updated_at=now_iso,
                claim_expires_at=expires_at,
            )
        except GenerationReconciliationError:
            raise
        except ValueError as exc:
            raise GenerationReconciliationError(str(exc), status_code=422) from None
        _write_record_unlocked(root, record)
        return "claimed", record


def record_generation_received(
    root: Path,
    *,
    draft_id: str,
    draft_version: int,
    request_id: str,
    request_digest: str,
    candidate: GeneratedStatblockCandidateV1,
) -> GenerationReconciliationRecordV1:
    """Durably bind the candidate locator immediately after downstream success."""
    with _reconciliation_lock(root):
        existing = _read_reconciliation_unlocked(
            root,
            draft_id=draft_id,
            draft_version=draft_version,
            request_id=request_id,
        )
        if existing is None:
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
        if existing.status in {"received", "completed"}:
            if (
                existing.candidate_id != candidate_id
                or existing.candidate_payload != payload
            ):
                raise GenerationReconciliationError(
                    "generation reconciliation conflict",
                    status_code=409,
                )
            return existing
        if existing.status not in {"pending", "abandoned"}:
            raise GenerationReconciliationError(
                "generation reconciliation conflict",
                status_code=409,
            )
        record = existing.model_copy(
            update={
                "status": "received",
                "candidate_id": candidate_id,
                "candidate_payload": payload,
                "claim_expires_at": None,
                "updated_at": _utc_now_iso(),
            }
        )
        return _write_record_unlocked(root, record)


def finalize_generation_request(
    root: Path,
    *,
    draft_id: str,
    draft_version: int,
    request_id: str,
    request_digest: str,
    candidate_id: str,
) -> GenerationReconciliationRecordV1:
    """Mark a received generation fully reconciled."""
    with _reconciliation_lock(root):
        existing = _read_reconciliation_unlocked(
            root,
            draft_id=draft_id,
            draft_version=draft_version,
            request_id=request_id,
        )
        if existing is None:
            raise GenerationReconciliationError(
                "missing generation reconciliation claim",
                status_code=500,
            )
        if existing.request_digest != request_digest:
            raise GenerationReconciliationError(
                "generation reconciliation conflict",
                status_code=409,
            )
        safe_candidate_id = validate_candidate_id(candidate_id)
        if existing.status == "completed":
            if existing.candidate_id != safe_candidate_id:
                raise GenerationReconciliationError(
                    "generation reconciliation conflict",
                    status_code=409,
                )
            return existing
        if existing.status != "received":
            raise GenerationReconciliationError(
                "generation reconciliation not received",
                status_code=500,
            )
        if existing.candidate_id != safe_candidate_id:
            raise GenerationReconciliationError(
                "generation reconciliation conflict",
                status_code=409,
            )
        record = existing.model_copy(
            update={
                "status": "completed",
                "updated_at": _utc_now_iso(),
            }
        )
        return _write_record_unlocked(root, record)


def load_received_candidate(
    record: GenerationReconciliationRecordV1,
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
) -> GenerationReconciliationRecordV1:
    """Compatibility helper for completed-record recovery paths."""
    return finalize_generation_request(
        root,
        draft_id=draft_id,
        draft_version=draft_version,
        request_id=request_id,
        request_digest=request_digest,
        candidate_id=candidate_id,
    )
