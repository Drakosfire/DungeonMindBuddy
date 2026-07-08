"""A10m PR E — Session 23 Lysandra durable identity dogfood validation.

Exercises authored merge → reconciliation plan → apply → projection reload
and durable-overlay skip behavior for the GM-chosen Lysandra survivor path.
"""

from __future__ import annotations

from apps.live_control_server.models.graph_authoring_overlay import (
    AuthoredGraphMergeObjectsAssertion,
    create_empty_authored_graph_overlay,
)
from apps.live_control_server.services.graph_authoring_overlay_projection import (
    apply_authored_overlay_to_graph_review_projection,
)
from graph_memory.projection.recap_projection import build_recap_graph_projection
from graph_memory.union_supergraph.merge_reconciliation import (
    plan_authored_merge_reconciliation,
)
from graph_memory.union_supergraph.merge_reconciliation_apply import (
    apply_union_supergraph_merge_plan,
)
from graph_memory.union_supergraph.redirects import (
    active_identity_redirect_map,
    resolve_union_node_id,
)
from tests.test_graph_authoring_overlay_models import provenance as overlay_provenance
from tests.test_graph_authoring_overlay_models import object_ref as overlay_object_ref
from tests.test_graph_memory_merge_reconciliation_planner import (
    CAMPAIGN_ID,
    PASS_ID,
    STAMP,
    merge_assertion,
    minimal_union_store,
    overlay_with_assertions,
    union_edge,
    union_node,
)

SURVIVOR_NODE_ID = "party:captain_lysandra_ironveil"
MERGED_AWAY_NODE_ID = "node:lysandra"
ASSERTION_ID = "assert-merge-lysandra"
SESSION_ID = "session-23"
RECAP_MARKDOWN = "[Lysandra](dmb-node:node:lysandra) commanded at Mireward."


def _lysandra_evidence() -> dict[str, dict[str, object]]:
    return {
        "evidence:session-23:lysandra:recap-mention": {
            "evidence_ref_id": "evidence:session-23:lysandra:recap-mention",
            "source_artifact_id": "artifact:session-23-recap",
            "source_domain": "recap",
            "evidence_role": "mention",
            "session_id": SESSION_ID,
            "can_open_source": True,
            "can_highlight_span": True,
        },
        "evidence:session-23:lysandra:mireward-command": {
            "evidence_ref_id": "evidence:session-23:lysandra:mireward-command",
            "source_artifact_id": "artifact:session-23-recap",
            "source_domain": "recap",
            "evidence_role": "command",
            "session_id": SESSION_ID,
            "can_open_source": True,
            "can_highlight_span": True,
        },
    }


def _lysandra_pre_reconciliation_store():
    """Duplicate Lysandra identities before durable reconciliation."""
    return minimal_union_store(
        nodes={
            MERGED_AWAY_NODE_ID: union_node(
                evidence_ref_ids=[
                    "evidence:session-23:lysandra:recap-mention",
                    "evidence:session-23:lysandra:mireward-command",
                ],
            ),
            SURVIVOR_NODE_ID: union_node(
                node_id=SURVIVOR_NODE_ID,
                label="Captain Lysandra Ironveil",
                kind="companion",
                role="companion",
                aliases=["Captain Lysandra Ironveil"],
                evidence_ref_ids=[],
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
        },
        evidence=_lysandra_evidence(),
    )


def _lysandra_overlay():
    return overlay_with_assertions(merge_assertion())


def _run_lysandra_durable_identity_pipeline(*, markdown: str | None = RECAP_MARKDOWN):
    store = _lysandra_pre_reconciliation_store()
    overlay = _lysandra_overlay()
    plan = plan_authored_merge_reconciliation(
        campaign_id=CAMPAIGN_ID,
        overlay=overlay,
        union_store=store,
        materialization_pass_id=PASS_ID,
    )
    applied_store, apply_result = apply_union_supergraph_merge_plan(
        union_store=store,
        plan=plan,
        applied_at=STAMP,
    )
    projection = build_recap_graph_projection(
        applied_store,
        session_id=SESSION_ID,
        markdown=markdown,
    )
    return store, plan, applied_store, apply_result, projection


def test_a10m_lysandra_merge_plan_apply_project_end_to_end() -> None:
    store, plan, applied_store, apply_result, projection = (
        _run_lysandra_durable_identity_pipeline()
    )

    assertion_plan = plan.plans[0]
    assert assertion_plan.survivor_node_id == SURVIVOR_NODE_ID
    assert assertion_plan.survivor_node_id != "character_lysandra"
    assert apply_result.merge_records_added == 1
    assert apply_result.redirects_added == 1

    redirect_map = active_identity_redirect_map(applied_store.identity_redirects)
    assert (
        resolve_union_node_id(MERGED_AWAY_NODE_ID, redirect_map)
        == SURVIVOR_NODE_ID
    )
    assert redirect_map[MERGED_AWAY_NODE_ID].to_node_id == SURVIVOR_NODE_ID

    assert SURVIVOR_NODE_ID in projection.node_views
    survivor = projection.node_views[SURVIVOR_NODE_ID]
    assert survivor.node_id == SURVIVOR_NODE_ID
    assert MERGED_AWAY_NODE_ID not in projection.node_views
    assert "character_lysandra" not in projection.node_views

    assert projection.markdown is not None
    assert f"dmb-node:{SURVIVOR_NODE_ID}" in projection.markdown
    assert f"dmb-node:{MERGED_AWAY_NODE_ID}" not in projection.markdown

    assert "Lysandra" in survivor.aliases
    assert len(survivor.evidence_badges) > 0
    assert len(survivor.adjacency) > 0
    assert survivor.adjacency[0].node_id == "location_mireward"
    assert MERGED_AWAY_NODE_ID in getattr(survivor, "merged_away_ids", [])
    assert ASSERTION_ID in getattr(survivor, "merge_assertion_ids", [])
    assert ASSERTION_ID in projection.union_identity_applied_assertion_ids

    merged_away = applied_store.nodes[MERGED_AWAY_NODE_ID]
    assert merged_away.state.get("memory_state") == "merged_away"
    assert merged_away.state.get("merged_into") == SURVIVOR_NODE_ID
    assert MERGED_AWAY_NODE_ID in store.nodes


def test_a10m_lysandra_durable_projection_prevents_duplicate_overlay_merge() -> None:
    _store, _plan, applied_store, _apply_result, projection = (
        _run_lysandra_durable_identity_pipeline()
    )
    overlay = create_empty_authored_graph_overlay(CAMPAIGN_ID, created_at=STAMP).model_copy(
        update={
            "assertions": [
                AuthoredGraphMergeObjectsAssertion.model_validate(
                    {
                        "assertion_id": ASSERTION_ID,
                        "assertion_kind": "merge_objects",
                        "operation": "merge",
                        "campaign_id": CAMPAIGN_ID,
                        "session_id": SESSION_ID,
                        "provenance": overlay_provenance().model_dump(),
                        "survivor_object_ref": overlay_object_ref(
                            node_id=SURVIVOR_NODE_ID,
                            label="Captain Lysandra Ironveil",
                            kind="companion",
                            role="companion",
                        ).model_dump(),
                        "merged_object_refs": [
                            overlay_object_ref(
                                node_id=MERGED_AWAY_NODE_ID,
                                label="Lysandra",
                                kind="character",
                            ).model_dump()
                        ],
                    }
                )
            ]
        }
    )

    enriched, summary = apply_authored_overlay_to_graph_review_projection(
        projection,
        overlay,
    )

    assert MERGED_AWAY_NODE_ID not in enriched.node_views
    assert SURVIVOR_NODE_ID in enriched.node_views
    assert any(
        diagnostic.code == "union_identity_overlay_merge_skipped_durable"
        for diagnostic in summary.diagnostics
    )

    survivor = enriched.node_views[SURVIVOR_NODE_ID]
    durable_survivor = projection.node_views[SURVIVOR_NODE_ID]
    assert len(survivor.aliases) == len(set(durable_survivor.aliases))
    assert len(survivor.aliases) == len(set(survivor.aliases))
