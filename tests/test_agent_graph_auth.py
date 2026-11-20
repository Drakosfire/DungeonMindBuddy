from __future__ import annotations

from types import SimpleNamespace
from typing import Any

from fastapi import HTTPException
import pytest
from starlette.requests import Request


LOCAL_OPERATOR_TOKEN = "test-local-operator-token-with-adequate-length"


def _graph_route_requests() -> list[tuple[str, dict[str, Any]]]:
    retrieval_context = {
        "worldId": "eldyrwild",
        "campaignId": "longmont-c2",
        "scopeMode": "world",
    }
    return [
        (
            "/api/live/agent/turn",
            {
                "schema": "dmb_agent_turn_request_v1",
                "client_thread_id": "thread-auth-test",
                "turn_id": "turn-auth-test",
                "surface": {"surface_id": "index", "instance_id": "index-auth-test"},
                "owner_scope": {"kind": "world", "world_id": "world-auth-test"},
                "primary_work": None,
                "client_work_state": "none",
                "graph_request": {
                    "mode": "world",
                    "world_id": "world-auth-test",
                    "campaign_id": None,
                    "revision_pin": None,
                    "focus": {"kind": "none", "session_id": None, "campaign_id": None},
                },
                "graph_selection": None,
                "message": "Read the graph.",
            },
        ),
        (
            "/api/live/query",
            {
                "campaign_id": "longmont-c2",
                "session": 29,
                "mode": "live",
                "query_backend": "hermes",
                "text": "Read the graph.",
                "world_graph_context": {
                    "world_id": "eldyrwild",
                    "campaign_id": "longmont-c2",
                    "scope_mode": "world",
                },
            },
        ),
        (
            "/api/live/world-graph/projection",
            {
                "schema": "dmb_world_graph_projection_request_v1",
                "worldId": "eldyrwyld",
                "campaignId": "longmont-c2",
                "scopeMode": "world",
                "admissibility": "gm",
            },
        ),
        (
            "/api/live/world-graph/managed-projection",
            {
                "schema": "dmb_managed_world_graph_projection_request_v1",
                "managedWorldId": "the-glass-orchard",
            },
        ),
        (
            "/api/live/world-graph/recap-projection",
            {
                "schema": "dmb_world_graph_projection_request_v1",
                "worldId": "eldyrwyld",
                "campaignId": "longmont-c2",
                "scopeMode": "world",
                "admissibility": "gm",
            },
        ),
        (
            "/api/live/world-graph/retrieval/search",
            {
                "schema": "dmb_world_graph_search_request_v1",
                **retrieval_context,
                "queryText": "keeper",
            },
        ),
        (
            "/api/live/world-graph/retrieval/object",
            {
                "schema": "dmb_world_graph_object_request_v1",
                **retrieval_context,
                "nodeId": "npc:keeper",
            },
        ),
        (
            "/api/live/world-graph/retrieval/complete-object",
            {
                "schema": "dmb_world_graph_object_projection_request_v1",
                **retrieval_context,
                "nodeId": "npc:keeper",
                "originSurface": "plan",
            },
        ),
        (
            "/api/live/world-graph/retrieval/neighborhood",
            {
                "schema": "dmb_world_graph_neighborhood_request_v1",
                **retrieval_context,
                "seedNodeIds": ["npc:keeper"],
            },
        ),
        (
            "/api/live/world-graph/retrieval/evidence",
            {
                "schema": "dmb_world_graph_evidence_request_v1",
                **retrieval_context,
                "target": {"kind": "node", "id": "npc:keeper"},
            },
        ),
        (
            "/api/live/world-graph/retrieval/source-anchor/read",
            {
                "schema": "dmb_world_graph_source_anchor_read_request_v1",
                **retrieval_context,
                "anchorId": "source-anchor:v1:test",
            },
        ),
        (
            "/api/live/threats/query-hydration",
            {
                "schema": "dmb_threat_query_hydration_request_v1",
                "worldId": "eldyrwild",
                "campaignId": "longmont-c2",
                "revisionPin": "rev:current",
                "queryText": "keeper",
            },
        ),
        (
            "/api/live/threat-drafts/{draft_id}/publication-operations/{operation_id}/identity-candidates/prepare",
            {"query_text": "keeper"},
        ),
    ]


def _request(
    *,
    path: str,
    headers: dict[str, str] | None = None,
    host: str = "127.0.0.1",
    app: Any = None,
) -> Request:
    scope: dict[str, Any] = {
        "type": "http",
        "http_version": "1.1",
        "method": "POST",
        "scheme": "http",
        "path": path,
        "raw_path": path.encode("ascii"),
        "query_string": b"",
        "headers": [
            (key.lower().encode("ascii"), value.encode("utf-8"))
            for key, value in (headers or {}).items()
        ],
        "client": (host, 50000),
        "server": ("127.0.0.1", 8000),
    }
    if app is not None:
        scope["app"] = app
    return Request(scope)


def _clear_auth_environment(monkeypatch: pytest.MonkeyPatch) -> None:
    from apps.live_control_server.services.agent_graph_auth import (
        AUTH_ENVIRONMENT_ENV,
        AUTH_MODE_ENV,
        LOCAL_OPERATOR_TOKEN_ENV,
    )

    for key in (AUTH_ENVIRONMENT_ENV, AUTH_MODE_ENV, LOCAL_OPERATOR_TOKEN_ENV):
        monkeypatch.delenv(key, raising=False)


def test_every_public_native_graph_route_has_its_exact_authorization_dependency() -> None:
    from fastapi.routing import APIRoute

    from apps.live_control_server.main import create_app
    from apps.live_control_server.services.agent_graph_auth import (
        native_graph_gm_dependency,
    )

    app = create_app()
    route_map = {
        route.path: route
        for route in app.routes
        if isinstance(route, APIRoute) and "POST" in route.methods
    }
    from apps.live_control_server.services.hosted_native_graph_access import (
        native_graph_explorer_dependency,
    )

    protected_routes = {
        "/api/live/world-graph/projection": native_graph_gm_dependency,
        "/api/live/world-graph/managed-projection": native_graph_explorer_dependency,
        "/api/live/world-graph/recap-projection": native_graph_gm_dependency,
        "/api/live/world-graph/retrieval/search": native_graph_gm_dependency,
        "/api/live/world-graph/retrieval/object": native_graph_gm_dependency,
        "/api/live/world-graph/retrieval/complete-object": native_graph_gm_dependency,
        "/api/live/world-graph/retrieval/neighborhood": native_graph_gm_dependency,
        "/api/live/world-graph/retrieval/evidence": native_graph_gm_dependency,
        "/api/live/world-graph/retrieval/source-anchor/read": native_graph_gm_dependency,
    }
    for path, expected_dependency in protected_routes.items():
        route = route_map[path]
        assert any(
            dependency.call is expected_dependency
            for dependency in route.dependant.dependencies
        ), path

    # Conditional endpoints use the same guard inside their handlers so their
    # graphless paths remain available without a credential.
    assert route_map["/api/live/agent/turn"].endpoint.__name__ == "post_agent_turn"
    assert route_map["/api/live/query"].endpoint.__name__ == "post_live_query"
    assert (
        route_map["/api/live/threats/query-hydration"].endpoint.__name__
        == "post_threat_query_hydration"
    )
    assert (
        route_map[
            "/api/live/threat-drafts/{draft_id}/publication-operations/{operation_id}/identity-candidates/prepare"
        ].endpoint.__name__
        == "post_prepare_identity_candidates"
    )


def test_route_matrix_payloads_validate_before_the_auth_gate() -> None:
    from apps.live_control_server.models.agent_turn import AgentTurnRequest
    from apps.live_control_server.models.world_graph_object_projection import (
        WorldGraphObjectProjectionRequest,
    )
    from apps.live_control_server.routes.live import LiveQueryRequest
    from apps.live_control_server.models.threat_query_hydration import (
        ThreatQueryHydrationRequestV1,
    )
    from apps.live_control_server.models.threat_publication_identity import (
        PrepareThreatIdentityCandidatesRequestV1,
    )
    from apps.live_control_server.services.agent_world_graph_query_context import (
        AgentWorldGraphQueryContextRequest,
    )
    from apps.live_control_server.services.managed_world_graph_projection import (
        ManagedWorldGraphProjectionRequest,
    )
    from graph_memory.projection.world_projection import WorldGraphProjectionRequest
    from graph_memory.retrieval.models import (
        WorldGraphEvidenceRequest,
        WorldGraphNeighborhoodRequest,
        WorldGraphObjectRequest,
        WorldGraphSearchRequest,
        WorldGraphSourceAnchorReadRequest,
    )

    model_by_path = {
        "/api/live/agent/turn": AgentTurnRequest,
        "/api/live/query": LiveQueryRequest,
        "/api/live/world-graph/projection": WorldGraphProjectionRequest,
        "/api/live/world-graph/managed-projection": ManagedWorldGraphProjectionRequest,
        "/api/live/world-graph/recap-projection": WorldGraphProjectionRequest,
        "/api/live/world-graph/retrieval/search": WorldGraphSearchRequest,
        "/api/live/world-graph/retrieval/object": WorldGraphObjectRequest,
        "/api/live/world-graph/retrieval/complete-object": WorldGraphObjectProjectionRequest,
        "/api/live/world-graph/retrieval/neighborhood": WorldGraphNeighborhoodRequest,
        "/api/live/world-graph/retrieval/evidence": WorldGraphEvidenceRequest,
        "/api/live/world-graph/retrieval/source-anchor/read": WorldGraphSourceAnchorReadRequest,
        "/api/live/threats/query-hydration": ThreatQueryHydrationRequestV1,
        "/api/live/threat-drafts/{draft_id}/publication-operations/{operation_id}/identity-candidates/prepare": PrepareThreatIdentityCandidatesRequestV1,
    }
    for path, payload in _graph_route_requests():
        if path == "/api/live/query":
            payload = {
                **payload,
                "world_graph_context": AgentWorldGraphQueryContextRequest.model_validate(
                    payload["world_graph_context"]
                ),
            }
        model_by_path[path].model_validate(payload)


def test_agent_and_legacy_query_guards_precede_runtime_or_session_work(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    from apps.live_control_server.models.agent_turn import AgentTurnRequest
    from apps.live_control_server.main import create_app
    from apps.live_control_server.routes import agent as agent_route
    from apps.live_control_server.routes import live as live_route
    from apps.live_control_server.routes.live import LiveQueryRequest
    from apps.live_control_server.services.agent_graph_auth import (
        AUTH_ENVIRONMENT_ENV,
        AUTH_MODE_ENV,
        LOCAL_OPERATOR_TOKEN_ENV,
    )

    _clear_auth_environment(monkeypatch)
    calls: list[str] = []

    def forbidden(name: str):
        def fail(*_args: Any, **_kwargs: Any) -> Any:
            calls.append(name)
            raise AssertionError(f"{name} ran before native Graph authorization")

        return fail

    monkeypatch.setattr(agent_route, "execute_agent_turn", forbidden("agent_runtime"))
    monkeypatch.setattr(live_route, "session_dir", forbidden("session_resolution"))
    monkeypatch.setattr(live_route, "process_live_query", forbidden("model_dispatch"))
    app = create_app()
    agent_path, agent_payload = _graph_route_requests()[0]
    query_path, query_payload = _graph_route_requests()[1]

    for path, body, invoke in (
        (
            agent_path,
            AgentTurnRequest.model_validate(agent_payload),
            agent_route.post_agent_turn,
        ),
        (
            query_path,
            LiveQueryRequest.model_validate(query_payload),
            live_route.post_live_query,
        ),
    ):
        request = _request(path=path, app=app)
        with pytest.raises(HTTPException) as missing_config:
            invoke(body, request)
        assert missing_config.value.status_code == 503
        assert missing_config.value.detail["code"] == "graph_auth_unavailable"

        monkeypatch.setenv(AUTH_MODE_ENV, "local_operator")
        monkeypatch.setenv(AUTH_ENVIRONMENT_ENV, "development")
        monkeypatch.setenv(LOCAL_OPERATOR_TOKEN_ENV, LOCAL_OPERATOR_TOKEN)
        with pytest.raises(HTTPException) as missing_credential:
            invoke(body, request)
        assert missing_credential.value.status_code == 401
        assert missing_credential.value.detail["code"] == "graph_auth_required"
        monkeypatch.delenv(AUTH_MODE_ENV)
        monkeypatch.delenv(AUTH_ENVIRONMENT_ENV)
        monkeypatch.delenv(LOCAL_OPERATOR_TOKEN_ENV)

    assert calls == []


def test_credential_config_token_and_loopback_enforcement() -> None:
    from apps.live_control_server.services.agent_graph_auth import (
        AUTH_ENVIRONMENT_ENV,
        AUTH_MODE_ENV,
        LOCAL_OPERATOR_TOKEN_ENV,
        NativeGraphPrincipal,
        authenticate_native_graph_principal,
        native_graph_gm_dependency,
    )
    from apps.live_control_server.models.agent_turn import AgentTurnRequest
    from pydantic import ValidationError

    import os

    environment = {
        AUTH_MODE_ENV: "local_operator",
        AUTH_ENVIRONMENT_ENV: "local",
        LOCAL_OPERATOR_TOKEN_ENV: LOCAL_OPERATOR_TOKEN,
    }
    request = _request(path="/api/live/world-graph/projection")
    old = {key: os.environ.get(key) for key in environment}
    try:
        os.environ.update(environment)
        with pytest.raises(HTTPException) as missing:
            authenticate_native_graph_principal(request)
        assert missing.value.status_code == 401
        assert missing.value.detail["code"] == "graph_auth_required"

        os.environ[AUTH_ENVIRONMENT_ENV] = "production"
        with pytest.raises(HTTPException) as production:
            authenticate_native_graph_principal(request)
        assert production.value.status_code == 503
        assert production.value.detail["code"] == "graph_auth_unavailable"
        os.environ.update(environment)

        os.environ[LOCAL_OPERATOR_TOKEN_ENV] = "too-short"
        with pytest.raises(HTTPException) as weak_config:
            authenticate_native_graph_principal(request)
        assert weak_config.value.status_code == 503
        os.environ.update(environment)

        valid_request = _request(
            path="/api/live/world-graph/projection",
            headers={"Authorization": f"Bearer {LOCAL_OPERATOR_TOKEN}"},
        )
        principal = authenticate_native_graph_principal(valid_request)
        assert (principal.subject, principal.role, principal.auth_method) == (
            "local_operator",
            "gm",
            "local_operator",
        )
        assert native_graph_gm_dependency(principal) == principal

        forged_headers = _request(
            path="/api/live/world-graph/projection",
            headers={
                "X-Role": "gm",
                "X-Authenticated-User": "local_operator",
                "X-Forwarded-For": "127.0.0.1",
            },
        )
        with pytest.raises(HTTPException) as forged:
            authenticate_native_graph_principal(forged_headers)
        assert forged.value.status_code == 403
        assert forged.value.detail["code"] == "graph_auth_proxy_forbidden"

        proxied_valid_credential = _request(
            path="/api/live/world-graph/projection",
            headers={
                "Authorization": f"Bearer {LOCAL_OPERATOR_TOKEN}",
                "X-Forwarded-For": "127.0.0.1",
            },
        )
        with pytest.raises(HTTPException) as proxied:
            authenticate_native_graph_principal(proxied_valid_credential)
        assert proxied.value.status_code == 403
        assert proxied.value.detail["code"] == "graph_auth_proxy_forbidden"

        forged_body = _graph_route_requests()[0][1]
        forged_body["role"] = "gm"
        with pytest.raises(ValidationError):
            AgentTurnRequest.model_validate(forged_body)

        invalid_request = _request(
            path="/api/live/world-graph/projection",
            headers={"Authorization": "Bearer wrong-test-credential"},
        )
        with pytest.raises(HTTPException) as invalid:
            authenticate_native_graph_principal(invalid_request)
        assert invalid.value.status_code == 401

        remote_request = _request(
            path="/api/live/world-graph/projection",
            headers={"Authorization": f"Bearer {LOCAL_OPERATOR_TOKEN}"},
            host="192.0.2.10",
        )
        with pytest.raises(HTTPException) as remote:
            authenticate_native_graph_principal(remote_request)
        assert remote.value.status_code == 403
        assert remote.value.detail["code"] == "graph_auth_loopback_required"

        with pytest.raises(HTTPException) as non_gm:
            native_graph_gm_dependency(
                NativeGraphPrincipal(
                    subject="local_player", role="player", auth_method="local_operator"
                )
            )
        assert non_gm.value.status_code == 403
        assert non_gm.value.detail["code"] == "graph_gm_required"
    finally:
        for key, value in old.items():
            if value is None:
                os.environ.pop(key, None)
            else:
                os.environ[key] = value


def test_graphless_agent_turn_requires_auth_before_world_or_runtime_access(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    from apps.live_control_server.models.agent_turn import AgentTurnRequest
    from apps.live_control_server.routes import agent as agent_route
    from apps.live_control_server.services.agent_graph_auth import (
        AUTH_ENVIRONMENT_ENV,
        AUTH_MODE_ENV,
        LOCAL_OPERATOR_TOKEN_ENV,
    )

    _clear_auth_environment(monkeypatch)
    monkeypatch.setenv(AUTH_MODE_ENV, "local_operator")
    monkeypatch.setenv(AUTH_ENVIRONMENT_ENV, "local")
    monkeypatch.setenv(
        LOCAL_OPERATOR_TOKEN_ENV, "test-local-operator-token-with-adequate-length"
    )
    touched: list[str] = []

    def forbidden_resolution(*_args: Any, **_kwargs: Any) -> Any:
        touched.append("world_or_work_resolution")
        raise AssertionError("unauthorized Graphless turn reached authority resolution")

    monkeypatch.setattr(agent_route, "_conversation_service", forbidden_resolution)
    monkeypatch.setattr(agent_route, "_owner_resolver", forbidden_resolution)
    monkeypatch.setattr(agent_route, "_work_resolver", forbidden_resolution)
    request = _request(
        path="/api/live/agent/turn",
        app=SimpleNamespace(
            state=SimpleNamespace(
                agent_turn_runtime=SimpleNamespace(
                    run=lambda *_args: pytest.fail("unauthorized turn dispatched runtime")
                )
            )
        ),
    )
    payload = {
        "schema": "dmb_agent_turn_request_v1",
        "client_thread_id": "thread-graphless-test",
        "turn_id": "turn-graphless-test",
        "surface": {"surface_id": "index", "instance_id": "index-home"},
        "owner_scope": None,
        "primary_work": None,
        "client_work_state": "none",
        "graph_request": {"mode": "none"},
        "graph_selection": None,
        "message": "Can you help?",
    }
    with pytest.raises(HTTPException) as exc_info:
        agent_route.post_agent_turn(AgentTurnRequest.model_validate(payload), request)

    assert exc_info.value.status_code == 401
    assert exc_info.value.detail["code"] == "graph_auth_required"
    assert touched == []


def test_managed_projection_local_authorization_precedes_projection(monkeypatch) -> None:
    from fastapi import FastAPI
    from fastapi.testclient import TestClient
    from apps.live_control_server.routes import world_graph_projection as route
    from apps.live_control_server.services import agent_graph_auth as auth

    _clear_auth_environment(monkeypatch)
    monkeypatch.setenv("DMB_DEPLOYMENT_ENVIRONMENT", "local")
    monkeypatch.setenv("DMB_AUTH_MODE", "local_operator")
    monkeypatch.setenv(auth.AUTH_ENVIRONMENT_ENV, "local")
    monkeypatch.setenv(auth.AUTH_MODE_ENV, "local_operator")
    monkeypatch.setenv(auth.LOCAL_OPERATOR_TOKEN_ENV, LOCAL_OPERATOR_TOKEN)
    calls = []

    def projection(body):
        calls.append((body.managed_world_id, body.revision_pin))
        raise route.WorldGraphProjectionServiceError(
            "Authorized projection reached", code="fixture", status_code=409,
        )

    monkeypatch.setattr(route, "project_managed_world_graph", projection)
    app = FastAPI()
    app.include_router(route.router)
    path = "/api/live/world-graph/managed-projection"
    body = {"schema": "dmb_managed_world_graph_projection_request_v1",
            "managedWorldId": "guarded-world", "revisionPin": "rev:guard"}
    with TestClient(app, client=("127.0.0.1", 50000)) as client:
        assert client.post(path, json=body).status_code == 401
        assert client.post(path, json=body,
                           headers={"Authorization": "Bearer invalid"}).status_code == 401
        assert calls == []
        headers = {"Authorization": "Bearer " + LOCAL_OPERATOR_TOKEN}
        allowed = client.post(path, json=body, headers=headers)
        assert allowed.status_code == 409, allowed.text
        assert calls == [("guarded-world", "rev:guard")]
        calls.clear()
        # Substitute only identity resolution; the actual role/route guards run.
        monkeypatch.setattr(auth, "authenticate_native_graph_principal",
            lambda _request: auth.NativeGraphPrincipal("player", "player", "local_operator"))
        denied = client.post(path, json=body, headers=headers)
        assert denied.status_code == 403, denied.text
        assert denied.json()["detail"]["code"] == "graph_gm_required"
        assert calls == []


@pytest.fixture
def retired_projection_routes(monkeypatch):
    import psycopg
    from fastapi import FastAPI
    from fastapi.routing import APIRoute
    from fastapi.testclient import TestClient
    from dungeonmind.infrastructure.postgres import PostgresDatabase
    from application_state.source import service as sources
    from apps.live_control_server.routes import world_graph_projection as route
    from apps.live_control_server.services import agent_graph_auth as auth
    from apps.live_control_server.services import world_graph_projection as projection
    from apps.live_control_server.services import world_graph_recap_projection as recap
    from apps.live_control_server.integrations.dungeonmind import world_graph_reads as direct

    _clear_auth_environment(monkeypatch)
    monkeypatch.setenv("DMB_DEPLOYMENT_ENVIRONMENT", "local")
    monkeypatch.setenv("DMB_AUTH_MODE", "local_operator")
    monkeypatch.setenv(auth.AUTH_ENVIRONMENT_ENV, "local")
    monkeypatch.setenv(auth.AUTH_MODE_ENV, "local_operator")
    monkeypatch.setenv(auth.LOCAL_OPERATOR_TOKEN_ENV, LOCAL_OPERATOR_TOKEN)
    calls = []

    def forbidden(*args, **kwargs):
        calls.append((args, kwargs))
        pytest.fail("Retired projection reached legacy service/Core/source work")

    monkeypatch.setattr(projection, "project_world_graph", forbidden)
    monkeypatch.setattr(recap, "build_world_graph_recap_projection_payload", forbidden)
    monkeypatch.setattr(recap, "project_world_graph", forbidden)
    monkeypatch.setattr(recap, "_load_corpus_markdown", forbidden)
    monkeypatch.setattr(direct, "direct_services_from_config", forbidden)
    monkeypatch.setattr(direct, "project_world_graph_direct", forbidden)
    monkeypatch.setattr(sources, "get_source_markdown", forbidden)
    monkeypatch.setattr(PostgresDatabase, "__init__", forbidden)
    monkeypatch.setattr(psycopg, "connect", forbidden)
    app = FastAPI()
    app.include_router(route.router)
    for endpoint in ("projection", "recap-projection"):
        path = "/api/live/world-graph/" + endpoint
        mounted = next(row for row in app.routes if isinstance(row, APIRoute) and row.path == path)
        assert any(d.call is auth.native_graph_gm_dependency for d in mounted.dependant.dependencies)
    with TestClient(app, client=("127.0.0.1", 50000)) as client:
        yield client, app, {"Authorization": "Bearer " + LOCAL_OPERATOR_TOKEN}, calls
    assert calls == []


def _retired_projection_body():
    return {
        "schema": "dmb_world_graph_projection_request_v1",
        "worldId": "legacy-world", "campaignId": "legacy-campaign",
        "scopeMode": "campaign", "admissibility": "gm",
        "focus": {"kind": "session", "sessionId": "session-1"},
    }


@pytest.mark.parametrize("endpoint", ["projection", "recap-projection"])
def test_retired_public_projection_returns_typed_410_without_legacy_io(
    retired_projection_routes, endpoint
):
    from graph_memory.projection.world_projection import PROJECTION_ERROR_SCHEMA

    client, _, headers, calls = retired_projection_routes
    response = client.post("/api/live/world-graph/" + endpoint,
                           headers=headers, json=_retired_projection_body())
    assert response.status_code == 410
    assert response.json() == {
        "schema": PROJECTION_ERROR_SCHEMA, "code": "legacy_projection_retired",
        "message": "Select a managed World to inspect its native graph.",
        "statusCode": 410, "diagnostics": [],
    }
    assert calls == []


@pytest.mark.parametrize("endpoint", ["projection", "recap-projection"])
def test_retired_public_projection_keeps_real_auth_and_player_refusal(
    retired_projection_routes, endpoint
):
    from apps.live_control_server.services import agent_graph_auth as auth

    client, app, _, calls = retired_projection_routes
    path = "/api/live/world-graph/" + endpoint
    for body in (_retired_projection_body(), {}):
        response = client.post(path, json=body)
        assert response.status_code == 401
        assert response.json()["detail"]["code"] == "graph_auth_required"
    app.dependency_overrides[auth.authenticate_native_graph_principal] = lambda: auth.NativeGraphPrincipal(
        "synthetic-player", "player", "local_operator"
    )
    for body in (_retired_projection_body(), {}):
        response = client.post(path, json=body)
        assert response.status_code == 403
        assert response.json()["detail"]["code"] == "graph_gm_required"
    assert calls == []


@pytest.mark.parametrize("endpoint", ["projection", "recap-projection"])
@pytest.mark.parametrize("change", [{"schema": "unknown"}, {"worldId": None},
                                    {"unexpected": "not-admitted"}, {"scopeMode": "unknown"}])
def test_retired_public_projection_preserves_model_validation(
    retired_projection_routes, endpoint, change
):
    client, _, headers, calls = retired_projection_routes
    response = client.post("/api/live/world-graph/" + endpoint,
                           headers=headers, json=_retired_projection_body() | change)
    assert response.status_code == 422 and response.json()["code"] == "invalid_request"
    assert calls == []


@pytest.mark.parametrize("endpoint", ["projection", "recap-projection"])
def test_retired_public_projection_preserves_query_rejection(retired_projection_routes, endpoint):
    client, _, headers, calls = retired_projection_routes
    response = client.post("/api/live/world-graph/" + endpoint + "?world=foreign",
                           headers=headers, json=_retired_projection_body())
    assert response.status_code == 422 and response.json()["code"] == "invalid_request"
    assert calls == []


@pytest.mark.parametrize("endpoint", ["projection", "recap-projection"])
@pytest.mark.parametrize("authenticated", [False, True])
def test_retired_public_projection_preserves_malformed_json_precedence(
    retired_projection_routes, endpoint, authenticated
):
    client, _, headers, calls = retired_projection_routes
    response = client.post("/api/live/world-graph/" + endpoint, content="{",
        headers={"Content-Type": "application/json", **(headers if authenticated else {})})
    assert response.status_code == 422 and response.json()["code"] == "invalid_request"
    assert calls == []


def test_managed_projection_success_remains_available_beside_retired_routes(
    retired_projection_routes, monkeypatch
):
    from apps.live_control_server.routes import world_graph_projection as route
    from tests.test_managed_world_graph_projection import _native_projection

    client, _, headers, legacy_calls = retired_projection_routes
    seen = []

    def managed(request):
        seen.append((request.managed_world_id, request.revision_pin))
        return route.ManagedWorldGraphProjectionResponse(
            schema="dmb_managed_world_graph_projection_v1",
            managed_world_id=request.managed_world_id, native_world_id="native-managed",
            binding_version=1, projection=_native_projection(request.managed_world_id),
        )

    monkeypatch.setattr(route, "project_managed_world_graph", managed)
    response = client.post("/api/live/world-graph/managed-projection", headers=headers,
        json={"schema": "dmb_managed_world_graph_projection_request_v1",
              "managedWorldId": "managed-world", "revisionPin": "rev:pinned"})
    assert response.status_code == 200, response.text
    assert seen == [("managed-world", "rev:pinned")]
    assert response.json()["managedWorldId"] == "managed-world"
    assert legacy_calls == []
