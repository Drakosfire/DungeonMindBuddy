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
def client() -> TestClient:
    return TestClient(create_app())


def test_prepare_route_maps_graph_review_error(
    client: TestClient,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(
        graph_authoring_route,
        "prepare_graph_object_authoring_write",
        lambda _request: (_ for _ in ()).throw(
            GraphObjectAuthoringError(
                "source must be resolved before publication",
                code="source_unresolved",
                status_code=409,
            )
        ),
    )

    response = client.post("/api/live/graph-authoring/prepare", json=_request_body())

    assert response.status_code == 409
    assert response.json()["detail"] == {
        "code": "source_unresolved",
        "message": "source must be resolved before publication",
    }


def test_commit_route_maps_inexpressible_confirmation_error(
    client: TestClient,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(
        graph_authoring_route,
        "commit_graph_object_authoring_write",
        lambda _request: (_ for _ in ()).throw(
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
