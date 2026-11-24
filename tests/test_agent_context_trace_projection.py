import hashlib
import json
from uuid import uuid4

import pytest

from application_state.agent_conversation.types import ValidatedGraphOperationEventV1
from apps.live_control_server.services.agent_context_trace_projection import graph_operation_observation
from graph_memory.retrieval.models import (
    WorldGraphEvidenceRequest, WorldGraphNeighborhoodRequest, WorldGraphObjectRequest,
    WorldGraphRetrievalResult, WorldGraphSearchRequest,
)


def fixture(node_count=1, claim_count=1, operation='search'):
    result=WorldGraphRetrievalResult.model_validate({
        'operation':'evidence' if operation=='support' else operation, 'outcome':'partial',
        'snapshot':{'worldId':'world', 'campaignId':'', 'revisionId':'rev', 'headRevisionId':'rev',
                    'isHead':True, 'focus':{'kind':'none'}, 'admissibility':'gm','scopeMode':'world'},
        'nodes':[{'nodeId':f'node:{n}', 'label':f'Place {n}', 'kind':'location', 'role':'mentioned',
                  'summary':'Source prose is not graph trace metadata.'} for n in range(node_count)],
        'attributes':[{'assertionId':f'claim:{n}', 'subjectNodeId':'node:0'} for n in range(claim_count)],
    })
    payload=result.model_dump(mode='json',by_alias=True)
    digest=hashlib.sha256(json.dumps(payload,ensure_ascii=False,sort_keys=True,separators=(',',':'),allow_nan=False).encode()).hexdigest()
    event=ValidatedGraphOperationEventV1(event_id=uuid4(),sequence=0,kind='validated_graph_operation',
        operation_id=uuid4(),operation='expand_graph_retrieval',request_arguments_sha256='a'*64,
        graph_revision='rev',result_packet_sha256=digest,assertion_ids=sorted(f'claim:{n}' for n in range(claim_count)),
        relationship_ids=[],evidence_ref_ids=[],evidence_sufficiency_status='insufficient',
        coverage_status='incomplete',truncated=False,source_opened=False)
    return result,payload,event


def request(operation):
    common={'worldId':'world','campaignId':'','scopeMode':'world','revisionPin':'rev'}
    if operation=='search':
        return WorldGraphSearchRequest.model_validate({**common,'schema':'dmb_world_graph_search_request_v1',
            'queryText':'Mirathorn operators','seedNodeIds':['city']})
    if operation=='object':
        return WorldGraphObjectRequest.model_validate({**common,'schema':'dmb_world_graph_object_request_v1','nodeId':'city'})
    if operation=='neighborhood':
        return WorldGraphNeighborhoodRequest.model_validate({**common,'schema':'dmb_world_graph_neighborhood_request_v1',
            'seedNodeIds':['city'],'maxDepth':2})
    return WorldGraphEvidenceRequest.model_validate({**common,'schema':'dmb_world_graph_evidence_request_v1',
        'target':{'kind':'node','id':'city'}})


@pytest.mark.parametrize('operation',['search','object','neighborhood','support'])
def test_records_actual_effective_request_defaults_and_execution_binding(operation):
    result,payload,event=fixture(operation=operation)
    observation=graph_operation_observation(request=request(operation),result=result,result_payload=payload,
        execution_event=event,sequence=2,elapsed_ms=5,duration_ms=1)
    assert observation['request']['operation']==operation
    assert observation['request']['max_source_anchors']==24
    assert observation['execution_event_id']==str(event.event_id)
    assert observation['request_arguments_sha256']==event.request_arguments_sha256
    assert observation['result_packet_sha256']==event.result_packet_sha256
    assert observation['result']['claim_ids']==event.assertion_ids
    if operation=='search':
        assert observation['request']['query_text']=='Mirathorn operators'
    if operation=='neighborhood':
        assert observation['request']['depth']==2


def test_projection_limits_are_explicit_and_do_not_change_model_retrieval_result():
    result,payload,event=fixture(70,140)
    original=json.dumps(payload,sort_keys=True)
    observation=graph_operation_observation(request=request('search'),result=result,result_payload=payload,
        execution_event=event,sequence=0,elapsed_ms=0,duration_ms=1)
    projection=observation['result']
    assert projection['projection_status']=='limited'
    assert projection['coverage_status']=='incomplete'
    assert projection['returned_counts']['nodes']==64 and projection['total_counts']['nodes']==70
    assert projection['returned_counts']['claims']==128 and projection['total_counts']['claims']==140
    assert projection['omission_codes']==['trace_nodes_limit','trace_claims_limit']
    assert json.dumps(payload,sort_keys=True)==original
    assert len(result.nodes)==70 and len(result.attributes)==140
    assert 'Source prose' not in json.dumps(observation)


@pytest.mark.parametrize('change',['payload','typed_result','ids','revision'])
def test_rejects_observation_that_does_not_match_its_validated_broker_event(change):
    result,payload,event=fixture()
    if change=='payload':
        payload={**payload,'outcome':'enough'}
    if change=='typed_result':
        result=result.model_copy(update={'nodes':[]})
    if change=='ids':
        event=event.model_copy(update={'assertion_ids':['foreign']})
    if change=='revision':
        event=event.model_copy(update={'graph_revision':'other'})
    with pytest.raises(ValueError,match='differs|identifiers'):
        graph_operation_observation(request=request('search'),result=result,result_payload=payload,
            execution_event=event,sequence=0,elapsed_ms=0,duration_ms=1)


def test_retains_only_directed_endpoints_from_validated_relationship_rows():
    result, _, event = fixture(node_count=2)
    result = WorldGraphRetrievalResult.model_validate({
        **result.model_dump(mode='json', by_alias=True),
        'relationships': [{'edgeId':'edge:one','sourceNodeId':'node:0','targetNodeId':'node:1',
                           'predicate':'knows','label':'Knows'}],
    })
    payload = result.model_dump(mode='json', by_alias=True)
    digest = hashlib.sha256(json.dumps(payload, ensure_ascii=False, sort_keys=True,
                                      separators=(',', ':'), allow_nan=False).encode()).hexdigest()
    event = event.model_copy(update={'result_packet_sha256':digest, 'relationship_ids':['edge:one']})
    observation = graph_operation_observation(request=request('search'), result=result, result_payload=payload,
        execution_event=event, sequence=0, elapsed_ms=0, duration_ms=1)
    from application_state.agent_conversation.context_trace import TraceGraphTool
    trace = TraceGraphTool.model_validate(observation)
    assert [row.model_dump() for row in trace.result.relationships] == [
        {'relationship_id':'edge:one', 'source_node_id':'node:0', 'target_node_id':'node:1'},
    ]
    del observation['result']['relationships']
    assert TraceGraphTool.model_validate(observation).result.relationships == []



def test_neighborhood_replay_keeps_only_recorded_discovery_with_visible_endpoints():
    result, _, event = fixture(node_count=65, operation="neighborhood")
    edges = [("discovery", "node:1"), ("examined", "node:2"), ("omitted", "node:64")]
    result = WorldGraphRetrievalResult.model_validate({
        **result.model_dump(mode="json", by_alias=True),
        "relationships": [
            {"edgeId": identity, "sourceNodeId": "node:0", "targetNodeId": target,
             "predicate": "knows", "label": "Knows"}
            for identity, target in edges
        ],
    })
    payload = result.model_dump(mode="json", by_alias=True)
    result._discovery_relationship_ids = ("discovery", "omitted")
    assert result.model_dump(mode="json", by_alias=True) == payload
    event = ValidatedGraphOperationEventV1.model_validate({
        **event.model_dump(),
        "result_packet_sha256": hashlib.sha256(json.dumps(
            payload, ensure_ascii=False, sort_keys=True, separators=(",", ":"),
        ).encode()).hexdigest(),
        "relationship_ids": sorted(identity for identity, _ in edges),
        "discovery_relationship_ids": list(result._discovery_relationship_ids),
        "truncated": True,
        "neighborhood_replay": {
            "hops": [
                {"relationship_id": "discovery", "from_node_id": "node:1", "to_node_id": "node:0"},
                {"relationship_id": "omitted", "from_node_id": "node:0", "to_node_id": "node:64"},
            ],
            "object_limit_pruned_ids": ["discarded"],
            "object_limit_pruned_count": 1,
        },
    })
    from application_state.agent_conversation.context_trace import TraceGraphTool

    trace = TraceGraphTool.model_validate(graph_operation_observation(
        request=request("neighborhood"), result=result, result_payload=payload, execution_event=event,
        sequence=0, elapsed_ms=0, duration_ms=1,
    ))
    assert trace.result.discovery_relationship_ids == ["discovery"]
    assert trace.result.neighborhood_replay.hops[0].from_node_id == "node:1"
    assert trace.result.neighborhood_replay.object_limit_pruned_ids == ["discarded"]
    from application_state.agent_conversation.context_trace_store import _validate_graph_tool_observation

    _validate_graph_tool_observation(trace, {"events": [event.model_dump(mode="json")]})


def test_replay_exclusions_use_applicable_explicit_votes_and_attempt_boundaries():
    from types import SimpleNamespace

    from application_state.agent_conversation.jev_retrieval_contract import (
        KEYWORD_KIND,
        RetrievalCandidate,
        retrieval_exclusions_for_replay,
    )
    from application_state.agent_conversation.neighborhood_replay import replay_exclusion_steps

    request = SimpleNamespace(candidates=(
        RetrievalCandidate(handle="kept", label="Kept", kind="object"),
        RetrievalCandidate(handle="dropped", label="Dropped", kind="object"),
        RetrievalCandidate(handle="saved-authored-page:outside", label="Outside", kind="page"),
        RetrievalCandidate(handle="hint", label="Hint", kind=KEYWORD_KIND),
    ))
    result = SimpleNamespace(answers={
        f"candidate_{index}": SimpleNamespace(selected=vote)
        for index, vote in enumerate(("include", "exclude", "exclude", "exclude"))
    })
    excluded = retrieval_exclusions_for_replay(request, result, requested_work="clarify")
    assert [candidate.handle for candidate in excluded.candidates] == ["dropped"]
    assert excluded.total == 1
    assert retrieval_exclusions_for_replay(request, result, requested_work="write_current_page") is None
    events = [
        {"kind": "native_plan_opening_selected_v1", "sequence": sequence,
         "exclusion_replay": excluded.model_dump()}
        for sequence in (1, 3, 5)
    ]
    assert [step.sequence for step in replay_exclusion_steps({"events": events}, start=2, stop=5)] == [3]


def test_effective_retrieval_selections_are_attempt_bounded_and_use_host_event():
    from application_state.agent_conversation.neighborhood_replay import effective_retrieval_selections

    events = [
        {"kind": "native_retrieval_selected_v1", "sequence": 3, "controller_attempt_id": "first",
         "operation": "select_candidates", "selected_handles": ["a", "b"]},
        {"kind": "native_retrieval_selected_v2", "sequence": 7, "controller_attempt_id": "second",
         "operation": "finish_retrieval", "selected_handles": []},
    ]
    first = effective_retrieval_selections({"events": events}, start=0, stop=7)
    second = effective_retrieval_selections({"events": events}, start=7, stop=None)
    assert [(x.operation, x.selected_count, x.controller_attempt_id) for x in first] == [("select_candidates", 2, "first")]
    assert [(x.operation, x.selected_count, x.controller_attempt_id) for x in second] == [("finish_retrieval", 0, "second")]
    assert effective_retrieval_selections(None, start=0, stop=None) == []


def test_trace_reader_projects_durable_selections_into_the_correct_attempt(monkeypatch):
    from contextlib import nullcontext
    from datetime import UTC, datetime
    from unittest.mock import Mock
    from uuid import uuid4
    from application_state.agent_conversation import context_trace_store, service
    from application_state.agent_conversation.context_trace import TurnContextTraceV1

    conversation, turn = uuid4(), uuid4()
    traces = [TurnContextTraceV1(trace_id=uuid4(), world_id='world', conversation_id=conversation,
              turn_id=turn, attempt=i, execution_start_sequence=start, started_at=datetime.now(UTC),
              observations=[]) for i, start in ((1, 0), (2, 5))]
    execution = {'events': [
        {'kind': 'native_retrieval_selected_v1', 'sequence': 2, 'controller_attempt_id': 'first',
         'operation': 'select_candidates', 'selected_handles': ['one']},
        {'kind': 'native_retrieval_selected_v1', 'sequence': 6, 'controller_attempt_id': 'second',
         'operation': 'finish_retrieval', 'selected_handles': []},
    ]}
    conn = Mock()
    first, second = Mock(), Mock()
    first.fetchone.return_value = (execution, conversation, None)
    second.fetchall.return_value = [(traces[0].model_dump(mode='json', by_alias=True), 1),
                                    (traces[1].model_dump(mode='json', by_alias=True), 2)]
    conn.execute.side_effect = [first, second]
    monkeypatch.setattr(context_trace_store, 'unit_of_work', lambda _: nullcontext(conn))
    monkeypatch.setattr(service, '_ready_dsn', lambda: 'test')
    monkeypatch.setattr(context_trace_store, 'native_assertion_steps', lambda *a, **kw: [])
    monkeypatch.setattr(context_trace_store, 'native_discovery_replay', lambda *a, **kw: None)
    monkeypatch.setattr(context_trace_store, 'replay_exclusion_steps', lambda *a, **kw: [])
    result = context_trace_store.TurnContextTraceStore().list_attempts(world_id='world', turn_id=turn)
    assert [(s.operation, s.selected_count) for s in result[0].effective_retrieval_selections] == [('select_candidates', 1)]
    assert [(s.operation, s.selected_count) for s in result[1].effective_retrieval_selections] == [('finish_retrieval', 0)]
