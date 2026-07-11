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


def test_rebuild_loads_identity_decisions_from_ledger_not_head(
    seeded_root: Path, monkeypatch
) -> None:
    """Rebuild must replay decisions from the durable ledger, not the current head."""
    root = seeded_root
    assertion = kernel.build_assertion(
        assertion_kind="node",
        acceptance_state="accepted",
        subject_node_id="npc_ledger_rebuild",
        label="Ledger Rebuild NPC",
        value={
            "kind": "npc",
            "role": "npc",
            "source_domains": ["manual_seed"],
            "aliases": ["Ledger Rebuild NPC"],
        },
        source_artifact_id="artifact:ledger-rebuild",
        campaign_scope="longmont-c2",
        epistemic_kind="fact",
        visibility="gm",
        identity_resolution_outcome="created_new",
    )
    authored = kernel.create_graph_contribution(
        world_id=WORLD_ID,
        source_kind="graph_review_authored_assertion",
        source_artifact_id="artifact:ledger-rebuild",
        source_revision_id="authored-1",
        authored_by="gm",
        accepted_assertions=[assertion],
    )
    merge = kernel.merge_contribution_to_revision(
        root, world_id=WORLD_ID, contribution=authored
    )
    assert merge.published is True

    _head, _rev, store = kernel.open_current_world_graph(root, WORLD_ID)
    decision = kernel.build_identity_decision_record(
        world_id=WORLD_ID,
        decision_kind="human_override",
        actor="gm",
        reason="ledger-backed rebuild decision",
        subject_node_id="npc_ledger_rebuild",
        source_candidate_id="candidate:ledger-rebuild",
    )
    store = kernel.record_identity_decision(store, decision)
    kernel.publish_world_revision(
        root,
        WORLD_ID,
        store,
        operation_ids=[decision.decision_id],
        expected_parent_revision_id=merge.revision_id,
    )

    # Prove collect does not depend on head: empty head identity_decisions while
    # the durable ledger still holds the payload.
    real_load = kernel.load_current_world_graph

    def _load_without_head_decisions(root_path, world_id):
        head, rev, current = real_load(root_path, world_id)
        stripped = current.model_copy(update={"identity_decisions": []})
        return head, rev, stripped

    monkeypatch.setattr(
        "graph_memory.kernel.contribution_rebuild.load_current_world_graph",
        _load_without_head_decisions,
    )
    kernel.rebuild_from_contributions(root, world_id=WORLD_ID, publish=False)

    import json

    ledger_path = (
        root
        / "graph_memory"
        / "worlds"
        / WORLD_ID
        / "identity_decisions"
        / f"{decision.decision_id.replace(':', '__')}.json"
    )
    persisted = json.loads(ledger_path.read_text(encoding="utf-8"))
    assert persisted["reason"] == "ledger-backed rebuild decision"

    report = json.loads(
        (
            root
            / "graph_memory"
            / "worlds"
            / WORLD_ID
            / "contribution_rebuild"
            / "latest.json"
        ).read_text(encoding="utf-8")
    )
    assert decision.decision_id in report["identity_decision_ids"]
