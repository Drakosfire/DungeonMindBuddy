"""Shared review mechanics refuse fabricated completeness without new grading."""
import copy
import json
from pathlib import Path
import subprocess
import sys

import pytest

from ingestion_evaluation.assessment import reference_resolver, report
from ingestion_evaluation.assembly import assemble
from ingestion_evaluation.comparison import compare
from ingestion_evaluation.review import PROFILE, precision
from ingestion_evaluation.runner import digest, read_pin
from tests.test_ingestion_evaluation_assessment import assessment
from tests.test_ingestion_evaluation_assembly import inputs
from tests.test_ingestion_evaluation_comparison import paired


def full_review(original, rows, owner):
    """A fixture, not a legacy status mapper or semantic reviewer."""
    return {**copy.deepcopy(original), 'schema': PROFILE, 'trial_id': 'opaque',
            'review_started_at': '2026-11-07T00:00:00Z',
            'review_finished_at': '2026-11-07T00:00:02Z',
            'review_wall_seconds': 2.0, 'human_review_minutes': None,
            'judgments': [{k: copy.deepcopy(row[k]) for k in
                           ('criterion_id', 'outcome', 'reason', 'evidence')} for row in rows],
            'produced_output_precision_inventory': [{'scope': 'Fixture field inventory'}],
            'precision_inventory_complete': True, 'severe_propositions': [],
            'severe_proposition_count': 0, 'severe_count_status': 'complete',
            'intervention_targets': [], 'unique_intervention_target_count': 0,
            'intervention_count_status': 'complete',
            'count_uncertainties': {'severe_propositions': [], 'intervention_targets': []},
            'output_contracts': [owner], 'unknowns': [], 'limits': []}


@pytest.fixture
def reviewed(assessment):
    spec, save, put = assessment
    row = spec['phases']['raw_extraction']['judgments'][0]
    original = json.loads(Path(row['review']['artifact']['path']).read_text())
    owner = put('owner.json', {'semantics': 'Fixture contract only'})
    doc = full_review(original, [row], owner)

    def adopt():
        pin = put('precision-review.json', doc)
        for phase in spec['phases'].values():
            if 'judgments' in phase:
                phase['phase_evidence'] = [pin]
                for judgment in phase['judgments']:
                    judgment['review'] = {'artifact': pin, 'pointer': '/judgments/0'}
        return save()

    return spec, doc, adopt, put


def checked(doc, *, require_full=True):
    return precision(doc, require_full=require_full, verify_pin=read_pin,
                     resolve_reference=reference_resolver())


def test_actual_cli_and_report_share_document_contract(reviewed):
    spec, doc, adopt, _ = reviewed
    spec['phases']['reviewed_output'] = copy.deepcopy(spec['phases']['raw_extraction'])
    result = report(adopt())
    records = result['review_document_precision']
    assert len(records) == 1
    assert records[0]['used_by_phases'] == ['raw_extraction', 'reviewed_output']
    assert records[0]['precision']['severe_proposition_count'] == 0
    assert 'phase execution' in records[0]['precision']['scope']
    assert result['measurements']['review_effort_minutes']['status'] == 'unknown'
    pin = spec['phases']['raw_extraction']['judgments'][0]['review']['artifact']
    cli = Path(__file__).resolve().parents[1] / 'scripts/evaluate_ingestion.py'
    process = subprocess.run([sys.executable, str(cli), 'review-validate', '--review', pin['path']],
                             check=True, capture_output=True, text=True)
    standalone = json.loads(process.stdout)
    assert standalone['precision'] == records[0]['precision']
    assert 'actual-result binding' in standalone['scope']


@pytest.mark.parametrize('metric', ['severe_propositions', 'intervention_targets'])
def test_uncertainty_status_is_per_metric_and_zero_is_not_clean(reviewed, metric):
    _, doc, _, _ = reviewed
    evidence = doc['judgments'][0]['evidence']
    doc['count_uncertainties'][metric] = [{'reason': 'Equivalence unresolved', 'evidence': evidence}]
    status = 'severe_count_status' if metric == 'severe_propositions' else 'intervention_count_status'
    doc[status] = 'confirmed_lower_bound'
    result = checked(doc)
    assert result[status] == 'confirmed_lower_bound'
    assert 'do not establish zero actual defects' in result['scope']
    other = 'intervention_count_status' if metric == 'severe_propositions' else 'severe_count_status'
    assert result[other] == 'complete'
    doc[status] = 'complete'
    with pytest.raises(ValueError, match='status contradicts'):
        checked(doc)


def test_incomplete_inspection_requires_both_incomplete_counts(reviewed):
    _, doc, _, _ = reviewed
    doc['precision_inventory_complete'] = False
    for field in ('severe_count_status', 'intervention_count_status'):
        with pytest.raises(ValueError, match='status contradicts'):
            checked(doc)
        doc[field] = 'incomplete_inventory'
    assert checked(doc)['severe_count_status'] == 'incomplete_inventory'


@pytest.mark.parametrize('field,value', [
    ('severe_proposition_count', 1), ('unique_intervention_target_count', 1),
    ('human_review_minutes', 2), ('review_wall_seconds', float('nan')),
    ('review_wall_seconds', float('inf')), ('severe_proposition_count', True),
])
def test_false_counts_and_automated_human_minutes_rejected(reviewed, field, value):
    _, doc, _, _ = reviewed
    doc[field] = value
    with pytest.raises(ValueError):
        checked(doc)


def test_exact_record_and_target_duplicates_rejected(reviewed):
    _, doc, _, _ = reviewed
    evidence = doc['judgments'][0]['evidence']
    severe = {'proposition': 'A source-unsupported assertion', 'severity': 'severe_semantic',
              'evidence': evidence, 'all_occurrence_selectors': evidence}
    doc['severe_propositions'] = [severe, copy.deepcopy(severe)]
    doc['severe_proposition_count'] = 2
    with pytest.raises(ValueError, match='Duplicate severe'):
        checked(doc)
    doc['severe_propositions'].pop()
    doc['severe_proposition_count'] = 1
    target = {'kind': 'node', 'item_id': 'N1', 'field_name': 'label', 'actions': ['hold'],
              'reason': 'Unsupported assertion', 'evidence': evidence}
    doc['intervention_targets'] = [target, {**target, 'reason': 'Another explanation'}]
    doc['unique_intervention_target_count'] = 2
    with pytest.raises(ValueError, match='Duplicate intervention'):
        checked(doc)
    doc['intervention_targets'].pop()
    doc['unique_intervention_target_count'] = 1
    assert checked(doc)['unique_intervention_target_count'] == 1
    doc['intervention_targets'][0]['actions'] = []
    with pytest.raises(ValueError, match='contract invalid'):
        checked(doc)


@pytest.mark.parametrize('value', [None, [], True, 'not an object'])
def test_standalone_review_requires_an_object(value):
    with pytest.raises(ValueError, match='must be a JSON object'):
        checked(value)


def test_review_cli_refuses_unrelated_operational_flags(reviewed):
    spec, _, adopt, _ = reviewed
    adopt()
    pin = spec['phases']['raw_extraction']['judgments'][0]['review']['artifact']
    cli = Path(__file__).resolve().parents[1] / 'scripts/evaluate_ingestion.py'
    result = subprocess.run([sys.executable, str(cli), 'review-validate', '--review', pin['path'],
                             '--qualification-sha', 'not-an-execution'],
                            capture_output=True, text=True)
    assert result.returncode != 0
    assert 'requires only --review' in result.stderr


@pytest.mark.parametrize('mutation', ['unknown_profile', 'missing_profile', 'missing_counter',
    'missing_artifact', 'extra_ref_key', 'dangling_pointer', 'bad_pin', 'duplicate_id'])
def test_profile_and_formal_reference_failures(reviewed, mutation):
    _, doc, _, _ = reviewed
    ref = doc['judgments'][0]['evidence'][0]
    if mutation == 'unknown_profile': doc['schema'] = 'unadopted-profile'
    elif mutation == 'missing_profile': del doc['schema']
    elif mutation == 'missing_counter': del doc['severe_proposition_count']
    elif mutation == 'missing_artifact': del ref['artifact']
    elif mutation == 'extra_ref_key': ref['decoded_inner_locator'] = '/parsed/field'
    elif mutation == 'dangling_pointer': ref['pointer'] = '/not-present'
    elif mutation == 'bad_pin': doc['output_contracts'][0]['sha256'] = '0' * 64
    elif mutation == 'duplicate_id': doc['judgments'].append(copy.deepcopy(doc['judgments'][0]))
    with pytest.raises((ValueError, KeyError)):
        checked(doc)


def test_annotations_preserved_and_referenced_graph_not_traversed(reviewed):
    _, doc, _, put = reviewed
    nested = put('referenced.json', {'nested': {'artifact': {'path': '/never/opened',
        'sha256': '0' * 64}, 'pointer': ''}})
    doc['produced_output_precision_inventory'][0].update(
        evidence=[{'artifact': nested, 'pointer': ''}],
        decoded_inner_locator='/parsed/annotation',
        decoded_selector={'pointer': '/not-a-formal-reference', 'response_index': 0})
    before = copy.deepcopy(doc)
    assert checked(doc)['validated_formal_references'] >= 2
    assert doc == before


def test_reference_format_error_names_location_and_preserves_cause(reviewed):
    _, doc, _, put = reviewed
    pin = put('not-json.txt', {})
    path = Path(pin['path'])
    path.write_text('Retained Markdown text')
    pin['sha256'] = digest(path.read_bytes())
    doc['produced_output_precision_inventory'][0]['evidence'] = [
        {'artifact': pin, 'pointer': ''}]
    with pytest.raises(ValueError, match='/produced_output_precision_inventory/0/evidence/0') as caught:
        checked(doc)
    assert isinstance(caught.value.__cause__, json.JSONDecodeError)


def test_coverage_only_precision_is_unknown_without_silent_profile_fallback(assessment):
    spec, save, _ = assessment
    result = report(save())
    assert result['review_document_precision'][0]['precision']['status'] == 'unknown'
    row = spec['phases']['raw_extraction']['judgments'][0]
    doc = json.loads(Path(row['review']['artifact']['path']).read_text())
    with pytest.raises(ValueError, match='profile required'):
        checked(doc)
    # General annotations alone do not assert precision completeness.
    assert checked({**doc, 'unknowns': ['Unresolved meaning'], 'limits': []},
                   require_full=False)['status'] == 'unknown'


def test_report_refuses_canonical_looking_annotation_instead_of_judgment(reviewed):
    spec, doc, adopt, put = reviewed
    path = adopt()
    doc['annotation'] = copy.deepcopy(doc['judgments'][0])
    pin = put('annotation-review.json', doc)
    spec['phases']['raw_extraction']['judgments'][0]['review'] = {
        'artifact': pin, 'pointer': '/annotation'}
    path.write_text(json.dumps(spec))
    with pytest.raises(ValueError, match='canonical judgment binding'):
        report(path)


def test_report_refuses_undeclared_extra_full_review_criterion(reviewed):
    _, doc, adopt, _ = reviewed
    doc['judgments'].append({**doc['judgments'][0], 'criterion_id': 'NOT_IN_GOLD'})
    with pytest.raises(ValueError, match='canonical judgment binding'):
        report(adopt())


def test_standalone_mechanics_do_not_establish_actual_result_binding(reviewed):
    _, doc, adopt, _ = reviewed
    doc['run_id'] = 'another-run'
    assert checked(doc)['status'] == 'reported'
    with pytest.raises(ValueError, match='another or unspecified run'):
        report(adopt())


def test_verified_json_cache_is_local_to_each_report_invocation(reviewed):
    _, doc, adopt, put = reviewed
    side = put('side-evidence.json', {'value': 1})
    doc['produced_output_precision_inventory'][0]['evidence'] = [
        {'artifact': side, 'pointer': '/value'}]
    path = adopt()
    report(path)
    Path(side['path']).write_text('{"value": 2}')
    with pytest.raises(ValueError, match='Review evidence reference invalid') as caught:
        report(path)
    assert 'Pin mismatch' in str(caught.value.__cause__)


def test_assembly_reuses_contract_and_leaves_no_output_on_failure(inputs, tmp_path):
    old = json.loads(inputs['review'].read_text())
    owner = tmp_path / 'owner.json'
    owner.write_text('{}')
    doc = full_review(old, old['judgments'], {'path': str(owner), 'sha256': digest(owner.read_bytes())})
    doc['severe_proposition_count'] = 1
    inputs['review'].write_text(json.dumps(doc))
    out = tmp_path / 'invalid-assembly'
    with pytest.raises(ValueError, match='count differs'):
        assemble(inputs['criteria'], inputs['result'], inputs['review'], out)
    assert not out.exists()


def test_comparison_reuses_same_precision_owner(paired, tmp_path):
    spec, save, put = paired
    pair = spec['pairs'][0]
    assessment_doc = json.loads(Path(pair['variant']['path']).read_text())
    row = assessment_doc['phases']['raw_extraction']['judgments'][0]
    old = json.loads(Path(row['review']['artifact']['path']).read_text())
    doc = full_review(old, [row], put('owner.json', {}))
    doc['severe_proposition_count'] = 1
    pin = put('bad-precision-review.json', doc)
    row['review'] = {'artifact': pin, 'pointer': '/judgments/0'}
    assessment_doc['phases']['raw_extraction']['phase_evidence'] = [pin]
    pair['variant'] = put('bad-precision-assessment.json', assessment_doc)
    with pytest.raises(ValueError, match='count differs'):
        compare(save())
