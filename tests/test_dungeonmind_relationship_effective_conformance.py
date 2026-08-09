"""Effective relationship conformance over continuity-governed descendants."""

from __future__ import annotations

import inspect
import json
import os
import shutil
from pathlib import Path

import pytest

import graph_memory.kernel as kernel
from apps.live_control_server.config import world_graph_root
from apps.live_control_server.integrations.dungeonmind_kernel.relationship_effective_conformance_v1 import (
    RELATIONSHIP_EFFECTIVE_CONFORMANCE_SCHEMA_V1,
    analyze_relationship_effective_conformance_v1,
    compact_relationship_effective_conformance_report_v1,
    resolve_carried_relationship_explicit_adapter_v1,
)
from apps.live_control_server.integrations.dungeonmind_kernel.relationship_explicit_adapters_v1 import (
    load_eldyrwild_relationship_explicit_adapter_catalog_v1,
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
from apps.live_control_server.integrations.dungeonmind_kernel.whole_world_conformance_v4 import (
    analyze_exact_buddy_world_revision_v4,
)
from graph_memory.union_supergraph.load import (
    DEFAULT_FIXTURE_PATH,
    load_union_supergraph_store,
)
from graph_memory.union_supergraph.model import (
    UnionSupergraphEdge,
    UnionSupergraphEvidence,
    UnionSupergraphNode,
    UnionSupergraphSourceArtifact,
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

_SPECIAL_SIX = _PR29_EDGE_IDS | _ADAPTER_EDGE_IDS

_WOLF_EDGE_ID = "edge:node:wolf:part_of:item:session17:centipede_meat_creature"

_SEED_EDGE_ID = "edge:item:session17:seed:located_in:pc:stafl"
_FEY_EDGE_ID = (
    "edge:node:fey_entity:present_at:pc:ephanna:appears-to-ephanna-in-prison"
)


def _clone_eldyrwild_root(tmp_path: Path) -> Path:
    """Copy Eldyrwild revisions into an isolated out-root; symlink runs for seals."""
    src_root = world_graph_root()
    eldyrwild_src = src_root / "graph_memory" / "worlds" / "eldyrwild"
    if not eldyrwild_src.is_dir():
        pytest.skip("Eldyrwild world graph not present")
    (tmp_path / "graph_memory" / "worlds").mkdir(parents=True)
    shutil.copytree(eldyrwild_src, tmp_path / "graph_memory" / "worlds" / "eldyrwild")
    runs = src_root / "graph_memory" / "runs"
    if runs.is_dir():
        os.symlink(runs, tmp_path / "graph_memory" / "runs")
    kernel.rollback_world_graph_head(tmp_path, ELDYRWILD_WORLD_ID, ELDYRWILD_REVISION_ID)
    return tmp_path


def _publish_unrelated_descendant(root: Path) -> str:
    store = kernel.load_world_graph_revision(
        root, ELDYRWILD_WORLD_ID, ELDYRWILD_REVISION_ID
    )
    store.nodes["npc:unrelated-continuity-rehearsal"] = UnionSupergraphNode(
        node_id="npc:unrelated-continuity-rehearsal",
        label="Unrelated continuity rehearsal",
        kind="npc",
        role="test",
        aliases=[],
        source_domains=["manual_seed"],
        evidence_ref_ids=[],
        state={},
    )
    result = kernel.publish_world_revision(
        root,
        ELDYRWILD_WORLD_ID,
        store,
        operation_ids=["op:eldyrwild-continuity-descendant-rehearsal"],
    )
    return result.revision.revision_id


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
    assert "continuity_state" not in carried_sig.parameters
    assert "store" not in carried_sig.parameters
    assert "graph_payload_sha256" not in carried_sig.parameters
    assert "root" in carried_sig.parameters
    with pytest.raises(TypeError):
        resolve_carried_relationship_explicit_adapter_v1(  # type: ignore[call-arg]
            root=Path("/tmp"),
            world_id="eldyrwild",
            revision_id=ELDYRWILD_REVISION_ID,
            edge=UnionSupergraphEdge(
                edge_id=_SEED_EDGE_ID,
                source_node_id="item:session17:seed",
                target_node_id="pc:stafl",
                predicate="located_in",
                label="located_in",
                direction="outbound",
                source_domains=["manual_seed"],
                evidence_ref_ids=[],
                state={},
            ),
            continuity_state="CARRIED_FORWARD",
        )


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


def test_unchanged_descendant_reapplies_exact_six_special_interpretations(
    tmp_path: Path,
) -> None:
    root = _clone_eldyrwild_root(tmp_path)
    r1 = _publish_unrelated_descendant(root)

    v4 = analyze_exact_buddy_world_revision_v4(
        root=root, world_id=ELDYRWILD_WORLD_ID, revision_id=r1
    )
    assert v4.relationship_semantic_count == 346
    assert v4.relationship_represented_count == 288
    assert v4.relationship_residual_count == 58
    assert _PR29_EDGE_IDS <= set(v4.relationship_residual_edge_ids)
    assert _ADAPTER_EDGE_IDS <= set(v4.relationship_residual_edge_ids)
    # Wolf remains ordinary v4 endpoint admission — not residual, not continuity-mapped.
    assert _WOLF_EDGE_ID not in v4.relationship_residual_edge_ids
    assert _WOLF_EDGE_ID in v4.relationship_newly_represented_edge_ids

    report = analyze_relationship_effective_conformance_v1(
        root=root, world_id=ELDYRWILD_WORLD_ID, revision_id=r1
    )
    assert report.relationship_semantic_count == 346
    assert report.relationship_effectively_represented_count == 294
    assert report.relationship_effective_residual_count == 52
    assert report.pr29_interpretation_applied_count == 3
    assert report.explicit_adapter_applied_count == 3
    assert set(report.newly_represented_by_continuity_edge_ids) == _SPECIAL_SIX
    assert _WOLF_EDGE_ID not in report.newly_represented_by_continuity_edge_ids
    assert len(report.active_adjudicated_edge_ids) == 59
    assert report.invalidated_adjudication_edge_ids == []
    assert report.dungeonmind_owned_remaining_count == 0
    assert report.dungeonmindbuddy_owned_remaining_count == 52
    dispositions = {
        row.key: row.count for row in report.remaining_residual_disposition_inventory
    }
    assert dispositions == _EXPECTED_REMAINING_DISPOSITIONS


def test_descendant_pr29_edge_change_blocks_that_interpretation_only(
    tmp_path: Path,
) -> None:
    root = _clone_eldyrwild_root(tmp_path)
    r1 = _publish_unrelated_descendant(root)
    store = kernel.load_world_graph_revision(root, ELDYRWILD_WORLD_ID, r1)
    edge = store.edges[_FEY_EDGE_ID]
    store.edges[_FEY_EDGE_ID] = edge.model_copy(update={"predicate": "located_in"})
    r2 = kernel.publish_world_revision(
        root,
        ELDYRWILD_WORLD_ID,
        store,
        operation_ids=["op:eldyrwild-invalidate-pr29-fey"],
    ).revision.revision_id

    report = analyze_relationship_effective_conformance_v1(
        root=root, world_id=ELDYRWILD_WORLD_ID, revision_id=r2
    )
    assert report.pr29_interpretation_applied_count == 2
    assert report.explicit_adapter_applied_count == 3
    assert _FEY_EDGE_ID not in report.newly_represented_by_continuity_edge_ids
    assert _FEY_EDGE_ID in report.invalidated_adjudication_edge_ids
    assert set(report.newly_represented_by_continuity_edge_ids) == (
        _SPECIAL_SIX - {_FEY_EDGE_ID}
    )
    # One special interpretation lost → 293 / 53 from the unchanged descendant base.
    assert report.relationship_effectively_represented_count == 293
    assert report.relationship_effective_residual_count == 53
    assert len(report.active_adjudicated_edge_ids) == 58


def test_descendant_adapter_edge_change_blocks_that_adapter_only(
    tmp_path: Path,
) -> None:
    root = _clone_eldyrwild_root(tmp_path)
    r1 = _publish_unrelated_descendant(root)
    store = kernel.load_world_graph_revision(root, ELDYRWILD_WORLD_ID, r1)
    edge = store.edges[_SEED_EDGE_ID]
    # Drift to an intentionally unresolved Buddy predicate so ordinary v4 does
    # not silently re-admit the edge after continuity invalidation.
    store.edges[_SEED_EDGE_ID] = edge.model_copy(update={"predicate": "identified_as"})
    r2 = kernel.publish_world_revision(
        root,
        ELDYRWILD_WORLD_ID,
        store,
        operation_ids=["op:eldyrwild-invalidate-adapter-seed"],
    ).revision.revision_id

    report = analyze_relationship_effective_conformance_v1(
        root=root, world_id=ELDYRWILD_WORLD_ID, revision_id=r2
    )
    assert report.pr29_interpretation_applied_count == 3
    assert report.explicit_adapter_applied_count == 2
    assert _SEED_EDGE_ID not in report.newly_represented_by_continuity_edge_ids
    assert _SEED_EDGE_ID in report.invalidated_adjudication_edge_ids
    assert set(report.newly_represented_by_continuity_edge_ids) == (
        _SPECIAL_SIX - {_SEED_EDGE_ID}
    )
    assert report.relationship_semantic_count == 346
    assert report.relationship_effectively_represented_count == 293
    assert report.relationship_effective_residual_count == 53
    assert len(report.active_adjudicated_edge_ids) == 58

def test_forged_carried_forward_in_another_world_yields_no_adapter(
    tmp_path: Path,
) -> None:
    """Exact PR #530 edge/shape in another world cannot forge continuity authority."""
    catalog = load_eldyrwild_relationship_explicit_adapter_catalog_v1()
    record = next(r for r in catalog.records if r.edge_id == _SEED_EDGE_ID)

    store = load_union_supergraph_store(DEFAULT_FIXTURE_PATH)
    store.nodes[record.expected_source_node_id] = UnionSupergraphNode(
        node_id=record.expected_source_node_id,
        label=record.expected_source_node_id,
        kind=record.expected_source_buddy_kind,
        role="test",
        aliases=[],
        source_domains=["manual_seed"],
        evidence_ref_ids=[],
        state={},
    )
    store.nodes[record.expected_target_node_id] = UnionSupergraphNode(
        node_id=record.expected_target_node_id,
        label=record.expected_target_node_id,
        kind=record.expected_target_buddy_kind,
        role="test",
        aliases=[],
        source_domains=["manual_seed"],
        evidence_ref_ids=[],
        state={},
    )
    evidence_id = "evidence:forge:seed"
    artifact_id = "artifact:forge:seed"
    store.evidence[evidence_id] = UnionSupergraphEvidence(
        evidence_ref_id=evidence_id,
        source_artifact_id=artifact_id,
        source_domain="manual_seed",
        evidence_role="supports",
        can_open_source=True,
        can_highlight_span=True,
        source_span_ref_id="span:forge",
        locator="span:forge",
    )
    store.source_artifacts[artifact_id] = UnionSupergraphSourceArtifact(
        source_artifact_id=artifact_id,
        source_domain="manual_seed",
        campaign_id="forge",
        uri="repo://synth/forge",
        content_sha256="a" * 64,
        status="active",
    )
    edge = UnionSupergraphEdge(
        edge_id=record.edge_id,
        source_node_id=record.expected_source_node_id,
        target_node_id=record.expected_target_node_id,
        predicate=record.expected_buddy_predicate,
        label=record.expected_buddy_predicate,
        direction="outbound",
        source_domains=["manual_seed"],
        evidence_ref_ids=[evidence_id],
        state={},
    )
    store.edges[record.edge_id] = edge

    other_world = "forge-adapter-world"
    revision_id = kernel.publish_world_revision(
        tmp_path,
        other_world,
        store,
        operation_ids=["op:forge-adapter-shape"],
    ).revision.revision_id

    # Public resolver derives continuity itself — forged CARRIED_FORWARD is impossible.
    resolved = resolve_carried_relationship_explicit_adapter_v1(
        root=tmp_path,
        world_id=other_world,
        revision_id=revision_id,
        edge=edge,
    )
    assert resolved is None

    with pytest.raises(TypeError):
        resolve_carried_relationship_explicit_adapter_v1(  # type: ignore[call-arg]
            root=tmp_path,
            world_id=other_world,
            revision_id=revision_id,
            edge=edge,
            continuity_state="CARRIED_FORWARD",
        )


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
