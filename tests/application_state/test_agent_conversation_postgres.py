from __future__ import annotations

from concurrent.futures import ThreadPoolExecutor
from uuid import uuid4

from application_state.agent_conversation import AgentConversationService
from application_state.agent_conversation.types import (
    ConversationCommand,
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


def _new(service: AgentConversationService, world_id: str):
    return service.new_conversation(
        ConversationCommand(
            world_id=world_id,
            command_id=uuid4(),
            expected_pointer_revision=0,
            expected_active_conversation_id=None,
        )
    )


def test_agent_conversation_migration_is_single_current_head(application_state_dsn: str) -> None:
    current, head = _current_and_head(application_state_dsn)
    assert current == head == "20261001_0010"


def test_fresh_service_instance_reads_committed_world_conversation(application_state_dsn: str) -> None:
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
    assert recovered.get_active_conversation("restart-recovery-world").conversation_id == receipt.conversation_id
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
    assert sum(isinstance(value, ApplicationStateConflictError) for value in outcomes) == 1
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
    assert len(service.list_turns("concurrent-turn-replay-world", conversation.conversation_id)) == 1
