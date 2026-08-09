"""Neutral durable assertion-support contract.

This model is shared by contribution merge code and union-supergraph
validation. It intentionally lives outside ``graph_memory.kernel`` so the
structural read-model validator does not depend on Kernel package imports.
"""

from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, ConfigDict, Field

ContributionAssertionKind = Literal[
    "node",
    "edge",
    "alias",
    "attribute",
    "evidence_ref",
]

AssertionSupportState = Literal[
    "supported",
    "unsupported",
    "contradicted",
    "retracted",
]


class DurableAssertionSupport(BaseModel):
    assertion_id: str
    active_contribution_ids: list[str] = Field(default_factory=list)
    superseded_contribution_ids: list[str] = Field(default_factory=list)
    retracted_contribution_ids: list[str] = Field(default_factory=list)
    contradicted_contribution_ids: list[str] = Field(default_factory=list)
    """Contribution IDs whose support was contradicted by a governed correction.

    Distinct from supersession/retraction: the source contribution itself may
    remain active for unrelated assertions while this assertion is historical.
    """
    evidence_ref_ids: list[str] = Field(default_factory=list)
    source_artifact_ids: list[str] = Field(default_factory=list)
    support_state: AssertionSupportState = "supported"
    introduced_by_contribution_id: str | None = None
    assertion_kind: ContributionAssertionKind | None = None
    graph_object_id: str | None = None
    provenance_lineage_version: Literal[1] = 1
    """Current revision-bound per-contribution provenance schema."""
    per_contribution_evidence_ref_ids: dict[str, list[str]] = Field(default_factory=dict)
    """Exact evidence lineage each active contribution asserted at merge time.

    Recorded per-contribution (not just aggregated) so projection can detect a
    contribution file mutated after publish even when the mutation only
    removes provenance-only fields (which do not change ``assertion_id``) and
    the resulting set is a trivial subset of the aggregate.
    """
    per_contribution_source_artifact_ids: dict[str, list[str]] = Field(default_factory=dict)
    """Exact source-artifact lineage each active contribution asserted at merge time."""

    model_config = ConfigDict(extra="forbid", strict=True)


__all__ = [
    "AssertionSupportState",
    "ContributionAssertionKind",
    "DurableAssertionSupport",
]
