"""Exercise lossless public inputs through the existing assessment consumer."""
import json
from pathlib import Path
import sys

import pytest

from ingestion_evaluation.blinding import prepare
from ingestion_evaluation.assembly import assemble
from ingestion_evaluation.runner import digest


@pytest.fixture
def case(tmp_path):
    def put(name, value):
        p = tmp_path / name
        p.write_text(json.dumps(value))
        return {'path': str(p), 'sha256': digest(p.read_bytes())}
    text = 'Malformed model text; reasoning_effort is a word here. 雪'
    response = {'text': text, 'sha256': digest(text.encode()), 'utf8_bytes': len(text.encode())}
    candidate = put('original-candidate.json', {'nodes': [{'description': text}], 'beats': []})
    raw = put('original-raw.json', {'execution_evidence': {'records': [
        {'kind': 'pass_telemetry', 'envelope': {'reasoning_effort': 'PRIVATE_SENTINEL'}},
        {'kind': 'raw_model_response', 'envelope': {'request': {'reasoning_effort': 'PRIVATE_SENTINEL'}, 'response': response}},
        {'kind': 'raw_model_response', 'envelope': {'response': response}},
    ]}})
    result = put('result.json', {'run': {'run_id': 'opaque-run', 'revision': 5,
        'components': {'candidate_graph': candidate, 'raw_model_response': raw}},
        'components': {'candidate_graph': candidate, 'raw_model_response': raw}})
    return {'put': put, 'result': Path(result['path']), 'candidate': candidate,
            'raw': raw, 'text': text, 'output': tmp_path / 'public', 'receipt': tmp_path / 'private.json'}


def invoke(case):
    return prepare(case['result'], case['output'], case['receipt'], 'opaque01')


def test_all_attempts_exact_utf8_no_telemetry_and_idempotent(case, monkeypatch):
    monkeypatch.setitem(sys.modules, 'psycopg', None)
    monkeypatch.setitem(sys.modules, 'ingestion_evaluation.buddy', None)
    receipt = invoke(case)
    assert receipt == invoke(case)
    out = case['output']
    assert (out / 'candidate.json').read_bytes() == Path(case['candidate']['path']).read_bytes()
    responses = json.loads((out / 'responses.json').read_text())['responses']
    assert [x['text'] for x in responses] == [case['text']] * 2  # repeated attempt not deduplicated
    assert len({x['response_id'] for x in responses}) == 2
    assert all('PRIVATE_SENTINEL' not in p.read_text() for p in out.iterdir())
    private = json.loads(case['receipt'].read_text())
    assert private['response_mapping'][0]['original_pointer'].endswith('/1/envelope/response/text')
    assert 'original-raw' in case['receipt'].read_text()


def test_public_refs_and_binding_work_in_unchanged_assembler(case, tmp_path):
    packet = invoke(case)
    put = case['put']
    gold = put('gold.json', {'facts': [{'claim_id': 'F1', 'expected_claim': 'required'}]})
    criteria = put('criteria.json', {'schema': 'dmb_ingestion_assessment_v1', 'gold': [gold],
        'criteria': [{'criterion_id': 'F1', 'dimension': 'recall', 'gold': {'artifact': gold, 'pointer': '/facts/0'}}]})
    binding = json.loads((case['output'] / 'binding.json').read_text())
    review = put('review.json', {**binding, 'judgments': [{'criterion_id': 'F1', 'outcome': 'fail',
        'reason': 'Retained failed text', 'evidence': [{'artifact': packet['public']['responses.json'],
                                                     'pointer': '/responses/0/text'}]}]})
    before = Path(review['path']).read_bytes()
    assemble(Path(criteria['path']), case['result'], Path(review['path']), tmp_path / 'assessment')
    assert Path(review['path']).read_bytes() == before


@pytest.mark.parametrize('mutation', ['text_hash', 'length', 'missing_text', 'candidate_hash',
    'run_binding', 'unexpected_kind', 'candidate_telemetry', 'unknown_candidate_root'])
def test_tamper_fails_before_any_output(case, mutation):
    result = json.loads(case['result'].read_text())
    raw = json.loads(Path(case['raw']['path']).read_text())
    candidate = json.loads(Path(case['candidate']['path']).read_text())
    response = raw['execution_evidence']['records'][1]['envelope']['response']
    if mutation == 'text_hash': response['sha256'] = '0' * 64
    elif mutation == 'length': response['utf8_bytes'] += 1
    elif mutation == 'missing_text': response['text'] = None
    elif mutation == 'candidate_hash': result['components']['candidate_graph']['sha256'] = '0' * 64
    elif mutation == 'run_binding': result['run']['components']['candidate_graph']['sha256'] = '0' * 64
    elif mutation == 'unexpected_kind': raw['execution_evidence']['records'][0]['kind'] = 'unknown'
    elif mutation == 'candidate_telemetry': candidate['nodes'][0]['usage'] = {'tokens': 1}
    elif mutation == 'unknown_candidate_root': candidate['provider_accounting'] = {}
    if mutation not in ('candidate_hash', 'run_binding'):
        for kind, value, pin in (('raw_model_response', raw, case['raw']), ('candidate_graph', candidate, case['candidate'])):
            path = Path(pin['path']); path.write_text(json.dumps(value))
            for part in (result['components'], result['run']['components']):
                part[kind]['sha256'] = digest(path.read_bytes())
    case['result'].write_text(json.dumps(result))
    with pytest.raises((ValueError, KeyError)):
        invoke(case)
    assert not case['output'].exists() and not case['receipt'].exists()


def test_private_receipt_never_inside_packet(case):
    with pytest.raises(ValueError, match='outside'):
        prepare(case['result'], case['output'], case['output'] / 'private.json', 'opaque01')
    assert not case['output'].exists()


def test_conflicting_private_receipt_prevents_all_public_writes(case):
    case['receipt'].write_text('preserve')
    with pytest.raises(ValueError, match='differs'):
        invoke(case)
    assert not case['output'].exists() and case['receipt'].read_text() == 'preserve'


def test_cli_requires_its_own_flags_and_rejects_unrelated_flags(case):
    import subprocess
    cli = Path(__file__).resolve().parents[1] / 'scripts/evaluate_ingestion.py'
    args = [sys.executable, str(cli), 'review-packet', '--result', str(case['result']),
            '--packet-output', str(case['output']), '--private-receipt', str(case['receipt']),
            '--review-id', 'opaque01']
    bad = subprocess.run(args + ['--audit', 'irrelevant'], capture_output=True)
    assert bad.returncode != 0 and not case['output'].exists()
    good = subprocess.run(args, capture_output=True, text=True, check=True)
    assert json.loads(good.stdout)['public']['candidate.json']['sha256'] == case['candidate']['sha256']


def test_unexpected_public_files_are_not_exposed_or_removed(case):
    case['output'].mkdir()
    (case['output'] / 'telemetry.json').write_text('preserve private evidence')
    with pytest.raises(ValueError, match='unexpected files'):
        invoke(case)
    assert (case['output'] / 'telemetry.json').read_text() == 'preserve private evidence'
    assert not case['receipt'].exists()


def test_host_materialization_origin_comes_from_owner_receipt_not_authored_text(case):
    result = json.loads(case['result'].read_text())
    raw_path = Path(case['raw']['path'])
    raw = json.loads(raw_path.read_text())
    first = raw['execution_evidence']['records'][1]['envelope']
    first.update(pass_name='actor_pass', ge_attempt={'event_id': 'attempt-1'})
    second = raw['execution_evidence']['records'][2]['envelope']
    second.update(pass_name='actor_pass-normalized', ge_attempt=None)
    # Identical text has different origins; no text-shape heuristic or redaction.
    raw_path.write_text(json.dumps(raw))
    for part in (result['components'], result['run']['components']):
        part['raw_model_response']['sha256'] = digest(raw_path.read_bytes())
    case['result'].write_text(json.dumps(result))
    invoke(case)
    rows = json.loads((case['output'] / 'responses.json').read_text())['responses']
    assert [r['origin'] for r in rows] == ['provider_response', 'host_materialization']
    assert rows[0]['text'] == rows[1]['text'] == case['text']
