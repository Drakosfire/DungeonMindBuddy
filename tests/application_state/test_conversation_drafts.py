from uuid import uuid4

import pytest
from fastapi import FastAPI, HTTPException
from fastapi.testclient import TestClient

from application_state.agent_conversation import conversation_drafts
from application_state.agent_conversation.service import AgentConversationService
from application_state.agent_conversation.types import TurnResult, TurnSubmission
from application_state.engine import connect
from tests.application_state.test_agent_conversation_service import _new, _provenance, _submitted_intent


def test_independent_conversation_draft_edits(application_state_dsn, monkeypatch):
    service = AgentConversationService()
    world_id = "turn-world"
    conversation = _new(service, world_id, expected_revision=0)
    conversation_id = conversation.conversation_id

    def finish_draft(title, conversation_revision):
        text = f"Draft {title} in chat."
        accepted = service.accept_turn(TurnSubmission(
            world_id=world_id,
            conversation_id=conversation_id,
            idempotency_key=uuid4(),
            expected_conversation_revision=conversation_revision,
            user_text=text,
            provenance=_provenance(world_id),
            submitted_intent_v1=_submitted_intent(world_id, text),
        ))
        running = service.begin_turn(world_id, conversation_id, accepted.turn_id, expected_revision=1)
        service.complete_turn(TurnResult(
            world_id=world_id,
            conversation_id=conversation_id,
            turn_id=accepted.turn_id,
            expected_revision=running.revision,
            assistant_text=title,
        ))
        return dict(world_id=world_id, conversation_id=conversation_id, turn_id=accepted.turn_id)

    first = finish_draft("First", 1)
    second = finish_draft("Second", service.get_active_conversation(world_id).revision)

    with connect(application_state_dsn) as conn:
        for scope, title in [(first, "First"), (second, "Second")]:
            conversation_drafts.create_draft(conn, **scope, markdown=title)
    assert service.conversation_draft_turn_ids(
        world_id, conversation_id, [first["turn_id"], second["turn_id"], uuid4()],
    ) == {first["turn_id"], second["turn_id"]}
    assert service.conversation_draft_turn_ids(
        world_id, uuid4(), [first["turn_id"], second["turn_id"]],
    ) == set()

    from apps.live_control_server.routes import agent
    from apps.live_control_server.services import hosted_native_graph_access

    monkeypatch.setattr(hosted_native_graph_access, "require_conversation_access", lambda *a, **kw: None)
    monkeypatch.setattr(agent, "_verified_world_id", lambda value: value)
    monkeypatch.setattr(agent, "_conversation_service", lambda request: AgentConversationService())
    app = FastAPI()
    app.include_router(agent.router)
    base = f"/agent/worlds/{world_id}/conversations"
    first_path = f"{base}/{conversation_id}/drafts/{first['turn_id']}"
    second_path = f"{base}/{conversation_id}/drafts/{second['turn_id']}"
    with TestClient(app) as client:
        for path, title in [(first_path, "First"), (second_path, "Second")]:
            response = client.put(path, json={"expected_revision": 1, "markdown": f"{title} edited"})
            assert response.status_code == 200, response.text
            assert response.json() == {"revision": 2, "markdown": f"{title} edited"}
    with TestClient(app) as client:
        assert client.get(first_path).json() == {"revision": 2, "markdown": "First edited"}
        assert client.get(second_path).json() == {"revision": 2, "markdown": "Second edited"}
        assert client.put(first_path, json={"expected_revision": 1, "markdown": "Stale"}).status_code == 409
        assert client.get(f"{base}/{uuid4()}/drafts/{first['turn_id']}").status_code == 404
    with connect(application_state_dsn) as conn:
        assert conn.execute(
            "SELECT assistant_text FROM agent.turn WHERE turn_id = %s", (first["turn_id"],)
        ).fetchone()[0] == "First"


def test_draft_route_checks_access_before_read_or_edit(monkeypatch):
    from apps.live_control_server.routes import agent
    from apps.live_control_server.services import hosted_native_graph_access

    def deny(*args, **kwargs):
        raise HTTPException(status_code=403)

    def unexpected(*args, **kwargs):
        pytest.fail("Conversation storage was opened before authorization")

    monkeypatch.setattr(hosted_native_graph_access, "require_conversation_access", deny)
    monkeypatch.setattr(agent, "_verified_world_id", unexpected)
    monkeypatch.setattr(agent, "_conversation_service", unexpected)
    app = FastAPI()
    app.include_router(agent.router)
    path = f"/agent/worlds/turn-world/conversations/{uuid4()}/drafts/{uuid4()}"
    with TestClient(app) as client:
        assert client.get(path).status_code == 403
        assert client.put(path, json={"expected_revision": 1, "markdown": "Edit"}).status_code == 403
