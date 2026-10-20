"""Pure native Play receipts and joins; no durable codec or provider dispatch.

Every owner value here still requires independent SERVER/APP resolution before
admission. These checks do not make caller-supplied metadata authoritative.
"""
from __future__ import annotations

import json
from dataclasses import dataclass
from typing import Annotated, Literal

from pydantic import Field, model_validator

from .play_graph_authority import (
    PlayGraphIntentV1, PlayGraphPolicyV1, PlaySourceFrameV1, PlaySourceLocatorV1,
    PlaySourceManifestV1, PlaySourcePayloadV1, PlayWorldGraphExecutionV1,
    NativePlayGraphPolicyV1, PlayGraphExecutionEventV1,
    source_entry, validate_play_source_owner_join,
)
from .rules_authority_types import ClosedRulesModel, Digest, canonical_bytes, canonical_sha256
from .types import (
    PlanWorldGraphAssembledInputV1, PlanWorldGraphAuthorityV1,
    PlanWorldGraphPacketV1, PlanWorldGraphSourceTokenAccountingV1,
    PlayContentBasis, PlayRunTurnContextReceiptV2,
    ProviderAttemptAuthorizedEventV1, ProviderAttemptAuthorizedEventV3,
    SourceScopeExtensionEventV3, validate_graph_packet_input,
    validate_graph_provider_envelope, validate_related_recap_context_scope_record,
)


class PlayWorldGraphPacketV1(PlanWorldGraphPacketV1):
    schema_: Literal["dmb_play_world_graph_packet_v1"] = Field(
        default="dmb_play_world_graph_packet_v1", alias="schema")


class PlayGraphSourceTokenAccountingV1(PlanWorldGraphSourceTokenAccountingV1):
    source_kind: Literal["play", "history", "graph", "instructions", "tools", "message", "rules"]


class PlayWorldGraphAssembledInputV1(PlanWorldGraphAssembledInputV1):
    source_token_accounting: Annotated[list[PlayGraphSourceTokenAccountingV1], Field(max_length=128)]


def play_source_locator(basis: PlayRunTurnContextReceiptV2) -> PlaySourceLocatorV1:
    return PlaySourceLocatorV1(world_id=basis.world_id, run_id=basis.run_id,
        run_revision=basis.run_revision, beat_id=basis.beat_id, scene_id=basis.scene_id,
        edition=PlayContentBasis(edition_revision=basis.edition_revision,
            edition_revision_id=basis.edition_revision_id, content_sha256=basis.content_sha256))


class PlayWorldGraphContextReceiptV1(ClosedRulesModel):
    schema_: Literal["dmb_play_world_graph_context_receipt_v1"] = Field(
        default="dmb_play_world_graph_context_receipt_v1", alias="schema")
    receipt_serializer_version: Literal["canonical-json-utf8-v1"]
    context_receipt_sha256: Digest
    play_graph_policy: PlayGraphPolicyV1
    play_basis: PlayRunTurnContextReceiptV2
    play_sources: PlaySourceManifestV1
    retrieval_session_id: Annotated[str, Field(min_length=1, max_length=128)]
    graph_authority: PlanWorldGraphAuthorityV1
    graph_packet: PlayWorldGraphPacketV1
    assembled_input: PlayWorldGraphAssembledInputV1
    evidence_mode: Literal["metadata_only"]
    source_opened: Literal[False]

    @property
    def committed_content_sha256(self) -> str:
        """Structural common evidence view of the genuine Play edition."""
        return self.play_basis.content_sha256

    @model_validator(mode="after")
    def exact_receipt(self):
        authority = self.graph_authority
        if (authority.managed_world_id != self.play_basis.world_id
                or authority.campaign_id is not None or authority.admissibility_version != "gm-v1"
                or any(not value.strip() or value != value.strip() for value in (
                    authority.managed_world_id, authority.native_world_id, self.retrieval_session_id))):
            raise ValueError("Play receipt requires exact canonical World-only GM authority")
        locator = play_source_locator(self.play_basis)
        kinds = set()
        for entry in self.play_sources.entries:
            if entry.locator != locator or entry.source_kind in kinds:
                raise ValueError("Play receipt source differs from its Run edition or selected target")
            kinds.add(entry.source_kind)
            if entry.source_kind == "scene_note":
                if self.play_basis.scene_note is None:
                    raise ValueError("Play note source was not supplied by its Run owner")
                expected = source_entry(PlaySourcePayloadV1(source_kind="scene_note",
                    locator=locator, text=self.play_basis.scene_note))
                if entry != expected:
                    raise ValueError("Play note commitment differs from its exact saved note")
        if self.graph_packet.selection_policy_version == "parent_initial_retrieval_with_selected_source_index_v1":
            raise ValueError("Native Play requires its World-wide source scope, not a selected-index policy")
        validate_graph_packet_input(self.graph_packet, self.assembled_input)
        payload = self.model_dump(mode="json", by_alias=True, exclude={"context_receipt_sha256"})
        if canonical_sha256(payload) != self.context_receipt_sha256:
            raise ValueError("Play receipt digest differs from its exact contents")
        if len(canonical_bytes(self)) > 131072:
            raise ValueError("Play receipt exceeds its UTF8 budget")
        return self


def _checked_receipt(receipt: PlayWorldGraphContextReceiptV1) -> PlayWorldGraphContextReceiptV1:
    return PlayWorldGraphContextReceiptV1.model_validate_json(receipt.model_dump_json(by_alias=True))


def validate_play_graph_intent_receipt(intent: PlayGraphIntentV1, receipt: PlayWorldGraphContextReceiptV1) -> None:
    """Original submitted intent must match independently resolved owner values."""
    intent = PlayGraphIntentV1.model_validate_json(intent.model_dump_json(by_alias=True))
    receipt = _checked_receipt(receipt)
    ref, basis = intent.primary_work, receipt.play_basis
    edition = PlayContentBasis(edition_revision=basis.edition_revision,
        edition_revision_id=basis.edition_revision_id, content_sha256=basis.content_sha256)
    if (intent.world_id != basis.world_id or ref.object_id != basis.run_id
            or ref.expected_revision != basis.run_revision or ref.play_content_basis != edition
            or intent.play_target.beat_id != basis.beat_id or intent.play_target.scene_id != basis.scene_id
            or intent.play_graph_policy != receipt.play_graph_policy):
        raise ValueError("Submitted Play intent differs from the independently resolved receipt")


def validate_play_graph_source_frame(receipt: PlayWorldGraphContextReceiptV1, frame: PlaySourceFrameV1,
                                     *, owner_resolved_current_moment_text: str | None) -> None:
    """Exact source commitment/body join, not proof of actual provider inclusion."""
    receipt = _checked_receipt(receipt)
    frame = PlaySourceFrameV1.model_validate_json(frame.model_dump_json(by_alias=True))
    if frame.manifest != receipt.play_sources:
        raise ValueError("Supplied Play frame differs from the frozen receipt manifest")
    validate_play_source_owner_join(frame, receipt.play_basis,
        owner_resolved_current_moment_text=owner_resolved_current_moment_text)


@dataclass(frozen=True)
class _ProviderPrefix:
    """The actual validated ledger prefix before one authorization, not a codec."""
    policy: NativePlayGraphPolicyV1
    events: tuple[PlayGraphExecutionEventV1, ...]


def validate_play_graph_execution_binding(receipt: PlayWorldGraphContextReceiptV1,
                                          execution: PlayWorldGraphExecutionV1) -> None:
    receipt = _checked_receipt(receipt)
    execution = PlayWorldGraphExecutionV1.model_validate_json(execution.model_dump_json(by_alias=True))
    scope, authority = execution.policy.source_read_scope, receipt.graph_authority
    if (execution.context_receipt_sha256 != receipt.context_receipt_sha256
            or scope.world_id != authority.managed_world_id or scope.campaign_id is not None
            or scope.graph_revision != authority.graph_revision
            or scope.retrieval_session_id != receipt.retrieval_session_id
            or any(pin.evidence_ref_id not in receipt.graph_packet.candidate_evidence_ref_ids
                for pin in scope.admitted_anchors)):
        raise ValueError("Play execution differs from its frozen receipt Graph scope")
    for index, event in enumerate(execution.events):
        if isinstance(event, SourceScopeExtensionEventV3) and (
                event.native_world_id != authority.native_world_id
                or event.binding_version != authority.binding_version):
            raise ValueError("Play source extension differs from its managed/native World authority")
        if isinstance(event, ProviderAttemptAuthorizedEventV1):
            validate_graph_provider_envelope(receipt, _ProviderPrefix(execution.policy,
                tuple(execution.events[:index])), event)
    validate_related_recap_context_scope_record(receipt, execution)


def validate_play_graph_provider_authorization(receipt: PlayWorldGraphContextReceiptV1,
        execution: PlayWorldGraphExecutionV1, event: ProviderAttemptAuthorizedEventV3) -> PlayWorldGraphExecutionV1:
    """Prepare the exact ledger append; caller still owns fenced commit/dispatch."""
    validate_play_graph_execution_binding(receipt, execution)
    receipt = _checked_receipt(receipt)
    execution = PlayWorldGraphExecutionV1.model_validate_json(execution.model_dump_json(by_alias=True))
    event = ProviderAttemptAuthorizedEventV3.model_validate_json(event.model_dump_json(by_alias=True))
    validate_graph_provider_envelope(receipt, execution, event)
    wire = execution.model_dump(mode="json", by_alias=True)
    wire["events"].append(event.model_dump(mode="json", by_alias=True))
    appended = PlayWorldGraphExecutionV1.model_validate_json(json.dumps(wire))
    validate_play_graph_execution_binding(receipt, appended)
    return appended
