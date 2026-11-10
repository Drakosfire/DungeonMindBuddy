from copy import deepcopy

import pytest

from evals.buddy_benchmark.writer_assessment import AXES, calibration_report, quality_schema, validate_judge_inputs


def inputs():
    return ([{'candidate_id': 'sample0', 'answer': {'answer_segments': [], 'limitations': [], 'requested_detail_gaps': []}}],
            {'required_concepts': [{'id': 'concept0', 'description': 'A required source-supported detail.'}]})


def native_answer_schema():
    return {'type': 'object', 'properties': {'schema': {'type': 'string', 'const': 'native_answer'},
        'answer_segments': {'type': 'array', 'items': {'type': 'object', 'properties': {'text': {'type': 'string'}},
            'required': ['text'], 'additionalProperties': False}},
        'limitations': {'type': 'array', 'items': {'type': 'string'}},
        'requested_detail_gaps': {'type': 'array', 'items': {'type': 'string'}}},
        'required': ['schema', 'answer_segments', 'limitations', 'requested_detail_gaps'], 'additionalProperties': False}


@pytest.mark.parametrize('corrupt', [None, 'identity', 'grades', 'schema', 'repeat', 'nested', 'limitation'])
def test_judge_input_contract_excludes_hidden_grades_and_provider_identity(corrupt):
    candidates, reference = inputs()
    schema = quality_schema(['sample0'], ['concept0'])
    if corrupt == 'identity': candidates[0]['model'] = 'hidden identity'
    elif corrupt == 'grades': reference['expected_grades'] = {'sample0': 'pass'}
    elif corrupt == 'schema': schema['properties'] = {}
    elif corrupt == 'repeat': candidates.append(deepcopy(candidates[0]))
    elif corrupt == 'nested': candidates[0]['answer']['answer_segments'] = [{'text': 'A claim', 'model': 'hidden', 'expected_grades': {}}]
    elif corrupt == 'limitation': candidates[0]['answer']['limitations'] = [{'human_expected_grade': 'fail'}]
    if corrupt:
        with pytest.raises(ValueError): validate_judge_inputs(candidates, reference, schema, answer_schema=native_answer_schema())
    else:
        validate_judge_inputs(candidates, reference, schema, answer_schema=native_answer_schema())


def test_calibration_counts_false_passes_failures_abstention_and_unknown_reference_separately():
    expected = {'required_concepts': ['concept0'], 'cases': [
        {'candidate_id': 'sample0', 'axes': {axis: 'unknown' for axis in AXES}}]}
    expected['cases'][0]['axes'].update(completeness='pass', grounding='fail', chronology='pass', citation_support='fail')
    actual = {'assessments': [{'candidate_id': 'sample0', 'covered_concepts': [],
        'dimensions': {axis: {'judgment': 'unknown', 'reason': 'A reason.', 'segment_indices': [], 'support_handles': []}
                       for axis in AXES}}]}
    actual['assessments'][0]['dimensions']['completeness']['judgment'] = 'fail'
    actual['assessments'][0]['dimensions']['grounding']['judgment'] = 'pass'
    actual['assessments'][0]['dimensions']['citation_support']['judgment'] = 'fail'
    report = calibration_report(expected, actual)
    assert report['axes']['completeness']['false_failures'] == 1
    assert report['axes']['grounding']['false_passes'] == 1
    assert report['axes']['chronology']['abstentions'] == 1
    assert report['axes']['citation_support']['agreements'] == 1
    assert report['axes']['prose']['reviewed'] == 0
    assert report['trusted_for_autograding'] is False
    actual['assessments'][0]['dimensions']['completeness']['judgment'] = 'pass'
    assert calibration_report(expected, actual)['internal_inconsistencies']


def test_native_schema_success_does_not_substitute_for_unique_candidate_coverage():
    expected = {'required_concepts': ['concept0'], 'cases': [
        {'candidate_id': key, 'axes': {axis: 'unknown' for axis in AXES}} for key in ('sample0', 'sample1')]}
    row = {'candidate_id': 'sample0', 'covered_concepts': ['concept0'], 'dimensions': {
        axis: {'judgment': 'pass', 'reason': '', 'segment_indices': [], 'support_handles': []} for axis in AXES}}
    with pytest.raises(ValueError, match='exactly once'):
        calibration_report(expected, {'assessments': [row, deepcopy(row)]})
