"""Common report binds retained evidence without awarding implicit acceptance."""
import copy
import json
from pathlib import Path
import subprocess
import sys

import pytest

from ingestion_evaluation.assessment import report, select
from ingestion_evaluation.runner import digest


@pytest.fixture
def assessment(tmp_path):
    def put(name, value):
        p = tmp_path / name
        p.write_text(json.dumps(value))
        return {'path': str(p), 'sha256': digest(p.read_bytes())}
    candidate = put('candidate.json', {'nodes': [{'description': 'Actual output'}]})
    result = put('result.json', {'run': {'run_id': 'one', 'revision': 5, 'components': {'candidate_graph': {'sha256': candidate['sha256']}}}})
    gold = put('gold.json', {'facts': [{'claim_id': 'F1', 'expected_claim': 'Expected claim'}]})
    review = put('review.json', {'run_id': 'one', 'revision': 5, 'candidate_sha256': candidate['sha256'], 'checks': [{'criterion_id': 'F1', 'status': 'SUPPORTED_PENDING_REVIEW'}]})
    unknown = {'status': 'unknown', 'reason': 'Not measured or executed'}
    spec = {'schema': 'dmb_ingestion_assessment_v1',
            'subject': {'result': {'artifact': result, 'pointer': '/run'}, 'candidate': candidate},
            'gold': [gold],
            'criteria': [{'criterion_id': 'F1', 'dimension': 'recall', 'gold': {'artifact': gold, 'pointer': '/facts/0'}}],
            'phases': {'raw_extraction': {'phase_evidence': [review], 'limitations': ['Content coverage only; precision holds remain.'], 'judgments': [
                {'criterion_id': 'F1', 'outcome': 'pass', 'reason': 'Coverage only; unrelated precision failures separate.',
                 'review': {'artifact': review, 'pointer': '/checks/0'},
                 'evidence': [{'artifact': candidate, 'pointer': '/nodes/0/description'}]}]},
                'reviewed_output': copy.deepcopy(unknown), 'publication': copy.deepcopy(unknown)},
            'measurements': {k: copy.deepcopy(unknown) for k in ['elapsed_ms', 'billed_cost_usd', 'review_effort_minutes']}}
    path = tmp_path / 'assessment.json'
    def save():
        path.write_text(json.dumps(spec))
        return path
    save()
    return spec, save, put


def test_actual_cli_keeps_phases_and_unknown_measurements_separate(assessment):
    _, save, _ = assessment
    cli = Path(__file__).resolve().parents[1] / 'scripts/evaluate_ingestion.py'
    output = subprocess.run([sys.executable, str(cli), 'assessment-report', '--manifest', str(save())],
                            capture_output=True, text=True, check=True)
    r = json.loads(output.stdout)
    assert r['phases']['raw_extraction']['by_dimension']['recall'] == {'pass': 1, 'fail': 0, 'partial': 0, 'unknown': 0}
    assert r['phases']['publication']['status'] == 'unknown'
    assert r['measurements']['billed_cost_usd']['status'] == 'unknown'
    assert r['phases']['raw_extraction']['limitations'] == ['Content coverage only; precision holds remain.']
    assert r['phases']['raw_extraction']['phase_evidence']


@pytest.mark.parametrize('mutation, error', [
    ('candidate', 'candidate differs'), ('missing', 'Every declared'),
    ('duplicate', 'duplicate'), ('gold_id', 'Gold object'),
    ('gold_authority', 'outside declared'), ('review_id', 'Review does not'),
    ('review_run', 'another or unspecified'), ('empty_evidence', 'inspectable'),
    ('empty_phase', 'phase evidence'), ('implicit_phase', 'three explicit'),
])
def test_rejects_mixed_or_incomplete_evidence(assessment, mutation, error):
    s, save, put = assessment
    phase = s['phases']['raw_extraction']; j = phase['judgments'][0]
    if mutation == 'candidate': s['subject']['candidate'] = put('other.json', {})
    elif mutation == 'missing': phase['judgments'] = []
    elif mutation == 'duplicate': phase['judgments'].append(copy.deepcopy(j))
    elif mutation == 'gold_id': s['criteria'][0]['criterion_id'] = 'F2'
    elif mutation == 'gold_authority': s['criteria'][0]['gold']['artifact'] = put('other.json', {'claim_id': 'F1'})
    elif mutation == 'review_id': j['review'] = {'artifact': put('other.json', {'run_id': 'one', 'revision': 5, 'candidate_sha256': s['subject']['candidate']['sha256'], 'criterion_id': 'F2'}), 'pointer': ''}
    elif mutation == 'review_run': j['review'] = {'artifact': put('other.json', {'run_id': 'other', 'criterion_id': 'F1'}), 'pointer': ''}
    elif mutation == 'empty_evidence': j['evidence'] = []
    elif mutation == 'empty_phase': phase['phase_evidence'] = []
    elif mutation == 'implicit_phase': del s['phases']['publication']
    with pytest.raises(ValueError, match=error): report(save())


def test_changed_artifact_refused(assessment):
    s, save, _ = assessment
    Path(s['gold'][0]['path']).write_text('{}')
    with pytest.raises(ValueError, match='Pin mismatch'): report(save())


@pytest.mark.parametrize('value', [-1, True, None, float('inf'), float('nan')])
def test_bad_or_missing_measurements_are_not_numbers(assessment, value):
    s, save, put = assessment
    s['measurements']['elapsed_ms'] = {'artifact': put('metric.json', {'value': value}), 'pointer': '/value'}
    with pytest.raises(ValueError, match='finite nonnegative'): report(save())


def test_zero_measurement_and_partial_unknown_judgments_preserved(assessment):
    s, save, put = assessment
    s['measurements']['billed_cost_usd'] = {'artifact': put('metric.json', {'cost': 0}), 'pointer': '/cost'}
    s['phases']['raw_extraction']['judgments'][0]['outcome'] = 'partial'
    r = report(save())
    assert r['measurements']['billed_cost_usd']['value'] == 0
    assert r['phases']['raw_extraction']['by_dimension']['recall']['partial'] == 1


@pytest.mark.parametrize('pointer', ['/list/-1', '/list/01', '/list/-', '/bad~2key', 'not/a/pointer'])
def test_invalid_selectors_not_evaluated(pointer):
    with pytest.raises(ValueError): select({'list': [1]}, pointer)


def test_escaped_pointer_keys():
    assert select({'a/b': {'~': 5}}, '/a~1b/~0') == 5


@pytest.mark.parametrize('changes', [
    {'candidate_sha256': '0' * 64}, {'revision': 1},
    {'run_revision': 1}, {'candidate_sha256': None},
    {'revision': None}, {'pins': {'candidate_graph': '0' * 64}},
])
def test_same_run_cannot_reuse_other_candidate_or_revision_review(assessment, changes):
    s, save, put = assessment
    judgment = s['phases']['raw_extraction']['judgments'][0]
    doc = json.loads(Path(judgment['review']['artifact']['path']).read_text())
    doc.update(changes)
    judgment['review']['artifact'] = put('changed-review.json', doc)
    with pytest.raises(ValueError, match='candidate binding|revision differs'):
        report(save())


def test_scalar_gold_constraint_retains_original_reference(assessment):
    s, save, put = assessment
    g = put('scalar-gold.json', {'constraints': ['Do not invent a completed trip.']})
    s['gold'] = [g]
    s['criteria'][0]['gold'] = {'artifact': g, 'pointer': '/constraints/0'}
    assert report(save())['phases']['raw_extraction']['criterion_count'] == 1


@pytest.mark.parametrize('gold_value', [{'id': 'F1', 'text': 'Interpretation'}, {'text': 'Withheld item', 'reason': 'Not authoritative'}])
def test_legacy_gold_objects_keep_original_identity_and_structure(assessment, gold_value):
    s, save, put = assessment
    g = put('object-gold.json', {'criteria': [gold_value]})
    s['gold'] = [g]
    s['criteria'][0]['gold'] = {'artifact': g, 'pointer': '/criteria/0'}
    assert report(save())['phases']['raw_extraction']['criterion_count'] == 1
