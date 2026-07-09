from __future__ import annotations

from apps.live_control_server.models.graph_authoring_overlay import (
    AuthoredGraphMergeObjectsAssertion,
    AuthoredGraphObjectRef,
    default_graph_authoring_provenance,
)
from apps.live_control_server.services.graph_object_authoring_merge_guard import (
    detect_merge_assertion_conflicts,
    find_superseded_merge_assertion_ids,
    find_superseded_merge_assertion_pairs,
    merge_assertions_conflict,
)
from tests.test_graph_memory_merge_reconciliation_planner import (
    CAMPAIGN_ID,
    merge_assertion,
    overlay_with_assertions,
)


def _ref(node_id: str, *, kind: str = "location") -> AuthoredGraphObjectRef:
    return AuthoredGraphObjectRef.model_validate(
        {
            "ref_kind": "existing_graph_node",
            "node_id": node_id,
            "label": node_id,
            "kind": kind,
        }
    )


def test_merge_assertions_conflict_when_cluster_overlaps_with_different_survivors() -> None:
    left = merge_assertion(
        assertion_id="assert-left",
        survivor_object_ref=_ref("organization_mireward_reach", kind="organization").model_dump(),
        merged_object_refs=[_ref("location_mireward_reach").model_dump()],
    )
    right = merge_assertion(
        assertion_id="assert-right",
        survivor_object_ref=_ref("location_mireward_reach").model_dump(),
        merged_object_refs=[_ref("organization_mireward_reach", kind="organization").model_dump()],
    )
    assert merge_assertions_conflict(left, right)


def test_merge_assertions_do_not_conflict_when_survivors_match() -> None:
    left = merge_assertion(
        assertion_id="assert-left",
        survivor_object_ref=_ref("location_mireward_reach").model_dump(),
        merged_object_refs=[_ref("organization_mireward_reach", kind="organization").model_dump()],
    )
    right = merge_assertion(
        assertion_id="assert-right",
        survivor_object_ref=_ref("location_mireward_reach").model_dump(),
        merged_object_refs=[_ref("node:mireward-reach").model_dump()],
    )
    assert not merge_assertions_conflict(left, right)


def test_merge_assertions_do_not_conflict_when_proposed_supersedes_existing_survivor() -> None:
    existing = merge_assertion(
        assertion_id="assert-existing",
        survivor_object_ref=_ref("character_captain_lysandra_ironveil", kind="character").model_dump(),
        merged_object_refs=[_ref("node:lysandra").model_dump()],
    )
    proposed = merge_assertion(
        assertion_id="assert-proposed",
        survivor_object_ref=_ref("party:captain_lysandra_ironveil", kind="companion").model_dump(),
        merged_object_refs=[
            _ref("node:lysandra").model_dump(),
            _ref("character_captain_lysandra_ironveil", kind="character").model_dump(),
        ],
    )
    assert not merge_assertions_conflict(proposed, existing)
    assert find_superseded_merge_assertion_ids(
        [proposed],
        existing_assertions=[existing],
    ) == {"assert-existing"}
    assert find_superseded_merge_assertion_pairs(
        [proposed],
        existing_assertions=[existing],
    ) == [("assert-existing", "assert-proposed")]


def test_detect_merge_assertion_conflicts_blocks_against_existing_overlay() -> None:
    existing = merge_assertion(
        assertion_id="assert-existing",
        survivor_object_ref=_ref("location_mireward_reach").model_dump(),
        merged_object_refs=[_ref("organization_mireward_reach", kind="organization").model_dump()],
    )
    proposed = merge_assertion(
        assertion_id="assert-proposed",
        survivor_object_ref=_ref("organization_mireward_reach", kind="organization").model_dump(),
        merged_object_refs=[_ref("location_mireward_reach").model_dump()],
    )
    overlay = overlay_with_assertions(existing)
    diagnostics = detect_merge_assertion_conflicts(
        [proposed],
        existing_assertions=overlay.assertions,
    )
    assert diagnostics
    assert diagnostics[0].code == "merge_assertion_conflicts_with_existing"
    assert diagnostics[0].severity == "error"
