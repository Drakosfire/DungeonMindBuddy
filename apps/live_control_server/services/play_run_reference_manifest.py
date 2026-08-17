"""Immutable Play Runtime reference-admission manifests for P2A Runs."""

from __future__ import annotations

import re
import uuid
from datetime import UTC, datetime
from pathlib import Path
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, ValidationError, field_validator, model_validator

from apps.live_control_server.services.play_run_registry import (
    PlayRunRecord,
    PlayRunRegistryError,
    _load_authoritative_record,
    _require_no_pending_rebase,
    play_run_path,
)
from apps.live_control_server.services.registry_file_lock import (
    registry_mutation_lock,
    workspace_document_mutation_lock,
)
from apps.live_control_server.services.workspace_document_registry import (
    WorkspaceDocumentRegistryError,
    get_workspace_document_snapshot_unlocked,
)
from src.live_play.live_store import load_json, write_json

PLAY_RUN_REFERENCE_MANIFEST_SCHEMA = "dmb_play_run_reference_manifest_v1"
PLAY_RUN_REFERENCE_MANIFESTS_REL = "out/runtime/play/reference-manifests"
MARKER_PREFIX = "dmb-playable-element:"
CANONICAL_MARKER_RE = re.compile(
    r"^<!-- dmb-playable-element:v1 kind=(scene|beat|choice|option) "
    r"id=((?:scene|beat|choice|option):[a-z0-9][a-z0-9._-]{0,127}) -->$"
)
PLAYABLE_ID_RE = re.compile(r"^(scene|beat|choice|option):[a-z0-9][a-z0-9._-]{0,127}$")
ATX_HEADING_RE = re.compile(r"^(#{2,4}) (.+)$")
_FENCE_OPEN_RE = re.compile(r"^( {0,3})(`{3,}|~{3,})(.*)$")
_FENCE_CLOSE_RE = re.compile(r"^( {0,3})(`{3,}|~{3,})[ \t]*$")
_SHA256_RE = re.compile(r"^[0-9a-f]{64}$")
KIND_HEADING_LEVEL = {
    "scene": 2,
    "beat": 3,
    "choice": 3,
    "option": 4,
}


class PlayRunReferenceManifestError(ValueError):
    """Fail-closed error for Run-bound reference-manifest operations."""

    status_code: int = 500

    def __init__(self, message: str, *, status_code: int = 500) -> None:
        super().__init__(message)
        self.status_code = status_code


def _utc_now_iso() -> str:
    return datetime.now(UTC).isoformat().replace("+00:00", "Z")


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


def _utc_iso(value: str) -> str:
    cleaned = value.strip()
    if not cleaned.endswith("Z"):
        raise ValueError("timestamp must be an ISO-8601 UTC value ending in Z")
    try:
        parsed = datetime.fromisoformat(cleaned[:-1] + "+00:00")
    except ValueError as exc:
        raise ValueError("timestamp must be an ISO-8601 UTC value") from exc
    if parsed.utcoffset() != UTC.utcoffset(parsed):
        raise ValueError("timestamp must be UTC")
    return cleaned


def _canonical_playable_id(kind: str, element_id: str, *, field_name: str) -> str:
    if not PLAYABLE_ID_RE.fullmatch(element_id) or not element_id.startswith(f"{kind}:"):
        raise ValueError(f"{field_name} must be a canonical {kind} id")
    return element_id


class PlayRunReferenceElement(BaseModel):
    model_config = ConfigDict(extra="forbid", strict=True)

    kind: Literal["scene", "beat", "choice", "option"]
    element_id: str
    scene_id: str | None = None
    choice_id: str | None = None

    @model_validator(mode="after")
    def _validate_membership(self) -> PlayRunReferenceElement:
        _canonical_playable_id(self.kind, self.element_id, field_name="element_id")
        if self.kind == "scene":
            if self.scene_id is not None or self.choice_id is not None:
                raise ValueError("scene must not include scene_id or choice_id")
            return self
        if self.scene_id is None:
            raise ValueError(f"{self.kind} requires scene_id")
        _canonical_playable_id("scene", self.scene_id, field_name="scene_id")
        if self.kind == "option":
            if self.choice_id is None:
                raise ValueError("option requires choice_id")
            _canonical_playable_id("choice", self.choice_id, field_name="choice_id")
            return self
        if self.choice_id is not None:
            raise ValueError(f"{self.kind} must not include choice_id")
        return self


class PlayRunReferenceManifest(BaseModel):
    model_config = ConfigDict(extra="forbid", strict=True)

    schema_version: Literal["dmb_play_run_reference_manifest_v1"] = (
        PLAY_RUN_REFERENCE_MANIFEST_SCHEMA
    )
    run_id: str
    playable_artifact_id: str
    playable_revision: int = Field(gt=0)
    playable_content_sha256: str
    elements: list[PlayRunReferenceElement]
    sealed_at: str

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
    def _validate_sha(cls, value: str) -> str:
        return _canonical_sha256(value, field_name="playable_content_sha256")

    @field_validator("sealed_at")
    @classmethod
    def _validate_timestamp(cls, value: str) -> str:
        return _utc_iso(value)

    @model_validator(mode="after")
    def _validate_elements(self) -> PlayRunReferenceManifest:
        ids = [element.element_id for element in self.elements]
        if len(ids) != len(set(ids)):
            raise ValueError("manifest elements must have unique element_id values")
        if ids != sorted(ids):
            raise ValueError("manifest elements must be sorted lexicographically by element_id")
        by_id = {element.element_id: element for element in self.elements}
        for element in self.elements:
            if element.kind in {"beat", "choice"}:
                scene = by_id.get(element.scene_id or "")
                if scene is None or scene.kind != "scene":
                    raise ValueError(
                        f"{element.kind} scene_id does not resolve to a Scene in this manifest"
                    )
            if element.kind == "option":
                scene = by_id.get(element.scene_id or "")
                choice = by_id.get(element.choice_id or "")
                if scene is None or scene.kind != "scene":
                    raise ValueError(
                        "option scene_id does not resolve to a Scene in this manifest"
                    )
                if choice is None or choice.kind != "choice":
                    raise ValueError(
                        "option choice_id does not resolve to a Choice in this manifest"
                    )
                if choice.scene_id != element.scene_id:
                    raise ValueError(
                        "option choice_id belongs to a different Scene than option scene_id"
                    )
        return self


def play_run_reference_manifests_dir(root: Path) -> Path:
    return root / PLAY_RUN_REFERENCE_MANIFESTS_REL


def play_run_reference_manifest_path(root: Path, run_id: str) -> Path:
    try:
        canonical = _canonical_uuid(run_id, field_name="run_id")
    except ValueError as exc:
        raise PlayRunReferenceManifestError(str(exc), status_code=422) from exc
    return play_run_reference_manifests_dir(root) / f"{canonical}.json"


def _dump_manifest(manifest: PlayRunReferenceManifest) -> dict[str, object]:
    return manifest.model_dump(mode="json", exclude_none=True)


def _opening_fence(line: str) -> tuple[str, int] | None:
    match = _FENCE_OPEN_RE.fullmatch(line)
    if match is None:
        return None
    marker = match.group(2)
    info = match.group(3)
    char = marker[0]
    if char == "`" and "`" in info:
        return None
    return char, len(marker)


def _closes_fence(line: str, char: str, length: int) -> bool:
    match = _FENCE_CLOSE_RE.fullmatch(line)
    if match is None:
        return False
    marker = match.group(2)
    return marker[0] == char and len(marker) >= length


def derive_play_run_reference_elements(markdown: str) -> list[PlayRunReferenceElement]:
    """Fail-closed P1 marker/membership scan. Returns unsorted elements."""
    normalized = markdown.replace("\ufeff", "").replace("\r\n", "\n").replace("\r", "\n")
    lines = normalized.split("\n")
    pending_kind: str | None = None
    pending_id: str | None = None
    fence_char: str | None = None
    fence_length = 0
    seen_ids: set[str] = set()
    current_scene_id: str | None = None
    current_choice_id: str | None = None
    derived: list[PlayRunReferenceElement] = []

    def fail(message: str) -> None:
        raise PlayRunReferenceManifestError(message, status_code=409)

    def admit(kind: str, element_id: str) -> None:
        nonlocal current_scene_id, current_choice_id
        if element_id in seen_ids:
            fail(f"duplicate playable element id: {element_id}")
        seen_ids.add(element_id)
        if kind == "scene":
            current_scene_id = element_id
            current_choice_id = None
            derived.append(PlayRunReferenceElement(kind="scene", element_id=element_id))
            return
        if current_scene_id is None:
            fail(f"orphan {kind} has no preceding marked Scene: {element_id}")
        if kind == "beat":
            current_choice_id = None
            derived.append(
                PlayRunReferenceElement(
                    kind="beat",
                    element_id=element_id,
                    scene_id=current_scene_id,
                )
            )
            return
        if kind == "choice":
            current_choice_id = element_id
            derived.append(
                PlayRunReferenceElement(
                    kind="choice",
                    element_id=element_id,
                    scene_id=current_scene_id,
                )
            )
            return
        if current_choice_id is None:
            fail(f"orphan option has no active marked Choice: {element_id}")
        derived.append(
            PlayRunReferenceElement(
                kind="option",
                element_id=element_id,
                scene_id=current_scene_id,
                choice_id=current_choice_id,
            )
        )

    for line in lines:
        if fence_char is not None:
            if _closes_fence(line, fence_char, fence_length):
                fence_char = None
                fence_length = 0
            continue
        opening = _opening_fence(line)
        if opening is not None:
            if pending_kind is not None:
                fail("playable element marker is orphaned; it must immediately precede a heading")
            fence_char, fence_length = opening
            continue
        if MARKER_PREFIX in line:
            if pending_kind is not None:
                fail("playable element marker is orphaned; it must immediately precede a heading")
            match = CANONICAL_MARKER_RE.fullmatch(line)
            if match is None:
                fail("non-canonical dmb-playable-element marker outside fenced code")
            kind, element_id = match.group(1), match.group(2)
            if not element_id.startswith(f"{kind}:"):
                fail("playable element id does not match marker kind")
            pending_kind = kind
            pending_id = element_id
            continue
        if pending_kind is None:
            continue
        heading = ATX_HEADING_RE.fullmatch(line)
        if heading is None:
            fail("playable element marker is orphaned; it must immediately precede a heading")
        level = len(heading.group(1))
        if level != KIND_HEADING_LEVEL[pending_kind]:
            fail(
                "playable element kind does not match heading level: "
                f"{pending_kind} expected H{KIND_HEADING_LEVEL[pending_kind]}"
            )
        admit(pending_kind, pending_id or "")
        pending_kind = None
        pending_id = None

    if pending_kind is not None:
        fail("playable element marker is orphaned; it must immediately precede a heading")
    return derived


def _load_manifest(path: Path) -> PlayRunReferenceManifest:
    try:
        expected_run_id = path.stem
        payload = load_json(path)
        manifest = PlayRunReferenceManifest.model_validate(payload)
        if manifest.run_id != expected_run_id:
            raise ValueError(
                "persisted run_id does not match the manifest file name: "
                f"{manifest.run_id} != {expected_run_id}"
            )
        return manifest
    except (OSError, TypeError, ValueError, ValidationError) as exc:
        raise PlayRunReferenceManifestError(
            f"malformed persisted Play Run reference manifest {path.name}: {exc}",
            status_code=500,
        ) from exc


def _require_binding_match(manifest: PlayRunReferenceManifest, record: PlayRunRecord) -> None:
    if (
        manifest.run_id != record.run_id
        or manifest.playable_artifact_id != record.playable_artifact_id
        or manifest.playable_revision != record.playable_revision
        or manifest.playable_content_sha256 != record.playable_content_sha256
    ):
        raise PlayRunReferenceManifestError(
            "persisted reference manifest identity does not match the Run binding",
            status_code=500,
        )


def load_play_run_reference_manifest_for_record(
    root: Path,
    record: PlayRunRecord,
) -> PlayRunReferenceManifest:
    """Load and bind-check the sealed sidecar for an already-loaded Run record.

    Does not consult workspace state and does not re-enter Run GET.
    """
    path = play_run_reference_manifest_path(root, record.run_id)
    if not path.is_file():
        raise PlayRunReferenceManifestError(
            f"Play Run reference manifest not found: {record.run_id}",
            status_code=404,
        )
    manifest = _load_manifest(path)
    _require_binding_match(manifest, record)
    return manifest


def get_play_run_reference_manifest(root: Path, run_id: str) -> PlayRunReferenceManifest:
    run_file = play_run_path(root, run_id)
    with registry_mutation_lock(run_file):
        _require_no_pending_rebase(root, run_id)
        if not run_file.is_file():
            raise PlayRunRegistryError(
                f"Play Run not found: {run_file.stem}",
                status_code=404,
            )
        record = _load_authoritative_record(root, run_file)
        return load_play_run_reference_manifest_for_record(root, record)


def _admit_snapshot(record: PlayRunRecord, root: Path) -> str:
    snapshot = get_workspace_document_snapshot_unlocked(root, record.playable_artifact_id)
    if snapshot.record.document_id != record.playable_artifact_id:
        raise PlayRunReferenceManifestError(
            "workspace document id does not match the Run binding",
            status_code=409,
        )
    if snapshot.record.kind != "runbook":
        raise PlayRunReferenceManifestError(
            "playable_artifact_id must identify a runbook workspace document",
            status_code=422,
        )
    if snapshot.record.status != "active":
        raise PlayRunReferenceManifestError(
            "runbook workspace document is discarded",
            status_code=409,
        )
    if snapshot.record.content_status != "committed":
        raise PlayRunReferenceManifestError(
            "runbook workspace document is not committed",
            status_code=409,
        )
    if not snapshot.file_exists:
        raise PlayRunReferenceManifestError(
            "committed runbook workspace target file is missing",
            status_code=409,
        )
    if snapshot.loaded_revision != record.playable_revision:
        raise PlayRunReferenceManifestError(
            "playable revision mismatch: "
            f"expected {record.playable_revision}, current {snapshot.loaded_revision}",
            status_code=409,
        )
    if snapshot.content_sha256 != record.playable_content_sha256:
        raise PlayRunReferenceManifestError(
            "playable content SHA mismatch",
            status_code=409,
        )
    return snapshot.markdown


def seal_or_replay_play_run_reference_manifest(
    root: Path,
    run_id: str,
) -> PlayRunReferenceManifest:
    run_file = play_run_path(root, run_id)
    with registry_mutation_lock(run_file):
        _require_no_pending_rebase(root, run_id)
        if not run_file.is_file():
            raise PlayRunRegistryError(
                f"Play Run not found: {run_file.stem}",
                status_code=404,
            )
        record = _load_authoritative_record(root, run_file)
        path = play_run_reference_manifest_path(root, record.run_id)

        with registry_mutation_lock(path):
            if path.is_file():
                manifest = _load_manifest(path)
                _require_binding_match(manifest, record)
                return manifest

            try:
                with workspace_document_mutation_lock(root, record.playable_artifact_id):
                    if path.is_file():
                        manifest = _load_manifest(path)
                        _require_binding_match(manifest, record)
                        return manifest

                    markdown = _admit_snapshot(record, root)
                    elements = sorted(
                        derive_play_run_reference_elements(markdown),
                        key=lambda element: element.element_id,
                    )
                    manifest = PlayRunReferenceManifest(
                        run_id=record.run_id,
                        playable_artifact_id=record.playable_artifact_id,
                        playable_revision=record.playable_revision,
                        playable_content_sha256=record.playable_content_sha256,
                        elements=elements,
                        sealed_at=_utc_now_iso(),
                    )
                    path.parent.mkdir(parents=True, exist_ok=True)
                    try:
                        write_json(path, _dump_manifest(manifest))
                    except (OSError, TypeError, ValueError) as exc:
                        raise PlayRunReferenceManifestError(
                            f"failed to persist Play Run reference manifest: {exc}",
                            status_code=500,
                        ) from exc
                    return manifest
            except WorkspaceDocumentRegistryError as exc:
                raise PlayRunReferenceManifestError(
                    str(exc),
                    status_code=exc.status_code,
                ) from exc
            except PlayRunRegistryError as exc:
                raise PlayRunReferenceManifestError(
                    str(exc),
                    status_code=exc.status_code,
                ) from exc
