from __future__ import annotations

import asyncio
from types import SimpleNamespace
from typing import Any
from urllib.parse import parse_qs, urlsplit

import httpx
from fastapi import FastAPI
import pytest

from apps.live_control_server.main import create_app
from apps.live_control_server.services.hosted_auth import (
    AUTH_MODE_ENV,
    AUTH_SESSION_PATH,
    CURRENT_USER_PATH,
    DMS_API_ORIGIN_ENV,
    DEPLOYMENT_ENVIRONMENT_ENV,
    HOSTED_MODE,
    LOCAL_MODE,
    LOGIN_PATH,
)


class _AsyncASGITestClient:
    def __init__(self, application: FastAPI) -> None:
        self.application = application

    def get(self, path: str, **kwargs: Any) -> httpx.Response:
        return asyncio.run(self._request(path, **kwargs))

    async def _request(self, path: str, **kwargs: Any) -> httpx.Response:
        async with httpx.AsyncClient(
            transport=httpx.ASGITransport(
                app=self.application,
                client=("127.0.0.1", 50000),
            ),
            base_url="http://testserver",
            follow_redirects=False,
        ) as client:
            return await client.get(path, **kwargs)


def _hosted_app(monkeypatch: pytest.MonkeyPatch) -> _AsyncASGITestClient:
    monkeypatch.setenv(DEPLOYMENT_ENVIRONMENT_ENV, "production")
    monkeypatch.setenv(AUTH_MODE_ENV, HOSTED_MODE)
    monkeypatch.setenv(DMS_API_ORIGIN_ENV, "https://dms.example.test")
    return _AsyncASGITestClient(create_app())


def test_login_uses_only_configured_dms_origin_and_preserves_buddy_route(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    client = _hosted_app(monkeypatch)
    return_to = "/play/run-7?panel=history#turn-3"

    response = client.get(
        LOGIN_PATH,
        params={"return_to": return_to},
        headers={
            "Host": "attacker.example.test",
            "Origin": "https://attacker.example.test",
            "X-Forwarded-Host": "redirect.attacker.example.test",
        },
    )

    parsed = urlsplit(response.headers["location"])
    assert response.status_code == 302
    assert f"{parsed.scheme}://{parsed.netloc}" == "https://dms.example.test"
    assert parsed.path == "/api/auth/login"
    assert parse_qs(parsed.query) == {
        "frontend": ["buddy"],
        "redirect": [return_to],
    }


@pytest.mark.parametrize(
    "return_to",
    [
        "https://attacker.example.test",
        "//attacker.example.test/path",
        "/%252f%252fattacker.example.test",
        "/%255c%255cattacker.example.test",
        "/%25%32%66%25%32%66attacker.example.test",
        "/%252%66attacker.example.test",
        "/%250%64x",
        "/path\r\nLocation: https://attacker.example.test",
        "/" + "a" * 4096,
    ],
)
def test_login_reduces_unsafe_return_targets_to_root(
    monkeypatch: pytest.MonkeyPatch,
    return_to: str,
) -> None:
    response = _hosted_app(monkeypatch).get(
        LOGIN_PATH,
        params={"return_to": return_to},
    )

    assert parse_qs(urlsplit(response.headers["location"]).query) == {
        "frontend": ["buddy"],
        "redirect": ["/"],
    }


def test_login_does_not_follow_a_bad_configured_dms_origin(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    client = _hosted_app(monkeypatch)
    monkeypatch.setenv(DMS_API_ORIGIN_ENV, "https://dms.example.test/path")

    response = client.get(LOGIN_PATH, params={"return_to": "/play"})

    assert response.status_code == 503
    assert response.json() == {"detail": {"code": "hosted_auth_unavailable"}}
    assert "location" not in response.headers


@pytest.mark.parametrize(
    ("resolution", "status_code", "payload"),
    [
        (SimpleNamespace(status="authenticated", principal=SimpleNamespace(subject="synthetic-user")), 200, {"status": "authenticated"}),
        (SimpleNamespace(status="signed_out", principal=None), 401, {"status": "signed_out"}),
        (SimpleNamespace(status="unavailable", principal=None), 503, {"status": "unavailable"}),
    ],
)
def test_session_status_distinguishes_login_from_service_failure(
    monkeypatch: pytest.MonkeyPatch,
    resolution: object,
    status_code: int,
    payload: dict[str, str],
) -> None:
    client = _hosted_app(monkeypatch)
    application = client.application
    application.state.dms_principal_resolver = SimpleNamespace(
        resolve=_resolved(resolution)
    )

    response = client.get(AUTH_SESSION_PATH)

    assert response.status_code == status_code
    assert response.json() == payload


def test_protected_api_keeps_service_outage_distinct_from_expired_session(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    client = _hosted_app(monkeypatch)
    application = client.application
    application.state.dms_principal_resolver = SimpleNamespace(
        resolve=_resolved(SimpleNamespace(status="unavailable", principal=None))
    )

    response = client.get(CURRENT_USER_PATH)

    assert response.status_code == 503
    assert response.json() == {
        "detail": {"code": "authentication_service_unavailable"}
    }


async def _resolve(_request: httpx.Request, resolution: object) -> object:
    return resolution


def _resolved(resolution: object):
    async def resolve(request):
        return await _resolve(request, resolution)

    return resolve


def test_local_operator_session_status_keeps_local_app_usable(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv(DEPLOYMENT_ENVIRONMENT_ENV, "local")
    monkeypatch.setenv(AUTH_MODE_ENV, LOCAL_MODE)
    response = _AsyncASGITestClient(create_app()).get(AUTH_SESSION_PATH)

    assert response.status_code == 200
    assert response.json() == {"status": "local_operator"}
