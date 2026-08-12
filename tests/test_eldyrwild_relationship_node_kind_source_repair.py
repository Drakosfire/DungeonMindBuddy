"""Proofs for the non-publishing Eldyrwild Stage-B kind repair authority."""

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
    BASE_GRAPH_PAYLOAD_SHA256,
    BASE_REVISION_ID,
    DEFERRED_RESIDUAL_EDGE_IDS,
    DUAL_SENSE_STOP_SPECS,
    EXPECTED_BASE_INVENTORY,
    EXPECTED_PROJECTED_INVENTORY,
    KIND_REPAIR_SPECS,
    LOCKED_MANIFEST_SHA256,
    MANIFEST_RELPATH,
    PREDECESSOR_CLOSURE_ID,
    PREDECESSOR_CLOSURE_MANIFEST_SHA256,
    RelationshipNodeKindSourceRepairError,
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


def test_manifest_pins_and_stage_b_shape_are_exact() -> None:
    path = REPO / MANIFEST_RELPATH
    manifest = _manifest()
    assert hashlib.sha256(path.read_bytes()).hexdigest() == LOCKED_MANIFEST_SHA256
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
        unit["edge_id"] for unit in predecessor["units"] if unit.get("deferred")
    }
    assert deferred == DEFERRED_RESIDUAL_EDGE_IDS
    assert manifest["expected_deferred_residual_edge_ids"] == sorted(deferred)
    assert manifest["expected_projected_inventory"] == EXPECTED_PROJECTED_INVENTORY
    assert manifest["expected_remaining_residual_edge_ids"] == sorted(
        repair_service.STAGE_B_REMAINING_RESIDUAL_EDGE_IDS
    )
    assert "aspect_splits" not in manifest
    assert not any(
        forbidden in json.dumps(manifest)
        for forbidden in ("aspect_node_id", "aspect_kind", "edges_rewired_to_aspect")
    )


def test_manifest_contains_only_four_source_bound_kind_repairs() -> None:
    manifest = _manifest()
    assert [row["node_id"] for row in manifest["kind_repairs"]] == sorted(
        spec["node_id"] for spec in KIND_REPAIR_SPECS
    )
    repaired_edges = {
        edge_id
        for row in manifest["kind_repairs"]
        for edge_id in row["affected_deferred_edge_ids"]
    }
    assert repaired_edges == {
        "edge:combat_shatter_mages_tower_spider:located_in:item_shatter_mages_tower",
        "edge:loc:stone_bridge:contains:mystery_stone_bridge_river_name",
        "edge:node:torrin_flamescale:serves:loc:guilds:represents",
        "edge:node:torvak_hempdealer_crew:member_of:item:torvak-hemp-caravan",
    }
    for row in manifest["kind_repairs"]:
        assert row["current_kind"] != row["corrected_kind"]
        assert row["source_required_kind"] == row["corrected_kind"]
        assert row["source_contribution_ids"]
        assert row["source_contribution_payload_sha256"]
        assert row["source_artifact_ids"]
        assert row["source_seals"]
        assert row["kind_basis"]["closure_unit_ids"]
        assert row["kind_basis"]["seal_excerpt_refs"]
        assert all(
            proof["disposition"] == "ENDPOINT_ADMISSION_GAP"
            for proof in row["admissibility_before"]
        )
        assert all(
            proof["disposition"] == "EXISTING_EXPLICIT_ADAPTER"
            for proof in row["admissibility_after"]
        )


def test_dual_sense_rows_are_explicit_stops() -> None:
    manifest = _manifest()
    stops = {row["node_id"]: row for row in manifest["deferred_dual_sense_stops"]}
    assert set(stops) == {
        "loc:wizard_college",
        "node:meat_distribution_network_session9",
        "node:hempholm_folk_revelry",
    }
    for spec in DUAL_SENSE_STOP_SPECS:
        row = stops[spec["node_id"]]
        assert row["current_kind"] == spec["current_kind"]
        assert row["deferred_edge_ids"] == sorted(spec["deferred_edge_ids"])
        assert row["retained_effective_edge_ids"] == sorted(
            spec["retained_effective_edge_ids"]
        )
        assert row["source_contribution_ids"]
        assert row["source_seals"]
        assert row["stop_basis"]["kind_only_insufficient"] is True
        assert row["stop_basis"]["proof"]["deferred_edges_admitted"] is True
        assert row["stop_basis"]["proof"]["retained_edges_residual_under_candidate"]


def test_status_is_eligible_on_exact_pin(tmp_path: Path) -> None:
    root = _clone_world(tmp_path)
    status = get_relationship_node_kind_source_repair_status(root, repo=REPO)
    assert status.eligibility == "eligible"
    assert status.head_revision_id == BASE_REVISION_ID
    assert status.base_inventory == EXPECTED_BASE_INVENTORY
    assert set(status.residual_edge_ids) == DEFERRED_RESIDUAL_EDGE_IDS


def test_status_rejects_stale_head(tmp_path: Path) -> None:
    root = _clone_world(tmp_path)
    head_path = root / "graph_memory" / "worlds" / "eldyrwild" / "head.json"
    head = json.loads(head_path.read_text(encoding="utf-8"))
    head["head_revision_id"] = "rev:a0d76578e9c3d51e8d4c6b05ffe87051"
    head_path.write_text(json.dumps(head), encoding="utf-8")
    status = get_relationship_node_kind_source_repair_status(root, repo=REPO)
    assert status.eligibility == "ineligible"
    assert "stale_base" in status.diagnostics


def test_owning_boundary_proof_projects_exact_inventory(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    root = _clone_world(tmp_path)
    calls: list[dict[str, Any]] = []
    original = repair_service._analyze_relationship_effective_conformance_with_authorities

    def spy(**kwargs: Any) -> Any:
        calls.append(kwargs)
        return original(**kwargs)

    monkeypatch.setattr(
        repair_service,
        "_analyze_relationship_effective_conformance_with_authorities",
        spy,
    )
    proof = prove_isolated_repair_effect(root, repo=REPO)
    assert proof.passed
    assert proof.base_inventory == EXPECTED_BASE_INVENTORY
    assert proof.projected_inventory == EXPECTED_PROJECTED_INVENTORY
    assert proof.zero_regressions
    assert set(
        proof.diagnostics
    ) >= {"effective_conformance_path:private_injectable_owner_boundary"}
    assert calls
    assert all("base_report" in call and "store" in call for call in calls)


def test_build_and_verify_project_exact_stage_b_inventory(tmp_path: Path) -> None:
    root = _clone_world(tmp_path)
    repository = _clone_repo(tmp_path)
    first = build_relationship_node_kind_source_repair(root=root, repo=repository)
    assert first.proof.passed
    assert first.proof.projected_inventory == EXPECTED_PROJECTED_INVENTORY
    assert set(first.proof.projected_inventory) == {
        "semantic",
        "represented",
        "residual",
        "uses_statblock_mechanics",
    }
    assert set(
        row["edge_id"]
        for row in first.proof.deferred_edge_proofs
        if row["edge_id"] in repair_service.STAGE_B_REMAINING_RESIDUAL_EDGE_IDS
    ) == repair_service.STAGE_B_REMAINING_RESIDUAL_EDGE_IDS
    pin = verify_relationship_node_kind_source_repair(root=root, repo=repository)
    assert pin is not None
    assert pin.projected_inventory == EXPECTED_PROJECTED_INVENTORY
    assert pin.manifest_sha256 == LOCKED_MANIFEST_SHA256


def test_identical_rebuild_is_already_built(tmp_path: Path) -> None:
    root = _clone_world(tmp_path)
    repository = _clone_repo(tmp_path)
    first = build_relationship_node_kind_source_repair(root=root, repo=repository)
    path = repository / MANIFEST_RELPATH
    first_bytes = path.read_bytes()
    second = build_relationship_node_kind_source_repair(root=root, repo=repository)
    assert "already_built" in second.diagnostics
    assert second.manifest_sha256 == first.manifest_sha256
    assert path.read_bytes() == first_bytes


def test_generated_digest_mismatch_refuses_before_first_write(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    root = _clone_world(tmp_path)
    repository = _clone_repo(tmp_path)
    monkeypatch.setattr(repair_service, "LOCKED_MANIFEST_SHA256", "0" * 64)
    with pytest.raises(RelationshipNodeKindSourceRepairError) as excinfo:
        build_relationship_node_kind_source_repair(root=root, repo=repository)
    assert excinfo.value.code == "manifest_digest_mismatch"
    assert not (repository / MANIFEST_RELPATH).exists()


def test_existing_different_manifest_refuses_without_write(tmp_path: Path) -> None:
    root = _clone_world(tmp_path)
    repository = _clone_repo(tmp_path)
    build_relationship_node_kind_source_repair(root=root, repo=repository)
    path = repository / MANIFEST_RELPATH
    tampered = path.read_bytes() + b"\n"
    path.write_bytes(tampered)
    with pytest.raises(RelationshipNodeKindSourceRepairError) as excinfo:
        build_relationship_node_kind_source_repair(root=root, repo=repository)
    assert excinfo.value.code == "locked_manifest_overwrite_refused"
    assert path.read_bytes() == tampered


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


def test_wrong_source_kind_refuses_even_when_adapter_can_admit(
    tmp_path: Path,
) -> None:
    root = _clone_world(tmp_path)
    _, _, store = repair_service._open_exact_base(root)
    wrong = [dict(spec) for spec in KIND_REPAIR_SPECS]
    wrong_spec = next(
        spec for spec in wrong if spec["node_id"] == "item:torvak-hemp-caravan"
    )
    wrong_spec["corrected_kind"] = "faction"
    with pytest.raises(RelationshipNodeKindSourceRepairError) as excinfo:
        repair_service._overlay_store(store, kind_repairs=wrong)
    assert excinfo.value.code == "source_kind_ambiguous"


def test_live_graph_head_and_tree_unchanged() -> None:
    root = world_graph_root()
    before_digest = snapshot_world_graph_tree_digest(root, "eldyrwild")
    before_head = kernel.open_world_graph_head(root, "eldyrwild").head_revision_id
    built = build_relationship_node_kind_source_repair(
        root=root,
        repo=REPO,
        allow_live_world=True,
    )
    assert built.proof.passed
    assert verify_relationship_node_kind_source_repair(root=root, repo=REPO) is not None
    assert snapshot_world_graph_tree_digest(root, "eldyrwild") == before_digest
    assert kernel.open_world_graph_head(root, "eldyrwild").head_revision_id == before_head
    assert before_head == BASE_REVISION_ID
