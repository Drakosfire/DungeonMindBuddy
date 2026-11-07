"""One offline assessment format; semantics remain an independent review judgment."""
from __future__ import annotations

from collections import Counter, defaultdict
import json
import math
from pathlib import Path
import re

from .runner import digest, read_pin

PHASES = ('raw_extraction', 'reviewed_output', 'publication')
OUTCOMES = frozenset({'pass', 'fail', 'partial', 'unknown'})
METRICS = frozenset({'elapsed_ms', 'billed_cost_usd', 'review_effort_minutes'})


def select(value, pointer):
    """Strict JSON Pointer, never eval, attribute access, or a filesystem path."""
    if not isinstance(pointer, str) or (pointer and not pointer.startswith('/')):
        raise ValueError('Expected a JSON Pointer')
    if not pointer:
        return value
    for token in pointer[1:].split('/'):
        if re.search(r'~(?![01])', token):
            raise ValueError('Invalid JSON Pointer escape')
        token = token.replace('~1', '/').replace('~0', '~')
        if isinstance(value, list):
            if not re.fullmatch(r'0|[1-9][0-9]*', token):
                raise ValueError('Invalid JSON array index')
            value = value[int(token)]
        elif isinstance(value, dict):
            value = value[token]
        else:
            raise ValueError('JSON Pointer traverses a scalar')
    return value


def reference(ref):
    if set(ref) != {'artifact', 'pointer'}:
        raise ValueError('Evidence requires an artifact pin and JSON Pointer')
    return select(json.loads(read_pin(ref['artifact'])), ref['pointer'])


def unknown(value):
    return (isinstance(value, dict) and set(value) == {'status', 'reason'}
            and value['status'] == 'unknown' and isinstance(value['reason'], str)
            and bool(value['reason'].strip()))


def bind_review(document, run, subject):
    """A mutable run ID alone cannot qualify a judgment about an older candidate."""
    if document.get('run_id', document.get('assessment_run_id')) != run['run_id']:
        raise ValueError('Review belongs to another or unspecified run')
    pins = document.get('pins', {})
    candidates = [v for v in (document.get('candidate_sha256'), pins.get('candidate_graph')) if v is not None]
    if not candidates or any(v != subject['candidate']['sha256'] for v in candidates):
        raise ValueError('Review requires the exact candidate binding')
    revisions = [document[k] for k in ('revision', 'run_revision', 'assessment_run_revision') if k in document]
    if any(type(v) is not int or v != run['revision'] for v in revisions):
        raise ValueError('Review revision differs from actual run')
    result_pin = pins.get('result')
    if result_pin is not None and result_pin != subject['result']['artifact']['sha256']:
        raise ValueError('Review result binding differs from actual run')
    if not revisions and result_pin is None:
        raise ValueError('Review requires exact revision or result binding')


def report(path: Path):
    raw = path.read_bytes()
    spec = json.loads(raw)
    if (set(spec) != {'schema', 'subject', 'gold', 'criteria', 'phases', 'measurements'}
            or spec['schema'] != 'dmb_ingestion_assessment_v1'):
        raise ValueError('Unsupported assessment format')
    subject = spec['subject']
    if set(subject) != {'result', 'candidate'}:
        raise ValueError('Assessment requires actual result and candidate pins')
    run = reference(subject['result'])
    read_pin(subject['candidate'])
    if run['components']['candidate_graph']['sha256'] != subject['candidate']['sha256']:
        raise ValueError('Assessment candidate differs from actual run')
    if not spec['gold']:
        raise ValueError('Assessment requires pinned Gold authority')
    gold_hashes = set()
    for pin in spec['gold']:
        read_pin(pin)
        gold_hashes.add(pin['sha256'])
    criteria = {}
    gold_references = set()
    for criterion in spec['criteria']:
        if set(criterion) != {'criterion_id', 'dimension', 'gold'}:
            raise ValueError('Criterion requires ID, dimension and exact Gold reference')
        cid = criterion['criterion_id']
        if not isinstance(cid, str) or not cid or cid in criteria:
            raise ValueError('Criteria require unique nonempty IDs')
        if not isinstance(criterion['dimension'], str) or not criterion['dimension']:
            raise ValueError('Criterion requires a dimension')
        ref = criterion['gold']
        if ref['artifact']['sha256'] not in gold_hashes:
            raise ValueError('Criterion is outside declared Gold authority')
        value = reference(ref)
        identifiers = ([value[k] for k in ('claim_id', 'check_id', 'criterion_id', 'constraint_id', 'id') if k in value]
                       if isinstance(value, dict) else [])
        if ((identifiers and cid not in identifiers)
                or not isinstance(value, (dict, str)) or not value):
            raise ValueError('Gold object does not identify this criterion')
        # Legacy constraints may have no intrinsic ID. Preserve their exact
        # Gold pointer rather than inventing a second Gold representation.
        identity = (ref['artifact']['sha256'], ref['pointer'])
        if identity in gold_references:
            raise ValueError('Duplicate Gold reference would inflate the denominator')
        gold_references.add(identity)
        criteria[cid] = criterion
    if not criteria or set(spec['phases']) != set(PHASES):
        raise ValueError('Assessment requires criteria and all three explicit phases')
    phases = {}
    for name in PHASES:
        phase = spec['phases'][name]
        if unknown(phase):
            phases[name] = phase
            continue
        if (set(phase) != {'judgments', 'phase_evidence', 'limitations'} or not phase['phase_evidence']
                or not isinstance(phase['limitations'], list)
                or any(not isinstance(v, str) or not v.strip() for v in phase['limitations'])):
            raise ValueError('Assessed phase requires retained phase evidence')
        for pin in phase['phase_evidence']:
            read_pin(pin)
        judgments = {}
        for judgment in phase['judgments']:
            if set(judgment) != {'criterion_id', 'outcome', 'review', 'evidence', 'reason'}:
                raise ValueError('Judgment requires explicit outcome, review, evidence and reason')
            cid = judgment['criterion_id']
            if cid not in criteria or cid in judgments or judgment['outcome'] not in OUTCOMES:
                raise ValueError('Invalid, duplicate or undeclared judgment')
            if not isinstance(judgment['reason'], str) or not judgment['reason'].strip():
                raise ValueError('Judgment requires a reason')
            review = reference(judgment['review'])
            review_document = json.loads(read_pin(judgment['review']['artifact']))
            bind_review(review_document, run, subject)
            if not isinstance(review, dict) or review.get('criterion_id') != cid:
                raise ValueError(f'Review does not identify this criterion: {cid}')
            for field in ('outcome', 'reason', 'evidence'):
                if field not in review or review[field] != judgment[field]:
                    raise ValueError(f'Review judgment differs for {cid}: {field}; '
                                     'an explicit matching canonical review row is required')
            if judgment['outcome'] != 'unknown' and not judgment['evidence']:
                raise ValueError('Known judgments require inspectable evidence')
            for ref in judgment['evidence']:
                reference(ref)
            judgments[cid] = judgment
        if set(judgments) != set(criteria):
            raise ValueError('Every declared criterion requires a judgment, including unknowns')
        counts = defaultdict(Counter)
        for cid, judgment in judgments.items():
            counts[criteria[cid]['dimension']][judgment['outcome']] += 1
        phases[name] = {'status': 'assessed', 'criterion_count': len(criteria),
                        'limitations': phase['limitations'], 'phase_evidence': phase['phase_evidence'],
                        'by_dimension': {d: {outcome: c[outcome] for outcome in sorted(OUTCOMES)}
                                         for d, c in sorted(counts.items())}}
    if set(spec['measurements']) != METRICS:
        raise ValueError('All standard measurements must be explicit, including unknowns')
    measurements = {}
    for metric, measurement in spec['measurements'].items():
        if unknown(measurement):
            measurements[metric] = measurement
        else:
            value = reference(measurement)
            if type(value) not in (int, float) or value < 0 or not math.isfinite(value):
                raise ValueError('Measured values must be finite nonnegative numbers; missing is unknown')
            measurements[metric] = {'value': value, 'evidence': measurement}
    return {'schema': 'dmb_ingestion_assessment_report_v1', 'assessment_sha256': digest(raw),
            'run_id': run['run_id'], 'candidate_sha256': subject['candidate']['sha256'],
            'phases': phases, 'measurements': measurements,
            'scope': 'Counts of explicitly reviewed judgments; criterion completeness and semantic truth require independent review. No publication authorization.'}
