"""Offline projection of sealed current-format reviews into canonical assessments."""
from __future__ import annotations

import json
from pathlib import Path
import tempfile

from ingestion_evaluation.assessment import report
from ingestion_evaluation.runner import digest, encoded, read_pin, retain_bytes


def _pin(path: Path) -> dict:
    return {'path': str(path.resolve()), 'sha256': digest(path.read_bytes())}


def _unknown(reason: str) -> dict:
    return {'status': 'unknown', 'reason': reason}


def assemble(criteria_path: Path, result_path: Path, review_path: Path, output: Path,
             *, audit_path: Path | None = None, timing_path: Path | None = None) -> dict:
    """Copy judgments, never invent them; validate all evidence before retaining outputs."""
    criteria_pin = _pin(criteria_path)
    criteria = json.loads(read_pin(criteria_pin))
    if criteria.get('schema') != 'dmb_ingestion_assessment_v1':
        raise ValueError('Criteria must come from the common assessment format')
    result_pin, review_pin = _pin(result_path), _pin(review_path)
    result = json.loads(read_pin(result_pin))
    review = json.loads(read_pin(review_pin))
    run = result['run']
    candidate = result['components']['candidate_graph']
    read_pin(candidate)
    candidate = {'path': str(Path(candidate['path']).resolve()), 'sha256': candidate['sha256']}
    rows = review.get('judgments')
    if not isinstance(rows, list) or not rows:
        raise ValueError('Sealed review requires current-format judgments')
    # Extra reviewer annotations stay in the pinned original, not in canonical rows.
    judgments = [{**{key: row[key] for key in ('criterion_id', 'outcome', 'reason', 'evidence')},
                  'review': {'artifact': review_pin, 'pointer': f'/judgments/{index}'}}
                 for index, row in enumerate(rows)]
    phase_evidence = [review_pin, criteria_pin]
    measurements = {
        'elapsed_ms': _unknown('No bound capture timing supplied'),
        'billed_cost_usd': _unknown('No bound reported billing supplied'),
        'review_effort_minutes': _unknown('Human review effort not measured; automated time is not human time'),
    }
    if timing_path is not None:
        timing_pin = _pin(timing_path)
        timing = json.loads(read_pin(timing_pin))
        if (timing.get('schema') != 'dmb_ingestion_capture_timing_v1'
                or timing.get('result_sha256') != result_pin['sha256']):
            raise ValueError('Timing does not bind this exact result')
        measurements['elapsed_ms'] = {'artifact': timing_pin, 'pointer': '/elapsed_ms'}
        phase_evidence.append(timing_pin)
    if audit_path is not None:
        audit_pin = _pin(audit_path)
        audit = json.loads(read_pin(audit_pin))
        matches = [(i, item) for i, item in enumerate(audit['items']) if item.get('run_id') == run['run_id']]
        if len(matches) != 1:
            raise ValueError('Audit must identify this run exactly once')
        index, item = matches[0]
        candidates = [x for x in item['components'] if x.get('kind') == 'candidate_graph']
        if len(candidates) != 1 or candidates[0]['sha256'] != candidate['sha256']:
            raise ValueError('Audit candidate differs from this result')
        summary = item['accounting']['summary']
        if summary.get('cost_status') == 'reported':
            measurements['billed_cost_usd'] = {
                'artifact': audit_pin, 'pointer': f'/items/{index}/accounting/summary/cost_usd'}
        else:
            measurements['billed_cost_usd'] = _unknown('Billing is not reported in the bound audit')
        phase_evidence.append(audit_pin)
    assessment = {
        'schema': 'dmb_ingestion_assessment_v1',
        'subject': {'result': {'artifact': result_pin, 'pointer': '/run'}, 'candidate': candidate},
        'gold': criteria['gold'], 'criteria': criteria['criteria'],
        'phases': {
            'raw_extraction': {'phase_evidence': phase_evidence, 'judgments': judgments,
                               'limitations': [
                                   'Projection of sealed independent judgments, not a new semantic assessment.',
                                   'Gold coverage does not establish whole-output precision or acceptance; '
                                   'preserve every defect, unknown and limitation in the pinned review.',
                                   'No reviewed-output or publication execution is inferred.',
                               ]},
            'reviewed_output': _unknown('No accepted reviewed-output assessment supplied'),
            'publication': _unknown('No publication assessment supplied'),
        },
        'measurements': measurements,
    }
    body = encoded(assessment)
    # Reuse the authoritative validator; no duplicate criterion/binding/metric checks.
    with tempfile.TemporaryDirectory(prefix='ingestion-assessment-') as temporary:
        draft = Path(temporary) / 'assessment.json'
        draft.write_bytes(body)
        checked = report(draft)
    outputs = {'assessment.json': body, 'assessment-report.json': encoded(checked)}
    # Check every conflict before writing either output; retries never overwrite evidence.
    for name, content in outputs.items():
        target = output / name
        if target.exists() and target.read_bytes() != content:
            raise ValueError(f'Existing evidence differs: {target}')
    output.mkdir(parents=True, exist_ok=True)
    for name, content in outputs.items():
        retain_bytes(output / name, content)
    return {'scope': 'Offline assessment assembly only; no semantic grading or publication authority',
            'outputs': {name: _pin(output / name) for name in outputs}}
