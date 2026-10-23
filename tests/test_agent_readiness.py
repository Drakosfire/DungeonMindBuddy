"""Readiness is local metadata, not an inference or private source request."""
from types import SimpleNamespace

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from apps.live_control_server.routes import agent
from apps.live_control_server.services.agent_readiness import agent_readiness
from apps.live_control_server.services.build_jev_runtime import PreparedBuildJevRuntime


def test_missing_config_does_not_expose_values(monkeypatch):
    monkeypatch.delenv("OPENAI_API_KEY", raising=False)
    monkeypatch.delenv("TYPESAFE_JEV_API_KEY", raising=False)
    result = agent_readiness(surface="build", world_graph=True, build_runtime=None)
    assert not result["configured"]
    assert len(result["issues"]) == 3
    assert "API_KEY" not in str(result)


@pytest.mark.parametrize("surface,graph,expected", [("build", False, False), ("plan", False, True), ("play", False, True), ("plan", True, False), ("play", True, False)])
def test_decision_requirement_matches_route(monkeypatch, surface, graph, expected):
    monkeypatch.setenv("OPENAI_API_KEY", "secret-answer")
    monkeypatch.delenv("TYPESAFE_JEV_API_KEY", raising=False)
    runtime = PreparedBuildJevRuntime(accounting=object(), unavailable_reason=None)
    result = agent_readiness(surface=surface, world_graph=graph, build_runtime=runtime)
    assert result["configured"] is expected
    assert "secret-answer" not in str(result)


def test_build_requires_prepared_runtime(monkeypatch):
    monkeypatch.setenv("OPENAI_API_KEY", "secret-answer")
    monkeypatch.setenv("TYPESAFE_JEV_API_KEY", "secret-decision")
    for runtime in (None, SimpleNamespace(accounting=object(), unavailable_reason=None), PreparedBuildJevRuntime()):
        assert not agent_readiness(surface="build", world_graph=True, build_runtime=runtime)["configured"]
    assert agent_readiness(surface="build", world_graph=True,
                           build_runtime=PreparedBuildJevRuntime(accounting=object(), unavailable_reason=None))["configured"]


def test_route_auth_and_surface_validation(monkeypatch):
    app = FastAPI()
    app.include_router(agent.router, prefix="/api/live")
    calls = []
    monkeypatch.setattr(agent, "enforce_native_graph_gm", lambda request: calls.append(True))
    client = TestClient(app)
    assert client.get("/api/live/agent/readiness?surface=other").status_code == 422
    result = client.get("/api/live/agent/readiness?surface=build")
    assert result.status_code == 200
    assert calls == [True]
    assert result.json()["surface"] == "build"
    from fastapi import HTTPException
    def reject(request):
        raise HTTPException(401, "Not authorized")
    monkeypatch.setattr(agent, "enforce_native_graph_gm", reject)
    assert client.get("/api/live/agent/readiness?surface=build").status_code == 401
