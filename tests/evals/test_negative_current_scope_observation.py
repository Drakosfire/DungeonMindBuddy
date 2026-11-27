"""The negative benchmark treats current-page scope as an unvalidated vote."""
import json

import pytest

from evals.negative_retrieval.trace_observation import controller_observations, observed_acquisitions


@pytest.mark.parametrize(('choice', 'expected'), [
    ('current_saved_page', 'current_saved_page'),
    ('anchored', 'anchored'), ('source_lookup', 'source_lookup'), ('uncertain', 'uncertain'),
    ('private untrusted text', 'other_or_invalid'), (None, 'other_or_invalid'),
])
def test_source_scope_projection_never_implies_an_admitted_decision_or_read(choice, expected):
    response = {'answers': {'source_need': {'selected': choice}}}
    trace = {'schema': 'dmb_turn_context_trace_v1', 'observations': [{
        'sequence': 0, 'kind': 'context_snapshot', 'snapshot_kind': 'provider_response', 'stage': 'after',
        'materials': [{'item_id': 'unvalidated-controller-decision:synthetic', 'text': json.dumps(response)}]}]}
    result = controller_observations(trace)
    snapshot, = result['controller_snapshots']
    assert snapshot['validation'] == 'unvalidated'
    assert snapshot['selections']['source_need'] == expected
    assert observed_acquisitions(trace)['observed'] == []
    assert observed_acquisitions(trace)['journal_complete'] is None
    assert 'private untrusted text' not in json.dumps(result)
