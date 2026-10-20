"""Real Build parent/SDK dispatch/APP; mocked transports and synthetic World IO.

These witnesses deliberately stop before the still-unimplemented mixed API DTO.
"""
import json
from hashlib import sha256
from uuid import UUID

import httpx
import httpx2
import psycopg
import pytest

from application_state.agent_conversation import AgentConversationService
from application_state.agent_conversation.rules_authority_policy import rules_capability
from application_state.agent_conversation.rules_authority_reads import MixedCompletedTurnV1
from apps.live_control_server.services.build_jev_harness import BuildJevHarness
from apps.live_control_server.services.rules_build_runtime import QUERY_CHOICE
from tests.test_agent_build_jev_ordinary_harness import (
    DecisionWire, WriterWire, ordinary_case, build_case as _build_case,
)
from tests.test_agent_build_governed_graph import execute
from tests.test_build_jev_estimated_continuations import counter


@pytest.fixture
def build_case(tmp_path, monkeypatch, application_state_dsn):
    return _build_case.__wrapped__(tmp_path, monkeypatch, application_state_dsn)


class RulesDecisionWire(DecisionWire):
    def __init__(self, *, query=True, dsn=None):
        super().__init__()
        self.query, self.dsn = query, dsn

    async def handle_async_request(self, request):
        response = await super().handle_async_request(request)
        body, answer = json.loads(request.content), response.json()
        if self.dsn and "rules_projection" in body["state"]:
            assert_committed_dispatch(self.dsn, request.content)
        if QUERY_CHOICE in body["questions"]:
            choices = body["questions"][QUERY_CHOICE]["criteria"]
            selected = "query:0" if self.query else "none"
            answer["answers"][QUERY_CHOICE] = {"type": "choice", "choice": selected, "confidence": 1,
                "probabilities": {key: float(key == selected) for key in choices}}
        return httpx2.Response(200, request=request, json=answer)


class RulesWriterWire(httpx.AsyncBaseTransport):
    def __init__(self, *, base=True, source_claim=True, dsn=None):
        self.calls = []
        self.base, self.source_claim, self.dsn = base, source_claim, dsn

    async def handle_async_request(self, request):
        self.calls.append(request)
        body = json.loads(request.content)
        packet = json.loads(body["input"])
        if self.dsn:
            assert_committed_dispatch(self.dsn, request.content)
        assert body["text"]["format"]["name"] == "dmb_rules_mixed_answer_v1"
        supports = [sid for op in packet["rules_projection"]["operations"]
            for sid in json.loads(op["packet_json"]).get("emitted_support_ids", [])]
        base_output = None
        if self.base:
            base_output = {"answer_context_status": "source_grounded_partial", "answer_segments": [
                {"kind": "source_passage_claim", "text": "Frank believes the western gate is haunted.",
                 "passage_handles": [packet["opened_passages"][0]["handle"]]}],
                "limitations": ["partial_retrieval"], "requested_detail_gaps": []}
        segments = [{"kind": "rules_claim", "text": "The supplied rules constrain ending movement in an occupied space.",
            "support_ids": supports[:1]}] if supports and self.source_claim else [
            {"kind": "rules_context", "category": "gap", "text": "No supporting travel rules were retrieved."}]
        raw = json.dumps({"schema": "dmb_rules_mixed_answer_v1", "base_output": base_output,
            "rules_segments": segments, "ordered_refs": ([{"domain": "base", "segment_index": None}] if base_output else []) + [
                {"domain": "rules", "segment_index": 0}]})
        return httpx.Response(200, request=request, json={"id": "resp_rules", "object": "response", "created_at": 1,
            "status": "completed", "model": body["model"], "output": [{"type": "message", "id": "msg_rules", "role": "assistant",
                "status": "completed", "content": [{"type": "output_text", "text": raw, "annotations": []}]}],
            "usage": {"input_tokens": 700, "output_tokens": 150, "total_tokens": 850}})


def run_parent(build_case, tmp_path, monkeypatch, *, base=True, question=None, query=True, decision=None, writer=None, prepare=None, dsn=None):
    case, reads = ordinary_case(build_case, monkeypatch)
    source, request, bootstrap = case
    request = request.model_copy(update={"message": question or "What do we know about Frank, and can I end my move in an occupied space?"})
    decision = decision or RulesDecisionWire(query=query, dsn=dsn)
    writer = writer or (RulesWriterWire(base=base, dsn=dsn) if query else WriterWire())
    harness = BuildJevHarness(decision_transport=decision, writer_transport=writer,
        accounting=counter(), rules_capability=rules_capability(graph=True))
    holder = {}
    def internal_response(adapter, **kwargs):
        holder["adapter"] = adapter
        if prepare:
            prepare(adapter)
        original = adapter.authorize_prepared_build_writer
        def checked(prepared):
            from apps.live_control_server.services import build_jev_writer
            assert json.loads(prepared.body) == adapter._build_writer_projection.kwargs()
            build_jev_writer.prepared_view(prepared, adapter._build_writer_projection, budget=adapter._frozen_build_writer_budget())
            allowed = original(prepared)
            assert allowed, f"writer gate: {adapter.failure!r}"
            return allowed
        adapter.authorize_prepared_build_writer = checked
        return harness.execute(adapter)
    harness.execute_response = internal_response
    from apps.live_control_server.routes import agent
    completed = execute((source, request, bootstrap), tmp_path, harness, historical_work_resolver=agent._historical_work_resolver)
    return completed, holder["adapter"], decision, writer, reads


@pytest.mark.parametrize("base", [False, True])
def test_real_build_parent_cited_rules_and_base_commit_reopen(application_state_dsn, build_case, tmp_path, monkeypatch, base):
    completed, adapter, decisions, writer, reads = run_parent(build_case, tmp_path, monkeypatch, base=base, dsn=application_state_dsn)
    assert isinstance(completed, MixedCompletedTurnV1)
    assert completed.base_projection.kind == ("approved" if base else "unclaimed")
    assert completed.accepted_binding.support_table and not completed.accepted_binding.graph_used
    assert len(writer.calls) == 1 and reads == {"graph": 1, "source": 1}
    assert AgentConversationService().inspect_turn(world_id=completed.envelope.world_id, turn_id=completed.envelope.turn_id) == completed
    with psycopg.connect(application_state_dsn) as conn:
        payload = conn.execute("SELECT payload FROM agent.turn_rules_execution WHERE turn_id=%s", (completed.envelope.turn_id,)).fetchone()[0]
    assert payload["state"] == "accepted" and payload["budget_use"]["calls"] == 1
    assert len(payload["supports"]) == 1
    authorizations = [e for e in payload["events"] if e["kind"] == "build_provider_authorized"]
    assert authorizations[-1]["role"] == "writer"
    assert UUID(authorizations[-1]["provider_attempt_id"]) == completed.accepted_binding.producing_provider_attempt_id
    # No duplicate excerpt context in intermediate controllers.
    for request in decisions.calls:
        state = json.loads(request.content)["state"]
        if "rules_projection" in state:
            assert state["rules_projection"]["operations"] == []
    final = json.loads(json.loads(writer.calls[0].content)["input"])
    assert len(final["rules_projection"]["operations"]) == 1
    raw_packet = json.loads(final["rules_projection"]["operations"][0]["packet_json"])
    assert len(raw_packet["support_capsules"]) == 1
    if base:
        assert completed.base_projection.turn.completion.source_citations
        assert "Frank believes" in completed.assistant_text
    assert adapter.failure is None


def assert_committed_dispatch(dsn, raw):
    """A separate connection sees both authorization/inclusion before mock IO."""
    body = json.loads(raw)
    state = body.get("state") or json.loads(body["input"])
    projection = state["rules_projection"]
    with psycopg.connect(dsn) as conn:
        rows = conn.execute("SELECT payload FROM agent.turn_rules_execution").fetchall()
    matches = [p for (p,) in rows if p["scope"]["authorization_id"] == projection["authorization_id"]]
    assert len(matches) == 1
    payload = matches[0]
    auth = [e for e in payload["events"] if e["kind"] == "build_provider_authorized"][-1]
    included = [e for e in payload["events"] if e["kind"] == "build_provider_included"][-1]
    assert auth["request_envelope_sha256"] == included["request_envelope_sha256"] == sha256(raw).hexdigest()
    assert auth["provider_attempt_id"] == included["provider_attempt_id"]
    assert payload["state"] == "active"
    assert not any(e["kind"] == "provider_outcome" and e["provider_attempt_id"] == auth["provider_attempt_id"] for e in payload["events"])


def test_no_rules_choice_finishes_ordinary_and_closes_unused_scope(application_state_dsn, build_case, tmp_path, monkeypatch):
    completed, _, decisions, writer, _ = run_parent(build_case, tmp_path, monkeypatch, query=False, dsn=application_state_dsn)
    assert completed.status == "completed" and not isinstance(completed, MixedCompletedTurnV1)
    assert len(writer.calls) == 1
    with psycopg.connect(application_state_dsn) as conn:
        payload = conn.execute("SELECT payload FROM agent.turn_rules_execution WHERE turn_id=%s", (completed.turn_id,)).fetchone()[0]
    assert payload["state"] == "unused" and payload["budget_use"]["calls"] == 0 and payload["supports"] == {}
    assert "rules_projection" not in json.loads(json.loads(writer.calls[0].content)["input"])


@pytest.mark.parametrize("unavailable", [False, True])
def test_missing_or_unavailable_rules_stays_an_explicit_uncited_gap(application_state_dsn, build_case, tmp_path, monkeypatch, unavailable):
    from apps.live_control_server.services import rules_lookup
    if unavailable:
        def fail(*args, **kwargs):
            raise rules_lookup.RulesCorpusUnavailable("fixture unavailable source")
        monkeypatch.setattr(rules_lookup, "query_rules", fail)
    completed, _, _, writer, _ = run_parent(build_case, tmp_path, monkeypatch, base=False,
        question="How fast can the party travel?", dsn=application_state_dsn)
    assert completed.accepted_binding.support_table == ()
    assert completed.accepted_binding.segment_map[0].domain == "rules_context"
    packet = json.loads(json.loads(json.loads(writer.calls[0].content)["input"])["rules_projection"]["operations"][0]["packet_json"])
    assert packet["status"] == ("unavailable" if unavailable else "no_evidence")
    assert packet["support_capsules"] == []


@pytest.mark.parametrize("failure", ["rules_append", "expired_claim"])
def test_failed_rules_admission_sends_no_controller_or_writer(application_state_dsn, build_case, tmp_path, monkeypatch, failure):
    from application_state.errors import ApplicationStateValidationError
    from generationengine import GenerationEngineError
    decision, writer = RulesDecisionWire(), RulesWriterWire()
    def prepare(adapter):
        if failure == "rules_append":
            def fail(*args, **kwargs):
                raise ApplicationStateValidationError("fixture Rules append failure")
            adapter.service.append_rules_provider_event = fail
        else:
            original = adapter.service.begin_rules_execution
            def begin(*args, **kwargs):
                record = original(*args, **kwargs)
                with psycopg.connect(application_state_dsn) as conn:
                    conn.execute("UPDATE agent.turn SET claim_expires_at=clock_timestamp()-interval '1 second' WHERE turn_id=%s", (record.execution.scope.turn_id,))
                return record
            adapter.service.begin_rules_execution = begin
    with pytest.raises(GenerationEngineError):
        run_parent(build_case, tmp_path, monkeypatch, decision=decision, writer=writer, prepare=prepare)
    assert decision.calls == writer.calls == []
    with psycopg.connect(application_state_dsn) as conn:
        payload = conn.execute("SELECT payload FROM agent.turn_rules_execution").fetchone()[0]
    assert payload["state"] == "active" and payload["events"] == [] and payload["supports"] == {}


def test_sdk_normalization_preserves_the_entire_frozen_mixed_schema():
    from application_state.agent_conversation.rules_authority_output import build_output_format
    from tests.test_rules_authority_output import packet
    from generationengine.utils.schema_utils import make_schema_strict
    schema = build_output_format(packet(), ())["schema"]
    assert make_schema_strict(schema) == schema


def test_never_dispatched_retry_keeps_exact_first_body_and_binds_fresh_attempt(
        application_state_dsn, build_case, tmp_path, monkeypatch):
    from generationengine import GenerationEngineError
    first_body, first_turn = [], []
    decision, writer = RulesDecisionWire(), RulesWriterWire()
    def before_first(adapter):
        original = adapter.authorize
        def capture(view):
            first_body.append(view["payloadJson"])
            return original(view)
        adapter.authorize = capture
        def fail_before_authorization():
            first_turn.append(adapter.fence.turn)
            raise ValueError("fixture pre-authorization interruption")
        adapter._tool_presentation = fail_before_authorization
    with pytest.raises(GenerationEngineError):
        run_parent(build_case, tmp_path, monkeypatch, decision=decision, writer=writer, prepare=before_first)
    assert len(first_body) == len(first_turn) == 1 and not decision.calls and not writer.calls
    with psycopg.connect(application_state_dsn) as conn:
        assert conn.execute("SELECT count(*) FROM agent.turn_rules_execution").fetchone()[0] == 0
        row = conn.execute("SELECT graph_context_execution FROM agent.turn WHERE turn_id=%s", (first_turn[0].turn_id,)).fetchone()[0]
        assert row["events"] == []
        conn.execute("UPDATE agent.turn SET claim_expires_at=clock_timestamp()-interval '1 second' WHERE turn_id=%s", (first_turn[0].turn_id,))
    completed, adapter, retried, final_writer, _ = run_parent(build_case, tmp_path, monkeypatch, dsn=application_state_dsn)
    assert completed.envelope.turn_id == first_turn[0].turn_id
    assert completed.envelope.attempt == first_turn[0].attempt + 1
    assert json.loads(retried.calls[0].content) == json.loads(first_body[0])
    assert sha256(retried.calls[0].content).hexdigest() == sha256(first_body[0].encode()).hexdigest()
    scope = adapter.rules_runtime.record.execution.scope
    assert scope.product_attempt == completed.envelope.attempt
    assert adapter.rules_runtime.record.execution.budget_use.calls == 1
    assert len(final_writer.calls) == 1
