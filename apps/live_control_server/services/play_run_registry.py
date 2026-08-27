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
    field_validator,
    model_serializer,
)

PLAY_RUN_RECORD_SCHEMA = "dmb_play_run_record_v1"
PLAY_RUNS_LIST_SCHEMA = "dmb_play_runs_list_v1"


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


def derive_v2_opening_beat_id(markdown: str) -> str | None:
    """First spine Beat in pinned document order, else first Beat, else None.

    Manifest array order is not document-order authority. Opening Beat is taken
    from BF1 fence/grammar-admitted markers in exact WorkRevision document
    order — not a raw line scan that would treat fenced examples as Beats.
    """
    from apps.live_control_server.services.play_run_reference_manifest import (
        PlayRunReferenceManifestError,
        V2_BEAT_MARKER_RE,
        _closes_fence,
        _opening_fence,
        derive_play_run_reference_elements_v2,
    )

    try:
        derived = derive_play_run_reference_elements_v2(markdown)
    except PlayRunReferenceManifestError:
        return None
    admitted = {beat.beat_id: beat.beat_kind for beat in derived.beats}
    if not admitted:
        return None

    normalized = markdown.replace("\ufeff", "").replace("\r\n", "\n").replace("\r", "\n")
    fence_char: str | None = None
    fence_length = 0
    first_beat: str | None = None
    for line in normalized.split("\n"):
        if fence_char is not None:
            if _closes_fence(line, fence_char, fence_length):
                fence_char = None
                fence_length = 0
            continue
        opening = _opening_fence(line)
        if opening is not None:
            fence_char, fence_length = opening
            continue
        match = V2_BEAT_MARKER_RE.fullmatch(line)
        if match is None:
            continue
        beat_id = match.group(1)
        if beat_id not in admitted:
            continue
        if first_beat is None:
            first_beat = beat_id
        if admitted[beat_id] == "spine":
            return beat_id
    return first_beat


def compare_v2_sealed_structure(markdown: str, manifest: object) -> str | None:
    """Fail closed when sealed v2 membership, beat_kind, or edges diverge."""
    from apps.live_control_server.services.play_run_reference_manifest import (
        PlayRunReferenceManifestError,
        derive_play_run_reference_elements_v2,
    )

    try:
        derived = derive_play_run_reference_elements_v2(markdown)
    except PlayRunReferenceManifestError as exc:
        return str(exc)

    derived_beats = {(beat.beat_id, beat.beat_kind) for beat in derived.beats}
    manifest_beats = {
        (beat.beat_id, beat.beat_kind) for beat in getattr(manifest, "beats", ())
    }
    if derived_beats != manifest_beats:
        return "sealed v2 manifest disagrees with pinned WorkRevision on Beat kind or membership"
    derived_scenes = {(scene.scene_id, scene.beat_id) for scene in derived.scenes}
    manifest_scenes = {
        (scene.scene_id, scene.beat_id) for scene in getattr(manifest, "scenes", ())
    }
    if derived_scenes != manifest_scenes:
        return "sealed v2 manifest disagrees with pinned WorkRevision on Scene membership"
    derived_choices = {
        (choice.choice_id, choice.beat_id, choice.scene_id) for choice in derived.choices
    }
    manifest_choices = {
        (choice.choice_id, choice.beat_id, choice.scene_id)
        for choice in getattr(manifest, "choices", ())
    }
    if derived_choices != manifest_choices:
        return "sealed v2 manifest disagrees with pinned WorkRevision on Choice membership"
    derived_options = {
        (option.option_id, option.choice_id) for option in derived.options
    }
    manifest_options = {
        (option.option_id, option.choice_id) for option in getattr(manifest, "options", ())
    }
    if derived_options != manifest_options:
        return "sealed v2 manifest disagrees with pinned WorkRevision on Option membership"
    derived_edges = {
        (edge.option_id, edge.effect, edge.target_kind, edge.target_id)
        for edge in derived.edges
    }
    manifest_edges = {
        (edge.option_id, edge.effect, edge.target_kind, edge.target_id)
        for edge in getattr(manifest, "edges", ())
    }
    if derived_edges != manifest_edges:
        return "sealed v2 manifest disagrees with pinned WorkRevision on authored transition edges"
    return None


def compare_run_manifest_binding(record: PlayRunRecord, manifest: object) -> str | None:
    """Fail closed when sealed JSON binding metadata diverges from the Run."""
    if getattr(manifest, "run_id", None) != record.run_id:
        return "sealed reference manifest run_id does not match the Run"
    if getattr(manifest, "playable_artifact_id", None) != record.playable_artifact_id:
        return "sealed reference manifest playable_artifact_id does not match the Run"
    if getattr(manifest, "playable_revision", None) != record.playable_revision:
        return "sealed reference manifest playable_revision does not match the Run"
    if getattr(manifest, "playable_content_sha256", None) != record.playable_content_sha256:
        return "sealed reference manifest playable_content_sha256 does not match the Run"
    return None


def ensure_v2_native_ready(root: Path, run_id: str, *, conflict_depth: int = 0) -> PlayRunRecord:
    """Owning first-admission workflow: pinned authority preflight, then seed.

    Load Run + sealed manifest from one application-state aggregate, prove the
    sealed JSON binding and behavior-bearing v2 contract against that exact
    pinned WorkRevision, then persist the opening Beat only if progress is
    still empty. CAS 409 rebinds the full authority set here rather than
    leaving orchestration to the caller.
    """
    from application_state.errors import ApplicationStateError
    from application_state.play.service import get_play_run_aggregate
    from apps.live_control_server.services.play_run_reference_manifest import (
        PlayRunReferenceManifestError,
        parse_manifest_payload,
    )
    from apps.live_control_server.services.workspace_document_registry import (
        get_committed_playable_revision,
    )

    canonical_run_id = _validate_run_id(run_id)
    try:
        aggregate = get_play_run_aggregate(canonical_run_id)
    except ApplicationStateError as exc:
        raise _map_application_state(exc) from exc
    record = _record_from_play_run(aggregate.run)
    try:
        manifest = parse_manifest_payload(aggregate.manifest.manifest, run_id=record.run_id)
    except PlayRunReferenceManifestError as exc:
        raise PlayRunRegistryError(str(exc), status_code=int(getattr(exc, "status_code", 500))) from exc
    if getattr(manifest, "schema_version", None) != "dmb_play_run_reference_manifest_v2":
        return record
    binding = compare_run_manifest_binding(record, manifest)
    if binding:
        raise PlayRunRegistryError(binding, status_code=422)
    try:
        committed = get_committed_playable_revision(
            record.playable_artifact_id,
            revision_n=record.playable_revision,
            expected_sha256=record.playable_content_sha256,
            kind="runbook",
        )
    except Exception as exc:
        raise PlayRunRegistryError(str(exc), status_code=int(getattr(exc, "status_code", 500))) from exc
    mismatch = compare_v2_sealed_structure(committed.markdown, manifest)
    if mismatch:
        raise PlayRunRegistryError(mismatch, status_code=422)
    opening = derive_v2_opening_beat_id(committed.markdown)
    if opening is None:
        raise PlayRunRegistryError(
            "v2 Playable has no Beat; native READY is fail-closed",
            status_code=422,
        )
    if not _progress_is_empty(record.progress):
        return record
    try:
        return replace_play_run_progress(
            root,
            run_id=run_id,
            expected_run_revision=record.run_revision,
            progress=PlayRunProgress(
                current_beat_id=opening,
                current_scene_id=None,
                resolved_beat_ids=[],
                selections={},
                notes_by_element_id={},
            ),
        )
    except PlayRunRegistryError as exc:
        if exc.status_code == 409 and conflict_depth < 2:
            return ensure_v2_native_ready(root, run_id, conflict_depth=conflict_depth + 1)
        raise


def _admit_progress_v2(
    progress: PlayRunProgress,
    *,
    manifest: object,
    status_code: int,
) -> PlayRunProgress:
    canonical = _canonicalize_progress(progress)
    beats = {beat.beat_id: beat for beat in getattr(manifest, "beats", ())}
    scenes = {scene.scene_id: scene for scene in getattr(manifest, "scenes", ())}
    choices = {choice.choice_id: choice for choice in getattr(manifest, "choices", ())}
    options = {option.option_id: option for option in getattr(manifest, "options", ())}

    def reject(field_name: str) -> None:
        raise PlayRunRegistryError(
            f"{field_name} is not admitted by the sealed Playable reference manifest",
            status_code=status_code,
        )

    if canonical.current_beat_id is None:
        raise PlayRunRegistryError(
            "v2 current_beat_id is required when progress is not empty",
            status_code=status_code,
        )
    if canonical.current_beat_id not in beats:
        reject("current_beat_id")
    if canonical.current_scene_id is not None:
        scene = scenes.get(canonical.current_scene_id)
        if scene is None:
            reject("current_scene_id")
            raise AssertionError("unreachable")
        if scene.beat_id != canonical.current_beat_id:
            raise PlayRunRegistryError(
                "current_scene_id does not belong to current_beat_id",
                status_code=status_code,
            )
    for beat_id in canonical.resolved_beat_ids:
        if beat_id not in beats:
            reject("resolved_beat_ids")
    for choice_id, option_id in canonical.selections.items():
        if choice_id not in choices:
            reject("selections")
        option = options.get(option_id)
        if option is None:
            reject("selections")
            raise AssertionError("unreachable")
        if option.choice_id != choice_id:
            raise PlayRunRegistryError(
                "selected option does not belong to the selected choice",
                status_code=status_code,
            )
    for element_id in canonical.notes_by_element_id:
        if (
            element_id not in beats
            and element_id not in scenes
            and element_id not in choices
            and element_id not in options
        ):
            reject("notes_by_element_id")
    return canonical


def _admit_progress(
    progress: PlayRunProgress,
    *,
    manifest: object,
    status_code: int,
) -> PlayRunProgress:
    schema_version = getattr(manifest, "schema_version", None)
    if schema_version == "dmb_play_run_reference_manifest_v2":
        return _admit_progress_v2(
            progress, manifest=manifest, status_code=status_code
        )
    if schema_version != "dmb_play_run_reference_manifest_v1":
        raise PlayRunRegistryError(
            "sealed reference manifest schema_version is not admitted",
            status_code=status_code,
        )
    elements = getattr(manifest, "elements", None)
    if elements is None:
        raise PlayRunRegistryError(
            "sealed reference manifest is malformed",
            status_code=status_code,
        )
    canonical = _canonicalize_progress(progress)
    by_id = {element.element_id: element for element in elements}

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


def get_play_run(root: Path, run_id: str) -> PlayRunRecord:
    del root
    from application_state.errors import ApplicationStateError
    from application_state.play.service import get_play_run_aggregate

    canonical_run_id = _validate_run_id(run_id)
    try:
        aggregate = get_play_run_aggregate(canonical_run_id)
    except ApplicationStateError as exc:
        raise _map_application_state(exc) from exc
    return _record_from_play_run(aggregate.run)


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
