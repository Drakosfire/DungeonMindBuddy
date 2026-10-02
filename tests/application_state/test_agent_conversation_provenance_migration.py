from __future__ import annotations

from uuid import uuid4

import psycopg
import pytest
from alembic import command

from application_state.agent_conversation import AgentConversationService
from application_state.agent_conversation.types import (
    ConversationCommand,
    DraftSave,
    HistoricalReference,
    TurnProvenance,
    TurnSubmission,
)
from application_state.cli import alembic_config


def test_0011_receipts_survive_additive_typed_provenance_migration(
    application_state_dsn: str,
) -> None:
    service = AgentConversationService()
    world_id = "provenance-migration-world"
    conversation_receipt = service.new_conversation(
        ConversationCommand(
            world_id=world_id,
            command_id=uuid4(),
            expected_pointer_revision=0,
            expected_active_conversation_id=None,
        )
    )
    provenance = TurnProvenance(
        world_id=world_id,
        surface_resolution="resolved",
        surface_id="plan",
        primary_work=HistoricalReference(
            resolution="resolved",
            kind="plan",
            object_id="legacy-plan-document",
            revision="legacy-work-revision-17",
            content_sha256="a" * 64,
        ),
        selected_object=HistoricalReference(resolution="absent"),
    )
    submission = TurnSubmission(
        world_id=world_id,
        conversation_id=conversation_receipt.conversation_id,
        idempotency_key=uuid4(),
        expected_conversation_revision=1,
        user_text="Preserve this legacy receipt.",
        provenance=provenance,
    )
    turn = service.accept_turn(submission)
    draft_save = DraftSave(
        world_id=world_id,
        conversation_id=conversation_receipt.conversation_id,
        draft_id=uuid4(),
        expected_revision=0,
        body="Preserve this legacy draft.",
        provenance=provenance,
    )
    draft = service.save_draft(draft_save)

    with psycopg.connect(application_state_dsn, autocommit=True) as conn:
        fingerprints_before = conn.execute(
            """
            SELECT request_fingerprint, idempotency_fingerprint
            FROM agent.turn WHERE turn_id = %s
            """,
            (turn.turn_id,),
        ).fetchone()
        draft_fingerprint_before = conn.execute(
            """
            SELECT request_fingerprint, source_fingerprint
            FROM agent.composer_draft WHERE draft_id = %s
            """,
            (draft.draft_id,),
        ).fetchone()

    command.downgrade(alembic_config(), "20261001_0011")
    command.upgrade(alembic_config(), "head")

    recovered = AgentConversationService()
    loaded_turn = recovered.list_turns(world_id, conversation_receipt.conversation_id)[
        0
    ]
    assert loaded_turn.turn_id == turn.turn_id
    assert loaded_turn.status == "accepted"
    assert loaded_turn.sequence == 1
    assert loaded_turn.provenance.surface_id == "plan"
    assert loaded_turn.provenance.surface_instance_id is None
    assert loaded_turn.provenance.primary_work.revision == "legacy-work-revision-17"
    assert loaded_turn.provenance.primary_work.content_sha256 == "a" * 64
    assert loaded_turn.provenance.primary_work.object_revision is None
    assert loaded_turn.provenance.primary_work.work_revision_id is None
    assert loaded_turn.provenance.primary_work.revision_n is None
    assert recovered.accept_turn(submission) == loaded_turn

    loaded_draft = recovered.get_draft(
        world_id, conversation_receipt.conversation_id, draft.draft_id
    )
    assert loaded_draft.body == "Preserve this legacy draft."
    assert loaded_draft.provenance.surface_instance_id is None
    assert loaded_draft.provenance.primary_work.revision == "legacy-work-revision-17"
    assert loaded_draft.provenance.primary_work.content_sha256 == "a" * 64
    assert loaded_draft.provenance.primary_work.object_revision is None

    with psycopg.connect(application_state_dsn, autocommit=True) as conn:
        assert (
            conn.execute(
                """
            SELECT request_fingerprint, idempotency_fingerprint
            FROM agent.turn WHERE turn_id = %s
            """,
                (turn.turn_id,),
            ).fetchone()
            == fingerprints_before
        )
        assert (
            conn.execute(
                """
            SELECT request_fingerprint, source_fingerprint
            FROM agent.composer_draft WHERE draft_id = %s
            """,
                (draft.draft_id,),
            ).fetchone()
            == draft_fingerprint_before
        )

    assert service.save_draft(draft_save) == draft


def test_downgrade_refuses_to_discard_typed_provenance(
    application_state_dsn: str,
) -> None:
    service = AgentConversationService()
    world_id = "provenance-downgrade-world"
    conversation = service.new_conversation(
        ConversationCommand(
            world_id=world_id,
            command_id=uuid4(),
            expected_pointer_revision=0,
            expected_active_conversation_id=None,
        )
    )
    provenance = TurnProvenance(
        world_id=world_id,
        surface_resolution="resolved",
        surface_id="plan",
        surface_instance_id="plan-pane-9",
        primary_work=HistoricalReference(
            resolution="resolved",
            kind="plan",
            object_id="plan-9",
            content_sha256="b" * 64,
            object_revision=7,
            work_revision_id=uuid4(),
            revision_n=3,
        ),
        selected_object=HistoricalReference(resolution="absent"),
    )
    accepted = service.accept_turn(
        TurnSubmission(
            world_id=world_id,
            conversation_id=conversation.conversation_id,
            idempotency_key=uuid4(),
            expected_conversation_revision=1,
            user_text="Keep typed provenance through rollback attempts.",
            provenance=provenance,
        )
    )

    with pytest.raises(
        RuntimeError, match="cannot downgrade while typed Agent provenance exists"
    ):
        command.downgrade(alembic_config(), "20261001_0011")

    loaded = service.list_turns(world_id, conversation.conversation_id)[0]
    assert loaded == accepted
    assert loaded.provenance.surface_instance_id == "plan-pane-9"
    assert loaded.provenance.primary_work.revision_n == 3
