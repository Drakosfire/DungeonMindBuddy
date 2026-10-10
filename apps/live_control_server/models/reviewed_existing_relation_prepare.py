"""Internal inputs for reviewed, existing-endpoint relation preparation.

These are not transport models. Only a trusted GM execution path may construct
the context; the semantic review remains a separate pinned artifact.
"""

from __future__ import annotations

from datetime import datetime
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, model_validator


class _StrictModel(BaseModel):
    model_config = ConfigDict(extra="forbid", strict=True)


class TrustedGMRelationContext(_StrictModel):
    buddy_world_id: str = Field(min_length=1)
    native_world_id: str = Field(min_length=1)
    campaign_id: str = Field(min_length=1)
    service_principal: Literal["service:buddy:reviewed-relations"]
    expected_parent_revision_id: str = Field(min_length=1)
    expected_parent_payload_sha256: str = Field(pattern=r"^[0-9a-f]{64}$")


class ReviewedExistingRelation(_StrictModel):
    candidate_edge_id: str = Field(min_length=1)
    relationship_id: str = Field(min_length=1)
    subject_object_id: str = Field(min_length=1)
    subject_kind: str = Field(min_length=1)
    qualified_predicate: str = Field(min_length=1)
    object_object_id: str = Field(min_length=1)
    object_kind: str = Field(min_length=1)
    source_span_ids: list[str] = Field(min_length=1)
    semantic_rationale: str = Field(min_length=1)

    @model_validator(mode="after")
    def _unique_spans(self) -> ReviewedExistingRelation:
        if len(self.source_span_ids) != len(set(self.source_span_ids)):
            raise ValueError("reviewed relation source spans must be unique")
        return self


class PinnedExistingRelationReview(_StrictModel):
    schema_version: Literal["dmb_reviewed_existing_relation_prepare_v1"] = (
        "dmb_reviewed_existing_relation_prepare_v1"
    )
    buddy_world_id: str = Field(min_length=1)
    native_world_id: str = Field(min_length=1)
    campaign_id: str = Field(min_length=1)
    source_run_id: str = Field(min_length=1)
    source_artifact_id: str = Field(min_length=1)
    source_revision_id: str = Field(min_length=1)
    source_body_sha256: str = Field(pattern=r"^[0-9a-f]{64}$")
    source_span_index_sha256: str = Field(pattern=r"^[0-9a-f]{64}$")
    candidate_graph_sha256: str = Field(pattern=r"^[0-9a-f]{64}$")
    expected_parent_revision_id: str = Field(min_length=1)
    expected_parent_payload_sha256: str = Field(pattern=r"^[0-9a-f]{64}$")
    semantic_reviewer_kind: Literal["agent_steward"]
    semantic_reviewer_id: str = Field(min_length=1)
    reviewed_at: datetime
    relations: list[ReviewedExistingRelation] = Field(min_length=1)
    review_sha256: str = Field(pattern=r"^[0-9a-f]{64}$")

    @model_validator(mode="after")
    def _review_shape(self) -> PinnedExistingRelationReview:
        if self.reviewed_at.tzinfo is None or self.reviewed_at.utcoffset() is None:
            raise ValueError("semantic review time must be timezone-aware")
        for field in ("candidate_edge_id", "relationship_id"):
            values = [getattr(relation, field) for relation in self.relations]
            if len(values) != len(set(values)):
                raise ValueError(f"reviewed relation {field} values must be unique")
        return self
