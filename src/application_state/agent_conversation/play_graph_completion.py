"""Native Play completion invariants; actual APP/raw-producing proof is separate."""
from __future__ import annotations

from uuid import UUID

from . import types as t
from .play_graph_context import validate_play_graph_execution_binding


def validate_play_graph_completion(completion: t.PlayWorldGraphCompletionV1,
        receipt: t.PlayWorldGraphContextReceiptV1, execution: t.PlayWorldGraphExecutionV1,
        producing_provider_attempt_id: UUID, claim_graph_event_ids: dict[str, list[UUID]]) -> None:
    completion = t.PlayWorldGraphCompletionV1.model_validate_json(completion.model_dump_json(by_alias=True))
    receipt = t.PlayWorldGraphContextReceiptV1.model_validate_json(receipt.model_dump_json(by_alias=True))
    execution = t.PlayWorldGraphExecutionV1.model_validate_json(execution.model_dump_json(by_alias=True))
    validate_play_graph_execution_binding(receipt, execution)
    if completion.context_receipt_sha256 != receipt.context_receipt_sha256:
        raise ValueError('Play completion differs from its frozen receipt')
    producing = next((event for event in execution.events
        if isinstance(event, t.ProviderAttemptAuthorizedEventV3)
        and event.provider_attempt_id == producing_provider_attempt_id), None)
    inclusions = [event for event in execution.events
        if isinstance(event, t.PlaySourceProviderInclusionV1)
        and event.provider_attempt_id == producing_provider_attempt_id]
    responses = [event for event in execution.events if isinstance(event, t.ProviderOutcomeEventV1)
        and event.provider_attempt_id == producing_provider_attempt_id and event.outcome == 'response_received']
    if len(responses) != 1 or any(not isinstance(event, t.CompletionBindingEventV1)
            for event in execution.events if event.sequence > responses[0].sequence):
        raise ValueError('Play completion requires the final acknowledged provider, without later acquisition')
    bindings = [event for event in execution.events if isinstance(event, t.CompletionBindingEventV1)]
    if bindings and (len(bindings) != 1 or bindings[0].provider_attempt_id != producing_provider_attempt_id
            or bindings[0].completion_sha256 != t.canonical_sha256(completion)
            or bindings[0].claim_graph_event_ids != claim_graph_event_ids):
        raise ValueError('Stored Play completion differs from its exact completion binding')
    included_sources = set()
    if inclusions:
        if (len(inclusions) != 1 or producing is None or inclusions[0].sequence >= producing.sequence
                or inclusions[0].envelope_sha256 != producing.envelope_sha256):
            raise ValueError('Play sources require the same actual producing request')
        included_sources = set(inclusions[0].source_ids)
    receipt_sources = {entry.source_id for entry in receipt.play_sources.entries}
    for segment in completion.answer_segments:
        if isinstance(segment, t.PlayContextClaimV1) and not set(segment.source_ids).issubset(
                included_sources & receipt_sources):
            raise ValueError('Play context claim used a source absent from the producing request')
    expected = t.derive_graph_execution_evidence_status_for_scope(
        context_receipt_sha256=completion.context_receipt_sha256,
        answer_segments=completion.answer_segments, citation_map=completion.citation_map,
        inputs=receipt, execution=execution, producing_provider_attempt_id=producing_provider_attempt_id,
        claim_graph_event_ids=claim_graph_event_ids, source_scope=execution.policy.source_read_scope)
    expected = {'plan_only_insufficient_evidence':'play_only_insufficient_evidence',
        'plan_only_graph_unused':'play_only_graph_unused'}.get(expected, expected)
    if completion.answer_context_status != expected:
        raise ValueError('Play answer status differs from actual producing evidence')
    t.validate_graph_execution_source_citations(completion.citation_map, execution, producing_provider_attempt_id)
