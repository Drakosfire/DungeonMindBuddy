"""One mechanical precision-review contract; independent semantics stay explicit."""
from __future__ import annotations

import math

from jsonschema import Draft202012Validator

from .runner import encoded

PROFILE = 'dmb_blinded_ingestion_review_v2'
CONTRACT = 'dmb_ingestion_review_precision_contract_v1'
PRECISION_FIELDS = frozenset({
    'produced_output_precision_inventory', 'precision_inventory_complete',
    'severe_propositions', 'severe_proposition_count', 'severe_count_status',
    'intervention_targets', 'unique_intervention_target_count',
    'intervention_count_status', 'count_uncertainties',
})
TEXT = {'type': 'string', 'pattern': r'\S'}
PIN = {'type': 'object', 'additionalProperties': False,
       'required': ['path', 'sha256'], 'properties': {
           'path': TEXT, 'sha256': {'type': 'string', 'pattern': '^[0-9a-f]{64}$'}}}
REF = {'type': 'object', 'additionalProperties': False,
       'required': ['artifact', 'pointer'], 'properties': {
           'artifact': PIN, 'pointer': {'type': 'string', 'pattern': '^(/.*)?$'}}}
EVIDENCE = {'type': 'array', 'items': REF}
UNCERTAINTIES = {'type': 'array', 'items': {
    'type': 'object', 'additionalProperties': False, 'required': ['reason', 'evidence'],
    'properties': {'reason': TEXT, 'evidence': {**EVIDENCE, 'minItems': 1}}}}
COUNT_STATUS = {'enum': ['complete', 'confirmed_lower_bound', 'incomplete_inventory']}
SCHEMA = {'type': 'object', 'additionalProperties': True, 'properties': {
    'schema': {'const': PROFILE}, 'trial_id': TEXT, 'run_id': TEXT,
    'revision': {'type': 'integer', 'minimum': 1},
    'candidate_sha256': {'type': 'string', 'pattern': '^[0-9a-f]{64}$'},
    'review_started_at': TEXT, 'review_finished_at': TEXT,
    'review_wall_seconds': {'type': 'number', 'minimum': 0},
    'human_review_minutes': {'type': 'null'},
    'judgments': {'type': 'array', 'minItems': 1, 'items': {
        'type': 'object', 'required': ['criterion_id', 'outcome', 'reason', 'evidence'],
        'properties': {'criterion_id': TEXT, 'reason': TEXT, 'evidence': EVIDENCE,
                       'outcome': {'enum': ['pass', 'fail', 'partial', 'unknown']}}}},
    'produced_output_precision_inventory': {'type': 'array', 'minItems': 1,
                                           'items': {'type': 'object'}},
    'precision_inventory_complete': {'type': 'boolean'},
    'severe_proposition_count': {'type': 'integer', 'minimum': 0},
    'severe_count_status': COUNT_STATUS,
    'severe_propositions': {'type': 'array', 'items': {
        'type': 'object', 'required': ['proposition', 'severity', 'evidence'],
        'properties': {'proposition': TEXT, 'severity': {'const': 'severe_semantic'},
                       'evidence': {**EVIDENCE, 'minItems': 1}}}},
    'unique_intervention_target_count': {'type': 'integer', 'minimum': 0},
    'intervention_count_status': COUNT_STATUS,
    'intervention_targets': {'type': 'array', 'items': {
        'type': 'object', 'required': ['kind', 'item_id', 'field_name', 'actions', 'reason', 'evidence'],
        'properties': {'kind': {'enum': ['node', 'edge', 'beat', 'disposition']},
                       'item_id': TEXT, 'field_name': TEXT, 'reason': TEXT,
                       'actions': {'type': 'array', 'minItems': 1, 'items': {'enum': [
                           'hold', 'select_exact_extent', 'correct_type', 'resolve_identity']}},
                       'evidence': {**EVIDENCE, 'minItems': 1}}}},
    'count_uncertainties': {'type': 'object', 'additionalProperties': False,
                            'required': ['severe_propositions', 'intervention_targets'],
                            'properties': {'severe_propositions': UNCERTAINTIES,
                                           'intervention_targets': UNCERTAINTIES}},
    'output_contracts': {'type': 'array', 'minItems': 1, 'items': PIN},
    'unknowns': {'type': 'array', 'items': TEXT},
    'limits': {'type': 'array', 'items': TEXT},
}}
SCHEMA['required'] = list(SCHEMA['properties'])
VALIDATOR = Draft202012Validator(SCHEMA)
REFERENCE_VALIDATOR = Draft202012Validator(REF)
PIN_VALIDATOR = Draft202012Validator(PIN)


def _check(validator, value):
    error = next(validator.iter_errors(value), None)
    if error is not None:
        path = '/' + '/'.join(str(x) for x in error.absolute_path)
        raise ValueError(f'Review precision contract invalid at {path} ({error.validator})')


def precision(document, *, resolve_reference, verify_pin, require_full=False):
    """Validate one document, never follow its references into an evidence graph.

    Callbacks reuse the existing strict reference and pin owners without an
    assessment/review import cycle. Inspection, materiality and equivalence are
    still reviewer claims, not mechanically certified source truth.
    """
    if not isinstance(document, dict):
        raise ValueError('Precision review must be a JSON object')
    if document.get('schema') != PROFILE:
        if require_full or PRECISION_FIELDS.intersection(document):
            raise ValueError('Explicit supported precision-review profile required')
        return {'status': 'unknown', 'reason': 'No declared whole-output precision review'}
    _check(VALIDATOR, document)
    if not math.isfinite(document['review_wall_seconds']):
        raise ValueError('Review wall seconds must be finite; never human minutes')
    judgments = {row['criterion_id']: f'/judgments/{index}'
                 for index, row in enumerate(document['judgments'])}
    if len(judgments) != len(document['judgments']):
        raise ValueError('Duplicate precision-review criterion ID')
    for records, count, status in (
        ('severe_propositions', 'severe_proposition_count', 'severe_count_status'),
        ('intervention_targets', 'unique_intervention_target_count', 'intervention_count_status'),
    ):
        if document[count] != len(document[records]):
            raise ValueError(f'Review precision count differs from confirmed records: {count}')
        expected = ('incomplete_inventory' if not document['precision_inventory_complete']
                    else 'confirmed_lower_bound' if document['count_uncertainties'][records]
                    else 'complete')
        if document[status] != expected:
            raise ValueError(f'Review precision status contradicts inventory/uncertainty: {status}')
    severe = document['severe_propositions']
    if len({encoded(row) for row in severe}) != len(severe):
        raise ValueError('Duplicate severe proposition record')
    targets = document['intervention_targets']
    if len({(r['kind'], r['item_id'], r['field_name']) for r in targets}) != len(targets):
        raise ValueError('Duplicate intervention target triple')

    references, pins = set(), set()

    def inspect(value, location=()):
        if isinstance(value, dict):
            # An artifact marker declares a formal reference. Naked or decoded
            # selectors are annotations, not qualified evidence or executable code.
            if 'artifact' in value:
                _check(REFERENCE_VALIDATOR, value)
                identity = encoded(value)
                if identity not in references:
                    try:
                        resolve_reference(value)
                    except (ValueError, KeyError, IndexError, OSError) as exc:
                        where = '/' + '/'.join(str(x) for x in location)
                        raise ValueError(f'Review evidence reference invalid at {where}') from exc
                    references.add(identity)
                return  # Never traverse the referenced document or its result.
            if set(value) == {'path', 'sha256'}:
                _check(PIN_VALIDATOR, value)
                identity = encoded(value)
                if identity not in pins:
                    verify_pin(value)
                    pins.add(identity)
                return
            for key, child in value.items():
                inspect(child, (*location, key))
        elif isinstance(value, list):
            for index, child in enumerate(value):
                inspect(child, (*location, index))

    inspect(document)
    fields = ('precision_inventory_complete', 'severe_proposition_count', 'severe_count_status',
              'unique_intervention_target_count', 'intervention_count_status',
              'count_uncertainties', 'output_contracts', 'unknowns', 'limits')
    return {'status': 'reported', 'contract': CONTRACT,
            **{key: document[key] for key in fields},
            'judgment_pointers': judgments,
            'validated_formal_references': len(references), 'validated_pins': len(pins),
            'scope': 'Document-level mechanical consistency, not semantic truth, '
                     'criterion completeness, phase execution or adoption. '
                     'Zero lower-bound findings do not establish zero actual defects.'}
