from __future__ import annotations

from typing import Any

from src.graph_memory import party_context as pc
from src.graph_memory.session_graph_context import (
    attach_party_participation_edges,
    merge_party_anchor_nodes,
    merge_party_collective,
)


def _encounter_nodes() -> dict[str, Any]:
    return {
        "observation_nodes": [
            {
                "node_id": "quest_clear_glowkindle_rats",
                "label": "Clear rats from Glowkindle's cellar",
                "node_type": "quest",
                "description": "Glowkindle asks the party to clear rats from the cellar.",
                "importance": "medium",
                "evidence_refs": [
                    {"source_span_ref_id": "spref:c1s22:001", "anchor_quotes": ["clear rats from the cellar"]}
                ],
            },
            {
                "node_id": "enc_glowkindle_cellar_rats",
                "label": "Glowkindle cellar rat fight",
                "node_type": "combat_encounter",
                "description": "The party fights a swarm of rats in the cellar.",
                "importance": "medium",
                "evidence_refs": [
                    {"source_span_ref_id": "spref:c1s22:002", "anchor_quotes": ["fought a swarm of rats"]}
                ],
            },
        ]
    }


def test_repeated_helper_application_does_not_duplicate_edges():
    party_ctx = pc.build_party_context_for_campaign("longmont-c2", 22)
    nodes, _ = merge_party_anchor_nodes([], party_ctx, default_semantic_state={"status": "unknown"})
    nodes.extend(_encounter_nodes()["observation_nodes"])
    nodes, edges, _ = merge_party_collective(nodes, [], party_ctx, default_semantic_state={"status": "unknown"})

    once, _ = attach_party_participation_edges(nodes, edges, party_ctx, default_semantic_state={"status": "unknown"})
    twice, _ = attach_party_participation_edges(nodes, once, party_ctx, default_semantic_state={"status": "unknown"})

    target_id = "edge:heroes-party-pursues-quest-clear-glowkindle-rats"
    assert [edge["edge_id"] for edge in twice].count(target_id) == 1


def test_helper_ignores_non_target_node_types_and_member_edges_by_default():
    party_ctx = pc.build_party_context_for_campaign("longmont-c2", 22)
    nodes, _ = merge_party_anchor_nodes([], party_ctx, default_semantic_state={"status": "unknown"})
    nodes.extend(
        {
            "node_id": f"node_{node_type}",
            "label": node_type.title(),
            "node_type": node_type,
            "evidence_refs": [],
        }
        for node_type in ("character", "location", "item", "thread", "mystery", "warning", "event")
    )
    nodes, edges, _ = merge_party_collective(nodes, [], party_ctx, default_semantic_state={"status": "unknown"})

    merged_edges, diag = attach_party_participation_edges(nodes, edges, party_ctx, default_semantic_state={"status": "unknown"})

    assert diag["skipped_reason"] == "no_encounter_or_quest_nodes"
    participation_edges = [edge for edge in merged_edges if "deterministic_party_participation" in edge.get("warnings", [])]
    assert participation_edges == []
    assert diag["subject_node_ids"] == []
