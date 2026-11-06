"""Offline paired diagnostics over the one authoritative assessment format."""
from __future__ import annotations

from collections import Counter
from decimal import Decimal
import json
from pathlib import Path
from statistics import median

from .assessment import METRICS, report
from .runner import digest, encoded, read_pin


def _load(pin):
    body = read_pin(pin)
    raw = json.loads(body)
    checked = report(Path(pin['path']))
    if checked['assessment_sha256'] != digest(body):
        raise ValueError('Assessment changed during verification')
    phase = checked['phases']['raw_extraction']
    if phase.get('status') != 'assessed':
        raise ValueError('Comparison requires assessed raw extraction')
    # Paths may differ across immutable copies; authority is content plus pointer.
    contract = sorted((c['criterion_id'], c['dimension'],
                       c['gold']['artifact']['sha256'], c['gold']['pointer'])
                      for c in raw['criteria'])
    return checked, digest(encoded({'criteria': contract,
                                    'gold': sorted(p['sha256'] for p in raw['gold'])}))


def _ratio(variant, control):
    if 'value' not in variant or 'value' not in control:
        return {'status': 'unknown', 'reason': 'At least one paired measurement is unknown'}
    if control['value'] == 0:
        return {'status': 'unknown', 'reason': 'Control denominator is zero'}
    return {'value': str(Decimal(str(variant['value'])) / Decimal(str(control['value'])))}


def compare(path: Path) -> dict:
    body = path.read_bytes()
    spec = json.loads(body)
    if (set(spec) != {'schema', 'expected_cases', 'pairs_per_case', 'pairs'}
            or spec['schema'] != 'dmb_ingestion_paired_comparison_v1'):
        raise ValueError('Unsupported paired comparison format')
    expected = spec['expected_cases']
    if (not isinstance(expected, list) or not expected
            or any(not isinstance(c, str) or not c.strip() for c in expected)
            or len(set(expected)) != len(expected)
            or type(spec['pairs_per_case']) is not int or spec['pairs_per_case'] < 1):
        raise ValueError('Declare unique cases and a positive exact pair count')
    if not isinstance(spec['pairs'], list):
        raise ValueError('Pairs must be an explicit list')
    counts = Counter()
    seen_pairs, seen_runs, contracts, rows = set(), set(), {}, []
    for pair in spec['pairs']:
        if (set(pair) != {'case_id', 'pair_id', 'control', 'variant'}
                or pair['case_id'] not in expected
                or not isinstance(pair['pair_id'], str) or not pair['pair_id'].strip()):
            raise ValueError('Each pair requires declared case, unique ID and two assessment pins')
        key = (pair['case_id'], pair['pair_id'])
        if key in seen_pairs:
            raise ValueError('Duplicate pair')
        seen_pairs.add(key)
        counts[pair['case_id']] += 1
        c, cs = _load(pair['control'])
        v, vs = _load(pair['variant'])
        if cs != vs or contracts.get(pair['case_id'], cs) != cs:
            raise ValueError('Gold/criterion contract differs within case')
        contracts[pair['case_id']] = cs
        for item in (c, v):
            if item['run_id'] in seen_runs:
                raise ValueError('A run cannot be reused across paired observations')
            seen_runs.add(item['run_id'])
        dimensions = {}
        for dim, vc in v['phases']['raw_extraction']['by_dimension'].items():
            cc = c['phases']['raw_extraction']['by_dimension'][dim]
            dimensions[dim] = {
                'variant_counts': vc, 'control_counts': cc,
                'delta_pass': vc['pass'] - cc['pass'],
                'delta_fail': vc['fail'] - cc['fail'],
                'delta_pass_bounds': [vc['pass'] - cc['pass'] - cc['unknown'],
                                      vc['pass'] + vc['unknown'] - cc['pass']],
                'delta_fail_bounds': [vc['fail'] - cc['fail'] - cc['unknown'],
                                      vc['fail'] + vc['unknown'] - cc['fail']],
            }
        rows.append({**pair, 'control_report': c, 'variant_report': v, 'dimensions': dimensions,
                     'measurement_ratios': {m: _ratio(v['measurements'][m], c['measurements'][m])
                                            for m in sorted(METRICS)}})
    if set(counts) != set(expected) or any(n != spec['pairs_per_case'] for n in counts.values()):
        raise ValueError('All declared cases and exact pair counts are required')
    cases = {}
    for case in expected:
        subset = [r for r in rows if r['case_id'] == case]
        dims = {}
        for dim in subset[0]['dimensions']:
            ds = [r['dimensions'][dim] for r in subset]
            pb = [median([d['delta_pass_bounds'][i] for d in ds]) for i in (0, 1)]
            fb = [median([d['delta_fail_bounds'][i] for d in ds]) for i in (0, 1)]
            status = ('fails_even_with_favorable_unknowns' if pb[1] < 0 or fb[0] > 0
                      else 'count_nonregression_under_all_unknown_outcomes'
                      if pb[0] >= 0 and fb[1] <= 0 else 'unknowns_can_change_count_gate')
            dims[dim] = {'median_delta_pass': median([d['delta_pass'] for d in ds]),
                         'median_delta_fail': median([d['delta_fail'] for d in ds]),
                         'median_pass_bounds': pb, 'median_fail_bounds': fb, 'count_gate': status}
        metrics = {}
        for metric in sorted(METRICS):
            values = [r['measurement_ratios'][metric] for r in subset]
            if any('value' not in v for v in values):
                metrics[metric] = {'status': 'unknown', 'reason': 'Incomplete paired measurements; no available-case median',
                                   'pairs': values}
            else:
                numbers = [Decimal(v['value']) for v in values]
                metrics[metric] = {'pairs': values, 'median_ratio': str(median(numbers)),
                                   'min_ratio': str(min(numbers)), 'max_ratio': str(max(numbers))}
        cases[case] = {'pair_count': len(subset), 'dimensions': dims, 'measurements': metrics}
    return {'schema': 'dmb_ingestion_paired_diagnostics_v1', 'spec_sha256': digest(body),
            'pairs': rows, 'cases': cases,
            'scope': 'Paired reviewed-count and measurement diagnostics, not semantic truth or adoption. '
                     'No pooled cases, precision certification, severe-claim veto or significance inference. '
                     'Matching Gold/criteria alone does not prove identical review semantics. '
                     'Inspect pinned reviews/limitations and the experiment contract separately.'}
