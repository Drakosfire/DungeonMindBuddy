"""Unit tests for GraphContribution models and deterministic IDs (PR005)."""

from __future__ import annotations

import graph_memory.kernel as kernel
from graph_memory.kernel.contributions import semantic_assertion_value


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
    assert kernel.compute_assertion_id(**kwargs) == kernel.compute_assertion_id(
        **kwargs
    )


def test_assertion_identity_excludes_only_top_level_provenance() -> None:
    value = {
        "kind": "location",
        "role": "town",
        "source_domains": ["worldbuilding"],
        "source_artifacts": [{"source_artifact_id": "artifact:worldbuilding"}],
        "evidence": [{"evidence_ref_id": "evidence:worldbuilding:mireward"}],
        "nested": {"source_domain": "semantic-vocabulary"},
    }
    original = {
        "kind": "location",
        "role": "town",
        "source_domains": ["worldbuilding"],
        "source_artifacts": [{"source_artifact_id": "artifact:worldbuilding"}],
        "evidence": [{"evidence_ref_id": "evidence:worldbuilding:mireward"}],
        "nested": {"source_domain": "semantic-vocabulary"},
    }
    common = dict(
        assertion_kind="node",
        acceptance_state="accepted",
        subject_node_id="location:mireward",
        label="Mireward",
        campaign_scope="longmont-c2",
        temporal_scope={"session_id": "session-23"},
        epistemic_kind="fact",
        visibility="gm",
    )
    worldbuilding = kernel.build_assertion(
        **common,
        value=value,
        evidence_ref_ids=["evidence:worldbuilding:mireward"],
        source_artifact_id="artifact:worldbuilding",
        source_revision_id="revision:worldbuilding",
        contribution_id="contribution:worldbuilding",
        identity_resolution_outcome="created_new",
    )
    recap = kernel.build_assertion(
        **common,
        value={
            **value,
            "source_domains": ["recap"],
            "source_artifacts": [{"source_artifact_id": "artifact:recap"}],
            "source_revision_id": "revision:recap",
            "evidence": [{"evidence_ref_id": "evidence:recap:mireward"}],
        },
        evidence_ref_ids=["evidence:recap:mireward"],
        source_artifact_id="artifact:recap",
        source_revision_id="revision:recap",
        contribution_id="contribution:recap",
        identity_resolution_outcome="resolved_existing",
    )

    assert worldbuilding.assertion_id == recap.assertion_id
    assert value == original
    assert semantic_assertion_value(value) == {
        "kind": "location",
        "role": "town",
        "nested": {"source_domain": "semantic-vocabulary"},
    }
    assert value == original


def test_assertion_identity_retains_semantic_scope_and_governance_fields() -> None:
    common = dict(
        assertion_kind="edge",
        subject_node_id="event:mireward-gate-battle",
        target_node_id="location:mireward",
        predicate="occurred_at",
        label="occurred at",
        value={"kind": "event", "role": "battle", "canon_state": "canonical"},
        campaign_scope="longmont-c2",
        temporal_scope={"session_id": "session-23"},
        epistemic_kind="fact",
        visibility="gm",
    )
    expected = kernel.compute_assertion_id(**common)
    variants = [
        {**common, "value": {**common["value"], "role": "aftermath"}},
        {**common, "campaign_scope": "longmont-c1"},
        {**common, "temporal_scope": {"session_id": "session-24"}},
        {**common, "epistemic_kind": "rumor"},
        {**common, "visibility": "player"},
        {**common, "predicate": "happened_near"},
        {**common, "target_node_id": "location:mirathorn"},
    ]

    assert all(
        kernel.compute_assertion_id(**variant) != expected for variant in variants
    )


def test_create_contribution_rekeys_caller_supplied_stale_assertion_id() -> None:
    stale = kernel.build_assertion(
        assertion_kind="node",
        acceptance_state="accepted",
        assertion_id="assertion:stale",
        subject_node_id="location:mireward",
        label="Mireward",
        value={"kind": "location", "role": "town", "source_domains": ["recap"]},
        campaign_scope="longmont-c2",
        epistemic_kind="fact",
        visibility="gm",
    )
    contribution = kernel.create_graph_contribution(
        world_id="eldyrwild",
        source_kind="manual_import",
        source_artifact_id="artifact:mireward",
        source_revision_id="revision:1",
        accepted_assertions=[stale],
    )

    assert contribution.accepted_assertions[0].assertion_id != stale.assertion_id
    assert any(
        diagnostic.startswith("assertion_identity_rekeyed:")
        for diagnostic in contribution.diagnostics
    )
    assert contribution.accepted_assertions[
        0
    ].assertion_id == kernel.compute_assertion_id(
        assertion_kind="node",
        subject_node_id="location:mireward",
        target_node_id=None,
        predicate=None,
        label="Mireward",
        value={"kind": "location", "role": "town", "source_domains": ["recap"]},
        campaign_scope="longmont-c2",
        temporal_scope=None,
        epistemic_kind="fact",
        visibility="gm",
    )


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
