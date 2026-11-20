"""Real SDK parameter omission and unchanged incomplete-response rejection."""
import asyncio
import json

import httpx
import pytest

from generationengine import GenerationClient, TextRequest
from generationengine.types import GenerationEngineError
from generationengine.text_dispatch import TextDispatchGate
from apps.live_control_server.services.plan_jev_writer import PlanWriterProvider
from application_state.agent_conversation.native_writer import output_request_fields,validate_output_request
from application_state.agent_conversation.native_execution import NativeWriterEstimatedBudgetV1


def run_reply(*, incomplete=False):
    calls=[]
    answer='Useful synthetic prose. ' * 5000
    def transport(request):
        calls.append(json.loads(request.content))
        payload={'id':'resp_synthetic','object':'response','created_at':1,'model':'gpt-6-luna',
            'status':'incomplete' if incomplete else 'completed',
            'output':[{'id':'msg_synthetic','type':'message','role':'assistant','status':'completed',
                'content':[{'type':'output_text','text':json.dumps({'answer':answer}),'annotations':[]}]}],
            'usage':{'input_tokens':25,'output_tokens':5001,'total_tokens':5026}}
        if incomplete:payload['incomplete_details']={'reason':'max_output_tokens'}
        return httpx.Response(200,request=request,json=payload)
    async def run():
        async def authorize(prepared):
            assert 'max_output_tokens' not in json.loads(prepared.body)
            return True
        async def record(event):
            return True
        provider=PlanWriterProvider(api_key='synthetic-not-secret',transport=httpx.MockTransport(transport),
            dispatch_gate=TextDispatchGate(authorize,record))
        client=GenerationClient(text_providers={'openai':provider})
        try:
            return await client.generate_structured(TextRequest(provider='openai',model='gpt-6-luna',
                user_prompt=json.dumps([{'role':'user','content':'A synthetic request.'}]),
                max_output_tokens=None,temperature=None,reasoning_effort='low',
                json_schema={'type':'object','properties':{'answer':{'type':'string'}},'required':['answer'],'additionalProperties':False},
                schema_name='synthetic_answer',max_conformance_retries=0,max_transport_retries=0))
        finally:await client.aclose()
    return calls,answer,run


def test_official_sdk_request_omits_cap_and_retains_large_reported_output():
    calls,answer,run=run_reply()
    result=asyncio.run(run())
    assert len(calls)==1 and 'max_output_tokens' not in calls[0]
    assert json.loads(result.text)['answer']==answer
    assert result.observation.output_tokens==5001


def test_provider_incomplete_is_not_accepted_when_app_output_cap_is_absent():
    calls,_,run=run_reply(incomplete=True)
    with pytest.raises(GenerationEngineError):asyncio.run(run())
    assert len(calls)==1 and 'max_output_tokens' not in calls[0]


def test_zero_reservation_is_omission_not_a_zero_or_null_sdk_cap():
    assert output_request_fields(0)=={}
    validate_output_request({'model':'gpt-6-luna'},0)
    for value in (0,None,4096):
        with pytest.raises(ValueError):validate_output_request({'max_output_tokens':value},0)


def test_historical_budget_keeps_its_original_capacity_and_hash_shape():
    wire=dict(schema='dmb_native_writer_estimated_budget_v1',provider='openai',
        model='gpt-6-luna',api_mode='responses',estimator='o200k_double_plus_4096_adaptive_context_v4',
        tokenizer_version='historical-counter',context_limit_tokens=128000,output_reserve_tokens=4096)
    saved=NativeWriterEstimatedBudgetV1.model_validate(wire)
    assert saved.model_dump(mode='json',by_alias=True)==wire
    validate_output_request({'max_output_tokens':4096},saved.output_reserve_tokens)


@pytest.mark.parametrize('window,reserve',[(None,4096),(128000,0)])
def test_native_writer_rejects_mixed_historical_and_provider_default_limits(window,reserve):
    wire=dict(schema='dmb_native_writer_estimated_budget_v1',provider='openai',
        model='gpt-6-luna',api_mode='responses',estimator='o200k_double_plus_4096_adaptive_context_v4',
        tokenizer_version='counter',context_limit_tokens=window,output_reserve_tokens=reserve)
    with pytest.raises(ValueError,match='complete historical or provider-owned'):
        NativeWriterEstimatedBudgetV1.model_validate(wire)
