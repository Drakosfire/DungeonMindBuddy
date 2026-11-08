"""Native writer capture and cross-family source integrity at their owning checks."""
from threading import RLock
from types import SimpleNamespace
from uuid import uuid4
import pytest
from application_state.errors import ApplicationStateValidationError
from apps.live_control_server.services.agent_context_trace_collector import ContextTraceCollector


@pytest.mark.parametrize('case', ['missing_response', 'foreign_response', 'foreign_producer'])
def test_native_writer_draft_requires_exact_acknowledged_producer(case):
    attempt = uuid4()
    authorization = SimpleNamespace(kind='plan_native_writer_authorized_v1', provider_attempt_id=attempt)
    events = [authorization]
    if case != 'missing_response':
        events.append(SimpleNamespace(kind='provider_outcome', outcome='response_received',
            provider_attempt_id=uuid4() if case == 'foreign_response' else attempt))
    collector = ContextTraceCollector.__new__(ContextTraceCollector)
    collector.fence = SimpleNamespace(renewer=SimpleNamespace(_lock=RLock(),
        _turn=SimpleNamespace(graph_context_execution=SimpleNamespace(events=events))))
    with pytest.raises(ApplicationStateValidationError, match='producing provider response'):
        collector.answer_draft('Unvalidated synthetic output',
            producing_provider_attempt_id=uuid4() if case == 'foreign_producer' else attempt)


@pytest.mark.parametrize('body_end,clause_start,statement_size,expected', [
    (5, 5, 10, None),
    (6, 4, 10, None),
    (10, 5, 10, None),
    (5, 5, 11, 'disagree on original body size'),
    (11, 5, 10, 'Source exposure interval'),
])
def test_body_and_statement_reads_preserve_original_source_integrity(
        body_end, clause_start, statement_size, expected):
    from application_state.agent_conversation.native_corpus import (
        validate_source_exposure, NativeBodySearchObservedV1)
    from application_state.agent_conversation.native_plan_statements import NativePlanStatementReadObservedV1
    catalog = SimpleNamespace(catalog_sha256='catalog', body_bytes=10, source=SimpleNamespace(
        artifact=SimpleNamespace(source_artifact_id='artifact'),
        revision=SimpleNamespace(source_revision_id='revision', content_sha256='digest')))
    search = NativeBodySearchObservedV1.model_construct(catalogs=(catalog,))
    support = SimpleNamespace(source_artifact_id='artifact', source_revision_id='revision',
        source_body_sha256='digest', clause_start_byte=clause_start,
        clause_end_byte=10 if clause_start == 5 else 8)
    statement = NativePlanStatementReadObservedV1.model_construct(
        reads=(SimpleNamespace(support=support, source_body_bytes=statement_size),))
    body = SimpleNamespace(excerpt=SimpleNamespace(catalog_sha256='catalog',
        section=SimpleNamespace(byte_start=0, byte_end=body_end)))
    execution = SimpleNamespace(events=(search, statement))
    if expected:
        with pytest.raises(ValueError, match=expected):
            validate_source_exposure(execution, (body,))
    else:
        validate_source_exposure(execution, (body,))


@pytest.fixture
def native_read_admission_probes(monkeypatch):
    """Exercise refusals inside the actual APP transaction before a normal read."""
    from application_state.agent_conversation import AgentConversationService
    from application_state.agent_conversation.native_plan_assertions import NativePlanAssertionReadAuthorizedV1
    authorize = AgentConversationService.authorize_native_read
    observe = AgentConversationService.observe_native_read
    calls = []

    def checked_authorize(self, world_id, conversation_id, turn_id, **kwargs):
        before = self.inspect_turn(world_id=world_id, turn_id=turn_id)
        with pytest.raises(ApplicationStateValidationError, match="Unknown native"):
            authorize(self, world_id, conversation_id, turn_id, **(kwargs | {"record_kind": "other"}))
        other = "statement" if kwargs["record_kind"] == "assertion" else "assertion"
        with pytest.raises(ApplicationStateValidationError):
            authorize(self, world_id, conversation_id, turn_id, **(kwargs | {"record_kind": other}))
        assert self.inspect_turn(world_id=world_id, turn_id=turn_id) == before
        from application_state.agent_conversation.native_context import SurfaceNativeContextReceiptV1
        shared = type(before.graph_context_receipt) is SurfaceNativeContextReceiptV1
        # A normalized typed ID may not reuse any existing event family.
        if shared:
            with pytest.raises(ApplicationStateValidationError):
                authorize(self, world_id, conversation_id, turn_id,
                    **(kwargs | {"event_id": str(before.graph_context_execution.events[0].event_id)}))
            assert self.inspect_turn(world_id=world_id, turn_id=turn_id) == before
        result = authorize(self, world_id, conversation_id, turn_id, **kwargs)
        updated_turn, _ = result
        if shared:
            with pytest.raises(ApplicationStateValidationError):
                authorize(self, world_id, conversation_id, turn_id,
                    **(kwargs | {"expected_revision": updated_turn.revision}))
            assert self.inspect_turn(world_id=world_id, turn_id=turn_id) == updated_turn
        return result

    def checked_observe(self, world_id, conversation_id, turn_id, **kwargs):
        before = self.inspect_turn(world_id=world_id, turn_id=turn_id)
        with pytest.raises(ApplicationStateValidationError, match="exact retained read grant"):
            observe(self, world_id, conversation_id, turn_id,
                **(kwargs | {"authorization_event_id": uuid4()}))
        with pytest.raises(ApplicationStateValidationError):
            observe(self, world_id, conversation_id, turn_id,
                **(kwargs | {"reads": (), "unavailable_ids": ("foreign-record",)}))
        # A caller cannot change an assertion grant into a statement observation,
        # or a statement grant into an assertion observation.
        wrong = {"support": {}, "source_body_bytes": 1} if any(
            isinstance(event, NativePlanAssertionReadAuthorizedV1)
            and event.event_id == kwargs["authorization_event_id"]
            for event in before.graph_context_execution.events) else {"assertion": {}, "evidence": (), "spans": ()}
        with pytest.raises(ApplicationStateValidationError):
            observe(self, world_id, conversation_id, turn_id,
                **(kwargs | {"reads": (wrong,), "unavailable_ids": ()}))
        assert self.inspect_turn(world_id=world_id, turn_id=turn_id) == before
        from application_state.agent_conversation.native_context import SurfaceNativeContextReceiptV1
        shared = type(before.graph_context_receipt) is SurfaceNativeContextReceiptV1
        if shared:
            for reused in (before.graph_context_execution.events[0].event_id,
                           kwargs["authorization_event_id"]):
                with pytest.raises(ApplicationStateValidationError, match="event IDs must be unique"):
                    observe(self, world_id, conversation_id, turn_id,
                        **(kwargs | {"event_id": str(reused)}))
                assert self.inspect_turn(world_id=world_id, turn_id=turn_id) == before
        result = observe(self, world_id, conversation_id, turn_id, **kwargs)
        updated_turn, _replayed = result
        if shared:
            with pytest.raises(ApplicationStateValidationError, match="event IDs must be unique"):
                observe(self, world_id, conversation_id, turn_id,
                    **(kwargs | {"expected_revision": updated_turn.revision}))
            assert self.inspect_turn(world_id=world_id, turn_id=turn_id) == updated_turn
        with pytest.raises(ApplicationStateValidationError):
            observe(self, world_id, conversation_id, turn_id,
                **(kwargs | {"expected_revision": updated_turn.revision, "event_id": uuid4()}))
        assert self.inspect_turn(world_id=world_id, turn_id=turn_id) == updated_turn
        calls.append(kwargs["authorization_event_id"])
        return result

    monkeypatch.setattr(AgentConversationService, "authorize_native_read", checked_authorize)
    monkeypatch.setattr(AgentConversationService, "observe_native_read", checked_observe)
    return calls
