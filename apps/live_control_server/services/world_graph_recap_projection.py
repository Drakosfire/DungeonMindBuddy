"""World Graph → Recap View projection (markdown + mention chips + node views)."""

from __future__ import annotations

import re
from pathlib import Path
from typing import Any

from apps.live_control_server.services.union_supergraph_projection_adapter import (
    load_corpus_normalized_recap_markdown,
)
from apps.live_control_server.services.world_graph_projection import (
    WorldGraphProjectionServiceError,
    project_world_graph,
)
from graph_memory.projection.focus_overlay import (
    GraphFocusOverlay,
    GraphProjectionEvidenceBadge,
)
from graph_memory.projection.node_view import (
    GraphProjectionAdjacencyCandidate,
    GraphProjectionNodeView,
    GraphProjectionSuggestedExpansion,
)
from graph_memory.projection.recap_projection import (
    RecapGraphProjection,
    RecapProjectionMention,
    splice_node_link_spans,
)
from graph_memory.projection.world_projection import (
    WorldGraphProjection,
    WorldGraphProjectionAdjacencyCandidate,
    WorldGraphProjectionDiagnostic,
    WorldGraphProjectionEvidenceBadge,
    WorldGraphProjectionNodeView,
    WorldGraphProjectionRequest,
    WorldGraphProjectionSuggestedExpansion,
)


def _adapt_relationship_direction(direction: str | None) -> str:
    if direction is None or direction == "":
        return "related"
    if direction == "outbound":
        return "outgoing"
    if direction == "inbound":
        return "incoming"
    return direction


def _adapt_evidence_badge(
    badge: WorldGraphProjectionEvidenceBadge,
) -> GraphProjectionEvidenceBadge:
    return GraphProjectionEvidenceBadge(
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


def _adapt_adjacency(
    candidate: WorldGraphProjectionAdjacencyCandidate,
) -> GraphProjectionAdjacencyCandidate:
    return GraphProjectionAdjacencyCandidate(
        edge_id=candidate.edge_id,
        node_id=candidate.node_id,
        label=candidate.label,
        kind=candidate.kind,
        predicate=candidate.predicate,
        direction=_adapt_relationship_direction(candidate.direction),
        anchored_to_focus_session=candidate.anchored_to_focus_session,
        source_domains=list(candidate.source_domains),
        evidence_ref_ids=list(candidate.evidence_ref_ids),
        edge_label=candidate.edge_label,
        session_ids=list(candidate.session_ids),
        campaign_scope=candidate.campaign_scope,
        related_summary=candidate.related_summary,
        source_excerpt=candidate.source_excerpt,
    )


def _adapt_suggested_expansion(
    candidate: WorldGraphProjectionSuggestedExpansion,
) -> GraphProjectionSuggestedExpansion:
    base = _adapt_adjacency(candidate)
    return GraphProjectionSuggestedExpansion(
        **base.model_dump(),
        rank=candidate.rank,
        rank_reason=candidate.rank_reason,
    )


def adapt_world_node_to_recap_view(
    node: WorldGraphProjectionNodeView,
) -> GraphProjectionNodeView:
    """Mirror Plan's adaptWorldGraphNodeForPlanCard for Recap GraphProjectionReader."""
    return GraphProjectionNodeView(
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


def _alias_entries_for_nodes(
    nodes: list[WorldGraphProjectionNodeView],
) -> list[tuple[str, str]]:
    """Build (alias, node_id) pairs, longest alias first for greedy matching."""
    entries: list[tuple[str, str]] = []
    seen: set[tuple[str, str]] = set()
    for node in nodes:
        candidates = [node.label, *node.aliases]
        for raw in candidates:
            alias = (raw or "").strip()
            if not alias:
                continue
            key = (alias.casefold(), node.node_id)
            if key in seen:
                continue
            seen.add(key)
            entries.append((alias, node.node_id))
    entries.sort(key=lambda item: len(item[0]), reverse=True)
    return entries


def project_world_markdown_mentions(
    markdown: str,
    nodes: list[WorldGraphProjectionNodeView],
) -> tuple[str, list[RecapProjectionMention]]:
    """Splice ``[label](dmb-node:…)`` chips from world node labels/aliases."""
    aliases = _alias_entries_for_nodes(nodes)
    occupied: list[tuple[int, int]] = []
    matches: list[tuple[int, int, str, str]] = []
    for alias, node_id in aliases:
        pattern = re.compile(rf"(?<![\w\\[]){re.escape(alias)}(?![\w\\]])", re.IGNORECASE)
        for match in pattern.finditer(markdown):
            start, end = match.span()
            if any(start < used_end and end > used_start for used_start, used_end in occupied):
                continue
            occupied.append((start, end))
            matches.append((start, end, match.group(0), node_id))

    matches.sort(key=lambda item: item[0])
    projected, offsets = splice_node_link_spans(markdown, matches)

    evidence_by_node = {node.node_id: list(node.evidence_ref_ids) for node in nodes}
    mentions: list[RecapProjectionMention] = []
    for (start, _end, label, node_id), offset in zip(matches, offsets):
        if offset is None:
            continue
        mentions.append(
            RecapProjectionMention(
                mention_id=f"mention:{node_id}:{start}",
                node_id=node_id,
                label=label,
                start_offset=offset[0],
                end_offset=offset[1],
                evidence_ref_ids=evidence_by_node.get(node_id, []),
            )
        )
    return projected, mentions


def _focus_overlay_from_world(
    projection: WorldGraphProjection,
    *,
    session_id: str,
) -> GraphFocusOverlay:
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
    return GraphFocusOverlay(
        focus_session_id=session_id,
        focused_evidence_ref_ids=focused_evidence,
        focused_edge_ids=focused_edges,
        focused_node_ids=focused_nodes,
    )


def build_world_graph_recap_projection(
    request: WorldGraphProjectionRequest,
    *,
    root: Path | None = None,
    corpus_markdown: str | None = None,
) -> RecapGraphProjection:
    """Project world head + focus-session corpus recap into Recap View payload.

    ``corpus_markdown`` may be injected for tests; otherwise loads the normalized
    corpus recap for ``(campaign_id, focus.session_id)``.
    """
    if request.focus.kind != "session" or not request.focus.session_id:
        raise WorldGraphProjectionServiceError(
            "World graph recap projection requires focus.kind=session and a session_id.",
            code="invalid_request",
            status_code=422,
            diagnostics=[
                WorldGraphProjectionDiagnostic(
                    code="invalid_request",
                    message=(
                        "World graph recap projection requires focus.kind=session "
                        "and a session_id."
                    ),
                    severity="error",
                )
            ],
        )

    session_id = request.focus.session_id
    campaign_id = request.focus.campaign_id or request.campaign_id

    world = project_world_graph(request, root=root)

    markdown = corpus_markdown
    if markdown is None:
        markdown = load_corpus_normalized_recap_markdown(
            campaign_id=campaign_id,
            session_id=session_id,
        )
    if not (markdown or "").strip():
        raise WorldGraphProjectionServiceError(
            f"Normalized recap markdown not found for {campaign_id} {session_id}.",
            code="recap_markdown_unavailable",
            status_code=404,
            diagnostics=[
                WorldGraphProjectionDiagnostic(
                    code="recap_markdown_unavailable",
                    message=(
                        f"Normalized recap markdown not found for {campaign_id} {session_id}."
                    ),
                    severity="error",
                )
            ],
        )

    projected_markdown, mentions = project_world_markdown_mentions(markdown, world.nodes)
    node_views = {
        node.node_id: adapt_world_node_to_recap_view(node) for node in world.nodes
    }

    return RecapGraphProjection(
        campaign_id=campaign_id,
        session_id=session_id,
        graph_id=world.snapshot.revision_id,
        markdown=projected_markdown,
        focus=_focus_overlay_from_world(world, session_id=session_id),
        node_views=node_views,
        mentions=mentions,
        source_spans=[],
    )


def build_world_graph_recap_projection_payload(
    request: WorldGraphProjectionRequest,
    *,
    root: Path | None = None,
    corpus_markdown: str | None = None,
) -> dict[str, Any]:
    projection = build_world_graph_recap_projection(
        request,
        root=root,
        corpus_markdown=corpus_markdown,
    )
    return projection.model_dump(mode="json")


__all__ = [
    "adapt_world_node_to_recap_view",
    "build_world_graph_recap_projection",
    "build_world_graph_recap_projection_payload",
    "project_world_markdown_mentions",
]
