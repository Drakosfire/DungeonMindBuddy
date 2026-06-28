from __future__ import annotations

from pydantic import BaseModel, ConfigDict, Field


class GraphFocusOverlay(BaseModel):
    """Projection focus metadata for rendering a scoped lens over a global graph."""

    model_config = ConfigDict(extra="allow", strict=True)

    focus_session_id: str | None = None
    focused_evidence_ref_ids: list[str] = Field(default_factory=list)
    focused_edge_ids: list[str] = Field(default_factory=list)
    focused_node_ids: list[str] = Field(default_factory=list)


class GraphProjectionEvidenceBadge(BaseModel):
    """Small display-ready source/evidence badge for projection consumers."""

    model_config = ConfigDict(extra="allow", strict=True)

    evidence_ref_id: str
    source_artifact_id: str
    source_domain: str
    evidence_role: str
    is_focus_session_evidence: bool = False
    can_open_source: bool = False
    can_highlight_span: bool = False
    label: str | None = None
    session_id: str | None = None
    source_span_ref_id: str | None = None
