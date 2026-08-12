"""Tests for the Eldyrwild relationship semantic closure program.

Covers the locked 55-row closure manifest, whole-ledger preflight, prefix-safe
apply on an exact-Q4 clone, per-closure-kind effects (identity merges,
governed replacements, compound decomposition, contradiction-only), durable
identity-decision ledger sync, idempotent/partial resume, and the finalizer
pin contract.
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
    EXPECTED_FINAL_INVENTORY,
    LOCKED_MANIFEST_SHA256,
    MANIFEST_RELPATH,
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


def _apply_single_unit_ops(root: Path, manifest: dict[str, Any], unit: dict) -> None:
    """Apply one unit's ops directly through kernel seams (crash simulation)."""
    for op in unit["operations"]:
        _h, _r, store = kernel.open_current_world_graph(root, ELDYRWILD_WORLD_ID)
        parent = kernel.open_world_graph_head(root, ELDYRWILD_WORLD_ID).head_revision_id
        if closure_service._op_applied(store, unit, op):
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
    assert manifest["unit_order"] == [u["unit_id"] for u in manifest["units"]]
    assert [u["ordinal"] for u in manifest["units"]] == list(range(1, 56))
    assert set(manifest["artifacts"]) == {
        "source-corrections",
        "compound-decompositions",
        "identity-migrations",
        "unsupported-assertions",
    }
    counts = {"identity_merge": 0, "contradicts_and_replaces": 0,
              "compound_decomposition": 0, "contradiction_only": 0}
    for unit in manifest["units"]:
        counts[unit["closure_kind"]] += 1
    assert counts == {
        "identity_merge": 7,
        "contradicts_and_replaces": 2,
        "compound_decomposition": 1,
        "contradiction_only": 45,
    }
    # Disposition ordering: identity -> source -> compound -> unsupported.
    ranks = {
        "IDENTITY_NOT_RELATIONSHIP": 0,
        "SOURCE_CORRECTION_REQUIRED": 1,
        "COMPOUND_ASSERTION_NOT_SINGLE_RELATIONSHIP": 2,
        "INSUFFICIENT_EVIDENCE": 3,
    }
    order = [ranks[u["disposition"]] for u in manifest["units"]]
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
    assert status.applied_unit_count == 0
    assert status.next_pending_unit_id == "closure-unit:001"


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


# ---------------------------------------------------------------------------
# Full closure exit (§15)
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
    assert len(result.applied_unit_ids) == 55
    assert result.already_applied_unit_ids == []
    assert len(result.published_revision_ids) == 63
    assert result.verify_passed
    assert result.final_inventory == EXPECTED_FINAL_INVENTORY

    head = kernel.open_world_graph_head(root, ELDYRWILD_WORLD_ID)
    assert head.head_revision_id == result.final_revision_id
    assert head.head_revision_id != BASE_REVISION_ID

    eff = analyze_relationship_effective_conformance_v1(
        root=root, world_id=ELDYRWILD_WORLD_ID, revision_id=head.head_revision_id
    )
    assert eff.relationship_semantic_count == 314
    assert eff.relationship_effectively_represented_count == 314
    assert eff.relationship_effective_residual_count == 0
    assert eff.uses_statblock_mechanics_count == 3
    assert eff.unadjudicated_remaining_count == 0
    assert eff.dungeonmind_owned_remaining_count == 0
    assert eff.dungeonmindbuddy_owned_remaining_count == 0
    assert eff.requires_readjudication_count == 0
    assert eff.remaining_residual_edge_ids == []


def test_closure_idempotent_resume(tmp_path: Path) -> None:
    root = _clone_eldyrwild(tmp_path)
    first = _apply_full(root)
    second = apply_relationship_semantic_closure(
        expected_base_revision_id=BASE_REVISION_ID, root=root, repo=REPO
    )
    assert second.failed_unit_id is None
    assert second.published_revision_ids == []
    assert second.applied_unit_ids == []
    assert len(second.already_applied_unit_ids) == 55
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
    assert len(result.applied_unit_ids) == 54
    assert result.verify_passed
    assert result.final_inventory == EXPECTED_FINAL_INVENTORY


def test_closure_non_prefix_applied_set_refused(tmp_path: Path) -> None:
    root = _clone_eldyrwild(tmp_path)
    manifest = _manifest()
    # Apply unit 2 while unit 1 is pending: not a manifest-order prefix.
    _apply_single_unit_ops(root, manifest, manifest["units"][1])
    with pytest.raises(RelationshipSemanticClosureError) as excinfo:
        apply_relationship_semantic_closure(
            expected_base_revision_id=BASE_REVISION_ID, root=root, repo=REPO
        )
    assert excinfo.value.code == "preflight_failed"
    assert "applied_units_not_a_prefix" in str(excinfo.value)


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
    assert len(contradiction_units) == 45
    for unit in contradiction_units:
        row = _support_row(store, unit["target_assertion_id"])
        assert row["support_state"] == "contradicted"
        assert (row.get("active_contribution_ids") or []) == []
        assert unit["edge_id"] not in current


def test_closure_preserves_unaffected_current_edges(tmp_path: Path) -> None:
    root = _clone_eldyrwild(tmp_path)
    before = _current_edge_ids(_load_store(root))
    manifest = _manifest()
    target_edges = {u["edge_id"] for u in manifest["units"]}
    assert target_edges <= before

    _apply_full(root)
    after = _current_edge_ids(_load_store(root))

    assert before - target_edges <= after
    new_edges = after - (before - target_edges)
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
    # 45 contradiction-only + 7 identity + 2 replacement + 1 decomposition
    # contradiction + 1 decomposition additive = 56 closure contributions.
    assert len(closure_contribution_ids) == 56
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
    assert pin.residual_edge_ids == []
    assert pin.base_revision_id == BASE_REVISION_ID
    assert len(pin.final_graph_payload_sha256) == 64

    verify = verify_relationship_semantic_closure(root=root, repo=REPO)
    assert verify is not None
    assert verify.final_revision_id == pin.final_revision_id
