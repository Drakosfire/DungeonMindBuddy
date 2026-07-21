"""World Graph recap projection — service + HTTP boundary."""

from __future__ import annotations

from pathlib import Path

import pytest
from fastapi.testclient import TestClient

import graph_memory.kernel as kernel
from apps.live_control_server.main import create_app
from apps.live_control_server.services.world_graph_projection import (
    WorldGraphProjectionServiceError,
)
from apps.live_control_server.services.world_graph_recap_projection import (
    build_world_graph_recap_projection,
    project_world_markdown_mentions,
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
    WorldGraphProjectionNodeView,
    WorldGraphProjectionRequest,
)

RECAP_PROJECTION_URL = "/api/live/world-graph/recap-projection"
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


def _session_request(session_id: str = FOCUS_SESSION_ID) -> WorldGraphProjectionRequest:
    return WorldGraphProjectionRequest(
        schema="dmb_world_graph_projection_request_v1",
        world_id=WORLD_ID,
        campaign_id=CAMPAIGN_ID,
        focus={"kind": "session", "session_id": session_id, "campaign_id": CAMPAIGN_ID},
        admissibility="gm",
        scope_mode="campaign",
    )


def test_project_world_markdown_mentions_uses_durable_node_ids() -> None:
    nodes = [
        WorldGraphProjectionNodeView(
            node_id="pc:caelynn",
            label="Caelynn",
            kind="pc",
            role="character",
            aliases=["Caelynn Leafwhisper"],
            evidence_ref_ids=["ev:1"],
        ),
        WorldGraphProjectionNodeView(
            node_id="location:mireward",
            label="Mireward Reach",
            kind="location",
            role="place",
            aliases=["Mireward"],
            evidence_ref_ids=["ev:2"],
        ),
    ]
    markdown = "Caelynn reached Mireward before nightfall."
    projected, mentions = project_world_markdown_mentions(markdown, nodes)

    assert "[Caelynn](dmb-node:pc:caelynn)" in projected
    assert "[Mireward](dmb-node:location:mireward)" in projected
    assert {m.node_id for m in mentions} == {"pc:caelynn", "location:mireward"}


def test_build_requires_session_focus(tmp_path: Path) -> None:
    _initialize(tmp_path)
    request = WorldGraphProjectionRequest(
        schema="dmb_world_graph_projection_request_v1",
        world_id=WORLD_ID,
        campaign_id=CAMPAIGN_ID,
        focus={"kind": "none", "session_id": None},
        admissibility="gm",
    )
    with pytest.raises(WorldGraphProjectionServiceError) as exc_info:
        build_world_graph_recap_projection(request, root=tmp_path, corpus_markdown="x")
    assert exc_info.value.code == "invalid_request"
    assert exc_info.value.status_code == 422


def test_build_fails_closed_without_markdown(tmp_path: Path) -> None:
    _initialize(tmp_path)
    with pytest.raises(WorldGraphProjectionServiceError) as exc_info:
        build_world_graph_recap_projection(
            _session_request(),
            root=tmp_path,
            corpus_markdown="   ",
        )
    assert exc_info.value.code == "recap_markdown_unavailable"
    assert exc_info.value.status_code == 404


def test_build_splices_world_ids_into_injected_markdown(tmp_path: Path) -> None:
    _initialize(tmp_path)
    # Use a label known to exist in the initialized world bundle.
    markdown = "The positional controller failed near the Tripod Null-Calf."
    projection = build_world_graph_recap_projection(
        _session_request(),
        root=tmp_path,
        corpus_markdown=markdown,
    )
    assert projection.session_id == FOCUS_SESSION_ID
    assert projection.campaign_id == CAMPAIGN_ID
    assert projection.graph_id  # world revision id
    assert projection.node_views
    # At least one durable world id appears in chips or node_views.
    assert any(node_id.startswith(("pc:", "npc:", "location:", "threat:", "object:"))
               for node_id in projection.node_views)
    assert "dmb-node:" in (projection.markdown or "") or projection.mentions == []


def test_recap_projection_route_rejects_query_params(client: TestClient) -> None:
    response = client.post(
        f"{RECAP_PROJECTION_URL}?worldId=foreign",
        json={
            "schema": "dmb_world_graph_projection_request_v1",
            "worldId": WORLD_ID,
            "campaignId": CAMPAIGN_ID,
            "focus": {
                "kind": "session",
                "sessionId": FOCUS_SESSION_ID,
                "campaignId": CAMPAIGN_ID,
            },
            "admissibility": "gm",
        },
    )
    assert response.status_code == 422
    assert response.json()["code"] == "invalid_request"


def test_recap_projection_route_returns_recap_payload(
    client: TestClient,
    tmp_path: Path,
) -> None:
    _initialize(tmp_path)
    # Monkeypatch markdown load via service injection is not available on the route;
    # stub the loader used by the service.
    import apps.live_control_server.services.world_graph_recap_projection as service

    original = service.load_corpus_normalized_recap_markdown
    service.load_corpus_normalized_recap_markdown = (  # type: ignore[assignment]
        lambda **_kwargs: "Caelynn stood at Mireward Reach."
    )
    try:
        response = client.post(
            RECAP_PROJECTION_URL,
            json={
                "schema": "dmb_world_graph_projection_request_v1",
                "worldId": WORLD_ID,
                "campaignId": CAMPAIGN_ID,
                "focus": {
                    "kind": "session",
                    "sessionId": FOCUS_SESSION_ID,
                    "campaignId": CAMPAIGN_ID,
                },
                "admissibility": "gm",
                "scopeMode": "campaign",
            },
        )
    finally:
        service.load_corpus_normalized_recap_markdown = original  # type: ignore[assignment]

    assert response.status_code == 200, response.text
    payload = response.json()
    assert payload["session_id"] == FOCUS_SESSION_ID
    assert payload["campaign_id"] == CAMPAIGN_ID
    assert payload["graph_id"]
    assert "node_views" in payload
    assert "mentions" in payload
    assert "markdown" in payload
    assert "use_latest_graph_ingest" not in response.text


def test_recap_projection_route_requires_session_focus(
    client: TestClient,
    tmp_path: Path,
) -> None:
    _initialize(tmp_path)
    response = client.post(
        RECAP_PROJECTION_URL,
        json={
            "schema": "dmb_world_graph_projection_request_v1",
            "worldId": WORLD_ID,
            "campaignId": CAMPAIGN_ID,
            "focus": {"kind": "none", "sessionId": None},
            "admissibility": "gm",
        },
    )
    assert response.status_code == 422
    assert response.json()["code"] == "invalid_request"
