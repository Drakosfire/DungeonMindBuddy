"""Verified legacy import preserves absence without relaxing fresh Turn writers."""

from types import SimpleNamespace
from uuid import uuid4

import psycopg
import pytest

from application_state.agent_conversation import AgentConversationService
from application_state.agent_conversation import repository as repo
from application_state.agent_conversation.types import (
    HistoricalReference,
    LegacyImport,
    LegacyTurn,
    SubmittedGraphRequestIntentV1,
    SubmittedTurnIntentV1,
    TurnProvenance,
)
from application_state.errors import ApplicationStateConflictError


def _provenance(world_id):
    return TurnProvenance(
        world_id=world_id,
        surface_resolution="resolved",
        surface_id="index",
        primary_work=HistoricalReference(resolution="absent"),
        selected_object=HistoricalReference(resolution="absent"),
    )


@pytest.mark.parametrize("answer", ["Retained historical answer.", None])
def test_verified_legacy_import_stores_absent_current_intent_and_replays_only_as_import(
    application_state_dsn, answer
):
    world = "verified-legacy-intent-world"
    turn = LegacyTurn(
        source_turn_id="historical-turn",
        world_id=world,
        user_text="Historical question.",
        assistant_text=answer,
        provenance=_provenance(world),
    )
    request = LegacyImport(
        world_id=world,
        source_import_key="verified:source:thread",
        source_thread_id="historical-thread",
        expected_pointer_revision=0,
        expected_active_conversation_id=None,
        activate=True,
        turns=[turn],
    )
    service = AgentConversationService()
    imported = service.import_legacy_conversation(request)
    assert AgentConversationService().import_legacy_conversation(request) == imported
    loaded = AgentConversationService().list_turns(world, imported.conversation_id)
    assert len(loaded) == imported.imported_turn_count == 1
    retained = loaded[0]
    assert retained.user_text == turn.user_text and retained.assistant_text == answer
    assert retained.status == ("completed" if answer is not None else "interrupted")
    assert retained.failure_code == (
        None if answer is not None else "legacy_unanswered"
    )
    assert retained.submitted_intent_fingerprint_v1 is None
    assert retained.submitted_intent_fingerprint_v2 is None
    with psycopg.connect(application_state_dsn) as conn:
        row = conn.execute(
            """SELECT idempotency_key, submitted_intent_schema,
            submitted_intent_fingerprint_v1, submitted_intent_fingerprint_v2,
            graph_context_receipt, graph_context_execution, play_context_receipt, completion
            FROM agent.turn WHERE turn_id=%s""",
            (retained.turn_id,),
        ).fetchone()
    assert row[1:] == (None,) * 7
    current_intent = SubmittedTurnIntentV1(
        world_id=world,
        client_thread_id="current-thread",
        message=turn.user_text,
        surface_id="index",
        surface_instance_id="current-index",
        client_work_state="none",
        primary_work=None,
        graph_request=SubmittedGraphRequestIntentV1(mode="none"),
        graph_selection=None,
    )
    with pytest.raises(
        ApplicationStateConflictError, match="legacy-receipt-unverifiable"
    ):
        service.reconcile_turn(world, row[0], current_intent)


def test_unknown_fresh_submission_missing_intent_still_refuses_before_write(
    application_state_dsn,
):
    # Do not repair the legacy producer with a blanket getattr fallback here.
    from datetime import UTC, datetime

    submission = SimpleNamespace(
        world_id="unknown-fresh-world",
        conversation_id=uuid4(),
        idempotency_key=uuid4(),
        user_text="Fresh metadata is required.",
        provenance=_provenance("unknown-fresh-world"),
    )
    with pytest.raises(AttributeError, match="submitted_intent_v1"):
        with psycopg.connect(application_state_dsn) as conn:
            repo.insert_turn(
                conn,
                turn_id=uuid4(),
                request_fingerprint="a" * 64,
                idempotency_fingerprint="b" * 64,
                submission=submission,
                sequence=1,
                now=datetime.now(UTC),
            )
    with psycopg.connect(application_state_dsn) as conn:
        assert conn.execute(
            "SELECT count(*) FROM agent.turn WHERE world_id=%s", (submission.world_id,)
        ).fetchone() == (0,)
