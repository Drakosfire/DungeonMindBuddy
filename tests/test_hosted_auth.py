from __future__ import annotations

import asyncio
from collections.abc import AsyncIterator
from typing import Any

import httpx
from fastapi import FastAPI, HTTPException, Request
from fastapi.responses import StreamingResponse
import pytest

from apps.live_control_server.services.dms_principal import DmsPrincipal
from apps.live_control_server.services.hosted_auth import (
    AUTH_MODE_ENV,
    CURRENT_USER_PATH,
    DEPLOYMENT_ENVIRONMENT_ENV,
    HOSTED_WORLD_ACCESS_ENV,
    LOGOUT_PATH,
    TRUSTED_FRONTEND_ORIGINS_ENV,
    authorize_world_access,
    install_hosted_request_boundary,
    require_local_unproxied_loopback,
    validate_hosted_auth_configuration,
)


FRONTEND_ORIGIN = "https://buddy.dungeonmind.net"


class _AsyncASGITestClient:
    """Run in-process ASGI requests without TestClient's worker-thread bridge."""

    def __init__(self, application: FastAPI) -> None:
        self.application = application

    def get(self, path: str, **kwargs: Any) -> httpx.Response:
        return asyncio.run(self._request("GET", path, **kwargs))

    def post(self, path: str, **kwargs: Any) -> httpx.Response:
        return asyncio.run(self._request("POST", path, **kwargs))

    async def _request(self, method: str, path: str, **kwargs: Any) -> httpx.Response:
        async with httpx.AsyncClient(
            transport=httpx.ASGITransport(app=self.application),
            base_url="http://testserver",
        ) as client:
            return await client.request(method, path, **kwargs)


def _app(
    *,
    principal: DmsPrincipal | None,
    verified_world_routes: frozenset[str] | None = None,
) -> tuple[_AsyncASGITestClient, list[str]]:
    app = FastAPI()
    app.state.dms_principal_resolver = _resolver(principal)
    observed: list[str] = []
    install_hosted_request_boundary(
        app,
        verified_world_routes=(
            frozenset(
                {
                    "/api/probe/read",
                    "/api/media/image",
                    "/api/history",
                    "/api/jobs",
                    "/api/provider",
                    "/api/stream",
                }
            )
            if verified_world_routes is None
            else verified_world_routes
        ),
    )

    @app.get(CURRENT_USER_PATH)
    async def current_user(request: Request) -> dict[str, str]:
        return {"sub": request.state.dms_principal.subject}

    @app.get("/api/probe/read")
    async def read_probe() -> dict[str, bool]:
        observed.append("read")
        return {"ok": True}

    @app.get("/api/media/image")
    async def media_probe() -> dict[str, bool]:
        observed.append("media")
        return {"ok": True}

    @app.post("/api/history")
    async def history_probe() -> dict[str, bool]:
        observed.append("history")
        return {"ok": True}

    @app.post("/api/jobs")
    async def jobs_probe() -> dict[str, bool]:
        observed.append("jobs")
        return {"ok": True}

    @app.post("/api/provider")
    async def provider_probe() -> dict[str, bool]:
        observed.append("provider")
        return {"ok": True}

    @app.get("/api/stream")
    async def stream_probe() -> StreamingResponse:
        observed.append("stream")

        async def events() -> AsyncIterator[str]:
            yield "data: ready\n\n"

        return StreamingResponse(events(), media_type="text/event-stream")

    @app.post(LOGOUT_PATH)
    async def logout_probe() -> dict[str, bool]:
        observed.append("logout")
        return {"ok": True}

    return _AsyncASGITestClient(app), observed


def _resolver(principal: DmsPrincipal | None):
    async def resolve(_request: Request) -> DmsPrincipal | None:
        return principal

    return resolve


@pytest.fixture(autouse=True)
def _hosted_environment(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv(DEPLOYMENT_ENVIRONMENT_ENV, "production")
    monkeypatch.setenv(AUTH_MODE_ENV, "hosted_dms")
    monkeypatch.setenv(
        HOSTED_WORLD_ACCESS_ENV,
        '{"world-alpha":["synthetic-managed-user"]}',
    )
    monkeypatch.setenv(TRUSTED_FRONTEND_ORIGINS_ENV, FRONTEND_ORIGIN)


def test_signed_out_request_is_rejected_before_route_execution() -> None:
    client, observed = _app(principal=None)

    response = client.get("/api/probe/read", params={"worldId": "world-alpha"})

    assert response.status_code == 401
    assert observed == []


def test_permitted_dms_subject_and_auth_status_are_available() -> None:
    client, observed = _app(principal=DmsPrincipal(subject="synthetic-managed-user"))

    status = client.get(CURRENT_USER_PATH)
    response = client.get("/api/probe/read", params={"worldId": "world-alpha"})

    assert status.status_code == 200
    assert status.json() == {"sub": "synthetic-managed-user"}
    assert response.status_code == 200
    assert observed == ["read"]


def test_world_route_is_denied_until_its_resource_binding_is_reviewed() -> None:
    client, observed = _app(
        principal=DmsPrincipal(subject="synthetic-managed-user"),
        verified_world_routes=frozenset(),
    )

    response = client.get("/api/probe/read", params={"worldId": "world-alpha"})

    assert response.status_code == 403
    assert response.json()["detail"]["code"] == "hosted_world_route_policy_unverified"
    assert observed == []


@pytest.mark.parametrize(
    "path",
    (
        "/api/probe/read/",
        "/api/%70robe/read",
        "/api%2Fprobe%2Fread",
    ),
)
def test_api_path_variants_do_not_reach_an_unverified_handler(path: str) -> None:
    client, observed = _app(
        principal=DmsPrincipal(subject="synthetic-managed-user"),
        verified_world_routes=frozenset(),
    )

    response = client.get(path, params={"world_id": "world-alpha"})

    assert response.status_code != 200
    assert observed == []


def test_cross_world_write_is_rejected_before_provider_or_job_side_effects() -> None:
    client, observed = _app(principal=DmsPrincipal(subject="synthetic-managed-user"))
    headers = {"Origin": FRONTEND_ORIGIN}
    for route in ("/api/provider", "/api/jobs", "/api/history"):
        response = client.post(route, json={"world_id": "world-other"}, headers=headers)
        assert response.status_code == 403
        assert response.json()["detail"]["code"] == "hosted_world_forbidden"
    for route in ("/api/probe/read", "/api/media/image"):
        response = client.get(route, params={"world_id": "world-other"})
        assert response.status_code == 403
    assert observed == []


def test_logout_requires_the_exact_dms_trusted_origin() -> None:
    client, observed = _app(principal=None)

    missing = client.post(LOGOUT_PATH)
    foreign = client.post(
        LOGOUT_PATH,
        headers={"Origin": "https://attacker.example"},
    )
    allowed = client.post(LOGOUT_PATH, headers={"Origin": FRONTEND_ORIGIN})

    assert missing.status_code == 403
    assert foreign.status_code == 403
    assert allowed.status_code == 200
    assert observed == ["logout"]


def test_hosted_logout_proxies_dms_cookie_and_returns_its_clear_cookie() -> None:
    from apps.live_control_server.main import create_app

    app = create_app()
    seen: list[httpx.Request] = []

    def dms_logout(request: httpx.Request) -> httpx.Response:
        seen.append(request)
        return httpx.Response(
            204,
            headers={
                "Set-Cookie": (
                    "dungeonmind_session=null; Domain=.dungeonmind.net; Path=/; "
                    "Secure; HttpOnly; SameSite=None"
                )
            },
        )

    dms_client = httpx.AsyncClient(transport=httpx.MockTransport(dms_logout))
    app.state.dms_http_client = dms_client
    client = _AsyncASGITestClient(app)

    try:
        rejected = client.post(LOGOUT_PATH)
        response = client.post(
            LOGOUT_PATH,
            headers={
                "Origin": FRONTEND_ORIGIN,
                "Cookie": "dungeonmind_session=synthetic-session-cookie",
            },
        )
    finally:
        asyncio.run(dms_client.aclose())

    assert rejected.status_code == 403
    assert response.status_code == 204
    assert len(seen) == 1
    assert seen[0].url == "https://api.dungeonmind.net/api/auth/logout"
    assert seen[0].headers["origin"] == FRONTEND_ORIGIN
    assert seen[0].headers["cookie"] == "dungeonmind_session=synthetic-session-cookie"
    assert response.headers.get_list("set-cookie") == [
        "dungeonmind_session=null; Domain=.dungeonmind.net; Path=/; Secure; "
        "HttpOnly; SameSite=None"
    ]


def test_readiness_stays_nonsensitive_and_not_ready_without_route_policies() -> None:
    from apps.live_control_server.main import create_app

    response = _AsyncASGITestClient(create_app()).get("/health/ready")

    assert response.status_code == 503
    assert response.json() == {
        "status": "not_ready",
        "code": "hosted_configuration_invalid",
    }
    assert "DATABASE_URL" not in response.text
    assert "synthetic-managed-user" not in response.text


def test_production_app_excludes_fixture_backed_graph_gold_review_routes(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    from apps.live_control_server.main import create_app

    monkeypatch.setenv(DEPLOYMENT_ENVIRONMENT_ENV, "production")

    application = create_app()

    assert not any(
        getattr(route, "path", "").startswith("/api/live/graph-preview")
        for route in application.routes
    )


def test_write_requires_one_exact_trusted_origin() -> None:
    client, observed = _app(principal=DmsPrincipal(subject="synthetic-managed-user"))
    body = {"world_id": "world-alpha"}

    missing = client.post("/api/provider", json=body)
    foreign = client.post(
        "/api/provider", json=body, headers={"Origin": "https://attacker.example"}
    )
    allowed = client.post(
        "/api/provider", json=body, headers={"Origin": FRONTEND_ORIGIN}
    )

    assert missing.status_code == 403
    assert foreign.status_code == 403
    assert allowed.status_code == 200
    assert observed == ["provider"]


def test_media_history_jobs_provider_and_streaming_require_an_authorized_world() -> None:
    client, observed = _app(principal=DmsPrincipal(subject="synthetic-managed-user"))

    for route in ("/api/media/image", "/api/stream"):
        assert client.get(route).status_code == 403
    for route in ("/api/history", "/api/jobs", "/api/provider"):
        response = client.post(route, json={"record_id": "opaque-only"}, headers={"Origin": FRONTEND_ORIGIN})
        assert response.status_code == 403

    assert observed == []


def test_authorized_media_history_jobs_provider_and_streaming_continue() -> None:
    client, observed = _app(principal=DmsPrincipal(subject="synthetic-managed-user"))

    assert client.get("/api/media/image", params={"worldId": "world-alpha"}).status_code == 200
    stream = client.get("/api/stream", params={"world_id": "world-alpha"})
    assert stream.status_code == 200
    assert stream.text == "data: ready\n\n"
    for route in ("/api/history", "/api/jobs", "/api/provider"):
        response = client.post(
            route,
            json={"scope": {"worldId": "world-alpha"}},
            headers={"Origin": FRONTEND_ORIGIN},
        )
        assert response.status_code == 200
    assert observed == ["media", "stream", "history", "jobs", "provider"]


def test_local_mode_rejects_loopback_requests_with_forwarded_metadata() -> None:
    from starlette.requests import Request as StarletteRequest

    request = StarletteRequest(
        {
            "type": "http",
            "http_version": "1.1",
            "method": "GET",
            "scheme": "http",
            "path": "/api/local",
            "raw_path": b"/api/local",
            "query_string": b"",
            "headers": [(b"x-forwarded-for", b"127.0.0.1")],
            "client": ("127.0.0.1", 50000),
            "server": ("127.0.0.1", 8000),
        }
    )

    with pytest.raises(HTTPException) as exc_info:
        require_local_unproxied_loopback(request)
    assert exc_info.value.status_code == 403


def test_production_configuration_is_explicit_and_separates_logical_databases(
    tmp_path: Any,
) -> None:
    roots = [tmp_path / name for name in ("worlds", "artifacts", "sessions", "graph")]
    for root in roots:
        root.mkdir()
    configuration = {
        DEPLOYMENT_ENVIRONMENT_ENV: "production",
        AUTH_MODE_ENV: "hosted_dms",
        "DUNGEONMIND_SERVER_API_ORIGIN": "https://api.dungeonmind.net",
        TRUSTED_FRONTEND_ORIGINS_ENV: FRONTEND_ORIGIN,
        HOSTED_WORLD_ACCESS_ENV: '{"world-alpha":["synthetic-managed-user"]}',
        "DUNGEONBUDDY_APPLICATION_STATE_DATABASE_URL": "postgresql://buddy:pw@db.example.test:5432/buddy_app",
        "DUNGEONMIND_WORLD_GRAPH_AUTHORITY_DATABASE_URL": "postgresql://mind:pw@db.example.test:5432/mind_worlds",
        "DMB_MANAGED_WORLD_DATA_ROOT": str(roots[0]),
        "DMB_ARTIFACT_DATA_ROOT": str(roots[1]),
        "DUNGEONMIND_LIVE_SESSION_DIR": str(roots[2]),
        "DUNGEONMIND_WORLD_GRAPH_ROOT": str(roots[3]),
        "DUNGEONMIND_RECAP_SOURCE_CONTENT_ROOT": "recaps",
    }

    assert validate_hosted_auth_configuration(configuration) == (
        "hosted_world_route_policy_unverified",
    )
    assert validate_hosted_auth_configuration(
        configuration,
        verified_world_routes=frozenset({"/api/probe/read"}),
    ) == ()
    same_database = {
        **configuration,
        "DUNGEONMIND_WORLD_GRAPH_AUTHORITY_DATABASE_URL": configuration[
            "DUNGEONBUDDY_APPLICATION_STATE_DATABASE_URL"
        ],
    }
    errors = validate_hosted_auth_configuration(same_database)
    assert "DUNGEONBUDDY_APPLICATION_STATE_DATABASE_URL" in errors
    assert "DUNGEONMIND_WORLD_GRAPH_AUTHORITY_DATABASE_URL" in errors
    same_owner = {
        **configuration,
        "DUNGEONMIND_WORLD_GRAPH_AUTHORITY_DATABASE_URL": (
            "postgresql://buddy:other@db.example.test:5432/mind_worlds"
        ),
    }
    errors = validate_hosted_auth_configuration(same_owner)
    assert "DUNGEONBUDDY_APPLICATION_STATE_DATABASE_URL" in errors
    assert "DUNGEONMIND_WORLD_GRAPH_AUTHORITY_DATABASE_URL" in errors


def test_world_assignment_is_per_dms_subject_and_does_not_claim_ownership() -> None:
    assignment = {"world-alpha": frozenset({"synthetic-managed-user"})}
    authorize_world_access("synthetic-managed-user", frozenset({"world-alpha"}), access=assignment)
    with pytest.raises(HTTPException) as forbidden:
        authorize_world_access("synthetic-managed-user", frozenset({"world-other"}), access=assignment)
    assert forbidden.value.status_code == 403
    with pytest.raises(HTTPException) as unassigned:
        authorize_world_access("other-managed-user", frozenset({"world-alpha"}), access=assignment)
    assert unassigned.value.status_code == 403
