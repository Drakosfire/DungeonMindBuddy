"""Create a distinct statblock for an explicitly confirmed conversation revision."""

from uuid import UUID

from pydantic import BaseModel, ConfigDict

from application_state.errors import (
    ApplicationStateConflictError,
    ApplicationStateIntegrityError,
    ApplicationStateUnavailableError,
    ApplicationStateValidationError,
)

from apps.live_control_server.integrations.dungeonmind_statblocks.client import (
    DungeonMindStatblockV1Client,
    StatblockV1Client,
)
from apps.live_control_server.integrations.dungeonmind_statblocks.definition_digest import (
    compute_definition_digest,
)
from apps.live_control_server.integrations.dungeonmind_statblocks.errors import (
    StatblockIntegrationError,
)
from apps.live_control_server.integrations.dungeonmind_statblocks.generated import (
    CreateStatblockRequestV1,
    StatblockDefinitionV1Input,
    ValidateDefinitionRequestV1,
    ValidationSeverity,
    ValidationStatus,
)
from apps.live_control_server.integrations.dungeonmind_statblocks.mechanics_locator import (
    MechanicsLocatorV1,
)


class ConversationVariantDraft(BaseModel):
    """Host-only handoff after resolving the writer's base reference."""

    model_config = ConfigDict(extra="forbid")

    base_event_id: UUID
    definition: StatblockDefinitionV1Input


class ConfirmConversationVariant(BaseModel):
    model_config = ConfigDict(extra="forbid")

    review_id: UUID


def save_variant(
    service, world_id: str, conversation_id: UUID, turn_id: UUID,
    confirmation: ConfirmConversationVariant, *, client: StatblockV1Client | None = None,
) -> MechanicsLocatorV1:
    scope = (world_id, conversation_id, turn_id)
    review = service.open_conversation_variant_review(
        *scope, review_id=confirmation.review_id,
    )
    definition = StatblockDefinitionV1Input.model_validate(review["definition"])
    digest = compute_definition_digest(definition)
    base = MechanicsLocatorV1.model_validate(review["base_locator"])
    revision = review["revision"]
    create = CreateStatblockRequestV1(
        idempotency_key=f"buddy:conversation-variant:{turn_id}:{revision}",
        definition=definition,
        change_summary="Create reviewed conversation statblock variant",
        accepted_through={
            "conversation_variant_review": str(confirmation.review_id),
            "base_mechanics": base.model_dump(mode="json"),
        },
    )

    body = create.model_dump(mode="json")
    existing = service.find_conversation_variant_save(
        *scope, revision=revision, create_request=body,
    )
    if existing is not None and existing["receipt"] is not None:
        return MechanicsLocatorV1.model_validate(existing["receipt"])

    if existing is None and service.open_conversation_draft(*scope)["revision"] != revision:
        raise ApplicationStateConflictError("Conversation draft changed. Reopen it before saving.")

    # Validation is read-only. Claiming the operation afterwards catches any
    # draft edit that committed while validation was in progress.
    owned_client = None
    try:
        if client is None:
            owned_client = client = DungeonMindStatblockV1Client()
        if existing is None:
            validation = client.validate_definition(ValidateDefinitionRequestV1(definition=definition))
            receipt = validation.validation_receipt
            if validation.definition_digest != digest or receipt.definition_digest != digest:
                raise ApplicationStateIntegrityError("Statblock validation returned different mechanics.")
            if receipt.status == ValidationStatus.invalid or any(
                issue.severity == ValidationSeverity.error for issue in receipt.issues or []
            ):
                raise ApplicationStateValidationError("Reviewed mechanics did not pass validation.")

            existing = service.claim_conversation_variant_save(
                *scope, revision=revision, create_request=body,
            )
            if existing is not None:
                return MechanicsLocatorV1.model_validate(existing)

        locator = client.create_statblock(body).locator
        if locator.statblock_id == base.statblock_id:
            raise ApplicationStateIntegrityError("Variant creation returned the original statblock.")
        if locator.definition_digest != digest:
            raise ApplicationStateIntegrityError("Saved statblock does not match reviewed mechanics.")
        service.record_conversation_variant_receipt(
            *scope, revision=revision, receipt=locator.model_dump(mode="json"),
        )
        return locator
    except StatblockIntegrationError as exc:
        raise ApplicationStateUnavailableError(
            "Statblock service could not confirm the save. Retry the same reviewed revision."
        ) from exc
    finally:
        if owned_client is not None:
            owned_client.close()
