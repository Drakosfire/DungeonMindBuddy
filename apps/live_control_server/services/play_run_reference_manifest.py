"""Immutable Play Runtime reference-admission manifests for P2A Runs."""

from __future__ import annotations

import re
import uuid
from datetime import UTC, datetime
from pathlib import Path
from typing import Literal, NamedTuple

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

PLAY_RUN_REFERENCE_MANIFEST_V2_SCHEMA = "dmb_play_run_reference_manifest_v2"
MARKER_V2_PROBE = "dmb-playable-element:v2"
_V2_ID_TAIL = r"[a-z0-9][a-z0-9._-]{0,127}"
_V2_ID_RE = r"((?:beat|scene|choice|option):" + _V2_ID_TAIL + r")"
_V2_SCENE_ID_RE = r"(scene:" + _V2_ID_TAIL + r")"
_V2_EDGE_LIST_RE = (
    r"((?:beat|scene):" + _V2_ID_TAIL + r"(?:,(?:beat|scene):" + _V2_ID_TAIL + r")*)"
)
V2_BEAT_MARKER_RE = re.compile(
    r"^<!-- dmb-playable-element:v2 kind=beat id=" + _V2_ID_RE
    + r"(?: beat_kind=(spine|optional|interrupt))? -->$"
)
V2_SCENE_MARKER_RE = re.compile(
    r"^<!-- dmb-playable-element:v2 kind=scene id=" + _V2_ID_RE + r" -->$"
)
V2_CHOICE_MARKER_RE = re.compile(
    r"^<!-- dmb-playable-element:v2 kind=choice id=" + _V2_ID_RE
    + r"(?: scene=" + _V2_SCENE_ID_RE + r")? -->$"
)
V2_OPTION_MARKER_RE = re.compile(
    r"^<!-- dmb-playable-element:v2 kind=option id=" + _V2_ID_RE
    + r"(?: activates=" + _V2_EDGE_LIST_RE + r")?"
    + r"(?: suppresses=" + _V2_EDGE_LIST_RE + r")? -->$"
)
V2_KIND_HEADING_LEVEL = {
    "beat": 2,
    "scene": 3,
    "choice": 3,
}
_LIST_ITEM_RE = re.compile(r"^(?:[-*+]|\d+[.)]) \S")
BEAT_KINDS = ("spine", "optional", "interrupt")


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


class PlayRunManifestV2Beat(BaseModel):
    model_config = ConfigDict(extra="forbid", strict=True)

    beat_id: str
    beat_kind: Literal["spine", "optional", "interrupt"] | None = None

    @field_validator("beat_id")
    @classmethod
    def _validate_beat_id(cls, value: str) -> str:
        return _canonical_playable_id("beat", value, field_name="beat_id")


class PlayRunManifestV2Scene(BaseModel):
    model_config = ConfigDict(extra="forbid", strict=True)

    scene_id: str
    beat_id: str

    @field_validator("scene_id")
    @classmethod
    def _validate_scene_id(cls, value: str) -> str:
        return _canonical_playable_id("scene", value, field_name="scene_id")

    @field_validator("beat_id")
    @classmethod
    def _validate_beat_id(cls, value: str) -> str:
        return _canonical_playable_id("beat", value, field_name="beat_id")


class PlayRunManifestV2Choice(BaseModel):
    model_config = ConfigDict(extra="forbid", strict=True)

    choice_id: str
    beat_id: str
    scene_id: str | None = None

    @field_validator("choice_id")
    @classmethod
    def _validate_choice_id(cls, value: str) -> str:
        return _canonical_playable_id("choice", value, field_name="choice_id")

    @field_validator("beat_id")
    @classmethod
    def _validate_beat_id(cls, value: str) -> str:
        return _canonical_playable_id("beat", value, field_name="beat_id")

    @field_validator("scene_id")
    @classmethod
    def _validate_scene_id(cls, value: str | None) -> str | None:
        if value is None:
            return None
        return _canonical_playable_id("scene", value, field_name="scene_id")


class PlayRunManifestV2Option(BaseModel):
    model_config = ConfigDict(extra="forbid", strict=True)

    option_id: str
    choice_id: str

    @field_validator("option_id")
    @classmethod
    def _validate_option_id(cls, value: str) -> str:
        return _canonical_playable_id("option", value, field_name="option_id")

    @field_validator("choice_id")
    @classmethod
    def _validate_choice_id(cls, value: str) -> str:
        return _canonical_playable_id("choice", value, field_name="choice_id")


class PlayRunManifestV2Edge(BaseModel):
    model_config = ConfigDict(extra="forbid", strict=True)

    option_id: str
    effect: Literal["activate", "suppress"]
    target_kind: Literal["beat", "scene"]
    target_id: str

    @field_validator("option_id")
    @classmethod
    def _validate_option_id(cls, value: str) -> str:
        return _canonical_playable_id("option", value, field_name="option_id")

    @field_validator("target_id")
    @classmethod
    def _validate_target_id(cls, value: str) -> str:
        if not PLAYABLE_ID_RE.fullmatch(value):
            raise ValueError("target_id must be a canonical beat or scene id")
        return value

    @model_validator(mode="after")
    def _validate_target_kind_matches_id(self) -> "PlayRunManifestV2Edge":
        if not self.target_id.startswith(f"{self.target_kind}:"):
            raise ValueError("target_id prefix must match target_kind")
        if self.target_kind not in {"beat", "scene"}:
            raise ValueError("target_kind must be beat or scene")
        return self


class PlayRunReferenceManifestV2(BaseModel):
    """Beat-first (v2) sealed Run reference manifest.

    Arrays are membership/inspection carriers sorted by id for determinism;
    they are not a document-order authority. Document order authority remains
    the bound revision bytes pinned by playable_content_sha256.
    """

    model_config = ConfigDict(extra="forbid", strict=True)

    schema_version: Literal["dmb_play_run_reference_manifest_v2"] = (
        PLAY_RUN_REFERENCE_MANIFEST_V2_SCHEMA
    )
    run_id: str
    playable_artifact_id: str
    playable_revision: int = Field(gt=0)
    playable_content_sha256: str
    sealed_at: str
    beats: list[PlayRunManifestV2Beat]
    scenes: list[PlayRunManifestV2Scene]
    choices: list[PlayRunManifestV2Choice]
    options: list[PlayRunManifestV2Option]
    edges: list[PlayRunManifestV2Edge]

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
    def _validate_membership(self) -> "PlayRunReferenceManifestV2":
        beat_ids = [beat.beat_id for beat in self.beats]
        scene_ids = [scene.scene_id for scene in self.scenes]
        choice_ids = [choice.choice_id for choice in self.choices]
        option_ids = [option.option_id for option in self.options]
        all_ids = beat_ids + scene_ids + choice_ids + option_ids
        if len(all_ids) != len(set(all_ids)):
            raise ValueError("manifest v2 element ids must be unique")
        for name, ids in (
            ("beats", beat_ids),
            ("scenes", scene_ids),
            ("choices", choice_ids),
            ("options", option_ids),
        ):
            if ids != sorted(ids):
                raise ValueError(f"manifest v2 {name} must be sorted by id")
        beat_set = set(beat_ids)
        scene_set = set(scene_ids)
        choice_set = set(choice_ids)
        option_set = set(option_ids)
        scene_beat = {scene.scene_id: scene.beat_id for scene in self.scenes}
        for scene in self.scenes:
            if scene.beat_id not in beat_set:
                raise ValueError("scene beat_id does not resolve to a Beat in this manifest")
        for choice in self.choices:
            if choice.beat_id not in beat_set:
                raise ValueError("choice beat_id does not resolve to a Beat in this manifest")
            if choice.scene_id is not None:
                if choice.scene_id not in scene_set:
                    raise ValueError("choice scene_id does not resolve to a Scene in this manifest")
                if scene_beat[choice.scene_id] != choice.beat_id:
                    raise ValueError("choice scene_id belongs to a different Beat than the choice")
        for option in self.options:
            if option.choice_id not in choice_set:
                raise ValueError("option choice_id does not resolve to a Choice in this manifest")
        for edge in self.edges:
            if edge.option_id not in option_set:
                raise ValueError("edge option_id does not resolve to an Option in this manifest")
            target_set = beat_set if edge.target_kind == "beat" else scene_set
            if edge.target_id not in target_set:
                raise ValueError("edge target_id does not resolve in this manifest")
        return self


AnyPlayRunReferenceManifest = PlayRunReferenceManifest | PlayRunReferenceManifestV2


def play_run_reference_manifests_dir(root: Path) -> Path:
    return root / PLAY_RUN_REFERENCE_MANIFESTS_REL


def play_run_reference_manifest_path(root: Path, run_id: str) -> Path:
    try:
        canonical = _canonical_uuid(run_id, field_name="run_id")
    except ValueError as exc:
        raise PlayRunReferenceManifestError(str(exc), status_code=422) from exc
    return play_run_reference_manifests_dir(root) / f"{canonical}.json"


def _dump_manifest(manifest: AnyPlayRunReferenceManifest) -> dict[str, object]:
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


class DerivedV2Membership(NamedTuple):
    beats: list[PlayRunManifestV2Beat]
    scenes: list[PlayRunManifestV2Scene]
    choices: list[PlayRunManifestV2Choice]
    options: list[PlayRunManifestV2Option]
    edges: list[PlayRunManifestV2Edge]


def detect_playable_grammar_version(markdown: str) -> int:
    """Return 2 when v2 structural directives are present, else 1.

    Marker lines themselves are validated by the versioned scanners; detection
    only chooses which scanner owns the document. A document with no markers
    stays on the legacy v1 path (empty membership).
    """
    normalized = markdown.replace("\ufeff", "").replace("\r\n", "\n").replace("\r", "\n")
    fence_char: str | None = None
    fence_length = 0
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
        if MARKER_V2_PROBE in line:
            return 2
    return 1


def _parse_v2_marker(line: str) -> tuple[str, str, dict[str, str]] | None:
    """Parse a canonical v2 marker. Returns (kind, id, attrs) or None."""
    beat = V2_BEAT_MARKER_RE.fullmatch(line)
    if beat is not None:
        attrs: dict[str, str] = {}
        if beat.group(2) is not None:
            attrs["beat_kind"] = beat.group(2)
        return "beat", beat.group(1), attrs
    scene = V2_SCENE_MARKER_RE.fullmatch(line)
    if scene is not None:
        return "scene", scene.group(1), {}
    choice = V2_CHOICE_MARKER_RE.fullmatch(line)
    if choice is not None:
        attrs = {}
        if choice.group(2) is not None:
            attrs["scene"] = choice.group(2)
        return "choice", choice.group(1), attrs
    option = V2_OPTION_MARKER_RE.fullmatch(line)
    if option is not None:
        attrs = {}
        if option.group(2) is not None:
            attrs["activates"] = option.group(2)
        if option.group(3) is not None:
            attrs["suppresses"] = option.group(3)
        return "option", option.group(1), attrs
    return None


def derive_play_run_reference_elements_v2(markdown: str) -> DerivedV2Membership:
    """Fail-closed Beat-first (v2) marker/membership scan.

    Grammar: beat on H2; scene/choice on H3 as Beat-owned siblings; option as
    a marked list item inside the current choice body. Any playable marker
    line that is not canonical v2 (including v1 markers) fails closed, which
    is what makes mixed-version documents unsealable.
    """
    normalized = markdown.replace("\ufeff", "").replace("\r\n", "\n").replace("\r", "\n")
    lines = normalized.split("\n")
    pending: tuple[str, str, dict[str, str]] | None = None
    fence_char: str | None = None
    fence_length = 0
    seen_ids: set[str] = set()
    current_beat_id: str | None = None
    current_choice_id: str | None = None
    scenes_in_current_beat: set[str] = set()
    beats: list[PlayRunManifestV2Beat] = []
    scenes: list[PlayRunManifestV2Scene] = []
    choices: list[PlayRunManifestV2Choice] = []
    options: list[PlayRunManifestV2Option] = []
    edges: list[PlayRunManifestV2Edge] = []

    def fail(message: str) -> None:
        raise PlayRunReferenceManifestError(message, status_code=409)

    def admit_heading(kind: str, element_id: str, attrs: dict[str, str]) -> None:
        nonlocal current_beat_id, current_choice_id, scenes_in_current_beat
        if element_id in seen_ids:
            fail(f"duplicate playable element id: {element_id}")
        seen_ids.add(element_id)
        if kind == "beat":
            current_beat_id = element_id
            current_choice_id = None
            scenes_in_current_beat = set()
            beat_kind = attrs.get("beat_kind")
            beats.append(
                PlayRunManifestV2Beat(
                    beat_id=element_id,
                    beat_kind=beat_kind if beat_kind in BEAT_KINDS else None,
                )
            )
            return
        if current_beat_id is None:
            fail(f"orphan {kind} has no preceding marked Beat: {element_id}")
        if kind == "scene":
            current_choice_id = None
            scenes_in_current_beat.add(element_id)
            scenes.append(
                PlayRunManifestV2Scene(scene_id=element_id, beat_id=current_beat_id)
            )
            return
        # choice
        current_choice_id = element_id
        scene_ref = attrs.get("scene")
        if scene_ref is not None and scene_ref not in scenes_in_current_beat:
            fail(
                "choice scene association must reference a Scene in the same Beat: "
                f"{element_id} -> {scene_ref}"
            )
        choices.append(
            PlayRunManifestV2Choice(
                choice_id=element_id,
                beat_id=current_beat_id,
                scene_id=scene_ref,
            )
        )

    def admit_option(element_id: str, attrs: dict[str, str]) -> None:
        if element_id in seen_ids:
            fail(f"duplicate playable element id: {element_id}")
        seen_ids.add(element_id)
        if current_choice_id is None:
            fail(f"orphan option has no active marked Choice: {element_id}")
        options.append(
            PlayRunManifestV2Option(option_id=element_id, choice_id=current_choice_id)
        )
        activated = attrs.get("activates", "")
        suppressed = attrs.get("suppresses", "")
        activated_ids = activated.split(",") if activated else []
        suppressed_ids = suppressed.split(",") if suppressed else []
        for effect, targets in (("activate", activated_ids), ("suppress", suppressed_ids)):
            if len(targets) != len(set(targets)):
                fail(f"duplicate {effect} target on option: {element_id}")
            for target in targets:
                target_kind = target.split(":", 1)[0]
                edges.append(
                    PlayRunManifestV2Edge(
                        option_id=element_id,
                        effect=effect,
                        target_kind=target_kind,
                        target_id=target,
                    )
                )
        overlap = set(activated_ids) & set(suppressed_ids)
        if overlap:
            fail(
                "option activates and suppresses the same target: "
                f"{element_id} -> {sorted(overlap)[0]}"
            )

    for line in lines:
        if fence_char is not None:
            if _closes_fence(line, fence_char, fence_length):
                fence_char = None
                fence_length = 0
            continue
        opening = _opening_fence(line)
        if opening is not None:
            if pending is not None:
                fail("playable element marker is orphaned; it must immediately precede its element")
            fence_char, fence_length = opening
            continue
        if MARKER_PREFIX in line:
            if pending is not None:
                fail("playable element marker is orphaned; it must immediately precede its element")
            parsed = _parse_v2_marker(line)
            if parsed is None:
                fail("non-canonical or mixed-version dmb-playable-element marker outside fenced code")
            kind, element_id, attrs = parsed
            if not element_id.startswith(f"{kind}:"):
                fail("playable element id does not match marker kind")
            pending = (kind, element_id, attrs)
            continue
        if pending is None:
            continue
        kind, element_id, attrs = pending
        if kind == "option":
            if _LIST_ITEM_RE.match(line) is None:
                fail("option marker must immediately precede a marked list item")
            admit_option(element_id, attrs)
            pending = None
            continue
        heading = ATX_HEADING_RE.fullmatch(line)
        if heading is None:
            fail("playable element marker is orphaned; it must immediately precede a heading")
        level = len(heading.group(1))
        expected = V2_KIND_HEADING_LEVEL[kind]
        if level != expected:
            fail(
                "playable element kind does not match heading level: "
                f"{kind} expected H{expected}"
            )
        admit_heading(kind, element_id, attrs)
        pending = None

    if pending is not None:
        fail("playable element marker is orphaned; it must immediately precede its element")

    known_beat_ids = {beat.beat_id for beat in beats}
    known_scene_ids = {scene.scene_id for scene in scenes}
    for edge in edges:
        known = known_beat_ids if edge.target_kind == "beat" else known_scene_ids
        if edge.target_id not in known:
            fail(f"transition edge targets an unknown id: {edge.target_id}")

    return DerivedV2Membership(
        beats=sorted(beats, key=lambda beat: beat.beat_id),
        scenes=sorted(scenes, key=lambda scene: scene.scene_id),
        choices=sorted(choices, key=lambda choice: choice.choice_id),
        options=sorted(options, key=lambda option: option.option_id),
        edges=sorted(edges, key=lambda edge: (edge.option_id, edge.effect, edge.target_id)),
    )


def _load_manifest(path: Path) -> AnyPlayRunReferenceManifest:
    try:
        expected_run_id = path.stem
        payload = load_json(path)
        if not isinstance(payload, dict):
            raise ValueError("manifest payload must be a JSON object")
        schema_version = payload.get("schema_version")
        manifest: AnyPlayRunReferenceManifest
        if schema_version == PLAY_RUN_REFERENCE_MANIFEST_SCHEMA:
            manifest = PlayRunReferenceManifest.model_validate(payload)
        elif schema_version == PLAY_RUN_REFERENCE_MANIFEST_V2_SCHEMA:
            manifest = PlayRunReferenceManifestV2.model_validate(payload)
        else:
            raise ValueError(f"unknown manifest schema version: {schema_version!r}")
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


def _require_binding_match(manifest: AnyPlayRunReferenceManifest, record: PlayRunRecord) -> None:
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
) -> AnyPlayRunReferenceManifest:
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


def get_play_run_reference_manifest(root: Path, run_id: str) -> AnyPlayRunReferenceManifest:
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
) -> AnyPlayRunReferenceManifest:
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
                    manifest: AnyPlayRunReferenceManifest
                    if detect_playable_grammar_version(markdown) == 2:
                        membership = derive_play_run_reference_elements_v2(markdown)
                        manifest = PlayRunReferenceManifestV2(
                            run_id=record.run_id,
                            playable_artifact_id=record.playable_artifact_id,
                            playable_revision=record.playable_revision,
                            playable_content_sha256=record.playable_content_sha256,
                            sealed_at=_utc_now_iso(),
                            beats=membership.beats,
                            scenes=membership.scenes,
                            choices=membership.choices,
                            options=membership.options,
                            edges=membership.edges,
                        )
                    else:
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
