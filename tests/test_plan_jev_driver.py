"""Actual Jev/APP decisions with receipt-producing synthetic local reads."""
import asyncio
from contextlib import contextmanager
from hashlib import sha256
import json
from uuid import uuid4

import httpx2
import pytest
from application_state.agent_conversation import types as t
from application_state.agent_conversation.plan_jev_graph_packet import project
from application_state.agent_conversation.rules_authority_types import canonical_sha256
from graph_memory.interaction.session import GraphReferent
from apps.live_control_server.services.plan_jev_driver import PlanJevDriver
from tests.test_plan_jev_dispatch import plan_adapter  # noqa: F401


def fixture_reads(adapter, *, anchors=1, body_chars=None):
    graph_calls, source_calls = [], []
    adapter._test_source_acquisitions = []
    @contextmanager
    def acquisition(anchor_ids):
        adapter._test_source_acquisitions.append(tuple(anchor_ids))
        yield
    adapter.source_read_acquisition = acquisition
    def graph(message):
        arguments = message['arguments']; graph_calls.append(arguments)
        operation = arguments['operation']; node = arguments.get('targets', [{'id': 'discovery'}])[0]['id']
        execution = adapter._broker_execution(); authority = adapter._broker_receipt().graph_authority
        refs = sorted(f'evidence:park:{i}' for i in range(anchors))
        pins = [t.GraphSourceScopeAnchorV2(anchor_id=f'anchor:park:{i}', evidence_ref_id=ref,
            source_artifact_id='artifact:park', source_revision_id='revision:park:1') for i, ref in enumerate(refs)]
        pins.sort(key=lambda pin: pin.anchor_id)
        packet = {'schema': 'dmb_world_graph_retrieval_result_v1', 'snapshot': {
            'worldId': authority.native_world_id, 'revisionId': authority.graph_revision},
            'nodes': [{'nodeId': 'pond', 'label': 'Park pond', 'kind': 'location'},
                      {'nodeId': 'bridge', 'label': 'Footbridge', 'kind': 'location'}],
            'attributes': [] if operation == 'search' else [{'assertionId': f'assertion:{node}',
                'subjectNodeId': node, 'predicate': 'description', 'value': 'A recorded wooden walkway',
                'epistemicKind': 'reported', 'temporalScope': 'past', 'evidenceRefIds': refs}],
            'sourceAnchors': [] if operation == 'search' else [{'anchorId': pin.anchor_id,
                'evidenceRefId': pin.evidence_ref_id, 'readable': True} for pin in pins]}
        event = t.ValidatedGraphOperationEventV3(kind='validated_graph_operation_v3', event_id=uuid4(),
            sequence=len(execution.events), operation_id=uuid4(), operation='expand_graph_retrieval',
            request_arguments_sha256=canonical_sha256(arguments), graph_revision=authority.graph_revision,
            result_packet_sha256=canonical_sha256(packet), assertion_ids=[] if operation == 'search' else [f'assertion:{node}'],
            relationship_ids=[], evidence_ref_ids=[] if operation == 'search' else refs,
            evidence_sufficiency_status='insufficient' if operation == 'search' else 'sufficient',
            coverage_status='complete', truncated=False, source_opened=False, returned_source_pins=[] if operation == 'search' else pins)
        adapter.turn, _ = adapter.fence.append('append_validated_graph_operation', 'operation_event', event)
        if event.returned_source_pins:
            execution = adapter._broker_execution(); scope = execution.policy.source_read_scope
            extension = t.SourceScopeExtensionEventV3(kind='source_scope_extension_v3', event_id=uuid4(),
                sequence=len(execution.events), origin_graph_event_id=event.event_id,
                context_receipt_sha256=execution.context_receipt_sha256, execution_policy_sha256=execution.execution_policy_sha256,
                world_id=adapter.world_id, native_world_id=authority.native_world_id, binding_version=authority.binding_version,
                campaign_id=None, graph_revision=authority.graph_revision, retrieval_session_id=scope.retrieval_session_id, pins=pins)
            adapter.turn, _ = adapter.fence.append('extend_source_scope', 'extension', extension)
        raw = json.dumps(packet | {'retrievalSessionId': adapter.bootstrap.retrieval_session.id, 'addedClaimIds': [], 'claimLedger': []})
        adapter.operation_payloads[event.event_id] = raw
        return {'resultJson': raw, 'retrievalSession': None}
    def source(message, *, bundle_internal):
        arguments = message['arguments']; source_calls.append(arguments)
        execution = adapter._broker_execution(); scope = execution.policy.source_read_scope
        pins = execution.effective_source_pins()
        auth = t.SourceReadAuthorizationEventV2(kind='source_read_authorized_v2', event_id=uuid4(),
            sequence=len(execution.events), read_call_id=uuid4(), context_receipt_sha256=execution.context_receipt_sha256,
            execution_policy_sha256=execution.execution_policy_sha256, retrieval_session_id=scope.retrieval_session_id,
            world_id=scope.world_id, campaign_id=None, graph_revision=scope.graph_revision,
            anchors=[pins[key] for key in arguments['anchorIds']], max_chars=arguments['maxChars'])
        adapter.turn, _ = adapter.fence.append('authorize_source_read', 'authorization', auth)
        receipts, results = [], []
        for anchor in arguments['anchorIds']:
            pin = pins[anchor]; text = f'The park account describes the walkway at {anchor}.'
            if body_chars is not None: text = text.ljust(body_chars, '.')
            receipt = t.SourceReadAnchorReceiptV2(source_read_id=f'read:{anchor}', anchor_id=anchor,
                evidence_ref_id=pin.evidence_ref_id, source_artifact_id=pin.source_artifact_id,
                source_revision_id=pin.source_revision_id, outcome='enough', content_sha256=sha256(text.encode()).hexdigest(),
                line_start=1, line_end=1, returned_chars=len(text), truncated=False, evidence_sufficiency_status='sufficient')
            receipts.append(receipt)
            results.append({'anchorId': anchor, 'sourceName': 'Synthetic park journal', 'content': text,
                'lineStart': 1, 'lineEnd': 1, 'outcome': 'enough'})
        event = t.ValidatedSourceReadEventV2(kind='validated_source_read_v2', event_id=uuid4(),
            sequence=len(adapter._broker_execution().events), read_call_id=auth.read_call_id, receipts=receipts)
        adapter.turn, fresh, captured = adapter.context_capture.persist_source_receipt(event, results,
            world_id=scope.world_id, graph_revision=scope.graph_revision)
        assert fresh and captured
        raw = json.dumps({'reads': results})
        adapter.source_payloads[event.event_id] = raw
        return {'resultJson': raw, 'retrievalSession': None}
    adapter.broker_graph_operation, adapter.broker_source_read = graph, source
    return graph_calls, source_calls


class Decisions(httpx2.AsyncBaseTransport):
    def __init__(self, *, sequential=False, discover=False):
        self.calls = []; self.sequential, self.discover = sequential, discover
    async def handle_async_request(self, request):
        body = json.loads(request.content); self.calls.append(body)
        candidates = body['state']['candidates']
        operation = 'select_candidates' if candidates else ('discover_more' if self.discover and len(self.calls) == 1 else 'finish_retrieval')
        answers = {}
        for name, question in body['questions'].items():
            choice = ('finish_retrieval' if operation == 'select_candidates' else operation) if name == 'operation' else (
                'include' if operation == 'select_candidates' and (not self.sequential or name == 'candidate_0') else 'exclude')
            answers[name] = {'type': 'choice', 'choice': choice, 'confidence': 1.0,
                'probabilities': {key: float(key == choice) for key in question['criteria']}}
        return httpx2.Response(200, request=request, json={'model': 'jev-1.14.0', 'answers': answers, 'usage': {}})


@pytest.mark.parametrize('sequential', [False, True])
@pytest.mark.parametrize('anchors', [1, 11, 45])
def test_shared_anchors_and_objects_read_once_with_actual_plan_decisions(plan_adapter, sequential, anchors):
    plan_adapter.bootstrap.retrieval_session.referents = [GraphReferent(id='pond', label='Park pond'),
                                                         GraphReferent(id='bridge', label='Footbridge')]
    graphs, sources = fixture_reads(plan_adapter, anchors=anchors)
    driver = PlanJevDriver(plan_adapter, dialogue=[{'role': 'user', 'content': 'Earlier park discussion.'}])
    transport = Decisions(sequential=sequential)
    proof = asyncio.run(driver.run(transport=transport, api_key='synthetic-not-secret'))
    assert [row['targets'][0]['id'] for row in graphs] == ['pond', 'bridge']
    assert len(sources) == (1 if anchors == 1 else 2 if anchors == 11 else 7)
    read_anchors = [anchor for call in sources for anchor in call['anchorIds']]
    assert len(read_anchors) == len(set(read_anchors)) == anchors
    assert all(call['maxChars'] == 12000 for call in sources)
    assert len(plan_adapter._test_source_acquisitions) == 1
    assert len(plan_adapter._test_source_acquisitions[0]) == anchors
    frame = project(plan_adapter.fence.turn, proof,
        plan_adapter.context_capture.trace.model_dump(mode='json')).frame
    assert len(frame['graph_records']) == 2 and len(frame['opened_passages']) == anchors
    assert all(row['source_name'] == 'Synthetic park journal' for row in frame['opened_passages'])
    assert len(driver.calls) == len(transport.calls) == (3 if sequential else 2)
    assert frame['dialogue_reference'] == [{'role': 'user', 'content': 'Earlier park discussion.'}]
    assert set(transport.calls[0]['state']) == {'question', 'candidates', 'dialogue_reference'}
    assert all(set(body['state']) == {'question', 'candidates', 'dialogue_reference', 'examined_subjects'}
        for body in transport.calls[1:])
    assert transport.calls[-1]['state']['examined_subjects'] == [
        {'label': 'Park pond', 'kind': 'World entity'}, {'label': 'Footbridge', 'kind': 'World entity'}]
    assert all(body['state']['dialogue_reference'] == frame['dialogue_reference'] for body in transport.calls)


def test_discovery_uses_full_question_once_and_selects_new_node_labels(plan_adapter):
    graphs, sources = fixture_reads(plan_adapter)
    driver = PlanJevDriver(plan_adapter)
    proof = asyncio.run(driver.run(transport=Decisions(discover=True), api_key='synthetic-not-secret'))
    assert [row['operation'] for row in graphs] == ['search', 'object', 'object']
    assert graphs[0]['queryText'] == plan_adapter.request.message
    assert len(sources) == 1 and len(proof['graph_packets']) == 3 and driver.finished


def test_unavailable_source_is_not_retried_and_gap_reaches_writer(plan_adapter):
    plan_adapter.bootstrap.retrieval_session.referents = [GraphReferent(id='pond', label='Park pond'),
                                                         GraphReferent(id='bridge', label='Footbridge')]
    fixture_reads(plan_adapter)
    calls = []
    def unavailable(message, **kwargs):
        calls.append(message)
        return plan_adapter._denied_tool_result('read_graph_source', 'source_anchor_unavailable', 409,
            'The source is unavailable.', arguments=message['arguments'])
    plan_adapter.broker_source_read = unavailable
    driver = PlanJevDriver(plan_adapter)
    proof = asyncio.run(driver.run(transport=Decisions(sequential=True), api_key='synthetic-not-secret'))
    assert len(calls) == 1 and driver.gaps == ['source_anchor_unavailable']
    frame = project(plan_adapter.fence.turn, proof, plan_adapter.context_capture.trace.model_dump(mode='json')).frame
    assert frame['opened_passages'] == [] and frame['unopened_evidence'] == ['e0']
    assert frame['retrieval_gaps'] == [{'operation': 'source_read', 'reason': 'source_anchor_unavailable'}]


def test_changed_selection_cannot_trigger_host_reads(plan_adapter):
    from application_state.agent_conversation.jev_retrieval_contract import RetrievalSelection
    from apps.live_control_server.services.plan_jev_dispatch import PlanJevDispatch
    plan_adapter.bootstrap.retrieval_session.referents = [GraphReferent(id='pond', label='Park pond')]
    graphs, sources = fixture_reads(plan_adapter)
    driver = PlanJevDriver(plan_adapter)
    dispatch = PlanJevDispatch(plan_adapter, driver.offered())
    asyncio.run(dispatch.run(transport=Decisions(), api_key='synthetic-not-secret'))
    driver.current = dispatch
    dispatch.selection = RetrievalSelection(operation='discover_more', selected_handles=())
    with pytest.raises(ValueError, match='no longer current'): driver.apply(dispatch)
    assert graphs == sources == []


def test_newer_unknown_provider_invalidates_old_selection_before_io(plan_adapter):
    from generationengine import GenerationEngineError
    from apps.live_control_server.services.plan_jev_dispatch import PlanJevDispatch
    plan_adapter.bootstrap.retrieval_session.referents = [GraphReferent(id='pond', label='Park pond')]
    graphs, sources = fixture_reads(plan_adapter)
    driver = PlanJevDriver(plan_adapter)
    first = PlanJevDispatch(plan_adapter, driver.offered())
    asyncio.run(first.run(transport=Decisions(), api_key='synthetic-not-secret'))
    driver.current = first
    class Unknown(httpx2.AsyncBaseTransport):
        async def handle_async_request(self, request): raise httpx2.ReadTimeout('synthetic unknown', request=request)
    following = PlanJevDispatch(plan_adapter, driver.offered())
    with pytest.raises(GenerationEngineError):
        asyncio.run(following.run(transport=Unknown(), api_key='synthetic-not-secret'))
    with pytest.raises(ValueError, match='no longer current'): driver.apply(first)
    assert graphs == sources == []


@pytest.mark.parametrize('case', ['foreign_target', 'unselected_search', 'unselected_neighborhood', 'newer_provider'])
def test_actual_graph_boundary_refuses_unselected_or_stale_decision_before_native_io(plan_adapter, monkeypatch, case):
    from generationengine import GenerationEngineError
    from application_state.agent_conversation.jev_retrieval_contract import RetrievalCandidate
    from apps.live_control_server.services.plan_jev_dispatch import PlanJevDispatch
    a = plan_adapter
    selected = RetrievalCandidate(handle='node:pond', label='Park pond', kind='location')
    first = PlanJevDispatch(a, (selected,))
    asyncio.run(first.run(transport=Decisions(), api_key='synthetic-not-secret'))
    if case == 'newer_provider':
        class Unknown(httpx2.AsyncBaseTransport):
            async def handle_async_request(self, request): raise httpx2.ReadTimeout('synthetic unknown', request=request)
        with pytest.raises(GenerationEngineError):
            asyncio.run(PlanJevDispatch(a, (selected,)).run(transport=Unknown(), api_key='synthetic-not-secret'))
    monkeypatch.setattr('apps.live_control_server.integrations.dungeonmind.world_graph_reads.direct_services_from_config',
        lambda *_args, **_kwargs: pytest.fail('unauthorized Plan acquisition reached native IO'))
    arguments = {'retrievalSessionId': a.bootstrap.retrieval_session.id, 'operation': 'object',
        'targets': [{'kind': 'node', 'id': 'bridge' if case == 'foreign_target' else 'pond'}]}
    if case == 'unselected_search': arguments = {'retrievalSessionId': a.bootstrap.retrieval_session.id,
        'operation': 'search', 'queryText': a.request.message}
    if case == 'unselected_neighborhood': arguments['operation'] = 'neighborhood'
    reply = a.broker_graph_operation({'toolName': 'expand_graph_retrieval', 'arguments': arguments})
    assert json.loads(reply['resultJson'])['code'] == 'plan_jev_acquisition_not_current'
    assert a.operation_payloads == {} and a.failure is None


def test_large_anchor_catalog_preserves_exhausted_character_policy(plan_adapter):
    plan_adapter.bootstrap.retrieval_session.referents = [GraphReferent(id='pond', label='Park pond')]
    graphs, sources = fixture_reads(plan_adapter, anchors=45, body_chars=12000)
    driver = PlanJevDriver(plan_adapter)
    proof = asyncio.run(driver.run(transport=Decisions(), api_key='synthetic-not-secret'))
    assert len(graphs) == 2 and len(sources) == 1
    assert len(plan_adapter._test_source_acquisitions) == 1
    assert len(driver.attempted_anchors) == 45
    assert len(sources[0]['anchorIds']) == 8
    execution = plan_adapter._broker_execution()
    assert t.source_read_character_usage(execution.policy, execution.events) == 96000
    frame = project(plan_adapter.fence.turn, proof,
        plan_adapter.context_capture.trace.model_dump(mode='json')).frame
    assert len(frame['opened_passages']) == 8
    assert driver.gaps == ['source_read_over_budget']
    assert frame['retrieval_gaps'] == [{'operation': 'source_read', 'reason': 'source_read_over_budget'}]


def test_actual_plan_graph_broker_does_not_build_unusable_recap_routes(plan_adapter, monkeypatch):
    from types import SimpleNamespace
    from graph_memory.retrieval.models import WorldGraphRetrievalResult
    from apps.live_control_server.services.plan_jev_dispatch import PlanJevDispatch
    from application_state.agent_conversation.jev_retrieval_contract import RetrievalCandidate
    a = plan_adapter
    selected = RetrievalCandidate(handle='node:pond', label='Park pond', kind='location')
    asyncio.run(PlanJevDispatch(a, (selected,)).run(transport=Decisions(), api_key='synthetic-not-secret'))
    world=a.bootstrap.world_scope.world_id
    revision=a.bootstrap.world_scope.revision_id
    result=WorldGraphRetrievalResult.model_validate({
        'operation':'object','outcome':'enough',
        'snapshot':{'worldId':world,'campaignId':'','revisionId':revision,'headRevisionId':revision,
            'isHead':True,'scopeMode':'world','admissibility':'gm','focus':{'kind':'none'}},
        'resolvedNodeId':'pond','matchedNodeIds':['pond'],
        'nodes':[{'nodeId':'pond','label':'Park pond','kind':'location','role':'target'}],
        'attributes':[{'assertionId':'assertion:pond','subjectNodeId':'pond','value':{'summary':'A park pond'},
            'evidenceRefIds':['evidence:pond']}],
        'sourceAnchors':[{'anchorId':'anchor:pond','revisionId':revision,'evidenceRefId':'evidence:pond',
            'sourceArtifactId':'artifact:pond','sourceDomain':'session_recap','readable':True,
            'locatorKind':'source_span','supportingAssertionIds':['assertion:pond']}]})
    pin=SimpleNamespace(anchor_id='anchor:pond',evidence_ref_id='evidence:pond',source_artifact_id='artifact:pond',
        source_revision_id='source:pond:1',graph_revision=revision)
    native=SimpleNamespace(result=result,source_pins=(pin,),reviewed_source_observations=(),
        observation_gap_codes=(),observation_missing_ids=())
    monkeypatch.setattr('apps.live_control_server.integrations.dungeonmind.world_graph_reads.direct_services_from_config',lambda *_:object())
    monkeypatch.setattr('apps.live_control_server.integrations.dungeonmind.world_graph_reads.get_object_with_reviewed_sources_direct_v3',lambda *_:native)
    monkeypatch.setattr(a,'_related_recap_offers',lambda *_:pytest.fail('Plan Jev cannot consume recap routes'))
    reply=a.broker_graph_operation({'toolName':'expand_graph_retrieval','arguments':{
        'retrievalSessionId':a.bootstrap.retrieval_session.id,'operation':'object','targets':[{'kind':'node','id':'pond'}]}})
    assert a.failure is None
    assert 'resultJson' in reply
    packet=json.loads(next(iter(a.operation_payloads.values())))
    assert packet['attributes'][0]['assertionId']=='assertion:pond'
    assert packet['sourceAnchors'][0]['anchorId']=='anchor:pond'
    assert 'relatedRecapContexts' not in packet
    event=next(e for e in a._broker_execution().events if e.kind=='validated_graph_operation_v3')
    assert event.assertion_ids==['assertion:pond'] and event.evidence_ref_ids==['evidence:pond']
    assert event.coverage_status=='complete' and event.evidence_sufficiency_status=='sufficient'
    assert a._broker_execution().effective_source_pins()['anchor:pond'].source_revision_id=='source:pond:1'


@pytest.mark.parametrize('matching', [True, False])
def test_exact_successful_bootstrap_discovery_is_not_repeated(plan_adapter, matching):
    from dataclasses import replace
    plan_adapter.bootstrap = replace(plan_adapter.bootstrap, completed_discovery_query=(
        plan_adapter.request.message if matching else 'A different earlier query'))
    graphs, sources = fixture_reads(plan_adapter)
    driver = PlanJevDriver(plan_adapter)
    transport = Decisions(discover=not matching)
    proof = asyncio.run(driver.run(transport=transport, api_key='synthetic-not-secret'))
    assert [g['operation'] for g in graphs] == ([] if matching else ['search', 'object', 'object'])
    assert driver.finished
    assert len(proof['graph_packets']) == (0 if matching else 3)
    assert 'discover_more' not in transport.calls[0]['questions']['operation']['criteria'] if matching else (
        'discover_more' in transport.calls[0]['questions']['operation']['criteria'])
