"""Create a distinct statblock for an explicitly confirmed conversation revision."""

from copy import deepcopy
import json
import logging
from typing import Literal
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field

from application_state.errors import (
    ApplicationStateConflictError,
    ApplicationStateIntegrityError,
    ApplicationStateUnavailableError,
    ApplicationStateValidationError,
)

from apps.live_control_server.integrations.dungeonmind_statblocks.client import (
    DungeonMindStatblockV1Client,
    StatblockV1Client,
    verify_exact_revision_mechanics_integrity,
)
from apps.live_control_server.integrations.dungeonmind_statblocks.definition_digest import (
    compute_definition_digest,
)
from apps.live_control_server.integrations.dungeonmind_statblocks.errors import (
    StatblockIntegrationError,
)
from apps.live_control_server.integrations.dungeonmind_statblocks.generated import (
    AppendRevisionRequestV1,
    CreateStatblockRequestV1,
    StatblockDefinitionV1Input,
    ValidateDefinitionRequestV1,
    ValidationSeverity,
    ValidationStatus,
)
from apps.live_control_server.services.statblock_saved_revision import (
    admitted_portrait_bindings,
    verify_append_result,
)
from apps.live_control_server.integrations.dungeonmind_statblocks.mechanics_locator import (
    MechanicsLocatorV1,
    locator_from_exact_revision,
    same_mechanics_locator,
)


class ConversationVariantDraft(BaseModel):
    """Host-only handoff after resolving the writer's base reference."""

    model_config = ConfigDict(extra="forbid")

    base_event_id: UUID
    definition: StatblockDefinitionV1Input


class ConfirmConversationVariant(BaseModel):
    model_config = ConfigDict(extra="forbid")

    review_id: UUID


logger = logging.getLogger(__name__)


def validate_variant_review(definition, *, client=None):
    """Obtain an owner receipt before presenting generated mechanics for confirmation."""
    from .statblock_definition_validation import validate_definition

    try:
        result = validate_definition(definition=definition, client=client)
    except ValueError:
        logger.warning("Statblock owner returned a malformed validation receipt.")
        return None
    receipt = result.validation_receipt
    if receipt is None:
        logger.warning(
            "Statblock variant validation returned no receipt (category=%s).",
            result.failure_category or "missing_receipt",
        )
        return None
    if result.definition_digest != compute_definition_digest(definition) or receipt.definition_digest != result.definition_digest:
        logger.warning("Statblock validation did not match the submitted draft definition.")
        return None
    return receipt


def variant_review_is_valid(definition, receipt):
    if receipt is None:
        return False
    if receipt.definition_digest != compute_definition_digest(definition):
        raise ApplicationStateIntegrityError("Statblock validation does not bind to the draft.")
    return receipt.status != ValidationStatus.invalid and not any(
        issue.severity == ValidationSeverity.error for issue in receipt.issues or []
    )


class VariantTextReplacement(BaseModel):
    model_config = ConfigDict(extra="forbid")

    rule_key: str = Field(min_length=1)
    field: Literal["rules_text", "timing_text", "condition_text"]
    replace_exact: str = Field(min_length=1)
    with_text: str = Field(min_length=1)


class VariantNameReplacement(BaseModel):
    model_config = ConfigDict(extra="forbid")

    field: Literal["name"]
    replace_exact: str = Field(min_length=1)
    with_text: str = Field(min_length=1)


class CorrectConversationVariant(BaseModel):
    model_config = ConfigDict(extra="forbid")

    expected_revision: int = Field(gt=0)
    replacements: list[VariantTextReplacement | VariantNameReplacement] = Field(min_length=1)


def apply_variant_text_corrections(definition, replacements):
    candidate = deepcopy(definition)
    rules = {rule["key"]: rule for rule in candidate["rule_elements"]}
    visited = set()
    for edit in replacements:
        if isinstance(edit, VariantNameReplacement):
            slot = ("identity", "name")
            name = edit.with_text.strip()
            if slot in visited or not name or edit.replace_exact == name:
                raise ApplicationStateValidationError("Choose one different statblock name.")
            if candidate["identity"]["name"] != edit.replace_exact:
                raise ApplicationStateConflictError("The statblock name changed. Reopen the review.")
            candidate["identity"]["name"] = name
            visited.add(slot)
            continue
        rule = rules.get(edit.rule_key)
        slot = (edit.rule_key, edit.field)
        if rule is None or slot in visited or edit.replace_exact == edit.with_text:
            raise ApplicationStateValidationError("Choose distinct current rule fields with actual changes.")
        visited.add(slot)
        if edit.field == "rules_text":
            owner = rule
        elif edit.field == "timing_text":
            owner = rule["activation"]
        else:
            owner = rule["activation"].get("trigger") or {}
        original = owner.get(edit.field)
        offset = original.find(edit.replace_exact) if isinstance(original, str) else -1
        if offset < 0 or original.find(edit.replace_exact, offset + 1) >= 0:
            raise ApplicationStateConflictError("The correction does not match one exact rule passage.")
        owner[edit.field] = original.replace(edit.replace_exact, edit.with_text, 1)
    return StatblockDefinitionV1Input.model_validate(candidate)


def correct_variant(service, world_id, conversation_id, turn_id, review_id, correction):
    scope = (world_id, conversation_id, turn_id)
    prior = service.open_conversation_variant_review(*scope, review_id=review_id)
    if prior["revision"] != correction.expected_revision or prior["saved"]:
        raise ApplicationStateConflictError("Reopen the current unsaved review before editing.")
    candidate = apply_variant_text_corrections(prior["definition"], correction.replacements)
    receipt = validate_variant_review(candidate)
    if not variant_review_is_valid(candidate, receipt):
        raise ApplicationStateValidationError("Corrected mechanics did not pass validation.")
    from .conversation_variant_markdown import render_variant_markdown

    return service.store_conversation_variant_correction(
        *scope, review_id=review_id, expected_revision=correction.expected_revision,
        definition=candidate.model_dump(mode="json"), markdown=render_variant_markdown(candidate),
    )


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


class SaveConversationVariantPortrait(BaseModel):
    model_config = ConfigDict(extra="forbid")

    operation_id: UUID
    base: MechanicsLocatorV1
    portrait_asset_id: UUID


def prepare_variant_portrait_append(
    command: SaveConversationVariantPortrait,
    *, review_id: UUID, exact, media_owner: str,
) -> AppendRevisionRequestV1:
    """Build an art-only append from an already authorized exact source."""
    verify_exact_revision_mechanics_integrity(exact)
    if not same_mechanics_locator(locator_from_exact_revision(exact), command.base):
        raise ApplicationStateConflictError("The selected variant revision changed. Reopen it before saving.")

    return AppendRevisionRequestV1(
        idempotency_key=str(command.operation_id),
        parent_revision_id=command.base.revision_id,
        definition=StatblockDefinitionV1Input.model_validate_json(exact.canonical_definition),
        change_summary="Attach a portrait to the saved conversation variant",
        asset_bindings=admitted_portrait_bindings(exact, command.portrait_asset_id, media_owner),
        accepted_through={
            "conversation_variant_review": str(review_id),
            "buddy_variant_portrait_operation": str(command.operation_id),
            "buddy_portrait_asset_id": str(command.portrait_asset_id),
        },
    )


def save_variant_portrait(
    service, world_id, conversation_id, turn_id, *, review_id, command, media_owner,
    client: StatblockV1Client | None = None,
):
    scope = (world_id, conversation_id, turn_id)
    selection = dict(review_id=review_id, operation_id=command.operation_id)
    original, saved = service.read_variant_portrait(*scope, **selection)
    base = MechanicsLocatorV1.model_validate(original)
    if not same_mechanics_locator(base, command.base):
        raise ApplicationStateConflictError("Select the exact saved conversation variant.")
    intent = command.model_dump(mode="json")
    if saved is not None:
        if saved["intent"] != intent:
            raise ApplicationStateConflictError("This Save key belongs to a different portrait selection.")
        if saved["refusal"] is not None:
            raise ApplicationStateConflictError("The statblock has a newer revision.")
        if saved["receipt"] is not None:
            return saved["receipt"]
    owned_client = None
    try:
        if client is None:
            owned_client = client = DungeonMindStatblockV1Client()
        if saved is None:
            exact = client.get_exact_revision(base.statblock_id, base.revision_id)
            append = prepare_variant_portrait_append(
                command, review_id=review_id, exact=exact, media_owner=media_owner,
            )
            saved = service.claim_variant_portrait(
                *scope, **selection, intent=intent, append_request=append.model_dump(mode="json"),
            )
        # Claim can replay an operation that completed while media was being admitted.
        if saved["refusal"] is not None:
            raise ApplicationStateConflictError("The statblock has a newer revision.")
        if saved["receipt"] is not None:
            return saved["receipt"]

        body = saved["append_request"]
        try:
            result = client.append_revision(base.statblock_id, body)
        except StatblockIntegrationError as exc:
            if exc.status_code == 409 and exc.error_code in {"stale_parent_revision", "parent_revision_mismatch"}:
                service.settle_variant_portrait(*scope, **selection, refusal=exc.error_code)
                raise ApplicationStateConflictError("The statblock has a newer revision.") from exc
            raise
        verify_append_result(
            result, base=base, expected_digest=base.definition_digest, request_body=body,
        )
        receipt = locator_from_exact_revision(result).model_dump(mode="json")
        service.settle_variant_portrait(*scope, **selection, receipt=receipt)
        return receipt
    except StatblockIntegrationError as exc:
        raise ApplicationStateUnavailableError("Retry the same portrait Save to recover its outcome.") from exc
    finally:
        if owned_client is not None:
            owned_client.close()


def open_saved_variant(
    service, world_id: str, conversation_id: UUID, turn_id: UUID,
    *, review_id: UUID, portrait_operation_id: UUID | None = None, client: StatblockV1Client | None = None,
):
    saved = None
    if portrait_operation_id is None:
        original = service.open_saved_conversation_variant_receipt(
            world_id, conversation_id, turn_id, review_id=review_id,
        )
    else:
        original, saved = service.read_variant_portrait(
            world_id, conversation_id, turn_id, review_id=review_id, operation_id=portrait_operation_id,
        )
        if saved is None or saved["receipt"] is None:
            raise ApplicationStateConflictError("The requested portrait revision is not saved.")
    base = MechanicsLocatorV1.model_validate(original)
    locator = MechanicsLocatorV1.model_validate(saved["receipt"]) if saved else base
    owned_client = None
    try:
        if client is None:
            owned_client = client = DungeonMindStatblockV1Client()
        revision = client.get_exact_revision(locator.statblock_id, locator.revision_id)
        verify_exact_revision_mechanics_integrity(revision)
        if not same_mechanics_locator(locator_from_exact_revision(revision), locator):
            raise ApplicationStateIntegrityError("Opened statblock differs from the saved variant.")
        if saved is not None:
            verify_append_result(
                revision, base=base, expected_digest=base.definition_digest, request_body=saved["append_request"],
            )
        resource = revision.model_dump(mode="json")
        resource["definition"] = json.loads(revision.canonical_definition)
        return {"locator": locator.model_dump(mode="json"), "revision": resource}
    except StatblockIntegrationError as exc:
        raise ApplicationStateUnavailableError("Could not reopen the saved variant.") from exc
    finally:
        if owned_client is not None:
            owned_client.close()
