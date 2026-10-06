from __future__ import annotations

import json
import time
from pathlib import Path

import pytest
from fastapi import HTTPException
from fastapi.testclient import TestClient
from starlette.requests import Request

from apps.live_control_server.main import create_app
from apps.live_control_server.services.agent_graph_auth import authenticate_native_graph_principal
from src import bootstrap_env


ORIGIN = "http://127.0.0.1:5202"
HOST = "127.0.0.1:8000"
SECRET = "synthetic-local-operator-capability-32-characters"
HEADERS = {"Origin": ORIGIN, "Host": HOST, "Sec-Fetch-Site": "same-origin"}
URL = "/api/live/agent/local-session"


@pytest.fixture(autouse=True)
def local_config(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> Path:
    store = tmp_path / "private" / "sessions.json"
    monkeypatch.setenv("DMB_AGENT_GRAPH_AUTH_MODE", "local_operator")
    monkeypatch.setenv("DMB_AGENT_GRAPH_AUTH_ENVIRONMENT", "development")
    monkeypatch.setenv("DMB_AGENT_GRAPH_LOCAL_OPERATOR_TOKEN", SECRET)
    monkeypatch.setenv("DMB_AGENT_GRAPH_LOCAL_UI_ORIGIN", ORIGIN)
    monkeypatch.setenv("DMB_AGENT_GRAPH_LOCAL_API_HOST", HOST)
    monkeypatch.setenv("DMB_AGENT_GRAPH_SESSION_STORE", str(store))
    return store


def _client() -> TestClient:
    return TestClient(create_app(), client=("127.0.0.1", 50000))


def _guard_request(cookie: str, method: str, *, csrf: str = "", origin: str = ORIGIN,
                   peer: str = "127.0.0.1") -> Request:
    headers = {"Host": HOST, "Cookie": f"dmb_local_graph_session={cookie}"}
    if method != "GET":
        headers["Origin"] = origin
        if csrf:
            headers["X-DMB-Graph-CSRF"] = csrf
    return Request({
        "type": "http", "method": method, "scheme": "http",
        "path": "/api/live/agent/turn", "raw_path": b"/api/live/agent/turn",
        "query_string": b"", "client": (peer, 50000), "server": ("127.0.0.1", 8000),
        "headers": [(key.lower().encode(), value.encode()) for key, value in headers.items()],
    })


def test_bootstrap_reload_status_and_revoke_are_durable(local_config: Path) -> None:
    client = _client()
    boot = client.post(URL, headers=HEADERS)
    assert boot.status_code == 200, boot.text
    assert boot.json()["status"] == "active"
    cookie = client.cookies.get("dmb_local_graph_session")
    assert cookie and len(cookie) >= 32
    assert "httponly" in boot.headers["set-cookie"].lower()
    assert "samesite=strict" in boot.headers["set-cookie"].lower()
    assert "path=/api/live" in boot.headers["set-cookie"].lower()
    assert "domain=" not in boot.headers["set-cookie"].lower()
    assert boot.headers["cache-control"] == "no-store"
    assert local_config.parent.stat().st_mode & 0o077 == 0
    assert local_config.stat().st_mode & 0o077 == 0
    stored = local_config.read_text(encoding="utf-8")
    assert cookie not in stored and SECRET not in stored

    reloaded = _client()
    reloaded.cookies.set("dmb_local_graph_session", cookie, path="/api/live")
    status = reloaded.get(URL, headers={"Host": HOST})
    assert status.status_code == 200, status.text
    csrf = status.json()["csrf_token"]
    assert csrf == boot.json()["csrf_token"]
    assert authenticate_native_graph_principal(_guard_request(cookie, "GET")).auth_method == "local_session"
    assert authenticate_native_graph_principal(_guard_request(cookie, "POST", csrf=csrf)).role == "gm"
    protected_body = {
        "schema": "dmb_world_graph_projection_request_v1", "worldId": "eldyrwyld",
        "campaignId": "longmont-c2", "scopeMode": "world", "admissibility": "gm",
    }
    protected_route = reloaded.post(
        "/api/live/world-graph/projection", json=protected_body, headers=HEADERS,
    )
    assert protected_route.status_code == 403, protected_route.text
    assert protected_route.json()["detail"]["code"] == "graph_auth_csrf_rejected"
    with pytest.raises(HTTPException) as no_csrf:
        authenticate_native_graph_principal(_guard_request(cookie, "POST"))
    assert no_csrf.value.status_code == 403
    with pytest.raises(HTTPException) as evil_origin:
        authenticate_native_graph_principal(_guard_request(cookie, "POST", csrf=csrf, origin="https://evil.invalid"))
    assert evil_origin.value.status_code == 403
    with pytest.raises(HTTPException) as remote_peer:
        authenticate_native_graph_principal(_guard_request(cookie, "GET", peer="192.0.2.1"))
    assert remote_peer.value.status_code == 403
    assert reloaded.delete(URL, headers=HEADERS).status_code == 403
    assert reloaded.delete(URL, headers={**HEADERS, "X-DMB-Graph-CSRF": "wrong"}).status_code == 403
    revoked = reloaded.delete(URL, headers={**HEADERS, "X-DMB-Graph-CSRF": csrf})
    assert revoked.status_code == 200, revoked.text
    assert reloaded.get(URL, headers={"Host": HOST}).status_code == 401


def test_private_profile_configures_real_local_session_boundary(
    local_config: Path, tmp_path: Path, monkeypatch: pytest.MonkeyPatch,
) -> None:
    private_dir = tmp_path / "profile"
    private_dir.mkdir(mode=0o700)
    profile = private_dir / "local-operator.env"
    profile.write_text(
        "DMB_AGENT_GRAPH_AUTH_MODE=local_operator\n"
        "DMB_AGENT_GRAPH_AUTH_ENVIRONMENT=development\n"
        f"DMB_AGENT_GRAPH_LOCAL_OPERATOR_TOKEN={SECRET}\n"
        f"DMB_AGENT_GRAPH_LOCAL_UI_ORIGIN={ORIGIN}\n"
        f"DMB_AGENT_GRAPH_LOCAL_API_HOST={HOST}\n"
        f"DMB_AGENT_GRAPH_SESSION_STORE={local_config}\n",
        encoding="utf-8",
    )
    profile.chmod(0o600)
    monkeypatch.setenv(bootstrap_env.LOCAL_GRAPH_PROFILE_ENV, str(profile))
    monkeypatch.setenv("DMB_AGENT_GRAPH_AUTH_MODE", "disabled")
    monkeypatch.setenv("DMB_AGENT_GRAPH_LOCAL_UI_ORIGIN", "https://wrong.invalid")
    monkeypatch.setattr(bootstrap_env, "_REPO_ROOT", tmp_path / "empty-checkout")

    bootstrap_env.load_dungeonmindbuddy_dotenv(override=False)

    assert _client().post(URL, headers=HEADERS).status_code == 200
    assert _client().post(URL, headers={**HEADERS, "Host": "wrong.invalid"}).status_code == 403


def test_cross_origin_host_and_forwarded_claims_cannot_bootstrap() -> None:
    client = _client()
    for headers in (
        {"Host": HOST},
        {**HEADERS, "Origin": "https://evil.invalid"},
        {**HEADERS, "Host": "evil.invalid", "X-Forwarded-Host": HOST},
        {**HEADERS, "Sec-Fetch-Site": "cross-site"},
    ):
        response = client.post(URL, headers=headers)
        assert response.status_code == 403, response.text
        assert "set-cookie" not in response.headers


def test_expiry_rotation_and_production_configuration_fail_closed(
    local_config: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    client = _client()
    assert client.post(URL, headers=HEADERS).status_code == 200
    entries = json.loads(local_config.read_text(encoding="utf-8"))
    local_config.write_text(json.dumps({key: int(time.time()) - 1 for key in entries}), encoding="utf-8")
    assert client.get(URL, headers={"Host": HOST}).status_code == 401

    assert client.post(URL, headers=HEADERS).status_code == 200
    monkeypatch.setenv("DMB_AGENT_GRAPH_LOCAL_OPERATOR_TOKEN", SECRET + "-rotated")
    assert client.get(URL, headers={"Host": HOST}).status_code == 401
    monkeypatch.setenv("DMB_AGENT_GRAPH_AUTH_ENVIRONMENT", "production")
    assert client.post(URL, headers=HEADERS).status_code == 503
