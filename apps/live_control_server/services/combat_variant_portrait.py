"""Resolve and adopt the exact illustrated revision of an existing Combat actor."""

from application_state.agent_conversation.service import AgentConversationService
from application_state.combat_encounters import adoption
from application_state.combat_encounters.adoption_types import ConversationPortraitPreview
from application_state.combat_encounters.types import ConversationVariantCombatSnapshot
from application_state.errors import ApplicationStateConflictError
from application_state.world_mechanics.types import MechanicsLocator

from .conversation_variant_save import open_saved_variant


def _resolve(world_id, selection):
    service = AgentConversationService()
    args = (world_id, selection.conversation_id, selection.turn_id)
    original, _operation = service.read_variant_portrait(
        *args, review_id=selection.review_id, operation_id=selection.portrait_operation_id,
    )
    opened = open_saved_variant(
        service, *args, review_id=selection.review_id,
        portrait_operation_id=selection.portrait_operation_id,
    )
    if MechanicsLocator.model_validate(opened["locator"]) != selection.locator:
        raise ApplicationStateConflictError("Portrait revision differs from the selected version")
    payload = {
        **selection.model_dump(mode="json", include={"conversation_id", "turn_id", "review_id"}),
        "origin": "conversation_variant_mechanics_v1",
        "managed_world_id": world_id,
        "locator": opened["locator"],
        "resource": opened["revision"],
    }
    snapshot = ConversationVariantCombatSnapshot(
        **payload, snapshot_digest=ConversationVariantCombatSnapshot.digest_payload(payload),
    )
    return MechanicsLocator.model_validate(original), snapshot


def preview(*, world_id, selection):
    _original, snapshot = _resolve(world_id, selection)
    return ConversationPortraitPreview(snapshot=snapshot)


def adopt(*, world_id, encounter_id, request):
    replay = adoption.inspect(
        world_id=world_id, encounter_id=encounter_id, operation_id=request.operation_id, request=request,
    )
    if replay is not None:
        return replay
    origin, snapshot = _resolve(world_id, request.source)
    return adoption.apply_verified(
        world_id=world_id, encounter_id=encounter_id, request=request, snapshot=snapshot, origin=origin,
    )
