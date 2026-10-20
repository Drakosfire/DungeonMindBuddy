"""Pure Play owner/source/provider joins; no durable codec or SDK dispatch."""
from __future__ import annotations

import json
from dataclasses import dataclass
from uuid import UUID

from . import types as t
from .play_graph_authority import validate_play_source_owner_join


def _checked_receipt(receipt: t.PlayWorldGraphContextReceiptV1) -> t.PlayWorldGraphContextReceiptV1:
    return t.PlayWorldGraphContextReceiptV1.model_validate_json(receipt.model_dump_json(by_alias=True))


def validate_play_graph_intent_receipt(intent: t.PlayGraphIntentV1, receipt: t.PlayWorldGraphContextReceiptV1) -> None:
    """Original submitted intent must match independently resolved owner values."""
    intent = t.PlayGraphIntentV1.model_validate_json(intent.model_dump_json(by_alias=True))
    receipt = _checked_receipt(receipt)
    ref, basis = (intent.primary_work, receipt.play_basis)
    edition = t.PlayContentBasis(edition_revision=basis.edition_revision, edition_revision_id=basis.edition_revision_id, content_sha256=basis.content_sha256)
    if intent.world_id != basis.world_id or ref.object_id != basis.run_id or ref.expected_revision != basis.run_revision or (ref.play_content_basis != edition) or (intent.play_target.beat_id != basis.beat_id) or (intent.play_target.scene_id != basis.scene_id) or (intent.play_graph_policy != receipt.play_graph_policy):
        raise ValueError('Submitted Play intent differs from the independently resolved receipt')


def validate_play_graph_source_frame(receipt: t.PlayWorldGraphContextReceiptV1, frame: t.PlaySourceFrameV1, *, owner_resolved_current_moment_text: str | None) -> None:
    """Exact source commitment/body join, not proof of actual provider inclusion."""
    receipt = _checked_receipt(receipt)
    frame = t.PlaySourceFrameV1.model_validate_json(frame.model_dump_json(by_alias=True))
    if frame.manifest != receipt.play_sources or t.canonical_sha256(frame) != receipt.play_source_frame_sha256:
        raise ValueError('Supplied Play frame differs from the frozen receipt manifest')
    validate_play_source_owner_join(frame, receipt.play_basis, owner_resolved_current_moment_text=owner_resolved_current_moment_text)


@dataclass(frozen=True)
class _ProviderPrefix:
    """The actual validated ledger prefix before one authorization, not a codec."""
    policy: t.NativePlayGraphPolicyV1
    events: tuple[t.PlayGraphExecutionEventV1, ...]


def validate_play_graph_execution_binding(receipt: t.PlayWorldGraphContextReceiptV1, execution: t.PlayWorldGraphExecutionV1) -> None:
    receipt = _checked_receipt(receipt)
    execution = t.PlayWorldGraphExecutionV1.model_validate_json(execution.model_dump_json(by_alias=True))
    scope, authority = (execution.policy.source_read_scope, receipt.graph_authority)
    if execution.context_receipt_sha256 != receipt.context_receipt_sha256 or scope.world_id != authority.managed_world_id or scope.campaign_id is not None or (scope.graph_revision != authority.graph_revision) or (scope.retrieval_session_id != receipt.retrieval_session_id) or any((pin.evidence_ref_id not in receipt.graph_packet.candidate_evidence_ref_ids for pin in scope.admitted_anchors)):
        raise ValueError('Play execution differs from its frozen receipt Graph scope')
    for index, event in enumerate(execution.events):
        if isinstance(event, t.PlaySourceProviderInclusionV1) and (
                event.source_ids != [entry.source_id for entry in receipt.play_sources.entries]
                or event.source_frame_sha256 != receipt.play_source_frame_sha256):
            raise ValueError('Play producer source frame differs from its exact frozen receipt')
        if isinstance(event, t.SourceScopeExtensionEventV3) and (event.native_world_id != authority.native_world_id or event.binding_version != authority.binding_version):
            raise ValueError('Play source extension differs from its managed/native World authority')
        if isinstance(event, t.ProviderAttemptAuthorizedEventV1):
            t.validate_graph_provider_envelope(receipt, _ProviderPrefix(execution.policy, tuple(execution.events[:index])), event)
    t.validate_related_recap_context_scope_record(receipt, execution)


def validate_play_graph_provider_authorization(receipt: t.PlayWorldGraphContextReceiptV1, execution: t.PlayWorldGraphExecutionV1, event: t.ProviderAttemptAuthorizedEventV3) -> t.PlayWorldGraphExecutionV1:
    """Prepare the exact ledger append; caller still owns fenced commit/dispatch."""
    validate_play_graph_execution_binding(receipt, execution)
    receipt = _checked_receipt(receipt)
    execution = t.PlayWorldGraphExecutionV1.model_validate_json(execution.model_dump_json(by_alias=True))
    event = t.ProviderAttemptAuthorizedEventV3.model_validate_json(event.model_dump_json(by_alias=True))
    t.validate_graph_provider_envelope(receipt, execution, event)
    wire = execution.model_dump(mode='json', by_alias=True)
    wire['events'].append(event.model_dump(mode='json', by_alias=True))
    appended = t.PlayWorldGraphExecutionV1.model_validate_json(json.dumps(wire))
    validate_play_graph_execution_binding(receipt, appended)
    return appended


def prepare_play_source_provider_inclusion(receipt: t.PlayWorldGraphContextReceiptV1,
        execution: t.PlayWorldGraphExecutionV1, frame: t.PlaySourceFrameV1, *,
        event_id: UUID, provider_attempt_id: UUID, envelope_sha256: str,
        owner_resolved_current_moment_text: str | None) -> t.PlaySourceProviderInclusionV1:
    """Derive an owner witness; APP commit and actual SDK input proof are separate."""
    validate_play_graph_execution_binding(receipt, execution)
    validate_play_graph_source_frame(receipt, frame,
        owner_resolved_current_moment_text=owner_resolved_current_moment_text)
    receipt, frame = _checked_receipt(receipt), t.PlaySourceFrameV1.model_validate_json(frame.model_dump_json(by_alias=True))
    event = t.PlaySourceProviderInclusionV1(kind='play_source_provider_inclusion_v1',
        event_id=event_id, sequence=len(execution.events),
        context_receipt_sha256=receipt.context_receipt_sha256,
        execution_policy_sha256=execution.execution_policy_sha256,
        provider_attempt_id=provider_attempt_id, envelope_sha256=envelope_sha256,
        source_frame_sha256=t.canonical_sha256(frame),
        source_ids=[entry.source_id for entry in frame.manifest.entries])
    wire = execution.model_dump(mode='json', by_alias=True)
    wire['events'].append(event.model_dump(mode='json', by_alias=True))
    pending = t.PlayWorldGraphExecutionV1.model_validate_json(json.dumps(wire))
    validate_play_graph_execution_binding(receipt, pending)
    return event
