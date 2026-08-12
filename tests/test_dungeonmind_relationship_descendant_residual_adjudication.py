"""Session-25 descendant residual adjudication (U₇) owning proofs."""

from __future__ import annotations

import hashlib
import json
import os
import shutil
from pathlib import Path

import pytest

import graph_memory.kernel as kernel
from apps.live_control_server.config import world_graph_root
from apps.live_control_server.integrations.dungeonmind_kernel.relationship_adjudication_authority_v1 import (
    HISTORICAL_A_AUTHORITY_ID,
    RELATIONSHIP_ADJUDICATION_AUTHORITY_SCHEMA_V1,
    SESSION25_DESCENDANT_AUTHORITY_ID,
    RelationshipAdjudicationAuthorityError,
    RelationshipAdjudicationAuthorityReportV1,
    RelationshipAdjudicationAuthorityRowV1,
    analyze_composed_relationship_adjudication_authority_v1,
    analyze_session25_descendant_continuity_v1,
    reject_naive_union_into_historical_a_anchor,
)
from apps.live_control_server.integrations.dungeonmind_kernel.relationship_adjudication_continuity_v1 import (
    RELATIONSHIP_ADJUDICATION_CONTINUITY_SCHEMA_V1,
    RelationshipAdjudicationContinuityReportV1,
    _analyze_relationship_adjudication_continuity_with_authorities,
    analyze_relationship_adjudication_continuity_v1,
    compact_relationship_adjudication_continuity_report_v1,
)
from apps.live_control_server.integrations.dungeonmind_kernel.relationship_descendant_residual_adjudication_v1 import (
    DESCENDANT_RESIDUAL_ADJUDICATION_SCHEMA_V1,
    DESCENDANT_RESIDUAL_SOURCE_SEALS_SCHEMA_V1,
    ELDYRWILD_DESCENDANT_RESIDUAL_FINDINGS,
    EXACT_U7_EDGE_IDS,
    EXPECTED_DESCENDANT_RESIDUAL_COUNT,
    S25_PARENT_REVISION_ID,
    S25_PAYLOAD_SHA256,
    S25_REVISION_ID,
    S25_SOURCE_ARTIFACT_CONTENT_SHA256,
    S25_SOURCE_ARTIFACT_ID,
    U7,
    RelationshipDescendantResidualAdjudicationError,
    analyze_eldyrwild_descendant_residual_adjudication_v1,
    compact_descendant_residual_adjudication_report_v1,
    descendant_residual_fixture_sha256,
    load_descendant_residual_source_seals,
)
from apps.live_control_server.integrations.dungeonmind_kernel.relationship_effective_conformance_v1 import (
    RelationshipEffectiveConformanceError,
    _analyze_relationship_effective_conformance_with_authorities,
    analyze_relationship_effective_conformance_v1,
    compact_relationship_effective_conformance_report_v1,
)
from apps.live_control_server.integrations.dungeonmind_kernel.relationship_explicit_adapters_v1 import (
    RelationshipExplicitAdapterCatalogV1,
)
from apps.live_control_server.integrations.dungeonmind_kernel.relationship_residual_adjudication import (
    ELDYRWILD_CAMPAIGN_ID,
    ELDYRWILD_PAYLOAD_SHA256,
    ELDYRWILD_RESIDUAL_FINDINGS,
    ELDYRWILD_REVISION_ID,
    ELDYRWILD_WORLD_ID,
    ReasonCode,
    ResidualDisposition,
    _adapter,
    _source,
    load_residual_source_seals,
)
from apps.live_control_server.integrations.dungeonmind_kernel.whole_world_conformance import (
    snapshot_world_graph_tree_digest,
)
from apps.live_control_server.integrations.dungeonmind_kernel.whole_world_conformance_v4 import (
    WholeWorldConformanceReportV4,
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
from graph_memory.world_supergraph.storage import (
    load_world_graph_revision_manifest,
    open_world_graph_head,
)

FIXTURES = Path(__file__).resolve().parent / "fixtures" / "dungeonmind_kernel"
DESCENDANT_SEALS_PATH = (
    FIXTURES / "eldyrwild_relationship_descendant_residual_source_seals_v1.json"
)
DESCENDANT_ADJUDICATION_PATH = (
    FIXTURES / "eldyrwild_relationship_descendant_residual_adjudication_v1.json"
)
HISTORICAL_ADJUDICATION_PATH = (
    FIXTURES / "eldyrwild_relationship_residual_adjudication_v1.json"
)
HISTORICAL_SEALS_PATH = (
    FIXTURES / "eldyrwild_relationship_residual_source_seals_v1.json"
)
CONTINUITY_FIXTURE_PATH = (
    FIXTURES / "eldyrwild_relationship_adjudication_continuity_v1.json"
)
EFFECTIVE_FIXTURE_PATH = (
    FIXTURES / "eldyrwild_relationship_effective_conformance_v1.json"
)
V4_FIXTURE_PATH = FIXTURES / "eldyrwild_post_v29_conformance_v1.json"

A_REVISION_ID = ELDYRWILD_REVISION_ID  # rev:3413bf6f5044cf2680233f5e37c90dcf
Q3_REVISION_ID = "rev:ba3abde1bfc3659795bcd77bb55eb9f7"
Q4_REVISION_ID = "rev:3759d8d6a02f09306397918234a2ded2"

_DESCENDANT_SEALS_SHA256 = (
    "a056f19338b321bc42e8d4c01e9e0b2fd91443b0f5cb6c794e1b6edf5abc838c"
)
_DESCENDANT_ADJUDICATION_SHA256 = (
    "4a2f86ee9c9ca5a020f139bd50c1a22d7a14405a4f53e55d8f7c4bb16da79e95"
)
_HISTORICAL_ADJUDICATION_SHA256 = (
    "9aeade076defff7258a0cc25b93c18dcb64e6cdf94533d1b9b8f8ca409a6fbd8"
)
_HISTORICAL_SEALS_SHA256 = (
    "aed63e2ec42c5a587f62cd012447f2eee6e66cdc5a2090382bf909e285779e6e"
)

_EXPECTED_Q3_REMAINING_DISPOSITIONS = {
    "SOURCE_CORRECTION_REQUIRED": 37,
    "COMPOUND_ASSERTION_NOT_SINGLE_RELATIONSHIP": 11,
    "IDENTITY_NOT_RELATIONSHIP": 7,
    "INSUFFICIENT_EVIDENCE": 1,
}

_SEED_EDGE_ID = "edge:item:session17:seed:located_in:pc:stafl"
_SYNTH_WORLD = "synth-s25-descendant-authority"
_SYNTH_CAMPAIGN = "synth-s25-campaign"


def _eldyrwild_available() -> bool:
    root = world_graph_root()
    return (root / "graph_memory" / "worlds" / "eldyrwild").is_dir()


def _require_eldyrwild() -> Path:
    if not _eldyrwild_available():
        pytest.skip("Eldyrwild world graph not present")
    return world_graph_root()


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
        campaign_id=_SYNTH_CAMPAIGN,
        uri=f"repo://synth/{artifact_id}",
        content_sha256=sha,
        status="active",
    )


def _clone_store(store: UnionSupergraphStore) -> UnionSupergraphStore:
    return UnionSupergraphStore.model_validate(
        store.model_dump(mode="python", by_alias=True)
    )


def _empty_catalog(*, revision_id: str) -> RelationshipExplicitAdapterCatalogV1:
    return RelationshipExplicitAdapterCatalogV1(
        world_id=_SYNTH_WORLD,
        campaign_id=_SYNTH_CAMPAIGN,
        source_revision_id=revision_id,
        source_graph_payload_sha256="0" * 64,
        records=[],
    )


def _base_report_v4(
    *,
    world_id: str,
    revision_id: str,
    residual_edge_ids: list[str],
    represented_count: int = 0,
) -> WholeWorldConformanceReportV4:
    residual = sorted(residual_edge_ids)
    payload = json.loads(V4_FIXTURE_PATH.read_text(encoding="utf-8"))
    report = WholeWorldConformanceReportV4.model_validate(payload)
    return report.model_copy(
        update={
            "source_world_id": world_id,
            "source_campaign_id": _SYNTH_CAMPAIGN,
            "source_revision_id": revision_id,
            "source_graph_payload_sha256": "1" * 64,
            "relationship_semantic_count": represented_count + len(residual),
            "relationship_represented_count": represented_count,
            "relationship_residual_count": len(residual),
            "relationship_residual_edge_ids": residual,
            "relationship_newly_represented_edge_ids": [],
            "uses_statblock_mechanics_count": 0,
        }
    )


def _empty_continuity(
    *,
    world_id: str,
    anchor_revision_id: str,
    requested_revision_id: str,
) -> RelationshipAdjudicationContinuityReportV1:
    return RelationshipAdjudicationContinuityReportV1(
        schema_version=RELATIONSHIP_ADJUDICATION_CONTINUITY_SCHEMA_V1,
        world_id=world_id,
        campaign_id=_SYNTH_CAMPAIGN,
        anchor_revision_id=anchor_revision_id,
        anchor_graph_payload_sha256="0" * 64,
        requested_revision_id=requested_revision_id,
        requested_graph_payload_sha256="1" * 64,
        anchor_is_ancestor=True,
        anchor_finding_count=0,
        carried_forward_count=0,
        invalidated_edge_change_count=0,
        invalidated_source_change_count=0,
        removed_edge_count=0,
        requires_readjudication_count=0,
        not_descendant_count=0,
        anchor_count=0,
        rows=[],
    )


# ---------------------------------------------------------------------------
# T1 — exact U₇ coverage at Q₃
# ---------------------------------------------------------------------------


@pytest.mark.skipif(not _eldyrwild_available(), reason="Eldyrwild world graph not present")
def test_t1_exact_u7_coverage_at_q3() -> None:
    root = _require_eldyrwild()
    report = analyze_relationship_effective_conformance_v1(
        root=root,
        world_id=ELDYRWILD_WORLD_ID,
        revision_id=Q3_REVISION_ID,
    )
    remaining = set(report.remaining_residual_edge_ids)
    assert remaining - set(ELDYRWILD_RESIDUAL_FINDINGS) == set(EXACT_U7_EDGE_IDS)
    assert set(ELDYRWILD_DESCENDANT_RESIDUAL_FINDINGS) == set(EXACT_U7_EDGE_IDS)
    seals = load_descendant_residual_source_seals()
    assert set(seals) == set(EXACT_U7_EDGE_IDS)
    assert len(EXACT_U7_EDGE_IDS) == EXPECTED_DESCENDANT_RESIDUAL_COUNT == 7
    assert set(EXACT_U7_EDGE_IDS).isdisjoint(ELDYRWILD_RESIDUAL_FINDINGS)


# ---------------------------------------------------------------------------
# T2 — S25 parent / payload / edges
# ---------------------------------------------------------------------------


@pytest.mark.skipif(not _eldyrwild_available(), reason="Eldyrwild world graph not present")
def test_t2_s25_parent_payload_and_u7_edges(tmp_path: Path) -> None:
    root = _clone_eldyrwild_world(tmp_path)
    manifest = load_world_graph_revision_manifest(root, ELDYRWILD_WORLD_ID, S25_REVISION_ID)
    assert manifest.parent_revision_id == S25_PARENT_REVISION_ID == A_REVISION_ID
    assert manifest.graph_payload_sha256 == S25_PAYLOAD_SHA256

    store = kernel.load_world_graph_revision(root, ELDYRWILD_WORLD_ID, S25_REVISION_ID)
    for edge_id in EXACT_U7_EDGE_IDS:
        assert edge_id in store.edges

    report = analyze_eldyrwild_descendant_residual_adjudication_v1(root=root)
    assert report.anchor_revision_id == S25_REVISION_ID
    assert report.anchor_graph_payload_sha256 == S25_PAYLOAD_SHA256
    assert report.adjudicated_count == 7
    compact = compact_descendant_residual_adjudication_report_v1(report)
    committed = json.loads(DESCENDANT_ADJUDICATION_PATH.read_text(encoding="utf-8"))
    assert compact == committed


# ---------------------------------------------------------------------------
# T3 — source support seals verify
# ---------------------------------------------------------------------------


@pytest.mark.skipif(not _eldyrwild_available(), reason="Eldyrwild world graph not present")
def test_t3_source_support_seals_verify() -> None:
    root = _require_eldyrwild()
    seals = load_descendant_residual_source_seals(DESCENDANT_SEALS_PATH)
    assert len(seals) == 7
    for edge_id in EXACT_U7_EDGE_IDS:
        seal = seals[edge_id]
        assert seal["source_artifact_id"] == S25_SOURCE_ARTIFACT_ID
        assert seal["artifact_content_sha256"] == S25_SOURCE_ARTIFACT_CONTENT_SHA256
        assert seal["primary_evidence_ref_id"]
        assert seal["excerpt_sha256"]
        assert seal["normalized_excerpt"].strip()

    # Live analysis verifies excerpts against Session-25 artifact bytes.
    report = analyze_eldyrwild_descendant_residual_adjudication_v1(
        root=root, verify_excerpts=True
    )
    assert report.adjudicated_count == 7
    assert report.world_graph_digest_before == report.world_graph_digest_after
    by_edge = {row.edge_id: row for row in report.records}
    for edge_id in EXACT_U7_EDGE_IDS:
        row = by_edge[edge_id]
        seal = seals[edge_id]
        assert row.primary_evidence_ref_id == seal["primary_evidence_ref_id"]
        assert row.source_artifact_id == seal["source_artifact_id"]
        assert row.excerpt_sha256 == seal["excerpt_sha256"]
        assert row.source_span_ref_id == seal["source_span_ref_id"]


# ---------------------------------------------------------------------------
# T4 — continuity ANCHOR at S25, CARRIED_FORWARD at Q₃
# ---------------------------------------------------------------------------


@pytest.mark.skipif(not _eldyrwild_available(), reason="Eldyrwild world graph not present")
def test_t4_descendant_continuity_anchor_then_carried(tmp_path: Path) -> None:
    root = _clone_eldyrwild_world(tmp_path)

    at_s25 = analyze_session25_descendant_continuity_v1(
        root=root,
        world_id=ELDYRWILD_WORLD_ID,
        revision_id=S25_REVISION_ID,
    )
    assert at_s25.anchor_revision_id == S25_REVISION_ID
    assert at_s25.anchor_graph_payload_sha256 == S25_PAYLOAD_SHA256
    assert at_s25.anchor_finding_count == 7
    assert at_s25.anchor_count == 7
    assert at_s25.carried_forward_count == 0
    assert {row.continuity_state for row in at_s25.rows} == {"ANCHOR"}
    assert {row.edge_id for row in at_s25.rows} == set(EXACT_U7_EDGE_IDS)

    at_q3 = analyze_session25_descendant_continuity_v1(
        root=root,
        world_id=ELDYRWILD_WORLD_ID,
        revision_id=Q3_REVISION_ID,
    )
    assert at_q3.anchor_revision_id == S25_REVISION_ID  # not re-anchored to Q₃
    assert at_q3.anchor_graph_payload_sha256 == S25_PAYLOAD_SHA256
    assert at_q3.carried_forward_count == 7
    assert at_q3.anchor_count == 0
    assert at_q3.invalidated_edge_change_count == 0
    assert at_q3.invalidated_source_change_count == 0
    assert at_q3.removed_edge_count == 0
    assert at_q3.requires_readjudication_count == 0
    assert {row.continuity_state for row in at_q3.rows} == {"CARRIED_FORWARD"}


# ---------------------------------------------------------------------------
# T5 — A immutable
# ---------------------------------------------------------------------------


def test_t5_historical_a_fixtures_and_public_continuity_immutable() -> None:
    assert (
        hashlib.sha256(HISTORICAL_ADJUDICATION_PATH.read_bytes()).hexdigest()
        == _HISTORICAL_ADJUDICATION_SHA256
    )
    assert (
        hashlib.sha256(HISTORICAL_SEALS_PATH.read_bytes()).hexdigest()
        == _HISTORICAL_SEALS_SHA256
    )
    assert (
        descendant_residual_fixture_sha256(DESCENDANT_SEALS_PATH)
        == _DESCENDANT_SEALS_SHA256
    )
    assert (
        descendant_residual_fixture_sha256(DESCENDANT_ADJUDICATION_PATH)
        == _DESCENDANT_ADJUDICATION_SHA256
    )

    adjudication = json.loads(HISTORICAL_ADJUDICATION_PATH.read_text(encoding="utf-8"))
    assert adjudication["revision_id"] == A_REVISION_ID
    assert adjudication["graph_payload_sha256"] == ELDYRWILD_PAYLOAD_SHA256
    assert len(adjudication["records"]) == 59
    assert len(ELDYRWILD_RESIDUAL_FINDINGS) == 59

    seals = load_residual_source_seals(HISTORICAL_SEALS_PATH)
    assert len(seals) == 59

    if not _eldyrwild_available():
        pytest.skip("Eldyrwild world graph not present")

    root = world_graph_root()
    at_a = analyze_relationship_adjudication_continuity_v1(
        root=root,
        world_id=ELDYRWILD_WORLD_ID,
        revision_id=A_REVISION_ID,
    )
    assert at_a.anchor_revision_id == A_REVISION_ID
    assert at_a.anchor_finding_count == 59
    assert at_a.anchor_graph_payload_sha256 == ELDYRWILD_PAYLOAD_SHA256
    compact = compact_relationship_adjudication_continuity_report_v1(at_a)
    committed = json.loads(CONTINUITY_FIXTURE_PATH.read_text(encoding="utf-8"))
    assert compact == committed

    at_q3 = analyze_relationship_adjudication_continuity_v1(
        root=root,
        world_id=ELDYRWILD_WORLD_ID,
        revision_id=Q3_REVISION_ID,
    )
    assert at_q3.anchor_revision_id == A_REVISION_ID
    assert at_q3.anchor_finding_count == 59
    assert at_q3.carried_forward_count == 59


# ---------------------------------------------------------------------------
# T6 — composed 59+7=66; reject naive union
# ---------------------------------------------------------------------------


@pytest.mark.skipif(not _eldyrwild_available(), reason="Eldyrwild world graph not present")
def test_t6_composed_authority_and_reject_naive_union(tmp_path: Path) -> None:
    root = _clone_eldyrwild_world(tmp_path)
    composed = analyze_composed_relationship_adjudication_authority_v1(
        root=root,
        world_id=ELDYRWILD_WORLD_ID,
        revision_id=Q3_REVISION_ID,
    )
    assert composed.schema_version == RELATIONSHIP_ADJUDICATION_AUTHORITY_SCHEMA_V1
    assert composed.historical_a_row_count == 59
    assert composed.session25_descendant_row_count == 7
    assert composed.composed_row_count == 66
    assert composed.historical_a.anchor_finding_count == 59
    assert composed.session25_descendant.anchor_finding_count == 7

    by_auth: dict[str, set[str]] = {
        HISTORICAL_A_AUTHORITY_ID: set(),
        SESSION25_DESCENDANT_AUTHORITY_ID: set(),
    }
    for row in composed.rows:
        by_auth[row.authority_id].add(row.edge_id)
        if row.authority_id == HISTORICAL_A_AUTHORITY_ID:
            assert row.anchor_revision_id == A_REVISION_ID
            assert row.continuity_state == "CARRIED_FORWARD"
            assert row.finding == ELDYRWILD_RESIDUAL_FINDINGS[row.edge_id]
        elif row.authority_id == SESSION25_DESCENDANT_AUTHORITY_ID:
            assert row.anchor_revision_id == S25_REVISION_ID
            assert row.continuity_state == "CARRIED_FORWARD"
            assert row.finding == ELDYRWILD_DESCENDANT_RESIDUAL_FINDINGS[row.edge_id]
        else:
            raise AssertionError(f"unexpected authority_id {row.authority_id}")
        assert row.disposition == row.finding.disposition.value
        assert row.responsible_repo == row.finding.responsible_repo.value
        assert row.next_action == row.finding.next_action.value
    assert by_auth[HISTORICAL_A_AUTHORITY_ID] == set(ELDYRWILD_RESIDUAL_FINDINGS)
    assert by_auth[SESSION25_DESCENDANT_AUTHORITY_ID] == set(EXACT_U7_EDGE_IDS)
    assert not (
        by_auth[HISTORICAL_A_AUTHORITY_ID] & by_auth[SESSION25_DESCENDANT_AUTHORITY_ID]
    )

    # Injected S25 continuity re-anchored at Q₃ must fail closed.
    bad_s25 = composed.session25_descendant.model_copy(
        update={"anchor_revision_id": Q3_REVISION_ID}
    )
    with pytest.raises(RelationshipAdjudicationAuthorityError, match="anchored at S25"):
        analyze_composed_relationship_adjudication_authority_v1(
            root=root,
            world_id=ELDYRWILD_WORLD_ID,
            revision_id=Q3_REVISION_ID,
            historical_a=composed.historical_a,
            session25_descendant=bad_s25,
            verify_excerpt=False,
        )

    with pytest.raises(RelationshipAdjudicationAuthorityError):
        reject_naive_union_into_historical_a_anchor(
            root=root,
            world_id=ELDYRWILD_WORLD_ID,
            revision_id=Q3_REVISION_ID,
        )


@pytest.mark.skipif(not _eldyrwild_available(), reason="Eldyrwild world graph not present")
def test_composed_rejects_mixed_requested_revision_or_payload(
    tmp_path: Path,
) -> None:
    """Stale/mixed injected continuity reports must not compose as one authority."""
    root = _clone_eldyrwild_world(tmp_path)
    a_at_s25 = analyze_relationship_adjudication_continuity_v1(
        root=root,
        world_id=ELDYRWILD_WORLD_ID,
        revision_id=S25_REVISION_ID,
    )
    s25_at_q3 = analyze_session25_descendant_continuity_v1(
        root=root,
        world_id=ELDYRWILD_WORLD_ID,
        revision_id=Q3_REVISION_ID,
        verify_excerpt=False,
    )
    assert a_at_s25.requested_revision_id == S25_REVISION_ID
    assert s25_at_q3.requested_revision_id == Q3_REVISION_ID
    assert a_at_s25.campaign_id == ELDYRWILD_CAMPAIGN_ID
    assert s25_at_q3.world_id == ELDYRWILD_WORLD_ID

    with pytest.raises(
        RelationshipAdjudicationAuthorityError,
        match="historical A continuity requested_revision_id mismatch",
    ):
        analyze_composed_relationship_adjudication_authority_v1(
            root=root,
            world_id=ELDYRWILD_WORLD_ID,
            revision_id=Q3_REVISION_ID,
            historical_a=a_at_s25,
            session25_descendant=s25_at_q3,
            verify_excerpt=False,
        )

    coherent = analyze_composed_relationship_adjudication_authority_v1(
        root=root,
        world_id=ELDYRWILD_WORLD_ID,
        revision_id=Q3_REVISION_ID,
        verify_excerpt=False,
    )
    bad_payload_a = coherent.historical_a.model_copy(
        update={"requested_graph_payload_sha256": "0" * 64}
    )
    with pytest.raises(
        RelationshipAdjudicationAuthorityError,
        match="requested payloads disagree",
    ):
        analyze_composed_relationship_adjudication_authority_v1(
            root=root,
            world_id=ELDYRWILD_WORLD_ID,
            revision_id=Q3_REVISION_ID,
            historical_a=bad_payload_a,
            session25_descendant=coherent.session25_descendant,
            verify_excerpt=False,
        )

    bad_campaign = coherent.historical_a.model_copy(
        update={"campaign_id": "not-longmont-c2"}
    )
    with pytest.raises(
        RelationshipAdjudicationAuthorityError,
        match="historical A continuity campaign_id mismatch",
    ):
        analyze_composed_relationship_adjudication_authority_v1(
            root=root,
            world_id=ELDYRWILD_WORLD_ID,
            revision_id=Q3_REVISION_ID,
            historical_a=bad_campaign,
            session25_descendant=coherent.session25_descendant,
            verify_excerpt=False,
        )

    bad_world = coherent.session25_descendant.model_copy(
        update={"world_id": "spoof-world"}
    )
    with pytest.raises(
        RelationshipAdjudicationAuthorityError,
        match="S25 descendant continuity world_id mismatch",
    ):
        analyze_composed_relationship_adjudication_authority_v1(
            root=root,
            world_id=ELDYRWILD_WORLD_ID,
            revision_id=Q3_REVISION_ID,
            historical_a=coherent.historical_a,
            session25_descendant=bad_world,
            verify_excerpt=False,
        )


# ---------------------------------------------------------------------------
# T7 — effective inventory transition
# ---------------------------------------------------------------------------


@pytest.mark.skipif(not _eldyrwild_available(), reason="Eldyrwild world graph not present")
def test_t7_effective_inventory_transition_at_q3() -> None:
    """Q₃ remains the immutable pre-C₄ S25 transition point.

    The committed effective fixture is anchored to the current effective
    baseline (Q₄ after the C₄ live exit); this revision-pinned proof keeps the
    exact Q₃ composed-inventory transition inspectable forever.
    """
    root = _require_eldyrwild()
    report = analyze_relationship_effective_conformance_v1(
        root=root,
        world_id=ELDYRWILD_WORLD_ID,
        revision_id=Q3_REVISION_ID,
    )
    assert report.relationship_semantic_count == 367
    assert report.relationship_effectively_represented_count == 311
    assert report.relationship_effective_residual_count == 56
    assert report.uses_statblock_mechanics_count == 3
    assert report.unadjudicated_remaining_count == 0
    assert report.dungeonmind_owned_remaining_count == 0
    assert report.dungeonmindbuddy_owned_remaining_count == 56
    assert report.requires_readjudication_count == 0

    dispositions = {
        row.key: row.count for row in report.remaining_residual_disposition_inventory
    }
    assert dispositions == _EXPECTED_Q3_REMAINING_DISPOSITIONS
    assert set(EXACT_U7_EDGE_IDS) <= set(report.remaining_residual_edge_ids)
    assert "UNADJUDICATED" not in dispositions

    compact = compact_relationship_effective_conformance_report_v1(report)
    assert compact["source_revision_id"] == Q3_REVISION_ID
    committed = json.loads(EFFECTIVE_FIXTURE_PATH.read_text(encoding="utf-8"))
    assert committed["source_revision_id"] == Q4_REVISION_ID


@pytest.mark.skipif(not _eldyrwild_available(), reason="Eldyrwild world graph not present")
def test_t7b_effective_inventory_transition_at_q4() -> None:
    """Q₄ is the post-C₄ transition: X₄ resolved, U₁–U₆ still current residual."""
    root = _require_eldyrwild()
    report = analyze_relationship_effective_conformance_v1(
        root=root,
        world_id=ELDYRWILD_WORLD_ID,
        revision_id=Q4_REVISION_ID,
    )
    assert report.relationship_semantic_count == 366
    assert report.relationship_effectively_represented_count == 311
    assert report.relationship_effective_residual_count == 55
    assert report.uses_statblock_mechanics_count == 3
    assert report.unadjudicated_remaining_count == 0
    assert report.dungeonmind_owned_remaining_count == 0
    assert report.dungeonmindbuddy_owned_remaining_count == 55
    assert report.requires_readjudication_count == 0

    dispositions = {
        row.key: row.count for row in report.remaining_residual_disposition_inventory
    }
    assert dispositions == {
        "SOURCE_CORRECTION_REQUIRED": 36,
        "COMPOUND_ASSERTION_NOT_SINGLE_RELATIONSHIP": 11,
        "IDENTITY_NOT_RELATIONSHIP": 7,
        "INSUFFICIENT_EVIDENCE": 1,
    }
    assert set(EXACT_U7_EDGE_IDS[:6]) <= set(report.remaining_residual_edge_ids)
    assert EXACT_U7_EDGE_IDS[6] not in report.remaining_residual_edge_ids
    assert "UNADJUDICATED" not in dispositions

    compact = compact_relationship_effective_conformance_report_v1(report)
    committed = json.loads(EFFECTIVE_FIXTURE_PATH.read_text(encoding="utf-8"))
    assert compact == committed


# ---------------------------------------------------------------------------
# T8 — active_adjudicated_edge_ids stays historical 59
# ---------------------------------------------------------------------------


@pytest.mark.skipif(not _eldyrwild_available(), reason="Eldyrwild world graph not present")
def test_t8_active_adjudicated_edge_ids_remain_historical_59() -> None:
    root = _require_eldyrwild()
    report = analyze_relationship_effective_conformance_v1(
        root=root,
        world_id=ELDYRWILD_WORLD_ID,
        revision_id=Q3_REVISION_ID,
    )
    assert len(report.active_adjudicated_edge_ids) == 59
    assert set(report.active_adjudicated_edge_ids) == set(ELDYRWILD_RESIDUAL_FINDINGS)
    assert set(EXACT_U7_EDGE_IDS).isdisjoint(report.active_adjudicated_edge_ids)


# ---------------------------------------------------------------------------
# T9 — historical closed successor still forbidden
# ---------------------------------------------------------------------------


def test_t9_historical_closed_successor_forbidden_without_composed(
    tmp_path: Path,
) -> None:
    """A-era EXPLICIT_ADAPTER_CANDIDATE remaining residual fails closed."""
    store_r0 = load_union_supergraph_store(DEFAULT_FIXTURE_PATH)
    evid = "evidence:synth:seed"
    art = "artifact:synth:seed"
    store_r0.nodes["item:session17:seed"] = _node("item:session17:seed", "item")
    store_r0.nodes["pc:stafl"] = _node("pc:stafl", "pc")
    store_r0.evidence[evid] = _evidence(evid, art, "span:seed")
    store_r0.source_artifacts[art] = _artifact(art, "aa" * 32)
    store_r0.edges[_SEED_EDGE_ID] = _edge(
        _SEED_EDGE_ID,
        source="item:session17:seed",
        target="pc:stafl",
        predicate="located_in",
        evidence_ref_id=evid,
    )
    r0 = kernel.publish_world_revision(
        tmp_path, _SYNTH_WORLD, store_r0, operation_ids=["op:t9-r0"]
    ).revision.revision_id
    store_r1 = _clone_store(store_r0)
    store_r1.nodes["npc:unrelated"] = _node("npc:unrelated", "npc")
    r1 = kernel.publish_world_revision(
        tmp_path, _SYNTH_WORLD, store_r1, operation_ids=["op:t9-r1"]
    ).revision.revision_id

    finding = ELDYRWILD_RESIDUAL_FINDINGS[_SEED_EDGE_ID]
    assert finding.disposition == ResidualDisposition.EXPLICIT_ADAPTER_CANDIDATE
    seals = {
        _SEED_EDGE_ID: {
            "edge_id": _SEED_EDGE_ID,
            "primary_evidence_ref_id": evid,
            "source_artifact_id": art,
            "artifact_content_sha256": "aa" * 32,
            "source_span_ref_id": "span:seed",
            "locator_kind": "paragraph",
            "locator": "span:seed",
            "excerpt_sha256": "ee" * 32,
        }
    }
    continuity = _analyze_relationship_adjudication_continuity_with_authorities(
        root=tmp_path,
        world_id=_SYNTH_WORLD,
        revision_id=r1,
        findings={_SEED_EDGE_ID: finding},
        seals_by_edge=seals,
        anchor_world_id=_SYNTH_WORLD,
        anchor_revision_id=r0,
        anchor_payload_sha256="0" * 64,
        campaign_id=_SYNTH_CAMPAIGN,
        anchor_store=store_r0,
        requested_store=store_r1,
        requested_payload_sha256="1" * 64,
        verify_excerpt=False,
    )
    base = _base_report_v4(
        world_id=_SYNTH_WORLD,
        revision_id=r1,
        residual_edge_ids=[_SEED_EDGE_ID],
    )
    with pytest.raises(
        RelationshipEffectiveConformanceError,
        match="closed dispositions",
    ):
        _analyze_relationship_effective_conformance_with_authorities(
            root=tmp_path,
            world_id=_SYNTH_WORLD,
            revision_id=r1,
            base_report=base,
            continuity=continuity,
            catalog=_empty_catalog(revision_id=r0),
            store=store_r1,
        )


def test_t9_historical_closed_successor_forbidden_with_composed_a_authority(
    tmp_path: Path,
) -> None:
    """Composed path still forbids closed dispositions under historical-A authority."""
    store = load_union_supergraph_store(DEFAULT_FIXTURE_PATH)
    evid = "evidence:synth:seed-a"
    art = "artifact:synth:seed-a"
    store.nodes["item:session17:seed"] = _node("item:session17:seed", "item")
    store.nodes["pc:stafl"] = _node("pc:stafl", "pc")
    store.evidence[evid] = _evidence(evid, art, "span:seed")
    store.source_artifacts[art] = _artifact(art, "bb" * 32)
    store.edges[_SEED_EDGE_ID] = _edge(
        _SEED_EDGE_ID,
        source="item:session17:seed",
        target="pc:stafl",
        predicate="located_in",
        evidence_ref_id=evid,
    )
    r0 = kernel.publish_world_revision(
        tmp_path, _SYNTH_WORLD, store, operation_ids=["op:t9c-r0"]
    ).revision.revision_id
    store_r1 = _clone_store(store)
    store_r1.nodes["npc:mark"] = _node("npc:mark", "npc")
    r1 = kernel.publish_world_revision(
        tmp_path, _SYNTH_WORLD, store_r1, operation_ids=["op:t9c-r1"]
    ).revision.revision_id

    finding = ELDYRWILD_RESIDUAL_FINDINGS[_SEED_EDGE_ID]
    seals = {
        _SEED_EDGE_ID: {
            "edge_id": _SEED_EDGE_ID,
            "primary_evidence_ref_id": evid,
            "source_artifact_id": art,
            "artifact_content_sha256": "bb" * 32,
            "source_span_ref_id": "span:seed",
            "locator_kind": "paragraph",
            "locator": "span:seed",
            "excerpt_sha256": "ee" * 32,
        }
    }
    continuity = _analyze_relationship_adjudication_continuity_with_authorities(
        root=tmp_path,
        world_id=_SYNTH_WORLD,
        revision_id=r1,
        findings={_SEED_EDGE_ID: finding},
        seals_by_edge=seals,
        anchor_world_id=_SYNTH_WORLD,
        anchor_revision_id=r0,
        anchor_payload_sha256="0" * 64,
        campaign_id=_SYNTH_CAMPAIGN,
        anchor_store=store,
        requested_store=store_r1,
        requested_payload_sha256="1" * 64,
        verify_excerpt=False,
    )
    a_row = RelationshipAdjudicationAuthorityRowV1(
        edge_id=_SEED_EDGE_ID,
        authority_id=HISTORICAL_A_AUTHORITY_ID,
        anchor_revision_id=A_REVISION_ID,
        anchor_graph_payload_sha256=ELDYRWILD_PAYLOAD_SHA256,
        requested_revision_id=r1,
        continuity_state="CARRIED_FORWARD",
        source_grounding_verified=True,
        durable_shape_verified=True,
        disposition=finding.disposition.value,
        responsible_repo=finding.responsible_repo.value,
        next_action=finding.next_action.value,
        finding=finding,
        reason_code=finding.reason_code.value,
    )
    composed = RelationshipAdjudicationAuthorityReportV1(
        schema_version=RELATIONSHIP_ADJUDICATION_AUTHORITY_SCHEMA_V1,
        world_id=_SYNTH_WORLD,
        campaign_id=_SYNTH_CAMPAIGN,
        requested_revision_id=r1,
        requested_graph_payload_sha256="1" * 64,
        historical_a=continuity,
        session25_descendant=_empty_continuity(
            world_id=_SYNTH_WORLD,
            anchor_revision_id=S25_REVISION_ID,
            requested_revision_id=r1,
        ),
        rows=[a_row],
        historical_a_row_count=1,
        session25_descendant_row_count=0,
        composed_row_count=1,
    )
    base = _base_report_v4(
        world_id=_SYNTH_WORLD,
        revision_id=r1,
        residual_edge_ids=[_SEED_EDGE_ID],
    )
    with pytest.raises(
        RelationshipEffectiveConformanceError,
        match="closed dispositions",
    ):
        _analyze_relationship_effective_conformance_with_authorities(
            root=tmp_path,
            world_id=_SYNTH_WORLD,
            revision_id=r1,
            base_report=base,
            continuity=continuity,
            catalog=_empty_catalog(revision_id=r0),
            store=store_r1,
            composed_authority=composed,
        )


# ---------------------------------------------------------------------------
# T10 — open descendant candidate may remain residual
# ---------------------------------------------------------------------------


def test_t10_open_descendant_candidate_may_remain_residual(tmp_path: Path) -> None:
    """S25 open EXPLICIT_ADAPTER_CANDIDATE survives residual inventory without closed-A guard."""
    store = load_union_supergraph_store(DEFAULT_FIXTURE_PATH)
    evid = "evidence:synth:u7"
    art = "artifact:synth:u7"
    store.nodes["pc:ephanna"] = _node("pc:ephanna", "pc")
    store.nodes["node:thrin-branchborn"] = _node("node:thrin-branchborn", "npc")
    store.evidence[evid] = _evidence(evid, art, "span:u7")
    store.source_artifacts[art] = _artifact(art, "cc" * 32)
    store.edges[U7] = _edge(
        U7,
        source="pc:ephanna",
        target="node:thrin-branchborn",
        predicate="hires",
        evidence_ref_id=evid,
    )
    r0 = kernel.publish_world_revision(
        tmp_path, _SYNTH_WORLD, store, operation_ids=["op:t10-r0"]
    ).revision.revision_id

    continuity = _empty_continuity(
        world_id=_SYNTH_WORLD,
        anchor_revision_id=r0,
        requested_revision_id=r0,
    )
    open_candidate = _adapter(
        "dnd5e:employs",
        rationale=(
            "Synthetic open descendant candidate: future adapter work may map "
            "assignment semantics without treating this as a closed A-era successor."
        ),
    )
    assert open_candidate.disposition == ResidualDisposition.EXPLICIT_ADAPTER_CANDIDATE
    assert (
        open_candidate.disposition
        != ELDYRWILD_DESCENDANT_RESIDUAL_FINDINGS[U7].disposition
    )
    s25_row = RelationshipAdjudicationAuthorityRowV1(
        edge_id=U7,
        authority_id=SESSION25_DESCENDANT_AUTHORITY_ID,
        anchor_revision_id=S25_REVISION_ID,
        anchor_graph_payload_sha256=S25_PAYLOAD_SHA256,
        requested_revision_id=r0,
        continuity_state="CARRIED_FORWARD",
        source_grounding_verified=True,
        durable_shape_verified=True,
        disposition=open_candidate.disposition.value,
        responsible_repo=open_candidate.responsible_repo.value,
        next_action=open_candidate.next_action.value,
        finding=open_candidate,
        reason_code=open_candidate.reason_code.value,
    )
    composed = RelationshipAdjudicationAuthorityReportV1(
        schema_version=RELATIONSHIP_ADJUDICATION_AUTHORITY_SCHEMA_V1,
        world_id=_SYNTH_WORLD,
        campaign_id=_SYNTH_CAMPAIGN,
        requested_revision_id=r0,
        requested_graph_payload_sha256="1" * 64,
        historical_a=continuity,
        session25_descendant=continuity,
        rows=[s25_row],
        historical_a_row_count=0,
        session25_descendant_row_count=1,
        composed_row_count=1,
    )
    base = _base_report_v4(
        world_id=_SYNTH_WORLD,
        revision_id=r0,
        residual_edge_ids=[U7],
    )
    report = _analyze_relationship_effective_conformance_with_authorities(
        root=tmp_path,
        world_id=_SYNTH_WORLD,
        revision_id=r0,
        base_report=base,
        continuity=continuity,
        catalog=_empty_catalog(revision_id=r0),
        store=store,
        composed_authority=composed,
    )
    assert report.unadjudicated_remaining_count == 0
    assert report.relationship_effective_residual_count == 1
    assert report.relationship_effectively_represented_count == 0
    assert U7 in report.remaining_residual_edge_ids
    dispositions = {
        row.key: row.count for row in report.remaining_residual_disposition_inventory
    }
    assert "UNADJUDICATED" not in dispositions
    # Ownership must propagate the bound open-candidate finding, not static U7 SCR.
    assert dispositions == {
        ResidualDisposition.EXPLICIT_ADAPTER_CANDIDATE.value: 1,
    }
    assert report.dungeonmindbuddy_owned_remaining_count == 1
    assert report.dungeonmind_owned_remaining_count == 0
    assert s25_row.finding is open_candidate
    assert s25_row.disposition == open_candidate.disposition.value


# ---------------------------------------------------------------------------
# T11 — wrong world / payload / missing coverage fail closed
# ---------------------------------------------------------------------------


def test_t11_wrong_world_payload_and_coverage_fail_closed(tmp_path: Path) -> None:
    seals_payload = json.loads(DESCENDANT_SEALS_PATH.read_text(encoding="utf-8"))
    assert seals_payload["schema"] == DESCENDANT_RESIDUAL_SOURCE_SEALS_SCHEMA_V1

    # Wrong world on public descendant analyzer.
    with pytest.raises(
        RelationshipDescendantResidualAdjudicationError, match="world mismatch"
    ):
        analyze_eldyrwild_descendant_residual_adjudication_v1(
            root=tmp_path,
            world_id="not-eldyrwild",
            revision_id=S25_REVISION_ID,
            verify_excerpts=False,
        )

    # Analyzer is pinned to S25 — Q₃ is not a valid adjudication origin.
    with pytest.raises(
        RelationshipDescendantResidualAdjudicationError, match="pinned to S25"
    ):
        analyze_eldyrwild_descendant_residual_adjudication_v1(
            root=tmp_path,
            world_id=ELDYRWILD_WORLD_ID,
            revision_id=Q3_REVISION_ID,
            verify_excerpts=False,
        )

    # Wrong seals payload digest.
    bad_seals = dict(seals_payload)
    bad_seals["anchor_graph_payload_sha256"] = "0" * 64
    bad_path = tmp_path / "bad_seals.json"
    bad_path.write_text(json.dumps(bad_seals), encoding="utf-8")
    with pytest.raises(
        RelationshipDescendantResidualAdjudicationError,
        match="anchor_graph_payload_sha256",
    ):
        load_descendant_residual_source_seals(bad_path)

    # Missing U₇ edge in seals (sealed_count still claims 7 → coverage fail).
    missing = dict(seals_payload)
    missing["seals"] = [row for row in seals_payload["seals"] if row["edge_id"] != U7]
    missing_path = tmp_path / "missing_edge_seals.json"
    missing_path.write_text(json.dumps(missing), encoding="utf-8")
    with pytest.raises(
        RelationshipDescendantResidualAdjudicationError,
        match="seals length|exact U|sealed_count",
    ):
        load_descendant_residual_source_seals(missing_path)

    # S25 continuity rejects non-exact findings.
    with pytest.raises(RelationshipAdjudicationAuthorityError, match="exact U"):
        analyze_session25_descendant_continuity_v1(
            root=tmp_path,
            world_id=ELDYRWILD_WORLD_ID,
            revision_id=Q3_REVISION_ID,
            findings={U7: _source(rationale="only one", reason=ReasonCode.PREDICATE_MISAPPLIED)},
            seals_by_edge={},
            verify_excerpt=False,
        )

    # Composed authority rejects wrong world.
    with pytest.raises(RelationshipAdjudicationAuthorityError, match="world mismatch"):
        analyze_composed_relationship_adjudication_authority_v1(
            root=tmp_path,
            world_id="spoof-world",
            revision_id=Q3_REVISION_ID,
            verify_excerpt=False,
        )

    adjudication = json.loads(DESCENDANT_ADJUDICATION_PATH.read_text(encoding="utf-8"))
    assert adjudication["schema"] == DESCENDANT_RESIDUAL_ADJUDICATION_SCHEMA_V1
    assert adjudication["anchor_revision_id"] == S25_REVISION_ID
    assert adjudication["adjudicated_count"] == 7


# ---------------------------------------------------------------------------
# T12 — no canonical mutation
# ---------------------------------------------------------------------------


@pytest.mark.skipif(not _eldyrwild_available(), reason="Eldyrwild world graph not present")
def test_t12_no_canonical_world_mutation() -> None:
    root = _require_eldyrwild()
    before_head = open_world_graph_head(root, ELDYRWILD_WORLD_ID).head_revision_id
    before_tree = snapshot_world_graph_tree_digest(root, ELDYRWILD_WORLD_ID)

    _ = analyze_eldyrwild_descendant_residual_adjudication_v1(root=root)
    _ = analyze_session25_descendant_continuity_v1(
        root=root,
        world_id=ELDYRWILD_WORLD_ID,
        revision_id=S25_REVISION_ID,
    )
    _ = analyze_session25_descendant_continuity_v1(
        root=root,
        world_id=ELDYRWILD_WORLD_ID,
        revision_id=Q3_REVISION_ID,
    )
    _ = analyze_composed_relationship_adjudication_authority_v1(
        root=root,
        world_id=ELDYRWILD_WORLD_ID,
        revision_id=Q3_REVISION_ID,
    )
    _ = analyze_relationship_effective_conformance_v1(
        root=root,
        world_id=ELDYRWILD_WORLD_ID,
        revision_id=Q3_REVISION_ID,
    )
    with pytest.raises(RelationshipAdjudicationAuthorityError):
        reject_naive_union_into_historical_a_anchor(
            root=root,
            world_id=ELDYRWILD_WORLD_ID,
            revision_id=Q3_REVISION_ID,
        )

    assert open_world_graph_head(root, ELDYRWILD_WORLD_ID).head_revision_id == before_head
    assert snapshot_world_graph_tree_digest(root, ELDYRWILD_WORLD_ID) == before_tree
    assert before_head == Q4_REVISION_ID
