"""Native current-submission source proof over prepared request shapes; no SDK."""
import json
from hashlib import sha256
from uuid import uuid4

import pytest

from application_state.agent_conversation import types as t
from application_state.agent_conversation.play_graph_authority import play_graph_execution_policy_digest
from application_state.agent_conversation.play_graph_input import NativePlayInputV1,prove_play_source_input
from application_state.agent_conversation.rules_authority_types import canonical_bytes
from tests.test_play_graph_context import fixture,seal_receipt
from tests.test_play_graph_authority import native_provider,MOMENT


def prepared(*,mode='chat_completions',blocks=False,mutate=None,raw_transform=None):
    receipt,execution,frame=fixture();submission=uuid4();question='Discuss the crossing 🦉.'
    carrier=NativePlayInputV1(submission_id=submission,message=question,source_frame=frame)
    text=canonical_bytes(carrier).decode()
    content=[{'type':'text' if mode=='chat_completions' else 'input_text','text':text}] if blocks else text
    key='messages' if mode=='chat_completions' else 'input'
    body={'model':'synthetic','tools':[],key:[{'role':'user','content':content}]}
    if mutate:mutate(body,key)
    raw=json.dumps(body,ensure_ascii=False,separators=(',',':'))
    if raw_transform:raw=raw_transform(raw)
    digest=sha256(raw.encode()).hexdigest()
    wire=receipt.model_dump(mode='json',by_alias=True)
    wire['assembled_input']['assembled_input_sha256']=digest
    receipt=seal_receipt(wire)
    execution=execution.model_copy(update={'context_receipt_sha256':receipt.context_receipt_sha256,
        'execution_policy_sha256':play_graph_execution_policy_digest(receipt.context_receipt_sha256,execution.policy)})
    authorization=native_provider(1).model_copy(update={'envelope_sha256':digest,'api_mode':mode})
    args=dict(receipt=receipt,execution=execution,authorization=authorization,prepared_request_json=raw,
        submission_id=submission,original_message=question,event_id=uuid4(),owner_resolved_current_moment_text=MOMENT)
    return args,frame


@pytest.mark.parametrize('mode',['chat_completions','codex_responses'])
@pytest.mark.parametrize('blocks',[False,True])
def test_actual_current_user_carrier_proves_exact_sources_without_persisting_bodies(mode,blocks):
    args,frame=prepared(mode=mode,blocks=blocks)
    result=prove_play_source_input(**args)
    assert result.provider_attempt_id==args['authorization'].provider_attempt_id
    assert result.envelope_sha256==sha256(args['prepared_request_json'].encode()).hexdigest()
    assert result.source_frame_sha256==t.canonical_sha256(frame)
    assert result.source_ids==[entry.source_id for entry in frame.manifest.entries]
    assert all(source.text not in result.model_dump_json() for source in frame.sources)
    assert args['execution'].events==[]  # Pure proof does not mutate/admit/dispatch.


@pytest.mark.parametrize('role',['assistant','tool','system','developer'])
def test_quoted_source_body_outside_user_carrier_grants_no_authority(role):
    args,_=prepared(mutate=lambda body,key:body[key][0].update(role=role))
    with pytest.raises(ValueError,match='current-submission'):prove_play_source_input(**args)


@pytest.mark.parametrize('change',['message','source','manifest_only','submission','extra','schema'])
def test_resealed_envelope_cannot_change_original_carrier(change):
    def mutate(body,key):
        value=json.loads(body[key][0]['content'])
        if change=='message':value['message']='Different question'
        if change=='source':value['source_frame']['sources'][0]['text']='Unowned source body'
        if change=='manifest_only':value['source_frame']=value['source_frame']['manifest']
        if change=='submission':value['submission_id']=str(uuid4())
        if change=='extra':value['opaque_context']={}
        if change=='schema':value['schema']='legacy_play_input'
        body[key][0]['content']=json.dumps(value,ensure_ascii=False)
    args,_=prepared(mutate=mutate)
    with pytest.raises(ValueError):prove_play_source_input(**args)


def test_current_submission_must_be_unique_even_when_duplicate_body_is_exact():
    args,_=prepared(mutate=lambda body,key:body[key].append(dict(body[key][0])))
    with pytest.raises(ValueError,match='current-submission'):prove_play_source_input(**args)


def test_old_submission_history_is_not_current_source_authority():
    def mutate(body,key):
        old=json.loads(body[key][0]['content']);old['submission_id']=str(uuid4())
        body[key].insert(0,{'role':'user','content':json.dumps(old)})
    args,frame=prepared(mutate=mutate)
    assert prove_play_source_input(**args).source_frame_sha256==t.canonical_sha256(frame)


@pytest.mark.parametrize('change',['body_hash','model','mode','mixed_representation','owner','receipt','first_envelope','prose','nested','empty'])
def test_source_proof_rejects_foreign_owner_envelope_or_fake_carrier(change):
    args,_=prepared()
    body=json.loads(args['prepared_request_json'])
    if change=='body_hash':args['prepared_request_json']+=' '
    if change=='model':args['authorization']=args['authorization'].model_copy(update={'model':'other'})
    if change=='mode':args['authorization']=args['authorization'].model_copy(update={'api_mode':'legacy_responses'})
    if change=='owner':args['owner_resolved_current_moment_text']='Other scene'
    if change=='receipt':args['receipt']=fixture()[0]
    if change=='first_envelope':args['authorization']=args['authorization'].model_copy(update={'input_tokens':13})
    if change in {'mixed_representation','prose','nested','empty'}:
        if change=='mixed_representation':body['input']=body['messages']
        if change=='prose':body['messages'][0]['content']='Quoted evidence: '+body['messages'][0]['content']
        if change=='nested':body['messages'][0]['content']=json.dumps({'quoted':json.loads(body['messages'][0]['content'])})
        if change=='empty':body['messages']=[]
        raw=json.dumps(body,ensure_ascii=False);digest=sha256(raw.encode()).hexdigest()
        args['prepared_request_json']=raw;args['authorization']=args['authorization'].model_copy(update={'envelope_sha256':digest})
    with pytest.raises(ValueError):prove_play_source_input(**args)


@pytest.mark.parametrize('raw_transform',[
    lambda raw:raw.replace('"model":"synthetic"','"model":"other","model":"synthetic"'),
    lambda raw:raw[:-1]+',"temperature":NaN}',
    lambda raw:' ' * 1050001,
])
def test_request_parser_rejects_duplicate_nonfinite_or_oversized_json(raw_transform):
    args,_=prepared(raw_transform=raw_transform)
    with pytest.raises(ValueError):prove_play_source_input(**args)
