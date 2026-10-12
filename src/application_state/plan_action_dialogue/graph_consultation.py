"""Action-basis adapter for the shared Graph evidence validators.

This module owns action identity and disposition, never Core resolution or model
semantics. Existing Graph events remain the authority for evidence/context reads.
"""

from __future__ import annotations

from application_state.agent_conversation.types import (
    CompletionBindingEventV1,
    GraphEvidenceValidationInputs,
    PlanWorldGraphClaimSegmentV1,
    PlanWorldGraphCompletionV1,
    PlanWorldGraphCompletionV2,
    PlanWorldGraphCitationMapV2,
    ProviderAttemptAuthorizedEventV1,
    ProviderOutcomeEventV1,
    RelatedRecapContextProviderInclusionEventV1,
    ValidatedGraphOperationEventV1,
    ValidatedRelatedRecapContextEventV1,
    ValidatedSourceReadEventV2,
    _canonical_sha256,
    derive_graph_execution_evidence_status,
    validate_graph_execution_source_citations,
    validate_graph_packet_input,
    validate_graph_provider_envelope,
    validate_graph_related_recap_context_scope,
    validate_graph_selected_source_binding,
)
from application_state.plan_action_dialogue.types import (
    PlanActionConsultation,
    PlanActionConsultationReceipt,
    PlanActionConsultationResult,
    PlanActionContextUnavailableResult,
    PlanActionProposalResult,
    PlanActionRecord,
)


def consultation_receipt_digest(receipt: PlanActionConsultationReceipt) -> str:
    return _canonical_sha256(receipt.model_dump(
        mode="json", by_alias=True, exclude={"consultation_receipt_sha256"}
    ))


def consultation_result_digest(result: PlanActionConsultationResult) -> str:
    return _canonical_sha256(result.model_dump(mode="json", by_alias=True))


def action_input_digest(receipt: PlanActionConsultationReceipt) -> str:
    return _canonical_sha256({
        "schema": "dmb_plan_action_input_commitment_v1",
        **receipt.model_dump(mode="json", by_alias=True, include={
            "surface_id", "surface_instance_id", "basis", "draft_matches_basis",
            "draft_sha256", "target_kind", "selected_text_sha256", "instruction",
            "continuation",
        }),
    })


def build_consultation_receipt(
    *, action: PlanActionRecord, surface_instance_id: str,
    graph_authority=None, graph_packet=None, assembled_input=None, authority_failure_code=None,
    continuation=None, history_conversation_id=None, history_attribution=(),
) -> PlanActionConsultationReceipt:
    """Build a fully validated receipt from the reserved action and server authority.

    The caller resolves authority and constructs the actual frozen envelope;
    this helper derives action identity and both commitments from those inputs.
    """
    seed = PlanActionConsultationReceipt.model_construct(
        receipt_serializer_version="canonical-json-utf8-v1",
        consultation_receipt_sha256="0" * 64,
        action_id=action.action_id, request_fingerprint=action.request_fingerprint,
        surface_id="plan", surface_instance_id=surface_instance_id,
        basis=action.basis, draft_matches_basis=action.draft_matches_basis,
        draft_sha256=action.draft_sha256, target_kind=action.target_kind,
        selected_text_sha256=action.selected_text_sha256, instruction=action.instruction,
        action_input_sha256="0" * 64, graph_authority=graph_authority,
        graph_packet=graph_packet, assembled_input=assembled_input,
        authority_status="resolved" if authority_failure_code is None else "unavailable",
        authority_failure_code=authority_failure_code,
        continuation=continuation, history_conversation_id=history_conversation_id,
        history_attribution=list(history_attribution),
    )
    seed = seed.model_copy(update={"action_input_sha256": action_input_digest(seed)})
    return PlanActionConsultationReceipt.model_validate(
        seed.model_dump(mode="json", by_alias=True)
        | {"consultation_receipt_sha256": consultation_receipt_digest(seed)}
    )


def consultation_validation_inputs(
    receipt: PlanActionConsultationReceipt,
) -> GraphEvidenceValidationInputs:
    if receipt.authority_status != "resolved":
        raise ValueError("unavailable action authority cannot supply Graph validation inputs")
    return GraphEvidenceValidationInputs(
        context_receipt_sha256=receipt.consultation_receipt_sha256,
        committed_content_sha256=receipt.basis.content_sha256,
        graph_authority=receipt.graph_authority,
        graph_packet=receipt.graph_packet,
        assembled_input=receipt.assembled_input,
    )


def validate_consultation_receipt(receipt: PlanActionConsultationReceipt) -> None:
    if not receipt.surface_instance_id.strip() or not receipt.instruction.strip():
        raise ValueError("action consultation requires a visible surface and instruction")
    if any(not value.strip() or value != value.strip()
           for value in (receipt.basis.world_id, receipt.basis.document_id, receipt.surface_instance_id)):
        raise ValueError("action consultation identity must be nonblank and trimmed")
    if receipt.action_input_sha256 != action_input_digest(receipt):
        raise ValueError("action input commitment differs from the frozen creative inputs")
    if receipt.draft_matches_basis != (receipt.draft_sha256 == receipt.basis.content_sha256):
        raise ValueError("action draft match witness differs from its exact digests")
    if receipt.consultation_receipt_sha256 != consultation_receipt_digest(receipt):
        raise ValueError("action consultation receipt digest differs from its contents")
    graph_fields = (receipt.graph_authority, receipt.graph_packet, receipt.assembled_input)
    if receipt.authority_status == "unavailable":
        if (any(value is not None for value in graph_fields)
                or not receipt.authority_failure_code or not receipt.authority_failure_code.strip()
                or receipt.history_attribution or receipt.history_conversation_id is not None):
            raise ValueError("unavailable action authority cannot carry Graph pins or attributed claims")
        return
    if any(value is None for value in graph_fields) or receipt.authority_failure_code is not None:
        raise ValueError("resolved action authority requires all frozen Graph inputs")
    authority = receipt.graph_authority
    if (authority.managed_world_id != receipt.basis.world_id
            or authority.admissibility_version != "gm-v1"
            or any(not value.strip() or value != value.strip()
                   for value in (authority.native_world_id, authority.graph_revision))):
        raise ValueError("action consultation requires its exact managed World GM authority")
    validate_graph_packet_input(receipt.graph_packet, receipt.assembled_input)
    source_ids = set()
    included = {pin.turn_id for pin in receipt.assembled_input.included_history}
    for attribution in receipt.history_attribution:
        if (attribution.source_conversation_id != receipt.history_conversation_id
                or attribution.plan_basis.model_dump(mode="json")
                != receipt.basis.model_dump(mode="json")
                or attribution.source_turn_id in source_ids
                or attribution.source_turn_id not in included):
            raise ValueError("historical Ask attribution differs from the frozen action history")
        source_ids.add(attribution.source_turn_id)
        completion_type = (PlanWorldGraphCompletionV2
                           if isinstance(attribution.citation_map, PlanWorldGraphCitationMapV2)
                           else PlanWorldGraphCompletionV1)
        completion_type(
            context_receipt_sha256=attribution.context_receipt_sha256,
            answer_basis=attribution.answer_basis, answer_context_status=attribution.answer_context_status,
            answer_segments=attribution.answer_segments, citation_map=attribution.citation_map,
        )


def validate_consultation(consultation: PlanActionConsultation) -> None:
    receipt, execution = consultation.receipt, consultation.execution
    if receipt.authority_status == "unavailable":
        result = consultation.result
        if execution is not None or (result is not None and (
                not isinstance(result, PlanActionContextUnavailableResult)
                or result.failure_code != receipt.authority_failure_code
                or result.consultation_receipt_sha256 != receipt.consultation_receipt_sha256)):
            raise ValueError("unavailable authority permits only a matching context_unavailable failure")
        if len(consultation.model_dump_json(by_alias=True).encode("utf-8")) > 1_000_000:
            raise ValueError("action consultation exceeds its storage limit")
        return
    if execution is None:
        raise ValueError("resolved action consultation requires frozen execution")
    if execution.context_receipt_sha256 != receipt.consultation_receipt_sha256:
        raise ValueError("action execution must bind the exact consultation receipt")
    scope, authority = execution.policy.source_read_scope, receipt.graph_authority
    if (scope.world_id != authority.managed_world_id
            or scope.campaign_id != authority.campaign_id
            or scope.graph_revision != authority.graph_revision
            or any(anchor.evidence_ref_id not in receipt.graph_packet.candidate_evidence_ref_ids
                   for anchor in scope.admitted_anchors)):
        raise ValueError("action source scope differs from its frozen Graph authority")
    accounting = execution.policy.provider_input_accounting
    if (accounting.estimator != receipt.assembled_input.tokenizer_name
            or (accounting.kind == "conservative_upper_bound"
                and receipt.assembled_input.tokenizer_version != "v1")):
        raise ValueError("action accounting differs from the frozen provider input")
    inputs = consultation_validation_inputs(receipt)
    validate_graph_selected_source_binding(inputs, execution)
    validate_graph_related_recap_context_scope(inputs, execution)
    for index, event in enumerate(execution.events):
        if isinstance(event, ValidatedGraphOperationEventV1):
            if event.graph_revision != authority.graph_revision:
                raise ValueError("action Graph operation must use the frozen revision")
        elif isinstance(event, ProviderAttemptAuthorizedEventV1):
            prior = execution.model_copy(update={"events": execution.events[:index]})
            validate_graph_provider_envelope(inputs, prior, event)
    bindings = [e for e in execution.events if isinstance(e, CompletionBindingEventV1)]
    result = consultation.result
    if result is None:
        if bindings:
            raise ValueError("action completion binding requires a terminal result")
    else:
        if result.consultation_receipt_sha256 != receipt.consultation_receipt_sha256:
            raise ValueError("action result differs from its consultation receipt")
        if any(isinstance(e, ProviderOutcomeEventV1) and e.outcome == "outcome_unknown"
               for e in execution.events):
            raise ValueError("unknown provider outcome cannot expose an action result")
        if isinstance(result, PlanActionContextUnavailableResult):
            if bindings:
                raise ValueError("unavailable context cannot carry an applicable completion binding")
        else:
            expected_sha = consultation_result_digest(result)
            if (len(bindings) != 1
                    or bindings[0].completion_sha256 != expected_sha
                    or bindings[0].provider_attempt_id != result.producing_provider_attempt_id
                    or bindings[0].claim_graph_event_ids != result.claim_graph_event_ids):
                raise ValueError("action result requires its exact terminal completion binding")
            attempts = [e for e in execution.events
                        if isinstance(e, ProviderAttemptAuthorizedEventV1)]
            if not attempts or attempts[-1].provider_attempt_id != result.producing_provider_attempt_id:
                raise ValueError("action result must come from its final provider attempt")
            if not result.message.strip():
                raise ValueError("action result requires a visible message")
            if result.citation_map is not None:
                if (result.citation_map.context_receipt_sha256 != receipt.consultation_receipt_sha256
                        or len(result.citation_map.entries) != len(result.claim_graph_event_ids)):
                    raise ValueError("action citations must bind the receipt and exact claim set")
            validate_graph_execution_source_citations(
                result.citation_map, execution, result.producing_provider_attempt_id
            )
            derive_graph_execution_evidence_status(
                context_receipt_sha256=result.consultation_receipt_sha256,
                answer_segments=result.answer_segments, citation_map=result.citation_map,
                inputs=inputs, execution=execution,
                producing_provider_attempt_id=result.producing_provider_attempt_id,
                claim_graph_event_ids=result.claim_graph_event_ids,
            )
            claims = [s for s in result.answer_segments if isinstance(s, PlanWorldGraphClaimSegmentV1)]
            if len({claim.claim_id for claim in claims}) != len(claims):
                raise ValueError("action Graph claim IDs must be unique")
            if not claims and result.citation_map is not None:
                raise ValueError("action without Graph claims cannot carry evidence citations")
            if result.kind == "clarification" and not claims:
                raise ValueError("sourced clarification requires admitted factual attribution")
            if isinstance(result, PlanActionProposalResult):
                _validate_proposal_disposition(consultation, claims)
    if len(consultation.model_dump_json(by_alias=True).encode("utf-8")) > 1_000_000:
        raise ValueError("action consultation exceeds its storage limit")


def _validate_proposal_disposition(consultation, claims) -> None:
    result, receipt, execution = consultation.result, consultation.receipt, consultation.execution
    if any(
        (isinstance(e, ValidatedSourceReadEventV2)
         and any(read.outcome in {"denied", "unavailable"} for read in e.receipts))
        or (isinstance(e, ValidatedRelatedRecapContextEventV1) and e.outcome == "unavailable")
        for e in execution.events
    ):
        raise ValueError("failed consultation reads cannot become an applicable proposal")
    if result.disposition == "explicit_draft_override_after_clarification":
        if receipt.continuation is None:
            raise ValueError("explicit draft override requires a linked clarification")
    elif result.disposition == "supported_context_used":
        included_context = any(
            isinstance(e, RelatedRecapContextProviderInclusionEventV1)
            and e.provider_attempt_id == result.producing_provider_attempt_id
            for e in execution.events
        )
        if not claims and not included_context:
            raise ValueError("supported context disposition requires included support")
    elif claims or not (
        (receipt.graph_packet.coverage_status == "complete" and not receipt.graph_packet.truncated)
        or any(isinstance(e, ValidatedGraphOperationEventV1)
               and e.coverage_status == "complete" and not e.truncated
               for e in execution.events)
    ):
        raise ValueError("no relevant fact disposition requires a successful bounded consultation")


def validate_consultation_record(record: PlanActionRecord) -> None:
    consultation = record.consultation
    if consultation is None:
        return
    receipt = consultation.receipt
    if (record.action_id != receipt.action_id
            or record.request_fingerprint != receipt.request_fingerprint
            or record.basis != receipt.basis
            or record.draft_matches_basis != receipt.draft_matches_basis
            or record.draft_sha256 != receipt.draft_sha256
            or record.target_kind != receipt.target_kind
            or record.selected_text_sha256 != receipt.selected_text_sha256
            or record.instruction != receipt.instruction
            or record.action_type != "revise" or record.playable_target_receipt is not None):
        raise ValueError("consultation differs from the frozen action identity")
    result = consultation.result
    if record.status == "completed":
        if result is None or isinstance(result, PlanActionContextUnavailableResult):
            raise ValueError("completed consulted action requires clarification or proposal")
        if record.assistant_summary != result.message:
            raise ValueError("completed action summary differs from its typed result")
    elif result is not None and (
        record.status != "failed" or not isinstance(result, PlanActionContextUnavailableResult)
        or record.failure_code != result.failure_code
    ):
        raise ValueError("noncompleted consulted action cannot expose an applicable result")
