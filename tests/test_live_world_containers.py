"""HTTP contract for GET/POST /api/live/world-containers."""

from __future__ import annotations

from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from apps.live_control_server.main import create_app
from apps.live_control_server.services.world_container_registry import (
    PUBLIC_RECORD_SCHEMA,
    PUBLIC_REGISTRY_SCHEMA,
    create_world_container,
    world_containers_path,
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
    assert body["schema_version"] == PUBLIC_REGISTRY_SCHEMA
    assert body["records"] == []


def test_create_and_list_world_container(client: TestClient, root: Path) -> None:
    response = client.post("/api/live/world-containers", json={"name": "The Glass Orchard"})
    assert response.status_code == 200
    created = response.json()
    assert created["world_id"] == "the-glass-orchard"
    assert created["name"] == "The Glass Orchard"
    assert created["source_root_relpath"] == "corpus/the-glass-orchard-markdown"
    assert created["schema_version"] == PUBLIC_RECORD_SCHEMA
    assert created["native_graph_binding"] == {
        "status": "unbound",
        "binding_version": 0,
    }
    assert "world_id" in created
    assert (root / created["source_root_relpath"]).is_dir()

    listed = client.get("/api/live/world-containers")
    assert listed.status_code == 200
    body = listed.json()
    assert body["schema_version"] == PUBLIC_REGISTRY_SCHEMA
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


def test_list_reads_legacy_registry_without_migration_or_mind_call(
    root: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    from apps.live_control_server.routes import world_containers

    path = world_containers_path(root)
    path.parent.mkdir(parents=True, exist_ok=True)
    original = (
        '{"schema_version":"dmb_world_container_registry_v1","records":['
        '{"schema_version":"dmb_world_container_record_v1","world_id":"legacy-world",'
        '"name":"Legacy World","source_root_relpath":"corpus/legacy-world-markdown",'
        '"created_at":"2026-01-01T00:00:00Z"}]}'
    ).encode("utf-8")
    path.write_bytes(original)
    monkeypatch.setattr(world_containers, "repo_root", lambda: root)
    monkeypatch.setattr(
        "apps.live_control_server.services.world_graph_binding._validate_with_mind",
        lambda _world_id: pytest.fail("WorldContainer list must not contact MIND"),
    )

    response = world_containers.get_world_containers()

    assert response["records"][0]["native_graph_binding"] == {
        "status": "unbound",
        "binding_version": 0,
    }
    assert path.read_bytes() == original
