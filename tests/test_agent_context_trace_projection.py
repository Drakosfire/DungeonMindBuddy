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
