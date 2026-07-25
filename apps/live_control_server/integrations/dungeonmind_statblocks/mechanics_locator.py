"""Six-field mechanics locator for accepted DungeonMindServer revisions.

Maps Server create/exact-read identity onto the frozen SBW07 §12 locator shape
consumed by later acceptance orchestration. Does not assign operation-authority
or product workflow states.
"""
from __future__ import annotations

from typing import Any, Literal, Mapping

from pydantic import Field

from apps.live_control_server.integrations.dungeonmind_statblocks.errors import (
    downstream_unexpected,
)
from apps.live_control_server.integrations.dungeonmind_statblocks.generated.models import (
    CreateStatblockResponseV1,
)
from apps.live_control_server.integrations.dungeonmind_statblocks.models import (
    ContractNameV1,
    ContractVersionV1,
    ExactRevisionResourceV1,
    StrictModel,
)

PROVIDER_DUNGEONMIND: Literal["dungeonmind"] = "dungeonmind"

_STATBLOCK_ID_PATTERN = r"^sb_[a-z0-9]+$"
_REVISION_ID_PATTERN = r"^rev_[a-z0-9]+$"
_DEFINITION_DIGEST_PATTERN = r"^sha256:[0-9a-f]{64}$"

__all__ = [
    "CreateStatblockResult",
    "MechanicsLocatorV1",
    "PROVIDER_DUNGEONMIND",
    "locator_from_create_response",
    "locator_from_exact_revision",
    "same_mechanics_locator",
]


class MechanicsLocatorV1(StrictModel):
    """Exact identity of one immutable DungeonMindServer mechanics revision."""

    provider: Literal["dungeonmind"] = PROVIDER_DUNGEONMIND
    statblock_id: str = Field(pattern=_STATBLOCK_ID_PATTERN)
    revision_id: str = Field(pattern=_REVISION_ID_PATTERN)
    contract: ContractNameV1
    contract_version: ContractVersionV1
    definition_digest: str = Field(pattern=_DEFINITION_DIGEST_PATTERN)


class CreateStatblockResult(StrictModel):
    """Buddy-facing create adapter result (transport observation only)."""

    locator: MechanicsLocatorV1
    server_metadata: dict[str, Any] = Field(default_factory=dict)


def same_mechanics_locator(
    left: MechanicsLocatorV1 | Mapping[str, Any],
    right: MechanicsLocatorV1 | Mapping[str, Any],
) -> bool:
    """§12 six-field locator equality (excludes provenance / timestamps)."""

    left_fields = _locator_identity_fields(left)
    right_fields = _locator_identity_fields(right)
    return left_fields == right_fields


def locator_from_create_response(response: CreateStatblockResponseV1) -> MechanicsLocatorV1:
    """Parse create response into a strict six-field locator; fail closed."""

    statblock = response.statblock
    revision = response.revision
    if statblock.statblock_id != revision.statblock_id:
        raise downstream_unexpected(
            "create response statblock_id does not match revision.statblock_id"
        )
    if statblock.latest_revision_id != revision.revision_id:
        raise downstream_unexpected(
            "create response latest_revision_id does not match revision.revision_id"
        )
    return MechanicsLocatorV1(
        provider=PROVIDER_DUNGEONMIND,
        statblock_id=revision.statblock_id,
        revision_id=revision.revision_id,
        contract=revision.contract,  # type: ignore[arg-type]
        contract_version=revision.contract_version,  # type: ignore[arg-type]
        definition_digest=revision.definition_digest,
    )


def locator_from_exact_revision(revision: ExactRevisionResourceV1) -> MechanicsLocatorV1:
    """Map an exact-revision read onto the same six-field locator."""

    return MechanicsLocatorV1(
        provider=PROVIDER_DUNGEONMIND,
        statblock_id=revision.statblock_id,
        revision_id=revision.revision_id,
        contract=revision.contract,
        contract_version=revision.contract_version,
        definition_digest=revision.definition_digest,
    )


def _locator_identity_fields(
    value: MechanicsLocatorV1 | Mapping[str, Any],
) -> tuple[str, str, str, str, str, str]:
    if isinstance(value, MechanicsLocatorV1):
        return (
            value.provider,
            value.statblock_id,
            value.revision_id,
            value.contract,
            value.contract_version,
            value.definition_digest,
        )
    try:
        return (
            str(value["provider"]),
            str(value["statblock_id"]),
            str(value["revision_id"]),
            str(value["contract"]),
            str(value["contract_version"]),
            str(value["definition_digest"]),
        )
    except KeyError:
        raise downstream_unexpected(
            "locator identity fields incomplete for same_mechanics_locator"
        ) from None
