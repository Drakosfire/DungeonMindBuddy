"""Backend-neutral recap projection payload contracts (CUTOVER D.3A).

Separated from ``recap_projection`` builders so mounted gold/manual/recap
surfaces can import response models without ``graph_memory.union_supergraph``.
"""

from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, ConfigDict, Field

from graph_memory.projection.focus_overlay import GraphFocusOverlay
from graph_memory.projection.node_view import GraphProjectionNodeView


class ProjectionIdentityDiagnostic(BaseModel):
    model_config = ConfigDict(extra="forbid")

    code: str
    message: str
    count: int | None = None
    severity: Literal["info", "warning", "error"] = "info"


# Historical alias used by UnionSupergraph builders/tests.
UnionProjectionIdentityDiagnostic = ProjectionIdentityDiagnostic


class RecapProjectionSourceSpan(BaseModel):
    model_config = ConfigDict(extra="allow", strict=True)

    span_id: str
    kind: str
    ordinal: int | None = None
    text_excerpt: str | None = None
    line_start: int | None = None
    line_end: int | None = None


class RecapProjectionMention(BaseModel):
    """A mention in recap text that resolves to a global graph node."""

    model_config = ConfigDict(extra="allow", strict=True)

    mention_id: str
    node_id: str
    label: str
    start_offset: int | None = None
    end_offset: int | None = None
    evidence_ref_ids: list[str] = Field(default_factory=list)


class RecapGraphProjection(BaseModel):
    """Backend-neutral projection payload for a graph-backed recap view."""

    model_config = ConfigDict(extra="allow", strict=True)

    campaign_id: str
    session_id: str
    graph_id: str | None = None
    markdown: str | None = None
    focus: GraphFocusOverlay
    node_views: dict[str, GraphProjectionNodeView]
    mentions: list[RecapProjectionMention] = Field(default_factory=list)
    source_spans: list[RecapProjectionSourceSpan] = Field(default_factory=list)
    union_identity_diagnostics: list[ProjectionIdentityDiagnostic] = Field(
        default_factory=list
    )
    union_identity_applied_assertion_ids: list[str] = Field(default_factory=list)
