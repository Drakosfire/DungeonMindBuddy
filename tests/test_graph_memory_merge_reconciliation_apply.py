from __future__ import annotations

from pathlib import Path

from graph_memory.union_supergraph.load import (
    DEFAULT_FIXTURE_PATH,
    load_union_supergraph_payload,
    load_union_supergraph_store,
    parse_union_supergraph_store,
)
from graph_memory.union_supergraph.merge_reconciliation import (
    MergeAssertionPlan,
    SurvivorHydrationPlan,
    UnionSupergraphMergePlan,
    make_identity_redirect_id,
    plan_authored_merge_reconciliation,
)
from graph_memory.union_supergraph.merge_reconciliation_apply import (
    apply_union_supergraph_merge_plan,
    apply_union_supergraph_merge_plan_to_file,
)
from graph_memory.union_supergraph.model import UnionIdentityRedirect
from graph_memory.union_supergraph.redirects import active_identity_redirect_map
from tests.test_graph_memory_merge_reconciliation_planner import (
    CAMPAIGN_ID,
    PASS_ID,
    STAMP,
    merge_assertion,
    minimal_union_store,
    object_ref,
    overlay_with_assertions,
    union_edge,
    union_node,
    _redirect,
)


def _lysandra_store_and_plan():
    store = minimal_union_store(
        nodes={
            "node:lysandra": union_node(),
            "location_mireward": union_node(
                node_id="location_mireward",
                label="Mireward",
                kind="location",
                role="location",
                aliases=["Mireward"],
                evidence_ref_ids=[],
            ),
        },
        edges={
            "edge:node:lysandra:travels_to:location_mireward": union_edge(),
        },
    )
    overlay = overlay_with_assertions(merge_assertion())
    plan = plan_authored_merge_reconciliation(
        campaign_id=CAMPAIGN_ID,
        overlay=overlay,
        union_store=store,
        materialization_pass_id=PASS_ID,
    )
    return store, plan


def _diagnostic_codes(result) -> set[str]:
    return {item.code for item in result.diagnostics}


def test_applies_lysandra_plan_in_memory() -> None:
    store, plan = _lysandra_store_and_plan()
    original_redirect_count = len(store.identity_redirects)

    updated_store, result = apply_union_supergraph_merge_plan(
        union_store=store,
        plan=plan,
        applied_at=STAMP,
    )

    assert len(store.identity_redirects) == original_redirect_count
    assert result.merge_records_added == 1
    assert result.redirects_added == 1
    assert len(updated_store.identity_redirects) == 1
    redirect = updated_store.identity_redirects[0]
    assert redirect.from_node_id == "node:lysandra"
    assert redirect.to_node_id == "party:captain_lysandra_ironveil"

    survivor = updated_store.nodes["party:captain_lysandra_ironveil"]
    assert "Lysandra" in survivor.aliases
    assert "evidence:session-23:lysandra:recap-mention" in survivor.evidence_ref_ids
    assert "recap" in survivor.source_domains

    merged_away = updated_store.nodes["node:lysandra"]
    assert merged_away.state["memory_state"] == "merged_away"
    assert merged_away.state["merged_into"] == "party:captain_lysandra_ironveil"

    active_edges = [
        edge
        for edge in updated_store.edges.values()
        if edge.state.get("memory_state") != "rewired_from_merged_away"
    ]
    assert any(
        edge.source_node_id == "party:captain_lysandra_ironveil"
        and edge.target_node_id == "location_mireward"
        for edge in active_edges
    )
    assert len(updated_store.identity_merge_records) == 1
    assert updated_store.identity_merge_records[0].assertion_id == "assert-merge-lysandra"
    assert "merge_assertion_applied" in _diagnostic_codes(result)


def test_gm_survivor_id_remains_canonical() -> None:
    store = minimal_union_store(
        nodes={
            "node:lysandra": union_node(
                evidence_ref_ids=[
                    "evidence:session-23:lysandra:recap-mention",
                    "evidence:worldbuilding:lysandra:note",
                ],
            ),
        }
    )
    overlay = overlay_with_assertions(merge_assertion())
    plan = plan_authored_merge_reconciliation(
        campaign_id=CAMPAIGN_ID,
        overlay=overlay,
        union_store=store,
        materialization_pass_id=PASS_ID,
    )

    updated_store, result = apply_union_supergraph_merge_plan(
        union_store=store,
        plan=plan,
        applied_at=STAMP,
    )

    assert result.survivor_nodes_created == 1
    assert "party:captain_lysandra_ironveil" in updated_store.nodes
    assert "character_lysandra" not in updated_store.nodes
    survivor = updated_store.nodes["party:captain_lysandra_ironveil"]
    assert survivor.node_id == "party:captain_lysandra_ironveil"
    assert "evidence:worldbuilding:lysandra:note" in survivor.evidence_ref_ids


def test_idempotent_reapply_skips_already_applied_assertion() -> None:
    store, plan = _lysandra_store_and_plan()

    first_store, first_result = apply_union_supergraph_merge_plan(
        union_store=store,
        plan=plan,
        applied_at=STAMP,
    )
    second_store, second_result = apply_union_supergraph_merge_plan(
        union_store=first_store,
        plan=plan,
        applied_at=STAMP,
    )

    assert first_result.merge_records_added == 1
    assert second_result.merge_records_added == 0
    assert len(second_store.identity_merge_records) == 1
    assert len(active_identity_redirect_map(second_store.identity_redirects)) == 1
    active_edges = [
        edge
        for edge in second_store.edges.values()
        if edge.state.get("memory_state") != "rewired_from_merged_away"
    ]
    assert (
        sum(
            1
            for edge in active_edges
            if edge.source_node_id == "party:captain_lysandra_ironveil"
            and edge.target_node_id == "location_mireward"
        )
        == 1
    )
    assert "merge_assertion_already_applied" in _diagnostic_codes(second_result)


def test_redirect_conflict_blocks_apply_for_assertion() -> None:
    store, plan = _lysandra_store_and_plan()
    store = store.model_copy(
        update={
            "identity_redirects": [
                _redirect(
                    redirect_id="redirect:conflict",
                    from_node_id="node:lysandra",
                    to_node_id="character:other_person",
                )
            ]
        },
        deep=True,
    )

    updated_store, result = apply_union_supergraph_merge_plan(
        union_store=store,
        plan=plan,
        applied_at=STAMP,
    )

    assert result.merge_records_added == 0
    assert "party:captain_lysandra_ironveil" not in updated_store.nodes
    assert len(updated_store.identity_merge_records) == 0
    assert "merge_apply_redirect_conflict" in _diagnostic_codes(result)


def test_mixed_redirect_conflict_skips_assertion_without_partial_mutation() -> None:
    survivor_id = "party:captain_lysandra_ironveil"
    store = minimal_union_store(
        nodes={
            "node:lysandra": union_node(),
            "character_lysandra": union_node(
                node_id="character_lysandra",
                label="Captain Lysandra Ironveil",
                aliases=["Lysandra"],
                evidence_ref_ids=["evidence:worldbuilding:lysandra:note"],
            ),
        },
        edges={
            "edge:node:lysandra:travels_to:location_mireward": union_edge(),
        },
        identity_redirects=[
            _redirect(
                redirect_id="redirect:conflict",
                from_node_id="character_lysandra",
                to_node_id="character:other_person",
            )
        ],
    )
    original_snapshot = store.model_dump()

    redirects = (
        UnionIdentityRedirect(
            redirect_id=make_identity_redirect_id("assert-mixed-conflict", "node:lysandra"),
            campaign_id=CAMPAIGN_ID,
            from_node_id="node:lysandra",
            to_node_id=survivor_id,
            assertion_id="assert-mixed-conflict",
            created_at=STAMP,
            status="active",
            materialization_pass_id=PASS_ID,
        ),
        UnionIdentityRedirect(
            redirect_id=make_identity_redirect_id(
                "assert-mixed-conflict",
                "character_lysandra",
            ),
            campaign_id=CAMPAIGN_ID,
            from_node_id="character_lysandra",
            to_node_id=survivor_id,
            assertion_id="assert-mixed-conflict",
            created_at=STAMP,
            status="active",
            materialization_pass_id=PASS_ID,
        ),
    )
    plan = UnionSupergraphMergePlan(
        campaign_id=CAMPAIGN_ID,
        materialization_pass_id=PASS_ID,
        plans=(
            MergeAssertionPlan(
                assertion_id="assert-mixed-conflict",
                survivor_node_id=survivor_id,
                merged_away_original_refs=("node:lysandra", "character_lysandra"),
                merged_away_node_ids=("node:lysandra", "character_lysandra"),
                redirects=redirects,
                aliases_to_union=("Lysandra", "Captain Lysandra Ironveil"),
                evidence_ref_ids_to_union=(
                    "evidence:session-23:lysandra:recap-mention",
                    "evidence:worldbuilding:lysandra:note",
                ),
                edges_to_rewire=(),
                survivor_hydration=SurvivorHydrationPlan(
                    survivor_node_id=survivor_id,
                    create_survivor_if_missing=True,
                    source_node_ids=("node:lysandra", "character_lysandra"),
                    aliases_to_add=("Lysandra", "Captain Lysandra Ironveil"),
                    evidence_ref_ids_to_add=(
                        "evidence:session-23:lysandra:recap-mention",
                        "evidence:worldbuilding:lysandra:note",
                    ),
                    source_domains_to_add=("recap",),
                ),
            ),
        ),
        diagnostics=(),
    )

    updated_store, result = apply_union_supergraph_merge_plan(
        union_store=store,
        plan=plan,
        applied_at=STAMP,
    )

    assert result.merge_records_added == 0
    assert result.redirects_added == 0
    assert result.survivor_nodes_created == 0
    assert result.survivor_nodes_updated == 0
    assert result.merged_away_nodes_marked == 0
    assert result.edges_rewired == 0
    assert result.edges_deduped == 0
    assert "merge_apply_redirect_conflict" in _diagnostic_codes(result)
    assert survivor_id not in updated_store.nodes
    assert updated_store.nodes["node:lysandra"].state.get("memory_state") != "merged_away"
    assert updated_store.nodes["character_lysandra"].state.get("memory_state") != "merged_away"
    assert len(updated_store.identity_redirects) == 1
    assert updated_store.identity_redirects[0].to_node_id == "character:other_person"
    assert updated_store.identity_merge_records == []
    assert updated_store.model_dump() == original_snapshot


def test_survivor_update_clears_prior_merged_away_state() -> None:
    """A later merge that picks a previously merged-away node as survivor must re-project it."""
    location_id = "location_mireward_reach"
    organization_id = "organization_mireward_reach"
    store = minimal_union_store(
        nodes={
            location_id: union_node(
                node_id=location_id,
                label="Mireward Reach",
                kind="location",
                role="location",
                aliases=["Mireward Reach"],
                evidence_ref_ids=["evidence:session-23:mireward:recap"],
            ),
            organization_id: union_node(
                node_id=organization_id,
                label="Mireward Reach",
                kind="organization",
                role="organization",
                aliases=["Mireward Reach org"],
                evidence_ref_ids=[],
            ),
        },
        edges={},
    )

    org_first_overlay = overlay_with_assertions(
        merge_assertion(
            assertion_id="assert-org-first",
            survivor_object_ref=object_ref(
                node_id=organization_id,
                label="Mireward Reach",
                kind="organization",
            ).model_dump(),
            merged_object_refs=[
                object_ref(
                    node_id=location_id,
                    label="Mireward Reach",
                    kind="location",
                ).model_dump(),
            ],
        )
    )
    org_first_plan = plan_authored_merge_reconciliation(
        campaign_id=CAMPAIGN_ID,
        overlay=org_first_overlay,
        union_store=store,
        materialization_pass_id=PASS_ID,
    )
    store, _ = apply_union_supergraph_merge_plan(
        union_store=store,
        plan=org_first_plan,
        applied_at=STAMP,
    )
    assert store.nodes[location_id].state["memory_state"] == "merged_away"

    location_survivor_overlay = overlay_with_assertions(
        merge_assertion(
            assertion_id="assert-location-survivor",
            survivor_object_ref=object_ref(
                node_id=location_id,
                label="Mireward Reach",
                kind="location",
            ).model_dump(),
            merged_object_refs=[
                object_ref(
                    node_id=organization_id,
                    label="Mireward Reach",
                    kind="organization",
                ).model_dump(),
            ],
        )
    )
    location_plan = plan_authored_merge_reconciliation(
        campaign_id=CAMPAIGN_ID,
        overlay=location_survivor_overlay,
        union_store=store,
        materialization_pass_id=f"{PASS_ID}:location-survivor",
    )
    store, result = apply_union_supergraph_merge_plan(
        union_store=store,
        plan=location_plan,
        applied_at=STAMP,
    )

    assert result.survivor_nodes_updated == 1
    assert store.nodes[location_id].state["memory_state"] == "graph_read_model"
    assert "merged_into" not in store.nodes[location_id].state
    assert store.nodes[organization_id].state["memory_state"] == "merged_away"


def test_dedupes_equivalent_survivor_edge() -> None:
    store = minimal_union_store(
        nodes={
            "node:lysandra": union_node(),
            "party:captain_lysandra_ironveil": union_node(
                node_id="party:captain_lysandra_ironveil",
                label="Captain Lysandra Ironveil",
                aliases=["Captain Lysandra Ironveil"],
                evidence_ref_ids=["evidence:session-23:party:recap-mention"],
            ),
            "location_mireward": union_node(
                node_id="location_mireward",
                label="Mireward",
                kind="location",
                role="location",
                aliases=["Mireward"],
                evidence_ref_ids=[],
            ),
        },
        edges={
            "edge:node:lysandra:travels_to:location_mireward": union_edge(),
            "edge:party:captain_lysandra_ironveil:travels_to:location_mireward": union_edge(
                edge_id="edge:party:captain_lysandra_ironveil:travels_to:location_mireward",
                source_node_id="party:captain_lysandra_ironveil",
                evidence_ref_ids=["evidence:session-23:party:recap-mention"],
            ),
        },
    )
    overlay = overlay_with_assertions(merge_assertion())
    plan = plan_authored_merge_reconciliation(
        campaign_id=CAMPAIGN_ID,
        overlay=overlay,
        union_store=store,
        materialization_pass_id=PASS_ID,
    )

    updated_store, result = apply_union_supergraph_merge_plan(
        union_store=store,
        plan=plan,
        applied_at=STAMP,
    )

    assert result.edges_deduped == 1
    assert result.edges_rewired == 0
    survivor_edge = updated_store.edges[
        "edge:party:captain_lysandra_ironveil:travels_to:location_mireward"
    ]
    assert "evidence:session-23:lysandra:recap-mention" in survivor_edge.evidence_ref_ids
    assert "rewired_from_edge_ids" in survivor_edge.state


def test_file_wrapper_creates_backup_and_writes_store(tmp_path) -> None:
    store, plan = _lysandra_store_and_plan()
    store_path = tmp_path / "preview_union_store.json"
    backup_dir = tmp_path / "backups"
    from graph_memory.union_supergraph.load import write_union_supergraph_store

    write_union_supergraph_store(store_path, store)

    result = apply_union_supergraph_merge_plan_to_file(
        union_store_path=store_path,
        plan=plan,
        applied_at=STAMP,
        backup_dir=backup_dir,
    )

    assert result.backup_path is not None
    assert Path(result.backup_path).exists()
    reloaded = load_union_supergraph_store(store_path)
    assert len(reloaded.identity_redirects) == 1
    assert len(reloaded.identity_merge_records) == 1
    assert "merge_apply_backup_created" in _diagnostic_codes(result)
    assert "merge_apply_store_written" in _diagnostic_codes(result)


def test_existing_stores_without_merge_records_still_load() -> None:
    fixture = load_union_supergraph_payload(DEFAULT_FIXTURE_PATH)
    assert "identity_merge_records" not in fixture

    store = parse_union_supergraph_store(fixture)
    assert store.identity_merge_records == []
