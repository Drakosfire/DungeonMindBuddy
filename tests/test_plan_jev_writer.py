"""Actual Jev → reads → one SDK writer → atomic APP completion, no network."""
import asyncio
import json
import httpx
import pytest
from generationengine import GenerationEngineError
from application_state.agent_conversation import AgentConversationService
from application_state.agent_conversation.rules_authority_policy import rules_capability
from application_state.agent_conversation.rules_authority_reads import MixedCompletedTurnV1
from apps.live_control_server.services.plan_jev_driver import PlanJevDriver
from apps.live_control_server.services.plan_jev_rules_runtime import PlanRulesRuntime
from apps.live_control_server.services.plan_jev_writer import PlanJevWriter
from apps.live_control_server.services import agent_turn_service as owner
from graph_memory.interaction.session import GraphReferent
from tests.test_plan_jev_dispatch import plan_adapter  # noqa: F401
from tests.test_plan_jev_driver import Decisions, fixture_reads
from tests.test_rules_lookup_broker import args


class WriterWire(httpx.AsyncBaseTransport):
    def __init__(self, adapter, text, *, status='completed', extra_output=()):
        self.adapter, self.text, self.status, self.extra_output = adapter, text, status, extra_output
        self.calls=[]; self.closed=False
    async def handle_async_request(self, request):
        self.calls.append(request)
        fresh=AgentConversationService().list_turns(self.adapter.world_id,self.adapter.turn.conversation_id)[-1]
        assert fresh.graph_context_execution.events[-1].outcome == 'sdk_entered'
        body=json.loads(request.content)
        assert isinstance(body['input'],list) and body['tools'] == []
        assert 'json' in ' '.join(row.get('content','') for row in body['input']).lower()
        assert 'coding agent' not in body['instructions'] and 'cwd' not in body['instructions']
        return httpx.Response(200,request=request,json={'id':'resp_plan_writer','object':'response','created_at':1,
            'status':self.status,'model':'gpt-6-luna','service_tier':'fast','output':[{'type':'message','id':'msg_plan_writer',
                'role':'assistant','status':'completed','content':[{'type':'output_text','text':self.text,'annotations':[]} ]},
                *self.extra_output], 'usage':{'input_tokens':600,'output_tokens':100,'total_tokens':700,
                    'input_tokens_details':{'cached_tokens':400},'output_tokens_details':{'reasoning_tokens':60}},
            **({'incomplete_details':{'reason':'max_output_tokens'}} if self.status=='incomplete' else {})})
    async def aclose(self): self.closed=True


def graph_answer():
    return {'answer_context_status':'graph_grounded','answer_segments':[{'kind':'graph_claim','claim_id':'claim:1',
        'text':'The park journal reports a wooden walkway.','target_kind':'assertion','target_id':'assertion:pond'}]}


def stage_graph(adapter):
    adapter.bootstrap.retrieval_session.referents=[GraphReferent(id='pond',label='Park pond')]
    fixture_reads(adapter)
    rules=PlanRulesRuntime(adapter,rules_capability(graph=True))
    driver=PlanJevDriver(adapter)  # no Rules selected; final writer still binds an empty Rules frame
    proof=asyncio.run(driver.run(transport=Decisions(),api_key='synthetic-not-secret'))
    return PlanJevWriter(adapter,proof,rules)


def test_actual_plan_writer_accepts_source_citation_and_exact_prompt(plan_adapter):
    writer=stage_graph(plan_adapter)
    wire=WriterWire(plan_adapter,json.dumps(graph_answer()))
    completed=asyncio.run(writer.run(transport=wire,api_key='synthetic-not-secret'))
    assert completed.status == 'completed' and len(wire.calls)==1 and wire.closed
    entry=completed.completion.citation_map.entries[0]
    assert entry.source_opened and entry.source_read_ids == ['read:anchor:park:0']
    assert entry.evidence_ref_ids == ['evidence:park:0']
    assert writer.call['usage'] == {'status':'reported','input_tokens':600,'output_tokens':100,
        'total_tokens':700,'cached_input_tokens':400,'uncached_input_tokens':200,'reasoning_tokens':60}
    assert writer.call['request_summary'] == {'reasoning_effort':'none'}
    prompts=[row for row in plan_adapter.context_capture.trace.observations if row.kind=='prompt_reference']
    assert prompts[-1].payload_sha256==writer.prepared.body_sha256
    assert prompts[-1].api_mode=='responses'
    assert not writer.authorize(writer.prepared)
    # Check actual SDK bytes: evidence appears once, machine proof remains host-side.
    body = json.loads(wire.calls[0].content)
    assert body['service_tier'] == 'fast'
    assert writer.call['response_service_tier'] == 'fast'
    assert body['reasoning'] == {'effort':'none'}
    frame = json.loads(body['input'][0]['content'])
    assert all('assertion_ids' not in row and 'relationship_ids' not in row
               for row in frame['retrieval_results'])
    passage = frame['opened_passages'][0]
    assert body['input'][0]['content'].count(passage['text']) == 1
    for field in ('source_artifact_id', 'source_revision_id', 'context_receipt_sha256',
                  'execution_policy_sha256', 'content_sha256'):
        assert field not in frame
        assert field not in passage
    assert entry.target_id == 'assertion:pond'
    assert entry.source_read_ids == ['read:anchor:park:0']


def test_actual_plan_writer_accepts_rules_and_no_graph(plan_adapter):
    a=plan_adapter
    a.request=a.request.model_copy(update={'message':args().question})
    a.submitted_intent=owner._submitted_turn_intent(a.request,world_id=a.world_id)
    rules=PlanRulesRuntime(a,rules_capability(graph=True))
    driver=PlanJevDriver(a,rules=rules)
    proof=asyncio.run(driver.run(transport=Decisions(),api_key='synthetic-not-secret'))
    writer=PlanJevWriter(a,proof,rules)
    capsule=rules.frame().supports[0]
    answer={'schema':'dmb_rules_mixed_answer_v1','base_output':None,
        'rules_segments':[{'kind':'rules_claim','text':capsule.excerpt_text,'support_ids':[str(capsule.support_id)]}],
        'ordered_refs':[{'domain':'rules','segment_index':0}]}
    wire=WriterWire(a,json.dumps(answer))
    completed=asyncio.run(writer.run(transport=wire,api_key='synthetic-not-secret'))
    assert isinstance(completed,MixedCompletedTurnV1) and completed.envelope.status=='completed'
    assert len(wire.calls)==1 and wire.closed
    assert rules.native.record.execution.events[-1].api_mode=='responses'


def test_incomplete_plan_reply_is_not_sealed_accepted_or_retried(plan_adapter):
    writer=stage_graph(plan_adapter)
    wire=WriterWire(plan_adapter,json.dumps(graph_answer()),status='incomplete')
    with pytest.raises(GenerationEngineError): asyncio.run(writer.run(transport=wire,api_key='synthetic-not-secret'))
    turn=plan_adapter.service.list_turns(plan_adapter.world_id,plan_adapter.turn.conversation_id)[0]
    assert len(wire.calls)==1 and wire.closed and turn.status!='completed'
    assert not any(row.kind=='native_provider_outcome' for row in writer.rules.native.record.execution.events)
    assert writer.call['usage']['input_tokens']==600 and writer.call['usage']['output_tokens']==100
    assert writer.output_limit_exceeded
    assert any(row.kind=='context_snapshot' and any(item.text==json.dumps(graph_answer()) for item in row.materials)
        for row in plan_adapter.context_capture.trace.observations)


def test_unexpected_sdk_tool_output_cannot_be_sealed_as_empty_tool_list(plan_adapter):
    writer=stage_graph(plan_adapter)
    wire=WriterWire(plan_adapter,json.dumps(graph_answer()),extra_output=({'type':'function_call',
        'id':'fc1','call_id':'call1','name':'unsupported','arguments':'{}','status':'completed'},))
    with pytest.raises(ValueError,match='unexpected tool'): asyncio.run(writer.run(transport=wire,api_key='synthetic-not-secret'))
    turn=plan_adapter.service.list_turns(plan_adapter.world_id,plan_adapter.turn.conversation_id)[0]
    assert len(wire.calls)==1 and wire.closed and turn.status!='completed'
    assert not any(row.kind=='native_provider_outcome' for row in writer.rules.native.record.execution.events)


def test_transport_close_failure_does_not_hide_an_already_accepted_turn(plan_adapter):
    writer=stage_graph(plan_adapter)
    class CloseFailure(WriterWire):
        async def aclose(self):
            self.closed=True
            raise RuntimeError('synthetic close failure')
    wire=CloseFailure(plan_adapter,json.dumps(graph_answer()))
    with pytest.raises(RuntimeError,match='close failure'):
        asyncio.run(writer.run(transport=wire,api_key='synthetic-not-secret'))
    turn=plan_adapter.service.list_turns(plan_adapter.world_id,plan_adapter.turn.conversation_id)[0]
    assert len(wire.calls)==1 and wire.closed and turn.status!='completed'


def test_unused_available_graph_uses_exact_plan_status_without_repair(plan_adapter):
    writer=stage_graph(plan_adapter)
    assert 'means graph_unused' not in writer.instructions
    assert 'Use plan_only_graph_unused' in writer.instructions
    answer={'answer_context_status':'plan_only_graph_unused','answer_segments':[
        {'kind':'connective','text':'We can discuss the image direction before choosing any established details.'}]}
    wire=WriterWire(plan_adapter,json.dumps(answer))
    completed=asyncio.run(writer.run(transport=wire,api_key='synthetic-not-secret'))
    assert completed.status=='completed' and len(wire.calls)==1
    assert completed.completion.answer_context_status=='plan_only_graph_unused'


def test_plan_writer_stops_renewal_and_uses_its_final_revision(plan_adapter,monkeypatch):
    writer=stage_graph(plan_adapter)
    original_stop=plan_adapter.stop
    original_complete=writer.rules.complete
    renewed=[]
    def stop_with_one_final_renewal():
        renewer=plan_adapter.fence.renewer
        with renewer._lock:
            turn=renewer._turn
            renewer._turn=plan_adapter.service.renew_turn_claim(turn.world_id,turn.conversation_id,turn.turn_id,
                expected_revision=turn.revision,lease_seconds=120)
            renewed.append(renewer._turn)
        return original_stop()
    def complete(turn,reply):
        assert not plan_adapter.fence.renewer._thread.is_alive()
        assert turn.revision==renewed[-1].revision
        return original_complete(turn,reply)
    monkeypatch.setattr(plan_adapter,'stop',stop_with_one_final_renewal)
    monkeypatch.setattr(writer.rules,'complete',complete)
    wire=WriterWire(plan_adapter,json.dumps(graph_answer()))
    completed=asyncio.run(writer.run(transport=wire,api_key='synthetic-not-secret'))
    assert completed.status=='completed' and completed.revision==renewed[-1].revision+1
    assert len(wire.calls)==1


def test_plan_writer_refuses_completion_when_renewal_error_is_reported(plan_adapter,monkeypatch):
    from apps.live_control_server.services.agent_turn_service import AgentTurnServiceError
    writer=stage_graph(plan_adapter)
    original_stop=plan_adapter.stop
    def failed_stop():
        with plan_adapter.fence.renewer._lock:
            plan_adapter.fence.renewer._error=RuntimeError('synthetic renewal uncertainty')
        return original_stop()
    monkeypatch.setattr(plan_adapter,'stop',failed_stop)
    monkeypatch.setattr(writer.rules,'complete',lambda *_args:pytest.fail('uncertain renewal reached completion'))
    wire=WriterWire(plan_adapter,json.dumps(graph_answer()))
    with pytest.raises(AgentTurnServiceError) as error:
        asyncio.run(writer.run(transport=wire,api_key='synthetic-not-secret'))
    assert error.value.code=='turn_claim_indeterminate' and len(wire.calls)==1 and wire.closed
    turn=plan_adapter.service.list_turns(plan_adapter.world_id,plan_adapter.turn.conversation_id)[0]
    assert turn.status!='completed'


@pytest.mark.parametrize('existing_link',[False,True])
def test_session_citation_title_comes_from_exact_writer_input(plan_adapter,existing_link):
    from dataclasses import replace
    from uuid import uuid4
    from urllib.parse import urlencode
    from application_state.agent_conversation.rules_authority_types import canonical_sha256
    a=plan_adapter
    run=str(uuid4())
    packet={'title':'Approach to Edge — Session Prep','world_id':a.world_id,'run_id':run,
        'review_revision':54,'ended_at':'2026-10-18T12:51:00Z',
        'sources':[{'kind':'scene_note','element_id':'crossing','text':'The boardwalk was pulled under.'}]}
    packet['sha256']=canonical_sha256(packet)
    a.work=replace(a.work,session_evidence={'sessions':[packet]})
    rules=PlanRulesRuntime(a,rules_capability(graph=True))
    proof=asyncio.run(PlanJevDriver(a).run(transport=Decisions(),api_key='synthetic-not-secret'))
    writer=PlanJevWriter(a,proof,rules)
    url='/play?'+urlencode({'world':a.world_id,'run':run,'evidence_revision':54})
    text=(f'[Session 54 scene notes]( {url} ) describe a submerged boardwalk.' if existing_link
        else 'Scene notes describe a submerged boardwalk.')
    candidate={'answer_context_status':'plan_only_insufficient_evidence','answer_segments':[
        {'kind':'session_evidence_claim','text':text,'run_id':run,'review_revision':54}]}
    completed=asyncio.run(writer.run(transport=WriterWire(a,json.dumps(candidate)),api_key='synthetic-not-secret'))
    assert 'Session 54' not in completed.assistant_text
    assert completed.assistant_text.count(url)==1
    assert '[Approach to Edge — Session Prep — notes and reflections]' in completed.assistant_text
    assert completed.completion.answer_segments[0].evidence_sha256==packet['sha256']
    saved=AgentConversationService().list_turns(a.world_id,completed.conversation_id)[-1]
    assert saved.assistant_text==completed.assistant_text


@pytest.mark.parametrize("field", ["_build_native_acquisition_services", "_plan_graph_read_services"])
def test_active_native_acquisition_refuses_writer_before_authorization_or_sdk_send(plan_adapter, field):
    writer = stage_graph(plan_adapter)
    before = plan_adapter.fence.turn.graph_context_execution.model_dump(mode='json')
    wire = WriterWire(plan_adapter, json.dumps(graph_answer()))
    setattr(plan_adapter, field, object())
    try:
        with pytest.raises(GenerationEngineError):
            asyncio.run(writer.run(transport=wire, api_key='synthetic-not-secret'))
        assert wire.calls == []
        assert writer.prepared is None
        assert plan_adapter.fence.turn.graph_context_execution.model_dump(mode='json') == before
    finally:
        setattr(plan_adapter, field, None)
