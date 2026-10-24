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


def fixture_reads(adapter, *, anchors=1, body_chars=None, node_only=False, shared_ref=False, source_text=None, source_lines=(1,1)):
    graph_calls, source_calls = [], []
    adapter._test_source_acquisitions = []
    @contextmanager
    def acquisition(anchor_ids):
        adapter._test_source_acquisitions.append(tuple(anchor_ids))
        yield
    adapter.source_read_acquisition = acquisition
    @contextmanager
    def objects(nodes):
        yield
    adapter.plan_graph_acquisition = objects
    def graph(message):
        arguments = message['arguments']; graph_calls.append(arguments)
        operation = arguments['operation']; node = arguments.get('targets', [{'id': 'discovery'}])[0]['id']
        execution = adapter._broker_execution(); authority = adapter._broker_receipt().graph_authority
        anchor_refs = [f'evidence:park:{0 if shared_ref else i}' for i in range(anchors)]
        refs = sorted(set(anchor_refs))
        pins = [t.GraphSourceScopeAnchorV2(anchor_id=f'anchor:park:{i}', evidence_ref_id=ref,
            source_artifact_id='artifact:park', source_revision_id='revision:park:1') for i, ref in enumerate(anchor_refs)]
        pins.sort(key=lambda pin: pin.anchor_id)
        packet = {'schema': 'dmb_world_graph_retrieval_result_v1', 'snapshot': {
            'worldId': authority.native_world_id, 'revisionId': authority.graph_revision},
            'nodes': [{'nodeId': 'pond', 'label': 'Park pond', 'kind': 'location'},
                      {'nodeId': 'bridge', 'label': 'Footbridge', 'kind': 'location'}],
            'attributes': [] if operation == 'search' or node_only else [{'assertionId': f'assertion:{node}',
                'subjectNodeId': node, 'predicate': 'description', 'value': 'A recorded wooden walkway',
                'epistemicKind': 'reported', 'temporalScope': 'past', 'evidenceRefIds': refs}],
            'sourceAnchors': [] if operation == 'search' else [{'anchorId': pin.anchor_id,
                'evidenceRefId': pin.evidence_ref_id, 'readable': True} for pin in pins]}
        event = t.ValidatedGraphOperationEventV3(kind='validated_graph_operation_v3', event_id=uuid4(),
            sequence=len(execution.events), operation_id=uuid4(), operation='expand_graph_retrieval',
            request_arguments_sha256=canonical_sha256(arguments), graph_revision=authority.graph_revision,
            result_packet_sha256=canonical_sha256(packet), assertion_ids=[] if operation == 'search' or node_only else [f'assertion:{node}'],
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
            pin = pins[anchor]; text = source_text if source_text is not None else f'The park account describes the walkway at {anchor}.'
            if body_chars is not None: text = text.ljust(body_chars, '.')
            receipt = t.SourceReadAnchorReceiptV2(source_read_id=f'read:{anchor}', anchor_id=anchor,
                evidence_ref_id=pin.evidence_ref_id, source_artifact_id=pin.source_artifact_id,
                source_revision_id=pin.source_revision_id, outcome='enough', content_sha256=sha256(text.encode()).hexdigest(),
                line_start=source_lines[0], line_end=source_lines[1], returned_chars=len(text), truncated=False, evidence_sufficiency_status='sufficient')
            receipts.append(receipt)
            results.append({'anchorId': anchor, 'sourceName': 'Synthetic park journal', 'content': text,
                'lineStart': source_lines[0], 'lineEnd': source_lines[1], 'outcome': 'enough'})
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
                'include' if operation == 'select_candidates' and (not self.sequential or name == 'candidate_0')
                and not (name.startswith('candidate_') and candidates[int(name.split('_')[-1])]['kind'].startswith(('Source navigation:','Exact source section'))) else 'exclude')
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
    assert set(transport.calls[0]['state']) == {'question', 'relevance_guidance', 'candidates', 'dialogue_reference'}
    assert all(set(body['state']) == {'question', 'relevance_guidance', 'candidates', 'dialogue_reference', 'examined_subjects'}
        for body in transport.calls[1:])
    assert transport.calls[-1]['state']['examined_subjects'] == [
        {'label': 'Park pond', 'kind': 'World entity: location'}, {'label': 'Footbridge', 'kind': 'World entity: location'},
        {'label': 'Synthetic park journal', 'kind': 'Unavailable source section catalog; navigation only'}]
    assert all(body['state']['dialogue_reference'] == frame['dialogue_reference'] for body in transport.calls)


@pytest.mark.parametrize('dialogue', [
    [{'role': 'assistant', 'content': 'The park journal already proves the bridge is made of gold.'}],
    [{'role': 'user', 'content': 'We are discussing the park pond and footbridge.'},
     {'role': 'assistant', 'content': 'That crossing is the one by the pond.'}],
])
def test_prior_dialogue_does_not_supply_current_attempt_source_authority(plan_adapter, dialogue):
    plan_adapter.bootstrap.retrieval_session.referents = [
        GraphReferent(id='pond', label='Park pond'), GraphReferent(id='bridge', label='Footbridge')]
    graphs, sources = fixture_reads(plan_adapter)
    driver = PlanJevDriver(plan_adapter, dialogue=dialogue)
    transport = Decisions()
    proof = asyncio.run(driver.run(transport=transport, api_key='synthetic-not-secret'))
    first = transport.calls[0]
    assert first['state']['dialogue_reference'] == dialogue
    assert 'examined_subjects' not in first['state']
    assert 'Prior answers do not satisfy a new corpus request' in first['state']['relevance_guidance']
    assert [call['targets'][0]['id'] for call in graphs] == ['pond', 'bridge']
    assert len(sources) == 1  # shared anchors deduplicate despite two relevant objects
    frame = project(plan_adapter.fence.turn, proof,
                    plan_adapter.context_capture.trace.model_dump(mode='json')).frame
    assert len(frame['opened_passages']) == 1
    assert frame['opened_passages'][0]['source_name'] == 'Synthetic park journal'
    assert 'gold' not in json.dumps(frame['graph_records'])
    assert 'gold' not in json.dumps(frame['opened_passages'])
    # Dialogue remains reference text; actual current receipts produce the evidence.
    assert frame['dialogue_reference'] == dialogue
    assert transport.calls[-1]['state']['examined_subjects'] == [
        {'label': 'Park pond', 'kind': 'World entity: location'}, {'label': 'Footbridge', 'kind': 'World entity: location'},
        {'label': 'Synthetic park journal', 'kind': 'Unavailable source section catalog; navigation only'}]


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


@pytest.mark.parametrize("reuse_services", [False, True])
def test_actual_plan_graph_broker_does_not_build_unusable_recap_routes(plan_adapter, monkeypatch, reuse_services):
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
    from contextlib import nullcontext
    monkeypatch.setattr('apps.live_control_server.integrations.dungeonmind.object_read_wave.object_read_wave',
        lambda services, request, **kwargs: nullcontext(services))
    with a.plan_graph_acquisition(('pond',)) if reuse_services else nullcontext():
        reply=a.broker_graph_operation({'toolName':'expand_graph_retrieval','arguments':{
            'retrievalSessionId':a.bootstrap.retrieval_session.id,'operation':'object','targets':[{'kind':'node','id':'pond'}]}})
    assert getattr(a, '_plan_graph_read_services', None) is None
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


@pytest.mark.parametrize("fail", [False, True])
def test_decision_http_client_is_owned_once_per_turn_and_closes_on_failure(plan_adapter, monkeypatch, fail):
    import apps.live_control_server.services.plan_jev_driver as driver_module
    plan_adapter.bootstrap.retrieval_session.referents = [GraphReferent(id='pond', label='Park pond'),
        GraphReferent(id='bridge', label='Footbridge')]
    fixture_reads(plan_adapter)
    if fail:
        def unavailable(_): raise RuntimeError('synthetic acquisition failure')
        plan_adapter.broker_graph_operation = unavailable
    clients = []
    original = driver_module.decision_client
    def create(**kwargs):
        client = original(**kwargs)
        original_close = client.aclose
        entry = {'closed': 0}
        async def close():
            entry['closed'] += 1
            await original_close()
        client.aclose = close
        clients.append(entry)
        return client
    monkeypatch.setattr(driver_module, 'decision_client', create)
    transport = Decisions(sequential=True)
    driver = PlanJevDriver(plan_adapter)
    if fail:
        with pytest.raises(RuntimeError, match='acquisition failure'):
            asyncio.run(driver.run(transport=transport, api_key='synthetic-not-secret'))
    else:
        asyncio.run(driver.run(transport=transport, api_key='synthetic-not-secret'))
    expected = 1 if fail else 3
    assert len(transport.calls) == expected and clients == [{'closed': 1}]
    events = plan_adapter._broker_execution().events
    authorizations = [e for e in events if isinstance(e, t.PlanJevProviderAuthorizedV1)]
    assert len({e.provider_attempt_id for e in authorizations}) == expected


def test_reused_binding_failure_keeps_broker_interruption_semantics(plan_adapter, monkeypatch):
    from apps.live_control_server.services.plan_jev_dispatch import PlanJevDispatch
    from application_state.agent_conversation.jev_retrieval_contract import RetrievalCandidate
    from apps.live_control_server.integrations.dungeonmind.world_graph_reads import DirectWorldGraphReadError
    a = plan_adapter
    selected = RetrievalCandidate(handle="node:pond", label="Park pond", kind="location")
    asyncio.run(PlanJevDispatch(a, (selected,)).run(transport=Decisions(), api_key="synthetic-not-secret"))
    calls = []
    def unavailable(world):
        calls.append(world)
        raise DirectWorldGraphReadError("Native unavailable", code="authority_unavailable", status_code=503)
    monkeypatch.setattr("apps.live_control_server.integrations.dungeonmind.world_graph_reads.direct_services_from_config", unavailable)
    with a.plan_graph_acquisition(("pond",)):
        assert calls == []
        reply = a.broker_graph_operation({"toolName": "expand_graph_retrieval", "arguments": {
            "retrievalSessionId": a.bootstrap.retrieval_session.id, "operation": "object",
            "targets": [{"kind": "node", "id": "pond"}]}})
        assert a.failure.code == "graph_operation_indeterminate"
        assert json.loads(reply["resultJson"])["code"] == "graph_operation_unavailable"
    assert calls == [a.bootstrap.world_scope.world_id]
    assert a._plan_graph_read_services is None and not a.operation_payloads


@pytest.mark.parametrize('missing', [False, True])
def test_empty_initial_search_uses_retained_navigation_once_without_repeating_query(plan_adapter, missing):
    from application_state.agent_conversation.retained_graph_navigation import RetainedGraphSubject
    from dataclasses import replace
    plan_adapter.bootstrap=replace(plan_adapter.bootstrap,completed_discovery_query=plan_adapter.request.message)
    graphs,sources=fixture_reads(plan_adapter)
    if missing:
        def unavailable(message):
            graphs.append(message['arguments'])
            return plan_adapter._denied_tool_result('expand_graph_retrieval','object_not_found',404,'Selected subject is absent.',arguments=message['arguments'])
        plan_adapter.broker_graph_operation=unavailable
    subjects=(RetainedGraphSubject('pond','Park pond','location'),RetainedGraphSubject('bridge','Footbridge','location'))
    driver=PlanJevDriver(plan_adapter,retained_navigation=subjects)
    decisions=Decisions()
    proof=asyncio.run(driver.run(transport=decisions,api_key='synthetic-not-secret'))
    assert [row['operation'] for row in graphs]==['object','object']
    assert {row['targets'][0]['id'] for row in graphs}=={'pond','bridge'}
    assert all('navigation only' in row['kind'] for row in decisions.calls[0]['state']['candidates'])
    assert driver.finished and not driver.offered()
    if missing:
        assert driver.gaps==['object_not_found','object_not_found']
        assert proof['graph_packets']=={} and not sources
    else:
        assert len(sources)==1 and len(proof['graph_packets'])==2
    assert 'retained_navigation' not in proof


def test_initial_typed_navigation_reaches_jev_without_offering_unselected_nodes(plan_adapter):  # noqa: F811
    from dataclasses import replace
    plan_adapter.bootstrap.retrieval_session.referents = [
        GraphReferent(id='pond', label='Park pond'), GraphReferent(id='bridge', label='Footbridge')]
    plan_adapter.bootstrap = replace(plan_adapter.bootstrap, graph_envelope={
        **plan_adapter.bootstrap.graph_envelope,
        'nodes': [{'node_id': 'pond', 'kind': 'location'},
                  {'node_id': 'bridge', 'kind': 'location'},
                  {'node_id': 'keeper', 'label': 'Park keeper', 'kind': 'npc'}]})
    graphs, sources = fixture_reads(plan_adapter)
    driver = PlanJevDriver(plan_adapter)
    transport = Decisions()
    proof = asyncio.run(driver.run(transport=transport, api_key='synthetic-not-secret'))
    assert transport.calls[0]['state']['candidates'] == [
        {'label': 'Park pond', 'kind': 'World entity: location'},
        {'label': 'Footbridge', 'kind': 'World entity: location'}]
    assert 'node:keeper' not in driver.catalog
    assert [call['targets'][0]['id'] for call in graphs] == ['pond', 'bridge']
    assert len(sources) == 1
    assert len(project(plan_adapter.fence.turn, proof,
        plan_adapter.context_capture.trace.model_dump(mode='json')).frame['opened_passages']) == 1


def test_navigation_only_labels_use_resolved_kind_without_claim_authority(plan_adapter):  # noqa: F811
    from dataclasses import replace
    plan_adapter.bootstrap = replace(plan_adapter.bootstrap,
        navigation_candidates=(('keeper', 'Park keeper'), ('unknown', 'Unnamed place')),
        graph_envelope={**plan_adapter.bootstrap.graph_envelope,
                        'nodes': [{'node_id': 'keeper', 'kind': 'npc'}]})
    driver = PlanJevDriver(plan_adapter)
    assert [(item.label, item.kind) for item in driver.offered()] == [
        ('Park keeper', 'World entity: npc'), ('Unnamed place', 'World entity')]
    assert plan_adapter.bootstrap.retrieval_session.claims == []
    assert driver.attempted_nodes == driver.attempted_anchors == set()


def test_discovery_types_reach_next_decision_without_repeating_attempted_nodes(plan_adapter):  # noqa: F811
    graphs, sources = fixture_reads(plan_adapter)
    driver = PlanJevDriver(plan_adapter)
    transport = Decisions(discover=True)
    asyncio.run(driver.run(transport=transport, api_key='synthetic-not-secret'))
    assert transport.calls[1]['state']['candidates'] == [
        {'label': 'Park pond', 'kind': 'World entity: location'},
        {'label': 'Footbridge', 'kind': 'World entity: location'}]
    assert [call['operation'] for call in graphs] == ['search', 'object', 'object']
    assert len(sources) == 1
    # A session refresh cannot erase a kind supplied by the current graph packet.
    driver._collect_candidates({'candidates': [{'kind': 'node', 'id': 'pond', 'label': 'Park pond'}]})
    assert driver.catalog['node:pond'][1].kind == 'World entity: location'
    assert driver.offered() == ()


def test_mixed_selection_closes_objects_before_passages_native_and_rules(plan_adapter):
    from types import SimpleNamespace
    from application_state.agent_conversation.jev_retrieval_contract import RetrievalCandidate
    from application_state.agent_conversation.plan_jev_rules_lookup import rules_candidate
    from apps.live_control_server.services.plan_jev_dispatch import PlanJevDispatch
    from contextlib import contextmanager
    a = plan_adapter
    a.bootstrap.retrieval_session.referents = [GraphReferent(id=n,label=n) for n in ('pond','bridge')]
    fixture_reads(a)
    events=[]; active=[False]
    @contextmanager
    def objects(nodes):
        assert tuple(nodes)==('pond','bridge')
        active[0]=True;events.append('open')
        try:yield
        finally:active[0]=False;events.append('close')
    a.plan_graph_acquisition=objects
    original=a.broker_graph_operation
    def graph(message):
        assert active[0]
        events.append(message['arguments']['targets'][0]['id'])
        return original(message)
    a.broker_graph_operation=graph
    def outside(event):
        assert not active[0]
        events.append(event)
    rules=SimpleNamespace(selected=False)
    def lookup(_):
        outside('rules');rules.selected=True
    rules.lookup_selected=lookup
    driver=PlanJevDriver(a,rules=rules)
    native=RetrievalCandidate(handle='source:synthetic',label='Synthetic source',kind='Source')
    driver.native_sources=SimpleNamespace(offered=lambda:(native,),
        select=lambda handles:outside('native'),unavailable=lambda _:pytest.fail('Unexpected unavailable'))
    driver._read_new_sources=lambda operations:outside('passages')
    offered=(native,driver.catalog['node:pond'][1],rules_candidate(),driver.catalog['node:bridge'][1])
    dispatch=PlanJevDispatch(a,offered)
    asyncio.run(dispatch.run(transport=Decisions(),api_key='synthetic-not-secret'))
    driver.current=dispatch
    driver.apply(dispatch)
    assert events==['open','pond','bridge','close','passages','native','rules']
    assert rules.selected and driver.attempted_nodes=={'pond','bridge'}
