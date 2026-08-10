"""Governed Eldyrwild Lysandra threat-direction correction proofs."""

from __future__ import annotations

import hashlib
import json
import os
import shutil
from pathlib import Path
from typing import Any

import pytest

import graph_memory.kernel as kernel
from apps.live_control_server.config import world_graph_root
from apps.live_control_server.integrations.dungeonmind_kernel.relationship_effective_conformance_v1 import (
    analyze_relationship_effective_conformance_v1,
)
from apps.live_control_server.integrations.dungeonmind_kernel.relationship_residual_adjudication import (
    ELDYRWILD_REVISION_ID,
    ELDYRWILD_WORLD_ID,
)
from apps.live_control_server.integrations.dungeonmind_kernel.whole_world_conformance import (
    snapshot_world_graph_tree_digest,
)
from apps.live_control_server.services.eldyrwild_lysandra_threat_direction_correction import (
    APPROVED_CORRECTION_RELPATH,
    CAMPAIGN_ID,
    LOCKED_CORRECTION_CONTRIBUTION_ID,
    LOCKED_CORRECTION_SOURCE_PAYLOAD_SHA256,
    LOCKED_SOURCE_ARTIFACT_ID,
    REPLACEMENT_ASSERTION_ID,
    REPLACEMENT_EDGE_ID,
    REPLACEMENT_PREDICATE,
    REPLACEMENT_SOURCE_NODE_ID,
    REPLACEMENT_TARGET_NODE_ID,
    TARGET_ASSERTION_ID,
    TARGET_CONTRIBUTION_ID,
    TARGET_EDGE_ID,
    TARGET_PREDICATE,
    TARGET_SOURCE_NODE_ID,
    TARGET_TARGET_NODE_ID,
    LysandraThreatDirectionCorrectionError,
    apply_lysandra_threat_direction_correction,
    get_lysandra_threat_direction_correction_status,
    load_approved_lysandra_threat_direction_correction,
)
from graph_memory.projection.world_projection import (
    PROJECTION_REQUEST_SCHEMA,
    WorldGraphProjectionFocus,
    WorldGraphProjectionRequest,
)
from graph_memory.union_supergraph.model import UnionSupergraphNode

REPO = Path(__file__).resolve().parents[1]
SOURCE_SEAL_PATH = (
    REPO
    / "tests/fixtures/dungeonmind_kernel/eldyrwild_relationship_residual_source_seals_v1.json"
)
ADJUDICATION_PATH = (
    REPO
    / "tests/fixtures/dungeonmind_kernel/eldyrwild_relationship_residual_adjudication_v1.json"
)
BASELINE_REBUILD_DIGEST_MISMATCH_CONTRIBUTION = "contribution:d3d244474789879c"


def _clone_eldyrwild(tmp_path: Path) -> Path:
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


def _project(root: Path, revision_id: str):
    return kernel.project_world_graph(
        root,
        WorldGraphProjectionRequest(
            schema=PROJECTION_REQUEST_SCHEMA,
            world_id=ELDYRWILD_WORLD_ID,
            campaign_id=CAMPAIGN_ID,
            focus=WorldGraphProjectionFocus(kind="none"),
            admissibility="gm",
            revision_pin=revision_id,
            scope_mode="campaign",
        ),
    )


def _sibling_support_fingerprint(store: Any) -> dict[str, dict[str, Any]]:
    rows: dict[str, dict[str, Any]] = {}
    for assertion_id, support in store.assertion_support.items():
        if not isinstance(support, dict):
            continue
        related = set(support.get("active_contribution_ids") or [])
        related |= set(support.get("contradicted_contribution_ids") or [])
        related |= set(support.get("superseded_contribution_ids") or [])
        related |= set(support.get("retracted_contribution_ids") or [])
        if support.get("introduced_by_contribution_id") == TARGET_CONTRIBUTION_ID:
            related.add(TARGET_CONTRIBUTION_ID)
        per_ev = support.get("per_contribution_evidence_ref_ids") or {}
        if TARGET_CONTRIBUTION_ID in related or TARGET_CONTRIBUTION_ID in per_ev:
            rows[assertion_id] = {
                key: support.get(key) for key in sorted(support.keys())
            }
    return rows


def _file_sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def test_approved_correction_artifact_locks_identity_and_target() -> None:
    contribution = load_approved_lysandra_threat_direction_correction(repo=REPO)
    digest = kernel.compute_contribution_source_payload_sha256(contribution)
    assert contribution.contribution_id == LOCKED_CORRECTION_CONTRIBUTION_ID
    assert digest == LOCKED_CORRECTION_SOURCE_PAYLOAD_SHA256
    assert len(contribution.accepted_assertions) == 1
    assert len(contribution.assertion_corrections) == 1
    link = contribution.assertion_corrections[0]
    assert link.target_contribution_id == TARGET_CONTRIBUTION_ID
    assert link.target_assertion_id == TARGET_ASSERTION_ID
    assert link.replacement_assertion_id == REPLACEMENT_ASSERTION_ID
    replacement = contribution.accepted_assertions[0]
    assert replacement.assertion_id == REPLACEMENT_ASSERTION_ID
    assert replacement.subject_node_id == REPLACEMENT_SOURCE_NODE_ID
    assert replacement.target_node_id == REPLACEMENT_TARGET_NODE_ID
    assert replacement.predicate == REPLACEMENT_PREDICATE
    assert replacement.campaign_scope == CAMPAIGN_ID
    value = replacement.value if isinstance(replacement.value, dict) else {}
    assert value.get("edge_id") == REPLACEMENT_EDGE_ID
    artifacts = value.get("source_artifacts") or []
    assert artifacts and artifacts[0].get("campaign_id") == CAMPAIGN_ID


def test_tampered_correction_artifact_fails_closed(tmp_path: Path) -> None:
    src = REPO / APPROVED_CORRECTION_RELPATH
    dst_repo = tmp_path / "repo"
    dst = dst_repo / APPROVED_CORRECTION_RELPATH
    dst.parent.mkdir(parents=True)
    payload = json.loads(src.read_text(encoding="utf-8"))
    payload["authored_by"] = "not-gm"
    dst.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")
    with pytest.raises(LysandraThreatDirectionCorrectionError) as exc:
        load_approved_lysandra_threat_direction_correction(repo=dst_repo)
    assert exc.value.code == "correction_artifact_tampered"


def test_real_clone_status_is_eligible(tmp_path: Path) -> None:
    root = _clone_eldyrwild(tmp_path)
    status = get_lysandra_threat_direction_correction_status(root=root, repo=REPO)
    assert status.eligibility == "eligible"
    assert status.head_revision_id
    assert status.continuity_state in {"ANCHOR", "CARRIED_FORWARD"}
    assert status.source_grounding_verified is True
    assert status.durable_shape_verified is True
    assert status.target_edge_id == TARGET_EDGE_ID
    assert status.correction_contribution_id == LOCKED_CORRECTION_CONTRIBUTION_ID


def test_stale_parent_fails_closed(tmp_path: Path) -> None:
    root = _clone_eldyrwild(tmp_path)
    status = get_lysandra_threat_direction_correction_status(root=root, repo=REPO)
    parent = status.head_revision_id
    assert parent
    store = kernel.load_world_graph_revision(root, ELDYRWILD_WORLD_ID, parent)
    store.nodes["npc:lysandra-stale-probe"] = UnionSupergraphNode(
        node_id="npc:lysandra-stale-probe",
        label="stale probe",
        kind="npc",
        role="probe",
        aliases=[],
        source_domains=["manual_seed"],
        evidence_ref_ids=[],
        state={},
    )
    advanced = kernel.publish_world_revision(
        root,
        ELDYRWILD_WORLD_ID,
        store,
        operation_ids=["op:lysandra-stale-parent-probe"],
    ).revision.revision_id
    assert advanced != parent
    with pytest.raises(LysandraThreatDirectionCorrectionError) as exc:
        apply_lysandra_threat_direction_correction(
            expected_parent_revision_id=parent,
            root=root,
            repo=REPO,
        )
    assert exc.value.code == "ineligible_parent"
    head, _, _ = kernel.open_current_world_graph(root, ELDYRWILD_WORLD_ID)
    assert head.head_revision_id == advanced


def test_real_clone_apply_preserves_history_and_parent_relative_conformance(
    tmp_path: Path,
) -> None:
    root = _clone_eldyrwild(tmp_path)
    seal_before = _file_sha256(SOURCE_SEAL_PATH)
    adj_before = _file_sha256(ADJUDICATION_PATH)

    status = get_lysandra_threat_direction_correction_status(root=root, repo=REPO)
    assert status.eligibility == "eligible"
    parent = status.head_revision_id
    assert parent

    # Baseline: full-world rebuild already fails on this Eldyrwild store.
    with pytest.raises(ValueError, match=BASELINE_REBUILD_DIGEST_MISMATCH_CONTRIBUTION):
        kernel.rebuild_from_contributions(
            root,
            world_id=ELDYRWILD_WORLD_ID,
            compare_revision_id=parent,
            publish=False,
        )

    store_p = kernel.load_world_graph_revision(root, ELDYRWILD_WORLD_ID, parent)
    siblings_p = _sibling_support_fingerprint(store_p)
    assert TARGET_ASSERTION_ID in siblings_p
    assert store_p.assertion_support[TARGET_ASSERTION_ID]["support_state"] == "supported"

    before_p = snapshot_world_graph_tree_digest(root, ELDYRWILD_WORLD_ID)
    eff_p = analyze_relationship_effective_conformance_v1(
        root=root, world_id=ELDYRWILD_WORLD_ID, revision_id=parent
    )
    assert snapshot_world_graph_tree_digest(root, ELDYRWILD_WORLD_ID) == before_p
    assert TARGET_EDGE_ID in eff_p.remaining_residual_edge_ids

    proj_p = _project(root, parent)
    rels_p = {rel.edge_id: rel for rel in proj_p.relationships}
    assert TARGET_EDGE_ID in rels_p
    assert REPLACEMENT_EDGE_ID not in rels_p
    assert rels_p[TARGET_EDGE_ID].source_node_id == TARGET_SOURCE_NODE_ID
    assert rels_p[TARGET_EDGE_ID].target_node_id == TARGET_TARGET_NODE_ID
    assert rels_p[TARGET_EDGE_ID].predicate == TARGET_PREDICATE

    result = apply_lysandra_threat_direction_correction(
        expected_parent_revision_id=parent,
        root=root,
        repo=REPO,
    )
    assert result.published is True
    assert result.parent_revision_id == parent
    child = result.revision_id
    assert child and child != parent

    store_q = kernel.load_world_graph_revision(root, ELDYRWILD_WORLD_ID, child)
    assert TARGET_EDGE_ID in store_q.edges  # durable history retained
    x_support = store_q.assertion_support[TARGET_ASSERTION_ID]
    assert x_support["support_state"] == "contradicted"
    assert TARGET_CONTRIBUTION_ID in (x_support.get("contradicted_contribution_ids") or [])
    assert not (x_support.get("active_contribution_ids") or [])
    xp_support = store_q.assertion_support[REPLACEMENT_ASSERTION_ID]
    assert xp_support["support_state"] == "supported"
    assert LOCKED_CORRECTION_CONTRIBUTION_ID in (
        xp_support.get("active_contribution_ids") or []
    )
    xp_edge = store_q.edges[REPLACEMENT_EDGE_ID]
    assert xp_edge.source_node_id == REPLACEMENT_SOURCE_NODE_ID
    assert xp_edge.target_node_id == REPLACEMENT_TARGET_NODE_ID
    assert xp_edge.predicate == REPLACEMENT_PREDICATE
    artifact = store_q.source_artifacts[LOCKED_SOURCE_ARTIFACT_ID]
    assert artifact.campaign_id == CAMPAIGN_ID

    siblings_q = _sibling_support_fingerprint(store_q)
    for assertion_id, before_row in siblings_p.items():
        if assertion_id == TARGET_ASSERTION_ID:
            continue
        assert siblings_q.get(assertion_id) == before_row

    # Old parent remains historical truth.
    store_p_after = kernel.load_world_graph_revision(root, ELDYRWILD_WORLD_ID, parent)
    assert (
        store_p_after.assertion_support[TARGET_ASSERTION_ID]["support_state"]
        == "supported"
    )
    proj_p_after = _project(root, parent)
    rels_p_after = {rel.edge_id: rel for rel in proj_p_after.relationships}
    assert TARGET_EDGE_ID in rels_p_after
    assert REPLACEMENT_EDGE_ID not in rels_p_after

    proj_q = _project(root, child)
    rels_q = {rel.edge_id: rel for rel in proj_q.relationships}
    assert TARGET_EDGE_ID not in rels_q
    assert REPLACEMENT_EDGE_ID in rels_q
    assert rels_q[REPLACEMENT_EDGE_ID].source_node_id == REPLACEMENT_SOURCE_NODE_ID
    assert rels_q[REPLACEMENT_EDGE_ID].target_node_id == REPLACEMENT_TARGET_NODE_ID
    assert rels_q[REPLACEMENT_EDGE_ID].predicate == REPLACEMENT_PREDICATE

    before_q = snapshot_world_graph_tree_digest(root, ELDYRWILD_WORLD_ID)
    eff_q = analyze_relationship_effective_conformance_v1(
        root=root, world_id=ELDYRWILD_WORLD_ID, revision_id=child
    )
    assert snapshot_world_graph_tree_digest(root, ELDYRWILD_WORLD_ID) == before_q
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
    assert TARGET_EDGE_ID not in eff_q.remaining_residual_edge_ids
    assert REPLACEMENT_EDGE_ID not in eff_q.remaining_residual_edge_ids

    # Exact retry is idempotent.
    retry = apply_lysandra_threat_direction_correction(
        expected_parent_revision_id=child,
        root=root,
        repo=REPO,
    )
    assert retry.published is False
    assert retry.revision_id == child
    head, _, _ = kernel.open_current_world_graph(root, ELDYRWILD_WORLD_ID)
    assert head.head_revision_id == child
    status_after = get_lysandra_threat_direction_correction_status(root=root, repo=REPO)
    assert status_after.eligibility == "already_applied"

    # Correction C is revision-bound with locked digest even though full-world
    # rebuild remains blocked by a pre-existing unrelated contribution mismatch.
    digests = store_q.contribution_source_payload_sha256 or {}
    assert digests.get(LOCKED_CORRECTION_CONTRIBUTION_ID) == (
        LOCKED_CORRECTION_SOURCE_PAYLOAD_SHA256
    )
    with pytest.raises(ValueError, match=BASELINE_REBUILD_DIGEST_MISMATCH_CONTRIBUTION):
        kernel.rebuild_from_contributions(
            root,
            world_id=ELDYRWILD_WORLD_ID,
            compare_revision_id=child,
            publish=False,
        )

    assert _file_sha256(SOURCE_SEAL_PATH) == seal_before
    assert _file_sha256(ADJUDICATION_PATH) == adj_before

    # Historical adjudication anchor remains the fixture contract.
    if (root / "graph_memory" / "worlds" / ELDYRWILD_WORLD_ID).is_dir():
        before_anchor = snapshot_world_graph_tree_digest(root, ELDYRWILD_WORLD_ID)
        anchor = analyze_relationship_effective_conformance_v1(
            root=root,
            world_id=ELDYRWILD_WORLD_ID,
            revision_id=ELDYRWILD_REVISION_ID,
        )
        assert snapshot_world_graph_tree_digest(root, ELDYRWILD_WORLD_ID) == before_anchor
        assert anchor.relationship_semantic_count == 346
        assert anchor.relationship_effectively_represented_count == 294
        assert anchor.relationship_effective_residual_count == 52
        assert anchor.uses_statblock_mechanics_count == 2


def test_replacement_collision_fails_closed(tmp_path: Path) -> None:
    root = _clone_eldyrwild(tmp_path)
    status = get_lysandra_threat_direction_correction_status(root=root, repo=REPO)
    parent = status.head_revision_id
    assert parent
    store = kernel.load_world_graph_revision(root, ELDYRWILD_WORLD_ID, parent)
    colliding = store.edges[TARGET_EDGE_ID].model_copy(
        update={
            "edge_id": REPLACEMENT_EDGE_ID,
            "source_node_id": "npc_lysandra",
            "target_node_id": "node:cultists_of_longmont",
            "predicate": "threatens",
        }
    )
    store.edges[REPLACEMENT_EDGE_ID] = colliding
    advanced = kernel.publish_world_revision(
        root,
        ELDYRWILD_WORLD_ID,
        store,
        operation_ids=["op:lysandra-collision-probe"],
    ).revision.revision_id
    with pytest.raises(LysandraThreatDirectionCorrectionError) as exc:
        apply_lysandra_threat_direction_correction(
            expected_parent_revision_id=advanced,
            root=root,
            repo=REPO,
        )
    assert exc.value.code == "ineligible_parent"
    head, _, _ = kernel.open_current_world_graph(root, ELDYRWILD_WORLD_ID)
    assert head.head_revision_id == advanced


def test_cli_status_and_apply_round_trip(tmp_path: Path) -> None:
    from scripts.apply_eldyrwild_lysandra_threat_direction_correction import main

    root = _clone_eldyrwild(tmp_path)
    status = get_lysandra_threat_direction_correction_status(root=root, repo=REPO)
    parent = status.head_revision_id
    assert parent
    assert main(["status", "--root", str(root)]) == 0
    assert (
        main(
            [
                "apply",
                "--root",
                str(root),
                "--expected-parent-revision-id",
                parent,
            ]
        )
        == 0
    )
    head, _, store = kernel.open_current_world_graph(root, ELDYRWILD_WORLD_ID)
    assert head.head_revision_id != parent
    assert store.assertion_support[TARGET_ASSERTION_ID]["support_state"] == "contradicted"
    assert (
        store.assertion_support[REPLACEMENT_ASSERTION_ID]["support_state"] == "supported"
    )
