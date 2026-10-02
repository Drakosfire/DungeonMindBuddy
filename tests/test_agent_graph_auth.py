from __future__ import annotations

from pathlib import Path
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


def test_every_public_native_graph_route_has_the_shared_gm_dependency() -> None:
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
    protected_routes = [
        "/api/live/world-graph/projection",
        "/api/live/world-graph/recap-projection",
        "/api/live/world-graph/retrieval/search",
        "/api/live/world-graph/retrieval/object",
        "/api/live/world-graph/retrieval/complete-object",
        "/api/live/world-graph/retrieval/neighborhood",
        "/api/live/world-graph/retrieval/evidence",
        "/api/live/world-graph/retrieval/source-anchor/read",
    ]
    for path in protected_routes:
        route = route_map[path]
        assert any(
            dependency.call is native_graph_gm_dependency
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
        assert forged.value.status_code == 401

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


def test_graphless_agent_turn_skips_the_graph_guard(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    from apps.live_control_server.models.agent_turn import AgentTurnRequest
    from apps.live_control_server.routes import agent as agent_route
    from apps.live_control_server.services.agent_runtime import (
        AgentRuntimeDescriptor,
        AgentRuntimeResult,
    )

    _clear_auth_environment(monkeypatch)

    class Runtime:
        descriptor = AgentRuntimeDescriptor("fake", "fake", "test", "conversation")

        def run(self, _invocation: Any) -> AgentRuntimeResult:
            return AgentRuntimeResult(
                status="ok",
                final_text="Graphless answer.",
                runtime_session_id="runtime",
            )

    def forbidden_guard(_request: Request) -> Any:
        raise AssertionError("graphless Agent turn invoked the graph guard")

    monkeypatch.setattr(agent_route, "enforce_native_graph_gm", forbidden_guard)
    monkeypatch.setattr(agent_route, "repo_root", lambda: tmp_path)
    monkeypatch.setattr(agent_route, "session_dir", lambda: tmp_path / "sessions")
    monkeypatch.setattr(agent_route, "_owner_resolver", lambda _body: None)
    monkeypatch.setattr(agent_route, "_work_resolver", lambda _body, _owner: None)
    request = SimpleNamespace(
        app=SimpleNamespace(state=SimpleNamespace(agent_turn_runtime=Runtime()))
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
    response = agent_route.post_agent_turn(
        AgentTurnRequest.model_validate(payload), request
    )
    assert response["answer"]["text"] == "Graphless answer."
