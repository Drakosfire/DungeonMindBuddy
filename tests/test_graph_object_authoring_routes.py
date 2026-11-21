"""Route-boundary tests for Graph Review prepare/confirm."""

from __future__ import annotations

import pytest
from fastapi.testclient import TestClient

import apps.live_control_server.routes.graph_authoring as graph_authoring_route
from apps.live_control_server.main import create_app
from apps.live_control_server.services.graph_object_authoring_prepare import (
    GraphObjectAuthoringError,
)


def _request_body() -> dict[str, object]:
    return {
        "campaignId": "longmont-c1",
        "worldId": "longmont-c1",
        "campaignRel": "Test Campaign/A5",
        "sourceRunId": "run-c1s2",
        "proposals": [
            {
                "localProposalId": "route-object",
                "proposalKind": "object",
                "status": "staged_local",
                "objectRef": {"label": "Route object", "kind": "party"},
                "visibility": {
                    "visibility": "gm_private",
                    "revealState": "unrevealed",
                },
                "provenancePreview": {
                    "origin": "human_authored",
                    "authoringSurface": "memory_ingest_graph_authoring",
                },
            }
        ],
    }


@pytest.fixture
def client(monkeypatch: pytest.MonkeyPatch) -> TestClient:
    monkeypatch.setenv("DMB_DEPLOYMENT_ENVIRONMENT", "local")
    monkeypatch.setenv("DMB_AUTH_MODE", "local_operator")
    return TestClient(create_app(), base_url="http://127.0.0.1:8000", client=("127.0.0.1", 50000))


def test_prepare_route_is_retired_without_dispatch(client, monkeypatch):
    from apps.live_control_server.services import graph_object_authoring_prepare

    calls = []
    def forbidden(*args, **kwargs):
        calls.append((args, kwargs))
        raise AssertionError("Retired prepare must not dispatch")
    monkeypatch.setattr(graph_object_authoring_prepare, "prepare_graph_object_authoring_write", forbidden)
    response = client.post("/api/live/graph-authoring/prepare", json=_request_body())
    assert response.status_code == 410
    assert response.json()["detail"]["code"] == "classic_manual_prepare_retired"
    assert calls == []
    assert client.app.openapi()["paths"]["/api/live/graph-authoring/prepare"]["post"]["deprecated"]


def test_retired_prepare_keeps_malformed_request_validation(client):
    response = client.post("/api/live/graph-authoring/prepare", json={"proposals": "invalid"})
    assert response.status_code == 422


def test_commit_route_maps_inexpressible_confirmation_error(
    client: TestClient,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(
        graph_authoring_route,
        "commit_graph_object_authoring_write",
        lambda _request, **_kwargs: (_ for _ in ()).throw(
            GraphObjectAuthoringError(
                "merge_objects is not publishable through DungeonMind",
                code="governed_write_inexpressible",
                status_code=409,
            )
        ),
    )
    body = _request_body()
    body["confirmToken"] = "v1.invalid.invalid"

    response = client.post("/api/live/graph-authoring/commit", json=body)

    assert response.status_code == 409
    assert response.json()["detail"] == {
        "code": "governed_write_inexpressible",
        "message": "merge_objects is not publishable through DungeonMind",
    }


def test_local_commit_dispatch_is_recovery_only(client, monkeypatch):
    def dispatch(_request, *, recovery_only):
        assert recovery_only is True
        raise GraphObjectAuthoringError("No original receipt", code="publication_receipt_unavailable", status_code=409)
    monkeypatch.setattr(graph_authoring_route, "commit_graph_object_authoring_write", dispatch)
    response = client.post("/api/live/graph-authoring/commit", json={**_request_body(), "confirmToken": "original-token"})
    assert response.status_code == 409
    assert response.json()["detail"]["code"] == "publication_receipt_unavailable"
