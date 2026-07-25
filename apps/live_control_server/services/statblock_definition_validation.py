"""SBW05a: authoritative definition validation via DungeonMindServer."""
from __future__ import annotations

from typing import Literal

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
    ValidationReceiptV1,
    ValidationResponseV1,
)
from apps.live_control_server.models.statblock_candidate_workflow import StrictModel


class ValidateDefinitionBuddyRequestV1(StrictModel):
    definition: StatblockDefinitionV1Input


class ValidateDefinitionBuddyResponseV1(StrictModel):
    schema_name: Literal["dmb_statblock_definition_validation_v1"] = Field(
        default="dmb_statblock_definition_validation_v1",
        alias="schema",
    )
    outcome: Literal["success", "failure"]
    definition_digest: str | None = None
    validation_receipt: ValidationReceiptV1 | None = None
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
    definition: StatblockDefinitionV1Input,
    client: StatblockV1Client | None = None,
) -> ValidateDefinitionBuddyResponseV1:
    """Submit an exact complete definition to Server validate; no local mechanics rules."""
    request = ValidateDefinitionRequestV1(definition=definition)
    owns = False
    active: StatblockV1Client | None = client
    try:
        # Construct inside the try: DungeonMindStatblockV1Client() can raise
        # integration_misconfigured before any network call.
        if active is None:
            active = DungeonMindStatblockV1Client()
            owns = True
        downstream = active.validate_definition(request)
        digest = associate_validation_digest(downstream)
        return ValidateDefinitionBuddyResponseV1(
            outcome="success",
            definition_digest=digest,
            validation_receipt=downstream.validation_receipt,
        )
    except StatblockIntegrationError as exc:
        return ValidateDefinitionBuddyResponseV1(
            outcome="failure",
            failure_category=exc.category,
            failure_message=exc.message,
        )
    finally:
        if owns and active is not None and hasattr(active, "close"):
            active.close()
