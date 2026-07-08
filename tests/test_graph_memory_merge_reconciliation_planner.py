from __future__ import annotations

from apps.live_control_server.models.graph_authoring_overlay import (
    AuthoredGraphMergeObjectsAssertion,
    AuthoredGraphOverlay,
    AuthoredGraphObjectRef,
    default_graph_authoring_provenance,
)
from graph_memory.union_supergraph.merge_reconciliation import (
    plan_authored_merge_reconciliation,
)
from graph_memory.union_supergraph.model import (
    UnionIdentityRedirect,
    UnionSupergraphEdge,
    UnionSupergraphNode,
    UnionSupergraphStore,
)

STAMP = "2026-07-08T00:00:00Z"
CAMPAIGN_ID = "longmont-c2"
PASS_ID = "pass:2026-07-08-test"


def provenance(**overrides):
    kwargs = {"created_at": STAMP}
    kwargs.update(overrides)
    return default_graph_authoring_provenance(**kwargs)


def object_ref(**overrides) -> AuthoredGraphObjectRef:
    data = {
        "ref_kind": "existing_graph_node",
        "node_id": "node:example",
        "label": "Example",
        "kind": "character",
    }
    data.update(overrides)
    return AuthoredGraphObjectRef.model_validate(data)


def merge_assertion(**overrides) -> AuthoredGraphMergeObjectsAssertion:
    data = {
        "assertion_id": "assert-merge-lysandra",
        "assertion_kind": "merge_objects",
        "operation": "merge",
        "campaign_id": CAMPAIGN_ID,
        "session_id": "session-23",
        "provenance": provenance().model_dump(),
        "survivor_object_ref": object_ref(
            node_id="party:captain_lysandra_ironveil",
            label="Captain Lysandra Ironveil",
        ).model_dump(),
        "merged_object_refs": [
            object_ref(node_id="node:lysandra", label="Lysandra").model_dump(),
        ],
        "merge_reason": "Search result identity merge",
    }
    data.update(overrides)
    return AuthoredGraphMergeObjectsAssertion.model_validate(data)


def union_node(**overrides) -> UnionSupergraphNode:
    data = {
        "node_id": "node:lysandra",
        "label": "Lysandra",
        "kind": "character",
        "role": "character",
        "aliases": ["Lysandra"],
        "source_domains": ["recap"],
        "evidence_ref_ids": ["evidence:session-23:lysandra:recap-mention"],
        "state": {"memory_state": "graph_read_model"},
    }
    data.update(overrides)
    return UnionSupergraphNode.model_validate(data)


def union_edge(**overrides) -> UnionSupergraphEdge:
    data = {
        "edge_id": "edge:node:lysandra:travels_to:location_mireward",
        "source_node_id": "node:lysandra",
        "target_node_id": "location_mireward",
        "predicate": "travels_to",
        "label": "travels to",
        "direction": "outbound",
        "source_domains": ["recap"],
        "session_ids": ["session-23"],
        "evidence_ref_ids": ["evidence:session-23:lysandra:recap-mention"],
        "state": {"memory_state": "graph_read_model"},
    }
    data.update(overrides)
    return UnionSupergraphEdge.model_validate(data)


def minimal_union_store(**overrides) -> UnionSupergraphStore:
    payload = {
        "schema": "dmb_union_supergraph_store_v0",
        "version": "0.1",
        "campaign_id": CAMPAIGN_ID,
        "focus_session_id": "session-23",
        "nodes": {},
        "edges": {},
        "evidence": {},
        "source_artifacts": {},
        "adjacency": {},
        "diagnostics": {},
        "identity_redirects": [],
    }
    payload.update(overrides)
    return UnionSupergraphStore.model_validate(payload)


def overlay_with_assertions(*assertions) -> AuthoredGraphOverlay:
    return AuthoredGraphOverlay.model_validate(
        {
            "campaign_id": CAMPAIGN_ID,
            "overlay_id": f"overlay-{CAMPAIGN_ID}",
            "created_at": STAMP,
            "updated_at": STAMP,
            "assertions": [assertion.model_dump() for assertion in assertions],
        }
    )


def _redirect(
    *,
    redirect_id: str,
    from_node_id: str,
    to_node_id: str,
) -> UnionIdentityRedirect:
    return UnionIdentityRedirect(
        redirect_id=redirect_id,
        campaign_id=CAMPAIGN_ID,
        from_node_id=from_node_id,
        to_node_id=to_node_id,
        assertion_id="assertion:existing",
        created_at=STAMP,
        status="active",
        materialization_pass_id="pass:existing",
    )


def _diagnostic_codes(plan) -> set[str]:
    return {item.code for item in plan.diagnostics}


def test_plans_lysandra_redirect() -> None:
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

    assert len(plan.plans) == 1
    assertion_plan = plan.plans[0]
    assert assertion_plan.survivor_node_id == "party:captain_lysandra_ironveil"
    assert assertion_plan.merged_away_original_refs == ("node:lysandra",)
    assert assertion_plan.merged_away_node_ids == ("node:lysandra",)
    assert len(assertion_plan.redirects) == 1
    assert assertion_plan.redirects[0].from_node_id == "node:lysandra"
    assert assertion_plan.redirects[0].to_node_id == "party:captain_lysandra_ironveil"
    assert "Lysandra" in assertion_plan.aliases_to_union
    assert "evidence:session-23:lysandra:recap-mention" in assertion_plan.evidence_ref_ids_to_union
    assert len(assertion_plan.edges_to_rewire) == 1
    rewire = assertion_plan.edges_to_rewire[0]
    assert rewire.original_source_node_id == "node:lysandra"
    assert rewire.planned_source_node_id == "party:captain_lysandra_ironveil"
    assert "merge_plan_created" in _diagnostic_codes(plan)


def test_gm_survivor_id_is_exact() -> None:
    store = minimal_union_store(
        nodes={
            "character_lysandra": union_node(
                node_id="character_lysandra",
                label="Captain Lysandra Ironveil",
                aliases=["Lysandra", "Captain Lysandra"],
                evidence_ref_ids=[
                    "evidence:session-23:lysandra:recap-mention",
                    "evidence:worldbuilding:lysandra:note",
                ],
            ),
            "node:lysandra": union_node(
                evidence_ref_ids=["evidence:session-23:lysandra:recap-mention"],
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

    assertion_plan = plan.plans[0]
    assert assertion_plan.survivor_node_id == "party:captain_lysandra_ironveil"
    assert assertion_plan.survivor_node_id != "character_lysandra"


def test_existing_same_target_redirect_is_idempotent() -> None:
    store = minimal_union_store(
        nodes={"node:lysandra": union_node()},
        identity_redirects=[
            _redirect(
                redirect_id="redirect:existing",
                from_node_id="node:lysandra",
                to_node_id="party:captain_lysandra_ironveil",
            )
        ],
    )
    overlay = overlay_with_assertions(merge_assertion())

    plan = plan_authored_merge_reconciliation(
        campaign_id=CAMPAIGN_ID,
        overlay=overlay,
        union_store=store,
        materialization_pass_id=PASS_ID,
    )

    assertion_plan = plan.plans[0]
    assert assertion_plan.redirects == ()
    assert "merge_redirect_already_materialized" in _diagnostic_codes(plan)


def test_conflicting_active_redirect_skips_assertion() -> None:
    store = minimal_union_store(
        nodes={"node:lysandra": union_node()},
        identity_redirects=[
            _redirect(
                redirect_id="redirect:conflict",
                from_node_id="node:lysandra",
                to_node_id="character:other_person",
            )
        ],
    )
    overlay = overlay_with_assertions(merge_assertion())

    plan = plan_authored_merge_reconciliation(
        campaign_id=CAMPAIGN_ID,
        overlay=overlay,
        union_store=store,
        materialization_pass_id=PASS_ID,
    )

    assert plan.plans == ()
    assert "merge_redirect_conflict" in _diagnostic_codes(plan)


def test_self_merge_skipped() -> None:
    store = minimal_union_store(
        nodes={
            "party:captain_lysandra_ironveil": union_node(
                node_id="party:captain_lysandra_ironveil",
                label="Captain Lysandra Ironveil",
                aliases=["Lysandra"],
                evidence_ref_ids=[],
            ),
        }
    )
    overlay = overlay_with_assertions(
        merge_assertion(
            merged_object_refs=[
                object_ref(
                    node_id="node:missing",
                    label="Captain Lysandra Ironveil",
                ).model_dump(),
            ],
        )
    )

    plan = plan_authored_merge_reconciliation(
        campaign_id=CAMPAIGN_ID,
        overlay=overlay,
        union_store=store,
        materialization_pass_id=PASS_ID,
    )

    assert plan.plans == ()
    assert "merge_assertion_self_merge" in _diagnostic_codes(plan)


def test_missing_merged_node_still_plans_redirect_with_warning() -> None:
    overlay = overlay_with_assertions(merge_assertion())

    plan = plan_authored_merge_reconciliation(
        campaign_id=CAMPAIGN_ID,
        overlay=overlay,
        union_store=minimal_union_store(),
        materialization_pass_id=PASS_ID,
    )

    assertion_plan = plan.plans[0]
    assert len(assertion_plan.redirects) == 1
    assert assertion_plan.redirects[0].from_node_id == "node:lysandra"
    assert assertion_plan.evidence_ref_ids_to_union == ()
    assert assertion_plan.edges_to_rewire == ()
    assert "merge_merged_node_missing" in _diagnostic_codes(plan)


def test_missing_survivor_produces_hydration_create_flag() -> None:
    store = minimal_union_store(nodes={"node:lysandra": union_node()})
    overlay = overlay_with_assertions(merge_assertion())

    plan = plan_authored_merge_reconciliation(
        campaign_id=CAMPAIGN_ID,
        overlay=overlay,
        union_store=store,
        materialization_pass_id=PASS_ID,
    )

    assertion_plan = plan.plans[0]
    assert assertion_plan.survivor_hydration is not None
    assert assertion_plan.survivor_hydration.create_survivor_if_missing is True
    assert "merge_survivor_node_missing" in _diagnostic_codes(plan)


def test_wrong_campaign_skipped() -> None:
    overlay = overlay_with_assertions(
        merge_assertion(campaign_id="other-campaign"),
    )

    plan = plan_authored_merge_reconciliation(
        campaign_id=CAMPAIGN_ID,
        overlay=overlay,
        union_store=minimal_union_store(),
        materialization_pass_id=PASS_ID,
    )

    assert plan.plans == ()
    assert "merge_assertion_wrong_campaign" in _diagnostic_codes(plan)
