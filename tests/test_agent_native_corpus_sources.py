"""Existing Plan claim/SDK path with actual Core source ownership and no Graph."""
import asyncio
from dataclasses import replace
from hashlib import sha256
import json
from types import SimpleNamespace
from uuid import uuid4

import httpx2
import pytest
from application_state.agent_conversation import AgentConversationService, types as t
from apps.live_control_server.services import agent_turn_service as owner
from apps.live_control_server.services.plan_jev_dispatch import PlanJevDispatch, request_budget
from apps.live_control_server.services.plan_source_turn import prepare
from tests.test_agent_turn_service import _pinned_plan_request, _pinned_plan_work
from tests.test_native_corpus_source_access import lane, admit, GM, BODY  # noqa: F401


@pytest.fixture
def source_adapter(application_state_dsn, monkeypatch, lane):
    monkeypatch.setattr('apps.live_control_server.services.agent_graph_policy.resolve_agent_graph_openai_inference',
        lambda **_: ('openai-api', 'gpt-6-luna', 'https://api.openai.com/v1'))
    lane.bound.managed_world_id = 'world:one'
    admit(lane)
    context, authority = prepare('world:one', GM, repository=lane.repo,
        resolve_identity=lambda _: lane.bound)
    request = _pinned_plan_request()
    request = type(request).model_validate(request.model_dump(mode='json', by_alias=True) | {
        'turn_id': str(uuid4()), 'plan_context_policy': {'policy': 'auto_plan_world'},
        'graph_request': {'mode': 'none'}})
    work = _pinned_plan_work('# Synthetic park Plan\nA proposed visit, not a played fact.\n')
    work = replace(work, content_basis=work.content_basis.model_copy(update={
        'content_sha256': sha256(work.plan_markdown.encode()).hexdigest(), 'work_revision_id': str(uuid4())}))
    request = request.model_copy(update={'primary_work': request.primary_work.model_copy(update={
        'expected_content_sha256': work.content_basis.content_sha256})})
    adapter = owner._PolicyExecutionAdapter(service=AgentConversationService(), request=request,
        world_id='world:one', work=work, bootstrap=None, playable_target=None,
        submitted_intent=owner._submitted_turn_intent(request, world_id='world:one'), existing_turn=None,
        budget=request_budget(), context_read_enabled=True,
        native_corpus_context=context, native_source_authority=authority)
    yield adapter
    if adapter.fence is not None:
        adapter.fence.renewer.stop_and_join()


class DecisionWire(httpx2.AsyncBaseTransport):
    def __init__(self, adapter, *, select_rule=False):
        self.adapter = adapter
        self.select_rule = select_rule
        self.sent = []

    async def handle_async_request(self, request):
        self.sent.append(request.content)
        turn = self.adapter.service.list_turns('world:one', self.adapter.turn.conversation_id)[0]
        assert turn.graph_context_execution.events[-1].outcome == 'sdk_entered'
        body = json.loads(request.content)
        # No source bytes or machine authority enters the semantic/navigation model.
        assert BODY not in request.content.decode()
        assert self.adapter.native_source_authority.revision_id not in request.content.decode()
        answers = {}
        for name, entry in body['questions'].items():
            selected = ('discuss' if name == 'requested_work' else
                'finish_retrieval' if name == 'operation' else 'exclude')
            if self.select_rule and name.startswith('candidate_'):
                candidate = body['state']['candidates'][int(name.split('_')[-1])]
                if candidate['kind'] == 'public_rules_lookup':
                    selected = 'include'
            assert selected in entry['criteria']
            answers[name] = {'type': 'choice', 'choice': selected, 'confidence': 1.0,
                'probabilities': {key: float(key == selected) for key in entry['criteria']}}
        return httpx2.Response(200, request=request, json={'model': 'jev-1.14.0', 'answers': answers,
            'usage': {'input_tokens': 37, 'output_tokens': 9}})


def test_existing_plan_sdk_claim_owns_trusted_source_context_without_classic_graph(source_adapter):
    from apps.live_control_server.services.native_source_navigation import navigator
    from apps.live_control_server.services.corpus_source_navigation import NativeBodyNavigation
    a = source_adapter
    dispatch = PlanJevDispatch.requested_work(a, page_title='Synthetic park Plan')
    wire = DecisionWire(a)
    selected, _ = asyncio.run(dispatch.run(transport=wire, api_key='synthetic-not-secret'))
    assert selected == 'discuss' and len(wire.sent) == 1
    turn = a.fence.turn
    assert isinstance(turn.graph_context_receipt, t.PlanSourceContextReceiptV1)
    assert isinstance(turn.graph_context_execution, t.PlanSourceExecutionV1)
    assert turn.graph_context_receipt.source_authority == a.native_corpus_context.authority
    assert turn.graph_context_receipt.graph_capability is None and a.bootstrap is None
    assert turn.graph_context_receipt.assembled_input.assembled_input_sha256 == dispatch.prepared.body_sha256
    assert isinstance(navigator(a), NativeBodyNavigation)
    assert navigator(a).offered()
    # The next decision is the versioned native parent, never a native-R Graph alias.
    next_call = PlanJevDispatch(a, navigator(a).offered(), allowed_operations=('select_candidates', 'finish_retrieval'))
    assert next_call.parent.source_revision == turn.graph_context_receipt.source_authority.revision_id
    assert next_call.parent.graph_revision is None
    next_wire = DecisionWire(a)
    selection, _ = asyncio.run(next_call.run(transport=next_wire, api_key='synthetic-not-secret'))
    assert selection.operation == 'finish_retrieval' and len(next_wire.sent) == 1
    reopened = AgentConversationService().list_turns('world:one', turn.conversation_id)[0]
    assert reopened == a.fence.turn
    assert len(reopened.graph_context_execution.events) == 8


def test_source_adapter_refuses_missing_or_foreign_trusted_context(source_adapter):
    a = source_adapter
    values = dict(service=a.service, request=a.request, world_id=a.world_id, work=a.work,
        bootstrap=None, playable_target=None, submitted_intent=a.submitted_intent,
        existing_turn=None, budget=a.budget, native_source_authority=a.native_source_authority)
    with pytest.raises(ValueError, match='trusted source context'):
        owner._PolicyExecutionAdapter(**values)
    foreign = SimpleNamespace(authority=a.native_source_authority.model_copy(update={'managed_world_id': 'foreign'}))
    with pytest.raises(ValueError, match='trusted source context'):
        owner._PolicyExecutionAdapter(**values, native_corpus_context=foreign)


def test_source_only_driver_and_rules_frame_preserve_independent_capabilities(source_adapter, monkeypatch):
    from apps.live_control_server.services.plan_jev_driver import PlanJevDriver
    from apps.live_control_server.services.plan_jev_rules_runtime import PlanRulesRuntime
    from application_state.agent_conversation.rules_authority_policy import rules_capability
    from apps.live_control_server.services.plan_jev_acquisition import read_subject_labels
    a = source_adapter
    semantic = PlanJevDispatch.requested_work(a, page_title='Synthetic park Plan')
    asyncio.run(semantic.run(transport=DecisionWire(a), api_key='synthetic-not-secret'))
    # The old classic registry must not be consulted by the new source navigator.
    monkeypatch.setattr('apps.live_control_server.services.native_source_navigation.NativeSourceNavigator',
        lambda *_args, **_kwargs: pytest.fail('obsolete source navigation used'))
    rules = PlanRulesRuntime(a, rules_capability(graph=True))
    driver = PlanJevDriver(a, rules=rules)
    assert driver.discovered and read_subject_labels(a) == {}
    assert any(candidate.kind == 'public_rules_lookup' for candidate in driver.offered())
    assert driver.native_sources.offered()
    proof = asyncio.run(driver.run(transport=DecisionWire(a), api_key='synthetic-not-secret'))
    assert proof['graph_packets'] == {} and proof['plan_markdown'] == a.work.plan_markdown
    frame = rules.frame()
    assert not frame.lookups and rules.native.record is not None
    assert rules.native.record.execution.scope.world_id == a.world_id
    assert a.fence.turn.graph_context_receipt.graph_capability is None


def test_unavailable_native_source_keeps_ordinary_rules_offer_without_fake_revision(source_adapter):
    from apps.live_control_server.services.plan_jev_driver import PlanJevDriver
    from apps.live_control_server.services.plan_jev_rules_runtime import PlanRulesRuntime
    from application_state.agent_conversation.rules_authority_policy import rules_capability
    a = source_adapter
    a.native_corpus_context = None
    a.native_source_authority = t.NativeCorpusUnavailableV1(managed_world_id=a.world_id,
        failure_code='native_source_head_unavailable')
    semantic = PlanJevDispatch.requested_work(a, page_title='Synthetic park Plan')
    # Only this synthetic transport's inspection uses a revision property.
    class NoRevisionWire(DecisionWire):
        async def handle_async_request(self, request):
            self.sent.append(request.content)
            body = json.loads(request.content)
            answers = {name: {'type': 'choice', 'choice': 'discuss', 'confidence': 1.0,
                'probabilities': {key: float(key == 'discuss') for key in entry['criteria']}}
                for name, entry in body['questions'].items()}
            return httpx2.Response(200, request=request, json={'model': 'jev-1.14.0', 'answers': answers,
                'usage': {'input_tokens': 37, 'output_tokens': 9}})
    asyncio.run(semantic.run(transport=NoRevisionWire(a), api_key='synthetic-not-secret'))
    rules = PlanRulesRuntime(a, rules_capability(graph=True))
    driver = PlanJevDriver(a, rules=rules)
    assert driver.native_sources.offered() == ()
    assert [c.kind for c in driver.offered()] == ['public_rules_lookup']
    dispatch = PlanJevDispatch(a, driver.offered(), allowed_operations=('select_candidates', 'finish_retrieval'))
    assert dispatch.parent.source_authority_status == 'unavailable'
    assert dispatch.parent.source_revision is None and dispatch.parent.graph_revision is None
    assert not rules.frame().lookups


def test_mixed_source_owner_refuses_before_rules_ledger_creation(source_adapter, monkeypatch):
    from apps.live_control_server.services.plan_jev_rules_runtime import PlanRulesRuntime
    from application_state.agent_conversation.rules_authority_policy import rules_capability
    a = source_adapter
    semantic = PlanJevDispatch.requested_work(a, page_title='Synthetic park Plan')
    asyncio.run(semantic.run(transport=DecisionWire(a), api_key='synthetic-not-secret'))
    rules = PlanRulesRuntime(a, rules_capability(graph=True))
    native = rules._initialize()
    original = a.fence.renewer._turn
    with a.fence.renewer._lock:
        a.fence.renewer._turn = original.model_copy(update={'graph_context_execution': None})
        monkeypatch.setattr(a.service, 'begin_rules_execution',
            lambda *_args, **_kwargs: pytest.fail('Rules ledger created for mixed source owner'))
        try:
            with pytest.raises(ValueError, match='exact receipt and execution'):
                native._bind()
            assert native.record is None
        finally:
            a.fence.renewer._turn = original


def test_source_only_actual_rules_selection_reads_once_under_its_own_authority(source_adapter, monkeypatch):
    from apps.live_control_server.services.plan_jev_driver import PlanJevDriver
    from apps.live_control_server.services.plan_jev_rules_runtime import PlanRulesRuntime
    from apps.live_control_server.services import rules_lookup_broker as broker
    from application_state.agent_conversation.rules_authority_policy import rules_capability
    from tests.test_rules_lookup_broker import args
    a = source_adapter
    a.request = a.request.model_copy(update={'message': args().question})
    a.submitted_intent = owner._submitted_turn_intent(a.request, world_id=a.world_id)
    semantic = PlanJevDispatch.requested_work(a, page_title='Synthetic park Plan')
    asyncio.run(semantic.run(transport=DecisionWire(a), api_key='synthetic-not-secret'))
    rules = PlanRulesRuntime(a, rules_capability(graph=True))
    calls = []
    original = broker.prepare_plan_lookup
    def read(execution, call_id, question, **kwargs):
        calls.append(question)
        return original(execution, call_id, question, **kwargs)
    monkeypatch.setattr(broker, 'prepare_plan_lookup', read)
    driver = PlanJevDriver(a, rules=rules)
    wire = DecisionWire(a, select_rule=True)
    proof = asyncio.run(driver.run(transport=wire, api_key='synthetic-not-secret'))
    frame = rules.frame()
    assert calls == [a.request.message] and len(wire.sent) == 2
    assert len(frame.lookups) == 1 and frame.lookups[0].status == 'evidence'
    assert proof['graph_packets'] == {} and a.fence.turn.graph_context_receipt.graph_capability is None
    rules.frame()
    assert calls == [a.request.message]


class SourceChoices(httpx2.AsyncBaseTransport):
    def __init__(self, *, sections=False):
        self.calls = []
        self.read_kind = 'Exact source section' if sections else 'Explicit full-document read'

    async def handle_async_request(self, request):
        body = json.loads(request.content)
        self.calls.append(body)
        assert len(self.calls) <= 4, body['state']
        answers = {}
        for name, entry in body['questions'].items():
            choice = 'finish_retrieval' if name == 'operation' else 'exclude'
            if name.startswith('candidate_'):
                candidate = body['state']['candidates'][int(name.split('_')[-1])]
                if candidate['kind'] in {'Source lexical navigation; not evidence or semantic completeness',
                                         self.read_kind}:
                    choice = 'include'
            answers[name] = {'type': 'choice', 'choice': choice, 'confidence': 1.0,
                'probabilities': {key: float(key == choice) for key in entry['criteria']}}
        return httpx2.Response(200, request=request, json={'model': 'jev-1.14.0', 'answers': answers,
            'usage': {'input_tokens': 37, 'output_tokens': 9}})


def test_actual_sdk_writer_receives_only_explicitly_selected_native_body(source_adapter):
    from apps.live_control_server.services.plan_jev_driver import PlanJevDriver
    from apps.live_control_server.services.plan_jev_rules_runtime import PlanRulesRuntime
    from apps.live_control_server.services.plan_jev_writer import PlanJevWriter
    from application_state.agent_conversation.rules_authority_policy import rules_capability
    from application_state.agent_conversation.native_corpus import NativeBodyProviderIncludedV1, selected_body_reads
    from tests.test_plan_jev_writer import WriterWire
    from generationengine import GenerationEngineError
    a = source_adapter
    a.request = a.request.model_copy(update={'message': 'Whom did Éphanna hear?'})
    a.submitted_intent = owner._submitted_turn_intent(a.request, world_id=a.world_id)
    semantic = PlanJevDispatch.requested_work(a, page_title='Synthetic park Plan')
    asyncio.run(semantic.run(transport=DecisionWire(a), api_key='synthetic-not-secret'))
    rules = PlanRulesRuntime(a, rules_capability(graph=True))
    driver = PlanJevDriver(a)
    proof = asyncio.run(driver.run(transport=SourceChoices(), api_key='synthetic-not-secret'))
    reads = selected_body_reads(a.fence.turn.graph_context_execution)
    assert len(reads) == 1 and reads[0].excerpt.selector_policy == 'native_full_document_v1'
    writer = PlanJevWriter(a, proof, rules)
    wire = WriterWire(a, '{}', status='incomplete')
    # Deliberately stop before answer normalization: this is actual input proof,
    # not a completed-answer or Q01/Q13 acceptance claim.
    with pytest.raises((ValueError, GenerationEngineError)):
        asyncio.run(writer.run(transport=wire, api_key='synthetic-not-secret'))
    assert len(wire.calls) == 1
    raw = wire.calls[0].content.decode()
    body = json.loads(raw)
    frame = json.loads(body['input'][0]['content'])
    evidence = frame['native_body_evidence']
    assert frame['schema'] == 'dmb_plan_jev_writer_frame_v6'
    assert evidence['excerpts'][0]['text'] == BODY
    assert evidence['excerpts'][0]['extent_kind'] == 'full_document'
    assert raw.count(BODY.splitlines()[2]) == 1
    assert a.native_source_authority.revision_id not in raw
    turn = AgentConversationService().list_turns(a.world_id, a.turn.conversation_id)[0]
    included = [e for e in turn.graph_context_execution.events if isinstance(e, NativeBodyProviderIncludedV1)]
    assert len(included) == 1 and included[0].read_event_ids == (reads[0].event_id,)
    assert included[0].envelope_sha256 == writer.prepared.body_sha256
    assert turn.status == 'running' and turn.completion is None


def test_actual_sdk_refuses_accumulated_whole_document_without_full_read(source_adapter, lane):
    from apps.live_control_server.services.plan_jev_driver import PlanJevDriver
    from apps.live_control_server.services.plan_jev_rules_runtime import PlanRulesRuntime
    from apps.live_control_server.services.plan_jev_writer import PlanJevWriter
    from application_state.agent_conversation.rules_authority_policy import rules_capability
    from application_state.agent_conversation.native_corpus import NativeBodyProviderIncludedV1, selected_body_reads
    from tests.test_plan_jev_writer import WriterWire
    from generationengine import GenerationEngineError
    a = source_adapter
    admit(lane, name='multi-section', body='# Meeting\n\nÉphanna heard the guard.\n\n## After\n\nÉphanna reunited with the party.\n')
    a.native_corpus_context, a.native_source_authority = prepare(a.world_id, GM,
        repository=lane.repo, resolve_identity=lambda _: lane.bound)
    a.request = a.request.model_copy(update={'message': 'Whom did Éphanna hear?'})
    a.submitted_intent = owner._submitted_turn_intent(a.request, world_id=a.world_id)
    semantic = PlanJevDispatch.requested_work(a, page_title='Synthetic park Plan')
    asyncio.run(semantic.run(transport=DecisionWire(a), api_key='synthetic-not-secret'))
    rules = PlanRulesRuntime(a, rules_capability(graph=True))
    proof = asyncio.run(PlanJevDriver(a).run(transport=SourceChoices(sections=True), api_key='synthetic-not-secret'))
    reads = selected_body_reads(a.fence.turn.graph_context_execution)
    assert len(reads) == 2 and all(read.excerpt.selector_policy == 'markdown_sections_v1' for read in reads)
    writer = PlanJevWriter(a, proof, rules)
    wire = WriterWire(a, '{}')
    with pytest.raises(GenerationEngineError):
        asyncio.run(writer.run(transport=wire, api_key='synthetic-not-secret'))
    assert wire.calls == []
    turn = AgentConversationService().list_turns(a.world_id, a.turn.conversation_id)[0]
    assert not any(isinstance(event, (NativeBodyProviderIncludedV1, t.PlanJevWriterAuthorizedV1))
        for event in turn.graph_context_execution.events)
