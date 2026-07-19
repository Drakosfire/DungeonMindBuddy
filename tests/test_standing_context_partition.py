"""Tests for standing-context / recap provenance partition."""

from __future__ import annotations

from graph_memory.standing_context_partition import (
    STANDING_WARNING,
    is_standing_context_node,
    partition_candidate_graph_by_provenance,
    party_registry_artifact_id,
    stamp_standing_registry_evidence,
)


def test_partition_moves_heroes_party_and_membership_edges() -> None:
    graph = {
        "schema": "dmb_candidate_graph_preview_v0",
        "nodes": [
            {
                "node_id": "node:baergrom",
                "label": "Baergrom",
                "node_type": "character",
                "evidence_refs": [{"source_ref_id": "r1", "source_artifact_id": "a"}],
                "proposed_action": "anchor",
                "warnings": ["known_entity_mention_evidence"],
            },
            {
                "node_id": "node:heroes-party",
                "label": "Heroes / party",
                "node_type": "group",
                "evidence_refs": [],
                "proposed_action": "anchor",
                "warnings": [STANDING_WARNING],
                "context_anchor": True,
            },
            {
                "node_id": "node:bubbles",
                "label": "Bubbles",
                "node_type": "creature",
                "evidence_refs": [{"source_ref_id": "r2", "source_artifact_id": "a"}],
                "proposed_action": "create",
                "warnings": [],
            },
        ],
        "edges": [
            {
                "edge_id": "e:member",
                "from_node_id": "node:baergrom",
                "to_node_id": "node:heroes-party",
                "relationship_type": "member_of",
                "evidence_refs": [],
                "context_anchor": True,
                "warnings": [STANDING_WARNING],
            },
            {
                "edge_id": "e:pursues",
                "from_node_id": "node:heroes-party",
                "to_node_id": "node:quest",
                "relationship_type": "pursues",
                "evidence_refs": [],
                "context_anchor": True,
                "warnings": [STANDING_WARNING],
            },
        ],
        "beats": [],
        "proposed_writes": [],
        "ignored_items": [],
        "deferred_items": [],
    }
    # quest not in graph — hybrid edge dropped
    recap, standing, diag = partition_candidate_graph_by_provenance(graph)
    assert {n["node_id"] for n in recap["nodes"]} == {"node:baergrom", "node:bubbles"}
    assert "node:heroes-party" in {n["node_id"] for n in standing["nodes"]}
    assert "node:baergrom" in {n["node_id"] for n in standing["nodes"]}
    assert {e["edge_id"] for e in standing["edges"]} == {"e:member"}
    assert recap["edges"] == []
    assert "e:pursues" in diag["dropped_hybrid_edge_ids"]


def test_stamp_standing_registry_evidence_fills_empty_refs() -> None:
    graph = {
        "nodes": [
            {
                "node_id": "node:heroes-party",
                "evidence_refs": [],
                "warnings": [],
            },
            {
                "node_id": "node:baergrom",
                "evidence_refs": [
                    {
                        "source_ref_id": "recap-ref",
                        "source_artifact_id": "artifact:recap:longmont-c1:session-3",
                    }
                ],
                "warnings": [],
            },
        ],
        "edges": [],
    }
    art = party_registry_artifact_id("longmont-c1")
    stamp_standing_registry_evidence(graph, source_artifact_id=art)
    for node in graph["nodes"]:
        refs = node["evidence_refs"]
        assert len(refs) == 1
        assert refs[0]["source_artifact_id"] == art
        assert refs[0]["can_highlight_span"] is True
        assert refs[0]["can_open_source"] is True
        assert STANDING_WARNING in node["warnings"]


def test_is_standing_context_node_fallback_without_context_anchor_flag() -> None:
    assert is_standing_context_node(
        {
            "node_id": "node:heroes-party",
            "evidence_refs": [],
            "warnings": [STANDING_WARNING],
        }
    )
    assert not is_standing_context_node(
        {
            "node_id": "node:baergrom",
            "evidence_refs": [{"source_ref_id": "x", "source_artifact_id": "a"}],
            "warnings": [],
        }
    )
