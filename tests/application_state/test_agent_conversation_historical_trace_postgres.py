from datetime import UTC, datetime
import hashlib
from uuid import uuid4

import psycopg
import pytest

from application_state.agent_conversation import AgentConversationService
from application_state.agent_conversation.context_trace import (
    TraceContextMaterial, TraceContextSnapshot, TraceHistoricalSourceReferenceV1,
    TraceRoute, TraceSourcePassage,
)
from application_state.agent_conversation.types import (
    ConversationCommand, GraphExecutionAccountingV1, GraphExecutionPolicyV2,
    GraphSourceReadScopeV2, GraphSourceScopeAnchorV2, HistoricalReference,
    PlanContextPolicyV1, PlanPlayableTargetReceiptV1, PlanWorldGraphExecutionV2,
    SourceReadAnchorReceiptV2, SourceReadAuthorizationEventV2, SubmittedGraphRequestIntentV1,
    SubmittedPlanPlayableTargetV1, SubmittedPrimaryWorkIntentV1, SubmittedTurnIntentV1,
    SubmittedTurnIntentV2, TurnFailure, TurnProvenance, TurnSubmission,
    ValidatedSourceReadEventV2, encode_plan_playable_target_reference,
    graph_execution_policy_digest_v2,
)
from application_state.errors import ApplicationStateConflictError
from tests.application_state.test_agent_conversation_postgres import _graph_receipt, _new


def _plain_turn(service, world, conversation):
    intent = SubmittedTurnIntentV1(world_id=world, client_thread_id="historical-trace",
        message="Observe restored context.", surface_id="index", surface_instance_id="index-home",
        client_work_state="none", primary_work=None,
        graph_request=SubmittedGraphRequestIntentV1(mode="none"), graph_selection=None)
    accepted = service.accept_turn(TurnSubmission(world_id=world, conversation_id=conversation.conversation_id,
        expected_conversation_revision=service.get_conversation(world, conversation.conversation_id).revision,
        idempotency_key=uuid4(), user_text=intent.message, submitted_intent_v1=intent,
        provenance=TurnProvenance(world_id=world, surface_resolution="resolved", surface_id="index",
            primary_work=HistoricalReference(resolution="absent"), selected_object=HistoricalReference(resolution="absent"))))
    turn = service.claim_turn(world, conversation.conversation_id, accepted.turn_id,
        expected_revision=accepted.revision, lease_seconds=60).turn
    identity = dict(world_id=world, conversation_id=conversation.conversation_id, turn_id=turn.turn_id,
                    expected_revision=turn.revision, attempt=turn.attempt, trace_id=uuid4())
    service.start_context_trace(**identity, started_at=datetime.now(UTC))
    return turn, identity


@pytest.fixture
def historical_pair(application_state_dsn):
    service = AgentConversationService()
    world = "historical-source-" + uuid4().hex
    conversation = _new(service, world)
    revision = uuid4()
    target = PlanPlayableTargetReceiptV1(schema="dmb_plan_playable_target_receipt_v1",
        kind="beat", id="beat:a", marker_grammar_version="v2")
    receipt = _graph_receipt(world, revision, target, candidate_evidence_ref_ids=["evidence-1"])
    scope = GraphSourceReadScopeV2(retrieval_session_id="synthetic-history", world_id=world,
        graph_revision="graph-rev-11", admitted_anchors=[GraphSourceScopeAnchorV2(anchor_id="anchor-1",
        evidence_ref_id="evidence-1", source_artifact_id="artifact-1", source_revision_id="source-revision-1")])
    policy = GraphExecutionPolicyV2(policy_version="test-v2", allowed_graph_operations=["search_assertions"],
        max_provider_attempts=2, max_graph_operations=0, max_results_per_operation=0,
        max_total_provider_input_tokens=100, max_total_provider_output_tokens=40,
        provider_input_accounting=GraphExecutionAccountingV1(kind="exact_token_count", estimator="synthetic-tokenizer"),
        source_opened=False, source_read_scope=scope, max_source_read_calls=1, max_source_read_anchors=1,
        max_source_read_chars=12000, max_chars_per_source_read=12000)
    execution = PlanWorldGraphExecutionV2(schema="dmb_agent_plan_world_graph_execution_v2",
        context_receipt_sha256=receipt.context_receipt_sha256,
        execution_policy_sha256=graph_execution_policy_digest_v2(receipt.context_receipt_sha256, policy),
        policy=policy, events=[])
    intent = SubmittedTurnIntentV2(world_id=world, client_thread_id="historical-source", message="Original read.",
        surface_id="plan", surface_instance_id="plan-pane-source-read", client_work_state="saved_clean",
        primary_work=SubmittedPrimaryWorkIntentV1(kind="plan", object_id="graph-receipt-plan", expected_revision=3,
            expected_revision_n=2, expected_content_sha256="a" * 64),
        plan_context_policy=PlanContextPolicyV1(policy="auto_plan_world"),
        playable_target=SubmittedPlanPlayableTargetV1(schema="dmb_plan_playable_target_v1", kind="beat", id="beat:a"),
        graph_request=SubmittedGraphRequestIntentV1(mode="none"), graph_selection=None)
    accepted = service.accept_turn(TurnSubmission(world_id=world, conversation_id=conversation.conversation_id,
        idempotency_key=uuid4(), expected_conversation_revision=1, user_text=intent.message, submitted_intent_v2=intent,
        graph_context_receipt=receipt, graph_context_execution=execution,
        provenance=TurnProvenance(world_id=world, surface_resolution="resolved", surface_id="plan",
            surface_instance_id="plan-pane-source-read", primary_work=HistoricalReference(resolution="resolved", kind="plan",
            object_id="graph-receipt-plan", content_sha256="a" * 64, object_revision=3, work_revision_id=revision, revision_n=2),
            supporting_work=[encode_plan_playable_target_reference(target)], selected_object=HistoricalReference(resolution="absent"))))
    original = service.claim_turn(world, conversation.conversation_id, accepted.turn_id,
        expected_revision=accepted.revision, lease_seconds=60).turn
    trace_id, read_call_id, event_id = uuid4(), uuid4(), uuid4()
    service.start_context_trace(world_id=world, conversation_id=conversation.conversation_id, turn_id=original.turn_id,
        expected_revision=original.revision, attempt=original.attempt, trace_id=trace_id, started_at=datetime.now(UTC))
    authorization = SourceReadAuthorizationEventV2(event_id=uuid4(), sequence=0, kind="source_read_authorized_v2",
        read_call_id=read_call_id, context_receipt_sha256=receipt.context_receipt_sha256,
        execution_policy_sha256=execution.execution_policy_sha256, retrieval_session_id=scope.retrieval_session_id,
        world_id=world, graph_revision=scope.graph_revision, anchors=scope.admitted_anchors, max_chars=12000)
    authorized, _ = service.authorize_source_read(world, conversation.conversation_id, original.turn_id,
        expected_revision=original.revision, expected_attempt=original.attempt, authorization=authorization)
    text = "Exact persisted historical source — restored without another read."
    digest = hashlib.sha256(text.encode()).hexdigest()
    source = SourceReadAnchorReceiptV2(source_read_id="source-read:original", anchor_id="anchor-1",
        evidence_ref_id="evidence-1", source_artifact_id="artifact-1", source_revision_id="source-revision-1",
        outcome="enough", content_sha256=digest, returned_chars=len(text), truncated=False,
        evidence_sufficiency_status="sufficient")
    event = ValidatedSourceReadEventV2(event_id=event_id, sequence=1, kind="validated_source_read_v2",
        read_call_id=read_call_id, receipts=[source])
    passage = TraceSourcePassage(sequence=0, elapsed_ms=1, source_read_event_id=event_id, read_call_id=read_call_id,
        world_id=world, graph_revision=scope.graph_revision, source_read_id=source.source_read_id,
        anchor_id=source.anchor_id, evidence_ref_id=source.evidence_ref_id, source_artifact_id=source.source_artifact_id,
        source_revision_id=source.source_revision_id, outcome="enough", returned_chars=len(text), content_sha256=digest, text=text)
    recorded, _ = service.record_validated_source_read(world, conversation.conversation_id, original.turn_id,
        expected_revision=authorized.revision, expected_attempt=original.attempt, receipt=event, source_passages=[passage])
    service.fail_turn(TurnFailure(world_id=world, conversation_id=conversation.conversation_id, turn_id=original.turn_id,
        expected_revision=recorded.revision, failure_code="synthetic_prior_terminal"), interrupted=True)
    current, identity = _plain_turn(service, world, conversation)
    reference = TraceHistoricalSourceReferenceV1(world_id=world, conversation_id=conversation.conversation_id,
        turn_id=original.turn_id, attempt=original.attempt, trace_id=trace_id, source_read_event_id=event_id,
        source_read_id=source.source_read_id, content_sha256=digest)
    return service, conversation, original, current, identity, reference, passage


def _snapshot(reference, route=None):
    return TraceContextSnapshot(sequence=0, elapsed_ms=2, stage="before", materials=[
        TraceContextMaterial(item_id="restored-source", state="model_context", role="source",
                             historical_source_reads=[reference], route=route)])


def test_historical_exact_reference_persists_without_text_or_new_authority(historical_pair):
    service, conversation, original, current, identity, ref, passage = historical_pair
    original_before = service.list_context_trace_attempts(world_id=ref.world_id, turn_id=original.turn_id)
    snapshot = _snapshot(ref, TraceRoute(route_id="historical-route", world_id=ref.world_id,
        graph_revision=passage.graph_revision, anchor_id=passage.anchor_id, content_sha256=ref.content_sha256))
    saved = service.append_context_trace(**identity, observation=snapshot)
    assert saved.capture_status == "recording"
    assert service.append_context_trace(**identity, observation=snapshot) == saved
    fresh = AgentConversationService()
    assert fresh.list_context_trace_attempts(world_id=ref.world_id, turn_id=current.turn_id)[0] == saved
    assert fresh.list_context_trace_attempts(world_id=ref.world_id, turn_id=original.turn_id) == original_before
    persisted = saved.model_dump(mode="json", by_alias=True)
    assert passage.text not in str(persisted)
    assert not any(item.kind == "source_passage" for item in saved.observations)
    reloaded = fresh.list_turns(ref.world_id, conversation.conversation_id)[-1]
    assert reloaded == current
    assert reloaded.graph_context_execution is None
    final = fresh.fail_turn(TurnFailure(world_id=ref.world_id, conversation_id=conversation.conversation_id,
        turn_id=current.turn_id, expected_revision=current.revision, failure_code="synthetic_final"))
    assert final.status == "failed"
    assert fresh.list_context_trace_attempts(world_id=ref.world_id, turn_id=current.turn_id)[0].capture_status == "complete"


@pytest.mark.parametrize("field", ["world_id", "conversation_id", "turn_id", "attempt", "trace_id",
                                    "source_read_event_id", "source_read_id", "content_sha256", "same_turn", "future_turn", "route"])
def test_unverified_historical_reference_marks_incomplete_without_snapshot_or_core_change(historical_pair, field, application_state_dsn):
    service, conversation, original, current, identity, ref, passage = historical_pair
    payload = ref.model_dump(mode="python")
    route = None
    if field == "same_turn":
        payload.update(turn_id=current.turn_id, attempt=current.attempt, trace_id=identity["trace_id"])
    elif field == "future_turn":
        # Keep the exact genuine passage identity valid; change only synthetic
        # turn ordering so this rejects independently of missing passage checks.
        with psycopg.connect(application_state_dsn) as conn:
            conn.execute("UPDATE agent.turn SET sequence=%s WHERE turn_id=%s",
                         (current.sequence + 1, original.turn_id))
    elif field == "route":
        route = TraceRoute(route_id="wrong-route", world_id=ref.world_id, graph_revision="different-revision")
    else:
        payload[field] = ("other-world" if field == "world_id" else
            "other-read" if field == "source_read_id" else "b" * 64 if field == "content_sha256" else
            ref.attempt + 1 if field == "attempt" else uuid4())
    saved = service.append_context_trace(**identity, observation=_snapshot(TraceHistoricalSourceReferenceV1.model_validate(payload), route))
    assert saved.capture_status == "incomplete"
    assert saved.capture_failure_code == "historical_source_unavailable"
    assert saved.observations == []
    assert next(turn for turn in service.list_turns(ref.world_id, conversation.conversation_id)
                if turn.turn_id == current.turn_id) == current
    final = service.fail_turn(TurnFailure(world_id=ref.world_id, conversation_id=conversation.conversation_id,
        turn_id=current.turn_id, expected_revision=current.revision, failure_code="synthetic_final"))
    assert final.status == "failed"
    assert service.list_context_trace_attempts(world_id=ref.world_id, turn_id=current.turn_id)[0].capture_status == "incomplete"


def test_actual_other_conversation_passage_is_unavailable(historical_pair):
    service, conversation, _, _, _, ref, _ = historical_pair
    pointer = service.get_world_pointer(ref.world_id)
    other = service.new_conversation(ConversationCommand(world_id=ref.world_id, command_id=uuid4(),
        expected_pointer_revision=pointer.revision, expected_active_conversation_id=conversation.conversation_id))
    current, identity = _plain_turn(service, ref.world_id, other)
    # A forged consumer-conversation pin cannot make a real earlier passage cross conversations.
    forged = ref.model_copy(update={"conversation_id": other.conversation_id})
    saved = service.append_context_trace(**identity, observation=_snapshot(forged))
    assert saved.capture_status == "incomplete"
    assert saved.observations == []
    assert service.list_turns(ref.world_id, other.conversation_id)[0] == current


def test_current_attempt_fence_precedes_historical_lookup(historical_pair, application_state_dsn):
    service, _, _, current, identity, ref, _ = historical_pair
    with pytest.raises(ApplicationStateConflictError, match="stale or expired claim"):
        service.append_context_trace(**{**identity, "attempt": current.attempt + 1}, observation=_snapshot(ref))
    with psycopg.connect(application_state_dsn) as conn:
        conn.execute("UPDATE agent.turn SET claim_expires_at=clock_timestamp()-interval '1 second' WHERE turn_id=%s", (current.turn_id,))
    with pytest.raises(ApplicationStateConflictError, match="stale or expired claim"):
        service.append_context_trace(**identity, observation=_snapshot(ref))
    assert service.list_context_trace_attempts(world_id=ref.world_id, turn_id=current.turn_id)[0].capture_status == "recording"
