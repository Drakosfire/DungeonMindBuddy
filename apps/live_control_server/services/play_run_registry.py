"""Durable Play Runtime records bound to exact committed Runbook revisions."""

from __future__ import annotations

import re
import uuid
from datetime import UTC, datetime
from pathlib import Path
from typing import Literal

from pydantic import (
    BaseModel,
    ConfigDict,
    Field,
    ValidationError,
    field_validator,
    model_serializer,
)

from src.live_play.live_store import load_json

PLAY_RUN_RECORD_SCHEMA = "dmb_play_run_record_v1"
PLAY_RUNS_LIST_SCHEMA = "dmb_play_runs_list_v1"
PLAY_RUNS_REL = "out/runtime/play/runs"


def _iso_z(value: datetime | str) -> str:
    if isinstance(value, str):
        return value
    stamp = value if value.tzinfo is not None else value.replace(tzinfo=UTC)
    return stamp.astimezone(UTC).isoformat().replace("+00:00", "Z")


def _map_application_state(exc: Exception) -> PlayRunRegistryError:
    return PlayRunRegistryError(str(exc), status_code=int(getattr(exc, "status_code", 500)))


def _record_from_play_run(run: object) -> PlayRunRecord:
    progress = getattr(run, "progress")
    return PlayRunRecord(
        run_id=str(run.run_id),
        campaign_id=run.campaign_id,
        playable_artifact_id=str(run.playable_work_object_id),
        playable_revision=int(run.playable_revision_n),
        playable_content_sha256=str(run.playable_content_sha256),
        run_revision=int(run.run_revision),
        created_at=_iso_z(run.created_at),
        updated_at=_iso_z(run.updated_at),
        progress=PlayRunProgress.model_validate(progress),
        rebased_from_run_revision=getattr(run, "rebased_from_run_revision", None),
    )


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
    rebased_from_run_revision: int | None = None

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

    @field_validator("rebased_from_run_revision")
    @classmethod
    def _validate_rebased_from_run_revision(cls, value: int | None) -> int | None:
        if value is None:
            return None
        if isinstance(value, bool) or value <= 0:
            raise ValueError("rebased_from_run_revision must be a positive integer")
        return value

    @model_serializer(mode="wrap")
    def _omit_absent_rebase_receipt(self, serializer: object) -> dict[str, object]:
        payload = serializer(self)
        if payload.get("rebased_from_run_revision") is None:
            payload.pop("rebased_from_run_revision", None)
        return payload


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
    del root
    from application_state.errors import ApplicationStateError
    from application_state.play.service import get_play_run_aggregate

    canonical_run_id = _validate_run_id(run_id)
    try:
        aggregate = get_play_run_aggregate(canonical_run_id)
    except ApplicationStateError as exc:
        raise _map_application_state(exc) from exc
    record = _record_from_play_run(aggregate.run)
    if not _progress_is_empty(record.progress):
        from apps.live_control_server.services.play_run_reference_manifest import (
            parse_manifest_payload,
        )

        parsed = parse_manifest_payload(
            aggregate.manifest.manifest, run_id=record.run_id
        )
        _admit_progress(record.progress, manifest=parsed, status_code=500)
    return record


def list_play_runs(
    root: Path,
    *,
    campaign_id: str | None = None,
    playable_artifact_id: str | None = None,
) -> list[PlayRunRecord]:
    del root
    from application_state.errors import ApplicationStateError
    from application_state.play.service import list_play_run_aggregates

    resolved_artifact_id = None
    if playable_artifact_id is not None:
        resolved_artifact_id = _validate_playable_artifact_id(playable_artifact_id)
    try:
        aggregates = list_play_run_aggregates(
            campaign_id=campaign_id,
            playable_artifact_id=resolved_artifact_id,
        )
    except ApplicationStateError as exc:
        raise _map_application_state(exc) from exc
    return [_record_from_play_run(aggregate.run) for aggregate in aggregates]


def create_or_replay_play_run(
    root: Path,
    *,
    run_id: str,
    playable_artifact_id: str,
    expected_playable_revision: int,
    expected_playable_content_sha256: str,
) -> PlayRunRecord:
    del root
    from application_state.errors import ApplicationStateError
    from application_state.play.service import create_play_run

    canonical_run_id = _validate_run_id(run_id)
    canonical_artifact_id = _validate_playable_artifact_id(playable_artifact_id)
    expected_revision = _validate_expected_revision(expected_playable_revision)
    expected_sha = _validate_expected_sha(expected_playable_content_sha256)
    try:
        aggregate = create_play_run(
            run_id=canonical_run_id,
            playable_artifact_id=canonical_artifact_id,
            expected_playable_revision=expected_revision,
            expected_playable_content_sha256=expected_sha,
        )
    except ApplicationStateError as exc:
        raise _map_application_state(exc) from exc
    return _record_from_play_run(aggregate.run)


def replace_play_run_progress(
    root: Path,
    *,
    run_id: str,
    expected_run_revision: int,
    progress: PlayRunProgress,
) -> PlayRunRecord:
    del root
    from application_state.errors import ApplicationStateError
    from application_state.play.service import replace_play_run_progress as replace_progress

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
    try:
        run = replace_progress(
            run_id=canonical_run_id,
            expected_run_revision=expected_run_revision,
            progress=progress.model_dump(mode="json"),
        )
    except ApplicationStateError as exc:
        raise _map_application_state(exc) from exc
    return _record_from_play_run(run)
