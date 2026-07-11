"""Contribution merge / supersession / retraction tests (PR005)."""

from __future__ import annotations

from pathlib import Path

import pytest

import graph_memory.kernel as kernel
from graph_memory.union_supergraph.load import (
    DEFAULT_FIXTURE_PATH,
    load_union_supergraph_store,
)

WORLD_ID = "eldyrwild"


@pytest.fixture
def fixture_store():
    return load_union_supergraph_store(DEFAULT_FIXTURE_PATH)


@pytest.fixture
def seeded_root(tmp_path: Path, fixture_store):
    result = kernel.publish_world_revision(
        tmp_path,
        WORLD_ID,
        fixture_store,
        operation_ids=["op:baseline-seed"],
    )
    return tmp_path, result.revision.revision_id


def _node_assertion(
    *,
    node_id: str,
    label: str,
    source_artifact_id: str,
    source_revision_id: str = "src-rev-1",
):
    return kernel.build_assertion(
        assertion_kind="node",
        acceptance_state="accepted",
        subject_node_id=node_id,
        label=label,
        value={
            "kind": "npc",
            "role": "npc",
            "source_domains": ["manual_seed"],
            "aliases": [label],
            "canon_state": "canonical",
        },
        evidence_ref_ids=[],
        source_artifact_id=source_artifact_id,
        source_revision_id=source_revision_id,
        campaign_scope="longmont-c2",
        epistemic_kind="fact",
        visibility="gm",
        identity_resolution_outcome="created_new",
    )


def test_merge_contribution_publishes_world_revision(seeded_root) -> None:
    root, parent = seeded_root
    assertion = _node_assertion(
        node_id="npc_hester",
        label="Hester",
        source_artifact_id="artifact:authored:hester",
    )
    contribution = kernel.create_graph_contribution(
        world_id=WORLD_ID,
        source_kind="source_extraction",
        source_artifact_id="artifact:authored:hester",
        source_revision_id="src-rev-1",
        extraction_profile="test_profile",
        campaign_scope="longmont-c2",
        accepted_assertions=[assertion],
    )
    result = kernel.merge_contribution_to_revision(
        root,
        world_id=WORLD_ID,
        contribution=contribution,
        expected_parent_revision_id=parent,
    )
    assert result.published is True
    assert result.revision_id is not None
    assert result.parent_revision_id == parent
    assert contribution.contribution_id in result.contribution_ids

    head, revision, store = kernel.open_current_world_graph(root, WORLD_ID)
    assert head.head_revision_id == result.revision_id
    assert revision.parent_revision_id == parent
    assert contribution.contribution_id in revision.operation_ids
    assert "npc_hester" in store.nodes
    assert store.nodes["npc_hester"].label == "Hester"


def test_failed_contribution_merge_leaves_prior_head_readable(seeded_root) -> None:
    root, parent = seeded_root
    # Edge endpoints do not exist → merge fails validation/value error path.
    assertion = kernel.build_assertion(
        assertion_kind="edge",
        acceptance_state="accepted",
        subject_node_id="missing_a",
        target_node_id="missing_b",
        predicate="related_to",
        label="related to",
        value={},
        identity_resolution_outcome="created_new",
    )
    contribution = kernel.create_graph_contribution(
        world_id=WORLD_ID,
        source_kind="source_extraction",
        source_artifact_id="artifact:bad",
        source_revision_id="src-rev-bad",
        extraction_profile="test_profile",
        accepted_assertions=[assertion],
    )
    result = kernel.merge_contribution_to_revision(
        root,
        world_id=WORLD_ID,
        contribution=contribution,
    )
    assert result.published is False
    assert result.revision_id is None
    assert any("merge_failed" in d for d in result.diagnostics)

    head, _rev, store = kernel.open_current_world_graph(root, WORLD_ID)
    assert head.head_revision_id == parent
    assert "missing_a" not in store.nodes


def test_idempotent_reprocessing_does_not_duplicate_graph_state(seeded_root) -> None:
    root, _parent = seeded_root
    assertion = _node_assertion(
        node_id="npc_willow",
        label="Willow",
        source_artifact_id="artifact:willow",
    )
    contribution = kernel.create_graph_contribution(
        world_id=WORLD_ID,
        source_kind="source_extraction",
        source_artifact_id="artifact:willow",
        source_revision_id="src-rev-1",
        extraction_profile="test_profile",
        accepted_assertions=[assertion],
    )
    first = kernel.merge_contribution_to_revision(
        root, world_id=WORLD_ID, contribution=contribution
    )
    assert first.published is True
    _head, _rev, store_after_first = kernel.open_current_world_graph(root, WORLD_ID)
    node_count = len(store_after_first.nodes)
    edge_count = len(store_after_first.edges)
    support = store_after_first.assertion_support[assertion.assertion_id]
    assert support["active_contribution_ids"] == [contribution.contribution_id]

    second = kernel.merge_contribution_to_revision(
        root, world_id=WORLD_ID, contribution=contribution
    )
    assert second.published is False
    assert any("idempotent_noop" in d for d in second.diagnostics)

    _head2, _rev2, store_after_second = kernel.open_current_world_graph(root, WORLD_ID)
    assert len(store_after_second.nodes) == node_count
    assert len(store_after_second.edges) == edge_count
    support2 = store_after_second.assertion_support[assertion.assertion_id]
    assert support2["active_contribution_ids"] == [contribution.contribution_id]


def test_superseded_contribution_retracts_only_unsupported_assertions(seeded_root) -> None:
    root, _ = seeded_root
    assertion_x = _node_assertion(
        node_id="npc_x",
        label="X",
        source_artifact_id="artifact:lineage",
        source_revision_id="src-rev-a",
    )
    assertion_y = _node_assertion(
        node_id="npc_y",
        label="Y",
        source_artifact_id="artifact:lineage",
        source_revision_id="src-rev-a",
    )
    contrib_a = kernel.create_graph_contribution(
        world_id=WORLD_ID,
        source_kind="source_extraction",
        source_artifact_id="artifact:lineage",
        source_revision_id="src-rev-a",
        extraction_profile="test_profile",
        accepted_assertions=[assertion_x, assertion_y],
    )
    merge_a = kernel.merge_contribution_to_revision(
        root, world_id=WORLD_ID, contribution=contrib_a
    )
    assert merge_a.published is True

    assertion_x_b = _node_assertion(
        node_id="npc_x",
        label="X",
        source_artifact_id="artifact:lineage",
        source_revision_id="src-rev-b",
    )
    contrib_b = kernel.create_graph_contribution(
        world_id=WORLD_ID,
        source_kind="source_extraction",
        source_artifact_id="artifact:lineage",
        source_revision_id="src-rev-b",
        extraction_profile="test_profile",
        accepted_assertions=[assertion_x_b],
        supersedes_contribution_id=contrib_a.contribution_id,
    )
    result = kernel.supersede_graph_contribution(
        root,
        world_id=WORLD_ID,
        new_contribution=contrib_b,
        superseded_contribution_id=contrib_a.contribution_id,
    )
    assert result.published is True
    assert contrib_a.contribution_id in result.superseded_contribution_ids

    _head, _rev, store = kernel.open_current_world_graph(root, WORLD_ID)
    support_x = store.assertion_support[assertion_x.assertion_id]
    support_y = store.assertion_support[assertion_y.assertion_id]
    assert support_x["support_state"] == "supported"
    assert contrib_b.contribution_id in support_x["active_contribution_ids"]
    assert support_y["support_state"] in {"unsupported", "retracted"}
    assert support_y["active_contribution_ids"] == []
    assert "npc_x" in store.nodes
    assert store.nodes["npc_y"].state.get("support_state") in {
        "unsupported",
        "retracted",
    }


def test_multi_source_support_preserves_assertion_after_one_retraction(seeded_root) -> None:
    root, _ = seeded_root
    assertion = _node_assertion(
        node_id="npc_shared",
        label="Shared",
        source_artifact_id="artifact:shared-a",
    )
    # Same assertion content → same assertion_id from both contributions.
    contrib_a = kernel.create_graph_contribution(
        world_id=WORLD_ID,
        source_kind="source_extraction",
        source_artifact_id="artifact:shared-a",
        source_revision_id="src-rev-1",
        extraction_profile="test_profile",
        accepted_assertions=[assertion],
    )
    contrib_b = kernel.create_graph_contribution(
        world_id=WORLD_ID,
        source_kind="source_extraction",
        source_artifact_id="artifact:shared-b",
        source_revision_id="src-rev-1",
        extraction_profile="test_profile",
        accepted_assertions=[assertion],
    )
    assert contrib_a.contribution_id != contrib_b.contribution_id

    kernel.merge_contribution_to_revision(
        root, world_id=WORLD_ID, contribution=contrib_a
    )
    kernel.merge_contribution_to_revision(
        root, world_id=WORLD_ID, contribution=contrib_b
    )

    retract = kernel.retract_graph_contribution(
        root,
        world_id=WORLD_ID,
        contribution_id=contrib_a.contribution_id,
        reason="source a withdrawn",
    )
    assert retract.published is True

    _head, _rev, store = kernel.open_current_world_graph(root, WORLD_ID)
    support = store.assertion_support[assertion.assertion_id]
    assert support["support_state"] == "supported"
    assert contrib_b.contribution_id in support["active_contribution_ids"]
    assert contrib_a.contribution_id not in support["active_contribution_ids"]
    assert "npc_shared" in store.nodes
    assert store.nodes["npc_shared"].state.get("memory_state") != "unsupported_assertion"


def test_graph_review_authored_assertion_uses_same_merge_path(seeded_root) -> None:
    root, _ = seeded_root
    assertion = _node_assertion(
        node_id="npc_authored",
        label="Authored NPC",
        source_artifact_id="artifact:graph-review:authored",
    )
    contribution = kernel.create_graph_contribution(
        world_id=WORLD_ID,
        source_kind="graph_review_authored_assertion",
        source_artifact_id="artifact:graph-review:authored",
        source_revision_id="authored-1",
        extraction_profile=None,
        authored_by="gm",
        accepted_assertions=[assertion],
    )
    assert contribution.source_kind == "graph_review_authored_assertion"
    result = kernel.merge_contribution_to_revision(
        root, world_id=WORLD_ID, contribution=contribution
    )
    assert result.published is True
    _head, _rev, store = kernel.open_current_world_graph(root, WORLD_ID)
    node = store.nodes["npc_authored"]
    assert node.state.get("introduced_by_contribution_id") == contribution.contribution_id
    support = store.assertion_support[assertion.assertion_id]
    assert support["introduced_by_contribution_id"] == contribution.contribution_id


def test_ambiguous_identity_contribution_does_not_enter_canonical_graph(seeded_root) -> None:
    root, parent = seeded_root
    mention = kernel.ContributionIdentityMention(
        mention_id="mention:hester",
        label="Hester",
        object_kind="npc",
        identity_resolution_outcome="ambiguous",
        diagnostics=["multiple plausible matches"],
        candidate_node_ids=["npc_a", "npc_b"],
    )
    contribution = kernel.create_graph_contribution(
        world_id=WORLD_ID,
        source_kind="source_extraction",
        source_artifact_id="artifact:ambiguous",
        source_revision_id="src-rev-1",
        extraction_profile="test_profile",
        accepted_assertions=[],
        unresolved_mentions=[mention],
        diagnostics=["ambiguous candidate retained"],
    )
    result = kernel.merge_contribution_to_revision(
        root, world_id=WORLD_ID, contribution=contribution
    )
    assert result.published is True
    assert any("ambiguous" in d for d in result.diagnostics)
    _head, _rev, store = kernel.open_current_world_graph(root, WORLD_ID)
    assert "mention:hester" not in store.nodes
    assert all(nid != "mention:hester" for nid in store.nodes)
    # No new canonical node from the ambiguous mention.
    assert "npc_hester" not in store.nodes


def test_blocked_collision_contribution_does_not_merge(seeded_root) -> None:
    root, parent = seeded_root
    # Accepted assertion marked with blocked_collision outcome must not enter graph.
    assertion = kernel.build_assertion(
        assertion_kind="node",
        acceptance_state="accepted",
        subject_node_id="loc_willow_collision",
        label="Willow",
        value={"kind": "location", "role": "location", "source_domains": ["manual_seed"]},
        identity_resolution_outcome="blocked_collision",
    )
    mention = kernel.ContributionIdentityMention(
        mention_id="mention:willow",
        label="Willow",
        object_kind="location",
        identity_resolution_outcome="blocked_collision",
        diagnostics=["cross-kind collision with npc Willow"],
        candidate_node_ids=["npc_willow_existing"],
    )
    contribution = kernel.create_graph_contribution(
        world_id=WORLD_ID,
        source_kind="source_extraction",
        source_artifact_id="artifact:blocked",
        source_revision_id="src-rev-1",
        extraction_profile="test_profile",
        accepted_assertions=[assertion],
        unresolved_mentions=[mention],
    )
    result = kernel.merge_contribution_to_revision(
        root, world_id=WORLD_ID, contribution=contribution
    )
    assert result.published is True
    _head, _rev, store = kernel.open_current_world_graph(root, WORLD_ID)
    assert "loc_willow_collision" not in store.nodes
    assert any("blocked_collision" in d for d in result.diagnostics)
