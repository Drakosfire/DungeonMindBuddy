"""Mounted hosted owner boundary; no public release route is installed here."""
import asyncio
from types import SimpleNamespace
from uuid import uuid4

import httpx
import psycopg
import pytest
from fastapi import FastAPI, HTTPException

from apps.live_control_server.routes import guest_releases
from apps.live_control_server.services import hosted_auth
from apps.live_control_server.services.dms_principal import DmsPrincipal


def test_owner_routes_fail_closed_and_require_owner(monkeypatch):
    monkeypatch.setenv(hosted_auth.DEPLOYMENT_ENVIRONMENT_ENV, "production")
    monkeypatch.setenv(hosted_auth.AUTH_MODE_ENV, "hosted_dms")
    monkeypatch.setenv(hosted_auth.TRUSTED_FRONTEND_ORIGINS_ENV, "https://buddy.example")
    monkeypatch.setattr(hosted_auth, "hosted_world_access", lambda: {"world": frozenset({"owner", "other"})})
    def owned(subject, world_id):
        if subject != "owner" or world_id != "world":
            raise HTTPException(status_code=403)
        return SimpleNamespace(world_id=world_id)
    monkeypatch.setattr(guest_releases, "_owned_world", owned)
    monkeypatch.setattr(guest_releases.guest_release, "owner_generation", lambda **_: 0)
    monkeypatch.setattr(guest_releases.guest_release, "pointer_status", lambda **_: (None, 0))
    monkeypatch.setattr(guest_releases.guest_release, "list_candidates", lambda **_: [{"release_id": "candidate", "created_at": "2026-11-20T00:00:00+00:00"}])
    monkeypatch.setattr(guest_releases.guest_release, "list_published", lambda **_: [{"release_id": "published", "current": True, "reviewable": True}])
    app = FastAPI()
    app.include_router(guest_releases.router)
    from apps.live_control_server.main import HOSTED_WORLD_SCOPE_RESOLVERS
    routes = {key: value for key, value in HOSTED_WORLD_SCOPE_RESOLVERS.items()
              if value is guest_releases.resolve_hosted_guest_release_world}
    assert len(routes) == 13
    hosted_auth.install_hosted_request_boundary(app, world_scope_resolvers=routes)
    async def principal(request):
        subject = request.headers.get("x-test-subject")
        return DmsPrincipal(subject) if subject else None
    app.state.dms_principal_resolver = principal
    def request(method, path, **kwargs):
        async def run():
            async with httpx.AsyncClient(transport=httpx.ASGITransport(app=app), base_url="http://test") as client:
                return await asyncio.wait_for(client.request(method, path, **kwargs), timeout=3)
        return asyncio.run(run())
    path = "/api/live/worlds/world/guest-releases/status"
    assert request("GET", path).status_code == 401
    assert request("GET", path, headers={"x-test-subject": "owner"}).status_code == 503
    monkeypatch.setenv("DMB_GUEST_RELEASE_ENABLED", "1")
    assert request("GET", path, headers={"x-test-subject": "other"}).status_code == 403
    response = request("GET", path, headers={"x-test-subject": "owner"})
    assert response.status_code == 200 and response.json() == {"public_id": None, "version": 0}
    assert response.headers["cache-control"] == "no-store"
    context = "/api/live/worlds/world/guest-releases/selection-context"
    body = {"document_id": str(uuid4()), "offset": 0}
    headers = {"x-test-subject": "owner", "origin": "https://buddy.example"}
    monkeypatch.setattr(guest_releases, "selection_options", lambda **_: {"graph_revision": "rev", "fields": [], "sources": []})
    assert request("POST", context, json=body).status_code == 401
    assert request("POST", context, json=body, headers={"x-test-subject": "other", "origin": "https://buddy.example"}).status_code == 403
    response = request("POST", context, json=body, headers=headers)
    assert response.status_code == 200 and response.headers["cache-control"] == "no-store"
    assert request("POST", context, json={**body, "offset": -1}, headers=headers).status_code == 422
    assert request("POST", context, json=body, headers={"x-test-subject": "owner", "origin": "https://evil.example"}).status_code == 403
    options = "/api/live/worlds/world/guest-releases/selection-options"
    monkeypatch.setattr(guest_releases, "selection_options", lambda **_: {"graph_revision": "rev", "fields": [], "sources": []})
    assert request("GET", options).status_code == 401
    assert request("GET", options, headers={"x-test-subject": "other"}).status_code == 403
    response = request("GET", options, headers={"x-test-subject": "owner"})
    assert response.status_code == 200 and response.json()["graph_revision"] == "rev"
    assert response.headers["cache-control"] == "no-store"
    image_id = uuid4()
    monkeypatch.setattr(guest_releases, "list_media", lambda **_: {"assets": [{"id": str(image_id)}], "next": None})
    monkeypatch.setattr(guest_releases, "preview_media", lambda **_: ("image/png", b"sanitized"))
    media_list = "/api/live/worlds/world/guest-releases/selection-media/list"
    image_preview = f"/api/live/worlds/world/guest-releases/selection-media/{image_id}"
    assert request("GET", image_preview).status_code == 401
    assert request("GET", image_preview, headers={"x-test-subject": "other"}).status_code == 403
    image_response = request("GET", image_preview, headers={"x-test-subject": "owner"})
    assert image_response.content == b"sanitized" and image_response.headers["cache-control"] == "no-store"
    owner_headers = {"x-test-subject": "owner", "origin": "https://buddy.example"}
    assert request("POST", media_list, json={}, headers=owner_headers).json()["assets"][0]["id"] == str(image_id)
    assert request("POST", media_list, json={"before_id": str(image_id)}, headers=owner_headers).status_code == 422
    assert request("POST", media_list, json={}, headers={"x-test-subject": "owner", "origin": "https://evil.example"}).status_code == 403
    listing = "/api/live/worlds/world/guest-releases/candidates"
    assert request("GET", listing).status_code == 401
    assert request("GET", listing, headers={"x-test-subject": "other"}).status_code == 403
    listed = request("GET", listing, headers={"x-test-subject": "owner"})
    assert listed.status_code == 200 and listed.json()["candidates"][0]["release_id"] == "candidate"
    assert listed.headers["cache-control"] == "no-store"
    history = "/api/live/worlds/world/guest-releases/published"
    assert request("GET", history).status_code == 401
    assert request("GET", history, headers={"x-test-subject": "other"}).status_code == 403
    response = request("GET", history, headers={"x-test-subject": "owner"})
    assert response.status_code == 200 and response.json()["releases"][0]["current"]
    assert response.headers["cache-control"] == "no-store"
    release_id, asset_id = uuid4(), uuid4()
    monkeypatch.setattr(guest_releases.guest_release, "review", lambda **_: ({"sources": []}, "a" * 64))
    monkeypatch.setattr(guest_releases.guest_release, "review_source_visibility", lambda **_: {})
    monkeypatch.setattr(guest_releases.guest_release, "review_asset", lambda **_: ("image/png", b"image"))
    preview = f"/api/live/worlds/world/guest-releases/candidates/{release_id}"
    assert request("GET", preview, headers={"x-test-subject": "other"}).status_code == 403
    response = request("GET", preview, headers={"x-test-subject": "owner"})
    assert response.status_code == 200 and response.json()["digest"] == "a" * 64
    response = request("GET", preview + f"/assets/{asset_id}", headers={"x-test-subject": "owner"})
    assert response.status_code == 200 and response.content == b"image"
    assert response.headers["cache-control"] == "no-store" and response.headers["x-content-type-options"] == "nosniff"
    def invalid_publication(**_):
        raise guest_releases.GuestReleaseEvidenceError("private native detail")
    monkeypatch.setattr(guest_releases, "publish_candidate", invalid_publication)
    publication = request("POST", preview + "/publish",
        headers={"x-test-subject": "owner", "origin": "https://buddy.example"},
        json={"digest": "a" * 64, "expected_version": 0, "operation_id": str(uuid4())})
    assert publication.status_code == 409 and publication.json() == {"detail": {"code": "guest_release_validation_failed"}}
    assert publication.headers["cache-control"] == "no-store"
    def invalid_assertion(**_):
        raise guest_releases.GuestReleaseAssertionError("private assertion identity")
    monkeypatch.setattr(guest_releases, "publish_candidate", invalid_assertion)
    publication = request("POST", preview + "/publish",
        headers={"x-test-subject": "owner", "origin": "https://buddy.example"},
        json={"digest": "a" * 64, "expected_version": 0, "operation_id": str(uuid4())})
    assert publication.status_code == 409 and "private assertion identity" not in publication.text
    assert request("GET", path + "?world_id=foreign", headers={"x-test-subject": "owner"}).status_code == 403
    body = {"graph_revision": "rev", "nodes": [], "relationships": [], "sources": [], "asset_ids": []}
    response = request("POST", "/api/live/worlds/world/guest-releases", json=body,
                           headers={"x-test-subject": "owner", "origin": "https://buddy.example"})
    assert response.status_code == 503
    monkeypatch.setattr(guest_releases, "prepare", invalid_assertion)
    response = request("POST", "/api/live/worlds/world/guest-releases", json=body,
                       headers={"x-test-subject": "owner", "origin": "https://buddy.example"})
    assert response.status_code == 409 and response.headers["cache-control"] == "no-store"
    assert "private assertion identity" not in response.text
    assert request("POST", "/api/live/worlds/world/guest-releases", json=body,
                       headers={"x-test-subject": "owner", "origin": "https://evil.example"}).status_code == 403
    assert request("GET", "/api/live/guest-releases/anything").status_code == 401


@pytest.mark.parametrize("route", ["options", "media_list", "preview"])
@pytest.mark.parametrize("transfer_back", [False, True])
def test_inventory_denies_inflight_ownership_change(application_state_dsn, monkeypatch, route, transfer_back):
    from application_state.world_catalog.service import create_world
    from apps.live_control_server.main import HOSTED_WORLD_SCOPE_RESOLVERS

    world = create_world(name="Ownership race", owner_subject="owner").record.world_id
    monkeypatch.setenv(hosted_auth.DEPLOYMENT_ENVIRONMENT_ENV, "production")
    monkeypatch.setenv(hosted_auth.AUTH_MODE_ENV, "hosted_dms")
    monkeypatch.setenv(hosted_auth.TRUSTED_FRONTEND_ORIGINS_ENV, "https://buddy.example")
    monkeypatch.setenv("DMB_GUEST_RELEASE_ENABLED", "1")
    monkeypatch.setattr(hosted_auth, "hosted_world_access", lambda: {world: frozenset({"owner"})})
    monkeypatch.setattr(guest_releases, "_owned_world", lambda subject, world_id: SimpleNamespace(world_id=world_id))

    def read_after_transfer(**_):
        # The read starts after the first owner check; simulate another owner's
        # private content becoming visible before the slow read completes.
        with psycopg.connect(application_state_dsn) as conn:
            conn.execute("UPDATE workspace.managed_world SET owner_subject='other' WHERE world_id=%s", (world,))
            if transfer_back:
                conn.execute("UPDATE workspace.managed_world SET owner_subject='owner' WHERE world_id=%s", (world,))
        if route == "preview":
            return "image/png", b"new owner's private image"
        return {"private": "new owner's private data"}

    monkeypatch.setattr(guest_releases, {"options": "selection_options", "media_list": "list_media", "preview": "preview_media"}[route], read_after_transfer)
    app = FastAPI()
    app.include_router(guest_releases.router)
    routes = {key: value for key, value in HOSTED_WORLD_SCOPE_RESOLVERS.items()
              if value is guest_releases.resolve_hosted_guest_release_world}
    hosted_auth.install_hosted_request_boundary(app, world_scope_resolvers=routes)
    async def principal(request):
        return DmsPrincipal("owner")
    app.state.dms_principal_resolver = principal

    async def run():
        async with httpx.AsyncClient(transport=httpx.ASGITransport(app=app), base_url="http://test") as client:
            base = f"/api/live/worlds/{world}/guest-releases"
            if route == "options":
                return await client.get(base + "/selection-options")
            if route == "preview":
                return await client.get(base + f"/selection-media/{uuid4()}")
            return await client.post(base + "/selection-media/list", json={}, headers={"origin": "https://buddy.example"})

    response = asyncio.run(run())
    assert response.status_code in (404, 409)
    assert response.headers["cache-control"] == "no-store"
    assert b"new owner's private" not in response.content


def test_independent_context_pagination_uses_exact_owner_source(monkeypatch):
    from apps.live_control_server.services import guest_release_selection as selection
    document = uuid4()
    world = "world"
    text = "\n".join(f"Line {index}" for index in range(205))
    evidence = SimpleNamespace(evidence_role="context")
    parsed = SimpleNamespace(get_evidence=lambda key: evidence if key == "ev" else None)
    access = SimpleNamespace(parsed=parsed)
    binding = SimpleNamespace(native_world_id="native")
    head = SimpleNamespace(head_revision_id="revision")
    source = SimpleNamespace(origin=SimpleNamespace(namespace="dungeonbuddy.workspace-document-registry",
        object_id=str(document), revision_id="registry-revision:1"),
        source_revision=SimpleNamespace(content_sha256="a" * 64), evidence_ref_ids=["ev"])
    catalog = SimpleNamespace(complete=True, sources=[source])
    page = SimpleNamespace(page=SimpleNamespace(status="active", object_revision=1, title="Recap"),
        metadata=SimpleNamespace(visibility_state="internal"),
        revision=SimpleNamespace(content_sha256="a" * 64, revision_n=1, markdown=text))
    monkeypatch.setattr(selection, "resolve_managed_world_binding", lambda _: binding)
    monkeypatch.setattr(selection.native_registry_source, "read_repository", lambda: SimpleNamespace(get_head=lambda _: head))
    monkeypatch.setattr(selection, "read_owner_graph", lambda **_: (binding, None,
        SimpleNamespace(listing=SimpleNamespace(admitted_assertion_ids=[])), access))
    monkeypatch.setattr(selection, "list_admitted_native_text_sources", lambda *_, **__: catalog)
    monkeypatch.setattr(selection, "committed_page", lambda *_, **__: page)
    monkeypatch.setattr(selection, "open_admitted_native_text", lambda *_: SimpleNamespace(status="available", body_text=text,
        span_start_byte=0, span_end_byte=len(text.encode())))
    monkeypatch.setattr(selection, "selected_page_excerpt", lambda **kwargs: ({"id": "local", "text": kwargs["expected_excerpt"]}, ("local",) * 9))
    monkeypatch.setattr(selection, "verify_source_citation", lambda **_: None)
    inventory = selection.selection_options(world_id=world)
    assert inventory["sources"] == [] and inventory["context_documents"] == [{"document_id": str(document), "title": "Recap"}]
    pages = [selection.selection_options(world_id=world, context_document_id=str(document), offset=offset)
             for offset in (0, 100, 200)]
    assert [len(page["sources"]) for page in pages] == [100, 100, 5]
    assert [page["next_offset"] for page in pages] == [100, 200, None]
    assert [page["sources"][0]["excerpt"] for page in pages] == ["Line 0", "Line 100", "Line 200"]
    assert selection.selection_options(world_id=world, context_document_id=str(uuid4()))["sources"] == []
