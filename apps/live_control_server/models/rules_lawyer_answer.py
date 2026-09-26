"""Validated answer and its exact retrieval witness."""

from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, ConfigDict, Field

from apps.live_control_server.models.rules_query import RulesQueryPacket


class RulesAnswer(BaseModel):
    model_config = ConfigDict(extra="forbid")

    status: Literal["supported", "insufficient_evidence", "unavailable"]
    answer: str | None = None
    citation_evidence_ref_ids: list[str] = Field(default_factory=list)
    needs_more_evidence: bool = False
    reason: str | None = None
    generation_trace_id: str | None = None


class RulesAnswerResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")

    schema_version: Literal["dmb_rules_answer_response_v1"] = "dmb_rules_answer_response_v1"
    packet: RulesQueryPacket
    answer: RulesAnswer
