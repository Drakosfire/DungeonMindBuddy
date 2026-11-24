from __future__ import annotations

import pytest
import asyncio
from datetime import UTC, datetime, timedelta

from fastapi import HTTPException, Request

from application_state.index_graph.sessions import (
    HOSTED_COOKIE,
    csrf_token,
    graph_cookie_name,
    require_index_graph_boundary,
)


def request(method: str, headers: list[tuple[bytes, bytes]]) -> Request:
    return Request({"type": "http", "method": method, "path": "/api/live/index-graph/graph",
                    "headers": headers, "scheme": "https", "server": ("buddy.example", 443),
                    "client": ("127.0.0.1", 1), "query_string": b""})


@pytest.fixture
def hosted(monkeypatch):
    monkeypatch.setenv("DMB_DEPLOYMENT_ENVIRONMENT", "production")
    monkeypatch.setenv("DMB_AUTH_MODE", "hosted_dms")
    monkeypatch.setenv("DMB_HOSTED_GUEST_GRAPH_ENABLED", "1")
    monkeypatch.setenv("AUTH_TRUSTED_FRONTEND_ORIGINS", "https://buddy.example")


def test_hosted_boundary_requires_same_origin_for_reads_and_writes(hosted):
    same = [(b"sec-fetch-site", b"same-origin")]
    require_index_graph_boundary(request("GET", same), unsafe=False)
    require_index_graph_boundary(request("POST", same + [(b"origin", b"https://buddy.example")]), unsafe=True)
    for headers in ([], [(b"sec-fetch-site", b"cross-site")],
                    same + [(b"origin", b"https://evil.example")]):
        with pytest.raises(HTTPException):
            require_index_graph_boundary(request("POST", headers), unsafe=True)
    with pytest.raises(HTTPException):
        require_index_graph_boundary(request("GET", same + [(b"origin", b"https://evil.example")]), unsafe=False)


def test_hosted_cookie_and_csrf_are_session_bound(hosted):
    assert graph_cookie_name() == HOSTED_COOKIE
    assert csrf_token("credential", "one") != csrf_token("credential", "two")
    assert csrf_token("credential", "one") != csrf_token("other", "one")


def test_hosted_boundary_is_default_off(hosted, monkeypatch):
    monkeypatch.delenv("DMB_HOSTED_GUEST_GRAPH_ENABLED")
    with pytest.raises(HTTPException) as rejected:
        require_index_graph_boundary(request("GET", [(b"sec-fetch-site", b"same-origin")]), unsafe=False)
    assert rejected.value.status_code == 404


def test_reset_requires_csrf_and_rotates_secure_cookie(hosted, monkeypatch):
    from application_state.index_graph import sessions
    from apps.live_control_server.routes import index_graph

    expires = datetime.now(UTC) + timedelta(days=30)
    old = sessions.IndexGraphSession("old-session", "buddy-index-graph:old", expires)
    new = sessions.IndexGraphSession("new-session", "buddy-index-graph:new", expires)
    monkeypatch.setattr(sessions, "lookup_session", lambda credential: old)
    calls = []
    monkeypatch.setattr(index_graph, "create_session", lambda **kwargs: (calls.append(kwargs) or ("new-credential", new)))
    async def inline_threadpool(function, *args):
        return function(*args)
    monkeypatch.setattr(index_graph, "run_in_threadpool", inline_threadpool)
    async def receive():
        return {"type": "http.request", "body": b"", "more_body": False}

    def reset_request(csrf=None):
        headers = [(b"sec-fetch-site", b"same-origin"), (b"origin", b"https://buddy.example"),
                   (b"cookie", f"{HOSTED_COOKIE}=old-credential".encode())]
        if csrf:
            headers.append((b"x-dmb-index-graph-csrf", csrf.encode()))
        req = request("POST", headers)
        return Request(req.scope, receive=receive)

    rejected = asyncio.run(index_graph.reset_graph(reset_request()))
    assert rejected.status_code == 403 and not calls
    response = asyncio.run(index_graph.reset_graph(reset_request(csrf_token("old-credential", "old-session"))))
    assert response.status_code == 200
    assert calls == [{"replace_credential": "old-credential"}]
    import json
    assert json.loads(response.body)["csrf_token"] == csrf_token("new-credential", "new-session")
    assert "Secure" in response.headers["set-cookie"] and "HttpOnly" in response.headers["set-cookie"]


def test_guest_world_cookie_migration_resumes_existing_graph(hosted, monkeypatch):
    from application_state.index_graph import sessions
    from apps.live_control_server.routes import index_graph

    monkeypatch.setenv("DMB_HOSTED_GUEST_BUILD_ENABLED", "1")
    from types import SimpleNamespace
    from apps.live_control_server.services import index_graph as graph_service
    monkeypatch.setattr(graph_service, "ensure_guest_managed_world", lambda _session: SimpleNamespace(record=SimpleNamespace(world_id="guest-world")))
    old = sessions.IndexGraphSession("old-session", "buddy-index-graph:old", datetime.now(UTC) + timedelta(days=30))
    monkeypatch.setattr(index_graph, "lookup_session", lambda credential: old)
    def no_create(**_kwargs):
        raise AssertionError("migration must not create another graph")
    monkeypatch.setattr(index_graph, "create_session", no_create)
    req = request("POST", [(b"cookie", f"{HOSTED_COOKIE}=old-credential".encode())])
    response = index_graph._start_or_resume_session(req)
    assert response.status_code == 200
    cookies = response.headers.getlist("set-cookie")
    assert any(cookie.startswith(f"{sessions.HOSTED_WORLD_COOKIE}=old-credential;") and "Path=/api/live;" in cookie and "HttpOnly" in cookie and "Secure" in cookie for cookie in cookies)
    assert any(cookie.startswith(f"{HOSTED_COOKIE}=old-credential;") and "Path=/api/live/index-graph;" in cookie and "Max-Age=0" not in cookie for cookie in cookies)


def test_guest_world_cookie_migration_rejects_conflicting_credentials(hosted, monkeypatch):
    from application_state.index_graph import sessions
    from apps.live_control_server.routes import index_graph

    monkeypatch.setenv("DMB_HOSTED_GUEST_BUILD_ENABLED", "1")
    headers = [(b"cookie", f"{HOSTED_COOKIE}=old; {sessions.HOSTED_WORLD_COOKIE}=other".encode())]
    response = index_graph._start_or_resume_session(request("POST", headers))
    assert response.status_code == 401


def test_guest_world_endpoint_requires_its_session_and_is_default_off(hosted, monkeypatch):
    import json
    from types import SimpleNamespace
    from application_state.index_graph import sessions
    from apps.live_control_server.routes import index_graph
    from apps.live_control_server.services import index_graph as graph_service

    req = request("POST", [(b"sec-fetch-site", b"same-origin"), (b"origin", b"https://buddy.example")])
    assert index_graph._get_guest_world(req).status_code == 404
    monkeypatch.setenv("DMB_HOSTED_GUEST_BUILD_ENABLED", "1")
    assert index_graph._get_guest_world(req).status_code == 401
    session = sessions.IndexGraphSession("session", "buddy-index-graph:one", datetime.now(UTC) + timedelta(days=30))
    monkeypatch.setattr(sessions, "lookup_session", lambda credential: session)
    monkeypatch.setattr(graph_service, "ensure_guest_managed_world", lambda actual: SimpleNamespace(record=SimpleNamespace(world_id="guest-one", name="Sizzek World")) if actual == session else None)
    req = request("POST", [(b"sec-fetch-site", b"same-origin"),
                           (b"origin", b"https://buddy.example"),
                           (b"x-dmb-index-graph-csrf", csrf_token("credential", "session").encode()),
                           (b"cookie", f"{sessions.HOSTED_WORLD_COOKIE}=credential".encode())])
    response = index_graph._get_guest_world(req)
    assert response.status_code == 200
    assert json.loads(response.body) == {"world_id": "guest-one", "name": "Sizzek World"}
    assert response.headers["cache-control"] == "no-store"


def test_guest_world_endpoint_rejects_write_without_csrf(hosted, monkeypatch):
    from application_state.index_graph import sessions
    from apps.live_control_server.routes import index_graph

    monkeypatch.setenv("DMB_HOSTED_GUEST_BUILD_ENABLED", "1")
    session = sessions.IndexGraphSession("session", "buddy-index-graph:one", datetime.now(UTC) + timedelta(days=30))
    monkeypatch.setattr(sessions, "lookup_session", lambda credential: session)
    req = request("POST", [(b"sec-fetch-site", b"same-origin"),
                           (b"origin", b"https://buddy.example"),
                           (b"cookie", f"{sessions.HOSTED_WORLD_COOKIE}=credential".encode())])
    assert index_graph._get_guest_world(req).status_code == 403


def test_guest_world_refuses_disclosure_if_session_expires_during_provisioning(hosted, monkeypatch):
    from types import SimpleNamespace
    from application_state.index_graph import sessions
    from apps.live_control_server.routes import index_graph
    from apps.live_control_server.services import index_graph as graph_service

    monkeypatch.setenv("DMB_HOSTED_GUEST_BUILD_ENABLED", "1")
    session = sessions.IndexGraphSession("session", "buddy-index-graph:one", datetime.now(UTC) + timedelta(days=30))
    calls = []
    def lookup(_credential):
        calls.append(1)
        if len(calls) > 1:
            raise sessions.IndexGraphSessionError("session_expired", "Session expired")
        return session
    monkeypatch.setattr(sessions, "lookup_session", lookup)
    monkeypatch.setattr(graph_service, "ensure_guest_managed_world", lambda _session: SimpleNamespace(record=SimpleNamespace(world_id="guest-one", name="Sizzek World")))
    req = request("POST", [(b"sec-fetch-site", b"same-origin"), (b"origin", b"https://buddy.example"),
                           (b"x-dmb-index-graph-csrf", csrf_token("credential", "session").encode()),
                           (b"cookie", f"{sessions.HOSTED_WORLD_COOKIE}=credential".encode())])
    assert index_graph._get_guest_world(req).status_code == 401
