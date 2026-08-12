"""Governed Eldyrwild Session-25 Ephanna→Thrin false-hires correction proofs."""

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
from apps.live_control_server.integrations.dungeonmind_kernel.relationship_adjudication_authority_v1 import (
    HISTORICAL_A_AUTHORITY_ID,
    SESSION25_DESCENDANT_AUTHORITY_ID,
    analyze_composed_relationship_adjudication_authority_v1,
)
from apps.live_control_server.integrations.dungeonmind_kernel.relationship_descendant_residual_adjudication_v1 import (
    EXACT_U7_EDGE_IDS,
    U1,
    U2,
    U3,
    U4,
    U5,
    U6,
    U7,
)
from apps.live_control_server.integrations.dungeonmind_kernel.relationship_effective_conformance_v1 import (
    analyze_relationship_effective_conformance_v1,
)
from apps.live_control_server.integrations.dungeonmind_kernel.relationship_residual_adjudication import (
    ELDYRWILD_RESIDUAL_FINDINGS,
    ELDYRWILD_WORLD_ID,
)
from apps.live_control_server.integrations.dungeonmind_kernel.whole_world_conformance import (
    snapshot_world_graph_tree_digest,
)
from apps.live_control_server.services import (
    eldyrwild_session25_ephanna_thrin_false_hires_correction as svc,
)
from apps.live_control_server.services.eldyrwild_session25_ephanna_thrin_false_hires_correction import (
    APPROVED_CORRECTION_RELPATH,
    C1_CORRECTION_CONTRIBUTION_ID,
    C1_CORRECTION_SOURCE_PAYLOAD_SHA256,
    C2_CORRECTION_CONTRIBUTION_ID,
    C2_CORRECTION_SOURCE_PAYLOAD_SHA256,
    C2_TARGET_ASSERTION_ID,
    C2_TARGET_EDGE_ID,
    C3_CORRECTION_CONTRIBUTION_ID,
    C3_CORRECTION_SOURCE_PAYLOAD_SHA256,
    C3_TARGET_ASSERTION_ID,
    C3_TARGET_EDGE_ID,
    CAMPAIGN_ID,
    ELIGIBLE_PARENT_PAYLOAD_SHA256,
    ELIGIBLE_PARENT_REVISION_ID,
    LOCKED_ARTIFACT_CONTENT_SHA256,
    LOCKED_CORRECTION_CONTRIBUTION_ID,
    LOCKED_CORRECTION_DIGEST,
    LOCKED_CORRECTION_RAW_ARTIFACT_SHA256,
    LOCKED_CORRECTION_SOURCE_PAYLOAD_SHA256,
    LOCKED_EVIDENCE_REF_ID,
    LOCKED_EXCERPT_SHA256,
    LOCKED_RECAP_ARTIFACT_ID,
    LOCKED_RECAP_ARTIFACT_URI,
    LOCKED_SOURCE_ARTIFACT_ID,
    LOCKED_SOURCE_REVISION_ID,
    LOCKED_SOURCE_SPAN_REF_ID,
    LOCKED_TARGET_CONTRIBUTION_IDS,
    LOCKED_TARGET_CONTRIBUTION_SOURCE_PAYLOAD_SHA256,
    R_CURRENT_REVISION_ID,
    TARGET_ASSERTION_ID,
    TARGET_EDGE_ID,
    TARGET_PREDICATE,
    TARGET_SOURCE_NODE_ID,
    TARGET_TARGET_NODE_ID,
    Session25EphannaThrinFalseHiresCorrectionError,
    apply_session25_ephanna_thrin_false_hires_correction,
    get_session25_ephanna_thrin_false_hires_correction_status,
    load_approved_session25_ephanna_thrin_false_hires_correction,
)
from apps.live_control_server.services.eldyrwild_lysandra_threat_direction_correction import (
    get_lysandra_threat_direction_correction_status,
)
from apps.live_control_server.services.eldyrwild_session24_cube_karsemine_false_location_correction import (
    get_session24_cube_karsemine_false_location_correction_status,
)
from apps.live_control_server.services.eldyrwild_session24_lysandra_caelynn_false_leads_correction import (
    get_session24_lysandra_caelynn_false_leads_correction_status,
)
from graph_memory.union_supergraph.model import UnionSupergraphNode
from graph_memory.world_supergraph import paths as world_paths
from graph_memory.world_supergraph.contribution_store import (
    load_contribution_index,
    load_contribution_record,
    save_contribution_index,
    write_contribution_record,
)
from graph_memory.world_supergraph.storage import list_revision_ids

REPO = Path(__file__).resolve().parents[1]
SOURCE_SEAL_PATH = (
    REPO
    / "tests/fixtures/dungeonmind_kernel/"
    / "eldyrwild_relationship_descendant_residual_source_seals_v1.json"
)
ADJUDICATION_PATH = (
    REPO
    / "tests/fixtures/dungeonmind_kernel/"
    / "eldyrwild_relationship_descendant_residual_adjudication_v1.json"
)
LOCKED_SOURCE_SEALS_SHA256 = (
    "a056f19338b321bc42e8d4c01e9e0b2fd91443b0f5cb6c794e1b6edf5abc838c"
)
LOCKED_ADJUDICATION_SHA256 = (
    "4a2f86ee9c9ca5a020f139bd50c1a22d7a14405a4f53e55d8f7c4bb16da79e95"
)

# Locked eligible parent P = formal R_current = Q₃ after #554 / #557 / C₃.
PRE_C_PARENT_REVISION_ID = ELIGIBLE_PARENT_REVISION_ID

# U1–U6 = EXACT_U7_EDGE_IDS minus U7 (the C₄ target).
PRESERVED_SIBLING_U_EDGE_IDS: tuple[str, ...] = (U1, U2, U3, U4, U5, U6)
assert PRESERVED_SIBLING_U_EDGE_IDS == tuple(
    e for e in EXACT_U7_EDGE_IDS if e != U7
)
assert U7 == TARGET_EDGE_ID

_EXPECTED_POST_C4_REMAINING_DISPOSITIONS = {
    "SOURCE_CORRECTION_REQUIRED": 36,
    "COMPOUND_ASSERTION_NOT_SINGLE_RELATIONSHIP": 11,
    "IDENTITY_NOT_RELATIONSHIP": 7,
    "INSUFFICIENT_EVIDENCE": 1,
}

_LOCKED_SOURCE_CONTRIBUTION_ID = next(iter(LOCKED_TARGET_CONTRIBUTION_IDS))


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


def _drop_c4_child_revisions(root: Path) -> None:
    """Remove any published child of Q₃ that revision-binds C₄ (post-live clones)."""
    for revision_id in list_revision_ids(root, ELDYRWILD_WORLD_ID):
        if revision_id == PRE_C_PARENT_REVISION_ID:
            continue
        try:
            manifest = kernel.load_world_graph_revision_manifest(
                root, ELDYRWILD_WORLD_ID, revision_id
            )
            store = kernel.load_world_graph_revision(
                root, ELDYRWILD_WORLD_ID, revision_id
            )
        except Exception:  # pragma: no cover - corrupt/partial revision dirs
            continue
        if getattr(manifest, "parent_revision_id", None) != PRE_C_PARENT_REVISION_ID:
            continue
        digests = store.contribution_source_payload_sha256 or {}
        if digests.get(LOCKED_CORRECTION_CONTRIBUTION_ID) != (
            LOCKED_CORRECTION_SOURCE_PAYLOAD_SHA256
        ):
            continue
        rev_dir = world_paths.revision_dir(root, ELDYRWILD_WORLD_ID, revision_id)
        if rev_dir.is_dir():
            shutil.rmtree(rev_dir)


def _ensure_pre_c_eligible_root(root: Path) -> None:
    """Force a clone onto exact eligible parent Q₃ with C₄ absent from the ledger.

    C₁–C₃ remain. Copying canonical Eldyrwild after the C₄ live cutover would
    inherit Q₄ and a mutable store that already contains locked C₄; eligible /
    apply / replay proofs require the pre-C₄ parent instead.
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
    _drop_c4_child_revisions(root)

    rebuild_latest = world_paths.contribution_rebuild_latest_path(
        root, ELDYRWILD_WORLD_ID
    )
    if rebuild_latest.is_file():
        rebuild_latest.unlink()


def _clone_eldyrwild(tmp_path: Path) -> Path:
    src_root = world_graph_root()
    eldyrwild_src = src_root / "graph_memory" / "worlds" / "eldyrwild"
    if not eldyrwild_src.is_dir():
        fallback = Path(
            "/home/drakosfire/Projects/DungeonOverMind/DungeonMindBuddy/out"
        )
        if (fallback / "graph_memory" / "worlds" / "eldyrwild").is_dir():
            src_root = fallback
            eldyrwild_src = src_root / "graph_memory" / "worlds" / "eldyrwild"
        else:
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


def _contribution_support_fingerprint(
    root: Path, store: Any, contribution_id: str
) -> dict[str, dict[str, Any]]:
    """Fingerprint assertion_support rows introduced by a locked contribution."""
    ledger = load_contribution_record(root, ELDYRWILD_WORLD_ID, contribution_id)
    assertion_ids = {a.assertion_id for a in ledger.accepted_assertions}
    rows: dict[str, dict[str, Any]] = {}
    for assertion_id in assertion_ids:
        support = store.assertion_support.get(assertion_id)
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


def test_target_not_in_historical_a_residual_findings() -> None:
    assert TARGET_EDGE_ID not in ELDYRWILD_RESIDUAL_FINDINGS
    assert U7 not in ELDYRWILD_RESIDUAL_FINDINGS
    assert set(EXACT_U7_EDGE_IDS).isdisjoint(ELDYRWILD_RESIDUAL_FINDINGS)


def test_source_and_adjudication_seals_for_target() -> None:
    assert _file_sha256(SOURCE_SEAL_PATH) == LOCKED_SOURCE_SEALS_SHA256
    assert _file_sha256(ADJUDICATION_PATH) == LOCKED_ADJUDICATION_SHA256

    seals = json.loads(SOURCE_SEAL_PATH.read_text(encoding="utf-8"))
    seal = next(s for s in seals["seals"] if s["edge_id"] == TARGET_EDGE_ID)
    assert seal["primary_evidence_ref_id"] == LOCKED_EVIDENCE_REF_ID
    assert seal["source_artifact_id"] == LOCKED_RECAP_ARTIFACT_ID
    assert seal["artifact_uri"] == LOCKED_RECAP_ARTIFACT_URI
    assert seal["artifact_content_sha256"] == LOCKED_ARTIFACT_CONTENT_SHA256
    assert seal["source_span_ref_id"] == LOCKED_SOURCE_SPAN_REF_ID
    assert seal["excerpt_sha256"] == LOCKED_EXCERPT_SHA256

    adj = json.loads(ADJUDICATION_PATH.read_text(encoding="utf-8"))
    rows = adj["records"]
    assert isinstance(rows, list)
    row = next(r for r in rows if r.get("edge_id") == TARGET_EDGE_ID)
    assert row["disposition"] == "SOURCE_CORRECTION_REQUIRED"
    assert row["reason_code"] == "PREDICATE_MISAPPLIED"
    assert row["responsible_repo"] == "DungeonMindBuddy"
    assert row["next_action"] == "AUTHOR_BUDDY_SOURCE_CORRECTION"
    assert row["requires_source_mutation"] is True
    assert row["primary_evidence_ref_id"] == LOCKED_EVIDENCE_REF_ID
    assert row["source_artifact_id"] == LOCKED_RECAP_ARTIFACT_ID
    assert row["source_span_ref_id"] == LOCKED_SOURCE_SPAN_REF_ID
    assert row["excerpt_sha256"] == LOCKED_EXCERPT_SHA256


def test_approved_correction_artifact_locks_identity_and_targets() -> None:
    contribution = load_approved_session25_ephanna_thrin_false_hires_correction(
        repo=REPO
    )
    digest = kernel.compute_contribution_source_payload_sha256(contribution)
    raw = (REPO / APPROVED_CORRECTION_RELPATH).read_bytes()
    assert hashlib.sha256(raw).hexdigest() == LOCKED_CORRECTION_RAW_ARTIFACT_SHA256
    assert contribution.contribution_id == LOCKED_CORRECTION_CONTRIBUTION_ID
    assert digest == LOCKED_CORRECTION_SOURCE_PAYLOAD_SHA256
    assert (
        kernel.compute_correction_digest(contribution.assertion_corrections)
        == LOCKED_CORRECTION_DIGEST
    )
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
    seal_dst = dst_repo / svc.SOURCE_SEAL_RELPATH
    seal_dst.parent.mkdir(parents=True)
    seal_dst.write_bytes(SOURCE_SEAL_PATH.read_bytes())
    adj_dst = dst_repo / svc.ADJUDICATION_RELPATH
    adj_dst.parent.mkdir(parents=True, exist_ok=True)
    adj_dst.write_bytes(ADJUDICATION_PATH.read_bytes())
    with pytest.raises(Session25EphannaThrinFalseHiresCorrectionError) as exc:
        load_approved_session25_ephanna_thrin_false_hires_correction(repo=dst_repo)
    assert exc.value.code == "integrity_failure"
    st = get_session25_ephanna_thrin_false_hires_correction_status(
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
    with pytest.raises(Session25EphannaThrinFalseHiresCorrectionError) as exc:
        load_approved_session25_ephanna_thrin_false_hires_correction(repo=dst_repo)
    assert exc.value.code == "integrity_failure"


def test_real_clone_status_is_eligible(tmp_path: Path) -> None:
    root = _clone_eldyrwild(tmp_path)
    status = get_session25_ephanna_thrin_false_hires_correction_status(
        root=root, repo=REPO
    )
    assert status.eligibility == "eligible"
    assert status.head_revision_id == R_CURRENT_REVISION_ID
    assert status.continuity_state in {"ANCHOR", "CARRIED_FORWARD"}
    assert status.source_grounding_verified is True
    assert status.durable_shape_verified is True
    assert status.target_edge_id == TARGET_EDGE_ID
    assert status.correction_contribution_id == LOCKED_CORRECTION_CONTRIBUTION_ID
    assert "Session-25" in (status.reason or "")
    assert "Session-24" not in (status.reason or "")


def test_composed_s25_authority_grounds_target_not_historical_a(
    tmp_path: Path,
) -> None:
    """Eligibility authority is composed S25, not historical A residual findings."""
    root = _clone_eldyrwild(tmp_path)
    parent = get_session25_ephanna_thrin_false_hires_correction_status(
        root=root, repo=REPO
    ).head_revision_id
    assert parent == ELIGIBLE_PARENT_REVISION_ID
    assert TARGET_EDGE_ID not in ELDYRWILD_RESIDUAL_FINDINGS

    composed = analyze_composed_relationship_adjudication_authority_v1(
        root=root,
        world_id=ELDYRWILD_WORLD_ID,
        revision_id=parent,
        verify_excerpt=True,
    )
    assert composed.historical_a_row_count == 59
    assert composed.session25_descendant_row_count == 7
    s25_row = next(
        r
        for r in composed.rows
        if r.edge_id == TARGET_EDGE_ID
        and r.authority_id == SESSION25_DESCENDANT_AUTHORITY_ID
    )
    assert s25_row.continuity_state in {"ANCHOR", "CARRIED_FORWARD"}
    assert s25_row.source_grounding_verified is True
    assert s25_row.durable_shape_verified is True
    assert s25_row.finding.disposition.value == "SOURCE_CORRECTION_REQUIRED"
    assert not any(
        r.edge_id == TARGET_EDGE_ID and r.authority_id == HISTORICAL_A_AUTHORITY_ID
        for r in composed.rows
    )


def test_stale_parent_fails_closed(tmp_path: Path) -> None:
    root = _clone_eldyrwild(tmp_path)
    status = get_session25_ephanna_thrin_false_hires_correction_status(
        root=root, repo=REPO
    )
    parent = status.head_revision_id
    assert parent
    store = kernel.load_world_graph_revision(root, ELDYRWILD_WORLD_ID, parent)
    store.nodes["npc:session25-hires-stale-probe"] = UnionSupergraphNode(
        node_id="npc:session25-hires-stale-probe",
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
        operation_ids=["op:session25-hires-stale-parent-probe"],
    ).revision.revision_id
    assert advanced != parent
    with pytest.raises(Session25EphannaThrinFalseHiresCorrectionError) as exc:
        apply_session25_ephanna_thrin_false_hires_correction(
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
    with pytest.raises(Session25EphannaThrinFalseHiresCorrectionError) as exc:
        apply_session25_ephanna_thrin_false_hires_correction(
            expected_parent_revision_id=head,
            root=root,
            repo=REPO,
            allow_live_world=False,
        )
    assert exc.value.code == "live_world_opt_in_required"
    st = get_session25_ephanna_thrin_false_hires_correction_status(
        root=root, repo=REPO
    )
    assert st.eligibility == "eligible"


def test_active_support_mismatch_is_ineligible(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    root = _clone_eldyrwild(tmp_path)
    head, revision, store = kernel.open_current_world_graph(root, ELDYRWILD_WORLD_ID)
    assert head.head_revision_id == R_CURRENT_REVISION_ID
    support = dict(store.assertion_support[TARGET_ASSERTION_ID])
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

    monkeypatch.setattr(
        kernel,
        "open_current_world_graph",
        lambda *args, **kwargs: (head, revision, store),
    )
    st = get_session25_ephanna_thrin_false_hires_correction_status(
        root=root, expected_parent_revision_id=head.head_revision_id, repo=REPO
    )
    assert st.eligibility == "ineligible"
    assert "active_support_mismatch_locked_c" in st.diagnostics


def test_outsider_support_is_ineligible(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    root = _clone_eldyrwild(tmp_path)
    head, revision, store = kernel.open_current_world_graph(root, ELDYRWILD_WORLD_ID)
    support = dict(store.assertion_support[TARGET_ASSERTION_ID])
    outsider = "contribution:outsider-session25-hires-support"
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
    monkeypatch.setattr(
        kernel,
        "open_current_world_graph",
        lambda *args, **kwargs: (head, revision, store),
    )
    st = get_session25_ephanna_thrin_false_hires_correction_status(
        root=root, expected_parent_revision_id=head.head_revision_id, repo=REPO
    )
    assert st.eligibility == "ineligible"
    assert "active_support_mismatch_locked_c" in st.diagnostics


def test_second_active_edge_assertion_id_is_ineligible(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """A second supported assertion ID on X₄ must fail closed before mutate.

    Distinct from multi-contributor support on the same assertion ID: the Kernel
    keeps the edge current when any other edge-kind assertion shares
    ``graph_object_id`` and remains supported with active contributors.
    """
    root = _clone_eldyrwild(tmp_path)
    head, revision, store = kernel.open_current_world_graph(root, ELDYRWILD_WORLD_ID)
    locked = next(iter(LOCKED_TARGET_CONTRIBUTION_IDS))
    primary = dict(store.assertion_support[TARGET_ASSERTION_ID])
    twin_id = "assertion:adversary-second-ephanna-hires-identity"
    twin = {
        **primary,
        "assertion_id": twin_id,
        "active_contribution_ids": [locked],
        "support_state": "supported",
        "assertion_kind": "edge",
        "graph_object_id": TARGET_EDGE_ID,
        "introduced_by_contribution_id": locked,
        "per_contribution_evidence_ref_ids": {
            locked: list(primary.get("evidence_ref_ids") or [])
        },
        "per_contribution_source_artifact_ids": {
            locked: list(primary.get("source_artifact_ids") or [])
        },
    }
    store.assertion_support[twin_id] = twin
    assert svc._active_edge_assertion_ids(store, TARGET_EDGE_ID) == {
        TARGET_ASSERTION_ID,
        twin_id,
    }
    monkeypatch.setattr(
        kernel,
        "open_current_world_graph",
        lambda *args, **kwargs: (head, revision, store),
    )
    st = get_session25_ephanna_thrin_false_hires_correction_status(
        root=root, expected_parent_revision_id=head.head_revision_id, repo=REPO
    )
    assert st.eligibility == "ineligible"
    assert "target_edge_active_assertion_ids_not_singleton" in st.diagnostics


def test_target_source_ledger_digest_drift_fails_before_publish(tmp_path: Path) -> None:
    """Mutable A(X₄) ledger digest drift vs Q₃ revision-bound seal must fail closed."""
    root = _clone_eldyrwild(tmp_path)
    parent = get_session25_ephanna_thrin_false_hires_correction_status(
        root=root, repo=REPO
    ).head_revision_id
    assert parent == ELIGIBLE_PARENT_REVISION_ID

    store_before = kernel.load_world_graph_revision(root, ELDYRWILD_WORLD_ID, parent)
    digests_before = dict(store_before.contribution_source_payload_sha256 or {})
    assert digests_before.get(_LOCKED_SOURCE_CONTRIBUTION_ID) == (
        LOCKED_TARGET_CONTRIBUTION_SOURCE_PAYLOAD_SHA256
    )

    ledger = load_contribution_record(
        root, ELDYRWILD_WORLD_ID, _LOCKED_SOURCE_CONTRIBUTION_ID
    )
    tampered = ledger.model_copy(update={"authored_by": "not-gm"})
    assert (
        kernel.compute_contribution_source_payload_sha256(tampered)
        != LOCKED_TARGET_CONTRIBUTION_SOURCE_PAYLOAD_SHA256
    )
    write_contribution_record(root, ELDYRWILD_WORLD_ID, tampered)

    store_after = kernel.load_world_graph_revision(root, ELDYRWILD_WORLD_ID, parent)
    assert dict(store_after.contribution_source_payload_sha256 or {}) == digests_before

    st = get_session25_ephanna_thrin_false_hires_correction_status(
        root=root, expected_parent_revision_id=parent, repo=REPO
    )
    assert st.eligibility == "integrity_failure"
    assert "target_source_mutable_digest_mismatch" in st.diagnostics
    before = snapshot_world_graph_tree_digest(root, ELDYRWILD_WORLD_ID)
    with pytest.raises(Session25EphannaThrinFalseHiresCorrectionError) as exc:
        apply_session25_ephanna_thrin_false_hires_correction(
            expected_parent_revision_id=parent,
            root=root,
            repo=REPO,
        )
    assert exc.value.code == "integrity_failure"
    assert snapshot_world_graph_tree_digest(root, ELDYRWILD_WORLD_ID) == before
    head, _, _ = kernel.open_current_world_graph(root, ELDYRWILD_WORLD_ID)
    assert head.head_revision_id == parent


def test_target_source_index_drift_after_apply_is_integrity_failure(
    tmp_path: Path,
) -> None:
    """Post-C₄ index/lifecycle drift of A(X₄) must not report already_applied."""
    root = _clone_eldyrwild(tmp_path)
    parent = get_session25_ephanna_thrin_false_hires_correction_status(
        root=root, repo=REPO
    ).head_revision_id
    assert parent
    result = apply_session25_ephanna_thrin_false_hires_correction(
        expected_parent_revision_id=parent,
        root=root,
        repo=REPO,
    )
    child = result.revision_id
    assert child
    assert (
        get_session25_ephanna_thrin_false_hires_correction_status(
            root=root, expected_parent_revision_id=child, repo=REPO
        ).eligibility
        == "already_applied"
    )

    store_before = kernel.load_world_graph_revision(root, ELDYRWILD_WORLD_ID, child)
    digests_before = dict(store_before.contribution_source_payload_sha256 or {})
    assert digests_before.get(_LOCKED_SOURCE_CONTRIBUTION_ID) == (
        LOCKED_TARGET_CONTRIBUTION_SOURCE_PAYLOAD_SHA256
    )
    ledger_path = world_paths.contribution_path(
        root, ELDYRWILD_WORLD_ID, _LOCKED_SOURCE_CONTRIBUTION_ID
    )
    ledger_bytes_before = ledger_path.read_bytes()

    index = load_contribution_index(root, ELDYRWILD_WORLD_ID)
    assert _LOCKED_SOURCE_CONTRIBUTION_ID in set(index.active_contribution_ids)
    index = index.model_copy(
        update={
            "active_contribution_ids": [
                x
                for x in index.active_contribution_ids
                if x != _LOCKED_SOURCE_CONTRIBUTION_ID
            ],
            "retracted_contribution_ids": sorted(
                set(index.retracted_contribution_ids)
                | {_LOCKED_SOURCE_CONTRIBUTION_ID}
            ),
        }
    )
    save_contribution_index(root, ELDYRWILD_WORLD_ID, index)

    store_after = kernel.load_world_graph_revision(root, ELDYRWILD_WORLD_ID, child)
    assert dict(store_after.contribution_source_payload_sha256 or {}) == digests_before
    assert ledger_path.read_bytes() == ledger_bytes_before
    assert svc._active_edge_assertion_ids(store_after, TARGET_EDGE_ID) == set()

    st = get_session25_ephanna_thrin_false_hires_correction_status(
        root=root, expected_parent_revision_id=child, repo=REPO
    )
    assert st.eligibility == "integrity_failure"
    assert "target_source_index_not_active" in st.diagnostics
    assert "target_source_index_retracted" in st.diagnostics

    before = snapshot_world_graph_tree_digest(root, ELDYRWILD_WORLD_ID)
    with pytest.raises(Session25EphannaThrinFalseHiresCorrectionError) as exc:
        apply_session25_ephanna_thrin_false_hires_correction(
            expected_parent_revision_id=child,
            root=root,
            repo=REPO,
        )
    assert exc.value.code == "integrity_failure"
    assert snapshot_world_graph_tree_digest(root, ELDYRWILD_WORLD_ID) == before
    head, _, _ = kernel.open_current_world_graph(root, ELDYRWILD_WORLD_ID)
    assert head.head_revision_id == child


def test_remaining_active_edge_assertion_after_apply_is_integrity_failure(
    tmp_path: Path,
) -> None:
    """already_applied must fail if a second active edge assertion still defines X₄."""
    root = _clone_eldyrwild(tmp_path)
    parent = get_session25_ephanna_thrin_false_hires_correction_status(
        root=root, repo=REPO
    ).head_revision_id
    assert parent
    result = apply_session25_ephanna_thrin_false_hires_correction(
        expected_parent_revision_id=parent,
        root=root,
        repo=REPO,
    )
    child = result.revision_id
    assert child

    store = kernel.load_world_graph_revision(root, ELDYRWILD_WORLD_ID, child)
    locked = next(iter(LOCKED_TARGET_CONTRIBUTION_IDS))
    primary = dict(store.assertion_support[TARGET_ASSERTION_ID])
    twin_id = "assertion:adversary-post-c4-surviving-hires"
    store.assertion_support[twin_id] = {
        **primary,
        "assertion_id": twin_id,
        "support_state": "supported",
        "assertion_kind": "edge",
        "graph_object_id": TARGET_EDGE_ID,
        "active_contribution_ids": [locked],
        "contradicted_contribution_ids": [],
        "introduced_by_contribution_id": locked,
        "per_contribution_evidence_ref_ids": {
            locked: list(primary.get("evidence_ref_ids") or [])
        },
        "per_contribution_source_artifact_ids": {
            locked: list(primary.get("source_artifact_ids") or [])
        },
    }
    advanced = kernel.publish_world_revision(
        root,
        ELDYRWILD_WORLD_ID,
        store,
        operation_ids=["op:session25-hires-surviving-second-assertion"],
    ).revision.revision_id

    st = get_session25_ephanna_thrin_false_hires_correction_status(
        root=root, expected_parent_revision_id=advanced, repo=REPO
    )
    assert st.eligibility == "integrity_failure"
    assert st.eligibility != "already_applied"
    assert "target_edge_still_has_active_assertions" in st.diagnostics


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
    st = get_session25_ephanna_thrin_false_hires_correction_status(
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
        operation_ids=["op:session25-hires-false-already-applied-probe"],
    ).revision.revision_id
    st = get_session25_ephanna_thrin_false_hires_correction_status(
        root=root, expected_parent_revision_id=advanced, repo=REPO
    )
    assert st.eligibility == "integrity_failure"
    assert st.eligibility != "already_applied"


def test_retry_without_replay_manifest_entry_fails_closed(tmp_path: Path) -> None:
    root = _clone_eldyrwild(tmp_path)
    parent = get_session25_ephanna_thrin_false_hires_correction_status(
        root=root, repo=REPO
    ).head_revision_id
    assert parent
    result = apply_session25_ephanna_thrin_false_hires_correction(
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
    digests = dict(store.contribution_source_payload_sha256 or {})
    assert digests.get(LOCKED_CORRECTION_CONTRIBUTION_ID) == (
        LOCKED_CORRECTION_SOURCE_PAYLOAD_SHA256
    )
    adversarial = kernel.publish_world_revision(
        root,
        ELDYRWILD_WORLD_ID,
        store,
        operation_ids=["op:session25-hires-strip-manifest-c"],
    ).revision.revision_id

    st = get_session25_ephanna_thrin_false_hires_correction_status(
        root=root, expected_parent_revision_id=adversarial, repo=REPO
    )
    assert st.eligibility == "integrity_failure"
    assert st.eligibility != "already_applied"
    with pytest.raises(Session25EphannaThrinFalseHiresCorrectionError) as exc:
        apply_session25_ephanna_thrin_false_hires_correction(
            expected_parent_revision_id=adversarial,
            root=root,
            repo=REPO,
        )
    assert exc.value.code == "integrity_failure"


def test_kernel_partial_multi_support_coverage_fails_before_mutation(
    tmp_path: Path,
) -> None:
    """A(X₄) is currently singleton; still prove #544 multi-support partial gate."""
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
    superseded = [
        x for x in (support.get("superseded_contribution_ids") or []) if x != second
    ]
    support["superseded_contribution_ids"] = superseded
    store.assertion_support[TARGET_ASSERTION_ID] = support
    multi = kernel.publish_world_revision(
        root,
        ELDYRWILD_WORLD_ID,
        store,
        operation_ids=["op:session25-hires-multi-support-partial-probe"],
    ).revision.revision_id

    before = snapshot_world_graph_tree_digest(root, ELDYRWILD_WORLD_ID)
    before_index = load_contribution_index(root, ELDYRWILD_WORLD_ID)
    partial = kernel.create_edge_assertion_contradiction_contribution(
        world_id=ELDYRWILD_WORLD_ID,
        authored_by="gm",
        target_assertion_id=TARGET_ASSERTION_ID,
        target_contribution_ids=[locked],
        source_artifact_id=(
            "graph-native:eldyrwild-correction:session25-hires-partial-adversary"
        ),
        source_revision_id="correction:eldyrwild:session25-hires-partial-adversary",
        campaign_scope=CAMPAIGN_ID,
        produced_at="2026-08-11T18:00:00Z",
    )
    result = kernel.contradict_edge_assertion_support(
        root,
        world_id=ELDYRWILD_WORLD_ID,
        contribution=partial,
        expected_parent_revision_id=multi,
    )
    assert result.published is False
    assert result.failure_code in {None, "correction_rejected", "correction_integrity_failure"}
    # Fail closed before durable mutation regardless of which Kernel gate fires.
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
    assert seal_before == LOCKED_SOURCE_SEALS_SHA256
    assert adj_before == LOCKED_ADJUDICATION_SHA256
    canonical_before = snapshot_world_graph_tree_digest(
        world_graph_root(), ELDYRWILD_WORLD_ID
    )

    status = get_session25_ephanna_thrin_false_hires_correction_status(
        root=root, repo=REPO
    )
    assert status.eligibility == "eligible"
    parent = status.head_revision_id
    assert parent == R_CURRENT_REVISION_ID
    assert parent == ELIGIBLE_PARENT_REVISION_ID

    parent_manifest = kernel.load_world_graph_revision_manifest(
        root, ELDYRWILD_WORLD_ID, parent
    )
    assert parent_manifest.graph_payload_sha256 == ELIGIBLE_PARENT_PAYLOAD_SHA256

    assert (
        get_lysandra_threat_direction_correction_status(root=root).eligibility
        == "already_applied"
    )
    assert (
        get_session24_cube_karsemine_false_location_correction_status(
            root=root
        ).eligibility
        == "already_applied"
    )
    assert (
        get_session24_lysandra_caelynn_false_leads_correction_status(
            root=root
        ).eligibility
        == "already_applied"
    )

    _assert_rebuild_equivalent(root, parent)

    store_p = kernel.load_world_graph_revision(root, ELDYRWILD_WORLD_ID, parent)
    siblings_p = _sibling_support_fingerprint(store_p)
    contrib_siblings_p = _contribution_support_fingerprint(
        root, store_p, _LOCKED_SOURCE_CONTRIBUTION_ID
    )
    assert TARGET_ASSERTION_ID in siblings_p
    assert TARGET_ASSERTION_ID in contrib_siblings_p
    assert store_p.assertion_support[TARGET_ASSERTION_ID]["support_state"] == "supported"
    active_p = set(
        store_p.assertion_support[TARGET_ASSERTION_ID].get("active_contribution_ids")
        or []
    )
    assert active_p == LOCKED_TARGET_CONTRIBUTION_IDS
    assert svc._active_edge_assertion_ids(store_p, TARGET_EDGE_ID) == {
        TARGET_ASSERTION_ID
    }
    digests_p = store_p.contribution_source_payload_sha256 or {}
    source_ok_p, source_diag_p = (
        svc._verify_locked_target_source_contribution_authority(
            root=root, store=store_p
        )
    )
    assert source_ok_p, source_diag_p
    assert digests_p.get(_LOCKED_SOURCE_CONTRIBUTION_ID) == (
        LOCKED_TARGET_CONTRIBUTION_SOURCE_PAYLOAD_SHA256
    )
    assert C2_TARGET_ASSERTION_ID in siblings_p
    assert siblings_p[C2_TARGET_ASSERTION_ID]["support_state"] == "contradicted"
    assert not (siblings_p[C2_TARGET_ASSERTION_ID].get("active_contribution_ids") or [])
    assert C3_TARGET_ASSERTION_ID in siblings_p
    assert siblings_p[C3_TARGET_ASSERTION_ID]["support_state"] == "contradicted"
    assert not (siblings_p[C3_TARGET_ASSERTION_ID].get("active_contribution_ids") or [])
    assert digests_p.get(C1_CORRECTION_CONTRIBUTION_ID) == (
        C1_CORRECTION_SOURCE_PAYLOAD_SHA256
    )
    assert digests_p.get(C2_CORRECTION_CONTRIBUTION_ID) == (
        C2_CORRECTION_SOURCE_PAYLOAD_SHA256
    )
    assert digests_p.get(C3_CORRECTION_CONTRIBUTION_ID) == (
        C3_CORRECTION_SOURCE_PAYLOAD_SHA256
    )

    for edge_id in PRESERVED_SIBLING_U_EDGE_IDS:
        assert edge_id in store_p.edges
        assert edge_id != TARGET_EDGE_ID

    before_p = snapshot_world_graph_tree_digest(root, ELDYRWILD_WORLD_ID)
    eff_p = analyze_relationship_effective_conformance_v1(
        root=root, world_id=ELDYRWILD_WORLD_ID, revision_id=parent
    )
    assert snapshot_world_graph_tree_digest(root, ELDYRWILD_WORLD_ID) == before_p
    assert TARGET_EDGE_ID in eff_p.remaining_residual_edge_ids
    residual_p = set(eff_p.remaining_residual_edge_ids)

    for cid in sorted(LOCKED_TARGET_CONTRIBUTION_IDS):
        ledger = load_contribution_record(root, ELDYRWILD_WORLD_ID, cid)
        assert ledger.status == "active"

    result = apply_session25_ephanna_thrin_false_hires_correction(
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
    assert svc._active_edge_assertion_ids(store_q, TARGET_EDGE_ID) == set()

    digests = store_q.contribution_source_payload_sha256 or {}
    assert digests.get(LOCKED_CORRECTION_CONTRIBUTION_ID) == (
        LOCKED_CORRECTION_SOURCE_PAYLOAD_SHA256
    )
    assert digests.get(_LOCKED_SOURCE_CONTRIBUTION_ID) == (
        LOCKED_TARGET_CONTRIBUTION_SOURCE_PAYLOAD_SHA256
    )
    source_ok_q, source_diag_q = (
        svc._verify_locked_target_source_contribution_authority(
            root=root, store=store_q
        )
    )
    assert source_ok_q, source_diag_q
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

    contrib_siblings_q = _contribution_support_fingerprint(
        root, store_q, _LOCKED_SOURCE_CONTRIBUTION_ID
    )
    for assertion_id, before_row in contrib_siblings_p.items():
        if assertion_id == TARGET_ASSERTION_ID:
            continue
        assert contrib_siblings_q.get(assertion_id) == before_row

    # U1–U6 remain current/supported after C₄.
    for edge_id in PRESERVED_SIBLING_U_EDGE_IDS:
        assert edge_id in store_q.edges
        matching = [
            aid
            for aid, support in store_q.assertion_support.items()
            if isinstance(support, dict) and support.get("graph_object_id") == edge_id
        ]
        assert matching, f"missing assertion_support for preserved edge {edge_id}"
        for aid in matching:
            support = store_q.assertion_support[aid]
            assert support.get("support_state") == "supported"
            assert list(support.get("active_contribution_ids") or [])

    # C₂/C₃ sibling corrections remain intact; C₁–C₃ digests remain revision-bound.
    assert C2_TARGET_EDGE_ID in store_q.edges
    c2_support = store_q.assertion_support[C2_TARGET_ASSERTION_ID]
    assert c2_support["support_state"] == "contradicted"
    assert not (c2_support.get("active_contribution_ids") or [])
    assert C3_TARGET_EDGE_ID in store_q.edges
    c3_support = store_q.assertion_support[C3_TARGET_ASSERTION_ID]
    assert c3_support["support_state"] == "contradicted"
    assert not (c3_support.get("active_contribution_ids") or [])
    digests_q = store_q.contribution_source_payload_sha256 or {}
    assert digests_q.get(C1_CORRECTION_CONTRIBUTION_ID) == (
        C1_CORRECTION_SOURCE_PAYLOAD_SHA256
    )
    assert digests_q.get(C2_CORRECTION_CONTRIBUTION_ID) == (
        C2_CORRECTION_SOURCE_PAYLOAD_SHA256
    )
    assert digests_q.get(C3_CORRECTION_CONTRIBUTION_ID) == (
        C3_CORRECTION_SOURCE_PAYLOAD_SHA256
    )
    assert (
        get_lysandra_threat_direction_correction_status(root=root).eligibility
        == "already_applied"
    )
    assert (
        get_session24_cube_karsemine_false_location_correction_status(
            root=root
        ).eligibility
        == "already_applied"
    )
    assert (
        get_session24_lysandra_caelynn_false_leads_correction_status(
            root=root
        ).eligibility
        == "already_applied"
    )

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
    assert eff_p.relationship_semantic_count == 367
    assert eff_p.relationship_effectively_represented_count == 311
    assert eff_p.relationship_effective_residual_count == 56
    assert eff_p.uses_statblock_mechanics_count == 3
    assert eff_q.relationship_semantic_count == 366
    assert eff_q.relationship_effectively_represented_count == 311
    assert eff_q.relationship_effective_residual_count == 55
    assert eff_q.uses_statblock_mechanics_count == 3
    assert (
        eff_q.base_relationship_residual_count
        == eff_p.base_relationship_residual_count - 1
    )
    assert (
        eff_q.dungeonmindbuddy_owned_remaining_count
        == eff_p.dungeonmindbuddy_owned_remaining_count - 1
    )
    dispositions = {
        row.key: row.count for row in eff_q.remaining_residual_disposition_inventory
    }
    assert dispositions == _EXPECTED_POST_C4_REMAINING_DISPOSITIONS

    # Composed continuity at Q₄: S25 still 7 rows, X₄ CARRIED_FORWARD, A still 59.
    composed_q = analyze_composed_relationship_adjudication_authority_v1(
        root=root,
        world_id=ELDYRWILD_WORLD_ID,
        revision_id=child,
        verify_excerpt=True,
    )
    assert composed_q.historical_a_row_count == 59
    assert composed_q.session25_descendant_row_count == 7
    assert composed_q.composed_row_count == 66
    x4_row = next(
        r
        for r in composed_q.rows
        if r.edge_id == TARGET_EDGE_ID
        and r.authority_id == SESSION25_DESCENDANT_AUTHORITY_ID
    )
    assert x4_row.continuity_state == "CARRIED_FORWARD"
    assert set(PRESERVED_SIBLING_U_EDGE_IDS) <= {
        r.edge_id
        for r in composed_q.rows
        if r.authority_id == SESSION25_DESCENDANT_AUTHORITY_ID
    }

    _assert_rebuild_equivalent(root, child)

    retry = apply_session25_ephanna_thrin_false_hires_correction(
        expected_parent_revision_id=child,
        root=root,
        repo=REPO,
    )
    assert retry.published is False
    assert retry.eligibility == "already_applied"
    assert retry.revision_id == child
    head, _, _ = kernel.open_current_world_graph(root, ELDYRWILD_WORLD_ID)
    assert head.head_revision_id == child
    status_after = get_session25_ephanna_thrin_false_hires_correction_status(
        root=root, repo=REPO
    )
    assert status_after.eligibility == "already_applied"

    with pytest.raises(Session25EphannaThrinFalseHiresCorrectionError) as stale_exc:
        apply_session25_ephanna_thrin_false_hires_correction(
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
    parent = get_session25_ephanna_thrin_false_hires_correction_status(
        root=root, repo=REPO
    ).head_revision_id
    assert parent
    result = apply_session25_ephanna_thrin_false_hires_correction(
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
    st = get_session25_ephanna_thrin_false_hires_correction_status(
        root=root, expected_parent_revision_id=child, repo=REPO
    )
    assert st.eligibility == "integrity_failure"


def test_c_ledger_inactive_is_integrity_failure(tmp_path: Path) -> None:
    root = _clone_eldyrwild(tmp_path)
    parent = get_session25_ephanna_thrin_false_hires_correction_status(
        root=root, repo=REPO
    ).head_revision_id
    assert parent
    result = apply_session25_ephanna_thrin_false_hires_correction(
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
    st = get_session25_ephanna_thrin_false_hires_correction_status(
        root=root, expected_parent_revision_id=child, repo=REPO
    )
    assert st.eligibility == "integrity_failure"


def test_c_index_only_split_brain_is_integrity_failure(tmp_path: Path) -> None:
    """Index-only reclassification must not report already_applied.

    Leaves Q₄ revision digest, replay manifest, ledger bytes/status, and
    contradicted target shape intact while dropping C₄ from the mutable
    contribution index (or classifying it retracted there).
    """
    root = _clone_eldyrwild(tmp_path)
    parent = get_session25_ephanna_thrin_false_hires_correction_status(
        root=root, repo=REPO
    ).head_revision_id
    assert parent
    result = apply_session25_ephanna_thrin_false_hires_correction(
        expected_parent_revision_id=parent,
        root=root,
        repo=REPO,
    )
    child = result.revision_id
    assert child
    assert (
        get_session25_ephanna_thrin_false_hires_correction_status(
            root=root, expected_parent_revision_id=child, repo=REPO
        ).eligibility
        == "already_applied"
    )

    store_before = kernel.load_world_graph_revision(root, ELDYRWILD_WORLD_ID, child)
    digests_before = dict(store_before.contribution_source_payload_sha256 or {})
    assert digests_before.get(LOCKED_CORRECTION_CONTRIBUTION_ID) == (
        LOCKED_CORRECTION_SOURCE_PAYLOAD_SHA256
    )
    ledger_path = world_paths.contribution_path(
        root, ELDYRWILD_WORLD_ID, LOCKED_CORRECTION_CONTRIBUTION_ID
    )
    ledger_bytes_before = ledger_path.read_bytes()
    ledger_before = load_contribution_record(
        root, ELDYRWILD_WORLD_ID, LOCKED_CORRECTION_CONTRIBUTION_ID
    )
    assert ledger_before.status == "active"

    index = load_contribution_index(root, ELDYRWILD_WORLD_ID)
    assert LOCKED_CORRECTION_CONTRIBUTION_ID in set(index.active_contribution_ids)
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

    store_after_tamper = kernel.load_world_graph_revision(
        root, ELDYRWILD_WORLD_ID, child
    )
    assert dict(store_after_tamper.contribution_source_payload_sha256 or {}) == (
        digests_before
    )
    assert ledger_path.read_bytes() == ledger_bytes_before
    ledger_after_tamper = load_contribution_record(
        root, ELDYRWILD_WORLD_ID, LOCKED_CORRECTION_CONTRIBUTION_ID
    )
    assert ledger_after_tamper.status == "active"
    assert (
        kernel.compute_contribution_source_payload_sha256(ledger_after_tamper)
        == LOCKED_CORRECTION_SOURCE_PAYLOAD_SHA256
    )
    x_support = store_after_tamper.assertion_support[TARGET_ASSERTION_ID]
    assert x_support["support_state"] == "contradicted"
    assert not (x_support.get("active_contribution_ids") or [])
    manifest_hit = False
    for entry in store_after_tamper.contribution_replay_manifest or []:
        cid = getattr(entry, "contribution_id", None)
        status_m = getattr(entry, "status", None)
        digest_m = getattr(entry, "source_payload_sha256", None)
        if cid == LOCKED_CORRECTION_CONTRIBUTION_ID:
            assert status_m == "active"
            assert digest_m == LOCKED_CORRECTION_SOURCE_PAYLOAD_SHA256
            manifest_hit = True
    assert manifest_hit

    st = get_session25_ephanna_thrin_false_hires_correction_status(
        root=root, expected_parent_revision_id=child, repo=REPO
    )
    assert st.eligibility == "integrity_failure"
    assert "mutable_C_index_not_active" in st.diagnostics
    assert "mutable_C_index_retracted" in st.diagnostics

    before = snapshot_world_graph_tree_digest(root, ELDYRWILD_WORLD_ID)
    before_index = load_contribution_index(root, ELDYRWILD_WORLD_ID)
    with pytest.raises(Session25EphannaThrinFalseHiresCorrectionError) as exc:
        apply_session25_ephanna_thrin_false_hires_correction(
            expected_parent_revision_id=child,
            root=root,
            repo=REPO,
        )
    assert exc.value.code == "integrity_failure"
    assert snapshot_world_graph_tree_digest(root, ELDYRWILD_WORLD_ID) == before
    after_index = load_contribution_index(root, ELDYRWILD_WORLD_ID)
    assert after_index.model_dump() == before_index.model_dump()
    head, _, _ = kernel.open_current_world_graph(root, ELDYRWILD_WORLD_ID)
    assert head.head_revision_id == child
    assert ledger_path.read_bytes() == ledger_bytes_before


def test_same_c_id_different_source_payload_fails_closed(tmp_path: Path) -> None:
    """Unbound mutable C with same ID but different digest must not be overwritten."""
    root = _clone_eldyrwild(tmp_path)
    parent = get_session25_ephanna_thrin_false_hires_correction_status(
        root=root, repo=REPO
    ).head_revision_id
    assert parent
    assert (
        get_session25_ephanna_thrin_false_hires_correction_status(
            root=root, repo=REPO
        ).eligibility
        == "eligible"
    )

    approved = load_approved_session25_ephanna_thrin_false_hires_correction(
        repo=REPO
    )
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

    st = get_session25_ephanna_thrin_false_hires_correction_status(
        root=root, expected_parent_revision_id=parent, repo=REPO
    )
    assert st.eligibility == "integrity_failure"
    assert "mutable_C_source_digest_collision" in st.diagnostics

    with pytest.raises(Session25EphannaThrinFalseHiresCorrectionError) as exc:
        apply_session25_ephanna_thrin_false_hires_correction(
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
