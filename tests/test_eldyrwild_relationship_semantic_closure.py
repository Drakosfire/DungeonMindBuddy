"""Tests for the Eldyrwild relationship semantic closure program.

Covers the locked 55-row closure manifest (46 mutable + 9 deferred kind-repair),
whole-ledger preflight with live source seals, operation-plan prefix-safe apply
on an exact-Q4 clone, authority-safe applied detection, deferred residual exit
(323/314/9/3), and the finalizer pin contract (exact Q4→head operation_plan
chain + rebuild equivalence; refuse replayable foreign descendants).
"""

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
from apps.live_control_server.integrations.dungeonmind_kernel.relationship_effective_conformance_v1 import (
    analyze_relationship_effective_conformance_v1,
)
from apps.live_control_server.services import (
    eldyrwild_relationship_semantic_closure as closure_service,
)
from apps.live_control_server.services.eldyrwild_relationship_semantic_closure import (
    BASE_PARENT_REVISION_ID,
    BASE_REVISION_ID,
    CLOSURE_DIR_RELPATH,
    CLOSURE_ID,
    DEFERRED_RESIDUAL_EDGE_IDS,
    DEFERRED_UNIT_COUNT,
    EXPECTED_FINAL_INVENTORY,
    LOCKED_MANIFEST_SHA256,
    MANIFEST_RELPATH,
    MUTABLE_UNIT_COUNT,
    OPERATION_PLAN_COUNT,
    RelationshipSemanticClosureError,
    apply_relationship_semantic_closure,
    finalize_relationship_semantic_closure,
    get_relationship_semantic_closure_status,
    verify_relationship_semantic_closure,
)
from graph_memory.union_supergraph.redirects import resolve_union_node_id

REPO = Path(__file__).resolve().parents[1]
ELDYRWILD_WORLD_ID = "eldyrwild"

EXPECTED_BASE_INVENTORY = {
    "semantic": 366,
    "represented": 311,
    "residual": 55,
    "uses_statblock_mechanics": 3,
    "unadjudicated": 0,
    "dungeonmind_owned": 0,
    "buddy_owned": 55,
}

REPLACEMENT_UNITS = {
    "edge:group_session24_refugees_of_edge:part_of:loc_3": "displaced_from",
    "edge:item:session17:centipede_meat_creature:leads_to:loc:ceiling": "travels_to",
}
DECOMPOSITION_UNIT_EDGE = (
    "edge:node:torvak_hempdealer:reports_threat_in:mystery:session4:hempholm-moving-tree"
)
DECOMPOSITION_ATOMIC_EDGE = (
    "edge:node:torvak_hempdealer:knows_about:mystery:session4:hempholm-moving-tree"
)
IDENTITY_UNIT_EDGES = {
    "edge:item:session11:council-headquarters:same_as:loc:the-council:same-place-as",
    "edge:item_enormous_boulder:same_as:item_foot_of_statue",
    "edge:item_session2_hidden_alchemy_room:same_as:location_003",
    "edge:loc:last_warehouse:same_as:loc:chilled_warehouse",
    "edge:loc:underground-entrance:same_as:mystery:session9:second_underground_entrance",
    "edge:obj:session9:scroll_abyssal:identified_as:mystery:session9:scroll_in_strange_language",
    "edge:organization:merchant-s-crossroads-apothecary:same_as:loc:crooked-retort",
}


def _clone_eldyrwild(tmp_path: Path) -> Path:
    """Clone the canonical world at its current head (exact Q4)."""
    src_root = world_graph_root()
    eldyrwild_src = src_root / "graph_memory" / "worlds" / "eldyrwild"
    if not eldyrwild_src.is_dir():
        fallback = Path(
            "/home/drakosfire/Projects/DungeonOverMind/DungeonMindBuddy/out"
        )
        if (fallback / "graph_memory" / "worlds" / "eldyrwild").is_dir():
            src_root = fallback
            eldyrwild_src = src_root / "graph_memory" / "worlds" / "eldyrwild"
        else:
            pytest.skip("Eldyrwild world graph not present")
    (tmp_path / "graph_memory" / "worlds").mkdir(parents=True)
    shutil.copytree(eldyrwild_src, tmp_path / "graph_memory" / "worlds" / "eldyrwild")
    runs = src_root / "graph_memory" / "runs"
    if runs.is_dir():
        os.symlink(runs, tmp_path / "graph_memory" / "runs")
    return tmp_path


def _load_store(root: Path) -> Any:
    _h, _r, store = kernel.open_current_world_graph(root, ELDYRWILD_WORLD_ID)
    return store


def _support_row(store: Any, assertion_id: str) -> dict[str, Any]:
    row = (store.assertion_support or {}).get(assertion_id)
    assert row is not None, f"missing support row for {assertion_id}"
    return row if isinstance(row, dict) else row.model_dump(mode="json")


def _current_edge_ids(store: Any) -> set[str]:
    current: set[str] = set()
    for row in (store.assertion_support or {}).values():
        if not isinstance(row, dict):
            row = row.model_dump(mode="json")
        if (
            row.get("assertion_kind") == "edge"
            and row.get("support_state") == "supported"
            and (row.get("active_contribution_ids") or [])
        ):
            current.add(row["graph_object_id"])
    return current


def _manifest() -> dict[str, Any]:
    return closure_service._load_manifest(repo=REPO)


def _unit(manifest: dict[str, Any], edge_id: str) -> dict[str, Any]:
    return next(u for u in manifest["units"] if u["edge_id"] == edge_id)


def _apply_ops(
    root: Path,
    manifest: dict[str, Any],
    unit: dict[str, Any],
    *,
    ops: list[dict[str, Any]] | None = None,
) -> None:
    """Apply selected unit ops directly through kernel seams (crash simulation)."""
    for op in ops if ops is not None else unit["operations"]:
        _h, _r, store = kernel.open_current_world_graph(root, ELDYRWILD_WORLD_ID)
        parent = kernel.open_world_graph_head(root, ELDYRWILD_WORLD_ID).head_revision_id
        if closure_service._op_applied(
            store, unit, op, root=root, manifest=manifest
        ):
            continue
        if op["op"] == "identity_merge":
            from graph_memory.kernel.identity_decisions import merge_identity

            updated, decision = merge_identity(
                store,
                world_id=ELDYRWILD_WORLD_ID,
                source_node_id=op["source_node_id"],
                target_node_id=op["target_node_id"],
                actor="gm",
                reason=op["merge_reason"],
            )
            kernel.publish_world_revision(
                root,
                ELDYRWILD_WORLD_ID,
                updated,
                operation_ids=[decision.decision_id],
                expected_parent_revision_id=parent,
            )
        else:
            contribution = closure_service._unit_contribution(
                manifest, op["contribution_id"]
            )
            if op["op"] == "contradict":
                result = kernel.contradict_edge_assertion_support(
                    root,
                    world_id=ELDYRWILD_WORLD_ID,
                    contribution=contribution,
                    expected_parent_revision_id=parent,
                )
            elif op["op"] == "correct":
                result = kernel.correct_edge_assertion_support(
                    root,
                    world_id=ELDYRWILD_WORLD_ID,
                    contribution=contribution,
                    expected_parent_revision_id=parent,
                )
            else:
                result = kernel.merge_contribution_to_revision(
                    root,
                    world_id=ELDYRWILD_WORLD_ID,
                    contribution=contribution,
                    expected_parent_revision_id=parent,
                )
            assert not result.failure_code, result.failure_message


def _apply_single_unit_ops(root: Path, manifest: dict[str, Any], unit: dict) -> None:
    _apply_ops(root, manifest, unit)


# ---------------------------------------------------------------------------
# Manifest integrity
# ---------------------------------------------------------------------------


def test_manifest_matches_locked_sha256() -> None:
    raw = (REPO / MANIFEST_RELPATH).read_text(encoding="utf-8")
    assert hashlib.sha256(raw.encode("utf-8")).hexdigest() == LOCKED_MANIFEST_SHA256


def test_manifest_structure_and_child_artifacts() -> None:
    manifest = _manifest()
    assert manifest["closure_id"] == CLOSURE_ID
    assert manifest["base_revision_id"] == BASE_REVISION_ID
    assert manifest["base_parent_revision_id"] == BASE_PARENT_REVISION_ID
    assert manifest["expected_base_inventory"] == EXPECTED_BASE_INVENTORY
    assert manifest["expected_final_inventory"] == EXPECTED_FINAL_INVENTORY
    assert manifest["unit_count"] == 55
    assert len(manifest["units"]) == 55
    assert manifest["mutable_unit_count"] == MUTABLE_UNIT_COUNT
    assert manifest["deferred_unit_count"] == DEFERRED_UNIT_COUNT
    assert len(manifest["operation_plan"]) == OPERATION_PLAN_COUNT
    assert frozenset(manifest["deferred_residual_edge_ids"]) == DEFERRED_RESIDUAL_EDGE_IDS
    assert manifest["unit_order"] == [u["unit_id"] for u in manifest["units"]]
    assert [u["ordinal"] for u in manifest["units"]] == list(range(1, 56))
    assert set(manifest["artifacts"]) == {
        "source-corrections",
        "compound-decompositions",
        "identity-migrations",
        "unsupported-assertions",
    }
    counts = {
        "identity_merge": 0,
        "contradicts_and_replaces": 0,
        "compound_decomposition": 0,
        "contradiction_only": 0,
        "deferred_buddy_kind_repair": 0,
    }
    for unit in manifest["units"]:
        counts[unit["closure_kind"]] += 1
        if unit["closure_kind"] == "deferred_buddy_kind_repair":
            assert unit.get("deferred") is True
            assert unit.get("operations") == []
        else:
            assert not unit.get("deferred")
            assert unit.get("operations")
    assert counts == {
        "identity_merge": 7,
        "contradicts_and_replaces": 2,
        "compound_decomposition": 1,
        "contradiction_only": 36,
        "deferred_buddy_kind_repair": 9,
    }
    # Mutable units first by disposition rank; deferred kind-repair last.
    mutable = [u for u in manifest["units"] if not u.get("deferred")]
    deferred = [u for u in manifest["units"] if u.get("deferred")]
    assert [u["ordinal"] for u in deferred] == list(range(47, 56))
    ranks = {
        "IDENTITY_NOT_RELATIONSHIP": 0,
        "SOURCE_CORRECTION_REQUIRED": 1,
        "COMPOUND_ASSERTION_NOT_SINGLE_RELATIONSHIP": 2,
        "INSUFFICIENT_EVIDENCE": 3,
    }
    order = [ranks[u["disposition"]] for u in mutable]
    assert order == sorted(order)


def test_manifest_tamper_refused(tmp_path: Path) -> None:
    forged = tmp_path / "repo"
    forged.mkdir()
    shutil.copytree(REPO / CLOSURE_DIR_RELPATH, forged / CLOSURE_DIR_RELPATH)
    manifest_path = forged / MANIFEST_RELPATH
    raw = manifest_path.read_text(encoding="utf-8")
    assert '"unit_count": 55' in raw
    manifest_path.write_text(
        raw.replace('"unit_count": 55', '"unit_count": 54', 1), encoding="utf-8"
    )
    with pytest.raises(RelationshipSemanticClosureError) as excinfo:
        closure_service._load_manifest(repo=forged)
    assert excinfo.value.code == "closure_manifest_tampered"


def test_child_artifact_tamper_refused(tmp_path: Path) -> None:
    forged = tmp_path / "repo"
    forged.mkdir()
    shutil.copytree(REPO / CLOSURE_DIR_RELPATH, forged / CLOSURE_DIR_RELPATH)
    child = forged / CLOSURE_DIR_RELPATH / "source-corrections.json"
    raw = child.read_text(encoding="utf-8")
    child.write_text(raw.replace('"gm"', '"GM"', 1), encoding="utf-8")
    with pytest.raises(RelationshipSemanticClosureError) as excinfo:
        closure_service._load_manifest(repo=forged)
    assert excinfo.value.code == "closure_artifact_tampered"


# ---------------------------------------------------------------------------
# Status + guards
# ---------------------------------------------------------------------------


def test_status_eligible_at_exact_q4(tmp_path: Path) -> None:
    root = _clone_eldyrwild(tmp_path)
    status = get_relationship_semantic_closure_status(root=root, repo=REPO)
    assert status.eligibility == "eligible"
    assert status.head_revision_id == BASE_REVISION_ID
    assert status.unit_count == 55
    assert status.mutable_unit_count == MUTABLE_UNIT_COUNT
    assert status.deferred_unit_count == DEFERRED_UNIT_COUNT
    assert status.applied_unit_count == 0
    assert status.next_pending_unit_id == "closure-unit:001"
    deferred_states = [u for u in status.units if u.deferred]
    assert len(deferred_states) == 9
    assert all(not u.applied and not u.pending_operations for u in deferred_states)


def test_status_ineligible_when_world_missing(tmp_path: Path) -> None:
    status = get_relationship_semantic_closure_status(root=tmp_path, repo=REPO)
    assert status.eligibility == "ineligible"
    assert "world_missing" in status.diagnostics


def test_apply_requires_exact_q4_base(tmp_path: Path) -> None:
    root = _clone_eldyrwild(tmp_path)
    with pytest.raises(RelationshipSemanticClosureError) as excinfo:
        apply_relationship_semantic_closure(
            expected_base_revision_id=BASE_PARENT_REVISION_ID,
            root=root,
            repo=REPO,
        )
    assert excinfo.value.code == "base_mismatch"


def test_apply_requires_expected_base_argument(tmp_path: Path) -> None:
    root = _clone_eldyrwild(tmp_path)
    with pytest.raises(RelationshipSemanticClosureError) as excinfo:
        apply_relationship_semantic_closure(
            expected_base_revision_id="", root=root, repo=REPO
        )
    assert excinfo.value.code == "expected_base_required"


def test_live_world_guard() -> None:
    with pytest.raises(RelationshipSemanticClosureError) as excinfo:
        apply_relationship_semantic_closure(
            expected_base_revision_id=BASE_REVISION_ID,
            root=world_graph_root(),
            repo=REPO,
            allow_live_world=False,
        )
    assert excinfo.value.code == "live_world_opt_in_required"


def test_finalize_refused_on_open_head(tmp_path: Path) -> None:
    root = _clone_eldyrwild(tmp_path)
    with pytest.raises(RelationshipSemanticClosureError) as excinfo:
        finalize_relationship_semantic_closure(root=root, repo=REPO)
    assert excinfo.value.code == "finalize_refused"


def test_preflight_live_seals_against_q4(tmp_path: Path) -> None:
    root = _clone_eldyrwild(tmp_path)
    manifest = _manifest()
    diagnostics = closure_service._preflight(
        root=root,
        manifest=manifest,
        expected_base_revision_id=BASE_REVISION_ID,
        repo=REPO,
    )
    assert diagnostics == []


def test_preflight_fails_when_artifact_bytes_tampered(tmp_path: Path) -> None:
    root = _clone_eldyrwild(tmp_path)
    manifest = _manifest()
    # Tamper a sealed recap artifact that a deferred unit seals against.
    deferred = next(u for u in manifest["units"] if u.get("deferred"))
    seal = deferred["seal"]
    uri = seal["artifact_uri"]
    assert uri.startswith("repo://")
    rel = uri[len("repo://") :]
    artifact_path = root / rel
    if not artifact_path.is_file():
        pytest.skip(f"sealed artifact not present at clone path: {artifact_path}")
    original = artifact_path.read_bytes()
    artifact_path.write_bytes(original + b"\n# tampered\n")
    diagnostics = closure_service._preflight(
        root=root,
        manifest=manifest,
        expected_base_revision_id=BASE_REVISION_ID,
        repo=REPO,
    )
    assert diagnostics
    assert any(d.startswith("live_seal_failed:") for d in diagnostics)


# ---------------------------------------------------------------------------
# Full closure exit
# ---------------------------------------------------------------------------


def _apply_full(root: Path) -> Any:
    result = apply_relationship_semantic_closure(
        expected_base_revision_id=BASE_REVISION_ID, root=root, repo=REPO
    )
    assert result.failed_unit_id is None, result.failure_message
    return result


def test_full_closure_exit_inventory(tmp_path: Path) -> None:
    root = _clone_eldyrwild(tmp_path)
    result = _apply_full(root)
    assert len(result.applied_unit_ids) == MUTABLE_UNIT_COUNT
    assert result.already_applied_unit_ids == []
    assert len(result.deferred_unit_ids) == DEFERRED_UNIT_COUNT
    assert len(result.published_revision_ids) == OPERATION_PLAN_COUNT
    assert result.verify_passed
    assert result.final_inventory == EXPECTED_FINAL_INVENTORY

    head = kernel.open_world_graph_head(root, ELDYRWILD_WORLD_ID)
    assert head.head_revision_id == result.final_revision_id
    assert head.head_revision_id != BASE_REVISION_ID

    eff = analyze_relationship_effective_conformance_v1(
        root=root, world_id=ELDYRWILD_WORLD_ID, revision_id=head.head_revision_id
    )
    assert eff.relationship_semantic_count == 323
    assert eff.relationship_effectively_represented_count == 314
    assert eff.relationship_effective_residual_count == 9
    assert eff.uses_statblock_mechanics_count == 3
    assert set(eff.remaining_residual_edge_ids) == DEFERRED_RESIDUAL_EDGE_IDS


def test_closure_idempotent_resume(tmp_path: Path) -> None:
    root = _clone_eldyrwild(tmp_path)
    first = _apply_full(root)
    second = apply_relationship_semantic_closure(
        expected_base_revision_id=BASE_REVISION_ID, root=root, repo=REPO
    )
    assert second.failed_unit_id is None
    assert second.published_revision_ids == []
    assert second.applied_unit_ids == []
    assert len(second.already_applied_unit_ids) == MUTABLE_UNIT_COUNT
    assert second.final_revision_id == first.final_revision_id
    assert second.verify_passed
    status = get_relationship_semantic_closure_status(root=root, repo=REPO)
    assert status.eligibility == "already_applied"


def test_closure_partial_prefix_resume(tmp_path: Path) -> None:
    root = _clone_eldyrwild(tmp_path)
    manifest = _manifest()
    # Simulate a crash after unit 1: apply its ops directly, then resume.
    _apply_single_unit_ops(root, manifest, manifest["units"][0])
    status = get_relationship_semantic_closure_status(root=root, repo=REPO)
    assert status.eligibility == "partially_applied"
    assert status.applied_unit_count == 1

    result = apply_relationship_semantic_closure(
        expected_base_revision_id=BASE_REVISION_ID, root=root, repo=REPO
    )
    assert result.failed_unit_id is None, result.failure_message
    assert result.already_applied_unit_ids == ["closure-unit:001"]
    assert len(result.applied_unit_ids) == MUTABLE_UNIT_COUNT - 1
    assert result.verify_passed
    assert result.final_inventory == EXPECTED_FINAL_INVENTORY


def test_closure_non_prefix_applied_set_refused(tmp_path: Path) -> None:
    root = _clone_eldyrwild(tmp_path)
    manifest = _manifest()
    # Apply unit 2 while unit 1 is pending: not an operation_plan prefix.
    _apply_single_unit_ops(root, manifest, manifest["units"][1])
    with pytest.raises(RelationshipSemanticClosureError) as excinfo:
        apply_relationship_semantic_closure(
            expected_base_revision_id=BASE_REVISION_ID, root=root, repo=REPO
        )
    assert excinfo.value.code == "preflight_failed"
    assert "applied_ops_not_a_prefix" in str(excinfo.value)


def test_operation_order_intra_unit_non_prefix_refused(tmp_path: Path) -> None:
    """Apply only identity_merge (op2) without contradict (op1) → refused."""
    root = _clone_eldyrwild(tmp_path)
    manifest = _manifest()
    identity_unit = next(
        u for u in manifest["units"] if u["closure_kind"] == "identity_merge"
    )
    merge_op = next(o for o in identity_unit["operations"] if o["op"] == "identity_merge")
    _apply_ops(root, manifest, identity_unit, ops=[merge_op])

    with pytest.raises(RelationshipSemanticClosureError) as excinfo:
        apply_relationship_semantic_closure(
            expected_base_revision_id=BASE_REVISION_ID, root=root, repo=REPO
        )
    assert excinfo.value.code == "preflight_failed"
    assert "applied_ops_not_a_prefix" in str(excinfo.value)

    status = get_relationship_semantic_closure_status(root=root, repo=REPO)
    assert status.eligibility == "integrity_failure"


def test_partial_op_resume_within_identity_unit(tmp_path: Path) -> None:
    """Apply only contradict of identity unit → resume completes identity_merge."""
    root = _clone_eldyrwild(tmp_path)
    manifest = _manifest()
    identity_unit = next(
        u for u in manifest["units"] if u["unit_id"] == "closure-unit:001"
    )
    contradict_op = next(o for o in identity_unit["operations"] if o["op"] == "contradict")
    _apply_ops(root, manifest, identity_unit, ops=[contradict_op])

    status = get_relationship_semantic_closure_status(root=root, repo=REPO)
    assert status.eligibility == "partially_applied"
    unit_state = next(u for u in status.units if u.unit_id == "closure-unit:001")
    assert unit_state.applied_operations == ["contradict#0"]
    assert unit_state.pending_operations == ["identity_merge#1"]

    result = apply_relationship_semantic_closure(
        expected_base_revision_id=BASE_REVISION_ID, root=root, repo=REPO
    )
    assert result.failed_unit_id is None, result.failure_message
    assert result.verify_passed
    assert result.final_inventory == EXPECTED_FINAL_INVENTORY


def test_authority_weak_digest_only_is_integrity_failure(tmp_path: Path) -> None:
    """Digest key present without full authority must not count as already_applied."""
    root = _clone_eldyrwild(tmp_path)
    manifest = _manifest()
    plan_op = next(o for o in manifest["operation_plan"] if o["op"] == "contradict")
    cid = plan_op["contribution_id"]
    locked = plan_op["source_payload_sha256"]

    parent = kernel.open_world_graph_head(root, ELDYRWILD_WORLD_ID).head_revision_id
    store = kernel.load_world_graph_revision(root, ELDYRWILD_WORLD_ID, parent)
    digests = dict(store.contribution_source_payload_sha256 or {})
    digests[cid] = locked
    store.contribution_source_payload_sha256 = digests
    advanced = kernel.publish_world_revision(
        root,
        ELDYRWILD_WORLD_ID,
        store,
        operation_ids=["op:closure-false-already-applied-digest-probe"],
    ).revision.revision_id

    status = get_relationship_semantic_closure_status(root=root, repo=REPO)
    assert status.head_revision_id == advanced
    assert status.eligibility == "integrity_failure"
    assert status.eligibility != "already_applied"
    assert status.eligibility != "partially_applied"

    with pytest.raises(RelationshipSemanticClosureError) as excinfo:
        apply_relationship_semantic_closure(
            expected_base_revision_id=BASE_REVISION_ID, root=root, repo=REPO
        )
    assert excinfo.value.code == "preflight_failed"


# ---------------------------------------------------------------------------
# Per-closure-kind effects
# ---------------------------------------------------------------------------


def test_identity_merges_durable_and_redirecting(tmp_path: Path) -> None:
    root = _clone_eldyrwild(tmp_path)
    manifest = _manifest()
    result = _apply_full(root)
    store = _load_store(root)

    ledger_dir = (
        root / "graph_memory" / "worlds" / "eldyrwild" / "identity_decisions"
    )
    ledger_ids = {
        json.loads(p.read_text(encoding="utf-8"))["decision_id"]
        for p in ledger_dir.glob("identity-decision__*.json")
    }
    store_decision_ids = {
        (d.get("decision_id") if isinstance(d, dict) else d.decision_id)
        for d in (store.identity_decisions or [])
    }

    identity_units = [
        u for u in manifest["units"] if u["closure_kind"] == "identity_merge"
    ]
    assert len(identity_units) == 7
    assert {u["edge_id"] for u in identity_units} == IDENTITY_UNIT_EDGES
    for unit in identity_units:
        merge_op = next(o for o in unit["operations"] if o["op"] == "identity_merge")
        source = store.nodes[merge_op["source_node_id"]]
        assert dict(source.state or {}).get("merged_into") == merge_op["target_node_id"]
        assert merge_op["expected_decision_id"] in store_decision_ids
        assert merge_op["expected_decision_id"] in ledger_ids
        resolved = resolve_union_node_id(
            merge_op["source_node_id"], store.identity_redirects or []
        )
        assert resolved == merge_op["target_node_id"]
        row = _support_row(store, unit["target_assertion_id"])
        assert row["support_state"] == "contradicted"
        assert (row.get("active_contribution_ids") or []) == []
    current = _current_edge_ids(store)
    for edge_id in IDENTITY_UNIT_EDGES:
        assert edge_id not in current
    assert result.verify_passed


def test_replacement_units_restore_atomic_edges(tmp_path: Path) -> None:
    root = _clone_eldyrwild(tmp_path)
    manifest = _manifest()
    _apply_full(root)
    store = _load_store(root)
    current = _current_edge_ids(store)

    for unit in manifest["units"]:
        if unit["closure_kind"] != "contradicts_and_replaces":
            continue
        edge_id = unit["edge_id"]
        assert edge_id in REPLACEMENT_UNITS
        row = _support_row(store, unit["target_assertion_id"])
        assert row["support_state"] == "contradicted"
        assert edge_id not in current
        shape = unit["edge_shape"]
        new_edge_id = (
            f"edge:{shape['source']}:{REPLACEMENT_UNITS[edge_id]}:{shape['target']}"
        )
        assert new_edge_id in store.edges
        assert new_edge_id in current


def test_compound_decomposition_atomic(tmp_path: Path) -> None:
    root = _clone_eldyrwild(tmp_path)
    manifest = _manifest()
    _apply_full(root)
    store = _load_store(root)
    current = _current_edge_ids(store)

    unit = _unit(manifest, DECOMPOSITION_UNIT_EDGE)
    assert unit["closure_kind"] == "compound_decomposition"
    row = _support_row(store, unit["target_assertion_id"])
    assert row["support_state"] == "contradicted"
    assert DECOMPOSITION_UNIT_EDGE not in current
    assert DECOMPOSITION_ATOMIC_EDGE in store.edges
    assert DECOMPOSITION_ATOMIC_EDGE in current


def test_contradiction_only_units_not_current(tmp_path: Path) -> None:
    root = _clone_eldyrwild(tmp_path)
    manifest = _manifest()
    _apply_full(root)
    store = _load_store(root)
    current = _current_edge_ids(store)

    contradiction_units = [
        u for u in manifest["units"] if u["closure_kind"] == "contradiction_only"
    ]
    assert len(contradiction_units) == 36
    for unit in contradiction_units:
        row = _support_row(store, unit["target_assertion_id"])
        assert row["support_state"] == "contradicted"
        assert (row.get("active_contribution_ids") or []) == []
        assert unit["edge_id"] not in current


def test_deferred_kind_repair_units_remain_residual(tmp_path: Path) -> None:
    root = _clone_eldyrwild(tmp_path)
    manifest = _manifest()
    _apply_full(root)
    store = _load_store(root)
    current = _current_edge_ids(store)

    deferred_units = [u for u in manifest["units"] if u.get("deferred")]
    assert len(deferred_units) == 9
    for unit in deferred_units:
        assert unit["edge_id"] in DEFERRED_RESIDUAL_EDGE_IDS
        row = _support_row(store, unit["target_assertion_id"])
        assert row["support_state"] == "supported"
        assert (row.get("active_contribution_ids") or [])
        assert unit["edge_id"] in current


def test_closure_preserves_unaffected_current_edges(tmp_path: Path) -> None:
    root = _clone_eldyrwild(tmp_path)
    before = _current_edge_ids(_load_store(root))
    manifest = _manifest()
    mutable_target_edges = {
        u["edge_id"] for u in manifest["units"] if not u.get("deferred")
    }
    deferred_edges = {u["edge_id"] for u in manifest["units"] if u.get("deferred")}
    assert mutable_target_edges | deferred_edges <= before

    _apply_full(root)
    after = _current_edge_ids(_load_store(root))

    assert before - mutable_target_edges <= after
    assert deferred_edges <= after
    new_edges = after - (before - mutable_target_edges)
    assert new_edges == {
        "edge:group_session24_refugees_of_edge:displaced_from:loc_3",
        "edge:item:session17:centipede_meat_creature:travels_to:loc:ceiling",
        DECOMPOSITION_ATOMIC_EDGE,
    }


def test_closure_contribution_index_coherence(tmp_path: Path) -> None:
    """Every closure contribution is revision-bound at head with an active index entry."""
    root = _clone_eldyrwild(tmp_path)
    manifest = _manifest()
    result = _apply_full(root)
    store = _load_store(root)
    bound = set((store.contribution_source_payload_sha256 or {}).keys())

    from graph_memory.world_supergraph.contribution_store import (
        load_contribution_index,
        load_contribution_record,
    )

    index = load_contribution_index(root, ELDYRWILD_WORLD_ID)
    active_index = set(index.active_contribution_ids)
    closure_contribution_ids: set[str] = set()
    for info in (manifest.get("artifacts") or {}).values():
        for entry in (info.get("_payload") or {}).get("entries") or []:
            closure_contribution_ids.update((entry.get("contributions") or {}).keys())
    # 36 contradiction-only + 7 identity contradict + 2 replacement
    # + 1 decomposition contradict + 1 additive = 47 closure contributions.
    assert len(closure_contribution_ids) == 47
    for contribution_id in closure_contribution_ids:
        assert contribution_id in bound
        assert contribution_id in active_index
        load_contribution_record(root, ELDYRWILD_WORLD_ID, contribution_id)
    assert result.verify_passed


def test_finalize_emits_pin_after_closure(tmp_path: Path) -> None:
    root = _clone_eldyrwild(tmp_path)
    result = _apply_full(root)
    pin = finalize_relationship_semantic_closure(root=root, repo=REPO)
    assert pin.final_revision_id == result.final_revision_id
    assert pin.final_inventory == EXPECTED_FINAL_INVENTORY
    assert set(pin.residual_edge_ids) == DEFERRED_RESIDUAL_EDGE_IDS
    assert pin.base_revision_id == BASE_REVISION_ID
    assert len(pin.final_graph_payload_sha256) == 64
    assert "q4_ancestry_proven" in pin.diagnostics
    assert "closure_operation_chain_exact" in pin.diagnostics
    assert "all_units_live_source_sealed" in pin.diagnostics
    assert "all_units_target_source_sealed" in pin.diagnostics
    assert "rebuild_equivalent_to_pinned_revision" in pin.diagnostics
    assert (
        "rebuild_equivalent_to_head" in pin.diagnostics
        or "rebuild_equivalent_to_published_head" in pin.diagnostics
    )

    verify = verify_relationship_semantic_closure(root=root, repo=REPO)
    assert verify is not None
    assert verify.final_revision_id == pin.final_revision_id


def test_finalize_refuses_foreign_descendant_without_rebuild_equivalence(
    tmp_path: Path,
) -> None:
    """After full closure, an adversarial head that breaks rebuild must refuse finalize."""
    root = _clone_eldyrwild(tmp_path)
    _apply_full(root)
    pin = verify_relationship_semantic_closure(root=root, repo=REPO)
    assert pin is not None
    assert "q4_ancestry_proven" in pin.diagnostics
    assert "closure_operation_chain_exact" in pin.diagnostics
    assert "rebuild_equivalent_to_pinned_revision" in pin.diagnostics

    head = kernel.open_world_graph_head(root, ELDYRWILD_WORLD_ID).head_revision_id
    store = kernel.load_world_graph_revision(root, ELDYRWILD_WORLD_ID, head)
    # Strip replay-manifest entries so pinned rebuild cannot prove equivalence.
    store.contribution_replay_manifest = []
    kernel.publish_world_revision(
        root,
        ELDYRWILD_WORLD_ID,
        store,
        operation_ids=["op:closure-foreign-descendant-probe"],
    )

    assert verify_relationship_semantic_closure(root=root, repo=REPO) is None
    with pytest.raises(RelationshipSemanticClosureError) as excinfo:
        finalize_relationship_semantic_closure(root=root, repo=REPO)
    assert excinfo.value.code == "finalize_refused"


def test_finalize_refuses_replayable_foreign_descendant_after_clean_closure(
    tmp_path: Path,
) -> None:
    """Valid ledger-backed foreign publish after clean closure must refuse finalize.

    Inventory and rebuild can still hold; the post-Q4 operation_plan chain must not.
    """
    root = _clone_eldyrwild(tmp_path)
    _apply_full(root)
    assert verify_relationship_semantic_closure(root=root, repo=REPO) is not None

    parent = kernel.open_world_graph_head(root, ELDYRWILD_WORLD_ID).head_revision_id
    foreign = kernel.create_graph_contribution(
        world_id=ELDYRWILD_WORLD_ID,
        source_kind="manual_import",
        source_artifact_id="artifact:closure-foreign-chain-probe",
        campaign_scope="eldyrwild",
        authored_by="gm",
        accepted_assertions=[
            kernel.build_assertion(
                assertion_kind="node",
                acceptance_state="accepted",
                subject_node_id="npc:closure_foreign_chain_probe",
                label="closure foreign chain probe",
                campaign_scope="eldyrwild",
                value={
                    "kind": "npc",
                    "role": "foreign_probe",
                    "source_domains": ["manual_seed"],
                },
                identity_resolution_outcome="created_new",
            )
        ],
    )
    merged = kernel.merge_contribution_to_revision(
        root,
        world_id=ELDYRWILD_WORLD_ID,
        contribution=foreign,
        expected_parent_revision_id=parent,
    )
    assert merged.published is True
    assert merged.revision_id != parent

    # Inventory unchanged — foreign node does not touch relationship residuals.
    eff = analyze_relationship_effective_conformance_v1(
        root=root, world_id=ELDYRWILD_WORLD_ID, revision_id=merged.revision_id
    )
    assert {
        "semantic": eff.relationship_semantic_count,
        "represented": eff.relationship_effectively_represented_count,
        "residual": eff.relationship_effective_residual_count,
        "uses_statblock_mechanics": eff.uses_statblock_mechanics_count,
    } == EXPECTED_FINAL_INVENTORY
    assert set(eff.remaining_residual_edge_ids) == DEFERRED_RESIDUAL_EDGE_IDS

    # Rebuild still succeeds for this ledger-backed foreign head.
    pinned = kernel.rebuild_from_contributions(
        root,
        world_id=ELDYRWILD_WORLD_ID,
        compare_revision_id=merged.revision_id,
        publish=False,
    )
    assert "rebuild_equivalent_to_pinned_revision" in list(
        getattr(pinned, "diagnostics", []) or []
    )

    assert verify_relationship_semantic_closure(root=root, repo=REPO) is None
    with pytest.raises(RelationshipSemanticClosureError) as excinfo:
        finalize_relationship_semantic_closure(root=root, repo=REPO)
    assert excinfo.value.code == "finalize_refused"


def test_partial_resume_refuses_when_applied_unit_target_source_drifts(
    tmp_path: Path,
) -> None:
    """Applied-prefix units must keep original target-contribution authority sealed."""
    from graph_memory.world_supergraph.contribution_store import (
        load_contribution_record,
        write_contribution_record,
    )

    root = _clone_eldyrwild(tmp_path)
    manifest = _manifest()
    # Apply a clean prefix of the first mutable unit, then drift its target source.
    first_unit = next(u for u in manifest["units"] if not u.get("deferred"))
    _apply_single_unit_ops(root, manifest, first_unit)

    target_cid = first_unit["target_contribution_ids"][0]
    ledger = load_contribution_record(root, ELDYRWILD_WORLD_ID, target_cid)
    tampered = ledger.model_copy(update={"authored_by": "not-gm"})
    write_contribution_record(root, ELDYRWILD_WORLD_ID, tampered)

    with pytest.raises(RelationshipSemanticClosureError) as excinfo:
        apply_relationship_semantic_closure(
            expected_base_revision_id=BASE_REVISION_ID, root=root, repo=REPO
        )
    assert excinfo.value.code == "preflight_failed"
    assert "target_source_" in str(excinfo.value)
