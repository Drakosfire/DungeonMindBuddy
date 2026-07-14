"""Service-boundary tests for PR007A world graph projection."""

from __future__ import annotations

from pathlib import Path
from unittest.mock import patch

import pytest

import graph_memory.kernel as kernel
from apps.live_control_server.services.world_graph_projection import (
    WorldGraphProjectionServiceError,
    project_world_graph,
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
    WorldGraphProjectionRequest,
)

BUNDLE_PATH = Path(
    "graph_data/approved_contribution_bundles/eldyrwild-longmont-c2-initial-v1"
)
WORLD_ID = "eldyrwild"
CAMPAIGN_ID = "longmont-c2"
FOCUS_SESSION_ID = "session-23"
BUNDLE_DIGEST = (
    "5f8288d3052a9e59192884f2c35a13d51f665095d84cca2081a56638108d3fa5"
)
APPROVED_MERGE_SHA = "f69c69f271c427209860d902636347b70fea5920"
ORDERED_CONTRIBUTION_IDS = [
    "contribution:82f23934d8eaca8a",
    "contribution:43782369bd717d32",
    "contribution:33d7cdb0ff623f28",
    "contribution:c086a0b72324ff16",
    "contribution:1227841724520c18",
    "contribution:022187fdefdf4557",
]


def _initialize(root: Path) -> None:
    bundle = load_contribution_bundle(BUNDLE_PATH)
    by_id = {item.contribution_id: item for item in bundle.contributions}
    plan = WorldInitializationPlan(
        schema=PLAN_SCHEMA,
        world_id=WORLD_ID,
        campaign_id=CAMPAIGN_ID,
        focus_session_id=FOCUS_SESSION_ID,
        ordered_contributions=[
            WorldInitializationContribution(
                contribution_id=contribution_id,
                payload_sha256=kernel.compute_contribution_payload_sha256(
                    by_id[contribution_id]
                ),
            )
            for contribution_id in ORDERED_CONTRIBUTION_IDS
        ],
        approval_attestation=WorldInitializationApprovalAttestation(
            bundle_id="eldyrwild-longmont-c2-initial-v1",
            bundle_digest=BUNDLE_DIGEST,
            approved_bundle_merge_sha=APPROVED_MERGE_SHA,
        ),
    )
    initialize_world_from_contributions(
        root,
        plan=plan,
        contributions=list(bundle.contributions),
        actor="gm",
    )


def _request() -> WorldGraphProjectionRequest:
    return WorldGraphProjectionRequest(
        schema=PROJECTION_REQUEST_SCHEMA,
        world_id=WORLD_ID,
        campaign_id=CAMPAIGN_ID,
    )


def test_service_uses_configured_root_and_kernel_boundary(tmp_path: Path) -> None:
    _initialize(tmp_path)
    configured = tmp_path / "configured-world-root"
    configured.mkdir()
    _initialize(configured)

    with patch(
        "apps.live_control_server.services.world_graph_projection.world_graph_root",
        return_value=configured,
    ):
        projection = project_world_graph(_request())

    assert projection.summary.node_count == 12
    head, _revision, _store = kernel.open_current_world_graph(configured, WORLD_ID)
    assert projection.snapshot.revision_id == head.head_revision_id


def test_service_maps_kernel_errors(tmp_path: Path) -> None:
    with pytest.raises(WorldGraphProjectionServiceError) as exc_info:
        project_world_graph(_request(), root=tmp_path)
    assert exc_info.value.code == "world_graph_unavailable"
    assert exc_info.value.status_code == 404
