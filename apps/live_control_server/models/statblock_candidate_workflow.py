"""Buddy-local candidate generation workflow models."""
from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, model_validator

from apps.live_control_server.integrations.dungeonmind_statblocks.models import (
    GeneratedStatblockCandidateV1,
)
from apps.live_control_server.models.threat_draft import ThreatDraftCandidateRefV1


class StrictModel(BaseModel):
    model_config = ConfigDict(extra="forbid")


class GenerateThreatDraftCandidateRequestV1(StrictModel):
    expected_draft_version: int = Field(ge=1)
    client_request_id: str | None = Field(default=None, min_length=1, max_length=128)


class PersistenceFailureV1(StrictModel):
    component: Literal["cache", "candidate_ref", "reconciliation"]
    category: str = Field(min_length=1, max_length=128)
    message: str = Field(min_length=1, max_length=1024)


class TerminalGenerationDispositionV1(StrictModel):
    """Buddy-local proof that one exact generation attempt is durably terminal."""

    status: Literal["terminal_failure", "terminal_expired"]
    draft_id: str = Field(min_length=1)
    source_draft_version: int = Field(ge=1)
    request_id: str = Field(min_length=1)
    request_digest: str = Field(pattern=r"^sha256:[0-9a-f]{64}$")
    scope_mode: Literal["world", "campaign"]
    world_id: str = Field(min_length=1)
    campaign_id: str | None

    model_config = ConfigDict(extra="forbid")

    @model_validator(mode="after")
    def _scope_is_coherent(self) -> TerminalGenerationDispositionV1:
        if self.scope_mode == "world" and self.campaign_id is not None:
            raise ValueError("World terminal disposition cannot name a campaign")
        if self.scope_mode == "campaign" and not self.campaign_id:
            raise ValueError("Campaign terminal disposition requires a campaign ID")
        return self


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
    terminal_disposition: TerminalGenerationDispositionV1 | None = None
    cache_status: (
        Literal[
            "stored",
            "missing",
            "partial_cache",
            "partial_ref",
            "partial_reconciliation",
            "partial_both",
            "reconciled",
        ]
        | None
    ) = None
    persistence_failures: list[PersistenceFailureV1] = Field(default_factory=list)

    model_config = ConfigDict(extra="forbid", populate_by_name=True)

    @model_validator(mode="after")
    def _terminal_proof_is_failure_only(self) -> GenerateThreatDraftCandidateResponseV1:
        if self.terminal_disposition is not None and (
            self.outcome != "failure"
            or self.candidate is not None
            or self.candidate_ref is not None
            or self.persistence_failures
        ):
            raise ValueError("terminal disposition requires a persisted failure without candidate materialization")
        return self


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
    # Present when Buddy can reverse-map the candidate to a ThreatDraft via candidate_refs.
    source_draft_id: str | None = None
    source_draft_version: int | None = Field(default=None, ge=1)
    source_draft_name: str | None = None

    model_config = ConfigDict(extra="forbid", populate_by_name=True)
