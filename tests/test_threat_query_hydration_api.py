"""SBW10a Threat query/hydration HTTP route tests."""

from __future__ import annotations

from unittest.mock import patch

from fastapi import HTTPException
from fastapi.testclient import TestClient
import pytest
from starlette.requests import Request

from apps.live_control_server.main import create_app
from apps.live_control_server.models.threat_query_hydration import (
    ThreatQueryHydrationResponseV1,
)
from apps.live_control_server.services.threat_query_hydration import (
    ThreatQueryHydrationError,
)

LOCAL_OPERATOR_TOKEN = "test-local-operator-token-with-adequate-length"


def _authorized_client(monkeypatch: pytest.MonkeyPatch) -> TestClient:
    monkeypatch.setenv("DMB_AGENT_GRAPH_AUTH_MODE", "local_operator")
    monkeypatch.setenv("DMB_AGENT_GRAPH_AUTH_ENVIRONMENT", "development")
    monkeypatch.setenv("DMB_AGENT_GRAPH_LOCAL_OPERATOR_TOKEN", LOCAL_OPERATOR_TOKEN)
    return TestClient(
        create_app(),
        client=("127.0.0.1", 50000),
        headers={"Authorization": f"Bearer {LOCAL_OPERATOR_TOKEN}"},
    )


def _request_context(
    authorization: str | None = None, *, host: str = "127.0.0.1"
) -> Request:
    headers = []
    if authorization is not None:
        headers.append((b"authorization", authorization.encode("utf-8")))
    path = "/api/live/threats/query-hydration"
    return Request(
        {
            "type": "http",
            "http_version": "1.1",
            "method": "POST",
            "scheme": "http",
            "path": path,
            "raw_path": path.encode("ascii"),
            "query_string": b"",
            "headers": headers,
            "client": (host, 50000),
            "server": ("127.0.0.1", 8000),
        }
    )


def test_query_hydration_route_ok(monkeypatch: pytest.MonkeyPatch) -> None:
    client = _authorized_client(monkeypatch)
    fake = ThreatQueryHydrationResponseV1(
        schema="dmb_threat_query_hydration_response_v1",
        world_id="world_eldyrwild",
        campaign_id="campaign_eldyrwild",
        scope_mode="campaign",
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


def test_query_hydration_route_unavailable_503(monkeypatch: pytest.MonkeyPatch) -> None:
    client = _authorized_client(monkeypatch)
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


def test_query_hydration_route_rejects_missing_revision_pin(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    client = _authorized_client(monkeypatch)
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


def test_query_hydration_denies_before_native_read(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    from apps.live_control_server.models.threat_query_hydration import (
        ThreatQueryHydrationRequestV1,
    )
    from apps.live_control_server.routes import threat_query_hydration as route
    from apps.live_control_server.services import agent_graph_auth
    from apps.live_control_server.services.agent_graph_auth import NativeGraphPrincipal

    for name in (
        "DMB_AGENT_GRAPH_AUTH_MODE",
        "DMB_AGENT_GRAPH_AUTH_ENVIRONMENT",
        "DMB_AGENT_GRAPH_LOCAL_OPERATOR_TOKEN",
    ):
        monkeypatch.delenv(name, raising=False)

    body = ThreatQueryHydrationRequestV1.model_validate(
        {
            "schema": "dmb_threat_query_hydration_request_v1",
            "worldId": "world_eldyrwild",
            "campaignId": "campaign_eldyrwild",
            "revisionPin": "rev_graph_pin_001",
            "queryText": "Float Goat",
        }
    )
    calls: list[str] = []
    monkeypatch.setattr(route, "world_graph_root", lambda: calls.append("root"))
    monkeypatch.setattr(
        route,
        "query_threats_with_hydration",
        lambda *_args, **_kwargs: calls.append("query"),
    )

    with pytest.raises(HTTPException) as missing_config:
        route.post_threat_query_hydration(body, _request_context())
    assert missing_config.value.status_code == 503

    monkeypatch.setenv("DMB_AGENT_GRAPH_AUTH_MODE", "local_operator")
    monkeypatch.setenv("DMB_AGENT_GRAPH_AUTH_ENVIRONMENT", "development")
    monkeypatch.setenv("DMB_AGENT_GRAPH_LOCAL_OPERATOR_TOKEN", LOCAL_OPERATOR_TOKEN)
    for authorization in (None, "Bearer wrong-test-credential"):
        with pytest.raises(HTTPException) as denied:
            route.post_threat_query_hydration(body, _request_context(authorization))
        assert denied.value.status_code == 401

    monkeypatch.setattr(
        agent_graph_auth,
        "authenticate_native_graph_principal",
        lambda _request: NativeGraphPrincipal(
            subject="local_player", role="player", auth_method="local_operator"
        ),
    )
    with pytest.raises(HTTPException) as non_gm:
        route.post_threat_query_hydration(
            body, _request_context(f"Bearer {LOCAL_OPERATOR_TOKEN}")
        )
    assert non_gm.value.status_code == 403
    assert calls == []


def test_query_hydration_authorized_path_reaches_native_read(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    from apps.live_control_server.models.threat_query_hydration import (
        ThreatQueryHydrationRequestV1,
        ThreatQueryHydrationResponseV1,
    )
    from apps.live_control_server.routes import threat_query_hydration as route

    monkeypatch.setenv("DMB_AGENT_GRAPH_AUTH_MODE", "local_operator")
    monkeypatch.setenv("DMB_AGENT_GRAPH_AUTH_ENVIRONMENT", "development")
    monkeypatch.setenv("DMB_AGENT_GRAPH_LOCAL_OPERATOR_TOKEN", LOCAL_OPERATOR_TOKEN)
    body = ThreatQueryHydrationRequestV1.model_validate(
        {
            "schema": "dmb_threat_query_hydration_request_v1",
            "worldId": "world_eldyrwild",
            "campaignId": "campaign_eldyrwild",
            "revisionPin": "rev_graph_pin_001",
            "queryText": "Float Goat",
        }
    )
    fake = ThreatQueryHydrationResponseV1(
        schema="dmb_threat_query_hydration_response_v1",
        world_id="world_eldyrwild",
        campaign_id="campaign_eldyrwild",
        scope_mode="campaign",
        revision_id="rev_graph_pin_001",
        query_text="Float Goat",
        result_label="threat_query_hydration_empty",
        hits=[],
        diagnostics=[],
    )
    calls: list[str] = []
    monkeypatch.setattr(route, "world_graph_root", lambda: calls.append("root"))

    def read(*_args, **_kwargs):
        calls.append("query")
        return fake

    monkeypatch.setattr(route, "query_threats_with_hydration", read)
    response = route.post_threat_query_hydration(
        body, _request_context(f"Bearer {LOCAL_OPERATOR_TOKEN}")
    )
    assert response.status_code == 200
    assert response.body
    assert calls == ["root", "query"]
