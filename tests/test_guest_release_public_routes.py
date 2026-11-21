"""Signed-out delivery is limited to exact release-owned read routes."""
import asyncio
import hashlib
import json
from uuid import uuid4

import httpx
from fastapi import FastAPI

from application_state.errors import ApplicationStateNotFoundError
from apps.live_control_server.routes import guest_release_public
from apps.live_control_server.services import hosted_auth
from apps.live_control_server.services.dms_principal import DmsPrincipal


def test_hosted_guest_read_boundary_and_pointer_pinning(monkeypatch):
    monkeypatch.setenv(hosted_auth.DEPLOYMENT_ENVIRONMENT_ENV, "production")
    monkeypatch.setenv(hosted_auth.AUTH_MODE_ENV, "hosted_dms")
    monkeypatch.setenv("DMB_GUEST_RELEASE_ENABLED", "1")
    monkeypatch.delenv("DMB_GUEST_RELEASE_PUBLIC_ENABLED", raising=False)
    app = FastAPI()
    app.include_router(guest_release_public.router)
    hosted_auth.install_hosted_request_boundary(app)
    async def no_principal(_request):
        return None
    app.state.dms_principal_resolver = no_principal
    public_id, release_id, asset_id, old_release = (uuid4() for _ in range(4))
    path = f"/api/live/guest-releases/{public_id}"
    asset_path = f"{path}/releases/{release_id}/assets/{asset_id}"
    state = {"published": True}
    def manifest(public):
        if not state["published"] or public != public_id:
            raise ApplicationStateNotFoundError("private details")
        return release_id, {"graph": {"nodes": [], "edges": []}, "sources": []}
    def asset(public, release, asset):
        if not state["published"] or (public, release, asset) != (public_id, release_id, asset_id):
            raise ApplicationStateNotFoundError("private details")
        return "image/png", b"copied image"
    monkeypatch.setattr(guest_release_public.guest_release, "public_manifest", manifest)
    monkeypatch.setattr(guest_release_public.guest_release, "public_asset", asset)
    def request(method, url, **kwargs):
        async def run():
            async with httpx.AsyncClient(transport=httpx.ASGITransport(app=app), base_url="http://test") as client:
                return await asyncio.wait_for(client.request(method, url, **kwargs), timeout=3)
        return asyncio.run(run())
    assert request("GET", path).status_code == 401
    monkeypatch.setenv("DMB_GUEST_RELEASE_PUBLIC_ENABLED", "1")
    response = request("GET", path)
    assert response.status_code == 200 and response.json()["release_id"] == str(release_id)
    assert response.headers["cache-control"] == "no-store" and response.headers["x-content-type-options"] == "nosniff"
    response = request("GET", asset_path)
    assert response.status_code == 200 and response.content == b"copied image"
    assert response.headers["cache-control"] == "no-store" and "sandbox" in response.headers["content-security-policy"]
    assert request("GET", f"{path}/releases/{old_release}/assets/{asset_id}").status_code == 404
    assert request("GET", path + "?world_id=private").status_code == 400
    assert request("GET", path, content=b"x").status_code == 400
    assert request("POST", path).status_code == 401
    assert request("HEAD", path).status_code == 401
    assert request("GET", path + "/anything").status_code == 401
    assert request("GET", "/api/live/worlds/private/guest-releases/status").status_code == 401
    state["published"] = False
    response = request("GET", path)
    assert response.status_code == 404 and "private details" not in response.text
    assert response.headers["cache-control"] == "no-store"
    assert request("GET", asset_path).status_code == 404


def test_guest_exception_does_not_bypass_local_loopback(monkeypatch):
    monkeypatch.setenv(hosted_auth.DEPLOYMENT_ENVIRONMENT_ENV, "local")
    monkeypatch.setenv(hosted_auth.AUTH_MODE_ENV, "local_operator")
    monkeypatch.setenv("DMB_GUEST_RELEASE_ENABLED", "1")
    monkeypatch.setenv("DMB_GUEST_RELEASE_PUBLIC_ENABLED", "1")
    app = FastAPI()
    app.include_router(guest_release_public.router)
    hosted_auth.install_hosted_request_boundary(app)
    async def run():
        async with httpx.AsyncClient(transport=httpx.ASGITransport(app=app, client=("203.0.113.9", 1234)), base_url="http://test") as client:
            return await client.get(f"/api/live/guest-releases/{uuid4()}")
    assert asyncio.run(run()).status_code == 403


def test_production_app_release_isolation_and_revocation(application_state_dsn, monkeypatch):
    """Exercise the actual app composition and APP store with synthetic identities."""
    from application_state import guest_release
    from application_state.world_catalog.service import create_world
    from apps.live_control_server.main import create_app
    from tests.test_guest_release_storage import _bind

    world = create_world(name="Guest boundary fixture", owner_subject="owner").record.world_id
    graph = _bind(application_state_dsn, world)
    asset_id = uuid4()
    content = b"synthetic image"
    release_id, digest = guest_release.stage(
        world_id=world, subject="owner", expected_owner_generation=guest_release.owner_generation(world_id=world, subject="owner"),
        manifest={"title": "synthetic public copy", "assets": [{"id": str(asset_id), "mime_type": "image/png",
                  "sha256": hashlib.sha256(content).hexdigest()}]},
        assets=[(asset_id, "image/png", content)], **graph)
    public_id, _ = guest_release.commit_validated_promotion(world_id=world, subject="owner", release_id=release_id,
        digest=digest, expected_version=0, operation_id=uuid4(), source_epoch=1)
    monkeypatch.setenv(hosted_auth.DEPLOYMENT_ENVIRONMENT_ENV, "production")
    monkeypatch.setenv(hosted_auth.AUTH_MODE_ENV, "hosted_dms")
    monkeypatch.setenv(hosted_auth.TRUSTED_FRONTEND_ORIGINS_ENV, "https://buddy.example")
    monkeypatch.setenv(hosted_auth.HOSTED_WORLD_ACCESS_ENV, json.dumps({world: ["owner", "other"]}))
    monkeypatch.setenv("DMB_GUEST_RELEASE_ENABLED", "1")
    monkeypatch.setenv("DMB_GUEST_RELEASE_PUBLIC_ENABLED", "1")
    app = create_app()
    async def principal(request):
        subject = request.headers.get("x-synthetic-subject")
        return DmsPrincipal(subject) if subject else None
    app.state.dms_principal_resolver = principal

    async def run():
        path = f"/api/live/guest-releases/{public_id}"
        asset = f"{path}/releases/{release_id}/assets/{asset_id}"
        private = f"/api/live/worlds/{world}/guest-releases/candidates/{release_id}"
        async with httpx.AsyncClient(transport=httpx.ASGITransport(app=app), base_url="http://test") as first, \
                   httpx.AsyncClient(transport=httpx.ASGITransport(app=app), base_url="http://test") as second:
            for client in (first, second):
                result = await client.get(path)
                assert result.status_code == 200 and result.json()["manifest"]["title"] == "synthetic public copy"
                assert result.headers["cache-control"] == "no-store"
                assert (await client.get(asset)).content == content
                assert (await client.get(private)).status_code == 401
            assert (await first.get(private, headers={"x-synthetic-subject": "other"})).status_code == 403
            assert (await first.get(private, headers={"x-synthetic-subject": "owner"})).status_code == 200
            guest_release.revoke(world_id=world, subject="owner", release_id=release_id)
            for client in (first, second):
                assert (await client.get(path)).status_code == 404
                assert (await client.get(asset)).status_code == 404
    asyncio.run(run())
