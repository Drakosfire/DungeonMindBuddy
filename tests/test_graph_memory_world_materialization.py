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
    _local_graph_fingerprint,
    materialize_world_graph,
    verify_rebuild,
)

REPO_ROOT = Path(__file__).resolve().parents[1]
MINIMAL_MANIFEST = (
    REPO_ROOT / "tests/fixtures/graph_memory/pr006/minimal_acceptance_manifest.json"
)
MINIMAL_BUNDLE = REPO_ROOT / "tests/fixtures/graph_memory/pr006/minimal_candidate_bundle.json"


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
    assert report["baseline_revision_id"] is not None
    head = kernel.open_world_graph_head(tmp_path, "eldyrwild")
    assert head.head_revision_id == report["head_revision_id"]


def test_merge_failure_leaves_prior_head_readable(tmp_path: Path) -> None:
    first = materialize_world_graph(
        repo_root=REPO_ROOT,
        store_root=tmp_path,
        manifest_path=MINIMAL_MANIFEST,
        bundle_path=MINIMAL_BUNDLE,
        fresh_root=True,
    )
    parent = first["head_revision_id"]

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
    materialize_world_graph(
        repo_root=REPO_ROOT,
        store_root=tmp_path,
        manifest_path=MINIMAL_MANIFEST,
        bundle_path=MINIMAL_BUNDLE,
        fresh_root=True,
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


def test_idempotent_replay_preserves_head_fingerprint_and_contributions(
    tmp_path: Path,
) -> None:
    first = materialize_world_graph(
        repo_root=REPO_ROOT,
        store_root=tmp_path,
        manifest_path=MINIMAL_MANIFEST,
        bundle_path=MINIMAL_BUNDLE,
        fresh_root=True,
    )
    head = first["head_revision_id"]
    _h, _r, store = kernel.open_current_world_graph(tmp_path, "eldyrwild")
    fp_before = _local_graph_fingerprint(store)
    contrib_before = first["active_contribution_count"]

    second = materialize_world_graph(
        repo_root=REPO_ROOT,
        store_root=tmp_path,
        manifest_path=MINIMAL_MANIFEST,
        bundle_path=MINIMAL_BUNDLE,
        fresh_root=False,
        expected_parent_revision_id=head,
    )
    _h2, _r2, store2 = kernel.open_current_world_graph(tmp_path, "eldyrwild")
    fp_after = _local_graph_fingerprint(store2)

    assert second["head_revision_id"] == head
    assert fp_after == fp_before
    assert second["active_contribution_count"] == contrib_before
    assert second["duplicate_graph_state_created"] is False


def test_fresh_baseline_is_empty_before_merges(tmp_path: Path) -> None:
    report = materialize_world_graph(
        repo_root=REPO_ROOT,
        store_root=tmp_path,
        manifest_path=MINIMAL_MANIFEST,
        bundle_path=MINIMAL_BUNDLE,
        fresh_root=True,
    )
    baseline_id = report["baseline_revision_id"]
    assert baseline_id
    baseline = kernel.load_world_graph_revision(tmp_path, "eldyrwild", baseline_id)
    assert baseline.nodes == {}
    assert baseline.edges == {}
    assert baseline.evidence == {}
    assert baseline.source_artifacts == {}
    assert report["node_count"] > 0
    assert report["rebuild_equivalent_to_head"] is True


def test_ambiguous_identity_is_fail_closed_not_created_new(monkeypatch: pytest.MonkeyPatch) -> None:
    from graph_memory.materialization import candidate_to_contribution as c2c
    from graph_memory.union_supergraph.model import (
        UnionSupergraphDiagnostics,
        UnionSupergraphStore,
    )

    store = UnionSupergraphStore(
        **{
            "schema": "dmb_union_supergraph_store_v0",
            "version": "0.1",
            "campaign_id": "longmont-c2",
            "graph_id": "longmont-c2:union-supergraph",
            "graph_domains": ["campaign"],
            "source_domains": ["recap"],
            "focus_session_id": "session-1",
            "nodes": {},
            "edges": {},
            "evidence": {},
            "source_artifacts": {},
            "aliases": {},
            "adjacency": {},
            "assertion_support": {},
            "diagnostics": UnionSupergraphDiagnostics(
                canon_promotion=False,
                approved_memory_write=False,
                corpus_mutation=False,
                production_retrieval=False,
            ),
        }
    )

    def _force_ambiguous(node, **_kwargs):
        return node["node_id"], "ambiguous"

    monkeypatch.setattr(c2c, "_resolve_node_outcome", _force_ambiguous)

    contrib = kernel.create_graph_contribution(
        world_id="eldyrwild",
        source_kind="source_extraction",
        source_artifact_id="artifact:test",
        source_revision_id="rev:test",
        extraction_profile="pr006-acceptance-v1",
        accepted_assertions=[
            kernel.build_assertion(
                assertion_kind="node",
                acceptance_state="accepted",
                subject_node_id="npc_x",
                label="Mystery",
                value={"kind": "npc", "aliases": ["Mystery"], "node_id": "npc_x"},
                identity_resolution_outcome="created_new",
            ),
            kernel.build_assertion(
                assertion_kind="edge",
                acceptance_state="accepted",
                subject_node_id="npc_x",
                target_node_id="loc_y",
                predicate="located_in",
                label="located in",
                value={},
                identity_resolution_outcome="created_new",
            ),
        ],
    )
    resolved = c2c.resolve_contribution_identities(
        contrib, store, world_id="eldyrwild"
    )
    assert all(
        a.identity_resolution_outcome != "created_new"
        for a in resolved.accepted_assertions
        if a.assertion_kind == "node"
    )
    assert not any(a.assertion_kind == "node" for a in resolved.accepted_assertions)
    assert any(
        a.acceptance_state == "rejected" and a.identity_resolution_outcome == "ambiguous"
        for a in resolved.rejected_assertions
        if a.assertion_kind == "node"
    )
    assert any(
        a.acceptance_state == "rejected" and a.assertion_kind == "edge"
        for a in resolved.rejected_assertions
    )
    assert any(m.identity_resolution_outcome == "ambiguous" for m in resolved.unresolved_mentions)


def test_bundle_sources_to_contributions_only_includes_accepted() -> None:
    bundle = json.loads(MINIMAL_BUNDLE.read_text(encoding="utf-8"))
    contribs = bundle_sources_to_contributions(bundle)
    accepted = [s for s in bundle["sources"] if s["status"] == "accepted"]
    assert len(contribs) == len(accepted)


def test_world_root_leaves_are_optional_in_inventory() -> None:
    from graph_memory.materialization.acceptance_manifest import (
        build_inventory,
        load_acceptance_manifest,
    )

    manifest = load_acceptance_manifest(MINIMAL_MANIFEST)
    inventory = build_inventory(
        manifest, repo_root=REPO_ROOT, manifest_path=MINIMAL_MANIFEST
    )
    world_items = [
        item for item in inventory["source_items"] if item["domain"] == "worldbuilding"
    ]
    required = [item for item in world_items if item["required"]]
    optional = [item for item in world_items if not item["required"]]
    assert len(required) == 1
    assert required[0]["path"].endswith("/Mirathorn/README.md")
    assert optional
    assert any(item["path"].endswith("Sewer Traps.md") for item in optional)
