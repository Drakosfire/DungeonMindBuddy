"""Buddy-local candidate generation workflow models."""
from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, ConfigDict, Field

from apps.live_control_server.integrations.dungeonmind_statblocks.models import (
    GeneratedStatblockCandidateV1,
)
from apps.live_control_server.models.threat_draft import ThreatDraftCandidateRefV1


class StrictModel(BaseModel):
    model_config = ConfigDict(extra="forbid")


class GenerateThreatDraftCandidateRequestV1(StrictModel):
    expected_draft_version: int = Field(ge=1)
    client_request_id: str | None = Field(default=None, min_length=1, max_length=128)


class GenerateThreatDraftCandidateResponseV1(StrictModel):
    schema_name: Literal["dmb_generate_threat_draft_candidate_response_v1"] = Field(
        default="dmb_generate_threat_draft_candidate_response_v1",
        alias="schema",
    )
    draft_id: str
    generated_from_draft_version: int
    request_id: str
    outcome: Literal["success", "failure"]
    candidate_ref: ThreatDraftCandidateRefV1 | None = None
    candidate: GeneratedStatblockCandidateV1 | None = None
    failure_category: str | None = None
    failure_message: str | None = None
    cache_status: (
        Literal["stored", "missing", "partial_cache", "partial_ref", "reconciled"] | None
    ) = None

    model_config = ConfigDict(extra="forbid", populate_by_name=True)


class ReadStatblockCandidateResponseV1(StrictModel):
    schema_name: Literal["dmb_statblock_candidate_read_v1"] = Field(
        default="dmb_statblock_candidate_read_v1",
        alias="schema",
    )
    candidate_id: str
    status: Literal["active", "expired", "unavailable", "missing"]
    candidate: GeneratedStatblockCandidateV1 | None = None
    failure_category: str | None = None
    failure_message: str | None = None

    model_config = ConfigDict(extra="forbid", populate_by_name=True)
