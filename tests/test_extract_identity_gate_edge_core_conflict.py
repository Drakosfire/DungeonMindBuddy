"""Identity-gate rejects same edge_id when core semantics disagree with head."""

from __future__ import annotations

from pathlib import Path

import pytest

import graph_memory.kernel as kernel
from graph_memory.candidate_graph_preview import (
    CANDIDATE_GRAPH_PREVIEW_SCHEMA,
    CANDIDATE_GRAPH_PREVIEW_VERSION,
    candidate_graph_preview_from_dict,
)
from graph_memory.contribution_bundles import load_contribution_bundle
from graph_memory.extract_identity_gate import (
    _active_edge_supports_by_object,
    _edge_core_conflict_diagnostic,
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
ORDERED_CONTRIBUTION_IDS = [
    "contribution:82f23934d8eaca8a",
    "contribution:43782369bd717d32",
    "contribution:33d7cdb0ff623f28",
    "contribution:c086a0b72324ff16",
    "contribution:1227841724520c18",
    "contribution:022187fdefdf4557",
]

SOURCE_NODE_ID = "pc:caelynn"
TARGET_NODE_ID = "threat:tripod-null-calf"
EDGE_ID = f"edge:{SOURCE_NODE_ID}:works_with:{TARGET_NODE_ID}"


@pytest.fixture
def loaded_bundle():
    return load_contribution_bundle(BUNDLE_PATH)


def _initialize(root: Path, bundle) -> None:
    by_id = {item.contribution_id: item for item in bundle.contributions}
    plan = WorldInitializationPlan(
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
    initialize_world_from_contributions(
        root,
        plan=plan,
        contributions=list(bundle.contributions),
        actor="gm",
    )


def _edge_assertion(*, label: str, session_id: str) -> kernel.GraphContributionAssertion:
    source_artifact_id = f"graph-native:test:edge-conflict-{session_id}"
    evidence_ref_id = f"evidence:test:edge-conflict-{session_id}"
    return kernel.build_assertion(
        assertion_kind="edge",
        acceptance_state="accepted",
        subject_node_id=SOURCE_NODE_ID,
        target_node_id=TARGET_NODE_ID,
        predicate="works_with",
        label=label,
        campaign_scope=CAMPAIGN_ID,
        source_artifact_id=source_artifact_id,
        evidence_ref_ids=[evidence_ref_id],
        temporal_scope={"session_id": session_id},
        value={
            "edge_id": EDGE_ID,
            "direction": "outbound",
            "source_domains": ["manual_seed"],
            "session_ids": [session_id],
            "source_domain": "manual_seed",
            "source_artifact_id": source_artifact_id,
            "source_artifacts": [
                {
                    "source_artifact_id": source_artifact_id,
                    "source_domain": "manual_seed",
                    "campaign_id": CAMPAIGN_ID,
                    "uri": f"graph-data://test/{source_artifact_id}",
                }
            ],
            "evidence_ref_ids": [evidence_ref_id],
            "evidence": [
                {
                    "evidence_ref_id": evidence_ref_id,
                    "source_artifact_id": source_artifact_id,
                    "source_domain": "manual_seed",
                    "locator": f"test://{session_id}/{EDGE_ID}",
                }
            ],
        },
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


def _node(node_id: str, label: str, node_type: str, suffix: str) -> dict:
    return {
        "node_id": node_id,
        "label": label,
        "node_type": node_type,
        "description": label,
        "importance": "medium",
        "semantic_state": _semantic(),
        "evidence_refs": [_evidence(suffix)],
        "proposed_action": "create",
        "confidence": "medium",
        "warnings": [],
    }


def test_edge_core_conflict_diagnostic_flags_label_disagreement(
    tmp_path: Path,
    loaded_bundle,
) -> None:
    _initialize(tmp_path, loaded_bundle)
    first = kernel.create_graph_contribution(
        world_id=WORLD_ID,
        source_kind="manual_import",
        source_artifact_id="graph-native:test:edge-conflict-s3",
        source_revision_id="edge-conflict-s3",
        accepted_assertions=[
            _edge_assertion(label="pulls net with", session_id="session-3")
        ],
    )
    merged = kernel.merge_contribution_to_revision(
        tmp_path, world_id=WORLD_ID, contribution=first
    )
    assert merged.published is True

    _head, _rev, store = kernel.open_current_world_graph(tmp_path, WORLD_ID)
    supports = _active_edge_supports_by_object(store)
    assert EDGE_ID in supports

    incoming = _edge_assertion(label="heals", session_id="session-5")
    conflict = _edge_core_conflict_diagnostic(
        incoming,
        root=tmp_path,
        world_id=WORLD_ID,
        supports_by_object=supports,
    )
    assert conflict is not None
    assert conflict.startswith(f"edge_core_semantic_conflict:{EDGE_ID}:")


def test_edge_core_conflict_diagnostic_allows_session_only_drift(
    tmp_path: Path,
    loaded_bundle,
) -> None:
    _initialize(tmp_path, loaded_bundle)
    first = kernel.create_graph_contribution(
        world_id=WORLD_ID,
        source_kind="manual_import",
        source_artifact_id="graph-native:test:edge-ok-s3",
        source_revision_id="edge-ok-s3",
        accepted_assertions=[
            _edge_assertion(label="works with", session_id="session-3")
        ],
    )
    assert kernel.merge_contribution_to_revision(
        tmp_path, world_id=WORLD_ID, contribution=first
    ).published

    _head, _rev, store = kernel.open_current_world_graph(tmp_path, WORLD_ID)
    supports = _active_edge_supports_by_object(store)
    incoming = _edge_assertion(label="works with", session_id="session-5")
    assert (
        _edge_core_conflict_diagnostic(
            incoming,
            root=tmp_path,
            world_id=WORLD_ID,
            supports_by_object=supports,
        )
        is None
    )


def test_identity_gate_rejects_forced_coarse_edge_label_collision(
    tmp_path: Path,
    loaded_bundle,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Even if mapping collapses to one id, gate must reject label disagreement."""
    _initialize(tmp_path, loaded_bundle)
    first = kernel.create_graph_contribution(
        world_id=WORLD_ID,
        source_kind="manual_import",
        source_artifact_id="graph-native:test:gate-conflict-s3",
        source_revision_id="gate-conflict-s3",
        accepted_assertions=[
            _edge_assertion(label="pulls net with", session_id="session-3")
        ],
    )
    assert kernel.merge_contribution_to_revision(
        tmp_path, world_id=WORLD_ID, contribution=first
    ).published

    monkeypatch.setattr(
        "graph_memory.candidate_graph_to_contribution.durable_edge_id_for_observation",
        lambda **_kwargs: EDGE_ID,
    )

    preview = candidate_graph_preview_from_dict(
        {
            "schema": CANDIDATE_GRAPH_PREVIEW_SCHEMA,
            "version": CANDIDATE_GRAPH_PREVIEW_VERSION,
            "preview_id": "preview:edge-conflict-gate",
            "campaign_id": CAMPAIGN_ID,
            "session_id": "session-5",
            "source_artifact_ids": ["artifact:recap:longmont-c2:session-22"],
            "status": "preview",
            "nodes": [
                _node("node:caelynn", "Caelynn", "character", "001"),
                _node("threat_tripod", "Tripod", "threat", "002"),
            ],
            "edges": [
                {
                    "edge_id": "e-heals",
                    "from_node_id": "node:caelynn",
                    "to_node_id": "threat_tripod",
                    "relationship_type": "works_with",
                    "label": "heals",
                    "semantic_state": _semantic(),
                    "evidence_refs": [_evidence("003")],
                    "proposed_action": "create",
                    "confidence": "medium",
                    "warnings": [],
                }
            ],
            "beats": [],
            "proposed_writes": [],
            "ignored_items": [],
            "deferred_items": [],
            "diagnostics": {
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
            },
        }
    )

    gate = gate_candidate_graph_against_head(
        preview,
        root=tmp_path,
        world_id=WORLD_ID,
        source_revision_id="sha256:testdigest-edge-conflict",
        campaign_scope=CAMPAIGN_ID,
        include_edges=True,
    )
    # Map threat_tripod → durable tripoid id; forced EDGE_ID uses TARGET_NODE_ID.
    # Remap monkeypatch to use the durable mapped endpoints' coarse id.
    # After gate mapping, subject becomes pc:caelynn; target becomes whatever
    # durable id threat_tripod resolves to (may be created_new, not tripoid head).
    # Prefer asserting diagnostic + rejected edge with label heals.
    assert any(
        "edge_core_semantic_conflict:" in d for d in gate.diagnostics
    ) or any(
        a.assertion_kind == "edge"
        and a.identity_resolution_outcome == "blocked_collision"
        for a in gate.rejected_assertions
    )
    # Stronger: if threat resolved/created and edge was mapped, it must be rejected
    # when the forced id collides with head.
    heals_rejected = [
        a
        for a in gate.rejected_assertions
        if a.assertion_kind == "edge" and (a.label or "") == "heals"
    ]
    heals_accepted = [
        a
        for a in gate.accepted_proposals
        if a.assertion_kind == "edge" and (a.label or "") == "heals"
    ]
    # Monkeypatched id is EDGE_ID (caelynn→tripod). Gate only checks that id.
    # If threat_tripod became a new node, mapped edge_id under monkeypatch is still
    # EDGE_ID (forced), so conflict should fire against head's EDGE_ID.
    assert heals_rejected
    assert not heals_accepted
    assert heals_rejected[0].identity_resolution_outcome == "blocked_collision"
