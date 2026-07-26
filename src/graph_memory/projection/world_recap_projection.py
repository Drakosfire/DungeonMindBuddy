"""World Graph → focus-session recap projection contracts (PR380A / PR #412).

Pure models and deterministic mention/adaptation helpers. No corpus I/O, no
registry enrichment, no world-scope widening, no synthetic graph facts.
"""

from __future__ import annotations

from typing import Literal

from pydantic import Field

from graph_memory.projection.markdown_mentions import (
    AMBIGUOUS_MENTION_DIAGNOSTIC,
    MentionBinding,
    project_markdown_mentions,
)
from graph_memory.projection.world_projection import (
    WorldGraphProjection,
    WorldGraphProjectionAdjacencyCandidate,
    WorldGraphProjectionDiagnostic,
    WorldGraphProjectionEvidenceBadge,
    WorldGraphProjectionNodeView,
    WorldGraphProjectionSnapshot,
    WorldGraphProjectionSuggestedExpansion,
    WorldGraphProjectionTextHighlightSpan,
    WorldGraphProjectionTrustBoundary,
    _ProjectionModel,
)

RECAP_PROJECTION_RESPONSE_SCHEMA = "dmb_world_graph_recap_projection_v1"


class WorldGraphRecapFocusOverlay(_ProjectionModel):
    focus_session_id: str | None = None
    focused_evidence_ref_ids: list[str] = Field(default_factory=list)
    focused_edge_ids: list[str] = Field(default_factory=list)
    focused_node_ids: list[str] = Field(default_factory=list)


class WorldGraphRecapEvidenceBadge(_ProjectionModel):
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


class WorldGraphRecapTextHighlightSpan(_ProjectionModel):
    start: int
    end: int


class WorldGraphRecapAdjacencyCandidate(_ProjectionModel):
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
    campaign_scope: str | None = None
    related_summary: str | None = None
    source_excerpt: str | None = None
    source_excerpt_is_full_paragraph: bool = False
    source_excerpt_highlight_spans: list[WorldGraphRecapTextHighlightSpan] = Field(
        default_factory=list
    )


class WorldGraphRecapSuggestedExpansion(WorldGraphRecapAdjacencyCandidate):
    rank: int = 1
    rank_reason: str = "connected thread"


class WorldGraphRecapNodeView(_ProjectionModel):
    node_id: str
    label: str
    kind: str
    role: str
    aliases: list[str] = Field(default_factory=list)
    source_domains: list[str] = Field(default_factory=list)
    evidence_badges: list[WorldGraphRecapEvidenceBadge] = Field(default_factory=list)
    adjacency: list[WorldGraphRecapAdjacencyCandidate] = Field(default_factory=list)
    suggested_expansions: list[WorldGraphRecapSuggestedExpansion] = Field(
        default_factory=list
    )
    anchored_to_focus_session: bool = False
    summary: str | None = None
    campaign_scope: str | None = None


class WorldGraphRecapMention(_ProjectionModel):
    mention_id: str
    node_id: str
    label: str
    start_offset: int | None = None
    end_offset: int | None = None
    # v1 mentions are navigation-only; never copy graph evidence authority.
    evidence_ref_ids: list[str] = Field(default_factory=list)


class WorldGraphRecapSourceSpan(_ProjectionModel):
    """Placeholder span shape; v1 always returns an empty list."""

    span_id: str
    source_artifact_id: str | None = None
    text_excerpt: str | None = None


class WorldGraphRecapProjection(_ProjectionModel):
    schema_: Literal["dmb_world_graph_recap_projection_v1"] = Field(
        alias="schema",
        default=RECAP_PROJECTION_RESPONSE_SCHEMA,
    )
    campaign_id: str
    session_id: str
    graph_id: str
    snapshot: WorldGraphProjectionSnapshot
    markdown: str
    focus: WorldGraphRecapFocusOverlay
    node_views: dict[str, WorldGraphRecapNodeView] = Field(default_factory=dict)
    mentions: list[WorldGraphRecapMention] = Field(default_factory=list)
    source_spans: list[WorldGraphRecapSourceSpan] = Field(default_factory=list)
    diagnostics: list[WorldGraphProjectionDiagnostic] = Field(default_factory=list)
    trust_boundary: WorldGraphProjectionTrustBoundary


def adapt_relationship_direction(direction: str | None) -> str:
    if direction is None or direction == "":
        return "related"
    if direction == "outbound":
        return "outgoing"
    if direction == "inbound":
        return "incoming"
    return direction


def _adapt_evidence_badge(
    badge: WorldGraphProjectionEvidenceBadge,
) -> WorldGraphRecapEvidenceBadge:
    return WorldGraphRecapEvidenceBadge(
        evidence_ref_id=badge.evidence_ref_id,
        source_artifact_id=badge.source_artifact_id,
        source_domain=badge.source_domain,
        evidence_role=badge.evidence_role,
        is_focus_session_evidence=badge.is_focus_session_evidence,
        can_open_source=badge.can_open_source,
        can_highlight_span=badge.can_highlight_span,
        label=badge.label,
        session_id=badge.session_id,
        source_span_ref_id=badge.source_span_ref_id,
    )


def _adapt_highlight_spans(
    spans: list[WorldGraphProjectionTextHighlightSpan],
) -> list[WorldGraphRecapTextHighlightSpan]:
    return [
        WorldGraphRecapTextHighlightSpan(start=span.start, end=span.end)
        for span in spans
    ]


def _adapt_adjacency(
    candidate: WorldGraphProjectionAdjacencyCandidate,
) -> WorldGraphRecapAdjacencyCandidate:
    return WorldGraphRecapAdjacencyCandidate(
        edge_id=candidate.edge_id,
        node_id=candidate.node_id,
        label=candidate.label,
        kind=candidate.kind,
        predicate=candidate.predicate,
        direction=adapt_relationship_direction(candidate.direction),
        anchored_to_focus_session=candidate.anchored_to_focus_session,
        source_domains=list(candidate.source_domains),
        evidence_ref_ids=list(candidate.evidence_ref_ids),
        edge_label=candidate.edge_label,
        session_ids=list(candidate.session_ids),
        campaign_scope=candidate.campaign_scope,
        related_summary=candidate.related_summary,
        source_excerpt=candidate.source_excerpt,
        source_excerpt_is_full_paragraph=candidate.source_excerpt_is_full_paragraph,
        source_excerpt_highlight_spans=_adapt_highlight_spans(
            list(candidate.source_excerpt_highlight_spans)
        ),
    )


def _adapt_suggested_expansion(
    candidate: WorldGraphProjectionSuggestedExpansion,
) -> WorldGraphRecapSuggestedExpansion:
    base = _adapt_adjacency(candidate)
    return WorldGraphRecapSuggestedExpansion(
        **base.model_dump(),
        rank=candidate.rank,
        rank_reason=candidate.rank_reason,
    )


def adapt_world_node_to_recap_view(
    node: WorldGraphProjectionNodeView,
) -> WorldGraphRecapNodeView:
    """Exact field adaptation for recap presentation; no invented graph facts."""
    return WorldGraphRecapNodeView(
        node_id=node.node_id,
        label=node.label,
        kind=node.kind,
        role=node.role,
        aliases=list(node.aliases),
        source_domains=list(node.source_domains),
        evidence_badges=[_adapt_evidence_badge(b) for b in node.evidence_badges],
        adjacency=[_adapt_adjacency(a) for a in node.adjacency],
        suggested_expansions=[
            _adapt_suggested_expansion(s) for s in node.suggested_expansions
        ],
        anchored_to_focus_session=node.anchored_to_focus_session,
        summary=node.summary,
        campaign_scope=node.campaign_scope,
    )


def focus_overlay_from_world(
    projection: WorldGraphProjection,
    *,
    session_id: str,
) -> WorldGraphRecapFocusOverlay:
    focused_evidence = sorted(
        evidence.evidence_ref_id
        for evidence in projection.evidence
        if evidence.session_id == session_id
    )
    focused_edges = sorted(
        rel.edge_id
        for rel in projection.relationships
        if session_id in rel.session_ids
    )
    focused_nodes = sorted(
        node.node_id for node in projection.nodes if node.anchored_to_focus_session
    )
    return WorldGraphRecapFocusOverlay(
        focus_session_id=session_id,
        focused_evidence_ref_ids=focused_evidence,
        focused_edge_ids=focused_edges,
        focused_node_ids=focused_nodes,
    )


def recap_projection_trust_boundary() -> WorldGraphProjectionTrustBoundary:
    return WorldGraphProjectionTrustBoundary(
        can_trust=[
            "snapshot identifies the exact graph read",
            "node_views and graph mention targets come from that snapshot",
            "markdown body comes from the requested canonical normalized recap",
            "graph_id equals snapshot.revision_id",
        ],
        cannot_trust=[
            "mention spans are evidence bindings",
            "source highlighting is available",
            "absent nodes were searched in other campaigns or world scope",
            "label/alias coverage is semantically complete",
            "recap prose has been promoted merely because it is displayed beside graph nodes",
        ],
    )


def project_world_markdown_mentions(
    markdown: str,
    nodes: list[WorldGraphProjectionNodeView],
) -> tuple[str, list[WorldGraphRecapMention], list[WorldGraphProjectionDiagnostic]]:
    """Splice unique label/alias surfaces into ``dmb-node:`` links.

    Thin recap adapter over :func:`project_markdown_mentions`. Binding order is
    the contract: surfaces are emitted in node-iteration order, label before
    aliases, with duplicates preserved, because the neutral linker quotes the
    first matching surface (original casing) in its ambiguity diagnostic.
    """
    bindings = [
        MentionBinding(surface=raw or "", node_id=node.node_id)
        for node in nodes
        for raw in (node.label, *node.aliases)
    ]
    projected, mentions, diagnostics = project_markdown_mentions(markdown, bindings)
    return (
        projected,
        [
            WorldGraphRecapMention(
                mention_id=mention.mention_id,
                node_id=mention.node_id,
                label=mention.label,
                start_offset=mention.start_offset,
                end_offset=mention.end_offset,
                evidence_ref_ids=[],
            )
            for mention in mentions
        ],
        [
            WorldGraphProjectionDiagnostic(
                code=diagnostic.code,
                message=diagnostic.message,
                severity=diagnostic.severity,
            )
            for diagnostic in diagnostics
        ],
    )


__all__ = [
    "AMBIGUOUS_MENTION_DIAGNOSTIC",
    "RECAP_PROJECTION_RESPONSE_SCHEMA",
    "WorldGraphRecapFocusOverlay",
    "WorldGraphRecapMention",
    "WorldGraphRecapNodeView",
    "WorldGraphRecapProjection",
    "WorldGraphRecapSourceSpan",
    "adapt_relationship_direction",
    "adapt_world_node_to_recap_view",
    "focus_overlay_from_world",
    "project_world_markdown_mentions",
    "recap_projection_trust_boundary",
]
