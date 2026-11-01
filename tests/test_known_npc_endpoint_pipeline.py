from __future__ import annotations


from src.graph_memory.extraction.category_candidate_graph_extractor import (
    CategoryGraphExtractionOptions,
    FixtureCategoryGraphPassClient,
    run_category_pipeline,
)


def run_fixture(text: str):
    ref = {"source_span_ref_id": "span-1", "anchor_quotes": [text]}
    outputs = {
        "actor_pass": {"observation_nodes": [{
            "node_id": "generated:vela", "label": "Vela", "node_type": "character",
            "description": "Duplicate fixture actor", "importance": "medium", "evidence_refs": [ref],
        }]},
        "location_pass": {"observation_nodes": [{
            "node_id": "location:inn", "label": "Lantern Inn", "node_type": "location",
            "description": "An inn", "importance": "medium", "evidence_refs": [ref],
        }]},
        "edge_pass": {"observation_edges": [{
            "edge_id": "edge:vela-inn", "from_node_id": "node:vela", "to_node_id": "location:inn",
            "label": "Vela is at the inn", "relationship_type": "located_in",
            "predicate_family": "spatial", "evidence_refs": [ref],
        }]},
    }
    fixture = FixtureCategoryGraphPassClient(outputs)
    messages = {}

    class Capture:
        def run_pass(self, name, **kwargs):
            messages[name] = kwargs["user_content"]
            return fixture.run_pass(name, **kwargs)

    options = CategoryGraphExtractionOptions(
        campaign_id="synthetic", session_id=None, session_number=None,
        source_text=text, source_span_index={
            "source_artifact_id": "artifact:synthetic", "source_ref_id": "artifact:synthetic:text",
            "spans": [{"span_id": "span-1", "source_span_ref_id": "span-1", "line_start": 1,
                       "line_end": 1, "text": text}],
        },
        model_id="synthetic",
    )
    return run_category_pipeline(Capture(), options), messages


def test_source_actor_is_not_replaced_by_a_canonical_registry_endpoint():
    result, messages = run_fixture("Vela serves ale at the Lantern Inn.")
    nodes = result.candidate_graph["nodes"]
    assert any(node["node_id"] == "generated:vela" for node in nodes)
    assert not any(node["node_id"] == "node:vela" for node in nodes)
    assert not result.candidate_graph["edges"]
    assert result.consolidation_diagnostics["dropped_edges_missing_endpoints"][0]["from_node_id"] == "node:vela"
    assert '"generated:vela"' in messages["edge_pass"]
