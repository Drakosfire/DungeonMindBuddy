"""Proofs for the non-publishing Eldyrwild deferred repair authority."""

from __future__ import annotations

import hashlib
import json
import os
import shutil
from pathlib import Path
from typing import Any

import pytest

import graph_memory.kernel as kernel
from apps.live_control_server.config import world_graph_root
from apps.live_control_server.integrations.dungeonmind_kernel.whole_world_conformance import (
    snapshot_world_graph_tree_digest,
)
from apps.live_control_server.services import (
    eldyrwild_relationship_node_kind_source_repair as repair_service,
)
from apps.live_control_server.services import (
    eldyrwild_relationship_semantic_closure as closure_service,
)
from apps.live_control_server.services.eldyrwild_relationship_node_kind_source_repair import (
    ASPECT_SPLIT_SPECS,
    BASE_GRAPH_PAYLOAD_SHA256,
    BASE_REVISION_ID,
    DEFERRED_RESIDUAL_EDGE_IDS,
    EXPECTED_BASE_INVENTORY,
    EXPECTED_PROJECTED_INVENTORY,
    KIND_REPAIR_SPECS,
    LOCKED_MANIFEST_SHA256,
    MANIFEST_RELPATH,
    PREDECESSOR_CLOSURE_ID,
    PREDECESSOR_CLOSURE_MANIFEST_SHA256,
    RelationshipNodeKindSourceRepairError,
    _validate_aspect_split_specs,
    build_relationship_node_kind_source_repair,
    get_relationship_node_kind_source_repair_status,
    prove_isolated_repair_effect,
    verify_relationship_node_kind_source_repair,
)


REPO = Path(__file__).resolve().parents[1]
CLOSURE_DIR = (
    REPO
    / "graph_data"
    / "approved_graph_corrections"
    / "eldyrwild"
    / "relationship-semantic-closure-v1"
)


def _clone_world(tmp_path: Path) -> Path:
    source_root = world_graph_root()
    source_world = source_root / "graph_memory" / "worlds" / "eldyrwild"
    if not source_world.is_dir():
        pytest.skip("Eldyrwild world graph not present")
    destination = tmp_path / "graph_memory" / "worlds"
    destination.mkdir(parents=True)
    shutil.copytree(source_world, destination / "eldyrwild")
    runs = source_root / "graph_memory" / "runs"
    if runs.is_dir():
        os.symlink(runs, tmp_path / "graph_memory" / "runs")
    return tmp_path


def _clone_repo(tmp_path: Path) -> Path:
    repository = tmp_path / "repo"
    shutil.copytree(CLOSURE_DIR, repository / CLOSURE_DIR.relative_to(REPO))
    return repository


def _manifest(repo: Path = REPO) -> dict[str, Any]:
    return json.loads((repo / MANIFEST_RELPATH).read_text(encoding="utf-8"))


def test_manifest_and_predecessor_base_pins_are_exact() -> None:
    manifest = _manifest()
    assert hashlib.sha256(
        (REPO / MANIFEST_RELPATH).read_bytes()
    ).hexdigest() == LOCKED_MANIFEST_SHA256
    assert manifest["repair_id"] == "eldyrwild-relationship-node-kind-source-repair-v1"
    assert manifest["base_revision_id"] == BASE_REVISION_ID
    assert manifest["base_graph_payload_sha256"] == BASE_GRAPH_PAYLOAD_SHA256
    assert manifest["predecessor_closure_id"] == PREDECESSOR_CLOSURE_ID
    assert (
        manifest["predecessor_closure_manifest_sha256"]
        == PREDECESSOR_CLOSURE_MANIFEST_SHA256
    )
    predecessor = closure_service._load_manifest(repo=REPO)
    deferred = {
        unit["edge_id"]
        for unit in predecessor["units"]
        if unit.get("deferred")
    }
    assert deferred == DEFERRED_RESIDUAL_EDGE_IDS
    assert manifest["expected_deferred_residual_edge_ids"] == sorted(deferred)


def test_manifest_covers_all_and_only_repairs() -> None:
    manifest = _manifest()
    assert [row["node_id"] for row in manifest["kind_repairs"]] == sorted(
        spec["node_id"] for spec in KIND_REPAIR_SPECS
    )
    assert [row["source_node_id"] for row in manifest["aspect_splits"]] == sorted(
        spec["source_node_id"] for spec in ASPECT_SPLIT_SPECS
    )
    repaired_edges = {
        edge_id
        for row in manifest["kind_repairs"]
        for edge_id in row["affected_deferred_edge_ids"]
    }
    split_edges = {
        edge_id
        for row in manifest["aspect_splits"]
        for edge_id in row["edges_rewired_to_aspect"]
    }
    assert repaired_edges | split_edges == DEFERRED_RESIDUAL_EDGE_IDS
    assert not repaired_edges & split_edges


def test_kind_repairs_are_source_supported() -> None:
    manifest = _manifest()
    for row in manifest["kind_repairs"]:
        assert row["current_kind"] != row["corrected_kind"]
        assert row["source_contribution_ids"]
        assert row["source_contribution_payload_sha256"]
        assert row["source_artifact_ids"]
        assert row["source_seals"]
        assert row["kind_basis"]["closure_unit_ids"]
        assert row["kind_basis"]["seal_excerpt_refs"]
        assert "adapter admission" in row["kind_basis"]["note"]
        assert all(
            proof["disposition"] == "ENDPOINT_ADMISSION_GAP"
            for proof in row["admissibility_before"]
        )
        assert all(
            proof["disposition"] == "EXISTING_EXPLICIT_ADAPTER"
            for proof in row["admissibility_after"]
        )


def test_aspect_split_conflicts_fail_closed(tmp_path: Path) -> None:
    root = _clone_world(tmp_path)
    store = kernel.load_world_graph_revision(root, "eldyrwild", BASE_REVISION_ID)
    conflicting = list(ASPECT_SPLIT_SPECS) + [dict(ASPECT_SPLIT_SPECS[0])]
    with pytest.raises(RelationshipNodeKindSourceRepairError) as excinfo:
        _validate_aspect_split_specs(store, conflicting)
    assert excinfo.value.code == "aspect_split_conflict"


def test_status_requires_exact_base(tmp_path: Path) -> None:
    root = _clone_world(tmp_path)
    status = get_relationship_node_kind_source_repair_status(root, repo=REPO)
    assert status.eligibility == "eligible"
    assert status.head_revision_id == BASE_REVISION_ID
    assert status.base_inventory == EXPECTED_BASE_INVENTORY
    assert set(status.residual_edge_ids) == DEFERRED_RESIDUAL_EDGE_IDS

    head_path = root / "graph_memory" / "worlds" / "eldyrwild" / "head.json"
    head = json.loads(head_path.read_text(encoding="utf-8"))
    head["head_revision_id"] = head["head_revision_id"]  # retain valid JSON shape
    head["head_revision_id"] = "rev:a0d76578e9c3d51e8d4c6b05ffe87051"
    head_path.write_text(json.dumps(head), encoding="utf-8")
    stale = get_relationship_node_kind_source_repair_status(root, repo=REPO)
    assert stale.eligibility == "ineligible"
    assert "stale_base" in stale.diagnostics


def test_isolated_overlay_proves_projected_inventory(tmp_path: Path) -> None:
    root = _clone_world(tmp_path)
    proof = prove_isolated_repair_effect(root, repo=REPO)
    assert proof.passed
    assert proof.all_deferred_edges_admitted
    assert proof.zero_regressions
    assert proof.base_inventory == EXPECTED_BASE_INVENTORY
    assert proof.projected_inventory == EXPECTED_PROJECTED_INVENTORY
    assert len(proof.deferred_edge_proofs) == 9
    assert all(
        row["disposition"] == "EXISTING_EXPLICIT_ADAPTER"
        for row in proof.deferred_edge_proofs
    )


def test_build_is_non_publishing_and_atomic(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    root = _clone_world(tmp_path)
    repository = _clone_repo(tmp_path)
    calls: list[str] = []

    def fail_publish(*args: Any, **kwargs: Any) -> None:
        calls.append("publish")
        raise AssertionError("repair authority must not publish")

    monkeypatch.setattr(repair_service.kernel, "publish_world_revision", fail_publish)
    first = build_relationship_node_kind_source_repair(root=root, repo=repository)
    first_bytes = (repository / MANIFEST_RELPATH).read_bytes()
    second = build_relationship_node_kind_source_repair(root=root, repo=repository)
    second_bytes = (repository / MANIFEST_RELPATH).read_bytes()
    assert first.manifest_sha256 == second.manifest_sha256
    assert first_bytes == second_bytes
    assert first.proof.passed and second.proof.passed
    assert calls == []


def test_tampered_manifest_fails_verify(tmp_path: Path) -> None:
    root = _clone_world(tmp_path)
    repository = _clone_repo(tmp_path)
    build_relationship_node_kind_source_repair(root=root, repo=repository)
    path = repository / MANIFEST_RELPATH
    raw = path.read_text(encoding="utf-8")
    path.write_text(raw.replace('"semantic": 323', '"semantic": 322', 1), encoding="utf-8")
    assert verify_relationship_node_kind_source_repair(root=root, repo=repository) is None


def test_verify_rejects_stale_head(tmp_path: Path) -> None:
    root = _clone_world(tmp_path)
    repository = _clone_repo(tmp_path)
    build_relationship_node_kind_source_repair(root=root, repo=repository)
    head_path = root / "graph_memory" / "worlds" / "eldyrwild" / "head.json"
    head = json.loads(head_path.read_text(encoding="utf-8"))
    head["head_revision_id"] = "rev:a0d76578e9c3d51e8d4c6b05ffe87051"
    head_path.write_text(json.dumps(head), encoding="utf-8")
    assert verify_relationship_node_kind_source_repair(root=root, repo=repository) is None


def test_live_root_hash_and_sample_unchanged_by_build_verify() -> None:
    root = world_graph_root()
    before_digest = snapshot_world_graph_tree_digest(root, "eldyrwild")
    before_head = kernel.open_world_graph_head(root, "eldyrwild").head_revision_id
    before_kind = kernel.load_world_graph_revision(
        root, "eldyrwild", BASE_REVISION_ID
    ).nodes["loc:wizard_college"].kind
    built = build_relationship_node_kind_source_repair(
        root=root,
        repo=REPO,
        allow_live_world=True,
    )
    assert built.proof.passed
    assert verify_relationship_node_kind_source_repair(root=root, repo=REPO) is not None
    after_digest = snapshot_world_graph_tree_digest(root, "eldyrwild")
    after_head = kernel.open_world_graph_head(root, "eldyrwild").head_revision_id
    after_kind = kernel.load_world_graph_revision(
        root, "eldyrwild", BASE_REVISION_ID
    ).nodes["loc:wizard_college"].kind
    assert before_digest == after_digest
    assert before_head == after_head == BASE_REVISION_ID
    assert before_kind == after_kind == "location"


def test_manifest_split_rows_include_retained_and_rewired_proofs() -> None:
    manifest = _manifest()
    for row in manifest["aspect_splits"]:
        before = {proof["edge_id"] for proof in row["admissibility_before"]}
        after = {proof["edge_id"] for proof in row["admissibility_after"]}
        assert before == after
        assert set(row["edges_rewired_to_aspect"]) <= before
        assert set(row["edges_retained_on_source"]) <= before
        assert row["split_basis"]["kernel_split_identity_insufficient"] is True


def test_verify_returns_projected_pin(tmp_path: Path) -> None:
    root = _clone_world(tmp_path)
    repository = _clone_repo(tmp_path)
    build_relationship_node_kind_source_repair(root=root, repo=repository)
    pin = verify_relationship_node_kind_source_repair(root=root, repo=repository)
    assert pin is not None
    assert pin.projected_inventory == EXPECTED_PROJECTED_INVENTORY
    assert pin.base_graph_payload_sha256 == BASE_GRAPH_PAYLOAD_SHA256
