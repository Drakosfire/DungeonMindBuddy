"""Exercise the offline assembly boundary with real common-report validation."""
import json
from pathlib import Path
import subprocess
import sys

import pytest

from ingestion_evaluation.assembly import assemble
from ingestion_evaluation.runner import digest


@pytest.fixture
def inputs(tmp_path):
    def put(name, value):
        p = tmp_path / name
        p.write_text(json.dumps(value))
        return {'path': str(p), 'sha256': digest(p.read_bytes())}
    candidate = put('candidate.json', {'nodes': [{'description': 'Actual model output'}]})
    result = put('result.json', {'run': {'run_id': 'one', 'revision': 5,
                 'components': {'candidate_graph': {'sha256': candidate['sha256']}}},
                 'components': {'candidate_graph': candidate}})
    gold = put('gold.json', {'facts': [{'claim_id': 'F1', 'expected_claim': 'Required fact'}]})
    criteria = put('criteria.json', {'schema': 'dmb_ingestion_assessment_v1', 'gold': [gold],
        'criteria': [{'criterion_id': 'F1', 'dimension': 'recall',
                      'gold': {'artifact': gold, 'pointer': '/facts/0'}}],
        'phases': {'publication': {'status': 'assessed', 'do_not_copy': True}}})
    review = put('review.json', {'run_id': 'one', 'revision': 5,
        'candidate_sha256': candidate['sha256'], 'unknowns': ['Precision not perfect'],
        'judgments': [{'criterion_id': 'F1', 'outcome': 'partial', 'reason': 'Mixed coverage',
            'expected_requirement': 'Reviewer annotation must stay in original only',
            'evidence': [{'artifact': candidate, 'pointer': '/nodes/0/description'}]}]})
    audit = put('audit.json', {'items': [{'run_id': 'one',
        'components': [{'kind': 'candidate_graph', **candidate}],
        'accounting': {'summary': {'cost_status': 'reported', 'cost_usd': 0.25}}}]})
    timing = put('timing.json', {'schema': 'dmb_ingestion_capture_timing_v1',
        'result_sha256': result['sha256'], 'elapsed_ms': 120.5})
    return {k: Path(v['path']) for k, v in locals().copy().items()
            if k in ('criteria', 'result', 'review', 'audit', 'timing')}


def invoke(inputs, output, *, measured=True):
    return assemble(inputs['criteria'], inputs['result'], inputs['review'], output,
                    audit_path=inputs['audit'] if measured else None,
                    timing_path=inputs['timing'] if measured else None)


def test_cli_projects_annotations_keeps_phases_and_actual_measurements(inputs, tmp_path):
    out = tmp_path / 'output'
    cli = Path(__file__).resolve().parents[1] / 'scripts/evaluate_ingestion.py'
    completed = subprocess.run([sys.executable, str(cli), 'assessment-assemble',
        '--manifest', str(inputs['criteria']), '--result', str(inputs['result']),
        '--review', str(inputs['review']), '--audit', str(inputs['audit']),
        '--timing', str(inputs['timing']), '--assessment-output', str(out)],
        capture_output=True, text=True, check=True)
    assert json.loads(completed.stdout)['outputs']['assessment.json']['path'] == str(out / 'assessment.json')
    a = json.loads((out / 'assessment.json').read_text())
    row = a['phases']['raw_extraction']['judgments'][0]
    assert set(row) == {'criterion_id', 'outcome', 'reason', 'review', 'evidence'}
    assert row['outcome'] == 'partial'
    assert 'expected_requirement' in inputs['review'].read_text()
    assert a['phases']['publication']['status'] == 'unknown'
    r = json.loads((out / 'assessment-report.json').read_text())
    assert r['phases']['raw_extraction']['by_dimension']['recall']['partial'] == 1
    assert r['measurements']['elapsed_ms']['value'] == 120.5
    assert r['measurements']['billed_cost_usd']['value'] == 0.25
    assert r['measurements']['review_effort_minutes']['status'] == 'unknown'


def test_offline_no_backend_import_and_missing_metrics_unknown(inputs, tmp_path, monkeypatch):
    monkeypatch.setitem(sys.modules, 'ingestion_evaluation.buddy', None)
    monkeypatch.setitem(sys.modules, 'psycopg', None)
    out = tmp_path / 'offline'
    invoke(inputs, out, measured=False)
    r = json.loads((out / 'assessment-report.json').read_text())
    assert all(x['status'] == 'unknown' for x in r['measurements'].values())


@pytest.mark.parametrize('mutation', ['run', 'candidate', 'missing_criterion', 'duplicate_criterion',
    'gold_id', 'legacy_review', 'bad_pointer', 'timing_result', 'negative_elapsed',
    'audit_run', 'audit_candidate', 'duplicate_audit_run', 'nonfinite_cost'])
def test_rejects_mixed_or_invalid_inputs_before_output(inputs, tmp_path, mutation):
    review = json.loads(inputs['review'].read_text())
    audit = json.loads(inputs['audit'].read_text())
    timing = json.loads(inputs['timing'].read_text())
    criteria = json.loads(inputs['criteria'].read_text())
    if mutation == 'run': review['run_id'] = 'other'
    elif mutation == 'candidate': review['candidate_sha256'] = '0' * 64
    elif mutation == 'missing_criterion': review['judgments'] = []
    elif mutation == 'duplicate_criterion': review['judgments'] *= 2
    elif mutation == 'gold_id': criteria['criteria'][0]['criterion_id'] = 'OTHER'
    elif mutation == 'legacy_review': review['checks'] = review.pop('judgments')
    elif mutation == 'bad_pointer': review['judgments'][0]['evidence'][0]['pointer'] = '/missing'
    elif mutation == 'timing_result': timing['result_sha256'] = '0' * 64
    elif mutation == 'negative_elapsed': timing['elapsed_ms'] = -1
    elif mutation == 'audit_run': audit['items'][0]['run_id'] = 'other'
    elif mutation == 'audit_candidate': audit['items'][0]['components'][0]['sha256'] = '0' * 64
    elif mutation == 'duplicate_audit_run': audit['items'] *= 2
    elif mutation == 'nonfinite_cost': audit['items'][0]['accounting']['summary']['cost_usd'] = float('nan')
    for name, value in [('review', review), ('audit', audit), ('timing', timing), ('criteria', criteria)]:
        inputs[name].write_text(json.dumps(value))
    out = tmp_path / 'invalid'
    with pytest.raises((ValueError, KeyError)):
        invoke(inputs, out)
    assert not out.exists()


def test_billing_unknown_is_not_zero(inputs, tmp_path):
    audit = json.loads(inputs['audit'].read_text())
    audit['items'][0]['accounting']['summary'] = {'cost_status': 'unknown', 'cost_usd': None}
    inputs['audit'].write_text(json.dumps(audit))
    out = tmp_path / 'unknown-cost'
    invoke(inputs, out)
    assert json.loads((out / 'assessment-report.json').read_text())['measurements']['billed_cost_usd']['status'] == 'unknown'


def test_repeat_and_missing_report_recovery_preserve_existing_evidence(inputs, tmp_path):
    out = tmp_path / 'repeat'
    invoke(inputs, out)
    original = (out / 'assessment.json').read_bytes()
    invoke(inputs, out)
    (out / 'assessment-report.json').unlink()
    invoke(inputs, out)
    assert (out / 'assessment.json').read_bytes() == original


def test_conflicting_report_does_not_create_or_overwrite_assessment(inputs, tmp_path):
    out = tmp_path / 'conflict'
    out.mkdir()
    (out / 'assessment-report.json').write_text('preserved failure evidence')
    with pytest.raises(ValueError, match='Existing evidence differs'):
        invoke(inputs, out)
    assert not (out / 'assessment.json').exists()
    assert (out / 'assessment-report.json').read_text() == 'preserved failure evidence'
