"""Typed Graph Kernel contribution models (PR005)."""

from __future__ import annotations

from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field

from graph_memory.evidence.assertion_support import (
    ContributionAssertionKind,
)

ContributionStatus = Literal[
    "active",
    "superseded",
    "retracted",
    "failed",
]

ContributionAssertionStatus = Literal[
    "candidate",
    "accepted",
    "rejected",
    "ambiguous_identity",
    "blocked_collision",
    "superseded",
    "retracted",
]

ContributionSourceKind = Literal[
    "source_extraction",
    "standing_context",
    "graph_review_authored_assertion",
    "identity_decision",
    "manual_import",
]

class _ContributionModel(BaseModel):
    model_config = ConfigDict(extra="forbid", strict=True)


class ContributionIdentityMention(_ContributionModel):
    """Unresolved / ambiguous / blocked identity mention retained at contribution level."""

    mention_id: str
    label: str
    object_kind: str
    aliases: list[str] = Field(default_factory=list)
    evidence_ref_ids: list[str] = Field(default_factory=list)
    identity_resolution_outcome: str
    diagnostics: list[str] = Field(default_factory=list)
    candidate_node_ids: list[str] = Field(default_factory=list)


class GraphContributionAssertion(_ContributionModel):
    assertion_id: str
    assertion_kind: ContributionAssertionKind
    subject_node_id: str | None = None
    target_node_id: str | None = None
    predicate: str | None = None
    label: str | None = None
    value: dict[str, Any] = Field(default_factory=dict)
    evidence_ref_ids: list[str] = Field(default_factory=list)
    source_artifact_id: str | None = None
    source_revision_id: str | None = None
    campaign_scope: str | None = None
    temporal_scope: dict[str, Any] | None = None
    visibility: str | None = None
    epistemic_kind: str | None = None
    acceptance_state: ContributionAssertionStatus
    identity_resolution_outcome: str | None = None
    contribution_id: str


class GraphContribution(_ContributionModel):
    contribution_id: str
    world_id: str
    source_kind: ContributionSourceKind
    source_artifact_id: str | None = None
    source_revision_id: str | None = None
    extraction_profile: str | None = None
    produced_at: str
    campaign_scope: str | None = None
    status: ContributionStatus = "active"
    supersedes_contribution_id: str | None = None
    candidate_assertions: list[GraphContributionAssertion] = Field(default_factory=list)
    accepted_assertions: list[GraphContributionAssertion] = Field(default_factory=list)
    rejected_assertions: list[GraphContributionAssertion] = Field(default_factory=list)
    unresolved_mentions: list[ContributionIdentityMention] = Field(default_factory=list)
    identity_decision_ids: list[str] = Field(default_factory=list)
    authored_by: str | None = None
    diagnostics: list[str] = Field(default_factory=list)


class ContributionMergeResult(_ContributionModel):
    world_id: str
    parent_revision_id: str | None = None
    revision_id: str | None = None
    contribution_ids: list[str] = Field(default_factory=list)
    accepted_assertion_ids: list[str] = Field(default_factory=list)
    rejected_assertion_ids: list[str] = Field(default_factory=list)
    retracted_assertion_ids: list[str] = Field(default_factory=list)
    superseded_contribution_ids: list[str] = Field(default_factory=list)
    diagnostics: list[str] = Field(default_factory=list)
    published: bool = False


class ContributionIntegrityReport(_ContributionModel):
    world_id: str
    head_revision_id: str | None = None
    contribution_count: int = 0
    active_contribution_count: int = 0
    superseded_contribution_count: int = 0
    retracted_contribution_count: int = 0
    failed_contribution_ids: list[str] = Field(default_factory=list)
    unsupported_assertion_ids: list[str] = Field(default_factory=list)
    assertion_introduced_by: dict[str, str] = Field(default_factory=dict)
    assertion_active_support: dict[str, list[str]] = Field(default_factory=dict)
    rebuild_equivalent_to_head: bool | None = None
    diagnostics: list[str] = Field(default_factory=list)
