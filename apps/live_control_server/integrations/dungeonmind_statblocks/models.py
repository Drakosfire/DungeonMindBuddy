"""Transport-envelope models for DungeonMind statblock v1 responses.

Candidate/definition/mechanics DTOs are OpenAPI-generated — import from
`apps.live_control_server.integrations.dungeonmind_statblocks.generated`.
This module keeps only Buddy-local health/readiness/exact-revision envelopes.
"""
from __future__ import annotations

from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field

from apps.live_control_server.integrations.dungeonmind_statblocks.generated import (
    GeneratedStatblockCandidateV1,
)
from apps.live_control_server.integrations.dungeonmind_statblocks.generated.models import (
    StatblockRevisionResourceV1 as GeneratedStatblockRevisionResourceV1,
)

# Published v1 identity (DungeonMindServer statblocks_v1).
ContractNameV1 = Literal["dungeonmind.dungeonbuddy-statblocks"]
ContractVersionV1 = Literal["1.0.0"]

__all__ = [
    "ContractNameV1",
    "ContractVersionV1",
    "ErrorDetailV1",
    "ErrorEnvelopeV1",
    "ExactRevisionResourceV1",
    "GeneratedStatblockCandidateV1",
    "HealthResponseV1",
    "ReadinessResponseV1",
    "StatblockIntegrationReadinessV1",
    "StrictModel",
]


class StrictModel(BaseModel):
    model_config = ConfigDict(extra="forbid")


class ErrorDetailV1(StrictModel):
    code: str
    message: str
    details: dict[str, Any] | None = None


class ErrorEnvelopeV1(StrictModel):
    error: ErrorDetailV1


class HealthResponseV1(StrictModel):
    status: str
    contract: ContractNameV1
    contract_version: ContractVersionV1
    capabilities: list[str] = Field(default_factory=list)


class ReadinessResponseV1(StrictModel):
    status: str
    contract: ContractNameV1
    generation_enabled: bool = False
    read_routes_enabled: bool = False
    errors: list[str] = Field(default_factory=list)
    detail: str | None = None


class ExactRevisionResourceV1(GeneratedStatblockRevisionResourceV1):
    """Complete published exact-revision resource used by read-only hydration.

    The generated model owns the nested statblock contract validation. Keeping
    the Buddy transport name preserves the integration boundary while avoiding
    an identity-only envelope that could mark malformed mechanics available.
    """


class StatblockIntegrationReadinessV1(StrictModel):
    schema_name: Literal["dmb_statblock_integration_readiness_v1"] = Field(
        default="dmb_statblock_integration_readiness_v1",
        alias="schema",
    )
    configured: bool
    available: bool
    downstream_status: str
    contract: ContractNameV1 | None = None
    contract_version: ContractVersionV1 | None = None
    capabilities: list[str] = Field(default_factory=list)
    diagnostics: list[str] = Field(default_factory=list)

    model_config = ConfigDict(extra="forbid", populate_by_name=True)
