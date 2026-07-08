"""Tests for durable union identity redirect projection behavior."""

from __future__ import annotations

from graph_memory.projection.recap_projection import build_recap_graph_projection
from graph_memory.union_supergraph.merge_reconciliation import plan_authored_merge_reconciliation
from graph_memory.union_supergraph.merge_reconciliation_apply import (
    apply_union_supergraph_merge_plan,
)
from graph_memory.union_supergraph.projection_identity import (
    build_union_projection_identity_context,
    is_projectable_union_edge,
    is_projectable_union_node,
    resolve_projected_node_id,
    resolve_projection_markdown_dmb_node_links,
)
from graph_memory.union_supergraph.redirects import active_identity_redirect_map
from tests.test_graph_memory_merge_reconciliation_planner import (
    CAMPAIGN_ID,
    PASS_ID,
    STAMP,
    merge_assertion,
    minimal_union_store,
    overlay_with_assertions,
    union_edge,
    union_node,
    _redirect,
)


def _lysandra_evidence() -> dict[str, dict[str, object]]:
    return {
        "evidence:session-23:lysandra:recap-mention": {
            "evidence_ref_id": "evidence:session-23:lysandra:recap-mention",
            "source_artifact_id": "artifact:session-23-recap",
            "source_domain": "recap",
            "evidence_role": "mention",
            "session_id": "session-23",
            "can_open_source": True,
            "can_highlight_span": True,
        }
    }


def _lysandra_applied_store():
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
        evidence=_lysandra_evidence(),
    )
    overlay = overlay_with_assertions(merge_assertion())
    plan = plan_authored_merge_reconciliation(
        campaign_id=CAMPAIGN_ID,
        overlay=overlay,
        union_store=store,
        materialization_pass_id=PASS_ID,
    )
    applied_store, _result = apply_union_supergraph_merge_plan(
        union_store=store,
        plan=plan,
        applied_at=STAMP,
    )
    return applied_store


def test_resolve_projected_node_id_follows_active_redirect() -> None:
    context = build_union_projection_identity_context(
        minimal_union_store(
            identity_redirects=[
                _redirect(
                    redirect_id="redirect:lysandra",
                    from_node_id="node:lysandra",
                    to_node_id="party:captain_lysandra_ironveil",
                )
            ]
        )
    )
    assert (
        resolve_projected_node_id("node:lysandra", context)
        == "party:captain_lysandra_ironveil"
    )


def test_merged_away_nodes_filtered_from_projection() -> None:
    store = _lysandra_applied_store()
    projection = build_recap_graph_projection(
        store,
        session_id="session-23",
        markdown="[Lysandra](dmb-node:node:lysandra) traveled.",
    )

    assert "node:lysandra" not in projection.node_views
    assert "party:captain_lysandra_ironveil" in projection.node_views
    assert any(
        item.code == "union_identity_merged_away_node_filtered"
        for item in projection.union_identity_diagnostics
    )


def test_rewired_from_edges_filtered_from_projection() -> None:
    store = _lysandra_applied_store()
    projection = build_recap_graph_projection(store, session_id="session-23")

    survivor = projection.node_views["party:captain_lysandra_ironveil"]
    assert len(survivor.adjacency) == 1
    assert survivor.adjacency[0].node_id == "location_mireward"
    assert survivor.adjacency[0].predicate == "travels_to"
    assert any(
        item.code == "union_identity_rewired_edge_filtered"
        for item in projection.union_identity_diagnostics
    )


def test_edge_endpoints_resolve_through_redirects_before_materialization() -> None:
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
        identity_redirects=[
            _redirect(
                redirect_id="redirect:lysandra",
                from_node_id="node:lysandra",
                to_node_id="party:captain_lysandra_ironveil",
            )
        ],
    )
    store = store.model_copy(
        update={
            "nodes": {
                **store.nodes,
                "party:captain_lysandra_ironveil": union_node(
                    node_id="party:captain_lysandra_ironveil",
                    label="Captain Lysandra Ironveil",
                    kind="companion",
                    role="companion",
                    aliases=["Lysandra"],
                    evidence_ref_ids=[],
                ),
            }
        },
        deep=True,
    )
    projection = build_recap_graph_projection(store, session_id="session-23")
    survivor = projection.node_views["party:captain_lysandra_ironveil"]
    assert len(survivor.adjacency) == 1
    assert survivor.adjacency[0].node_id == "location_mireward"
    assert any(
        item.code == "union_identity_edge_endpoint_resolved"
        for item in projection.union_identity_diagnostics
    )


def test_dmb_node_mention_target_resolves_to_survivor() -> None:
    store = _lysandra_applied_store()
    projection = build_recap_graph_projection(
        store,
        session_id="session-23",
        markdown="[Lysandra](dmb-node:node:lysandra) traveled.",
    )

    assert "dmb-node:party:captain_lysandra_ironveil" in (projection.markdown or "")
    assert "dmb-node:node:lysandra" not in (projection.markdown or "")
    assert any(
        item.code == "union_identity_mention_target_resolved"
        for item in projection.union_identity_diagnostics
    )


def test_survivor_node_carries_merge_provenance() -> None:
    store = _lysandra_applied_store()
    projection = build_recap_graph_projection(store, session_id="session-23")
    survivor = projection.node_views["party:captain_lysandra_ironveil"]

    assert "node:lysandra" in getattr(survivor, "merged_away_ids", [])
    assert getattr(survivor, "merge_assertion_ids", [])
    assert getattr(survivor, "identity_merge_record_ids", [])
    assert "assert-merge-lysandra" in projection.union_identity_applied_assertion_ids


def test_is_projectable_union_node_and_edge_helpers() -> None:
    store = _lysandra_applied_store()
    context = build_union_projection_identity_context(store)

    assert not is_projectable_union_node(store.nodes["node:lysandra"], context)
    assert is_projectable_union_node(
        store.nodes["party:captain_lysandra_ironveil"],
        context,
    )

    rewired_edge = next(
        edge
        for edge in store.edges.values()
        if edge.state.get("memory_state") == "rewired_from_merged_away"
    )
    active_edge = next(
        edge
        for edge in store.edges.values()
        if edge.source_node_id == "party:captain_lysandra_ironveil"
    )
    assert not is_projectable_union_edge(rewired_edge, context)
    assert is_projectable_union_edge(active_edge, context)


def test_resolve_projection_markdown_dmb_node_links() -> None:
    context = build_union_projection_identity_context(
        minimal_union_store(
            identity_redirects=[
                _redirect(
                    redirect_id="redirect:lysandra",
                    from_node_id="node:lysandra",
                    to_node_id="party:captain_lysandra_ironveil",
                )
            ]
        )
    )
    markdown = "[Lysandra](dmb-node:node:lysandra) traveled."
    updated, count = resolve_projection_markdown_dmb_node_links(markdown, context)
    assert count == 1
    assert updated == "[Lysandra](dmb-node:party:captain_lysandra_ironveil) traveled."


def test_active_redirect_map_matches_store() -> None:
    store = _lysandra_applied_store()
    redirect_map = active_identity_redirect_map(store.identity_redirects)
    assert redirect_map["node:lysandra"].to_node_id == "party:captain_lysandra_ironveil"
