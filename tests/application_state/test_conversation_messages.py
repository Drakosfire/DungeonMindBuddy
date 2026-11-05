"""Saved text projection, distinct from full accepted-record inspection."""

from uuid import uuid4
import pytest
from application_state.agent_conversation import AgentConversationService, library
from application_state.agent_conversation.types import (
    TurnSubmission,
    TurnResult,
    ConversationTrashCommand,
)
from application_state.errors import (
    ApplicationStateNotFoundError,
    ApplicationStateValidationError,
)
from tests.application_state.test_agent_conversation_service import (
    _provenance,
    _submitted_intent,
)
from tests.application_state.test_conversation_library import new


def retained(service):
    cid = new(service)
    for i in range(3):
        text = f"Question {i}\nSecond line"
        accepted = service.accept_turn(
            TurnSubmission(
                world_id="world-one",
                conversation_id=cid,
                idempotency_key=uuid4(),
                expected_conversation_revision=service.get_conversation(
                    "world-one", cid
                ).revision,
                user_text=text,
                provenance=_provenance(),
                submitted_intent_v1=_submitted_intent("world-one", text),
            )
        )
        running = service.begin_turn(
            "world-one", cid, accepted.turn_id, expected_revision=accepted.revision
        )
        service.complete_turn(
            TurnResult(
                world_id="world-one",
                conversation_id=cid,
                turn_id=accepted.turn_id,
                expected_revision=running.revision,
                assistant_text=f"Saved answer {i} — unchanged.",
            )
        )
    return cid


def test_preview_preserves_exact_text_order_and_cursor_without_turn_hydration(
    application_state_dsn, monkeypatch
):
    service = AgentConversationService()
    cid = retained(service)
    expected = [
        {
            key: getattr(t, key)
            for key in ("turn_id", "sequence", "status", "user_text", "assistant_text")
        }
        for t in service.list_turns("world-one", cid)
    ]
    for row in expected:
        row["turn_id"] = str(row["turn_id"])
    monkeypatch.setattr(
        AgentConversationService,
        "list_turns",
        lambda *a, **k: pytest.fail("Text preview hydrated full execution records"),
    )
    page = library.read_messages("world-one", cid, limit=2)
    assert page["messages"] == expected[1:] and page["next_before_sequence"] == 2
    earlier = library.read_messages("world-one", cid, limit=2, before_sequence=2)
    assert (
        earlier["messages"] == expected[:1] and earlier["next_before_sequence"] is None
    )
    assert library.read_messages("world-one", cid, before_sequence=1)["messages"] == []
    assert set(page) == {
        "schema",
        "world_id",
        "conversation_id",
        "messages",
        "next_before_sequence",
    }
    with pytest.raises(ApplicationStateNotFoundError):
        library.read_messages("foreign-world", cid)
    with pytest.raises(ApplicationStateNotFoundError):
        library.read_messages("world-one", uuid4())
    with pytest.raises(ApplicationStateValidationError):
        library.read_messages("world-one", cid, limit=0)


def test_trash_keeps_message_artifacts_available_without_activating(
    application_state_dsn,
):
    service = AgentConversationService()
    cid = retained(service)
    before = library.read_messages("world-one", cid)
    pointer = service.get_world_pointer("world-one")
    service.set_conversation_trash(
        ConversationTrashCommand(
            world_id="world-one",
            conversation_id=cid,
            command_id=uuid4(),
            expected_pointer_revision=pointer.revision,
            expected_active_conversation_id=cid,
        ),
        restore=False,
    )
    trashed_pointer = service.get_world_pointer("world-one")
    assert library.read_messages("world-one", cid) == before
    assert service.get_world_pointer("world-one") == trashed_pointer
