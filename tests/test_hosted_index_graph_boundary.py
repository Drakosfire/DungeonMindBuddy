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
