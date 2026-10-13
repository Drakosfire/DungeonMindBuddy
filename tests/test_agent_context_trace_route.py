import asyncio
from datetime import UTC, datetime
from hashlib import sha256
from types import SimpleNamespace
from uuid import uuid4

import httpx
import pytest
from fastapi import FastAPI

from application_state.agent_conversation.context_trace import TraceSourcePassage, TurnContextTraceV1
from apps.live_control_server.routes import agent


@pytest.fixture
def trace_api(monkeypatch):
    token = "context-trace-local-test-token-" * 2
    monkeypatch.setenv("DMB_AGENT_GRAPH_AUTH_MODE", "local_operator")
    monkeypatch.setenv("DMB_AGENT_GRAPH_AUTH_ENVIRONMENT", "local")
    monkeypatch.setenv("DMB_AGENT_GRAPH_LOCAL_OPERATOR_TOKEN", token)
    world = "world-one"
    turn_id = uuid4()
    calls = []
    attempts = []

    def read(**binding):
        calls.append(binding)
        return attempts

    monkeypatch.setattr(agent, "_verified_world_id", lambda value: value)
    monkeypatch.setattr(agent, "_conversation_service", lambda request: SimpleNamespace(list_context_trace_attempts=read))
    app = FastAPI()
    app.include_router(agent.router, prefix="/api/live")

    async def get(*, authorized=True, query=""):
        async with httpx.AsyncClient(transport=httpx.ASGITransport(app=app, client=("127.0.0.1", 1234)), base_url="http://test") as client:
            return await client.get(f"/api/live/agent/worlds/{world}/conversation/turns/{turn_id}/context-trace{query}",
                                    headers={"Authorization": f"Bearer {token}"} if authorized else {})

    return SimpleNamespace(world=world, turn_id=turn_id, calls=calls, attempts=attempts, get=get)


def test_historical_turn_without_trace_returns_explicit_empty_attempts(trace_api):
    response = asyncio.run(trace_api.get())
    assert response.status_code == 200
    assert response.json()["attempts"] == []
    assert trace_api.calls == [{"world_id": trace_api.world, "turn_id": trace_api.turn_id}]


def test_opt_in_trace_read_returns_exact_captured_passage(trace_api):
    text = "Complete recorded passage. " * 100
    passage = TraceSourcePassage(sequence=0, elapsed_ms=1, source_read_event_id=uuid4(), read_call_id=uuid4(),
        world_id=trace_api.world, graph_revision="revision", source_read_id="read", anchor_id="anchor",
        evidence_ref_id="evidence", source_artifact_id="source", source_revision_id="source-revision",
        outcome="enough", returned_chars=len(text), content_sha256=sha256(text.encode()).hexdigest(), text=text)
    trace_api.attempts.append(TurnContextTraceV1(trace_id=uuid4(), world_id=trace_api.world,
        conversation_id=uuid4(), turn_id=trace_api.turn_id, attempt=1, execution_start_sequence=0,
        started_at=datetime.now(UTC), observations=[passage]))
    response = asyncio.run(trace_api.get())
    assert response.status_code == 200
    assert response.json()["schema"] == "dmb_agent_turn_context_trace_response_v1"
    assert response.json()["attempts"][0]["observations"][0]["text"] == text


def test_trace_read_authentication_precedes_storage(trace_api):
    response = asyncio.run(trace_api.get(authorized=False))
    assert response.status_code == 401
    assert trace_api.calls == []


def test_wrong_world_trace_binding_is_not_exposed(trace_api):
    trace_api.attempts.append(TurnContextTraceV1(trace_id=uuid4(), world_id="other-world",
        conversation_id=uuid4(), turn_id=trace_api.turn_id, attempt=1, execution_start_sequence=0,
        started_at=datetime.now(UTC), observations=[]))
    response = asyncio.run(trace_api.get())
    assert response.status_code == 409
    assert "other-world" not in response.text
    assert "attempts" not in response.text


def test_trace_read_rejects_extra_selectors(trace_api):
    response = asyncio.run(trace_api.get(query="?world=other-world"))
    assert response.status_code == 422
    assert trace_api.calls == []
