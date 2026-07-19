"""Tests for C1 additive World Graph apply (PC world-ownership + Heroes + S1–S3)."""

from __future__ import annotations

from pathlib import Path

import pytest

import graph_memory.kernel as kernel
from apps.live_control_server.services.c1_world_graph_additive_apply import (
    C1AdditiveApplyError,
    apply_approved_c1_additive_bundle,
    get_c1_additive_apply_status,
    load_approved_c1_additive_bundle,
)
from graph_memory.contribution_bundles import load_contribution_bundle
from graph_memory.kernel.world_initialization import initialize_world_from_contributions
from graph_memory.kernel.world_initialization_models import (
    PLAN_SCHEMA,
    WorldInitializationApprovalAttestation,
    WorldInitializationContribution,
    WorldInitializationPlan,
)
from graph_memory.projection.world_projection import (
    PROJECTION_REQUEST_SCHEMA,
    WorldGraphProjectionFocus,
    WorldGraphProjectionRequest,
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


def test_load_approved_c1_bundle_parses() -> None:
    bundle = load_approved_c1_additive_bundle(REPO)
    assert bundle.manifest["bundle_id"] == "eldyrwild-longmont-c1-s1-s3-v1"
    assert len(bundle.contributions) == 5
    assert bundle.contributions[0].supersedes_contribution_id == (
        "contribution:33d7cdb0ff623f28"
    )


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

