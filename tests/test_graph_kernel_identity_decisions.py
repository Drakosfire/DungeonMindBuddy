"""Graph Kernel identity decision / merge / split / unmerge tests (PR004)."""

from __future__ import annotations

import graph_memory.kernel as kernel
from graph_memory.union_supergraph.load import (
    DEFAULT_FIXTURE_PATH,
    load_union_supergraph_payload,
    parse_union_supergraph_store,
)
from graph_memory.union_supergraph.model import UnionSupergraphNode, UnionSupergraphStore
from graph_memory.union_supergraph.redirects import (
    active_identity_redirect_map,
    is_redirected_node_id,
)


def _base_store() -> UnionSupergraphStore:
    return parse_union_supergraph_store(load_union_supergraph_payload(DEFAULT_FIXTURE_PATH))


def _add_node(store: UnionSupergraphStore, node: UnionSupergraphNode) -> UnionSupergraphStore:
    nodes = dict(store.nodes)
    nodes[node.node_id] = node
    aliases = dict(store.aliases)
    for alias in node.aliases:
        aliases[alias.casefold()] = node.node_id
    aliases[node.label.casefold()] = node.node_id
    adjacency = dict(store.adjacency)
    adjacency.setdefault(node.node_id, [])
    return store.model_copy(update={"nodes": nodes, "aliases": aliases, "adjacency": adjacency})


def _npc(node_id: str, label: str, *aliases: str) -> UnionSupergraphNode:
    return UnionSupergraphNode(
        node_id=node_id,
        label=label,
        kind="npc",
        role="npc",
        aliases=list(aliases) or [label],
        source_domains=["recap"],
        evidence_ref_ids=[f"evidence:{node_id}"],
        state={
            "memory_state": "graph_read_model",
            "identity_canon_state": "canonical",
        },
    )


def test_merge_identity_creates_redirect_and_decision() -> None:
    store = _base_store()
    store = _add_node(store, _npc("npc_lysandra_dup", "Lysandra", "Lysandra"))
    store = _add_node(store, _npc("npc_lysandra", "Captain Lysandra", "Lysandra Ironveil"))

    updated, decision = kernel.merge_identity(
        store,
        world_id="eldyrwild",
        source_node_id="npc_lysandra_dup",
        target_node_id="npc_lysandra",
        actor="gm:drakosfire",
        reason="Same character across ingest duplicate and hub",
    )

    assert decision.decision_kind == "merge"
    assert decision.subject_node_id == "npc_lysandra_dup"
    assert decision.target_node_id == "npc_lysandra"
    assert "npc_lysandra_dup" in decision.affected_node_ids
    assert "npc_lysandra" in decision.affected_node_ids
    assert decision.merge_side_effects is not None
    assert "Lysandra" in decision.merge_side_effects.aliases_added_to_target
    assert "evidence:npc_lysandra_dup" in decision.merge_side_effects.evidence_ref_ids_added_to_target
    assert any(
        rewrite.alias_key == "lysandra" for rewrite in decision.merge_side_effects.alias_map_rewrites
    )

    assert is_redirected_node_id("npc_lysandra_dup", updated.identity_redirects)
    active = active_identity_redirect_map(updated.identity_redirects)
    assert active["npc_lysandra_dup"].to_node_id == "npc_lysandra"

    source = updated.nodes["npc_lysandra_dup"]
    assert source.state.get("memory_state") == "merged_away"
    assert source.state.get("identity_canon_state") == "merged_away"
    assert source.state.get("merged_into") == "npc_lysandra"
    # Source remains inspectable; aliases/evidence not silently lost on target.
    target = updated.nodes["npc_lysandra"]
    assert "Lysandra" in target.aliases or "lysandra" in {a.casefold() for a in target.aliases}
    assert "evidence:npc_lysandra_dup" in target.evidence_ref_ids
    assert any(d["decision_id"] == decision.decision_id for d in updated.identity_decisions)


def test_split_identity_creates_replayable_decision() -> None:
    store = _add_node(_base_store(), _npc("npc_merged", "Twin Figure", "Twin"))
    updated, decision = kernel.split_identity(
        store,
        world_id="eldyrwild",
        merged_node_id="npc_merged",
        new_node_id="npc_split_sibling",
        actor="gm:drakosfire",
        reason="Twin Figure was two people",
    )

    assert decision.decision_kind == "split"
    assert set(decision.affected_node_ids) == {"npc_merged", "npc_split_sibling"}
    assert "npc_split_sibling" in updated.nodes
    new_node = updated.nodes["npc_split_sibling"]
    assert new_node.state.get("identity_state") == "split_from"
    assert new_node.state.get("split_from_node_id") == "npc_merged"
    assert updated.nodes["npc_merged"].state.get("split_produced_node_id") == "npc_split_sibling"
    round_trip = kernel.IdentityDecisionRecord.model_validate(decision.model_dump(mode="json"))
    assert round_trip.decision_id == decision.decision_id


def test_unmerge_identity_supersedes_merge_decision() -> None:
    store = _base_store()
    store = _add_node(store, _npc("npc_a", "Aria Vale", "AriaVale"))
    store = _add_node(store, _npc("npc_b", "Aria Bright", "Bright"))

    merged, merge_decision = kernel.merge_identity(
        store,
        world_id="eldyrwild",
        source_node_id="npc_a",
        target_node_id="npc_b",
        actor="gm:drakosfire",
        reason="Mistaken merge of Aria",
    )
    assert is_redirected_node_id("npc_a", merged.identity_redirects)
    assert merged.aliases.get("ariavale") == "npc_b"
    assert "Aria Vale" in merged.nodes["npc_b"].aliases or "AriaVale" in merged.nodes["npc_b"].aliases

    unmerged, unmerge_decision = kernel.unmerge_identity(
        merged,
        world_id="eldyrwild",
        decision_id=merge_decision.decision_id,
        actor="gm:drakosfire",
        reason="Undo mistaken Aria merge",
    )

    assert unmerge_decision.decision_kind == "unmerge"
    assert merge_decision.decision_id in unmerge_decision.supersedes_decision_ids
    assert not is_redirected_node_id("npc_a", unmerged.identity_redirects)

    # Original merge decision remains inspectable as superseded.
    original = next(
        d for d in unmerged.identity_decisions if d["decision_id"] == merge_decision.decision_id
    )
    assert original["status"] == "superseded"
    assert original["decision_kind"] == "merge"
    assert original["merge_side_effects"] is not None

    restored = unmerged.nodes["npc_a"]
    assert restored.state.get("memory_state") == "graph_read_model"
    assert restored.state.get("identity_canon_state") == "canonical"
    assert "merged_into" not in restored.state

    # Alias/evidence delta reversed on target; source alias ownership restored.
    target_aliases = {a.casefold() for a in unmerged.nodes["npc_b"].aliases}
    assert "ariavale" not in target_aliases
    assert "aria vale" not in target_aliases
    assert "evidence:npc_a" not in unmerged.nodes["npc_b"].evidence_ref_ids
    assert unmerged.aliases.get("ariavale") == "npc_a"
    assert unmerged.aliases.get("aria vale") == "npc_a"


def test_unmerge_restores_alias_routing_away_from_old_target() -> None:
    store = _base_store()
    store = _add_node(store, _npc("npc_a", "Aria Vale", "AriaVale"))
    store = _add_node(store, _npc("npc_b", "Aria Bright", "Bright"))

    merged, merge_decision = kernel.merge_identity(
        store,
        world_id="eldyrwild",
        source_node_id="npc_a",
        target_node_id="npc_b",
        actor="gm:drakosfire",
        reason="Temporary merge",
    )
    unmerged, _ = kernel.unmerge_identity(
        merged,
        world_id="eldyrwild",
        decision_id=merge_decision.decision_id,
        actor="gm:drakosfire",
        reason="Undo temporary merge",
    )

    candidate = kernel.IdentityCandidate(
        world_id="eldyrwild",
        candidate_id="cand:aria-vale",
        label="Aria Vale",
        object_kind="npc",
        aliases=["AriaVale"],
        evidence_ref_ids=["evidence:session:aria"],
    )
    resolution = kernel.resolve_identity(unmerged, candidate)
    assert resolution.outcome == "resolved_existing"
    assert resolution.target_node_id == "npc_a"
    assert resolution.target_node_id != "npc_b"


def test_merge_rejects_noncanonical_provisional_target() -> None:
    store = _base_store()
    store = _add_node(store, _npc("npc_source", "Source", "Source"))
    provisional = UnionSupergraphNode(
        node_id="npc_prov_target",
        label="Target",
        kind="npc",
        role="npc",
        aliases=["Target"],
        source_domains=["recap"],
        evidence_ref_ids=["evidence:prov"],
        state={
            "memory_state": "graph_read_model",
            "identity_canon_state": "noncanonical_provisional",
        },
    )
    store = _add_node(store, provisional)

    try:
        kernel.merge_identity(
            store,
            world_id="eldyrwild",
            source_node_id="npc_source",
            target_node_id="npc_prov_target",
            actor="gm:drakosfire",
            reason="Should fail",
        )
        raise AssertionError("expected ValueError for provisional merge target")
    except ValueError as exc:
        assert "noncanonical_provisional" in str(exc)


def test_merge_rejects_merged_away_target() -> None:
    store = _base_store()
    store = _add_node(store, _npc("npc_x", "X", "X"))
    store = _add_node(store, _npc("npc_y", "Y", "Y"))
    store = _add_node(store, _npc("npc_z", "Z", "Z"))
    merged, _ = kernel.merge_identity(
        store,
        world_id="eldyrwild",
        source_node_id="npc_y",
        target_node_id="npc_z",
        actor="gm:drakosfire",
        reason="y into z",
    )
    try:
        kernel.merge_identity(
            merged,
            world_id="eldyrwild",
            source_node_id="npc_x",
            target_node_id="npc_y",
            actor="gm:drakosfire",
            reason="into merged-away y",
        )
        raise AssertionError("expected ValueError for merged_away merge target")
    except ValueError as exc:
        assert "merged_away" in str(exc)