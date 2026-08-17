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


class PlayRunProgress(BaseModel):
    model_config = ConfigDict(extra="forbid", strict=True)

    current_scene_id: str | None
    current_beat_id: str | None
    resolved_beat_ids: list[str]
    selections: dict[str, str]
    notes_by_element_id: dict[str, str]


class ReplacePlayRunProgressRequest(BaseModel):
    model_config = ConfigDict(extra="forbid", strict=True)

    expected_run_revision: int = Field(gt=0)
    progress: PlayRunProgress


def empty_play_run_progress() -> PlayRunProgress:
    return PlayRunProgress(
        current_scene_id=None,
        current_beat_id=None,
        resolved_beat_ids=[],
        selections={},
        notes_by_element_id={},
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
    progress: PlayRunProgress = Field(default_factory=empty_play_run_progress)

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


def _canonicalize_progress(progress: PlayRunProgress) -> PlayRunProgress:
    return PlayRunProgress(
        current_scene_id=progress.current_scene_id,
        current_beat_id=progress.current_beat_id,
        resolved_beat_ids=sorted(set(progress.resolved_beat_ids)),
        selections=dict(progress.selections),
        notes_by_element_id=dict(progress.notes_by_element_id),
    )


def _progress_is_empty(progress: PlayRunProgress) -> bool:
    canonical = _canonicalize_progress(progress)
    return (
        canonical.current_scene_id is None
        and canonical.current_beat_id is None
        and canonical.resolved_beat_ids == []
        and canonical.selections == {}
        and canonical.notes_by_element_id == {}
    )


def _admit_progress(
    progress: PlayRunProgress,
    *,
    manifest: object,
    status_code: int,
) -> PlayRunProgress:
    canonical = _canonicalize_progress(progress)
    by_id = {element.element_id: element for element in manifest.elements}

    def require(element_id: str, kinds: set[str], field_name: str) -> object:
        element = by_id.get(element_id)
        if element is None or element.kind not in kinds:
            raise PlayRunRegistryError(
                f"{field_name} is not admitted by the sealed Playable reference manifest",
                status_code=status_code,
            )
        return element

    if canonical.current_beat_id is not None and canonical.current_scene_id is None:
        raise PlayRunRegistryError(
            "current_beat_id requires current_scene_id",
            status_code=status_code,
        )
    if canonical.current_scene_id is not None:
        require(canonical.current_scene_id, {"scene"}, "current_scene_id")
    if canonical.current_beat_id is not None:
        beat = require(canonical.current_beat_id, {"beat"}, "current_beat_id")
        if beat.scene_id != canonical.current_scene_id:
            raise PlayRunRegistryError(
                "current_beat_id does not belong to current_scene_id",
                status_code=status_code,
            )
    for beat_id in canonical.resolved_beat_ids:
        require(beat_id, {"beat"}, "resolved_beat_ids")
    for choice_id, option_id in canonical.selections.items():
        require(choice_id, {"choice"}, "selections")
        option = require(option_id, {"option"}, "selections")
        if option.choice_id != choice_id:
            raise PlayRunRegistryError(
                "selected option does not belong to the selected choice",
                status_code=status_code,
            )
    for element_id in canonical.notes_by_element_id:
        require(
            element_id,
            {"scene", "beat", "choice", "option"},
            "notes_by_element_id",
        )
    return canonical


def _load_bound_manifest(root: Path, record: PlayRunRecord):
    from apps.live_control_server.services.play_run_reference_manifest import (
        PlayRunReferenceManifestError,
        load_play_run_reference_manifest_for_record,
    )

    try:
        return load_play_run_reference_manifest_for_record(root, record)
    except PlayRunReferenceManifestError as exc:
        raise PlayRunRegistryError(str(exc), status_code=exc.status_code) from exc


def _revalidate_persisted_progress(root: Path, record: PlayRunRecord) -> None:
    if _progress_is_empty(record.progress):
        return
    try:
        manifest = _load_bound_manifest(root, record)
    except PlayRunRegistryError as exc:
        status = 500 if exc.status_code == 404 else exc.status_code
        raise PlayRunRegistryError(
            f"persisted Play Run progress cannot be admitted: {exc}",
            status_code=status,
        ) from exc
    canonical = _admit_progress(record.progress, manifest=manifest, status_code=500)
    if record.progress.resolved_beat_ids != canonical.resolved_beat_ids:
        raise PlayRunRegistryError(
            "persisted resolved_beat_ids must be duplicate-free and lexicographically sorted",
            status_code=500,
        )


def _load_authoritative_record(root: Path, path: Path) -> PlayRunRecord:
    record = _load_record(path)
    _revalidate_persisted_progress(root, record)
    return record


def _require_no_pending_rebase(root: Path, run_id: str) -> None:
    from apps.live_control_server.services.play_run_rebase import (
        PlayRunRebaseError,
        require_no_pending_rebase_intent,
    )

    try:
        require_no_pending_rebase_intent(root, run_id)
    except PlayRunRebaseError as exc:
        raise PlayRunRegistryError(str(exc), status_code=exc.status_code) from exc


def get_play_run(root: Path, run_id: str) -> PlayRunRecord:
    path = play_run_path(root, run_id)
    from apps.live_control_server.services.play_run_rebase import rebase_intent_exists

    if not path.is_file() and not rebase_intent_exists(root, run_id):
        raise PlayRunRegistryError(
            f"Play Run not found: {_validate_run_id(run_id)}",
            status_code=404,
        )
    with registry_mutation_lock(path):
        _require_no_pending_rebase(root, run_id)
        if not path.is_file():
            raise PlayRunRegistryError(
                f"Play Run not found: {_validate_run_id(run_id)}",
                status_code=404,
            )
        return _load_authoritative_record(root, path)


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

    records: list[PlayRunRecord] = []
    for path in sorted(directory.glob("*.json")):
        with registry_mutation_lock(path):
            _require_no_pending_rebase(root, path.stem)
            records.append(_load_authoritative_record(root, path))
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
        _require_no_pending_rebase(root, canonical_run_id)
        if path.is_file():
            existing = _load_authoritative_record(root, path)
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
                    progress=empty_play_run_progress(),
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


def replace_play_run_progress(
    root: Path,
    *,
    run_id: str,
    expected_run_revision: int,
    progress: PlayRunProgress,
) -> PlayRunRecord:
    canonical_run_id = _validate_run_id(run_id)
    if (
        not isinstance(expected_run_revision, int)
        or isinstance(expected_run_revision, bool)
        or expected_run_revision <= 0
    ):
        raise PlayRunRegistryError(
            "expected_run_revision must be a positive integer",
            status_code=422,
        )
    path = play_run_path(root, canonical_run_id)

    with registry_mutation_lock(path):
        _require_no_pending_rebase(root, canonical_run_id)
        if not path.is_file():
            raise PlayRunRegistryError(
                f"Play Run not found: {canonical_run_id}",
                status_code=404,
            )
        existing = _load_authoritative_record(root, path)
        bytes_before = path.read_bytes()
        try:
            manifest = _load_bound_manifest(root, existing)
        except PlayRunRegistryError as exc:
            if exc.status_code == 404:
                raise PlayRunRegistryError(
                    "Play Run reference manifest is required before progress mutation",
                    status_code=409,
                ) from exc
            raise
        admitted = _admit_progress(progress, manifest=manifest, status_code=422)
        current_progress = _canonicalize_progress(existing.progress)

        if expected_run_revision == existing.run_revision:
            if admitted == current_progress:
                if path.read_bytes() != bytes_before:
                    raise PlayRunRegistryError(
                        "progress no-op rewrote Run bytes",
                        status_code=500,
                    )
                return existing
        elif (
            expected_run_revision == existing.run_revision - 1
            and admitted == current_progress
        ):
            if path.read_bytes() != bytes_before:
                raise PlayRunRegistryError(
                    "progress replay rewrote Run bytes",
                    status_code=500,
                )
            return existing
        else:
            raise PlayRunRegistryError(
                "run_revision does not match the current Play Run",
                status_code=409,
            )

        updated = existing.model_copy(
            update={
                "run_revision": existing.run_revision + 1,
                "updated_at": _utc_now_iso(),
                "progress": admitted,
            }
        )
        try:
            write_json(path, updated.model_dump(mode="json"))
        except (OSError, TypeError, ValueError) as exc:
            raise PlayRunRegistryError(
                f"failed to persist Play Run progress: {exc}",
                status_code=500,
            ) from exc
        return updated
