"""Saved selection adapter through the real governed HTTP boundary; isolated native port."""
from types import SimpleNamespace
import pytest
from tests.test_graph_document_source import case, TEXT
from apps.live_control_server.services.graph_document_relationship import DocumentRelationshipRequest, relationship_request


def intent(c):
    return {'world_id':'eldyrwild','document_source':c.selector.model_dump(by_alias=True),'quote':TEXT.strip(),
        'source':{'node_id':None,'label':'Brin','kind':'npc'},
        'target':{'node_id':None,'label':'Shop','kind':'location'},
        'predicate':'owns','label':'owns','context':'Brin owns this shop in the authored setting.'}


@pytest.fixture
def graph(case,monkeypatch):
    from fastapi.testclient import TestClient
    monkeypatch.setenv('DMB_AGENT_GRAPH_AUTH_MODE','local_operator')
    monkeypatch.setenv('DMB_AGENT_GRAPH_AUTH_ENVIRONMENT','local')
    monkeypatch.setenv('DMB_AGENT_GRAPH_LOCAL_OPERATOR_TOKEN','synthetic-relationship-local-token-with-adequate-length')
    case.client=TestClient(case.client.app,client=('127.0.0.1',50000),headers={'Authorization':'Bearer synthetic-relationship-local-token-with-adequate-length'})
    nodes=[]
    monkeypatch.setattr('apps.live_control_server.services.graph_document_relationship.project_managed_world_graph',lambda *a,**kw:SimpleNamespace(projection=SimpleNamespace(nodes=nodes)))
    return nodes


def test_request_preview_and_explicit_confirmation_reuse_existing_writer(case,graph):
    original=case.target.read_bytes()
    response=case.client.post('/api/live/graph-authoring/document-relationship/request',json=intent(case))
    assert response.status_code==200,response.text
    request=response.json()
    assert case.authority.publish_calls==0
    preview=case.client.post('/api/live/graph-authoring/prepare',json=request)
    assert preview.status_code==200,preview.text
    assert case.authority.publish_calls==0
    confirmed={**request,'confirmToken':preview.json()['confirm_token']}
    for _ in range(2):
        receipt=case.client.post('/api/live/graph-authoring/commit',json=confirmed)
        assert receipt.status_code==200,receipt.text
    assert case.authority.publish_calls==1
    assert case.target.read_bytes()==original
    assert request['proposals'][-1]['summary']==intent(case)['context']
    assert request['proposals'][-1]['relationshipLabel']=='owns — '+intent(case)['context']
    edge=next(a for a in case.authority.published_requests[0].contribution.accepted_assertions if a.assertion_kind=='edge')
    assert edge.label==request['proposals'][-1]['relationshipLabel']


@pytest.mark.parametrize('mutation',['quote','revision','world','self','predicate'])
def test_invalid_review_refuses_without_publication(case,graph,mutation):
    request=intent(case)
    if mutation=='quote':request['quote']='Not in the source'
    elif mutation=='revision':request['document_source']['revision']+=1
    elif mutation=='world':request['world_id']='foreign'
    elif mutation=='self':request['target']=request['source']
    else:request['predicate']=' '
    response=case.client.post('/api/live/graph-authoring/document-relationship/request',json=request)
    assert response.status_code==409,response.text
    assert case.authority.publish_calls==0


@pytest.mark.parametrize('alias',[False,True])
def test_new_identity_cannot_duplicate_existing_name_or_alias(case,graph,alias):
    graph.append(SimpleNamespace(node_id='npc:brin',label='Smith' if alias else 'Brin',kind='npc',aliases=['Brin'] if alias else []))
    response=case.client.post('/api/live/graph-authoring/document-relationship/request',json=intent(case))
    assert response.status_code==409,response.text
    assert 'already exists' in response.text
    assert case.authority.publish_calls==0


def test_existing_identity_requires_exact_world_label_and_kind(case,graph):
    graph.append(SimpleNamespace(node_id='npc:brin',label='Brin',kind='npc',aliases=[]))
    request=intent(case);request['source']['node_id']='npc:brin'
    built=relationship_request(case.root,DocumentRelationshipRequest.model_validate(request))
    assert len(built.proposals)==2
    assert built.proposals[-1].source_object_ref['nodeId']=='npc:brin'
    request['source']['kind']='location'
    assert case.client.post('/api/live/graph-authoring/document-relationship/request',json=request).status_code==409


def test_temporal_context_and_direction_are_preserved_without_inference(case,graph):
    request=intent(case);request['target']={'node_id':None,'label':'Rowan','kind':'npc'}
    request.update(predicate='works_with',label='worked together temporarily',context='A past temporary stint; this asserts no current employment or reciprocal edge.')
    built=relationship_request(case.root,DocumentRelationshipRequest.model_validate(request))
    row=built.proposals[-1]
    assert row.relationship_type=='works_with' and row.direction=='directed'
    assert row.summary==request['context'] and row.relationship_label==request['label']+' — '+request['context']
    assert len([p for p in built.proposals if p.proposal_kind=='relationship'])==1


def test_missing_source_is_an_actionable_registry_error(case,graph,monkeypatch):
    from apps.live_control_server.services.workspace_document_registry import WorkspaceDocumentRegistryError
    def missing(*args):
        raise WorkspaceDocumentRegistryError('The selected saved page is no longer available.')
    monkeypatch.setattr('apps.live_control_server.services.graph_document_relationship.get_workspace_document_snapshot',missing)
    response=case.client.post('/api/live/graph-authoring/document-relationship/request',json=intent(case))
    assert response.status_code==404,response.text
    assert response.json()['detail']['code']=='relationship_source_unavailable'
    assert case.authority.publish_calls==0


@pytest.mark.parametrize('body,quote',[(TEXT+TEXT,TEXT.strip()),(TEXT+'\nAnother source block.\n',TEXT+'\nAnother source block.')])
def test_ambiguous_or_cross_block_quote_cannot_be_previewed(case,graph,body,quote):
    import hashlib
    from apps.live_control_server.services.workspace_document_registry import mark_workspace_document_committed
    request=intent(case)
    case.target.write_text(body)
    record=mark_workspace_document_committed(case.root,case.record.document_id)
    request['document_source'].update(revision=record.revision,contentSha256=hashlib.sha256(body.encode()).hexdigest())
    request['quote']=quote
    response=case.client.post('/api/live/graph-authoring/document-relationship/request',json=request)
    assert response.status_code==409,response.text
    assert case.authority.publish_calls==0


@pytest.mark.parametrize('mode,status',[('missing',401),('wrong',401),('remote',403),('player',403)])
def test_new_adapter_denies_before_source_graph_or_freeze_io(case,graph,monkeypatch,mode,status):
    from fastapi.testclient import TestClient
    from unittest.mock import Mock
    from apps.live_control_server.services.agent_graph_auth import authenticate_native_graph_principal,NativeGraphPrincipal
    protected=Mock(side_effect=AssertionError('Denied request must not reach protected source/native IO'))
    monkeypatch.setattr('apps.live_control_server.routes.graph_authoring.relationship_request',protected)
    if mode=='player':
        case.client.app.dependency_overrides[authenticate_native_graph_principal]=lambda:NativeGraphPrincipal('player','player','local_operator')
    headers={} if mode=='missing' else {'Authorization':'Bearer wrong' if mode=='wrong' else 'Bearer synthetic-relationship-local-token-with-adequate-length'}
    client=TestClient(case.client.app,client=('203.0.113.1' if mode=='remote' else '127.0.0.1',50000))
    response=client.post('/api/live/graph-authoring/document-relationship/request',json=intent(case),headers=headers)
    assert response.status_code==status,response.text
    protected.assert_not_called()
