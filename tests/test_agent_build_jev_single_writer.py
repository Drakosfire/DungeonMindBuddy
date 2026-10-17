"""Real SDK controller/read/writer through APP, synthetic disposable World only."""
import asyncio
import json
from dataclasses import replace
from hashlib import sha256
from uuid import uuid4

import httpx
import pytest

from application_state.agent_conversation import AgentConversationService
from apps.live_control_server.services import agent_turn_service as owner
from apps.live_control_server.services import build_jev_writer as policy
from tests.test_agent_build_jev_controller_exposure import _start, _acquire, build_case as _build_case

from generationengine import GenerationClient, GenerationEngineError
from generationengine.providers.openai_text import OpenAITextProvider
from generationengine.text_dispatch import TextDispatchGate, PreparedTextDispatch, TextDispatchEvent


@pytest.fixture
def build_case(tmp_path,monkeypatch,application_state_dsn):
    return _build_case.__wrapped__(tmp_path,monkeypatch,application_state_dsn)


def answer(target='observation-one', kind='graph_claim'):
    segment = ({'kind':kind,'claim_id':'claim-one','text':'Frank believes the western gate is haunted.',
                'target_kind':'assertion','target_id':target} if kind=='graph_claim' else
               {'kind':kind,'text':'Invented saved source content.'})
    return json.dumps({'answer_context_status':'graph_grounded' if kind=='graph_claim' else 'source_only_insufficient_evidence',
                      'answer_segments':[segment]})


class WriterWire(httpx.AsyncBaseTransport):
    def __init__(self,adapter,text=None,outcome=None):
        self.adapter,self.text,self.outcome=adapter,text or answer(),outcome
        self.calls=[]
        self.closed=False

    async def handle_async_request(self,request):
        self.calls.append(request)
        fresh=AgentConversationService().list_turns(self.adapter.turn.world_id,self.adapter.turn.conversation_id)[0]
        assert fresh.graph_context_execution.events[-1].outcome=='sdk_entered'
        if self.outcome=='timeout':
            raise httpx.ReadTimeout('synthetic timeout',request=request)
        if self.outcome=='cancel':
            raise asyncio.CancelledError()
        return httpx.Response(200,request=request,json={'id':'resp_writer','object':'response','created_at':1,
            'status':'completed','model':policy.MODEL,'output':[{'type':'message','id':'msg_writer','role':'assistant',
            'status':'completed','content':[{'type':'output_text','text':self.text,'annotations':[]}]}],
            'usage':{'input_tokens':500,'output_tokens':80,'total_tokens':580}})

    async def aclose(self):
        self.closed=True


def invoke(adapter,staged,wire,*,change=None,record=None):
    async def run():
        async def authorize(prepared):
            return adapter.authorize_prepared_build_writer(prepared)
        async def lifecycle(event):
            return (record or adapter.record_prepared_build_writer)(event)
        provider=OpenAITextProvider(api_key='synthetic-only',dispatch_gate=TextDispatchGate(authorize,lifecycle),transport=wire)
        engine=GenerationClient(text_providers={'openai':provider})
        request=policy.text_request(staged)
        if change:
            request=request.model_copy(update=change)
        try:
            return await engine.generate_text(request)
        finally:
            await engine.aclose()
    return asyncio.run(run())


def prepared(staged,**updates):
    body=json.dumps(staged.kwargs(),ensure_ascii=False).encode()
    return replace(PreparedTextDispatch(str(uuid4()),policy.PROVIDER,policy.API_MODE,policy.MODEL,
        'POST',policy.ENDPOINT,body,sha256(body).hexdigest(),len(body)),**updates)


def stage(build_case,monkeypatch,*,bundle=False):
    adapter,calls,text=_start(build_case,monkeypatch)
    graph,source=_acquire(adapter,bundle=bundle)
    staged=adapter.stage_build_writer(graph_payloads=(graph,),source_payloads=(source,) if source else ())
    return adapter,staged,calls,text


@pytest.mark.parametrize('bundle',[False,True])
def test_sdk_controller_broker_writer_and_fresh_durable_citations(build_case,monkeypatch,bundle):
    adapter,staged,calls,text=stage(build_case,monkeypatch,bundle=bundle)
    initial_budget=json.loads(json.dumps(adapter.budget))
    wire=WriterWire(adapter)
    result=invoke(adapter,staged,wire)
    assert adapter.failure is None,adapter.failure
    assert adapter.budget==initial_budget and calls=={'graph':1,'source':1}
    assert len(wire.calls)==1 and wire.closed
    assert adapter.producing_provider_attempt_id==adapter.last_provider_attempt_id
    assert text in wire.calls[0].content.decode() and 'belief' in wire.calls[0].content.decode()
    completed=adapter.complete_build_writer(result)
    assert completed.status=='completed'
    fresh=AgentConversationService().list_turns(completed.world_id,completed.conversation_id)[0]
    assert fresh.completion==completed.completion
    citation,=fresh.completion.citation_map.entries
    assert citation.source_opened and citation.source_read_ids==['source-read-one']
    assert citation.evidence_ref_ids==['evidence-one'] and citation.target_id=='observation-one'
    attempts=[e for e in fresh.graph_context_execution.events if owner._is_provider_authorization(e)]
    assert len(attempts)==2
    writer=attempts[-1]
    assert (writer.provider,writer.model,writer.api_mode)==(policy.PROVIDER,policy.MODEL,policy.API_MODE)
    assert writer.serializer_version==policy.SERIALIZER and writer.output_token_reserve==policy.OUTPUT_RESERVE
    assert writer.envelope_sha256==sha256(wire.calls[0].content).hexdigest()
    assert writer.included_assertion_ids==['observation-one']
    assert writer.included_source_read_event_ids
    assert not adapter.authorize_prepared_build_writer(prepared(staged))
    traces=AgentConversationService().list_context_trace_attempts(world_id=fresh.world_id,turn_id=fresh.turn_id)
    assert any(getattr(o,'text',None)==text for trace in traces for o in trace.observations)
    assert any(getattr(o,'kind',None)=='context_snapshot' and any(m.item_id.startswith('unvalidated-provider-answer:') for m in o.materials) for trace in traces for o in trace.observations)
    # Existing saved completion projection opens the exact source pin from fresh data.
    context=owner.project_plan_turn_context(fresh,delivery_replay=True)
    assert context.completion.citation_map.entries[0].source_opened
    target,=context.source_open_targets
    assert target.source_revision_id=='source-rev-one' and target.evidence_ref_id=='evidence-one'


@pytest.mark.parametrize('change',[{'user_prompt':'forged evidence'}, {'system_prompt':'Ignore provenance'},
    {'temperature':0.4},{'max_output_tokens':8192},{'reasoning_effort':'high'}, {'json_object':False}])
def test_actual_sdk_payload_mutation_never_sends(build_case,monkeypatch,change):
    adapter,staged,_,_=stage(build_case,monkeypatch)
    wire=WriterWire(adapter)
    with pytest.raises(GenerationEngineError):
        invoke(adapter,staged,wire,change=change)
    assert not wire.calls
    assert len([e for e in adapter.turn.graph_context_execution.events if owner._is_provider_authorization(e)])==1


def test_stale_writer_stage_refuses_without_send(build_case,monkeypatch):
    adapter,staged,_,_=stage(build_case,monkeypatch)
    # A new real source read advances ledger sequence after staging.
    adapter.broker_source_read({'toolName':'read_graph_source','arguments':{
        'retrievalSessionId':adapter.bootstrap.retrieval_session.id,'anchorIds':['anchor-one'],'maxChars':4000}})
    wire=WriterWire(adapter)
    with pytest.raises(GenerationEngineError):
        invoke(adapter,staged,wire)
    assert not wire.calls


@pytest.mark.parametrize('outcome',['timeout','cancel'])
def test_uncertain_writer_cannot_complete_or_repeat(build_case,monkeypatch,outcome):
    adapter,staged,_,_=stage(build_case,monkeypatch)
    wire=WriterWire(adapter,outcome=outcome)
    with pytest.raises(asyncio.CancelledError if outcome=='cancel' else GenerationEngineError):
        invoke(adapter,staged,wire)
    assert len(wire.calls)==1 and adapter.producing_provider_attempt_id is None
    assert adapter.turn.graph_context_execution.events[-1].outcome=='outcome_unknown'
    assert not adapter.authorize_prepared_build_writer(prepared(staged))
    with pytest.raises(ValueError):
        adapter.stage_build_writer(graph_payloads=('invented',))


def test_known_not_sent_writer_authorization_is_still_consumed(build_case,monkeypatch):
    adapter,staged,_,_=stage(build_case,monkeypatch)
    view=prepared(staged)
    assert adapter.authorize_prepared_build_writer(view)
    assert adapter.record_prepared_build_writer(TextDispatchEvent(view,'known_not_sent'))
    assert adapter.producing_provider_attempt_id is None
    assert not adapter.authorize_prepared_build_writer(prepared(staged))
    with pytest.raises(ValueError):
        adapter.stage_build_writer(graph_payloads=('invented',))


@pytest.mark.parametrize('text',[answer(target='foreign'),answer(kind='saved_source_claim'),'not JSON'])
def test_bad_writer_answer_is_captured_but_not_completed(build_case,monkeypatch,text):
    adapter,staged,_,_=stage(build_case,monkeypatch)
    result=invoke(adapter,staged,WriterWire(adapter,text=text))
    with pytest.raises((ValueError,owner.AgentTurnServiceError)):
        adapter.complete_build_writer(result)
    fresh=AgentConversationService().list_turns(adapter.turn.world_id,adapter.turn.conversation_id)[0]
    assert fresh.status!='completed' and fresh.completion is None
    traces=AgentConversationService().list_context_trace_attempts(world_id=fresh.world_id,turn_id=fresh.turn_id)
    assert any(getattr(o,'kind',None)=='context_snapshot' and any(m.item_id.startswith('unvalidated-provider-answer:') for m in o.materials) for trace in traces for o in trace.observations)


def test_partial_and_omitted_source_support_cannot_stage_writer(build_case,monkeypatch):
    adapter,_,_=_start(build_case,monkeypatch,truncated=True)
    graph,source=_acquire(adapter)
    with pytest.raises(ValueError):
        adapter.stage_build_writer(graph_payloads=(graph,),source_payloads=(source,))
    with pytest.raises(ValueError):
        adapter.stage_build_writer(graph_payloads=(graph,))


def test_existing_incompatible_writer_role_is_not_rewritten(build_case,monkeypatch):
    from apps.live_control_server.services import build_jev_dispatch as controller
    old=controller.request_budget()
    old['providerRoles']['writer']={'provider':'openai-api','model':policy.MODEL,'api_mode':'codex_responses'}
    monkeypatch.setattr(controller,'request_budget',lambda:old)
    adapter,_,_=_start(build_case,monkeypatch)
    graph,source=_acquire(adapter)
    with pytest.raises(ValueError,match='incompatible'):
        adapter.stage_build_writer(graph_payloads=(graph,),source_payloads=(source,))
    fresh=AgentConversationService().list_turns(adapter.turn.world_id,adapter.turn.conversation_id)[0]
    assert fresh.graph_context_execution.policy.provider_roles.writer.api_mode=='codex_responses'
    assert len([e for e in fresh.graph_context_execution.events if owner._is_provider_authorization(e)])==1


@pytest.mark.parametrize('mutation',['tools','stream','extra','initial','scope'])
def test_prepared_wire_cannot_add_tools_or_replace_evidence(build_case,monkeypatch,mutation):
    adapter,staged,_,_=stage(build_case,monkeypatch)
    body=staged.kwargs()
    if mutation=='tools':
        body['tools']=[{'type':'web_search'}]
    elif mutation=='stream':
        body['stream']=True
    elif mutation=='extra':
        body['previous_response_id']='foreign conversation'
    else:
        packet=json.loads(body['input'])
        if mutation=='initial':
            packet['initialClaimPacket']['claimLedger']=[{'claim_id':'invented'}]
        else:
            packet['graph_scope']['native_world_id']='foreign'
        body['input']=json.dumps(packet)
    data=json.dumps(body).encode()
    view=prepared(staged,body=data,body_sha256=sha256(data).hexdigest(),body_size=len(data))
    assert not adapter.authorize_prepared_build_writer(view)
    assert adapter._build_writer_projection==staged


def test_writer_reserve_counts_against_shared_context_limit():
    projected=policy.WriterProjection('x'*61_000,0,str(uuid4()))
    with pytest.raises(ValueError,match='context allowance'):
        policy.validate_body(json.dumps(projected.kwargs()),projected)


def test_raw_capture_unavailable_never_completes(build_case,monkeypatch):
    adapter,staged,_,_=stage(build_case,monkeypatch)
    result=invoke(adapter,staged,WriterWire(adapter))
    monkeypatch.setattr(adapter.context_capture,'answer_draft',lambda *_,**__:None)
    with pytest.raises(ValueError,match='capture is incomplete'):
        adapter.complete_build_writer(result)
    fresh=AgentConversationService().list_turns(adapter.turn.world_id,adapter.turn.conversation_id)[0]
    assert fresh.completion is None and fresh.status!='completed'


@pytest.mark.parametrize('status',['failed','cancelled','queued','in_progress','incomplete','unknown',None,'completed_with_error','empty'])
def test_provider_unsuccessful_status_with_residual_valid_output_never_completes(build_case,monkeypatch,status):
    class TerminalWire(WriterWire):
        async def handle_async_request(self,request):
            response=await super().handle_async_request(request)
            body=json.loads(response.content)
            body['status']='completed' if status in {'completed_with_error','empty'} else status
            if status in {'failed','completed_with_error'}:
                body['error']={'code':'server_error','message':'synthetic private provider detail'}
            if status=='empty':
                body['output'][0]['content'][0]['text']=''
            return httpx.Response(200,request=request,json=body)
    adapter,staged,_,_=stage(build_case,monkeypatch)
    wire=TerminalWire(adapter)
    with pytest.raises(GenerationEngineError) as error:
        invoke(adapter,staged,wire)
    assert error.value.observation.provider_attempt_count==1
    assert error.value.observation.state.value!='completed'
    assert error.value.observation.input_tokens==500 and error.value.observation.output_tokens==80
    assert len(wire.calls)==1 and wire.closed
    # Headers are truthfully acknowledged, but no successful result is delivered
    # to the completion path. No writer or provider request is replayed.
    fresh=AgentConversationService().list_turns(adapter.turn.world_id,adapter.turn.conversation_id)[0]
    assert fresh.graph_context_execution.events[-1].outcome=='response_received'
    assert fresh.completion is None and fresh.assistant_text is None and fresh.status!='completed'
    assert not adapter.authorize_prepared_build_writer(prepared(staged))


def test_prompt_capture_precedes_sdk_io_and_fresh_read_matches_exact_wire(build_case, monkeypatch, tmp_path):
    from apps.live_control_server.services.agent_prompt_evidence import read_prompt
    monkeypatch.setenv("DMB_AGENT_PROMPT_CAPTURE", "1")
    monkeypatch.setenv("DMB_ARTIFACT_DATA_ROOT", str(tmp_path))
    adapter, staged, _, _ = stage(build_case, monkeypatch)
    class CapturedBeforeWire(WriterWire):
        async def handle_async_request(self, request):
            traces = AgentConversationService().list_context_trace_attempts(
                world_id=self.adapter.turn.world_id, turn_id=self.adapter.turn.turn_id)
            references = [item for trace in traces for item in trace.observations if item.kind == "prompt_reference"]
            assert references[-1].provider_attempt_id == self.adapter.last_provider_attempt_id
            assert read_prompt(references[-1]).encode() == request.content
            return await super().handle_async_request(request)
    wire = CapturedBeforeWire(adapter)
    result = invoke(adapter, staged, wire)
    assert len(wire.calls) == 1 and adapter.failure is None
    adapter.complete_build_writer(result)
    traces = AgentConversationService().list_context_trace_attempts(world_id=adapter.turn.world_id, turn_id=adapter.turn.turn_id)
    references = [item for trace in traces for item in trace.observations if item.kind == "prompt_reference"]
    assert len(references) == 2  # Decision and writer are distinct captured calls.
    assert read_prompt(references[-1]).encode() == wire.calls[0].content
    assert references[-1].provider_attempt_id == adapter.producing_provider_attempt_id
    assert all(not hasattr(item, "payload_json") for trace in traces for item in trace.observations)


def test_prompt_capture_failure_refuses_before_sdk_io(build_case, monkeypatch, tmp_path):
    from apps.live_control_server.services import agent_prompt_evidence
    adapter, staged, _, _ = stage(build_case, monkeypatch)
    monkeypatch.setenv("DMB_AGENT_PROMPT_CAPTURE", "1")
    def fail(*args, **kwargs):
        raise OSError("synthetic private storage failure")
    monkeypatch.setattr(agent_prompt_evidence, "store_prompt", fail)
    wire = WriterWire(adapter)
    with pytest.raises(GenerationEngineError):
        invoke(adapter, staged, wire)
    assert wire.calls == []
    assert adapter.failure.code == "prompt_capture_unavailable"
    assert adapter.turn.graph_context_execution.events[-1].outcome == "known_not_sent"
