import asyncio
from copy import deepcopy

import pytest

from evals.graph_memory_layer.jev_controller_cohort import cases, score_case
from evals.graph_memory_layer.jev_evidence_loop import request_for, validate_snapshot
from evals.graph_memory_layer.run_jev_controller_cohort import run_cohort


def test_cohort_is_frozen_valid_and_gold_never_in_decision_requests():
    for case in cases().values():
        snapshot = case['snapshot']
        validate_snapshot(snapshot)
        units = list(snapshot['units'].values())
        first = request_for(snapshot, units, list(snapshot['actions'].values()))
        changed = deepcopy(case)
        changed['gold'] = {'secret_gold_canary': 'NEVER SEND THIS'}
        assert request_for(changed['snapshot'], units, list(snapshot['actions'].values())) == first
        assert 'gold' not in first and 'expected_status' not in first['state']
    assert len(cases()) == 6


@pytest.mark.parametrize('status,ids,passed', [
    ('provisionally_supported', ['u1', 'u2'], True),
    ('provisionally_supported', ['u1'], False),
    ('retrieval_exhausted', ['u1', 'u2'], False),
])
def test_scoring_requires_correct_stop_and_all_required_support(status, ids, passed):
    case = cases()['two_hop_granular']
    result = {'status': status, 'selected_evidence': [case['snapshot']['units'][u] for u in ids]}
    assert score_case(result, case['gold'])['passed'] is passed


def test_missing_evidence_false_sufficient_is_a_failure():
    case = cases()['belief_is_not_confirmed_cause']
    assert not score_case({'status': 'provisionally_supported', 'selected_evidence': []}, case['gold'])['passed']


def test_runner_preserves_each_failure_without_provider_retry(tmp_path):
    calls = []
    async def unavailable(request):
        calls.append(request)
        raise TimeoutError()
    report = asyncio.run(run_cohort(unavailable, tmp_path/'cohort'))
    assert len(calls) == 6  # Different frozen cases, one attempted decision each.
    assert report['passed'] == 0 and report['luna_calls'] == 0
    assert all(r['actual_status'] == 'decision_unavailable_or_invalid' for r in report['cases'])
    with pytest.raises(FileExistsError):
        asyncio.run(run_cohort(unavailable, tmp_path/'cohort'))
    assert len(calls) == 6


def test_question_only_cohort_collapses_identical_question_variants(tmp_path):
    calls = []
    async def unavailable(request):
        calls.append(request)
        assert len(request['state']['requirements']) == 1
        assert request['state']['requirements'][0]['text'] == request['state']['user_question']
        assert request['state']['evidence'] == []
        raise TimeoutError()
    report = asyncio.run(run_cohort(unavailable, tmp_path/'cohort', question_only=True))
    assert len(calls) == report['total'] == 5
    assert report['question_only'] is True
