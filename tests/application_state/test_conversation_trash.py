"""Real PostgreSQL lifecycle/replay and retained-content boundary checks."""
from uuid import uuid4
import psycopg
import pytest
from application_state.agent_conversation import AgentConversationService
from application_state.agent_conversation import library
from application_state.agent_conversation.types import ConversationTrashCommand, DraftSave, ReopenCommand
from application_state.errors import ApplicationStateConflictError, ApplicationStateNotFoundError
from tests.application_state.test_conversation_library import new, archive
from tests.application_state.test_agent_conversation_service import _provenance


def command(service, cid, world="world-one"):
    pointer = service.get_world_pointer(world)
    return ConversationTrashCommand(world_id=world, conversation_id=cid, command_id=uuid4(), expected_pointer_revision=pointer.revision, expected_active_conversation_id=pointer.active_conversation_id)


def test_trash_active_restore_archived_and_preserve_draft(application_state_dsn):
    service = AgentConversationService()
    cid = new(service)
    draft_id = uuid4()
    draft = service.save_draft(DraftSave(world_id="world-one", conversation_id=cid, draft_id=draft_id, expected_revision=0, body="Unsent work", provenance=_provenance()))
    trash = command(service, cid)
    receipt = service.set_conversation_trash(trash, restore=False)
    assert receipt.command_kind == "trash" and receipt.active_conversation_id is None
    assert service.get_conversation("world-one", cid).status == "trashed"
    assert library.list_library("world-one")["items"] == []
    assert [row["conversation_id"] for row in library.list_library("world-one", status="trashed")["items"]] == [str(cid)]
    assert service.get_draft("world-one", cid, draft_id) == draft
    restore = command(service, cid)
    restored = service.set_conversation_trash(restore, restore=True)
    assert restored.command_kind == "restore" and restored.active_conversation_id is None
    assert service.get_conversation("world-one", cid).status == "archived"
    assert service.get_draft("world-one", cid, draft_id) == draft
    reopened = service.reopen_conversation(ReopenCommand(**command(service, cid).model_dump()))
    assert reopened.active_conversation_id == cid
    assert service.set_conversation_trash(trash, restore=False) == receipt
    assert service.set_conversation_trash(restore, restore=True) == restored
    assert service.get_active_conversation("world-one").conversation_id == cid


def test_archived_trash_keeps_turns_and_current_pointer(application_state_dsn):
    service = AgentConversationService()
    cid = archive(service, count=2)
    pointer = service.get_world_pointer("world-one")
    with psycopg.connect(application_state_dsn) as conn:
        before = conn.execute("SELECT to_jsonb(t) FROM agent.turn t WHERE conversation_id=%s ORDER BY sequence", (cid,)).fetchall()
    trash = command(service, cid)
    service.set_conversation_trash(trash, restore=False)
    assert service.get_world_pointer("world-one").active_conversation_id == pointer.active_conversation_id
    with pytest.raises(ApplicationStateConflictError):
        service.reopen_conversation(ReopenCommand(**command(service, cid).model_dump()))
    service.set_conversation_trash(command(service, cid), restore=True)
    with psycopg.connect(application_state_dsn) as conn:
        assert conn.execute("SELECT to_jsonb(t) FROM agent.turn t WHERE conversation_id=%s ORDER BY sequence", (cid,)).fetchall() == before
    assert service.get_active_conversation("world-one").conversation_id == pointer.active_conversation_id


def test_lifecycle_scope_conflict_and_uncertain_replay(application_state_dsn):
    service = AgentConversationService()
    cid = new(service)
    stale = command(service, cid)
    other = new(service)
    with pytest.raises(ApplicationStateConflictError):
        service.set_conversation_trash(stale, restore=False)
    foreign = command(service, cid, "foreign-world")
    with pytest.raises(ApplicationStateNotFoundError):
        service.set_conversation_trash(foreign, restore=False)
    trash = command(service, cid)
    receipt = service.set_conversation_trash(trash, restore=False)
    service.set_conversation_trash(command(service, cid), restore=True)
    service.set_conversation_trash(command(service, cid), restore=False)
    assert service.set_conversation_trash(trash, restore=False) == receipt
    assert service.get_active_conversation("world-one").conversation_id == other
    with pytest.raises(ApplicationStateConflictError):
        service.set_conversation_trash(trash, restore=True)
