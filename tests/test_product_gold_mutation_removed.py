"""The product router cannot mutate independently owned evaluation fixtures."""
from fastapi import FastAPI
from fastapi.testclient import TestClient
import pytest

from apps.live_control_server.routes import graph_authoring, graph_preview


@pytest.mark.parametrize("operation", ["prepare", "commit", "verify-commit"])
def test_product_gold_mutation_endpoints_are_absent(operation):
    app = FastAPI()
    app.include_router(graph_preview.router)
    with TestClient(app) as client:
        response = client.post(f"/api/live/graph-preview/gold-authoring/{operation}", json={})
    assert response.status_code == 404
    assert not any("gold-authoring" in path for path in app.openapi()["paths"])


def test_read_only_gold_inspection_and_native_authoring_routes_remain(monkeypatch):
    app = FastAPI()
    app.include_router(graph_preview.router)
    app.include_router(graph_authoring.router)
    monkeypatch.setattr(graph_preview, "discover_gold_review_sessions", lambda root: [])
    with TestClient(app) as client:
        response = client.get("/api/live/graph-preview/gold-review/sessions")
        assert response.status_code == 200
        assert response.json()["sessions"] == []
        kinds = client.get("/api/live/graph-authoring/object-kinds")
        assert kinds.status_code == 200
        assert kinds.json()["objectKinds"]
    paths = app.openapi()["paths"]
    assert "/api/live/graph-preview/gold-review/projection" in paths
    assert "/api/live/graph-authoring/prepare" in paths
    assert "/api/live/graph-authoring/commit" in paths
