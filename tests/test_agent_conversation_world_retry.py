from __future__ import annotations

from concurrent.futures import ThreadPoolExecutor
from threading import Barrier
from uuid import UUID, uuid4

import psycopg
import pytest
from alembic import command

from application_state.agent_conversation import AgentConversationService
from application_state.agent_conversation.types import (
    ConversationCommand,
    HistoricalReference,
    SubmittedGraphRequestIntentV1,
    SubmittedPrimaryWorkIntentV1,
    SubmittedTurnIntentV1,
    TurnProvenance,
    TurnResult,
    TurnSubmission,
    turn_idempotency_fingerprint,
)
from application_state.cli import _current_and_head, alembic_config
from application_state.errors import ApplicationStateConflictError


def _provenance(world_id: str, *, work_revision: str = "work-revision-3") -> TurnProvenance:
    return TurnProvenance(
        world_id=world_id,
        surface_resolution="resolved",
        surface_id="plan",
        primary_work=HistoricalReference(
            resolution="resolved",
            kind="plan",
            object_id="plan:main",
            revision=work_revision,
        ),
        supporting_work=[
            HistoricalReference(
                resolution="resolved",
                kind="source_artifact",
                object_id="source:7",
                revision="source-revision-2",
                content_sha256="a" * 64,
            )
        ],
        selected_object=HistoricalReference(resolution="absent"),
    )


def _new_conversation(service: AgentConversationService, world_id: str):
    pointer = service.get_world_pointer(world_id)
    return service.new_conversation(
        ConversationCommand(
            world_id=world_id,
            command_id=uuid4(),
            expected_pointer_revision=pointer.revision,
            expected_active_conversation_id=pointer.active_conversation_id,
        )
    )


def _submission(
    world_id: str,
    conversation_id: UUID,
    idempotency_key: UUID,
    *,
    expected_revision: int = 1,
    user_text: str = "Apply the accepted details.",
    provenance: TurnProvenance | None = None,
) -> TurnSubmission:
    return TurnSubmission(
        world_id=world_id,
        conversation_id=conversation_id,
        idempotency_key=idempotency_key,
        expected_conversation_revision=expected_revision,
        user_text=user_text,
        provenance=provenance or _provenance(world_id),
        submitted_intent_v1=SubmittedTurnIntentV1(
            world_id=world_id,
            client_thread_id="world-retry-client-thread",
            message=user_text,
            surface_id="plan",
            surface_instance_id="plan-main",
            client_work_state="saved_clean",
            primary_work=SubmittedPrimaryWorkIntentV1(
                kind="plan",
                object_id="plan:main",
                expected_revision=3,
                expected_revision_n=17,
                expected_content_sha256="a" * 64,
            ),
            graph_request=SubmittedGraphRequestIntentV1(mode="none"),
            graph_selection=None,
        ),
    )


def test_completed_turn_retry_after_world_switch_returns_original_receipt(
    application_state_dsn: str,
) -> None:
    service = AgentConversationService()
    world_id = "world-retry-after-switch"
    first = _new_conversation(service, world_id)
    key = uuid4()
    original = _submission(world_id, first.conversation_id, key)
    accepted = service.accept_turn(original)
    running = service.begin_turn(
        world_id, first.conversation_id, accepted.turn_id, expected_revision=accepted.revision
    )
    completed = service.complete_turn(
        TurnResult(
            world_id=world_id,
            conversation_id=first.conversation_id,
            turn_id=accepted.turn_id,
            expected_revision=running.revision,
            assistant_text="The details were applied.",
        )
    )

    later = _new_conversation(service, world_id)
    later_before = service.get_active_conversation(world_id)
    assert later_before is not None and later_before.conversation_id == later.conversation_id

    retry = _submission(
        world_id,
        later.conversation_id,
        key,
        expected_revision=later_before.revision,
    )
    replayed = service.accept_turn(retry)

    assert replayed == completed
    assert replayed.conversation_id == first.conversation_id
    assert replayed.status == "completed"
    assert service.get_active_conversation(world_id) == later_before
    assert service.list_turns(world_id, later.conversation_id) == []

    changed_message = "A different submission."
    with pytest.raises(ApplicationStateConflictError, match="different submitted intent"):
        service.accept_turn(
            retry.model_copy(
                update={
                    "user_text": changed_message,
                    "submitted_intent_v1": retry.submitted_intent_v1.model_copy(
                        update={"message": changed_message}
                    ),
                }
            )
        )
    changed_plan_basis = retry.submitted_intent_v1.primary_work.model_copy(
        update={
            "expected_revision_n": retry.submitted_intent_v1.primary_work.expected_revision_n
            + 1,
            "expected_content_sha256": "b" * 64,
        }
    )
    changed_plan_intent = retry.submitted_intent_v1.model_copy(
        update={"primary_work": changed_plan_basis}
    )
    with pytest.raises(ApplicationStateConflictError, match="different submitted intent"):
        service.accept_turn(
            retry.model_copy(update={"submitted_intent_v1": changed_plan_intent})
        )
    assert service.accept_turn(
        retry.model_copy(update={"provenance": _provenance(world_id, work_revision="work-4")})
    ) == completed


def test_same_turn_key_is_independent_across_worlds(application_state_dsn: str) -> None:
    service = AgentConversationService()
    key = uuid4()
    first_world = "world-key-scope-one"
    second_world = "world-key-scope-two"
    first_conversation = _new_conversation(service, first_world)
    second_conversation = _new_conversation(service, second_world)

    first = service.accept_turn(
        _submission(first_world, first_conversation.conversation_id, key)
    )
    second = service.accept_turn(
        _submission(second_world, second_conversation.conversation_id, key)
    )

    assert first.turn_id != second.turn_id
    assert first.world_id == first_world
    assert second.world_id == second_world


def test_retry_racing_world_pointer_switch_has_one_receipt(application_state_dsn: str) -> None:
    service = AgentConversationService()
    world_id = "world-retry-switch-race"
    first = _new_conversation(service, world_id)
    key = uuid4()
    original = _submission(world_id, first.conversation_id, key)
    accepted = service.accept_turn(original)
    running = service.begin_turn(
        world_id, first.conversation_id, accepted.turn_id, expected_revision=accepted.revision
    )
    service.complete_turn(
        TurnResult(
            world_id=world_id,
            conversation_id=first.conversation_id,
            turn_id=accepted.turn_id,
            expected_revision=running.revision,
            assistant_text="Recorded before the race.",
        )
    )
    pointer = service.get_world_pointer(world_id)
    switch = ConversationCommand(
        world_id=world_id,
        command_id=uuid4(),
        expected_pointer_revision=pointer.revision,
        expected_active_conversation_id=pointer.active_conversation_id,
    )
    barrier = Barrier(2)

    def retry():
        barrier.wait()
        return AgentConversationService().accept_turn(original)

    def switch_pointer():
        barrier.wait()
        return AgentConversationService().new_conversation(switch)

    with ThreadPoolExecutor(max_workers=2) as pool:
        retry_future = pool.submit(retry)
        switch_future = pool.submit(switch_pointer)
        retried, later = retry_future.result(), switch_future.result()

    assert retried.turn_id == accepted.turn_id
    assert later.conversation_id != first.conversation_id
    assert service.get_active_conversation(world_id).conversation_id == later.conversation_id
    assert service.list_turns(world_id, later.conversation_id) == []


def _insert_v10_turns(
    dsn: str,
    *,
    world_id: str,
    keys: list[UUID],
    user_texts: list[str],
) -> list[tuple[UUID, UUID]]:
    now_sql = "CURRENT_TIMESTAMP"
    rows: list[tuple[UUID, UUID]] = []
    with psycopg.connect(dsn) as conn:
        for index, (key, user_text) in enumerate(zip(keys, user_texts, strict=True)):
            conversation_id = uuid4()
            turn_id = uuid4()
            rows.append((conversation_id, turn_id))
            conn.execute(
                f"""
                INSERT INTO agent.conversation (
                    conversation_id, world_id, status, revision, next_turn_sequence,
                    created_at, updated_at, archived_at
                ) VALUES (%s, %s, 'archived', 1, 2, {now_sql}, {now_sql}, {now_sql})
                """,
                (conversation_id, world_id),
            )
            conn.execute(
                f"""
                INSERT INTO agent.turn (
                    turn_id, conversation_id, world_id, idempotency_key, sequence,
                    revision, status, request_fingerprint, user_text, assistant_text,
                    failure_code, surface_resolution, surface_id, attempt, accepted_at,
                    completed_at, updated_at
                ) VALUES (%s, %s, %s, %s, 1, 1, 'interrupted', %s, %s, NULL,
                          'legacy_unanswered', 'resolved', 'plan', 0,
                          {now_sql}, {now_sql}, {now_sql})
                """,
                (turn_id, conversation_id, world_id, key, "b" * 64, user_text),
            )
            conn.execute(
                """
                INSERT INTO agent.turn_reference (
                    turn_id, reference_role, ordinal, resolution, kind, object_id,
                    revision, content_sha256
                ) VALUES
                    (%s, 'primary', 0, 'resolved', 'plan', 'plan:main', 'work-revision-3', NULL),
                    (%s, 'supporting', 0, 'resolved', 'source_artifact', 'source:7', 'source-revision-2', %s),
                    (%s, 'selected', 0, 'absent', NULL, NULL, NULL, NULL)
                """,
                (turn_id, turn_id, "a" * 64, turn_id),
            )
    return rows


def test_0011_backfills_stable_fingerprints_for_existing_turns(
    application_state_dsn: str,
) -> None:
    command.downgrade(alembic_config(), "20261001_0010")
    key = uuid4()
    world_id = "world-fingerprint-backfill"
    _insert_v10_turns(
        application_state_dsn,
        world_id=world_id,
        keys=[key],
        user_texts=["Keep the historical receipt."],
    )

    command.upgrade(alembic_config(), "head")

    expected = turn_idempotency_fingerprint(
        world_id,
        "Keep the historical receipt.",
        _provenance(world_id),
    )
    with psycopg.connect(application_state_dsn) as conn:
        (stored,) = conn.execute(
            "SELECT idempotency_fingerprint FROM agent.turn WHERE world_id = %s AND idempotency_key = %s",
            (world_id, key),
        ).fetchone()
    assert stored == expected
    assert _current_and_head(application_state_dsn) == ("20261008_0019", "20261008_0019")


def test_0011_fails_closed_on_legacy_duplicate_world_keys(
    application_state_dsn: str,
) -> None:
    command.downgrade(alembic_config(), "20261001_0010")
    key = uuid4()
    _insert_v10_turns(
        application_state_dsn,
        world_id="world-legacy-key-collision",
        keys=[key, key],
        user_texts=["First receipt.", "Second receipt."],
    )

    with pytest.raises(RuntimeError, match="existing duplicate"):
        command.upgrade(alembic_config(), "head")

    assert _current_and_head(application_state_dsn) == ("20261001_0010", "20261008_0019")
    with psycopg.connect(application_state_dsn) as conn:
        columns = conn.execute(
            """
            SELECT count(*) FROM information_schema.columns
            WHERE table_schema = 'agent' AND table_name = 'turn'
              AND column_name = 'idempotency_fingerprint'
            """
        ).fetchone()[0]
        assert columns == 0
        assert conn.execute(
            "SELECT count(*) FROM agent.turn WHERE world_id = %s AND idempotency_key = %s",
            ("world-legacy-key-collision", key),
        ).fetchone()[0] == 2
