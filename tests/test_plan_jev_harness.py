"""Actual turn-service seam, current APP, GE SDKs, Debug trace and replay."""
import json
import httpx2
import pytest
from application_state.agent_conversation import AgentConversationService
from apps.live_control_server.services.agent_turn_service import execute_agent_turn, AgentTurnServiceError
from apps.live_control_server.services.hermes_session_store import HermesSessionPointerStore
from apps.live_control_server.services.plan_jev_harness import PlanJevHarness
from tests.test_plan_jev_dispatch import plan_adapter  # noqa: F401
from tests.test_plan_jev_writer import WriterWire


class Finish(httpx2.AsyncBaseTransport):
    def __init__(self): self.calls=[]
    async def handle_async_request(self, request):
        self.calls.append(request); body=json.loads(request.content)
        answers={}
        for name,question in body['questions'].items():
            choice='finish_retrieval' if name=='operation' else 'exclude'
            answers[name]={'type':'choice','choice':choice,'confidence':1,
                'probabilities':{key:float(key==choice) for key in question['criteria']}}
        return httpx2.Response(200,request=request,json={'model':'jev-1.14.0','answers':answers,
            'usage':{'input_tokens':31,'output_tokens':7}})


def route_case(a,tmp_path,*,status='completed'):
    decisions=Finish()
    class Harness(PlanJevHarness):
        def execute(self,adapter,**kwargs):
            wire.adapter=adapter
            return super().execute(adapter,**kwargs)
    answer=json.dumps({'answer_context_status':'plan_only_insufficient_evidence','answer_segments':[
        {'kind':'plan_claim','text':'The authored Plan proposes a park visit.'}]})
    wire=WriterWire(None,answer,status=status)
    harness=Harness(decision_transport=decisions,writer_transport=wire,
        decision_api_key='synthetic-not-secret',writer_api_key='synthetic-not-secret')
    kwargs=dict(root=tmp_path,pointer_store=HermesSessionPointerStore(tmp_path/'pointers'),
        owner_resolver=lambda request:{'kind':'world','id':a.world_id,'name':'Synthetic park World'},
        work_resolver=lambda *_args:a.work,graph_resolver=lambda *_args:pytest.fail('unused campaign graph'),
        plan_graph_resolver=lambda *_args:a.bootstrap,runtime=harness,conversation_service=AgentConversationService())
    return harness,decisions,wire,kwargs


def test_turn_service_plan_harness_delivers_and_replays_without_another_call(plan_adapter,tmp_path):
    harness,decisions,wire,kwargs=route_case(plan_adapter,tmp_path)
    response=execute_agent_turn(plan_adapter.request,**kwargs)
    assert response.answer.status=='ok' and 'proposes a park visit' in response.answer.text
    assert response.plan_context.delivery_replay is False
    assert len(decisions.calls)==len(wire.calls)==1 and len(harness.calls)==2
    assert harness.calls[0]['usage']['input_tokens']==31 and harness.calls[1]['usage']['input_tokens']==600
    turn=kwargs['conversation_service'].list_turns(plan_adapter.world_id,wire.adapter.turn.conversation_id)[0]
    trace=kwargs['conversation_service'].list_context_trace_attempts(world_id=plan_adapter.world_id,turn_id=turn.turn_id)[0]
    assert len([row for row in trace.observations if row.kind=='prompt_reference'])==2
    replay=execute_agent_turn(plan_adapter.request,**kwargs)
    assert replay.answer.text==response.answer.text and replay.plan_context.delivery_replay
    assert len(decisions.calls)==len(wire.calls)==1


def test_output_limit_failure_is_durable_with_prompt_and_usage_and_no_retry(plan_adapter,tmp_path):
    harness,decisions,wire,kwargs=route_case(plan_adapter,tmp_path,status='incomplete')
    with pytest.raises(AgentTurnServiceError): execute_agent_turn(plan_adapter.request,**kwargs)
    assert len(decisions.calls)==len(wire.calls)==1 and harness.output_limit_exceeded
    turn=kwargs['conversation_service'].list_turns(plan_adapter.world_id,wire.adapter.turn.conversation_id)[0]
    assert turn.status=='interrupted' and turn.failure_code=='provider_output_limit_exceeded'
    trace=kwargs['conversation_service'].list_context_trace_attempts(world_id=plan_adapter.world_id,turn_id=turn.turn_id)[0]
    assert len([row for row in trace.observations if row.kind=='prompt_reference'])==2
    assert any(row.kind=='provider_call' and row.input_tokens==600 and row.output_tokens==100 for row in trace.observations)


def test_owner_loads_completed_canonical_dialogue_once_for_followup(plan_adapter,tmp_path,monkeypatch):
    from uuid import uuid4
    harness,decisions,wire,kwargs=route_case(plan_adapter,tmp_path)
    first=execute_agent_turn(plan_adapter.request,**kwargs)
    assert first.answer.status == 'ok'
    service=kwargs['conversation_service']
    original=service.list_turns
    reads=[]
    def counted(*args,**kwargs):
        reads.append((args,kwargs))
        return original(*args,**kwargs)
    monkeypatch.setattr(service,'list_turns',counted)
    second=plan_adapter.request.model_copy(update={'turn_id':str(uuid4()),
        'message':'Ground that location in the journal.'})
    response=execute_agent_turn(second,**kwargs)
    assert response.answer.status == 'ok'
    assert len(reads)==1
    expected=[{'role':'user','content':plan_adapter.request.message},
              {'role':'assistant','content':first.answer.text}]
    state=json.loads(decisions.calls[-1].content)['state']
    assert state['question']==second.message
    assert state['dialogue_reference']==expected
    writer=json.loads(wire.calls[-1].content)
    frame=json.loads(writer['input'][0]['content'])
    assert frame['dialogue_reference']==expected
    assert len(decisions.calls)==len(wire.calls)==2
    # Replay exits before re-reading history or paying for another decision.
    replay=execute_agent_turn(second,**kwargs)
    assert replay.plan_context.delivery_replay and len(reads)==1
    assert len(decisions.calls)==len(wire.calls)==2


@pytest.mark.parametrize('include_graph',[False,True])
def test_owner_followup_retains_full_actual_rules_completion(plan_adapter,tmp_path,include_graph):
    import asyncio
    from uuid import uuid4
    from application_state.agent_conversation.rules_authority_policy import rules_capability
    from application_state.agent_conversation.rules_authority_reads import MixedCompletedTurnV1
    from apps.live_control_server.services import agent_turn_service as owner
    from apps.live_control_server.services.plan_jev_driver import PlanJevDriver
    from apps.live_control_server.services.plan_jev_rules_runtime import PlanRulesRuntime
    from apps.live_control_server.services.plan_jev_writer import PlanJevWriter
    from tests.test_plan_jev_driver import Decisions,fixture_reads
    from tests.test_plan_jev_writer import graph_answer
    from tests.test_rules_lookup_broker import args
    from graph_memory.interaction.session import GraphReferent
    a=plan_adapter
    a.request=a.request.model_copy(update={'message':args().question})
    a.submitted_intent=owner._submitted_turn_intent(a.request,world_id=a.world_id)
    if include_graph:
        a.bootstrap.retrieval_session.referents=[GraphReferent(id='pond',label='Park pond')]
        fixture_reads(a)
    rules=PlanRulesRuntime(a,rules_capability(graph=True))
    driver=PlanJevDriver(a,rules=rules)
    proof=asyncio.run(driver.run(transport=Decisions(),api_key='synthetic-not-secret'))
    writer=PlanJevWriter(a,proof,rules)
    support=rules.frame().supports[0]
    answer={'schema':'dmb_rules_mixed_answer_v1',
        'base_output':graph_answer() if include_graph else None,
        'rules_segments':[{'kind':'rules_claim','text':support.excerpt_text,
                           'support_ids':[str(support.support_id)]}],
        'ordered_refs':([{'domain':'base','segment_index':None}] if include_graph else [])
            +[{'domain':'rules','segment_index':0}]}
    completed=asyncio.run(writer.run(transport=WriterWire(a,json.dumps(answer)),api_key='synthetic-not-secret'))
    assert isinstance(completed,MixedCompletedTurnV1)
    harness,decisions,wire,kwargs=route_case(a,tmp_path)
    followup=a.request.model_copy(update={'turn_id':str(uuid4()),'message':'How does that apply here?'})
    response=execute_agent_turn(followup,**kwargs)
    assert response.answer.status=='ok'
    expected=[{'role':'user','content':a.request.message},
              {'role':'assistant','content':completed.assistant_text}]
    assert json.loads(decisions.calls[0].content)['state']['dialogue_reference']==expected
    assert json.loads(json.loads(wire.calls[0].content)['input'][0]['content'])['dialogue_reference']==expected
    assert support.excerpt_text in expected[1]['content']


def test_ordinary_governed_plan_selects_jev_and_replay_skips_factory(plan_adapter,tmp_path,monkeypatch):
    from apps.live_control_server.services import plan_jev_harness,agent_turn_service
    harness,decisions,wire,kwargs=route_case(plan_adapter,tmp_path)
    kwargs.pop('runtime')
    constructions=[]
    def factory():
        constructions.append(True)
        return harness
    monkeypatch.setattr(plan_jev_harness,'default_plan_jev_runtime',factory)
    monkeypatch.setattr(agent_turn_service,'default_hermes_agent_runtime',lambda:pytest.fail('Unexpected Plan fallback'))
    result=execute_agent_turn(plan_adapter.request,**kwargs)
    assert result.answer.status=='ok' and len(constructions)==1
    assert len(decisions.calls)==len(wire.calls)==1
    replay=execute_agent_turn(plan_adapter.request,**kwargs)
    assert replay.plan_context.delivery_replay and len(constructions)==1
    assert len(decisions.calls)==len(wire.calls)==1


def test_ordinary_plan_factory_failure_does_not_fallback_or_dispatch(plan_adapter,tmp_path,monkeypatch):
    from apps.live_control_server.services import plan_jev_harness,agent_turn_service
    _,decisions,wire,kwargs=route_case(plan_adapter,tmp_path)
    kwargs.pop('runtime')
    def unavailable():
        raise RuntimeError('Synthetic unavailable runtime')
    monkeypatch.setattr(plan_jev_harness,'default_plan_jev_runtime',unavailable)
    monkeypatch.setattr(agent_turn_service,'default_hermes_agent_runtime',lambda:pytest.fail('Unexpected Plan fallback'))
    with pytest.raises(AgentTurnServiceError) as failed:
        execute_agent_turn(plan_adapter.request,**kwargs)
    assert failed.value.code=='runtime_unavailable'
    assert not decisions.calls and not wire.calls
