from __future__ import annotations

from src.graph_memory.extraction.category_candidate_graph_extractor import consolidate_category_outputs


def outputs(*, edge_source="node:heroes-party"):
    ref = {"source_span_ref_id": "synthetic:span-1", "anchor_quotes": ["The party seeks the Archivist."]}
    return {
        "actor_pass": {"observation_nodes": [{
            "node_id": "npc:archivist", "label": "Archivist", "node_type": "character",
            "description": "An archivist", "importance": "medium", "evidence_refs": [ref],
        }]},
        "edge_pass": {"observation_edges": [{
            "edge_id": "edge:party-seeks", "from_node_id": edge_source, "to_node_id": "npc:archivist",
            "label": "The party seeks the Archivist", "relationship_type": "seeks",
            "predicate_family": "social", "evidence_refs": [ref],
        }]},
    }


def source_membership_outputs(*, existing_party: bool):
    ref = {
        "source_span_ref_id": "synthetic:membership-span",
        "anchor_quotes": ["Baergrom joins the heroes / party."],
    }
    nodes = [{
        "node_id": "node:baergrom",
        "label": "Baergrom Stoutheart",
        "node_type": "character",
        "corpus_ref": {"type": "pc", "ref_id": "baergrom", "resolution": "resolved"},
        "evidence_refs": [ref],
    }]
    if existing_party:
        nodes.append({
            "node_id": "node:heroes-party",
            "label": "Heroes / party",
            "node_type": "group",
            "evidence_refs": [],
        })
    return {
        "actor_pass": {"observation_nodes": nodes},
        "edge_pass": {"observation_edges": [{
            "edge_id": "edge:source-membership",
            "from_node_id": "node:baergrom",
            "to_node_id": "node:heroes-party",
            "label": "Baergrom is part of the heroes / party",
            "relationship_type": "member_of",
            "predicate_family": "membership",
            "evidence_refs": [ref],
        }]},
    }


def test_preedge_party_endpoint_remains_available_during_edge_checks():
    data = outputs()
    before = consolidate_category_outputs({"actor_pass": data["actor_pass"]}, campaign_id="longmont-c2", session=2)
    assert any(n["node_id"] == "node:heroes-party" for n in before["nodes"])
    after = consolidate_category_outputs(data, campaign_id="longmont-c2", session=2)
    assert any(e["edge_id"] == "edge:party-seeks" for e in after["edges"])
    assert after["consolidation_diagnostics"]["dropped_edges_missing_endpoints"] == []
    membership = [e for e in after["edges"] if e["relationship_type"] == "member_of"]
    assert len(membership) == 6
    assert len({e["edge_id"] for e in membership}) == 6


def test_source_backed_membership_precedes_roster_anchor_for_existing_and_seeded_party():
    expected_ref = {
        "source_span_ref_id": "synthetic:membership-span",
        "anchor_quotes": ["Baergrom joins the heroes / party."],
    }
    for existing_party in (False, True):
        result = consolidate_category_outputs(
            source_membership_outputs(existing_party=existing_party),
            campaign_id="longmont-c2",
            session=2,
        )
        assert any(node["node_id"] == "node:heroes-party" for node in result["nodes"])
        assert result["consolidation_diagnostics"]["dropped_edges_missing_endpoints"] == []
        membership = [
            edge for edge in result["edges"]
            if edge["relationship_type"] == "member_of"
            and edge["from_node_id"] == "node:baergrom"
            and edge["to_node_id"] == "node:heroes-party"
        ]
        assert len(membership) == 1
        assert membership[0]["edge_id"] == "edge:source-membership"
        assert membership[0]["evidence_refs"] == [expected_ref]
        assert not membership[0].get("context_anchor", False)
        assert len([edge for edge in result["edges"] if edge["relationship_type"] == "member_of"]) == 6


def test_unknown_endpoint_is_still_dropped():
    result = consolidate_category_outputs(outputs(edge_source="unknown:party"), campaign_id="longmont-c2", session=2)
    assert not any(e["edge_id"] == "edge:party-seeks" for e in result["edges"])
    assert result["consolidation_diagnostics"]["dropped_edges_missing_endpoints"][0]["from_node_id"] == "unknown:party"


def test_absent_roster_does_not_create_a_party_or_accept_its_edge():
    result = consolidate_category_outputs(outputs(), campaign_id="synthetic", session=None)
    assert not any(n["node_id"] == "node:heroes-party" for n in result["nodes"])
    assert not any(e["edge_id"] == "edge:party-seeks" for e in result["edges"])
