"""Real PostgreSQL lifecycle/replay and retained-content boundary checks."""
from uuid import uuid4
import psycopg
import pytest
from application_state.agent_conversation import AgentConversationService
from application_state.agent_conversation import library
from application_state.agent_conversation.types import ConversationTrashCommand, DraftSave, ReopenCommand, TurnFailure
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
    cid = archive(service, count=2, keep_active=True)
    for turn in service.list_turns("world-one", cid):
        running = service.begin_turn("world-one", cid, turn.turn_id, expected_revision=turn.revision)
        service.fail_turn(TurnFailure(
            world_id="world-one", conversation_id=cid, turn_id=turn.turn_id,
            expected_revision=running.revision, failure_code="synthetic_before_dispatch",
        ), interrupted=True)
    new(service)
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


@pytest.mark.parametrize("switched", [False, True])
def test_trash_does_not_hide_a_reply_accepted_in_another_tab(application_state_dsn, switched):
    service = AgentConversationService()
    cid = archive(service, count=1, keep_active=not switched)
    before = service.get_world_pointer("world-one")
    with pytest.raises(ApplicationStateConflictError, match="reply in progress"):
        service.set_conversation_trash(command(service, cid), restore=False)
    assert service.get_world_pointer("world-one") == before
    assert service.get_conversation("world-one", cid).status == ("archived" if switched else "active")
    assert library.list_library("world-one", status="trashed")["items"] == []


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


def test_receipts_keep_their_reference_after_erasing_a_conversation(application_state_dsn):
    service = AgentConversationService()
    erased = new(service)
    current = new(service)
    service.set_conversation_trash(command(service, erased), restore=False)

    with psycopg.connect(application_state_dsn) as conn:
        before = conn.execute("""
            SELECT command_id, conversation_id, expected_active_conversation_id,
                   result_active_conversation_id
            FROM agent.command_receipt WHERE world_id = 'world-one'
            ORDER BY command_id
        """).fetchall()
        assert any(row[1] == erased for row in before)
        assert any(row[1] == current and row[2] == erased for row in before)
        assert conn.execute("""
            DELETE FROM agent.conversation
            WHERE world_id = 'world-one' AND conversation_id = %s
        """, (erased,)).rowcount == 1
        assert conn.execute("""
            SELECT command_id, conversation_id, expected_active_conversation_id,
                   result_active_conversation_id
            FROM agent.command_receipt WHERE world_id = 'world-one'
            ORDER BY command_id
        """).fetchall() == before
        assert conn.execute("""
            SELECT conversation_id, world_id FROM agent.conversation_identity
            WHERE conversation_id = %s
        """, (erased,)).fetchone() == (erased, "world-one")

    assert service.get_active_conversation("world-one").conversation_id == current


def test_receipt_cannot_bind_a_conversation_identity_in_another_world(application_state_dsn):
    service = AgentConversationService()
    foreign = new(service, world="foreign-world")
    new(service)

    with psycopg.connect(application_state_dsn) as conn:
        with pytest.raises(psycopg.errors.ForeignKeyViolation):
            conn.execute("""
                INSERT INTO agent.command_receipt
                    (world_id, command_id, command_kind, request_fingerprint,
                     expected_pointer_revision, conversation_id, result_pointer_revision, recorded_at)
                VALUES ('world-one', %s, 'archive', repeat('0', 64), 1, %s, 2, clock_timestamp())
            """, (uuid4(), foreign))


def test_permanent_delete_removes_chat_content_and_is_idempotent(
    application_state_dsn, tmp_path, monkeypatch,
):
    from psycopg.types.json import Jsonb

    from application_state.agent_conversation.types import ConversationDeleteCommand

    service = AgentConversationService()
    cid = archive(service, count=1, keep_active=True)
    draft_id = uuid4()
    service.save_draft(DraftSave(
        world_id="world-one", conversation_id=cid, draft_id=draft_id,
        expected_revision=0, body="Unsent work", provenance=_provenance(),
    ))
    turn, = service.list_turns("world-one", cid)
    running = service.begin_turn("world-one", cid, turn.turn_id, expected_revision=turn.revision)
    service.fail_turn(TurnFailure(
        world_id="world-one", conversation_id=cid, turn_id=turn.turn_id,
        expected_revision=running.revision, failure_code="synthetic_before_dispatch",
    ), interrupted=True)
    trace_id = uuid4()
    evidence_id = uuid4()
    with psycopg.connect(application_state_dsn) as conn:
        conn.execute("""
            INSERT INTO agent.turn_context_trace (turn_id, attempt, trace_id, payload)
            VALUES (%s, 1, %s, %s)
            ON CONFLICT (turn_id, attempt) DO UPDATE
                SET trace_id = EXCLUDED.trace_id, payload = EXCLUDED.payload
        """, (turn.turn_id, trace_id, Jsonb({
            "schema": "dmb_turn_context_trace_v1", "trace_id": str(trace_id),
            "turn_id": str(turn.turn_id), "world_id": "world-one",
            "conversation_id": str(cid), "attempt": 1,
            "execution_start_sequence": 0, "capture_status": "complete",
            "observations": [{"kind": "prompt_reference", "evidence_id": str(evidence_id)}],
        })))

    delete = ConversationDeleteCommand(**command(service, cid).model_dump())
    with pytest.raises(ApplicationStateConflictError, match="Move the conversation"):
        service.delete_conversation(delete)
    service.set_conversation_trash(command(service, cid), restore=False)
    current = new(service)
    other_draft_id = uuid4()
    service.save_draft(DraftSave(
        world_id="world-one", conversation_id=current, draft_id=other_draft_id,
        expected_revision=0, body="Keep this draft", provenance=_provenance(),
    ))
    delete = ConversationDeleteCommand(**command(service, cid).model_dump())
    restore = command(service, cid)
    receipt = service.delete_conversation(delete)
    assert receipt.command_kind == "delete"
    assert service.delete_conversation(delete) == receipt
    assert receipt.active_conversation_id == current
    assert service.get_draft("world-one", current, other_draft_id).body == "Keep this draft"
    with pytest.raises(ApplicationStateNotFoundError):
        service.list_turns("world-one", cid)
    with pytest.raises(ApplicationStateConflictError):
        service.set_conversation_trash(restore, restore=True)
    assert not library.list_library("world-one", status="trashed")["items"]

    with psycopg.connect(application_state_dsn) as conn:
        assert conn.execute(
            "SELECT turn_id FROM agent.turn WHERE conversation_id=%s", (cid,),
        ).fetchall() == []
        assert conn.execute(
            "SELECT draft_id FROM agent.composer_draft WHERE conversation_id=%s", (cid,),
        ).fetchall() == []
        assert conn.execute(
            "SELECT trace_id FROM agent.turn_context_trace WHERE turn_id=%s", (turn.turn_id,),
        ).fetchall() == []
        assert conn.execute("""
            SELECT kind, evidence_id FROM agent.conversation_erasure_file WHERE conversation_id=%s
        """, (cid,)).fetchall() == [("prompt", evidence_id)]

    from application_state.errors import ApplicationStateUnavailableError
    from apps.live_control_server.services import conversation_erasure

    evidence_dir = tmp_path / "out" / "agent_request_evidence"
    evidence_dir.mkdir(mode=0o700, parents=True)
    target = evidence_dir / f"{evidence_id}.json"
    target.write_text("prepared request for the erased chat")
    unrelated = evidence_dir / f"{uuid4()}.json"
    unrelated.write_text("prepared request for another chat")
    monkeypatch.setattr(conversation_erasure, "artifact_data_root", lambda: tmp_path)
    with monkeypatch.context() as scoped:
        def offline():
            raise OSError("synthetic unavailable evidence volume")

        scoped.setattr(conversation_erasure, "artifact_data_root", offline)
        with pytest.raises(ApplicationStateUnavailableError, match="Deletion is finishing"):
            conversation_erasure.finish_conversation_erasure(cid)
    assert target.exists()
    assert service.delete_conversation(delete) == receipt
    conversation_erasure.finish_conversation_erasure(cid)
    conversation_erasure.finish_conversation_erasure(cid)
    assert not target.exists()
    assert unrelated.read_text() == "prepared request for another chat"
    with psycopg.connect(application_state_dsn) as conn:
        assert conn.execute("""
            SELECT evidence_id FROM agent.conversation_erasure_file WHERE conversation_id=%s
        """, (cid,)).fetchall() == []


def test_permanent_delete_does_not_win_after_restore_or_cross_world(application_state_dsn):
    from application_state.agent_conversation.types import ConversationDeleteCommand

    service = AgentConversationService()
    cid = new(service)
    service.set_conversation_trash(command(service, cid), restore=False)

    foreign = ConversationDeleteCommand(**command(service, cid, "foreign-world").model_dump())
    with pytest.raises(ApplicationStateNotFoundError):
        service.delete_conversation(foreign)
    pending_delete = ConversationDeleteCommand(**command(service, cid).model_dump())
    service.set_conversation_trash(command(service, cid), restore=True)
    with pytest.raises(ApplicationStateConflictError):
        service.delete_conversation(pending_delete)
    assert service.get_conversation("world-one", cid).status == "archived"


def test_retry_edge_is_immutable_until_its_trashed_conversation_is_erased(application_state_dsn):
    from application_state.agent_conversation.types import ConversationDeleteCommand, TurnSubmission
    from tests.application_state.test_agent_conversation_service import _submitted_intent

    service = AgentConversationService()
    cid = new(service)

    def accept():
        text = "The same question"
        return service.accept_turn(TurnSubmission(
            world_id="world-one", conversation_id=cid, idempotency_key=uuid4(),
            expected_conversation_revision=service.get_conversation("world-one", cid).revision,
            user_text=text, provenance=_provenance().model_copy(update={"surface_id": "build"}),
            submitted_intent_v1=_submitted_intent("world-one", text, surface_id="build"),
        ))

    def interrupt(turn):
        running = service.begin_turn("world-one", cid, turn.turn_id, expected_revision=turn.revision)
        return service.fail_turn(TurnFailure(
            world_id="world-one", conversation_id=cid, turn_id=turn.turn_id,
            expected_revision=running.revision, failure_code="synthetic_before_dispatch",
        ), interrupted=True)

    parent = interrupt(accept())
    child = accept()
    with psycopg.connect(application_state_dsn) as conn:
        conn.execute("""
            INSERT INTO agent.turn_retry
                (predecessor_id, successor_id, root_id, world_id, conversation_id, predecessor_revision, ordinal)
            VALUES (%s, %s, %s, 'world-one', %s, %s, 1)
        """, (parent.turn_id, child.turn_id, parent.turn_id, cid, parent.revision))
    interrupt(child)
    service.set_conversation_trash(command(service, cid), restore=False)

    with psycopg.connect(application_state_dsn) as conn:
        with pytest.raises(psycopg.errors.RaiseException, match="Retry lineage is immutable"):
            with conn.transaction():
                conn.execute("DELETE FROM agent.turn_retry WHERE conversation_id=%s", (cid,))
    service.delete_conversation(ConversationDeleteCommand(**command(service, cid).model_dump()))
    with psycopg.connect(application_state_dsn) as conn:
        assert conn.execute("SELECT 1 FROM agent.turn_retry WHERE conversation_id=%s", (cid,)).fetchall() == []
