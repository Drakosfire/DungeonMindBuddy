"""Tests for candidate_graph → Kernel GraphContribution mapping."""

from __future__ import annotations

import hashlib
from pathlib import Path

import pytest

from graph_memory.candidate_graph_preview import (
    CANDIDATE_GRAPH_PREVIEW_SCHEMA,
    CANDIDATE_GRAPH_PREVIEW_VERSION,
    CandidateNode,
    candidate_graph_preview_from_dict,
)
from graph_memory.candidate_graph_to_contribution import (
    CandidateGraphMappingError,
    candidate_graph_to_contribution,
    kernel_kind_for_node_type,
    load_typed_candidate_graph,
    map_candidate_edge_to_assertion,
    map_candidate_node_to_assertion,
    verify_source_revision,
)


def _semantic(*, canon: str = "played_canon", authority: str = "system_derived") -> dict:
    return {
        "canon_state": canon,
        "lifecycle_state": "candidate",
        "evidence_role": "source_evidence",
        "authority_state": authority,
        "visibility_state": "gm_private",
    }


def _evidence(
    suffix: str,
    *,
    artifact: str = "artifact:recap:longmont-c2:session-22",
) -> dict:
    return {
        "source_ref_id": f"ref:{suffix}",
        "source_artifact_id": artifact,
        "source_anchor_id": f"anchor:{suffix}",
        "label": "span",
        "evidence_role": "source_evidence",
        "can_open_source": True,
        "can_highlight_span": True,
        "source_span_ref_id": f"session-22:recap:paragraph:{suffix}",
        "anchor_quotes": ["quote"],
    }


def _diagnostics() -> dict:
    return {
        "preview_only": True,
        "extraction_performed": False,
        "llm_used": False,
        "runtime_connected": False,
        "plan_connected": False,
        "agent_interaction_connected": False,
        "corpus_scanned": False,
        "corpus_mutated": False,
        "facts_promoted": False,
        "canon_promoted": False,
        "unresolved_evidence_refs": 0,
        "missing_evidence_objects": 0,
        "warning_count": 0,
    }


def _minimal_graph(
    *,
    with_evidence: bool = True,
    canon: str = "played_canon",
    multi_source: bool = False,
) -> dict:
    art_a = "artifact:recap:longmont-c2:session-22"
    art_b = "artifact:recap:longmont-c2:session-22-alt"
    vial_evidence = [_evidence("006", artifact=art_a)] if with_evidence else []
    puddle_evidence = (
        [
            _evidence("007", artifact=art_b if multi_source else art_a),
        ]
        if with_evidence
        else []
    )
    return {
        "schema": CANDIDATE_GRAPH_PREVIEW_SCHEMA,
        "version": CANDIDATE_GRAPH_PREVIEW_VERSION,
        "preview_id": "preview:test-promote-minimal",
        "session_id": "session-22",
        "campaign_id": "longmont-c2",
        "source_artifact_ids": [art_a] + ([art_b] if multi_source else []),
        "status": "preview",
        "nodes": [
            {
                "node_id": "obj_session22_vial",
                "label": "vial",
                "node_type": "item",
                "description": "Small vial of puddle water",
                "importance": "medium",
                "semantic_state": _semantic(canon=canon),
                "evidence_refs": vial_evidence,
                "proposed_action": "create",
                "confidence": "medium",
                "warnings": [],
            },
            {
                "node_id": "mystery_puddles",
                "label": "Magic puddles",
                "node_type": "mystery",
                "description": "Puddles with delayed reflections",
                "importance": "medium",
                "semantic_state": _semantic(canon=canon),
                "evidence_refs": puddle_evidence,
                "proposed_action": "create",
                "confidence": "medium",
                "warnings": [],
            },
        ],
        "edges": [
            {
                "edge_id": "e33",
                "from_node_id": "obj_session22_vial",
                "to_node_id": "mystery_puddles",
                "relationship_type": "linked_to",
                "label": "linked to",
                "semantic_state": _semantic(canon=canon),
                "evidence_refs": [_evidence("007")] if with_evidence else [],
                "proposed_action": "create",
                "confidence": "medium",
                "warnings": [],
            },
            {
                "edge_id": "e_orphan",
                "from_node_id": "obj_session22_vial",
                "to_node_id": "not_in_selection",
                "relationship_type": "related_to",
                "label": "orphan",
                "semantic_state": _semantic(canon=canon),
                "evidence_refs": [_evidence("007")] if with_evidence else [],
                "proposed_action": "create",
                "confidence": "medium",
                "warnings": [],
            },
        ],
        "beats": [],
        "proposed_writes": [],
        "ignored_items": [],
        "deferred_items": [],
        "diagnostics": _diagnostics(),
    }


def test_kernel_kind_mapping() -> None:
    assert kernel_kind_for_node_type("character") == "npc"
    assert kernel_kind_for_node_type("item") == "item"
    assert kernel_kind_for_node_type("location") == "location"
    assert kernel_kind_for_node_type("creature") == "creature"


def test_load_typed_rejects_extractor_semantic_aliases() -> None:
    payload = _minimal_graph()
    payload["nodes"][0]["semantic_state"] = {
        "canon_status": "preview_only",
        "lifecycle": "candidate",
        "memory_status": "uncommitted",
    }
    with pytest.raises(CandidateGraphMappingError, match="extractor semantic_state"):
        load_typed_candidate_graph(payload)


def test_load_typed_rejects_missing_nodes_only_payload() -> None:
    with pytest.raises(CandidateGraphMappingError, match="unsupported schema"):
        load_typed_candidate_graph({"nodes": []})


def test_map_node_uses_kernel_value_shape() -> None:
    preview = candidate_graph_preview_from_dict(_minimal_graph())
    node = preview.nodes[0]
    assertion = map_candidate_node_to_assertion(
        node,
        source_revision_id="sha256:abc123",
        verified_source_artifact_id="artifact:recap:longmont-c2:session-22",
        campaign_scope="longmont-c2",
        session_id="session-22",
        campaign_id="longmont-c2",
    )
    assert assertion.assertion_kind == "node"
    assert assertion.acceptance_state == "candidate"
    assert assertion.value["kind"] == "item"
    assert assertion.value["role"] == "item"
    assert assertion.value["canon_state"] == "canonical"
    assert assertion.visibility == "gm"
    assert assertion.value["aliases"] == ["vial"]
    assert assertion.value["source_domains"] == ["recap"]
    assert assertion.evidence_ref_ids
    assert assertion.value["evidence"]
    assert "node_type" not in assertion.value


def test_party_anchor_aliases_survive_typed_load_and_contribution() -> None:
    """Party name-pass stamps aliases; promote IR must admit and carry them."""
    payload = _minimal_graph()
    payload["nodes"] = [
        {
            "node_id": "node:baergrom",
            "label": "Baergrom",
            "node_type": "character",
            "description": "Party member (PC)",
            "importance": "high",
            "semantic_state": _semantic(),
            "evidence_refs": [_evidence("pc-baergrom")],
            "proposed_action": "anchor",
            "confidence": "high",
            "warnings": [],
            "aliases": ["Baergrom", "Baer"],
        }
    ]
    payload["edges"] = []
    payload["source_artifact_ids"] = ["artifact:recap:longmont-c2:session-22"]

    preview = load_typed_candidate_graph(payload)
    assert preview.nodes[0].aliases == ("Baergrom", "Baer")

    contribution = candidate_graph_to_contribution(
        preview,
        world_id="eldyrwild",
        source_revision_id="sha256:deadbeef",
        node_ids=["node:baergrom"],
        include_edges=False,
    )
    node_assertions = [
        a for a in contribution.candidate_assertions if a.assertion_kind == "node"
    ]
    assert len(node_assertions) == 1
    assert node_assertions[0].value["aliases"] == ["Baergrom", "Baer"]
    assert node_assertions[0].label == "Baergrom"


def test_creature_node_survives_typed_load_and_contribution() -> None:
    """Named plot-active creatures from actor_pass must promote with kind creature."""
    payload = _minimal_graph()
    payload["nodes"] = [
        {
            "node_id": "node:bubbles",
            "label": "Bubbles the Float Goat",
            "node_type": "creature",
            "description": "The Float Goat rescued during the flood.",
            "importance": "medium",
            "semantic_state": _semantic(),
            "evidence_refs": [_evidence("bubbles")],
            "proposed_action": "create",
            "confidence": "high",
            "warnings": [],
        }
    ]
    payload["edges"] = []

    preview = load_typed_candidate_graph(payload)
    assert preview.nodes[0].node_type == "creature"

    contribution = candidate_graph_to_contribution(
        preview,
        world_id="eldyrwild",
        source_revision_id="sha256:deadbeef",
        node_ids=["node:bubbles"],
        include_edges=False,
    )
    node_assertions = [
        a for a in contribution.candidate_assertions if a.assertion_kind == "node"
    ]
    assert len(node_assertions) == 1
    assert node_assertions[0].value["kind"] == "creature"
    assert node_assertions[0].value["role"] == "creature"
    assert node_assertions[0].value["aliases"] == ["Bubbles the Float Goat"]


def test_map_fails_closed_without_evidence() -> None:
    preview = candidate_graph_preview_from_dict(_minimal_graph(with_evidence=False))
    # Bypass validate; construct node with empty evidence directly.
    node = CandidateNode(
        node_id="x",
        label="x",
        node_type="item",
        description=None,
        importance="medium",
        semantic_state=preview.nodes[0].semantic_state,
        evidence_refs=(),
        proposed_action="create",
        confidence="medium",
    )
    with pytest.raises(CandidateGraphMappingError, match="no evidence_refs"):
        map_candidate_node_to_assertion(
            node,
            source_revision_id="sha256:abc",
            verified_source_artifact_id="artifact:recap:longmont-c2:session-22",
            campaign_scope="longmont-c2",
        )


def test_planning_scaffold_semantics_rejected() -> None:
    with pytest.raises(CandidateGraphMappingError, match="not promote-eligible"):
        candidate_graph_to_contribution(
            candidate_graph_preview_from_dict(
                _minimal_graph(canon="planning_scaffold")
            ),
            world_id="eldyrwild",
            source_revision_id="sha256:deadbeef",
        )


def test_llm_generated_authority_rejected() -> None:
    payload = _minimal_graph()
    payload["nodes"][0]["semantic_state"]["authority_state"] = "llm_generated"
    with pytest.raises(CandidateGraphMappingError, match="authority_state"):
        candidate_graph_to_contribution(
            candidate_graph_preview_from_dict(payload),
            world_id="eldyrwild",
            source_revision_id="sha256:deadbeef",
            node_ids=["obj_session22_vial"],
            include_edges=False,
        )


def test_map_fails_closed_without_source_revision() -> None:
    with pytest.raises(CandidateGraphMappingError, match="source_revision_id"):
        candidate_graph_to_contribution(
            candidate_graph_preview_from_dict(_minimal_graph()),
            world_id="eldyrwild",
            source_revision_id="",
        )


def test_multi_source_evidence_rejected_until_per_artifact_verify() -> None:
    preview = candidate_graph_preview_from_dict(_minimal_graph(multi_source=True))
    with pytest.raises(CandidateGraphMappingError, match="multi-artifact"):
        candidate_graph_to_contribution(
            preview,
            world_id="eldyrwild",
            source_revision_id="sha256:deadbeef",
            node_ids=["obj_session22_vial", "mystery_puddles"],
            include_edges=False,
        )


def test_map_edge_rejects_artifact_mismatch() -> None:
    from graph_memory.candidate_graph_to_contribution import map_candidate_edge_to_assertion

    preview = candidate_graph_preview_from_dict(_minimal_graph())
    edge = preview.edges[0]
    with pytest.raises(CandidateGraphMappingError, match="!= verified"):
        map_candidate_edge_to_assertion(
            edge,
            source_revision_id="sha256:abc",
            verified_source_artifact_id="artifact:other",
            campaign_scope="longmont-c2",
            session_id="session-22",
            campaign_id="longmont-c2",
        )

def test_verify_source_revision_hashes_file(tmp_path: Path) -> None:
    source = tmp_path / "recap.md"
    content = b"session 22 recap body\n"
    source.write_bytes(content)
    digest = hashlib.sha256(content).hexdigest()
    verified = verify_source_revision(
        source_uri=str(source),
        source_revision_id=f"sha256:{digest}",
    )
    assert verified == f"sha256:{digest}"
    with pytest.raises(CandidateGraphMappingError, match="mismatch"):
        verify_source_revision(
            source_uri=str(source),
            source_revision_id="sha256:deadbeef",
        )


def test_party_registry_source_artifact_omits_session_id() -> None:
    from graph_memory.candidate_graph_to_contribution import _source_artifact_payload

    party = _source_artifact_payload(
        source_artifact_id="artifact:party-registry:longmont-c1",
        source_revision_id="sha256:deadbeef",
        source_domain="party_registry",
        campaign_id="longmont-c1",
        session_id="session-4",
        source_uri="repo://corpus/_party_registry.json",
    )
    assert "session_id" not in party

    recap = _source_artifact_payload(
        source_artifact_id="artifact:recap:session-4",
        source_revision_id="sha256:deadbeef",
        source_domain="recap",
        campaign_id="longmont-c1",
        session_id="session-4",
        source_uri="repo://corpus/recap.md",
    )
    assert recap.get("session_id") == "session-4"

    contribution = candidate_graph_to_contribution(
        candidate_graph_preview_from_dict(_minimal_graph()),
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


def test_party_registry_edge_omits_session_stamp() -> None:
    preview = candidate_graph_preview_from_dict(_minimal_graph())
    edge = preview.edges[0]
    party = map_candidate_edge_to_assertion(
        edge,
        source_revision_id="sha256:deadbeef",
        verified_source_artifact_id="artifact:recap:longmont-c2:session-22",
        campaign_scope="longmont-c2",
        source_domain="party_registry",
        session_id="session-4",
        campaign_id="longmont-c2",
    )
    assert "session_ids" not in party.value
    assert party.temporal_scope is None

    recap = map_candidate_edge_to_assertion(
        edge,
        source_revision_id="sha256:deadbeef",
        verified_source_artifact_id="artifact:recap:longmont-c2:session-22",
        campaign_scope="longmont-c2",
        source_domain="recap",
        session_id="session-4",
        campaign_id="longmont-c2",
    )
    assert recap.value.get("session_ids") == ["session-4"]
    assert recap.temporal_scope == {"session_id": "session-4"}
