"""Genuine source owner + guarded SDK + durable APP result; synthetic HTTP only."""
import asyncio
from hashlib import sha256
import json
from uuid import uuid4

import httpx
import pytest

from application_state.agent_conversation import AgentConversationService
from application_state.build_proposal.service import BuildProposalService
from apps.live_control_server.models.build_document_proposal import BuildDocumentProposalRequest
from apps.live_control_server.services import build_document_proposal as owner
from tests.application_state.test_agent_conversation_postgres import _new
from apps.live_control_server.services.world_container_registry import create_world_container
from apps.live_control_server.services.workspace_document_registry import (
    create_workspace_document, mark_workspace_document_committed, get_workspace_document_snapshot,
)

TABLE = '| NPC | Job | Detail |\n| --- | --- | --- |\n| Nia | Baker | Keeps a blue lantern |'


@pytest.fixture
def request_case(tmp_path,monkeypatch,application_state_dsn):
    create_world_container(tmp_path,name='Elderwyld')
    record=create_workspace_document(tmp_path,title='Edge',campaign_id='elderwyld',world_id='elderwyld',
        kind='worldbuilding_source',source_domain='worldbuilding',document_class='lore',authority_state='draft',visibility_state='internal')
    target=tmp_path/record.target_relpath
    target.parent.mkdir(parents=True,exist_ok=True)
    target.write_text('## Edge\nA fort town at the edge of a swamp.\n')
    mark_workspace_document_committed(tmp_path,record.document_id,expected_revision=1)
    source=get_workspace_document_snapshot(tmp_path,record.document_id)
    monkeypatch.setattr(owner,'managed_world_data_root',lambda:tmp_path)
    monkeypatch.setattr(owner,'_model',lambda:'gpt-6-luna')
    monkeypatch.setenv('OPENAI_API_KEY','synthetic-only-not-a-key')
    monkeypatch.setenv('DMB_AGENT_PROMPT_CAPTURE','1')
    monkeypatch.setenv('DMB_ARTIFACT_DATA_ROOT',str(tmp_path))
    conversation = _new(AgentConversationService(),'elderwyld')
    request = BuildDocumentProposalRequest(idempotency_key=uuid4(), conversation_id=conversation.conversation_id,
        expected_pointer_revision=1, instruction='Create an NPC and job in a table.', draft_markdown=source.markdown,
        basis=dict(world_id='elderwyld',document_id=source.record.document_id,registry_revision=source.loaded_revision,
            content_sha256=source.content_sha256,visibility='internal',draft_sha256=sha256(source.markdown.encode()).hexdigest(),
            caret=1,draft_generation=0,selection_generation=0))
    return request, source, tmp_path


class Wire(httpx.AsyncBaseTransport):
    def __init__(self,request,text=None,timeout=False):
        self.request,self.calls,self.timeout=request,[],timeout
        self.text=text or json.dumps(dict(target='captured',destination='current_page',replacement_markdown=TABLE,summary='Proposed NPC table.',assumptions=['Nia is invented.']))
    async def handle_async_request(self,request):
        row = BuildProposalService().get('elderwyld',self.request.idempotency_key)
        assert row.state=='sdk_entered' and row.authorization is not None
        assert row.authorization.payload_sha256==sha256(request.content).hexdigest()
        from apps.live_control_server.services.agent_prompt_evidence import read_prompt
        assert read_prompt(row.authorization).encode()==request.content
        self.calls.append(request)
        if self.timeout:
            raise httpx.ReadTimeout('synthetic timeout',request=request)
        response = {'id':'resp_compose','object':'response','created_at':1,
            'status':'completed','model':json.loads(request.content)['model'],'output':[{'type':'message','id':'msg','role':'assistant','status':'completed',
                'content':[{'type':'output_text','text':self.text,'annotations':[]}]}],
            'usage':{'input_tokens':100,'output_tokens':40,'total_tokens':140}}
        events = [dict(type="response.output_text.delta", sequence_number=1,
                       item_id="msg", output_index=0, content_index=0, delta=self.text),
                  dict(type="response.completed", sequence_number=2, response=response)]
        return httpx.Response(200, request=request, headers={"content-type":"text/event-stream"},
            content=''.join('data: '+json.dumps(event)+'\n\n' for event in events).encode())



def test_source_sdk_durable_proposal_and_no_replay(request_case):
    request,source,_ = request_case
    wire=Wire(request)
    result=asyncio.run(owner.compose(request,transport=wire))
    assert result.state=='proposed' and result.proposal.replacement_markdown==TABLE
    assert len(wire.calls)==1 and result.observation['conformance_retry_count']==0
    body=json.loads(wire.calls[0].content)
    assert body['tools']==[] and json.loads(body['input'])['draft_markdown']==source.markdown
    assert body['text']['format'] == {'type':'json_schema','name':'build_document_proposal',
        'schema':owner.BuildComposeOutput.model_json_schema(),'strict':True}
    assert 'output_format' not in json.loads(body['input'])
    assert 'Return only' not in body['instructions'] and 'JSON with exactly' not in body['instructions']
    assert 'concrete spatial details' in body['instructions']
    assert 'identify inventions in assumptions' in body['instructions']
    assert 'Never invent a played event' in body['instructions']
    assert 'not a request\nfor a catalogue of unknowns' in body['instructions']
    assert result.raw_response==wire.text
    assert BuildProposalService().get('elderwyld',result.action_id)==result
    again=asyncio.run(owner.compose(request,transport=wire))
    assert again==result and len(wire.calls)==1
    prompt=owner.read_prompt('elderwyld',result.action_id)
    assert prompt['payload_json'].encode()==wire.calls[0].content


def test_uncertain_dispatch_is_not_replayed(request_case):
    request,_,_=request_case
    wire=Wire(request,timeout=True)
    with pytest.raises(Exception):
        asyncio.run(owner.compose(request,transport=wire))
    row=BuildProposalService().get('elderwyld',request.idempotency_key)
    assert row.state=='unknown' and len(wire.calls)==1
    assert asyncio.run(owner.compose(request,transport=wire)).state=='unknown'
    assert len(wire.calls)==1


@pytest.mark.parametrize('markdown',['<script>bad</script>','[Nia](dmb-node:npc:invented)','<!-- dmb-playable-element:v2:fake -->','```dmb-work-plan-v1\n{}\n```'])
def test_inert_markdown_validation_rejects_fabricated_authority(request_case,markdown):
    request,_,_=request_case
    wire=Wire(request,text=json.dumps(dict(target='captured',destination='current_page',replacement_markdown=markdown,summary='Bad proposal',assumptions=[])))
    with pytest.raises(ValueError):
        asyncio.run(owner.compose(request,transport=wire))
    row=BuildProposalService().get('elderwyld',request.idempotency_key)
    assert row.state=='failed' and row.raw_response==wire.text


def test_source_revision_drift_refuses_without_sdk(request_case):
    request,source,tmp=request_case
    from apps.live_control_server.services.workspace_document_registry import update_workspace_document_metadata
    update_workspace_document_metadata(tmp,source.record.document_id,expected_revision=source.loaded_revision,title='Renamed')
    wire=Wire(request)
    with pytest.raises(ValueError):
        asyncio.run(owner.compose(request,transport=wire))
    assert wire.calls==[]


def test_routes_preserve_exact_receipt_and_private_prompt_scope(request_case, monkeypatch):
    from fastapi import FastAPI
    from fastapi.testclient import TestClient
    from apps.live_control_server.routes import agent
    request, _, _ = request_case
    wire = Wire(request)
    real_compose = owner.compose
    async def compose(body):
        return await real_compose(body, transport=wire)
    monkeypatch.setattr(owner, 'compose', compose)
    monkeypatch.setattr(agent, 'enforce_native_graph_gm', lambda _: None)
    monkeypatch.setattr(agent, '_verified_world_id', lambda value: value)
    app = FastAPI()
    app.include_router(agent.router, prefix='/api/live')
    root = '/api/live/agent/worlds/elderwyld/build-proposals'
    with TestClient(app) as client:
        reply = client.post(root, json=request.model_dump(mode='json'))
        assert reply.status_code == 200, reply.text
        row = reply.json()['record']
        assert row['state'] == 'proposed' and 'raw_response' not in row
        assert len(wire.calls) == 1
        assert client.post(root, json=request.model_dump(mode='json')).json()['record'] == row
        assert len(wire.calls) == 1
        action = row['action_id']
        listing = client.get(root, params={'conversation_id':str(request.conversation_id)})
        assert listing.status_code == 200 and listing.json()['records'] == [row]
        assert client.get(f'{root}/{action}').json()['record'] == row
        prompt = client.get(f'{root}/{action}/prompt')
        assert prompt.status_code == 200 and prompt.headers['cache-control'] == 'no-store'
        assert prompt.json()['payload_json'].encode() == wire.calls[0].content
        assert client.get(f'/api/live/agent/worlds/foreign/build-proposals/{action}/prompt').status_code == 404
        assert client.get(f'{root}/{action}/prompt?extra=selector').status_code == 422
        duplicate = [('conversation_id',str(request.conversation_id))]*2
        assert client.get(root,params=duplicate).status_code == 422
        inserted = client.post(f'{root}/{action}/inserted',params={'expected_revision':row['revision']})
        assert inserted.status_code == 200 and inserted.json()['record']['inserted_in_draft'] is True
        assert client.get(f'{root}/{action}').json()['record']['inserted_in_draft'] is True
        assert client.post(root,json={**request.model_dump(mode='json'),'basis':{**request.basis.model_dump(),'world_id':'foreign'}}).status_code == 422


@pytest.mark.parametrize('method,suffix', [('GET',''),('POST',''),('GET','/00000000-0000-4000-8000-000000000001'),
    ('GET','/00000000-0000-4000-8000-000000000001/prompt'),('POST','/00000000-0000-4000-8000-000000000001/inserted')])
def test_routes_require_gm_before_storage(request_case,monkeypatch,method,suffix):
    from fastapi import FastAPI, HTTPException
    from fastapi.testclient import TestClient
    from apps.live_control_server.routes import agent
    request,_,_=request_case
    def deny(_):
        raise HTTPException(status_code=403,detail={'code':'gm_required'})
    monkeypatch.setattr(agent,'enforce_native_graph_gm',deny)
    monkeypatch.setattr(agent,'_verified_world_id',lambda _: pytest.fail('Denied caller reached owner resolution'))
    app=FastAPI()
    app.include_router(agent.router,prefix='/api/live')
    with TestClient(app) as client:
        params={'conversation_id':str(request.conversation_id)} if method=='GET' and not suffix else {'expected_revision':1} if suffix.endswith('inserted') else {}
        reply=client.request(method,'/api/live/agent/worlds/elderwyld/build-proposals'+suffix,params=params,
            json=request.model_dump(mode='json') if method=='POST' and not suffix else None)
        assert reply.status_code==403



def test_strict_schema_failure_retains_raw_response_usage_and_never_repairs(request_case):
    request,_,_=request_case
    wire=Wire(request,text='{"replacement_markdown":123}')
    with pytest.raises(Exception):
        asyncio.run(owner.compose(request,transport=wire))
    row=BuildProposalService().get('elderwyld',request.idempotency_key)
    assert row.state=='failed' and row.raw_response==wire.text
    assert len(wire.calls)==1
    assert row.observation['input_tokens']==100 and row.observation['output_tokens']==40
    assert row.observation['conformance_retry_count']==0
    assert asyncio.run(owner.compose(request,transport=wire))==row
    assert len(wire.calls)==1


def test_editor_anchor_survives_actual_proposal_persistence_and_replay(request_case):
    request, _, _ = request_case
    request = request.model_copy(update={"basis": request.basis.model_copy(update={"editor_sha256": "e" * 64})})
    wire = Wire(request)
    result = asyncio.run(owner.compose(request, transport=wire))
    reopened = BuildProposalService().get("elderwyld", result.action_id)
    assert reopened.reservation.basis.editor_sha256 == "e" * 64
    assert reopened.reservation.fingerprint == result.request_fingerprint
    assert asyncio.run(owner.compose(request, transport=wire)) == reopened
    assert len(wire.calls) == 1
    changed = request.model_copy(update={"basis": request.basis.model_copy(update={"editor_sha256": "f" * 64})})
    with pytest.raises(owner.BuildComposeError, match="build_compose_request_changed"):
        asyncio.run(owner.compose(changed, transport=wire))
    assert len(wire.calls) == 1


def test_historical_basis_keeps_its_exact_serialized_shape_and_fingerprint(request_case):
    from application_state.build_proposal.types import BuildProposalBasis
    from pydantic import ValidationError
    request, _, _ = request_case
    old = request.basis.model_dump(mode="json")
    assert "editor_sha256" not in old and "selection" not in old
    basis = BuildProposalBasis.model_validate(old)
    assert basis.editor_sha256 is None and basis.model_dump(mode="json") == old
    assert request.model_copy(update={"basis": basis}).model_dump(mode="json") == request.model_dump(mode="json")
    with pytest.raises(ValidationError):
        BuildProposalBasis.model_validate({**old, "editor_sha256": "not-a-digest"})


def test_selected_revision_target_is_frozen_in_writer_and_reservation(request_case):
    from application_state.build_proposal.types import BuildProposalSelection
    request, source, root = request_case
    selected = BuildProposalSelection(end=18, text="A fort town")
    request = request.model_copy(update={"basis": request.basis.model_copy(update={"selection": selected}),
        "instruction": "Revise this passage to emphasize the flooded road."})
    wire = Wire(request)
    result = asyncio.run(owner.compose(request, transport=wire))
    body = json.loads(wire.calls[0].content)
    packet = json.loads(body["input"])
    assert packet["source_basis"]["selection"] == selected.model_dump(mode="json")
    assert "revise only that selected passage" in body["instructions"]
    assert result.reservation.basis.selection == selected
    assert get_workspace_document_snapshot(root, source.record.document_id) == source
    assert asyncio.run(owner.compose(request, transport=wire)) == result
    assert len(wire.calls) == 1
    changed = request.model_copy(update={"basis": request.basis.model_copy(update={
        "selection": BuildProposalSelection(end=19, text="A different target")})})
    with pytest.raises(owner.BuildComposeError, match="request_changed"):
        asyncio.run(owner.compose(changed, transport=wire))


@pytest.mark.parametrize("selection", [{"end":1,"text":"Text"},{"end":5,"text":"  "},{"end":True,"text":"Text"}])
def test_invalid_selected_revision_target_is_refused(request_case, selection):
    from application_state.build_proposal.types import BuildProposalBasis
    from pydantic import ValidationError
    request, _, _ = request_case
    with pytest.raises(ValidationError):
        BuildProposalBasis.model_validate({**request.basis.model_dump(mode="json"), "selection":selection})


@pytest.mark.parametrize('destination', ['different_page', 'unresolved'])
def test_writer_refuses_foreign_destination_without_creating_a_proposal(request_case, destination):
    request, source, _ = request_case
    raw = json.dumps(dict(target="captured",destination=destination, replacement_markdown='',
        summary='The requested destination differs or is unresolved.', assumptions=[]))
    wire = Wire(request, text=raw)
    with pytest.raises(owner.BuildComposeTargetMismatch, match='build_compose_target_mismatch'):
        asyncio.run(owner.compose(request, transport=wire))
    row = BuildProposalService().get('elderwyld', request.idempotency_key)
    assert row.state == 'failed' and row.failure_code == 'build_compose_target_mismatch'
    assert row.proposal is None and row.raw_response == raw
    assert len(wire.calls) == 1
    assert asyncio.run(owner.compose(request, transport=wire)) == row
    assert len(wire.calls) == 1
    assert get_workspace_document_snapshot(owner.managed_world_data_root(), source.record.document_id) == source


@pytest.mark.parametrize('destination', [None, 'another_page', 1])
def test_missing_or_invalid_destination_has_no_old_wire_fallback(destination):
    from pydantic import ValidationError
    raw = dict(replacement_markdown='A useful paragraph.', summary='Writing.', assumptions=[])
    if destination is not None:
        raw['destination'] = destination
    with pytest.raises(ValidationError):
        owner._result(json.dumps(raw))


def test_destination_is_not_added_to_retained_proposal_records():
    from application_state.build_proposal.types import BuildGeneratedProposal
    raw = dict(replacement_markdown='A useful paragraph.', summary='Writing.', assumptions=[])
    stored = BuildGeneratedProposal.model_validate(raw)
    assert stored.model_dump() == raw
    assert owner._result(json.dumps(dict(target='captured',destination='current_page', **raw))) == stored.model_copy(update={"target":"captured"})


def test_whole_body_offer_is_bound_into_request_result_and_replay(request_case):
    from application_state.build_proposal.types import BuildPageBodyOffer
    request, source, _ = request_case
    request = request.model_copy(update={
        'basis': request.basis.model_copy(update={'editor_sha256':'e'*64}),
        'page_body_offer':BuildPageBodyOffer(end=83),
    })
    body = dict(destination='current_page', target='page_body',
        replacement_markdown='Preparation only.\n\nOffer communication before combat.',
        summary='Replace the page body.', assumptions=[])
    wire=Wire(request,text=json.dumps(body))
    record=asyncio.run(owner.compose(request,transport=wire))
    assert record.proposal.target=='page_body'
    assert record.reservation.basis.caret==1 and record.reservation.basis.selection is None
    packet=json.loads(json.loads(wire.calls[0].content)['input'])
    assert packet['page_body_offer']=={'end':83}
    assert asyncio.run(owner.compose(request,transport=wire))==record
    assert len(wire.calls)==1
    changed=request.model_copy(update={'page_body_offer':BuildPageBodyOffer(end=84)})
    with pytest.raises(owner.BuildComposeError,match='request_changed'):
        asyncio.run(owner.compose(changed,transport=wire))
    assert get_workspace_document_snapshot(owner.managed_world_data_root(),source.record.document_id)==source


@pytest.mark.parametrize('target,markdown', [('page_body','Complete body.'),('unavailable','')])
def test_unoffered_or_unavailable_whole_page_never_falls_back_to_append(target,markdown):
    with pytest.raises(owner.BuildComposeTargetMismatch):
        owner._result(json.dumps(dict(destination='current_page',target=target,
            replacement_markdown=markdown,summary='Cannot safely replace.',assumptions=[])))


def test_new_writer_output_requires_target_but_old_stored_result_keeps_exact_bytes():
    from pydantic import ValidationError
    from application_state.build_proposal.types import BuildGeneratedProposal
    raw=dict(replacement_markdown='Old fragment.',summary='Retained.',assumptions=[])
    assert BuildGeneratedProposal.model_validate(raw).model_dump()==raw
    with pytest.raises(ValidationError):
        owner._result(json.dumps(dict(destination='current_page',**raw)))


def test_offered_body_cannot_be_interpreted_as_a_historical_targetless_result(request_case):
    from application_state.build_proposal.types import BuildPageBodyOffer, BuildProposalRecord
    from pydantic import ValidationError
    request,_,_=request_case
    request=request.model_copy(update={'basis':request.basis.model_copy(update={'editor_sha256':'e'*64}),
        'page_body_offer':BuildPageBodyOffer(end=83)})
    record=asyncio.run(owner.compose(request,transport=Wire(request)))
    raw=record.model_dump(mode='json');raw['proposal'].pop('target')
    with pytest.raises(ValidationError,match='explicit generated target'):
        BuildProposalRecord.model_validate(raw)


def test_page_end_is_a_distinct_frozen_writer_choice_not_a_moved_caret(request_case):
    from application_state.build_proposal.types import BuildPageEndOffer
    request, source, _ = request_case
    request = request.model_copy(update={
        'basis': request.basis.model_copy(update={'editor_sha256':'e'*64}),
        'page_end_offer':BuildPageEndOffer(end=83),
    })
    body = dict(destination='current_page', target='page_end',
        replacement_markdown='## Readiness\n\n- Check the proposed route.',
        summary='Add after existing content.', assumptions=[])
    wire=Wire(request,text=json.dumps(body))
    record=asyncio.run(owner.compose(request,transport=wire))
    assert record.proposal.target=='page_end'
    assert record.reservation.basis.caret==1 and record.reservation.basis.selection is None
    packet=json.loads(json.loads(wire.calls[0].content)['input'])
    assert packet['page_end_offer']=={'end':83} and packet['page_body_offer'] is None
    assert asyncio.run(owner.compose(request,transport=wire))==record and len(wire.calls)==1
    changed=request.model_copy(update={'page_end_offer':BuildPageEndOffer(end=84)})
    with pytest.raises(owner.BuildComposeError,match='request_changed'):
        asyncio.run(owner.compose(changed,transport=wire))
    assert get_workspace_document_snapshot(owner.managed_world_data_root(),source.record.document_id)==source


def test_unoffered_page_end_never_falls_back_to_caret():
    with pytest.raises(owner.BuildComposeTargetMismatch,match='not_offered'):
        owner._result(json.dumps(dict(destination='current_page',target='page_end',
            replacement_markdown='Addition.',summary='Append.',assumptions=[])))


def test_historical_reservation_has_no_implicit_page_end_offer(request_case):
    from application_state.build_proposal.types import BuildProposalReservation
    request,_,_=request_case
    original=request.reservation_only()
    raw=original.model_dump(mode='json')
    assert 'page_end_offer' not in raw
    assert BuildProposalReservation.model_validate(raw).model_dump(mode='json')==raw
    assert BuildProposalReservation.model_validate(raw).fingerprint==original.fingerprint

pytestmark = pytest.mark.usefixtures("application_state_dsn")


def test_source_reader_accepts_exact_committed_nonfile_owner_projection(request_case, monkeypatch):
    request, source, _ = request_case
    projection = source.model_copy(update={"file_exists": False,
        "record": source.record.model_copy(update={"target_relpath": None})})
    monkeypatch.setattr(owner, "get_workspace_document_snapshot", lambda *args: projection)
    assert owner._source(request).markdown == source.markdown
    for changes in ({"content_status": "draft"}, {"world_id": "foreign"},
                    {"document_id": str(uuid4())}, {"revision": source.loaded_revision + 1}):
        projection.record = source.record.model_copy(update=changes)
        with pytest.raises(owner.BuildComposeError, match="build_compose_source_changed"):
            owner._source(request)
