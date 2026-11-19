"""One selected dependency lifetime, with fresh native reads and durable guards."""
import asyncio
import json
from uuid import uuid4
from tests import test_native_graph_inspection as _subject_core_tests

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
    from apps.live_control_server.services.agent_graph_auth import NativeGraphPrincipal
    a.native_principal = NativeGraphPrincipal(subject="test:gm", role="gm", auth_method="local_operator")
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
    monkeypatch.setenv("DMB_NATIVE_PLAN_SUBJECT_SEARCH_WORLD", a.bootstrap.world_scope.world_id)
    monkeypatch.setattr(
        'apps.live_control_server.integrations.dungeonmind.world_graph_reads.direct_services_from_config',
        lambda _: pytest.fail("classic service resolved during native subject search"),
    )

    def native_search(request, principal, **kwargs):
        authority = a._broker_graph_receipt().graph_authority
        assert request.world_id == authority.managed_world_id
        assert request.revision_pin == authority.graph_revision
        assert principal == a.native_principal
        assert kwargs == {"expected_native_world_id": authority.native_world_id,
                          "expected_binding_version": authority.binding_version, "known_subject_id": "pond"}
        return search(None, request).result.model_copy(update={
            "snapshot": search_snapshot(request),
        })

    def search_snapshot(request):
        from graph_memory.retrieval.models import WorldGraphRetrievalSnapshot
        return WorldGraphRetrievalSnapshot(world_id=request.world_id, campaign_id="",
            revision_id=request.revision_pin, head_revision_id=request.revision_pin, is_head=True,
            scope_mode="world", admissibility="gm", focus={"kind": "none"})

    monkeypatch.setattr(
        'apps.live_control_server.services.native_graph_inspection.plan_subject_search',
        native_search,
    )
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


# Actual Core fixture aliases; no replacement of B's broker/search/read helpers.

_subject_core_inspection = _subject_core_tests.inspection
recap_lane = _subject_core_tests.recap_lane
subject_plan_adapter = plan_adapter


@pytest.mark.parametrize("selector", [None, "stale-other-world"])
def test_subject_search_actual_app_ack_core_read_and_durable_reload(
    subject_plan_adapter, _subject_core_inspection, monkeypatch, selector,
):
    """Core-produced object DTO is prefix transport; B's search path is production."""
    from dataclasses import replace
    from datetime import UTC, datetime
    from types import SimpleNamespace
    from application_state.agent_conversation import AgentConversationService, types as t
    from application_state.agent_conversation.plan_jev_decision import current_selection
    from apps.live_control_server.services import native_graph_inspection as native
    from apps.live_control_server.services.agent_graph_auth import NativeGraphPrincipal
    from apps.live_control_server.services.agent_turn_service import _PolicyExecutionAdapter
    from apps.live_control_server.services.plan_jev_acquisition import subject_search_acquisition, read_subject_labels
    from apps.live_control_server.integrations.dungeonmind import world_graph_reads as direct
    from graph_memory.interaction.session_store import create_session
    from graph_memory.retrieval.models import WorldGraphObjectRequest

    x = _subject_core_inspection
    case = _subject_core_tests._subject_search_case(x, monkeypatch, sparse_aliases=True)
    a = subject_plan_adapter
    selected = case.worlds["managed"]
    record = case.records["managed"]
    case.records[a.world_id] = type(record).model_validate({
        **record.model_dump(mode="json"), "world_id": a.world_id,
    })
    monkeypatch.setattr('apps.live_control_server.services.native_source_navigation.resolve_managed_world_binding',
                        case.managed.resolve_managed_world_binding)
    scope = replace(a.bootstrap.world_scope, world_id=selected.space, revision_id=case.pin)
    session = a.bootstrap.retrieval_session.model_copy(deep=True)
    session.snapshot = session.snapshot.model_copy(update={"world_id": selected.space, "revision_id": case.pin})
    a.bootstrap = replace(a.bootstrap, world_scope=scope, binding_version=selected.version,
        retrieval_session=session, graph_envelope={**a.bootstrap.graph_envelope,
            "world_id": selected.space, "revision_id": case.pin})
    a.native_principal = NativeGraphPrincipal(subject="test:gm", role="gm", auth_method="local_operator")
    assert a.fence is None and a.world_id != selected.space
    create_session(session)
    first = PlanJevDispatch(a, (RetrievalCandidate(handle="node:" + case.root, label="Catalog label", kind="World entity"),))
    asyncio.run(first.run(transport=Decisions(), api_key="synthetic-not-secret"))
    assert current_selection(a.fence.turn).selected_handles == ["node:" + case.root]
    authority = a._broker_graph_receipt().graph_authority
    assert (authority.managed_world_id, authority.native_world_id, authority.binding_version,
            authority.graph_revision) == (a.world_id, selected.space, selected.version, case.pin)

    def core_object(node):
        request = WorldGraphObjectRequest.model_validate({
            "schema": "dmb_world_graph_object_request_v1", "worldId": a.world_id,
            "campaignId": "", "scopeMode": "world", "revisionPin": case.pin, "nodeId": node,
        })
        result = native.shared_exact_object(request, a.native_principal)
        return result.model_copy(update={"snapshot": result.snapshot.model_copy(update={"world_id": selected.space})})

    # This is an explicitly fixture-owned prefix, not production object migration.
    produced = core_object(case.root)
    packet = produced.model_dump(mode="json", by_alias=True)
    arguments = {"retrievalSessionId": session.id, "operation": "object",
                 "targets": [{"kind": "node", "id": case.root}]}
    event = t.ValidatedGraphOperationEventV3(kind="validated_graph_operation_v3", event_id=uuid4(),
        sequence=len(a._broker_execution().events), operation_id=uuid4(),
        operation="expand_graph_retrieval", request_arguments_sha256=t.canonical_sha256(arguments),
        graph_revision=case.pin, result_packet_sha256=t.canonical_sha256(packet),
        assertion_ids=sorted({row.assertion_id for row in produced.attributes}),
        relationship_ids=sorted({row.edge_id for row in produced.relationships}),
        evidence_ref_ids=sorted({row.evidence_ref_id for row in produced.source_anchors}),
        evidence_sufficiency_status="insufficient", coverage_status="complete", truncated=False,
        source_opened=False, returned_source_pins=[])
    a.turn, _ = a.fence.append('append_validated_graph_operation', 'operation_event', event)
    a.operation_payloads[event.event_id] = json.dumps(packet | {
        "retrievalSessionId": session.id, "addedClaimIds": [], "claimLedger": [],
    })
    label = read_subject_labels(a)[case.root]
    dispatch = PlanJevDispatch(a, (RetrievalCandidate(handle="mentions:" + case.root, label=label,
        kind="Search other mentions of this explored World subject"),))
    asyncio.run(dispatch.run(transport=Decisions(), api_key="synthetic-not-secret"))
    if selector is None:
        monkeypatch.delenv("DMB_NATIVE_PLAN_SUBJECT_SEARCH_WORLD", raising=False)
    else:
        monkeypatch.setenv("DMB_NATIVE_PLAN_SUBJECT_SEARCH_WORLD", selector)
    monkeypatch.setattr(direct, "direct_services_from_config", lambda *_: pytest.fail("classic search service"))
    monkeypatch.setattr(direct, "search_world_graph_direct_v3", lambda *_: pytest.fail("classic search read"))
    runtime = _subject_core_tests.transport.runtime(case.repo, x.lane.domain, x.lane.profile,
        now=datetime.now(UTC), operation_id="joint-subject-head-advance")
    runtime.commit_prepared_change(runtime.prepare_change(_subject_core_tests.wk.WorldChangeIntent(
        selected.space, "later head", (_subject_core_tests.wk.CreateObject("later"),))), confirmed_by="local_operator")
    head, events = case.repo.get_head(selected.space), case.repo.head_events(selected.space)
    epoch = case.repo.open_native_source_view(selected.space).epoch
    before_pins = dict(a._broker_execution().effective_source_pins())
    before_payloads = dict(a.source_payloads)
    with subject_search_acquisition(a, dispatch, "mentions:" + case.root):
        message = {"toolName": "expand_graph_retrieval", "arguments": {
            "retrievalSessionId": session.id, "operation": "search", "queryText": label}}
        reply = _PolicyExecutionAdapter.broker_graph_operation(a, message)
        result = json.loads(reply["resultJson"])
        assert result.get("operation") == "search", result
        assert result["snapshot"]["worldId"] == selected.space
        assert result["snapshot"]["revisionId"] == case.pin
        assert result["snapshot"]["headRevisionId"] == head.head_revision_id
        assert result["snapshot"]["isHead"] is False
        assert result["attributes"] == result["relationships"] == result["sourceAnchors"] == []
        assert case.subjects["phrase"] in result["matchedNodeIds"]
        again = _PolicyExecutionAdapter.broker_graph_operation(a, message)
        assert json.loads(again["resultJson"])["code"] == "plan_jev_acquisition_not_current"
    turn = a.fence.turn
    durable = AgentConversationService().inspect_turn(world_id=a.world_id, turn_id=turn.turn_id)
    assert durable.graph_context_execution == turn.graph_context_execution
    search_event = durable.graph_context_execution.events[-1]
    assert isinstance(search_event, t.ValidatedGraphOperationEventV3)
    assert search_event.assertion_ids == search_event.relationship_ids == search_event.evidence_ref_ids == search_event.returned_source_pins == []
    assert a._broker_execution().effective_source_pins() == before_pins
    assert a.source_payloads == before_payloads
    target = case.subjects["phrase"]
    object_message = {"toolName": "expand_graph_retrieval", "arguments": {
        "retrievalSessionId": session.id, "operation": "object", "targets": [{"kind": "node", "id": target}]}}
    denied = _PolicyExecutionAdapter.broker_graph_operation(a, object_message)
    assert json.loads(denied["resultJson"])["code"] == "plan_jev_acquisition_not_current"
    # A distinct actual APP acknowledgement is required before object transport.
    candidate = next(row for row in result["nodes"] if row["nodeId"] == target)
    object_dispatch = PlanJevDispatch(a, (RetrievalCandidate(handle="node:" + target,
        label=candidate["label"], kind="World entity"),))
    asyncio.run(object_dispatch.run(transport=Decisions(), api_key="synthetic-not-secret"))
    assert current_selection(a.fence.turn).selected_handles == ["node:" + target]
    transport_calls = []
    def object_transport(_services, request, **_kwargs):
        transport_calls.append(request.node_id)
        return SimpleNamespace(result=core_object(request.node_id), source_pins=(),
            reviewed_source_observations=(), observation_gap_codes=(), observation_missing_ids=())
    with monkeypatch.context() as object_fixture:
        object_fixture.setattr(direct, "direct_services_from_config", lambda *_: object())
        object_fixture.setattr(direct, "get_object_with_reviewed_sources_direct_v3", object_transport)
        opened = _PolicyExecutionAdapter.broker_graph_operation(a, object_message)
    assert json.loads(opened["resultJson"]).get("operation") == "object", opened
    assert transport_calls == [target]
    assert case.repo.get_head(selected.space) == head and case.repo.head_events(selected.space) == events
    assert case.repo.open_native_source_view(selected.space).epoch == epoch
