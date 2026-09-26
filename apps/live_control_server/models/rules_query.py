"""Read-only, citation-bearing Rules Lawyer query packet."""

from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator


class StrictModel(BaseModel):
    model_config = ConfigDict(extra="forbid")


class RulesQueryRequest(StrictModel):
    schema_version: Literal["dmb_rules_query_request_v1"] = "dmb_rules_query_request_v1"
    question: str = Field(min_length=1, max_length=2000)
    ruleset_id: str = Field(min_length=1, max_length=100)
    max_hits: int = Field(default=5, ge=1, le=20)

    @field_validator("question", "ruleset_id")
    @classmethod
    def strip_required(cls, value: str) -> str:
        stripped = value.strip()
        if not stripped:
            raise ValueError("must not be blank")
        return stripped


RulesQueryStatus = Literal[
    "success", "no_evidence", "insufficient_evidence",
    "rules_space_unavailable", "downstream_failure",
]


class RulesEvidenceItem(StrictModel):
    rank: int = Field(ge=1)
    entity_id: str
    assertion_id: str
    evidence_ref_id: str
    evidence_unit_id: str
    source_artifact_id: str
    source_revision_id: str | None = None
    source_uri: str | None = None
    source_locator: str | None = None
    locator: str | None = None
    source_anchor_id: str | None = None
    excerpt: str | None = None


class RulesQueryTrace(StrictModel):
    searched_revision_id: str
    search_result_digest: str | None = None
    searched_entities: int = 0
    admitted_assertions: int = 0
    returned_evidence: int = 0
    completeness: Literal["complete", "partial", "unavailable"]
    reason: str | None = None


class RulesQueryPacket(StrictModel):
    schema_version: Literal["dmb_rules_query_packet_v1"] = "dmb_rules_query_packet_v1"
    query_id: str
    ruleset_id: str
    rules_space_id: str | None = None
    rules_revision_id: str | None = None
    status: RulesQueryStatus
    evidence: list[RulesEvidenceItem] = Field(default_factory=list)
    trace: RulesQueryTrace
