"""Unit tests for GraphContribution models and deterministic IDs (PR005)."""

from __future__ import annotations

import graph_memory.kernel as kernel


def test_create_graph_contribution_has_deterministic_id() -> None:
    assertion = kernel.build_assertion(
        assertion_kind="node",
        acceptance_state="accepted",
        subject_node_id="npc_hester",
        label="Hester",
        value={"kind": "npc", "role": "npc", "source_domains": ["manual_seed"]},
        evidence_ref_ids=["evidence:manual:hester"],
        epistemic_kind="fact",
        visibility="gm",
    )
    first = kernel.create_graph_contribution(
        world_id="eldyrwild",
        source_kind="source_extraction",
        source_artifact_id="artifact:recap:s1",
        source_revision_id="rev-src-1",
        extraction_profile="category_v0",
        campaign_scope="longmont-c2",
        accepted_assertions=[assertion],
        produced_at="2026-01-01T00:00:00Z",
    )
    second = kernel.create_graph_contribution(
        world_id="eldyrwild",
        source_kind="source_extraction",
        source_artifact_id="artifact:recap:s1",
        source_revision_id="rev-src-1",
        extraction_profile="category_v0",
        campaign_scope="longmont-c2",
        accepted_assertions=[assertion],
        produced_at="2026-07-10T12:00:00Z",
    )
    assert first.contribution_id == second.contribution_id
    assert first.contribution_id.startswith("contribution:")
    assert first.produced_at != second.produced_at
    assert first.accepted_assertions[0].contribution_id == first.contribution_id


def test_compute_assertion_id_is_stable_for_same_content() -> None:
    kwargs = dict(
        assertion_kind="edge",
        subject_node_id="npc_a",
        target_node_id="loc_b",
        predicate="travels_to",
        label="travels to",
        value={"direction": "outbound"},
        campaign_scope="longmont-c2",
        temporal_scope={"session_id": "session-1"},
        epistemic_kind="fact",
        visibility="gm",
    )
    assert kernel.compute_assertion_id(**kwargs) == kernel.compute_assertion_id(**kwargs)


def test_kernel_exports_pr005_apis_after_pr005() -> None:
    for name in (
        "create_graph_contribution",
        "merge_contribution_to_revision",
        "supersede_graph_contribution",
        "retract_graph_contribution",
        "rebuild_from_contributions",
        "build_contribution_integrity_report",
        "GraphContribution",
        "DurableAssertionSupport",
        "ContributionMergeResult",
    ):
        assert name in kernel.__all__
        assert hasattr(kernel, name)

    for name in (
        "project_world_graph",
        "build_projection_payload",
        "resolve_projection_admissibility",
    ):
        assert name not in kernel.__all__
        assert not hasattr(kernel, name)
