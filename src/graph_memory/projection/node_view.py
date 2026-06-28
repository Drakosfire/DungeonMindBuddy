from __future__ import annotations

from pydantic import BaseModel, ConfigDict, Field

from graph_memory.projection.focus_overlay import GraphProjectionEvidenceBadge


class GraphProjectionAdjacencyCandidate(BaseModel):
    """A projection-ready adjacent node candidate."""

    model_config = ConfigDict(extra="allow", strict=True)

    edge_id: str
    node_id: str
    label: str
    kind: str
    predicate: str
    direction: str
    anchored_to_focus_session: bool = False
    source_domains: list[str] = Field(default_factory=list)
    evidence_ref_ids: list[str] = Field(default_factory=list)


class GraphProjectionNodeView(BaseModel):
    """Projection-ready view of a global node."""

    model_config = ConfigDict(extra="allow", strict=True)

    node_id: str
    label: str
    kind: str
    role: str
    aliases: list[str] = Field(default_factory=list)
    source_domains: list[str] = Field(default_factory=list)
    evidence_badges: list[GraphProjectionEvidenceBadge] = Field(default_factory=list)
    adjacency: list[GraphProjectionAdjacencyCandidate] = Field(default_factory=list)
    anchored_to_focus_session: bool = False
    summary: str | None = None
