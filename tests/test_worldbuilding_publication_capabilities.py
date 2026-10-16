"""Configuration discovery does not prepare, authorize, or publish a plan."""

from __future__ import annotations

import asyncio

import httpx
import pytest
from fastapi import FastAPI

from apps.live_control_server import config
from apps.live_control_server.models.extract_promote import WorldbuildingWritePlanResponse
from apps.live_control_server.routes import extract_promote as routes
from apps.live_control_server.services import agent_graph_auth as auth

URL = "/api/live/extract-promote/worldbuilding/capabilities"
TOKEN = "synthetic-operator-token-" + "x" * 32
SECRET_DSN = "postgresql://synthetic:do-not-disclose@invalid/native"


@pytest.fixture(autouse=True)
def isolated_configuration(monkeypatch):
    monkeypatch.setenv(auth.AUTH_MODE_ENV, "local_operator")
    monkeypatch.setenv(auth.AUTH_ENVIRONMENT_ENV, "local")
    monkeypatch.setenv(auth.LOCAL_OPERATOR_TOKEN_ENV, TOKEN)
    monkeypatch.delenv(config.WORLD_GRAPH_AUTHORITY_ENV, raising=False)
    monkeypatch.delenv(config.WORLD_GRAPH_AUTHORITY_DATABASE_URL_ENV, raising=False)

    def forbidden(*_args, **_kwargs):
        pytest.fail("Capability discovery attempted publication or authority access")

    monkeypatch.setattr(routes, "prepare_worldbuilding", forbidden)
    monkeypatch.setattr(routes, "confirm_worldbuilding", forbidden)
    from apps.live_control_server.ports import world_graph_authority_access
    monkeypatch.setattr(world_graph_authority_access, "get_world_graph_authority", forbidden)
    import psycopg
    monkeypatch.setattr(psycopg, "connect", forbidden)
    # Discovery must not perform even an unrelated HTTP/provider request.
    import urllib.request
    monkeypatch.setattr(urllib.request, "urlopen", forbidden)


def call(*, token=TOKEN, query="", peer="127.0.0.1"):
    app = FastAPI()
    app.include_router(routes.router)

    async def request():
        async with httpx.AsyncClient(
            transport=httpx.ASGITransport(app=app, client=(peer, 1234)),
            base_url="http://test",
        ) as client:
            return await client.get(
                URL + query,
                headers={"Authorization": f"Bearer {token}"} if token else {},
            )

    return asyncio.run(request())


def test_configured_does_not_connect_and_contains_no_secret(monkeypatch):
    monkeypatch.setenv(config.WORLD_GRAPH_AUTHORITY_DATABASE_URL_ENV, SECRET_DSN)
    response = call()
    assert response.status_code == 200
    assert response.json() == {
        "schema": "dmb_worldbuilding_publication_capabilities_v1",
        "confirmationSupported": True,
        "configured": True,
        "unavailabilityReasons": [],
    }
    assert SECRET_DSN not in response.text
    assert TOKEN not in response.text


@pytest.mark.parametrize("value", [None, "", "   "])
def test_database_configuration_missing(monkeypatch, value):
    if value is not None:
        monkeypatch.setenv(config.WORLD_GRAPH_AUTHORITY_DATABASE_URL_ENV, value)
    response = call()
    assert response.status_code == 200
    assert response.json()["configured"] is False
    assert response.json()["confirmationSupported"] is True
    assert response.json()["unavailabilityReasons"] == ["native_database_unconfigured"]


@pytest.mark.parametrize("mode", ["buddy_files", "quiesced", "untrusted-secret-value"])
def test_invalid_authority_does_not_expose_configuration(monkeypatch, mode):
    monkeypatch.setenv(config.WORLD_GRAPH_AUTHORITY_ENV, mode)
    monkeypatch.setenv(config.WORLD_GRAPH_AUTHORITY_DATABASE_URL_ENV, SECRET_DSN)
    response = call()
    assert response.status_code == 200
    assert response.json()["configured"] is False
    assert response.json()["unavailabilityReasons"] == ["native_authority_configuration_invalid"]
    assert mode not in response.text
    assert SECRET_DSN not in response.text


def test_reports_both_missing_configuration_reasons(monkeypatch):
    monkeypatch.setenv(config.WORLD_GRAPH_AUTHORITY_ENV, "quiesced")
    assert call().json()["unavailabilityReasons"] == [
        "native_authority_configuration_invalid", "native_database_unconfigured",
    ]


@pytest.mark.parametrize("token", [None, "wrong-token"])
def test_requires_real_authentication(token):
    assert call(token=token).status_code == 401


def test_missing_auth_configuration_fails_closed(monkeypatch):
    monkeypatch.delenv(auth.LOCAL_OPERATOR_TOKEN_ENV)
    assert call().status_code == 503


def test_non_loopback_fails_closed():
    assert call(peer="192.0.2.1").status_code == 403


def test_player_cannot_discover_gm_capability():
    app = FastAPI()
    app.include_router(routes.router)
    app.dependency_overrides[auth.authenticate_native_graph_principal] = lambda: auth.NativeGraphPrincipal(
        subject="synthetic-player", role="player", auth_method="local_operator"
    )

    async def request():
        async with httpx.AsyncClient(transport=httpx.ASGITransport(app=app), base_url="http://test") as client:
            return await client.get(URL)

    assert asyncio.run(request()).status_code == 403


def test_selector_query_cannot_turn_discovery_into_plan_lookup():
    response = call(query="?worldId=other&runId=run")
    assert response.status_code == 422
    assert response.json()["code"] == "invalid_request"


def test_plan_schema_stays_separate_and_historical_metadata_is_unchanged():
    properties = WorldbuildingWritePlanResponse.model_json_schema(by_alias=True)["properties"]
    assert "confirmationSupported" not in properties
    assert "configured" not in properties
    assert "unavailabilityReasons" not in properties
    assert properties["confirmable"]["const"] is False
    assert properties["confirmableReason"]["const"] == (
        "BLD-10a prepares an inert write plan; graph confirmation is not implemented."
    )
