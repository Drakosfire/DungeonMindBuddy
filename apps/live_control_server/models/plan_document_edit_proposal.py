"""Inert, exact-target Plan edit proposals from the Plan Agent surface."""

from __future__ import annotations

from typing import Literal
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, model_serializer, model_validator


class PlanEditHistoryMessage(BaseModel):
    model_config = ConfigDict(extra="forbid")

    role: Literal["user", "assistant"]
    content: str = Field(min_length=1, max_length=4000)


class WorldPlanPlayableTarget(BaseModel):
    model_config = ConfigDict(extra="forbid")

    kind: Literal["scene", "beat", "choice", "option"]
    id: str = Field(pattern=r"^(scene|beat|choice|option):[a-z0-9][a-z0-9._-]{0,127}$")

    @model_validator(mode="after")
    def kind_matches_id(self):
        if self.id.split(":", 1)[0] != self.kind:
            raise ValueError("Playable target kind must match its canonical ID prefix")
        return self


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


class WorldPlanDocumentEditProposalRequest(BaseModel):
    """Proposal input for a saved World-owned Plan, without campaign/session authority."""

    model_config = ConfigDict(extra="forbid")

    idempotency_key: UUID
    document_id: str = Field(min_length=1, max_length=128)
    world_id: str = Field(min_length=1, max_length=128)
    base_revision: int = Field(ge=1)
    base_content_sha256: str = Field(pattern=r"^[0-9a-f]{64}$")
    draft_markdown: str = Field(max_length=80_000)
    draft_sha256: str = Field(pattern=r"^[0-9a-f]{64}$")
    target_kind: Literal["replace_selection", "insert_at_caret", "replace_playable_body"]
    selected_text: str = Field(max_length=8000)
    playable_target: WorldPlanPlayableTarget | None = None
    body_serialization_version: Literal["plan-playable-body-markdown-v1"] | None = None
    target_body_markdown: str | None = Field(default=None, max_length=8000)
    target_body_sha256: str | None = Field(default=None, pattern=r"^[0-9a-f]{64}$")
    instruction: str = Field(min_length=1, max_length=4000)
    conversation_history: list[PlanEditHistoryMessage] = Field(default_factory=list, max_length=12)

    @model_validator(mode="after")
    def target_fields_match_mode(self):
        if any(0xD800 <= ord(character) <= 0xDFFF for character in self.draft_markdown):
            raise ValueError("draft_markdown must contain valid Unicode scalar values")
        card_fields = (
            self.playable_target,
            self.body_serialization_version,
            self.target_body_markdown,
            self.target_body_sha256,
        )
        if self.target_kind == "replace_playable_body":
            if self.selected_text != "" or any(value is None for value in card_fields):
                raise ValueError("replace_playable_body requires an empty selection and all typed body fields")
            if self.target_body_markdown == "":
                raise ValueError("target_body_markdown must be non-empty")
            if any(0xD800 <= ord(character) <= 0xDFFF for character in self.target_body_markdown or ""):
                raise ValueError("target_body_markdown must contain valid Unicode scalar values")
        elif any(value is not None for value in card_fields):
            raise ValueError("Playable body fields are valid only for replace_playable_body")
        return self


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


class WorldPlanDocumentEditProposalResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")

    schema_version: Literal[
        "dmb_world_plan_document_edit_proposal_v1",
        "dmb_world_plan_document_edit_proposal_v2",
    ] = (
        "dmb_world_plan_document_edit_proposal_v1"
    )
    action_id: UUID
    idempotency_key: UUID
    document_id: str
    world_id: str
    base_revision: int
    base_content_sha256: str
    draft_sha256: str
    target_kind: Literal["replace_selection", "insert_at_caret", "replace_playable_body"]
    selected_text_sha256: str | None
    playable_target: WorldPlanPlayableTarget | None = None
    marker_grammar_version: Literal["v1", "v2"] | None = None
    body_scope: Literal["heading_body", "beat_direct_body", "option_item_content"] | None = None
    range_semantics_version: Literal["plan-playable-ranges-v1"] | None = None
    body_serialization_version: Literal["plan-playable-body-markdown-v1"] | None = None
    target_body_sha256: str | None = Field(default=None, pattern=r"^[0-9a-f]{64}$")
    replacement_markdown: str
    summary: str
    assumptions: list[str]
    model: str
    model_observed: bool
    model_latency_ms: int
    wall_latency_ms: int
    usage: dict[str, int | float] | None = None

    @model_validator(mode="after")
    def response_fields_match_version(self):
        card_fields = (
            self.playable_target,
            self.marker_grammar_version,
            self.body_scope,
            self.range_semantics_version,
            self.body_serialization_version,
            self.target_body_sha256,
        )
        if self.schema_version == "dmb_world_plan_document_edit_proposal_v2":
            if self.target_kind != "replace_playable_body" or self.selected_text_sha256 is not None:
                raise ValueError("schema v2 is reserved for Playable body actions")
            if any(value is None for value in card_fields):
                raise ValueError("schema v2 requires the complete typed Playable target receipt")
        elif self.target_kind == "replace_playable_body" or self.selected_text_sha256 is None or any(value is not None for value in card_fields):
            raise ValueError("schema v1 must retain the legacy selection/caret response shape")
        return self

    @model_serializer(mode="wrap")
    def serialize_legacy_shape(self, handler):
        data = handler(self)
        if self.schema_version == "dmb_world_plan_document_edit_proposal_v1":
            for field in (
                "playable_target",
                "marker_grammar_version",
                "body_scope",
                "range_semantics_version",
                "body_serialization_version",
                "target_body_sha256",
            ):
                data.pop(field, None)
        return data
