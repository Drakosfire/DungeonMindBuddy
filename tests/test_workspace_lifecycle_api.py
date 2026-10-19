"""Authenticated World Trash boundaries against real file/Content/Play owners."""

from pathlib import Path

from fastapi import FastAPI
from fastapi.testclient import TestClient
import pytest

from apps.live_control_server.routes import workspace_lifecycle as routes
from apps.live_control_server.services.world_container_registry import (
    create_world_container,
)
from apps.live_control_server.services.workspace_document_registry import (
    create_workspace_document,
    get_workspace_document,
    list_workspace_documents,
)
from tests.application_state.test_play_run_editions_postgres import (
    WORLD,
    create_source_run,
    read,
)

TOKEN = "synthetic-trash-test-operator-00000000"
HEADERS = {"Authorization": f"Bearer {TOKEN}"}
BASE = "/api/live/world-workspace"


@pytest.fixture
def api(tmp_path, monkeypatch, application_state_dsn):
    monkeypatch.setenv("DMB_AGENT_GRAPH_AUTH_MODE", "local_operator")
    monkeypatch.setenv("DMB_AGENT_GRAPH_AUTH_ENVIRONMENT", "local")
    monkeypatch.setenv("DMB_AGENT_GRAPH_LOCAL_OPERATOR_TOKEN", TOKEN)
    world = create_world_container(tmp_path, name="Edition Test World")
    assert world.world_id == WORLD
    create_world_container(tmp_path, name="Other World")
    monkeypatch.setattr(routes, "_root", lambda: tmp_path)
    app = FastAPI()
    app.include_router(routes.router)
    return TestClient(app, client=("127.0.0.1", 45000))


def source(root: Path, *, world=WORLD):
    return create_workspace_document(
        root,
        title="Media acceptance",
        campaign_id=world,
        world_id=world,
        kind="worldbuilding_source",
        source_domain="worldbuilding",
        document_class="location",
        authority_state="draft",
        visibility_state="internal",
    )


def test_auth_owner_and_revision_reject_before_document_effects(api, tmp_path):
    doc = source(tmp_path)
    path = f"{BASE}/documents/{doc.document_id}/trash"
    body = {"expected_revision": doc.revision}
    assert api.get(BASE + "/trash", params={"world_id": WORLD}).status_code == 401
    assert api.post(path, params={"world_id": WORLD}, json=body).status_code == 401
    assert (
        api.post(
            path, params={"world_id": "other-world"}, json=body, headers=HEADERS
        ).status_code
        == 404
    )
    assert (
        api.post(
            path,
            params={"world_id": WORLD},
            json={"expected_revision": 99},
            headers=HEADERS,
        ).status_code
        == 409
    )
    assert (
        api.post(
            path,
            params={"world_id": WORLD},
            json={"expected_revision": True},
            headers=HEADERS,
        ).status_code
        == 422
    )
    assert get_workspace_document(tmp_path, doc.document_id) == doc


def test_build_trash_restore_keeps_source_bytes_and_separately_owned_media(
    api, tmp_path
):
    doc = source(tmp_path)
    foreign = source(tmp_path, world="other-world")
    target = tmp_path / doc.target_relpath
    target.parent.mkdir(parents=True, exist_ok=True)
    exact = b"# Media acceptance\r\n\r\n![Map](dmb-media:73b40978-e638-4ab3-992d-5dc493e8d229)\r\n"
    target.write_bytes(exact)
    asset = tmp_path / "out" / "media" / "shared-sentinel.png"
    asset.parent.mkdir(parents=True, exist_ok=True)
    asset.write_bytes(b"owned independently")
    path = f"{BASE}/documents/{doc.document_id}"
    moved = api.post(
        path + "/trash",
        params={"world_id": WORLD},
        json={"expected_revision": doc.revision},
        headers=HEADERS,
    )
    assert moved.status_code == 200, moved.text
    moved = moved.json()
    assert moved["status"] == "trashed"
    assert moved["revision"] == doc.revision + 1
    inventory = api.get(BASE + "/trash", params={"world_id": WORLD}, headers=HEADERS)
    assert inventory.status_code == 200, inventory.text
    assert [item["id"] for item in inventory.json()["items"]] == [doc.document_id]
    assert inventory.json()["items"][0]["status"] == "trashed"
    assert doc.document_id not in [
        item.document_id for item in list_workspace_documents(tmp_path)
    ]
    assert get_workspace_document(tmp_path, foreign.document_id) == foreign
    assert target.read_bytes() == exact
    assert asset.read_bytes() == b"owned independently"
    restored = api.post(
        path + "/restore",
        params={"world_id": WORLD},
        json={"expected_revision": moved["revision"]},
        headers=HEADERS,
    )
    assert restored.status_code == 200, restored.text
    assert get_workspace_document(tmp_path, doc.document_id).status == "active"
    assert target.read_bytes() == exact
    assert asset.read_bytes() == b"owned independently"
    assert (
        api.get(BASE + "/trash", params={"world_id": WORLD}, headers=HEADERS).json()[
            "items"
        ]
        == []
    )


def test_plan_trash_preserves_existing_pinned_session_and_history(api, tmp_path):
    obj, pin, aggregate = create_source_run()
    run = aggregate.run
    path = f"{BASE}/documents/{obj.work_object_id}"
    moved = api.post(
        path + "/trash",
        params={"world_id": WORLD},
        json={"expected_revision": obj.object_revision},
        headers=HEADERS,
    )
    assert moved.status_code == 200, moved.text
    assert read(run.run_id).markdown == pin.markdown
    trash = api.get(
        BASE + "/trash", params={"world_id": WORLD}, headers=HEADERS
    ).json()["items"]
    assert len(trash) == 1 and trash[0]["surface"] == "plan"
    assert (
        api.post(
            path + "/restore",
            params={"world_id": WORLD},
            json={"expected_revision": moved.json()["revision"]},
            headers=HEADERS,
        ).status_code
        == 200
    )
    assert read(run.run_id).markdown == pin.markdown


def test_session_route_requires_both_revisions_and_preserves_history(api):
    _, pin, aggregate = create_source_run()
    run = aggregate.run
    path = f"{BASE}/sessions/{run.run_id}"
    body = {"expected_revision": run.run_revision, "expected_content_revision": 0}
    assert (
        api.post(path + "/trash", params={"world_id": WORLD}, json=body).status_code
        == 401
    )
    assert (
        api.post(
            path + "/trash",
            params={"world_id": "other-world"},
            json=body,
            headers=HEADERS,
        ).status_code
        == 404
    )
    assert (
        api.post(
            path + "/trash",
            params={"world_id": WORLD},
            json={"expected_revision": run.run_revision},
            headers=HEADERS,
        ).status_code
        == 422
    )
    moved = api.post(
        path + "/trash", params={"world_id": WORLD}, json=body, headers=HEADERS
    )
    assert moved.status_code == 200, moved.text
    assert read(run.run_id).markdown == pin.markdown
    inventory = api.get(
        BASE + "/trash", params={"world_id": WORLD}, headers=HEADERS
    ).json()["items"]
    assert (
        len(inventory) == 1
        and inventory[0]["surface"] == "play"
        and inventory[0]["content_revision"] == 0
    )
    assert (
        api.post(
            path + "/restore",
            params={"world_id": WORLD},
            json={**body, "expected_revision": moved.json()["revision"]},
            headers=HEADERS,
        ).status_code
        == 200
    )
    assert read(run.run_id).markdown == pin.markdown
