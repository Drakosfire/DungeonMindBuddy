from hashlib import sha256
from threading import Lock
from types import SimpleNamespace
from uuid import uuid4

import pytest
from pydantic import ValidationError

from application_state.agent_conversation.context_trace import TurnContextTraceV1
from application_state.errors import ApplicationStateConflictError, ApplicationStateValidationError
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
        if self.trace.capture_status == "incomplete" and self.trace.capture_failure_code != failure_code:
            raise ApplicationStateConflictError("first capture marker is immutable")
        self.trace = self.trace.model_copy(update={"capture_status": "incomplete", "capture_failure_code": failure_code})
        return self.trace

    def list_context_trace_attempts(self, **binding):
        return [self.trace]


def collector():
    store = Store()
    turn = SimpleNamespace(world_id="world", conversation_id=uuid4(), turn_id=uuid4(), revision=4, attempt=1, sequence=2)
    fence = SimpleNamespace(service=store, turn=turn, renewer=SimpleNamespace(_lock=Lock(), _turn=turn))
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


def test_trace_collector_accepts_more_than_eight_passages_within_byte_and_character_bounds():
    capture, store, _ = collector()
    passages = []
    for index in range(9):
        text = f"bounded source passage {index}"
        event = source_event(text)
        passages.extend(capture.source_passages(
            event, [{"content": text}], world_id="world",
            graph_revision="graph-revision",
        ))
    assert len(passages) == 9
    assert sum(item.returned_chars for item in passages) < 96_000
    assert store.trace.capture_status == "recording"
    assert capture._capture_exhausted() is False


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


def test_producer_observations_survive_real_postgres_terminal_failure(application_state_dsn):
    from time import monotonic
    from application_state.agent_conversation.types import TurnFailure
    from apps.live_control_server.services.agent_turn_service import _ClaimFence
    from tests.application_state.test_agent_conversation_context_trace_postgres import _setup_turn

    service, turn, _, trace = _setup_turn()
    fence = _ClaimFence(service, turn)
    capture = ContextTraceCollector.__new__(ContextTraceCollector)
    capture.fence, capture.trace, capture.started = fence, trace, monotonic()
    capture.provider_attempts_by_request = {}
    capture.ambiguous_provider_requests = set()
    try:
        capture.provider_usage([{"provider": "openai-api", "response_model": "test-model",
                                "status": "ok", "duration_ms": 12,
                                "usage": {"status": "reported", "input_tokens": 42, "output_tokens": 7}}])
        capture.observe({"kind": "failure", "phase": "delivery", "code": "synthetic_delivery_failure"})
        assert fence.turn.revision == turn.revision
    finally:
        current, error = fence.stop()
        assert error is None
    service.fail_turn(TurnFailure(world_id=current.world_id, conversation_id=current.conversation_id,
                                 turn_id=current.turn_id, expected_revision=current.revision,
                                 failure_code="synthetic_delivery_failure"))
    saved = service.list_context_trace_attempts(world_id=turn.world_id, turn_id=turn.turn_id)[0]
    assert saved.terminal_status == "failed"
    assert saved.capture_status == "complete"
    assert saved.observations[0].input_tokens == 42
    assert saved.observations[0].output_tokens == 7
    assert saved.observations[1].code == "synthetic_delivery_failure"


@pytest.mark.parametrize("reason,code", [
    ("trace exceeds the explicit 1 MiB per-attempt ceiling", "trace_size_limit"),
    ("captured source passages exceed the 96,000 character turn ceiling", "source_character_capture_limit"),
])
def test_known_source_cap_retries_only_same_receipt_without_releasing_bytes(reason, code):
    capture, store, turn = collector()
    event = source_event("source text")
    appends = []
    def append(method, name, received, **options):
        appends.append((method, name, received, options))
        if options:
            raise ApplicationStateValidationError(reason)
        return turn, True
    capture.fence.append = append
    updated, fresh, may_release = capture.persist_source_receipt(
        event, [{"content": "source text"}], world_id="world", graph_revision="revision",
    )
    assert updated is turn and fresh is True and may_release is False
    assert len(appends) == 2
    assert appends[0][2] is appends[1][2] is event
    assert appends[1][3] == {}
    assert store.trace.capture_failure_code == code


def test_owned_pydantic_root_cap_is_recognized_without_matching_arbitrary_wrapped_messages():
    from apps.live_control_server.services.agent_context_trace_collector import _source_capture_limit
    owned = ValidationError.from_exception_data("TurnContextTraceV1", [{"type": "value_error", "loc": (),
        "input": {}, "ctx": {"error": ValueError("trace exceeds the explicit 1 MiB per-attempt ceiling")}}])
    error = ApplicationStateValidationError(str(owned))
    error.__cause__ = owned
    assert _source_capture_limit(error) == "trace_size_limit"
    foreign = ValidationError.from_exception_data("ForeignGraphReceipt", [{"type": "value_error", "loc": (),
        "input": {}, "ctx": {"error": ValueError("trace exceeds the explicit 1 MiB per-attempt ceiling")}}])
    error.__cause__ = foreign
    assert _source_capture_limit(error) is None


@pytest.mark.parametrize("failure", [
    ConnectionError("unknown write disposition"),
    ApplicationStateValidationError("source passage trace belongs to a different World"),
])
def test_uncertain_or_identity_source_capture_failure_has_no_receipt_retry(failure):
    capture, store, _ = collector()
    appends = []
    def append(*args, **kwargs):
        appends.append((args, kwargs))
        raise failure
    capture.fence.append = append
    with pytest.raises(type(failure)):
        capture.persist_source_receipt(source_event("source text"), [{"content": "source text"}],
                                       world_id="world", graph_revision="revision")
    assert len(appends) == 1
    assert store.trace.capture_status == "recording"


def test_parent_tool_denial_records_safe_failure_without_evidence_authority():
    import json
    from apps.live_control_server.services.agent_turn_service import _PolicyExecutionAdapter
    capture, store, _ = collector()
    adapter = _PolicyExecutionAdapter.__new__(_PolicyExecutionAdapter)
    adapter.context_capture = capture
    adapter.denied_tool_payloads = {}
    denied = adapter._denied_tool_result("read_graph_source", "source_anchor_not_admitted", 403,
                                        "Source could not be admitted.", arguments={"anchorIds": ["private-anchor-42"]})
    assert json.loads(denied["resultJson"])["code"] == "source_anchor_not_admitted"
    observed = store.trace.observations[0]
    assert observed.kind == "failure" and observed.phase == "source_read"
    assert observed.code == "source_anchor_not_admitted"
    assert "private-anchor-42" not in observed.model_dump_json()
    assert "content" not in observed.model_dump()


def compaction_fixture():
    import json
    from apps.live_control_server.services.agent_context_compaction_report import compaction_report
    from apps.live_control_server.services.agent_conversation_context import compact_conversation_context
    text = "Frank and Sara operate the Rocky Talkie."
    messages = [
        {"role": "user", "content": "Tell me about Mirathorn."},
        {"role": "tool", "content": json.dumps({"schema": "dmb_world_graph_source_anchor_read_v1",
            "outcome": "enough", "anchorId": "anchor", "evidenceRefId": "evidence", "sourceArtifactId": "artifact",
            "snapshot": {"worldId": "native-world", "revisionId": "graph-revision"}, "content": text})},
        {"role": "assistant", "content": "Frank and Sara are operators."},
    ]
    return text, compaction_report(messages, compact_conversation_context(messages))


@pytest.mark.parametrize("session_hint", [False, True])
def test_compaction_matches_observed_bytes_to_exact_prior_trace_and_keeps_only_routes_after(session_hint):
    from application_state.agent_conversation.context_trace import TraceSourcePassage
    capture, store, turn = collector()
    text, report = compaction_fixture()
    prior_turn = SimpleNamespace(turn_id=uuid4(), sequence=1)
    event = source_event(text)
    passage = TraceSourcePassage(**capture.source_passages(event, [{"content": text}], world_id="world",
                                                         graph_revision="graph-revision")[0].model_dump())
    prior = store.trace.model_copy(update={"turn_id": prior_turn.turn_id, "trace_id": uuid4(), "observations": [passage]})
    prior_turns, prior_traces = [prior_turn], {prior_turn.turn_id: prior}
    if session_hint:
        turn.sequence = 3
        report.prior_sources[0].retrieval_session_id = "original-session"
        prior_turn.graph_context_execution = SimpleNamespace(events=[SimpleNamespace(
            kind="source_read_authorized_v2", read_call_id=passage.read_call_id, retrieval_session_id="original-session")])
        other_turn = SimpleNamespace(turn_id=uuid4(), sequence=2)
        other_passage = passage.model_copy(update={"read_call_id": uuid4(), "source_read_event_id": uuid4()})
        other_turn.graph_context_execution = SimpleNamespace(events=[SimpleNamespace(
            kind="source_read_authorized_v2", read_call_id=other_passage.read_call_id, retrieval_session_id="other-session")])
        other_trace = prior.model_copy(update={"trace_id": uuid4(), "turn_id": other_turn.turn_id, "observations": [other_passage]})
        prior_turns.append(other_turn)
        prior_traces[other_turn.turn_id] = other_trace
    store.list_turns = lambda *args, **kwargs: prior_turns
    store.list_context_trace_attempts = lambda **kwargs: [prior_traces[kwargs["turn_id"]]]
    capture.compaction(report, graph_world_id="native-world")
    pair = [o for o in capture.trace.observations if o.kind == "context_snapshot"]
    assert pair[0].snapshot_kind == "compaction_input"
    assert pair[1].snapshot_kind == "compaction_output"
    assert pair[0].comparison_id == pair[1].comparison_id is not None
    before, after = store.trace.observations[:2]
    remembered = next(item for item in before.materials if item.role == "source")
    ref = remembered.historical_source_reads[0]
    assert ref.trace_id == prior.trace_id and ref.turn_id == prior_turn.turn_id
    assert ref.content_sha256 == sha256(text.encode()).hexdigest()
    assert remembered.source_read_event_id is None and remembered.source_reads == []
    assert not any(item.role == "source" and item.state == "model_context" for item in after.materials)
    route = next(item for item in after.materials if item.state == "retrieval_route")
    assert route.route.anchor_id == "anchor" and route.route.world_id == turn.world_id


def test_missing_historical_capture_is_explicit_without_rewriting_history_or_blocking_new_reads():
    capture, store, _ = collector()
    text, report = compaction_fixture()
    original = report.model_dump_json()
    store.list_turns = lambda *args, **kwargs: []
    capture.compaction(report, graph_world_id="native-world")
    pair = [o for o in capture.trace.observations if o.kind == "context_snapshot"]
    assert pair[0].snapshot_kind == "compaction_input"
    assert pair[1].snapshot_kind == "compaction_output"
    assert pair[0].comparison_id == pair[1].comparison_id is not None
    assert store.trace.capture_failure_code == "historical_source_unavailable"
    assert report.model_dump_json() == original
    assert not any(item.role == "source" for item in store.trace.observations[0].materials)
    assert capture.source_passages(source_event(text), [{"content": text}], world_id="world", graph_revision="revision")


def test_provider_context_distinguishes_included_current_sources_from_other_reads():
    capture, store, _ = collector()
    event = source_event("Included passage.")
    unrelated = source_event("Other retrieved passage.")
    first = capture.source_passages(event, [{"content": "Included passage."}], world_id="world", graph_revision="revision")[0]
    second = capture.source_passages(unrelated, [{"content": "Other retrieved passage."}], world_id="world", graph_revision="revision")[0]
    store.trace = store.trace.model_copy(update={"observations": [first, second.model_copy(update={"sequence": 1})]})
    capture.refresh_after_source_capture()
    capture.provider_context("Tell me about Mirathorn.", [event])
    assert capture.trace.observations[-1].snapshot_kind == "provider_input"
    snapshot = store.trace.observations[-1]
    sources = [item for item in snapshot.materials if item.role == "source"]
    assert len(sources) == 1 and sources[0].source_read_event_id == event.event_id
    assert snapshot.materials[0].text == "Tell me about Mirathorn."
    capture.answer_context("The evidence names Frank and Sara.")
    assert capture.trace.observations[-1].snapshot_kind == "validated_answer"
    after = store.trace.observations[-1]
    assert after.stage == "after"
    assert after.materials[-1].text == "The evidence names Frank and Sara."
    assert [item.source_read_event_id for item in after.materials if item.role == "source"] == [event.event_id]


def test_provider_context_rejects_uncaptured_source_inclusion():
    capture, store, _ = collector()
    with pytest.raises(ApplicationStateValidationError, match="no exact captured passage"):
        capture.provider_context("Question", [source_event("Uncaptured passage.")])
    assert store.trace.observations == []


def test_retained_knowledge_and_routes_are_present_only_if_the_actual_request_contains_them():
    import json
    from apps.live_control_server.services.agent_conversation_context import ROUTE_MARKER
    capture, store, _ = collector()
    _, report = compaction_fixture()
    store.list_turns = lambda *args, **kwargs: []
    capture.compaction(report, graph_world_id="native-world")
    pair = [o for o in capture.trace.observations if o.kind == "context_snapshot"]
    assert pair[0].snapshot_kind == "compaction_input"
    assert pair[1].snapshot_kind == "compaction_output"
    assert pair[0].comparison_id == pair[1].comparison_id is not None
    capture.provider_context("Who are its operators?", [], body={"input": [
        {"role": item.role, "content": [{"type": "input_text", "text": item.text}]} for item in report.after_visible
    ]})
    snapshot = store.trace.observations[-1]
    assert any(item.text == "Frank and Sara are operators." for item in snapshot.materials)
    assert not any(item.state == "retrieval_route" for item in snapshot.materials)
    capture.provider_context("Who are its operators?", [], body={"input": [{"role": "user", "content":
        ROUTE_MARKER + json.dumps(report.routes, ensure_ascii=False, separators=(",", ":"))}]})
    assert any(item.state == "retrieval_route" for item in store.trace.observations[-1].materials)
    capture.provider_context("Who are its operators?", [], body={"input": []})
    assert len(store.trace.observations[-1].materials) == 1


def test_later_gap_preserves_first_marker_and_capacity_remains_independent():
    capture, store, _ = collector()
    capture.mark_incomplete("historical_source_unavailable")
    capture.mark_incomplete("recap_context_capture_unavailable")
    assert store.trace.capture_failure_code == "historical_source_unavailable"
    assert store.trace.observations[-1].code == "recap_context_capture_unavailable"
    assert not capture._capture_exhausted()
    capture.mark_incomplete("trace_size_limit")
    assert store.trace.capture_failure_code == "historical_source_unavailable"
    assert store.trace.observations[-1].code == "trace_size_limit"
    assert capture._capture_exhausted()


def answer_capture_case():
    capture, store, turn = collector()
    producer = uuid4()
    turn.graph_context_execution = SimpleNamespace(events=[
        SimpleNamespace(kind='provider_attempt_authorized_v3', provider_attempt_id=producer),
        SimpleNamespace(kind='provider_outcome', provider_attempt_id=producer, outcome='response_received')])
    turn.graph_context_receipt = SimpleNamespace(context_receipt_sha256='c' * 64)
    capture.bound_context_receipt_sha256 = 'c' * 64
    return capture, store, turn, producer


def test_unvalidated_answer_capture_exact_idempotent_and_not_authority():
    capture, store, turn, producer = answer_capture_case()
    answer = '{"citation_map":{"broken":[]},"text":"Ω quoted draft"}'
    capture.answer_draft(answer, producing_provider_attempt_id=producer)
    assert capture.trace.observations[-1].snapshot_kind == "provider_response"
    capture.answer_draft(answer, producing_provider_attempt_id=producer)
    assert capture.trace.observations[-1].snapshot_kind == "provider_response"
    snapshot, = store.trace.observations
    item, = snapshot.materials
    assert item.text == answer and item.role == 'assistant'
    assert item.item_id == f'unvalidated-provider-answer:{producer}:{"c" * 64}'
    assert item.source_reads == [] and item.route is None
    assert len(store.bindings) == 1
    with pytest.raises(ApplicationStateValidationError, match='different bytes'):
        capture.answer_draft(answer + ' ', producing_provider_attempt_id=producer)
    assert store.trace.observations[0].materials[0].text == answer
    assert turn.graph_context_execution.events[-1].outcome == 'response_received'


@pytest.mark.parametrize('change', ['wrong', 'earlier', 'no-response'])
def test_answer_draft_rejects_foreign_or_nonproducing_attempt(change):
    capture, store, turn, producer = answer_capture_case()
    if change == 'wrong':
        producer = uuid4()
    elif change == 'earlier':
        turn.graph_context_execution.events.append(SimpleNamespace(
            kind='provider_attempt_authorized_v3', provider_attempt_id=uuid4()))
    else:
        turn.graph_context_execution.events.pop()
    with pytest.raises(ApplicationStateValidationError, match='producing provider response'):
        capture.answer_draft('draft', producing_provider_attempt_id=producer)
    assert store.trace.observations == []


@pytest.mark.parametrize('problem', ['bytes', 'aggregate', 'events', 'encoding'])
def test_answer_draft_omissions_are_explicit_and_never_prefixes(problem):
    capture, store, _, producer = answer_capture_case()
    text = 'exact draft'
    if problem == 'bytes':
        text = 'x' * 1_048_576
    elif problem == 'aggregate':
        capture.observe({'kind':'context_snapshot','stage':'before','materials':[
            {'item_id':'retained','state':'model_context','role':'assistant','text':'x'*1_040_000}]})
        text = 'x' * 10_000
    elif problem == 'events':
        # The real APP ceiling is exercised through this collector preflight;
        # fake store avoids 2048 irrelevant database roundtrips.
        item = SimpleNamespace(kind='failure')
        capture.trace = capture.trace.model_copy(update={'observations':[item]*2048})
    else:
        text = '\ud800'
    capture.answer_draft(text, producing_provider_attempt_id=producer)
    assert capture.trace.capture_status == 'incomplete'
    expected = 'size_limit' if problem in {'bytes','aggregate'} else ('event_limit' if problem == 'events' else 'encoding_unavailable')
    assert capture.trace.capture_failure_code == 'answer_draft_' + expected
    assert not any(getattr(m,'item_id','').startswith('unvalidated-provider-answer:')
        for o in capture.trace.observations if o.kind == 'context_snapshot' for m in o.materials)


def test_answer_draft_persistence_failure_propagates_without_retry():
    capture, store, _, producer = answer_capture_case()
    store.failure = ApplicationStateConflictError('fenced')
    with pytest.raises(ApplicationStateConflictError):
        capture.answer_draft('draft', producing_provider_attempt_id=producer)
    assert len(store.bindings) == 1 and store.trace.observations == []


@pytest.mark.parametrize('change',['receipt','turn','world','conversation'])
def test_answer_draft_cannot_rebind_frozen_trace_context(change):
    capture, store, turn, producer = answer_capture_case()
    if change == 'receipt':
        turn.graph_context_receipt.context_receipt_sha256 = 'd' * 64
    elif change == 'world':
        turn.world_id = 'other'
    elif change == 'turn':
        turn.turn_id = uuid4()
    else:
        turn.conversation_id = uuid4()
    with pytest.raises(ApplicationStateValidationError, match='frozen trace context'):
        capture.answer_draft('draft',producing_provider_attempt_id=producer)
    assert store.trace.observations == []


def test_prompt_capture_is_strict_even_when_trace_append_returns_only_incomplete(tmp_path, monkeypatch):
    monkeypatch.setenv("DMB_ARTIFACT_DATA_ROOT", str(tmp_path))
    capture, store, _ = collector()
    authorization = SimpleNamespace(provider_attempt_id=uuid4(), provider="openai", model="synthetic",
        api_mode="responses", serializer_version="serializer")
    view = {"payloadJson":"{}", "payloadSha256":sha256(b"{}").hexdigest(), "payloadUtf8Bytes":2}
    capture.capture_prompt(view, authorization)
    assert store.trace.observations[0].kind == "prompt_reference"
    store.append_context_trace = lambda **_:store.trace
    with pytest.raises(ApplicationStateValidationError, match="not durably captured"):
        capture.capture_prompt(view, authorization)


def test_usage_correlates_exact_requests_with_same_model_even_when_reported_out_of_order():
    capture, store, _ = collector()
    first, second = uuid4(), uuid4()
    capture.bind_provider_request("sdk-first", first)
    capture.bind_provider_request("sdk-second", second)
    capture.provider_usage([
        {"provider": "openai-api", "requested_model": "same", "runtime_api_request_id": request,
         "status": status, "duration_ms": 20, "usage": {"status": "reported", "input_tokens": tokens, "output_tokens": 7}}
        for request, status, tokens in [("sdk-second", "error", 52), ("sdk-first", "ok", 42)]
    ])
    assert [item.provider_attempt_id for item in store.trace.observations] == [second, first]
    assert [item.input_tokens for item in store.trace.observations] == [52, 42]
    assert [item.outcome for item in store.trace.observations] == ["failed", "response_received"]


@pytest.mark.parametrize("request_id", [None, "", "missing", [], True])
def test_usage_never_guesses_unavailable_request_identity(request_id):
    capture, store, _ = collector()
    capture.bind_provider_request("known", uuid4())
    capture.provider_usage([{"provider": "openai-api", "requested_model": "same", "runtime_api_request_id": request_id,
        "status": "ok", "usage": {"status": "reported", "input_tokens": 42}}])
    assert store.trace.observations[0].provider_attempt_id is None
    assert store.trace.observations[0].input_tokens == 42


def test_conflicting_request_identity_is_never_correlated_again():
    capture, store, _ = collector()
    first, second = uuid4(), uuid4()
    capture.bind_provider_request("same", first)
    capture.bind_provider_request("same", first)
    capture.bind_provider_request("same", second)
    capture.bind_provider_request("same", first)
    capture.provider_usage([{"provider": "openai-api", "requested_model": "same", "runtime_api_request_id": "same", "status": "ok"}])
    assert store.trace.observations[0].provider_attempt_id is None


@pytest.mark.parametrize("title", ["Longmont C2 · Session 24", "Edge — Café 中文"])
def test_source_capture_retains_registered_title_without_changing_evidence(title):
    capture, store, _ = collector()
    text = "Exact source passage."
    event = source_event(text)
    passage = capture.source_passages(event, [{"content": text, "sourceName": title}],
        world_id="world", graph_revision="revision")[0]
    assert passage.source_name == title
    assert passage.source_artifact_id == event.receipts[0].source_artifact_id
    assert passage.content_sha256 == event.receipts[0].content_sha256
    assert passage.text == text
    assert store.trace.observations == []


@pytest.mark.parametrize("title", [None, "", "  ", 42, {"name": "untrusted shape"}])
def test_source_capture_does_not_fabricate_unavailable_names(title):
    capture, _, _ = collector()
    passage = capture.source_passages(source_event("Exact text"), [{"content": "Exact text", "sourceName": title}],
        world_id="world", graph_revision="revision")[0]
    assert passage.source_name is None

def test_snapshot_purpose_is_explicit_and_historical_serialization_unchanged():
    from application_state.agent_conversation.context_trace import TraceContextSnapshot
    from pydantic import ValidationError
    old = dict(kind="context_snapshot", stage="before", sequence=0, elapsed_ms=0.0, materials=[])
    assert TraceContextSnapshot.model_validate(old).model_dump(mode="json") == old
    with pytest.raises(ValidationError, match="comparison identity"):
        TraceContextSnapshot.model_validate({**old, "snapshot_kind": "compaction_input"})
    with pytest.raises(ValidationError, match="captured purpose"):
        TraceContextSnapshot.model_validate({**old, "snapshot_kind": "provider_response"})


def test_authored_trace_uses_exact_app_event_and_preserves_known_capture_failure_marker():
    from tests.test_agent_context_trace_types import _authored_trace_fixture
    capture, store, _ = collector()
    event, _, _ = _authored_trace_fixture()
    capture.authored_reference(event)
    observed = store.trace.observations[0]
    assert observed.kind == 'authored_graph_reference_v1'
    assert observed.execution_event == event
    store.failure = ApplicationStateValidationError('trace capture rejected')
    capture.authored_reference(event)
    assert store.trace.capture_status == 'incomplete'
    assert store.trace.capture_failure_code == 'trace_observation_rejected'
    assert store.trace.observations == [observed]
