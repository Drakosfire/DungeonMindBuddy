"""Synthetic source/Graph fixtures with actual SDK, APP and PostgreSQL admission."""
from copy import deepcopy
import json
from types import SimpleNamespace
from uuid import uuid4
import httpx
import pytest
from tests.test_build_related_pages import build_case
import tests.test_build_related_pages as cases
from application_state.agent_conversation import types as t
from application_state.agent_conversation import connected_page_origins as origins
from application_state.agent_conversation.collaboration import saved_excerpt
from application_state.agent_conversation.source_writer_output import validate_writer_format


@pytest.fixture
def primary_review(build_case,monkeypatch,tmp_path,request):
    selected = getattr(request,"param",None)=="selected"
    aliased = getattr(request,"param",None)=="aliased"
    if aliased:
        from hashlib import sha256
        original_case=cases.world_case
        original_snapshot=cases.BuildDraftSnapshotV1
        captured=[]
        def world_case(*args,**kwargs):
            value=original_case(*args,**kwargs);captured.append(value[0][0].markdown);return value
        def snapshot(**kwargs):
            text=captured[0]
            return original_snapshot(**{**kwargs,"draft_markdown":text,"draft_sha256":sha256(text.encode()).hexdigest()})
        monkeypatch.setattr(cases,"world_case",world_case)
        monkeypatch.setattr(cases,"BuildDraftSnapshotV1",snapshot)
    original=cases.PagesWriter
    class PrimaryWriter(original):
        async def handle_async_request(self,request):
            response=await super().handle_async_request(request)
            wire=json.loads(request.content);packet=json.loads(wire['input'])
            from application_state.agent_conversation.build_draft_context import resolve_body_aliases
            primary=resolve_body_aliases(packet)['artifact_under_edit']['sections'][0]
            if aliased:
                assert packet['artifact_under_edit']['sections'][0]['text_ref']=='working_draft_context'
                assert 'use that body with the saved row' in wire['instructions']
                assert 'Never use working_draft_context as a saved origin' not in wire['instructions']
            assert packet[origins.KEY]==origins.POLICY
            assert wire['text']['format']['name']==('build_intentional_plan_selection_answer_v1' if selected else origins.FORMAT)
            if selected:
                assert packet['plan_output_contract']['kind']=='build_plan_output_contract_v2'
                assert wire['text']['format']['schema']['$defs']['ProposedStepV2']['required']==['text','kind','selected']
            assert primary['read_id'] in wire['text']['format']['schema']['$defs']['ProposedConnectedPage']['properties']['read_id']['enum']
            data=response.json();body=json.loads(data['output'][0]['content'][0]['text'])
            body['collaboration'].update(read_id=primary['read_id'],quote=primary['text'])
            data['output'][0]['content'][0]['text']=json.dumps(body)
            return httpx.Response(200,request=request,json=data)
    monkeypatch.setattr(cases,'PagesWriter',PrimaryWriter)
    return cases.completed.__wrapped__(build_case,monkeypatch,tmp_path,SimpleNamespace(param='connected_page_cap' if selected else 'connected_page'))


def parts(value):
    turn,service,*_=value
    binding=next(e for e in turn.graph_context_execution.events if isinstance(e,t.CompletionBindingEventV1))
    return turn,service,binding.provider_attempt_id


def test_primary_origin_survives_actual_sdk_app_and_derived_readback(primary_review):
    from apps.live_control_server.services.agent_connected_page_origin import open_origin
    turn,service,attempt=parts(primary_review)
    result=open_origin(service,turn.world_id,turn.turn_id)
    read=next(e for e in turn.graph_context_execution.events if isinstance(e,t.ValidatedBuildSectionReadV1)
        and str(e.read_id)==turn.completion.collaboration.read_id)
    assert result['origin']==dict(kind='saved_page_excerpt',document_id=turn.provenance.primary_work.object_id,
        revision=read.source_basis.registry_revision,content_sha256=read.source_basis.content_sha256,
        line_start=read.line_start,line_end=read.line_end,selected_text=read.text)
    assert service.inspect_turn(world_id=turn.world_id,turn_id=turn.turn_id)==turn
    assert result['read_id']==turn.completion.collaboration.read_id


def test_acquired_read_without_producer_inclusion_is_not_an_origin(primary_review):
    turn,_,attempt=parts(primary_review);execution=turn.graph_context_execution
    changed=execution.model_copy(update={'events':[e for e in execution.events if not isinstance(e,t.BuildSectionProviderInclusionV1)]})
    rows=origins.execution_rows(changed,turn.graph_context_receipt.source_basis,attempt)
    with pytest.raises(ValueError,match='unread'):
        saved_excerpt(turn.completion.collaboration,rows)


def test_other_requested_work_cannot_gain_a_primary_origin(primary_review):
    turn,_,attempt=parts(primary_review);execution=turn.graph_context_execution
    changed=execution.model_copy(update={'events':[e.model_copy(update={'requested_work':'discuss'})
        if isinstance(e,t.BuildRequestedWorkResolutionV1) else e for e in execution.events]})
    with pytest.raises(ValueError,match='unread'):
        saved_excerpt(turn.completion.collaboration,origins.execution_rows(changed,turn.graph_context_receipt.source_basis,attempt))


def test_marker_and_new_format_are_closed_and_historical_schema_stays_related_only(primary_review):
    from application_state.agent_conversation.build_intentional_response import output_schema
    packet=json.loads(primary_review[5].staged.input_json)
    fmt={'type':'json_schema','name':origins.FORMAT,'strict':True,'schema':output_schema(packet)}
    validate_writer_format(fmt,packet)
    old=deepcopy(packet);del old[origins.KEY]
    old_schema=output_schema(old)
    primary_ids={r['read_id'] for r in packet['artifact_under_edit']['sections']}
    assert not primary_ids.intersection(old_schema['$defs']['ProposedConnectedPage']['properties']['read_id']['enum'])
    with pytest.raises(ValueError,match='marker and writer format'):
        validate_writer_format(fmt,old)
    with pytest.raises(ValueError,match='marker and writer format'):
        validate_writer_format({**fmt,'name':'build_intentional_response_answer_v1'},packet)
    changed=deepcopy(packet);changed[origins.KEY]='unknown'
    with pytest.raises(ValueError):origins.packet_rows(changed)


def test_omitted_or_changed_primary_input_cannot_gain_origin_authority(primary_review):
    turn,_,attempt=parts(primary_review);packet=json.loads(primary_review[5].staged.input_json)
    auth=next(e for e in turn.graph_context_execution.events if isinstance(e,t.ProviderAttemptAuthorizedEventV3) and e.provider_attempt_id==attempt)
    for mutation in ['text','omit','basis']:
        changed=deepcopy(packet)
        if mutation=='text':changed['artifact_under_edit']['sections'][0]['text']='Foreign text'
        elif mutation=='omit':changed['artifact_under_edit']['sections']=[]
        else:changed['source_basis']['content_sha256']='a'*64
        with pytest.raises(ValueError):origins.validate_packet(changed,turn.graph_context_execution,auth)


def test_exact_excerpt_offsets_and_ambiguous_quote_refusal(primary_review):
    proposal=primary_review[0].completion.collaboration.model_copy(update={'read_id':str(uuid4()),'quote':'hinge'})
    row={'read_id':proposal.read_id,'markdown':'Heading\nhinge check\nLast','_line_offset':17,
        'page':{'document_id':str(uuid4()),'registry_revision':3,'content_sha256':'a'*64}}
    origin=saved_excerpt(proposal,[row]);assert origin['line_start']==origin['line_end']==19
    assert origin['selected_text']=='hinge check'
    with pytest.raises(ValueError,match='one exact occurrence'):saved_excerpt(proposal,[{**row,'markdown':'hinge hinge'}])
    with pytest.raises(ValueError,match='unread'):saved_excerpt(proposal,[row,row])


@pytest.mark.parametrize('completed',['connected_page'],indirect=True)
def test_related_origin_readback_remains_available(completed):
    from apps.live_control_server.services.agent_connected_page_origin import open_origin
    turn,service,*_=completed
    assert open_origin(service,turn.world_id,turn.turn_id)['origin']['document_id']!=turn.provenance.primary_work.object_id


# Reuse the existing related-review integration fixture for the final contrast case.
from tests.test_build_related_pages import completed


def test_origin_http_route_is_authenticated_and_has_no_caller_selector(primary_review,monkeypatch):
    from fastapi import FastAPI
    from fastapi.testclient import TestClient
    from apps.live_control_server.routes import agent
    turn,service,_=parts(primary_review)
    token='synthetic-origin-operator-token-with-adequate-length'
    monkeypatch.setenv('DMB_AGENT_GRAPH_AUTH_MODE','local_operator')
    monkeypatch.setenv('DMB_AGENT_GRAPH_AUTH_ENVIRONMENT','development')
    monkeypatch.setenv('DMB_AGENT_GRAPH_LOCAL_OPERATOR_TOKEN',token)
    monkeypatch.setattr(agent,'_verified_world_id',lambda value:value)
    calls=[]
    def owner(request):
        calls.append(request)
        return service
    monkeypatch.setattr(agent,'_conversation_service',owner)
    app=FastAPI();app.include_router(agent.router,prefix='/api/live')
    path=f'/api/live/agent/worlds/{turn.world_id}/conversation/turns/{turn.turn_id}/connected-page-origin'
    with TestClient(app,client=('127.0.0.1',5000)) as client:
        assert client.get(path).status_code==401 and not calls
        headers={'Authorization':'Bearer '+token}
        response=client.get(path,headers=headers)
        assert response.status_code==200,response.text
        assert response.json()['read_id']==turn.completion.collaboration.read_id
        count=len(calls)
        assert client.get(path+'?read_id=foreign',headers=headers).status_code==422
        assert len(calls)==count
        assert client.get(path+'/extra',headers=headers).status_code==404


@pytest.mark.parametrize('primary_review',['aliased'],indirect=True)
def test_primary_saved_origin_uses_exact_body_alias_through_sdk_app(primary_review):
    from apps.live_control_server.services.agent_connected_page_origin import open_origin
    turn,service,_=parts(primary_review)
    origin=open_origin(service,turn.world_id,turn.turn_id)['origin']
    assert origin['document_id']==turn.provenance.primary_work.object_id
    assert turn.completion.collaboration.quote in origin['selected_text']
    assert service.inspect_turn(world_id=turn.world_id,turn_id=turn.turn_id)==turn


@pytest.mark.parametrize('primary_review',['selected'],indirect=True)
def test_selection_contract_composes_with_actual_primary_origin_sdk_app(primary_review):
    from apps.live_control_server.services.agent_connected_page_origin import open_origin
    turn,service,_=parts(primary_review)
    assert turn.completion.schema_=='dmb_build_intentional_response_completion_v3'
    packet=json.loads(primary_review[5].staged.input_json)
    from application_state.agent_conversation.build_intentional_response import output_schema
    fmt={'type':'json_schema','name':'build_intentional_plan_selection_answer_v1','strict':True,'schema':output_schema(packet)}
    validate_writer_format(fmt,packet)
    for mutate in ('missing_marker','old_format','missing_selected'):
        changed=deepcopy(packet);changed_format=deepcopy(fmt)
        if mutate=='missing_marker':changed.pop('plan_output_contract')
        elif mutate=='old_format':changed_format['name']=origins.FORMAT
        else:changed_format['schema']['$defs']['ProposedStepV2']['required'].remove('selected')
        with pytest.raises(ValueError):validate_writer_format(changed_format,changed)
    assert open_origin(service,turn.world_id,turn.turn_id)['origin']['document_id']==turn.provenance.primary_work.object_id
    assert service.inspect_turn(world_id=turn.world_id,turn_id=turn.turn_id)==turn
