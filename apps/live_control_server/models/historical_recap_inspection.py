"""Read-only API model for exact historical recap source inspection."""

from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, ConfigDict, Field
from pydantic.alias_generators import to_camel

HISTORICAL_RECAP_INSPECTION_SCHEMA = "dmb_historical_recap_inspection_v1"
HistoricalRecapSourceStatus = Literal["available", "unavailable"]


class _HistoricalRecapInspectionModel(BaseModel):
    model_config = ConfigDict(
        alias_generator=to_camel,
        extra="forbid",
        populate_by_name=True,
        strict=True,
    )


class HistoricalRecapInspectionResponse(_HistoricalRecapInspectionModel):
    schema_: Literal["dmb_historical_recap_inspection_v1"] = Field(
        default=HISTORICAL_RECAP_INSPECTION_SCHEMA,
        alias="schema",
    )
    run_id: str
    run_status: str
    source_domain: str
    source_artifact_id: str
    campaign_id: str | None = None
    session_id: str | None = None
    source_status: HistoricalRecapSourceStatus
    source_uri: str | None = None
    source_sha256: str | None = None
    source_prose: str | None = None
    unavailable_reason: str | None = None
