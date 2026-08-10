"""Effective relationship conformance over continuity-governed descendants."""

from __future__ import annotations

import hashlib
import inspect
import json
import os
import shutil
from pathlib import Path
from typing import Any

import pytest

import graph_memory.kernel as kernel
from apps.live_control_server.config import world_graph_root
from apps.live_control_server.integrations.dungeonmind_kernel.relationship_adjudication_continuity_v1 import (
    _analyze_relationship_adjudication_continuity_with_authorities,
    prove_revision_is_anchor_or_descendant_v1,
)
from apps.live_control_server.integrations.dungeonmind_kernel.relationship_effective_conformance_v1 import (
    RELATIONSHIP_EFFECTIVE_CONFORMANCE_SCHEMA_V1,
    _analyze_relationship_effective_conformance_with_authorities,
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
    WholeWorldConformanceReportV4,
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
    UnionSupergraphStore,
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
V4_FIXTURE_PATH = FIXTURES / "eldyrwild_post_v29_conformance_v1.json"
APPROVED_LYSANDRA_CORRECTION_PATH = (
    Path(__file__).resolve().parents[1]
    / "graph_data"
    / "approved_graph_corrections"
    / "eldyrwild"
    / "lysandra-threat-direction-v1.json"
)

# Current effective-conformance baseline after Lysandra live exit (Q_live).
# Distinct from immutable adjudication anchor ELDYRWILD_REVISION_ID (A).
R_CURRENT_REVISION_ID = "rev:b90646fb5b135988bd7842cde858c96e"
R_CURRENT_PAYLOAD_SHA256 = (
    "9bec03ebf893c1c5aca592f283757d5f455f2e67cf0fef7f85852cb85b2d480c"
)
Q_LIVE_REVISION_ID = R_CURRENT_REVISION_ID
P_LIVE_REVISION_ID = "rev:dfdf38edbefd734d108832e92467b208"
LOCKED_CORRECTION_CONTRIBUTION_ID = "contribution:4c65f668dc95ef4f"
LOCKED_CORRECTION_SOURCE_PAYLOAD_SHA256 = (
    "78d4d7118c3ba71ed0f930157bcd2343c675ccab8544580ff0aa506aa9ec0c5d"
)
TARGET_ASSERTION_ID = "assertion:1dc0fef6561c3282"
TARGET_EDGE_ID = (
    "edge:npc_lysandra:threatens:node:cultists_of_longmont:is-threatened-by-cultists"
)
REPLACEMENT_ASSERTION_ID = "assertion:3668ba31192a37ad"
REPLACEMENT_EDGE_ID = "edge:node:cultists_of_longmont:threatens:npc_lysandra"

_HISTORICAL_ADJUDICATION_FIXTURE_SHA256 = (
    "9aeade076defff7258a0cc25b93c18dcb64e6cdf94533d1b9b8f8ca409a6fbd8"
)
_HISTORICAL_ADAPTER_FIXTURE_SHA256 = (
    "310964d48e719f8027ea7d0db2f0ebada9ee6062251dc4b1258c0948bdf7a9fa"
)
_LOCKED_CORRECTION_RAW_ARTIFACT_SHA256 = (
    "ff0e07b1eee2085f8a6e8280e431e4d8d1eefa809b929538afe9f3f79a2c2518"
)

_SYNTH_EFFECTIVE_WORLD = "synth-effective-domain"
_SYNTH_EFFECTIVE_CAMPAIGN = "synth-effective-campaign"
_SEVENTH_EDGE_ID = (
    "edge:combat_shatter_mages_tower_spider:located_in:item_shatter_mages_tower"
)

_EXPECTED_CURRENT_REMAINING_DISPOSITIONS = {
    "SOURCE_CORRECTION_REQUIRED": 34,
    "COMPOUND_ASSERTION_NOT_SINGLE_RELATIONSHIP": 10,
    "IDENTITY_NOT_RELATIONSHIP": 6,
    "INSUFFICIENT_EVIDENCE": 1,
    "UNADJUDICATED": 7,
}

# Disposition inventory on the immutable adjudication anchor domain (A and
# unchanged A-descendants used by hermetic continuity proofs).
_EXPECTED_ANCHOR_REMAINING_DISPOSITIONS = {
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

_SPECIAL_DOMAIN_EDGE_IDS = frozenset(_SPECIAL_SIX | {_WOLF_EDGE_ID, _SEVENTH_EDGE_ID})


def _node(node_id: str, kind: str) -> UnionSupergraphNode:
    return UnionSupergraphNode(
        node_id=node_id,
        label=node_id,
        kind=kind,
        role="synth",
        aliases=[],
        source_domains=["manual_seed"],
        evidence_ref_ids=[],
        state={},
    )


def _edge(
    edge_id: str,
    *,
    source: str,
    target: str,
    predicate: str,
    evidence_ref_id: str,
) -> UnionSupergraphEdge:
    return UnionSupergraphEdge(
        edge_id=edge_id,
        source_node_id=source,
        target_node_id=target,
        predicate=predicate,
        label=predicate,
        direction="outbound",
        source_domains=["manual_seed"],
        session_ids=[],
        evidence_ref_ids=[evidence_ref_id],
        state={},
    )


def _evidence(evidence_id: str, artifact_id: str, span: str) -> UnionSupergraphEvidence:
    return UnionSupergraphEvidence(
        evidence_ref_id=evidence_id,
        source_artifact_id=artifact_id,
        source_domain="manual_seed",
        evidence_role="supports",
        can_open_source=True,
        can_highlight_span=True,
        source_span_ref_id=span,
        locator=span,
    )


def _artifact(artifact_id: str, sha: str) -> UnionSupergraphSourceArtifact:
    return UnionSupergraphSourceArtifact(
        source_artifact_id=artifact_id,
        source_domain="manual_seed",
        campaign_id=_SYNTH_EFFECTIVE_CAMPAIGN,
        uri=f"repo://synth/{artifact_id}",
        content_sha256=sha,
        status="active",
    )


def _clone_store(store: UnionSupergraphStore) -> UnionSupergraphStore:
    return UnionSupergraphStore.model_validate(
        store.model_dump(mode="python", by_alias=True)
    )


def _special_domain_specs() -> list[dict[str, str]]:
    """Exact six special edges + wolf ordinary + one non-special residual."""
    return [
        {
            "edge_id": _FEY_EDGE_ID,
            "source": "node:fey_entity",
            "source_kind": "faction",
            "target": "pc:ephanna",
            "target_kind": "pc",
            "predicate": "present_at",
        },
        {
            "edge_id": (
                "edge:pc:bonogo:defends_weakened_location:"
                "node:prisoners_session9:protects"
            ),
            "source": "pc:bonogo",
            "source_kind": "pc",
            "target": "node:prisoners_session9",
            "target_kind": "group",
            "predicate": "defends_weakened_location",
        },
        {
            "edge_id": "edge:pc:caelynn:controls_comms_with:npc_grobnok",
            "source": "pc:caelynn",
            "source_kind": "pc",
            "target": "npc_grobnok",
            "target_kind": "npc",
            "predicate": "controls_comms_with",
        },
        {
            "edge_id": _SEED_EDGE_ID,
            "source": "item:session17:seed",
            "source_kind": "item",
            "target": "pc:stafl",
            "target_kind": "pc",
            "predicate": "located_in",
        },
        {
            "edge_id": "edge:node:cultists_of_longmont:part_of:node:lesandra:led-by",
            "source": "node:cultists_of_longmont",
            "source_kind": "faction",
            "target": "node:lesandra",
            "target_kind": "npc",
            "predicate": "part_of",
        },
        {
            "edge_id": "edge:node:pippa:leads_to:loc:stone_bridge",
            "source": "node:pippa",
            "source_kind": "npc",
            "target": "loc:stone_bridge",
            "target_kind": "location",
            "predicate": "leads_to",
        },
        {
            "edge_id": _WOLF_EDGE_ID,
            "source": "node:wolf",
            "source_kind": "npc",
            "target": "item:session17:centipede_meat_creature",
            "target_kind": "item",
            "predicate": "part_of",
        },
        {
            "edge_id": _SEVENTH_EDGE_ID,
            "source": "combat_shatter_mages_tower_spider",
            "source_kind": "encounter",
            "target": "item_shatter_mages_tower",
            "target_kind": "item",
            "predicate": "located_in",
        },
    ]


def _special_domain_store() -> UnionSupergraphStore:
    """Minimal hermetic domain covering the 6 special + wolf + seventh residual."""
    store = load_union_supergraph_store(DEFAULT_FIXTURE_PATH)
    for index, spec in enumerate(_special_domain_specs()):
        evidence_id = f"evidence:synth:special:{index}"
        artifact_id = f"artifact:synth:special:{index}"
        span = f"span:synth:special:{index}"
        sha = f"{index:02d}" * 32
        store.nodes[spec["source"]] = _node(spec["source"], spec["source_kind"])
        store.nodes[spec["target"]] = _node(spec["target"], spec["target_kind"])
        store.evidence[evidence_id] = _evidence(evidence_id, artifact_id, span)
        store.source_artifacts[artifact_id] = _artifact(artifact_id, sha)
        store.edges[spec["edge_id"]] = _edge(
            spec["edge_id"],
            source=spec["source"],
            target=spec["target"],
            predicate=spec["predicate"],
            evidence_ref_id=evidence_id,
        )
    return store


def _special_domain_findings() -> dict[str, Any]:
    return {
        edge_id: ELDYRWILD_RESIDUAL_FINDINGS[edge_id]
        for edge_id in sorted(_SPECIAL_DOMAIN_EDGE_IDS)
    }


def _special_domain_seals(store: UnionSupergraphStore) -> dict[str, dict[str, Any]]:
    seals: dict[str, dict[str, Any]] = {}
    for edge_id in _SPECIAL_DOMAIN_EDGE_IDS:
        edge = store.edges[edge_id]
        evidence_id = edge.evidence_ref_ids[0]
        evidence = store.evidence[evidence_id]
        artifact = store.source_artifacts[evidence.source_artifact_id]
        seals[edge_id] = {
            "edge_id": edge_id,
            "primary_evidence_ref_id": evidence_id,
            "source_artifact_id": evidence.source_artifact_id,
            "artifact_content_sha256": artifact.content_sha256,
            "source_span_ref_id": evidence.source_span_ref_id,
            "locator_kind": "paragraph",
            "locator": evidence.locator,
            "excerpt_sha256": "ee" * 32,
        }
    return seals


def _publish_store(
    root: Path, world_id: str, store: UnionSupergraphStore, op: str
) -> str:
    result = kernel.publish_world_revision(
        root,
        world_id,
        store,
        operation_ids=[op],
    )
    revision_id = result.revision.revision_id
    assert revision_id
    return revision_id


def _synthetic_descendant_base_report_v4(
    *,
    world_id: str,
    revision_id: str,
    residual_edge_ids: list[str],
) -> WholeWorldConformanceReportV4:
    """Ordinary-v4 stand-in: six special + seventh residual; wolf already represented."""
    residual = sorted(residual_edge_ids)
    assert _WOLF_EDGE_ID not in residual
    assert set(_SPECIAL_SIX) <= set(residual)
    assert _SEVENTH_EDGE_ID in residual
    semantic_count = len(residual) + 1  # + wolf ordinary v4
    represented_count = 1
    payload = json.loads(V4_FIXTURE_PATH.read_text(encoding="utf-8"))
    report = WholeWorldConformanceReportV4.model_validate(payload)
    return report.model_copy(
        update={
            "source_world_id": world_id,
            "source_campaign_id": _SYNTH_EFFECTIVE_CAMPAIGN,
            "source_revision_id": revision_id,
            "source_graph_payload_sha256": "1" * 64,
            "relationship_semantic_count": semantic_count,
            "relationship_represented_count": represented_count,
            "relationship_residual_count": len(residual),
            "relationship_residual_edge_ids": residual,
            "relationship_newly_represented_edge_ids": [_WOLF_EDGE_ID],
            "uses_statblock_mechanics_count": 0,
        }
    )


def _analyze_synth_effective(
    *,
    root: Path,
    revision_id: str,
    anchor_revision_id: str,
    anchor_store: UnionSupergraphStore,
    requested_store: UnionSupergraphStore,
    residual_edge_ids: list[str] | None = None,
) -> Any:
    findings = _special_domain_findings()
    seals = _special_domain_seals(anchor_store)
    continuity = _analyze_relationship_adjudication_continuity_with_authorities(
        root=root,
        world_id=_SYNTH_EFFECTIVE_WORLD,
        revision_id=revision_id,
        findings=findings,
        seals_by_edge=seals,
        anchor_world_id=_SYNTH_EFFECTIVE_WORLD,
        anchor_revision_id=anchor_revision_id,
        anchor_payload_sha256="0" * 64,
        campaign_id=_SYNTH_EFFECTIVE_CAMPAIGN,
        anchor_store=anchor_store,
        requested_store=requested_store,
        requested_payload_sha256="1" * 64,
        verify_excerpt=False,
    )
    residual = residual_edge_ids
    if residual is None:
        residual = sorted(_SPECIAL_SIX | {_SEVENTH_EDGE_ID})
    base_report = _synthetic_descendant_base_report_v4(
        world_id=_SYNTH_EFFECTIVE_WORLD,
        revision_id=revision_id,
        residual_edge_ids=residual,
    )
    return _analyze_relationship_effective_conformance_with_authorities(
        root=root,
        world_id=_SYNTH_EFFECTIVE_WORLD,
        revision_id=revision_id,
        base_report=base_report,
        continuity=continuity,
        catalog=load_eldyrwild_relationship_explicit_adapter_catalog_v1(),
        store=requested_store,
    ), continuity


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
    assert payload["source_revision_id"] == R_CURRENT_REVISION_ID
    assert payload["source_graph_payload_sha256"] == R_CURRENT_PAYLOAD_SHA256
    assert payload["relationship_semantic_count"] == 369
    assert payload["relationship_effectively_represented_count"] == 311
    assert payload["relationship_effective_residual_count"] == 58
    assert payload["uses_statblock_mechanics_count"] == 3
    assert payload["dungeonmind_owned_remaining_count"] == 0
    assert payload["dungeonmindbuddy_owned_remaining_count"] == 51
    assert payload["unadjudicated_remaining_count"] == 7
    assert payload["requires_readjudication_count"] == 0
    assert len(payload["active_adjudicated_edge_ids"]) == 59
    assert TARGET_EDGE_ID not in payload["remaining_residual_edge_ids"]
    assert REPLACEMENT_EDGE_ID not in payload["remaining_residual_edge_ids"]
    assert payload["explicit_adapter_applied_count"] == 3
    assert payload["pr29_interpretation_applied_count"] == 3
    assert set(payload["newly_represented_by_continuity_edge_ids"]) == _SPECIAL_SIX

    dispositions = {
        row["key"]: row["count"]
        for row in payload["remaining_residual_disposition_inventory"]
    }
    assert dispositions == _EXPECTED_CURRENT_REMAINING_DISPOSITIONS

    # Historical adjudication/adapter fixtures remain sealed and distinct from
    # the current effective baseline (they answer a different authority question).
    adjudication_sha = hashlib.sha256(
        ADJUDICATION_FIXTURE_PATH.read_bytes()
    ).hexdigest()
    adapter_sha = hashlib.sha256(
        ADAPTER_CONFORMANCE_FIXTURE_PATH.read_bytes()
    ).hexdigest()
    assert adjudication_sha == _HISTORICAL_ADJUDICATION_FIXTURE_SHA256
    assert adapter_sha == _HISTORICAL_ADAPTER_FIXTURE_SHA256

    adjudication = json.loads(ADJUDICATION_FIXTURE_PATH.read_text(encoding="utf-8"))
    dm_owned = {
        record["edge_id"]
        for record in adjudication["records"]
        if record["responsible_repo"] == "DungeonMind"
    }
    assert dm_owned == _PR29_EDGE_IDS | {_WOLF_EDGE_ID}
    assert _WOLF_EDGE_ID not in payload["remaining_residual_edge_ids"]
    assert _WOLF_EDGE_ID not in payload["newly_represented_by_continuity_edge_ids"]
    assert adjudication["revision_id"] == ELDYRWILD_REVISION_ID
    assert adjudication["graph_payload_sha256"] == ELDYRWILD_PAYLOAD_SHA256


def test_synthetic_descendant_effective_composition_is_unconditional(
    tmp_path: Path,
) -> None:
    """Hermetic proof of descendant effective composition — never skips.

    Constructs the six special edges + wolf ordinary v4 + one non-special residual
    through private helpers only (no live Eldyrwild World Graph).
    """
    assert _SPECIAL_DOMAIN_EDGE_IDS <= set(ELDYRWILD_RESIDUAL_FINDINGS)
    assert len(_special_domain_findings()) == 8

    store_r0 = _special_domain_store()
    r0 = _publish_store(tmp_path, _SYNTH_EFFECTIVE_WORLD, store_r0, "op:synth-r0")

    store_r1 = _clone_store(store_r0)
    store_r1.nodes["npc:unrelated-synth"] = _node("npc:unrelated-synth", "npc")
    r1 = _publish_store(tmp_path, _SYNTH_EFFECTIVE_WORLD, store_r1, "op:synth-r1")

    ok, diagnostic, _ = prove_revision_is_anchor_or_descendant_v1(
        root=tmp_path,
        world_id=_SYNTH_EFFECTIVE_WORLD,
        requested_revision_id=r1,
        anchor_revision_id=r0,
        anchor_world_id=_SYNTH_EFFECTIVE_WORLD,
    )
    assert ok is True
    assert diagnostic is None

    report, continuity = _analyze_synth_effective(
        root=tmp_path,
        revision_id=r1,
        anchor_revision_id=r0,
        anchor_store=store_r0,
        requested_store=store_r1,
    )

    assert continuity.anchor_is_ancestor is True
    assert continuity.carried_forward_count == 8
    assert {row.continuity_state for row in continuity.rows} == {"CARRIED_FORWARD"}
    assert set(row.edge_id for row in continuity.rows if row.edge_id in _SPECIAL_SIX) == (
        _SPECIAL_SIX
    )

    # Ordinary v4 leaves the six special + seventh residual; wolf already represented.
    assert report.base_relationship_represented_count == 1
    assert report.base_relationship_residual_count == 7
    assert set(report.newly_represented_by_continuity_edge_ids) | set(
        report.remaining_residual_edge_ids
    ) == (_SPECIAL_SIX | {_SEVENTH_EDGE_ID})

    assert report.pr29_interpretation_applied_count == 3
    assert report.explicit_adapter_applied_count == 3
    assert set(report.newly_represented_by_continuity_edge_ids) == _SPECIAL_SIX
    assert _SEVENTH_EDGE_ID not in report.newly_represented_by_continuity_edge_ids
    assert _WOLF_EDGE_ID not in report.newly_represented_by_continuity_edge_ids
    assert report.remaining_residual_edge_ids == [_SEVENTH_EDGE_ID]
    assert report.relationship_semantic_count == 8
    assert report.relationship_effectively_represented_count == 7
    assert report.relationship_effective_residual_count == 1
    assert report.invalidated_adjudication_edge_ids == []

    # Invalidate one PR #29 row only.
    store_r2 = _clone_store(store_r1)
    fey = store_r2.edges[_FEY_EDGE_ID]
    store_r2.edges[_FEY_EDGE_ID] = fey.model_copy(update={"predicate": "located_in"})
    r2 = _publish_store(tmp_path, _SYNTH_EFFECTIVE_WORLD, store_r2, "op:synth-pr29")
    report_pr29, continuity_pr29 = _analyze_synth_effective(
        root=tmp_path,
        revision_id=r2,
        anchor_revision_id=r0,
        anchor_store=store_r0,
        requested_store=store_r2,
    )
    by_id = {row.edge_id: row for row in continuity_pr29.rows}
    assert by_id[_FEY_EDGE_ID].continuity_state == "INVALIDATED_BY_EDGE_CHANGE"
    assert by_id[_SEED_EDGE_ID].continuity_state == "CARRIED_FORWARD"
    assert report_pr29.pr29_interpretation_applied_count == 2
    assert report_pr29.explicit_adapter_applied_count == 3
    assert _FEY_EDGE_ID not in report_pr29.newly_represented_by_continuity_edge_ids
    assert set(report_pr29.newly_represented_by_continuity_edge_ids) == (
        _SPECIAL_SIX - {_FEY_EDGE_ID}
    )
    assert report_pr29.relationship_effectively_represented_count == 6
    assert report_pr29.relationship_effective_residual_count == 2
    assert _FEY_EDGE_ID in report_pr29.remaining_residual_edge_ids
    assert _SEVENTH_EDGE_ID in report_pr29.remaining_residual_edge_ids

    # Invalidate one adapter row only (from the unchanged descendant).
    store_r3 = _clone_store(store_r1)
    seed = store_r3.edges[_SEED_EDGE_ID]
    store_r3.edges[_SEED_EDGE_ID] = seed.model_copy(
        update={"predicate": "identified_as"}
    )
    r3 = _publish_store(tmp_path, _SYNTH_EFFECTIVE_WORLD, store_r3, "op:synth-adapter")
    report_adapter, continuity_adapter = _analyze_synth_effective(
        root=tmp_path,
        revision_id=r3,
        anchor_revision_id=r0,
        anchor_store=store_r0,
        requested_store=store_r3,
    )
    by_id = {row.edge_id: row for row in continuity_adapter.rows}
    assert by_id[_SEED_EDGE_ID].continuity_state == "INVALIDATED_BY_EDGE_CHANGE"
    assert by_id[_FEY_EDGE_ID].continuity_state == "CARRIED_FORWARD"
    assert report_adapter.pr29_interpretation_applied_count == 3
    assert report_adapter.explicit_adapter_applied_count == 2
    assert _SEED_EDGE_ID not in report_adapter.newly_represented_by_continuity_edge_ids
    assert set(report_adapter.newly_represented_by_continuity_edge_ids) == (
        _SPECIAL_SIX - {_SEED_EDGE_ID}
    )
    assert report_adapter.relationship_effectively_represented_count == 6
    assert report_adapter.relationship_effective_residual_count == 2


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
    assert dispositions == _EXPECTED_ANCHOR_REMAINING_DISPOSITIONS


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
        revision_id=R_CURRENT_REVISION_ID,
    )
    after = snapshot_world_graph_tree_digest(root, ELDYRWILD_WORLD_ID)
    assert before == after
    compact = compact_relationship_effective_conformance_report_v1(report)
    committed = json.loads(EFFECTIVE_FIXTURE_PATH.read_text(encoding="utf-8"))
    assert compact == committed
    assert compact["source_revision_id"] == R_CURRENT_REVISION_ID
    assert TARGET_EDGE_ID not in compact["remaining_residual_edge_ids"]
    assert REPLACEMENT_EDGE_ID not in compact["remaining_residual_edge_ids"]


def test_effective_conformance_inherits_support_aware_v4_correction_delta(
    tmp_path: Path,
) -> None:
    """§7F: effective conformance on correction-shaped P and Q follows support-aware v4."""
    from graph_memory.union_supergraph.load import (
        DEFAULT_FIXTURE_PATH,
        load_union_supergraph_store,
    )

    world_id = "effective-correction-delta"
    campaign_id = "longmont-c2"
    root = tmp_path
    kernel.publish_world_revision(
        root,
        world_id,
        load_union_supergraph_store(DEFAULT_FIXTURE_PATH),
        operation_ids=["op:effective-correction-baseline"],
    )

    def _node(node_id: str, kind: str):
        return kernel.build_assertion(
            assertion_kind="node",
            acceptance_state="accepted",
            subject_node_id=node_id,
            label=node_id,
            campaign_scope=campaign_id,
            value={"kind": kind, "role": "probe", "source_domains": ["manual_seed"]},
            identity_resolution_outcome="created_new",
        )

    def _edge(
        *,
        edge_id: str,
        source_node_id: str,
        target_node_id: str,
        predicate: str,
        evidence_ref_id: str,
        source_artifact_id: str,
    ):
        return kernel.build_assertion(
            assertion_kind="edge",
            acceptance_state="accepted",
            subject_node_id=source_node_id,
            target_node_id=target_node_id,
            predicate=predicate,
            label=predicate,
            campaign_scope=campaign_id,
            visibility="gm",
            epistemic_kind="fact",
            identity_resolution_outcome="resolved_existing",
            evidence_ref_ids=[evidence_ref_id],
            source_artifact_id=source_artifact_id,
            value={
                "edge_id": edge_id,
                "source_node_id": source_node_id,
                "target_node_id": target_node_id,
                "predicate": predicate,
                "direction": "outbound",
                "source_domains": ["manual_seed"],
                "evidence": [
                    {
                        "evidence_ref_id": evidence_ref_id,
                        "source_artifact_id": source_artifact_id,
                        "source_domain": "manual_seed",
                    }
                ],
            },
        )

    source = kernel.create_graph_contribution(
        world_id=world_id,
        source_kind="manual_import",
        source_artifact_id="artifact:eff-corr:source",
        campaign_scope=campaign_id,
        accepted_assertions=[
            _node("npc:eff-a", "npc"),
            _node("npc:eff-b", "npc"),
            _node("faction:eff-c", "faction"),
            _edge(
                edge_id="edge:eff:x",
                source_node_id="npc:eff-a",
                target_node_id="npc:eff-b",
                predicate="same_as",
                evidence_ref_id="evidence:eff:x",
                source_artifact_id="artifact:eff-corr:source",
            ),
        ],
    )
    published = kernel.merge_contribution_to_revision(
        root, world_id=world_id, contribution=source
    )
    assert published.published is True
    parent = published.revision_id
    assert parent

    before_p = snapshot_world_graph_tree_digest(root, world_id)
    eff_p = analyze_relationship_effective_conformance_v1(
        root=root, world_id=world_id, revision_id=parent
    )
    after_p = snapshot_world_graph_tree_digest(root, world_id)
    assert before_p == after_p
    assert "edge:eff:x" in eff_p.remaining_residual_edge_ids

    x_assertion = next(a for a in source.accepted_assertions if a.assertion_kind == "edge")
    replacement = _edge(
        edge_id="edge:eff:xp",
        source_node_id="faction:eff-c",
        target_node_id="npc:eff-a",
        predicate="threatens",
        evidence_ref_id="evidence:eff:xp",
        source_artifact_id="artifact:eff-corr:c",
    )
    correction = kernel.create_edge_assertion_correction_contribution(
        world_id=world_id,
        authored_by="gm-operator",
        target_contribution_id=source.contribution_id,
        target_assertion_id=x_assertion.assertion_id,
        replacement_assertion=replacement,
        source_artifact_id="artifact:eff-corr:c",
        campaign_scope=campaign_id,
    )
    corrected = kernel.correct_edge_assertion_support(
        root,
        world_id=world_id,
        contribution=correction,
        expected_parent_revision_id=parent,
    )
    assert corrected.published is True
    child = corrected.revision_id
    assert child

    before_q = snapshot_world_graph_tree_digest(root, world_id)
    eff_q = analyze_relationship_effective_conformance_v1(
        root=root, world_id=world_id, revision_id=child
    )
    after_q = snapshot_world_graph_tree_digest(root, world_id)
    assert before_q == after_q

    assert eff_q.relationship_semantic_count == eff_p.relationship_semantic_count
    assert (
        eff_q.relationship_effectively_represented_count
        == eff_p.relationship_effectively_represented_count + 1
    )
    assert (
        eff_q.relationship_effective_residual_count
        == eff_p.relationship_effective_residual_count - 1
    )
    assert eff_q.uses_statblock_mechanics_count == eff_p.uses_statblock_mechanics_count
    assert "edge:eff:x" not in eff_q.remaining_residual_edge_ids
    assert "edge:eff:xp" not in eff_q.remaining_residual_edge_ids
    store_q = kernel.load_world_graph_revision(root, world_id, child)
    assert "edge:eff:x" in store_q.edges

    # Immutable adjudication-domain observation on historical A remains 346/294/52/2.
    # That is not the current effective fixture (R_current / Q_live).
    eldyrwild = world_graph_root() / "graph_memory" / "worlds" / "eldyrwild"
    if eldyrwild.is_dir():
        before = snapshot_world_graph_tree_digest(world_graph_root(), ELDYRWILD_WORLD_ID)
        anchor = analyze_relationship_effective_conformance_v1(
            root=world_graph_root(),
            world_id=ELDYRWILD_WORLD_ID,
            revision_id=ELDYRWILD_REVISION_ID,
        )
        after = snapshot_world_graph_tree_digest(world_graph_root(), ELDYRWILD_WORLD_ID)
        assert before == after
        assert anchor.relationship_semantic_count == 346
        assert anchor.relationship_effectively_represented_count == 294
        assert anchor.relationship_effective_residual_count == 52
        assert anchor.uses_statblock_mechanics_count == 2
        assert anchor.source_revision_id == ELDYRWILD_REVISION_ID
        current_fixture = json.loads(EFFECTIVE_FIXTURE_PATH.read_text(encoding="utf-8"))
        assert current_fixture["source_revision_id"] == R_CURRENT_REVISION_ID
        assert current_fixture["relationship_semantic_count"] != 346


def _clone_eldyrwild_world(tmp_path: Path) -> Path:
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


def test_r_current_ancestry_includes_adjudication_anchor_and_q_live(
    tmp_path: Path,
) -> None:
    root = _clone_eldyrwild_world(tmp_path)
    ok_a, diag_a, _ = prove_revision_is_anchor_or_descendant_v1(
        root=root,
        world_id=ELDYRWILD_WORLD_ID,
        requested_revision_id=R_CURRENT_REVISION_ID,
        anchor_revision_id=ELDYRWILD_REVISION_ID,
    )
    assert ok_a is True, diag_a
    ok_q, diag_q, _ = prove_revision_is_anchor_or_descendant_v1(
        root=root,
        world_id=ELDYRWILD_WORLD_ID,
        requested_revision_id=R_CURRENT_REVISION_ID,
        anchor_revision_id=Q_LIVE_REVISION_ID,
    )
    assert ok_q is True, diag_q
    ok_p, diag_p, _ = prove_revision_is_anchor_or_descendant_v1(
        root=root,
        world_id=ELDYRWILD_WORLD_ID,
        requested_revision_id=Q_LIVE_REVISION_ID,
        anchor_revision_id=P_LIVE_REVISION_ID,
    )
    assert ok_p is True, diag_p


def test_r_current_retains_lysandra_correction_authority(tmp_path: Path) -> None:
    from apps.live_control_server.services.eldyrwild_lysandra_threat_direction_correction import (
        get_lysandra_threat_direction_correction_status,
    )
    from graph_memory.kernel.contributions import (
        compute_contribution_source_payload_sha256,
    )
    from graph_memory.world_supergraph.contribution_store import load_contribution_record

    root = _clone_eldyrwild_world(tmp_path)
    store = kernel.load_world_graph_revision(
        root, ELDYRWILD_WORLD_ID, R_CURRENT_REVISION_ID
    )
    x = store.assertion_support[TARGET_ASSERTION_ID]
    xp = store.assertion_support[REPLACEMENT_ASSERTION_ID]
    assert x["support_state"] == "contradicted"
    assert not (x.get("active_contribution_ids") or [])
    assert xp["support_state"] == "supported"
    assert list(xp.get("active_contribution_ids") or []) == [
        LOCKED_CORRECTION_CONTRIBUTION_ID
    ]
    assert REPLACEMENT_EDGE_ID in store.edges
    ledger = load_contribution_record(
        root, ELDYRWILD_WORLD_ID, LOCKED_CORRECTION_CONTRIBUTION_ID
    )
    assert (
        compute_contribution_source_payload_sha256(ledger)
        == LOCKED_CORRECTION_SOURCE_PAYLOAD_SHA256
    )
    st = get_lysandra_threat_direction_correction_status(
        root=root, expected_parent_revision_id=R_CURRENT_REVISION_ID
    )
    assert st.eligibility == "already_applied"


def test_historical_x_continuity_remains_source_grounded(tmp_path: Path) -> None:
    from apps.live_control_server.integrations.dungeonmind_kernel.relationship_adjudication_continuity_v1 import (
        analyze_relationship_adjudication_continuity_v1,
    )

    root = _clone_eldyrwild_world(tmp_path)
    continuity = analyze_relationship_adjudication_continuity_v1(
        root=root,
        world_id=ELDYRWILD_WORLD_ID,
        revision_id=R_CURRENT_REVISION_ID,
    )
    rows = {row.edge_id: row for row in continuity.rows}
    assert TARGET_EDGE_ID in rows
    row = rows[TARGET_EDGE_ID]
    assert row.source_grounding_verified is True
    assert row.durable_shape_verified is True
    store = kernel.load_world_graph_revision(
        root, ELDYRWILD_WORLD_ID, R_CURRENT_REVISION_ID
    )
    assert TARGET_EDGE_ID in store.edges
    report = analyze_relationship_effective_conformance_v1(
        root=root,
        world_id=ELDYRWILD_WORLD_ID,
        revision_id=R_CURRENT_REVISION_ID,
    )
    assert TARGET_EDGE_ID not in report.remaining_residual_edge_ids


def test_source_and_adjudication_seals_unchanged_by_reanchor() -> None:
    assert (
        hashlib.sha256(ADJUDICATION_FIXTURE_PATH.read_bytes()).hexdigest()
        == _HISTORICAL_ADJUDICATION_FIXTURE_SHA256
    )
    assert (
        hashlib.sha256(ADAPTER_CONFORMANCE_FIXTURE_PATH.read_bytes()).hexdigest()
        == _HISTORICAL_ADAPTER_FIXTURE_SHA256
    )
    assert (
        hashlib.sha256(APPROVED_LYSANDRA_CORRECTION_PATH.read_bytes()).hexdigest()
        == _LOCKED_CORRECTION_RAW_ARTIFACT_SHA256
    )
    adjudication = json.loads(ADJUDICATION_FIXTURE_PATH.read_text(encoding="utf-8"))
    assert adjudication["revision_id"] == ELDYRWILD_REVISION_ID
    assert adjudication["graph_payload_sha256"] == ELDYRWILD_PAYLOAD_SHA256


def test_r_current_rebuilds_pinned_and_unpinned(tmp_path: Path) -> None:
    root = _clone_eldyrwild_world(tmp_path)
    pinned = kernel.rebuild_from_contributions(
        root,
        world_id=ELDYRWILD_WORLD_ID,
        compare_revision_id=R_CURRENT_REVISION_ID,
        publish=False,
    )
    unpinned = kernel.rebuild_from_contributions(
        root,
        world_id=ELDYRWILD_WORLD_ID,
        publish=False,
    )
    pinned_diag = list(getattr(pinned, "diagnostics", []) or [])
    unpinned_diag = list(getattr(unpinned, "diagnostics", []) or [])
    assert "rebuild_equivalent_to_pinned_revision" in pinned_diag
    assert (
        "rebuild_equivalent_to_head" in unpinned_diag
        or "rebuild_equivalent_to_published_head" in unpinned_diag
    )
    # Rebuild audit is clone-local; prove Lysandra authority still reconstructs.
    store = kernel.load_world_graph_revision(
        root, ELDYRWILD_WORLD_ID, R_CURRENT_REVISION_ID
    )
    assert store.assertion_support[TARGET_ASSERTION_ID]["support_state"] == "contradicted"
    assert store.assertion_support[REPLACEMENT_ASSERTION_ID]["support_state"] == "supported"
    assert list(
        store.assertion_support[REPLACEMENT_ASSERTION_ID]["active_contribution_ids"]
    ) == [LOCKED_CORRECTION_CONTRIBUTION_ID]


def test_effective_reanchor_tests_do_not_mutate_canonical_world() -> None:
    root = world_graph_root()
    eldyrwild = root / "graph_memory" / "worlds" / "eldyrwild"
    if not eldyrwild.is_dir():
        pytest.skip("Eldyrwild world graph not present")
    before_head = kernel.open_world_graph_head(root, ELDYRWILD_WORLD_ID).head_revision_id
    before_tree = snapshot_world_graph_tree_digest(root, ELDYRWILD_WORLD_ID)
    before_index = (
        root / "graph_memory" / "worlds" / "eldyrwild" / "contribution_index.json"
    ).read_bytes()
    _ = analyze_relationship_effective_conformance_v1(
        root=root,
        world_id=ELDYRWILD_WORLD_ID,
        revision_id=R_CURRENT_REVISION_ID,
    )
    assert (
        kernel.open_world_graph_head(root, ELDYRWILD_WORLD_ID).head_revision_id
        == before_head
        == R_CURRENT_REVISION_ID
    )
    assert snapshot_world_graph_tree_digest(root, ELDYRWILD_WORLD_ID) == before_tree
    assert (
        root / "graph_memory" / "worlds" / "eldyrwild" / "contribution_index.json"
    ).read_bytes() == before_index
