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


def _merge_shadow(
    source_id: str = "npc_shadow_src",
    target_id: str = "npc_shadow_tgt",
    source_label: str = "Shadow Name",
    target_label: str = "Canonical Name",
) -> tuple[UnionSupergraphStore, object]:
    store = _base_store()
    store = _add_node(store, _npc(source_id, source_label, source_label))
    store = _add_node(store, _npc(target_id, target_label, target_label))
    return kernel.merge_identity(
        store,
        world_id="eldyrwild",
        source_node_id=source_id,
        target_node_id=target_id,
        actor="gm:drakosfire",
        reason="merge shadow source into survivor",
    )


def test_remove_identity_alias_retires_merge_shadow_and_preserves_history() -> None:
    merged, merge_decision = _merge_shadow()
    merge_before = dict(next(
        item for item in merged.identity_decisions
        if item["decision_id"] == merge_decision.decision_id
    ))
    redirects_before = [item.model_dump(mode="json") for item in merged.identity_redirects]
    evidence_before = list(merged.nodes["npc_shadow_tgt"].evidence_ref_ids)

    updated, decision = kernel.remove_identity_alias(
        merged,
        world_id="eldyrwild",
        subject_node_id="npc_shadow_tgt",
        alias="Shadow Name",
        actor="gm:drakosfire",
        reason="retire merge-shadow alias",
    )

    assert decision.decision_kind == "alias_remove"
    assert decision.subject_node_id == "npc_shadow_tgt"
    assert decision.target_node_id is None
    assert decision.alias == "Shadow Name"
    assert decision.merge_side_effects is None
    assert decision.affected_node_ids == ["npc_shadow_tgt"]
    assert "Shadow Name" not in updated.nodes["npc_shadow_tgt"].aliases
    assert updated.aliases.get("shadow name") is None
    assert updated.aliases.get("canonical name") == "npc_shadow_tgt"

    merge_after = dict(next(
        item for item in updated.identity_decisions
        if item["decision_id"] == merge_decision.decision_id
    ))
    assert merge_after == merge_before
    assert "Shadow Name" in merge_decision.merge_side_effects.aliases_added_to_target
    assert [item.model_dump(mode="json") for item in updated.identity_redirects] == redirects_before
    assert updated.nodes["npc_shadow_src"].state.get("memory_state") == "merged_away"
    assert list(updated.nodes["npc_shadow_tgt"].evidence_ref_ids) == evidence_before
    assert any(item["decision_id"] == decision.decision_id for item in updated.identity_decisions)


def test_remove_identity_alias_retains_shared_remaining_index_key() -> None:
    store = _base_store()
    store = _add_node(store, _npc("npc_src", "Extra Alias", "Extra Alias"))
    store = _add_node(store, _npc("npc_tgt", "Keep Key", "Keep Key", "Extra Alias"))
    merged, _ = kernel.merge_identity(
        store,
        world_id="eldyrwild",
        source_node_id="npc_src",
        target_node_id="npc_tgt",
        actor="gm:drakosfire",
        reason="union extra alias",
    )
    # Target label still produces keep key after Extra Alias is retired.
    updated, _ = kernel.remove_identity_alias(
        merged,
        world_id="eldyrwild",
        subject_node_id="npc_tgt",
        alias="Extra Alias",
        actor="gm:drakosfire",
        reason="drop extra alias only",
    )
    assert updated.aliases.get("extra alias") is None
    assert updated.aliases.get("keep key") == "npc_tgt"


def test_remove_identity_alias_exact_retry_is_noop() -> None:
    merged, _ = _merge_shadow()
    first, decision = kernel.remove_identity_alias(
        merged,
        world_id="eldyrwild",
        subject_node_id="npc_shadow_tgt",
        alias="Shadow Name",
        actor="gm:drakosfire",
        reason="retire merge-shadow alias",
    )
    second, retry = kernel.remove_identity_alias(
        first,
        world_id="eldyrwild",
        subject_node_id="npc_shadow_tgt",
        alias="Shadow Name",
        actor="gm:drakosfire",
        reason="retire merge-shadow alias",
    )
    assert retry.decision_id == decision.decision_id
    assert second.identity_decisions == first.identity_decisions
    assert second.nodes["npc_shadow_tgt"].aliases == first.nodes["npc_shadow_tgt"].aliases
    assert second.aliases == first.aliases


def test_remove_identity_alias_same_reason_after_reintroduction_refuses() -> None:
    merged, _ = _merge_shadow()
    removed, _ = kernel.remove_identity_alias(
        merged,
        world_id="eldyrwild",
        subject_node_id="npc_shadow_tgt",
        alias="Shadow Name",
        actor="gm:drakosfire",
        reason="retire merge-shadow alias",
    )
    reintroduced, _ = kernel.merge_identity(
        _add_node(removed, _npc("npc_shadow_src2", "Shadow Name", "Shadow Name")),
        world_id="eldyrwild",
        source_node_id="npc_shadow_src2",
        target_node_id="npc_shadow_tgt",
        actor="gm:drakosfire",
        reason="later merge reintroduces shadow",
    )
    assert "Shadow Name" in reintroduced.nodes["npc_shadow_tgt"].aliases
    try:
        kernel.remove_identity_alias(
            reintroduced,
            world_id="eldyrwild",
            subject_node_id="npc_shadow_tgt",
            alias="Shadow Name",
            actor="gm:drakosfire",
            reason="retire merge-shadow alias",
        )
        raise AssertionError("expected reintroduction collision")
    except ValueError as exc:
        assert "reintroduction collision" in str(exc)
    assert "Shadow Name" in reintroduced.nodes["npc_shadow_tgt"].aliases


def test_remove_identity_alias_new_reason_after_reintroduction_succeeds() -> None:
    merged, first_merge = _merge_shadow()
    removed, first_remove = kernel.remove_identity_alias(
        merged,
        world_id="eldyrwild",
        subject_node_id="npc_shadow_tgt",
        alias="Shadow Name",
        actor="gm:drakosfire",
        reason="retire merge-shadow alias",
    )
    reintroduced, _ = kernel.merge_identity(
        _add_node(removed, _npc("npc_shadow_src2", "Shadow Name", "Shadow Name")),
        world_id="eldyrwild",
        source_node_id="npc_shadow_src2",
        target_node_id="npc_shadow_tgt",
        actor="gm:drakosfire",
        reason="later merge reintroduces shadow",
    )
    updated, second_remove = kernel.remove_identity_alias(
        reintroduced,
        world_id="eldyrwild",
        subject_node_id="npc_shadow_tgt",
        alias="Shadow Name",
        actor="gm:drakosfire",
        reason="retire reintroduced shadow",
    )
    assert second_remove.decision_id != first_remove.decision_id
    assert "Shadow Name" not in updated.nodes["npc_shadow_tgt"].aliases
    assert any(item["decision_id"] == first_remove.decision_id for item in updated.identity_decisions)
    merge_row = next(
        item for item in updated.identity_decisions
        if item["decision_id"] == first_merge.decision_id
    )
    assert "Shadow Name" in merge_row["merge_side_effects"]["aliases_added_to_target"]


def test_remove_identity_alias_refuses_missing_alias() -> None:
    merged, _ = _merge_shadow()
    try:
        kernel.remove_identity_alias(
            merged,
            world_id="eldyrwild",
            subject_node_id="npc_shadow_tgt",
            alias="Not Present",
            actor="gm:drakosfire",
            reason="missing",
        )
        raise AssertionError("expected missing alias to fail")
    except ValueError as exc:
        assert "not currently materialized" in str(exc)


def test_remove_identity_alias_refuses_canonical_label() -> None:
    merged, _ = _merge_shadow()
    try:
        kernel.remove_identity_alias(
            merged,
            world_id="eldyrwild",
            subject_node_id="npc_shadow_tgt",
            alias="Canonical Name",
            actor="gm:drakosfire",
            reason="unlabel",
        )
        raise AssertionError("expected canonical label refusal")
    except ValueError as exc:
        assert "canonical label" in str(exc)


def test_remove_identity_alias_refuses_merged_away_subject() -> None:
    merged, _ = _merge_shadow()
    try:
        kernel.remove_identity_alias(
            merged,
            world_id="eldyrwild",
            subject_node_id="npc_shadow_src",
            alias="Shadow Name",
            actor="gm:drakosfire",
            reason="wrong subject",
        )
        raise AssertionError("expected merged-away subject refusal")
    except ValueError as exc:
        assert "merged_away" in str(exc)


def test_remove_identity_alias_refuses_unknown_subject() -> None:
    store = _base_store()
    try:
        kernel.remove_identity_alias(
            store,
            world_id="eldyrwild",
            subject_node_id="npc_missing",
            alias="X",
            actor="gm:drakosfire",
            reason="missing node",
        )
        raise AssertionError("expected unknown subject")
    except KeyError as exc:
        assert "npc_missing" in str(exc)


def test_record_identity_decision_refuses_alias_remove() -> None:
    store = _base_store()
    decision = kernel.build_identity_decision_record(
        world_id="eldyrwild",
        decision_kind="alias_remove",
        actor="gm:drakosfire",
        reason="append only",
        subject_node_id="npc_shadow_tgt",
        alias="Shadow Name",
    )
    try:
        kernel.record_identity_decision(store, decision)
        raise AssertionError("expected append-only alias_remove refusal")
    except ValueError as exc:
        assert "remove_identity_alias" in str(exc)


def test_unmerge_refuses_after_later_alias_remove() -> None:
    merged, merge_decision = _merge_shadow()
    removed, _ = kernel.remove_identity_alias(
        merged,
        world_id="eldyrwild",
        subject_node_id="npc_shadow_tgt",
        alias="Shadow Name",
        actor="gm:drakosfire",
        reason="retire merge-shadow alias",
    )
    try:
        kernel.unmerge_identity(
            removed,
            world_id="eldyrwild",
            decision_id=merge_decision.decision_id,
            actor="gm:drakosfire",
            reason="undo merge after remove",
        )
        raise AssertionError("expected unmerge composition refusal")
    except ValueError as exc:
        assert "later alias_remove" in str(exc)
    assert "Shadow Name" not in removed.nodes["npc_shadow_tgt"].aliases
    original = next(
        item for item in removed.identity_decisions
        if item["decision_id"] == merge_decision.decision_id
    )
    assert original["status"] == "active"


def test_remove_identity_alias_refuses_unresolved_support() -> None:
    merged, _ = _merge_shadow()
    support = kernel.DurableAssertionSupport(
        assertion_id="assertion:unresolved-alias",
        active_contribution_ids=["contribution:missing"],
        support_state="supported",
        assertion_kind="alias",
        graph_object_id="npc_shadow_tgt",
    )
    blocked = merged.model_copy(
        update={
            "assertion_support": {
                support.assertion_id: support.model_dump(mode="json"),
            }
        }
    )
    try:
        kernel.remove_identity_alias(
            blocked,
            world_id="eldyrwild",
            subject_node_id="npc_shadow_tgt",
            alias="Shadow Name",
            actor="gm:drakosfire",
            reason="unresolved",
        )
        raise AssertionError("expected unresolved support refusal")
    except ValueError as exc:
        assert "cannot resolve assertion support" in str(exc)


def test_remove_identity_alias_refuses_bundled_node_alias(tmp_path) -> None:
    from graph_memory.union_supergraph.load import load_union_supergraph_store

    store = load_union_supergraph_store(DEFAULT_FIXTURE_PATH)
    kernel.publish_world_revision(
        tmp_path,
        "eldyrwild",
        store,
        operation_ids=["op:alias-remove-node-support"],
    )
    assertion = kernel.build_assertion(
        assertion_kind="node",
        acceptance_state="accepted",
        subject_node_id="npc_grounded_node",
        label="Grounded Node",
        value={
            "kind": "npc",
            "role": "npc",
            "source_domains": ["manual_seed"],
            "aliases": ["Grounded Node", "Bundled Alias"],
        },
        source_artifact_id="artifact:grounded-node",
        campaign_scope="longmont-c2",
        epistemic_kind="fact",
        visibility="gm",
        identity_resolution_outcome="created_new",
    )
    authored = kernel.create_graph_contribution(
        world_id="eldyrwild",
        source_kind="graph_review_authored_assertion",
        source_artifact_id="artifact:grounded-node",
        source_revision_id="authored-grounded-node",
        authored_by="gm",
        accepted_assertions=[assertion],
    )
    merge = kernel.merge_contribution_to_revision(
        tmp_path, world_id="eldyrwild", contribution=authored
    )
    assert merge.published is True
    _head, _rev, current = kernel.open_current_world_graph(tmp_path, "eldyrwild")
    try:
        kernel.remove_identity_alias(
            current,
            world_id="eldyrwild",
            subject_node_id="npc_grounded_node",
            alias="Bundled Alias",
            actor="gm:drakosfire",
            reason="source grounded",
            root=tmp_path,
        )
        raise AssertionError("expected bundled node alias refusal")
    except ValueError as exc:
        assert "independent semantic support" in str(exc)


def test_remove_identity_alias_refuses_explicit_alias_assertion(tmp_path) -> None:
    from graph_memory.union_supergraph.load import load_union_supergraph_store

    store = load_union_supergraph_store(DEFAULT_FIXTURE_PATH)
    kernel.publish_world_revision(
        tmp_path,
        "eldyrwild",
        store,
        operation_ids=["op:alias-remove-alias-support"],
    )
    node_assertion = kernel.build_assertion(
        assertion_kind="node",
        acceptance_state="accepted",
        subject_node_id="npc_grounded_alias",
        label="Grounded Alias Node",
        value={
            "kind": "npc",
            "role": "npc",
            "source_domains": ["manual_seed"],
            "aliases": ["Grounded Alias Node"],
        },
        source_artifact_id="artifact:grounded-alias",
        campaign_scope="longmont-c2",
        epistemic_kind="fact",
        visibility="gm",
        identity_resolution_outcome="created_new",
    )
    alias_assertion = kernel.build_assertion(
        assertion_kind="alias",
        acceptance_state="accepted",
        subject_node_id="npc_grounded_alias",
        label="Explicit Alias",
        value={"alias": "Explicit Alias"},
        source_artifact_id="artifact:grounded-alias",
        campaign_scope="longmont-c2",
        epistemic_kind="fact",
        visibility="gm",
        identity_resolution_outcome="resolved_existing",
    )
    authored = kernel.create_graph_contribution(
        world_id="eldyrwild",
        source_kind="graph_review_authored_assertion",
        source_artifact_id="artifact:grounded-alias",
        source_revision_id="authored-grounded-alias",
        authored_by="gm",
        accepted_assertions=[node_assertion, alias_assertion],
    )
    merge = kernel.merge_contribution_to_revision(
        tmp_path, world_id="eldyrwild", contribution=authored
    )
    assert merge.published is True
    _head, _rev, current = kernel.open_current_world_graph(tmp_path, "eldyrwild")
    try:
        kernel.remove_identity_alias(
            current,
            world_id="eldyrwild",
            subject_node_id="npc_grounded_alias",
            alias="Explicit Alias",
            actor="gm:drakosfire",
            reason="source grounded alias assertion",
            root=tmp_path,
        )
        raise AssertionError("expected explicit alias assertion refusal")
    except ValueError as exc:
        assert "independent semantic support" in str(exc)