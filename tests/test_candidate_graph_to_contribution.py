"""Tests for candidate_graph → Kernel GraphContribution mapping."""

from __future__ import annotations

import pytest

from graph_memory.candidate_graph_to_contribution import (
    CandidateGraphMappingError,
    candidate_graph_to_contribution,
    kernel_kind_for_node_type,
    map_candidate_node_to_assertion,
)


def _minimal_graph(*, with_evidence: bool = True) -> dict:
    evidence = (
        [
            {
                "source_span_ref_id": "session-22:recap:paragraph:006",
                "anchor_quotes": ["vial of puddle water"],
            }
        ]
        if with_evidence
        else []
    )
    return {
        "schema": "dmb_candidate_graph_preview_v0",
        "session_id": "session-22",
        "campaign_id": "longmont-c2",
        "source_artifact_ids": ["artifact:recap:longmont-c2:session-22"],
        "nodes": [
            {
                "node_id": "obj_session22_vial",
                "label": "vial",
                "node_type": "item",
                "description": "Small vial of puddle water",
                "evidence_refs": evidence,
            },
            {
                "node_id": "mystery_puddles",
                "label": "Magic puddles",
                "node_type": "mystery",
                "description": "Puddles with delayed reflections",
                "evidence_refs": [
                    {
                        "source_span_ref_id": "session-22:recap:paragraph:007",
                        "anchor_quotes": ["delayed reflections"],
                    }
                ]
                if with_evidence
                else [],
            },
        ],
        "edges": [
            {
                "edge_id": "e33",
                "from_node_id": "obj_session22_vial",
                "to_node_id": "mystery_puddles",
                "relationship_type": "linked_to",
                "predicate_family": "social_relation",
                "label": "linked to",
                "evidence_refs": [
                    {
                        "source_span_ref_id": "session-22:recap:paragraph:007",
                        "anchor_quotes": ["vial"],
                    }
                ]
                if with_evidence
                else [],
            },
            {
                "edge_id": "e_orphan",
                "from_node_id": "obj_session22_vial",
                "to_node_id": "not_in_selection",
                "relationship_type": "related_to",
                "label": "orphan",
                "evidence_refs": [
                    {
                        "source_span_ref_id": "session-22:recap:paragraph:007",
                        "anchor_quotes": ["x"],
                    }
                ],
            },
        ],
    }


def test_kernel_kind_mapping() -> None:
    assert kernel_kind_for_node_type("character") == "npc"
    assert kernel_kind_for_node_type("item") == "item"
    assert kernel_kind_for_node_type("location") == "location"


def test_map_node_uses_kernel_value_shape() -> None:
    node = _minimal_graph()["nodes"][0]
    assertion = map_candidate_node_to_assertion(
        node,
        source_artifact_id="artifact:recap:longmont-c2:session-22",
        source_revision_id="sha256:abc123",
        campaign_scope="longmont-c2",
        session_id="session-22",
        campaign_id="longmont-c2",
    )
    assert assertion.assertion_kind == "node"
    assert assertion.acceptance_state == "candidate"
    assert assertion.value["kind"] == "item"
    assert assertion.value["role"] == "item"
    assert "aliases" in assertion.value
    assert "source_domains" in assertion.value
    assert assertion.value["source_domains"] == ["recap"]
    assert assertion.evidence_ref_ids
    assert assertion.value["evidence"]
    assert "node_type" not in assertion.value


def test_map_fails_closed_without_evidence() -> None:
    node = _minimal_graph(with_evidence=False)["nodes"][0]
    with pytest.raises(CandidateGraphMappingError, match="no evidence_refs"):
        map_candidate_node_to_assertion(
            node,
            source_artifact_id="artifact:x",
            source_revision_id="sha256:abc",
            campaign_scope="longmont-c2",
        )


def test_map_fails_closed_without_source_revision() -> None:
    with pytest.raises(CandidateGraphMappingError, match="source_revision_id"):
        candidate_graph_to_contribution(
            _minimal_graph(),
            world_id="eldyrwild",
            source_revision_id="",
        )


def test_candidate_graph_maps_nodes_and_in_scope_edges_only() -> None:
    contribution = candidate_graph_to_contribution(
        _minimal_graph(),
        world_id="eldyrwild",
        source_revision_id="sha256:deadbeef",
        node_ids=["obj_session22_vial", "mystery_puddles"],
    )
    assert contribution.source_kind == "source_extraction"
    assert contribution.source_revision_id == "sha256:deadbeef"
    assert contribution.accepted_assertions == []
    kinds = {a.assertion_kind for a in contribution.candidate_assertions}
    assert kinds == {"node", "edge"}
    edge_assertions = [
        a for a in contribution.candidate_assertions if a.assertion_kind == "edge"
    ]
    assert len(edge_assertions) == 1
    assert edge_assertions[0].predicate == "linked_to"
    assert edge_assertions[0].subject_node_id == "obj_session22_vial"
    assert edge_assertions[0].target_node_id == "mystery_puddles"
    node_assertions = [
        a for a in contribution.candidate_assertions if a.assertion_kind == "node"
    ]
    assert len(node_assertions) == 2
