"""Real Build parent/SDK dispatch/APP; mocked transports and synthetic World IO.

Includes internal completion and the actual mixed API response/replay projection.
"""
import json
from hashlib import sha256
from uuid import UUID

import httpx
import httpx2
import psycopg
import pytest

from application_state.agent_conversation import AgentConversationService
from application_state.agent_conversation.rules_authority_reads import MixedCompletedTurnV1
from apps.live_control_server.services.build_jev_runtime import PreparedBuildJevRuntime
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


def run_parent(build_case, tmp_path, monkeypatch, *, base=True, question=None, query=True, decision=None, writer=None, prepare=None, dsn=None, api_response=False):
    case, reads = ordinary_case(build_case, monkeypatch)
    source, request, bootstrap = case
    request = request.model_copy(update={"message": question or "What do we know about Frank, and can I end my move in an occupied space?"})
    decision = decision or RulesDecisionWire(query=query, dsn=dsn)
    writer = writer or (RulesWriterWire(base=base, dsn=dsn) if query else WriterWire())
    harness = PreparedBuildJevRuntime(accounting=counter(), unavailable_reason=None).create()
    harness.decision_transport, harness.writer_transport = decision, writer
    holder = {}
    original_response = harness.execute_response
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
        return original_response(adapter, **kwargs) if api_response else harness.execute(adapter)
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
    traces = AgentConversationService().list_context_trace_attempts(world_id=completed.envelope.world_id, turn_id=completed.envelope.turn_id)
    raw_outputs = [m for trace in traces for o in trace.observations if o.kind == "context_snapshot"
                   for m in o.materials if m.item_id.startswith("unvalidated-") and m.role == "assistant"
                   and m.text and '"dmb_rules_mixed_answer_v1"' in m.text]
    assert len(raw_outputs) == 1
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


@pytest.mark.parametrize("failure", [None, "query_rules", "admitted_bundle"])
def test_missing_or_unavailable_rules_stays_an_explicit_uncited_gap(application_state_dsn, build_case, tmp_path, monkeypatch, failure):
    from apps.live_control_server.services import rules_lookup
    if failure:
        def fail(*args, **kwargs):
            raise rules_lookup.RulesCorpusUnavailable("fixture unavailable source")
        monkeypatch.setattr(rules_lookup, failure, fail)
    completed, _, _, writer, _ = run_parent(build_case, tmp_path, monkeypatch, base=False,
        question="How fast can the party travel?", dsn=application_state_dsn)
    assert completed.accepted_binding.support_table == ()
    assert completed.accepted_binding.segment_map[0].domain == "rules_context"
    packet = json.loads(json.loads(json.loads(writer.calls[0].content)["input"])["rules_projection"]["operations"][0]["packet_json"])
    assert packet["status"] == ("unavailable" if failure else "no_evidence")
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


@pytest.mark.parametrize("base", [False, True])
def test_next_real_build_turn_uses_full_mixed_history_as_reference_only(
    application_state_dsn, build_case, tmp_path, monkeypatch, base,
):
    from uuid import uuid4

    first, _, _, _, _ = run_parent(build_case, tmp_path, monkeypatch, base=base)
    source, request, bootstrap = build_case
    next_case = source, request.model_copy(update={"turn_id": str(uuid4())}), bootstrap
    second, _, decisions, writer, _ = run_parent(
        next_case, tmp_path, monkeypatch, query=False,
        question="Discuss the previous answer without changing the page.",
    )
    assert second.status == "completed"
    first_body = json.loads(decisions.calls[0].content)
    interaction = first_body["state"]["decision"]["state"]["interaction"]
    assert interaction["history"] == [{
        "turn_id": str(first.envelope.turn_id),
        "user": first.envelope.user_text,
        "assistant": first.assistant_text,
        "user_sha256": sha256(first.envelope.user_text.encode()).hexdigest(),
        "assistant_sha256": sha256(first.assistant_text.encode()).hexdigest(),
    }]
    assert interaction["history_policy"] == "newest_complete_pairs_up_to_6_and_12000_chars_reference_only_v1"
    # Historical Rules text carries no producing support capsules or new lookup.
    assert "rules_projection" not in json.loads(json.loads(writer.calls[0].content)["input"])
    with psycopg.connect(application_state_dsn) as conn:
        payload = conn.execute("SELECT payload FROM agent.turn_rules_execution WHERE turn_id=%s", (second.turn_id,)).fetchone()[0]
    assert payload["state"] == "unused" and payload["supports"] == {}


@pytest.mark.parametrize("base", [False, True])
def test_real_build_mixed_api_response_and_replay_without_current_reads(
    application_state_dsn, build_case, tmp_path, monkeypatch, base,
):
    from apps.live_control_server.models.agent_turn import AgentRulesTurnResponseV1
    from apps.live_control_server.services.agent_turn_service import execute_agent_turn, AgentTurnServiceError
    from apps.live_control_server.services.hermes_session_store import HermesSessionPointerStore

    response, adapter, decisions, writer, _ = run_parent(
        build_case, tmp_path, monkeypatch, base=base, api_response=True)
    assert isinstance(response, AgentRulesTurnResponseV1)
    binding = response.rules_context.accepted_binding
    stored = AgentConversationService().inspect_turn(world_id=binding.world_id, turn_id=binding.turn_id)
    assert response.answer.text == stored.assistant_text
    assert response.answer.graph_grounded == binding.graph_used
    assert (response.rules_context.base_context is not None) == base
    assert (response.rules_context.unclaimed_context is not None) != base
    if base:
        assert not response.rules_context.base_context.delivery_replay
    else:
        assert not response.rules_context.unclaimed_context.delivery_replay
        assert response.rules_context.unclaimed_context.receipt == stored.base_projection.graph_context_receipt
    initial_calls = len(decisions.calls), len(writer.calls)
    def forbidden(*args, **kwargs):
        pytest.fail("A completed mixed replay must not resolve current work, graph, corpus or runtime")
    from apps.live_control_server.services import rules_lookup
    monkeypatch.setattr(rules_lookup, "admitted_bundle", forbidden)
    replay = execute_agent_turn(adapter.request, root=tmp_path,
        pointer_store=HermesSessionPointerStore(tmp_path / "mixed-replay"),
        owner_resolver=lambda _: {"kind": "world", "id": binding.world_id},
        work_resolver=forbidden, graph_resolver=forbidden, runtime_factory=forbidden,
        conversation_service=AgentConversationService())
    assert isinstance(replay, AgentRulesTurnResponseV1)
    assert replay.answer.text == response.answer.text
    assert replay.rules_context.accepted_binding == binding
    assert replay.answer.trace["usage"]["model_call_count"] == 0
    if base:
        assert replay.rules_context.base_context.delivery_replay
    else:
        assert replay.rules_context.unclaimed_context.delivery_replay
        assert replay.rules_context.unclaimed_context.receipt == response.rules_context.unclaimed_context.receipt
    assert (len(decisions.calls), len(writer.calls)) == initial_calls
    # Exercise the mounted native route's JSON serialization and auth boundary.
    import asyncio
    from fastapi import FastAPI
    from apps.live_control_server.routes import agent
    token = "mixed-replay-operator-" * 2
    monkeypatch.setenv("DMB_AGENT_GRAPH_AUTH_MODE", "local_operator")
    monkeypatch.setenv("DMB_AGENT_GRAPH_AUTH_ENVIRONMENT", "local")
    monkeypatch.setenv("DMB_AGENT_GRAPH_LOCAL_OPERATOR_TOKEN", token)
    monkeypatch.setattr(agent, "repo_root", lambda: tmp_path)
    monkeypatch.setattr(agent, "session_dir", lambda: tmp_path / "mixed-route")
    monkeypatch.setattr(agent, "_owner_resolver", lambda _: {"kind": "world", "id": binding.world_id})
    monkeypatch.setattr(agent, "_work_resolver", forbidden)
    monkeypatch.setattr(agent, "_graph_resolver", forbidden)
    app = FastAPI()
    app.state.agent_conversation_service = AgentConversationService()
    app.include_router(agent.router, prefix="/api/live")
    async def post():
        async with httpx.AsyncClient(transport=httpx.ASGITransport(app=app, client=("127.0.0.1", 1234)), base_url="http://test") as client:
            return await client.post("/api/live/agent/turn", json=adapter.request.model_dump(mode="json", by_alias=True),
                headers={"Authorization": f"Bearer {token}"})
    mounted = asyncio.run(post())
    assert mounted.status_code == 200, mounted.text
    projected = AgentRulesTurnResponseV1.model_validate_json(mounted.content)
    assert projected.answer.text == response.answer.text
    assert projected.rules_context.accepted_binding == binding
    assert projected.answer.trace["usage"]["model_call_count"] == 0
    assert AgentConversationService().inspect_turn(world_id=binding.world_id, turn_id=binding.turn_id) == stored
    changed = adapter.request.model_copy(update={"message": adapter.request.message + " changed"})
    with pytest.raises(AgentTurnServiceError) as denied:
        execute_agent_turn(changed, root=tmp_path, pointer_store=HermesSessionPointerStore(tmp_path / "mixed-replay"),
            owner_resolver=lambda _: {"kind": "world", "id": binding.world_id},
            work_resolver=forbidden, graph_resolver=forbidden, runtime_factory=forbidden,
            conversation_service=AgentConversationService())
    assert denied.value.code == "turn_idempotency_conflict"


@pytest.mark.parametrize("discovery_status", ["complete", "partial", "source_not_admitted"])
def test_default_build_rules_does_not_require_source_ingestion(
    application_state_dsn, build_case, tmp_path, monkeypatch, discovery_status,
):
    from dataclasses import replace
    from apps.live_control_server.services import build_jev_runtime as prepared
    from apps.live_control_server.services.build_jev_harness import BuildJevHarness

    case, reads = ordinary_case(build_case, monkeypatch)
    source, request, bootstrap = case
    request = request.model_copy(update={"message": "Use lookup_rules for ending movement in an occupied space."})
    discovery = dict(bootstrap.build_source_discovery)
    discovery["status"] = discovery_status
    if discovery_status == "partial":
        discovery.update(eligible_count=len(discovery["entries"]) + 1, next_page_token="more-reviewed-observations")
    elif discovery_status == "source_not_admitted":
        discovery.update(entries=[], eligible_count=None, next_page_token=None, coverage=None)
        discovery.pop("source_revision_id", None)
    bootstrap = replace(bootstrap, build_source_discovery=discovery)
    decisions, writer = RulesDecisionWire(dsn=application_state_dsn), RulesWriterWire(base=False, dsn=application_state_dsn)
    monkeypatch.setattr(prepared, "BuildJevHarness", lambda **kwargs: BuildJevHarness(
        decision_transport=decisions, writer_transport=writer, **kwargs,
    ))
    factory = PreparedBuildJevRuntime(accounting=counter(), unavailable_reason=None)
    result = execute((source, request, bootstrap), tmp_path, None, build_runtime_factory=factory)
    assert result.schema_ == "dmb_agent_rules_turn_response_v1"
    assert result.rules_context.accepted_binding.support_table
    assert len(writer.calls) == 1
    if discovery_status == "source_not_admitted":
        assert reads == {"graph": 0, "source": 0}
        scopes = [json.loads(call.content)["state"].get("decision", {}).get("state", {}).get("scope")
                  for call in decisions.calls]
        scopes = [scope for scope in scopes if scope is not None]
        assert scopes and all(scope["kind"] == "saved_build_source" for scope in scopes)
        assert all("source_revision_id" not in scope for scope in scopes)
    calls_before = len(decisions.calls)
    monkeypatch.setattr(PreparedBuildJevRuntime, "create", lambda self: pytest.fail("replay constructed runtime"))
    replay = execute((source, request, bootstrap), tmp_path, None, build_runtime_factory=factory)
    assert replay.rules_context.accepted_binding == result.rules_context.accepted_binding
    assert replay.answer.text == result.answer.text
    assert len(decisions.calls) == calls_before and len(writer.calls) == 1


class AbstainingRulesDecisionWire(RulesDecisionWire):
    """Exact normalized vote from the ordinary Sheep failure, without story text."""
    def __init__(self):
        super().__init__(query=False)

    async def handle_async_request(self, request):
        response = await super().handle_async_request(request)
        answer = response.json()
        if QUERY_CHOICE in answer["answers"]:
            answer["answers"][QUERY_CHOICE].update(confidence=.34, probabilities={"none": .67, "query:0": .33})
        return httpx2.Response(200, request=request, json=answer)


def test_uncertain_none_vote_completes_cited_source_answer_without_rules_read(application_state_dsn, build_case, tmp_path, monkeypatch):
    completed, adapter, decisions, writer, reads = run_parent(build_case, tmp_path, monkeypatch,
        query=False, decision=AbstainingRulesDecisionWire(), dsn=application_state_dsn)
    assert completed.status == "completed"
    assert completed.completion.source_citations
    assert len(writer.calls) == 1
    assert len(decisions.calls) == 5
    assert reads == {"graph": 1, "source": 1}
    assert adapter.rules_runtime.outputs == []
    assert adapter.rules_runtime._selection is None
    with psycopg.connect(application_state_dsn) as conn:
        payload = conn.execute("SELECT payload FROM agent.turn_rules_execution WHERE turn_id=%s", (completed.turn_id,)).fetchone()[0]
    assert payload["budget_use"]["calls"] == 0
    assert payload["supports"] == {}
    assert not any(event["kind"] == "lookup_authorized" for event in payload["events"])


@pytest.mark.parametrize("selected,scores", [
    ("query:0", {"none": .33, "query:0": .67}),
    ("foreign", {"none": 1., "query:0": 0.}),
    ("none", {"none": float("nan"), "query:0": 0.}),
    ("none", {"none": 1.2, "query:0": -.2}),
    ("none", {"none": .67, "query:0": .1}),
    ("none", {"none": .67}),
    ("none", {"none": True, "query:0": False}),
])
def test_invalid_or_uncertain_positive_vote_does_not_select_lookup(selected, scores):
    from apps.live_control_server.services.rules_build_runtime import RulesBuildRuntime
    runtime = object.__new__(RulesBuildRuntime)
    runtime.offers = ("A synthetic question",)
    runtime._selection = None
    with pytest.raises(ValueError, match="unresolved or uncalibrated"):
        runtime.select(request_id="request", vote={"kind": "choice", "selected": selected, "probabilities": scores}, operation="answer_from_sources")
    assert runtime._selection is None


class PrimaryRulesDecision(RulesDecisionWire):
    async def handle_async_request(self, request):
        response = await super().handle_async_request(request)
        body, data = json.loads(request.content), response.json()
        selecting = body["state"].get("writer_selection_policy")
        for key, answer in data["answers"].items():
            labels = body["questions"][key].get("criteria", {})
            chosen = "irrelevant" if selecting else next((label for label in labels if label.startswith("saved:")), None) if key == "next" else None
            if chosen is not None:
                answer.update(choice=chosen, probabilities={label: float(label == chosen) for label in labels})
        return httpx2.Response(200, request=request, json=data)


class PrimaryRulesWriter(RulesWriterWire):
    async def handle_async_request(self, request):
        response = await super().handle_async_request(request)
        packet, data = json.loads(json.loads(request.content)["input"]), response.json()
        section, = packet["artifact_under_edit"]["sections"]
        raw = json.loads(data["output"][0]["content"][0]["text"])
        raw["base_output"] = {"answer_context_status": "source_grounded_partial", "answer_segments": [
            {"kind": "saved_source_claim", "text": section["text"], "section_read_ids": [section["read_id"]]}],
            "limitations": ["partial_retrieval"], "requested_detail_gaps": []}
        raw["ordered_refs"].insert(0, {"domain": "base", "segment_index": None})
        data["output"][0]["content"][0]["text"] = json.dumps(raw)
        return httpx.Response(200, request=request, json=data)


def test_actual_primary_page_and_rules_survive_irrelevant_selection(application_state_dsn, build_case, tmp_path, monkeypatch):
    completed, _, _, writer, reads = run_parent(build_case, tmp_path, monkeypatch,
        decision=PrimaryRulesDecision(dsn=application_state_dsn),
        writer=PrimaryRulesWriter(base=False, dsn=application_state_dsn))
    assert isinstance(completed, MixedCompletedTurnV1)
    assert completed.base_projection.kind == "approved"
    assert completed.base_projection.turn.completion.answer_basis == "saved_source"
    assert reads == {"graph": 0, "source": 0}
    packet = json.loads(json.loads(writer.calls[0].content)["input"])
    assert packet["schema"] == packet["rules_projection"]["carrier_schema"] == "dmb_build_primary_context_writer_v1"
    assert packet["exposure"]["saved_sections"] == [] and packet["artifact_under_edit"]["sections"]
    assert AgentConversationService().inspect_turn(world_id=completed.envelope.world_id, turn_id=completed.envelope.turn_id) == completed
