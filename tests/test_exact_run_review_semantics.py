"""Review semantics come from validated typed candidates, never friendly prose."""
from types import SimpleNamespace
import pytest
from graph_memory.candidate_graph_preview import candidate_graph_preview_to_dict
from apps.live_control_server.services.extract_promote import _assert_and_project_candidate_evidence
from tests.test_cutover_worldbuilding_authority_port import _preview

@pytest.mark.parametrize("predicate", ["owns", "hires", "child_of", "unknown_relation"])
def test_exact_projection_preserves_type_predicate_and_direction(predicate):
    payload = candidate_graph_preview_to_dict(_preview())
    artifact = payload['source_artifact_ids'][0]
    nodes = payload['nodes']; nodes[0]['node_type'] = 'character'; nodes[1]['node_type'] = 'faction'
    nodes[0]['label'] = 'Merchant'; nodes[1]['label'] = 'Guild'
    edge = payload['edges'][0]
    edge.update(label='sold something to', relationship_type=predicate)
    for holder in [*nodes, *payload['edges']]:
        holder['evidence_refs'] = [{"source_ref_id": "ref-one", "can_open_source": True, "can_highlight_span": True, "source_artifact_id": artifact, "source_span_ref_id": "span-one",
            "anchor_quotes": ["The merchant spoke to the guild."]}]
    review = _assert_and_project_candidate_evidence(candidate_payload=payload,
        source_prose='The merchant spoke to the guild.', source_artifact_id=artifact,
        span_index=SimpleNamespace(spans=[SimpleNamespace(source_span_id='span-one', start_line=1, end_line=1)]))
    projected = {a.assertion_id: a for a in review}
    assert projected[nodes[0]['node_id']].node_type == 'character'
    assert projected[nodes[0]['node_id']].contribution_kind == 'npc'
    assert projected[nodes[1]['node_id']].node_type == 'faction'
    actual = projected[edge['edge_id']]
    assert actual.label == 'sold something to'
    assert actual.relationship_type == predicate
    assert actual.from_candidate_node_id == edge['from_node_id']
    assert actual.to_candidate_node_id == edge['to_node_id']
    wire = actual.model_dump(by_alias=True)
    assert wire['relationshipType'] == predicate
    assert wire['fromCandidateNodeId'] == edge['from_node_id']
