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
    evidence_ref_ids: list[str] = Field(default_factory=list)
    source_artifact_ids: list[str] = Field(default_factory=list)
    support_state: AssertionSupportState = "supported"
    introduced_by_contribution_id: str | None = None
    assertion_kind: ContributionAssertionKind | None = None
    graph_object_id: str | None = None

    model_config = ConfigDict(extra="forbid", strict=True)


__all__ = [
    "AssertionSupportState",
    "ContributionAssertionKind",
    "DurableAssertionSupport",
]
