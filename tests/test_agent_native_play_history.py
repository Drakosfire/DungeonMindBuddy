"""Actual native history wire retains frozen recovery proof without inventing an answer."""
import asyncio
from types import SimpleNamespace

import httpx
import pytest
from fastapi import FastAPI

from apps.live_control_server.routes import agent
from apps.live_control_server.services.agent_turn_service import project_play_turn_context, AgentTurnServiceError
from tests.test_play_graph_records import retained, NOW


@pytest.mark.parametrize("status", ["accepted", "running", "failed", "interrupted"])
@pytest.mark.parametrize("correlation", [False, True])
def test_native_history_projects_exact_noncompleted_receipt(status, correlation, monkeypatch):
    turn = retained(status=status)
    if status in {"failed", "interrupted"}:
        turn = turn.model_copy(update={"completed_at": NOW, "failure_code": "provider_failed"})
    token = "native-play-history-operator-token" * 2
    monkeypatch.setenv("DMB_AGENT_GRAPH_AUTH_MODE", "local_operator")
    monkeypatch.setenv("DMB_AGENT_GRAPH_AUTH_ENVIRONMENT", "local")
    monkeypatch.setenv("DMB_AGENT_GRAPH_LOCAL_OPERATOR_TOKEN", token)
    monkeypatch.setattr(agent, "_verified_world_id", lambda world: world)
    pointer = SimpleNamespace(revision=1, active_conversation_id=turn.conversation_id)
    service = SimpleNamespace(get_world_pointer=lambda _: pointer,
        get_active_conversation=lambda _: SimpleNamespace(conversation_id=turn.conversation_id),
        list_turns=lambda *_args, **_kwargs: [turn])
    app = FastAPI()
    app.state.agent_conversation_service = service
    app.include_router(agent.router, prefix="/api/live")

    async def get():
        async with httpx.AsyncClient(transport=httpx.ASGITransport(app=app, client=("127.0.0.1", 1234)), base_url="http://test") as client:
            return await client.get(f"/api/live/agent/worlds/{turn.world_id}/conversation",
                params={"include_turn_correlation": str(correlation).lower()}, headers={"Authorization": f"Bearer {token}"})
    response = asyncio.run(get())
    assert response.status_code == 200, response.text
    body = response.json()
    assert body["schema"] == ("dmb_agent_conversation_history_v3" if correlation else "dmb_agent_conversation_history_v2")
    row = body["turns"][0]
    assert row["lifecycle_status"] == status and row["assistant_text"] is None
    assert ("idempotency_key" in row) == correlation
    context = row["play_context"]
    assert context["receipt"] == turn.graph_context_receipt.model_dump(mode="json", by_alias=True)
    assert context["completion"] is None and context["delivery_replay"] is True
    assert context["execution"]["automatic_redispatch"] is False
    assert context["receipt"]["play_basis"]["edition_revision"] == 0
    assert context["receipt"]["play_basis"]["scene_id"] == "scene:boardwalk"


@pytest.mark.parametrize("field", ["world_id", "provenance", "play_context_receipt"])
def test_native_history_refuses_foreign_terminal_receipt(field):
    turn = retained(status="failed")
    if field == "world_id": value = "foreign-world"
    elif field == "provenance": value = turn.provenance.model_copy(update={"surface_id": "plan"})
    else: value = turn.play_context_receipt.model_copy(update={"scene_id": "scene:other"})
    turn = turn.model_copy(update={field: value})
    with pytest.raises(AgentTurnServiceError, match="historical receipt"):
        project_play_turn_context(turn, delivery_replay=True)
