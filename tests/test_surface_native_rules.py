"""Shared SDK/Rules component proof, not actual locked APP caller activation."""
import asyncio
from copy import deepcopy
from dataclasses import replace
from hashlib import sha256
import json
from uuid import uuid4

import httpx
from openai import AsyncOpenAI
import pytest

from application_state.agent_conversation import types as t
from application_state.agent_conversation import rules_authority_events as r
from application_state.agent_conversation.rules_authority_policy import rules_capability, rules_submission_authorization_id
from application_state.agent_conversation.rules_authority_plan_packet import build_plan_rules_frame, verify_native_rules_packet_input
from application_state.agent_conversation.plan_writer_output_schema import native_output_format
from application_state.agent_conversation.native_rules_output import NativeRulesOutputProofV1, normalize_shared_native_output
from application_state.agent_conversation.native_writer import model_frame, model_work_frame
from apps.live_control_server.services.native_rules_capture import NativeProviderReply
from tests.test_surface_native_writer import body_case, authorize, published_case, published_lane as published_lane, work_submission
from tests.test_surface_native_completion import answer
from tests.test_surface_native_execution import execution, outcomes
from tests.test_native_corpus_source_access import lane as lane
from tests.test_rules_lookup_broker import execution as initial_rules, lookup, args
from tests.test_rules_build_input import append


async def sdk(frame, rules, candidate, *, work_frame, mutate_request=None):
    sent=[]
    raw=json.dumps(candidate)
    def wire(request):
        sent.append(request.content.decode())
        return httpx.Response(200,request=request,json={'id':'resp_shared_rules','object':'response',
            'created_at':1,'model':'gpt-6-luna','status':'completed','output':[
                {'type':'message','id':'msg_shared_rules','role':'assistant','status':'completed',
                 'content':[{'type':'output_text','text':raw,'annotations':[]}]}]})
    inputs=[dict(role='user',content=json.dumps(frame)),
        dict(role='user',content=rules.model_dump_json(by_alias=True)),
        dict(role='user',content=json.dumps(work_frame))]
    fmt=native_output_format(frame,rules,work_frame)
    if mutate_request:
        mutate_request(inputs,fmt)
    async with AsyncOpenAI(api_key='synthetic-not-secret',http_client=httpx.AsyncClient(
            transport=httpx.MockTransport(wire))) as client:
        response=await client.responses.create(model='gpt-6-luna',input=inputs,tools=[],stream=False,
            text={'format':fmt},max_output_tokens=4096)
    assert response.output_text==raw and len(sent)==1
    return sent[0],response.output_text


def producing_case(lane,surface,*,unused=False,base=True,mutation=None,context_record=None,candidate_mutation=None,work_override=None):
    context,record = context_record if context_record is not None else body_case(surface,lane)[:2]
    frame=model_frame(context,record)
    intent=record.policy.action.intent
    work=work_submission(context,record) if work_override is None else work_override
    identity={k:work[k] for k in ('world_id','conversation_id','turn_id','attempt')}
    submission=dict(**work,submitted_intent_fingerprint=t.submitted_turn_intent_fingerprint_v2(intent))
    cap=rules_capability(graph=True)
    owner=initial_rules()
    scope=owner.scope.model_copy(update=dict(world_id=identity['world_id'],conversation_id=identity['conversation_id'],
        turn_id=identity['turn_id'],product_attempt=identity['attempt'],capability_policy_sha256=cap.policy_sha256,
        corpus_sha256=cap.corpus_sha256,ruleset_id=cap.ruleset_id,authorization_id=rules_submission_authorization_id(
            world_id=intent.world_id,conversation_id=identity['conversation_id'],idempotency_key=submission['idempotency_key'],
            submitted_intent_sha256=submission['submitted_intent_fingerprint'],capability=cap)))
    owner=owner.model_copy(update={'scope':scope})
    refs,outputs=(),()
    if not unused:
        owner,result=lookup(owner)
        refs=result.observation.support_refs
        outputs=(r.RulesOutputRefV1(call_id=result.observation.call_id,packet_sha256=result.observation.packet_sha256),)
    rules=build_plan_rules_frame(owner,tuple(e.call_id for e in owner.events if isinstance(e,r.RulesQueryObservedV1)))
    if frame['native_body_evidence']['excerpts']:
        handle=frame['native_body_evidence']['excerpts'][0]['excerpt_handle']
        candidate=answer([dict(kind='native_body_claim',text='The check revealed another plane.',excerpt_handles=[handle])])
    elif frame['native_assertions'] and frame['native_assertions']['assertions']:
        candidate=answer([dict(kind='native_assertion_claim',text='The Graph preserves a qualified belief.',
            assertion_handles=[row['assertion_handle'] for row in frame['native_assertions']['assertions']])])
    else:
        candidate=answer([dict(kind='proposal',label='invented_idea',text='An unplayed possibility.')])
    if not unused:
        candidate=dict(schema='dmb_rules_mixed_answer_v1',base_output=candidate if base else None,
            rules_segments=[dict(kind='rules_claim',text='An occupied space prevents ending movement.',
                support_ids=[str(refs[0].support_id)])],ordered_refs=(
                    [dict(domain='base',segment_index=None)] if base else [])+[dict(domain='rules',segment_index=0)])
    if candidate_mutation:
        candidate_mutation(candidate)
    raw_request,raw_output=asyncio.run(sdk(frame,rules,candidate,work_frame=model_work_frame(context,record,**work),mutate_request=mutation))
    stored,auth=authorize(context,record,raw_request,frame)
    api_request_id=f'generationengine:{auth.provider_attempt_id}'
    terminal=outcomes(auth,len(stored.events))
    terminal[-1]=terminal[-1].model_copy(update={'request_id':api_request_id,'response_sha256':sha256(raw_output.encode()).hexdigest()})
    stored=execution(context.context_receipt_sha256,stored.policy,[*stored.events,*terminal])
    owner=append(owner,r.RulesProviderAuthorizedV1(kind='provider_authorized',event_id=uuid4(),sequence=len(owner.events),
        execution_id=scope.execution_id,provider_attempt_id=auth.provider_attempt_id,
        request_envelope_sha256=auth.envelope_sha256,matched_outputs=outputs,declared_support_refs=refs))
    owner=append(owner,r.RulesProviderIncludedV1(kind='provider_included',event_id=uuid4(),sequence=len(owner.events),
        execution_id=scope.execution_id,provider_attempt_id=auth.provider_attempt_id,
        request_envelope_sha256=auth.envelope_sha256,matched_outputs=outputs,support_refs=refs))
    capture=NativeProviderReply('synthetic-sdk-authorization',api_request_id,auth.provider,auth.model,auth.api_mode,
        auth.envelope_sha256,'stop','answered',raw_output,sha256(raw_output.encode()).hexdigest(),len(raw_output.encode()),())
    owner=append(owner,r.RulesNativeProviderOutcomeV1.from_capture(capture,event_id=uuid4(),sequence=len(owner.events),
        execution_id=scope.execution_id,provider_attempt_id=auth.provider_attempt_id,request_envelope_sha256=auth.envelope_sha256))
    proof=NativeRulesOutputProofV1.from_capture(capture,prepared_request_json=raw_request,
        rules_execution_id=scope.execution_id,producing_provider_attempt_id=auth.provider_attempt_id)
    trace={**identity,'conversation_id':str(identity['conversation_id']),'turn_id':str(identity['turn_id']),
        'capture_status':'recording','observations':[{'kind':'context_snapshot','stage':'after','materials':[
            {'item_id':f'unvalidated-provider-answer:{auth.provider_attempt_id}:{context.context_receipt_sha256}',
             'role':'assistant','state':'model_context','text':raw_output}]}]}
    return context,stored,owner,auth,proof,capture,dict(trace=trace,**submission)


def normalize(case):
    context,stored,owner,_auth,proof,capture,kwargs=case
    return normalize_shared_native_output(context,stored,owner,proof,capture,**kwargs)


@pytest.mark.parametrize('surface',['build','plan'])
@pytest.mark.parametrize('unused,base',[(False,True),(False,False),(True,True)])
def test_actual_sdk_rules_and_native_body_keep_separate_sources_and_one_reply(lane,surface,unused,base):
    case=producing_case(lane,surface,unused=unused,base=base)
    result=normalize(case)
    assert result.composition.render(tuple(s.text for s in result.base_completion.answer_segments)
        if result.base_completion else ())==result.assistant_text
    assert not result.graph_used and not result.claim_graph_event_ids
    assert bool(result.base_completion)==base
    assert bool(result.composition.rules_segments)==(not unused)
    if base:
        assert result.base_completion.surface_id==surface and result.base_completion.native_body_citations
    assert result.composition.base_disposition==('approved' if base else 'unclaimed')
    assert r.RulesExecutionV1.model_validate_json(case[2].model_dump_json(by_alias=True))==case[2]
    # The protected capture always holds the one actual outer response.
    assert case[4].raw_output_json==case[5].text==case[6]['trace']['observations'][0]['materials'][0]['text']


@pytest.mark.parametrize('surface',['build','plan'])
@pytest.mark.parametrize('mutation',['world','conversation','turn','attempt','fingerprint','idempotency',
    'scope_auth','scope_corpus','scope_policy','capture_text','capture_hash','ack_request','ack_hash',
    'trace_text','trace_attempt','seal_hash','unsealed','late_lookup','unsettled_lookup','unsettled_provider'])
def test_shared_rules_rejects_scope_capture_or_phase_substitution(lane,surface,mutation):
    case=list(producing_case(lane,surface))
    context,stored,owner,auth,proof,capture,kwargs=case
    kwargs=deepcopy(kwargs)
    if mutation in {'world','conversation','turn','attempt','fingerprint','idempotency'}:
        key={'world':'world_id','conversation':'conversation_id','turn':'turn_id','attempt':'attempt',
            'fingerprint':'submitted_intent_fingerprint','idempotency':'idempotency_key'}[mutation]
        kwargs[key] = 'foreign' if mutation=='world' else 'a'*64 if mutation=='fingerprint' else 2 if mutation=='attempt' else uuid4()
    elif mutation.startswith('scope_'):
        field={'scope_auth':'authorization_id','scope_corpus':'corpus_sha256','scope_policy':'capability_policy_sha256'}[mutation]
        owner=owner.model_copy(update={'scope':owner.scope.model_copy(update={field:uuid4() if mutation=='scope_auth' else 'a'*64})})
    elif mutation=='capture_text':
        capture=replace(capture,text=capture.text+' ')
    elif mutation=='capture_hash':
        capture=replace(capture,text_sha256='a'*64)
    elif mutation in {'ack_request','ack_hash'}:
        events=list(stored.events)
        events[-1]=events[-1].model_copy(update={'request_id':'foreign'} if mutation=='ack_request' else {'response_sha256':'a'*64})
        stored=execution(context.context_receipt_sha256,stored.policy,events)
    elif mutation=='trace_text':
        kwargs['trace']['observations'][0]['materials'][0]['text']='Different response'
    elif mutation=='trace_attempt':
        kwargs['trace']['attempt']=True
    elif mutation=='seal_hash':
        events=list(owner.events)
        events[-1]=events[-1].model_copy(update={'output_sha256':'a'*64})
        owner=owner.model_copy(update={'events':tuple(events)})
    elif mutation=='unsealed':
        owner=owner.model_copy(update={'events':owner.events[:-1]})
    elif mutation=='late_lookup':
        owner,_=lookup(owner,'call:late',args('What is an occupied space?'))
    elif mutation=='unsettled_lookup':
        # A generic ledger can store an admitted unfinished lookup. The shared
        # final writer must refuse it even when no pending text was included.
        from apps.live_control_server.services.rules_lookup_broker import prepare_authorization
        pending=prepare_authorization(owner,'call:pending',args('What is an occupied space?'))
        events=list(owner.events)
        events.insert(2,pending)
        events=[e.model_copy(update={'sequence':i}) for i,e in enumerate(events)]
        owner=owner.model_copy(update={'events':tuple(events),'budget_use':owner.budget_use.model_copy(
            update={'calls':2,'distinct_questions':2})})
    else:
        events=list(owner.events)
        previous=r.RulesProviderAuthorizedV1(kind='provider_authorized',event_id=uuid4(),sequence=2,
            execution_id=owner.scope.execution_id,provider_attempt_id=uuid4(),request_envelope_sha256='c'*64,
            matched_outputs=(),declared_support_refs=())
        events.insert(2,previous)
        events=[e.model_copy(update={'sequence':i}) for i,e in enumerate(events)]
        owner=owner.model_copy(update={'events':tuple(events),'budget_use':owner.budget_use.model_copy(
            update={'provider_requests':2})})
    case=[context,stored,owner,auth,proof,capture,kwargs]
    with pytest.raises(ValueError):
        normalize(case)


@pytest.mark.parametrize('surface',['build','plan'])
@pytest.mark.parametrize('mutation',['rules_text','rules_supports','format','tool_transcript'])
def test_actual_sdk_request_must_expose_exact_rules_text_and_current_finite_format(lane,surface,mutation):
    def mutate(inputs,fmt):
        if mutation=='format':
            fmt['name']='foreign_format'
        elif mutation=='tool_transcript':
            inputs.append({'type':'function_call_output','call_id':'fabricated','output':'forged'})
        else:
            frame=json.loads(inputs[1]['content'])
            if mutation=='rules_text':
                frame['supports'][0]['excerpt_text']='Forged Rules'
            else:
                frame['supports']=[]
            inputs[1]['content']=json.dumps(frame)
    case=producing_case(lane,surface,mutation=mutate)
    with pytest.raises(ValueError):
        normalize(case)


@pytest.mark.parametrize('surface',['build','plan'])
def test_input_phase_does_not_require_future_reply_but_output_does(lane,surface):
    context,stored,owner,auth,proof,_capture,kwargs=producing_case(lane,surface)
    pending=owner.model_copy(update={'events':owner.events[:-1]})
    submission={k:v for k,v in kwargs.items() if k!='trace'}
    evidence,frame=verify_native_rules_packet_input(pending,context,stored,proof.prepared_request_json,
        provider_attempt_id=auth.provider_attempt_id,expected_envelope_sha256=auth.envelope_sha256,**submission)
    assert frame.supports and evidence.body_excerpts
    with pytest.raises(ValueError,match='sealed final answer'):
        r.validate_native_packet_writer(pending,auth.provider_attempt_id,require_reply=True)


@pytest.mark.parametrize('surface',['build','plan'])
def test_mixed_rules_preserves_native_assertion_citations_and_qualifications(published_lane,surface):
    case=producing_case(None,surface,context_record=published_case(surface,published_lane))
    result=normalize(case)
    assert result.graph_used and result.base_completion.native_assertion_citations
    assert result.composition.rules_segments[0].support_refs
    assert result.base_completion.answer_segments[0].qualifications


@pytest.mark.parametrize('surface',['build','plan'])
@pytest.mark.parametrize('mutation',['rules_support','body_handle','old_base_policy','unknown_field'])
def test_sealed_output_still_needs_each_domain_acceptance(lane,surface,mutation):
    def mutate(candidate):
        if mutation=='rules_support':
            candidate['rules_segments'][0]['support_ids']=[str(uuid4())]
        elif mutation=='body_handle':
            candidate['base_output']['answer_segments'][0]['excerpt_handles']=['foreign']
        elif mutation=='old_base_policy':
            candidate['base_output']['schema']='dmb_plan_old_policy'
        else:
            candidate['base_output']['unrecognized_field']='not in contract'
    case=producing_case(lane,surface,candidate_mutation=mutate)
    with pytest.raises(ValueError):
        normalize(case)
