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
def source_adapter(application_state_dsn, monkeypatch, lane, request):
    monkeypatch.setattr('apps.live_control_server.services.agent_graph_policy.resolve_agent_graph_openai_inference',
        lambda **_: ('openai-api', 'gpt-6-luna', 'https://api.openai.com/v1'))
    supplied = getattr(request, 'param', None)
    unique = isinstance(supplied, dict) and supplied.get('unique_world') is True
    world_id = f'world:plan-reader-{uuid4()}' if unique else 'world:one'
    sources = supplied['sources'] if unique else supplied or [('first', BODY)]
    lane.bound.managed_world_id = world_id
    for name, body in sources:
        admit(lane, name, body=body)
    context, authority = prepare(world_id, GM, repository=lane.repo,
        resolve_identity=lambda _: lane.bound)
    request = _pinned_plan_request()
    if unique:
        request = request.model_copy(update={'owner_scope': request.owner_scope.model_copy(update={'world_id': world_id})})
    request = type(request).model_validate(request.model_dump(mode='json', by_alias=True) | {
        'turn_id': str(uuid4()), 'plan_context_policy': {'policy': 'auto_plan_world'},
        'graph_request': {'mode': 'none'}})
    work = _pinned_plan_work('# Synthetic park Plan\nA proposed visit, not a played fact.\n')
    work = replace(work, world_id=world_id, owner_id=world_id, content_basis=work.content_basis.model_copy(update={
        'world_id': world_id, 'content_sha256': sha256(work.plan_markdown.encode()).hexdigest(), 'work_revision_id': str(uuid4())}))
    request = request.model_copy(update={'primary_work': request.primary_work.model_copy(update={
        'expected_content_sha256': work.content_basis.content_sha256})})
    adapter = owner._PolicyExecutionAdapter(service=AgentConversationService(), request=request,
        world_id=world_id, work=work, bootstrap=None, playable_target=None,
        submitted_intent=owner._submitted_turn_intent(request, world_id=world_id), existing_turn=None,
        budget=request_budget(), context_read_enabled=True,
        native_corpus_context=context, native_source_authority=authority)
    adapter._test_creative = bool(unique and supplied.get('no_source'))
    adapter._test_multi = bool(unique and supplied.get('multi_source'))
    adapter._test_long = bool(unique and supplied.get('long_context'))
    adapter._test_missing = bool(unique and supplied.get('missing_source'))
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
    def __init__(self, *, sections=False, direct=False, writer_passages=False, controller_source=False, no_source=False):
        self.controller_source = controller_source
        self.no_source = no_source
        self.calls = []
        self.direct = direct
        self.writer_passages = writer_passages
        self.selected_kinds = []
        self.read_kind = 'Exact source section' if sections else 'Explicit full-document read'

    async def handle_async_request(self, request):
        body = json.loads(request.content)
        self.calls.append(body)
        assert b'source_discovery_mode' not in request.content
        assert b'controller_selection_v1' not in request.content
        assert len(self.calls) <= (5 if self.writer_passages else 4), body['state']
        answers = {}
        selected_kinds = []
        for name, entry in body['questions'].items():
            choice = ('discuss' if name == 'requested_work' else
                      'finish_retrieval' if name == 'operation' else
                      'review_after_reads' if name == 'post_read_plan' else 'exclude')
            if name.startswith('candidate_'):
                candidate = body['state']['candidates'][int(name.split('_')[-1])]
                direct_kind = 'Explicit admitted full-source read; metadata choice, not evidence'
                kinds = ({direct_kind} if self.direct else
                    {'Source lexical navigation; not evidence or semantic completeness', self.read_kind})
                if (not self.direct and self.read_kind == 'Explicit full-document read'
                        and any(c['kind'].startswith('Navigation scan:') for c in body['state'].get('examined_subjects', []))):
                    kinds.add(direct_kind)
                if self.writer_passages:
                    passage_kind = ('Select passage from inspected source' if self.direct
                                    else 'Exact source section')
                    selected = (self.direct and (candidate['kind'] == direct_kind
                        or candidate['kind'].startswith('Expand to all other admitted native sources'))
                        or candidate['kind'] == passage_kind and ' · Witness · ' in candidate['label'])
                else:
                    selected = candidate['kind'] in kinds
                if (self.controller_source and not self.direct
                        and candidate['kind'] == 'Source lexical navigation; not evidence or semantic completeness'):
                    selected = True
                if self.no_source:
                    selected = False
                if selected:
                    choice = 'include'
                    selected_kinds.append(candidate['kind'])
            assert choice in entry['criteria'], (name, choice, entry['criteria'])
            answers[name] = {'type': 'choice', 'choice': choice, 'confidence': 1.0,
                'probabilities': {key: float(key == choice) for key in entry['criteria']}}
        self.selected_kinds.append(tuple(selected_kinds))
        from application_state.agent_conversation.jev_retrieval_contract import MODEL
        return httpx2.Response(200, request=request, json={'model': MODEL, 'answers': answers,
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


def test_actual_sdk_includes_acknowledged_sections_covering_whole_document(source_adapter, lane):
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
    wire = WriterWire(a, '{}', status='incomplete')
    # Stop after the real SDK request, before answer normalization. The source
    # grants compose; an incomplete model reply still must not become an answer.
    with pytest.raises((ValueError, GenerationEngineError)):
        asyncio.run(writer.run(transport=wire, api_key='synthetic-not-secret'))
    assert len(wire.calls) == 1
    frame = json.loads(json.loads(wire.calls[0].content)['input'][0]['content'])
    excerpts = frame['native_body_evidence']['excerpts']
    assert len(excerpts) == len(reads)
    assert {row['text'] for row in excerpts} == {read.excerpt.text for read in reads}
    assert all(row['extent_kind'] == 'section' for row in excerpts)
    turn = AgentConversationService().list_turns(a.world_id, a.turn.conversation_id)[0]
    included = [event for event in turn.graph_context_execution.events
        if isinstance(event, NativeBodyProviderIncludedV1)]
    assert len(included) == 1
    assert set(included[0].read_event_ids) == {read.event_id for read in reads}
    assert any(isinstance(event, t.PlanJevWriterAuthorizedV1) for event in turn.graph_context_execution.events)
    assert turn.completion is None


def stage_source_writer(a):
    from apps.live_control_server.services.plan_jev_driver import PlanJevDriver
    from apps.live_control_server.services.plan_jev_rules_runtime import PlanRulesRuntime
    from apps.live_control_server.services.plan_jev_writer import PlanJevWriter
    from application_state.agent_conversation.rules_authority_policy import rules_capability
    a.request = a.request.model_copy(update={'message': 'Whom did Éphanna hear?'})
    a.submitted_intent = owner._submitted_turn_intent(a.request, world_id=a.world_id)
    semantic = PlanJevDispatch.requested_work(a, page_title='Synthetic park Plan')
    asyncio.run(semantic.run(transport=DecisionWire(a), api_key='synthetic-not-secret'))
    rules = PlanRulesRuntime(a, rules_capability(graph=True))
    proof = asyncio.run(PlanJevDriver(a).run(transport=SourceChoices(), api_key='synthetic-not-secret'))
    return PlanJevWriter(a, proof, rules)


def test_actual_native_body_answer_completes_and_reloads_with_exact_citation(source_adapter):
    from tests.test_plan_jev_writer import WriterWire
    a = source_adapter
    writer = stage_source_writer(a)
    handle = writer.projection.frame['native_body_evidence']['excerpts'][0]['excerpt_handle']
    output = {'schema': 'dmb_surface_evidence_answer_v6', 'limitations': [], 'requested_detail_gaps': [],
        'answer_segments': [{'kind': 'native_body_claim', 'text': 'The source says Éphanna heard the guard.',
            'excerpt_handles': [handle]}]}
    wire = WriterWire(a, json.dumps(output, ensure_ascii=False))
    completed = asyncio.run(writer.run(transport=wire, api_key='synthetic-not-secret'))
    assert completed.status == 'completed' and len(wire.calls) == 1
    assert isinstance(completed.completion, t.SurfaceEvidenceCompletionV5)
    assert completed.completion.answer_context_status == 'source_grounded'
    citation = completed.completion.native_body_citations[0]
    assert citation.selector_policy == 'native_full_document_v1'
    assert not hasattr(citation, 'app_source_revision_id')
    fresh = AgentConversationService().inspect_turn(world_id=a.world_id, turn_id=completed.turn_id)
    assert fresh == completed and fresh.completion.native_body_citations == [citation]


def finish_body_answer(a):
    from tests.test_plan_jev_writer import WriterWire
    writer = stage_source_writer(a)
    handle = writer.projection.frame['native_body_evidence']['excerpts'][0]['excerpt_handle']
    output = {'schema': 'dmb_surface_evidence_answer_v6', 'limitations': [], 'requested_detail_gaps': [],
        'answer_segments': [{'kind': 'native_body_claim', 'text': 'The source says Éphanna heard the guard.',
            'excerpt_handles': [handle]}]}
    completed = asyncio.run(writer.run(transport=WriterWire(a, json.dumps(output)), api_key='synthetic-not-secret'))
    return writer, output, completed


@pytest.mark.parametrize('display_state',['available','unavailable','error'])
def test_native_body_history_replay_and_current_access_open_original_revision(source_adapter, lane, monkeypatch, display_state):
    from apps.live_control_server.services.agent_native_source_sections import open_native_body_excerpt
    from apps.live_control_server.services.agent_source_passages import SourcePassageOpenError
    from application_state.agent_conversation.repository import _plan_ask_history_attribution
    a = source_adapter
    _, _, completed = finish_body_answer(a)
    from application_state.agent_conversation.native_corpus import resolve_retained_body_citation

    citation = completed.completion.native_body_citations[0]
    _, section, retained = resolve_retained_body_citation(completed.graph_context_execution, citation)
    assert section.section_id == citation.section_id and retained == BODY
    with pytest.raises(ValueError, match="retained extent"):
        resolve_retained_body_citation(
            completed.graph_context_execution, citation.model_copy(update={"excerpt_sha256": "0" * 64}),
        )
    for field, substitution in (
        ("catalog_sha256", "0" * 64),
        ("content_sha256", "0" * 64),
        ("source_artifact_id", "foreign-artifact"),
        ("native_source_revision_id", "foreign-revision"),
    ):
        with pytest.raises(ValueError, match="retained source identity"):
            resolve_retained_body_citation(
                completed.graph_context_execution, citation.model_copy(update={field: substitution}),
            )

    from application_state.agent_conversation.native_corpus import (
        PriorBodyCitationReferenceV1, resolve_prior_body_citation,
    )
    current = completed.model_copy(update={"sequence": completed.sequence + 1})
    reference = PriorBodyCitationReferenceV1(turn_id=completed.turn_id,
        completion_sha256=t.canonical_sha256(completed.completion), citation_index=0)
    history_ids = {completed.turn_id}
    assert resolve_prior_body_citation(current, completed, reference, history_turn_ids=history_ids) == (
        completed.completion.answer_segments[citation.segment_index].text, BODY,
    )
    for foreign in (completed, current.model_copy(update={"world_id": "world:foreign"}),
                    current.model_copy(update={"conversation_id": uuid4()})):
        with pytest.raises(ValueError, match="outside the completed conversation history"):
            resolve_prior_body_citation(foreign, completed, reference, history_turn_ids=history_ids)
    with pytest.raises(ValueError, match="outside the completed conversation history"):
        resolve_prior_body_citation(current, completed, reference, history_turn_ids=set())
    with pytest.raises(ValueError, match="retained completion"):
        resolve_prior_body_citation(current, completed,
            reference.model_copy(update={"completion_sha256": "0" * 64}), history_turn_ids=history_ids)

    history = _plan_ask_history_attribution(completed)
    assert isinstance(history, t.PlanEvidenceHistoryAttributionV5)
    assert type(history).model_validate_json(history.model_dump_json()) == history
    replay = owner._completed_turn_replay(a.request, owner={'kind': 'world', 'id': a.world_id}, turn=completed)
    assert replay.answer.text == completed.assistant_text
    assert replay.plan_context.schema_ == 'dmb_agent_plan_source_context_response_v1'
    assert replay.plan_context.completion == completed.completion and replay.plan_context.delivery_replay
    original_revision = completed.graph_context_receipt.source_authority.revision_id
    admit(lane, name='later-head', body='# Later\n\nAnother scene.\n')
    assert lane.repo.get_head('world:test').head_revision_id != original_revision
    display_calls = []
    def display(items, world):
        display_calls.append((items, world))
        if display_state == 'error':raise RuntimeError('Display lookup unavailable')
        return [dict(status=display_state,label='Session 15 recap',campaign_id='longmont-c1',
            session_id='session-15',origin_matches_current_metadata=True)]
    monkeypatch.setattr('apps.live_control_server.services.native_source_display.source_display_metadata',display)
    opened = open_native_body_excerpt(world_id=a.world_id, turn_id=completed.turn_id, citation_index=0,
        principal=GM, repository=lane.repo, resolve_identity=lambda _: lane.bound)
    assert opened.content == BODY and opened.citation == completed.completion.native_body_citations[0]
    assert opened.schema_ == 'dmb_agent_native_body_excerpt_read_v2'
    assert opened.display_label == ('Session 15 recap · campaign: longmont-c1 · session: session-15' if display_state == 'available' else None)
    assert len(display_calls) == 1
    # Current ownership change cannot be bypassed by retained body/trace bytes.
    lane.bound = SimpleNamespace(**(vars(lane.bound) | {'binding_version': 2}))
    with pytest.raises(SourcePassageOpenError, match='native_body_access_unavailable'):
        open_native_body_excerpt(world_id=a.world_id, turn_id=completed.turn_id, citation_index=0,
            principal=GM, repository=lane.repo, resolve_identity=lambda _: lane.bound)
    assert len(display_calls) == 1  # Denied access never reaches presentation lookup.
    refused_service = SimpleNamespace(inspect_turn=lambda **_: pytest.fail('player reached APP/source IO'))
    with pytest.raises(SourcePassageOpenError, match='native_body_access_denied'):
        open_native_body_excerpt(world_id=a.world_id, turn_id=completed.turn_id, citation_index=0,
            principal=SimpleNamespace(role='player'), service=refused_service)


def test_native_body_completion_refuses_producer_scope_and_citation_substitutions(source_adapter):
    from application_state.agent_conversation.native_answer_output import normalize_native_answer, NativeAnswerError
    a = source_adapter
    writer, output, completed = finish_body_answer(a)
    support = a.build_claim_evidence[writer.authorization.provider_attempt_id]
    for changed in (replace(support, context_receipt_sha256='f' * 64),
                    replace(support, provider_attempt_id=uuid4()), replace(support, envelope_sha256='f' * 64)):
        with pytest.raises(NativeAnswerError):
            normalize_native_answer(output, completed, writer.authorization.provider_attempt_id, support=changed)
    for field in ('read_event_id', 'excerpt_sha256', 'native_source_revision_id', 'selector_policy'):
        value = completed.model_dump(mode='json', by_alias=True)
        row = value['completion']['native_body_citations'][0]
        row[field] = (str(uuid4()) if field == 'read_event_id' else '0' * 64 if field == 'excerpt_sha256'
            else 'foreign-revision' if field == 'native_source_revision_id' else 'markdown_sections_v1')
        for event in value['graph_context_execution']['events']:
            if event['kind'] == 'completion_binding':
                event['completion_sha256'] = t.canonical_sha256(value['completion'])
        with pytest.raises(ValueError):
            t.Turn.model_validate(value)
    missing = completed.model_dump(mode='json', by_alias=True)
    events = missing['graph_context_execution']['events']
    events[:] = [event for event in events if event['kind'] != 'native_body_provider_included_v1']
    for sequence, event in enumerate(events): event['sequence'] = sequence
    with pytest.raises(ValueError, match='unique producing inclusion'):
        t.Turn.model_validate(missing)
    # Source answers cannot select an unoffered handle or downgrade their grammar.
    forged = json.loads(json.dumps(output))
    forged['answer_segments'][0]['excerpt_handles'] = ['b-foreign']
    with pytest.raises(NativeAnswerError):
        normalize_native_answer(forged, completed, writer.authorization.provider_attempt_id, support=support)
    with pytest.raises(NativeAnswerError):
        normalize_native_answer(output | {'schema': 'dmb_surface_evidence_answer_v5'}, completed,
            writer.authorization.provider_attempt_id, support=support)
    graph_claim = output | {'answer_segments': [{'kind': 'graph_claim', 'claim_id': 'claim:1',
        'text': 'Forged Graph fact.', 'target_kind': 'assertion', 'target_id': 'assertion:foreign',
        'passage_handles': []}]}
    with pytest.raises(NativeAnswerError):
        normalize_native_answer(graph_claim, completed, writer.authorization.provider_attempt_id, support=support)


def test_source_only_rules_completion_and_reload_has_no_fabricated_graph(source_adapter):
    from apps.live_control_server.services.plan_jev_driver import PlanJevDriver
    from apps.live_control_server.services.plan_jev_rules_runtime import PlanRulesRuntime
    from apps.live_control_server.services.plan_jev_writer import PlanJevWriter
    from application_state.agent_conversation.rules_authority_policy import rules_capability
    from application_state.agent_conversation.rules_authority_reads import MixedCompletedTurnV1
    from tests.test_plan_jev_writer import WriterWire
    from tests.test_rules_lookup_broker import args
    a = source_adapter
    a.request = a.request.model_copy(update={'message': args().question})
    a.submitted_intent = owner._submitted_turn_intent(a.request, world_id=a.world_id)
    semantic = PlanJevDispatch.requested_work(a, page_title='Synthetic park Plan')
    asyncio.run(semantic.run(transport=DecisionWire(a), api_key='synthetic-not-secret'))
    rules = PlanRulesRuntime(a, rules_capability(graph=True))
    proof = asyncio.run(PlanJevDriver(a, rules=rules).run(transport=DecisionWire(a, select_rule=True), api_key='synthetic-not-secret'))
    from application_state.agent_conversation.rules_authority_plan_packet import model_rules_frame
    frame = rules.frame()
    support = model_rules_frame(frame).supports[0]
    output = {'kind': 'rules_answer', 'base_output': None,
        'rules_segments': [{'kind': 'rules_claim', 'text': support.excerpt_text,
            'support_ids': [support.support_id]}], 'ordered_refs': [{'domain': 'rules', 'segment_index': 0}]}
    completed = asyncio.run(PlanJevWriter(a, proof, rules).run(transport=WriterWire(a, json.dumps(output)), api_key='synthetic-not-secret'))
    assert isinstance(completed, MixedCompletedTurnV1)
    assert completed.base_projection.kind == 'unclaimed' and not completed.accepted_binding.graph_used
    assert completed.base_projection.graph_context_receipt.graph_capability is None
    assert completed.accepted_binding.support_table[0].support_id == frame.supports[0].support_id
    assert AgentConversationService().inspect_turn(world_id=a.world_id, turn_id=completed.envelope.turn_id) == completed


HTTP_PASSAGE = '# Witness\n\nÉphanna heard the guard.\n\n'
HTTP_BODY = HTTP_PASSAGE + '# Other scene\n\nUnselected unrelated private context.\n'


@pytest.mark.parametrize('source_adapter', [[('first', HTTP_BODY)],
    {'unique_world': True, 'sources': [('first', HTTP_BODY)]},
    {'unique_world': True, 'no_source': True, 'sources': [('first', HTTP_BODY)]},
    {'unique_world': True, 'multi_source': True, 'sources': [('first', HTTP_BODY), ('second', HTTP_BODY.replace('Éphanna heard the guard.', 'Éphanna heard the bell.'))]},
    {'unique_world': True, 'no_source': True, 'long_context': True, 'sources': [('first', HTTP_BODY)]},
    {'unique_world': True, 'missing_source': True, 'sources': [('first', HTTP_BODY)]}],
    indirect=True, ids=['current-plan-source', 'controller-source', 'controller-creative', 'controller-multi-source', 'controller-long-context', 'controller-missing-source'])
@pytest.mark.parametrize("graph_available", [False, True])
@pytest.mark.parametrize('direct',[False,True])
def test_ordinary_http_plan_source_answer_uses_published_graph_authority(source_adapter, lane, monkeypatch, tmp_path, graph_available,direct):
    from fastapi import FastAPI
    from fastapi.testclient import TestClient
    from apps.live_control_server.routes import agent
    from apps.live_control_server.services import plan_jev_harness
    from apps.live_control_server.services.plan_jev_harness import PlanJevHarness
    from apps.live_control_server.services import managed_world_graph_projection as managed
    from apps.live_control_server.integrations.dungeonmind import native_registry_source
    from tests.test_plan_jev_writer import WriterWire
    a = source_adapter
    creative = a._test_creative
    multi = a._test_multi
    long_context = a._test_long
    missing = a._test_missing
    if missing and direct:
        pytest.skip('Missing-source control covers lexical search')
    if long_context and direct:
        pytest.skip('Long-context control covers creative lexical-free route once')
    if multi and direct:
        pytest.skip('Multi-source control covers lexical selection; direct selection has separate single-source controls')
    request = a.request.model_copy(update={'message': ('Suggest a name for a fictional harbor. The keeper accepts a blue bead at dawn.' if creative else 'What was the secret password?' if missing else 'Whom did Éphanna hear?'),
        'plan_context_policy': t.PlanContextPolicyV2(policy='auto_plan_world', graph_source='reviewed_native_graph')})
    monkeypatch.setenv('DMB_AGENT_GRAPH_AUTH_MODE', 'local_operator')
    monkeypatch.setenv('DMB_AGENT_GRAPH_AUTH_ENVIRONMENT', 'local')
    token = 'synthetic-native-test-token-1234567890'
    monkeypatch.setenv('DMB_AGENT_GRAPH_LOCAL_OPERATOR_TOKEN', token)
    monkeypatch.setattr(agent, 'repo_root', lambda: tmp_path)
    monkeypatch.setattr(agent, 'session_dir', lambda: tmp_path / 'sessions')
    monkeypatch.setattr(agent, '_owner_resolver', lambda _: {'kind': 'world', 'id': a.world_id, 'name': 'Synthetic World'})
    monkeypatch.setattr(agent, '_verified_world_id', lambda world: world)
    monkeypatch.setattr(agent, '_work_resolver', lambda *_: a.work)
    monkeypatch.setattr(agent, '_graph_resolver', lambda *_: pytest.fail('unexpected generic Graph fallback'))
    from apps.live_control_server.services.native_graph_reads import prepare_query
    from application_state.agent_conversation.native_plan_statements import NativePlanQueryUnavailableV1
    graph_calls = []
    def published_graph(*_args, native_query_mode=False, native_source_context=None, native_principal=None, **_kwargs):
        assert native_query_mode, "Fresh Plan selected a classic Graph path"
        graph_calls.append(True)
        if not graph_available:
            return None, NativePlanQueryUnavailableV1(managed_world_id=a.world_id,
                reason='native_graph_binding_unavailable')
        return prepare_query(a.world_id, _args[0].message, native_principal,
            source_context=native_source_context, repository=lane.repo, resolve_binding=lambda _:lane.bound)
    monkeypatch.setattr(agent, "_plan_context_resolver", published_graph)
    monkeypatch.setattr('apps.live_control_server.integrations.dungeonmind.world_graph_reads.direct_services_from_config',
        lambda *_: pytest.fail('Classic fallback in source-only Plan'))
    monkeypatch.setattr(managed, 'resolve_managed_source_identity', lambda _: lane.bound)
    def read_repository(*, verification_cache=None):
        from apps.live_control_server.integrations.dungeonmind.native_corpus_source import _turn_revision_proof
        assert verification_cache is None or verification_cache is _turn_revision_proof
        return lane.repo
    monkeypatch.setattr(native_registry_source, 'repository', read_repository)
    choices = SourceChoices(direct=direct, writer_passages=True, controller_source=True, no_source=creative)
    if creative:
        from apps.live_control_server.integrations.dungeonmind import native_corpus_source
        monkeypatch.setattr(native_corpus_source, 'capture_native_sources',
            lambda **_kw: pytest.fail('Creative turn performed a native source scan'))
    class SourceWriter(WriterWire):
        async def handle_async_request(self, request):
            assert b'source_discovery_mode' not in request.content
            assert b'controller_selection_v1' not in request.content
            if creative:
                final_context_question = long_context and b'What token was accepted at dawn?' in request.content
                if final_context_question:
                    assert b'blue bead at dawn' in request.content, 'Earliest conversation evidence missing'
                self.text = json.dumps({'schema': 'dmb_surface_evidence_answer_v8', 'limitations': [],
                    'answer_segments': [
                        {'kind': 'proposal', 'label': 'invented_idea',
                         'text': 'A blue bead.' if final_context_question else 'Lantern Quay.'}]})
                return await super().handle_async_request(request)
            if missing:
                from application_state.agent_conversation.native_plan_assertions import POLICY
                self.text = json.dumps({'schema': POLICY, 'limitations': ['missing_requested_details', 'partial_retrieval'], 'answer_segments': []})
                return await super().handle_async_request(request)
            import re
            from application_state.agent_conversation.native_evidence_view import PLAN_EVIDENCE_HEADING
            messages = json.loads(request.content)['input']
            evidence = [row for row in messages if row['content'].startswith(PLAN_EVIDENCE_HEADING)]
            assert len(evidence) == 1 and messages[-1] == evidence[0]
            prose = evidence[0]['content']
            assert evidence[0]['role'] == 'user'
            handles = re.findall(r'^\[(body\d+)\] [^\n]+$', prose, re.MULTILINE)
            assert len(handles) == (2 if multi else 1), prose
            handle = handles[0]
            assert 'Éphanna heard the guard.' in prose and HTTP_BODY not in prose
            if multi:
                assert 'Éphanna heard the bell.' in prose, prose
            assert 'Unselected unrelated private context.' not in prose
            assert 'native_body_evidence' not in prose and 'source_artifact_id' not in prose
            authority = self.adapter.turn.graph_context_receipt.source_authority
            assert authority.revision_id not in prose and sha256(HTTP_BODY.encode()).hexdigest() not in prose
            self.excerpt_handle = handle
            from application_state.agent_conversation.native_plan_assertions import POLICY
            self.text = json.dumps({'schema': POLICY, 'limitations': [],
                'answer_segments': [{'kind': 'native_body_claim', 'text': 'The source says Éphanna heard the guard.', 'excerpt_handles': handles}]})
            return await super().handle_async_request(request)
    wire = SourceWriter(None, '')
    class Harness(PlanJevHarness):
        def execute(self, adapter, **kwargs):
            wire.adapter = adapter
            try:
                return super().execute(adapter, **kwargs)
            except BaseException:
                import traceback
                wire.failure = traceback.format_exc()
                raise
    constructions = []
    def factory():
        constructions.append(True)
        return Harness(decision_transport=choices, writer_transport=wire,
            decision_api_key='synthetic-not-secret', writer_api_key='synthetic-not-secret')
    monkeypatch.setattr(plan_jev_harness, 'default_plan_jev_runtime', factory)
    app = FastAPI(); app.include_router(agent.router, prefix='/api/live')
    client = TestClient(app, client=('127.0.0.1', 42000), headers={'Authorization': 'Bearer ' + token})
    response = client.post('/api/live/agent/turn', json=request.model_dump(mode='json', by_alias=True))
    assert response.status_code == 200, response.text + getattr(wire,"failure","")
    data = response.json()
    assert data['plan_context']['schema'] == 'dmb_agent_surface_native_context_response_v1'
    receipt = data['plan_context']['receipt']
    assert receipt['work_context']['surface_id'] == 'plan' and graph_calls == [True]
    assert 'graph_capability' not in receipt
    if graph_available:
        assert receipt['native_query']['authority']['revision_id'] == receipt['source_authority']['revision_id']
        assert receipt['native_query']['question'] == request.message
    else:
        assert receipt['native_query']['schema'] == 'dmb_native_plan_query_unavailable_v1'
    assert data['answer']['status'] == 'ok' and not data['answer']['graph_grounded']
    assert len(wire.calls) == len(constructions) == 1
    if creative:
        from application_state.agent_conversation.native_corpus import (
            NativeBodySearchAuthorizedV1, NativePlanRequestSearchAuthorizedV1,
            NativeBodyReadAuthorizedV1, NativeDirectSourceAuthorizedV1,
        )
        turn = wire.adapter.turn
        assert turn.graph_context_execution.policy.action.source_discovery_mode == 'controller_selection_v1'
        assert not any(isinstance(e, (NativeBodySearchAuthorizedV1, NativePlanRequestSearchAuthorizedV1,
                                      NativeBodyReadAuthorizedV1, NativeDirectSourceAuthorizedV1))
                       for e in turn.graph_context_execution.events)
        assert 'Lantern Quay' in turn.assistant_text
        replay = client.post('/api/live/agent/turn', json=request.model_dump(mode='json', by_alias=True))
        assert replay.status_code == 200 and replay.json()['plan_context']['delivery_replay']
        assert len(wire.calls) == len(constructions) == 1
        if long_context:
            for index in range(10):
                choices.calls.clear()
                followup = request.model_copy(update={'turn_id': str(uuid4()),
                    'message': ('What token was accepted at dawn?' if index == 9 else f'Consider harbor detail {index}.')})
                response = client.post('/api/live/agent/turn', json=followup.model_dump(mode='json', by_alias=True))
                assert response.status_code == 200, response.text + getattr(wire, 'failure', '')
                turn = wire.adapter.turn
                assert not any(isinstance(event, (NativeBodySearchAuthorizedV1, NativePlanRequestSearchAuthorizedV1,
                    NativeBodyReadAuthorizedV1, NativeDirectSourceAuthorizedV1)) for event in turn.graph_context_execution.events)
            assert 'blue bead' in turn.assistant_text
        return
    selection_count = len(choices.calls)
    if missing:
        from application_state.agent_conversation.native_corpus import (
            NativeBodySearchAuthorizedV1, NativePlanRequestSearchAuthorizedV1, NativeBodyReadObservedV1,
        )
        turn = wire.adapter.turn
        events = turn.graph_context_execution.events
        assert not any(type(event) is NativePlanRequestSearchAuthorizedV1 for event in events)
        assert sum(type(event) is NativeBodySearchAuthorizedV1 for event in events) == 1
        assert not any(type(event) is NativeBodyReadObservedV1 for event in events)
        completed = wire.adapter.service.inspect_turn(world_id=a.world_id, turn_id=turn.turn_id)
        assert not completed.completion.native_body_citations
        assert any(item.code in ('missing_requested_details', 'partial_retrieval') for item in completed.completion.limitations)
        return
    if multi:
        from application_state.agent_conversation.native_corpus import (
            NativeBodySearchAuthorizedV1, NativePlanRequestSearchAuthorizedV1,
            NativeBodyReadObservedV1,
        )
        turn = wire.adapter.turn
        events = turn.graph_context_execution.events
        assert turn.graph_context_execution.policy.action.source_discovery_mode == 'controller_selection_v1'
        assert not any(type(event) is NativePlanRequestSearchAuthorizedV1 for event in events)
        assert sum(type(event) is NativeBodySearchAuthorizedV1 for event in events) == 1
        reads = [event for event in events if type(event) is NativeBodyReadObservedV1]
        assert len(reads) == 2
        completed = wire.adapter.service.inspect_turn(world_id=a.world_id, turn_id=turn.turn_id)
        citations = completed.completion.native_body_citations
        assert len(citations) == 2
        assert {citation.read_event_id for citation in citations} == {read.event_id for read in reads}
        assert len({citation.source_artifact_id for citation in citations}) == 2
        for index in range(2):
            opened = client.get(f'/api/live/agent/worlds/{a.world_id}/conversation/turns/{turn.turn_id}/native-body-excerpts/{index}')
            assert opened.status_code == 200
            assert opened.json()['content'] in (HTTP_PASSAGE, HTTP_PASSAGE.replace('guard.', 'bell.'))
        replay = client.post('/api/live/agent/turn', json=request.model_dump(mode='json', by_alias=True))
        assert replay.status_code == 200 and replay.json()['plan_context']['delivery_replay']
        assert len(wire.calls) == len(constructions) == 1 and len(choices.calls) == selection_count
        return
    groups = [group for group in choices.selected_kinds if group]
    if not direct:
        assert groups[0] == ('Source lexical navigation; not evidence or semantic completeness',)
        assert groups[-1] == ('Exact source section',)
    else:
        assert groups == [
            ('Explicit admitted full-source read; metadata choice, not evidence',),
            ('Select passage from inspected source',),
        ]
    assert 'max_output_tokens' not in json.loads(wire.calls[0].content)
    turn = wire.adapter.turn
    from application_state.agent_conversation.native_corpus import (
        NativeDirectSourceAuthorizedV1, NativeDirectSourceObservedV1,
        NativeBodySearchAuthorizedV1, NativePlanRequestSearchAuthorizedV1,
        NativeBodyReadAuthorizedV1, NativeBodyReadObservedV1, NativeBodySearchObservedV1,
    )
    events = turn.graph_context_execution.events
    assert turn.graph_context_execution.policy.action.source_discovery_mode == 'controller_selection_v1'
    assert not any(type(e) is NativePlanRequestSearchAuthorizedV1 for e in events)
    assert sum(type(e) is NativeBodySearchAuthorizedV1 for e in events) == (0 if direct else 1)
    read_type = NativeDirectSourceObservedV1 if direct else NativeBodyReadObservedV1
    grant_type = NativeDirectSourceAuthorizedV1 if direct else NativeBodyReadAuthorizedV1
    reads = [e for e in events if type(e) is read_type]
    grants = [e for e in events if type(e) is grant_type]
    assert len(reads) == len(grants) == 1
    assert sum(isinstance(e, NativeBodyReadObservedV1) for e in events) == 1
    assert reads[0].authorization_event_id == grants[0].event_id
    assert grants[0].sequence < reads[0].sequence
    if direct:
        catalog = reads[0].catalog
        assert reads[0].excerpt.selector_policy == 'native_full_document_v1'
        assert catalog.source.artifact.source_artifact_id == grants[0].source_artifact_id
        assert catalog.source.revision.source_revision_id == grants[0].source_revision_id
    else:
        catalogs = [c for event in events if type(event) is NativeBodySearchObservedV1
                    for c in event.catalogs if c.catalog_sha256 == reads[0].excerpt.catalog_sha256]
        catalog, = catalogs
        assert reads[0].excerpt.selector_policy == 'markdown_sections_v1'
        assert grants[0].catalog_sha256 == catalog.catalog_sha256
    from application_state.agent_conversation.native_corpus import native_body_handle
    from application_state.agent_conversation.native_execution import NativePlanActionV2, NativeWriterAuthorizedV1
    from application_state.agent_conversation.native_retrieval import native_selection_types
    assert type(turn.graph_context_execution.policy.action) is NativePlanActionV2
    section, = [s for s in catalog.sections if s.label == 'Witness']
    handle = native_body_handle(catalog.catalog_sha256, section.section_id)
    assert any(handle in event.selected_handles
               and (event.sequence > reads[0].sequence if direct else event.sequence < grants[0].sequence)
               for event in events if isinstance(event, native_selection_types()))
    producing, = [event for event in events if isinstance(event, NativeWriterAuthorizedV1)]
    assert reads[0].event_id in producing.native_read_event_ids
    completed = wire.adapter.service.inspect_turn(world_id=a.world_id, turn_id=turn.turn_id)
    citation, = completed.completion.native_body_citations
    assert citation.read_event_id == reads[0].event_id and citation.catalog_sha256 == catalog.catalog_sha256
    assert citation.source_artifact_id == catalog.source.artifact.source_artifact_id
    assert citation.native_source_revision_id == catalog.source.revision.source_revision_id
    assert citation.content_sha256 == sha256(HTTP_BODY.encode()).hexdigest()
    assert citation.selector_policy == reads[0].excerpt.selector_policy
    assert citation.excerpt_sha256 == sha256(HTTP_PASSAGE.encode()).hexdigest()
    if direct:
        assert citation.section_id != reads[0].excerpt.section.section_id  # Derived passage, original read identity.
    else:
        assert citation.section_id == section.section_id
    assert (citation.line_start, citation.line_end) == (section.line_start, section.line_end) == (1, 4)
    assert 0 < section.byte_end - section.byte_start < catalog.body_bytes
    admit(lane, name='head-after-http-answer', body='# Later\n\nAnother event.\n')
    opened = client.get(f'/api/live/agent/worlds/{a.world_id}/conversation/turns/{turn.turn_id}/native-body-excerpts/0')
    assert opened.status_code == 200, opened.text
    assert opened.json()['content'] == HTTP_PASSAGE
    assert opened.json()['citation'] == citation.model_dump(mode='json', by_alias=True)
    replay = client.post('/api/live/agent/turn', json=request.model_dump(mode='json', by_alias=True))
    assert replay.status_code == 200, replay.text
    assert replay.json()['plan_context']['completion'] == data['plan_context']['completion']
    assert replay.json()['plan_context']['delivery_replay']
    assert len(wire.calls) == len(constructions) == 1 and len(choices.calls) == selection_count
    assert graph_calls == [True]  # Original completion reopens without reacquiring current Graph authority.
    history = client.get(f'/api/live/agent/worlds/{a.world_id}/conversation?include_turn_correlation=true')
    assert history.status_code == 200, history.text
    assert history.json()['turns'][0]['plan_context']['completion'] == data['plan_context']['completion']
    target = f'/api/live/agent/worlds/{a.world_id}/conversation/turns/{turn.turn_id}/native-body-excerpts/0'
    invalid = client.get(target + '?source=foreign')
    assert invalid.status_code == 422
    lane.bound = SimpleNamespace(**(vars(lane.bound) | {'binding_version': 2}))
    denied = client.get(target)
    assert denied.status_code == 409 and denied.json()['detail']['code'] == 'native_body_access_unavailable'
    assert len(wire.calls) == len(constructions) == 1 and len(choices.calls) == selection_count


@pytest.mark.parametrize('source_adapter', [[
    ('first', '---\ntitle: Session 1\n---\nThe session describes a market.\n'),
    ('second', '---\ntitle: Session 29\n---\nBrin told the group about Edge.\n'),
]], indirect=True)
def test_actual_controller_full_document_offers_keep_distinctive_query_matches(source_adapter):
    from apps.live_control_server.services.plan_jev_driver import PlanJevDriver
    a = source_adapter
    a.request = a.request.model_copy(update={'message': 'What did Brin tell the group in Session 29?'})
    a.submitted_intent = owner._submitted_turn_intent(a.request, world_id=a.world_id)
    semantic = PlanJevDispatch.requested_work(a, page_title='Synthetic park Plan')
    asyncio.run(semantic.run(transport=DecisionWire(a), api_key='synthetic-not-secret'))
    wire = SourceChoices()
    asyncio.run(PlanJevDriver(a).run(transport=wire, api_key='synthetic-not-secret'))
    offers = next(call['state']['candidates'] for call in wire.calls
        if any(c['kind'] == 'Explicit full-document read' for c in call['state']['candidates']))
    documents = [c for c in offers if c['kind'] == 'Explicit full-document read']
    assert len(documents) == 2
    assert len({c['label'] for c in documents}) == 2
    assert all('matched terms:' in c['label'] for c in documents)
    assert sum('29' in c['label'] and 'brin' in c['label'] for c in documents) == 1
    assert all('Brin told the group about Edge.' not in c['label'] for c in documents)
    from application_state.agent_conversation.native_corpus import selected_body_reads
    reads = selected_body_reads(a.fence.turn.graph_context_execution)
    assert len(reads) == 2
    assert all(read.excerpt.selector_policy == 'native_full_document_v1' for read in reads)


@pytest.mark.parametrize("family", ["plan-v1", "plan-v2", "build"])
@pytest.mark.parametrize("covered", [False, True])
def test_batch_coverage_preserves_exact_native_plan_passage_requirement(monkeypatch, family, covered):
    from application_state.agent_conversation import native_corpus, plan_jev_decision
    from application_state.agent_conversation.native_execution import NativePlanActionV2
    from apps.live_control_server.services.corpus_source_navigation import NativeBodyNavigation
    from tests.test_surface_native_execution import component

    _, record = component("build" if family == "build" else "plan", unavailable=True)
    policy = record.policy
    if family == "plan-v2":
        previous = policy.action.model_dump(mode="python", by_alias=True)
        previous.pop("action_version", None)
        action = NativePlanActionV2(**previous, related_page_catalog=())
        policy = type(policy).model_validate(policy.model_dump(mode="python") | {"action": action})
    execution = SimpleNamespace(policy=policy)
    turn = SimpleNamespace(graph_context_execution=execution)
    selection = object()
    monkeypatch.setattr(plan_jev_decision, "current_selection", lambda actual: selection if actual is turn else None)
    calls = []
    def covering(actual_execution, actual_selection, handle, *, require_passage):
        assert actual_execution is execution and actual_selection is selection
        assert handle == "native-body:exact"
        calls.append(require_passage)
        return (uuid4(),) if covered else ()
    monkeypatch.setattr(native_corpus, "selected_batch_covering_reads", covering)
    navigator = object.__new__(NativeBodyNavigation)
    navigator.adapter = SimpleNamespace(fence=SimpleNamespace(turn=turn))
    assert navigator._fulfilled_in_current_selection("native-body:exact") is covered
    assert calls == [family == "plan-v2"]


def test_shared_legacy_plan_action_builder_keeps_historical_mode(monkeypatch):
    from apps.live_control_server.services import build_related_pages, plan_source_turn
    from tests.test_agent_turn_service import _pinned_plan_request, _pinned_plan_work

    request = _pinned_plan_request().model_copy(update={
        'plan_context_policy': t.PlanContextPolicyV2(policy='auto_plan_world', graph_source='reviewed_native_graph'),
    })
    work = _pinned_plan_work('# Synthetic legacy Plan\n')
    work = replace(work, content_basis=work.content_basis.model_copy(update={'work_revision_id': str(uuid4())}))
    intent = owner._submitted_turn_intent(request, world_id='world:one')
    monkeypatch.setattr(build_related_pages, 'discover', lambda _request: ())
    _, action = plan_source_turn._native_plan_parts(
        request, plan_source_turn._plan_basis(work), None, intent)
    assert action.source_discovery_mode is None
    assert 'source_discovery_mode' not in action.model_dump(mode='json', by_alias=True)
