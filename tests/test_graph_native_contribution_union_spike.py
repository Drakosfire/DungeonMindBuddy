from __future__ import annotations

from scripts.spike_graph_native_contribution_union import (
    EVENT_ID,
    MIREWARD_ID,
    WORLD_ID,
    _contributions,
    run_spike,
)

import graph_memory.kernel as kernel


def test_graph_native_contributions_union_and_rebuild(tmp_path) -> None:
    contribution_a, contribution_b, mireward = _contributions()
    assert mireward.assertion_id == contribution_b.accepted_assertions[0].assertion_id
    assert contribution_a.contribution_id != contribution_b.contribution_id

    summary = run_spike(tmp_path / "spike")
    head, revision, graph = kernel.open_current_world_graph(tmp_path / "spike", WORLD_ID)
    support = graph.assertion_support[mireward.assertion_id]
    edges = [
        edge
        for edge in graph.edges.values()
        if edge.source_node_id == EVENT_ID
        and edge.target_node_id == MIREWARD_ID
        and edge.predicate == "occurred_at"
    ]
    contribution_health = kernel.build_contribution_integrity_report(
        tmp_path / "spike", world_id=WORLD_ID, check_rebuild=True
    )

    assert list(graph.nodes).count(MIREWARD_ID) == 1
    assert {contribution_a.contribution_id, contribution_b.contribution_id} == set(
        support["active_contribution_ids"]
    )
    assert set(support["source_artifact_ids"]) == {
        "graph-native:pr006a:support-a",
        "graph-native:pr006a:support-b",
    }
    assert len(edges) == 1
    assert edges[0].session_ids == ["session-23"]
    assert revision.revision_id == summary["final_head_revision_id"] == head.head_revision_id
    assert revision.parent_revision_id == summary["revision_a_id"]
    assert contribution_health.failed_contribution_ids == [summary["failed_contribution_id"]]
    assert contribution_health.rebuild_equivalent_to_head is True


def test_spike_refuses_existing_output_root(tmp_path) -> None:
    root = tmp_path / "spike"
    root.mkdir()
    try:
        run_spike(root)
    except FileExistsError:
        pass
    else:
        raise AssertionError("existing output root must be rejected")
