"""Seed frozen synthetic dialogue only in the current owned App clone."""
from uuid import UUID, uuid4

from .fixture_binding import verify_preflight_snapshot
from .owned_db_fixture import checked_owned_dsn


def seed_dialogue(fixture, *, world, template, snapshot):
    """Create a fresh synthetic conversation using the conversation owner.

    Page provisioning and ownership of the synthetic World remain caller
    prerequisites. A partially failed seed is retained for inspection; it is
    never automatically retried or reset.
    """
    from application_state.agent_conversation import AgentConversationService
    from application_state.agent_conversation.types import (
        ConversationCommand, HistoricalReference, SubmittedGraphRequestIntentV1,
        SubmittedPrimaryWorkIntentV1, SubmittedTurnIntentV1, TurnProvenance,
        TurnResult, TurnSubmission,
    )

    prefix = "negative-seed-"
    if not isinstance(world, str) or not world.startswith(prefix):
        raise ValueError("A uniquely named synthetic World is required")
    try:
        if UUID(world[len(prefix):]).hex != world[len(prefix):]:
            raise ValueError
    except (ValueError, AttributeError):
        raise ValueError("A uniquely named synthetic World is required") from None
    history = fixture.get("history")
    if (not isinstance(history, list) or len(history) > 12 or len(history) % 2
            or any(not isinstance(row, dict) or set(row) != {"role", "content"}
                   or row["role"] != ("user" if i % 2 == 0 else "assistant")
                   or not isinstance(row["content"], str) or not row["content"].strip()
                   for i, row in enumerate(history))):
        raise ValueError("Synthetic history must contain complete nonblank dialogue pairs")
    verify_preflight_snapshot(fixture, template, world, snapshot)
    checked_owned_dsn()
    service = AgentConversationService()
    pointer = service.get_world_pointer(world)
    if pointer.revision != 0 or pointer.active_conversation_id is not None:
        raise ValueError("Synthetic World already has conversation state")
    conversation = service.new_conversation(ConversationCommand(
        world_id=world, command_id=uuid4(), expected_pointer_revision=0,
        expected_active_conversation_id=None))
    page = template["primary_work"]
    provenance = TurnProvenance(
        world_id=world, surface_resolution="resolved", surface_id="build",
        surface_instance_id=page["object_id"],
        primary_work=HistoricalReference(resolution="resolved", kind="build", object_id=page["object_id"],
                                         revision=str(page["expected_revision"]),
                                         content_sha256=page["expected_content_sha256"]),
        selected_object=HistoricalReference(resolution="absent"))
    for index in range(0, len(history), 2):
        user, assistant = history[index]["content"], history[index + 1]["content"]
        active = service.get_conversation(world, conversation.conversation_id)
        intent = SubmittedTurnIntentV1(
            world_id=world, client_thread_id="synthetic-seed", message=user, surface_id="build",
            surface_instance_id=page["object_id"], client_work_state="saved_clean",
            primary_work=SubmittedPrimaryWorkIntentV1(kind="build", object_id=page["object_id"],
                expected_revision=page["expected_revision"], expected_content_sha256=page["expected_content_sha256"]),
            graph_request=SubmittedGraphRequestIntentV1(mode="none"), graph_selection=None)
        accepted = service.accept_turn(TurnSubmission(
            world_id=world, conversation_id=conversation.conversation_id, idempotency_key=uuid4(),
            expected_conversation_revision=active.revision, user_text=user, provenance=provenance,
            submitted_intent_v1=intent))
        running = service.begin_turn(world, conversation.conversation_id, accepted.turn_id,
                                     expected_revision=accepted.revision)
        service.complete_turn(TurnResult(world_id=world, conversation_id=conversation.conversation_id,
            turn_id=accepted.turn_id, expected_revision=running.revision, assistant_text=assistant))
    dialogue = service.list_build_dialogue(world, conversation.conversation_id)
    if [(row["user"], row["assistant"]) for row in dialogue] != [
            (history[i]["content"], history[i + 1]["content"]) for i in range(0, len(history), 2)]:
        raise ValueError("Seeded dialogue did not round-trip through the Build owner")
    return conversation.conversation_id
