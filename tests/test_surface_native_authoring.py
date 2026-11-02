"""Actual owned writer requests with shared native input; no Turn activation."""
import asyncio
from hashlib import sha256
import json
from uuid import NAMESPACE_URL, uuid4, uuid5

import pytest

from application_state.agent_conversation import types as t
from application_state.agent_conversation import build_draft_context as draft
from application_state.agent_conversation.build_intentional_response import Capabilities
from application_state.agent_conversation.native_writer import model_frame, model_work_frame, verify_input_records
from application_state.build_proposal.types import BuildWriteCapability, BuildProposalOrigin
from apps.live_control_server.services import build_document_proposal as owner, build_image_writer as image_owner
from tests.test_build_document_proposal import request_case as original_case, Wire
from tests.test_build_proposal_shared_writer import Parent
from tests.test_surface_native_context import seal, provenance_for
from tests.test_surface_native_execution import component, execution, controller, outcomes, build_resolution
from tests.test_surface_native_writer import authorize, with_work_selection


@pytest.fixture
def request_case(tmp_path,monkeypatch,application_state_dsn):
    return original_case.__wrapped__(tmp_path,monkeypatch,application_state_dsn)


def native_case(request,operation,*,captured=True):
    context,record=component('build',unavailable=True)
    request=request.model_copy(update={'basis':request.basis.model_copy(update={'editor_sha256':'b'*64})})
    cap=BuildWriteCapability.model_validate(request.model_dump(exclude={'instruction','origin'}))
    basis=t.BuildSourceContextBasisV1.model_validate({k:getattr(cap.basis,k)
        for k in t.BuildSourceContextBasisV1.model_fields})
    work_context=context.work_context.model_copy(update={'source_basis':basis})
    provenance=provenance_for(work_context).model_copy(update={'surface_instance_id':record.policy.action.intent.surface_instance_id})
    turn_id,client_id=uuid4(),uuid4()
    work=dict(world_id=basis.world_id,conversation_id=cap.conversation_id,turn_id=turn_id,attempt=1,
        provenance=provenance,idempotency_key=uuid5(NAMESPACE_URL,f'dmb-agent-turn:{basis.world_id}:{client_id}'),work_proof={})
    snapshot=draft.BuildDraftSnapshotV1(**basis.model_dump(),draft_markdown=cap.draft_markdown,
        draft_sha256=cap.basis.draft_sha256,editor_sha256=cap.basis.editor_sha256,draft_generation=cap.basis.draft_generation)
    draft_request=draft.BuildDraftContextRequestV1(snapshot=snapshot,conversation_id=cap.conversation_id,
        expected_pointer_revision=cap.expected_pointer_revision)
    old=record.policy.action.intent
    intent=old.model_copy(update=dict(world_id=basis.world_id,message=request.instruction,
        primary_work=old.primary_work.model_copy(update=dict(object_id=basis.document_id,expected_revision=basis.registry_revision,
            expected_content_sha256=basis.content_sha256)),graph_request=old.graph_request.model_copy(update={'world_id':basis.world_id}),
        build_write_capability_sha256=t.canonical_sha256(cap.model_dump(mode='json')),
        build_draft_context_sha256=draft.digest(draft_request.model_dump(mode='json',by_alias=True)) if captured else None))
    action=record.policy.action.model_copy(update=dict(intent=intent,write_capability=cap,
        capabilities=Capabilities(('answer_from_sources','propose_build_insertion','prepare_build_image')),saved_source_char_count=len(cap.draft_markdown)))
    wire=context.model_dump(mode='json',by_alias=True)
    wire.update(work_context=work_context.model_dump(mode='json'),provenance_sha256=t.canonical_sha256(provenance))
    wire['source_authority']['managed_world_id']=basis.world_id
    wire['native_query']['managed_world_id']=basis.world_id
    context=type(context).model_validate_json(json.dumps(seal(wire)))
    policy=record.policy.model_copy(update=dict(action=action,source_authority_sha256=t.canonical_sha256(context.source_authority),
        native_query_sha256=t.canonical_sha256(context.native_query)))
    first=controller('build',policy,sequence=2 if captured else 0)
    wire=context.model_dump(mode='json',by_alias=True)
    wire['assembled_input']['tokenizer_name']=first.input_estimator
    context=type(context).model_validate_json(json.dumps(seal(wire)))
    events=[]
    if captured:
        captured_record=draft.BuildDraftContextRecordV1(record_id=uuid4(),turn_id=turn_id,conversation_id=cap.conversation_id,
            attempt=1,submitted_intent_fingerprint=t.submitted_turn_intent_fingerprint_v2(intent),
            expected_pointer_revision=cap.expected_pointer_revision,snapshot=snapshot)
        event=t.BuildDraftContextCapturedV1(kind='build_draft_context_captured_v1',event_id=uuid4(),sequence=0,record=captured_record)
        events.extend([event,t.BuildDraftProviderInclusionV1(kind='build_draft_provider_inclusion_v1',event_id=uuid4(),sequence=1,
            provider_attempt_id=first.provider_attempt_id,envelope_sha256=first.envelope_sha256,
            draft_event_id=event.event_id,snapshot_sha256=snapshot.snapshot_sha256)])
    events.extend([first,*outcomes(first,len(events)+1)])
    selection=build_resolution(policy,first,len(events),turn_id=turn_id,
        requested='write_current_page' if operation=='propose_build_insertion' else 'prepare_image')
    events.append(selection)
    record=with_work_selection(execution(context.context_receipt_sha256,policy,events))
    origin=BuildProposalOrigin(client_turn_id=client_id,durable_turn_id=turn_id,turn_attempt=1,
        broker_operation_id=selection.broker_operation_id,arguments_sha256=selection.arguments_sha256)
    return request.model_copy(update={'origin':origin}),cap,(context,record,work)


def reviewed_case(request):
    from application_state.agent_conversation.reviewed_action import ReviewedStepBinding, ReviewedStepReference, admission_manifest, digest
    request,cap,native=native_case(request,'propose_build_insertion',captured=True)
    context,record,work=native
    binding=ReviewedStepBinding(reference=ReviewedStepReference(conversation_id=work['conversation_id'],
        source_turn_id=uuid4(),command_id=uuid4()),step_id=uuid4(),kind='prepare_insertion',
        source_answer_sha256='d'*64,dispatch_sha256='e'*64)
    intent=record.policy.action.intent.model_copy(update={'reviewed_step':binding})
    action=record.policy.action.model_copy(update={'intent':intent})
    broker='build-reviewed:'+digest(dict(turn_id=str(work['turn_id']),attempt=1,binding=binding.model_dump(mode='json')))
    selected=t.BuildReviewedActionSelectionV1(kind='build_reviewed_action_selected_v1',event_id=uuid4(),sequence=1,
        intent=intent,operation='propose_build_insertion',broker_operation_id=broker,
        capability_sha256=intent.build_write_capability_sha256,arguments_sha256=digest({'instruction':intent.message}))
    captured=record.events[0]
    captured=captured.model_copy(update={'record':captured.record.model_copy(update={
        'submitted_intent_fingerprint':t.submitted_turn_intent_fingerprint_v2(intent)})})
    events=[captured,selected,*[e for e in record.events[1:] if not isinstance(e,t.BuildRequestedWorkResolutionV1)]]
    # The existing controller acquires context after the author's operation choice.
    events=[e.model_copy(update={'sequence':i}) for i,e in enumerate(events)]
    wire=context.model_dump(mode='json',by_alias=True)
    wire['assembled_input']=dict(assembler_version='reviewed_author_admission_v1',
        submitted_intent_sha256=t.canonical_sha256(intent),assembled_input_sha256=digest(admission_manifest(intent)))
    context=type(context).model_validate_json(json.dumps(seal(wire)))
    record=execution(context.context_receipt_sha256,record.policy.model_copy(update={'action':action}),events)
    request=request.model_copy(update={'origin':request.origin.model_copy(update={'broker_operation_id':broker,
        'arguments_sha256':selected.arguments_sha256})})
    return request,cap,(context,record,work)


def test_reviewed_proposal_uses_actual_selected_action_without_fabricated_resolution(request_case):
    request,_source,_root=request_case
    request,_cap,native=reviewed_case(request)
    context,record,work=native
    body=owner.prepare_writer_request(request,writer_model=record.policy.provider_roles.writer.model,
        frozen_history=(),_native_context=native)
    frame=json.loads(body['input'])
    assert 'response_contract' not in frame['surface_work']
    assert frame['surface_work']['captured_editor']['idempotency_key']==str(request.idempotency_key)
    assert not any(isinstance(e,t.BuildRequestedWorkResolutionV1) for e in record.events)
    raw=json.dumps(body)
    stored,auth=authorize(context,record,raw,frame['native_evidence'])
    assert verify_input_records(context,stored,auth,raw,**work).work_frame==frame['surface_work']


@pytest.mark.parametrize('operation',['propose_build_insertion','prepare_build_image'])
@pytest.mark.parametrize('captured',[False,True])
def test_owned_request_uses_one_actual_work_body_and_dedicated_schema(request_case,operation,captured):
    request,_source,_root=request_case
    request,cap,native=native_case(request,operation,captured=captured)
    context,record,work=native
    model=record.policy.provider_roles.writer.model
    if operation=='propose_build_insertion':
        prepared=owner.prepare_writer_request(request,writer_model=model,frozen_history=(),_native_context=native)
        schema=owner.BuildComposeOutput.model_json_schema()
    else:
        prepared=image_owner.writer_request(cap,request.instruction,(),writer_model=model,_native_context=native)
        schema=image_owner.ImageDirectionV2.model_json_schema()
    raw=json.dumps(prepared)
    packet=json.loads(prepared['input'])
    assert packet['surface_work']==model_work_frame(context,record,**work)
    assert packet['native_evidence']==model_frame(context,record)
    assert prepared['text']['format']['schema']==schema and prepared['tools']==[]
    assert not {'source_basis','draft_markdown','captured_capability','related_authored_pages'} & packet.keys()
    assert prepared['input'].count(json.dumps(cap.draft_markdown)[1:-1])==1
    assert ('working_draft_context' in packet['surface_work'])==captured
    stored,auth=authorize(context,record,raw,packet['native_evidence'])
    assert verify_input_records(context,stored,auth,raw,**work).work_frame==packet['surface_work']


def test_unadmitted_native_turn_cannot_reserve_or_send(request_case):
    from application_state.errors import ApplicationStateConflictError
    from application_state.build_proposal.service import BuildProposalService
    request,_source,_root=request_case
    request,_cap,native=native_case(request,'propose_build_insertion')
    parent=Parent(request)
    parent.writer_model=native[1].policy.provider_roles.writer.model
    wire=Wire(request)
    # No synthetic legacy Turn can stand in for the missing native APP caller.
    with pytest.raises(ApplicationStateConflictError,match='current Agent turn claim'):
        asyncio.run(owner.compose_with_writer(request,parent.gate(),writer_model=parent.writer_model,
            transport=wire,frozen_history=(),_native_context=native))
    assert not wire.calls and not parent.prepared
    assert BuildProposalService().list('elderwyld',request.conversation_id)==[]


@pytest.mark.parametrize('operation',['propose_build_insertion','prepare_build_image'])
def test_actual_sdk_uses_exact_owned_request_and_shared_input_proof(request_case,operation):
    import httpx
    from generationengine import GenerationClient, TextRequest
    from generationengine.providers.openai_text import OpenAITextProvider
    from generationengine.text_dispatch import TextDispatchGate
    from generationengine import TextCompleted
    request,_source,_root=request_case
    request,cap,native=native_case(request,operation)
    context,record,work=native
    model=record.policy.provider_roles.writer.model
    if operation=='propose_build_insertion':
        expected=owner.prepare_writer_request(request,writer_model=model,frozen_history=(),_native_context=native)
        output=dict(target='captured',destination='current_page',replacement_markdown='A proposed copper lamp.',
            summary='Proposed detail.',assumptions=['The lamp is invented.'])
    else:
        expected=image_owner.writer_request(cap,request.instruction,(),writer_model=model,_native_context=native)
        output=dict(prompt='An imagined copper lamp.',alt='Proposed lamp illustration',purpose='illustration')
    text=json.dumps(output)
    calls=[]
    proved=[]
    async def gate(prepared):
        assert json.loads(prepared.body)==expected
        stored,auth=authorize(context,record,prepared.body.decode(),model_frame(context,record))
        proved.append(verify_input_records(context,stored,auth,prepared.body.decode(),**work))
        return True
    async def lifecycle(_event):
        return True
    def wire(physical):
        calls.append(physical)
        response=dict(id='resp_native_authoring',object='response',created_at=1,status='completed',model=model,
            output=[dict(type='message',id='msg',role='assistant',status='completed',
                content=[dict(type='output_text',text=text,annotations=[])])])
        if expected['stream']:
            events=[dict(type='response.output_text.delta',sequence_number=1,item_id='msg',output_index=0,
                content_index=0,delta=text),dict(type='response.completed',sequence_number=2,response=response)]
            return httpx.Response(200,request=physical,headers={'content-type':'text/event-stream'},
                content=''.join('data: '+json.dumps(e)+'\n\n' for e in events).encode())
        return httpx.Response(200,request=physical,json=response)
    async def run():
        provider=OpenAITextProvider(api_key='synthetic-only',dispatch_gate=TextDispatchGate(gate,lifecycle),
            transport=httpx.MockTransport(wire))
        client=GenerationClient(text_providers={'openai':provider})
        fmt=expected['text']['format']
        call=TextRequest(provider='openai',model=model,user_prompt=expected['input'],system_prompt=expected['instructions'],
            max_output_tokens=4096,temperature=None,reasoning_effort='low',json_schema=fmt['schema'],schema_name=fmt['name'],
            max_conformance_retries=0,max_transport_retries=0)
        try:
            if expected['stream']:
                completed=None
                async for event in client.stream_text(call):
                    if isinstance(event,TextCompleted):
                        completed=event
                assert completed is not None
                return completed.final_text
            result=await client.generate_structured(call)
            return result.text
        finally:
            await client.aclose()
    raw=asyncio.run(run())
    assert json.loads(raw)==output and len(calls)==len(proved)==1
    # This proves actual producer/SDK input, not native APP Turn acceptance.



@pytest.mark.parametrize('mutation',['work','native','instruction','schema','duplicate_body','tools','other_operation'])
def test_native_owned_input_rejects_reauthorized_body_substitution(request_case,mutation):
    request,_source,_root=request_case
    request,_cap,native=native_case(request,'propose_build_insertion')
    context,record,work=native
    body=owner.prepare_writer_request(request,writer_model=record.policy.provider_roles.writer.model,
        frozen_history=(),_native_context=native)
    packet=json.loads(body['input'])
    if mutation=='work':
        packet['surface_work']['working_draft_context']['draft_markdown']='Changed'
    elif mutation=='native':
        packet['native_evidence']['user_question']='Changed'
    elif mutation=='instruction':
        packet['instruction']='Changed'
    elif mutation in {'schema','other_operation'}:
        packet['schema']='wrong' if mutation=='schema' else 'dmb_build_image_direction_input_v1'
    elif mutation=='duplicate_body':
        packet['draft_markdown']=request.draft_markdown
    else:
        body['tools']=[{'type':'function','name':'unauthorized'}]
    body['input']=json.dumps(packet)
    raw=json.dumps(body)
    stored,auth=authorize(context,record,raw,model_frame(context,record))
    with pytest.raises(ValueError):
        verify_input_records(context,stored,auth,raw,**work)


@pytest.mark.parametrize('mutation',['operation','capability','model','origin','instruction','raw_frames','extra_material'])
def test_owned_staging_rejects_wrong_host_inputs_without_reserving(request_case,mutation):
    request,_source,_root=request_case
    request,_cap,native=native_case(request,'propose_build_insertion')
    model=native[1].policy.provider_roles.writer.model
    kwargs=dict(writer_model=model,frozen_history=(),_native_context=native)
    if mutation=='operation':
        request,_cap,native=native_case(request,'prepare_build_image')
        kwargs['_native_context']=native
    elif mutation=='capability':
        request=request.model_copy(update={'basis':request.basis.model_copy(update={'caret':2})})
    elif mutation=='model':
        kwargs['writer_model']='unapproved-model'
    elif mutation=='origin':
        request=request.model_copy(update={'origin':request.origin.model_copy(update={'durable_turn_id':uuid4()})})
    elif mutation=='instruction':
        request=request.model_copy(update={'instruction':'Different selected work'})
    elif mutation=='raw_frames':
        kwargs['_native_context']={'native_evidence':{},'surface_work':{}}
    else:
        kwargs['authored_reference_material']={'invented':'injected'}
    with pytest.raises(ValueError):
        owner.prepare_writer_request(request,**kwargs)
    from application_state.build_proposal.service import BuildProposalService
    assert BuildProposalService().list('elderwyld',request.conversation_id)==[]


@pytest.mark.parametrize('field',['draft_markdown','editor_sha256','draft_generation'])
def test_captured_editor_and_working_draft_cannot_describe_different_edits(request_case,field):
    request,_source,_root=request_case
    _request,cap,native=native_case(request,'propose_build_insertion')
    context,record,_work=native
    if field=='draft_markdown':
        text=cap.draft_markdown+'Changed editor body.'
        cap=cap.model_copy(update={'draft_markdown':text,'basis':cap.basis.model_copy(update={
            'draft_sha256':sha256(text.encode()).hexdigest()})})
    else:
        cap=cap.model_copy(update={'basis':cap.basis.model_copy(update={
            field:'c'*64 if field=='editor_sha256' else cap.basis.draft_generation+1})})
    action=record.policy.action
    intent=action.intent.model_copy(update={'build_write_capability_sha256':t.canonical_sha256(cap.model_dump(mode='json'))})
    action=action.model_copy(update={'intent':intent,'write_capability':cap})
    events=[e.model_copy(update={'record':e.record.model_copy(update={
        'submitted_intent_fingerprint':t.submitted_turn_intent_fingerprint_v2(intent)})})
        if isinstance(e,t.BuildDraftContextCapturedV1) else e.model_copy(update={
            'capability_sha256':intent.build_write_capability_sha256,
            'response_capabilities_sha256':e.response_capabilities_sha256})
        if isinstance(e,t.BuildRequestedWorkResolutionV1) else e for e in record.events]
    with pytest.raises(ValueError,match='editor|working draft'):
        execution(context.context_receipt_sha256,record.policy.model_copy(update={'action':action}),events)
