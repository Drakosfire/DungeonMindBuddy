"""Governed Eldyrwild Session-24 cube→Karsemine false-location correction proofs."""

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
    ELDYRWILD_WORLD_ID,
)
from apps.live_control_server.integrations.dungeonmind_kernel.whole_world_conformance import (
    snapshot_world_graph_tree_digest,
)
from apps.live_control_server.services import (
    eldyrwild_session24_cube_karsemine_false_location_correction as svc,
)
from apps.live_control_server.services.eldyrwild_session24_cube_karsemine_false_location_correction import (
    APPROVED_CORRECTION_RELPATH,
    CAMPAIGN_ID,
    HISTORICAL_ADJUDICATED_SUPPORT_IDS,
    LOCKED_CORRECTION_CONTRIBUTION_ID,
    LOCKED_CORRECTION_RAW_ARTIFACT_SHA256,
    LOCKED_CORRECTION_SOURCE_PAYLOAD_SHA256,
    LOCKED_SOURCE_ARTIFACT_ID,
    LOCKED_SOURCE_REVISION_ID,
    LOCKED_TARGET_CONTRIBUTION_IDS,
    R_CURRENT_REVISION_ID,
    TARGET_ASSERTION_ID,
    TARGET_EDGE_ID,
    TARGET_PREDICATE,
    TARGET_SOURCE_NODE_ID,
    TARGET_TARGET_NODE_ID,
    Session24CubeKarsemineFalseLocationCorrectionError,
    apply_session24_cube_karsemine_false_location_correction,
    get_session24_cube_karsemine_false_location_correction_status,
    load_approved_session24_cube_karsemine_false_location_correction,
)
from graph_memory.union_supergraph.model import UnionSupergraphNode
from graph_memory.world_supergraph import paths as world_paths
from graph_memory.world_supergraph.contribution_store import (
    load_contribution_index,
    load_contribution_record,
    save_contribution_index,
    write_contribution_record,
)

REPO = Path(__file__).resolve().parents[1]
SOURCE_SEAL_PATH = (
    REPO
    / "tests/fixtures/dungeonmind_kernel/eldyrwild_relationship_residual_source_seals_v1.json"
)
ADJUDICATION_PATH = (
    REPO
    / "tests/fixtures/dungeonmind_kernel/eldyrwild_relationship_residual_adjudication_v1.json"
)

# Locked eligible parent used by the canonical Session-24 live exit (also the
# service's R_CURRENT at package authoring: post-Lysandra / pre-Session-24).
PRE_C_PARENT_REVISION_ID = R_CURRENT_REVISION_ID
POST_C_CHILD_REVISION_ID = "rev:b8dfc063bc13a4fb297e83f5f9b313d9"


def _strip_contribution_from_clone(root: Path, contribution_id: str) -> None:
    index = load_contribution_index(root, ELDYRWILD_WORLD_ID)
    if contribution_id in set(index.all_contribution_ids) or contribution_id in set(
        index.active_contribution_ids
    ):
        index = index.model_copy(
            update={
                "all_contribution_ids": [
                    x for x in index.all_contribution_ids if x != contribution_id
                ],
                "active_contribution_ids": [
                    x for x in index.active_contribution_ids if x != contribution_id
                ],
                "superseded_contribution_ids": [
                    x for x in index.superseded_contribution_ids if x != contribution_id
                ],
                "retracted_contribution_ids": [
                    x for x in index.retracted_contribution_ids if x != contribution_id
                ],
                "failed_contribution_ids": [
                    x for x in index.failed_contribution_ids if x != contribution_id
                ],
            }
        )
        save_contribution_index(root, ELDYRWILD_WORLD_ID, index)

    contrib_path = world_paths.contribution_path(
        root, ELDYRWILD_WORLD_ID, contribution_id
    )
    if contrib_path.is_file():
        contrib_path.unlink()


def _ensure_pre_c_eligible_root(root: Path) -> None:
    """Force a clone onto explicit pre-C₂ parent P with C₂ absent from the ledger.

    Copying canonical Eldyrwild after the Session-24 live cutover inherits Q and a
    mutable store that already contains locked C₂. Eligible/apply/replay proofs
    require the pre-C₂ parent instead, so restore that state inside the clone.
    """
    try:
        kernel.load_world_graph_revision(
            root, ELDYRWILD_WORLD_ID, PRE_C_PARENT_REVISION_ID
        )
    except Exception as exc:  # pragma: no cover - fixture absence
        pytest.skip(f"pre-C parent {PRE_C_PARENT_REVISION_ID} unavailable: {exc}")

    kernel.rollback_world_graph_head(
        root, ELDYRWILD_WORLD_ID, PRE_C_PARENT_REVISION_ID
    )
    _strip_contribution_from_clone(root, LOCKED_CORRECTION_CONTRIBUTION_ID)

    post_c_dir = world_paths.revision_dir(
        root, ELDYRWILD_WORLD_ID, POST_C_CHILD_REVISION_ID
    )
    if post_c_dir.is_dir():
        shutil.rmtree(post_c_dir)

    rebuild_latest = world_paths.contribution_rebuild_latest_path(
        root, ELDYRWILD_WORLD_ID
    )
    if rebuild_latest.is_file():
        rebuild_latest.unlink()


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
    _ensure_pre_c_eligible_root(tmp_path)
    return tmp_path


def _sibling_support_fingerprint(store: Any) -> dict[str, dict[str, Any]]:
    """Fingerprint every assertion_support row for unrelated-preservation proofs."""
    rows: dict[str, dict[str, Any]] = {}
    for assertion_id, support in store.assertion_support.items():
        if not isinstance(support, dict):
            continue
        rows[assertion_id] = {key: support.get(key) for key in sorted(support.keys())}
    return rows


def _file_sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _assert_rebuild_equivalent(root: Path, revision_id: str) -> list[str]:
    pinned = kernel.rebuild_from_contributions(
        root,
        world_id=ELDYRWILD_WORLD_ID,
        compare_revision_id=revision_id,
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
    return pinned_diag + unpinned_diag


def test_source_and_adjudication_seals_for_target() -> None:
    seals = json.loads(SOURCE_SEAL_PATH.read_text(encoding="utf-8"))
    seal = next(s for s in seals["seals"] if s["edge_id"] == TARGET_EDGE_ID)
    assert seal["primary_evidence_ref_id"].endswith("session-24:recap:paragraph:002")
    assert seal["source_artifact_id"] == "artifact:recap:longmont-c2:session-24"
    assert (
        seal["artifact_content_sha256"]
        == "603c1590da3aca71d90c8b69abed59368219d5dc1e3d1adf83db1bf854b5cc95"
    )
    assert (
        seal["excerpt_sha256"]
        == "5b3f91b9addeb2e140b72678de5660871cad2832a198c3990080f4213a17a609"
    )

    adj = json.loads(ADJUDICATION_PATH.read_text(encoding="utf-8"))
    rows = adj["records"]
    assert isinstance(rows, list)
    row = next(r for r in rows if r.get("edge_id") == TARGET_EDGE_ID)
    assert row["disposition"] == "SOURCE_CORRECTION_REQUIRED"
    assert row["reason_code"] == "PREDICATE_MISAPPLIED"
    assert row["next_action"] == "AUTHOR_BUDDY_SOURCE_CORRECTION"
    assert TARGET_ASSERTION_ID in row["supporting_assertion_ids"]
    assert set(row["supporting_contribution_ids"]) == HISTORICAL_ADJUDICATED_SUPPORT_IDS


def test_approved_correction_artifact_locks_identity_and_targets() -> None:
    contribution = load_approved_session24_cube_karsemine_false_location_correction(
        repo=REPO
    )
    digest = kernel.compute_contribution_source_payload_sha256(contribution)
    raw = (REPO / APPROVED_CORRECTION_RELPATH).read_bytes()
    assert hashlib.sha256(raw).hexdigest() == LOCKED_CORRECTION_RAW_ARTIFACT_SHA256
    assert contribution.contribution_id == LOCKED_CORRECTION_CONTRIBUTION_ID
    assert digest == LOCKED_CORRECTION_SOURCE_PAYLOAD_SHA256
    assert contribution.authored_by == "gm"
    assert contribution.source_kind == "graph_review_authored_assertion"
    assert contribution.source_artifact_id == LOCKED_SOURCE_ARTIFACT_ID
    assert contribution.source_revision_id == LOCKED_SOURCE_REVISION_ID
    assert contribution.campaign_scope == CAMPAIGN_ID
    assert contribution.accepted_assertions == []
    assert contribution.supersedes_contribution_id is None
    declared = {link.target_contribution_id for link in contribution.assertion_corrections}
    assert declared == LOCKED_TARGET_CONTRIBUTION_IDS
    for link in contribution.assertion_corrections:
        assert link.correction_kind == "contradicts"
        assert link.target_assertion_id == TARGET_ASSERTION_ID
        assert link.replacement_assertion_id is None


def test_semantic_tamper_fails_as_integrity_failure(tmp_path: Path) -> None:
    src = REPO / APPROVED_CORRECTION_RELPATH
    dst_repo = tmp_path / "repo"
    dst = dst_repo / APPROVED_CORRECTION_RELPATH
    dst.parent.mkdir(parents=True)
    payload = json.loads(src.read_text(encoding="utf-8"))
    payload["authored_by"] = "not-gm"
    dst.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")
    # Also need source seals for status path that loads artifact first.
    seal_dst = dst_repo / svc.SOURCE_SEAL_RELPATH
    seal_dst.parent.mkdir(parents=True)
    seal_dst.write_bytes(SOURCE_SEAL_PATH.read_bytes())
    with pytest.raises(Session24CubeKarsemineFalseLocationCorrectionError) as exc:
        load_approved_session24_cube_karsemine_false_location_correction(repo=dst_repo)
    assert exc.value.code == "integrity_failure"
    st = get_session24_cube_karsemine_false_location_correction_status(
        root=tmp_path, repo=dst_repo
    )
    assert st.eligibility == "integrity_failure"


def test_raw_byte_tamper_fails_as_integrity_failure(tmp_path: Path) -> None:
    src = REPO / APPROVED_CORRECTION_RELPATH
    dst_repo = tmp_path / "repo"
    dst = dst_repo / APPROVED_CORRECTION_RELPATH
    dst.parent.mkdir(parents=True)
    payload = json.loads(src.read_text(encoding="utf-8"))
    dst.write_text(json.dumps(payload, indent=2) + "\n  \n", encoding="utf-8")
    assert hashlib.sha256(dst.read_bytes()).hexdigest() != (
        LOCKED_CORRECTION_RAW_ARTIFACT_SHA256
    )
    with pytest.raises(Session24CubeKarsemineFalseLocationCorrectionError) as exc:
        load_approved_session24_cube_karsemine_false_location_correction(repo=dst_repo)
    assert exc.value.code == "integrity_failure"


def test_real_clone_status_is_eligible(tmp_path: Path) -> None:
    root = _clone_eldyrwild(tmp_path)
    status = get_session24_cube_karsemine_false_location_correction_status(
        root=root, repo=REPO
    )
    assert status.eligibility == "eligible"
    assert status.head_revision_id == R_CURRENT_REVISION_ID
    assert status.continuity_state in {"ANCHOR", "CARRIED_FORWARD"}
    assert status.source_grounding_verified is True
    assert status.durable_shape_verified is True
    assert status.target_edge_id == TARGET_EDGE_ID
    assert status.correction_contribution_id == LOCKED_CORRECTION_CONTRIBUTION_ID


def test_stale_parent_fails_closed(tmp_path: Path) -> None:
    root = _clone_eldyrwild(tmp_path)
    status = get_session24_cube_karsemine_false_location_correction_status(
        root=root, repo=REPO
    )
    parent = status.head_revision_id
    assert parent
    store = kernel.load_world_graph_revision(root, ELDYRWILD_WORLD_ID, parent)
    store.nodes["npc:session24-stale-probe"] = UnionSupergraphNode(
        node_id="npc:session24-stale-probe",
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
        operation_ids=["op:session24-stale-parent-probe"],
    ).revision.revision_id
    assert advanced != parent
    with pytest.raises(Session24CubeKarsemineFalseLocationCorrectionError) as exc:
        apply_session24_cube_karsemine_false_location_correction(
            expected_parent_revision_id=parent,
            root=root,
            repo=REPO,
        )
    assert exc.value.code == "stale_expected_parent"
    head, _, _ = kernel.open_current_world_graph(root, ELDYRWILD_WORLD_ID)
    assert head.head_revision_id == advanced


def test_live_root_apply_requires_opt_in(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    root = _clone_eldyrwild(tmp_path)
    head = kernel.open_current_world_graph(root, ELDYRWILD_WORLD_ID)[0].head_revision_id
    monkeypatch.setattr(svc, "live_world_graph_root", lambda: root)
    monkeypatch.setattr(svc, "world_graph_root", lambda: root)
    with pytest.raises(Session24CubeKarsemineFalseLocationCorrectionError) as exc:
        apply_session24_cube_karsemine_false_location_correction(
            expected_parent_revision_id=head,
            root=root,
            repo=REPO,
            allow_live_world=False,
        )
    assert exc.value.code == "live_world_opt_in_required"
    st = get_session24_cube_karsemine_false_location_correction_status(
        root=root, repo=REPO
    )
    assert st.eligibility == "eligible"


def test_active_support_mismatch_is_ineligible(tmp_path: Path) -> None:
    root = _clone_eldyrwild(tmp_path)
    parent = kernel.open_current_world_graph(root, ELDYRWILD_WORLD_ID)[0].head_revision_id
    store = kernel.load_world_graph_revision(root, ELDYRWILD_WORLD_ID, parent)
    support = dict(store.assertion_support[TARGET_ASSERTION_ID])
    # Reintroduce historical second supporter so A(X) != locked single-target C.
    second = "contribution:a01be11c6967afd9"
    support["active_contribution_ids"] = sorted(LOCKED_TARGET_CONTRIBUTION_IDS | {second})
    per_ev = dict(support.get("per_contribution_evidence_ref_ids") or {})
    per_art = dict(support.get("per_contribution_source_artifact_ids") or {})
    locked = next(iter(LOCKED_TARGET_CONTRIBUTION_IDS))
    per_ev[second] = list(per_ev.get(locked) or support.get("evidence_ref_ids") or [])
    per_art[second] = list(per_art.get(locked) or support.get("source_artifact_ids") or [])
    support["per_contribution_evidence_ref_ids"] = per_ev
    support["per_contribution_source_artifact_ids"] = per_art
    store.assertion_support[TARGET_ASSERTION_ID] = support
    advanced = kernel.publish_world_revision(
        root,
        ELDYRWILD_WORLD_ID,
        store,
        operation_ids=["op:session24-support-mismatch-probe"],
    ).revision.revision_id
    st = get_session24_cube_karsemine_false_location_correction_status(
        root=root, expected_parent_revision_id=advanced, repo=REPO
    )
    assert st.eligibility == "ineligible"
    assert "active_support_mismatch_locked_c" in st.diagnostics


def test_outside_historical_support_is_ineligible(tmp_path: Path) -> None:
    root = _clone_eldyrwild(tmp_path)
    parent = kernel.open_current_world_graph(root, ELDYRWILD_WORLD_ID)[0].head_revision_id
    store = kernel.load_world_graph_revision(root, ELDYRWILD_WORLD_ID, parent)
    support = dict(store.assertion_support[TARGET_ASSERTION_ID])
    outsider = "contribution:outsider-session24-support"
    locked = next(iter(LOCKED_TARGET_CONTRIBUTION_IDS))
    support["active_contribution_ids"] = [locked, outsider]
    per_ev = dict(support.get("per_contribution_evidence_ref_ids") or {})
    per_art = dict(support.get("per_contribution_source_artifact_ids") or {})
    per_ev[outsider] = list(per_ev.get(locked) or support.get("evidence_ref_ids") or [])
    per_art[outsider] = list(
        per_art.get(locked) or support.get("source_artifact_ids") or []
    )
    support["per_contribution_evidence_ref_ids"] = per_ev
    support["per_contribution_source_artifact_ids"] = per_art
    store.assertion_support[TARGET_ASSERTION_ID] = support
    advanced = kernel.publish_world_revision(
        root,
        ELDYRWILD_WORLD_ID,
        store,
        operation_ids=["op:session24-outsider-support-probe"],
    ).revision.revision_id
    st = get_session24_cube_karsemine_false_location_correction_status(
        root=root, expected_parent_revision_id=advanced, repo=REPO
    )
    assert st.eligibility == "ineligible"
    assert "active_support_outside_historical" in st.diagnostics


def test_x_not_effective_residual_is_ineligible(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    root = _clone_eldyrwild(tmp_path)

    class _Eff:
        remaining_residual_edge_ids: list[str] = []

    monkeypatch.setattr(
        svc,
        "analyze_relationship_effective_conformance_v1",
        lambda **kwargs: _Eff(),
    )
    st = get_session24_cube_karsemine_false_location_correction_status(
        root=root, repo=REPO
    )
    assert st.eligibility == "ineligible"
    assert "target_not_effective_residual" in st.diagnostics


def test_false_positive_already_applied_without_revision_bound_c(
    tmp_path: Path,
) -> None:
    root = _clone_eldyrwild(tmp_path)
    parent = kernel.open_current_world_graph(root, ELDYRWILD_WORLD_ID)[0].head_revision_id
    store = kernel.load_world_graph_revision(root, ELDYRWILD_WORLD_ID, parent)
    target = dict(store.assertion_support[TARGET_ASSERTION_ID])
    evidence_ids = list(target.get("evidence_ref_ids") or [])
    artifact_ids = list(target.get("source_artifact_ids") or [])
    store.assertion_support[TARGET_ASSERTION_ID] = {
        **target,
        "support_state": "contradicted",
        "active_contribution_ids": [],
        "contradicted_contribution_ids": sorted(LOCKED_TARGET_CONTRIBUTION_IDS),
        "per_contribution_evidence_ref_ids": {},
        "per_contribution_source_artifact_ids": {},
        "evidence_ref_ids": evidence_ids,
        "source_artifact_ids": artifact_ids,
    }
    advanced = kernel.publish_world_revision(
        root,
        ELDYRWILD_WORLD_ID,
        store,
        operation_ids=["op:session24-false-already-applied-probe"],
    ).revision.revision_id
    st = get_session24_cube_karsemine_false_location_correction_status(
        root=root, expected_parent_revision_id=advanced, repo=REPO
    )
    assert st.eligibility == "integrity_failure"
    assert st.eligibility != "already_applied"


def test_retry_without_replay_manifest_entry_fails_closed(tmp_path: Path) -> None:
    root = _clone_eldyrwild(tmp_path)
    parent = get_session24_cube_karsemine_false_location_correction_status(
        root=root, repo=REPO
    ).head_revision_id
    assert parent
    result = apply_session24_cube_karsemine_false_location_correction(
        expected_parent_revision_id=parent,
        root=root,
        repo=REPO,
    )
    child = result.revision_id
    assert child and result.published

    store = kernel.load_world_graph_revision(root, ELDYRWILD_WORLD_ID, child)
    store.contribution_replay_manifest = [
        entry
        for entry in (store.contribution_replay_manifest or [])
        if getattr(entry, "contribution_id", None) != LOCKED_CORRECTION_CONTRIBUTION_ID
        and (
            not isinstance(entry, dict)
            or entry.get("contribution_id") != LOCKED_CORRECTION_CONTRIBUTION_ID
        )
    ]
    # Keep digest map, ledger, and contradicted shape intact.
    digests = dict(store.contribution_source_payload_sha256 or {})
    assert digests.get(LOCKED_CORRECTION_CONTRIBUTION_ID) == (
        LOCKED_CORRECTION_SOURCE_PAYLOAD_SHA256
    )
    adversarial = kernel.publish_world_revision(
        root,
        ELDYRWILD_WORLD_ID,
        store,
        operation_ids=["op:session24-strip-manifest-c"],
    ).revision.revision_id

    st = get_session24_cube_karsemine_false_location_correction_status(
        root=root, expected_parent_revision_id=adversarial, repo=REPO
    )
    assert st.eligibility == "integrity_failure"
    assert st.eligibility != "already_applied"
    with pytest.raises(Session24CubeKarsemineFalseLocationCorrectionError) as exc:
        apply_session24_cube_karsemine_false_location_correction(
            expected_parent_revision_id=adversarial,
            root=root,
            repo=REPO,
        )
    assert exc.value.code == "integrity_failure"


def test_kernel_partial_multi_support_coverage_fails_before_mutation(
    tmp_path: Path,
) -> None:
    """A(X) is currently singleton; still prove #544 multi-support partial gate."""
    root = _clone_eldyrwild(tmp_path)
    parent = kernel.open_current_world_graph(root, ELDYRWILD_WORLD_ID)[0].head_revision_id
    store = kernel.load_world_graph_revision(root, ELDYRWILD_WORLD_ID, parent)
    support = dict(store.assertion_support[TARGET_ASSERTION_ID])
    locked = next(iter(LOCKED_TARGET_CONTRIBUTION_IDS))
    second = "contribution:a01be11c6967afd9"
    support["active_contribution_ids"] = [locked, second]
    support["support_state"] = "supported"
    per_ev = dict(support.get("per_contribution_evidence_ref_ids") or {})
    per_art = dict(support.get("per_contribution_source_artifact_ids") or {})
    per_ev[second] = list(per_ev.get(locked) or support.get("evidence_ref_ids") or [])
    per_art[second] = list(per_art.get(locked) or support.get("source_artifact_ids") or [])
    support["per_contribution_evidence_ref_ids"] = per_ev
    support["per_contribution_source_artifact_ids"] = per_art
    # Ensure second is not listed as superseded for this adversarial support row.
    superseded = [
        x for x in (support.get("superseded_contribution_ids") or []) if x != second
    ]
    support["superseded_contribution_ids"] = superseded
    store.assertion_support[TARGET_ASSERTION_ID] = support
    multi = kernel.publish_world_revision(
        root,
        ELDYRWILD_WORLD_ID,
        store,
        operation_ids=["op:session24-multi-support-partial-probe"],
    ).revision.revision_id

    before = snapshot_world_graph_tree_digest(root, ELDYRWILD_WORLD_ID)
    before_index = load_contribution_index(root, ELDYRWILD_WORLD_ID)
    partial = kernel.create_edge_assertion_contradiction_contribution(
        world_id=ELDYRWILD_WORLD_ID,
        authored_by="gm",
        target_assertion_id=TARGET_ASSERTION_ID,
        target_contribution_ids=[locked],
        source_artifact_id=(
            "graph-native:eldyrwild-correction:session24-partial-adversary"
        ),
        source_revision_id="correction:eldyrwild:session24-partial-adversary",
        campaign_scope=CAMPAIGN_ID,
        produced_at="2026-08-10T18:00:00Z",
    )
    result = kernel.contradict_edge_assertion_support(
        root,
        world_id=ELDYRWILD_WORLD_ID,
        contribution=partial,
        expected_parent_revision_id=multi,
    )
    assert result.published is False
    assert result.failure_code == "correction_rejected"
    assert snapshot_world_graph_tree_digest(root, ELDYRWILD_WORLD_ID) == before
    head, _, store_after = kernel.open_current_world_graph(root, ELDYRWILD_WORLD_ID)
    assert head.head_revision_id == multi
    assert store_after.assertion_support[TARGET_ASSERTION_ID]["support_state"] == (
        "supported"
    )
    assert set(
        store_after.assertion_support[TARGET_ASSERTION_ID]["active_contribution_ids"]
    ) == {locked, second}
    after_index = load_contribution_index(root, ELDYRWILD_WORLD_ID)
    assert after_index.active_contribution_ids == before_index.active_contribution_ids
    with pytest.raises(FileNotFoundError):
        load_contribution_record(root, ELDYRWILD_WORLD_ID, partial.contribution_id)


def test_real_clone_apply_preserves_history_and_parent_relative_conformance(
    tmp_path: Path,
) -> None:
    root = _clone_eldyrwild(tmp_path)
    seal_before = _file_sha256(SOURCE_SEAL_PATH)
    adj_before = _file_sha256(ADJUDICATION_PATH)
    canonical_before = snapshot_world_graph_tree_digest(
        world_graph_root(), ELDYRWILD_WORLD_ID
    )

    status = get_session24_cube_karsemine_false_location_correction_status(
        root=root, repo=REPO
    )
    assert status.eligibility == "eligible"
    parent = status.head_revision_id
    assert parent == R_CURRENT_REVISION_ID

    _assert_rebuild_equivalent(root, parent)

    store_p = kernel.load_world_graph_revision(root, ELDYRWILD_WORLD_ID, parent)
    siblings_p = _sibling_support_fingerprint(store_p)
    assert TARGET_ASSERTION_ID in siblings_p
    assert store_p.assertion_support[TARGET_ASSERTION_ID]["support_state"] == "supported"
    active_p = set(
        store_p.assertion_support[TARGET_ASSERTION_ID].get("active_contribution_ids")
        or []
    )
    assert active_p == LOCKED_TARGET_CONTRIBUTION_IDS

    before_p = snapshot_world_graph_tree_digest(root, ELDYRWILD_WORLD_ID)
    eff_p = analyze_relationship_effective_conformance_v1(
        root=root, world_id=ELDYRWILD_WORLD_ID, revision_id=parent
    )
    assert snapshot_world_graph_tree_digest(root, ELDYRWILD_WORLD_ID) == before_p
    assert TARGET_EDGE_ID in eff_p.remaining_residual_edge_ids
    residual_p = set(eff_p.remaining_residual_edge_ids)

    # Snapshot source contribution status (must remain durable/active).
    for cid in sorted(LOCKED_TARGET_CONTRIBUTION_IDS):
        ledger = load_contribution_record(root, ELDYRWILD_WORLD_ID, cid)
        assert ledger.status == "active"

    result = apply_session24_cube_karsemine_false_location_correction(
        expected_parent_revision_id=parent,
        root=root,
        repo=REPO,
    )
    assert result.published is True
    assert result.parent_revision_id == parent
    child = result.revision_id
    assert child and child != parent

    store_q = kernel.load_world_graph_revision(root, ELDYRWILD_WORLD_ID, child)
    assert TARGET_EDGE_ID in store_q.edges
    edge = store_q.edges[TARGET_EDGE_ID]
    assert edge.source_node_id == TARGET_SOURCE_NODE_ID
    assert edge.target_node_id == TARGET_TARGET_NODE_ID
    assert edge.predicate == TARGET_PREDICATE

    x_support = store_q.assertion_support[TARGET_ASSERTION_ID]
    assert x_support["support_state"] == "contradicted"
    assert not (x_support.get("active_contribution_ids") or [])
    contradicted = set(x_support.get("contradicted_contribution_ids") or [])
    assert LOCKED_TARGET_CONTRIBUTION_IDS.issubset(contradicted)

    digests = store_q.contribution_source_payload_sha256 or {}
    assert digests.get(LOCKED_CORRECTION_CONTRIBUTION_ID) == (
        LOCKED_CORRECTION_SOURCE_PAYLOAD_SHA256
    )
    ledger_c = load_contribution_record(
        root, ELDYRWILD_WORLD_ID, LOCKED_CORRECTION_CONTRIBUTION_ID
    )
    assert ledger_c.status == "active"
    assert (
        kernel.compute_contribution_source_payload_sha256(ledger_c)
        == LOCKED_CORRECTION_SOURCE_PAYLOAD_SHA256
    )
    index = load_contribution_index(root, ELDYRWILD_WORLD_ID)
    assert LOCKED_CORRECTION_CONTRIBUTION_ID in set(index.active_contribution_ids)

    manifest_hit = False
    for entry in store_q.contribution_replay_manifest or []:
        cid = getattr(entry, "contribution_id", None)
        status_m = getattr(entry, "status", None)
        digest_m = getattr(entry, "source_payload_sha256", None)
        if cid == LOCKED_CORRECTION_CONTRIBUTION_ID:
            assert status_m == "active"
            assert digest_m == LOCKED_CORRECTION_SOURCE_PAYLOAD_SHA256
            manifest_hit = True
    assert manifest_hit

    # No replacement assertion authored.
    assert not any(
        isinstance(row, dict)
        and row.get("introduced_by_contribution_id") == LOCKED_CORRECTION_CONTRIBUTION_ID
        and row.get("support_state") == "supported"
        and row.get("assertion_id") != TARGET_ASSERTION_ID
        for row in store_q.assertion_support.values()
    )

    siblings_q = _sibling_support_fingerprint(store_q)
    for assertion_id, before_row in siblings_p.items():
        if assertion_id == TARGET_ASSERTION_ID:
            continue
        assert siblings_q.get(assertion_id) == before_row

    for cid in sorted(LOCKED_TARGET_CONTRIBUTION_IDS):
        ledger = load_contribution_record(root, ELDYRWILD_WORLD_ID, cid)
        assert ledger.status == "active"

    store_p_after = kernel.load_world_graph_revision(root, ELDYRWILD_WORLD_ID, parent)
    assert (
        store_p_after.assertion_support[TARGET_ASSERTION_ID]["support_state"]
        == "supported"
    )

    before_q = snapshot_world_graph_tree_digest(root, ELDYRWILD_WORLD_ID)
    eff_q = analyze_relationship_effective_conformance_v1(
        root=root, world_id=ELDYRWILD_WORLD_ID, revision_id=child
    )
    assert snapshot_world_graph_tree_digest(root, ELDYRWILD_WORLD_ID) == before_q
    assert (
        eff_q.relationship_semantic_count == eff_p.relationship_semantic_count - 1
    )
    assert (
        eff_q.relationship_effectively_represented_count
        == eff_p.relationship_effectively_represented_count
    )
    assert (
        eff_q.relationship_effective_residual_count
        == eff_p.relationship_effective_residual_count - 1
    )
    assert eff_q.uses_statblock_mechanics_count == eff_p.uses_statblock_mechanics_count
    assert TARGET_EDGE_ID not in eff_q.remaining_residual_edge_ids
    residual_q = set(eff_q.remaining_residual_edge_ids)
    assert residual_p - residual_q == {TARGET_EDGE_ID}

    _assert_rebuild_equivalent(root, child)

    retry = apply_session24_cube_karsemine_false_location_correction(
        expected_parent_revision_id=child,
        root=root,
        repo=REPO,
    )
    assert retry.published is False
    assert retry.eligibility == "already_applied"
    assert retry.revision_id == child
    head, _, _ = kernel.open_current_world_graph(root, ELDYRWILD_WORLD_ID)
    assert head.head_revision_id == child
    status_after = get_session24_cube_karsemine_false_location_correction_status(
        root=root, repo=REPO
    )
    assert status_after.eligibility == "already_applied"

    with pytest.raises(Session24CubeKarsemineFalseLocationCorrectionError) as stale_exc:
        apply_session24_cube_karsemine_false_location_correction(
            expected_parent_revision_id=parent,
            root=root,
            repo=REPO,
        )
    assert stale_exc.value.code == "stale_expected_parent"
    head2, _, _ = kernel.open_current_world_graph(root, ELDYRWILD_WORLD_ID)
    assert head2.head_revision_id == child

    assert _file_sha256(SOURCE_SEAL_PATH) == seal_before
    assert _file_sha256(ADJUDICATION_PATH) == adj_before
    assert (
        snapshot_world_graph_tree_digest(world_graph_root(), ELDYRWILD_WORLD_ID)
        == canonical_before
    )


def test_c_ledger_digest_mismatch_is_integrity_failure(tmp_path: Path) -> None:
    root = _clone_eldyrwild(tmp_path)
    parent = get_session24_cube_karsemine_false_location_correction_status(
        root=root, repo=REPO
    ).head_revision_id
    assert parent
    result = apply_session24_cube_karsemine_false_location_correction(
        expected_parent_revision_id=parent,
        root=root,
        repo=REPO,
    )
    child = result.revision_id
    assert child

    ledger = load_contribution_record(
        root, ELDYRWILD_WORLD_ID, LOCKED_CORRECTION_CONTRIBUTION_ID
    )
    tampered = ledger.model_copy(update={"authored_by": "not-gm"})
    write_contribution_record(root, ELDYRWILD_WORLD_ID, tampered)
    st = get_session24_cube_karsemine_false_location_correction_status(
        root=root, expected_parent_revision_id=child, repo=REPO
    )
    assert st.eligibility == "integrity_failure"


def test_c_ledger_inactive_is_integrity_failure(tmp_path: Path) -> None:
    root = _clone_eldyrwild(tmp_path)
    parent = get_session24_cube_karsemine_false_location_correction_status(
        root=root, repo=REPO
    ).head_revision_id
    assert parent
    result = apply_session24_cube_karsemine_false_location_correction(
        expected_parent_revision_id=parent,
        root=root,
        repo=REPO,
    )
    child = result.revision_id
    assert child

    ledger = load_contribution_record(
        root, ELDYRWILD_WORLD_ID, LOCKED_CORRECTION_CONTRIBUTION_ID
    )
    inactive = ledger.model_copy(update={"status": "retracted"})
    write_contribution_record(root, ELDYRWILD_WORLD_ID, inactive)
    index = load_contribution_index(root, ELDYRWILD_WORLD_ID)
    index = index.model_copy(
        update={
            "active_contribution_ids": [
                x
                for x in index.active_contribution_ids
                if x != LOCKED_CORRECTION_CONTRIBUTION_ID
            ],
            "retracted_contribution_ids": sorted(
                set(index.retracted_contribution_ids)
                | {LOCKED_CORRECTION_CONTRIBUTION_ID}
            ),
        }
    )
    save_contribution_index(root, ELDYRWILD_WORLD_ID, index)
    st = get_session24_cube_karsemine_false_location_correction_status(
        root=root, expected_parent_revision_id=child, repo=REPO
    )
    assert st.eligibility == "integrity_failure"


def test_same_c_id_different_source_payload_fails_closed(tmp_path: Path) -> None:
    """Unbound mutable C with same ID but different digest must not be overwritten."""
    root = _clone_eldyrwild(tmp_path)
    parent = get_session24_cube_karsemine_false_location_correction_status(
        root=root, repo=REPO
    ).head_revision_id
    assert parent
    assert (
        get_session24_cube_karsemine_false_location_correction_status(
            root=root, repo=REPO
        ).eligibility
        == "eligible"
    )

    approved = load_approved_session24_cube_karsemine_false_location_correction(
        repo=REPO
    )
    # produced_at is metadata-only for contribution identity, so the ID stays
    # locked while the source-payload digest diverges.
    colliding = approved.model_copy(update={"produced_at": "2020-01-01T00:00:00Z"})
    assert colliding.contribution_id == LOCKED_CORRECTION_CONTRIBUTION_ID
    colliding_digest = kernel.compute_contribution_source_payload_sha256(colliding)
    assert colliding_digest != LOCKED_CORRECTION_SOURCE_PAYLOAD_SHA256
    write_contribution_record(root, ELDYRWILD_WORLD_ID, colliding)

    before = snapshot_world_graph_tree_digest(root, ELDYRWILD_WORLD_ID)
    before_index = load_contribution_index(root, ELDYRWILD_WORLD_ID)
    before_ledger_bytes = world_paths.contribution_path(
        root, ELDYRWILD_WORLD_ID, LOCKED_CORRECTION_CONTRIBUTION_ID
    ).read_bytes()

    st = get_session24_cube_karsemine_false_location_correction_status(
        root=root, expected_parent_revision_id=parent, repo=REPO
    )
    assert st.eligibility == "integrity_failure"
    assert "mutable_C_source_digest_collision" in st.diagnostics

    with pytest.raises(Session24CubeKarsemineFalseLocationCorrectionError) as exc:
        apply_session24_cube_karsemine_false_location_correction(
            expected_parent_revision_id=parent,
            root=root,
            repo=REPO,
        )
    assert exc.value.code == "integrity_failure"

    assert snapshot_world_graph_tree_digest(root, ELDYRWILD_WORLD_ID) == before
    after_index = load_contribution_index(root, ELDYRWILD_WORLD_ID)
    assert after_index.model_dump() == before_index.model_dump()
    head, _, _ = kernel.open_current_world_graph(root, ELDYRWILD_WORLD_ID)
    assert head.head_revision_id == parent
    assert (
        world_paths.contribution_path(
            root, ELDYRWILD_WORLD_ID, LOCKED_CORRECTION_CONTRIBUTION_ID
        ).read_bytes()
        == before_ledger_bytes
    )
    still = load_contribution_record(
        root, ELDYRWILD_WORLD_ID, LOCKED_CORRECTION_CONTRIBUTION_ID
    )
    assert (
        kernel.compute_contribution_source_payload_sha256(still) == colliding_digest
    )
