from __future__ import annotations

from pydantic import BaseModel, ConfigDict, Field

from graph_memory.projection.focus_overlay import (
    GraphFocusOverlay,
    GraphProjectionEvidenceBadge,
)
from graph_memory.projection.node_view import (
    GraphProjectionAdjacencyCandidate,
    GraphProjectionNodeView,
)
from graph_memory.union_supergraph.model import UnionSupergraphStore


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
    focus: GraphFocusOverlay
    node_views: dict[str, GraphProjectionNodeView]
    mentions: list[RecapProjectionMention] = Field(default_factory=list)


def build_focus_overlay(
    store: UnionSupergraphStore,
    focus_session_id: str | None = None,
) -> GraphFocusOverlay:
    """Build deterministic focus metadata from a union-supergraph store."""

    resolved_focus_session_id = (
        focus_session_id if focus_session_id is not None else store.focus_session_id
    )
    focused_evidence_ref_ids = sorted(
        evidence_ref_id
        for evidence_ref_id, evidence in store.evidence.items()
        if evidence.session_id == resolved_focus_session_id
    )
    focused_edge_ids = sorted(
        edge_id
        for edge_id, edge in store.edges.items()
        if resolved_focus_session_id in edge.session_ids
    )
    focused_node_ids = sorted(
        node_id
        for node_id, node in store.nodes.items()
        if set(node.evidence_ref_ids).intersection(focused_evidence_ref_ids)
        or any(
            edge_id in focused_edge_ids
            for edge_id in _edge_ids_touching_node(store, node_id)
        )
    )

    return GraphFocusOverlay(
        focus_session_id=resolved_focus_session_id,
        focused_evidence_ref_ids=focused_evidence_ref_ids,
        focused_edge_ids=focused_edge_ids,
        focused_node_ids=focused_node_ids,
    )


def build_node_view(
    store: UnionSupergraphStore,
    node_id: str,
    focus_session_id: str | None = None,
) -> GraphProjectionNodeView:
    """Build a projection-ready view for one global node."""

    node = store.nodes[node_id]
    resolved_focus_session_id = (
        focus_session_id if focus_session_id is not None else store.focus_session_id
    )
    focus_evidence_ids = {
        evidence_ref_id
        for evidence_ref_id, evidence in store.evidence.items()
        if evidence.session_id == resolved_focus_session_id
    }
    evidence_badges = [
        _build_evidence_badge(store, evidence_ref_id, resolved_focus_session_id)
        for evidence_ref_id in node.evidence_ref_ids
    ]
    adjacency = [
        _build_adjacency_candidate(
            store,
            item.edge_id,
            item.node_id,
            item.direction,
            item.anchored_to_focus_session,
        )
        for item in store.adjacency.get(node_id, [])
    ]

    return GraphProjectionNodeView(
        node_id=node.node_id,
        label=node.label,
        kind=node.kind,
        role=node.role,
        aliases=list(node.aliases),
        source_domains=list(node.source_domains),
        evidence_badges=evidence_badges,
        adjacency=adjacency,
        anchored_to_focus_session=bool(
            set(node.evidence_ref_ids).intersection(focus_evidence_ids)
        )
        or any(candidate.anchored_to_focus_session for candidate in adjacency),
        summary=None,
    )


def build_recap_graph_projection(
    store: UnionSupergraphStore,
    session_id: str,
) -> RecapGraphProjection:
    """Build a backend-neutral recap graph projection from a union-supergraph store."""

    return RecapGraphProjection(
        campaign_id=store.campaign_id,
        session_id=session_id,
        graph_id=store.graph_id,
        focus=build_focus_overlay(store, focus_session_id=session_id),
        node_views={
            node_id: build_node_view(store, node_id, focus_session_id=session_id)
            for node_id in sorted(store.nodes)
        },
        mentions=[],
    )


def _build_evidence_badge(
    store: UnionSupergraphStore,
    evidence_ref_id: str,
    focus_session_id: str | None,
) -> GraphProjectionEvidenceBadge:
    evidence = store.evidence[evidence_ref_id]
    source_domain = str(evidence.source_domain)
    return GraphProjectionEvidenceBadge(
        evidence_ref_id=evidence.evidence_ref_id,
        source_artifact_id=evidence.source_artifact_id,
        source_domain=source_domain,
        evidence_role=evidence.evidence_role,
        is_focus_session_evidence=evidence.session_id == focus_session_id,
        can_open_source=evidence.can_open_source,
        can_highlight_span=evidence.can_highlight_span,
        label=f"{source_domain}: {evidence.evidence_role}",
    )


def _build_adjacency_candidate(
    store: UnionSupergraphStore,
    edge_id: str,
    adjacent_node_id: str,
    direction: str,
    anchored_to_focus_session: bool,
) -> GraphProjectionAdjacencyCandidate:
    edge = store.edges[edge_id]
    adjacent_node = store.nodes[adjacent_node_id]
    return GraphProjectionAdjacencyCandidate(
        edge_id=edge.edge_id,
        node_id=adjacent_node.node_id,
        label=adjacent_node.label,
        kind=adjacent_node.kind,
        predicate=edge.predicate,
        direction=direction,
        anchored_to_focus_session=anchored_to_focus_session,
        source_domains=list(edge.source_domains),
        evidence_ref_ids=list(edge.evidence_ref_ids),
    )


def _edge_ids_touching_node(store: UnionSupergraphStore, node_id: str) -> list[str]:
    return [
        edge_id
        for edge_id, edge in store.edges.items()
        if edge.source_node_id == node_id or edge.target_node_id == node_id
    ]
