"""Tests for C1 additive World Graph apply (PC world-ownership + Heroes + S1–S3)."""

# PR003_INTERNAL_GRAPH_KERNEL_EXEMPTION: fixture ledger mutation for additive-apply
# proof; keep until tests move fully onto kernel contribution helpers.

from __future__ import annotations

import json
from pathlib import Path

import pytest
from pydantic import ValidationError

import graph_memory.kernel as kernel
from apps.live_control_server.services.c1_world_graph_additive_apply import (
    APPROVED_C1_BUNDLE_DIGEST,
    APPROVED_C1_BUNDLE_ID,
    APPROVED_ORDERED_CONTRIBUTION_IDS,
    C1AdditiveApplyError,
    apply_approved_c1_additive_bundle,
    get_c1_additive_apply_status,
    load_approved_c1_additive_bundle,
)
from graph_memory.contribution_bundles import load_contribution_bundle
from graph_memory.kernel.contribution_models import GraphContributionAssertion
from graph_memory.kernel.world_initialization import initialize_world_from_contributions
from graph_memory.kernel.world_initialization_models import (
    PLAN_SCHEMA,
    WorldInitializationApprovalAttestation,
    WorldInitializationContribution,
    WorldInitializationPlan,
)
from graph_memory.kernel.world_projection import WorldGraphProjectionError
from graph_memory.projection.world_projection import (
    PROJECTION_REQUEST_SCHEMA,
    WorldGraphProjectionFocus,
    WorldGraphProjectionRequest,
)
from graph_memory.union_supergraph.model import ContributionReplayManifestEntry
from graph_memory.world_supergraph.contribution_store import (
    load_contribution_index,
    save_contribution_index,
)

REPO = Path(__file__).resolve().parents[1]
C2_BUNDLE = (
    REPO
    / "graph_data/approved_contribution_bundles/eldyrwild-longmont-c2-initial-v1"
)
WORLD_ID = "eldyrwild"
BUNDLE_DIGEST = (
    "5f8288d3052a9e59192884f2c35a13d51f665095d84cca2081a56638108d3fa5"
)
APPROVED_MERGE_SHA = "65ae001e0852d827ecd680200a965a576c705b1d"
ORDERED_CONTRIBUTION_IDS = [
    "contribution:82f23934d8eaca8a",
    "contribution:43782369bd717d32",
    "contribution:33d7cdb0ff623f28",
    "contribution:c086a0b72324ff16",
    "contribution:1227841724520c18",
    "contribution:022187fdefdf4557",
]


@pytest.fixture
def loaded_c2_bundle():
    return load_contribution_bundle(C2_BUNDLE)


def _attestation() -> WorldInitializationApprovalAttestation:
    return WorldInitializationApprovalAttestation(
        bundle_id="eldyrwild-longmont-c2-initial-v1",
        bundle_digest=BUNDLE_DIGEST,
        approved_bundle_merge_sha=APPROVED_MERGE_SHA,
    )


def _plan(bundle) -> WorldInitializationPlan:
    by_id = {c.contribution_id: c for c in bundle.contributions}
    return WorldInitializationPlan(
        schema=PLAN_SCHEMA,
        world_id=WORLD_ID,
        campaign_id="longmont-c2",
        focus_session_id="session-23",
        ordered_contributions=[
            WorldInitializationContribution(
                contribution_id=contribution_id,
                payload_sha256=kernel.compute_contribution_payload_sha256(
                    by_id[contribution_id]
                ),
            )
            for contribution_id in ORDERED_CONTRIBUTION_IDS
        ],
        approval_attestation=_attestation(),
    )


def _initialize_c2(root: Path, bundle) -> None:
    result = initialize_world_from_contributions(
        root,
        plan=_plan(bundle),
        contributions=list(bundle.contributions),
        actor="gm",
    )
    assert result.published is True


def _request(
    campaign_id: str,
    *,
    query_text: str | None = None,
) -> WorldGraphProjectionRequest:
    return WorldGraphProjectionRequest(
        schema=PROJECTION_REQUEST_SCHEMA,
        world_id=WORLD_ID,
        campaign_id=campaign_id,
        focus=WorldGraphProjectionFocus(kind="session", session_id="session-3"),
        admissibility="gm",
        query_text=query_text,
    )


def _apply_first_c1_step(root: Path) -> str:
    bundle = load_approved_c1_additive_bundle(REPO)
    first = bundle.contributions[0]
    head, _, _ = kernel.open_current_world_graph(root, WORLD_ID)
    supersede = kernel.supersede_graph_contribution(
        root,
        world_id=WORLD_ID,
        new_contribution=first,
        superseded_contribution_id="contribution:33d7cdb0ff623f28",
        expected_parent_revision_id=head.head_revision_id,
    )
    assert supersede.published is True
    return bundle.contributions[1].contribution_id


def test_load_approved_c1_bundle_parses() -> None:
    bundle = load_approved_c1_additive_bundle(REPO)
    assert bundle.manifest["bundle_id"] == APPROVED_C1_BUNDLE_ID
    assert bundle.digest == APPROVED_C1_BUNDLE_DIGEST
    assert [c.contribution_id for c in bundle.contributions] == list(
        APPROVED_ORDERED_CONTRIBUTION_IDS
    )
    assert bundle.contributions[0].supersedes_contribution_id == (
        "contribution:33d7cdb0ff623f28"
    )


def test_load_rejects_tampered_manifest_digest(tmp_path: Path) -> None:
    src = REPO / "graph_data/approved_contribution_bundles/eldyrwild-longmont-c1-s1-s3-v1"
    dst = tmp_path / "eldyrwild-longmont-c1-s1-s3-v1"
    for path in src.rglob("*"):
        if path.is_file():
            target = dst / path.relative_to(src)
            target.parent.mkdir(parents=True, exist_ok=True)
            target.write_bytes(path.read_bytes())
    manifest_path = dst / "manifest.json"
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    manifest["bundle_digest"] = "0" * 64
    manifest_path.write_text(json.dumps(manifest, indent=2) + "\n", encoding="utf-8")

    # Point loader at a fake repo root that contains the tampered bundle path.
    fake_repo = tmp_path
    # load uses repo_root / APPROVED_C1_BUNDLE_RELPATH; recreate that layout.
    nested = (
        fake_repo
        / "graph_data/approved_contribution_bundles/eldyrwild-longmont-c1-s1-s3-v1"
    )
    if nested != dst:
        nested.parent.mkdir(parents=True, exist_ok=True)
        if nested.exists():
            pass
        else:
            nested.symlink_to(dst, target_is_directory=True)

    with pytest.raises(C1AdditiveApplyError) as exc_info:
        load_approved_c1_additive_bundle(fake_repo)
    assert exc_info.value.code == "invalid_bundle"
    assert "bundle_digest" in str(exc_info.value)


def test_apply_c1_additive_makes_pcs_world_owned_and_c1_visible(
    tmp_path: Path,
    loaded_c2_bundle,
) -> None:
    _initialize_c2(tmp_path, loaded_c2_bundle)
    status_before = get_c1_additive_apply_status(root=tmp_path, repo=REPO)
    assert status_before.head_present is True
    assert status_before.already_applied is False

    result = apply_approved_c1_additive_bundle(
        actor="gm",
        root=tmp_path,
        repo=REPO,
    )
    assert result.published is True
    assert "contribution:b978465948b6923a" in result.applied_contribution_ids
    assert "contribution:33d7cdb0ff623f28" in result.superseded_contribution_ids

    c1 = kernel.project_world_graph(tmp_path, _request("longmont-c1"))
    c1_ids = {node.node_id for node in c1.nodes}
    assert "pc:caelynn" in c1_ids
    assert "party:heroes-party" in c1_ids
    assert "event:longmont-c1:session-3:stone-bridge-flood" in c1_ids
    assert "location:stonebridge" in c1_ids
    assert "location:mirathorn" in c1_ids
    assert "party:questionable-company" not in c1_ids
    assert "threat:tripod-null-calf" not in c1_ids

    c2 = kernel.project_world_graph(tmp_path, _request("longmont-c2"))
    c2_ids = {node.node_id for node in c2.nodes}
    assert "pc:caelynn" in c2_ids
    assert "party:questionable-company" in c2_ids
    assert "threat:tripod-null-calf" in c2_ids
    assert "party:heroes-party" not in c2_ids
    assert "event:longmont-c1:session-3:stone-bridge-flood" not in c2_ids

    search = kernel.project_world_graph(
        tmp_path,
        _request("longmont-c1", query_text="Stone Bridge Flood"),
    )
    assert search.query_context is not None
    assert (
        "event:longmont-c1:session-3:stone-bridge-flood"
        in search.query_context.matched_node_ids
    )


def test_apply_without_head_fails_closed(tmp_path: Path) -> None:
    with pytest.raises(C1AdditiveApplyError) as exc_info:
        apply_approved_c1_additive_bundle(actor="gm", root=tmp_path, repo=REPO)
    assert exc_info.value.code == "world_graph_unavailable"


def test_agent_world_graph_context_ready_for_c1_after_apply(
    tmp_path: Path,
    loaded_c2_bundle,
) -> None:
    from apps.live_control_server.services.agent_world_graph_query_context import (
        AgentWorldGraphQueryContextRequest,
        resolve_agent_world_graph_query_context,
    )

    _initialize_c2(tmp_path, loaded_c2_bundle)
    apply_approved_c1_additive_bundle(actor="gm", root=tmp_path, repo=REPO)

    nested = AgentWorldGraphQueryContextRequest.model_validate(
        {
            "schema": "dmb_agent_world_graph_query_context_request_v1",
            "world_id": WORLD_ID,
            "campaign_id": "longmont-c1",
            "focus": {"kind": "session", "session_id": "session-3"},
            "admissibility": "gm",
        }
    )
    envelope = resolve_agent_world_graph_query_context(
        nested,
        outer_text="What happened at the Stone Bridge Flood?",
        outer_campaign_id="longmont-c1",
        root=tmp_path,
    )
    assert envelope["status"] == "ready"
    assert envelope["campaign_id"] == "longmont-c1"
    assert "campaign_scope_mismatch" not in (envelope.get("warning_codes") or [])
    matched = envelope.get("matched_node_ids") or []
    assert "event:longmont-c1:session-3:stone-bridge-flood" in matched


def test_partial_apply_refuses_blind_retry(
    tmp_path: Path,
    loaded_c2_bundle,
) -> None:
    _initialize_c2(tmp_path, loaded_c2_bundle)
    _apply_first_c1_step(tmp_path)

    status = get_c1_additive_apply_status(root=tmp_path, repo=REPO)
    assert status.partial_applied is True
    assert status.qc_roster_superseded is True
    assert status.applied_contribution_ids == [APPROVED_ORDERED_CONTRIBUTION_IDS[0]]
    assert status.pending_contribution_ids == list(APPROVED_ORDERED_CONTRIBUTION_IDS[1:])

    with pytest.raises(C1AdditiveApplyError) as exc_info:
        apply_approved_c1_additive_bundle(actor="gm", root=tmp_path, repo=REPO)
    assert exc_info.value.code == "partial_apply_detected"


def test_partial_apply_resumes_successfully(
    tmp_path: Path,
    loaded_c2_bundle,
) -> None:
    _initialize_c2(tmp_path, loaded_c2_bundle)
    next_id = _apply_first_c1_step(tmp_path)

    status = get_c1_additive_apply_status(root=tmp_path, repo=REPO)
    assert status.partial_applied is True
    assert status.pending_contribution_ids[0] == next_id

    result = apply_approved_c1_additive_bundle(
        actor="gm",
        root=tmp_path,
        repo=REPO,
        resume_from_contribution_id=next_id,
    )
    assert result.published is True
    assert result.applied_contribution_ids == list(APPROVED_ORDERED_CONTRIBUTION_IDS)

    status_after = get_c1_additive_apply_status(root=tmp_path, repo=REPO)
    assert status_after.already_applied is True
    assert status_after.partial_applied is False
    assert status_after.qc_roster_superseded is True


def test_already_applied_restart_is_idempotent(
    tmp_path: Path,
    loaded_c2_bundle,
) -> None:
    _initialize_c2(tmp_path, loaded_c2_bundle)
    first = apply_approved_c1_additive_bundle(actor="gm", root=tmp_path, repo=REPO)
    assert first.published is True
    second = apply_approved_c1_additive_bundle(actor="gm", root=tmp_path, repo=REPO)
    assert second.published is False
    assert "already_applied" in second.diagnostics
    assert second.applied_contribution_ids == list(APPROVED_ORDERED_CONTRIBUTION_IDS)


def test_non_prefix_active_membership_fails_closed(
    tmp_path: Path,
    loaded_c2_bundle,
) -> None:
    _initialize_c2(tmp_path, loaded_c2_bundle)
    _apply_first_c1_step(tmp_path)
    bundle = load_approved_c1_additive_bundle(REPO)
    head, _revision, store = kernel.open_current_world_graph(tmp_path, WORLD_ID)
    # Corrupt the pinned head: activate step 2 without step 1.
    orphan = bundle.contributions[2]
    from apps.live_control_server.services.c1_world_graph_additive_apply import (
        _expected_head_source_payload_sha256,
    )

    corrupted = list(store.contribution_replay_manifest or [])
    corrupted.append(
        ContributionReplayManifestEntry(
            contribution_id=orphan.contribution_id,
            status="active",
            source_payload_sha256=_expected_head_source_payload_sha256(orphan),
        )
    )
    kernel.publish_world_graph_revision(
        tmp_path,
        WORLD_ID,
        store.model_copy(update={"contribution_replay_manifest": corrupted}),
        operation_ids=["test:corrupt-non-prefix"],
        expected_parent_revision_id=head.head_revision_id,
    )

    with pytest.raises(C1AdditiveApplyError) as exc_info:
        get_c1_additive_apply_status(root=tmp_path, repo=REPO)
    assert exc_info.value.code == "partial_apply_corrupt"
    assert "exact ordered prefix" in str(exc_info.value)


def test_status_follows_pinned_head_not_mutable_index(
    tmp_path: Path,
    loaded_c2_bundle,
) -> None:
    _initialize_c2(tmp_path, loaded_c2_bundle)
    apply_approved_c1_additive_bundle(actor="gm", root=tmp_path, repo=REPO)

    # Mutable ledger/index no longer lists C1 contributions as active, but the
    # pinned head replay manifest still does → status must remain already_applied.
    index = load_contribution_index(tmp_path, WORLD_ID)
    stripped_active = [
        cid
        for cid in index.active_contribution_ids
        if cid not in APPROVED_ORDERED_CONTRIBUTION_IDS
    ]
    save_contribution_index(
        tmp_path,
        WORLD_ID,
        index.model_copy(update={"active_contribution_ids": stripped_active}),
    )

    status = get_c1_additive_apply_status(root=tmp_path, repo=REPO)
    assert status.already_applied is True
    assert status.applied_contribution_ids == list(APPROVED_ORDERED_CONTRIBUTION_IDS)

    # Blind retry remains an already_applied no-op bound to the head.
    result = apply_approved_c1_additive_bundle(actor="gm", root=tmp_path, repo=REPO)
    assert result.published is False
    assert "already_applied" in result.diagnostics


def test_resume_after_later_step_failure(
    tmp_path: Path,
    loaded_c2_bundle,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    _initialize_c2(tmp_path, loaded_c2_bundle)
    next_id = _apply_first_c1_step(tmp_path)
    bundle = load_approved_c1_additive_bundle(REPO)
    fail_id = bundle.contributions[2].contribution_id

    real_merge = kernel.merge_contribution_to_revision

    def _flaky_merge(*args, **kwargs):
        contribution = kwargs.get("contribution") or args[2]
        if contribution.contribution_id == fail_id:
            from graph_memory.kernel.contribution_models import ContributionMergeResult

            return ContributionMergeResult(
                world_id=WORLD_ID,
                published=False,
                diagnostics=["injected_later_step_failure"],
            )
        return real_merge(*args, **kwargs)

    monkeypatch.setattr(kernel, "merge_contribution_to_revision", _flaky_merge)
    with pytest.raises(C1AdditiveApplyError) as exc_info:
        apply_approved_c1_additive_bundle(
            actor="gm",
            root=tmp_path,
            repo=REPO,
            resume_from_contribution_id=next_id,
        )
    assert exc_info.value.code == "merge_failed"

    monkeypatch.setattr(kernel, "merge_contribution_to_revision", real_merge)
    status = get_c1_additive_apply_status(root=tmp_path, repo=REPO)
    assert status.partial_applied is True
    assert status.applied_contribution_ids == [
        APPROVED_ORDERED_CONTRIBUTION_IDS[0],
        APPROVED_ORDERED_CONTRIBUTION_IDS[1],
    ]
    assert status.pending_contribution_ids[0] == fail_id

    result = apply_approved_c1_additive_bundle(
        actor="gm",
        root=tmp_path,
        repo=REPO,
        resume_from_contribution_id=fail_id,
    )
    assert result.published is True
    assert result.applied_contribution_ids == list(APPROVED_ORDERED_CONTRIBUTION_IDS)


def test_blank_campaign_scope_rejected_on_assertion() -> None:
    with pytest.raises(ValidationError):
        GraphContributionAssertion.model_validate(
            {
                "assertion_id": "assertion:blank-scope",
                "assertion_kind": "node",
                "subject_node_id": "pc:caelynn",
                "value": {"label": "Caelynn"},
                "acceptance_state": "accepted",
                "contribution_id": "contribution:test",
                "campaign_scope": "   ",
            }
        )


def test_blank_campaign_scope_fails_closed_in_projection_helpers() -> None:
    from graph_memory.kernel.world_projection import (
        _campaign_scope_is_visible,
        _object_campaign_scope,
    )

    assert _campaign_scope_is_visible(None, request_campaign_id="longmont-c1") is True
    with pytest.raises(WorldGraphProjectionError) as visible_exc:
        _campaign_scope_is_visible("", request_campaign_id="longmont-c1")
    assert visible_exc.value.code == "invalid_campaign_scope"

    with pytest.raises(WorldGraphProjectionError) as world_exc:
        _campaign_scope_is_visible(
            "  ",
            request_campaign_id="longmont-c1",
            scope_mode="world",
        )
    assert world_exc.value.code == "invalid_campaign_scope"

    assert (
        _campaign_scope_is_visible(
            "longmont-c2",
            request_campaign_id="longmont-c1",
            scope_mode="world",
        )
        is True
    )

    assert _object_campaign_scope({"campaign_scope": None}) is None
    with pytest.raises(WorldGraphProjectionError) as object_exc:
        _object_campaign_scope({"campaign_scope": "  "})
    assert object_exc.value.code == "invalid_campaign_scope"
