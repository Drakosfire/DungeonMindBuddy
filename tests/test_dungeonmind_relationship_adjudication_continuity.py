"""Adjudication continuity across Eldyrwild descendant World Graph revisions."""

from __future__ import annotations

import inspect
import json
from pathlib import Path
from typing import Any

import pytest

import graph_memory.kernel as kernel
from apps.live_control_server.config import world_graph_root
from apps.live_control_server.integrations.dungeonmind_kernel.relationship_adjudication_continuity_v1 import (
    RELATIONSHIP_ADJUDICATION_CONTINUITY_SCHEMA_V1,
    _analyze_relationship_adjudication_continuity_with_authorities,
    analyze_relationship_adjudication_continuity_v1,
    compact_relationship_adjudication_continuity_report_v1,
    continuity_active_edge_ids_v1,
    prove_revision_is_anchor_or_descendant_v1,
)
from apps.live_control_server.integrations.dungeonmind_kernel.relationship_residual_adjudication import (
    ELDYRWILD_PAYLOAD_SHA256,
    ELDYRWILD_RESIDUAL_FINDINGS,
    ELDYRWILD_REVISION_ID,
    ELDYRWILD_WORLD_ID,
    AdjudicationFinding,
    NextAction,
    ReasonCode,
    ResidualDisposition,
    ResponsibleRepo,
    load_residual_source_seals,
)
from apps.live_control_server.integrations.dungeonmind_kernel.whole_world_conformance import (
    snapshot_world_graph_tree_digest,
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
CONTINUITY_FIXTURE_PATH = (
    FIXTURES / "eldyrwild_relationship_adjudication_continuity_v1.json"
)
ADJUDICATION_FIXTURE_PATH = (
    FIXTURES / "eldyrwild_relationship_residual_adjudication_v1.json"
)

SYNTH_WORLD = "continuity-synth"
SYNTH_CAMPAIGN = "synth-campaign"
_EDGE_A = "edge:synth:a:located_in:loc:a"
_EDGE_B = "edge:synth:b:threatens:npc:b"
_EDGE_C = "edge:synth:c:same_as:npc:c"

_EVID_A = "evidence:synth:a"
_EVID_B = "evidence:synth:b"
_EVID_C = "evidence:synth:c"
_ART_A = "artifact:synth:a"
_ART_B = "artifact:synth:b"
_ART_C = "artifact:synth:c"
_SHA_A = "a" * 64
_SHA_B = "b" * 64
_SHA_C = "c" * 64


def _finding(
    disposition: ResidualDisposition,
    *,
    next_action: NextAction = NextAction.AUTHOR_BUDDY_SOURCE_CORRECTION,
    reason: ReasonCode = ReasonCode.PREDICATE_MISAPPLIED,
) -> AdjudicationFinding:
    return AdjudicationFinding(
        disposition=disposition,
        reason_code=reason,
        responsible_repo=ResponsibleRepo.DUNGEONMINDBUDDY,
        next_action=next_action,
        rationale="synthetic continuity finding",
    )


def _synth_findings() -> dict[str, AdjudicationFinding]:
    return {
        _EDGE_A: _finding(ResidualDisposition.SOURCE_CORRECTION_REQUIRED),
        _EDGE_B: _finding(
            ResidualDisposition.SOURCE_CORRECTION_REQUIRED,
            reason=ReasonCode.DIRECTION_CONTRADICTION,
        ),
        _EDGE_C: _finding(
            ResidualDisposition.IDENTITY_NOT_RELATIONSHIP,
            next_action=NextAction.MIGRATE_VIA_IDENTITY_SEAM,
            reason=ReasonCode.IDENTITY_EQUIVALENCE,
        ),
    }


def _synth_seals() -> dict[str, dict[str, Any]]:
    return {
        _EDGE_A: {
            "edge_id": _EDGE_A,
            "primary_evidence_ref_id": _EVID_A,
            "source_artifact_id": _ART_A,
            "artifact_content_sha256": _SHA_A,
            "source_span_ref_id": "span:a",
            "locator_kind": "paragraph",
            "locator": "paragraph:001",
            "excerpt_sha256": "aa" * 32,
        },
        _EDGE_B: {
            "edge_id": _EDGE_B,
            "primary_evidence_ref_id": _EVID_B,
            "source_artifact_id": _ART_B,
            "artifact_content_sha256": _SHA_B,
            "source_span_ref_id": "span:b",
            "locator_kind": "paragraph",
            "locator": "paragraph:002",
            "excerpt_sha256": "bb" * 32,
        },
        _EDGE_C: {
            "edge_id": _EDGE_C,
            "primary_evidence_ref_id": _EVID_C,
            "source_artifact_id": _ART_C,
            "artifact_content_sha256": _SHA_C,
            "source_span_ref_id": "span:c",
            "locator_kind": "paragraph",
            "locator": "paragraph:003",
            "excerpt_sha256": "cc" * 32,
        },
    }


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
        campaign_id=SYNTH_CAMPAIGN,
        uri=f"repo://synth/{artifact_id}",
        content_sha256=sha,
        status="active",
    )


def _synth_store() -> UnionSupergraphStore:
    store = load_union_supergraph_store(DEFAULT_FIXTURE_PATH)
    nodes = {
        "npc:a": _node("npc:a", "npc"),
        "loc:a": _node("loc:a", "location"),
        "npc:b_src": _node("npc:b_src", "npc"),
        "npc:b": _node("npc:b", "npc"),
        "npc:c_src": _node("npc:c_src", "npc"),
        "npc:c": _node("npc:c", "npc"),
    }
    edges = {
        _EDGE_A: _edge(
            _EDGE_A,
            source="npc:a",
            target="loc:a",
            predicate="located_in",
            evidence_ref_id=_EVID_A,
        ),
        _EDGE_B: _edge(
            _EDGE_B,
            source="npc:b_src",
            target="npc:b",
            predicate="threatens",
            evidence_ref_id=_EVID_B,
        ),
        _EDGE_C: _edge(
            _EDGE_C,
            source="npc:c_src",
            target="npc:c",
            predicate="same_as",
            evidence_ref_id=_EVID_C,
        ),
    }
    evidence = {
        _EVID_A: _evidence(_EVID_A, _ART_A, "span:a"),
        _EVID_B: _evidence(_EVID_B, _ART_B, "span:b"),
        _EVID_C: _evidence(_EVID_C, _ART_C, "span:c"),
    }
    artifacts = {
        _ART_A: _artifact(_ART_A, _SHA_A),
        _ART_B: _artifact(_ART_B, _SHA_B),
        _ART_C: _artifact(_ART_C, _SHA_C),
    }
    store.nodes.update(nodes)
    store.edges.update(edges)
    store.evidence.update(evidence)
    store.source_artifacts.update(artifacts)
    return store


def _clone_store(store: UnionSupergraphStore) -> UnionSupergraphStore:
    return UnionSupergraphStore.model_validate(
        store.model_dump(mode="python", by_alias=True)
    )

def _publish_store(root: Path, world_id: str, store: UnionSupergraphStore, op: str) -> str:
    result = kernel.publish_world_revision(
        root,
        world_id,
        store,
        operation_ids=[op],
    )
    revision_id = result.revision.revision_id
    assert revision_id
    return revision_id


def _analyze_synth(
    *,
    root: Path,
    revision_id: str,
    anchor_revision_id: str,
    anchor_store: UnionSupergraphStore,
    requested_store: UnionSupergraphStore | None = None,
    world_id: str = SYNTH_WORLD,
) -> Any:
    return _analyze_relationship_adjudication_continuity_with_authorities(
        root=root,
        world_id=world_id,
        revision_id=revision_id,
        findings=_synth_findings(),
        seals_by_edge=_synth_seals(),
        anchor_world_id=SYNTH_WORLD,
        anchor_revision_id=anchor_revision_id,
        anchor_payload_sha256="0" * 64,
        campaign_id=SYNTH_CAMPAIGN,
        anchor_store=anchor_store,
        requested_store=requested_store,
        requested_payload_sha256="1" * 64,
        verify_excerpt=False,
    )


def test_public_api_rejects_caller_supplied_semantic_authority() -> None:
    sig = inspect.signature(analyze_relationship_adjudication_continuity_v1)
    assert "findings" not in sig.parameters
    assert "seals_by_edge" not in sig.parameters
    assert "anchor_store" not in sig.parameters
    assert "catalog" not in sig.parameters
    with pytest.raises(TypeError):
        analyze_relationship_adjudication_continuity_v1(  # type: ignore[call-arg]
            root=Path("/tmp"),
            world_id="eldyrwild",
            revision_id=ELDYRWILD_REVISION_ID,
            findings={},
        )


def test_continuity_anchor_ids_match_adjudication_fixture() -> None:
    adjudication = json.loads(ADJUDICATION_FIXTURE_PATH.read_text(encoding="utf-8"))
    fixture_ids = sorted(record["edge_id"] for record in adjudication["records"])
    runtime_ids = sorted(ELDYRWILD_RESIDUAL_FINDINGS)
    assert len(runtime_ids) == 59
    assert fixture_ids == runtime_ids
    seals = load_residual_source_seals()
    assert sorted(seals) == runtime_ids


def test_committed_eldyrwild_continuity_fixture_is_durable_regression_contract() -> None:
    payload = json.loads(CONTINUITY_FIXTURE_PATH.read_text(encoding="utf-8"))
    assert payload["schema_version"] == RELATIONSHIP_ADJUDICATION_CONTINUITY_SCHEMA_V1
    assert payload["world_id"] == ELDYRWILD_WORLD_ID
    assert payload["anchor_revision_id"] == ELDYRWILD_REVISION_ID
    assert payload["requested_revision_id"] == ELDYRWILD_REVISION_ID
    assert payload["anchor_graph_payload_sha256"] == ELDYRWILD_PAYLOAD_SHA256
    assert payload["anchor_is_ancestor"] is True
    assert payload["anchor_finding_count"] == 59
    assert payload["anchor_count"] == 59
    assert payload["carried_forward_count"] == 0
    assert payload["requires_readjudication_count"] == 0
    assert payload["invalidated_edge_change_count"] == 0
    assert payload["invalidated_source_change_count"] == 0
    assert payload["removed_edge_count"] == 0
    row_ids = sorted(row["edge_id"] for row in payload["rows"])
    assert row_ids == sorted(ELDYRWILD_RESIDUAL_FINDINGS)
    assert all(row["continuity_state"] == "ANCHOR" for row in payload["rows"])
    assert all(row["source_grounding_verified"] for row in payload["rows"])
    assert all(row["durable_shape_verified"] for row in payload["rows"])


def test_descendant_carry_forward_and_edge_change_and_removal(tmp_path: Path) -> None:
    store_r0 = _synth_store()
    r0 = _publish_store(tmp_path, SYNTH_WORLD, store_r0, "op:r0")

    # R1: unrelated durable change (extra node) — edges unchanged.
    store_r1 = _clone_store(store_r0)
    store_r1.nodes["npc:unrelated"] = _node("npc:unrelated", "npc")
    r1 = _publish_store(tmp_path, SYNTH_WORLD, store_r1, "op:r1")

    report_r1 = _analyze_synth(
        root=tmp_path,
        revision_id=r1,
        anchor_revision_id=r0,
        anchor_store=store_r0,
        requested_store=store_r1,
    )
    assert report_r1.anchor_is_ancestor is True
    assert report_r1.carried_forward_count == 3
    assert report_r1.invalidated_edge_change_count == 0
    assert {row.continuity_state for row in report_r1.rows} == {"CARRIED_FORWARD"}

    # R2: change one adjudicated edge predicate.
    store_r2 = _clone_store(store_r1)
    store_r2.edges[_EDGE_B] = _edge(
        _EDGE_B,
        source="npc:b_src",
        target="npc:b",
        predicate="serves",
        evidence_ref_id=_EVID_B,
    )
    r2 = _publish_store(tmp_path, SYNTH_WORLD, store_r2, "op:r2")
    report_r2 = _analyze_synth(
        root=tmp_path,
        revision_id=r2,
        anchor_revision_id=r0,
        anchor_store=store_r0,
        requested_store=store_r2,
    )
    by_id = {row.edge_id: row for row in report_r2.rows}
    assert by_id[_EDGE_B].continuity_state == "INVALIDATED_BY_EDGE_CHANGE"
    assert by_id[_EDGE_A].continuity_state == "CARRIED_FORWARD"
    assert by_id[_EDGE_C].continuity_state == "CARRIED_FORWARD"
    assert report_r2.invalidated_edge_change_count == 1
    assert report_r2.carried_forward_count == 2

    # R3: remove one adjudicated edge.
    store_r3 = _clone_store(store_r2)
    del store_r3.edges[_EDGE_A]
    r3 = _publish_store(tmp_path, SYNTH_WORLD, store_r3, "op:r3")
    report_r3 = _analyze_synth(
        root=tmp_path,
        revision_id=r3,
        anchor_revision_id=r0,
        anchor_store=store_r0,
        requested_store=store_r3,
    )
    by_id = {row.edge_id: row for row in report_r3.rows}
    assert by_id[_EDGE_A].continuity_state == "EDGE_REMOVED"
    assert by_id[_EDGE_B].continuity_state == "INVALIDATED_BY_EDGE_CHANGE"
    assert by_id[_EDGE_C].continuity_state == "CARRIED_FORWARD"
    assert report_r3.removed_edge_count == 1


def test_source_drift_invalidates_even_when_edge_shape_identical(tmp_path: Path) -> None:
    store_r0 = _synth_store()
    r0 = _publish_store(tmp_path, SYNTH_WORLD, store_r0, "op:r0-source")
    store_r1 = _clone_store(store_r0)
    # Keep edge shape; change sealed artifact digest.
    store_r1.source_artifacts[_ART_A] = _artifact(_ART_A, "f" * 64)
    r1 = _publish_store(tmp_path, SYNTH_WORLD, store_r1, "op:r1-source")
    report = _analyze_synth(
        root=tmp_path,
        revision_id=r1,
        anchor_revision_id=r0,
        anchor_store=store_r0,
        requested_store=store_r1,
    )
    by_id = {row.edge_id: row for row in report.rows}
    assert by_id[_EDGE_A].continuity_state == "INVALIDATED_BY_SOURCE_CHANGE"
    assert by_id[_EDGE_A].diagnostic == "SOURCE_GROUNDING_DRIFT"
    assert by_id[_EDGE_B].continuity_state == "CARRIED_FORWARD"
    assert by_id[_EDGE_C].continuity_state == "CARRIED_FORWARD"


def test_sibling_fork_does_not_inherit_adjudication(tmp_path: Path) -> None:
    """B is a sibling of the anchor (shares a pre-anchor parent), not a descendant."""
    store_pre = _synth_store()
    store_pre.nodes["npc:pre"] = _node("npc:pre", "npc")
    r_pre = _publish_store(tmp_path, SYNTH_WORLD, store_pre, "op:fork-pre")

    store_r0 = _clone_store(store_pre)
    store_r0.nodes["npc:anchor-mark"] = _node("npc:anchor-mark", "npc")
    r0 = _publish_store(tmp_path, SYNTH_WORLD, store_r0, "op:fork-r0")

    store_a = _clone_store(store_r0)
    store_a.nodes["npc:branch-a"] = _node("npc:branch-a", "npc")
    r_a = _publish_store(tmp_path, SYNTH_WORLD, store_a, "op:fork-a")

    # Repoint head to pre-anchor parent and publish sibling B of the anchor.
    kernel.rollback_world_graph_head(tmp_path, SYNTH_WORLD, r_pre)
    store_b = _clone_store(store_pre)
    store_b.nodes["npc:branch-b"] = _node("npc:branch-b", "npc")
    # Ensure identical adjudicated edge IDs exist on B.
    assert _EDGE_A in store_b.edges
    r_b = _publish_store(tmp_path, SYNTH_WORLD, store_b, "op:fork-b")

    ok_a, _, _ = prove_revision_is_anchor_or_descendant_v1(
        root=tmp_path,
        world_id=SYNTH_WORLD,
        requested_revision_id=r_a,
        anchor_revision_id=r0,
    )
    ok_b, diag_b, _ = prove_revision_is_anchor_or_descendant_v1(
        root=tmp_path,
        world_id=SYNTH_WORLD,
        requested_revision_id=r_b,
        anchor_revision_id=r0,
    )
    assert ok_a is True
    assert ok_b is False
    assert diag_b == "ANCESTRY_UNPROVEN"

    report_a = _analyze_synth(
        root=tmp_path,
        revision_id=r_a,
        anchor_revision_id=r0,
        anchor_store=store_r0,
        requested_store=store_a,
    )
    assert report_a.carried_forward_count == 3

    report_b = _analyze_synth(
        root=tmp_path,
        revision_id=r_b,
        anchor_revision_id=r0,
        anchor_store=store_r0,
        requested_store=store_b,
    )
    assert report_b.anchor_is_ancestor is False
    assert report_b.carried_forward_count == 0
    assert report_b.not_descendant_count == 3
    assert all(row.continuity_state == "NOT_DESCENDANT" for row in report_b.rows)

def test_different_world_receives_zero_carried_adjudications(tmp_path: Path) -> None:
    store = _synth_store()
    r0 = _publish_store(tmp_path, "other-world", store, "op:other")
    report = analyze_relationship_adjudication_continuity_v1(
        root=tmp_path,
        world_id="other-world",
        revision_id=r0,
    )
    assert report.carried_forward_count == 0
    assert report.anchor_count == 0
    assert report.not_descendant_count == 59
    assert all(row.continuity_state == "NOT_DESCENDANT" for row in report.rows)
    assert all(row.diagnostic == "WORLD_MISMATCH" for row in report.rows)


def test_eldyrwild_continuity_integration_when_present() -> None:
    root = world_graph_root()
    eldyrwild = root / "graph_memory" / "worlds" / "eldyrwild"
    if not eldyrwild.is_dir():
        pytest.skip("Eldyrwild world graph not present")
    before = snapshot_world_graph_tree_digest(root, ELDYRWILD_WORLD_ID)
    report = analyze_relationship_adjudication_continuity_v1(
        root=root,
        world_id=ELDYRWILD_WORLD_ID,
        revision_id=ELDYRWILD_REVISION_ID,
    )
    after = snapshot_world_graph_tree_digest(root, ELDYRWILD_WORLD_ID)
    assert before == after
    compact = compact_relationship_adjudication_continuity_report_v1(report)
    committed = json.loads(CONTINUITY_FIXTURE_PATH.read_text(encoding="utf-8"))
    assert compact == committed
    assert len(continuity_active_edge_ids_v1(report)) == 59
