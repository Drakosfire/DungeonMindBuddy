"""Tests for world materialization orchestration (PR006)."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

import graph_memory.kernel as kernel
from graph_memory.materialization.acceptance_manifest import AcceptanceManifestError
from graph_memory.materialization.candidate_to_contribution import (
    bundle_sources_to_contributions,
)
from graph_memory.materialization.world_materializer import (
    build_pr006_baseline_store,
    materialize_world_graph,
    verify_rebuild,
)

REPO_ROOT = Path(__file__).resolve().parents[1]
MINIMAL_MANIFEST = (
    REPO_ROOT / "tests/fixtures/graph_memory/pr006/minimal_acceptance_manifest.json"
)
MINIMAL_BUNDLE = REPO_ROOT / "tests/fixtures/graph_memory/pr006/minimal_candidate_bundle.json"


def test_baseline_passes_union_fixture_validation() -> None:
    store = build_pr006_baseline_store()
    assert store.focus_session_id == "session-23"
    assert "pc_caelynn" in store.nodes


def test_materialize_fresh_root_publishes_head(tmp_path: Path) -> None:
    report = materialize_world_graph(
        repo_root=REPO_ROOT,
        store_root=tmp_path,
        manifest_path=MINIMAL_MANIFEST,
        bundle_path=MINIMAL_BUNDLE,
        fresh_root=True,
    )
    assert report["node_count"] > 0
    assert report["edge_count"] > 0
    assert report["rebuild_equivalent_to_head"] is True
    head = kernel.open_world_graph_head(tmp_path, "eldyrwild")
    assert head.head_revision_id == report["head_revision_id"]


def test_merge_failure_leaves_prior_head_readable(tmp_path: Path) -> None:
    store = build_pr006_baseline_store()
    published = kernel.publish_world_revision(
        tmp_path,
        "eldyrwild",
        store,
        operation_ids=["op:test-baseline"],
    )
    parent = published.revision.revision_id

    bad = kernel.create_graph_contribution(
        world_id="eldyrwild",
        source_kind="source_extraction",
        source_artifact_id="artifact:bad",
        source_revision_id="rev:bad",
        extraction_profile="pr006-acceptance-v1",
        accepted_assertions=[
            kernel.build_assertion(
                assertion_kind="edge",
                acceptance_state="accepted",
                subject_node_id="missing_a",
                target_node_id="missing_b",
                predicate="related_to",
                label="related",
                value={},
                identity_resolution_outcome="created_new",
            )
        ],
    )
    result = kernel.merge_contribution_to_revision(
        tmp_path,
        world_id="eldyrwild",
        contribution=bad,
        expected_parent_revision_id=parent,
    )
    assert result.published is False
    head = kernel.open_world_graph_head(tmp_path, "eldyrwild")
    assert head.head_revision_id == parent


def test_materialize_requires_expected_parent_when_head_exists(tmp_path: Path) -> None:
    store = build_pr006_baseline_store()
    kernel.publish_world_revision(
        tmp_path,
        "eldyrwild",
        store,
        operation_ids=["op:test-baseline"],
    )
    with pytest.raises(AcceptanceManifestError):
        materialize_world_graph(
            repo_root=REPO_ROOT,
            store_root=tmp_path,
            manifest_path=MINIMAL_MANIFEST,
            bundle_path=MINIMAL_BUNDLE,
            fresh_root=False,
        )


def test_verify_rebuild_equivalent_after_materialize(tmp_path: Path) -> None:
    materialize_world_graph(
        repo_root=REPO_ROOT,
        store_root=tmp_path,
        manifest_path=MINIMAL_MANIFEST,
        bundle_path=MINIMAL_BUNDLE,
        fresh_root=True,
    )
    payload = verify_rebuild(tmp_path, "eldyrwild")
    assert payload["rebuild_equivalent_to_head"] is True


def test_idempotent_replay_sets_duplicate_flag_false(tmp_path: Path) -> None:
    first = materialize_world_graph(
        repo_root=REPO_ROOT,
        store_root=tmp_path,
        manifest_path=MINIMAL_MANIFEST,
        bundle_path=MINIMAL_BUNDLE,
        fresh_root=True,
    )
    head = first["head_revision_id"]
    second = materialize_world_graph(
        repo_root=REPO_ROOT,
        store_root=tmp_path,
        manifest_path=MINIMAL_MANIFEST,
        bundle_path=MINIMAL_BUNDLE,
        fresh_root=False,
        expected_parent_revision_id=head,
    )
    assert second["duplicate_graph_state_created"] is False
