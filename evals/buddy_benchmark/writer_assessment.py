"""Native writer-judge contract and offline calibration; never product acceptance."""
from copy import deepcopy

AXES = ('completeness', 'grounding', 'attribution', 'chronology', 'citation_support', 'directness', 'prose')
JUDGMENTS = ('pass', 'fail', 'unknown')


def _object(properties):
    return {'type': 'object', 'properties': properties, 'required': list(properties), 'additionalProperties': False}


def quality_schema(candidate_ids, concept_ids):
    dimension = _object({'judgment': {'type': 'string', 'enum': list(JUDGMENTS)},
        'reason': {'type': 'string'}, 'segment_indices': {'type': 'array', 'items': {'type': 'integer', 'minimum': 0}},
        'support_handles': {'type': 'array', 'items': {'type': 'string'}}})
    case = _object({'candidate_id': {'type': 'string', 'enum': list(candidate_ids)},
        'covered_concepts': {'type': 'array', 'items': {'type': 'string', 'enum': list(concept_ids)}},
        'dimensions': _object({axis: deepcopy(dimension) for axis in AXES})})
    return _object({'assessments': {'type': 'array', 'items': case,
        'minItems': len(candidate_ids), 'maxItems': len(candidate_ids)}})


def validate_judge_inputs(candidates, reference, schema):
    if (not isinstance(candidates, list) or not candidates
            or any(not isinstance(c, dict) or set(c) != {'candidate_id', 'answer'}
                or not isinstance(c['candidate_id'], str) or not c['candidate_id'].strip()
                or not isinstance(c['answer'], dict)
                or set(c['answer']) != {'answer_segments', 'limitations', 'requested_detail_gaps'}
                or not all(isinstance(c['answer'][key], list) for key in c['answer']) for c in candidates)):
        raise ValueError('Judge candidates require blind local IDs and semantic answers only')
    ids = [c['candidate_id'] for c in candidates]
    if len(ids) != len(set(ids)):
        raise ValueError('Repeated judge candidate')
    if (not isinstance(reference, dict) or set(reference) != {'required_concepts'}
            or not isinstance(reference['required_concepts'], list) or not reference['required_concepts']
            or any(not isinstance(c, dict) or set(c) != {'id', 'description'}
                or any(not isinstance(c[key], str) or not c[key].strip() for key in c)
                for c in reference['required_concepts'])):
        raise ValueError('Judge reference contains criteria, never expected candidate grades')
    concepts = [c['id'] for c in reference['required_concepts']]
    if len(concepts) != len(set(concepts)) or schema != quality_schema(ids, concepts):
        raise ValueError('Judge schema differs from pinned candidates/reference')


def calibration_report(expected, actual):
    """Compare explicit reviewed axes; unknown human judgments never count as pass."""
    import jsonschema
    cases = expected['cases']
    ids = [c['candidate_id'] for c in cases]
    concepts = expected['required_concepts']
    if not ids or len(ids) != len(set(ids)) or len(concepts) != len(set(concepts)):
        raise ValueError('Invalid calibration reference identities')
    jsonschema.validate(actual, quality_schema(ids, concepts))
    judgments = {c['candidate_id']: c for c in actual['assessments']}
    if len(judgments) != len(actual['assessments']) or set(judgments) != set(ids):
        raise ValueError('Judge must assess every candidate exactly once')
    totals = {axis: {'reviewed': 0, 'agreements': 0, 'false_passes': 0,
                     'false_failures': 0, 'abstentions': 0} for axis in AXES}
    differences, inconsistencies = [], []
    for case in cases:
        if set(case['axes']) != set(AXES) or any(v not in JUDGMENTS for v in case['axes'].values()):
            raise ValueError('Calibration requires explicit reviewed or unknown axes')
        observed = judgments[case['candidate_id']]
        covered = observed['covered_concepts']
        if len(covered) != len(set(covered)):
            inconsistencies.append({'candidate_id': case['candidate_id'], 'reason': 'duplicate covered concepts'})
        if ((set(covered) == set(concepts)) != (observed['dimensions']['completeness']['judgment'] == 'pass')
                and observed['dimensions']['completeness']['judgment'] != 'unknown'):
            inconsistencies.append({'candidate_id': case['candidate_id'], 'reason': 'coverage/completeness disagreement'})
        for axis, human in case['axes'].items():
            if human == 'unknown':
                continue
            judge = observed['dimensions'][axis]['judgment']
            count = totals[axis]
            count['reviewed'] += 1
            count['agreements'] += human == judge
            count['false_passes'] += human == 'fail' and judge == 'pass'
            count['false_failures'] += human == 'pass' and judge == 'fail'
            count['abstentions'] += judge == 'unknown'
            if human != judge:
                differences.append({'candidate_id': case['candidate_id'], 'axis': axis,
                                    'reviewed': human, 'judge': judge})
    return {'schema': 'dmb_writer_judge_calibration_v1', 'axes': totals,
        'disagreements': differences, 'internal_inconsistencies': inconsistencies,
        'trusted_for_autograding': False,
        'limits': 'Descriptive calibration only. Human taste is not inferred; unknown reference axes are unscored.'}
