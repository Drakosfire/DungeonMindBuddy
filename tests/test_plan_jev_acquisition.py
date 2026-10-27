"""One selected dependency lifetime, with fresh native reads and durable guards."""
import asyncio
import json

import pytest
from application_state.agent_conversation.jev_retrieval_contract import RetrievalCandidate
from apps.live_control_server.services.plan_jev_dispatch import PlanJevDispatch
from tests.test_plan_jev_dispatch import plan_adapter  # noqa: F401
from tests.test_plan_jev_driver import Decisions


def selected(adapter):
    dispatch = PlanJevDispatch(adapter, tuple(RetrievalCandidate(
        handle=f"node:{node}", label=node, kind="location") for node in ("pond", "bridge")))
    asyncio.run(dispatch.run(transport=Decisions(), api_key="synthetic-not-secret"))


def test_bundle_binds_once_and_clears_on_error_then_rebinds(plan_adapter, monkeypatch):
    selected(plan_adapter)
    calls = []
    def bind(world):
        assert plan_adapter.authorize({}) is False
        result = object()
        calls.append((world, result))
        return result
    monkeypatch.setattr('apps.live_control_server.integrations.dungeonmind.world_graph_reads.direct_services_from_config', bind)
    with pytest.raises(RuntimeError, match="stop"):
        with plan_adapter.plan_graph_acquisition(("pond", "bridge")):
            assert calls == []
            assert plan_adapter._plan_graph_read_services.resolve() is plan_adapter._plan_graph_read_services.resolve()
            assert len(calls) == 1
            with pytest.raises(ValueError, match="current decision"):
                with plan_adapter.plan_graph_acquisition(("pond", "bridge")):
                    pytest.fail("Nested acquisition")
            raise RuntimeError("stop")
    assert plan_adapter._plan_graph_read_services is None
    with plan_adapter.plan_graph_acquisition(("pond", "bridge")):
        assert plan_adapter._plan_graph_read_services.resolve() is calls[1][1]
    assert len(calls) == 2 and calls[0][1] is not calls[1][1]
    assert all(world == plan_adapter.bootstrap.world_scope.world_id for world, _ in calls)


@pytest.mark.parametrize("nodes", [("pond", "foreign"), ("pond", "pond"), ("pond",)])
def test_bundle_refuses_changed_selection_before_native_bind(plan_adapter, monkeypatch, nodes):
    selected(plan_adapter)
    monkeypatch.setattr('apps.live_control_server.integrations.dungeonmind.world_graph_reads.direct_services_from_config',
        lambda *_: pytest.fail("Unselected native IO"))
    with pytest.raises(ValueError, match="selected targets"):
        with plan_adapter.plan_graph_acquisition(nodes):
            pytest.fail("Invalid acquisition")


def test_unacknowledged_or_failed_bind_never_leaves_active_lifetime(plan_adapter, monkeypatch):
    with pytest.raises(ValueError, match="current decision"):
        with plan_adapter.plan_graph_acquisition(("pond",)):
            pytest.fail("Unacknowledged acquisition")
    selected(plan_adapter)
    def unavailable(world):
        raise RuntimeError("Native binding unavailable")
    monkeypatch.setattr('apps.live_control_server.integrations.dungeonmind.world_graph_reads.direct_services_from_config', unavailable)
    with pytest.raises(RuntimeError, match="Native binding unavailable"):
        with plan_adapter.plan_graph_acquisition(("pond", "bridge")):
            plan_adapter._plan_graph_read_services.resolve()
    assert plan_adapter._plan_graph_read_services is None


def test_two_objects_through_real_broker_share_native_context_and_keep_events(plan_adapter, monkeypatch):
    from dataclasses import replace
    from graph_memory.interaction.session import GraphReferent
    from tests.test_world_graph_retrieval_contract import _selected_native_fixture
    services, request, revision = _selected_native_fixture(unrelated=1)
    a = plan_adapter
    scope = replace(a.bootstrap.world_scope, world_id=request.world_id, revision_id=revision)
    a.bootstrap.retrieval_session.snapshot = a.bootstrap.retrieval_session.snapshot.model_copy(update={
        'world_id':request.world_id, 'revision_id':revision})
    a.bootstrap.retrieval_session.referents = [GraphReferent(id=n, label=n) for n in ('obj:tavern','obj:noise:0')]
    a.bootstrap = replace(a.bootstrap, world_scope=scope,
        graph_envelope={**a.bootstrap.graph_envelope, 'world_id':request.world_id,'revision_id':revision})
    candidates = tuple(RetrievalCandidate(handle=f'node:{n}',label=n,kind='location') for n in ('obj:tavern','obj:noise:0'))
    asyncio.run(PlanJevDispatch(a,candidates).run(transport=Decisions(),api_key='synthetic-not-secret'))
    from unittest.mock import Mock
    opened = Mock(wraps=services.projection.open_read_context)
    monkeypatch.setattr(services.projection,'open_read_context',opened)
    monkeypatch.setattr('apps.live_control_server.integrations.dungeonmind.world_graph_reads.direct_services_from_config',lambda _:services)
    with a.plan_graph_acquisition(('obj:tavern','obj:noise:0')):
        lifetime = a._plan_graph_read_services
        assert opened.call_count == 0 and a.authorize({}) is False
        for node in ('obj:tavern','obj:noise:0'):
            reply = a.broker_graph_operation({'toolName':'expand_graph_retrieval','arguments':{
                'retrievalSessionId':a.bootstrap.retrieval_session.id,'operation':'object',
                'targets':[{'kind':'node','id':node}]}})
            assert a.failure is None, reply
        assert opened.call_count == 1
        retained = lifetime.for_object(request)
    assert a._plan_graph_read_services is None
    with pytest.raises(RuntimeError,match='closed'):
        lifetime.resolve()
    assert retained.object_read_wave._native is None
    events = [e for e in a._broker_execution().events if e.kind=='validated_graph_operation_v3']
    assert len(events)==2 and len({e.operation_id for e in events})==2
    assert all(e.graph_revision==revision and e.returned_source_pins for e in events)


def selected_subject_search(a):
    from graph_memory.interaction.session import GraphReferent
    from apps.live_control_server.services.plan_jev_driver import PlanJevDriver
    from tests.test_plan_jev_driver import fixture_reads
    a.bootstrap.retrieval_session.referents = [GraphReferent(id='pond', label='Catalog label')]
    fixture_reads(a, subject_searches=True)
    driver=PlanJevDriver(a)
    first=PlanJevDispatch(a,driver.offered())
    asyncio.run(first.run(transport=Decisions(),api_key='synthetic-not-secret'))
    driver.current=first; driver.apply(first)
    mentions=tuple(c for c in driver.offered() if c.handle=='mentions:pond')
    assert len(mentions)==1 and mentions[0].label=='Park pond'
    dispatch=PlanJevDispatch(a,mentions)
    asyncio.run(dispatch.run(transport=Decisions(),api_key='synthetic-not-secret'))
    return dispatch


@pytest.mark.parametrize('case',['valid','empty','query','target','observations','closed','repeat','native_error'])
def test_subject_search_exact_real_broker_gate_and_single_use(plan_adapter,monkeypatch,case):
    from types import SimpleNamespace
    from graph_memory.retrieval.models import WorldGraphRetrievalResult
    from apps.live_control_server.services.agent_turn_service import _PolicyExecutionAdapter
    from apps.live_control_server.services.plan_jev_acquisition import subject_search_acquisition
    a=plan_adapter
    dispatch=selected_subject_search(a)
    calls=[]
    def search(services,request):
        calls.append(request.query_text)
        if case=='native_error': raise RuntimeError('synthetic native search failed')
        return SimpleNamespace(source_pins=(SimpleNamespace(anchor_id='search-only-anchor',graph_revision=a.bootstrap.world_scope.revision_id),),result=WorldGraphRetrievalResult.model_validate({
            'operation':'search','outcome':'empty' if case=='empty' else 'enough',
            'snapshot':{'worldId':a.bootstrap.world_scope.world_id,'campaignId':'',
                'revisionId':a.bootstrap.world_scope.revision_id,'headRevisionId':a.bootstrap.world_scope.revision_id,
                'isHead':True,'scopeMode':'world','admissibility':'gm','focus':{'kind':'none'}},
            'nodes':[] if case=='empty' else [{'nodeId':'bridge','label':'Footbridge','kind':'location','role':'match'}],
            'attributes':[{'assertionId':'search-only-assertion','subjectNodeId':'bridge',
                'value':{'summary':'Search-only assertion must not become writer evidence'},'evidenceRefIds':['search-only-evidence']}],
            'relationships':[{'edgeId':'search-only-edge','sourceNodeId':'pond','targetNodeId':'bridge',
                'predicate':'near','label':'near','evidenceRefIds':['search-only-evidence']}],
            'sourceAnchors':[{'anchorId':'search-only-anchor','revisionId':a.bootstrap.world_scope.revision_id,
                'evidenceRefId':'search-only-evidence','sourceArtifactId':'search-only-artifact',
                'sourceDomain':'session_recap','readable':True,'locatorKind':'source_span',
                'supportingAssertionIds':['search-only-assertion'],'supportingGraphObjectIds':['pond','bridge']}]}))
    monkeypatch.setattr('apps.live_control_server.integrations.dungeonmind.world_graph_reads.direct_services_from_config',lambda _:object())
    monkeypatch.setattr('apps.live_control_server.integrations.dungeonmind.world_graph_reads.search_world_graph_direct_v3',search)
    arguments={'retrievalSessionId':a.bootstrap.retrieval_session.id,'operation':'search','queryText':'Park pond'}
    if case=='query': arguments['queryText']='Other private story'
    if case=='target': arguments['targets']=[{'kind':'node','id':'pond'}]
    if case=='observations': arguments['observationIds']=['other']
    source_payloads=dict(a.source_payloads)
    source_pins=dict(a._broker_execution().effective_source_pins())
    with subject_search_acquisition(a,dispatch,'mentions:pond'):
        if case=='closed':
            a._plan_graph_read_services.close()
        reply=_PolicyExecutionAdapter.broker_graph_operation(a,{'toolName':'expand_graph_retrieval','arguments':arguments})
        if case in {'query','target','observations','closed'}:
            assert json.loads(reply['resultJson'])['code']==(
                'invalid_arguments' if case=='observations' else 'plan_jev_acquisition_not_current')
            assert calls==[]
        else:
            assert calls==['Park pond']
            if case!='native_error':
                result=json.loads(reply['resultJson'])
                assert result['operation']=='search' and result['attributes']==result['relationships']==result['sourceAnchors']==[]
                event=a._broker_execution().events[-1]
                assert event.kind=='validated_graph_operation_v3'
                assert event.assertion_ids==event.relationship_ids==event.evidence_ref_ids==event.returned_source_pins==[]
                assert a.source_payloads==source_payloads and a._broker_execution().effective_source_pins()==source_pins
                assert result['outcome']==('empty' if case=='empty' else 'enough')
            if case=='repeat':
                again=_PolicyExecutionAdapter.broker_graph_operation(a,{'toolName':'expand_graph_retrieval','arguments':arguments})
                assert json.loads(again['resultJson'])['code']=='plan_jev_acquisition_not_current'
                assert calls==['Park pond']
    assert a._plan_graph_read_services is None
    if case=='valid':
        from apps.live_control_server.services.plan_jev_driver import PlanJevDriver
        from application_state.agent_conversation.plan_jev_graph_packet import project
        asyncio.run(PlanJevDispatch(a,()).run(transport=Decisions(),api_key='synthetic-not-secret'))
        driver=PlanJevDriver(a);driver.finished=True
        frame=project(a.fence.turn,driver.proof(),a.context_capture.trace.model_dump(mode='json')).frame
        assert 'search-only' not in json.dumps(frame)
    if case=='native_error':
        assert a.failure is not None
        assert a._plan_subject_search_attempts=={'park pond'}


@pytest.mark.parametrize('case',['parent','label','unselected','foreign_handle','stale_parent'])
def test_subject_scope_refuses_forged_parent_or_handle(plan_adapter,case):
    from apps.live_control_server.services.plan_jev_acquisition import subject_search_acquisition
    a=plan_adapter; dispatch=selected_subject_search(a)
    handle='mentions:pond'
    if case=='stale_parent':
        asyncio.run(PlanJevDispatch(a,()).run(transport=Decisions(),api_key='synthetic-not-secret'))
    if case=='parent': dispatch.parent=dispatch.parent.model_copy(update={'question':'Different question'})
    if case=='label':
        candidate=dispatch.parent.candidates[0].model_copy(update={'label':'Forged label'})
        dispatch.parent=dispatch.parent.model_copy(update={'candidates':(candidate,)})
    if case=='unselected': handle='mentions:bridge'
    if case=='foreign_handle': handle='node:pond'
    with pytest.raises(ValueError,match='current offered canonical label'):
        with subject_search_acquisition(a,dispatch,handle): pytest.fail('Forged subject scope')
    assert getattr(a,'_plan_graph_read_services',None) is None
