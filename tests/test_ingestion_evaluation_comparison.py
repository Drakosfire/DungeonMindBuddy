"""Real canonical validation precedes every numeric paired diagnostic."""
import copy
import json
from pathlib import Path
import subprocess
import sys

import pytest

from ingestion_evaluation.comparison import compare
from ingestion_evaluation.runner import digest
from tests.test_ingestion_evaluation_assessment import assessment


@pytest.fixture
def paired(assessment, tmp_path):
    original, _, put = assessment
    def item(name, outcome, cost=2, elapsed=10):
        s = copy.deepcopy(original)
        result = put(name + '-result.json', {'run': {'run_id': name, 'revision': 5,
            'components': {'candidate_graph': {'sha256': s['subject']['candidate']['sha256']}}}})
        s['subject']['result']['artifact'] = result
        phase = s['phases']['raw_extraction']
        review = put(name + '-review.json', {'run_id': name, 'revision': 5,
            'candidate_sha256': s['subject']['candidate']['sha256'], 'criterion_id': 'F1',
            'outcome': outcome, 'reason': phase['judgments'][0]['reason'],
            'evidence': phase['judgments'][0]['evidence']})
        phase['phase_evidence'] = [review]
        phase['judgments'][0].update(outcome=outcome, review={'artifact': review, 'pointer': ''})
        measured = put(name + '-metrics.json', {'cost': cost, 'elapsed': elapsed})
        s['measurements']['billed_cost_usd'] = {'artifact': measured, 'pointer': '/cost'}
        s['measurements']['elapsed_ms'] = {'artifact': measured, 'pointer': '/elapsed'}
        return put(name + '.json', s)
    spec = {'schema': 'dmb_ingestion_paired_comparison_v1', 'expected_cases': ['case'],
            'pairs_per_case': 2, 'pairs': [
                {'case_id': 'case', 'pair_id': '1', 'control': item('c1', 'pass'),
                 'variant': item('v1', 'unknown', 1, 5)},
                {'case_id': 'case', 'pair_id': '2', 'control': item('c2', 'pass'),
                 'variant': item('v2', 'fail', 0.5, 2)},
            ]}
    path = tmp_path / 'comparison.json'
    def save():
        path.write_text(json.dumps(spec))
        return path
    return spec, save, put


def test_real_cli_variation_unknown_bounds_and_offline_operation(paired, monkeypatch):
    _, save, _ = paired
    monkeypatch.setitem(sys.modules, 'psycopg', None)
    monkeypatch.setitem(sys.modules, 'ingestion_evaluation.buddy', None)
    r = compare(save())
    case = r['cases']['case']
    dimension = case['dimensions']['recall']
    assert dimension['median_pass_bounds'] == [-1, -0.5]
    assert dimension['median_fail_bounds'] == [0.5, 1]
    assert dimension['count_gate'] == 'fails_even_with_favorable_unknowns'
    metric = case['measurements']['billed_cost_usd']
    assert metric['median_ratio'] == '0.375'
    assert (metric['min_ratio'], metric['max_ratio']) == ('0.25', '0.5')
    assert case['measurements']['review_effort_minutes']['status'] == 'unknown'
    assert r['pairs'][0]['variant_report']['phases']['publication']['status'] == 'unknown'
    cli = Path(__file__).resolve().parents[1] / 'scripts/evaluate_ingestion.py'
    out = subprocess.run([sys.executable, str(cli), 'assessment-compare', '--manifest', str(save())],
                         check=True, capture_output=True, text=True)
    assert json.loads(out.stdout) == r


@pytest.mark.parametrize('mutation', ['missing_pair', 'missing_case', 'extra_pair', 'reused_run',
    'pair_id', 'gold_contract', 'tamper_pin', 'bad_metric', 'zero_denominator', 'missing_metric'])
def test_declared_pairs_and_bound_inputs(paired, mutation):
    spec, save, put = paired
    pair = spec['pairs'][1]
    if mutation == 'missing_pair': spec['pairs'].pop()
    elif mutation == 'missing_case': spec['expected_cases'].append('unobserved')
    elif mutation == 'extra_pair': spec['pairs'].append(copy.deepcopy(pair))
    elif mutation == 'reused_run': pair['variant'] = spec['pairs'][0]['variant']
    elif mutation == 'pair_id': pair['pair_id'] = '1'
    elif mutation == 'tamper_pin': pair['variant']['sha256'] = '0' * 64
    else:
        s = json.loads(Path(pair['control']['path']).read_text())
        if mutation == 'gold_contract': s['criteria'][0]['dimension'] = 'different'
        elif mutation == 'missing_metric': s['measurements']['billed_cost_usd'] = {'status': 'unknown', 'reason': 'Missing'}
        else:
            pin = put('replacement-metric.json', {'cost': float('nan') if mutation == 'bad_metric' else 0})
            s['measurements']['billed_cost_usd'] = {'artifact': pin, 'pointer': '/cost'}
        pair['control'] = put('replacement-control.json', s)
    if mutation in ('zero_denominator', 'missing_metric'):
        result = compare(save())['cases']['case']['measurements']['billed_cost_usd']
        assert result['status'] == 'unknown' and 'median_ratio' not in result
    else:
        with pytest.raises((ValueError, KeyError)):
            compare(save())


@pytest.mark.parametrize('count', [0, -1, True, 1.5])
def test_invalid_declared_replication(paired, count):
    spec, save, _ = paired
    spec['pairs_per_case'] = count
    with pytest.raises(ValueError): compare(save())


@pytest.mark.parametrize('outcomes,status', [
    (['pass', 'pass'], 'count_nonregression_under_all_unknown_outcomes'),
    (['unknown', 'pass'], 'unknowns_can_change_count_gate'),
])
def test_favorable_unknowns_are_not_automatic_passes(paired, outcomes, status):
    spec, save, put = paired
    for pair, outcome in zip(spec['pairs'], outcomes):
        s = json.loads(Path(pair['variant']['path']).read_text())
        phase = s['phases']['raw_extraction']
        judgment = phase['judgments'][0]
        judgment['outcome'] = outcome
        reviewed = json.loads(Path(judgment['review']['artifact']['path']).read_text())
        reviewed['outcome'] = outcome
        review_pin = put(pair['pair_id'] + '-changed-review.json', reviewed)
        judgment['review']['artifact'] = review_pin
        phase['phase_evidence'] = [review_pin]
        pair['variant'] = put(pair['pair_id'] + '-changed.json', s)
    assert compare(save())['cases']['case']['dimensions']['recall']['count_gate'] == status


def test_paired_comparison_cannot_count_a_forged_verdict(paired):
    spec, save, put = paired
    pair = spec['pairs'][1]
    assessment = json.loads(Path(pair['variant']['path']).read_text())
    assessment['phases']['raw_extraction']['judgments'][0]['outcome'] = 'pass'
    pair['variant'] = put('forged-assessment.json', assessment)
    with pytest.raises(ValueError, match='Review judgment differs for F1: outcome'):
        compare(save())
