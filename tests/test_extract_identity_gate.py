"""Tests for head-pinned extract identity gate."""

from __future__ import annotations

from pathlib import Path

import pytest

import graph_memory.kernel as kernel
from graph_memory.candidate_graph_preview import (
    CANDIDATE_GRAPH_PREVIEW_SCHEMA,
    CANDIDATE_GRAPH_PREVIEW_VERSION,
    candidate_graph_preview_from_dict,
)
from graph_memory.candidate_graph_to_contribution import CandidateGraphMappingError
from graph_memory.contribution_bundles import load_contribution_bundle
from graph_memory.extract_identity_gate import (
    build_accepted_contribution_from_proposals,
    gate_candidate_graph_against_head,
)
from graph_memory.kernel.world_initialization import initialize_world_from_contributions
from graph_memory.kernel.world_initialization_models import (
    PLAN_SCHEMA,
    WorldInitializationApprovalAttestation,
    WorldInitializationContribution,
    WorldInitializationPlan,
)

REPO_ROOT = Path(__file__).resolve().parents[1]
BUNDLE_PATH = (
    REPO_ROOT
    / "graph_data/approved_contribution_bundles/eldyrwild-longmont-c2-initial-v1"
)
BUNDLE_DIGEST = (
    "5f8288d3052a9e59192884f2c35a13d51f665095d84cca2081a56638108d3fa5"
)
BUNDLE_ID = "eldyrwild-longmont-c2-initial-v1"
WORLD_ID = "eldyrwild"
CAMPAIGN_ID = "longmont-c2"
FOCUS_SESSION_ID = "session-23"
APPROVED_MERGE_SHA = "65ae001e0852d827ecd680200a965a576c705b1d"
ACTOR = "gm"
ORDERED_CONTRIBUTION_IDS = [
    "contribution:82f23934d8eaca8a",
    "contribution:43782369bd717d32",
    "contribution:33d7cdb0ff623f28",
    "contribution:c086a0b72324ff16",
    "contribution:1227841724520c18",
    "contribution:022187fdefdf4557",
]


@pytest.fixture
def loaded_bundle():
    return load_contribution_bundle(BUNDLE_PATH)


def _plan(bundle) -> WorldInitializationPlan:
    by_id = {item.contribution_id: item for item in bundle.contributions}
    return WorldInitializationPlan(
        schema=PLAN_SCHEMA,
        world_id=WORLD_ID,
        campaign_id=CAMPAIGN_ID,
        focus_session_id=FOCUS_SESSION_ID,
        ordered_contributions=[
            WorldInitializationContribution(
                contribution_id=contribution_id,
                payload_sha256=kernel.compute_contribution_payload_sha256(
                    by_id[contribution_id]
                ),
            )
            for contribution_id in ORDERED_CONTRIBUTION_IDS
        ],
        approval_attestation=WorldInitializationApprovalAttestation(
            bundle_id=BUNDLE_ID,
            bundle_digest=BUNDLE_DIGEST,
            approved_bundle_merge_sha=APPROVED_MERGE_SHA,
        ),
    )


def _initialize(root: Path, bundle):
    return initialize_world_from_contributions(
        root,
        plan=_plan(bundle),
        contributions=list(bundle.contributions),
        actor=ACTOR,
    )


def _semantic() -> dict:
    return {
        "canon_state": "played_canon",
        "lifecycle_state": "candidate",
        "evidence_role": "source_evidence",
        "authority_state": "system_derived",
        "visibility_state": "gm_private",
    }


def _evidence(suffix: str) -> dict:
    return {
        "source_ref_id": f"ref:{suffix}",
        "source_artifact_id": "artifact:recap:longmont-c2:session-22",
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


def _node(node_id: str, label: str, node_type: str, suffix: str, description: str) -> dict:
    return {
        "node_id": node_id,
        "label": label,
        "node_type": node_type,
        "description": description,
        "importance": "medium",
        "semantic_state": _semantic(),
        "evidence_refs": [_evidence(suffix)],
        "proposed_action": "create",
        "confidence": "medium",
        "warnings": [],
    }


def _candidate_graph() -> dict:
    return {
        "schema": CANDIDATE_GRAPH_PREVIEW_SCHEMA,
        "version": CANDIDATE_GRAPH_PREVIEW_VERSION,
        "preview_id": "preview:test-identity-gate",
        "session_id": "session-22",
        "campaign_id": "longmont-c2",
        "source_artifact_ids": ["artifact:recap:longmont-c2:session-22"],
        "status": "preview",
        "nodes": [
            _node("node:caelynn", "Caelynn", "character", "001", "PC"),
            _node("loc_mireward", "Mireward", "location", "002", "Town"),
            _node("obj_session22_vial", "vial", "item", "006", "Puddle sample vial"),
            _node("mystery_puddles", "Magic puddles", "mystery", "007", "Delayed reflections"),
        ],
        "edges": [
            {
                "edge_id": "e33",
                "from_node_id": "obj_session22_vial",
                "to_node_id": "mystery_puddles",
                "relationship_type": "linked_to",
                "label": "linked to",
                "semantic_state": _semantic(),
                "evidence_refs": [_evidence("007")],
                "proposed_action": "create",
                "confidence": "medium",
                "warnings": [],
            }
        ],
        "beats": [],
        "proposed_writes": [],
        "ignored_items": [],
        "deferred_items": [],
        "diagnostics": _diagnostics(),
    }


def test_identity_gate_attaches_existing_and_creates_new(
    tmp_path: Path, loaded_bundle
) -> None:
    _initialize(tmp_path, loaded_bundle)
    preview = candidate_graph_preview_from_dict(_candidate_graph())
    gate = gate_candidate_graph_against_head(
        preview,
        root=tmp_path,
        world_id=WORLD_ID,
        source_revision_id="sha256:testdigest001",
    )
    assert gate.parent_revision_id.startswith("rev:")
    assert gate.node_id_map["node:caelynn"] == "pc:caelynn"
    assert gate.node_id_map["loc_mireward"] == "location:mireward"
    assert gate.node_id_map["obj_session22_vial"]
    assert gate.node_id_map["mystery_puddles"]
    assert gate.identity_outcome_snapshot["node:caelynn"] == "resolved_existing"

    outcomes = {
        a.subject_node_id: a.identity_resolution_outcome
        for a in gate.accepted_proposals
        if a.assertion_kind == "node"
    }
    assert outcomes["pc:caelynn"] == "resolved_existing"
    assert outcomes["location:mireward"] == "resolved_existing"
    assert outcomes[gate.node_id_map["obj_session22_vial"]] == "created_new"

    edge_proposals = [
        a for a in gate.accepted_proposals if a.assertion_kind == "edge"
    ]
    assert len(edge_proposals) == 1
    assert edge_proposals[0].subject_node_id == gate.node_id_map["obj_session22_vial"]
    assert edge_proposals[0].target_node_id == gate.node_id_map["mystery_puddles"]
    assert gate.scorer_report["matched"]
    assert "unresolved_ambiguity" in gate.scorer_report


def test_ambiguous_identity_parks_unresolved(tmp_path: Path, loaded_bundle) -> None:
    _initialize(tmp_path, loaded_bundle)
    graph = {
        "schema": CANDIDATE_GRAPH_PREVIEW_SCHEMA,
        "version": CANDIDATE_GRAPH_PREVIEW_VERSION,
        "preview_id": "preview:test-collision",
        "session_id": "session-22",
        "campaign_id": "longmont-c2",
        "source_artifact_ids": ["artifact:recap:longmont-c2:session-22"],
        "status": "preview",
        "nodes": [
            _node("item_named_caelynn", "Caelynn", "item", "001", "Wrong kind"),
        ],
        "edges": [],
        "beats": [],
        "proposed_writes": [],
        "ignored_items": [],
        "deferred_items": [],
        "diagnostics": _diagnostics(),
    }
    gate = gate_candidate_graph_against_head(
        candidate_graph_preview_from_dict(graph),
        root=tmp_path,
        world_id=WORLD_ID,
        source_revision_id="sha256:testdigest002",
    )
    assert gate.accepted_proposals == []
    assert len(gate.unresolved_mentions) == 1
    assert gate.unresolved_mentions[0].identity_resolution_outcome == "blocked_collision"
    assert "item_named_caelynn" not in gate.node_id_map


def test_partial_edge_selection_rejected(tmp_path: Path, loaded_bundle) -> None:
    _initialize(tmp_path, loaded_bundle)
    gate = gate_candidate_graph_against_head(
        candidate_graph_preview_from_dict(_candidate_graph()),
        root=tmp_path,
        world_id=WORLD_ID,
        source_revision_id="sha256:testdigest004",
        node_ids=["obj_session22_vial", "mystery_puddles"],
    )
    edge = next(a for a in gate.accepted_proposals if a.assertion_kind == "edge")
    vial = next(
        a
        for a in gate.accepted_proposals
        if a.assertion_kind == "node"
        and a.subject_node_id == gate.node_id_map["obj_session22_vial"]
    )
    with pytest.raises(CandidateGraphMappingError, match="target endpoint"):
        build_accepted_contribution_from_proposals(
            gate,
            root=tmp_path,
            accepted_assertion_ids=[vial.assertion_id, edge.assertion_id],
            proposal_digest="digest-a",
        )


def test_edge_only_second_artifact_rejected_by_identity_gate(
    tmp_path: Path, loaded_bundle
) -> None:
    """Node evidence A + edge evidence B must not bypass the single-artifact gate.

    Regression: gate called candidate_graph_to_contribution(include_edges=False)
    then mapped edges without re-checking artifacts.
    """
    _initialize(tmp_path, loaded_bundle)
    payload = _candidate_graph()
    art_a = "artifact:recap:longmont-c2:session-22"
    art_b = "artifact:recap:longmont-c2:session-22-alt"
    # Top-level and node evidence stay on A; only the edge points at B.
    payload["source_artifact_ids"] = [art_a]
    for node in payload["nodes"]:
        for ref in node["evidence_refs"]:
            ref["source_artifact_id"] = art_a
    for edge in payload["edges"]:
        for ref in edge["evidence_refs"]:
            ref["source_artifact_id"] = art_b
    with pytest.raises(CandidateGraphMappingError, match="multi-artifact"):
        gate_candidate_graph_against_head(
            candidate_graph_preview_from_dict(payload),
            root=tmp_path,
            world_id=WORLD_ID,
            source_revision_id="sha256:testdigest-edge-artifact",
            source_artifact_id=art_a,
            node_ids=["obj_session22_vial", "mystery_puddles"],
            include_edges=True,
        )


def test_different_selections_produce_different_contribution_ids(
    tmp_path: Path, loaded_bundle
) -> None:
    _initialize(tmp_path, loaded_bundle)
    gate = gate_candidate_graph_against_head(
        candidate_graph_preview_from_dict(_candidate_graph()),
        root=tmp_path,
        world_id=WORLD_ID,
        source_revision_id="sha256:testdigest005",
        node_ids=["obj_session22_vial", "mystery_puddles"],
        include_edges=False,
    )
    nodes = [a for a in gate.accepted_proposals if a.assertion_kind == "node"]
    assert len(nodes) == 2
    # Same proposal digest — selection_digest must still distinguish subsets.
    same_digest = "digest-same-proposal"
    a_only = build_accepted_contribution_from_proposals(
        gate,
        root=tmp_path,
        accepted_assertion_ids=[nodes[0].assertion_id],
        proposal_digest=same_digest,
    )
    both = build_accepted_contribution_from_proposals(
        gate,
        root=tmp_path,
        accepted_assertion_ids=[nodes[0].assertion_id, nodes[1].assertion_id],
        proposal_digest=same_digest,
    )
    assert a_only.contribution_id != both.contribution_id
    assert any(d.startswith("selection_digest:") for d in a_only.diagnostics)


def test_build_accepted_contribution_and_merge(
    tmp_path: Path, loaded_bundle
) -> None:
    init = _initialize(tmp_path, loaded_bundle)
    parent = init.current_head_revision_id or init.initial_head_revision_id
    assert parent is not None
    gate = gate_candidate_graph_against_head(
        candidate_graph_preview_from_dict(_candidate_graph()),
        root=tmp_path,
        world_id=WORLD_ID,
        source_revision_id="sha256:testdigest003",
        node_ids=["obj_session22_vial", "mystery_puddles"],
    )
    contribution = build_accepted_contribution_from_proposals(
        gate,
        root=tmp_path,
        proposal_digest="digest-merge-test",
    )
    assert contribution.accepted_assertions
    assert all(a.acceptance_state == "accepted" for a in contribution.accepted_assertions)
    result = kernel.merge_contribution_to_revision(
        tmp_path,
        world_id=WORLD_ID,
        contribution=contribution,
        expected_parent_revision_id=parent,
    )
    assert result.published is True
    assert result.revision_id != parent
    rebuild = kernel.rebuild_from_contributions(tmp_path, world_id=WORLD_ID, publish=False)
    assert "rebuild_equivalent_to_head" in rebuild.diagnostics
    store = kernel.open_current_world_graph(tmp_path, WORLD_ID)[2]
    vial_id = gate.node_id_map["obj_session22_vial"]
    mystery_id = gate.node_id_map["mystery_puddles"]
    assert vial_id in store.nodes
    assert mystery_id in store.nodes
    assert "pc:caelynn" in store.nodes
