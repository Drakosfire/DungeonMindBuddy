"""HTTP-boundary tests for PR007A world graph projection."""

from __future__ import annotations

import json
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

import graph_memory.kernel as kernel
from apps.live_control_server.main import create_app
from graph_memory.contribution_bundles import load_contribution_bundle
from graph_memory.kernel.world_initialization import initialize_world_from_contributions
from graph_memory.kernel.world_initialization_models import (
    PLAN_SCHEMA,
    WorldInitializationApprovalAttestation,
    WorldInitializationContribution,
    WorldInitializationPlan,
)

PROJECTION_URL = "/api/live/world-graph/projection"
WORLD_ID = "eldyrwild"
CAMPAIGN_ID = "longmont-c2"
FOCUS_SESSION_ID = "session-23"
BUNDLE_PATH = Path(
    "graph_data/approved_contribution_bundles/eldyrwild-longmont-c2-initial-v1"
)
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


@pytest.fixture
def client(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> TestClient:
    monkeypatch.setenv("DUNGEONMIND_WORLD_GRAPH_ROOT", str(tmp_path))
    return TestClient(create_app())


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


def test_projection_route_rejects_query_params(client: TestClient) -> None:
    response = client.post(
        f"{PROJECTION_URL}?worldId=foreign",
        json={
            "schema": "dmb_world_graph_projection_request_v1",
            "worldId": WORLD_ID,
            "campaignId": CAMPAIGN_ID,
        },
    )
    assert response.status_code == 422
    payload = response.json()
    assert payload["schema"] == "dmb_world_graph_projection_error_v1"
    assert payload["code"] == "invalid_request"


def test_projection_route_rejects_forbidden_fields(client: TestClient) -> None:
    response = client.post(
        PROJECTION_URL,
        json={
            "schema": "dmb_world_graph_projection_request_v1",
            "worldId": WORLD_ID,
            "campaignId": CAMPAIGN_ID,
            "previewUnionStorePath": "/tmp/forbidden",
        },
    )
    assert response.status_code == 422
    assert response.json()["code"] == "invalid_request"


def test_projection_route_returns_camel_case_graph_after_init(
    client: TestClient,
    tmp_path: Path,
) -> None:
    _initialize(tmp_path)
    response = client.post(
        PROJECTION_URL,
        json={
            "schema": "dmb_world_graph_projection_request_v1",
            "worldId": WORLD_ID,
            "campaignId": CAMPAIGN_ID,
            "queryText": "positional controller",
        },
    )

    assert response.status_code == 200
    payload = response.json()
    assert payload["schema"] == "dmb_world_graph_projection_v1"
    assert payload["snapshot"]["worldId"] == WORLD_ID
    assert payload["summary"]["nodeCount"] == 12
    assert payload["queryContext"]["matchedNodeIds"][0] == "threat:tripod-null-calf"
    assert "revision_id" not in json.dumps(payload)
    assert "matched_node_ids" not in json.dumps(payload)
