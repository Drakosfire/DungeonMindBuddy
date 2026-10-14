import copy
import pytest
from src.graph_memory.extraction.category_candidate_graph_extractor import consolidate_category_outputs


def fixture(label):
    refs = [{'source_span_ref_id': 'synthetic:span', 'anchor_quotes': ['A guard grapples Iria.']}]
    nodes = [{'node_id': i, 'label': name, 'node_type': 'character', 'evidence_refs': refs}
             for i, name in [('node:guard', 'Guard'), ('node:iria', 'Iria')]]
    return {'actor_pass': {'observation_nodes': nodes}, 'edge_pass': {'observation_edges': [{
        'edge_id': 'edge:fixture', 'from_node_id': 'node:guard', 'to_node_id': 'node:iria',
        'relationship_type': 'attacks', 'label': label, 'evidence_refs': refs,
    }]}}


def test_explicit_self_rejection_is_deferred_with_evidence_and_tuple():
    inputs = fixture('Omitted: no source support for a guard attacking Iria')
    supported = copy.deepcopy(inputs['edge_pass']['observation_edges'][0])
    supported.update(edge_id='edge:supported', label='The guard grapples Iria')
    inputs['edge_pass']['observation_edges'].append(supported)
    before = copy.deepcopy(inputs)
    result = consolidate_category_outputs(inputs, campaign_id='synthetic', session=None)
    assert [e['edge_id'] for e in result['edges']] == ['edge:supported']
    assert len(result['deferred_items']) == 1
    deferred = result['deferred_items'][0]
    assert deferred['evidence_refs'][0]['source_span_ref_id'] == 'synthetic:span'
    assert 'node:guard attacks node:iria' in deferred['reason']
    assert 'edge:fixture' in deferred['reason']
    assert inputs == before


@pytest.mark.parametrize('label', [
    'The guard omitted an attack', 'Omitted: a room from the draft',
    'Iria says "Omitted: no source support"', 'No source support is discussed by the guard',
])
def test_narrative_or_ambiguous_labels_are_not_semantically_classified(label):
    result = consolidate_category_outputs(fixture(label), campaign_id='synthetic', session=None)
    assert len(result['edges']) == 1
    assert not result['deferred_items']
