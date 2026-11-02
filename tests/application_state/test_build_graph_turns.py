"""Build's genuine source basis through the real governed APP ledger."""
from datetime import UTC, datetime
import hashlib
from uuid import uuid4

import psycopg
from psycopg.types.json import Jsonb
import pytest
from pydantic import ValidationError

from application_state.agent_conversation import AgentConversationService
from application_state.agent_conversation import types as t
from application_state.agent_conversation.context_trace import TraceContextDecision, TraceSourcePassage
from application_state.errors import ApplicationStateConflictError
from tests.application_state.test_agent_conversation_postgres import (
    _graph_receipt, _new, _provider_authorization_event, _accepted_execution_turn,
)
from tests.application_state.test_agent_conversation_service import _v2_graph_execution_fixture


def _rehash(payload):
    payload = dict(payload)
    payload.pop("context_receipt_sha256", None)
    payload["context_receipt_sha256"] = t._canonical_sha256(payload)
    return payload


def _submission(conversation_id=None):
    world = "build-ledger-world"
    old = _graph_receipt(world, uuid4(), candidate_evidence_ref_ids=["evidence-1"])
    payload = old.model_dump(mode="json", by_alias=True)
    for field in ("plan_basis", "plan_context_policy", "playable_target"):
        payload.pop(field)
    payload.update(schema="dmb_build_graph_context_receipt_v1", source_basis={
        "world_id": world, "document_id": "mirathorn-fixture", "registry_revision": 2,
        "content_sha256": hashlib.sha256(b"Mirathorn source.").hexdigest(), "visibility": "internal",
    })
    receipt = t.BuildGraphContextReceiptV1.model_validate(_rehash(payload))
    original, _, _ = _v2_graph_execution_fixture()
    policy_data = original.policy.model_dump(mode="json", by_alias=True)
    policy_data["source_read_scope"].update(world_id=world, graph_revision="graph-rev-11")
    policy = t.GraphExecutionPolicyV2.model_validate(policy_data)
    execution = t.PlanWorldGraphExecutionV2(
        context_receipt_sha256=receipt.context_receipt_sha256,
        execution_policy_sha256=t.graph_execution_policy_digest_v2(receipt.context_receipt_sha256, policy),
        policy=policy, events=[],
    )
    digest = receipt.source_basis.content_sha256
    intent = t.BuildGraphIntentV1(
        world_id=world, client_thread_id="build-thread", message="What can I learn from this source?",
        surface_id="build", surface_instance_id="build-pane", client_work_state="saved_clean",
        primary_work={"kind": "build", "object_id": "mirathorn-fixture", "expected_revision": 2,
                      "expected_content_sha256": digest},
        graph_request={"mode": "world", "world_id": world, "focus": {"kind": "none"}},
        graph_selection=None,
    )
    provenance = t.TurnProvenance(
        world_id=world, surface_resolution="resolved", surface_id="build", surface_instance_id="build-pane",
        primary_work={"resolution": "resolved", "kind": "build", "object_id": "mirathorn-fixture",
                      "revision": "2", "content_sha256": digest},
        supporting_work=[
            {"resolution": "resolved", "kind": "dmb_build_source_visibility_v1", "object_id": "internal", "revision": "1"},
            {"resolution": "resolved", "kind": "dmb_build_graph_binding_v1", "object_id": "native-world-17", "revision": "4"},
            {"resolution": "resolved", "kind": "world_graph_revision", "object_id": "native-world-17", "revision": "graph-rev-11"},
        ], selected_object={"resolution": "absent"},
    )
    return t.TurnSubmission(world_id=world, conversation_id=conversation_id or uuid4(),
        idempotency_key=uuid4(), expected_conversation_revision=1, user_text=intent.message,
        provenance=provenance, submitted_intent_v2=intent,
        graph_context_receipt=receipt, graph_context_execution=execution)


def _accept_claim(service):
    world = "build-ledger-world"
    conversation = _new(service, world)
    submission = _submission(conversation.conversation_id)
    accepted = service.accept_turn(submission)
    turn = service.claim_turn(world, conversation.conversation_id, accepted.turn_id,
        expected_revision=accepted.revision, lease_seconds=60).turn
    return submission, turn


def _append_provider(service, turn, graph_events=(), source_events=(), final_outcome="response_received"):
    attempt_id = uuid4()
    event = _provider_authorization_event(attempt_id=attempt_id, sequence=len(turn.graph_context_execution.events),
        assertions=["assertion-1"] if graph_events else [], evidence_refs=["evidence-1"] if graph_events else [],
        graph_event_ids=[e.event_id for e in graph_events])
    event = t.ProviderAttemptAuthorizedEventV2.model_validate(event.model_dump(mode="python") | {
        "kind": "provider_attempt_authorized_v2", "included_source_read_event_ids": [e.event_id for e in source_events],
    })
    turn, fresh = service.authorize_provider_attempt_v2(turn.world_id, turn.conversation_id, turn.turn_id,
        expected_revision=turn.revision, expected_attempt=turn.attempt, provider_attempt_event=event)
    assert fresh
    for state in ("sdk_entered", final_outcome):
        turn, fresh = service.record_provider_outcome(turn.world_id, turn.conversation_id, turn.turn_id,
            expected_revision=turn.revision, expected_attempt=turn.attempt,
            outcome=t.ProviderOutcomeEventV1(event_id=uuid4(), sequence=len(turn.graph_context_execution.events),
                kind="provider_outcome", provider_attempt_id=attempt_id, outcome=state))
        assert fresh
    return turn, attempt_id


def _completion(submission):
    return t.BuildGraphCompletionV1(
        context_receipt_sha256=submission.graph_context_receipt.context_receipt_sha256,
        answer_basis="saved_source", answer_context_status="source_only_insufficient_evidence",
        answer_segments=[{"kind": "saved_source_claim", "text": "Mirathorn source.",
                          "content_sha256": submission.graph_context_receipt.source_basis.content_sha256}],
        citation_map=None,
    )


def test_real_build_ledger_completion_reopen_and_replay(application_state_dsn):
    service = AgentConversationService()
    submission, turn = _accept_claim(service)
    turn, provider_id = _append_provider(service, turn)
    completion = _completion(submission)
    wrong = completion.model_dump(mode="json", by_alias=True)
    wrong["answer_segments"][0]["content_sha256"] = "f" * 64
    with pytest.raises(ValueError, match="frozen source digest"):
        t.validate_execution_completion(t.BuildGraphCompletionV1.model_validate(wrong),
            submission.graph_context_receipt, turn.graph_context_execution, provider_id, {})
    result = t.TurnResult(world_id=turn.world_id, conversation_id=turn.conversation_id,
        turn_id=turn.turn_id, expected_revision=turn.revision, assistant_text="Mirathorn source.",
        completion=completion, producing_provider_attempt_id=provider_id, claim_graph_event_ids={})
    completed = service.complete_turn(result)
    fresh = AgentConversationService()
    assert fresh.list_turns(turn.world_id, turn.conversation_id) == [completed]
    assert fresh.complete_turn(result) == completed
    assert fresh.accept_turn(submission) == completed
    assert fresh.reconcile_turn(world_id=turn.world_id, idempotency_key=submission.idempotency_key,
        submitted_intent=submission.submitted_intent_v2) == completed
    changed = submission.submitted_intent_v2.model_copy(update={"message": "different"})
    with pytest.raises(ApplicationStateConflictError):
        fresh.reconcile_turn(world_id=turn.world_id, idempotency_key=submission.idempotency_key,
            submitted_intent=changed)


def test_build_timeout_keeps_provider_lifecycle_and_protected_trace(application_state_dsn):
    service = AgentConversationService()
    _, turn = _accept_claim(service)
    trace_id = uuid4()
    service.start_context_trace(world_id=turn.world_id, conversation_id=turn.conversation_id,
        turn_id=turn.turn_id, expected_revision=turn.revision, attempt=turn.attempt,
        trace_id=trace_id, started_at=datetime.now(UTC))
    service.append_context_trace(world_id=turn.world_id, conversation_id=turn.conversation_id,
        turn_id=turn.turn_id, expected_revision=turn.revision, attempt=turn.attempt, trace_id=trace_id,
        observation=TraceContextDecision(sequence=0, elapsed_ms=1, kind="context_decision", action="retained",
            item_ids=["saved-source"], reason_code="question_relevance", policy_version="test-v1"))
    turn, _ = _append_provider(service, turn, final_outcome="outcome_unknown")
    failed = service.fail_turn(t.TurnFailure(world_id=turn.world_id, conversation_id=turn.conversation_id,
        turn_id=turn.turn_id, expected_revision=turn.revision, failure_code="hermes_worker_timeout"))
    fresh = AgentConversationService()
    assert fresh.list_turns(turn.world_id, turn.conversation_id)[0] == failed
    assert len(failed.graph_context_execution.events) == 3
    assert failed.graph_context_execution.events[-1].outcome == "outcome_unknown"
    with pytest.raises(ApplicationStateConflictError, match="cannot be reclaimed"):
        fresh.claim_turn(turn.world_id, turn.conversation_id, turn.turn_id, expected_revision=failed.revision)
    traces = fresh.list_context_trace_attempts(world_id=turn.world_id, turn_id=turn.turn_id)
    assert len(traces) == 1 and len(traces[0].observations) == 1


def test_build_graph_answer_requires_brokered_evidence_and_opened_passage(application_state_dsn):
    service = AgentConversationService()
    submission, turn = _accept_claim(service)
    service.start_context_trace(world_id=turn.world_id, conversation_id=turn.conversation_id,
        turn_id=turn.turn_id, expected_revision=turn.revision, attempt=turn.attempt,
        trace_id=uuid4(), started_at=datetime.now(UTC))

    def append(method, **kwargs):
        nonlocal turn
        turn, inserted = getattr(service, method)(turn.world_id, turn.conversation_id, turn.turn_id,
            expected_revision=turn.revision, expected_attempt=turn.attempt, **kwargs)
        assert inserted

    graph_event = t.ValidatedGraphOperationEventV1(event_id=uuid4(), sequence=0,
        kind="validated_graph_operation", operation_id=uuid4(), operation="search_assertions",
        request_arguments_sha256="a" * 64, graph_revision="graph-rev-11", result_packet_sha256="b" * 64,
        assertion_ids=["assertion-1"], relationship_ids=[], evidence_ref_ids=["evidence-1"],
        evidence_sufficiency_status="sufficient", coverage_status="complete", truncated=False, source_opened=False)
    append("append_validated_graph_operation", operation_event=graph_event)
    scope = turn.graph_context_execution.policy.source_read_scope
    call_id = uuid4()
    authorization = t.SourceReadAuthorizationEventV2(event_id=uuid4(), sequence=1,
        kind="source_read_authorized_v2", read_call_id=call_id,
        context_receipt_sha256=submission.graph_context_receipt.context_receipt_sha256,
        execution_policy_sha256=turn.graph_context_execution.execution_policy_sha256,
        retrieval_session_id=scope.retrieval_session_id, world_id=turn.world_id, campaign_id=None,
        graph_revision="graph-rev-11", anchors=scope.admitted_anchors, max_chars=12000)
    append("authorize_source_read", authorization=authorization)
    text = "Float Goats carry goods across lakes and rivers."
    digest = hashlib.sha256(text.encode()).hexdigest()
    read = t.SourceReadAnchorReceiptV2(source_read_id="source-read:goats", anchor_id="anchor-1",
        evidence_ref_id="evidence-1", source_artifact_id="artifact-1", source_revision_id="source-revision-1",
        outcome="enough", content_sha256=digest, line_start=1, line_end=1,
        returned_chars=len(text), truncated=False, evidence_sufficiency_status="sufficient")
    read_event = t.ValidatedSourceReadEventV2(event_id=uuid4(), sequence=2,
        kind="validated_source_read_v2", read_call_id=call_id, receipts=[read])
    passage = TraceSourcePassage(sequence=0, elapsed_ms=1, source_read_event_id=read_event.event_id,
        read_call_id=call_id, world_id=turn.world_id, graph_revision="graph-rev-11",
        source_read_id=read.source_read_id, anchor_id=read.anchor_id, evidence_ref_id=read.evidence_ref_id,
        source_artifact_id=read.source_artifact_id, source_revision_id=read.source_revision_id,
        line_start=1, line_end=1, outcome="enough", returned_chars=len(text), content_sha256=digest, text=text)
    append("record_validated_source_read", receipt=read_event, source_passages=[passage])
    turn, provider_id = _append_provider(service, turn, [graph_event], [read_event])
    receipt_digest = submission.graph_context_receipt.context_receipt_sha256
    claim = dict(kind="graph_claim", claim_id="goats", text=text, target_kind="assertion",
        target_id="assertion-1", graph_revision="graph-rev-11", evidence_ref_ids=["evidence-1"])
    completion = t.BuildGraphCompletionV1(context_receipt_sha256=receipt_digest,
        answer_basis="saved_source_plus_world_graph", answer_context_status="graph_grounded",
        answer_segments=[claim], citation_map={"context_receipt_sha256": receipt_digest,
            "entries": [{k: v for k, v in claim.items() if k not in {"kind", "text"}} | {
                "source_read_ids": [read.source_read_id], "source_opened": True}]})
    forged = completion.model_dump(mode="json", by_alias=True)
    forged["citation_map"]["entries"][0]["source_read_ids"] = ["source-read:invented"]
    with pytest.raises(ValueError):
        t.validate_execution_completion(t.BuildGraphCompletionV1.model_validate(forged),
            submission.graph_context_receipt, turn.graph_context_execution, provider_id,
            {"goats": [graph_event.event_id]})
    forged = completion.model_dump(mode="json", by_alias=True)
    forged["answer_segments"][0]["target_id"] = "assertion-not-admitted"
    forged["citation_map"]["entries"][0]["target_id"] = "assertion-not-admitted"
    with pytest.raises(ValueError):
        t.validate_execution_completion(t.BuildGraphCompletionV1.model_validate(forged),
            submission.graph_context_receipt, turn.graph_context_execution, provider_id,
            {"goats": [graph_event.event_id]})
    completed = service.complete_turn(t.TurnResult(world_id=turn.world_id, conversation_id=turn.conversation_id,
        turn_id=turn.turn_id, expected_revision=turn.revision, assistant_text=text, completion=completion,
        producing_provider_attempt_id=provider_id, claim_graph_event_ids={"goats": [graph_event.event_id]}))
    fresh = AgentConversationService()
    assert fresh.list_turns(turn.world_id, turn.conversation_id) == [completed]
    traces = fresh.list_context_trace_attempts(world_id=turn.world_id, turn_id=turn.turn_id)
    assert traces[0].observations[0].text == text
    assert completed.completion.citation_map.entries[0].source_opened


@pytest.mark.parametrize("field,value", [
    ("surface_id", "plan"), ("world_id", "other-world"),
    ("primary_work", {"kind": "plan", "object_id": "fake-plan", "expected_revision": 2,
                      "expected_revision_n": 2, "expected_content_sha256": "a" * 64}),
])
def test_build_intent_does_not_impersonate_plan_or_foreign_world(field, value):
    data = _submission().submitted_intent_v2.model_dump(mode="json", by_alias=True)
    data[field] = value
    with pytest.raises(ValidationError):
        t.BuildGraphIntentV1.model_validate(data)


@pytest.mark.parametrize("field,value", [("document_id", "foreign"), ("registry_revision", 3),
    ("content_sha256", "f" * 64), ("visibility", "player_safe")])
def test_build_frozen_source_must_match_intent_and_provenance(field, value):
    data = _submission().model_dump(mode="json", by_alias=True)
    data["graph_context_receipt"]["source_basis"][field] = value
    data["graph_context_receipt"] = _rehash(data["graph_context_receipt"])
    data["graph_context_execution"]["context_receipt_sha256"] = data["graph_context_receipt"]["context_receipt_sha256"]
    policy = t.GraphExecutionPolicyV2.model_validate(data["graph_context_execution"]["policy"])
    data["graph_context_execution"]["execution_policy_sha256"] = t.graph_execution_policy_digest_v2(
        data["graph_context_receipt"]["context_receipt_sha256"], policy)
    with pytest.raises(ValidationError):
        t.TurnSubmission.model_validate(data)


def test_build_source_claim_cannot_take_graph_authority_or_wrong_digest():
    submission = _submission()
    completion = _completion(submission)
    with pytest.raises(ValidationError):
        t.BuildGraphCompletionV1.model_validate(completion.model_dump(mode="json", by_alias=True) | {
            "answer_basis": "saved_source_plus_world_graph", "answer_context_status": "graph_grounded"})
    with pytest.raises(ValidationError):
        t.BuildGraphCompletionV1.model_validate(completion.model_dump(mode="json", by_alias=True) | {
            "answer_segments": [{"kind": "plan_claim", "text": "fake", "plan_content_sha256": "a" * 64}]})
    plan_receipt = _graph_receipt("build-ledger-world", uuid4())
    with pytest.raises(ValueError, match="Plan contract"):
        t.validate_completion_against_receipt(completion, plan_receipt)
    with pytest.raises(ValueError, match="same surface contract"):
        t.validate_execution_completion(completion, plan_receipt,
            submission.graph_context_execution, uuid4(), {})


@pytest.mark.parametrize("field,value", [("native_world_id", "foreign-native"),
    ("binding_version", 5), ("graph_revision", "foreign-revision")])
def test_build_native_binding_cannot_replace_frozen_authority(field, value):
    data = _submission().model_dump(mode="json", by_alias=True)
    data["graph_context_receipt"]["graph_authority"][field] = value
    data["graph_context_receipt"] = _rehash(data["graph_context_receipt"])
    data["graph_context_execution"]["context_receipt_sha256"] = data["graph_context_receipt"]["context_receipt_sha256"]
    policy = t.GraphExecutionPolicyV2.model_validate(data["graph_context_execution"]["policy"])
    data["graph_context_execution"]["execution_policy_sha256"] = t.graph_execution_policy_digest_v2(
        data["graph_context_receipt"]["context_receipt_sha256"], policy)
    with pytest.raises(ValidationError):
        t.TurnSubmission.model_validate(data)


def test_reader_fence_keeps_plan_rows_and_fingerprints_unchanged(application_state_dsn):
    from alembic import command
    from application_state.cli import alembic_config
    service = AgentConversationService()
    conversation, _, _, claimed = _accepted_execution_turn(service, "existing-plan-world")
    before = claimed.model_dump(mode="json", by_alias=True)
    with pytest.raises(RuntimeError, match="recovery forward"):
        command.downgrade(alembic_config(), "20261013_0023")
    loaded = AgentConversationService().list_turns("existing-plan-world", conversation.conversation_id)[0]
    assert loaded.model_dump(mode="json", by_alias=True) == before
    assert loaded.submitted_intent_fingerprint_v2 == claimed.submitted_intent_fingerprint_v2


def test_reader_fence_keeps_build_rows_and_retry_identity_unchanged(application_state_dsn):
    from alembic import command
    from application_state.cli import alembic_config
    submission, turn = _accept_claim(AgentConversationService())
    with pytest.raises(RuntimeError, match="recovery forward"):
        command.downgrade(alembic_config(), "20261013_0023")
    assert AgentConversationService().list_turns(turn.world_id, turn.conversation_id)[0] == turn
    assert AgentConversationService().accept_turn(submission) == turn


@pytest.mark.parametrize("mutation", ["missing_source", "wrong_world", "plan_basis"])
def test_sql_rejects_malformed_build_receipts(application_state_dsn, mutation):
    service = AgentConversationService()
    submission, turn = _accept_claim(service)
    receipt = submission.graph_context_receipt.model_dump(mode="json", by_alias=True)
    if mutation == "missing_source":
        receipt.pop("source_basis")
    if mutation == "wrong_world":
        receipt["source_basis"]["world_id"] = "foreign"
    if mutation == "plan_basis":
        receipt["plan_basis"] = {}
    with psycopg.connect(application_state_dsn) as conn:
        with pytest.raises(psycopg.errors.CheckViolation):
            conn.execute("UPDATE agent.turn SET graph_context_receipt=%s WHERE turn_id=%s", (Jsonb(receipt), turn.turn_id))
