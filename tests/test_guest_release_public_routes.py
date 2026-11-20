"""Signed-out delivery is limited to exact release-owned read routes."""
import asyncio
from uuid import uuid4

import httpx
from fastapi import FastAPI

from application_state.errors import ApplicationStateNotFoundError
from apps.live_control_server.routes import guest_release_public
from apps.live_control_server.services import hosted_auth


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
