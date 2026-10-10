"""Internal, byte-pinned semantic selection for one sealed extract proposal."""

from __future__ import annotations

from datetime import datetime
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, model_validator


class _StrictModel(BaseModel):
    model_config = ConfigDict(extra="forbid", strict=True)


class TrustedGMExtractContext(_StrictModel):
    managed_world_id: str = Field(min_length=1)
    native_world_id: str = Field(min_length=1)
    campaign_id: str = Field(min_length=1)
    expected_parent_revision_id: str = Field(min_length=1)


class SemanticAssertionDecision(_StrictModel):
    assertion_id: str = Field(min_length=1)
    disposition: Literal["accept", "reject", "defer"]


class PinnedExtractSemanticReview(_StrictModel):
    schema_version: Literal["dmb_reviewed_extract_confirmation_v1"] = (
        "dmb_reviewed_extract_confirmation_v1"
    )
    semantic_reviewer_kind: Literal["agent_steward"]
    semantic_reviewer_id: str = Field(min_length=1)
    reviewed_at: datetime
    proposal_id: str = Field(min_length=1)
    proposal_digest: str = Field(pattern=r"^[0-9a-f]{64}$")
    prepared_package_sha256: str = Field(pattern=r"^[0-9a-f]{64}$")
    source_run_id: str = Field(min_length=1)
    source_artifact_id: str = Field(min_length=1)
    source_revision_id: str = Field(min_length=1)
    source_body_sha256: str = Field(pattern=r"^[0-9a-f]{64}$")
    source_span_index_sha256: str = Field(pattern=r"^[0-9a-f]{64}$")
    candidate_graph_sha256: str = Field(pattern=r"^[0-9a-f]{64}$")
    candidate_admission_digest: str = Field(pattern=r"^[0-9a-f]{64}$")
    expected_parent_revision_id: str = Field(min_length=1)
    expected_parent_payload_sha256: str = Field(pattern=r"^[0-9a-f]{64}$")
    decisions: list[SemanticAssertionDecision] = Field(min_length=1)
    selected_assertion_ids: list[str] = Field(min_length=1)

    @model_validator(mode="after")
    def _exact_selection(self) -> PinnedExtractSemanticReview:
        if (
            self.reviewed_at.tzinfo is None
            or self.reviewed_at.utcoffset() is None
            or self.reviewed_at.utcoffset().total_seconds() != 0
        ):
            raise ValueError("actual semantic review time must be UTC")
        ids = [decision.assertion_id for decision in self.decisions]
        if ids != sorted(set(ids)):
            raise ValueError("semantic decisions must have unique sorted assertion IDs")
        selected = self.selected_assertion_ids
        if selected != sorted(set(selected)):
            raise ValueError("selected assertion IDs must be unique and sorted")
        accepted = {
            item.assertion_id for item in self.decisions if item.disposition == "accept"
        }
        if not set(selected) <= accepted:
            raise ValueError(
                "every selected assertion must have an explicit accept decision"
            )
        return self


class ReviewedExtractBinding(_StrictModel):
    """Facts embedded in the hashed Core candidate for recovery comparison."""

    artifact_sha256: str = Field(pattern=r"^[0-9a-f]{64}$")
    prepared_package_sha256: str = Field(pattern=r"^[0-9a-f]{64}$")
    semantic_reviewer_kind: Literal["agent_steward"]
    semantic_reviewer_id: str = Field(min_length=1)
    reviewed_at: datetime
    service_principal: Literal["service:buddy:reviewed-extract"]
    proposal_id: str = Field(min_length=1)
    proposal_digest: str = Field(pattern=r"^[0-9a-f]{64}$")
    source_artifact_id: str = Field(min_length=1)
    source_revision_id: str = Field(min_length=1)
    source_body_sha256: str = Field(pattern=r"^[0-9a-f]{64}$")
    source_span_index_sha256: str = Field(pattern=r"^[0-9a-f]{64}$")
    candidate_graph_sha256: str = Field(pattern=r"^[0-9a-f]{64}$")
    candidate_admission_digest: str = Field(pattern=r"^[0-9a-f]{64}$")
    expected_parent_revision_id: str = Field(min_length=1)
    expected_parent_payload_sha256: str = Field(pattern=r"^[0-9a-f]{64}$")
    selected_assertion_ids: list[str] = Field(min_length=1)
