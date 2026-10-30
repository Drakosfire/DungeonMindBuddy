"""The obsolete default-World status API cannot masquerade as native status."""
from fastapi import FastAPI
from fastapi.testclient import TestClient

from apps.live_control_server.routes.extract_promote import router


def test_old_status_is_absent_while_native_publication_routes_remain():
    app = FastAPI()
    app.include_router(router)
    with TestClient(app) as client:
        response = client.get("/api/live/extract-promote/status")
    assert response.status_code == 404
    paths = {route.path for route in app.routes}
    assert "/api/live/extract-promote/prepare" in paths
    assert "/api/live/extract-promote/confirm" in paths
