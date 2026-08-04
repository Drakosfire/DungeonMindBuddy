"""SBW10a Threat query/hydration HTTP route tests."""
from __future__ import annotations

from unittest.mock import patch

from fastapi.testclient import TestClient

from apps.live_control_server.main import create_app
from apps.live_control_server.models.threat_query_hydration import (
    ThreatQueryHydrationResponseV1,
)
from apps.live_control_server.services.threat_query_hydration import (
    ThreatQueryHydrationError,
)


def test_query_hydration_route_ok() -> None:
    app = create_app()
    client = TestClient(app)
    fake = ThreatQueryHydrationResponseV1(
        schema="dmb_threat_query_hydration_response_v1",
        world_id="world_eldyrwild",
        campaign_id="campaign_eldyrwild",
        revision_id="rev_graph_pin_001",
        query_text="Float Goat",
        result_label="threat_query_hydration_empty",
        hits=[],
        diagnostics=[],
    )
    with patch(
        "apps.live_control_server.routes.threat_query_hydration.query_threats_with_hydration",
        return_value=fake,
    ):
        response = client.post(
            "/api/live/threats/query-hydration",
            json={
                "schema": "dmb_threat_query_hydration_request_v1",
                "worldId": "world_eldyrwild",
                "campaignId": "campaign_eldyrwild",
                "revisionPin": "rev_graph_pin_001",
                "queryText": "Float Goat",
            },
        )
    assert response.status_code == 200
    body = response.json()
    assert body["resultLabel"] == "threat_query_hydration_empty"
    assert body["revisionId"] == "rev_graph_pin_001"


def test_query_hydration_route_unavailable_503() -> None:
    app = create_app()
    client = TestClient(app)
    with patch(
        "apps.live_control_server.routes.threat_query_hydration.query_threats_with_hydration",
        side_effect=ThreatQueryHydrationError(
            "graph down",
            result_label="threat_query_hydration_unavailable",
            status_code=503,
            diagnostics=["projection_unavailable"],
        ),
    ):
        response = client.post(
            "/api/live/threats/query-hydration",
            json={
                "schema": "dmb_threat_query_hydration_request_v1",
                "worldId": "world_eldyrwild",
                "campaignId": "campaign_eldyrwild",
                "revisionPin": "rev_graph_pin_001",
                "queryText": "Float Goat",
            },
        )
    assert response.status_code == 503
    assert response.json()["resultLabel"] == "threat_query_hydration_unavailable"


def test_query_hydration_route_rejects_missing_revision_pin() -> None:
    app = create_app()
    client = TestClient(app)
    response = client.post(
        "/api/live/threats/query-hydration",
        json={
            "schema": "dmb_threat_query_hydration_request_v1",
            "worldId": "world_eldyrwild",
            "campaignId": "campaign_eldyrwild",
            "queryText": "Float Goat",
        },
    )
    assert response.status_code == 422
