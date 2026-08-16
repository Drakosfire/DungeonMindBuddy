"""Durable Play Runtime records bound to exact committed Runbook revisions."""

from __future__ import annotations

import re
import uuid
from datetime import UTC, datetime
from pathlib import Path
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, ValidationError, field_validator

from apps.live_control_server.services.registry_file_lock import (
    registry_mutation_lock,
    workspace_document_mutation_lock,
)
from apps.live_control_server.services.workspace_document_registry import (
    WorkspaceDocumentRegistryError,
    get_workspace_document_snapshot_unlocked,
)
from src.live_play.live_store import load_json, write_json

PLAY_RUN_RECORD_SCHEMA = "dmb_play_run_record_v1"
PLAY_RUNS_LIST_SCHEMA = "dmb_play_runs_list_v1"
PLAY_RUNS_REL = "out/runtime/play/runs"
_SHA256_RE = re.compile(r"^[0-9a-f]{64}$")


class PlayRunRegistryError(ValueError):
    """Fail-closed error for durable Play Run operations."""

    status_code: int = 500

    def __init__(self, message: str, *, status_code: int = 500) -> None:
        super().__init__(message)
        self.status_code = status_code


def _canonical_uuid(value: str, *, field_name: str) -> str:
    cleaned = value.strip()
    try:
        parsed = uuid.UUID(cleaned)
    except (AttributeError, ValueError) as exc:
        raise ValueError(f"{field_name} must be a canonical UUID") from exc
    canonical = str(parsed)
    if cleaned != canonical:
        raise ValueError(f"{field_name} must be a canonical UUID")
    return canonical


def _canonical_sha256(value: str, *, field_name: str) -> str:
    cleaned = value.strip()
    if not _SHA256_RE.fullmatch(cleaned):
        raise ValueError(f"{field_name} must be 64 lowercase hex characters")
    return cleaned


def _parse_utc_iso(value: str) -> datetime:
    cleaned = value.strip()
    if not cleaned.endswith("Z"):
        raise ValueError("timestamp must be an ISO-8601 UTC value ending in Z")
    try:
        parsed = datetime.fromisoformat(cleaned[:-1] + "+00:00")
    except ValueError as exc:
        raise ValueError("timestamp must be an ISO-8601 UTC value") from exc
    if parsed.utcoffset() != UTC.utcoffset(parsed):
        raise ValueError("timestamp must be UTC")
    return parsed


def _utc_iso(value: str) -> str:
    cleaned = value.strip()
    _parse_utc_iso(cleaned)
    return cleaned


class CreatePlayRunRequest(BaseModel):
    model_config = ConfigDict(extra="forbid", strict=True)

    playable_artifact_id: str
    expected_playable_revision: int = Field(gt=0)
    expected_playable_content_sha256: str

    @field_validator("playable_artifact_id")
    @classmethod
    def _validate_playable_artifact_id(cls, value: str) -> str:
        return _canonical_uuid(value, field_name="playable_artifact_id")

    @field_validator("expected_playable_content_sha256")
    @classmethod
    def _validate_expected_sha(cls, value: str) -> str:
        return _canonical_sha256(
            value,
            field_name="expected_playable_content_sha256",
        )


class PlayRunRecord(BaseModel):
    model_config = ConfigDict(extra="forbid", strict=True)

    schema_version: Literal["dmb_play_run_record_v1"] = PLAY_RUN_RECORD_SCHEMA
    run_id: str
    campaign_id: str
    playable_artifact_id: str
    playable_revision: int = Field(gt=0)
    playable_content_sha256: str
    run_revision: int = Field(default=1, gt=0)
    created_at: str
    updated_at: str

    @field_validator("run_id")
    @classmethod
    def _validate_run_id(cls, value: str) -> str:
        return _canonical_uuid(value, field_name="run_id")

    @field_validator("playable_artifact_id")
    @classmethod
    def _validate_playable_artifact_id(cls, value: str) -> str:
        return _canonical_uuid(value, field_name="playable_artifact_id")

    @field_validator("playable_content_sha256")
    @classmethod
    def _validate_playable_sha(cls, value: str) -> str:
        return _canonical_sha256(value, field_name="playable_content_sha256")

    @field_validator("campaign_id")
    @classmethod
    def _validate_campaign_id(cls, value: str) -> str:
        if not value.strip():
            raise ValueError("campaign_id must be non-empty")
        return value

    @field_validator("created_at", "updated_at")
    @classmethod
    def _validate_timestamp(cls, value: str) -> str:
        return _utc_iso(value)


class PlayRunsListResponse(BaseModel):
    model_config = ConfigDict(extra="forbid", strict=True)

    schema_version: Literal["dmb_play_runs_list_v1"] = PLAY_RUNS_LIST_SCHEMA
    records: list[PlayRunRecord] = Field(default_factory=list)


def _utc_now_iso() -> str:
    return datetime.now(UTC).isoformat().replace("+00:00", "Z")


def play_runs_dir(root: Path) -> Path:
    return root / PLAY_RUNS_REL


def play_run_path(root: Path, run_id: str) -> Path:
    canonical = _validate_run_id(run_id)
    return play_runs_dir(root) / f"{canonical}.json"


def _validate_run_id(run_id: str) -> str:
    try:
        return _canonical_uuid(run_id, field_name="run_id")
    except ValueError as exc:
        raise PlayRunRegistryError(str(exc), status_code=422) from exc


def _validate_playable_artifact_id(playable_artifact_id: str) -> str:
    try:
        return _canonical_uuid(
            playable_artifact_id,
            field_name="playable_artifact_id",
        )
    except ValueError as exc:
        raise PlayRunRegistryError(str(exc), status_code=422) from exc


def _validate_expected_revision(expected_playable_revision: int) -> int:
    if (
        not isinstance(expected_playable_revision, int)
        or isinstance(expected_playable_revision, bool)
        or expected_playable_revision <= 0
    ):
        raise PlayRunRegistryError(
            "expected_playable_revision must be a positive integer",
            status_code=422,
        )
    return expected_playable_revision


def _validate_expected_sha(expected_playable_content_sha256: str) -> str:
    try:
        return _canonical_sha256(
            expected_playable_content_sha256,
            field_name="expected_playable_content_sha256",
        )
    except ValueError as exc:
        raise PlayRunRegistryError(str(exc), status_code=422) from exc


def _load_record(path: Path) -> PlayRunRecord:
    try:
        expected_run_id = _canonical_uuid(path.stem, field_name="run file name")
        record = PlayRunRecord.model_validate(load_json(path))
        if record.run_id != expected_run_id:
            raise ValueError(
                "persisted run_id does not match the Run file name: "
                f"{record.run_id} != {expected_run_id}"
            )
        return record
    except (OSError, TypeError, ValueError, ValidationError) as exc:
        raise PlayRunRegistryError(
            f"malformed persisted Play Run {path.name}: {exc}",
            status_code=500,
        ) from exc


def get_play_run(root: Path, run_id: str) -> PlayRunRecord:
    path = play_run_path(root, run_id)
    if not path.is_file():
        raise PlayRunRegistryError(
            f"Play Run not found: {_validate_run_id(run_id)}",
            status_code=404,
        )
    return _load_record(path)


def list_play_runs(
    root: Path,
    *,
    campaign_id: str | None = None,
    playable_artifact_id: str | None = None,
) -> list[PlayRunRecord]:
    resolved_artifact_id = None
    if playable_artifact_id is not None:
        resolved_artifact_id = _validate_playable_artifact_id(playable_artifact_id)

    directory = play_runs_dir(root)
    if not directory.is_dir():
        return []

    records = [_load_record(path) for path in sorted(directory.glob("*.json"))]
    if campaign_id is not None:
        records = [record for record in records if record.campaign_id == campaign_id]
    if resolved_artifact_id is not None:
        records = [
            record
            for record in records
            if record.playable_artifact_id == resolved_artifact_id
        ]

    records.sort(key=lambda record: record.run_id)
    records.sort(key=lambda record: _parse_utc_iso(record.created_at), reverse=True)
    return records


def create_or_replay_play_run(
    root: Path,
    *,
    run_id: str,
    playable_artifact_id: str,
    expected_playable_revision: int,
    expected_playable_content_sha256: str,
) -> PlayRunRecord:
    canonical_run_id = _validate_run_id(run_id)
    canonical_artifact_id = _validate_playable_artifact_id(playable_artifact_id)
    expected_revision = _validate_expected_revision(expected_playable_revision)
    expected_sha = _validate_expected_sha(expected_playable_content_sha256)
    path = play_runs_dir(root) / f"{canonical_run_id}.json"

    with registry_mutation_lock(path):
        if path.is_file():
            existing = _load_record(path)
            if (
                existing.playable_artifact_id == canonical_artifact_id
                and existing.playable_revision == expected_revision
                and existing.playable_content_sha256 == expected_sha
            ):
                return existing
            raise PlayRunRegistryError(
                "run_id is already bound to a different Playable revision",
                status_code=409,
            )

        try:
            with workspace_document_mutation_lock(root, canonical_artifact_id):
                snapshot = get_workspace_document_snapshot_unlocked(
                    root,
                    canonical_artifact_id,
                )

                if snapshot.record.kind != "runbook":
                    raise PlayRunRegistryError(
                        "playable_artifact_id must identify a runbook workspace document",
                        status_code=422,
                    )
                if snapshot.record.status != "active":
                    raise PlayRunRegistryError(
                        "runbook workspace document is discarded",
                        status_code=409,
                    )
                if snapshot.record.content_status != "committed":
                    raise PlayRunRegistryError(
                        "runbook workspace document is not committed",
                        status_code=409,
                    )
                if not snapshot.file_exists:
                    raise PlayRunRegistryError(
                        "committed runbook workspace target file is missing",
                        status_code=409,
                    )
                if snapshot.loaded_revision != expected_revision:
                    raise PlayRunRegistryError(
                        "playable revision mismatch: "
                        f"expected {expected_revision}, current {snapshot.loaded_revision}",
                        status_code=409,
                    )
                if snapshot.content_sha256 != expected_sha:
                    raise PlayRunRegistryError(
                        "playable content SHA mismatch",
                        status_code=409,
                    )

                now = _utc_now_iso()
                record = PlayRunRecord(
                    run_id=canonical_run_id,
                    campaign_id=snapshot.record.campaign_id,
                    playable_artifact_id=canonical_artifact_id,
                    playable_revision=snapshot.loaded_revision,
                    playable_content_sha256=snapshot.content_sha256,
                    created_at=now,
                    updated_at=now,
                )
                path.parent.mkdir(parents=True, exist_ok=True)
                try:
                    write_json(path, record.model_dump(mode="json"))
                except (OSError, TypeError, ValueError) as exc:
                    raise PlayRunRegistryError(
                        f"failed to persist Play Run: {exc}",
                        status_code=500,
                    ) from exc
                return record
        except WorkspaceDocumentRegistryError as exc:
            raise PlayRunRegistryError(
                str(exc),
                status_code=exc.status_code,
            ) from exc
