"""Transport-envelope models for DungeonMind statblock v1 responses."""
from __future__ import annotations

from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field

# Published v1 identity (DungeonMindServer statblocks_v1).
ContractNameV1 = Literal["dungeonmind.dungeonbuddy-statblocks"]
ContractVersionV1 = Literal["1.0.0"]

_STATBLOCK_ID_PATTERN = r"^sb_[a-z0-9]+$"
_REVISION_ID_PATTERN = r"^rev_[a-z0-9]+$"
_DEFINITION_DIGEST_PATTERN = r"^sha256:[0-9a-f]{64}$"


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


class ExactRevisionResourceV1(StrictModel):
    """Minimal exact-revision identity fields required by SBW01 proofs."""

    model_config = ConfigDict(extra="allow")

    statblock_id: str = Field(pattern=_STATBLOCK_ID_PATTERN)
    revision_id: str = Field(pattern=_REVISION_ID_PATTERN)
    definition_digest: str = Field(pattern=_DEFINITION_DIGEST_PATTERN)
    contract: ContractNameV1
    contract_version: ContractVersionV1
    definition: dict[str, Any] | None = None


_CANDIDATE_ID_PATTERN = r"^cand_[a-z0-9]+$"


class CandidateGenerationReceiptV1(StrictModel):
    request_id: str = Field(min_length=1, max_length=128)
    actor: str | None = None
    caller_scope: str | None = None
    generated_at: str | None = None
    input_tokens: int | None = None
    latency_ms: int | None = None
    model: str | None = None
    output_tokens: int | None = None
    prompt_version: str | None = None
    provider: str | None = None
    provider_request_id: str | None = None
    provider_response_id: str | None = None
    schema_fingerprint: str | None = None
    schema_version: str | None = None
    source_definition_digest: str | None = None
    source_description_digest: str | None = None
    source_locator: dict[str, Any] | None = None


class CandidateValidationReceiptV1(StrictModel):
    status: str = Field(min_length=1, max_length=64)
    validated_at: str = Field(min_length=1, max_length=64)
    definition_digest: str | None = None
    mode: str | None = None
    validator_version: str | None = None
    canonicalizer_version: str | None = None
    issues: list[dict[str, Any]] = Field(default_factory=list)


class GeneratedStatblockCandidateV1(StrictModel):
    """Published DungeonMind candidate envelope enforced at Buddy's trust boundary."""

    candidate_id: str = Field(pattern=_CANDIDATE_ID_PATTERN)
    contract: ContractNameV1
    contract_version: ContractVersionV1
    created_at: str = Field(min_length=1, max_length=64)
    expires_at: str | None = None
    definition: dict[str, Any]
    generation_receipt: CandidateGenerationReceiptV1
    validation_receipt: CandidateValidationReceiptV1
    assets: list[dict[str, Any]] = Field(default_factory=list)
    asset_warnings: list[dict[str, Any] | str] = Field(default_factory=list)
    asset_brief: dict[str, Any] | None = None
    source_locator: dict[str, Any] | None = None


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
