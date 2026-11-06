"""Candidate IDs are a host composition concern, not semantic identity."""
import copy
import json

import pytest

from src.graph_memory.extraction.category_candidate_graph_extractor import consolidate_category_outputs
from src.graph_memory.extraction.recap_extraction_profile import RECAP_EXTRACTION_PROFILE


def node(local_id, label):
    return {'node_id': local_id, 'label': label, 'description': label,
            'node_type': 'item', 'evidence_refs': []}


def compose(outputs, profile=RECAP_EXTRACTION_PROFILE):
    return consolidate_category_outputs(outputs, campaign_id='synthetic', session=1, profile=profile)


def test_independent_local_ids_are_injective_reversible_and_inputs_unchanged():
    outputs = {'object_pass': {'observation_nodes': [node('N001', 'Map')]},
               'thread_pass': {'observation_nodes': [node('N001', 'Uncertain activity')]}}
    original = copy.deepcopy(outputs)
    graph = compose(outputs)
    assert graph == compose(outputs)
    assert outputs == original
    assert len({n['node_id'] for n in graph['nodes']}) == 2
    bindings = graph['consolidation_diagnostics']['node_id_bindings']
    assert {tuple(json.loads(n['node_id'].removeprefix('recap-model-node:'))) for n in graph['nodes']} == {
        ('object_pass', 'N001'), ('thread_pass', 'N001')}
    assert {b['candidate_node_id'] for b in bindings} == {n['node_id'] for n in graph['nodes']}
    assert [n['description'] for n in graph['nodes']] == ['Map', 'Uncertain activity']


@pytest.mark.parametrize('ids', [('N001', 'N001'), (' N001 ', 'N001'), ('',), (None,)])
def test_same_pass_ambiguity_or_missing_id_fails_before_inventory(ids):
    with pytest.raises(ValueError, match='(duplicate|missing) node ID'):
        compose({'object_pass': {'observation_nodes': [node(i, 'Object') for i in ids]}})


def test_delimiter_like_local_ids_cannot_alias_another_pass():
    graph = compose({'object_pass': {'observation_nodes': [node('thread_pass:N001', 'Map')]},
                     'thread_pass': {'observation_nodes': [node('object_pass:N001', 'Mystery')]}})
    assert len({n['node_id'] for n in graph['nodes']}) == 2


def test_only_advertised_endpoint_ids_bind_no_ambiguous_old_endpoint_repair():
    outputs = {'object_pass': {'observation_nodes': [node('N001', 'Map')]},
               'thread_pass': {'observation_nodes': [node('N001', 'Mystery')]}}
    advertised = [n['node_id'] for n in compose(outputs)['nodes']]
    outputs['edge_pass'] = {'observation_edges': [
        {'edge_id': 'good', 'from_node_id': advertised[0], 'to_node_id': advertised[1],
         'label': 'associated', 'relationship_type': 'associated_with', 'evidence_refs': []},
        {'edge_id': 'ambiguous', 'from_node_id': 'N001', 'to_node_id': advertised[1],
         'label': 'associated', 'relationship_type': 'associated_with', 'evidence_refs': []}]}
    graph = compose(outputs)
    assert [e['edge_id'] for e in graph['edges']] == ['good']
    assert graph['edges'][0]['from_node_id'] == advertised[0]
    assert graph['consolidation_diagnostics']['dropped_edges_missing_endpoints'][0]['edge_id'] == 'ambiguous'


def test_other_profiles_do_not_change_identity_composition():
    from src.graph_memory.extraction.worldbuilding_plumbing_profile import WORLDBUILDING_PLUMBING_PROFILE
    from src.graph_memory.extraction.extraction_profile import get_extraction_profile
    for profile in [WORLDBUILDING_PLUMBING_PROFILE,
                    get_extraction_profile('recap_category_encounter_job_preview', '2.0')]:
        graph = compose({'object_pass': {'observation_nodes': [node('N001', 'Map')]}}, profile)
        assert [n['node_id'] for n in graph['nodes']] == ['N001']
        assert 'node_id_bindings' not in graph['consolidation_diagnostics']


def test_actual_pipeline_advertises_distinct_ids_before_later_calls_and_preserves_endpoints():
    import hashlib
    from src.graph_memory.source_span import build_source_span_index_for_text, source_span_index_to_dict
    from src.graph_memory.extraction.category_candidate_graph_extractor import (
        CategoryGraphExtractionOptions, extract_category_candidate_graph,
    )
    source = 'The traveler carries a map.'
    index = source_span_index_to_dict(build_source_span_index_for_text(
        source_artifact_id='synthetic:source', content_sha256=hashlib.sha256(source.encode()).hexdigest(), text=source))
    from src.graph_memory.extraction.category_candidate_graph_extractor import source_packet_rows_from_span_index
    ref = {'source_span_ref_id': source_packet_rows_from_span_index(index, source_text=source)[0]['source_span_ref_id'],
           'anchor_quotes': [source]}
    class Client:
        def __init__(self): self.inventory = None
        def run_pass(self, name, *, user_content, **kwargs):
            if name in ('actor_pass', 'object_pass'):
                row = node('N001', 'Traveler' if name == 'actor_pass' else 'Map')
                row['node_type'] = 'character' if name == 'actor_pass' else 'item'
                row['evidence_refs'] = [copy.deepcopy(ref)]
                parsed = {'observation_nodes': [row]}
            elif name == 'beat_pass':
                self.inventory = json.JSONDecoder().raw_decode(
                    user_content.split('## Node identity inventory\n\n```json\n', 1)[1])[0]
                assert len({n['node_id'] for n in self.inventory}) == 2
                parsed = {'observation_beats': []}
            elif name == 'edge_pass':
                assert self.inventory is not None
                for row in self.inventory:
                    assert json.dumps(row['node_id']) in user_content
                parsed = {'observation_edges': [{'edge_id': 'e1',
                    'from_node_id': self.inventory[0]['node_id'], 'to_node_id': self.inventory[1]['node_id'],
                    'label': 'Carries', 'relationship_type': 'associated_with', 'evidence_refs': [copy.deepcopy(ref)]}]}
            else:
                parsed = {'observation_nodes': []}
            return {'parsed': parsed, 'cost_usd': 0, 'usage': {}, 'elapsed_ms': 1, 'response_id': name}
    client = Client()
    result = extract_category_candidate_graph(CategoryGraphExtractionOptions(
        campaign_id='synthetic', session_id='session-1', session_number=1, source_text=source,
        source_span_index=index, profile=RECAP_EXTRACTION_PROFILE), client=client)
    assert len(result.candidate_graph['nodes']) == 2
    assert len(result.candidate_graph['edges']) == 1
    edge = result.candidate_graph['edges'][0]
    assert (edge['from_node_id'], edge['to_node_id']) == tuple(row['node_id'] for row in client.inventory)
    assert all(row['description'] in ('Traveler', 'Map') for row in result.candidate_graph['nodes'])
