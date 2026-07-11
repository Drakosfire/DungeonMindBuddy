"""PR006A graph-native contribution union spike."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any

import graph_memory.kernel as kernel
from graph_memory.union_supergraph.load import DEFAULT_FIXTURE_PATH, load_union_supergraph_store
WORLD_ID = "eldyrwild"
CAMPAIGN_SCOPE = "longmont-c2"
MIREWARD_ID = "location:mireward"
EVENT_ID = "event:longmont-c2:session-23:mireward-gate-battle"
def _node_assertion(
    *,
    node_id: str,
    label: str,
    kind: str,
    role: str,
    source_artifact_id: str,
) -> kernel.GraphContributionAssertion:
    return kernel.build_assertion(
        assertion_kind="node",
        acceptance_state="accepted",
        subject_node_id=node_id,
        label=label,
        value={
            "kind": kind,
            "role": role,
            "aliases": [label],
            "source_domains": ["manual_seed"],
            "canon_state": "canonical",
        },
        source_artifact_id=source_artifact_id,
        campaign_scope=CAMPAIGN_SCOPE,
        epistemic_kind="fact",
        visibility="gm",
        identity_resolution_outcome="created_new",
    )


def _contributions() -> tuple[kernel.GraphContribution, kernel.GraphContribution, kernel.GraphContributionAssertion]:
    mireward_a = _node_assertion(
        node_id=MIREWARD_ID,
        label="Mireward",
        kind="location",
        role="town",
        source_artifact_id="graph-native:pr006a:support-a",
    )
    mireward_b = _node_assertion(
        node_id=MIREWARD_ID,
        label="Mireward",
        kind="location",
        role="town",
        source_artifact_id="graph-native:pr006a:support-b",
    )
    event = _node_assertion(
        node_id=EVENT_ID,
        label="Mireward Gate Battle",
        kind="event",
        role="encounter",
        source_artifact_id="graph-native:pr006a:support-b",
    )
    occurred_at = kernel.build_assertion(
        assertion_kind="edge",
        acceptance_state="accepted",
        subject_node_id=EVENT_ID,
        target_node_id=MIREWARD_ID,
        predicate="occurred_at",
        label="occurred at",
        value={
            "source_domains": ["manual_seed"],
            "session_ids": ["session-23"],
            "canon_state": "canonical",
        },
        source_artifact_id="graph-native:pr006a:support-b",
        campaign_scope=CAMPAIGN_SCOPE,
        epistemic_kind="fact",
        visibility="gm",
        identity_resolution_outcome="resolved_existing",
    )
    contribution_a = kernel.create_graph_contribution(
        world_id=WORLD_ID,
        source_kind="manual_import",
        source_artifact_id="graph-native:pr006a:support-a",
        source_revision_id="graph-revision:a",
        extraction_profile="pr006a-graph-native-spike-v1",
        campaign_scope=CAMPAIGN_SCOPE,
        accepted_assertions=[mireward_a],
    )
    contribution_b = kernel.create_graph_contribution(
        world_id=WORLD_ID,
        source_kind="manual_import",
        source_artifact_id="graph-native:pr006a:support-b",
        source_revision_id="graph-revision:b",
        extraction_profile="pr006a-graph-native-spike-v1",
        campaign_scope=CAMPAIGN_SCOPE,
        accepted_assertions=[mireward_b, event, occurred_at],
    )
    if mireward_a.assertion_id != mireward_b.assertion_id:
        raise AssertionError("shared Mireward assertions must have one assertion ID")
    return contribution_a, contribution_b, mireward_a
def _invalid_edge_contribution() -> kernel.GraphContribution:
    assertion = kernel.build_assertion(
        assertion_kind="edge",
        acceptance_state="accepted",
        subject_node_id="location:missing",
        target_node_id="location:also-missing",
        predicate="occurred_at",
        label="occurred at",
        value={"source_domains": ["manual_seed"]},
        source_artifact_id="graph-native:pr006a:invalid",
        campaign_scope=CAMPAIGN_SCOPE,
        epistemic_kind="fact",
        visibility="gm",
        identity_resolution_outcome="resolved_existing",
    )
    return kernel.create_graph_contribution(
        world_id=WORLD_ID,
        source_kind="manual_import",
        source_artifact_id="graph-native:pr006a:invalid",
        source_revision_id="graph-revision:invalid",
        extraction_profile="pr006a-graph-native-spike-v1",
        campaign_scope=CAMPAIGN_SCOPE,
        accepted_assertions=[assertion],
    )
def run_spike(root: Path) -> dict[str, Any]:
    """Run the isolated graph-only proof and return its inspected summary."""
    if root.exists():
        raise FileExistsError(f"output root already exists: {root}")
    baseline = kernel.publish_world_revision(
        root,
        WORLD_ID,
        load_union_supergraph_store(DEFAULT_FIXTURE_PATH),
        operation_ids=["pr006a:baseline"],
    )
    contribution_a, contribution_b, mireward = _contributions()
    merged_a = kernel.merge_contribution_to_revision(
        root,
        world_id=WORLD_ID,
        contribution=contribution_a,
        expected_parent_revision_id=baseline.revision.revision_id,
    )
    merged_b = kernel.merge_contribution_to_revision(
        root,
        world_id=WORLD_ID,
        contribution=contribution_b,
        expected_parent_revision_id=merged_a.revision_id,
    )
    head, revision, graph = kernel.open_current_world_graph(root, WORLD_ID)
    support = graph.assertion_support[mireward.assertion_id]
    matching_edges = [
        edge
        for edge in graph.edges.values()
        if edge.source_node_id == EVENT_ID
        and edge.target_node_id == MIREWARD_ID
        and edge.predicate == "occurred_at"
    ]
    if (
        not merged_a.published
        or not merged_b.published
        or MIREWARD_ID not in graph.nodes
        or EVENT_ID not in graph.nodes
        or len(matching_edges) != 1
        or matching_edges[0].session_ids != ["session-23"]
        or set(support["active_contribution_ids"])
        != {contribution_a.contribution_id, contribution_b.contribution_id}
        or set(support["source_artifact_ids"])
        != {
            "graph-native:pr006a:support-a",
            "graph-native:pr006a:support-b",
        }
    ):
        raise AssertionError("valid graph-native union guarantees failed")

    world_health = kernel.build_world_integrity_report(root, WORLD_ID)
    contribution_health = kernel.build_contribution_integrity_report(
        root, world_id=WORLD_ID, check_rebuild=True
    )
    rebuilt = kernel.rebuild_from_contributions(root, world_id=WORLD_ID, publish=False)
    if not (
        world_health.load_ok
        and world_health.validation_ok
        and contribution_health.rebuild_equivalent_to_head
        and "rebuild_equivalent_to_head" in rebuilt.diagnostics
    ):
        raise AssertionError("integrity or rebuild guarantee failed")

    failed = kernel.merge_contribution_to_revision(
        root, world_id=WORLD_ID, contribution=_invalid_edge_contribution()
    )
    final_head, final_revision, final_graph = kernel.open_current_world_graph(root, WORLD_ID)
    failed_health = kernel.build_contribution_integrity_report(root, world_id=WORLD_ID)
    if (
        failed.published
        or final_head.head_revision_id != head.head_revision_id
        or final_revision.revision_id != revision.revision_id
        or MIREWARD_ID not in final_graph.nodes
        or len(matching_edges) != 1
        or failed.contribution_ids[0] not in failed_health.failed_contribution_ids
    ):
        raise AssertionError("failed contribution changed the valid head")

    return {
        "baseline_revision_id": baseline.revision.revision_id,
        "baseline_parent_revision_id": baseline.revision.parent_revision_id,
        "contribution_a_id": contribution_a.contribution_id,
        "revision_a_id": merged_a.revision_id,
        "revision_a_parent_revision_id": merged_a.parent_revision_id,
        "contribution_b_id": contribution_b.contribution_id,
        "final_head_revision_id": final_head.head_revision_id,
        "final_parent_revision_id": final_revision.parent_revision_id,
        "shared_mireward_assertion_id": mireward.assertion_id,
        "node_count": len(final_graph.nodes),
        "edge_count": len(final_graph.edges),
        "shared_support": support,
        "failed_contribution_id": failed.contribution_ids[0],
        "world_integrity": {
            "load_ok": world_health.load_ok,
            "validation_ok": world_health.validation_ok,
        },
        "rebuild_equivalent": True,
    }


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", type=Path, required=True)
    args = parser.parse_args()
    print(json.dumps(run_spike(args.root), sort_keys=True))
if __name__ == "__main__":
    main()
