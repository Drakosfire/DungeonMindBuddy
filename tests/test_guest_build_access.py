from __future__ import annotations

import pytest
from fastapi import FastAPI
from starlette.testclient import TestClient

from apps.live_control_server.native_graph_demo import NativeGraphDemoService
from apps.live_control_server.routes import index_graph, live, workspace_documents
from apps.live_control_server.services import index_graph as graph_service
from apps.live_control_server.services.hosted_auth import install_hosted_request_boundary
from dungeonmind.infrastructure.memory.vnext_sources import InMemoryNativeSourceEvidenceRepository


def test_guest_plan_routes_are_default_off(monkeypatch):
    from apps.live_control_server.services.guest_build_access import matches_guest_build_route
    monkeypatch.delenv("DMB_HOSTED_GUEST_PLAN_ENABLED", raising=False)
    assert not matches_guest_build_route("GET", "/api/live/workspace-documents/world-plans")
    assert not matches_guest_build_route("POST", "/api/live/workspace-documents/world-plans")
    monkeypatch.setenv("DMB_HOSTED_GUEST_PLAN_ENABLED", "1")
    assert matches_guest_build_route("GET", "/api/live/workspace-documents/world-plans")
    assert matches_guest_build_route("POST", "/api/live/workspace-documents/world-plans")
    assert not matches_guest_build_route("DELETE", "/api/live/workspace-documents/world-plans")


@pytest.fixture
def guests(application_state_dsn, monkeypatch, tmp_path):
    repo = InMemoryNativeSourceEvidenceRepository()
    seed = NativeGraphDemoService(repo, tmp_path / "seed", storage_label="memory")
    try:
        source = seed.graph()
    finally:
        seed.close()
    monkeypatch.setattr(graph_service, "repository", lambda: repo)
    monkeypatch.setenv("DMB_DEPLOYMENT_ENVIRONMENT", "production")
    monkeypatch.setenv("DMB_AUTH_MODE", "hosted_dms")
    monkeypatch.setenv("DMB_HOSTED_GUEST_GRAPH_ENABLED", "1")
    monkeypatch.setenv("DMB_HOSTED_GUEST_BUILD_ENABLED", "1")
    monkeypatch.setenv("DMB_GUEST_GRAPH_SOURCE_SPACE", source["world_id"])
    monkeypatch.setenv("DMB_GUEST_GRAPH_SOURCE_REVISION", source["revision_id"])
    monkeypatch.setenv("AUTH_TRUSTED_FRONTEND_ORIGINS", "https://buddy.example")
    monkeypatch.setattr(workspace_documents, "repo_root", lambda: tmp_path)
    monkeypatch.setattr(live, "repo_root", lambda: tmp_path)
    app = FastAPI()
    app.include_router(index_graph.router)
    app.include_router(workspace_documents.router)
    app.include_router(live.router)
    install_hosted_request_boundary(app)
    async def signed_out(_request):
        return None
    app.state.dms_principal_resolver = signed_out
    headers = {"Origin": "https://buddy.example", "Sec-Fetch-Site": "same-origin"}
    clients = [TestClient(app, base_url="https://buddy.example", headers=headers) for _ in range(2)]
    contexts = []
    for client in clients:
        start = client.post("/api/live/index-graph/session")
        assert start.status_code == 200
        csrf = start.json()["csrf_token"]
        world = client.post("/api/live/index-graph/world", headers={"X-DMB-Index-Graph-CSRF": csrf})
        assert world.status_code == 200
        contexts.append((client, csrf, world.json()["world_id"]))
    return contexts, repo, source


def test_guest_create_save_and_reopen_isolated_document(guests):
    contexts, repo, source = guests
    (first, token, world), (second, other_token, other_world) = contexts
    headers = {"X-DMB-Index-Graph-CSRF": token}
    body = {"title": "Guest notes", "world_id": world, "campaign_id": world, "kind": "worldbuilding_source", "source_domain": "worldbuilding", "document_class": "lore", "authority_state": "draft", "visibility_state": "internal"}
    created = first.post("/api/live/workspace-documents", headers=headers, json=body)
    assert created.status_code == 200, created.text
    doc = created.json()["document_id"]
    assert second.get(f"/api/live/workspace-documents/{doc}").status_code == 403
    assert second.get("/api/live/workspace-documents/pages/inventory", params={"world_id": world}).status_code == 403
    prepared = first.post("/api/live/tiptap/markdown-write/prepare", headers=headers,
                          json={"document_id": doc, "markdown": "# Guest note\n\nA fresh clue."})
    assert prepared.status_code == 200, prepared.text
    receipt = prepared.json()
    committed = first.post("/api/live/tiptap/markdown-write/commit", headers=headers,
                           json={"document_id": doc, "markdown": "# Guest note\n\nA fresh clue.",
                                 "writer_confirm_token": receipt["writer_confirm_token"],
                                 "expected_revision": receipt["registry_revision"]})
    assert committed.status_code == 200, committed.text
    opened = first.get(f"/api/live/workspace-documents/{doc}/snapshot")
    assert opened.status_code == 200, opened.text
    assert "A fresh clue." in opened.json()["markdown"]
    assert second.get(f"/api/live/workspace-documents/{doc}/snapshot").status_code == 403
    assert second.post("/api/live/tiptap/markdown-write/prepare", headers={"X-DMB-Index-Graph-CSRF": other_token},
                       json={"document_id": doc, "markdown": "Cross-session attempt"}).status_code == 403
    assert second.post("/api/live/tiptap/markdown-write/commit", headers={"X-DMB-Index-Graph-CSRF": other_token},
                       json={"document_id": doc, "markdown": "# Guest note\n\nA fresh clue.",
                             "writer_confirm_token": receipt["writer_confirm_token"], "expected_revision": receipt["registry_revision"]}).status_code == 403
    assert repo.get_head(source["world_id"]).head_revision_id == source["revision_id"]
    reset = first.post("/api/live/index-graph/reset", headers=headers)
    assert reset.status_code == 200
    assert first.get(f"/api/live/workspace-documents/{doc}").status_code in (401, 403)
    assert other_world != world


def test_guest_plan_create_and_isolation(guests, monkeypatch):
    monkeypatch.setenv("DMB_HOSTED_GUEST_PLAN_ENABLED", "1")
    contexts, _, _ = guests
    (first, token, world), (second, _, other_world) = contexts
    headers = {"X-DMB-Index-Graph-CSRF": token}
    path = "/api/live/workspace-documents/world-plans"
    body = {"schema_version": "dmb_workspace_document_create_v2", "scope_mode": "world", "world_id": world, "title": "Guest plan"}
    assert first.post(path, json=body).status_code == 403
    assert first.post(path, headers=headers, json={**body, "world_id": other_world}).status_code == 403
    assert first.post(path, headers={**headers, "Origin": "https://bad.example"}, json=body).status_code == 403
    assert first.get(path, params=[("world_id", world), ("world_id", world)]).status_code in (400, 403)
    created = first.post(path, headers=headers, json=body)
    assert created.status_code == 200, created.text
    doc = created.json()["document_id"]
    inventory = first.get(path, params={"world_id": world})
    assert inventory.status_code == 200, inventory.text
    assert any(record["document_id"] == doc for record in inventory.json()["records"])
    draft = {"document_id": doc, "markdown": "# Guest plan\n\nA new clue.", "scope_mode": "world", "world_id": world,
             "schema_version": "dmb_tiptap_markdown_write_prepare_v2"}
    prepared = first.post("/api/live/tiptap/markdown-write/prepare", headers=headers, json=draft)
    assert prepared.status_code == 200, prepared.text
    assert second.post("/api/live/tiptap/markdown-write/prepare", headers={"X-DMB-Index-Graph-CSRF": contexts[1][1]}, json=draft).status_code == 403
    receipt = prepared.json()
    commit = {**draft, "schema_version": "dmb_tiptap_markdown_write_commit_v2",
              "writer_confirm_token": receipt["writer_confirm_token"], "expected_revision": receipt["registry_revision"]}
    saved = first.post("/api/live/tiptap/markdown-write/commit", headers=headers, json=commit)
    assert saved.status_code == 200, saved.text
    snapshot = first.get(f"/api/live/workspace-documents/{doc}/snapshot")
    assert snapshot.status_code == 200, snapshot.text
    assert "A new clue." in snapshot.json()["markdown"]
    assert second.get(f"/api/live/workspace-documents/{doc}/snapshot").status_code == 403
    assert second.get(path, params={"world_id": world}).status_code == 403
    assert first.post("/api/live/index-graph/reset", headers=headers).status_code == 200
    assert first.get(f"/api/live/workspace-documents/{doc}/snapshot").status_code in (401, 403)


def test_released_pages_open_through_ordinary_guest_build(guests, monkeypatch, tmp_path):
    import hashlib
    import json

    contexts, _, source = guests
    (first, token, world), (second, _, other_world) = contexts
    bundle = tmp_path / 'released-documents.json'
    bundle.write_text(json.dumps({'version': 1, 'graph_space': source['world_id'],
                                  'graph_revision': source['revision_id'],
                                  'documents': [{'title': 'Apprentice', 'markdown': 'A source.'}]}))
    monkeypatch.setenv('DMB_GUEST_DOCUMENT_BUNDLE', str(bundle))
    monkeypatch.setenv('DMB_GUEST_DOCUMENT_BUNDLE_SHA256', hashlib.sha256(bundle.read_bytes()).hexdigest())
    inventory = first.get('/api/live/workspace-documents/pages/inventory', params={'world_id': world})
    assert inventory.status_code == 200, inventory.text
    record, = inventory.json()['records']
    assert record['title'] == 'Apprentice'
    doc = record['document_id']
    snapshot = first.get(f'/api/live/workspace-documents/{doc}/snapshot')
    assert snapshot.status_code == 200, snapshot.text
    assert 'A source.' in snapshot.json()['markdown']
    assert second.get(f'/api/live/workspace-documents/{doc}/snapshot').status_code == 403
    other = second.get('/api/live/workspace-documents/pages/inventory', params={'world_id': other_world})
    assert other.status_code == 200 and other.json()['records'][0]['document_id'] != doc
    assert first.post('/api/live/index-graph/reset', headers={'X-DMB-Index-Graph-CSRF': token}).status_code == 200
    assert first.get(f'/api/live/workspace-documents/{doc}/snapshot').status_code in (401, 403)


def test_guest_build_rejects_cross_world_and_missing_csrf(guests):
    (first, token, world), (second, other_token, other_world) = guests[0]
    body = {"title": "Foreign", "world_id": other_world, "campaign_id": other_world, "kind": "worldbuilding_source", "source_domain": "worldbuilding", "document_class": "lore", "authority_state": "draft", "visibility_state": "internal"}
    assert first.post("/api/live/workspace-documents", headers={"X-DMB-Index-Graph-CSRF": token}, json=body).status_code == 403
    body.update(world_id=world, campaign_id=world)
    assert first.post("/api/live/workspace-documents", json=body).status_code == 403
    assert first.post("/api/live/workspace-documents", headers={"Origin": "https://bad.example", "X-DMB-Index-Graph-CSRF": token}, json=body).status_code == 403
    assert first.get("/api/live/world-containers").status_code == 401
    assert first.get("/api/live/workspace-documents/pages/inventory", params=[("world_id", world), ("world_id", other_world)]).status_code in (400, 403)


def test_guest_document_limit_is_atomic_under_concurrent_creates(guests, monkeypatch):
    from concurrent.futures import ThreadPoolExecutor
    from apps.live_control_server.services import guest_build_access

    (client, token, world), _ = guests[0]
    monkeypatch.setattr(guest_build_access, "MAX_GUEST_PAGES", 1)
    body = {"title": "Guest note", "world_id": world, "campaign_id": world,
            "kind": "worldbuilding_source", "source_domain": "worldbuilding", "document_class": "lore",
            "authority_state": "draft", "visibility_state": "internal"}
    def create():
        return client.post("/api/live/workspace-documents", headers={"X-DMB-Index-Graph-CSRF": token}, json=body)
    with ThreadPoolExecutor(max_workers=2) as pool:
        results = list(pool.map(lambda _: create(), range(2)))
    assert sorted(response.status_code for response in results) == [200, 409]
    inventory = client.get("/api/live/workspace-documents/pages/inventory", params={"world_id": world})
    assert inventory.status_code == 200
    assert len(inventory.json()["records"]) == 1


def test_guest_revision_budget_does_not_replace_saved_content(guests, monkeypatch):
    from apps.live_control_server.services import guest_build_access

    (client, token, world), _ = guests[0]
    monkeypatch.setattr(guest_build_access, "MAX_GUEST_REVISIONS", 1)
    headers = {"X-DMB-Index-Graph-CSRF": token}
    body = {"title": "Guest note", "world_id": world, "campaign_id": world,
            "kind": "worldbuilding_source", "source_domain": "worldbuilding", "document_class": "lore",
            "authority_state": "draft", "visibility_state": "internal"}
    document = client.post("/api/live/workspace-documents", headers=headers, json=body).json()["document_id"]
    submitted = []
    def save(text):
        prepared = client.post("/api/live/tiptap/markdown-write/prepare", headers=headers,
                               json={"document_id": document, "markdown": text})
        assert prepared.status_code == 200
        receipt = prepared.json()
        packet = {"document_id": document, "markdown": text,
                  "writer_confirm_token": receipt["writer_confirm_token"],
                  "expected_revision": receipt["registry_revision"]}
        submitted.append(packet)
        return client.post("/api/live/tiptap/markdown-write/commit", headers=headers, json=packet)
    first_save = save("First saved version")
    assert first_save.status_code == 200
    assert client.post("/api/live/tiptap/markdown-write/commit", headers=headers, json=submitted[0]).status_code == 200
    assert save("Second saved version").status_code == 409
    snapshot = client.get(f"/api/live/workspace-documents/{document}/snapshot")
    assert snapshot.status_code == 200
    assert snapshot.json()["markdown"] == "First saved version\n"


def test_authenticated_identity_does_not_fall_back_to_guest_cookie(guests):
    from apps.live_control_server.services.dms_principal import DmsPrincipal
    (client, token, world), _ = guests[0]
    async def signed_in(_request):
        return DmsPrincipal(subject="different-owner")
    client.app.state.dms_principal_resolver = signed_in
    body = {"title": "Guest note", "world_id": world, "campaign_id": world,
            "kind": "worldbuilding_source", "source_domain": "worldbuilding", "document_class": "lore",
            "authority_state": "draft", "visibility_state": "internal"}
    assert client.post("/api/live/workspace-documents", headers={"X-DMB-Index-Graph-CSRF": token}, json=body).status_code == 403


def test_reset_waits_for_guest_commit_transaction(guests, application_state_dsn, monkeypatch):
    import time
    from concurrent.futures import ThreadPoolExecutor
    from threading import Event
    from application_state.engine import connect
    from apps.live_control_server.services import guest_build_access

    (client, token, world), _ = guests[0]
    headers = {"X-DMB-Index-Graph-CSRF": token}
    body = {"title": "Race note", "world_id": world, "campaign_id": world,
            "kind": "worldbuilding_source", "source_domain": "worldbuilding", "document_class": "lore",
            "authority_state": "draft", "visibility_state": "internal"}
    doc = client.post("/api/live/workspace-documents", headers=headers, json=body).json()["document_id"]
    prepared = client.post("/api/live/tiptap/markdown-write/prepare", headers=headers,
                           json={"document_id": doc, "markdown": "A racing edit"}).json()
    packet = {"document_id": doc, "markdown": "A racing edit", "writer_confirm_token": prepared["writer_confirm_token"],
              "expected_revision": prepared["registry_revision"]}
    entered, release = Event(), Event()
    original = guest_build_access.guest_write_capacity
    def hold_transaction(*args, **kwargs):
        original(*args, **kwargs)
        if not kwargs.get("creating"):
            entered.set()
            if not release.wait(10):
                raise RuntimeError("guest commit race test timed out")
    monkeypatch.setattr(guest_build_access, "guest_write_capacity", hold_transaction)
    with ThreadPoolExecutor(max_workers=2) as pool:
        commit = pool.submit(client.post, "/api/live/tiptap/markdown-write/commit", headers=headers, json=packet)
        try:
            assert entered.wait(10)
            reset = pool.submit(client.post, "/api/live/index-graph/reset", headers=headers)
            deadline = time.monotonic() + 5
            with connect(application_state_dsn) as connection:
                while time.monotonic() < deadline:
                    waiting = connection.execute(
                        "SELECT count(*) FROM pg_stat_activity WHERE datname = current_database() AND wait_event_type = 'Lock'"
                    ).fetchone()[0]
                    if waiting:
                        break
                    time.sleep(0.05)
            assert waiting > 0, "reset never reached the session lock"
        finally:
            release.set()
        assert commit.result(timeout=10).status_code in (200, 401, 403)
        assert reset.result(timeout=10).status_code == 200
    assert client.get(f"/api/live/workspace-documents/{doc}").status_code in (401, 403)


@pytest.mark.parametrize(("limit", "value"), [("MAX_GUEST_REVISIONS", 1), ("MAX_GUEST_SAVED_BYTES", 12)])
def test_guest_saved_content_limits_are_atomic_across_documents(guests, monkeypatch, limit, value):
    from concurrent.futures import ThreadPoolExecutor
    from apps.live_control_server.services import guest_build_access

    (client, token, world), _ = guests[0]
    monkeypatch.setattr(guest_build_access, limit, value)
    headers = {"X-DMB-Index-Graph-CSRF": token}
    body = {"title": "Guest note", "world_id": world, "campaign_id": world,
            "kind": "worldbuilding_source", "source_domain": "worldbuilding", "document_class": "lore",
            "authority_state": "draft", "visibility_state": "internal"}
    documents = [client.post("/api/live/workspace-documents", headers=headers, json=body).json()["document_id"] for _ in range(2)]
    packets = []
    for document in documents:
        prepared = client.post("/api/live/tiptap/markdown-write/prepare", headers=headers,
                               json={"document_id": document, "markdown": "New clue"}).json()
        packets.append({"document_id": document, "markdown": "New clue",
                        "writer_confirm_token": prepared["writer_confirm_token"],
                        "expected_revision": prepared["registry_revision"]})
    with ThreadPoolExecutor(max_workers=2) as pool:
        results = list(pool.map(lambda packet: client.post("/api/live/tiptap/markdown-write/commit", headers=headers, json=packet), packets))
    assert sorted(response.status_code for response in results) == [200, 409]
