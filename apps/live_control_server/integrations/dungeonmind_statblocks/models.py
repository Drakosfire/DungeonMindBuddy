"""Transport-envelope models for DungeonMind statblock v1 responses."""
from __future__ import annotations

from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field


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
    contract: str
    contract_version: str
    capabilities: list[str] = Field(default_factory=list)


class ReadinessResponseV1(StrictModel):
    status: str
    contract: str
    generation_enabled: bool = False
    read_routes_enabled: bool = False
    errors: list[str] = Field(default_factory=list)
    detail: str | None = None


class ExactRevisionResourceV1(StrictModel):
    """Minimal exact-revision identity fields required by SBW01 proofs."""

    model_config = ConfigDict(extra="allow")

    statblock_id: str
    revision_id: str
    definition_digest: str
    contract: str | None = None
    contract_version: str | None = None
    definition: dict[str, Any] | None = None


class StatblockIntegrationReadinessV1(StrictModel):
    schema_name: Literal["dmb_statblock_integration_readiness_v1"] = Field(
        default="dmb_statblock_integration_readiness_v1",
        alias="schema",
    )
    configured: bool
    available: bool
    downstream_status: str
    contract: str | None = None
    contract_version: str | None = None
    capabilities: list[str] = Field(default_factory=list)
    diagnostics: list[str] = Field(default_factory=list)

    model_config = ConfigDict(extra="forbid", populate_by_name=True)
