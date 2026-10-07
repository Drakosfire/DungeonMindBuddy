from __future__ import annotations

import hashlib
import json
from datetime import UTC, datetime, timedelta
from uuid import uuid4

import pytest

from application_state.agent_conversation import AgentConversationService
from application_state.agent_conversation import repository as repo
from application_state.agent_conversation import service as service_module
from application_state.agent_conversation.types import (
    ConversationCommand,
    PlanContextPolicyV1,
    PlanAskHistoryAttributionV1,
    GraphExecutionAccountingV1,
    GraphExecutionPolicyV2,
    GraphSourceReadScopeV2,
    GraphSourceScopeAnchorV2,
    PlanWorldGraphExecutionV2,
    PlanWorldGraphExecutionV1,
    GraphExecutionPolicyV1,
    ProviderAttemptAuthorizedEventV1,
    ValidatedGraphOperationEventV1,
    plan_world_graph_context_receipt_digest,
    PlanWorldGraphCitationMapV2,
    PlanWorldGraphCompletionV2,
    ProviderAttemptAuthorizedEventV2,
    ProviderOutcomeEventV1,
    SourceReadAnchorReceiptV2,
    SourceReadAuthorizationEventV2,
    ValidatedSourceReadEventV2,
    graph_execution_policy_digest_v2,
    PlanPlayableTargetReceiptV1,
    PlanWorldGraphCitationMapV1,
    PlanWorldGraphCitationV1,
    PlanWorldGraphClaimSegmentV1,
    PlanWorldGraphCompletionV1,
    PlanWorldGraphContextReceiptV1,
    HistoricalReference,
    PlanAskContextBasis,
    SubmittedPlanPlayableTargetV1,
    SubmittedPrimaryWorkIntentV1,
    SubmittedTurnIntentV2,
    SubmittedGraphRequestIntentV1,
    SubmittedTurnIntentV1,
    TurnFailure,
    TurnProvenance,
    TurnResult,
    TurnSubmission,
    encode_plan_playable_target_reference,
)
from application_state.errors import (
    ApplicationStateIntegrityError,
    ApplicationStateValidationError,
)


def _basis(world_id: str = "ask-projection-world") -> PlanAskContextBasis:
    return PlanAskContextBasis(
        world_id=world_id,
        document_id="plan-document-7",
        object_revision=9,
        work_revision_id=uuid4(),
        revision_n=4,
        content_sha256="d" * 64,
    )


def _reference(basis: PlanAskContextBasis) -> HistoricalReference:
    return HistoricalReference(
        resolution="resolved",
        kind="plan",
        object_id=basis.document_id,
        content_sha256=basis.content_sha256,
        object_revision=basis.object_revision,
        work_revision_id=basis.work_revision_id,
        revision_n=basis.revision_n,
    )


def _new_conversation(service: AgentConversationService, world_id: str):
    return service.new_conversation(
        ConversationCommand(
            world_id=world_id,
            command_id=uuid4(),
            expected_pointer_revision=0,
            expected_active_conversation_id=None,
        )
    )


def _add_turn(
    service: AgentConversationService,
    world_id: str,
    conversation_id,
    basis: PlanAskContextBasis,
    *,
    sequence: int,
    question: str,
    primary: HistoricalReference | None = None,
    supporting: list[HistoricalReference] | None = None,
    surface_resolution: str = "resolved",
    surface_id: str | None = "plan",
    complete: bool = True,
    fail: bool = False,
    running: bool = False,
):
    primary_reference = primary or _reference(basis)
    provenance = TurnProvenance(
        world_id=world_id,
        surface_resolution=surface_resolution,
        surface_id=surface_id,
        primary_work=primary_reference,
        supporting_work=supporting or [],
        selected_object=HistoricalReference(resolution="absent"),
    )
    intent = SubmittedTurnIntentV1(
        world_id=world_id,
        client_thread_id="ask-projection-test-thread",
        message=question,
        surface_id=surface_id or "index",
        surface_instance_id="ask-projection-test-pane",
        client_work_state="saved_clean" if surface_id == "plan" else "none",
        primary_work=(
            SubmittedPrimaryWorkIntentV1(
                kind="plan",
                object_id=basis.document_id,
                expected_revision=basis.object_revision,
                expected_revision_n=basis.revision_n,
                expected_content_sha256=basis.content_sha256,
            )
            if surface_id == "plan"
            else None
        ),
        graph_request=SubmittedGraphRequestIntentV1(mode="none"),
        graph_selection=None,
    )
    turn = service.accept_turn(
        TurnSubmission(
            world_id=world_id,
            conversation_id=conversation_id,
            idempotency_key=uuid4(),
            expected_conversation_revision=sequence,
            user_text=question,
            provenance=provenance,
            submitted_intent_v1=intent,
        )
    )
    if complete or fail or running:
        claimed = service.begin_turn(
            world_id,
            conversation_id,
            turn.turn_id,
            expected_revision=turn.revision,
        )
        if fail:
            return service.fail_turn(
                TurnFailure(
                    world_id=world_id,
                    conversation_id=conversation_id,
                    turn_id=turn.turn_id,
                    expected_revision=claimed.revision,
                    failure_code="test-failure",
                )
            )
        if running:
            return claimed
        if not complete:
            return claimed
        return service.complete_turn(
            TurnResult(
                world_id=world_id,
                conversation_id=conversation_id,
                turn_id=turn.turn_id,
                expected_revision=claimed.revision,
                assistant_text=f"Answer for {question}",
            )
        )
    return turn


def _graph_receipt(
    basis: PlanAskContextBasis,
    target: PlanPlayableTargetReceiptV1,
    *,
    assertion_id: str,
    evidence_ref_id: str,
) -> PlanWorldGraphContextReceiptV1:
    payload = {
        "schema": "dmb_agent_plan_world_graph_context_receipt_v1",
        "receipt_serializer_version": "canonical-json-utf8-v1",
        "context_receipt_sha256": "0" * 64,
        "plan_context_policy": {
            "schema": "dmb_plan_context_policy_v1",
            "policy": "auto_plan_world",
        },
        "plan_basis": basis.model_dump(mode="json"),
        "playable_target": target.model_dump(mode="json", by_alias=True),
        "graph_authority": {
            "managed_world_id": basis.world_id,
            "native_world_id": "native-world-ask-history",
            "binding_version": 1,
            "scope_mode": "world",
            "campaign_id": None,
            "admissibility_version": "ask-history-test-v1",
            "graph_revision": "ask-history-graph-rev-1",
        },
        "graph_packet": {
            "schema": "dmb_plan_world_graph_packet_v1",
            "packet_serializer_version": "canonical-json-utf8-v1",
            "selection_policy_version": "ask-history-selection-v1",
            "evidence_sufficiency_policy_version": "ask-history-sufficiency-v1",
            "retrieval_packet_sha256": "1" * 64,
            "candidate_assertion_ids": [assertion_id],
            "candidate_relationship_ids": [],
            "candidate_evidence_ref_ids": [evidence_ref_id],
            "retrieval_status": "complete",
            "evidence_sufficiency_status": "sufficient",
            "result_limit": 8,
            "coverage_status": "incomplete",
            "truncated": False,
            "omission_reasons": [],
        },
        "assembled_input": {
            "assembler_version": "ask-history-assembler-v1",
            "budget_policy_version": "ask-history-budget-v1",
            "provider_model_name": "synthetic-model",
            "provider_model_version": "1",
            "tokenizer_name": "synthetic-tokenizer",
            "tokenizer_version": "1",
            "provider_envelope_input_tokens": 10,
            "output_token_reserve": 8,
            "context_window_limit": 100,
            "packet_disposition": "included",
            "packet_disposition_reason": None,
            "dispatched_packet_sha256": "2" * 64,
            "dispatched_assertion_ids": [assertion_id],
            "dispatched_relationship_ids": [],
            "dispatched_evidence_ref_ids": [evidence_ref_id],
            "source_token_accounting": [],
            "included_history": [],
            "assembled_input_sha256": "3" * 64,
        },
        "evidence_mode": "metadata_only",
        "source_opened": False,
    }
    encoded = json.dumps(
        {
            key: value
            for key, value in payload.items()
            if key != "context_receipt_sha256"
        },
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
        allow_nan=False,
    ).encode("utf-8")
    payload["context_receipt_sha256"] = hashlib.sha256(encoded).hexdigest()
    return PlanWorldGraphContextReceiptV1.model_validate(payload)


def _add_graph_ask(
    service: AgentConversationService,
    basis: PlanAskContextBasis,
    conversation_id,
    *,
    sequence: int,
    target_id: str,
    question: str,
    answer: str,
    source_opened: bool | None = None,
    completion_version: int = 2,
    historical_graph_operation: bool = False,
    execution_version: int = 2,
):
    target = PlanPlayableTargetReceiptV1(
        schema="dmb_plan_playable_target_receipt_v1",
        kind="beat",
        id=target_id,
        marker_grammar_version="v2",
    )
    assertion_id = f"assertion-{sequence}"
    evidence_ref_id = "ev:016" if historical_graph_operation else f"evidence-{sequence}"
    claim_id = "rel:004" if historical_graph_operation else f"claim-{sequence}"
    claim_kind = "relationship" if historical_graph_operation else "assertion"
    claim_target = "rel:004" if historical_graph_operation else assertion_id
    historical_targets = ["rel:004", "rel:014", "rel:017", "rel:018", "rel:019", "rel:020"]
    historical_refs = [f"ev:{n:03d}" for n in [2, 3, 4, 5, 10, 11, 12, 13, 14, 16, 18, 19, 20, 21, 22, 23, 24]]
    receipt = _graph_receipt(
        basis,
        target,
        assertion_id=assertion_id,
        evidence_ref_id=evidence_ref_id,
    )
    if historical_graph_operation:
        # Sanitized seq5 structure: empty insufficient initial dispatch, then a producing
        # Graph operation with six relationships and seventeen refs, including rel:004/ev:016.
        unsealed = receipt.model_copy(update={
            "graph_packet": receipt.graph_packet.model_copy(update={
                "selection_policy_version": "parent_initial_retrieval_v1", "candidate_assertion_ids": [],
                "candidate_relationship_ids": [f"rel:{n:03d}" for n in range(1, 17)],
                "candidate_evidence_ref_ids": [f"ev:{n:03d}" for n in range(1, 18)],
                "evidence_sufficiency_status": "insufficient", "result_limit": 32,
                "omission_reasons": ["insufficient_evidence"],
            }),
            "assembled_input": receipt.assembled_input.model_copy(update={
                "packet_disposition": "omitted_insufficient", "packet_disposition_reason": "insufficient_evidence",
                "dispatched_packet_sha256": None, "dispatched_assertion_ids": [],
                "dispatched_relationship_ids": [], "dispatched_evidence_ref_ids": [],
            }),
        })
        receipt = PlanWorldGraphContextReceiptV1.model_validate(
            unsealed.model_dump(mode="json", by_alias=True) | {"context_receipt_sha256": plan_world_graph_context_receipt_digest(unsealed)}
        )
    execution = None
    if source_opened is not None:
        scope = GraphSourceReadScopeV2(
            retrieval_session_id=f"history-source-session-{sequence}", world_id=basis.world_id,
            campaign_id=None, graph_revision=receipt.graph_authority.graph_revision,
            admitted_anchors=[GraphSourceScopeAnchorV2(
                anchor_id=f"anchor-{sequence}", evidence_ref_id=evidence_ref_id,
                source_artifact_id=f"artifact-{sequence}", source_revision_id=f"source-revision-{sequence}",
            )],
        )
        policy = GraphExecutionPolicyV2(
            policy_version="ask-history-policy-v2", allowed_graph_operations=["expand_graph_retrieval"] if historical_graph_operation else ["search_assertions"],
            max_provider_attempts=2 if historical_graph_operation else 1, max_graph_operations=1 if historical_graph_operation else 0, max_results_per_operation=32 if historical_graph_operation else 0,
            max_total_provider_input_tokens=100, max_total_provider_output_tokens=40,
            provider_input_accounting=GraphExecutionAccountingV1(kind="exact_token_count", estimator="synthetic-tokenizer"),
            source_opened=False, source_read_scope=scope,
            max_source_read_calls=1, max_source_read_anchors=1,
            max_source_read_chars=100, max_chars_per_source_read=100,
        )
        if execution_version == 1:
            policy = GraphExecutionPolicyV1.model_validate({
                key: value for key, value in policy.model_dump(mode="json").items()
                if key not in {"source_read_scope", "max_source_read_calls", "max_source_read_anchors", "max_source_read_chars", "max_chars_per_source_read"}
            })
            execution = PlanWorldGraphExecutionV1(context_receipt_sha256=receipt.context_receipt_sha256, policy=policy, events=[])
        else:
            execution = PlanWorldGraphExecutionV2(
                context_receipt_sha256=receipt.context_receipt_sha256,
                execution_policy_sha256=graph_execution_policy_digest_v2(receipt.context_receipt_sha256, policy),
                policy=policy, events=[],
            )
    surface_instance_id = f"plan-ask-pane-{sequence}"
    intent = SubmittedTurnIntentV2(
        world_id=basis.world_id,
        client_thread_id="ask-history-test-thread",
        message=question,
        surface_id="plan",
        surface_instance_id=surface_instance_id,
        client_work_state="saved_clean",
        primary_work=SubmittedPrimaryWorkIntentV1(
            kind="plan",
            object_id=basis.document_id,
            expected_revision=basis.object_revision,
            expected_revision_n=basis.revision_n,
            expected_content_sha256=basis.content_sha256,
        ),
        plan_context_policy=PlanContextPolicyV1(policy="auto_plan_world"),
        playable_target=SubmittedPlanPlayableTargetV1(
            schema="dmb_plan_playable_target_v1", kind="beat", id=target_id
        ),
        graph_request=SubmittedGraphRequestIntentV1(mode="none"),
        graph_selection=None,
    )
    provenance = TurnProvenance(
        world_id=basis.world_id,
        surface_resolution="resolved",
        surface_id="plan",
        surface_instance_id=surface_instance_id,
        primary_work=_reference(basis),
        supporting_work=[encode_plan_playable_target_reference(target)],
        selected_object=HistoricalReference(resolution="absent"),
    )
    accepted = service.accept_turn(
        TurnSubmission(
            world_id=basis.world_id,
            conversation_id=conversation_id,
            idempotency_key=uuid4(),
            expected_conversation_revision=sequence,
            user_text=question,
            provenance=provenance,
            submitted_intent_v2=intent,
            graph_context_receipt=receipt,
            graph_context_execution=execution,
        )
    )
    claimed = service.claim_turn(
        basis.world_id,
        conversation_id,
        accepted.turn_id,
        expected_revision=accepted.revision,
    ).turn
    producing_attempt = None
    source_read_ids = []
    graph_event_ids = []
    if execution is not None:
        scope = getattr(execution.policy, "source_read_scope", None)
        read_event_ids = []
        if source_opened:
            authorization = SourceReadAuthorizationEventV2(
                event_id=uuid4(), sequence=0, kind="source_read_authorized_v2", read_call_id=uuid4(),
                context_receipt_sha256=receipt.context_receipt_sha256,
                execution_policy_sha256=execution.execution_policy_sha256,
                retrieval_session_id=scope.retrieval_session_id, world_id=basis.world_id,
                campaign_id=None, graph_revision=scope.graph_revision, anchors=scope.admitted_anchors, max_chars=100,
            )
            claimed, _ = service.authorize_source_read(
                basis.world_id, conversation_id, accepted.turn_id,
                expected_revision=claimed.revision, expected_attempt=claimed.attempt, authorization=authorization,
            )
            read_id = f"source-read:history-{sequence}"
            read = ValidatedSourceReadEventV2(
                event_id=uuid4(), sequence=1, kind="validated_source_read_v2", read_call_id=authorization.read_call_id,
                receipts=[SourceReadAnchorReceiptV2(
                    source_read_id=read_id, anchor_id=f"anchor-{sequence}", evidence_ref_id=evidence_ref_id,
                    source_artifact_id=f"artifact-{sequence}", source_revision_id=f"source-revision-{sequence}",
                    outcome="enough", content_sha256="a" * 64, line_start=1, line_end=2,
                    returned_chars=40, truncated=False, evidence_sufficiency_status="sufficient",
                )],
            )
            claimed, _ = service.record_validated_source_read(
                basis.world_id, conversation_id, accepted.turn_id,
                expected_revision=claimed.revision, expected_attempt=claimed.attempt, receipt=read,
            )
            read_event_ids = [read.event_id]
            source_read_ids = [read_id]
        if historical_graph_operation:
            first_fields = dict(
                event_id=uuid4(), sequence=0, kind="provider_attempt_authorized", provider_attempt_id=uuid4(),
                envelope_sha256=receipt.assembled_input.assembled_input_sha256, serializer_version="canonical-json-utf8-v1",
                provider="synthetic-provider", model="synthetic-model", api_mode="messages", tool_schema_sha256="c" * 64,
                input_accounting_kind="exact_token_count", input_estimator="synthetic-tokenizer",
                input_tokens=10, output_token_reserve=8, included_assertion_ids=[],
                included_relationship_ids=[], included_evidence_ref_ids=[], included_graph_event_ids=[],
            )
            if execution_version == 2:
                first_fields.update(kind="provider_attempt_authorized_v2", included_source_read_event_ids=[])
                first_provider = ProviderAttemptAuthorizedEventV2(**first_fields)
                authorize = service.authorize_provider_attempt_v2
            else:
                first_provider = ProviderAttemptAuthorizedEventV1(**first_fields)
                authorize = service.authorize_provider_attempt
            claimed, _ = authorize(
                basis.world_id, conversation_id, accepted.turn_id,
                expected_revision=claimed.revision, expected_attempt=claimed.attempt, provider_attempt_event=first_provider,
            )
            for outcome in ["sdk_entered", "response_received"]:
                claimed, _ = service.record_provider_outcome(
                    basis.world_id, conversation_id, accepted.turn_id,
                    expected_revision=claimed.revision, expected_attempt=claimed.attempt,
                    outcome=ProviderOutcomeEventV1(
                        event_id=uuid4(), sequence=len(claimed.graph_context_execution.events), kind="provider_outcome",
                        provider_attempt_id=first_provider.provider_attempt_id, outcome=outcome,
                        response_sha256="e" * 64 if outcome == "response_received" else None,
                    ),
                )
            graph_event = ValidatedGraphOperationEventV1(
                event_id=uuid4(), sequence=len(claimed.graph_context_execution.events), kind="validated_graph_operation",
                operation_id=uuid4(), operation="expand_graph_retrieval", request_arguments_sha256="f" * 64,
                graph_revision=receipt.graph_authority.graph_revision, result_packet_sha256="a" * 64,
                assertion_ids=[], relationship_ids=historical_targets, evidence_ref_ids=historical_refs,
                evidence_sufficiency_status="sufficient", coverage_status="incomplete", truncated=True, source_opened=False,
            )
            claimed, _ = service.append_validated_graph_operation(
                basis.world_id, conversation_id, accepted.turn_id,
                expected_revision=claimed.revision, expected_attempt=claimed.attempt, operation_event=graph_event,
            )
            graph_event_ids = [graph_event.event_id]
        producing_attempt = uuid4()
        provider = ProviderAttemptAuthorizedEventV2(
            event_id=uuid4(), sequence=len(claimed.graph_context_execution.events),
            kind="provider_attempt_authorized_v2", provider_attempt_id=producing_attempt,
            envelope_sha256=receipt.assembled_input.assembled_input_sha256, serializer_version="canonical-json-utf8-v1",
            provider="synthetic-provider", model="synthetic-model", api_mode="messages", tool_schema_sha256="c" * 64,
            input_accounting_kind="exact_token_count", input_estimator="synthetic-tokenizer",
            input_tokens=10, output_token_reserve=8, included_assertion_ids=[] if historical_graph_operation else [assertion_id],
            included_relationship_ids=historical_targets if historical_graph_operation else [],
            included_evidence_ref_ids=historical_refs if historical_graph_operation else [evidence_ref_id],
            included_graph_event_ids=graph_event_ids, included_source_read_event_ids=read_event_ids,
        )
        if execution_version == 1:
            fields = provider.model_dump(mode="json", by_alias=True)
            fields.pop("included_source_read_event_ids")
            fields["kind"] = "provider_attempt_authorized"
            provider = ProviderAttemptAuthorizedEventV1.model_validate(fields)
            authorize_provider = service.authorize_provider_attempt
        else:
            authorize_provider = service.authorize_provider_attempt_v2
        claimed, _ = authorize_provider(
            basis.world_id, conversation_id, accepted.turn_id,
            expected_revision=claimed.revision, expected_attempt=claimed.attempt, provider_attempt_event=provider,
        )
        for outcome in ["sdk_entered", "response_received"]:
            claimed, _ = service.record_provider_outcome(
                basis.world_id, conversation_id, accepted.turn_id,
                expected_revision=claimed.revision, expected_attempt=claimed.attempt,
                outcome=ProviderOutcomeEventV1(
                    event_id=uuid4(), sequence=len(claimed.graph_context_execution.events), kind="provider_outcome",
                    provider_attempt_id=producing_attempt, outcome=outcome,
                    response_sha256="e" * 64 if outcome == "response_received" else None,
                ),
            )
    completion = PlanWorldGraphCompletionV1(
        context_receipt_sha256=receipt.context_receipt_sha256,
        answer_basis="committed_plan_plus_world_graph",
        answer_context_status="graph_grounded_partial",
        answer_segments=[
            PlanWorldGraphClaimSegmentV1(
                kind="graph_claim",
                claim_id=claim_id,
                text=answer,
                target_kind=claim_kind,
                target_id=claim_target,
                graph_revision="ask-history-graph-rev-1",
                evidence_ref_ids=[evidence_ref_id],
            )
        ],
        citation_map=PlanWorldGraphCitationMapV1(
            context_receipt_sha256=receipt.context_receipt_sha256,
            entries=[
                PlanWorldGraphCitationV1(
                    claim_id=claim_id,
                    target_kind=claim_kind,
                    target_id=claim_target,
                    graph_revision="ask-history-graph-rev-1",
                    evidence_ref_ids=[evidence_ref_id],
                    source_opened=False,
                )
            ],
        ),
    )
    if execution is not None and completion_version == 2:
        payload = completion.model_dump(mode="json", by_alias=True)
        payload["schema"] = "dmb_plan_world_graph_completion_v2"
        payload["citation_map"]["schema"] = "dmb_graph_citation_map_v2"
        payload["citation_map"]["entries"][0].update(source_read_ids=source_read_ids, source_opened=source_opened)
        completion = PlanWorldGraphCompletionV2.model_validate(payload)
    return service.complete_turn(
        TurnResult(
            world_id=basis.world_id,
            conversation_id=conversation_id,
            turn_id=accepted.turn_id,
            expected_revision=claimed.revision,
            assistant_text=answer,
            completion=completion,
            producing_provider_attempt_id=producing_attempt,
            claim_graph_event_ids={claim_id: graph_event_ids} if execution is not None else None,
        )
    )


def _set_accepted_at(application_state_dsn: str, turn_id, accepted_at: datetime) -> None:
    import psycopg

    with psycopg.connect(application_state_dsn) as conn:
        conn.execute(
            "UPDATE agent.turn SET accepted_at = %s WHERE turn_id = %s",
            (accepted_at, turn_id),
        )


def test_exact_basis_filters_every_field_before_limit_and_returns_safe_pairs(
    application_state_dsn: str,
) -> None:
    service = AgentConversationService()
    basis = _basis()
    conversation = _new_conversation(service, basis.world_id)

    expected_ids = []
    for sequence, question in enumerate(("older match", "newer match"), start=1):
        turn = _add_turn(
            service,
            basis.world_id,
            conversation.conversation_id,
            basis,
            sequence=sequence,
            question=question,
        )
        expected_ids.append(turn.turn_id)

    mismatches = (
        {"document_id": "another-document"},
        {"object_revision": basis.object_revision + 1},
        {"work_revision_id": uuid4()},
        {"revision_n": basis.revision_n + 1},
        {"content_sha256": "e" * 64},
    )
    for offset, changes in enumerate(mismatches, start=3):
        mismatched_basis = basis.model_copy(update=changes)
        _add_turn(
            service,
            basis.world_id,
            conversation.conversation_id,
            basis,
            sequence=offset,
            question=f"mismatch {offset}",
            primary=_reference(mismatched_basis),
        )

    pairs = service.list_completed_plan_ask_context(basis.world_id, basis, limit=2)
    assert [pair.source_record_id for pair in pairs] == expected_ids
    assert [pair.question for pair in pairs] == ["older match", "newer match"]
    assert [pair.source_kind for pair in pairs] == ["ask", "ask"]
    assert [pair.source_sequence for pair in pairs] == [1, 2]
    assert all(pair.answer.startswith("Answer for ") for pair in pairs)
    assert set(pairs[0].model_dump()) == {
        "source_kind",
        "source_sequence",
        "source_record_id",
        "accepted_at",
        "question",
        "answer",
        "history_attribution",
    }
    assert pairs[0].history_attribution is None


def test_scene_a_graph_ask_stays_attributed_when_next_proposal_targets_scene_b(
    application_state_dsn: str,
) -> None:
    service = AgentConversationService()
    basis = _basis()
    conversation = _new_conversation(service, basis.world_id)
    scene_a = _add_graph_ask(
        service,
        basis,
        conversation.conversation_id,
        sequence=1,
        target_id="beat:scene-a",
        question="What happened in scene A?",
        answer="Scene A exposed the hidden route.",
    )
    next_proposal_target = "beat:scene-b"

    pairs = AgentConversationService().list_completed_plan_ask_context(
        basis.world_id, basis
    )

    assert len(pairs) == 1
    pair = pairs[0]
    assert pair.source_record_id == scene_a.turn_id
    assert pair.question == "What happened in scene A?"
    assert pair.answer == "Scene A exposed the hidden route."
    attribution = pair.history_attribution
    assert attribution is not None
    assert attribution.source_turn_id == scene_a.turn_id
    assert attribution.source_conversation_id == conversation.conversation_id
    assert attribution.surface_id == "plan"
    assert attribution.surface_instance_id == "plan-ask-pane-1"
    assert attribution.plan_basis == basis
    assert attribution.playable_target is not None
    assert attribution.playable_target.id == "beat:scene-a"
    assert attribution.playable_target.id != next_proposal_target
    assert attribution.answer_basis == "committed_plan_plus_world_graph"
    assert attribution.answer_context_status == "graph_grounded_partial"
    assert attribution.answer_segments[0].text == pair.answer
    assert attribution.citation_map is not None
    assert (
        attribution.citation_map.context_receipt_sha256
        == attribution.context_receipt_sha256
    )
    assert attribution.citation_map.entries[0].target_id == "assertion-1"


@pytest.mark.parametrize("corruption", ["receipt_plan_basis", "target_identity"])
def test_invalid_graph_ask_authority_fails_closed(
    application_state_dsn: str, corruption: str
) -> None:
    import psycopg

    service = AgentConversationService()
    basis = _basis()
    conversation = _new_conversation(service, basis.world_id)
    turn = _add_graph_ask(
        service,
        basis,
        conversation.conversation_id,
        sequence=1,
        target_id="beat:scene-a",
        question="What happened in scene A?",
        answer="Scene A exposed the hidden route.",
    )
    with psycopg.connect(application_state_dsn, autocommit=True) as conn:
        if corruption == "receipt_plan_basis":
            from psycopg.types.json import Jsonb

            receipt, completion = conn.execute(
                """
                SELECT graph_context_receipt, completion
                FROM agent.turn
                WHERE turn_id = %s
                """,
                (turn.turn_id,),
            ).fetchone()
            receipt["plan_basis"]["document_id"] = "another-plan-document"
            canonical_receipt = {
                key: value
                for key, value in receipt.items()
                if key != "context_receipt_sha256"
            }
            new_receipt_digest = hashlib.sha256(
                json.dumps(
                    canonical_receipt,
                    ensure_ascii=False,
                    sort_keys=True,
                    separators=(",", ":"),
                    allow_nan=False,
                ).encode("utf-8")
            ).hexdigest()
            receipt["context_receipt_sha256"] = new_receipt_digest
            completion["context_receipt_sha256"] = new_receipt_digest
            completion["citation_map"]["context_receipt_sha256"] = new_receipt_digest
            conn.execute(
                """
                UPDATE agent.turn
                SET graph_context_receipt = %s, completion = %s
                WHERE turn_id = %s
                """,
                (Jsonb(receipt), Jsonb(completion), turn.turn_id),
            )
        else:
            conn.execute(
                """
                UPDATE agent.turn_reference
                SET object_id = %s
                WHERE turn_id = %s
                  AND reference_role = 'supporting'
                  AND kind = 'dmb_plan_playable_target_v1'
                """,
                ("beat:scene-b", turn.turn_id),
            )

    with pytest.raises(ApplicationStateIntegrityError):
        AgentConversationService().list_completed_plan_ask_context(
            basis.world_id, basis
        )


def test_newer_exact_basis_rows_in_another_world_do_not_consume_source_cap(
    application_state_dsn: str,
) -> None:
    service = AgentConversationService()
    basis = _basis()
    target_conversation = _new_conversation(service, basis.world_id)
    target_turns = [
        _add_turn(
            service,
            basis.world_id,
            target_conversation.conversation_id,
            basis,
            sequence=sequence,
            question=f"target world {sequence}",
        )
        for sequence in range(1, 3)
    ]

    other_world_id = "ask-projection-other-world"
    other_basis = basis.model_copy(update={"world_id": other_world_id})
    other_conversation = _new_conversation(service, other_world_id)
    for sequence in range(1, 5):
        other_turn = _add_turn(
            service,
            other_world_id,
            other_conversation.conversation_id,
            other_basis,
            sequence=sequence,
            question=f"other world {sequence}",
        )
        _set_accepted_at(
            application_state_dsn,
            other_turn.turn_id,
            datetime.now(UTC) + timedelta(days=1, seconds=sequence),
        )

    pairs = service.list_completed_plan_ask_context(basis.world_id, basis, limit=2)
    assert [pair.source_record_id for pair in pairs] == [
        turn.turn_id for turn in target_turns
    ]
    assert [pair.question for pair in pairs] == ["target world 1", "target world 2"]


def test_eligibility_precedes_cap_and_newest_six_are_returned_oldest_first(
    application_state_dsn: str,
) -> None:
    service = AgentConversationService()
    basis = _basis()
    conversation = _new_conversation(service, basis.world_id)
    now = datetime.now(UTC)

    older_eligible = _add_turn(
        service,
        basis.world_id,
        conversation.conversation_id,
        basis,
        sequence=1,
        question="eligible one",
    )
    _set_accepted_at(application_state_dsn, older_eligible.turn_id, now)
    failed = _add_turn(
        service,
        basis.world_id,
        conversation.conversation_id,
        basis,
        sequence=2,
        question="failed newer",
        fail=True,
    )
    _set_accepted_at(application_state_dsn, failed.turn_id, now + timedelta(seconds=10))
    _add_turn(
        service,
        basis.world_id,
        conversation.conversation_id,
        basis,
        sequence=3,
        question="accepted newer",
        complete=False,
    )
    _add_turn(
        service,
        basis.world_id,
        conversation.conversation_id,
        basis,
        sequence=4,
        question="running newer",
        running=True,
    )
    for sequence in range(5, 12):
        turn = _add_turn(
            service,
            basis.world_id,
            conversation.conversation_id,
            basis,
            sequence=sequence,
            question=f"eligible {sequence}",
        )
        _set_accepted_at(
            application_state_dsn,
            turn.turn_id,
            now + timedelta(seconds=sequence),
        )

    pairs = service.list_completed_plan_ask_context(basis.world_id, basis)
    assert len(pairs) == 6
    assert [pair.question for pair in pairs] == [
        "eligible 6",
        "eligible 7",
        "eligible 8",
        "eligible 9",
        "eligible 10",
        "eligible 11",
    ]
    assert [pair.source_sequence for pair in pairs] == [6, 7, 8, 9, 10, 11]


def test_pointer_rotation_and_empty_pointer_never_create_or_leak_history(
    application_state_dsn: str,
) -> None:
    import psycopg

    service = AgentConversationService()
    basis = _basis()
    first = _new_conversation(service, basis.world_id)
    archived_turn = _add_turn(
        service,
        basis.world_id,
        first.conversation_id,
        basis,
        sequence=1,
        question="archived pair",
    )
    second = service.new_conversation(
        ConversationCommand(
            world_id=basis.world_id,
            command_id=uuid4(),
            expected_pointer_revision=1,
            expected_active_conversation_id=first.conversation_id,
        )
    )
    assert service.list_completed_plan_ask_context(basis.world_id, basis) == []
    assert service.get_active_conversation(basis.world_id).conversation_id == second.conversation_id

    empty_world = "ask-projection-no-pointer"
    with psycopg.connect(application_state_dsn) as conn:
        before = conn.execute(
            "SELECT count(*) FROM agent.world_state WHERE world_id = %s", (empty_world,)
        ).fetchone()[0]
    assert service.list_completed_plan_ask_context(
        empty_world, _basis(empty_world)
    ) == []
    with psycopg.connect(application_state_dsn) as conn:
        after = conn.execute(
            "SELECT count(*) FROM agent.world_state WHERE world_id = %s", (empty_world,)
        ).fetchone()[0]
    assert before == after == 0
    assert archived_turn.turn_id not in {
        pair.source_record_id
        for pair in service.list_completed_plan_ask_context(basis.world_id, basis)
    }


def test_equal_acceptance_times_are_stably_ordered_by_source_sequence(
    application_state_dsn: str,
) -> None:
    service = AgentConversationService()
    basis = _basis()
    conversation = _new_conversation(service, basis.world_id)
    turns = [
        _add_turn(
            service,
            basis.world_id,
            conversation.conversation_id,
            basis,
            sequence=sequence,
            question=f"tied {sequence}",
        )
        for sequence in range(1, 4)
    ]
    tied_at = datetime(2026, 10, 3, tzinfo=UTC)
    for turn in turns:
        _set_accepted_at(application_state_dsn, turn.turn_id, tied_at)

    pairs = service.list_completed_plan_ask_context(basis.world_id, basis)
    assert [pair.source_sequence for pair in pairs] == [1, 2, 3]
    assert [pair.source_record_id for pair in pairs] == [turn.turn_id for turn in turns]


def test_supporting_only_incomplete_unresolved_and_wrong_surface_are_excluded(
    application_state_dsn: str,
) -> None:
    service = AgentConversationService()
    basis = _basis()
    conversation = _new_conversation(service, basis.world_id)
    nonmatching_primary = HistoricalReference(
        resolution="unresolved",
        kind="plan",
        object_id=basis.document_id,
    )
    _add_turn(
        service,
        basis.world_id,
        conversation.conversation_id,
        basis,
        sequence=1,
        question="supporting only",
        primary=nonmatching_primary,
        supporting=[_reference(basis)],
    )
    _add_turn(
        service,
        basis.world_id,
        conversation.conversation_id,
        basis,
        sequence=2,
        question="absent primary",
        primary=HistoricalReference(resolution="absent"),
    )
    incomplete_primary = HistoricalReference(
        resolution="resolved",
        kind="plan",
        object_id=basis.document_id,
        content_sha256=basis.content_sha256,
    )
    _add_turn(
        service,
        basis.world_id,
        conversation.conversation_id,
        basis,
        sequence=3,
        question="incomplete typed basis",
        primary=incomplete_primary,
    )
    _add_turn(
        service,
        basis.world_id,
        conversation.conversation_id,
        basis,
        sequence=4,
        question="wrong surface",
        surface_id="index",
    )
    _add_turn(
        service,
        basis.world_id,
        conversation.conversation_id,
        basis,
        sequence=5,
        question="unresolved surface",
        surface_resolution="unresolved",
        surface_id=None,
    )
    assert service.list_completed_plan_ask_context(basis.world_id, basis) == []


def test_world_mismatch_and_invalid_limits_fail_before_database_access(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    service = AgentConversationService()
    basis = _basis()

    def fail_if_called(*_args, **_kwargs):
        raise AssertionError("database access must not occur after invalid input")

    monkeypatch.setattr(service_module, "_ready_dsn", fail_if_called)
    with pytest.raises(ApplicationStateValidationError, match="must match"):
        service.list_completed_plan_ask_context("different-world", basis)
    for limit in (0, 7, True, 1.5):
        with pytest.raises(ApplicationStateValidationError, match="between 1 and 6"):
            service.list_completed_plan_ask_context(basis.world_id, basis, limit=limit)


def test_repository_projection_uses_one_unlocked_select(monkeypatch: pytest.MonkeyPatch) -> None:
    statements: list[str] = []

    class Cursor:
        def __enter__(self):
            return self

        def __exit__(self, *_args):
            return False

        def execute(self, statement, _params):
            statements.append(statement)

        def fetchall(self):
            return []

    class Connection:
        def cursor(self, **_kwargs):
            return Cursor()

    result = repo.list_completed_plan_ask_context(
        Connection(), "ask-projection-world", _basis(), limit=6
    )
    assert result == []
    assert len(statements) == 1
    normalized = " ".join(statements[0].lower().split())
    assert normalized.startswith("select ")
    assert " for update" not in normalized
    assert " for share" not in normalized
    assert "t.sequence desc" in normalized
    assert "t.turn_id desc" in normalized


@pytest.mark.parametrize("source_opened", [False, True])
def test_v2_completed_ask_history_preserves_exact_source_reads_and_origin(
    application_state_dsn: str, source_opened: bool,
) -> None:
    service = AgentConversationService()
    basis = _basis()
    conversation = _new_conversation(service, basis.world_id)
    turn = _add_graph_ask(
        service, basis, conversation.conversation_id, sequence=1,
        target_id="beat:scene-a", question="What happened in scene A?",
        answer="Scene A exposed the hidden route.", source_opened=source_opened,
    )
    pair, = AgentConversationService().list_completed_plan_ask_context(basis.world_id, basis)
    attribution = pair.history_attribution
    assert attribution is not None
    assert attribution.source_turn_id == turn.turn_id == pair.source_record_id
    assert attribution.source_conversation_id == conversation.conversation_id
    assert attribution.source_sequence == 1
    assert attribution.surface_id == "plan"
    assert attribution.surface_instance_id == "plan-ask-pane-1"
    assert attribution.plan_basis == basis
    assert attribution.playable_target.id == "beat:scene-a"
    assert attribution.playable_target.marker_grammar_version == "v2"
    assert pair.question == "What happened in scene A?"
    assert pair.answer == "Scene A exposed the hidden route."
    assert attribution.context_receipt_sha256 == turn.graph_context_receipt.context_receipt_sha256
    assert attribution.answer_basis == "committed_plan_plus_world_graph"
    assert attribution.answer_context_status == "graph_grounded_partial"
    assert isinstance(attribution.citation_map, PlanWorldGraphCitationMapV2)
    citation, = attribution.citation_map.entries
    assert citation.source_opened is source_opened
    assert citation.source_read_ids == (["source-read:history-1"] if source_opened else [])
    assert attribution.answer_segments == turn.completion.answer_segments
    assert PlanAskHistoryAttributionV1.model_validate_json(attribution.model_dump_json(by_alias=True)) == attribution
    assert AgentConversationService().list_completed_plan_ask_context(
        basis.world_id, basis.model_copy(update={"content_sha256": "f" * 64})
    ) == []


@pytest.mark.parametrize("corruption", ["foreign_read", "excluded_read", "target_identity"])
def test_v2_ask_history_rejects_source_or_target_outside_producing_authority(
    application_state_dsn: str, corruption: str,
) -> None:
    import psycopg
    from psycopg.types.json import Jsonb

    service = AgentConversationService()
    basis = _basis()
    conversation = _new_conversation(service, basis.world_id)
    turn = _add_graph_ask(
        service, basis, conversation.conversation_id, sequence=1,
        target_id="beat:scene-a", question="What happened in scene A?",
        answer="Scene A exposed the hidden route.", source_opened=True,
    )
    with psycopg.connect(application_state_dsn, autocommit=True) as conn:
        if corruption == "target_identity":
            conn.execute(
                "UPDATE agent.turn_reference SET object_id = 'beat:scene-b' WHERE turn_id = %s AND reference_role = 'supporting'",
                (turn.turn_id,),
            )
        else:
            execution, completion = conn.execute(
                "SELECT graph_context_execution, completion FROM agent.turn WHERE turn_id = %s", (turn.turn_id,),
            ).fetchone()
            if corruption == "foreign_read":
                completion["citation_map"]["entries"][0]["source_read_ids"] = ["source-read:other-turn"]
                # Reseal the binding to prove the read authority check, rather than just digest mismatch.
                execution["events"][-1]["completion_sha256"] = hashlib.sha256(json.dumps(
                    completion, ensure_ascii=False, sort_keys=True, separators=(",", ":"), allow_nan=False,
                ).encode("utf-8")).hexdigest()
            else:
                attempt = next(event for event in execution["events"] if event["kind"] == "provider_attempt_authorized_v2")
                attempt["included_source_read_event_ids"] = []
            conn.execute(
                "UPDATE agent.turn SET graph_context_execution = %s, completion = %s WHERE turn_id = %s",
                (Jsonb(execution), Jsonb(completion), turn.turn_id),
            )
    with pytest.raises(ApplicationStateIntegrityError):
        AgentConversationService().list_completed_plan_ask_context(basis.world_id, basis)


def test_v1_completion_history_remains_typed_with_persisted_execution(
    application_state_dsn: str,
) -> None:
    service = AgentConversationService()
    basis = _basis()
    conversation = _new_conversation(service, basis.world_id)
    turn = _add_graph_ask(
        service, basis, conversation.conversation_id, sequence=1,
        target_id="beat:scene-a", question="What happened in scene A?",
        answer="Scene A exposed the hidden route.", source_opened=False, completion_version=1,
    )
    pair, = AgentConversationService().list_completed_plan_ask_context(basis.world_id, basis)
    attribution = pair.history_attribution
    assert attribution is not None
    assert attribution.source_turn_id == turn.turn_id
    assert attribution.plan_basis == basis
    assert attribution.playable_target.id == "beat:scene-a"
    assert isinstance(attribution.citation_map, PlanWorldGraphCitationMapV1)
    assert attribution.citation_map.entries[0].source_opened is False
    assert "source_read_ids" not in attribution.citation_map.entries[0].model_dump()
    assert PlanAskHistoryAttributionV1.model_validate_json(attribution.model_dump_json(by_alias=True)) == attribution


@pytest.mark.parametrize("version", [1, 2])
def test_historical_graph_operation_ask_reads_and_replays_unchanged(
    application_state_dsn: str, monkeypatch: pytest.MonkeyPatch, version: int,
) -> None:
    service = AgentConversationService()
    basis = _basis()
    conversation = _new_conversation(service, basis.world_id)
    for sequence in range(1, 5):
        _add_turn(service, basis.world_id, conversation.conversation_id, basis,
                  sequence=sequence, question=f"Synthetic prior question {sequence}")
    completed = _add_graph_ask(
        service, basis, conversation.conversation_id, sequence=5,
        target_id="beat:historical-card", question="Synthetic historical Graph question",
        answer="Synthetic historical Graph answer.", source_opened=False,
        historical_graph_operation=True, execution_version=version, completion_version=version,
    )
    frozen = completed.model_dump(mode="json", by_alias=True)
    assert completed.graph_context_receipt.graph_packet.selection_policy_version == "parent_initial_retrieval_v1"
    assert completed.graph_context_receipt.graph_packet.evidence_sufficiency_status == "insufficient"
    assert completed.graph_context_receipt.assembled_input.packet_disposition == "omitted_insufficient"
    assert completed.graph_context_receipt.assembled_input.dispatched_assertion_ids == []
    assert completed.graph_context_receipt.assembled_input.dispatched_relationship_ids == []
    assert completed.graph_context_receipt.assembled_input.dispatched_evidence_ref_ids == []
    operation = completed.graph_context_execution.events[3]
    assert len(operation.relationship_ids) == 6 and len(operation.evidence_ref_ids) == 17
    assert operation.truncated and operation.coverage_status == "incomplete"
    assert completed.completion.answer_context_status == "graph_grounded_partial"
    assert completed.completion.citation_map.entries[0].target_id == "rel:004"
    assert completed.completion.citation_map.entries[0].evidence_ref_ids == ["ev:016"]
    assert "evidence-1" not in completed.graph_context_receipt.assembled_input.dispatched_evidence_ref_ids
    assert completed.completion.citation_map.entries[0].source_opened is False
    fresh = AgentConversationService()
    assert fresh.list_turns(basis.world_id, conversation.conversation_id)[-1].model_dump(mode="json", by_alias=True) == frozen
    pair = next(pair for pair in fresh.list_completed_plan_ask_context(basis.world_id, basis) if pair.source_record_id == completed.turn_id)
    assert pair.source_sequence == 5
    assert pair.answer == completed.assistant_text
    assert pair.history_attribution.source_turn_id == completed.turn_id
    assert pair.history_attribution.plan_basis == basis
    assert pair.history_attribution.playable_target.id == "beat:historical-card"
    assert pair.history_attribution.citation_map == completed.completion.citation_map
    assert PlanAskHistoryAttributionV1.model_validate_json(pair.history_attribution.model_dump_json(by_alias=True)) == pair.history_attribution
    submission = TurnSubmission(
        world_id=basis.world_id, conversation_id=conversation.conversation_id,
        idempotency_key=completed.idempotency_key, expected_conversation_revision=5,
        user_text=completed.user_text, provenance=completed.provenance,
        submitted_intent_v2=SubmittedTurnIntentV2(
            world_id=basis.world_id, client_thread_id="ask-history-test-thread", message=completed.user_text,
            surface_id="plan", surface_instance_id="plan-ask-pane-5", client_work_state="saved_clean",
            primary_work=SubmittedPrimaryWorkIntentV1(
                kind="plan", object_id=basis.document_id, expected_revision=basis.object_revision,
                expected_revision_n=basis.revision_n, expected_content_sha256=basis.content_sha256,
            ),
            plan_context_policy=PlanContextPolicyV1(policy="auto_plan_world"),
            playable_target=SubmittedPlanPlayableTargetV1(schema="dmb_plan_playable_target_v1", kind="beat", id="beat:historical-card"),
            graph_request=SubmittedGraphRequestIntentV1(mode="none"), graph_selection=None,
        ),
        graph_context_receipt=completed.graph_context_receipt,
        graph_context_execution=completed.graph_context_execution.model_copy(update={"events": []}),
    )
    monkeypatch.setattr(service_module, "_lock_pointer", lambda *_args: pytest.fail("completed replay touched mutable acceptance state"))
    replayed = fresh.accept_turn(submission)
    assert replayed.model_dump(mode="json", by_alias=True) == frozen
    assert fresh.list_turns(basis.world_id, conversation.conversation_id)[-1].model_dump(mode="json", by_alias=True) == frozen
