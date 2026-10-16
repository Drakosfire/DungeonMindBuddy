"""Actual SDK first wire request through the real APP gate; synthetic only."""
import asyncio
import hashlib
import json
from dataclasses import replace
from uuid import uuid4

import httpx2
import pytest

from generationengine import BinaryDecisionQuestion, DecisionRequest, GenerationClient, GenerationEngineError
from generationengine.decision_dispatch import DecisionDispatchGate, PreparedDecisionDispatch, DecisionDispatchEvent
from generationengine.providers.typesafe_decision import TypeSafeDecisionProvider
from application_state.agent_conversation import AgentConversationService
from application_state.agent_conversation import types as t
from apps.live_control_server.routes import agent
from apps.live_control_server.services import agent_turn_service as owner
from apps.live_control_server.services import build_jev_dispatch as policy
from tests.test_agent_build_governed_graph import build_case as _build_case_fixture


@pytest.fixture
def build_case(tmp_path, monkeypatch, application_state_dsn):
    return _build_case_fixture.__wrapped__(tmp_path, monkeypatch, application_state_dsn)


def _adapter(build_case):
    _, request, bootstrap = build_case
    work = agent._work_resolver(request, {"kind": "world", "id": "elderwyld"})
    adapter = owner._PolicyExecutionAdapter(service=AgentConversationService(), request=request,
        world_id="elderwyld", work=work, bootstrap=bootstrap, playable_target=None,
        submitted_intent=owner._submitted_turn_intent(request, world_id="elderwyld"),
        existing_turn=None, budget=policy.request_budget(), context_read_enabled=True)
    state = policy.first_state(work, bootstrap, request.message,
        owner._expected_initial_claim_packet(bootstrap))
    return adapter, state


def _prepared(state, questions=None, **updates):
    body = json.dumps({"state": state, "model": policy.MODEL, "questions": questions or {
        "yes": {"type": "noul", "instructions": "Does discovery identify a relevant next read?"}
    }}, ensure_ascii=False).encode()
    prepared = PreparedDecisionDispatch(str(uuid4()), policy.PROVIDER, "vercel_ai_gateway", policy.MODEL,
        "POST", policy.ENDPOINT, body, hashlib.sha256(body).hexdigest(), len(body))
    return replace(prepared, **updates)


class Wire(httpx2.AsyncBaseTransport):
    def __init__(self, adapter, *, timeout=False, cancel=False):
        self.adapter, self.timeout, self.calls, self.closed = adapter, timeout, [], False
        self.cancel = cancel

    async def handle_async_request(self, request):
        self.calls.append(request)
        turn = self.adapter.turn
        fresh = AgentConversationService().list_turns(turn.world_id, turn.conversation_id)[0]
        assert fresh.graph_context_execution.events[-1].outcome == "sdk_entered"
        assert "TypeSafe-Danger-Zone-Long-Context" not in request.headers
        if self.cancel:
            raise asyncio.CancelledError()
        if self.timeout:
            raise httpx2.ReadTimeout("synthetic transport timeout", request=request)
        return httpx2.Response(200, request=request, json={"model": policy.MODEL,
            "usage": {"input_tokens": 14, "output_tokens": 1},
            "answers": {"yes": {"type": "noul", "noul": 0.8}}})

    async def aclose(self):
        self.closed = True


def _invoke(adapter, state, wire, seen):
    async def run():
        async def authorize(prepared):
            seen.append(prepared)
            return adapter.authorize_prepared_build_decision(prepared)
        async def record(event):
            return adapter.record_prepared_build_decision(event)
        provider = TypeSafeDecisionProvider(api_key="synthetic-not-a-credential",
            dispatch_gate=DecisionDispatchGate(authorize, record), transport=wire)
        client = GenerationClient(decision_providers={"typesafe": provider})
        try:
            return await client.decide(DecisionRequest(provider=policy.PROVIDER, model=policy.MODEL,
                state=state, questions=(BinaryDecisionQuestion(name="yes", question="Is a next read discoverable?"),),
                max_transport_retries=2))
        finally:
            await client.aclose()
    return asyncio.run(run())


def test_real_sdk_first_decision_freezes_exact_wire_basis_and_lifecycle(build_case):
    adapter, state = _adapter(build_case)
    wire, seen = Wire(adapter), []
    result = _invoke(adapter, state, wire, seen)
    assert result.observation.input_tokens == 14
    assert len(wire.calls) == len(seen) == 1 and wire.closed
    prepared = seen[0]
    turn = adapter.turn
    fresh = AgentConversationService().list_turns(turn.world_id, turn.conversation_id)[0]
    receipt, execution = fresh.graph_context_receipt, fresh.graph_context_execution
    assert isinstance(execution.policy, t.ControllerWriterGraphExecutionPolicyV3)
    assert receipt.source_basis.content_sha256 == state["source_basis"]["content_sha256"]
    assert receipt.assembled_input.budget_policy_version == "build_jev_first_basis_discovery_v1"
    assert receipt.assembled_input.context_window_limit == policy.REQUEST_LIMIT
    assert receipt.assembled_input.assembled_input_sha256 == prepared.body_sha256
    auth, entered, response = execution.events
    assert str(auth.provider_attempt_id) == prepared.attempt_id
    assert auth.envelope_sha256 == hashlib.sha256(wire.calls[0].content).hexdigest()
    assert auth.serializer_version == policy.SERIALIZER
    assert [entered.outcome, response.outcome] == ["sdk_entered", "response_received"]
    assert response.status_code == 200
    assert adapter.producing_provider_attempt_id is None
    assert adapter.work.build_source.markdown not in prepared.body.decode()
    assert not adapter.authorize_prepared_build_decision(prepared)  # first-dispatch only
    assert not adapter.record_prepared_build_decision(replace(
        DecisionDispatchEvent(prepared, "response_received", 200),
        request=replace(prepared, attempt_id=str(uuid4()))))


@pytest.mark.parametrize("cancel", [False, True])
def test_transport_timeout_keeps_unknown_outcome_without_another_send(build_case, cancel):
    adapter, state = _adapter(build_case)
    wire, seen = Wire(adapter, timeout=not cancel, cancel=cancel), []
    with pytest.raises(asyncio.CancelledError if cancel else GenerationEngineError):
        _invoke(adapter, state, wire, seen)
    assert len(wire.calls) == 1 and wire.closed
    turn = adapter.turn
    fresh = AgentConversationService().list_turns(turn.world_id, turn.conversation_id)[0]
    assert fresh.graph_context_execution.events[-1].outcome == "outcome_unknown"
    assert adapter.producing_provider_attempt_id is None


@pytest.mark.parametrize("mutation", ["source", "question", "world", "native", "revision", "session", "discovery", "packet", "extra"])
def test_authority_mutations_fail_before_turn_claim(build_case, mutation):
    adapter, state = _adapter(build_case)
    state = json.loads(json.dumps(state))
    if mutation == "source":
        state["source_basis"]["content_sha256"] = "f" * 64
    elif mutation == "question":
        state["user_question"] = "A different question"
    elif mutation in {"world", "native", "revision", "session"}:
        field = {"world": "managed_world_id", "native": "native_world_id", "revision": "graph_revision", "session": "retrieval_session_id"}[mutation]
        state["graph_scope"][field] = "foreign"
    elif mutation == "discovery":
        state["discovery"] = {"entries": ["invented"]}
    elif mutation == "packet":
        state["initialClaimPacket"]["claimLedger"] = [{"claim_id": "invented"}]
    else:
        state["authority_override"] = True
    assert adapter.authorize_prepared_build_decision(_prepared(state)) is False
    assert adapter.fence is None and adapter.turn is None


@pytest.mark.parametrize("changes", [{"model": "foreign"}, {"provider": "openai-api"},
    {"provider_transport": "other"}, {"method": "GET"}, {"url": policy.ENDPOINT + "?other=1"},
    {"body_sha256": "f" * 64}, {"body_size": 0}, {"attempt_id": "not-a-uuid"}])
def test_prepared_identity_mismatch_fails_before_claim(build_case, changes):
    adapter, state = _adapter(build_case)
    assert adapter.authorize_prepared_build_decision(_prepared(state, **changes)) is False
    assert adapter.fence is None


def test_per_question_and_total_wire_limits_include_instructions_and_options(build_case):
    _, state = _adapter(build_case)
    # One huge instruction fails the per-question ceiling while total is <64k.
    huge = _prepared(state, {"q": {"type": "choice", "instructions": "x" * 32_000,
        "criteria": {"a": "first", "b": "second"}}})
    with pytest.raises(ValueError, match="per-question"):
        policy.prepared_view(huge, state)
    huge_option = _prepared(state, {"q": {"type": "choice", "instructions": "choose",
        "criteria": {"a": "x" * 32_000, "b": "second"}}})
    with pytest.raises(ValueError, match="per-question"):
        policy.prepared_view(huge_option, state)
    many = _prepared(state, {f"q{i}": {"type": "noul", "instructions": "x" * 10_000} for i in range(7)})
    with pytest.raises(ValueError, match="request context"):
        policy.prepared_view(many, state)


def test_generic_mapping_cannot_bypass_actual_prepared_bridge(build_case):
    adapter, state = _adapter(build_case)
    assert not adapter.authorize(policy.prepared_view(_prepared(state), state))
    assert adapter.fence is None


def test_stale_parent_fence_blocks_sending_and_preserves_pending_authorization(build_case):
    adapter, state = _adapter(build_case)
    original = adapter.record_prepared_build_decision
    renewed = []
    def record(event):
        if event.outcome == "sending":
            turn = adapter.turn
            renewed.append(AgentConversationService().renew_turn_claim(turn.world_id, turn.conversation_id, turn.turn_id,
                expected_revision=turn.revision, lease_seconds=60))
        return original(event)
    adapter.record_prepared_build_decision = record
    wire, seen = Wire(adapter), []
    with pytest.raises(GenerationEngineError):
        _invoke(adapter, state, wire, seen)
    assert wire.calls == [] and wire.closed
    turn = renewed[0]
    fresh = AgentConversationService().list_turns(turn.world_id, turn.conversation_id)[0]
    assert fresh == turn
    assert len(fresh.graph_context_execution.events) == 1


def test_nonempty_initial_graph_packet_is_admitted_from_exact_sdk_state(build_case):
    from graph_memory.interaction.authority_classifier import claims_from_retrieval_result
    from graph_memory.interaction.session import GraphRetrievalSession, CoverageState, SourceAnchorState

    source, request, bootstrap = build_case
    claims = claims_from_retrieval_result({"relationships": [{
        "edgeId": "rel:seed", "sourceNodeId": "node:one", "targetNodeId": "node:two",
        "predicate": "guards", "evidenceRefIds": ["ev:one"]}],
        "sourceAnchors": [{"anchorId": "anchor:one", "revisionId": "native-rev-3", "evidenceRefId": "ev:one",
            "readable": True, "supportingGraphObjectIds": []}]}, revision_id="native-rev-3")
    session = GraphRetrievalSession(snapshot=bootstrap.retrieval_session.snapshot,
        question=request.message, coverage=CoverageState(state="ready"), claims=claims,
        source_anchors=[SourceAnchorState(anchor_id="anchor:one", readable=True)])
    bootstrap = replace(bootstrap, retrieval_session=session,
        candidate_relationship_ids=("rel:seed",), candidate_evidence_ref_ids=("ev:one",),
        evidence_by_anchor_id={"anchor:one": "ev:one"}, source_scope_anchors=({
            "anchor_id": "anchor:one", "evidence_ref_id": "ev:one", "source_artifact_id": "artifact:one",
            "source_revision_id": "source-rev:one"},))
    adapter, state = _adapter((source, request, bootstrap))
    wire, seen = Wire(adapter), []
    _invoke(adapter, state, wire, seen)
    auth = adapter.turn.graph_context_execution.events[0]
    assert auth.included_relationship_ids == ["rel:seed"]
    assert auth.included_evidence_ref_ids == ["ev:one"]
    actual = json.loads(wire.calls[0].content)["state"]["initialClaimPacket"]
    assert actual == owner._expected_initial_claim_packet(bootstrap)
    assert actual["claimLedger"][0]["support"]["source_anchor_ids"] == ["anchor:one"]


@pytest.mark.parametrize("field,value", [("contextLimitTokens", 1_050_000),
    ("outputReserveTokens", 2048), ("model", "foreign")])
def test_bridge_cannot_borrow_or_change_frozen_role_budget(build_case, field, value):
    adapter, state = _adapter(build_case)
    adapter.budget = dict(adapter.budget, **{field: value})
    assert not adapter.authorize_prepared_build_decision(_prepared(state))
    assert adapter.fence is None


def test_exact_conservative_per_question_boundary(build_case):
    _, state = _adapter(build_case)
    questions = {"q": {"type": "noul", "instructions": ""}}
    body = {"state": state, "model": policy.MODEL, "questions": questions}
    encoded = json.dumps(body, ensure_ascii=True, separators=(",", ":")).encode()
    allowance = policy.QUESTION_LIMIT - len(encoded) - 64 * (1 + policy._json_nodes(body))
    assert allowance > 0
    questions["q"]["instructions"] = "x" * allowance
    policy.prepared_view(_prepared(state, questions), state)
    questions["q"]["instructions"] += "x"
    with pytest.raises(ValueError, match="per-question"):
        policy.prepared_view(_prepared(state, questions), state)


def test_exact_conservative_total_request_boundary(build_case):
    _, state = _adapter(build_case)
    questions = {f"q{i}": {"type": "noul", "instructions": ""} for i in range(3)}
    prepared = _prepared(state, questions)
    decoded = json.loads(prepared.body)
    allowance = policy.REQUEST_LIMIT - prepared.body_size - 64 * (1 + policy._json_nodes(decoded))
    for index, question in enumerate(questions.values()):
        question["instructions"] = "x" * (allowance // 3 + (index < allowance % 3))
    policy.prepared_view(_prepared(state, questions), state)
    questions["q0"]["instructions"] += "x"
    with pytest.raises(ValueError, match="request context"):
        policy.prepared_view(_prepared(state, questions), state)
