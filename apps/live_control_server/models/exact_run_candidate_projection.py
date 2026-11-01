"""Exact candidate read model; no admitted-World authority."""

from __future__ import annotations
from typing import Literal
from pydantic import BaseModel, ConfigDict, Field
from pydantic.alias_generators import to_camel
from graph_memory.projection.node_view import GraphProjectionNodeView
from graph_memory.projection.recap_projection_contracts import RecapProjectionSourceSpan


class ReadModel(BaseModel):
    model_config = ConfigDict(
        extra="forbid", strict=True, alias_generator=to_camel, populate_by_name=True
    )


class CandidateReadEvidence(ReadModel):
    source_span_id: str
    start_line: int
    end_line: int
    paragraph_text: str
    anchor_quotes: list[str]
    can_highlight: bool


class CandidateReadNode(ReadModel):
    view_key: str
    candidate_node_id: str
    label: str
    node_type: str
    description: str
    confidence: str
    semantic_state: dict[str, str]
    warnings: list[str]
    evidence: list[CandidateReadEvidence]


class CandidateReadEdge(ReadModel):
    candidate_edge_id: str
    from_view_key: str | None
    to_view_key: str | None
    from_candidate_id: str
    to_candidate_id: str
    relationship_type: str
    label: str
    evidence: list[CandidateReadEvidence]


class SourceDisplaySegment(ReadModel):
    source_start: int
    source_end: int
    display_start: int
    display_end: int


class ExactRunCandidateProjection(ReadModel):
    schema_: Literal["dmb_exact_run_candidate_projection_v1"] = Field(
        default="dmb_exact_run_candidate_projection_v1", alias="schema"
    )
    trust_boundary: Literal["unpublished_candidate"] = "unpublished_candidate"
    run_id: str
    run_revision: int
    run_status: Literal["reviewable", "promoted"]
    profile_id: Literal["recap_category_v1@1.0", "recap_category_v2@2.0", "recap_category_encounter_job_preview@2.0"]
    source_domain: Literal["recap"] = "recap"
    source_artifact_id: str
    source_revision_id: str
    source_sha256: str
    candidate_sha256: str
    span_index_sha256: str
    campaign_id: str
    session_id: str
    managed_world_id: str
    native_world_id: str
    binding_version: int
    run_world_binding_status: Literal["frozen_verified", "source_only"]
    source_markdown: str
    narrative_markdown: str
    projected_markdown: str
    source_display_segments: list[SourceDisplaySegment]
    nodes: list[CandidateReadNode]
    edges: list[CandidateReadEdge]
    node_views: dict[str, GraphProjectionNodeView]
    source_spans: list[RecapProjectionSourceSpan]
    mentions_count: int
    unlinked_node_count: int
    beat_count: int
    diagnostics: list[str]
