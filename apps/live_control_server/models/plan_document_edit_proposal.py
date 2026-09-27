"""Inert, exact-target Plan edit proposals from the Plan Agent surface."""

from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, ConfigDict, Field


class PlanEditHistoryMessage(BaseModel):
    model_config = ConfigDict(extra="forbid")

    role: Literal["user", "assistant"]
    content: str = Field(min_length=1, max_length=4000)


class PlanDocumentEditProposalRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    document_id: str = Field(min_length=1, max_length=128)
    world_id: str = Field(min_length=1, max_length=128)
    session: int = Field(ge=1)
    base_revision: int = Field(ge=1)
    base_content_sha256: str = Field(pattern=r"^[0-9a-f]{64}$")
    draft_markdown: str = Field(max_length=80_000)
    draft_sha256: str = Field(pattern=r"^[0-9a-f]{64}$")
    target_kind: Literal["replace_selection", "insert_at_caret"]
    selected_text: str = Field(max_length=8000)
    instruction: str = Field(min_length=1, max_length=4000)
    conversation_history: list[PlanEditHistoryMessage] = Field(default_factory=list, max_length=12)


class GeneratedPlanEditProposal(BaseModel):
    """Model output only; never accept target identity or write effects from it."""

    model_config = ConfigDict(extra="forbid")

    replacement_markdown: str
    summary: str
    assumptions: list[str]
    cannot_complete_reason: str | None


class PlanDocumentEditProposalResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")

    schema_version: Literal["dmb_plan_document_edit_proposal_v1"] = (
        "dmb_plan_document_edit_proposal_v1"
    )
    document_id: str
    world_id: str
    session: int
    base_revision: int
    base_content_sha256: str
    draft_sha256: str
    target_kind: Literal["replace_selection", "insert_at_caret"]
    selected_text_sha256: str
    replacement_markdown: str
    summary: str
    assumptions: list[str]
    model: str
    model_observed: bool
    model_latency_ms: int
    wall_latency_ms: int
    usage: dict[str, int | float] | None = None
