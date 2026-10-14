from __future__ import annotations

import pytest

from src.graph_memory.extraction.category_candidate_graph_extractor import (
    CategoryGraphExtractionOptions,
    FixtureCategoryGraphPassClient,
    run_category_pipeline,
)
from src.graph_memory.extraction.known_entity_registry import known_entities_from_world_graph


def run_fixture(text: str, entities: list[dict]):
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
        model_id="deepseek/deepseek-v4.1-flash", enable_party_claimed_fill=False,
        extra_known_entities=tuple(known_entities_from_world_graph({"nodes": entities}, include_kinds=None)),
    )
    return run_category_pipeline(Capture(), options), messages


def entity(node_id="node:vela", label="Vela", kind="dnd5e:npc", aliases=None):
    return {"node_id": node_id, "label": label, "kind": kind, "aliases": aliases or []}


@pytest.mark.parametrize("kind", ["npc", "character", "dnd5e:npc"])
def test_verified_mentioned_npc_survives_as_canonical_edge_endpoint(kind):
    result, messages = run_fixture("Vela serves ale at the Lantern Inn.", [entity(kind=kind)])
    nodes = result.candidate_graph["nodes"]
    canonical = [n for n in nodes if n["node_id"] == "node:vela"]
    assert len(canonical) == 1
    assert not any(n["node_id"] == "generated:vela" for n in nodes)
    assert canonical[0]["evidence_refs"][0]["anchor_quotes"] == ["Vela"]
    consolidated = messages["edge_pass"].split("## Consolidated nodes", 1)[1]
    assert '"node:vela"' in consolidated
    assert any(e["from_node_id"] == "node:vela" and e["to_node_id"] == "location:inn"
               for e in result.candidate_graph["edges"])
    assert result.consolidation_diagnostics["dropped_edges_missing_endpoints"] == []


def test_unmentioned_verified_npc_is_not_inserted():
    result, _ = run_fixture("The Lantern Inn is quiet.", [entity()])
    assert not any(n["node_id"] == "node:vela" for n in result.candidate_graph["nodes"])
    assert not result.candidate_graph["edges"]


def test_ambiguous_alias_does_not_create_either_endpoint():
    result, _ = run_fixture("The Keeper serves ale at the Lantern Inn.", [
        entity(aliases=["Keeper"]), entity("node:other", "Other", aliases=["Keeper"]),
    ])
    assert not any(n["node_id"] in {"node:vela", "node:other"} for n in result.candidate_graph["nodes"])
    assert not result.candidate_graph["edges"]


def test_unknown_kind_is_not_coerced_to_npc():
    result, _ = run_fixture("Vela serves ale at the Lantern Inn.", [entity(kind="unknown:thing")])
    assert not any(n["node_id"] == "node:vela" for n in result.candidate_graph["nodes"])
    assert not result.candidate_graph["edges"]
