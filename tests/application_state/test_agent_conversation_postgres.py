from __future__ import annotations

from concurrent.futures import ThreadPoolExecutor
from uuid import uuid4

import pytest

from application_state.agent_conversation import AgentConversationService
from application_state.agent_conversation.types import (
    ConversationCommand,
    DraftSave,
    HistoricalReference,
    TurnProvenance,
    TurnSubmission,
)
from application_state.cli import _current_and_head
from application_state.errors import ApplicationStateConflictError


def _reference(kind: str, object_id: str, revision: str, digest: str | None = None):
    return HistoricalReference(
        resolution="resolved",
        kind=kind,
        object_id=object_id,
        revision=revision,
        content_sha256=digest,
    )


def _provenance(world_id: str) -> TurnProvenance:
    return TurnProvenance(
        world_id=world_id,
        surface_resolution="resolved",
        surface_id="index",
        primary_work=_reference("plan", "plan-uuid-1", "work-revision-3"),
        supporting_work=[
            _reference("source_artifact", "source-7", "revision-12", "f" * 64)
        ],
        selected_object=HistoricalReference(resolution="absent"),
    )


def _typed_provenance(world_id: str) -> TurnProvenance:
    digest = "d" * 64
    return TurnProvenance(
        world_id=world_id,
        surface_resolution="resolved",
        surface_id="plan",
        surface_instance_id="plan-pane-7",
        primary_work=HistoricalReference(
            resolution="resolved",
            kind="plan",
            object_id="plan-document-7",
            content_sha256=digest,
            object_revision=9,
            work_revision_id=uuid4(),
            revision_n=4,
        ),
        supporting_work=[
            HistoricalReference(
                resolution="resolved",
                kind="runbook",
                object_id="runbook-2",
                content_sha256="e" * 64,
                object_revision=5,
                work_revision_id=uuid4(),
                revision_n=12,
            )
        ],
        selected_object=HistoricalReference(
            resolution="resolved",
            kind="plan",
            object_id="plan-selection-3",
            content_sha256="f" * 64,
            object_revision=6,
            work_revision_id=uuid4(),
            revision_n=8,
        ),
    )


def _new(service: AgentConversationService, world_id: str):
    return service.new_conversation(
        ConversationCommand(
            world_id=world_id,
            command_id=uuid4(),
            expected_pointer_revision=0,
            expected_active_conversation_id=None,
        )
    )


def test_agent_conversation_migration_is_single_current_head(
    application_state_dsn: str,
) -> None:
    current, head = _current_and_head(application_state_dsn)
    assert current == head == "20261002_0013"


def test_turn_and_draft_round_trip_exact_typed_provenance(
    application_state_dsn: str,
) -> None:
    writer = AgentConversationService()
    world_id = "typed-provenance-world"
    conversation = _new(writer, world_id)
    provenance = _typed_provenance(world_id)
    submission = TurnSubmission(
        world_id=world_id,
        conversation_id=conversation.conversation_id,
        idempotency_key=uuid4(),
        expected_conversation_revision=1,
        user_text="Ask about the pinned plan.",
        provenance=provenance,
    )

    accepted = writer.accept_turn(submission)
    assert writer.accept_turn(submission) == accepted
    recovered = AgentConversationService()
    loaded_turn = recovered.list_turns(world_id, conversation.conversation_id)[0]
    assert loaded_turn.provenance == provenance
    assert loaded_turn.provenance.surface_instance_id == "plan-pane-7"
    assert loaded_turn.provenance.primary_work.object_revision == 9
    assert loaded_turn.provenance.primary_work.work_revision_id == (
        provenance.primary_work.work_revision_id
    )
    assert loaded_turn.provenance.primary_work.revision_n == 4
    assert loaded_turn.provenance.supporting_work == provenance.supporting_work
    assert loaded_turn.provenance.selected_object == provenance.selected_object

    different_instance = provenance.model_copy(
        update={"surface_instance_id": "plan-pane-8"}
    )
    with pytest.raises(
        ApplicationStateConflictError, match="different content or provenance"
    ):
        recovered.accept_turn(
            submission.model_copy(update={"provenance": different_instance})
        )

    changed_revisions = (
        ("object_revision", provenance.primary_work.object_revision + 1),
        ("work_revision_id", uuid4()),
        ("revision_n", provenance.primary_work.revision_n + 1),
    )
    for field, value in changed_revisions:
        different_plan_revision = provenance.primary_work.model_copy(
            update={field: value}
        )
        different_basis = provenance.model_copy(
            update={"primary_work": different_plan_revision}
        )
        with pytest.raises(
            ApplicationStateConflictError, match="different content or provenance"
        ):
            recovered.accept_turn(
                submission.model_copy(update={"provenance": different_basis})
            )

    save = DraftSave(
        world_id=world_id,
        conversation_id=conversation.conversation_id,
        draft_id=uuid4(),
        expected_revision=0,
        body="A recoverable composer draft.",
        provenance=provenance,
    )
    draft = writer.save_draft(save)
    assert writer.save_draft(save) == draft
    loaded_draft = AgentConversationService().get_draft(
        world_id, conversation.conversation_id, save.draft_id
    )
    assert loaded_draft.provenance == provenance
    assert loaded_draft.provenance.surface_instance_id == "plan-pane-7"


def test_fresh_service_instance_reads_committed_world_conversation(
    application_state_dsn: str,
) -> None:
    writer = AgentConversationService()
    receipt = _new(writer, "restart-recovery-world")
    submission = TurnSubmission(
        world_id="restart-recovery-world",
        conversation_id=receipt.conversation_id,
        idempotency_key=uuid4(),
        expected_conversation_revision=1,
        user_text="Keep this after process restart.",
        provenance=_provenance("restart-recovery-world"),
    )
    accepted = writer.accept_turn(submission)

    recovered = AgentConversationService()
    assert (
        recovered.get_active_conversation("restart-recovery-world").conversation_id
        == receipt.conversation_id
    )
    turns = recovered.list_turns("restart-recovery-world", receipt.conversation_id)
    assert len(turns) == 1 and turns[0].turn_id == accepted.turn_id
    assert turns[0].provenance.supporting_work[0].content_sha256 == "f" * 64


def test_distinct_concurrent_new_commands_are_fenced_by_pointer_revision(
    application_state_dsn: str,
) -> None:
    service = AgentConversationService()
    first = _new(service, "concurrent-new-world")
    pointer = service.get_world_pointer("concurrent-new-world")
    requests = [
        ConversationCommand(
            world_id="concurrent-new-world",
            command_id=uuid4(),
            expected_pointer_revision=pointer.revision,
            expected_active_conversation_id=pointer.active_conversation_id,
        )
        for _ in range(2)
    ]

    def run(command: ConversationCommand):
        try:
            return service.new_conversation(command)
        except ApplicationStateConflictError as exc:
            return exc

    with ThreadPoolExecutor(max_workers=2) as pool:
        outcomes = list(pool.map(run, requests))
    assert sum(not isinstance(value, Exception) for value in outcomes) == 1
    assert (
        sum(isinstance(value, ApplicationStateConflictError) for value in outcomes) == 1
    )
    active = service.get_active_conversation("concurrent-new-world")
    assert active is not None
    assert active.conversation_id != first.conversation_id
    assert len(service.list_conversations("concurrent-new-world")) == 2


def test_duplicate_turn_submission_concurrent_replay_returns_one_turn(
    application_state_dsn: str,
) -> None:
    service = AgentConversationService()
    conversation = _new(service, "concurrent-turn-replay-world")
    request = TurnSubmission(
        world_id="concurrent-turn-replay-world",
        conversation_id=conversation.conversation_id,
        idempotency_key=uuid4(),
        expected_conversation_revision=1,
        user_text="The same accepted submission.",
        provenance=_provenance("concurrent-turn-replay-world"),
    )
    with ThreadPoolExecutor(max_workers=2) as pool:
        results = list(pool.map(service.accept_turn, [request, request]))
    assert results[0].turn_id == results[1].turn_id
    assert results[0].sequence == results[1].sequence == 1
    assert (
        len(
            service.list_turns(
                "concurrent-turn-replay-world", conversation.conversation_id
            )
        )
        == 1
    )
