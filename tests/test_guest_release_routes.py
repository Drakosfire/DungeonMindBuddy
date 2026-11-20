"""Mounted hosted owner boundary; no public release route is installed here."""
import asyncio
from types import SimpleNamespace
from uuid import uuid4

import httpx
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
    monkeypatch.setattr(guest_releases.guest_release, "pointer_status", lambda **_: (None, 0))
    monkeypatch.setattr(guest_releases.guest_release, "list_candidates", lambda **_: [{"release_id": "candidate", "created_at": "2026-11-20T00:00:00+00:00"}])
    monkeypatch.setattr(guest_releases.guest_release, "list_published", lambda **_: [{"release_id": "published", "current": True, "reviewable": True}])
    app = FastAPI()
    app.include_router(guest_releases.router)
    from apps.live_control_server.main import HOSTED_WORLD_SCOPE_RESOLVERS
    routes = {key: value for key, value in HOSTED_WORLD_SCOPE_RESOLVERS.items()
              if value is guest_releases.resolve_hosted_guest_release_world}
    assert len(routes) == 10
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
    options = "/api/live/worlds/world/guest-releases/selection-options"
    monkeypatch.setattr(guest_releases, "selection_options", lambda **_: {"graph_revision": "rev", "fields": [], "sources": []})
    assert request("GET", options).status_code == 401
    assert request("GET", options, headers={"x-test-subject": "other"}).status_code == 403
    response = request("GET", options, headers={"x-test-subject": "owner"})
    assert response.status_code == 200 and response.json()["graph_revision"] == "rev"
    assert response.headers["cache-control"] == "no-store"
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
