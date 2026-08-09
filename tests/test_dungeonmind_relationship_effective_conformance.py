"""Effective relationship conformance over continuity-governed descendants."""

from __future__ import annotations

import inspect
import json
from pathlib import Path

import pytest

from apps.live_control_server.config import world_graph_root
from apps.live_control_server.integrations.dungeonmind_kernel.relationship_effective_conformance_v1 import (
    RELATIONSHIP_EFFECTIVE_CONFORMANCE_SCHEMA_V1,
    analyze_relationship_effective_conformance_v1,
    compact_relationship_effective_conformance_report_v1,
    resolve_carried_relationship_explicit_adapter_v1,
)
from apps.live_control_server.integrations.dungeonmind_kernel.relationship_residual_adjudication import (
    ELDYRWILD_PAYLOAD_SHA256,
    ELDYRWILD_RESIDUAL_FINDINGS,
    ELDYRWILD_REVISION_ID,
    ELDYRWILD_WORLD_ID,
)
from apps.live_control_server.integrations.dungeonmind_kernel.whole_world_conformance import (
    snapshot_world_graph_tree_digest,
)

FIXTURES = Path(__file__).resolve().parent / "fixtures" / "dungeonmind_kernel"
EFFECTIVE_FIXTURE_PATH = (
    FIXTURES / "eldyrwild_relationship_effective_conformance_v1.json"
)
ADAPTER_CONFORMANCE_FIXTURE_PATH = (
    FIXTURES / "eldyrwild_relationship_explicit_adapter_conformance_v1.json"
)
ADJUDICATION_FIXTURE_PATH = (
    FIXTURES / "eldyrwild_relationship_residual_adjudication_v1.json"
)

_EXPECTED_REMAINING_DISPOSITIONS = {
    "SOURCE_CORRECTION_REQUIRED": 35,
    "COMPOUND_ASSERTION_NOT_SINGLE_RELATIONSHIP": 10,
    "IDENTITY_NOT_RELATIONSHIP": 6,
    "INSUFFICIENT_EVIDENCE": 1,
}

_PR29_EDGE_IDS = {
    "edge:node:fey_entity:present_at:pc:ephanna:appears-to-ephanna-in-prison",
    "edge:pc:bonogo:defends_weakened_location:node:prisoners_session9:protects",
    "edge:pc:caelynn:controls_comms_with:npc_grobnok",
}

_ADAPTER_EDGE_IDS = {
    "edge:item:session17:seed:located_in:pc:stafl",
    "edge:node:cultists_of_longmont:part_of:node:lesandra:led-by",
    "edge:node:pippa:leads_to:loc:stone_bridge",
}

_WOLF_EDGE_ID = "edge:node:wolf:part_of:item:session17:centipede_meat_creature"


def test_public_effective_api_rejects_caller_supplied_authority() -> None:
    sig = inspect.signature(analyze_relationship_effective_conformance_v1)
    assert "base_report" not in sig.parameters
    assert "continuity" not in sig.parameters
    assert "catalog" not in sig.parameters
    assert "findings" not in sig.parameters
    with pytest.raises(TypeError):
        analyze_relationship_effective_conformance_v1(  # type: ignore[call-arg]
            root=Path("/tmp"),
            world_id="eldyrwild",
            revision_id=ELDYRWILD_REVISION_ID,
            catalog={},
        )

    carried_sig = inspect.signature(resolve_carried_relationship_explicit_adapter_v1)
    assert "catalog" not in carried_sig.parameters
    assert "vocabulary" not in carried_sig.parameters


def test_committed_eldyrwild_effective_fixture_is_durable_regression_contract() -> None:
    payload = json.loads(EFFECTIVE_FIXTURE_PATH.read_text(encoding="utf-8"))
    assert payload["schema_version"] == RELATIONSHIP_EFFECTIVE_CONFORMANCE_SCHEMA_V1
    assert payload["world_id"] == ELDYRWILD_WORLD_ID
    assert payload["source_revision_id"] == ELDYRWILD_REVISION_ID
    assert payload["source_graph_payload_sha256"] == ELDYRWILD_PAYLOAD_SHA256
    assert payload["relationship_semantic_count"] == 346
    assert payload["relationship_effectively_represented_count"] == 294
    assert payload["relationship_effective_residual_count"] == 52
    assert payload["uses_statblock_mechanics_count"] == 2
    assert payload["dungeonmind_owned_remaining_count"] == 0
    assert payload["dungeonmindbuddy_owned_remaining_count"] == 52
    assert payload["unadjudicated_remaining_count"] == 0
    assert payload["requires_readjudication_count"] == 0
    assert len(payload["active_adjudicated_edge_ids"]) == 59
    assert payload["active_adjudicated_edge_ids"] == sorted(ELDYRWILD_RESIDUAL_FINDINGS)
    assert payload["invalidated_adjudication_edge_ids"] == []
    assert payload["explicit_adapter_applied_count"] == 3
    # On the exact anchor, PR #29 interpretations are already represented by
    # historical v4 exact-domain overrides, so the effective layer does not
    # re-apply them as newly represented residuals.
    assert payload["pr29_interpretation_applied_count"] == 0
    assert set(payload["newly_represented_by_continuity_edge_ids"]) == _ADAPTER_EDGE_IDS

    dispositions = {
        row["key"]: row["count"]
        for row in payload["remaining_residual_disposition_inventory"]
    }
    assert dispositions == _EXPECTED_REMAINING_DISPOSITIONS

    # Cross-check remaining residual set against historical adapter conformance.
    adapter_fixture = json.loads(
        ADAPTER_CONFORMANCE_FIXTURE_PATH.read_text(encoding="utf-8")
    )
    assert (
        payload["remaining_residual_edge_ids"]
        == adapter_fixture["remaining_residual_edge_ids"]
    )

    adjudication = json.loads(ADJUDICATION_FIXTURE_PATH.read_text(encoding="utf-8"))
    dm_owned = {
        record["edge_id"]
        for record in adjudication["records"]
        if record["responsible_repo"] == "DungeonMind"
    }
    assert dm_owned == _PR29_EDGE_IDS | {_WOLF_EDGE_ID}
    assert _WOLF_EDGE_ID not in payload["remaining_residual_edge_ids"]
    assert _WOLF_EDGE_ID not in payload["newly_represented_by_continuity_edge_ids"]


def test_eldyrwild_effective_conformance_integration_when_present() -> None:
    root = world_graph_root()
    eldyrwild = root / "graph_memory" / "worlds" / "eldyrwild"
    if not eldyrwild.is_dir():
        pytest.skip("Eldyrwild world graph not present")
    before = snapshot_world_graph_tree_digest(root, ELDYRWILD_WORLD_ID)
    report = analyze_relationship_effective_conformance_v1(
        root=root,
        world_id=ELDYRWILD_WORLD_ID,
        revision_id=ELDYRWILD_REVISION_ID,
    )
    after = snapshot_world_graph_tree_digest(root, ELDYRWILD_WORLD_ID)
    assert before == after
    compact = compact_relationship_effective_conformance_report_v1(report)
    committed = json.loads(EFFECTIVE_FIXTURE_PATH.read_text(encoding="utf-8"))
    assert compact == committed
