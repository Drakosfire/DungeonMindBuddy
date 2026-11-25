from __future__ import annotations

import pytest
from fastapi import FastAPI
from starlette.testclient import TestClient

from apps.live_control_server.native_graph_demo import NativeGraphDemoService
from apps.live_control_server.routes import index_graph, live, workspace_documents, play_runs
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


def test_guest_play_routes_require_both_flags(monkeypatch):
    from apps.live_control_server.services.guest_build_access import matches_guest_build_route
    monkeypatch.delenv("DMB_HOSTED_GUEST_PLAN_ENABLED", raising=False)
    monkeypatch.setenv("DMB_HOSTED_GUEST_PLAY_ENABLED", "1")
    assert not matches_guest_build_route("GET", "/api/live/world-play-runs/v2")
    monkeypatch.setenv("DMB_HOSTED_GUEST_PLAN_ENABLED", "1")
    assert matches_guest_build_route("GET", "/api/live/world-play-runs/v2")
    assert not matches_guest_build_route("DELETE", "/api/live/world-play-runs/v2")


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
    app.include_router(play_runs.router)
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


def test_guest_play_run_is_bound_to_session(guests, monkeypatch):
    from application_state.content.service import create_world_plan, commit_plan
    from tests.application_state.play_runtime_helpers import V2_SOURCE_MARKDOWN, gate_progress
    from apps.live_control_server.services import guest_build_access
    from apps.live_control_server.services.play_run_edition_structure import structure_signature
    from uuid import uuid4
    monkeypatch.setenv("DMB_HOSTED_GUEST_PLAN_ENABLED", "1")
    monkeypatch.setenv("DMB_HOSTED_GUEST_PLAY_ENABLED", "1")
    contexts, _, _ = guests
    (first, token, world), (second, other_token, other_world) = contexts
    plan = create_world_plan(title="Guest play", world_id=world)
    plan, revision = commit_plan(str(plan.work_object_id), V2_SOURCE_MARKDOWN,
                                 expected_world_id=world, expected_revision=plan.object_revision)
    run = str(uuid4())
    path = f"/api/live/world-play-runs/v2/{run}"
    scenes = structure_signature(V2_SOURCE_MARKDOWN)["membership"]["scenes"]
    body = {"schema_version": "dmb_world_session_create_v1", "playable_artifact_id": str(plan.work_object_id),
            "expected_playable_revision": revision.revision_n, "expected_playable_work_revision_id": str(revision.work_revision_id),
            "expected_playable_content_sha256": revision.content_sha256, "entry_scene_id": scenes[0]["scene_id"],
            "encounters": [{"scene_id": scene["scene_id"], "template": None} for scene in scenes]}
    headers = {"X-DMB-Index-Graph-CSRF": token}
    source = {key: body[key] for key in ("playable_artifact_id", "expected_playable_revision", "expected_playable_work_revision_id", "expected_playable_content_sha256")}
    revision_read = first.get(f"/api/live/workspace-documents/{plan.work_object_id}/committed-revision")
    assert revision_read.status_code == 200, revision_read.text
    preview = first.post("/api/live/world-play-runs/v2/preparation", params={"world_id": world}, headers=headers, json=source)
    assert preview.status_code == 200, preview.text
    assert first.put(path, params={"world_id": world}, json=body).status_code == 403
    assert first.put(path, params={"world_id": world}, headers={**headers, "Origin": "https://bad.example"}, json=body).status_code == 403
    assert first.get(path, params=[("world_id", world), ("world_id", world)]).status_code in (400, 403)
    assert second.put(path, params={"world_id": world}, headers={"X-DMB-Index-Graph-CSRF": other_token}, json=body).status_code == 403
    created = first.put(path, params={"world_id": world}, headers=headers, json=body)
    assert created.status_code == 200, created.text
    monkeypatch.setattr(guest_build_access, "MAX_GUEST_RUNS", 1)
    assert first.put(path, params={"world_id": world}, headers=headers, json=body).status_code == 200
    assert first.put(f"/api/live/world-play-runs/v2/{uuid4()}", params={"world_id": world}, headers=headers, json=body).status_code == 409
    progress = first.put(f"{path}/progress", params={"world_id": world}, headers=headers,
                         json={"expected_run_revision": 1, "progress": gate_progress().model_dump(mode="json")})
    assert progress.status_code == 200, progress.text
    assert progress.json()["progress"]["selections"]["choice:route"] == "option:fire"
    assert first.put("/api/live/world-play-runs/v2/active", params={"world_id": world}, headers=headers,
                     json={"run_id": run}).status_code == 200
    reopened = first.get(path, params={"world_id": world})
    assert reopened.status_code == 200
    assert reopened.json()["progress"]["selections"]["choice:route"] == "option:fire"
    assert first.get(f"{path}/reference-manifest", params={"world_id": world}).status_code == 200
    assert first.get(f"{path}/content", params={"world_id": world}).status_code == 200
    assert second.get(path, params={"world_id": other_world}).status_code in (403, 404)
    assert first.post("/api/live/index-graph/reset", headers=headers).status_code == 200
    assert first.get(path, params={"world_id": world}).status_code in (401, 403)


@pytest.mark.parametrize("operation", ["create", "progress"])
def test_guest_play_write_serializes_with_reset(guests, application_state_dsn, monkeypatch, operation):
    from concurrent.futures import ThreadPoolExecutor
    from threading import Event
    from uuid import uuid4
    import time
    from application_state.content.service import create_world_plan, commit_plan
    from application_state.engine import connect
    from apps.live_control_server.services import guest_build_access
    from apps.live_control_server.services.play_run_edition_structure import structure_signature
    from tests.application_state.play_runtime_helpers import V2_SOURCE_MARKDOWN, gate_progress
    monkeypatch.setenv("DMB_HOSTED_GUEST_PLAN_ENABLED", "1")
    monkeypatch.setenv("DMB_HOSTED_GUEST_PLAY_ENABLED", "1")
    (client, token, world), _ = guests[0]
    plan = create_world_plan(title="Guest play", world_id=world)
    plan, revision = commit_plan(str(plan.work_object_id), V2_SOURCE_MARKDOWN, expected_world_id=world, expected_revision=plan.object_revision)
    scenes = structure_signature(V2_SOURCE_MARKDOWN)["membership"]["scenes"]
    body = {"schema_version": "dmb_world_session_create_v1", "playable_artifact_id": str(plan.work_object_id),
            "expected_playable_revision": revision.revision_n, "expected_playable_work_revision_id": str(revision.work_revision_id),
            "expected_playable_content_sha256": revision.content_sha256, "entry_scene_id": scenes[0]["scene_id"],
            "encounters": [{"scene_id": scene["scene_id"], "template": None} for scene in scenes]}
    headers = {"X-DMB-Index-Graph-CSRF": token}
    run_id = str(uuid4())
    path = f"/api/live/world-play-runs/v2/{run_id}"
    if operation == "progress":
        created = client.put(path, params={"world_id": world}, headers=headers, json=body)
        assert created.status_code == 200, created.text
    entered, release = Event(), Event()
    original = guest_build_access._lock_guest_session
    def hold(*args, **kwargs):
        original(*args, **kwargs)
        entered.set()
        if not release.wait(10): raise RuntimeError("guest Play race test timed out")
    monkeypatch.setattr(guest_build_access, "_lock_guest_session", hold)
    with ThreadPoolExecutor(max_workers=2) as pool:
        target = path if operation == "create" else f"{path}/progress"
        payload = body if operation == "create" else {"expected_run_revision": 1, "progress": gate_progress().model_dump(mode="json")}
        create = pool.submit(client.put, target, params={"world_id": world}, headers=headers, json=payload)
        try:
            assert entered.wait(10)
            reset = pool.submit(client.post, "/api/live/index-graph/reset", headers=headers)
            deadline = time.monotonic() + 5
            with connect(application_state_dsn) as connection:
                while time.monotonic() < deadline:
                    waiting = connection.execute("SELECT count(*) FROM pg_stat_activity WHERE datname = current_database() AND wait_event_type = 'Lock'").fetchone()[0]
                    if waiting: break
                    time.sleep(0.05)
            assert waiting > 0
        finally:
            release.set()
        assert create.result(timeout=10).status_code in (200, 401, 403)
        assert reset.result(timeout=10).status_code == 200


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
    from apps.live_control_server.services import guest_build_access
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
    monkeypatch.setattr(guest_build_access, "MAX_GUEST_SAVED_BYTES", 1)
    assert first.post("/api/live/tiptap/markdown-write/commit", headers=headers, json=commit).status_code == 409
    monkeypatch.setattr(guest_build_access, "MAX_GUEST_SAVED_BYTES", 16 * 1024 * 1024)
    saved = first.post("/api/live/tiptap/markdown-write/commit", headers=headers, json=commit)
    assert saved.status_code == 200, saved.text
    monkeypatch.setattr(guest_build_access, "MAX_GUEST_SAVED_BYTES", 1)
    assert first.post("/api/live/tiptap/markdown-write/commit", headers=headers, json=commit).status_code == 200
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


@pytest.mark.parametrize("kind", ["page", "plan"])
def test_reset_waits_for_guest_commit_transaction(guests, application_state_dsn, monkeypatch, kind):
    import time
    from concurrent.futures import ThreadPoolExecutor
    from threading import Event
    from application_state.engine import connect
    from apps.live_control_server.services import guest_build_access

    (client, token, world), _ = guests[0]
    headers = {"X-DMB-Index-Graph-CSRF": token}
    if kind == "plan":
        monkeypatch.setenv("DMB_HOSTED_GUEST_PLAN_ENABLED", "1")
        body = {"title": "Race plan", "world_id": world, "scope_mode": "world"}
        doc = client.post("/api/live/workspace-documents/world-plans", headers=headers, json=body).json()["document_id"]
        scope = {"scope_mode": "world", "world_id": world, "schema_version": "dmb_tiptap_markdown_write_prepare_v2"}
    else:
        body = {"title": "Race note", "world_id": world, "campaign_id": world,
                "kind": "worldbuilding_source", "source_domain": "worldbuilding", "document_class": "lore",
                "authority_state": "draft", "visibility_state": "internal"}
        doc = client.post("/api/live/workspace-documents", headers=headers, json=body).json()["document_id"]
        scope = {}
    prepared = client.post("/api/live/tiptap/markdown-write/prepare", headers=headers,
                           json={"document_id": doc, "markdown": "A racing edit", **scope}).json()
    packet = {"document_id": doc, "markdown": "A racing edit", "writer_confirm_token": prepared["writer_confirm_token"],
              "expected_revision": prepared["registry_revision"]}
    if kind == "plan": packet.update({**scope, "schema_version": "dmb_tiptap_markdown_write_commit_v2"})
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
