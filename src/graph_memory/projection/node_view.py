from __future__ import annotations

from pydantic import BaseModel, ConfigDict, Field

from graph_memory.projection.focus_overlay import GraphProjectionEvidenceBadge


class GraphProjectionTextHighlightSpan(BaseModel):
    """A character-offset range within ``source_excerpt`` to visually highlight."""

    model_config = ConfigDict(extra="allow", strict=True)

    start: int
    end: int


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
    edge_label: str | None = None
    session_ids: list[str] = Field(default_factory=list)
    # Effective campaign tenancy for this edge (null = world-universal).
    # Surfaced so world-lens relationship stamps can qualify sessions (C1 · S2).
    campaign_scope: str | None = None
    related_summary: str | None = None
    source_excerpt: str | None = None
    """Recap source text supporting this relationship. Resolves to the full
    source paragraph when a paragraph text index is available; otherwise
    falls back to the (often pre-abridged) evidence label."""
    source_excerpt_is_full_paragraph: bool = False
    source_excerpt_highlight_spans: list[GraphProjectionTextHighlightSpan] = Field(
        default_factory=list
    )


class GraphProjectionSuggestedExpansion(GraphProjectionAdjacencyCandidate):
    """Ranked adjacent node recommended for graph crawl / expansion."""

    rank: int = 1
    rank_reason: str = "connected thread"


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
    suggested_expansions: list[GraphProjectionSuggestedExpansion] = Field(
        default_factory=list
    )
    anchored_to_focus_session: bool = False
    summary: str | None = None
