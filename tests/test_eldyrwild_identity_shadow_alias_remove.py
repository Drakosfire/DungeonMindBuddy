"""Governed exact-six Eldyrwild identity-shadow alias_remove proofs."""

from __future__ import annotations

import os
import shutil
from pathlib import Path

import pytest

import graph_memory.kernel as kernel
from apps.live_control_server.config import live_world_graph_root, world_graph_root
from apps.live_control_server.integrations.dungeonmind_kernel.relationship_effective_conformance_v1 import (
    analyze_relationship_effective_conformance_v1,
)
from apps.live_control_server.services.eldyrwild_identity_shadow_alias_remove import (
    EXPECTED_CANONICAL_REVISION_ID,
    EXPECTED_RELATIONSHIP_INVENTORY,
    KEEPER_ALIASES,
    SHADOW_ALIAS_TARGETS,
    WORLD_ID,
    EldyrwildIdentityShadowAliasRemoveError,
    apply_eldyrwild_identity_shadow_alias_remove,
    expected_decision_id,
    get_eldyrwild_identity_shadow_alias_remove_status,
    retirement_reason,
)
from graph_memory.world_supergraph.contribution_store import load_contribution_index
from graph_memory.world_supergraph.identity_decision_store import (
    load_identity_decision_record,
)


def _clone_eldyrwild(tmp_path: Path) -> Path:
    src_root = world_graph_root()
    eldyrwild_src = src_root / "graph_memory" / "worlds" / "eldyrwild"
    if not eldyrwild_src.is_dir():
        pytest.skip("Eldyrwild world graph not present")
    (tmp_path / "graph_memory" / "worlds").mkdir(parents=True)
    shutil.copytree(eldyrwild_src, tmp_path / "graph_memory" / "worlds" / "eldyrwild")
    runs = src_root / "graph_memory" / "runs"
    if runs.is_dir():
        os.symlink(runs, tmp_path / "graph_memory" / "runs")
    return tmp_path


def _alias_present(store: object, node_id: str, alias: str) -> bool:
    node = store.nodes[node_id]
    key = alias.casefold()
    return any(item.strip() and item.casefold() == key for item in node.aliases)


def _merge_payload(store: object, decision_id: str) -> dict[str, object]:
    for raw in store.identity_decisions:
        payload = dict(raw)
        if payload.get("decision_id") == decision_id:
            return payload
    raise AssertionError(f"missing merge {decision_id}")


def _inventory(root: Path, revision_id: str) -> dict[str, int]:
    eff = analyze_relationship_effective_conformance_v1(
        root=root, world_id=WORLD_ID, revision_id=revision_id
    )
    return {
        "semantic": eff.relationship_semantic_count,
        "represented": eff.relationship_effectively_represented_count,
        "residual": eff.relationship_effective_residual_count,
        "uses_statblock_mechanics": eff.uses_statblock_mechanics_count,
    }


def _assert_rebuild_equivalent(root: Path, revision_id: str) -> None:
    pinned = kernel.rebuild_from_contributions(
        root,
        world_id=WORLD_ID,
        compare_revision_id=revision_id,
        publish=False,
    )
    unpinned = kernel.rebuild_from_contributions(
        root,
        world_id=WORLD_ID,
        publish=False,
    )
    pinned_diag = list(getattr(pinned, "diagnostics", []) or [])
    unpinned_diag = list(getattr(unpinned, "diagnostics", []) or [])
    assert "rebuild_equivalent_to_pinned_revision" in pinned_diag
    assert (
        "rebuild_equivalent_to_head" in unpinned_diag
        or "rebuild_equivalent_to_published_head" in unpinned_diag
    )


def _assert_cleaned_store(store: object) -> None:
    for target in SHADOW_ALIAS_TARGETS:
        assert not _alias_present(store, target.survivor_node_id, target.alias)
        owner = store.aliases.get(target.derived_store_key)
        node = store.nodes[target.survivor_node_id]
        remaining_keys = {node.label.casefold(), *(item.casefold() for item in node.aliases)}
        if target.derived_store_key not in remaining_keys:
            assert owner != target.survivor_node_id
    for keeper in KEEPER_ALIASES:
        assert _alias_present(store, keeper.node_id, keeper.alias)


def test_package_targets_are_exactly_six_named_aliases() -> None:
    assert len(SHADOW_ALIAS_TARGETS) == 6
    survivors = [target.survivor_node_id for target in SHADOW_ALIAS_TARGETS]
    aliases = [target.alias for target in SHADOW_ALIAS_TARGETS]
    assert len(set(survivors)) == 6
    assert len(set(aliases)) == 6
    keeper_ids = {keeper.node_id for keeper in KEEPER_ALIASES}
    keeper_aliases = {keeper.alias.casefold() for keeper in KEEPER_ALIASES}
    assert keeper_ids.isdisjoint(set(survivors))
    assert keeper_aliases.isdisjoint({alias.casefold() for alias in aliases})
    assert "Captain" in {keeper.alias for keeper in KEEPER_ALIASES}
    assert "Thrin Branchborn" in {keeper.alias for keeper in KEEPER_ALIASES}


def test_status_on_current_clone_is_eligible(tmp_path: Path) -> None:
    root = _clone_eldyrwild(tmp_path)
    status = get_eldyrwild_identity_shadow_alias_remove_status(root=root)
    if status.head_revision_id != EXPECTED_CANONICAL_REVISION_ID:
        pytest.skip(
            f"clone head {status.head_revision_id} is not the expected canonical pin"
        )
    assert status.eligibility == "eligible"
    assert status.keeper_aliases_present is True
    assert status.retired_alias_count == 0


def test_apply_refuses_live_world_without_opt_in() -> None:
    live = live_world_graph_root()
    if not (live / "graph_memory" / "worlds" / "eldyrwild").is_dir():
        pytest.skip("live Eldyrwild world graph not present")
    with pytest.raises(EldyrwildIdentityShadowAliasRemoveError) as exc:
        apply_eldyrwild_identity_shadow_alias_remove(
            expected_parent_revision_id=EXPECTED_CANONICAL_REVISION_ID,
            root=live,
            allow_live_world=False,
        )
    assert exc.value.code == "live_world_opt_in_required"


def test_apply_refuses_stale_expected_parent(tmp_path: Path) -> None:
    root = _clone_eldyrwild(tmp_path)
    with pytest.raises(EldyrwildIdentityShadowAliasRemoveError) as exc:
        apply_eldyrwild_identity_shadow_alias_remove(
            expected_parent_revision_id="rev:not-the-current-head",
            root=root,
            allow_live_world=False,
        )
    assert exc.value.code == "stale_expected_parent"


def test_keepers_refuse_remove_identity_alias(tmp_path: Path) -> None:
    root = _clone_eldyrwild(tmp_path)
    _, _, store = kernel.open_current_world_graph(root, WORLD_ID)
    for keeper in KEEPER_ALIASES:
        with pytest.raises(ValueError) as exc:
            kernel.remove_identity_alias(
                store,
                world_id=WORLD_ID,
                subject_node_id=keeper.node_id,
                alias=keeper.alias,
                actor="gm",
                reason="test keeper removal must fail",
                root=root,
            )
        assert "independent semantic support" in str(exc.value)
        assert _alias_present(store, keeper.node_id, keeper.alias)


def test_clone_apply_replay_retry_and_invariants(tmp_path: Path) -> None:
    root = _clone_eldyrwild(tmp_path)
    head, _, before = kernel.open_current_world_graph(root, WORLD_ID)
    parent = head.head_revision_id
    if parent != EXPECTED_CANONICAL_REVISION_ID:
        pytest.skip(f"clone head {parent} is not the expected canonical pin")

    merge_before = {
        target.merge_decision_id: _merge_payload(before, target.merge_decision_id)
        for target in SHADOW_ALIAS_TARGETS
    }
    contribution_ids_before = set(
        load_contribution_index(root, WORLD_ID).all_contribution_ids
    )
    inventory_before = _inventory(root, parent)

    result = apply_eldyrwild_identity_shadow_alias_remove(
        expected_parent_revision_id=parent,
        root=root,
        allow_live_world=False,
    )
    assert result.published is True
    assert result.eligibility == "eligible"
    assert result.parent_revision_id == parent
    assert result.revision_id
    assert result.revision_id != parent
    assert result.decision_ids == [
        expected_decision_id(target) for target in SHADOW_ALIAS_TARGETS
    ]

    head_after, _, after = kernel.open_current_world_graph(root, WORLD_ID)
    assert head_after.head_revision_id == result.revision_id
    _assert_cleaned_store(after)
    for target in SHADOW_ALIAS_TARGETS:
        assert _merge_payload(after, target.merge_decision_id) == merge_before[
            target.merge_decision_id
        ]
        redirect = next(
            item
            for item in after.identity_redirects
            if item.from_node_id == target.merged_away_node_id and item.status == "active"
        )
        assert redirect.to_node_id == target.survivor_node_id
        away = after.nodes[target.merged_away_node_id]
        away_state = str(away.state.get("memory_state") or "")
        away_canon = str(
            away.state.get("identity_canon_state") or away.state.get("canon_state") or ""
        )
        assert away_state == "merged_away" or away_canon == "merged_away"
        record = load_identity_decision_record(
            root, WORLD_ID, expected_decision_id(target)
        )
        assert record.decision_kind == "alias_remove"
        assert record.subject_node_id == target.survivor_node_id
        assert record.alias == target.alias
        assert record.reason == retirement_reason(target)

    assert set(load_contribution_index(root, WORLD_ID).all_contribution_ids) == (
        contribution_ids_before
    )
    assert _inventory(root, result.revision_id) == inventory_before
    assert inventory_before == EXPECTED_RELATIONSHIP_INVENTORY
    _assert_rebuild_equivalent(root, result.revision_id)

    retry = apply_eldyrwild_identity_shadow_alias_remove(
        expected_parent_revision_id=result.revision_id,
        root=root,
        allow_live_world=False,
    )
    assert retry.published is False
    assert retry.eligibility == "already_applied"
    retry_head, _, retry_store = kernel.open_current_world_graph(root, WORLD_ID)
    assert retry_head.head_revision_id == result.revision_id
    _assert_cleaned_store(retry_store)


def test_apply_script_status_on_clone(tmp_path: Path) -> None:
    root = _clone_eldyrwild(tmp_path)
    from scripts.apply_eldyrwild_identity_shadow_alias_remove import main

    code = main(["status", "--root", str(root)])
    assert code == 0
