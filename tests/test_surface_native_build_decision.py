"""Actual synthetic controller SDK proof through the one Build semantic owner."""
import asyncio
from dataclasses import asdict
from hashlib import sha256
import json
from uuid import UUID, uuid4

import httpx2
import pytest

from generationengine import GenerationClient
from generationengine.types import DecisionRequest, ChoiceDecisionQuestion
from generationengine.providers.typesafe_decision import TypeSafeDecisionProvider
from generationengine.decision_dispatch import DecisionDispatchGate
from application_state.agent_conversation import types as t
from application_state.agent_conversation import build_intentional_response as semantic
from application_state.agent_conversation.native_writer import model_work_frame
from application_state.build_proposal.types import BuildWriteCapability
from tests.test_surface_native_execution import component, execution, controller, build_resolution, BUILD_TURN_ID
from tests.test_surface_native_context import seal, provenance_for
from tests.test_surface_native_work_input import work_case, produce
from tests.test_surface_native_writer import with_work_selection
from tests.test_surface_native_completion import answer


def sdk_case(requested='discuss',*,capable=False,auxiliary=False,probability=1.0):
    context,record=component('build',unavailable=True)
    conversation=uuid4()
    if capable:
        basis=context.work_context.source_basis
        cap=BuildWriteCapability(idempotency_key=uuid4(),conversation_id=conversation,expected_pointer_revision=1,
            basis=dict(**basis.model_dump(),draft_sha256=sha256(b'draft').hexdigest(),editor_sha256='b'*64,
                caret=0,draft_generation=0,selection_generation=0),draft_markdown='draft')
        action=record.policy.action
        action=action.model_copy(update={'intent':action.intent.model_copy(update={
            'build_write_capability_sha256':t.canonical_sha256(cap.model_dump(mode='json'))}),
            'write_capability':cap,'capabilities':semantic.Capabilities(
                ('answer_from_sources','propose_build_insertion','prepare_build_image'),
                ('questions','plan','connected_page','relationship'),True,None)})
        record=execution(context.context_receipt_sha256,record.policy.model_copy(update={'action':action}))
    action=record.policy.action
    state=dict(user_question=action.intent.message,requested_work_policy=semantic.POLICY,
        interaction=dict(allowed_operations=list(action.capabilities.operations),
            capability_sha256=action.intent.build_write_capability_sha256))
    request_id='select:'+semantic.digest(state)
    questions=[ChoiceDecisionQuestion(kind='choice',name='requested_work',question=semantic.decision_instructions(),
        options=tuple(semantic.WORK))]
    if auxiliary:
        questions.extend(ChoiceDecisionQuestion(kind='choice',name=name,question='Acquire this optional reference?',
            options=('read','skip')) for name in ('related_page_0','rules_query'))
    captured={}
    async def authorize(prepared):
        nonlocal context,record
        from application_state.agent_conversation.build_decision_context import identity
        auth=controller('build',record.policy).model_copy(update={'provider_attempt_id':UUID(prepared.attempt_id),
            'envelope_sha256':prepared.body_sha256,'dispatch_identity_sha256':identity(
                envelope_sha256=prepared.body_sha256,provider='typesafe',model=prepared.model,
                api_mode='typesafe_decision',context_mode='default')})
        wire=context.model_dump(mode='json',by_alias=True)
        wire['assembled_input'].update(assembled_input_sha256=prepared.body_sha256,
            provider_envelope_input_tokens=auth.input_tokens,output_token_reserve=auth.output_token_reserve,
            tokenizer_name=auth.input_estimator)
        context=type(context).model_validate_json(json.dumps(seal(wire)))
        record=execution(context.context_receipt_sha256,record.policy,[auth])
        captured.update(auth=auth,request_json=prepared.body.decode())
        return True
    async def lifecycle(event):
        nonlocal record
        status={'sending':'sdk_entered','response_received':'response_received'}[event.outcome]
        value=t.ProviderOutcomeEventV1(kind='provider_outcome',event_id=uuid4(),sequence=len(record.events),
            provider_attempt_id=UUID(event.request.attempt_id),outcome=status)
        record=execution(context.context_receipt_sha256,record.policy,[*record.events,value])
        return True
    class Wire(httpx2.AsyncBaseTransport):
        async def handle_async_request(self,request):
            body=json.loads(request.content)
            answers={}
            for name,q in body['questions'].items():
                label=requested if name=='requested_work' else 'skip'
                scores={option:(probability if option==label else (1-probability)/(len(q['criteria'])-1))
                    for option in q['criteria']}
                answers[name]=dict(type='choice',choice=label,probabilities=scores,confidence=probability)
            return httpx2.Response(200,request=request,json=dict(model='jev-1.14.0',answers=answers,
                usage=dict(input_tokens=25,output_tokens=7)))
    async def run():
        provider=TypeSafeDecisionProvider(api_key='synthetic-only',transport=Wire(),
            dispatch_gate=DecisionDispatchGate(authorize,lifecycle))
        client=GenerationClient(decision_providers={'typesafe':provider})
        try:
            return await client.decide(DecisionRequest(model='jev-1.14.0',provider='typesafe',
                state={'decision':dict(request_id=request_id,state=state)},questions=tuple(questions)))
        finally:
            await client.aclose()
    result=asyncio.run(run())
    proof=dict(request_json=captured['request_json'],response_json=result.model_dump_json())
    event=build_resolution(record.policy,captured['auth'],len(record.events),requested=requested).model_copy(update={
        'machine_request_id':request_id,'controller_response_sha256':sha256(proof['response_json'].encode()).hexdigest(),
        'broker_operation_id':semantic.operation_id_for(BUILD_TURN_ID,1,request_id,requested)})
    trace={'observations':[dict(kind='context_snapshot',materials=[dict(
        item_id=f'unvalidated-controller-decision:{event.controller_attempt_id}:selection',text=proof['response_json'])])]}
    work=dict(world_id=action.intent.world_id,conversation_id=conversation,turn_id=BUILD_TURN_ID,attempt=1,
        provenance=provenance_for(context.work_context).model_copy(update={'surface_instance_id':action.intent.surface_instance_id}),
        idempotency_key=uuid4(),work_proof={})
    return context,record,event,proof,trace,work


@pytest.mark.parametrize('requested,capable',[('discuss',False),('clarify_request',False),('plan',True),
    ('write_current_page',True),('prepare_image',True),('change_mechanics',True),('publish_relationships',True)])
@pytest.mark.parametrize('auxiliary',[False,True])
def test_native_uses_actual_build_controller_proof_and_frozen_capabilities(requested,capable,auxiliary):
    context,record,event,proof,trace,work=sdk_case(requested,capable=capable,auxiliary=auxiliary)
    semantic.validate_selection_records(record,event,proof,trace,user_text=record.policy.action.intent.message,
        turn_id=work['turn_id'],attempt=work['attempt'])
    record=with_work_selection(execution(context.context_receipt_sha256,record.policy,[*record.events,event]))
    frame=model_work_frame(context,record,**work)
    assert frame['response_contract']==event.resolution
    assert event.response_capabilities_sha256==semantic.digest(asdict(record.policy.action.capabilities))
    assert 'response_capabilities_sha256' not in record.policy.model_dump()
    if requested in {'change_mechanics','publish_relationships'}:
        assert event.resolution['barrier']=='requested_executor_not_offered'
        assert event.operation=='answer_from_sources'


@pytest.mark.parametrize('mutation',['turn','attempt','message','capture','request','response','answer_names','vote'])
def test_controller_proof_cannot_change_identity_capture_or_auxiliary_answers(mutation):
    _context,record,event,proof,trace,work=sdk_case(auxiliary=True)
    identity=dict(user_text=record.policy.action.intent.message,turn_id=work['turn_id'],attempt=1)
    if mutation=='turn':
        identity['turn_id']=uuid4()
    elif mutation=='attempt':
        identity['attempt']=2
    elif mutation=='message':
        identity['user_text']='Changed question'
    elif mutation=='capture':
        trace['observations']=[]
    elif mutation=='request':
        proof['request_json']+=' '
    else:
        raw=json.loads(proof['response_json'])
        if mutation=='answer_names':
            raw['answers'].pop('rules_query')
        elif mutation=='vote':
            raw['answers']['requested_work']['selected']='plan'
        proof['response_json']=json.dumps(raw)
        if mutation in {'answer_names','vote'}:
            event=event.model_copy(update={'controller_response_sha256':sha256(proof['response_json'].encode()).hexdigest()})
            trace['observations'][0]['materials'][0]['text']=proof['response_json']
    with pytest.raises(ValueError):
        semantic.validate_selection_records(record,event,proof,trace,**identity)


def test_image_selection_keeps_its_existing_confidence_threshold():
    _context,record,event,proof,trace,work=sdk_case('prepare_image',capable=True,probability=.85)
    with pytest.raises(ValueError,match='admission threshold'):
        semantic.validate_selection_records(record,event,proof,trace,user_text=record.policy.action.intent.message,
            turn_id=work['turn_id'],attempt=1)


@pytest.mark.parametrize('mutation',['missing','duplicate','unacknowledged','operation','resolution','capabilities','menu','turn'])
def test_shared_writer_rejects_missing_or_changed_semantic_authority(mutation):
    context,record,work=work_case('build')
    events=list(record.events)
    index=next(i for i,e in enumerate(events) if isinstance(e,t.BuildRequestedWorkResolutionV1))
    event=events[index]
    if mutation=='missing':
        events.pop(index)
    elif mutation=='duplicate':
        events.insert(index,event.model_copy(update={'event_id':uuid4()}))
    elif mutation=='unacknowledged':
        before=next(i for i,e in enumerate(events) if isinstance(e,t.ProviderOutcomeEventV1) and e.outcome=='response_received')
        events[before]=events[before].model_copy(update={'outcome':'known_not_sent'})
    elif mutation=='turn':
        work['turn_id']=uuid4()
    else:
        changes={'operation':{'operation':'propose_build_insertion'},'resolution':{'resolution':{}},
            'capabilities':{'response_capabilities_sha256':'b'*64},'menu':{'menu_sha256':'b'*64}}[mutation]
        events[index]=event.model_copy(update=changes)
    with pytest.raises(ValueError):
        altered=execution(context.context_receipt_sha256,record.policy,
            [e.model_copy(update={'sequence':i}) for i,e in enumerate(events)])
        produce(context,altered,work,candidate=answer([dict(kind='discussion',text='Discuss the request.')]))


def test_writer_cannot_override_the_retained_response_contract():
    context,record,work=work_case('build')
    def mutate(frame):
        frame['response_contract']['requested_work']='prepare_image'
    stored,auth,proof,_=produce(context,record,work,mutate=mutate)
    from application_state.agent_conversation.native_completion import normalize_output
    with pytest.raises(ValueError,match='surface work'):
        normalize_output(context,stored,auth,**proof)
