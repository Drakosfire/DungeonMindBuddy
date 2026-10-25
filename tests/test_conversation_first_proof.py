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
        key: int(key == selected) for key in ('converse', 'research', 'write', 'image')}}}}


def test_labels_and_rubrics_never_reach_models():
    for case in cases():
        changed = deepcopy(case)
        changed.update(id='identity_canary', expected_step='secret_gold', expected_questions=987)
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
        return response('write')
    async def write(*args):
        pytest.fail('Wrong route must not be repaired using gold')
    row = asyncio.run(one(cases()[1], 0, decide, write))
    assert not row['passed'] and row['selected'] == 'write' and len(row['calls']) == 1


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
    {'converse': .5, 'research': .5, 'write': 0, 'image': 0},
    {'converse': float('nan'), 'research': 0, 'write': 0, 'image': 0},
    {'converse': 1, 'research': 1, 'write': 0, 'image': 0},
])
def test_ambiguous_or_invalid_decision_is_not_success(scores):
    with pytest.raises(ValueError):
        choose({'answers': {'next_step': {'selected': 'converse', 'probabilities': scores}}})
