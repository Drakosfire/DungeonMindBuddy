"""Pure native Play intent and actually supplied source commitments.

Not registered with durable Turn codecs yet. These values do not resolve an
edition, admit a Turn, authorize a provider or grant Graph/played-truth authority.
"""
from __future__ import annotations

from hashlib import sha256
from typing import Annotated, Literal

from pydantic import ConfigDict, Field, model_validator

from .types import (PlayContentBasis, PlayRunTurnContextReceiptV2,
                    SubmittedPrimaryWorkIntentV1, SubmittedTurnIntentV1)
from .rules_authority_types import ClosedRulesModel, Digest, canonical_bytes, canonical_sha256

MarkerBeat = Annotated[str, Field(pattern=r"^beat:[a-z0-9][a-z0-9._-]{0,127}$")]
MarkerScene = Annotated[str, Field(pattern=r"^scene:[a-z0-9][a-z0-9._-]{0,127}$")]
OwnerId = Annotated[str, Field(min_length=1, max_length=128)]
SourceKind = Literal["current_moment", "scene_note"]


class PlayGraphPolicyV1(ClosedRulesModel):
    schema_: Literal["dmb_play_graph_policy_v1"] = Field(default="dmb_play_graph_policy_v1", alias="schema")
    policy: Literal["native_play_world_v1"] = "native_play_world_v1"


class SubmittedPlayTargetV1(ClosedRulesModel):
    schema_: Literal["dmb_submitted_play_target_v1"] = Field(default="dmb_submitted_play_target_v1", alias="schema")
    beat_id: MarkerBeat
    scene_id: MarkerScene | None
    marker_grammar_version: Literal["v2"] = "v2"


class PlayGraphIntentV1(SubmittedTurnIntentV1):
    model_config = ConfigDict(extra="forbid", frozen=True, revalidate_instances="always")
    schema_: Literal["dmb_play_graph_intent_v1"] = Field(default="dmb_play_graph_intent_v1", alias="schema")
    surface_id: Literal["play"]
    client_work_state: Literal["saved_clean", "saved_dirty"]
    primary_work: SubmittedPrimaryWorkIntentV1
    play_graph_policy: PlayGraphPolicyV1
    play_target: SubmittedPlayTargetV1
    playable_target: None = None
    selected_knowledge: None = None
    graph_selection: None = None

    @model_validator(mode="after")
    def exact_native_play_intent(self):
        ref, graph = self.primary_work, self.graph_request
        if (ref.kind != "run" or ref.play_content_basis is None
                or graph.mode != "world" or graph.campaign_id is not None
                or graph.focus is None or graph.focus.kind != "none"):
            raise ValueError("Native Play Graph requires exact Run edition and World-only intent")
        return self


def play_graph_intent_fingerprint(intent: PlayGraphIntentV1) -> str:
    """New explicit protocol; never reinterprets a historical intent algorithm."""
    checked = PlayGraphIntentV1.model_validate_json(intent.model_dump_json(by_alias=True))
    return canonical_sha256(checked.model_dump(mode="json", by_alias=True, exclude={"client_thread_id"}))


class PlaySourceLocatorV1(ClosedRulesModel):
    world_id: OwnerId
    run_id: OwnerId
    run_revision: Annotated[int, Field(ge=1)]
    edition: PlayContentBasis
    beat_id: MarkerBeat
    scene_id: MarkerScene | None

    @model_validator(mode="after")
    def canonical_owner(self):
        if any(value != value.strip() for value in (self.world_id, self.run_id)):
            raise ValueError("Play source owners must be canonical")
        return self


class PlaySourcePayloadV1(ClosedRulesModel):
    schema_: Literal["dmb_play_source_payload_v1"] = Field(default="dmb_play_source_payload_v1", alias="schema")
    source_kind: SourceKind
    locator: PlaySourceLocatorV1
    text: Annotated[str, Field(min_length=1, max_length=32000)]

    @model_validator(mode="after")
    def bounded_source(self):
        if (not self.text.strip() or len(self.text.encode("utf-8")) > 32768
                or len(canonical_bytes(self)) > 49152):
            raise ValueError("Play source exceeds its text/payload budget or is blank")
        if self.source_kind == "scene_note" and self.locator.scene_id is None:
            raise ValueError("Saved scene-note source requires a selected Scene")
        return self


class PlaySourceManifestEntryV1(ClosedRulesModel):
    source_id: Annotated[str, Field(pattern=r"^play-source:[a-f0-9]{64}$")]
    source_kind: SourceKind
    locator: PlaySourceLocatorV1
    payload_sha256: Digest
    payload_utf8_bytes: Annotated[int, Field(ge=1, le=49152)]
    text_sha256: Digest
    text_utf8_bytes: Annotated[int, Field(ge=1, le=32768)]
    text_codepoints: Annotated[int, Field(ge=1, le=32000)]

    @model_validator(mode="after")
    def source_identity(self):
        if self.source_id != "play-source:" + self.payload_sha256:
            raise ValueError("Play source handle differs from its exact payload")
        return self


def source_entry(payload: PlaySourcePayloadV1) -> PlaySourceManifestEntryV1:
    checked = PlaySourcePayloadV1.model_validate_json(payload.model_dump_json(by_alias=True))
    raw, text = canonical_bytes(checked), checked.text.encode("utf-8")
    digest = sha256(raw).hexdigest()
    return PlaySourceManifestEntryV1(source_id="play-source:" + digest,
        source_kind=checked.source_kind, locator=checked.locator,
        payload_sha256=digest, payload_utf8_bytes=len(raw),
        text_sha256=sha256(text).hexdigest(), text_utf8_bytes=len(text), text_codepoints=len(checked.text))


class PlaySourceManifestV1(ClosedRulesModel):
    schema_: Literal["dmb_play_source_manifest_v1"] = Field(default="dmb_play_source_manifest_v1", alias="schema")
    entries: Annotated[tuple[PlaySourceManifestEntryV1, ...], Field(max_length=2)]
    manifest_sha256: Digest

    @model_validator(mode="after")
    def sealed_manifest(self):
        ids = [entry.source_id for entry in self.entries]
        if ids != sorted(set(ids)):
            raise ValueError("Play source manifest must be sorted and distinct")
        payload = self.model_dump(mode="json", by_alias=True, exclude={"manifest_sha256"})
        if self.manifest_sha256 != canonical_sha256(payload):
            raise ValueError("Play source manifest seal differs")
        return self


class PlaySourceFrameV1(ClosedRulesModel):
    schema_: Literal["dmb_play_source_frame_v1"] = Field(default="dmb_play_source_frame_v1", alias="schema")
    manifest: PlaySourceManifestV1
    sources: Annotated[tuple[PlaySourcePayloadV1, ...], Field(max_length=2)]

    @model_validator(mode="after")
    def exact_supplied_sources(self):
        if tuple(source_entry(source) for source in self.sources) != self.manifest.entries:
            raise ValueError("Play frame source bodies differ from its manifest")
        if len(canonical_bytes(self)) > 65536:
            raise ValueError("Play source frame exceeds its UTF8 budget")
        return self


def play_source_frame(sources: tuple[PlaySourcePayloadV1, ...]) -> PlaySourceFrameV1:
    pairs = sorted(((source_entry(source), source) for source in sources), key=lambda pair: pair[0].source_id)
    entries = tuple(entry for entry, _ in pairs)
    seal = canonical_sha256({"schema": "dmb_play_source_manifest_v1", "entries": [entry.model_dump(mode="json", by_alias=True) for entry in entries]})
    return PlaySourceFrameV1(manifest=PlaySourceManifestV1(entries=entries, manifest_sha256=seal),
        sources=tuple(source for _, source in pairs))


def validate_play_source_owner_join(frame: PlaySourceFrameV1, basis: PlayRunTurnContextReceiptV2,
                                    *, owner_resolved_current_moment_text: str | None) -> None:
    """Check exact owner values, NOT obtain their authority or prove provider inclusion.

    Admission must supply the independently Run/edition-owner-resolved basis/text.
    Passing arbitrary model/caller text here cannot turn it into source authority.
    Actual first/final provider input inclusion remains a separate required proof.
    """
    checked = PlaySourceFrameV1.model_validate_json(frame.model_dump_json(by_alias=True))
    basis = PlayRunTurnContextReceiptV2.model_validate_json(basis.model_dump_json(by_alias=True))
    expected = (basis.world_id, basis.run_id, basis.run_revision, basis.edition_revision,
        basis.edition_revision_id, basis.content_sha256, basis.beat_id, basis.scene_id)
    kinds = set()
    for source in checked.sources:
        loc = source.locator
        actual = (loc.world_id, loc.run_id, loc.run_revision, loc.edition.edition_revision,
            loc.edition.edition_revision_id, loc.edition.content_sha256, loc.beat_id, loc.scene_id)
        if actual != expected or source.source_kind in kinds:
            raise ValueError("Play source differs from its exact owning Run/edition/target")
        kinds.add(source.source_kind)
        text = basis.scene_note if source.source_kind == "scene_note" else owner_resolved_current_moment_text
        if text is None or source.text != text:
            raise ValueError("Play source body was not supplied by its independent source owner")
