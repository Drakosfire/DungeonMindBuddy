"""HTTP contract for GET/POST /api/live/world-containers."""

from __future__ import annotations

from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from apps.live_control_server.main import create_app
from apps.live_control_server.services.world_container_registry import (
    REGISTRY_SCHEMA,
    create_world_container,
)


@pytest.fixture
def root(tmp_path: Path) -> Path:
    return tmp_path


@pytest.fixture
def client(root: Path, monkeypatch: pytest.MonkeyPatch) -> TestClient:
    monkeypatch.setattr(
        "apps.live_control_server.routes.world_containers.repo_root",
        lambda: root,
    )
    return TestClient(create_app())


def test_list_empty_world_containers(client: TestClient) -> None:
    response = client.get("/api/live/world-containers")
    assert response.status_code == 200
    body = response.json()
    assert body["schema_version"] == REGISTRY_SCHEMA
    assert body["records"] == []


def test_create_and_list_world_container(client: TestClient, root: Path) -> None:
    response = client.post("/api/live/world-containers", json={"name": "The Glass Orchard"})
    assert response.status_code == 200
    created = response.json()
    assert created["world_id"] == "the-glass-orchard"
    assert created["name"] == "The Glass Orchard"
    assert created["source_root_relpath"] == "corpus/the-glass-orchard-markdown"
    assert created["schema_version"] == "dmb_world_container_record_v1"
    assert "world_id" in created
    assert (root / created["source_root_relpath"]).is_dir()

    listed = client.get("/api/live/world-containers")
    assert listed.status_code == 200
    body = listed.json()
    assert body["schema_version"] == REGISTRY_SCHEMA
    assert len(body["records"]) == 1
    assert body["records"][0] == created


def test_create_rejects_extra_fields(client: TestClient) -> None:
    response = client.post(
        "/api/live/world-containers",
        json={
            "name": "Nope",
            "world_id": "client-id",
            "source_root_relpath": "corpus/hack-markdown",
        },
    )
    assert response.status_code == 422


def test_create_rejects_empty_name(client: TestClient) -> None:
    response = client.post("/api/live/world-containers", json={"name": "   "})
    assert response.status_code == 422


def test_create_is_idempotent_over_http(client: TestClient) -> None:
    first = client.post("/api/live/world-containers", json={"name": "Retry World"})
    second = client.post("/api/live/world-containers", json={"name": "retry world"})
    assert first.status_code == 200
    assert second.status_code == 200
    assert first.json()["world_id"] == second.json()["world_id"]
    listed = client.get("/api/live/world-containers").json()
    assert len(listed["records"]) == 1


def test_unmanaged_root_collision_over_http(client: TestClient, root: Path) -> None:
    (root / "corpus" / "stolen-path-markdown").mkdir(parents=True)
    response = client.post("/api/live/world-containers", json={"name": "Stolen Path"})
    assert response.status_code == 409


def test_service_create_visible_to_http_list(client: TestClient, root: Path) -> None:
    create_world_container(root, name="Seeded")
    body = client.get("/api/live/world-containers").json()
    assert len(body["records"]) == 1
    assert body["records"][0]["name"] == "Seeded"
