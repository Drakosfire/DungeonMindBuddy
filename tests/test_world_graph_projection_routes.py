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


# --- CUTOVER R.3: mounted direct DungeonMind projection ----------------------


def test_projection_route_dispatches_direct_in_dungeonmind_mode(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Mounted proof: the projection HTTP route executes in DungeonMind.

    Kernel/hydration explosion stubs prove the legacy graph read machinery
    never runs; the response carries the DungeonMind revision identity.
    """
    from apps.live_control_server.integrations.dungeonmind import (
        world_graph_reads as direct,
    )
    from apps.live_control_server.integrations.dungeonmind_kernel import (
        world_graph_authority,
    )
    from graph_memory.world_supergraph import storage
    from tests.test_cutover_direct_dungeonmind_world_graph_reads import (
        CAMPAIGN_ONE,
        NOW,
        _FakeBundle,
        _payload,
        _receipt,
        _seed_sources,
    )
    from tests.test_cutover_direct_dungeonmind_world_graph_reads import (
        WORLD_ID as DIRECT_WORLD_ID,
    )

    from dungeonmind.contracts.graph import PublishRevisionCommand
    from dungeonmind.infrastructure.memory import InMemoryWorldGraphRepository

    world_graph = InMemoryWorldGraphRepository()
    published = world_graph.publish_revision(
        PublishRevisionCommand(
            world_id=DIRECT_WORLD_ID,
            parent_revision_id=None,
            expected_parent_revision_id=None,
            operation_ids=["op:mounted-projection-r3"],
            graph_schema="dm_union_graph_v6",
            graph_payload=_payload(),
            created_at=NOW,
        )
    )
    bundle = _FakeBundle(
        world_graph,
        _seed_sources(),
        _receipt(DIRECT_WORLD_ID, published.revision_id),
    )
    services = direct.direct_services_from_bundle(bundle, DIRECT_WORLD_ID)

    monkeypatch.setenv(
        storage.WORLD_GRAPH_AUTHORITY_ENV, storage.WORLD_GRAPH_AUTHORITY_DUNGEONMIND
    )
    monkeypatch.setenv("DUNGEONMIND_WORLD_GRAPH_DIRECT_READ", "1")
    monkeypatch.setenv(
        "DUNGEONMIND_WORLD_GRAPH_AUTHORITY_DATABASE_URL", "postgresql://unused"
    )
    monkeypatch.setenv("DUNGEONMIND_WORLD_GRAPH_ROOT", str(tmp_path / "graph-root"))
    storage.clear_world_graph_cache_roots()
    monkeypatch.setattr(
        direct, "direct_services_from_config", lambda world_id: services
    )

    def _explode(*_args, **_kwargs):
        raise AssertionError("legacy kernel must not run on the direct read path")

    monkeypatch.setattr(kernel, "project_world_graph_from_context", _explode)
    monkeypatch.setattr(kernel, "resolve_projection_read_context", _explode)
    monkeypatch.setattr(world_graph_authority, "route_read_request", _explode)

    client = TestClient(create_app())
    response = client.post(
        PROJECTION_URL,
        json={
            "schema": "dmb_world_graph_projection_request_v1",
            "world_id": DIRECT_WORLD_ID,
            "campaign_id": CAMPAIGN_ONE,
            "admissibility": "gm",
            "scope_mode": "campaign",
        },
    )
    assert response.status_code == 200
    body = response.json()
    assert body["snapshot"]["revisionId"] == published.revision_id
    assert body["snapshot"]["isHead"] is True
    node_ids = {node["nodeId"] for node in body["nodes"]}
    assert node_ids == {"obj:tavern", "obj:hidden-cellar", "obj:hero", "obj:road-sign"}
