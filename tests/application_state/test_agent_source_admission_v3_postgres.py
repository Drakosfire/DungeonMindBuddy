"""Owning APP V3 admission, capture and claim-fence proofs; synthetic sources only."""
from datetime import UTC, datetime
import hashlib
import json
from uuid import uuid4

import psycopg
import pytest

from application_state.agent_conversation import AgentConversationService
from application_state.agent_conversation import types as t
from application_state.agent_conversation.context_trace import (
    MAX_CONTEXT_TRACE_BYTES, CONTEXT_TRACE_TERMINAL_RESERVE_BYTES,
    TraceContextMaterial, TraceContextSnapshot, TraceSourcePassage,
)
from application_state.errors import ApplicationStateConflictError, ApplicationStateValidationError
from tests.application_state.test_agent_conversation_postgres import _new
from tests.application_state.test_agent_conversation_service import _source_admission_v3_fixture


@pytest.fixture
def v3_turn(application_state_dsn):
    service = AgentConversationService()
    receipt, execution, origin, extension = _source_admission_v3_fixture()
    basis = receipt.plan_basis
    conversation = _new(service, basis.world_id)
    intent = t.SubmittedTurnIntentV2(world_id=basis.world_id, client_thread_id="source-admission",
        message="Read a traversal-discovered source.", surface_id="plan", surface_instance_id="plan-main",
        client_work_state="saved_clean", primary_work=t.SubmittedPrimaryWorkIntentV1(kind="plan",
            object_id=basis.document_id, expected_revision=basis.object_revision,
            expected_revision_n=basis.revision_n, expected_content_sha256=basis.content_sha256),
        plan_context_policy=receipt.plan_context_policy, graph_request=t.SubmittedGraphRequestIntentV1(mode="none"),
        graph_selection=None)
    accepted = service.accept_turn(t.TurnSubmission(world_id=basis.world_id, conversation_id=conversation.conversation_id,
        idempotency_key=uuid4(), expected_conversation_revision=1, user_text=intent.message,
        submitted_intent_v2=intent, graph_context_receipt=receipt, graph_context_execution=execution,
        provenance=t.TurnProvenance(world_id=basis.world_id, surface_resolution="resolved", surface_id="plan",
            surface_instance_id="plan-main", primary_work=t.HistoricalReference(resolution="resolved", kind="plan",
                object_id=basis.document_id, object_revision=basis.object_revision, work_revision_id=basis.work_revision_id,
                revision_n=basis.revision_n, content_sha256=basis.content_sha256),
            selected_object=t.HistoricalReference(resolution="absent"))))
    turn = service.claim_turn(basis.world_id, conversation.conversation_id, accepted.turn_id,
        expected_revision=accepted.revision, lease_seconds=60).turn
    trace_id = uuid4()
    service.start_context_trace(world_id=turn.world_id, conversation_id=turn.conversation_id, turn_id=turn.turn_id,
        expected_revision=turn.revision, attempt=turn.attempt, trace_id=trace_id, started_at=datetime.now(UTC))
    return service, turn, receipt, execution, origin, extension, trace_id


def _append(service, turn, method, field, event, **extra):
    return getattr(service, method)(turn.world_id, turn.conversation_id, turn.turn_id,
        expected_revision=turn.revision, expected_attempt=turn.attempt, **{field: event}, **extra)


def _admit(v3_turn):
    service, turn, receipt, execution, origin, extension, trace_id = v3_turn
    turn, inserted = _append(service, turn, "append_validated_graph_operation", "operation_event", origin)
    assert inserted
    turn, inserted = _append(service, turn, "extend_source_scope", "extension", extension)
    assert inserted
    return service, turn, receipt, execution, origin, extension, trace_id


def _authorization(turn, pin, chars=3):
    execution = turn.graph_context_execution
    scope = execution.policy.source_read_scope
    return t.SourceReadAuthorizationEventV2(event_id=uuid4(), sequence=len(execution.events), kind="source_read_authorized_v2",
        read_call_id=uuid4(), context_receipt_sha256=execution.context_receipt_sha256,
        execution_policy_sha256=execution.execution_policy_sha256, retrieval_session_id=scope.retrieval_session_id,
        world_id=turn.world_id, campaign_id=scope.campaign_id, graph_revision=scope.graph_revision,
        anchors=[pin], max_chars=chars)


def _read_event(turn, authorization, text="abc"):
    pin = authorization.anchors[0]
    read = t.SourceReadAnchorReceiptV2(source_read_id="read-"+uuid4().hex, **pin.model_dump(), outcome="enough",
        content_sha256=hashlib.sha256(text.encode()).hexdigest(), returned_chars=len(text), truncated=False,
        evidence_sufficiency_status="sufficient")
    event = t.ValidatedSourceReadEventV2(event_id=uuid4(), sequence=len(turn.graph_context_execution.events),
        kind="validated_source_read_v2", read_call_id=authorization.read_call_id, receipts=[read])
    passage = TraceSourcePassage(sequence=0, elapsed_ms=1, source_read_event_id=event.event_id,
        read_call_id=authorization.read_call_id, world_id=turn.world_id, graph_revision=authorization.graph_revision,
        source_read_id=read.source_read_id, **pin.model_dump(), outcome="enough", text=text,
        returned_chars=len(text), content_sha256=read.content_sha256)
    return event, passage


def _provider(turn, receipt, origin, reads):
    a = receipt.assembled_input
    return t.ProviderAttemptAuthorizedEventV3(event_id=uuid4(), sequence=len(turn.graph_context_execution.events),
        kind="provider_attempt_authorized_v3", provider_attempt_id=uuid4(), envelope_sha256=a.assembled_input_sha256,
        serializer_version="canonical-json-utf8-v1", provider="synthetic", model=a.provider_model_name,
        api_mode="messages", tool_schema_sha256="5"*64, input_accounting_kind="exact_token_count",
        input_estimator=a.tokenizer_name, input_tokens=a.provider_envelope_input_tokens,
        output_token_reserve=a.output_token_reserve, included_assertion_ids=[], included_relationship_ids=[],
        included_evidence_ref_ids=origin.evidence_ref_ids, included_graph_event_ids=[origin.event_id],
        included_source_read_event_ids=[event.event_id for event in reads])


def test_v3_fresh_readback_nine_passages_inclusion_and_no_unknown_follow(v3_turn):
    service, turn, receipt, initial, origin, extension, _ = _admit(v3_turn)
    reads = []
    for pin in extension.pins:
        authorization = _authorization(turn, pin)
        turn, _ = _append(service, turn, "authorize_source_read", "authorization", authorization)
        event, passage = _read_event(turn, authorization)
        turn, _ = _append(service, turn, "record_validated_source_read", "receipt", event, source_passages=[passage])
        reads.append(event)
    reloaded = AgentConversationService().list_turns(turn.world_id, turn.conversation_id)[0]
    assert reloaded == turn and isinstance(reloaded.graph_context_execution, t.PlanWorldGraphExecutionV3)
    assert reloaded.graph_context_execution.policy == initial.policy
    assert reloaded.graph_context_receipt == receipt
    trace = service.list_context_trace_attempts(world_id=turn.world_id, turn_id=turn.turn_id)[0]
    assert len([item for item in trace.observations if isinstance(item, TraceSourcePassage)]) == 9
    attempt = _provider(turn, receipt, origin, reads)
    turn, _ = _append(service, turn, "authorize_provider_attempt", "provider_attempt_event", attempt)
    assert len(turn.graph_context_execution.events[-1].included_source_read_event_ids) == 9
    citation_map = t.PlanWorldGraphCitationMapV2(context_receipt_sha256=receipt.context_receipt_sha256,
        entries=[t.PlanWorldGraphCitationV2(claim_id=f"opened-{i}", target_kind="assertion", target_id="assertion-1",
            graph_revision=extension.graph_revision, evidence_ref_ids=[read.receipts[0].evidence_ref_id],
            source_read_ids=[read.receipts[0].source_read_id], source_opened=True) for i, read in enumerate(reads)])
    t.validate_graph_execution_source_citations(citation_map, turn.graph_context_execution, attempt.provider_attempt_id)
    forged = citation_map.model_copy(update={"entries": [citation_map.entries[0].model_copy(update={"source_read_ids": ["uncaptured-forgery"]})]})
    with pytest.raises(ValueError, match="source reads"):
        t.validate_graph_execution_source_citations(forged, turn.graph_context_execution, attempt.provider_attempt_id)
    unknown = t.ProviderOutcomeEventV1(event_id=uuid4(), sequence=len(turn.graph_context_execution.events),
        kind="provider_outcome", provider_attempt_id=attempt.provider_attempt_id, outcome="outcome_unknown")
    turn, _ = _append(service, turn, "record_provider_outcome", "outcome", unknown)
    for method, field, event in [
        ("extend_source_scope", "extension", extension.model_copy(update={"event_id": uuid4(), "sequence": len(turn.graph_context_execution.events)})),
        ("authorize_source_read", "authorization", _authorization(turn, extension.pins[0])),
        ("append_validated_graph_operation", "operation_event", origin.model_copy(update={"event_id": uuid4(), "operation_id": uuid4(), "sequence": len(turn.graph_context_execution.events)})),
    ]:
        with pytest.raises(ApplicationStateValidationError, match="unknown provider outcome"):
            _append(service, turn, method, field, event)
    turn = service.fail_turn(t.TurnFailure(world_id=turn.world_id, conversation_id=turn.conversation_id,
        turn_id=turn.turn_id, expected_revision=turn.revision, failure_code="provider_outcome_unknown"), interrupted=True)
    with pytest.raises(ApplicationStateConflictError, match="prior provider authorization"):
        service.claim_turn(turn.world_id, turn.conversation_id, turn.turn_id, expected_revision=turn.revision)


@pytest.mark.parametrize("fence", ["fresh", "stale", "attempt", "expired"])
def test_v3_extension_owning_fences_duplicates_and_origin_immutability(v3_turn, application_state_dsn, fence):
    service, turn, _, _, origin, extension, _ = v3_turn
    turn, _ = _append(service, turn, "append_validated_graph_operation", "operation_event", origin)
    if fence == "expired":
        with psycopg.connect(application_state_dsn) as conn:
            conn.execute("UPDATE agent.turn SET claim_expires_at=clock_timestamp()-interval '1 second' WHERE turn_id=%s", (turn.turn_id,))
    revision = turn.revision-1 if fence == "stale" else turn.revision
    attempt = turn.attempt+1 if fence == "attempt" else turn.attempt
    if fence != "fresh":
        with pytest.raises(ApplicationStateConflictError):
            service.extend_source_scope(turn.world_id, turn.conversation_id, turn.turn_id,
                expected_revision=revision, expected_attempt=attempt, extension=extension)
        assert service.list_turns(turn.world_id, turn.conversation_id)[0].graph_context_execution == turn.graph_context_execution
        return
    turn, fresh = _append(service, turn, "extend_source_scope", "extension", extension)
    assert fresh
    assert _append(service, turn, "extend_source_scope", "extension", extension) == (turn, False)
    with pytest.raises(ApplicationStateConflictError, match="changed content"):
        _append(service, turn, "append_validated_graph_operation", "operation_event", origin.model_copy(update={"returned_source_pins": []}))


@pytest.mark.parametrize("change", ["forged", "foreign_native", "foreign_binding", "mixed", "changed_pin"])
def test_v3_owning_rejects_unproven_or_mixed_admission(v3_turn, change):
    service, turn, _, _, origin, extension, _ = v3_turn
    turn, _ = _append(service, turn, "append_validated_graph_operation", "operation_event", origin)
    if change in {"mixed", "changed_pin"}:
        admitted, _ = _append(service, turn, "extend_source_scope", "extension", extension)
        authorization = _authorization(admitted, extension.pins[0])
        forged = extension.pins[0].model_copy(update={"anchor_id": "unreturned"})
        authorization = authorization.model_copy(update={"anchors": [extension.pins[0], forged] if change == "mixed" else [forged]})
        with pytest.raises(ApplicationStateValidationError, match="unadmitted or changed"):
            _append(service, admitted, "authorize_source_read", "authorization", authorization)
        return
    extension = extension.model_copy(update={
        {"forged": "origin_graph_event_id", "foreign_native": "native_world_id", "foreign_binding": "binding_version"}[change]:
        uuid4() if change == "forged" else (99 if change == "foreign_binding" else "foreign")})
    with pytest.raises(ApplicationStateValidationError):
        _append(service, turn, "extend_source_scope", "extension", extension)
    assert service.list_turns(turn.world_id, turn.conversation_id)[0] == turn


def test_v3_trace_capacity_rolls_back_passage_and_blocks_uncaptured_inclusion(v3_turn):
    service, turn, receipt, _, origin, extension, trace_id = _admit(v3_turn)
    identity = dict(world_id=turn.world_id, conversation_id=turn.conversation_id, turn_id=turn.turn_id,
        expected_revision=turn.revision, attempt=turn.attempt, trace_id=trace_id)
    trace = service.list_context_trace_attempts(world_id=turn.world_id, turn_id=turn.turn_id)[0]
    event = TraceContextSnapshot(sequence=0, elapsed_ms=0, stage="before", materials=[
        TraceContextMaterial(item_id="question", state="model_context", role="user", text="")])
    payload = trace.model_dump(mode="json", by_alias=True) | {"observations": [event.model_dump(mode="json")]}
    overhead = len(json.dumps(payload, ensure_ascii=True, sort_keys=True).encode())
    event.materials[0].text = "x"*(MAX_CONTEXT_TRACE_BYTES-CONTEXT_TRACE_TERMINAL_RESERVE_BYTES-overhead-20)
    service.append_context_trace(**identity, observation=event)
    authorization = _authorization(turn, extension.pins[0], chars=12000)
    turn, _ = _append(service, turn, "authorize_source_read", "authorization", authorization)
    read, passage = _read_event(turn, authorization, text="x"*12000)
    with pytest.raises(ApplicationStateValidationError, match="storage|size|1 MiB"):
        _append(service, turn, "record_validated_source_read", "receipt", read, source_passages=[passage])
    assert service.list_turns(turn.world_id, turn.conversation_id)[0] == turn
    service.mark_context_trace_incomplete(**(identity | {"expected_revision": turn.revision}), failure_code="source_capture_capacity")
    turn, _ = _append(service, turn, "record_validated_source_read", "receipt", read)
    with pytest.raises(ApplicationStateValidationError, match="captured source passages"):
        _append(service, turn, "authorize_provider_attempt", "provider_attempt_event", _provider(turn, receipt, origin, [read]))
    trace = service.list_context_trace_attempts(world_id=turn.world_id, turn_id=turn.turn_id)[0]
    assert trace.capture_status == "incomplete" and not any(isinstance(item, TraceSourcePassage) for item in trace.observations)
    terminal = service.fail_turn(t.TurnFailure(world_id=turn.world_id, conversation_id=turn.conversation_id,
        turn_id=turn.turn_id, expected_revision=turn.revision, failure_code="source_capacity"), interrupted=True)
    assert terminal.assistant_text is None and terminal.completion is None


def test_v3_migration_refuses_loss_of_admission(v3_turn, application_state_dsn):
    from alembic import command
    from application_state.cli import alembic_config
    with pytest.raises(RuntimeError, match="V3 Graph source admission"):
        command.downgrade(alembic_config(), "20261013_0022")
    service, turn, *_ = v3_turn
    assert AgentConversationService().list_turns(turn.world_id, turn.conversation_id)[0] == turn


def test_v3_migration_keeps_v1_execution_bytes(application_state_dsn):
    from alembic import command
    from application_state.cli import alembic_config
    from tests.application_state.test_agent_conversation_postgres import _accepted_execution_turn
    service = AgentConversationService()
    _, _, _, turn = _accepted_execution_turn(service, "legacy-v1-admission")
    with psycopg.connect(application_state_dsn) as conn:
        before = conn.execute("SELECT graph_context_execution::text FROM agent.turn WHERE turn_id=%s", (turn.turn_id,)).fetchone()[0]
    command.downgrade(alembic_config(), "20261013_0022")
    command.upgrade(alembic_config(), "head")
    with psycopg.connect(application_state_dsn) as conn:
        after = conn.execute("SELECT graph_context_execution::text FROM agent.turn WHERE turn_id=%s", (turn.turn_id,)).fetchone()[0]
    assert before == after
    assert service.list_turns(turn.world_id, turn.conversation_id)[0] == turn


def test_v3_expired_authorized_claim_preserves_version_and_admission(v3_turn, application_state_dsn):
    service, turn, receipt, _, origin, extension, _ = _admit(v3_turn)
    attempt = _provider(turn, receipt, origin, [])
    turn, _ = _append(service, turn, "authorize_provider_attempt", "provider_attempt_event", attempt)
    entered = t.ProviderOutcomeEventV1(event_id=uuid4(), sequence=len(turn.graph_context_execution.events),
        kind="provider_outcome", provider_attempt_id=attempt.provider_attempt_id, outcome="sdk_entered")
    turn, _ = _append(service, turn, "record_provider_outcome", "outcome", entered)
    with psycopg.connect(application_state_dsn) as conn:
        conn.execute("UPDATE agent.turn SET claim_expires_at=clock_timestamp()-interval '1 second' WHERE turn_id=%s", (turn.turn_id,))
    with pytest.raises(ApplicationStateConflictError, match="potentially sent"):
        service.claim_turn(turn.world_id, turn.conversation_id, turn.turn_id, expected_revision=turn.revision)
    settled = AgentConversationService().list_turns(turn.world_id, turn.conversation_id)[0]
    assert settled.status == "interrupted" and isinstance(settled.graph_context_execution, t.PlanWorldGraphExecutionV3)
    assert settled.graph_context_execution.events[:-1] == turn.graph_context_execution.events
    assert settled.graph_context_execution.events[-1].outcome == "outcome_unknown"
    assert settled.graph_context_execution.effective_source_pins()[extension.pins[0].anchor_id] == extension.pins[0]
    with pytest.raises(ApplicationStateConflictError):
        _append(service, settled, "extend_source_scope", "extension", extension)


def test_v3_completion_preserves_24_reads_for_one_claim_and_fresh_process(v3_turn):
    import os
    import subprocess
    import sys

    service, turn, receipt, initial, origin, extension, trace_id = v3_turn
    target = "assertion-many-source-passages"
    origin = origin.model_copy(update={"assertion_ids": [target]})
    service, turn, receipt, _, origin, extension, _ = _admit(
        (service, turn, receipt, initial, origin, extension, trace_id))
    reads = []
    for _ in range(24):
        authorization = _authorization(turn, extension.pins[0])
        turn, _ = _append(service, turn, "authorize_source_read", "authorization", authorization)
        read, passage = _read_event(turn, authorization)
        turn, _ = _append(service, turn, "record_validated_source_read", "receipt", read, source_passages=[passage])
        reads.append(read)
    attempt = _provider(turn, receipt, origin, reads).model_copy(update={"included_assertion_ids": [target]})
    turn, _ = _append(service, turn, "authorize_provider_attempt", "provider_attempt_event", attempt)
    for outcome in ("sdk_entered", "response_received"):
        event = t.ProviderOutcomeEventV1(event_id=uuid4(), sequence=len(turn.graph_context_execution.events),
            kind="provider_outcome", provider_attempt_id=attempt.provider_attempt_id, outcome=outcome)
        turn, _ = _append(service, turn, "record_provider_outcome", "outcome", event)
    read_ids = sorted(read.receipts[0].source_read_id for read in reads)
    refs = [extension.pins[0].evidence_ref_id]
    claim = t.PlanWorldGraphClaimSegmentV1(kind="graph_claim", claim_id="claim-many", text="Source-backed statement.",
        target_kind="assertion", target_id=target, graph_revision=extension.graph_revision, evidence_ref_ids=refs)
    citation = t.PlanWorldGraphCitationV2(claim_id=claim.claim_id, target_kind=claim.target_kind,
        target_id=target, graph_revision=claim.graph_revision, evidence_ref_ids=refs,
        source_read_ids=read_ids, source_opened=True)
    completion = t.PlanWorldGraphCompletionV2(context_receipt_sha256=receipt.context_receipt_sha256,
        answer_basis="committed_plan_plus_world_graph", answer_context_status="graph_grounded",
        answer_segments=[claim], citation_map=t.PlanWorldGraphCitationMapV2(
            context_receipt_sha256=receipt.context_receipt_sha256, entries=[citation]))
    completed = service.complete_turn(t.TurnResult(world_id=turn.world_id, conversation_id=turn.conversation_id,
        turn_id=turn.turn_id, expected_revision=turn.revision, assistant_text=claim.text,
        completion=completion, producing_provider_attempt_id=attempt.provider_attempt_id,
        claim_graph_event_ids={claim.claim_id: [origin.event_id]}))
    fresh = AgentConversationService().list_turns(turn.world_id, turn.conversation_id)[0]
    assert fresh == completed and fresh.completion.citation_map.entries[0].source_read_ids == read_ids
    child = subprocess.check_output([sys.executable, "-c", """
import json,sys
from uuid import UUID
from application_state.agent_conversation import AgentConversationService
turn = AgentConversationService().list_turns(sys.argv[1], UUID(sys.argv[2]))[0]
print(json.dumps(turn.model_dump(mode="json",by_alias=True)))
""", turn.world_id, str(turn.conversation_id)], env=os.environ.copy(), text=True)
    assert json.loads(child) == completed.model_dump(mode="json", by_alias=True)
