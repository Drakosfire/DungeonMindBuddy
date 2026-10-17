"""Actual controller/writer SDK bytes and exact persisted saved-source bindings."""
import json
from dataclasses import replace
from hashlib import sha256
from uuid import uuid4

import pytest

from application_state.agent_conversation import AgentConversationService
from application_state.agent_conversation import types as t
from application_state.errors import ApplicationStateError
from apps.live_control_server.services import agent_turn_service as owner
from apps.live_control_server.services import build_jev_writer as writer
from tests.test_agent_build_jev_controller_exposure import _start, _acquire, build_case as _build_case
from tests.test_agent_build_jev_dispatch import _invoke, Wire
from tests.test_agent_build_jev_single_writer import invoke, WriterWire


@pytest.fixture
def build_case(tmp_path,monkeypatch,application_state_dsn):
    return _build_case.__wrapped__(tmp_path,monkeypatch,application_state_dsn)


def fresh(adapter):
    return AgentConversationService().list_turns(adapter.turn.world_id,adapter.turn.conversation_id)[0]


def source_answer(reads,*,same_text=False):
    return json.dumps({'answer_context_status':'source_only_insufficient_evidence','answer_segments':[
        {'kind':'saved_source_claim','text':'An authored proposal.' if same_text else f'Authored excerpt {index+1}.',
         'section_read_ids':[read['read_id']]} for index,read in enumerate(reads)]})


def staged(build_case,monkeypatch,*,second_controller=False,two=False,mixed=False):
    adapter,_,_=_start(build_case,monkeypatch)
    reads=[json.loads(adapter.read_build_section(line_start=2,line_end=2))]
    if two:
        reads.append(json.loads(adapter.read_build_section(line_start=3,line_end=3)))
    if second_controller:
        state=adapter.stage_build_controller_exposure(section_read_ids=tuple(r['read_id'] for r in reads))
        assert state['exposure']['saved_sections']==sorted(reads,key=lambda r:r['event_id'])
        _invoke(adapter,state,Wire(adapter),[])
    graph,source=_acquire(adapter) if mixed else (None,None)
    projection=adapter.stage_build_writer(graph_payloads=(graph,) if graph else (),source_payloads=(source,) if source else (),
        section_read_ids=tuple(r['read_id'] for r in reads))
    return adapter,projection,reads


@pytest.mark.parametrize('two',[False,True])
def test_sdk_controller_sections_writer_and_fresh_answer_binding(build_case,monkeypatch,two):
    adapter,projection,reads=staged(build_case,monkeypatch,second_controller=True,two=two)
    raw=source_answer(reads,same_text=two)
    wire=WriterWire(adapter,text=raw)
    result=invoke(adapter,projection,wire)
    body=json.loads(wire.calls[0].content)
    assert json.loads(body['input'])['exposure']['saved_sections']==sorted(reads,key=lambda r:r['event_id'])
    assert body['instructions']==writer.SOURCE_INSTRUCTIONS and body['tools']==[]
    assert 'Do not emit saved_source_claim' not in body['instructions']
    completed=adapter.complete_build_writer(result)
    turn=fresh(adapter)
    assert turn.status=='completed' and turn.completion==completed.completion
    bindings=[event for event in turn.graph_context_execution.events if isinstance(event,t.BuildSectionAnswerBindingV1)]
    assert len(bindings)==1
    binding=bindings[0]
    assert binding.provider_attempt_id==adapter.producing_provider_attempt_id
    assert binding.completion_sha256==t._canonical_sha256(turn.completion.model_dump(mode='json',by_alias=True))
    assert [item.segment_index for item in binding.bindings]==list(range(len(reads)))
    assert [item.section_event_ids for item in binding.bindings]==[[__import__('uuid').UUID(r['event_id'])] for r in reads]
    for index,segment in enumerate(turn.completion.answer_segments):
        assert segment.model_dump(mode='json')=={'kind':'saved_source_claim','text':'An authored proposal.' if two else 'Authored excerpt 1.',
            'content_sha256':turn.graph_context_receipt.source_basis.content_sha256}
        assert binding.bindings[index].text_sha256==sha256(segment.text.encode()).hexdigest()
    inclusion=[event for event in turn.graph_context_execution.events if isinstance(event,t.BuildSectionProviderInclusionV1)
        and event.provider_attempt_id==adapter.producing_provider_attempt_id][0]
    assert set(inclusion.section_event_ids)=={__import__('uuid').UUID(r['event_id']) for r in reads}
    assert owner.project_plan_turn_context(turn,delivery_replay=True).completion==turn.completion


def test_mixed_graph_and_authored_source_remain_distinct(build_case,monkeypatch):
    adapter,projection,reads=staged(build_case,monkeypatch,mixed=True)
    answer=json.loads(source_answer(reads))
    answer['answer_context_status']='graph_grounded'
    answer['answer_segments'].append({'kind':'graph_claim','claim_id':'graph-one','text':'Frank believes the western gate is haunted.',
        'target_kind':'assertion','target_id':'observation-one'})
    result=invoke(adapter,projection,WriterWire(adapter,text=json.dumps(answer)))
    adapter.complete_build_writer(result)
    turn=fresh(adapter)
    citation,=turn.completion.citation_map.entries
    assert citation.target_id=='observation-one' and citation.source_opened
    binding=next(event for event in turn.graph_context_execution.events if isinstance(event,t.BuildSectionAnswerBindingV1))
    assert [item.segment_index for item in binding.bindings]==[0]
    assert turn.completion.answer_segments[0].kind=='saved_source_claim'
    assert turn.completion.answer_segments[1].kind=='graph_claim'


@pytest.mark.parametrize('fault',['foreign','duplicate','omitted','wrong_text','invalid_text','graph_promotion'])
def test_writer_cannot_claim_unincluded_or_forged_section_selectors(build_case,monkeypatch,fault):
    adapter,projection,reads=staged(build_case,monkeypatch)
    answer=json.loads(source_answer(reads))
    segment=answer['answer_segments'][0]
    if fault=='foreign':
        segment['section_read_ids']=[str(uuid4())]
    elif fault=='duplicate':
        segment['section_read_ids']*=2
    elif fault=='omitted':
        segment.pop('section_read_ids')
    elif fault=='wrong_text':
        segment['content_sha256']='f'*64
    elif fault=='invalid_text':
        segment['text']=33
    else:
        answer['answer_context_status']='graph_grounded'
        answer['answer_segments']=[{'kind':'graph_claim','claim_id':'fake','text':'Pretend Graph fact.',
            'target_kind':'assertion','target_id':reads[0]['read_id']}]
    result=invoke(adapter,projection,WriterWire(adapter,text=json.dumps(answer)))
    with pytest.raises((ValueError,owner.AgentTurnServiceError)):
        adapter.complete_build_writer(result)
    assert fresh(adapter).completion is None


def test_controller_included_section_is_not_implicitly_in_writer(build_case,monkeypatch):
    adapter,_,_=_start(build_case,monkeypatch)
    read=json.loads(adapter.read_build_section(line_start=2,line_end=2))
    state=adapter.stage_build_controller_exposure(section_read_ids=(read['read_id'],))
    _invoke(adapter,state,Wire(adapter),[])
    graph,source=_acquire(adapter)
    projection=adapter.stage_build_writer(graph_payloads=(graph,),source_payloads=(source,))
    result=invoke(adapter,projection,WriterWire(adapter,text=source_answer([read])))
    with pytest.raises(ValueError):
        adapter.complete_build_writer(result)
    assert fresh(adapter).completion is None


@pytest.mark.parametrize('fault',['text','source','event','omit'])
def test_exact_prepared_packet_mutation_cannot_send(build_case,monkeypatch,fault):
    adapter,projection,reads=staged(build_case,monkeypatch)
    packet=json.loads(projection.input_json)
    if fault=='omit':
        packet['exposure']['saved_sections']=[]
    else:
        item=packet['exposure']['saved_sections'][0]
        if fault=='text':
            item['text']='Forged section'
        elif fault=='source':
            item['source_basis']['document_id']='foreign'
        else:
            item['event_id']=str(uuid4())
    altered=replace(projection,input_json=json.dumps(packet))
    wire=WriterWire(adapter,text=source_answer(reads))
    from generationengine import GenerationEngineError
    with pytest.raises(GenerationEngineError):
        invoke(adapter,altered,wire)
    assert wire.calls==[]


def test_app_refuses_saved_claim_without_mandatory_binding(build_case,monkeypatch):
    adapter,projection,reads=staged(build_case,monkeypatch)
    invoke(adapter,projection,WriterWire(adapter,text=source_answer(reads)))
    turn=adapter.stop()
    completion=t.BuildGraphCompletionV1(context_receipt_sha256=turn.graph_context_receipt.context_receipt_sha256,
        answer_basis='saved_source',answer_context_status='source_only_insufficient_evidence',
        answer_segments=[t.SavedSourceClaimV1(kind='saved_source_claim',text='Authored excerpt 1.',
            content_sha256=turn.graph_context_receipt.source_basis.content_sha256)],citation_map=None)
    with pytest.raises(ApplicationStateError):
        AgentConversationService().complete_turn(t.TurnResult(world_id=turn.world_id,conversation_id=turn.conversation_id,
            turn_id=turn.turn_id,expected_revision=turn.revision,assistant_text='Authored excerpt 1.',completion=completion,
            producing_provider_attempt_id=adapter.producing_provider_attempt_id,claim_graph_event_ids={}))
    assert fresh(adapter).completion is None


@pytest.mark.parametrize('mutation',['missing','completion','duplicate','source','orphan'])
def test_fresh_reload_checks_exact_source_binding_not_sidecar(build_case,monkeypatch,mutation):
    adapter,projection,reads=staged(build_case,monkeypatch,two=True)
    result=invoke(adapter,projection,WriterWire(adapter,text=source_answer(reads)))
    turn=adapter.complete_build_writer(result)
    data=turn.model_dump(mode='json',by_alias=True)
    events=data['graph_context_execution']['events']
    source_binding=next(e for e in events if e['kind']=='build_section_answer_binding_v1')
    if mutation=='missing':
        events.remove(source_binding)
    elif mutation=='completion':
        data['completion']['answer_segments'].reverse()
        data['assistant_text']='\n'.join(s['text'] for s in data['completion']['answer_segments'])
        digest=t._canonical_sha256(data['completion'])
        next(e for e in events if e['kind']=='completion_binding')['completion_sha256']=digest
    elif mutation=='duplicate':
        events.insert(-1,{**source_binding,'event_id':str(uuid4())})
    elif mutation=='source':
        source_binding['bindings'][0]['section_event_ids']=[str(uuid4())]
    else:
        data['completion']=None
        data['assistant_text']=None
        data['status']='running'
        events.pop()
    for index,event in enumerate(events):
        event['sequence']=index
    with pytest.raises(ValueError):
        t.Turn.model_validate(data)


def test_completed_replay_compares_source_bindings(build_case,monkeypatch):
    adapter,projection,reads=staged(build_case,monkeypatch)
    result=invoke(adapter,projection,WriterWire(adapter,text=source_answer(reads)))
    supplied=[]
    original=adapter.service.complete_turn
    def record(value):
        supplied.append(value)
        return original(value)
    monkeypatch.setattr(adapter.service,'complete_turn',record)
    completed=adapter.complete_build_writer(result)
    replay=AgentConversationService().complete_turn(supplied[0])
    assert replay==completed
    changed=supplied[0].model_copy(update={'build_section_bindings':[]})
    with pytest.raises(ApplicationStateError):
        AgentConversationService().complete_turn(changed)


def test_app_inclusion_digest_and_pending_identity_are_checked(build_case,monkeypatch):
    adapter,_,_=_start(build_case,monkeypatch)
    read=json.loads(adapter.read_build_section(line_start=2,line_end=2))
    turn=adapter.fence.turn
    execution=turn.graph_context_execution
    receipt=t.ValidatedBuildSectionReadV1.model_validate(read)
    inclusion=t.BuildSectionProviderInclusionV1(kind='build_section_provider_inclusion_v1',event_id=uuid4(),
        sequence=len(execution.events),context_receipt_sha256=execution.context_receipt_sha256,
        execution_policy_sha256=execution.execution_policy_sha256,provider_attempt_id=uuid4(),envelope_sha256='a'*64,
        section_event_ids=[receipt.event_id],sections_sha256=t.build_sections_digest([receipt]))
    bad=inclusion.model_copy(update={'sections_sha256':'f'*64})
    service=AgentConversationService()
    with pytest.raises(ApplicationStateError):
        service.record_build_section_inclusion(turn.world_id,turn.conversation_id,turn.turn_id,
            expected_revision=turn.revision,expected_attempt=turn.attempt,inclusion=bad)
    pending,created=service.record_build_section_inclusion(turn.world_id,turn.conversation_id,turn.turn_id,
        expected_revision=turn.revision,expected_attempt=turn.attempt,inclusion=inclusion)
    assert created
    first=next(e for e in pending.graph_context_execution.events if owner._is_provider_authorization(e))
    wrong=first.model_copy(update={'event_id':uuid4(),'sequence':len(pending.graph_context_execution.events),
        'provider_attempt_id':uuid4()})
    with pytest.raises(ApplicationStateError):
        service.authorize_provider_attempt_v2(pending.world_id,pending.conversation_id,pending.turn_id,
            expected_revision=pending.revision,expected_attempt=pending.attempt,provider_attempt_event=wrong)
    assert fresh(adapter).completion is None


def test_old_frozen_policy_does_not_gain_selected_source_authority(build_case,monkeypatch):
    from apps.live_control_server.services import build_jev_dispatch
    old_budget = build_jev_dispatch.request_budget()
    old_budget.pop('savedSourceInputPolicy')
    old_budget['schema'] = 'dmb_build_jev_first_request_budget_v2'
    monkeypatch.setattr(build_jev_dispatch, 'request_budget', lambda: dict(old_budget))
    adapter,_,_=_start(build_case,monkeypatch)
    read=json.loads(adapter.read_build_section(line_start=2,line_end=2))
    with pytest.raises(ValueError,match='explicit selected-section'):
        adapter.stage_build_controller_exposure(section_read_ids=(read['read_id'],))
    assert not isinstance(fresh(adapter).graph_context_execution.policy,t.BuildSectionControllerWriterPolicyV1)
