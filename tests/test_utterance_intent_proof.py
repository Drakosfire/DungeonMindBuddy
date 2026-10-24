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
    case['gold']['branches']=['clarify']
    result=asyncio.run(one(case,'fork',0,fail,tmp_path))
    assert not result['passed'] and result['actual']['outcome']=='error'
    assert result['error']=='TimeoutError'
    assert not score({'intent':'discuss','outcome':'reply'},case['gold'])['passed']


def test_wrong_unavailable_artifact_fails_complete_route():
    gold={'intent':'create','outcome':'unavailable','branches':['mechanics']}
    assert not score({'intent':'create','outcome':'unavailable','branch':'image'},gold)['passed']


def test_failed_second_call_preserves_reported_first_call_usage(tmp_path):
    from evals.utterance_intent.cases import fresh_holdout
    case=fresh_holdout()[0]
    calls=0
    async def provider(_):
        nonlocal calls
        calls+=1
        if calls==2:raise TimeoutError('synthetic branch failure')
        return {'answers':{'intent':{'selected':'discuss','probabilities':{'discuss':1,'create':0}}},
                'observation':{'input_tokens':600,'output_tokens':30}}
    result=asyncio.run(one(case,'fork',0,provider,tmp_path))
    assert result['input_tokens']==600 and result['output_tokens']==30
    assert not result['input_tokens_complete'] and not result['passed']


def test_missing_gold_rejected_before_provider(tmp_path):
    from evals.utterance_intent.proof import run
    async def forbidden(_):raise AssertionError('Must not call provider')
    import pytest
    with pytest.raises(ValueError,match='branch gold'):
        asyncio.run(run([{'id':'bad','gold':{'intent':'create','outcome':'unavailable'}}],forbidden,tmp_path/'output'))
    assert not (tmp_path/'output').exists()


def test_flat_and_fork_leaf_definitions_match():
    from evals.utterance_intent.cases import fresh_holdout
    case=fresh_holdout()[0]
    flat=sdk_request(request(case,'intent_flat'))['questions'][0]
    for intent in ('discuss','create'):
        fork=sdk_request(request(case,'fork',intent))['questions'][0]
        assert flat['question']==fork['question']
        assert all(flat['option_descriptions'][o]==fork['option_descriptions'][o] for o in fork['options'])


def test_ablation_reconstructs_exact_interaction_and_keeps_semantic_context():
    interaction={'history':[{'user':'Read the page','assistant':'Source context'}],
                 'allowed_operations':['answer_from_sources'],'page_target':{'body':'Keep current draft'}}
    payload={'model':'jev-1.14.0','questions':{'operation':{'type':'choice','instructions':'Choose','criteria':{'answer_from_sources':None}}},
             'state':{'context_accounting':{'request_limit_tokens':100},
                      'interaction':interaction,'initialClaimPacket':{'evidence':['Retain all facts']},
                      'graph_scope':{'revision':7},'rules_projection':{'authorization':'unchanged'},
                      'decision':{'model':'jev-1.14.0','request_id':'diagnostic','kind':'operation',
                                  'state':{'interaction':deepcopy(interaction),'user_question':'Read the page'}}}}
    case={'baseline_request':payload}
    for variant in ('metadata_only','deduplicated','dedup_metadata'):
        actual=request(case,variant)
        assert actual['questions']==payload['questions']
        if variant in ('deduplicated','dedup_metadata'):
            assert actual['state']['decision']['state']['interaction']=={'exact_reference':'state.interaction'}
            actual['state']['decision']['state']['interaction']=deepcopy(actual['state']['interaction'])
        if variant in ('metadata_only','dedup_metadata'):
            actual['state']['context_accounting']=deepcopy(payload['state']['context_accounting'])
            for key in ('model','request_id'):actual['state']['decision'][key]=payload['state']['decision'][key]
        assert actual==payload
    assert case['baseline_request']==payload


def test_different_interactions_are_never_collapsed():
    import pytest
    case={'baseline_request':{'state':{'interaction':{'history':['new']},
                                     'decision':{'state':{'interaction':{'history':['old']}}}}}}
    with pytest.raises(ValueError,match='copies differ'):
        request(case,'deduplicated')


def test_instruction_variant_moves_identical_guidance_only():
    from evals.utterance_intent.cases import instruction_holdout
    from evals.utterance_intent.proof import SEMANTICS,LEAF_QUESTION
    for case in instruction_holdout():
        control=request(case,'intent_flat')
        candidate=request(case,'instruction_flat')
        assert candidate['questions']['route']['question']==SEMANTICS+'\n'+LEAF_QUESTION
        candidate['questions']['route']['question']=LEAF_QUESTION
        candidate['state']['routing_guidance']=SEMANTICS
        assert candidate==control
        altered=deepcopy(case);altered['gold']={'secret':'must_not_leak'};altered['id']='secret_identity'
        assert request(altered,'instruction_flat')==request(case,'instruction_flat')
        DecisionRequest.model_validate(sdk_request(request(case,'instruction_flat')))


def test_operator_adjudication_preserves_original_run_and_reports_unique_weight():
    from evals.utterance_intent.adjudication import adjudicate
    from evals.utterance_intent.proof import digest
    import pytest
    case={'id':'names','question':'Brainstorm a list of ten names.',
          'gold':{'intent':'discuss','outcome':'reply','branches':['brainstorm']}}
    manifest={'cases':[case]}
    report={'manifest_sha256':digest(manifest),'rows':[{'family':'dogfood','variant':'candidate','case_id':'names',
             'actual':{'intent':'create','outcome':'writing','branch':'writing'}}]*2}
    originals=deepcopy((manifest,report))
    override={'case_id':'names','question_sha256':digest(case['question']),
              'authority':'Explicit operator clarification: stage a page suggestion',
              'gold':{'intent':'create','outcome':'writing','branches':['writing']}}
    result=adjudicate(manifest,report,[override])
    assert result['groups'][0]['complete']==2
    assert result['groups'][0]['unique_utterances']==1
    assert result['groups'][0]['utterance_macro_intent_outcome']==1
    assert (manifest,report)==originals
    override['question_sha256']='wrong'
    with pytest.raises(ValueError,match='question differs'):adjudicate(manifest,report,[override])
