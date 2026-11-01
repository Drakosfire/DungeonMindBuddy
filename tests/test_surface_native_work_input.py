"""One SDK envelope must prove both native evidence and actual surface work."""
import asyncio
from copy import deepcopy
from hashlib import sha256
import json
from uuid import uuid4

import pytest

from application_state.agent_conversation import types as t
from application_state.agent_conversation.native_writer import model_frame, model_work_frame, verify_input_records
from application_state.agent_conversation.native_completion import normalize_output
from apps.live_control_server.services.native_rules_capture import NativeProviderReply
from tests.test_surface_native_build_work import case as build_case
from tests.test_surface_native_plan_work import case as plan_case
from tests.test_surface_native_writer import authorize
from tests.test_surface_native_context import provenance_for
from tests.test_surface_native_execution import execution, choice, outcomes
from tests.test_surface_native_completion import sdk_reply, answer


def work_case(surface,*,draft=True,selected=True):
    if surface=='build':
        context,record,captured,reads,identity=build_case(with_draft=draft,selected=selected)
        work=dict(**{k:identity[k] for k in ('world_id','conversation_id','turn_id','attempt')},
            provenance=provenance_for(context.work_context).model_copy(update={
                'surface_instance_id':record.policy.action.intent.surface_instance_id}),
            idempotency_key=uuid4(),work_proof={})
    else:
        context,record,provenance,key,proof,conversation=plan_case(
            requested='write_current_page' if draft else 'discuss',placement='after:0',captured=draft)
        active=next(e for e in reversed(record.events) if isinstance(e,t.ProviderAttemptAuthorizedEventV1))
        finished=choice(context,record,active,len(record.events),'finish_retrieval')
        record=execution(context.context_receipt_sha256,record.policy,[*record.events,finished])
        work=dict(world_id=provenance.world_id,conversation_id=conversation,turn_id=uuid4(),attempt=1,
            provenance=provenance,idempotency_key=key,work_proof=proof)
    return context,record,work


def produce(context,record,work,*,mutate=None):
    native=model_frame(context,record)
    frame=model_work_frame(context,record,**work)
    physical=deepcopy(frame)
    if mutate:
        mutate(physical)
    candidate=answer([dict(kind='proposal',label='invented_idea',text='A possibility for review, not played fact.')])
    raw,text=asyncio.run(sdk_reply(native,candidate,physical))
    stored,auth=authorize(context,record,raw,native)
    request_id=f'generationengine:{auth.provider_attempt_id}'
    terminal=outcomes(auth,len(stored.events))
    terminal[-1]=terminal[-1].model_copy(update={'request_id':request_id,'response_sha256':sha256(text.encode()).hexdigest()})
    stored=execution(context.context_receipt_sha256,stored.policy,[*stored.events,*terminal])
    capture=NativeProviderReply('synthetic-work-sdk',request_id,auth.provider,auth.model,auth.api_mode,
        auth.envelope_sha256,'stop','answered',text,sha256(text.encode()).hexdigest(),len(text.encode()),())
    identity={k:work[k] for k in ('world_id','conversation_id','turn_id','attempt')}
    trace={**identity,'conversation_id':str(identity['conversation_id']),'turn_id':str(identity['turn_id']),
        'capture_status':'recording','observations':[{'kind':'context_snapshot','stage':'after','materials':[
            {'item_id':f'unvalidated-provider-answer:{auth.provider_attempt_id}:{context.context_receipt_sha256}',
                'role':'assistant','state':'model_context','text':text}]}]}
    return stored,auth,dict(prepared_request_json=raw,raw_output_json=text,capture=capture,trace=trace,**work),frame


@pytest.mark.parametrize('surface',['build','plan'])
@pytest.mark.parametrize('draft,selected',[(False,False),(True,False),(True,True)])
def test_same_sdk_input_and_output_preserve_actual_work_and_native_authority(surface,draft,selected):
    context,record,work=work_case(surface,draft=draft,selected=selected)
    stored,auth,proof,frame=produce(context,record,work)
    evidence=verify_input_records(context,stored,auth,proof['prepared_request_json'],**work)
    result=normalize_output(context,stored,auth,**proof)
    assert evidence.work_frame==frame
    assert not evidence.body_excerpts and not evidence.native_assertions and not evidence.native_statements
    assert result.answer_context_status=='creative_proposal'
    assert not result.native_body_citations and not result.native_assertion_citations
    assert len([e for e in stored.events if e.kind=='native_writer_authorized_v1'])==1
    if surface=='build':
        assert frame['artifact_under_edit']['role']=='authored_page_under_edit_not_world_or_played_truth'
        assert len(frame['artifact_under_edit']['sections'])==(1 if draft and selected else 0 if draft else 2)
        assert ('working_draft_context' in frame)==draft
    else:
        assert frame['session_evidence'] and frame['authored_sources']
        if draft:
            assert frame['focused_edit_target']['location']=='After Objective'
            assert frame['current_page_draft']['state']=='unsaved_working_draft'


@pytest.mark.parametrize('surface',['build','plan'])
@pytest.mark.parametrize('mutation',['missing','duplicate','work_text','work_role','extra_authority','conversation','turn','attempt',
    'provenance','key','host_body'])
def test_native_answer_cannot_bypass_or_substitute_its_surface_work(surface,mutation):
    context,record,work=work_case(surface)
    def mutate(frame):
        if mutation=='work_text':
            if surface=='build':
                frame['working_draft_context']['draft_markdown']='Changed'
            else:
                frame['committed_plan_blocks'][0]['text']='Changed'
        elif mutation=='work_role':
            if surface=='build':
                frame['artifact_under_edit']['role']='accepted_world_fact'
            else:
                frame['current_page_draft']['state']='played_fact'
        elif mutation=='extra_authority':
            frame['graph_authority']={'revision':'forged'}
    stored,auth,proof,frame=produce(context,record,work,mutate=mutate)
    if mutation in {'missing','duplicate'}:
        body=json.loads(proof['prepared_request_json'])
        body['input']=body['input'][:1] if mutation=='missing' else [*body['input'],body['input'][1]]
        proof['prepared_request_json']=json.dumps(body)
        # Re-authorize the altered actual envelope: this must fail on work, not only a byte hash.
        stored,auth=authorize(context,record,proof['prepared_request_json'],model_frame(context,record))
    elif mutation in {'conversation','turn','attempt'}:
        proof[{'conversation':'conversation_id','turn':'turn_id','attempt':'attempt'}[mutation]]=2 if mutation=='attempt' else uuid4()
    elif mutation=='provenance':
        proof['provenance']=work['provenance'].model_copy(update={'surface_instance_id':'foreign'})
    elif mutation=='key':
        # Plan selectors are submission-salted; Build has no selector salted by this key.
        if surface=='build':
            proof['idempotency_key']='not-a-uuid'
        else:
            proof['idempotency_key']=uuid4()
    elif mutation=='host_body':
        proof['work_proof']=dict(work['work_proof'],plan_markdown='Changed')
    if mutation in {'missing','duplicate','work_text','work_role','extra_authority'}:
        with pytest.raises(ValueError,match='surface work|evidence frame'):
            verify_input_records(context,stored,auth,proof['prepared_request_json'],**work)
    with pytest.raises(ValueError):
        normalize_output(context,stored,auth,**proof)


@pytest.mark.parametrize('surface',['build','plan'])
@pytest.mark.parametrize('missing_work',[False,True])
def test_mixed_rules_output_requires_the_same_actual_draft_and_session_work(surface,missing_work):
    from tests.test_surface_native_rules import producing_case, normalize
    context,record,work=work_case(surface)
    def mutate(inputs,fmt):
        if missing_work:
            inputs.pop()
    case=producing_case(None,surface,context_record=(context,record),work_override=work,mutation=mutate)
    if missing_work:
        with pytest.raises(ValueError,match='prepared input'):
            normalize(case)
    else:
        result=normalize(case)
        assert result.base_completion.answer_context_status=='creative_proposal'
        assert result.composition.rules_segments
        assert not result.graph_used
