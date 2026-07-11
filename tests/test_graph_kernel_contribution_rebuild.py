"""Contribution rebuild tests (PR005)."""

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
def seeded_root(tmp_path: Path):
    store = load_union_supergraph_store(DEFAULT_FIXTURE_PATH)
    kernel.publish_world_revision(
        tmp_path,
        WORLD_ID,
        store,
        operation_ids=["op:baseline-seed"],
    )
    return tmp_path


def test_rebuild_from_contributions_matches_head_for_fixture(seeded_root: Path) -> None:
    root = seeded_root
    assertion = kernel.build_assertion(
        assertion_kind="node",
        acceptance_state="accepted",
        subject_node_id="npc_rebuild",
        label="Rebuild NPC",
        value={
            "kind": "npc",
            "role": "npc",
            "source_domains": ["manual_seed"],
            "aliases": ["Rebuild NPC"],
        },
        source_artifact_id="artifact:rebuild",
        campaign_scope="longmont-c2",
        epistemic_kind="fact",
        visibility="gm",
        identity_resolution_outcome="created_new",
    )
    authored = kernel.create_graph_contribution(
        world_id=WORLD_ID,
        source_kind="graph_review_authored_assertion",
        source_artifact_id="artifact:rebuild",
        source_revision_id="authored-1",
        authored_by="gm",
        accepted_assertions=[assertion],
    )
    merge = kernel.merge_contribution_to_revision(
        root, world_id=WORLD_ID, contribution=authored
    )
    assert merge.published is True

    # Apply an identity decision on a pair of fixture nodes and ensure rebuild keeps it.
    _head, _rev, store = kernel.open_current_world_graph(root, WORLD_ID)
    # Use a harmless alias decision recorded on the store (human override record).
    decision = kernel.build_identity_decision_record(
        world_id=WORLD_ID,
        decision_kind="human_override",
        actor="gm",
        reason="confirm rebuild npc",
        subject_node_id="npc_rebuild",
        source_candidate_id="candidate:rebuild",
    )
    store = kernel.record_identity_decision(store, decision)
    published = kernel.publish_world_revision(
        root,
        WORLD_ID,
        store,
        operation_ids=[decision.decision_id],
        expected_parent_revision_id=merge.revision_id,
    )
    assert published.revision.revision_id

    result = kernel.rebuild_from_contributions(root, world_id=WORLD_ID, publish=False)
    assert "rebuild_equivalent_to_head" in result.diagnostics
    assert authored.contribution_id in result.contribution_ids

    _h2, _r2, head_store = kernel.open_current_world_graph(root, WORLD_ID)
    assert "npc_rebuild" in head_store.nodes
    decision_ids = {
        item.get("decision_id") for item in head_store.identity_decisions
    }
    assert decision.decision_id in decision_ids
