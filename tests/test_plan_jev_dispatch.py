"""Actual Plan dispatch gate and APP receipt with synthetic GE transport."""
import asyncio
from dataclasses import replace
from hashlib import sha256
import json
from uuid import uuid4

import httpx2
import pytest
from generationengine import GenerationEngineError
from application_state.agent_conversation import AgentConversationService
from application_state.agent_conversation import types as t
from application_state.agent_conversation.jev_retrieval_contract import RetrievalCandidate
from apps.live_control_server.services import agent_turn_service as owner
from apps.live_control_server.services.agent_runtime import AgentWorldScope
from apps.live_control_server.services.plan_jev_dispatch import PlanJevDispatch, request_budget
from graph_memory.interaction.session import CoverageState, GraphRetrievalSession, SessionSnapshot
from tests.test_agent_turn_service import _pinned_plan_request, _pinned_plan_work


@pytest.fixture
def plan_adapter(application_state_dsn, monkeypatch):
    monkeypatch.setattr('apps.live_control_server.services.agent_graph_policy.resolve_agent_graph_openai_inference',
        lambda **_: ('openai-api', 'gpt-6-luna', 'https://api.openai.com/v1'))
    request = _pinned_plan_request()
    request = type(request).model_validate(request.model_dump(mode='json', by_alias=True) | {
        'turn_id': str(uuid4()), 'plan_context_policy': {'policy': 'auto_plan_world'},
        'graph_request': {'mode': 'none'}})
    work = _pinned_plan_work('# Synthetic park Plan\nA proposed visit, not a played fact.\n')
    work = replace(work, content_basis=work.content_basis.model_copy(update={"content_sha256": sha256(work.plan_markdown.encode()).hexdigest(), "work_revision_id": str(uuid4())}))
    request = request.model_copy(update={'primary_work': request.primary_work.model_copy(update={
        'expected_content_sha256': work.content_basis.content_sha256})})
    session = GraphRetrievalSession(snapshot=SessionSnapshot(world_id='native-park', campaign_id='',
        focus={'kind': 'none'}, admissibility='gm', revision_id='park:1', is_head=True, scope_mode='world'),
        question=request.message, coverage=CoverageState(state='empty'), claims=[], source_anchors=[])
    bootstrap = owner.AgentPlanWorldGraphBootstrap(graph_envelope={'status': 'empty', 'revision_id': 'park:1',
        'world_id': 'native-park', 'scope_mode': 'world'},
        world_scope=AgentWorldScope(world_id='native-park', campaign_id='', focus={'kind': 'none'},
            admissibility='gm', revision_id='park:1', scope_mode='world'), retrieval_session=session,
        binding_version=1, source_root_relpath='corpus/synthetic', candidate_assertion_ids=(),
        candidate_relationship_ids=(), candidate_evidence_ref_ids=(), evidence_by_anchor_id={})
    adapter = owner._PolicyExecutionAdapter(service=AgentConversationService(), request=request,
        world_id='world:one', work=work, bootstrap=bootstrap, playable_target=None,
        submitted_intent=owner._submitted_turn_intent(request, world_id='world:one'), existing_turn=None,
        budget=request_budget(), context_read_enabled=True)
    yield adapter
    if adapter.fence is not None: adapter.fence.renewer.stop_and_join()


class Wire(httpx2.AsyncBaseTransport):
    def __init__(self, adapter, *, timeout=False, operation='finish_retrieval', missing_usage=False, independent_includes=False):
        self.adapter, self.timeout, self.calls = adapter, timeout, []
        self.operation, self.missing_usage = operation, missing_usage
        self.independent_includes = independent_includes
    async def handle_async_request(self, request):
        self.calls.append(request)
        current = self.adapter.service.list_turns('world:one', self.adapter.turn.conversation_id)[0]
        assert current.graph_context_execution.events[-1].outcome == 'sdk_entered'
        body = json.loads(request.content)
        assert set(body['state']) == {'question', 'candidates'}
        assert body['state']['candidates'] == [{'label': 'Park pond', 'kind': 'location'}]
        assert 'native-park' not in request.content.decode() and 'park:1' not in request.content.decode()
        if self.timeout: raise httpx2.ReadTimeout('synthetic ambiguous response', request=request)
        answers = {}
        for name, entry in body['questions'].items():
            choice = self.operation if name == 'operation' else ('include' if self.operation == 'select_candidates' or self.independent_includes else 'exclude')
            answers[name] = {'type': 'choice', 'choice': choice, 'confidence': 1.0,
                'probabilities': {key: float(key == choice) for key in entry['criteria']}}
        return httpx2.Response(200, request=request, json={'model': 'jev-1.14.0', 'answers': answers,
            'usage': {} if self.missing_usage else {'input_tokens': 37, 'output_tokens': 9}})


def controller(adapter):
    return PlanJevDispatch(adapter, (RetrievalCandidate(handle='node:park-pond', label='Park pond', kind='location'),))


def test_actual_first_plan_decision_freezes_wire_claim_and_selection(plan_adapter):
    dispatch = controller(plan_adapter); wire = Wire(plan_adapter)
    selection, result = asyncio.run(dispatch.run(transport=wire, api_key='synthetic-not-secret'))
    turn = plan_adapter.fence.turn
    assert len(wire.calls) == 1 and selection.operation == 'finish_retrieval'
    receipt, execution = turn.graph_context_receipt, turn.graph_context_execution
    assert isinstance(execution.policy, t.PlanJevRetrievalPolicyV1)
    assert receipt.assembled_input.assembled_input_sha256 == dispatch.prepared.body_sha256
    assert receipt.assembled_input.dispatched_assertion_ids == []
    assert receipt.assembled_input.dispatched_evidence_ref_ids == []
    assert execution.events[-1].actual_input_tokens == result.observation.input_tokens == 37
    assert execution.events[-1].actual_output_tokens == 9
    assert plan_adapter.context_capture.trace.capture_status == 'recording'
    assert [row.kind for row in execution.events] == ['plan_jev_provider_authorized_v1',
        'provider_outcome', 'provider_outcome', 'plan_jev_retrieval_selected_v1']
    assert not dispatch.authorize(dispatch.prepared)
    with pytest.raises(ValueError, match='unique'): dispatch.acknowledge(result)


def test_actual_unknown_plan_dispatch_does_not_retry_or_admit_selection(plan_adapter):
    dispatch = controller(plan_adapter); wire = Wire(plan_adapter, timeout=True)
    with pytest.raises(GenerationEngineError):
        asyncio.run(dispatch.run(transport=wire, api_key='synthetic-not-secret'))
    execution = plan_adapter.fence.turn.graph_context_execution
    assert len(wire.calls) == 1 and execution.events[-1].outcome == 'outcome_unknown'
    assert not any(isinstance(e, t.PlanJevRetrievalSelectionV1) for e in execution.events)


def test_plan_continuation_keeps_receipt_and_actual_call_accounting(plan_adapter):
    first = controller(plan_adapter); wire = Wire(plan_adapter, operation='select_candidates')
    selection, _ = asyncio.run(first.run(transport=wire, api_key='synthetic-not-secret'))
    receipt = plan_adapter.fence.turn.graph_context_receipt
    assert selection.operation == 'select_candidates'
    assert first.call['usage'] == {'status': 'reported', 'input_tokens': 37, 'output_tokens': 9, 'total_tokens': 46}
    final = controller(plan_adapter); final_wire = Wire(plan_adapter, missing_usage=True)
    selection, _ = asyncio.run(final.run(transport=final_wire, api_key='synthetic-not-secret'))
    assert selection.operation == 'finish_retrieval' and len(final_wire.calls) == 1
    assert plan_adapter.fence.turn.graph_context_receipt == receipt
    assert final.call['usage']['status'] == 'unavailable'
    assert final.call['usage']['input_tokens'] is None and final.call['usage']['output_tokens'] is None
    trace = plan_adapter.context_capture.trace
    usage = [row for row in trace.observations if row.kind == 'provider_call' and row.input_tokens == 37]
    assert len(usage) == 1 and usage[0].provider_attempt_id == first.authorization.provider_attempt_id
    assert plan_adapter.fence.turn.graph_context_execution.events[-1].actual_input_tokens is None


@pytest.mark.parametrize('mutation', ['metadata', 'question', 'model', 'hash', 'endpoint'])
def test_changed_actual_wire_refused_before_plan_claim(plan_adapter, mutation):
    from generationengine.decision_dispatch import PreparedDecisionDispatch
    from application_state.agent_conversation.jev_retrieval_contract import prepare_decision
    dispatch = controller(plan_adapter)
    request = prepare_decision(dispatch.parent)
    body = {'model': request.model, 'state': request.state, 'questions': {
        q.name: {'type': 'choice', 'instructions': q.question, 'criteria': {option: None for option in q.options}}
        for q in request.questions}}
    if mutation == 'metadata': body['state'] = body['state'] | {'receipt_sha256': 'host-only-proof'}
    if mutation == 'question': body['state'] = body['state'] | {'question': 'Different question'}
    if mutation == 'model': body['model'] = 'different-model'
    raw = json.dumps(body).encode()
    prepared = PreparedDecisionDispatch(str(uuid4()), 'typesafe', 'vercel_ai_gateway', 'jev-1.14.0',
        'POST', 'https://ai-gateway.vercel.sh/typesafe/v1/systemone', raw, sha256(raw).hexdigest(), len(raw))
    if mutation == 'hash': prepared = replace(prepared, body_sha256='a' * 64)
    if mutation == 'endpoint': prepared = replace(prepared, url='https://example.invalid/')
    with pytest.raises(ValueError): dispatch.authorize(prepared)
    assert plan_adapter.turn is None and plan_adapter.fence is None


def test_unknown_previous_decision_blocks_new_sdk_send(plan_adapter):
    first = controller(plan_adapter); first_wire = Wire(plan_adapter, timeout=True)
    with pytest.raises(GenerationEngineError):
        asyncio.run(first.run(transport=first_wire, api_key='synthetic-not-secret'))
    following = controller(plan_adapter); following_wire = Wire(plan_adapter)
    with pytest.raises(GenerationEngineError):
        asyncio.run(following.run(transport=following_wire, api_key='synthetic-not-secret'))
    assert len(first_wire.calls) == 1 and following_wire.calls == []
    assert following.call is None


def test_actual_app_composes_relevant_candidate_before_global_finish(plan_adapter):
    dispatch=controller(plan_adapter)
    wire=Wire(plan_adapter,independent_includes=True)
    selected,result=asyncio.run(dispatch.run(transport=wire,api_key='synthetic-not-secret'))
    assert selected.operation=='select_candidates' and selected.selected_handles==('node:park-pond',)
    assert result.answers['candidate_0'].selected=='include'
    event=plan_adapter.fence.turn.graph_context_execution.events[-1]
    assert event.operation=='select_candidates' and event.selected_handles==['node:park-pond']


def test_active_native_acquisition_refuses_decision_before_claim_or_sdk_send(plan_adapter):
    dispatch = controller(plan_adapter)
    wire = Wire(plan_adapter)
    plan_adapter._build_native_acquisition_services = object()
    try:
        with pytest.raises(GenerationEngineError):
            asyncio.run(dispatch.run(transport=wire, api_key='synthetic-not-secret'))
        assert wire.calls == []
        assert plan_adapter.fence is None
        assert dispatch.prepared is None
    finally:
        plan_adapter._build_native_acquisition_services = None
