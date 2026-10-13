from hashlib import sha256
from threading import Lock
from types import SimpleNamespace
from uuid import uuid4

import pytest
from pydantic import ValidationError

from application_state.agent_conversation.context_trace import TurnContextTraceV1
from application_state.errors import ApplicationStateValidationError
from apps.live_control_server.services.agent_context_trace_collector import ContextTraceCollector


class Store:
    def __init__(self):
        self.bindings = []
        self.failure = None

    def start_context_trace(self, **binding):
        self.trace = TurnContextTraceV1(
            **{key: value for key, value in binding.items() if key != "expected_revision"},
            execution_start_sequence=0, observations=[],
        )
        return self.trace

    def append_context_trace(self, *, observation, **binding):
        self.bindings.append(binding)
        if self.failure:
            raise self.failure
        self.trace = self.trace.model_copy(update={"observations": [*self.trace.observations, observation]})
        return self.trace

    def mark_context_trace_incomplete(self, *, failure_code, **binding):
        self.trace = self.trace.model_copy(update={"capture_status": "incomplete", "capture_failure_code": failure_code})
        return self.trace

    def list_context_trace_attempts(self, **binding):
        return [self.trace]


def collector():
    store = Store()
    turn = SimpleNamespace(world_id="world", conversation_id=uuid4(), turn_id=uuid4(), revision=4, attempt=1)
    fence = SimpleNamespace(service=store, renewer=SimpleNamespace(_lock=Lock(), _turn=turn))
    return ContextTraceCollector(fence), store, turn


def test_observations_use_current_execution_revision_and_assigned_sequence():
    capture, store, turn = collector()
    capture.observe({"kind": "failure", "code": "graph_denied", "phase": "graph_retrieval"})
    turn.revision = 9
    capture.observe({"kind": "failure", "code": "provider_denied", "phase": "provider"})
    assert [item.sequence for item in store.trace.observations] == [0, 1]
    assert [item["expected_revision"] for item in store.bindings] == [4, 9]


def test_known_capture_rejection_is_explicit_and_does_not_retry_append():
    capture, store, _ = collector()
    store.failure = ApplicationStateValidationError("bounded capture rejected")
    capture.observe({"kind": "failure", "code": "graph_denied", "phase": "graph_retrieval"})
    capture.observe({"kind": "failure", "code": "provider_denied", "phase": "provider"})
    assert store.trace.capture_status == "incomplete"
    assert store.trace.capture_failure_code == "trace_observation_rejected"
    assert len(store.bindings) == 1


def test_transport_failure_propagates_without_retry_or_marking_safe_cap_failure():
    capture, store, _ = collector()
    store.failure = ConnectionError("database unavailable")
    with pytest.raises(ConnectionError):
        capture.observe({"kind": "failure", "code": "graph_denied", "phase": "graph_retrieval"})
    assert store.trace.capture_status == "recording"
    assert len(store.bindings) == 1


def source_event(text):
    receipt = SimpleNamespace(source_read_id="read", anchor_id="anchor", evidence_ref_id="evidence",
                              source_artifact_id="artifact", source_revision_id="revision",
                              line_start=1, line_end=2, outcome="enough", returned_chars=len(text),
                              content_sha256=sha256(text.encode()).hexdigest())
    return SimpleNamespace(event_id=uuid4(), read_call_id=uuid4(), receipts=[receipt])


def test_exact_source_snapshot_is_not_appended_separately_from_receipt():
    capture, store, _ = collector()
    event = source_event("Frank and Sara operate the Rocky Talkie.")
    passages = capture.source_passages(event, [{"content": "Frank and Sara operate the Rocky Talkie."}],
                                      world_id="world", graph_revision="graph-revision")
    assert passages[0].source_read_event_id == event.event_id
    assert passages[0].content_sha256 == event.receipts[0].content_sha256
    assert store.trace.observations == []
    store.trace = store.trace.model_copy(update={"observations": passages})
    capture.refresh_after_source_capture()
    capture.observe({"kind": "failure", "code": "source_denied", "phase": "source_read"})
    assert store.trace.observations[-1].sequence == 1


def test_changed_source_bytes_cannot_be_captured():
    capture, _, _ = collector()
    with pytest.raises(ValidationError):
        capture.source_passages(source_event("recorded"), [{"content": "tampered"}],
                                world_id="world", graph_revision="graph-revision")


def test_incomplete_capture_cannot_claim_new_source_bytes():
    capture, _, _ = collector()
    capture.mark_incomplete("trace_observation_rejected")
    with pytest.raises(ApplicationStateValidationError):
        capture.source_passages(source_event("recorded"), [{"content": "recorded"}],
                                world_id="world", graph_revision="graph-revision")


def test_usage_keeps_reported_actuals_separate_from_request_accounting():
    capture, store, _ = collector()
    capture.provider_usage([{
        "provider": "openai-api", "requested_model": "requested", "response_model": "actual",
        "status": "ok", "duration_ms": 12.5,
        "request_summary": {"input_tokens": 90000},
        "usage": {"status": "reported", "input_tokens": 42, "output_tokens": 7},
    }])
    observed = store.trace.observations[0]
    assert observed.model == "actual"
    assert (observed.input_tokens, observed.output_tokens) == (42, 7)
    assert observed.input_upper_bound is None
    assert observed.duration_ms == 12.5


@pytest.mark.parametrize("usage", [
    {"status": "unavailable", "input_tokens": 90000},
    {"status": "reported", "input_tokens": True, "output_tokens": -1},
    {},
])
def test_unknown_or_invalid_usage_is_not_presented_as_actual(usage):
    capture, store, _ = collector()
    capture.provider_usage([{"provider": "openai-api", "requested_model": "model",
                             "status": "error", "usage": usage}])
    observed = store.trace.observations[0]
    assert observed.input_tokens is None and observed.output_tokens is None
    assert observed.outcome == "failed"


def test_missing_model_identity_marks_trace_incomplete_without_inventing_model():
    capture, store, _ = collector()
    capture.provider_usage([{"status": "ok", "usage": {"status": "reported", "input_tokens": 42}}])
    assert store.trace.capture_failure_code == "provider_identity_unavailable"
    assert store.trace.observations == []
