from datetime import UTC, datetime
import json
from uuid import uuid4

import psycopg
from psycopg.types.json import Jsonb
import pytest

from application_state.agent_conversation import AgentConversationService
from application_state.agent_conversation.context_trace import (
    CONTEXT_TRACE_TERMINAL_RESERVE_BYTES, MAX_CONTEXT_TRACE_BYTES,
    TraceContextSnapshot, TraceContextMaterial,
)
from application_state.agent_conversation.types import (
    TurnSubmission, TurnProvenance, HistoricalReference, SubmittedTurnIntentV1,
    SubmittedGraphRequestIntentV1, TurnFailure, TurnResult,
)
from application_state.errors import ApplicationStateValidationError
from tests.application_state.test_agent_conversation_postgres import _new


def _setup_turn():
    service = AgentConversationService()
    world_id = "trace-regression-" + uuid4().hex
    conversation = _new(service, world_id)
    intent = SubmittedTurnIntentV1(
        world_id=world_id, client_thread_id="trace", message="question", surface_id="index",
        surface_instance_id="index-home", client_work_state="none", primary_work=None,
        graph_request=SubmittedGraphRequestIntentV1(mode="none"), graph_selection=None,
    )
    turn = service.accept_turn(TurnSubmission(
        world_id=world_id, conversation_id=conversation.conversation_id, idempotency_key=uuid4(),
        expected_conversation_revision=1, user_text=intent.message, submitted_intent_v1=intent,
        provenance=TurnProvenance(world_id=world_id, surface_resolution="resolved", surface_id="index",
                                 primary_work=HistoricalReference(resolution="absent"),
                                 selected_object=HistoricalReference(resolution="absent")),
    ))
    turn = service.claim_turn(world_id, conversation.conversation_id, turn.turn_id,
                              expected_revision=turn.revision, lease_seconds=60).turn
    identity = dict(world_id=world_id, conversation_id=conversation.conversation_id,
                    turn_id=turn.turn_id, expected_revision=turn.revision,
                    attempt=turn.attempt, trace_id=uuid4())
    trace = service.start_context_trace(**identity, started_at=datetime.now(UTC))
    return service, turn, identity, trace


@pytest.mark.parametrize("terminal", ["completed", "failed", "interrupted"])
def test_near_capacity_trace_preserves_core_terminal_and_marks_overflow(application_state_dsn, terminal):
    service, turn, identity, trace = _setup_turn()
    event = TraceContextSnapshot(sequence=0, elapsed_ms=0, stage="before", materials=[
        TraceContextMaterial(item_id="question", state="model_context", role="user", text=""),
    ])
    payload = {**trace.model_dump(mode="json", by_alias=True), "observations": [event.model_dump(mode="json")]}
    overhead = len(json.dumps(payload, ensure_ascii=True, sort_keys=True).encode())
    text = "x" * (MAX_CONTEXT_TRACE_BYTES - CONTEXT_TRACE_TERMINAL_RESERVE_BYTES - overhead - 20)
    event.materials[0].text = text
    saved = service.append_context_trace(**identity, observation=event)
    assert saved.capture_status == "recording"
    overflow = TraceContextSnapshot(sequence=1, elapsed_ms=1, stage="after", materials=[
        TraceContextMaterial(item_id="extra", state="model_context", role="user", text="é" * 4096),
    ])
    limited = service.append_context_trace(**identity, observation=overflow)
    assert limited.capture_status == "incomplete"
    assert limited.capture_failure_code == "trace_size_limit"
    assert limited.observations == [event]
    if terminal == "completed":
        final = service.complete_turn(TurnResult(world_id=turn.world_id, conversation_id=turn.conversation_id,
            turn_id=turn.turn_id, expected_revision=turn.revision, assistant_text="answer"))
    else:
        final = service.fail_turn(TurnFailure(world_id=turn.world_id, conversation_id=turn.conversation_id,
            turn_id=turn.turn_id, expected_revision=turn.revision, failure_code="synthetic_failure"),
            interrupted=terminal == "interrupted")
    assert final.status == terminal
    closed = AgentConversationService().list_context_trace_attempts(world_id=turn.world_id, turn_id=turn.turn_id)[0]
    assert closed.terminal_status == terminal
    assert closed.closed_at == final.completed_at
    assert closed.observations[0].materials[0].text == text
    with psycopg.connect(application_state_dsn) as conn:
        assert conn.execute("SELECT octet_length(payload::text) FROM agent.turn_context_trace WHERE turn_id=%s", (turn.turn_id,)).fetchone()[0] <= MAX_CONTEXT_TRACE_BYTES


def test_unknown_present_source_is_rejected_and_core_failure_still_commits(application_state_dsn):
    service, turn, identity, _ = _setup_turn()
    event = TraceContextSnapshot(sequence=0, elapsed_ms=0, stage="after", materials=[
        TraceContextMaterial(item_id="phantom", state="model_context", role="source",
            source_read_event_id=uuid4(), source_reads=[{"source_read_id": "missing", "content_sha256": "a" * 64}]),
    ])
    with pytest.raises(ApplicationStateValidationError, match="earlier captured same-turn"):
        service.append_context_trace(**identity, observation=event)
    final = service.fail_turn(TurnFailure(world_id=turn.world_id, conversation_id=turn.conversation_id,
        turn_id=turn.turn_id, expected_revision=turn.revision, failure_code="synthetic_failure"))
    assert final.status == "failed"
    assert not service.list_context_trace_attempts(world_id=turn.world_id, turn_id=turn.turn_id)[0].observations


def test_trace_migration_rejects_missing_identity_fields(application_state_dsn):
    _, turn, _, _ = _setup_turn()
    with pytest.raises(psycopg.errors.CheckViolation):
        with psycopg.connect(application_state_dsn) as conn:
            conn.execute("UPDATE agent.turn_context_trace SET payload=%s WHERE turn_id=%s",
                (Jsonb({"execution_start_sequence": 0, "observations": []}), turn.turn_id))


def _captured_passage_fixture(dsn):
    from hashlib import sha256
    from application_state.agent_conversation.context_trace import TraceSourcePassage, TraceHistoricalSourceReferenceV1
    service, turn, identity, trace = _setup_turn()
    text = 'Earlier 🦉 source.'
    passage = TraceSourcePassage(sequence=0, elapsed_ms=1, source_read_event_id=uuid4(), read_call_id=uuid4(),
        world_id=turn.world_id, graph_revision='revision', source_read_id='source/a ?&=', anchor_id='anchor',
        evidence_ref_id='evidence', source_artifact_id='artifact', source_name='Longmont C2 · Session 24', source_revision_id='revision',
        outcome='enough', returned_chars=len(text), content_sha256=sha256(text.encode()).hexdigest(), text=text)
    payload = trace.model_dump(mode='json', by_alias=True)
    payload['observations'] = [passage.model_dump(mode='json')]
    with psycopg.connect(dsn) as conn:
        conn.execute('UPDATE agent.turn_context_trace SET payload=%s WHERE turn_id=%s AND attempt=1', (Jsonb(payload), turn.turn_id))
        # Deliberately invalid model in another attempt: exact reads must not load it.
        other = {**payload, 'attempt': 2, 'trace_id': str(uuid4()), 'observations': [{'invalid': True}]}
        conn.execute('INSERT INTO agent.turn_context_trace(turn_id,attempt,trace_id,payload) VALUES(%s,2,%s,%s)',
            (turn.turn_id, other['trace_id'], Jsonb(other)))
    reference = TraceHistoricalSourceReferenceV1(world_id=turn.world_id, conversation_id=turn.conversation_id,
        turn_id=turn.turn_id, attempt=1, trace_id=trace.trace_id, source_read_event_id=passage.source_read_event_id,
        source_read_id=passage.source_read_id, content_sha256=passage.content_sha256)
    return service, reference, passage, payload


def test_exact_historical_read_loads_only_one_attempt(application_state_dsn, monkeypatch):
    from application_state.agent_conversation import context_trace_store
    service, reference, passage, _ = _captured_passage_fixture(application_state_dsn)
    load = context_trace_store._load_trace
    seen = []
    def record(payload):
        seen.append(payload['attempt'])
        return load(payload)
    monkeypatch.setattr(context_trace_store, '_load_trace', record)
    read = service.read_historical_source_passage(reference)
    assert read == passage
    assert read.source_name == "Longmont C2 · Session 24"
    assert seen == [1]


@pytest.mark.parametrize('field', ['world_id', 'conversation_id', 'turn_id', 'trace_id', 'attempt', 'source_read_event_id', 'source_read_id', 'content_sha256'])
def test_exact_historical_read_rejects_every_changed_pin(application_state_dsn, field):
    from application_state.errors import ApplicationStateNotFoundError
    service, reference, _, _ = _captured_passage_fixture(application_state_dsn)
    value = 3 if field == 'attempt' else 'b' * 64 if field == 'content_sha256' else 'foreign' if field in {'world_id', 'source_read_id'} else uuid4()
    changed = type(reference).model_validate({**reference.model_dump(), field: value})
    with pytest.raises(ApplicationStateNotFoundError):
        service.read_historical_source_passage(changed)


@pytest.mark.parametrize('corruption', ['hash', 'count', 'world', 'duplicate'])
def test_exact_historical_read_fails_closed_on_stored_corruption(application_state_dsn, corruption):
    service, reference, _, payload = _captured_passage_fixture(application_state_dsn)
    if corruption == 'hash': payload['observations'][0]['text'] = 'Changed source!'
    if corruption == 'count': payload['observations'][0]['returned_chars'] += 1
    if corruption == 'world': payload['world_id'] = 'foreign'
    if corruption == 'duplicate': payload['observations'].append({**payload['observations'][0], 'sequence': 1})
    with psycopg.connect(application_state_dsn) as conn:
        conn.execute('UPDATE agent.turn_context_trace SET payload=%s WHERE turn_id=%s AND attempt=1', (Jsonb(payload), reference.turn_id))
    from application_state.errors import ApplicationStateError
    with pytest.raises(ApplicationStateError):
        service.read_historical_source_passage(reference)


def test_source_name_page_projection_is_exact_and_excludes_source_bytes(application_state_dsn):
    service, reference, passage, _ = _captured_passage_fixture(application_state_dsn)
    labels = service.source_name_labels(reference.world_id, reference.conversation_id, [reference.turn_id])
    assert len(labels) == 1
    assert labels[0]['source_name'] == passage.source_name
    assert labels[0]['source_read_event_id'] == str(passage.source_read_event_id)
    assert labels[0]['content_sha256'] == passage.content_sha256
    assert set(labels[0]) == {'turn_id','source_read_event_id','source_read_id','source_artifact_id',
        'source_revision_id','anchor_id','evidence_ref_id','graph_revision','content_sha256','source_name'}
    assert 'text' not in labels[0]
    assert service.source_name_labels('foreign',reference.conversation_id,[reference.turn_id]) == []
    assert service.source_name_labels(reference.world_id,uuid4(),[reference.turn_id]) == []


@pytest.mark.parametrize('field', ['world_id','conversation_id','turn_id','trace_id','attempt'])
def test_source_name_page_refuses_changed_trace_owner(application_state_dsn,field):
    service, reference, _, payload = _captured_passage_fixture(application_state_dsn)
    payload[field] = 2 if field == 'attempt' else 'foreign'
    if field in {'turn_id', 'trace_id', 'attempt'}:
        with pytest.raises(psycopg.errors.CheckViolation), psycopg.connect(application_state_dsn) as conn:
            conn.execute('UPDATE agent.turn_context_trace SET payload=%s WHERE turn_id=%s AND attempt=1',
                (Jsonb(payload), reference.turn_id))
        return
    with psycopg.connect(application_state_dsn) as conn:
        conn.execute('UPDATE agent.turn_context_trace SET payload=%s WHERE turn_id=%s AND attempt=1',
            (Jsonb(payload),reference.turn_id))
    assert service.source_name_labels(reference.world_id,reference.conversation_id,[reference.turn_id]) == []


def test_authored_observation_requires_a_recorded_event_at_the_real_trace_append_boundary(application_state_dsn):
    from tests.test_agent_context_trace_types import _authored_trace_fixture
    service, turn, identity, _ = _setup_turn()
    _, _, observation = _authored_trace_fixture()
    with pytest.raises(ApplicationStateValidationError, match='exact turn ledger'):
        service.append_context_trace(**identity, observation=observation)
    assert not service.list_context_trace_attempts(world_id=turn.world_id, turn_id=turn.turn_id)[0].observations
