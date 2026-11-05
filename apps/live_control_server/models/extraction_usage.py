"""Bounded public accounting; private prompts/responses are never projected."""

from typing import Literal
from pydantic import Field
from apps.live_control_server.models.saved_recap_runs import SavedRecapRun
from pydantic import BaseModel


class UsageMetrics(BaseModel):
    model_config = SavedRecapRun.model_config
    input_tokens: int | None = Field(default=None, ge=0)
    output_tokens: int | None = Field(default=None, ge=0)
    cached_input_tokens: int | None = Field(default=None, ge=0)
    reasoning_tokens: int | None = Field(default=None, ge=0)
    total_tokens: int | None = Field(default=None, ge=0)
    known_input_tokens: int | None = Field(default=None, ge=0)
    known_output_tokens: int | None = Field(default=None, ge=0)
    provider_attempts: int | None = Field(default=None, ge=0)
    cost_usd: float | None = Field(default=None, ge=0, allow_inf_nan=False)
    known_cost_usd: float | None = Field(default=None, ge=0, allow_inf_nan=False)
    cost_status: Literal["reported", "partial", "unavailable", "not_dispatched"] = (
        "unavailable"
    )
    pricing_source: str | None = None


class PassUsage(UsageMetrics):
    pass_name: str


class ExtractionUsageResponse(BaseModel):
    model_config = SavedRecapRun.model_config
    schema_: Literal["dmb_extraction_usage_v1"] = Field(
        default="dmb_extraction_usage_v1", alias="schema"
    )
    managed_world_id: str
    run_id: str
    run_revision: int
    currency: Literal["USD"] = "USD"
    totals: UsageMetrics
    passes: list[PassUsage]
