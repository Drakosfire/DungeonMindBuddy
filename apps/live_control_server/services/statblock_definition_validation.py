"""SBW05a: authoritative definition validation via DungeonMindServer."""
from __future__ import annotations

from typing import Any, Literal

from pydantic import ConfigDict, Field

from apps.live_control_server.integrations.dungeonmind_statblocks.client import (
    DungeonMindStatblockV1Client,
    StatblockV1Client,
)
from apps.live_control_server.integrations.dungeonmind_statblocks.errors import (
    StatblockIntegrationError,
)
from apps.live_control_server.integrations.dungeonmind_statblocks.generated import (
    StatblockDefinitionV1Input,
    ValidateDefinitionRequestV1,
    ValidationResponseV1,
)
from apps.live_control_server.models.statblock_candidate_workflow import StrictModel


class ValidateDefinitionBuddyRequestV1(StrictModel):
    definition: dict[str, Any] | StatblockDefinitionV1Input


class ValidateDefinitionBuddyResponseV1(StrictModel):
    schema_name: Literal["dmb_statblock_definition_validation_v1"] = Field(
        default="dmb_statblock_definition_validation_v1",
        alias="schema",
    )
    outcome: Literal["success", "failure"]
    definition_digest: str | None = None
    validation_receipt: dict[str, Any] | None = None
    failure_category: str | None = None
    failure_message: str | None = None

    model_config = ConfigDict(extra="forbid", populate_by_name=True)


def associate_validation_digest(response: ValidationResponseV1) -> str:
    """Return the digest that must bind editor eligibility to this receipt."""
    digest = response.definition_digest
    receipt_digest = response.validation_receipt.definition_digest
    if digest != receipt_digest:
        raise ValueError("validation digest mismatch between response and receipt")
    return digest


def validate_definition(
    *,
    definition: dict[str, Any] | StatblockDefinitionV1Input,
    client: StatblockV1Client | None = None,
) -> ValidateDefinitionBuddyResponseV1:
    """Submit an exact complete definition to Server validate; no local mechanics rules."""
    typed = (
        definition
        if isinstance(definition, StatblockDefinitionV1Input)
        else StatblockDefinitionV1Input.model_validate(definition)
    )
    request = ValidateDefinitionRequestV1(definition=typed)
    active = client or DungeonMindStatblockV1Client()
    owns = client is None
    try:
        downstream = active.validate_definition(request)
        digest = associate_validation_digest(downstream)
        return ValidateDefinitionBuddyResponseV1(
            outcome="success",
            definition_digest=digest,
            validation_receipt=downstream.validation_receipt.model_dump(
                mode="json", by_alias=True
            ),
        )
    except StatblockIntegrationError as exc:
        return ValidateDefinitionBuddyResponseV1(
            outcome="failure",
            failure_category=exc.category,
            failure_message=exc.message,
        )
    finally:
        if owns and hasattr(active, "close"):
            active.close()
