"""Mounted HTTP boundary for owner-created hosted Worlds."""

import psycopg
import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from apps.live_control_server.routes.world_containers import router
from apps.live_control_server.services.dms_principal import DmsPrincipal
from apps.live_control_server.services.hosted_auth import install_hosted_request_boundary
from apps.live_control_server.services.hosted_native_graph_access import (
    WORLD_COLLECTION_PATH, hosted_owner_collection, hosted_owner_creation,
)

ORIGIN = "https://buddy.dungeonmind.net"


@pytest.fixture
def hosted_client(application_state_dsn, monkeypatch):
    monkeypatch.setenv("DMB_DEPLOYMENT_ENVIRONMENT", "production")
    monkeypatch.setenv("DMB_AUTH_MODE", "hosted_dms")
    monkeypatch.setenv("DMB_HOSTED_OWNER_CREATION_CAPABILITY", "1")
    monkeypatch.setenv("DMB_HOSTED_WORLD_ACCESS_JSON", '{"existing":["alice"]}')
    monkeypatch.setenv("AUTH_TRUSTED_FRONTEND_ORIGINS", ORIGIN)
    with psycopg.connect(application_state_dsn) as conn:
        conn.execute("""UPDATE workspace.hosted_world_creation_policy
            SET enabled=true, owner_world_limit=3, global_world_limit=12,
                owner_rate_limit=20, global_rate_limit=40, rate_window_seconds=60""")
    app = FastAPI()
    async def principal(request):
        subject = request.headers.get("x-test-subject")
        return DmsPrincipal(subject=subject) if subject else None
    app.state.dms_principal_resolver = principal
    app.include_router(router)
    install_hosted_request_boundary(app, collection_authorizers={
        ("GET", WORLD_COLLECTION_PATH): hosted_owner_collection,
        ("POST", WORLD_COLLECTION_PATH): hosted_owner_creation,
    })
    with TestClient(app) as client:
        yield client


def test_hosted_create_binds_verified_owner_and_retries(hosted_client):
    headers = {"Origin": ORIGIN, "x-test-subject": "alice"}
    body = {"name": "Carnival", "request_key": "request_key_0001"}
    first = hosted_client.post(WORLD_COLLECTION_PATH, json=body, headers=headers)
    assert first.status_code == 200, first.text
    assert first.headers["cache-control"] == "no-store"
    assert first.json()["native_graph_binding"]["status"] == "provisioning"
    assert "owner_subject" not in first.json()
    assert hosted_client.post(WORLD_COLLECTION_PATH, json=body, headers=headers).json() == first.json()
    listed = hosted_client.get(WORLD_COLLECTION_PATH, headers=headers)
    assert listed.status_code == 200
    assert [item["world_id"] for item in listed.json()["records"]] == [first.json()["world_id"]]
    other = hosted_client.get(WORLD_COLLECTION_PATH, headers={"x-test-subject": "bob"})
    assert other.json()["records"] == []


@pytest.mark.parametrize("headers,body,status", [
    ({"Origin": ORIGIN}, {"name": "Carnival", "request_key": "request_key_0001"}, 401),
    ({"Origin": "https://foreign.example", "x-test-subject": "alice"}, {"name": "Carnival", "request_key": "request_key_0001"}, 403),
    ({"Origin": ORIGIN, "x-test-subject": "alice"}, {"name": "Carnival", "request_key": "request_key_0001", "owner_subject": "bob"}, 422),
])
def test_hosted_create_rejects_untrusted_requests_before_world_write(hosted_client, application_state_dsn, headers, body, status):
    assert hosted_client.post(WORLD_COLLECTION_PATH, json=body, headers=headers).status_code == status
    with psycopg.connect(application_state_dsn) as conn:
        assert conn.execute("SELECT count(*) FROM workspace.managed_world").fetchone()[0] == 0


def test_hosted_creation_capability_is_off_by_default(hosted_client, application_state_dsn, monkeypatch):
    monkeypatch.delenv("DMB_HOSTED_OWNER_CREATION_CAPABILITY", raising=False)
    response = hosted_client.post(WORLD_COLLECTION_PATH, json={"name": "Carnival", "request_key": "request_key_0001"},
                                  headers={"Origin": ORIGIN, "x-test-subject": "alice"})
    assert response.status_code == 403
    with psycopg.connect(application_state_dsn) as conn:
        assert conn.execute("SELECT count(*) FROM workspace.managed_world").fetchone()[0] == 0


@pytest.mark.parametrize("content", [
    b'{"name":"Carnival","name":"Other","request_key":"request_key_0001"}',
    b'{"name":"' + b'x' * 4096 + b'","request_key":"request_key_0001"}',
], ids=["duplicate-json-key", "oversized-body"])
def test_ambiguous_or_oversized_create_is_rejected_before_write(hosted_client, application_state_dsn, content):
    response = hosted_client.post(WORLD_COLLECTION_PATH, content=content,
                                  headers={"Origin": ORIGIN, "x-test-subject": "alice", "Content-Type": "application/json"})
    assert response.status_code == 403
    with psycopg.connect(application_state_dsn) as conn:
        assert conn.execute("SELECT count(*) FROM workspace.managed_world").fetchone()[0] == 0
        assert conn.execute("SELECT count(*) FROM workspace.hosted_world_creation_attempt").fetchone()[0] == 0
