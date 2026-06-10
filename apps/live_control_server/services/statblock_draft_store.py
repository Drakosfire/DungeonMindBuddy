from __future__ import annotations

import re
from collections.abc import Callable
from datetime import UTC, datetime
from pathlib import Path
from typing import Literal

from pydantic import BaseModel, Field

from src.live_play.live_store import load_json, write_json
from src.statblocks.lifecycle_artifact import StatblockDraftArtifact

DRAFTS_DIR_NAME = "statblock_drafts"
SCHEMA_VERSION_RECORD = "dmb_statblock_draft_record_v1"
_SAFE_ARTIFACT_ID = re.compile(r"^[A-Za-z0-9_.:-]+$")


class StatblockDraftStoreError(ValueError):
    status_code = 422


class UnsafeArtifactIdError(StatblockDraftStoreError):
    pass


class StatblockDraftNotFoundError(FileNotFoundError):
    status_code = 404


class StoredStatblockDraftRecord(BaseModel):
    schema_version: Literal["dmb_statblock_draft_record_v1"] = SCHEMA_VERSION_RECORD
    artifact_id: str
    title: str
    campaign_id: str
    session: int
    stored_at: str
    updated_at: str
    storage_path: str
    corpus_relpath: str | None = None
    corpus_display_path: str | None = None
    corpus_written_at: str | None = None
    corpus_preview_token: str | None = None
    retrieval_status: str | None = None
    retrieval_manifest_path: str | None = None
    retrieval_activated_at: str | None = None
    retrieval_verified_at: str | None = None
    retrieval_query: str | None = None
    retrieval_evidence_path: str | None = None
    retrieval_evidence_score: float | None = None
    artifact: StatblockDraftArtifact


class StoredStatblockDraftSummary(BaseModel):
    artifact_id: str
    title: str
    draft_id: str
    review_status: str
    lifecycle_state: str
    storage_status: str
    corpus_status: str
    stored_at: str
    updated_at: str
    storage_path: str
    corpus_relpath: str | None = None
    corpus_display_path: str | None = None
    corpus_written_at: str | None = None
    corpus_preview_token: str | None = None
    retrieval_status: str | None = None
    retrieval_manifest_path: str | None = None
    retrieval_activated_at: str | None = None
    retrieval_verified_at: str | None = None
    retrieval_query: str | None = None
    retrieval_evidence_path: str | None = None
    retrieval_evidence_score: float | None = None


class StoreStatblockDraftRequest(BaseModel):
    artifact: StatblockDraftArtifact
    source: Literal["workbench"] = "workbench"


class StoreStatblockDraftResponse(BaseModel):
    schema_version: Literal["dmb_statblock_draft_store_v1"] = (
        "dmb_statblock_draft_store_v1"
    )
    record: StoredStatblockDraftRecord
    diagnostics: list[str] = Field(default_factory=list)


class ListStatblockDraftsResponse(BaseModel):
    schema_version: Literal["dmb_statblock_draft_list_v1"] = (
        "dmb_statblock_draft_list_v1"
    )
    drafts: list[StoredStatblockDraftSummary]


class ReadStatblockDraftResponse(BaseModel):
    schema_version: Literal["dmb_statblock_draft_read_v1"] = (
        "dmb_statblock_draft_read_v1"
    )
    record: StoredStatblockDraftRecord


def _utc_now() -> datetime:
    return datetime.now(UTC)


def _isoformat_z(value: datetime) -> str:
    return value.astimezone(UTC).isoformat().replace("+00:00", "Z")


def _validate_artifact_id(artifact_id: str) -> str:
    if not artifact_id or not _SAFE_ARTIFACT_ID.fullmatch(artifact_id):
        raise UnsafeArtifactIdError("unsafe statblock draft artifact_id")
    if ".." in artifact_id or artifact_id.startswith(("~", ".")):
        raise UnsafeArtifactIdError("unsafe statblock draft artifact_id")
    parsed = Path(artifact_id)
    if parsed.is_absolute() or parsed.name != artifact_id:
        raise UnsafeArtifactIdError("unsafe statblock draft artifact_id")
    if "://" in artifact_id:
        raise UnsafeArtifactIdError("unsafe statblock draft artifact_id")
    return artifact_id


def _drafts_dir(base: Path) -> Path:
    return base / DRAFTS_DIR_NAME


def _draft_path(base: Path, artifact_id: str) -> Path:
    safe_id = _validate_artifact_id(artifact_id)
    return _drafts_dir(base) / f"{safe_id}.json"


def _relative_storage_path(artifact_id: str) -> str:
    safe_id = _validate_artifact_id(artifact_id)
    return f"{DRAFTS_DIR_NAME}/{safe_id}.json"


def _summary_from_record(record: StoredStatblockDraftRecord) -> StoredStatblockDraftSummary:
    artifact = record.artifact
    return StoredStatblockDraftSummary(
        artifact_id=record.artifact_id,
        title=record.title,
        draft_id=artifact.draft_id,
        review_status=artifact.review_status,
        lifecycle_state=artifact.lifecycle_state,
        storage_status=artifact.storage_status,
        corpus_status=artifact.corpus_status,
        stored_at=record.stored_at,
        updated_at=record.updated_at,
        storage_path=record.storage_path,
        corpus_relpath=record.corpus_relpath,
        corpus_display_path=record.corpus_display_path,
        corpus_written_at=record.corpus_written_at,
        corpus_preview_token=record.corpus_preview_token,
        retrieval_status=record.retrieval_status,
        retrieval_manifest_path=record.retrieval_manifest_path,
        retrieval_activated_at=record.retrieval_activated_at,
        retrieval_verified_at=record.retrieval_verified_at,
        retrieval_query=record.retrieval_query,
        retrieval_evidence_path=record.retrieval_evidence_path,
        retrieval_evidence_score=record.retrieval_evidence_score,
    )


def store_statblock_draft(
    *,
    base: Path,
    campaign_id: str,
    session: int,
    artifact: StatblockDraftArtifact,
    now: Callable[[], datetime] | None = None,
) -> StoredStatblockDraftRecord:
    artifact_id = _validate_artifact_id(artifact.artifact_id)
    clock = now or _utc_now
    timestamp = _isoformat_z(clock())
    path = _draft_path(base, artifact_id)
    existing_stored_at = timestamp
    if path.is_file():
        existing = StoredStatblockDraftRecord.model_validate(load_json(path))
        existing_stored_at = existing.stored_at

    stored_artifact = artifact.model_copy(
        update={
            "lifecycle_state": "stored_artifact",
            "storage_status": "stored_draft",
            "corpus_status": "not_promoted",
            "updated_at": timestamp,
        }
    )
    record = StoredStatblockDraftRecord(
        artifact_id=artifact_id,
        title=stored_artifact.title,
        campaign_id=campaign_id,
        session=session,
        stored_at=existing_stored_at,
        updated_at=timestamp,
        storage_path=_relative_storage_path(artifact_id),
        artifact=stored_artifact,
    )
    path.parent.mkdir(parents=True, exist_ok=True)
    write_json(path, record.model_dump(mode="json"))
    return record


def list_statblock_drafts(*, base: Path) -> list[StoredStatblockDraftSummary]:
    drafts_dir = _drafts_dir(base)
    if not drafts_dir.is_dir():
        return []
    summaries: list[StoredStatblockDraftSummary] = []
    for path in drafts_dir.glob("*.json"):
        record = StoredStatblockDraftRecord.model_validate(load_json(path))
        summaries.append(_summary_from_record(record))
    summaries.sort(key=lambda item: (item.title.lower(), item.artifact_id))
    summaries.sort(key=lambda item: item.updated_at, reverse=True)
    return summaries


def read_statblock_draft(*, base: Path, artifact_id: str) -> StoredStatblockDraftRecord:
    path = _draft_path(base, artifact_id)
    if not path.is_file():
        raise StatblockDraftNotFoundError("statblock draft not found")
    return StoredStatblockDraftRecord.model_validate(load_json(path))


def update_statblock_draft_record(*, base: Path, record: StoredStatblockDraftRecord) -> StoredStatblockDraftRecord:
    artifact_id = _validate_artifact_id(record.artifact_id)
    path = _draft_path(base, artifact_id)
    if not path.is_file():
        raise StatblockDraftNotFoundError("statblock draft not found")
    write_json(path, record.model_dump(mode="json"))
    return record
