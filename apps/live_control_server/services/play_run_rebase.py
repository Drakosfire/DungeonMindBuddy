"""Preserve-only same-artifact Play Run rebase with forward-recovery intent."""

from __future__ import annotations

import hashlib
import json
import re
from pathlib import Path
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, ValidationError, field_validator, model_validator

from apps.live_control_server.services.play_run_reference_manifest import (
    PlayRunReferenceManifest,
    PlayRunReferenceManifestError,
    _dump_manifest,
    _load_manifest,
    _require_binding_match,
    derive_play_run_reference_elements,
    play_run_reference_manifest_path,
)
from apps.live_control_server.services.play_run_registry import (
    PlayRunProgress,
    PlayRunRecord,
    PlayRunRegistryError,
    _load_record,
    _progress_is_empty,
    _utc_now_iso,
    play_run_path,
)
from apps.live_control_server.services.registry_file_lock import (
    registry_mutation_lock,
    registry_token,
    workspace_document_mutation_lock,
)
from apps.live_control_server.services.workspace_document_registry import (
    WorkspaceDocumentRegistryError,
    get_workspace_document_snapshot_unlocked,
)
from src.live_play.live_store import load_json, write_json

PLAY_RUN_REBASE_INTENT_SCHEMA = "dmb_play_run_rebase_intent_v1"
PLAY_RUN_REBASE_INTENTS_REL = "out/runtime/play/rebase-intents"
_SHA256_RE = re.compile(r"^[0-9a-f]{64}$")
_ABSENT_TOKEN = "absent"


class PlayRunRebaseError(ValueError):
    """Fail-closed error for preserve-only Play Run rebase."""

    status_code: int = 500

    def __init__(self, message: str, *, status_code: int = 500) -> None:
        super().__init__(message)
        self.status_code = status_code


class RebasePlayRunRequest(BaseModel):
    model_config = ConfigDict(extra="forbid", strict=True)

    expected_run_revision: int = Field(gt=0)
    target_playable_revision: int = Field(gt=0)
    target_playable_content_sha256: str

    @field_validator("target_playable_content_sha256")
    @classmethod
    def _validate_target_sha(cls, value: str) -> str:
        cleaned = value.strip()
        if not _SHA256_RE.fullmatch(cleaned):
            raise ValueError(
                "target_playable_content_sha256 must be 64 lowercase hex characters"
            )
        return cleaned


class PlayRunRebaseIntent(BaseModel):
    model_config = ConfigDict(extra="forbid", strict=True)

    schema_version: Literal["dmb_play_run_rebase_intent_v1"] = PLAY_RUN_REBASE_INTENT_SCHEMA
    run_id: str
    expected_source_run_revision: int = Field(gt=0)
    source_playable_artifact_id: str
    source_playable_revision: int = Field(gt=0)
    source_playable_content_sha256: str
    source_run_token: str
    source_manifest_token: str
    target_run: PlayRunRecord
    target_manifest: PlayRunReferenceManifest
    prepared_at: str

    @model_validator(mode="after")
    def _validate_intent_coherence(self) -> PlayRunRebaseIntent:
        if not _SHA256_RE.fullmatch(self.source_run_token):
            raise ValueError("source_run_token must be 64 lowercase hex characters")
        if self.source_manifest_token != _ABSENT_TOKEN and not _SHA256_RE.fullmatch(
            self.source_manifest_token
        ):
            raise ValueError(
                "source_manifest_token must be 'absent' or 64 lowercase hex characters"
            )
        target = self.target_run
        manifest = self.target_manifest
        if target.run_id != self.run_id:
            raise ValueError("target_run.run_id must match intent run_id")
        if target.playable_artifact_id != self.source_playable_artifact_id:
            raise ValueError("target_run must keep the source playable_artifact_id")
        if target.run_revision != self.expected_source_run_revision + 1:
            raise ValueError("target_run.run_revision must be expected_source_run_revision + 1")
        if target.playable_revision <= self.source_playable_revision:
            raise ValueError("target_run.playable_revision must be strictly newer")
        if (
            manifest.run_id != target.run_id
            or manifest.playable_artifact_id != target.playable_artifact_id
            or manifest.playable_revision != target.playable_revision
            or manifest.playable_content_sha256 != target.playable_content_sha256
        ):
            raise ValueError("target_manifest must bind exactly to target_run")
        return self


def play_run_rebase_intents_dir(root: Path) -> Path:
    return root / PLAY_RUN_REBASE_INTENTS_REL


def play_run_rebase_intent_path(root: Path, run_id: str) -> Path:
    from apps.live_control_server.services.play_run_registry import _validate_run_id

    canonical = _validate_run_id(run_id)
    return play_run_rebase_intents_dir(root) / f"{canonical}.json"


def rebase_intent_exists(root: Path, run_id: str) -> bool:
    return play_run_rebase_intent_path(root, run_id).is_file()


def require_no_pending_rebase_intent(root: Path, run_id: str) -> None:
    if rebase_intent_exists(root, run_id):
        raise PlayRunRebaseError(
            f"Play Run rebase recovery is pending: {run_id}",
            status_code=503,
        )


def _raise_registry(exc: PlayRunRegistryError) -> None:
    raise PlayRunRebaseError(str(exc), status_code=exc.status_code) from exc


def _raise_manifest(exc: PlayRunReferenceManifestError) -> None:
    raise PlayRunRebaseError(str(exc), status_code=exc.status_code) from exc


def _json_token(payload: dict[str, object]) -> str:
    text = json.dumps(payload, indent=2, ensure_ascii=False) + "\n"
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def _run_payload_token(record: PlayRunRecord) -> str:
    return _json_token(record.model_dump(mode="json"))


def _manifest_payload_token(manifest: PlayRunReferenceManifest) -> str:
    return _json_token(_dump_manifest(manifest))


def _load_intent(path: Path) -> PlayRunRebaseIntent:
    try:
        expected_run_id = path.stem
        intent = PlayRunRebaseIntent.model_validate(load_json(path))
        if intent.run_id != expected_run_id:
            raise ValueError(
                "persisted rebase intent run_id does not match the intent file name: "
                f"{intent.run_id} != {expected_run_id}"
            )
        return intent
    except (OSError, TypeError, ValueError, ValidationError) as exc:
        raise PlayRunRebaseError(
            f"malformed persisted Play Run rebase intent {path.name}: {exc}",
            status_code=500,
        ) from exc


def _admit_progress_for_rebase(
    progress: PlayRunProgress,
    *,
    manifest: PlayRunReferenceManifest,
) -> None:
    by_id = {element.element_id: element for element in manifest.elements}

    def require(element_id: str, kinds: set[str], field_name: str) -> object:
        element = by_id.get(element_id)
        if element is None or element.kind not in kinds:
            raise PlayRunRebaseError(
                f"{field_name} {element_id} is not admitted by the target Playable reference manifest",
                status_code=409,
            )
        return element

    if progress.current_beat_id is not None and progress.current_scene_id is None:
        raise PlayRunRebaseError(
            "current_beat_id requires current_scene_id",
            status_code=409,
        )
    if progress.current_scene_id is not None:
        require(progress.current_scene_id, {"scene"}, "current_scene_id")
    if progress.current_beat_id is not None:
        beat = require(progress.current_beat_id, {"beat"}, "current_beat_id")
        if beat.scene_id != progress.current_scene_id:
            raise PlayRunRebaseError(
                f"current_beat_id {progress.current_beat_id} does not belong to "
                f"current_scene_id {progress.current_scene_id}",
                status_code=409,
            )
    for beat_id in progress.resolved_beat_ids:
        require(beat_id, {"beat"}, "resolved_beat_ids")
    for choice_id, option_id in progress.selections.items():
        require(choice_id, {"choice"}, "selections")
        option = require(option_id, {"option"}, "selections")
        if option.choice_id != choice_id:
            raise PlayRunRebaseError(
                f"selections {choice_id} -> {option_id} does not belong to that Choice",
                status_code=409,
            )
    for element_id in progress.notes_by_element_id:
        require(
            element_id,
            {"scene", "beat", "choice", "option"},
            "notes_by_element_id",
        )


def _prove_target_pair(root: Path, record: PlayRunRecord) -> PlayRunReferenceManifest:
    path = play_run_reference_manifest_path(root, record.run_id)
    if not path.is_file():
        raise PlayRunRebaseError(
            "completed rebase target manifest is missing",
            status_code=500,
        )
    try:
        manifest = _load_manifest(path)
        _require_binding_match(manifest, record)
    except PlayRunReferenceManifestError as exc:
        raise PlayRunRebaseError(
            f"completed rebase target manifest failed integrity: {exc}",
            status_code=500,
        ) from exc
    if not _progress_is_empty(record.progress):
        try:
            _admit_progress_for_rebase(record.progress, manifest=manifest)
        except PlayRunRebaseError as exc:
            raise PlayRunRebaseError(
                f"completed rebase target progress failed integrity: {exc}",
                status_code=500,
            ) from exc
    return manifest


def _same_target_binding(record: PlayRunRecord, request: RebasePlayRunRequest) -> bool:
    return (
        record.playable_revision == request.target_playable_revision
        and record.playable_content_sha256 == request.target_playable_content_sha256
    )


def _admit_target_snapshot(
    record: PlayRunRecord,
    *,
    root: Path,
    target_revision: int,
    target_sha: str,
) -> str:
    snapshot = get_workspace_document_snapshot_unlocked(root, record.playable_artifact_id)
    if snapshot.record.document_id != record.playable_artifact_id:
        raise PlayRunRebaseError(
            "workspace document id does not match the Run binding",
            status_code=409,
        )
    if snapshot.record.campaign_id != record.campaign_id:
        raise PlayRunRebaseError(
            "workspace campaign_id does not match the Run campaign",
            status_code=409,
        )
    if snapshot.record.kind != "runbook":
        raise PlayRunRebaseError(
            "playable_artifact_id must identify a runbook workspace document",
            status_code=422,
        )
    if snapshot.record.status != "active":
        raise PlayRunRebaseError(
            "runbook workspace document is discarded",
            status_code=409,
        )
    if snapshot.record.content_status != "committed":
        raise PlayRunRebaseError(
            "runbook workspace document is not committed",
            status_code=409,
        )
    if not snapshot.file_exists:
        raise PlayRunRebaseError(
            "committed runbook workspace target file is missing",
            status_code=409,
        )
    if snapshot.loaded_revision != target_revision:
        raise PlayRunRebaseError(
            "playable revision mismatch: "
            f"expected {target_revision}, current {snapshot.loaded_revision}",
            status_code=409,
        )
    if snapshot.content_sha256 != target_sha:
        raise PlayRunRebaseError(
            "playable content SHA mismatch",
            status_code=409,
        )
    return snapshot.markdown


def _request_matches_intent(request: RebasePlayRunRequest, intent: PlayRunRebaseIntent) -> bool:
    return (
        request.expected_run_revision == intent.expected_source_run_revision
        and request.target_playable_revision == intent.target_run.playable_revision
        and request.target_playable_content_sha256
        == intent.target_run.playable_content_sha256
    )


def _write_intent(path: Path, intent: PlayRunRebaseIntent) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    try:
        write_json(path, intent.model_dump(mode="json"))
    except (OSError, TypeError, ValueError) as exc:
        raise PlayRunRebaseError(
            f"failed to persist Play Run rebase intent: {exc}",
            status_code=500,
        ) from exc


def _write_target_manifest(path: Path, manifest: PlayRunReferenceManifest) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    try:
        write_json(path, _dump_manifest(manifest))
    except (OSError, TypeError, ValueError) as exc:
        raise PlayRunRebaseError(
            f"failed to persist target Play Run reference manifest: {exc}",
            status_code=503,
        ) from exc


def _write_target_run(path: Path, record: PlayRunRecord) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    try:
        write_json(path, record.model_dump(mode="json"))
    except (OSError, TypeError, ValueError) as exc:
        raise PlayRunRebaseError(
            f"failed to persist target Play Run: {exc}",
            status_code=503,
        ) from exc


def _delete_intent(path: Path) -> None:
    try:
        path.unlink()
    except FileNotFoundError:
        return
    except OSError as exc:
        raise PlayRunRebaseError(
            f"failed to delete Play Run rebase intent: {exc}",
            status_code=503,
        ) from exc


def _classify_recovery_stage(
    *,
    run_path: Path,
    manifest_path: Path,
    intent: PlayRunRebaseIntent,
) -> Literal["prepared", "manifest_installed", "run_committed"]:
    current_run_token = registry_token(run_path)
    current_manifest_token = registry_token(manifest_path)
    target_run_token = _run_payload_token(intent.target_run)
    target_manifest_token = _manifest_payload_token(intent.target_manifest)

    if (
        current_run_token == target_run_token
        and current_manifest_token == target_manifest_token
    ):
        return "run_committed"
    if (
        current_run_token == intent.source_run_token
        and current_manifest_token == target_manifest_token
    ):
        return "manifest_installed"
    if current_run_token == intent.source_run_token and current_manifest_token == (
        intent.source_manifest_token
    ):
        return "prepared"
    raise PlayRunRebaseError(
        "contradictory Play Run rebase recovery state",
        status_code=500,
    )


def _complete_from_stage(
    *,
    run_path: Path,
    manifest_path: Path,
    intent_path: Path,
    intent: PlayRunRebaseIntent,
    stage: Literal["prepared", "manifest_installed", "run_committed"],
) -> PlayRunRecord:
    if stage == "prepared":
        _write_target_manifest(manifest_path, intent.target_manifest)
        stage = "manifest_installed"
    if stage == "manifest_installed":
        _write_target_run(run_path, intent.target_run)
        stage = "run_committed"
    _delete_intent(intent_path)
    return intent.target_run


def _resume_intent(
    *,
    root: Path,
    run_path: Path,
    manifest_path: Path,
    intent_path: Path,
    request: RebasePlayRunRequest,
) -> PlayRunRecord:
    intent = _load_intent(intent_path)
    if not _request_matches_intent(request, intent):
        raise PlayRunRebaseError(
            "a different Play Run rebase request is already pending",
            status_code=409,
        )
    with registry_mutation_lock(manifest_path):
        stage = _classify_recovery_stage(
            run_path=run_path,
            manifest_path=manifest_path,
            intent=intent,
        )
        return _complete_from_stage(
            run_path=run_path,
            manifest_path=manifest_path,
            intent_path=intent_path,
            intent=intent,
            stage=stage,
        )


def rebase_or_replay_play_run(
    root: Path,
    *,
    run_id: str,
    expected_run_revision: int,
    target_playable_revision: int,
    target_playable_content_sha256: str,
) -> PlayRunRecord:
    try:
        request = RebasePlayRunRequest(
            expected_run_revision=expected_run_revision,
            target_playable_revision=target_playable_revision,
            target_playable_content_sha256=target_playable_content_sha256,
        )
    except ValidationError as exc:
        raise PlayRunRebaseError(str(exc), status_code=422) from exc

    run_path = play_run_path(root, run_id)
    intent_path = play_run_rebase_intent_path(root, run_id)
    manifest_path = play_run_reference_manifest_path(root, run_id)

    with registry_mutation_lock(run_path):
        if intent_path.is_file():
            return _resume_intent(
                root=root,
                run_path=run_path,
                manifest_path=manifest_path,
                intent_path=intent_path,
                request=request,
            )
        if not run_path.is_file():
            raise PlayRunRebaseError(
                f"Play Run not found: {run_path.stem}",
                status_code=404,
            )
        try:
            record = _load_record(run_path)
        except PlayRunRegistryError as exc:
            _raise_registry(exc)

        if _same_target_binding(record, request):
            _prove_target_pair(root, record)
            if record.run_revision == request.expected_run_revision + 1:
                return record
            if record.run_revision == request.expected_run_revision:
                return record
            raise PlayRunRebaseError(
                "run_revision does not match the current Play Run",
                status_code=409,
            )

        if request.expected_run_revision != record.run_revision:
            raise PlayRunRebaseError(
                "run_revision does not match the current Play Run",
                status_code=409,
            )
        if request.target_playable_revision <= record.playable_revision:
            raise PlayRunRebaseError(
                "target_playable_revision must be strictly newer than the current Playable revision",
                status_code=409,
            )

        with registry_mutation_lock(manifest_path):
            source_manifest_token = registry_token(manifest_path)
            if source_manifest_token != _ABSENT_TOKEN:
                try:
                    source_manifest = _load_manifest(manifest_path)
                    _require_binding_match(source_manifest, record)
                except PlayRunReferenceManifestError as exc:
                    _raise_manifest(exc)
            elif not _progress_is_empty(record.progress):
                raise PlayRunRebaseError(
                    "Play Run reference manifest is required before rebasing non-empty progress",
                    status_code=409,
                )

            try:
                with workspace_document_mutation_lock(root, record.playable_artifact_id):
                    markdown = _admit_target_snapshot(
                        record,
                        root=root,
                        target_revision=request.target_playable_revision,
                        target_sha=request.target_playable_content_sha256,
                    )
                    try:
                        elements = sorted(
                            derive_play_run_reference_elements(markdown),
                            key=lambda element: element.element_id,
                        )
                    except PlayRunReferenceManifestError as exc:
                        _raise_manifest(exc)
                    sealed_at = _utc_now_iso()
                    updated_at = sealed_at
                    target_manifest = PlayRunReferenceManifest(
                        run_id=record.run_id,
                        playable_artifact_id=record.playable_artifact_id,
                        playable_revision=request.target_playable_revision,
                        playable_content_sha256=request.target_playable_content_sha256,
                        elements=elements,
                        sealed_at=sealed_at,
                    )
                    _admit_progress_for_rebase(record.progress, manifest=target_manifest)
                    target_run = record.model_copy(
                        update={
                            "playable_revision": request.target_playable_revision,
                            "playable_content_sha256": request.target_playable_content_sha256,
                            "run_revision": record.run_revision + 1,
                            "updated_at": updated_at,
                            "progress": record.progress,
                        }
                    )
                    intent = PlayRunRebaseIntent(
                        run_id=record.run_id,
                        expected_source_run_revision=record.run_revision,
                        source_playable_artifact_id=record.playable_artifact_id,
                        source_playable_revision=record.playable_revision,
                        source_playable_content_sha256=record.playable_content_sha256,
                        source_run_token=registry_token(run_path),
                        source_manifest_token=source_manifest_token,
                        target_run=target_run,
                        target_manifest=target_manifest,
                        prepared_at=sealed_at,
                    )
                    _write_intent(intent_path, intent)
                    return _complete_from_stage(
                        run_path=run_path,
                        manifest_path=manifest_path,
                        intent_path=intent_path,
                        intent=intent,
                        stage="prepared",
                    )
            except WorkspaceDocumentRegistryError as exc:
                raise PlayRunRebaseError(str(exc), status_code=exc.status_code) from exc
