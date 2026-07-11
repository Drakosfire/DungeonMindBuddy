"""Contribution integrity report tests (PR005)."""

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


def test_integrity_report_lists_contribution_support(seeded_root: Path) -> None:
    root = seeded_root
    assertion = kernel.build_assertion(
        assertion_kind="node",
        acceptance_state="accepted",
        subject_node_id="npc_integrity",
        label="Integrity",
        value={
            "kind": "npc",
            "role": "npc",
            "source_domains": ["manual_seed"],
            "aliases": ["Integrity"],
        },
        source_artifact_id="artifact:integrity",
        identity_resolution_outcome="created_new",
    )
    contrib = kernel.create_graph_contribution(
        world_id=WORLD_ID,
        source_kind="source_extraction",
        source_artifact_id="artifact:integrity",
        source_revision_id="src-1",
        extraction_profile="test_profile",
        accepted_assertions=[assertion],
    )
    kernel.merge_contribution_to_revision(root, world_id=WORLD_ID, contribution=contrib)

    # Failed contribution
    bad = kernel.build_assertion(
        assertion_kind="edge",
        acceptance_state="accepted",
        subject_node_id="nope_a",
        target_node_id="nope_b",
        predicate="related_to",
        identity_resolution_outcome="created_new",
    )
    bad_contrib = kernel.create_graph_contribution(
        world_id=WORLD_ID,
        source_kind="source_extraction",
        source_artifact_id="artifact:bad-integrity",
        source_revision_id="src-bad",
        extraction_profile="test_profile",
        accepted_assertions=[bad],
    )
    failed = kernel.merge_contribution_to_revision(
        root, world_id=WORLD_ID, contribution=bad_contrib
    )
    assert failed.published is False

    # Supersede away a second assertion to create unsupported state
    y = kernel.build_assertion(
        assertion_kind="node",
        acceptance_state="accepted",
        subject_node_id="npc_temp",
        label="Temp",
        value={
            "kind": "npc",
            "role": "npc",
            "source_domains": ["manual_seed"],
            "aliases": ["Temp"],
        },
        source_artifact_id="artifact:temp",
        source_revision_id="src-a",
        identity_resolution_outcome="created_new",
    )
    a = kernel.create_graph_contribution(
        world_id=WORLD_ID,
        source_kind="source_extraction",
        source_artifact_id="artifact:temp",
        source_revision_id="src-a",
        extraction_profile="test_profile",
        accepted_assertions=[y],
    )
    kernel.merge_contribution_to_revision(root, world_id=WORLD_ID, contribution=a)
    b = kernel.create_graph_contribution(
        world_id=WORLD_ID,
        source_kind="source_extraction",
        source_artifact_id="artifact:temp",
        source_revision_id="src-b",
        extraction_profile="test_profile",
        accepted_assertions=[],
        supersedes_contribution_id=a.contribution_id,
    )
    kernel.supersede_graph_contribution(
        root,
        world_id=WORLD_ID,
        new_contribution=b,
        superseded_contribution_id=a.contribution_id,
    )

    report = kernel.build_contribution_integrity_report(
        root, world_id=WORLD_ID, check_rebuild=True
    )
    assert report.world_id == WORLD_ID
    assert report.head_revision_id is not None
    assert report.contribution_count >= 3
    assert report.active_contribution_count >= 1
    assert bad_contrib.contribution_id in report.failed_contribution_ids
    assert assertion.assertion_id in report.assertion_introduced_by
    assert (
        report.assertion_introduced_by[assertion.assertion_id]
        == contrib.contribution_id
    )
    assert contrib.contribution_id in report.assertion_active_support.get(
        assertion.assertion_id, []
    )
    assert y.assertion_id in report.unsupported_assertion_ids
    assert report.rebuild_equivalent_to_head is True
