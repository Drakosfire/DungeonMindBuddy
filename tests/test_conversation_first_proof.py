import asyncio
from copy import deepcopy
import json

import pytest
from generationengine.types import DecisionRequest

from evals.conversation_first.cases import cases
from evals.conversation_first.scaffold import decision_request, frame
from evals.conversation_first.proof import choose, one


def response(selected):
    return {'answers': {'next_step': {'selected': selected, 'probabilities': {
        key: int(key == selected) for key in ('converse', 'research', 'prepare')}}}}


def test_labels_and_rubrics_never_reach_models():
    for case in cases():
        changed = deepcopy(case)
        changed.update(id='identity_canary', expected_step='secret_gold', expected_questions=987, expected_item='item_gold_canary', cohort='cohort_canary')
        assert decision_request(case) == decision_request(changed)
        assert frame(case) == frame(changed)
        assert 'secret_gold' not in json.dumps(decision_request(changed))
        DecisionRequest.model_validate(decision_request(case))


def test_workflow_ablation_changes_only_catalog():
    for case in cases():
        with_catalog = frame(case)
        without = frame(case, include_workflow=False)
        assert with_catalog.pop('workflow_catalog')
        assert without.pop('workflow_catalog') == []
        assert with_catalog == without


def test_wrong_route_does_not_use_gold_to_call_writer():
    async def decide(request, entry):
        return response('research')
    async def write(*args):
        pytest.fail('Wrong route must not be repaired using gold')
    row = asyncio.run(one(cases()[1], 0, decide, write))
    assert not row['passed'] and row['selected'] == 'research' and len(row['calls']) == 1


def test_provider_failure_retains_prior_call_and_fails():
    async def decide(request, entry):
        return response('converse')
    async def write(value, entry):
        raise TimeoutError('synthetic timeout')
    row = asyncio.run(one(cases()[1], 0, decide, write))
    assert row['error'] == 'TimeoutError' and not row['passed']
    assert row['calls'][0]['response'] and row['calls'][1]['response'] is None


def test_wrong_question_count_and_invalid_schema_fail():
    async def decide(request, entry):
        return response('converse')
    async def write(value, entry):
        return {'output': {'acknowledgement': 'Ready.', 'workflow_suggestion': None, 'questions': []}}
    assert not asyncio.run(one(cases()[1], 0, decide, write))['passed']
    async def malformed(value, entry):
        return {'output': {'secret_reasoning': 'not a reply'}}
    assert asyncio.run(one(cases()[1], 0, decide, malformed))['error'] == 'ValidationError'


@pytest.mark.parametrize('scores', [
    {'converse': .5, 'research': .5, 'prepare': 0},
    {'converse': float('nan'), 'research': 0, 'prepare': 0},
    {'converse': 1, 'research': 1, 'prepare': 0},
])
def test_ambiguous_or_invalid_decision_is_not_success(scores):
    with pytest.raises(ValueError):
        choose({'answers': {'next_step': {'selected': 'converse', 'probabilities': scores}}})


def test_controller_does_not_receive_workflow_steps_or_identity():
    for case in cases():
        assert 'develop_connected_place' not in json.dumps(decision_request(case))
        assert 'workflow_catalog' not in decision_request(case)['state']


def test_no_catalog_schema_does_not_leak_skill_identity_and_unknown_selection_fails():
    from evals.conversation_first.scaffold import REPLY_SCHEMA
    from evals.conversation_first.proof import validate_reply
    assert 'develop_connected_place' not in json.dumps(REPLY_SCHEMA)
    with pytest.raises(ValueError, match='unavailable workflow'):
        validate_reply({'output': {'acknowledgement': 'Ready', 'questions': [],
            'workflow_suggestion': 'develop_connected_place'}}, frame(cases()[1], include_workflow=False))


def test_failed_writer_preserves_received_invalid_text_and_known_usage():
    from evals.conversation_first.proof import retain_attempt
    from generationengine.types import StructuredAttemptCompleted
    async def decide(request, entry):
        return response('converse')
    async def write(value, entry):
        retain_attempt(entry, StructuredAttemptCompleted(operation_id='proof', event_id='proof:1',
            ordinal=1, kind='initial', provider='openai', requested_model='gpt-6-luna',
            resolved_model='gpt-6-luna', response_model='gpt-6-luna', provider_request_id='request',
            provider_response_id='response', text='invalid JSON', input_tokens=100, output_tokens=3))
        raise ValueError('received invalid output')
    row = asyncio.run(one(cases()[1], 0, decide, write))
    assert not row['passed']
    attempt = row['calls'][1]['attempts'][0]
    assert attempt['text'] == 'invalid JSON' and attempt['input_tokens'] == 100


def test_prepared_item_labels_do_not_reach_second_stage():
    from evals.conversation_first.scaffold import preparation_request
    for case in cases():
        changed = deepcopy(case)
        changed.update(id='identity_canary', expected_item='item_gold_canary', expected_step='secret_gold')
        assert preparation_request(case) == preparation_request(changed)
        assert 'item_gold_canary' not in json.dumps(preparation_request(changed))
        DecisionRequest.model_validate(preparation_request(case))


def test_prepare_routes_to_item_stage_without_writer_or_execution():
    from evals.conversation_first.scaffold import PREPARED_ITEMS
    case = next(c for c in cases() if c['id'] == 'new_shop_page')
    async def decide(request, entry):
        if request['questions'][0]['name'] == 'next_step':
            return response('prepare')
        return {'answers': {'prepared_item': {'selected': 'connected_page', 'probabilities': {
            key: int(key == 'connected_page') for key in PREPARED_ITEMS}}}}
    async def write(*args):
        pytest.fail('Classification must not dispatch a writer or create a page')
    row = asyncio.run(one(case, 0, decide, write))
    assert row['passed'] and row['prepared_item'] == 'connected_page'
    assert [c['role'] for c in row['calls']] == ['controller', 'prepared_item_controller']


def test_wrong_item_fails_even_when_prepare_route_matches():
    from evals.conversation_first.scaffold import PREPARED_ITEMS
    case = next(c for c in cases() if c['id'] == 'new_shop_page')
    async def decide(request, entry):
        if request['questions'][0]['name'] == 'next_step':
            return response('prepare')
        return {'answers': {'prepared_item': {'selected': 'image_preparation', 'probabilities': {
            key: int(key == 'image_preparation') for key in PREPARED_ITEMS}}}}
    async def write(*args):
        pytest.fail('No writer')
    row = asyncio.run(one(case, 0, decide, write))
    assert not row['passed'] and row['selected'] == 'prepare'


def test_first_stage_has_only_three_generic_actions():
    for case in cases():
        assert decision_request(case)['questions'][0]['options'] == ['converse', 'research', 'prepare']
