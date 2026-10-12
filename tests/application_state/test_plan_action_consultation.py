"""Synthetic action/Graph contracts and isolated PostgreSQL owning witnesses."""

from __future__ import annotations

from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timezone
from uuid import uuid4

import psycopg
import pytest
from pydantic import ValidationError

from application_state.agent_conversation.types import (
    GraphExecutionAccountingV1, GraphExecutionPolicyV2,
    GraphSourceReadScopeV2, GraphSourceScopeAnchorV2,
    CompletionBindingEventV1, PlanWorldGraphExecutionV2,
    PlanWorldGraphAssembledInputV1, PlanWorldGraphAuthorityV1,
    PlanWorldGraphCitationMapV2, PlanWorldGraphCitationV2,
    PlanWorldGraphClaimSegmentV1, PlanWorldGraphPacketV1,
    PlanWorldGraphConnectiveSegmentV1,
    ProviderAttemptAuthorizedEventV2, ProviderOutcomeEventV1,
    SourceReadAnchorReceiptV2, SourceReadAuthorizationEventV2,
    ValidatedGraphOperationEventV1, ValidatedSourceReadEventV2,
    graph_execution_policy_digest_v2,
)
from application_state.cli import upgrade_to_head
from application_state.config import APPLICATION_STATE_DSN_ENV
from application_state.errors import ApplicationStateConflictError, ApplicationStateValidationError
from application_state.plan_action_dialogue.graph_consultation import (
    build_consultation_receipt, consultation_result_digest,
    historical_ask_answer_digest, render_answer_segments,
)
from application_state.plan_action_dialogue.service import PlanActionDialogueService
from application_state.plan_action_dialogue.types import (
    PlanActionBasis, PlanActionClarificationResult, PlanActionConsultation,
    PlanActionConsultationReceipt, PlanActionContinuation,
    PlanActionContextUnavailableResult, PlanActionProposalResult,
    PlanActionRecord, PlanActionReservation,
)
from tests.application_state.conftest import _admin_dsn, _create_database, _drop_database, _replace_database


@pytest.fixture
def application_state_dsn(monkeypatch):
    """Use the repository test-admin configuration, with a new action DB per test."""
    admin = _admin_dsn()
    name = "prime_action_consultation_" + uuid4().hex[:12]
    _create_database(admin, name)
    dsn = _replace_database(admin, name)
    monkeypatch.setenv(APPLICATION_STATE_DSN_ENV, dsn)
    try:
        upgrade_to_head(dsn=dsn)
        yield dsn
    finally:
        monkeypatch.delenv(APPLICATION_STATE_DSN_ENV, raising=False)
        _drop_database(admin, name)


def reservation(*, basis=None, instruction="Give the observatory a hidden door."):
    return PlanActionReservation(
        idempotency_key=uuid4(), request_fingerprint="b" * 64, action_type="revise",
        basis=basis or PlanActionBasis(
            world_id="synthetic-world", document_id="synthetic-plan", object_revision=4,
            work_revision_id=uuid4(), revision_n=2, content_sha256="a" * 64,
        ),
        draft_matches_basis=False, draft_sha256="c" * 64,
        target_kind="replace_selection", selected_text_sha256="d" * 64,
        instruction=instruction,
    )


def model_action(request=None):
    request = request or reservation()
    now = datetime.now(timezone.utc)
    return PlanActionRecord(
        **request.model_dump(mode="python"), action_id=uuid4(), status="pending",
        assistant_summary=None, failure_code=None, dispatch_token=uuid4(), fence=1,
        action_sequence=1, accepted_at=now, completed_at=None, lease_expires_at=now,
    )


def frozen_inputs(action, *, revision="graph-r1", continuation=None):
    authority = PlanWorldGraphAuthorityV1(
        managed_world_id=action.basis.world_id, native_world_id="native-synthetic",
        binding_version=1, scope_mode="world", campaign_id=None,
        admissibility_version="gm-v1", graph_revision=revision,
    )
    packet = PlanWorldGraphPacketV1(
        packet_serializer_version="canonical-json-utf8-v1",
        selection_policy_version="parent_initial_retrieval_with_bounded_source_index_v1",
        evidence_sufficiency_policy_version="synthetic-v1", retrieval_packet_sha256="1" * 64,
        candidate_assertion_ids=["assertion:observatory"], candidate_relationship_ids=[],
        candidate_evidence_ref_ids=["evidence:authored"], retrieval_status="complete",
        evidence_sufficiency_status="sufficient", result_limit=8,
        coverage_status="complete", truncated=False, omission_reasons=[],
    )
    assembled = PlanWorldGraphAssembledInputV1(
        assembler_version="synthetic-v1", budget_policy_version="synthetic-v1",
        provider_model_name="synthetic", provider_model_version="1",
        tokenizer_name="synthetic", tokenizer_version="1", provider_envelope_input_tokens=10,
        output_token_reserve=10, context_window_limit=100,
        packet_disposition="included", dispatched_packet_sha256="2" * 64,
        dispatched_assertion_ids=["assertion:observatory"], dispatched_relationship_ids=[],
        dispatched_evidence_ref_ids=["evidence:authored"], source_token_accounting=[],
        included_history=[], assembled_input_sha256="3" * 64,
    )
    receipt = build_consultation_receipt(
        action=action, surface_instance_id="plan-pane", graph_authority=authority,
        graph_packet=packet, assembled_input=assembled, continuation=continuation,
    )
    policy = GraphExecutionPolicyV2(
        policy_version="plan_world_graph_execution_v1",
        allowed_graph_operations=["expand_graph_retrieval"], max_provider_attempts=2,
        max_graph_operations=2, max_results_per_operation=8,
        max_total_provider_input_tokens=100, max_total_provider_output_tokens=40,
        provider_input_accounting=GraphExecutionAccountingV1(
            kind="exact_token_count", estimator="synthetic"
        ), source_opened=False,
        source_read_scope=GraphSourceReadScopeV2(
            retrieval_session_id="synthetic-session", world_id=action.basis.world_id,
            campaign_id=None, graph_revision=revision,
            admitted_anchors=[GraphSourceScopeAnchorV2(
                anchor_id="anchor:authored", evidence_ref_id="evidence:authored",
                source_artifact_id="artifact:authored", source_revision_id="source-r1",
            )],
        ), max_source_read_calls=2, max_source_read_anchors=2,
        max_source_read_chars=24000, max_chars_per_source_read=12000,
    )
    return receipt, policy


def consultation_events(receipt, policy):
    first_id, final_id, call_id = uuid4(), uuid4(), uuid4()
    def provider(attempt, sequence, digest, graph_ids=(), read_ids=()):
        return ProviderAttemptAuthorizedEventV2(
            event_id=uuid4(), sequence=sequence, kind="provider_attempt_authorized_v2",
            provider_attempt_id=attempt, envelope_sha256=digest,
            serializer_version="canonical-json-utf8-v1", provider="synthetic",
            model="synthetic", api_mode="messages", tool_schema_sha256="4" * 64,
            input_accounting_kind="exact_token_count", input_estimator="synthetic",
            input_tokens=10, output_token_reserve=10,
            included_assertion_ids=["assertion:observatory"], included_relationship_ids=[],
            included_evidence_ref_ids=["evidence:authored"],
            included_graph_event_ids=list(graph_ids), included_source_read_event_ids=list(read_ids),
        )
    operation = ValidatedGraphOperationEventV1(
        event_id=uuid4(), sequence=3, kind="validated_graph_operation", operation_id=uuid4(),
        operation="expand_graph_retrieval", request_arguments_sha256="5" * 64,
        graph_revision=receipt.graph_authority.graph_revision, result_packet_sha256="6" * 64,
        assertion_ids=["assertion:observatory"], relationship_ids=[],
        evidence_ref_ids=["evidence:authored"], evidence_sufficiency_status="sufficient",
        coverage_status="complete", truncated=False, source_opened=False,
    )
    auth = SourceReadAuthorizationEventV2(
        event_id=uuid4(), sequence=4, kind="source_read_authorized_v2", read_call_id=call_id,
        context_receipt_sha256=receipt.consultation_receipt_sha256,
        execution_policy_sha256=graph_execution_policy_digest_v2(
            receipt.consultation_receipt_sha256, policy
        ), retrieval_session_id=policy.source_read_scope.retrieval_session_id,
        world_id=receipt.basis.world_id, campaign_id=None,
        graph_revision=receipt.graph_authority.graph_revision,
        anchors=policy.source_read_scope.admitted_anchors, max_chars=12000,
    )
    read = ValidatedSourceReadEventV2(
        event_id=uuid4(), sequence=5, kind="validated_source_read_v2", read_call_id=call_id,
        receipts=[SourceReadAnchorReceiptV2(
            source_read_id="source-read:authored", anchor_id="anchor:authored",
            evidence_ref_id="evidence:authored", source_artifact_id="artifact:authored",
            source_revision_id="source-r1", outcome="enough", content_sha256="7" * 64,
            line_start=1, line_end=4, returned_chars=80, truncated=False,
            evidence_sufficiency_status="sufficient",
        )],
    )
    events = [provider(first_id, 0, receipt.assembled_input.assembled_input_sha256),
              ProviderOutcomeEventV1(event_id=uuid4(), sequence=1, kind="provider_outcome",
                                     provider_attempt_id=first_id, outcome="sdk_entered"),
              ProviderOutcomeEventV1(event_id=uuid4(), sequence=2, kind="provider_outcome",
                                     provider_attempt_id=first_id, outcome="response_received"),
              operation, auth, read,
              provider(final_id, 6, "8" * 64, [operation.event_id], [read.event_id]),
              ProviderOutcomeEventV1(event_id=uuid4(), sequence=7, kind="provider_outcome",
                                     provider_attempt_id=final_id, outcome="sdk_entered"),
              ProviderOutcomeEventV1(event_id=uuid4(), sequence=8, kind="provider_outcome",
                                     provider_attempt_id=final_id, outcome="response_received")]
    return events


def attributed_result(receipt, events, *, proposal=False, disposition="supported_context_used"):
    claim = PlanWorldGraphClaimSegmentV1(
        kind="graph_claim", claim_id="claim:owner", text="Mira owns the observatory.",
        target_kind="assertion", target_id="assertion:observatory",
        graph_revision=receipt.graph_authority.graph_revision,
        evidence_ref_ids=["evidence:authored"],
    )
    common = dict(
        result_id=uuid4(), consultation_receipt_sha256=receipt.consultation_receipt_sha256,
        message="Mira owns the observatory.\nIs the new door hers?",
        producing_provider_attempt_id=events[6].provider_attempt_id,
        answer_segments=[claim, PlanWorldGraphConnectiveSegmentV1(kind="connective", text="Is the new door hers?")],
        citation_map=PlanWorldGraphCitationMapV2(
            context_receipt_sha256=receipt.consultation_receipt_sha256,
            entries=[PlanWorldGraphCitationV2(
                claim_id=claim.claim_id, target_kind=claim.target_kind, target_id=claim.target_id,
                graph_revision=claim.graph_revision, evidence_ref_ids=claim.evidence_ref_ids,
                source_read_ids=["source-read:authored"], source_opened=True,
            )],
        ), claim_graph_event_ids={claim.claim_id: [events[3].event_id]},
    )
    return (PlanActionProposalResult(kind="proposal", disposition=disposition,
                                    proposal_sha256="9" * 64, **common)
            if proposal else PlanActionClarificationResult(kind="clarification", **common))


def frozen_action(service, action, **kwargs):
    receipt, policy = frozen_inputs(action, **kwargs)
    frozen, fresh = service.freeze_consultation(
        action_id=action.action_id, token=action.dispatch_token, fence=action.fence,
        receipt=receipt, policy=policy,
    )
    assert fresh
    return frozen, receipt, policy


def complete_action(service, action, *, proposal=False, **kwargs):
    frozen, receipt, policy = frozen_action(service, action, **kwargs)
    events = consultation_events(receipt, policy)
    for event in events:
        frozen, fresh = service.append_consultation_event(
            action_id=action.action_id, token=action.dispatch_token, fence=action.fence, event=event,
        )
        assert fresh
    result = attributed_result(receipt, events, proposal=proposal)
    return service.finish_consultation(
        action_id=action.action_id, token=action.dispatch_token, fence=action.fence, result=result,
    ), events


def test_action_receipt_is_truthful_and_digest_bound():
    action = model_action()
    receipt, _policy = frozen_inputs(action)
    assert receipt.basis == action.basis and receipt.draft_sha256 != receipt.basis.content_sha256
    assert "plan_context_policy" not in receipt.model_dump()
    assert "plan_basis" not in receipt.model_dump()
    assert "consultation" not in action.model_dump(mode="json")
    for changes in ({"draft_sha256": "e" * 64}, {"instruction": "Changed intent."},
                    {"graph_authority": receipt.graph_authority.model_copy(update={"graph_revision": "r2"})}):
        with pytest.raises(ValidationError):
            PlanActionConsultationReceipt.model_validate(
                receipt.model_dump(mode="python") | changes
            )
    with pytest.raises(ValidationError):
        PlanActionClarificationResult.model_validate({"kind": "clarification", "replacement_markdown": "bad"})


def model_consultation(receipt, policy, events, result):
    binding = CompletionBindingEventV1(
        event_id=uuid4(), sequence=len(events), kind="completion_binding",
        provider_attempt_id=result.producing_provider_attempt_id,
        completion_sha256=consultation_result_digest(result),
        claim_graph_event_ids=result.claim_graph_event_ids,
    )
    return PlanActionConsultation(
        receipt=receipt,
        execution=PlanWorldGraphExecutionV2(
            context_receipt_sha256=receipt.consultation_receipt_sha256,
            execution_policy_sha256=graph_execution_policy_digest_v2(
                receipt.consultation_receipt_sha256, policy
            ), policy=policy, events=[*events, binding],
        ), result=result,
    )


@pytest.mark.parametrize("mutation", ["claim_target", "graph_revision", "context_as_source"])
def test_action_attribution_rejects_foreign_claims_and_context_as_evidence(mutation):
    receipt, policy = frozen_inputs(model_action())
    events = consultation_events(receipt, policy)
    result = attributed_result(receipt, events)
    model_consultation(receipt, policy, events, result)
    if mutation == "context_as_source":
        citation = result.citation_map.entries[0].model_copy(
            update={"source_read_ids": ["dm-context-anchor:v2:session-22"]}
        )
        changed = result.model_copy(update={
            "citation_map": result.citation_map.model_copy(update={"entries": [citation]})
        })
    else:
        changes = {"target_id": "foreign-target"} if mutation == "claim_target" else {"graph_revision": "foreign-revision"}
        claim = result.answer_segments[0].model_copy(update=changes)
        changed = result.model_copy(update={"answer_segments": [claim]})
    with pytest.raises(ValueError):
        model_consultation(receipt, policy, events, changed)


def test_action_override_requires_explicit_linked_clarification():
    receipt, policy = frozen_inputs(model_action())
    events = consultation_events(receipt, policy)
    result = attributed_result(receipt, events, proposal=True,
                               disposition="explicit_draft_override_after_clarification")
    with pytest.raises(ValueError, match="linked clarification"):
        model_consultation(receipt, policy, events, result)


def test_shared_extraction_preserves_ask_validation_and_wire_shapes():
    from tests.application_state.test_agent_conversation_service import _indexed_graph_completion_fixture
    from tests.application_state.test_agent_conversation_postgres import _execution_completion_fixture
    from application_state.agent_conversation.types import (
        _ask_graph_validation_inputs, derive_graph_execution_evidence_status,
        validate_execution_completion,
    )
    v1_receipt, v1_completion, v1_execution, v1_attempt, _ = _execution_completion_fixture()
    v2_receipt, v2_execution, v2_completion, v2_attempt, v2_operation = _indexed_graph_completion_fixture(packet_coverage="incomplete")
    for receipt, execution, completion, attempt, claims in [
        (v1_receipt, v1_execution, v1_completion, v1_attempt, {"claim-classification": []}),
        (v2_receipt, v2_execution, v2_completion, v2_attempt, {"claim-indexed": [v2_operation]}),
    ]:
        before = execution.model_dump_json(by_alias=True)
        validate_execution_completion(completion, receipt, execution, attempt, claims)
        expected = derive_graph_execution_evidence_status(
            context_receipt_sha256=completion.context_receipt_sha256,
            answer_segments=completion.answer_segments, citation_map=completion.citation_map,
            inputs=_ask_graph_validation_inputs(receipt), execution=execution,
            producing_provider_attempt_id=attempt, claim_graph_event_ids=claims,
        )
        assert expected == completion.answer_context_status
        assert type(execution).model_validate_json(before).model_dump_json(by_alias=True) == before


@pytest.mark.parametrize("revision_case", ["current", "older"])
def test_optional_historical_ask_attribution_keeps_basis_and_source_identity(revision_case):
    from tests.application_state.test_agent_conversation_service import _indexed_graph_completion_fixture
    from application_state.agent_conversation.types import PlanAskHistoryAttributionV1, PlanWorldGraphHistoryPinV1
    old, _execution, completion, _attempt, _event = _indexed_graph_completion_fixture(packet_coverage="incomplete")
    action = model_action(reservation(basis=PlanActionBasis.model_validate(old.plan_basis.model_dump())))
    receipt, _policy = frozen_inputs(action, revision=(old.graph_authority.graph_revision
                                    if revision_case == "current" else "graph-r2"))
    conversation_id, turn_id = uuid4(), uuid4()
    attribution = PlanAskHistoryAttributionV1(
        source_turn_id=turn_id, source_conversation_id=conversation_id, source_sequence=1,
        surface_instance_id="plan-pane", plan_basis=old.plan_basis, playable_target=None,
        context_receipt_sha256=old.context_receipt_sha256, answer_basis=completion.answer_basis,
        answer_context_status=completion.answer_context_status, answer_segments=completion.answer_segments,
        citation_map=completion.citation_map,
    )
    assembled = receipt.assembled_input.model_copy(update={
        "included_history": [PlanWorldGraphHistoryPinV1(turn_id=turn_id, answer_sha256=historical_ask_answer_digest(attribution))]
    })
    kwargs = dict(action=action, surface_instance_id="plan-pane", graph_authority=receipt.graph_authority,
                  graph_packet=receipt.graph_packet, assembled_input=assembled,
                  history_conversation_id=conversation_id)
    valid = build_consultation_receipt(**kwargs, history_attribution=[attribution])
    assert valid.history_attribution[0].source_turn_id == turn_id
    assert (valid.history_attribution[0].answer_segments[0].graph_revision
            == valid.graph_authority.graph_revision) == (revision_case == "current")
    with pytest.raises(ValueError, match="historical Ask"):
        build_consultation_receipt(**kwargs, history_attribution=[
            attribution.model_copy(update={"source_conversation_id": uuid4()})
        ])
    changed_answer = attribution.model_copy(update={"answer_segments": [
        attribution.answer_segments[0].model_copy(update={"text": "Changed answer under the same turn ID."})
    ]})
    with pytest.raises(ValueError, match="historical Ask"):
        build_consultation_receipt(**kwargs, history_attribution=[changed_answer])


@pytest.mark.parametrize("proposal", [False, True])
def test_pg_typed_result_and_source_receipts_survive_fresh_history(application_state_dsn, proposal):
    service = PlanActionDialogueService()
    request = reservation()
    action, fresh = service.reserve(request)
    assert fresh
    completed, events = complete_action(service, action, proposal=proposal)
    assert completed.status == "completed"
    assert completed.consultation.result.kind == ("proposal" if proposal else "clarification")
    reload = PlanActionDialogueService().get_by_key(request.basis.world_id, request.idempotency_key)
    assert reload.consultation == completed.consultation
    assert reload.consultation.execution.events[5] == events[5]
    assert reload.assistant_summary == render_answer_segments(reload.consultation.result.answer_segments)
    assert reload.consultation.result.answer_segments[-1].kind == "connective"
    assert service.list_status(request.basis).actions[0].consultation == reload.consultation
    assert service.completed_context(request.basis)[0].consultation == reload.consultation
    payload = reload.consultation.model_dump(mode="json", by_alias=True)
    assert "replacement_markdown" not in str(payload)
    assert "source_uri" not in str(payload) and "continuation_token" not in str(payload)
    assert "source-read:authored" in str(payload)
    replay, created = service.reserve(request)
    assert not created and replay.action_id == action.action_id
    assert replay.consultation == completed.consultation


def test_pg_freeze_and_provider_append_are_token_fenced_and_idempotent(application_state_dsn):
    service = PlanActionDialogueService()
    action, _ = service.reserve(reservation())
    receipt, policy = frozen_inputs(action)
    with pytest.raises(ApplicationStateConflictError):
        service.freeze_consultation(action_id=action.action_id, token=uuid4(), fence=action.fence,
                                    receipt=receipt, policy=policy)
    frozen, _, _ = frozen_action(service, action)
    same, created = service.freeze_consultation(
        action_id=action.action_id, token=action.dispatch_token, fence=action.fence,
        receipt=receipt, policy=policy,
    )
    assert not created and same.consultation == frozen.consultation
    changed, changed_policy = frozen_inputs(action, revision="new-head")
    with pytest.raises(ApplicationStateConflictError):
        service.freeze_consultation(action_id=action.action_id, token=action.dispatch_token,
                                    fence=action.fence, receipt=changed, policy=changed_policy)
    event = consultation_events(receipt, policy)[0]
    for token, fence in [(uuid4(), action.fence), (action.dispatch_token, action.fence + 1)]:
        with pytest.raises(ApplicationStateConflictError):
            service.append_consultation_event(action_id=action.action_id, token=token, fence=fence, event=event)
    recorded, fresh = service.append_consultation_event(
        action_id=action.action_id, token=action.dispatch_token, fence=action.fence, event=event,
    )
    assert fresh
    duplicate, fresh = service.append_consultation_event(
        action_id=action.action_id, token=action.dispatch_token, fence=action.fence, event=event,
    )
    assert not fresh and duplicate.consultation == recorded.consultation
    with pytest.raises(ApplicationStateValidationError):
        service.finish(action_id=action.action_id, token=action.dispatch_token,
                       fence=action.fence, status="completed", summary="Bypass")


def test_pg_terminal_result_rejects_wrong_dispatch_and_commits_once(application_state_dsn):
    service = PlanActionDialogueService()
    action, _ = service.reserve(reservation())
    _, receipt, policy = frozen_action(service, action)
    events = consultation_events(receipt, policy)
    for event in events:
        service.append_consultation_event(action_id=action.action_id, token=action.dispatch_token,
                                          fence=action.fence, event=event)
    result = attributed_result(receipt, events)
    unrelated = result.model_copy(update={"message": "Unrelated visible claim without attribution."})
    with pytest.raises(ValueError, match="ordered attributed segments"):
        service.finish_consultation(action_id=action.action_id, token=action.dispatch_token,
                                    fence=action.fence, result=unrelated)
    for token, fence in [(uuid4(), action.fence), (action.dispatch_token, action.fence + 1)]:
        with pytest.raises(ApplicationStateConflictError):
            service.finish_consultation(action_id=action.action_id, token=token, fence=fence, result=result)
    unchanged = service.get_by_key(action.basis.world_id, action.idempotency_key)
    assert unchanged.status == "pending" and unchanged.consultation.result is None
    assert len(unchanged.consultation.execution.events) == len(events)
    service.finish_consultation(action_id=action.action_id, token=action.dispatch_token,
                                fence=action.fence, result=result)
    loaded = PlanActionDialogueService().get_by_key(action.basis.world_id, action.idempotency_key)
    assert loaded.assistant_summary == render_answer_segments(result.answer_segments)
    assert service.completed_context(action.basis)[0].assistant_summary == loaded.assistant_summary
    with pytest.raises(ApplicationStateConflictError):
        service.finish_consultation(action_id=action.action_id, token=action.dispatch_token,
                                    fence=action.fence, result=result)


def test_pg_concurrent_freeze_has_one_fresh_gate(application_state_dsn):
    service = PlanActionDialogueService()
    action, _ = service.reserve(reservation())
    receipt, policy = frozen_inputs(action)
    def freeze(_):
        return PlanActionDialogueService().freeze_consultation(
            action_id=action.action_id, token=action.dispatch_token,
            fence=action.fence, receipt=receipt, policy=policy,
        )[1]
    with ThreadPoolExecutor(max_workers=2) as pool:
        assert sum(pool.map(freeze, range(2))) == 1


def test_pg_historical_answer_hash_rejects_changed_same_turn_and_survives_reload(application_state_dsn):
    from tests.application_state.test_agent_conversation_service import _indexed_graph_completion_fixture
    from application_state.agent_conversation.types import PlanAskHistoryAttributionV1, PlanWorldGraphHistoryPinV1
    from application_state.plan_action_dialogue.graph_consultation import consultation_receipt_digest
    old, _execution, completion, _attempt, _event = _indexed_graph_completion_fixture(packet_coverage="incomplete")
    service = PlanActionDialogueService()
    request = reservation(basis=PlanActionBasis.model_validate(old.plan_basis.model_dump()))
    action, _ = service.reserve(request)
    receipt, policy = frozen_inputs(action, revision="graph-r2")
    conversation_id, turn_id = uuid4(), uuid4()
    attribution = PlanAskHistoryAttributionV1(
        source_turn_id=turn_id, source_conversation_id=conversation_id, source_sequence=1,
        surface_instance_id="plan-pane", plan_basis=old.plan_basis, playable_target=None,
        context_receipt_sha256=old.context_receipt_sha256, answer_basis=completion.answer_basis,
        answer_context_status=completion.answer_context_status, answer_segments=completion.answer_segments,
        citation_map=completion.citation_map,
    )
    assembled = receipt.assembled_input.model_copy(update={"included_history": [
        PlanWorldGraphHistoryPinV1(turn_id=turn_id, answer_sha256=historical_ask_answer_digest(attribution))
    ]})
    valid = build_consultation_receipt(
        action=action, surface_instance_id="plan-pane", graph_authority=receipt.graph_authority,
        graph_packet=receipt.graph_packet, assembled_input=assembled,
        history_conversation_id=conversation_id, history_attribution=[attribution],
    )
    altered = attribution.model_copy(update={"answer_segments": [
        attribution.answer_segments[0].model_copy(update={"text": "Unrelated answer under the original turn ID."})
    ]})
    bad = valid.model_copy(update={"history_attribution": [altered]})
    bad = bad.model_copy(update={"consultation_receipt_sha256": consultation_receipt_digest(bad)})
    with pytest.raises(ValueError, match="historical Ask"):
        service.freeze_consultation(action_id=action.action_id, token=action.dispatch_token,
                                    fence=action.fence, receipt=bad, policy=policy)
    assert service.get_by_key(action.basis.world_id, action.idempotency_key).consultation is None
    service.freeze_consultation(action_id=action.action_id, token=action.dispatch_token,
                                fence=action.fence, receipt=valid, policy=policy)
    loaded = PlanActionDialogueService().get_by_key(action.basis.world_id, action.idempotency_key)
    assert loaded.consultation.receipt.history_attribution == [attribution]
    assert loaded.consultation.receipt.assembled_input.included_history[0].answer_sha256 == historical_ask_answer_digest(attribution)


def test_pg_linked_clarification_preserves_intent_and_revalidates_current_graph(application_state_dsn):
    service = PlanActionDialogueService()
    request = reservation()
    first, _ = service.reserve(request)
    previous, _ = complete_action(service, first)
    link = PlanActionContinuation(
        continuation_of_action_id=first.action_id,
        clarification_id=previous.consultation.result.result_id,
        previous_result_sha256=consultation_result_digest(previous.consultation.result),
        previous_instruction=request.instruction,
    )
    reply, _ = service.reserve(reservation(basis=request.basis, instruction="Yes, her mother's."))
    frozen, receipt, _ = frozen_action(service, reply, revision="graph-r2", continuation=link)
    assert frozen.consultation.receipt.continuation.previous_instruction == request.instruction
    assert receipt.graph_authority.graph_revision == "graph-r2"
    assert previous.consultation.receipt.graph_authority.graph_revision == "graph-r1"
    other, _ = service.reserve(reservation(basis=request.basis, instruction="Another reply."))
    other_receipt, policy = frozen_inputs(other, continuation=link)
    with pytest.raises(ApplicationStateConflictError, match="superseded"):
        service.freeze_consultation(action_id=other.action_id, token=other.dispatch_token,
                                    fence=other.fence, receipt=other_receipt, policy=policy)


@pytest.mark.parametrize("change", ["world", "basis", "draft", "target", "predecessor", "surface"])
def test_pg_foreign_stale_or_mismatched_clarification_is_rejected(application_state_dsn, change):
    service = PlanActionDialogueService()
    request = reservation()
    first, _ = service.reserve(request)
    previous, _ = complete_action(service, first)
    link = PlanActionContinuation(
        continuation_of_action_id=first.action_id,
        clarification_id=previous.consultation.result.result_id,
        previous_result_sha256=consultation_result_digest(previous.consultation.result),
        previous_instruction=request.instruction,
    )
    next_request = reservation(basis=request.basis, instruction="A reply.")
    if change == "world":
        next_request = next_request.model_copy(update={"basis": request.basis.model_copy(update={"world_id": "other-world"})})
    elif change == "basis":
        next_request = next_request.model_copy(update={"basis": request.basis.model_copy(update={"object_revision": 5})})
    elif change == "draft":
        next_request = next_request.model_copy(update={"draft_sha256": "e" * 64})
    elif change == "target":
        next_request = next_request.model_copy(update={"selected_text_sha256": "e" * 64})
    elif change == "predecessor":
        link = link.model_copy(update={"clarification_id": uuid4()})
    reply, _ = service.reserve(next_request)
    receipt, policy = frozen_inputs(reply, continuation=link)
    if change == "surface":
        from application_state.plan_action_dialogue.graph_consultation import build_consultation_receipt
        receipt = build_consultation_receipt(
            action=reply, surface_instance_id="foreign-pane", graph_authority=receipt.graph_authority,
            graph_packet=receipt.graph_packet, assembled_input=receipt.assembled_input, continuation=link,
        )
    with pytest.raises(ApplicationStateConflictError, match="predecessor"):
        service.freeze_consultation(action_id=reply.action_id, token=reply.dispatch_token,
                                    fence=reply.fence, receipt=receipt, policy=policy)


def test_pg_concurrent_reply_freeze_has_one_successor(application_state_dsn):
    service = PlanActionDialogueService()
    request = reservation()
    first, _ = service.reserve(request)
    previous, _ = complete_action(service, first)
    link = PlanActionContinuation(
        continuation_of_action_id=first.action_id, clarification_id=previous.consultation.result.result_id,
        previous_result_sha256=consultation_result_digest(previous.consultation.result),
        previous_instruction=request.instruction,
    )
    replies = [service.reserve(reservation(basis=request.basis, instruction=f"Reply {i}."))[0] for i in range(2)]
    def attempt(reply):
        try:
            frozen_action(PlanActionDialogueService(), reply, continuation=link)
            return True
        except ApplicationStateConflictError:
            return False
    with ThreadPoolExecutor(max_workers=2) as pool:
        assert sum(pool.map(attempt, replies)) == 1


def test_pg_unknown_outcome_and_expiry_never_expose_result(application_state_dsn):
    service = PlanActionDialogueService()
    action, _ = service.reserve(reservation())
    _, receipt, policy = frozen_action(service, action)
    events = consultation_events(receipt, policy)
    for event in events[:1]:
        service.append_consultation_event(action_id=action.action_id, token=action.dispatch_token,
                                          fence=action.fence, event=event)
    unknown = ProviderOutcomeEventV1(event_id=uuid4(), sequence=1, kind="provider_outcome",
                                     provider_attempt_id=events[0].provider_attempt_id, outcome="outcome_unknown")
    service.append_consultation_event(action_id=action.action_id, token=action.dispatch_token,
                                      fence=action.fence, event=unknown)
    unavailable = PlanActionContextUnavailableResult(
        kind="context_unavailable", result_id=uuid4(),
        consultation_receipt_sha256=receipt.consultation_receipt_sha256,
        message="The consultation outcome is uncertain.", failure_code="context_unavailable",
    )
    with pytest.raises(ValueError, match="unknown provider"):
        service.finish_consultation(action_id=action.action_id, token=action.dispatch_token,
                                    fence=action.fence, result=unavailable)
    with pytest.raises(ApplicationStateValidationError, match="indeterminate"):
        service.finish(action_id=action.action_id, token=action.dispatch_token,
                       fence=action.fence, status="failed", failure_code="provider_unknown")
    with psycopg.connect(application_state_dsn) as conn:
        conn.execute("UPDATE plan_action.action SET lease_expires_at=clock_timestamp()-interval '1 second' WHERE action_id=%s", (action.action_id,))
    reloaded = service.get_by_key(action.basis.world_id, action.idempotency_key)
    assert reloaded.status == "indeterminate" and reloaded.consultation.result is None
    assert reloaded.dispatch_token is None


def test_pg_context_unavailable_is_failed_not_empty_knowledge(application_state_dsn):
    service = PlanActionDialogueService()
    action, _ = service.reserve(reservation())
    _, receipt, _ = frozen_action(service, action)
    result = PlanActionContextUnavailableResult(
        kind="context_unavailable", result_id=uuid4(),
        consultation_receipt_sha256=receipt.consultation_receipt_sha256,
        message="The source could not be read.", failure_code="required_read_unavailable",
    )
    failed = service.finish_consultation(action_id=action.action_id, token=action.dispatch_token,
                                        fence=action.fence, result=result)
    assert failed.status == "failed" and failed.assistant_summary is None
    assert service.list_status(action.basis).actions[0].consultation.result == result


def test_pg_unresolved_authority_freezes_plain_failure_without_fake_graph(application_state_dsn):
    service = PlanActionDialogueService()
    action, _ = service.reserve(reservation())
    unavailable = build_consultation_receipt(
        action=action, surface_instance_id="plan-pane", authority_failure_code="binding_unavailable"
    )
    frozen, fresh = service.freeze_consultation(
        action_id=action.action_id, token=action.dispatch_token, fence=action.fence, receipt=unavailable
    )
    assert fresh and frozen.consultation.execution is None
    receipt, policy = frozen_inputs(action)
    events = consultation_events(receipt, policy)
    with pytest.raises(ApplicationStateValidationError):
        service.append_consultation_event(action_id=action.action_id, token=action.dispatch_token,
                                          fence=action.fence, event=events[0])
    with pytest.raises(ApplicationStateValidationError):
        service.finish_consultation(action_id=action.action_id, token=action.dispatch_token,
                                    fence=action.fence, result=attributed_result(receipt, events, proposal=True))
    with pytest.raises(ApplicationStateConflictError):
        service.freeze_consultation(action_id=action.action_id, token=action.dispatch_token,
                                    fence=action.fence, receipt=receipt, policy=policy)
    result = PlanActionContextUnavailableResult(
        kind="context_unavailable", result_id=uuid4(),
        consultation_receipt_sha256=unavailable.consultation_receipt_sha256,
        message="World knowledge authority could not be resolved.", failure_code="binding_unavailable",
    )
    service.finish_consultation(action_id=action.action_id, token=action.dispatch_token,
                                fence=action.fence, result=result)
    loaded = PlanActionDialogueService().get_by_key(action.basis.world_id, action.idempotency_key)
    assert loaded.status == "failed" and loaded.consultation.result == result
    assert loaded.consultation.receipt.graph_authority is None
    assert loaded.consultation.receipt.graph_packet is None
    assert loaded.consultation.receipt.assembled_input is None
    assert loaded.consultation.execution is None


def test_pg_malformed_row_fails_closed_and_downgrade_preserves_receipts(application_state_dsn):
    from alembic import command
    from application_state.cli import alembic_config
    service = PlanActionDialogueService()
    action, _ = service.reserve(reservation())
    frozen, _, _ = frozen_action(service, action)
    with pytest.raises(RuntimeError, match="refusing to downgrade"):
        command.downgrade(alembic_config(), "20261008_0019")
    with psycopg.connect(application_state_dsn) as conn:
        conn.execute("UPDATE plan_action.action SET consultation=jsonb_set(consultation,'{receipt,action_input_sha256}',to_jsonb(%s::text)) WHERE action_id=%s", ("f" * 64, action.action_id))
    with pytest.raises(ValidationError):
        service.get_by_key(action.basis.world_id, action.idempotency_key)
    assert frozen.consultation.result is None


def test_current_related_recap_consultation_preserves_context_boundary():
    from application_state.agent_conversation.types import (
        RelatedRecapContextAdmissionV2, RelatedRecapProvenanceBindingV2,
        RelatedRecapContextAuthorizationEventV2, ValidatedRelatedRecapContextEventV2,
        RelatedRecapContextProviderInclusionEventV2, _canonical_sha256,
        related_recap_provenance_result_digest, related_recap_context_inclusion_digest,
    )
    from tests.application_state.test_agent_conversation_service import _related_recap_admission_fixture
    receipt, policy = frozen_inputs(model_action())
    events = consultation_events(receipt, policy)[:3]
    binding = RelatedRecapProvenanceBindingV2(evidence_ref_id="evidence:authored",source_artifact_id="artifact:authored",source_revision_id="source-r1")
    data = _related_recap_admission_fixture().model_dump(mode="json",by_alias=True) | {
        "managed_world_id":receipt.basis.world_id,"native_world_id":"native-synthetic","binding_version":1,
        "graph_revision":"graph-r1","target_id":"assertion:observatory","provenance_bindings":[binding.model_dump(mode="json")],
        "descriptor_world_id":"native-synthetic","descriptor_graph_revision_id":"graph-r1",
        "descriptor_source_artifact_id":"artifact:authored","descriptor_source_revision_id":"source-r1",
        "provenance_result_sha256":related_recap_provenance_result_digest(managed_world_id=receipt.basis.world_id,
            native_world_id="native-synthetic",binding_version=1,graph_revision="graph-r1",target_kind="assertion",
            target_id="assertion:observatory",provenance_bindings=[binding]),
    }
    admission=RelatedRecapContextAdmissionV2.model_validate(data)
    authorization=RelatedRecapContextAuthorizationEventV2(event_id=uuid4(),sequence=3,kind="related_recap_context_authorized_v2",
        read_call_id=uuid4(),context_receipt_sha256=receipt.consultation_receipt_sha256,
        execution_policy_sha256=graph_execution_policy_digest_v2(receipt.consultation_receipt_sha256,policy),admission=admission,max_chars=100)
    read=ValidatedRelatedRecapContextEventV2(event_id=uuid4(),sequence=4,kind="validated_related_recap_context_v2",
        read_call_id=authorization.read_call_id,authorization_event_id=authorization.event_id,
        admission_sha256=_canonical_sha256(admission.model_dump(mode="json",by_alias=True)),outcome="enough",
        range_semantics_version="utf8-character-offset-in-markdown-session-recap-v2",source_bytes_sha256=admission.descriptor_content_sha256,
        section_sha256="a"*64,page_content_sha256="b"*64,selected_form="legacy_h2",session_heading_line=1,
        recap_marker_line=4,heading_line=1,line_start=5,line_end=6,offset_chars=0,returned_chars=50,truncated=False)
    final=consultation_events(receipt,policy)[6].model_copy(update={"included_graph_event_ids":[],"included_source_read_event_ids":[]})
    inclusion=RelatedRecapContextProviderInclusionEventV2(event_id=uuid4(),sequence=5,kind="related_recap_context_provider_inclusion_v2",
        provider_attempt_id=final.provider_attempt_id,envelope_sha256=final.envelope_sha256,
        included_context_event_ids=[read.event_id],included_context_sha256=related_recap_context_inclusion_digest([read]),included_chars=50)
    execution=PlanWorldGraphExecutionV2(context_receipt_sha256=receipt.consultation_receipt_sha256,
        execution_policy_sha256=authorization.execution_policy_sha256,policy=policy,events=[*events,authorization,read,inclusion,final])
    consultation=PlanActionConsultation(receipt=receipt,execution=execution,result=None)
    assert consultation.execution.events[-2].kind=="related_recap_context_provider_inclusion_v2"
    # A current related event ID never becomes literal claim support.
    from application_state.agent_conversation.types import validate_graph_execution_source_citations
    citation=PlanWorldGraphCitationV2(claim_id="claim:owner",target_kind="assertion",target_id="assertion:observatory",
        graph_revision="graph-r1",evidence_ref_ids=["evidence:authored"],source_opened=True,source_read_ids=[str(read.event_id)])
    with pytest.raises(ValueError):
        validate_graph_execution_source_citations(PlanWorldGraphCitationMapV2(context_receipt_sha256=receipt.consultation_receipt_sha256,entries=[citation]),
            execution,final.provider_attempt_id)
