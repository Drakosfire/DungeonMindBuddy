"""Benchmark integrity, not assertions that a routing hypothesis succeeds."""
from copy import deepcopy
import json
from evals.utterance_intent.cases import public_cases
from evals.utterance_intent.proof import request,sdk_request,score,one
from generationengine.types import DecisionRequest
import asyncio


def test_gold_and_case_identity_never_enter_candidate_requests():
    for case in public_cases():
        for variant,intent in [('intent_flat',None),('fork',None),('fork','discuss'),('fork','create')]:
            before=request(case,variant,intent)
            altered=deepcopy(case);altered['gold']={'secret':'gold_canary'};altered['id']='identity_canary'
            assert request(altered,variant,intent)==before
            assert 'gold_canary' not in json.dumps(before)
            DecisionRequest.model_validate(sdk_request(before))


def test_captured_choice_options_and_rules_question_survive_adapter():
    payload={'model':'jev-1.14.0','state':{'data':'opaque'},'questions':{
        'operation':{'type':'choice','instructions':'What next?','criteria':{'answer_from_sources':None,'cannot_select':None}},
        'rules_query':{'type':'choice','instructions':'Rules?','criteria':{'none':None,'query:0':None}}}}
    converted=DecisionRequest.model_validate(sdk_request(payload))
    assert converted.state==payload['state']
    assert converted.questions[0].options==('answer_from_sources','cannot_select')
    assert converted.questions[1].name=='rules_query'
    assert converted.max_transport_retries==0


def test_transport_error_is_failure_not_a_correct_clarification(tmp_path):
    async def fail(_):raise TimeoutError('synthetic timeout')
    case=next(c for c in public_cases() if c['id']=='constructed-unknown_reference')
    result=asyncio.run(one(case,'fork',0,fail,tmp_path))
    assert not result['passed'] and result['actual']['outcome']=='error'
    assert result['error']=='TimeoutError'
    assert not score({'intent':'discuss','outcome':'reply'},case['gold'])['passed']
