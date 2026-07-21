from __future__ import annotations

import re
from collections.abc import Mapping, Sequence
from typing import Any

from pydantic import BaseModel, ConfigDict, Field

from graph_memory.projection.focus_overlay import (
    GraphFocusOverlay,
    GraphProjectionEvidenceBadge,
)
from graph_memory.anchor_quotes import find_anchor_quote_matches
from graph_memory.projection.node_view import (
    GraphProjectionAdjacencyCandidate,
    GraphProjectionNodeView,
    GraphProjectionSuggestedExpansion,
    GraphProjectionTextHighlightSpan,
)
from graph_memory.union_supergraph.model import UnionSupergraphNode, UnionSupergraphStore
from graph_memory.union_supergraph.projection_identity import (
    UnionProjectionIdentityContext,
    UnionProjectionIdentityDiagnostic,
    append_identity_projection_diagnostics,
    build_union_projection_identity_context,
    is_projectable_union_edge,
    is_projectable_union_node,
    projectable_node_ids,
    resolve_projected_node_id,
    resolve_projection_markdown_dmb_node_links,
    survivor_identity_provenance,
)

_PLACEHOLDER_NODE_SUMMARIES = frozenset({"deterministic party context anchor"})


def _node_projection_summary(node: UnionSupergraphNode) -> str | None:
    node_extra = node.model_extra or {}
    description = node_extra.get("description")
    if not isinstance(description, str):
        return None
    trimmed = description.strip()
    if not trimmed or trimmed.casefold() in _PLACEHOLDER_NODE_SUMMARIES:
        return None
    return trimmed


_LABEL_ELLIPSIS_PATTERN = re.compile(r"\s*(?:\.\.\.|\u2026)\s*")


def _split_label_fragments(label: str) -> list[str]:
    """Split a (possibly elided) evidence label into its verbatim fragments.

    Evidence labels are frequently built by excerpting literal substrings of
    the source paragraph and joining the gaps with an ellipsis. Splitting on
    that ellipsis recovers the original verbatim fragments, which can then be
    literally re-located in the full paragraph for highlighting.
    """
    fragments = [part.strip() for part in _LABEL_ELLIPSIS_PATTERN.split(label)]
    return [fragment for fragment in fragments if fragment]


class _ResolvedSourceExcerpt:
    __slots__ = ("text", "is_full_paragraph", "highlight_spans")

    def __init__(
        self,
        text: str | None,
        *,
        is_full_paragraph: bool = False,
        highlight_spans: list[GraphProjectionTextHighlightSpan] | None = None,
    ) -> None:
        self.text = text
        self.is_full_paragraph = is_full_paragraph
        self.highlight_spans = highlight_spans or []


def _resolve_evidence_source_excerpt(
    store: UnionSupergraphStore,
    evidence_ref_ids: Sequence[str],
    *,
    paragraph_text_by_span_id: Mapping[str, str] | None = None,
) -> _ResolvedSourceExcerpt:
    for evidence_ref_id in evidence_ref_ids:
        evidence = store.evidence.get(evidence_ref_id)
        if evidence is None:
            continue
        evidence_extra = evidence.model_extra or {}
        label = evidence_extra.get("label")
        label_text = label.strip() if isinstance(label, str) and label.strip() else None
        anchor_quotes_raw = evidence_extra.get("anchor_quotes")
        anchor_quotes = [
            quote.strip()
            for quote in anchor_quotes_raw
            if isinstance(quote, str) and quote.strip()
        ] if isinstance(anchor_quotes_raw, list) else []

        paragraph_text = (
            paragraph_text_by_span_id.get(evidence.source_span_ref_id or "")
            if paragraph_text_by_span_id
            else None
        )
        if paragraph_text:
            fragments = anchor_quotes or (
                _split_label_fragments(label_text) if label_text else []
            )
            highlight_spans = [
                GraphProjectionTextHighlightSpan(start=match.char_start, end=match.char_end)
                for match in find_anchor_quote_matches(paragraph_text, fragments)
            ]
            return _ResolvedSourceExcerpt(
                paragraph_text,
                is_full_paragraph=True,
                highlight_spans=highlight_spans,
            )

        if label_text:
            return _ResolvedSourceExcerpt(label_text)
        if anchor_quotes:
            return _ResolvedSourceExcerpt(anchor_quotes[0])
    return _ResolvedSourceExcerpt(None)


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
    union_identity_diagnostics: list[UnionProjectionIdentityDiagnostic] = Field(
        default_factory=list
    )
    union_identity_applied_assertion_ids: list[str] = Field(default_factory=list)


def build_focus_overlay(
    store: UnionSupergraphStore,
    focus_session_id: str | None = None,
    *,
    identity_context: UnionProjectionIdentityContext | None = None,
) -> GraphFocusOverlay:
    """Build deterministic focus metadata from a union-supergraph store."""

    context = identity_context or build_union_projection_identity_context(store)
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
        and is_projectable_union_edge(edge, context)
    )
    focused_node_ids = sorted(
        resolve_projected_node_id(node_id, context)
        for node_id, node in store.nodes.items()
        if is_projectable_union_node(node, context)
        and (
            set(node.evidence_ref_ids).intersection(focused_evidence_ref_ids)
            or any(
                edge_id in focused_edge_ids
                for edge_id in _edge_ids_touching_node(store, node_id, identity_context=context)
            )
        )
    )
    focused_node_ids = sorted(set(focused_node_ids))

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
    *,
    identity_context: UnionProjectionIdentityContext | None = None,
    paragraph_text_by_span_id: Mapping[str, str] | None = None,
) -> GraphProjectionNodeView:
    """Build a projection-ready view for one global node."""

    view, _resolved_count = _build_node_view_with_identity(
        store,
        node_id,
        focus_session_id=focus_session_id,
        identity_context=identity_context,
        paragraph_text_by_span_id=paragraph_text_by_span_id,
    )
    return view


def _build_node_view_with_identity(
    store: UnionSupergraphStore,
    node_id: str,
    *,
    focus_session_id: str | None = None,
    identity_context: UnionProjectionIdentityContext | None = None,
    paragraph_text_by_span_id: Mapping[str, str] | None = None,
) -> tuple[GraphProjectionNodeView, int]:
    context = identity_context or build_union_projection_identity_context(store)
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
        if evidence_ref_id in store.evidence
    ]
    adjacency, edge_endpoints_resolved = _build_node_adjacency(
        store,
        node_id,
        focus_session_id=resolved_focus_session_id,
        identity_context=context,
        paragraph_text_by_span_id=paragraph_text_by_span_id,
    )

    suggested_expansions = _build_suggested_expansions(store, adjacency)

    node_extra = node.model_extra or {}
    description = node_extra.get("description")
    summary = description.strip() if isinstance(description, str) and description.strip() else None

    provenance = survivor_identity_provenance(node_id, context)
    return (
        GraphProjectionNodeView(
            node_id=node.node_id,
            label=node.label,
            kind=node.kind,
            role=node.role,
            aliases=list(node.aliases),
            source_domains=list(node.source_domains),
            evidence_badges=evidence_badges,
            adjacency=adjacency,
            suggested_expansions=suggested_expansions,
            anchored_to_focus_session=bool(
                set(node.evidence_ref_ids).intersection(focus_evidence_ids)
            )
            or any(candidate.anchored_to_focus_session for candidate in adjacency),
            summary=summary,
            **provenance,
        ),
        edge_endpoints_resolved,
    )


def build_recap_graph_projection(
    store: UnionSupergraphStore,
    session_id: str,
    markdown: str | None = None,
    source_spans: list[RecapProjectionSourceSpan] | None = None,
    *,
    paragraph_text_by_span_id: Mapping[str, str] | None = None,
    known_entity_mentions: Mapping[str, Any] | Sequence[Mapping[str, Any]] | None = None,
) -> RecapGraphProjection:
    """Build a backend-neutral recap graph projection from a union-supergraph store."""

    identity_context = build_union_projection_identity_context(store)
    diagnostics = list(identity_context.diagnostics)
    merged_away_filtered = sum(
        1
        for node in store.nodes.values()
        if not is_projectable_union_node(node, identity_context)
    )
    rewired_edges_filtered = sum(
        1
        for edge in store.edges.values()
        if not is_projectable_union_edge(edge, identity_context)
    )

    projected_markdown, mentions, mention_targets_resolved = _project_markdown_mentions(
        store,
        markdown,
        identity_context=identity_context,
        paragraph_text_by_span_id=paragraph_text_by_span_id,
        known_entity_mentions=known_entity_mentions,
        diagnostics=diagnostics,
    )
    if projected_markdown is not None:
        projected_markdown, markdown_redirect_count = resolve_projection_markdown_dmb_node_links(
            projected_markdown,
            identity_context,
        )
    else:
        markdown_redirect_count = 0
    mention_targets_resolved += markdown_redirect_count

    edge_endpoints_resolved = 0
    node_views: dict[str, GraphProjectionNodeView] = {}
    for node_id in projectable_node_ids(store, identity_context):
        view, resolved_count = _build_node_view_with_identity(
            store,
            node_id,
            focus_session_id=session_id,
            identity_context=identity_context,
            paragraph_text_by_span_id=paragraph_text_by_span_id,
        )
        edge_endpoints_resolved += resolved_count
        node_views[node_id] = view

    append_identity_projection_diagnostics(
        diagnostics,
        merged_away_nodes_filtered=merged_away_filtered,
        rewired_edges_filtered=rewired_edges_filtered,
        edge_endpoints_resolved=edge_endpoints_resolved,
        mention_targets_resolved=mention_targets_resolved,
    )

    return RecapGraphProjection(
        campaign_id=store.campaign_id,
        session_id=session_id,
        graph_id=store.graph_id,
        markdown=projected_markdown,
        focus=build_focus_overlay(
            store,
            focus_session_id=session_id,
            identity_context=identity_context,
        ),
        node_views=node_views,
        mentions=mentions,
        source_spans=source_spans or [],
        union_identity_diagnostics=diagnostics,
        union_identity_applied_assertion_ids=sorted(identity_context.applied_assertion_ids),
    )


def splice_node_link_spans(
    markdown: str,
    spans: list[tuple[int, int, str, str]],
) -> tuple[str, list[tuple[int, int] | None]]:
    """Splice `[label](dmb-node:node_id)` at each ``(start, end, label, node_id)``
    span (offsets given in the *original* ``markdown`` coordinates) and return the
    resulting markdown plus, for each input span (by original list position), its
    ``(start, end)`` offset in the *projected* string it was actually spliced into
    (or ``None`` if the span was dropped for overlapping an earlier one).

    This is the single place that turns a located mention span into the literal
    markdown link text the frontend renders as a pill. Every consumer (live
    auto-linking, gold anchor lookup) must go through this so mention offsets are
    always computed against the text they actually describe — offsets computed
    against pre-splice text drift out of alignment with every earlier span spliced
    in ahead of them, since each replacement is longer than the span it replaces.
    """
    occupied: list[tuple[int, int]] = []
    accepted: list[tuple[int, int, str, str, int]] = []
    for index, (start, end, label, node_id) in enumerate(spans):
        if any(start < used_end and end > used_start for used_start, used_end in occupied):
            continue
        occupied.append((start, end))
        accepted.append((start, end, label, node_id, index))

    accepted.sort(key=lambda item: item[0])

    pieces: list[str] = []
    projected_offsets: list[tuple[int, int] | None] = [None] * len(spans)
    cursor = 0
    projected_length = 0
    for start, end, label, node_id, index in accepted:
        prefix = markdown[cursor:start]
        pieces.append(prefix)
        projected_length += len(prefix)

        replacement = f"[{label}](dmb-node:{node_id})"
        mention_start = projected_length
        pieces.append(replacement)
        projected_length += len(replacement)
        projected_offsets[index] = (mention_start, projected_length)
        cursor = end

    pieces.append(markdown[cursor:])
    return "".join(pieces), projected_offsets


def _iter_known_entity_mention_rows(
    known_entity_mentions: Mapping[str, Any] | Sequence[Mapping[str, Any]] | None,
) -> list[Mapping[str, Any]]:
    if known_entity_mentions is None:
        return []
    if isinstance(known_entity_mentions, Mapping):
        rows = known_entity_mentions.get("mentions")
        if isinstance(rows, list):
            return [row for row in rows if isinstance(row, Mapping)]
        return []
    return [row for row in known_entity_mentions if isinstance(row, Mapping)]


def _paragraph_start_offsets(
    markdown: str,
    paragraph_text_by_span_id: Mapping[str, str],
) -> dict[str, int]:
    """Locate each paragraph's first occurrence in full markdown (fail closed on miss)."""
    starts: dict[str, int] = {}
    search_from = 0
    # Prefer ordinal stability: scan spans in appearance order when possible by
    # walking markdown and matching remaining paragraph texts greedily.
    remaining = {
        span_id: text
        for span_id, text in paragraph_text_by_span_id.items()
        if isinstance(text, str) and text
    }
    # First pass: exact unique find from current cursor when texts are sequential.
    ordered_ids = sorted(remaining.keys())
    for span_id in ordered_ids:
        text = remaining[span_id]
        idx = markdown.find(text, search_from)
        if idx < 0:
            idx = markdown.find(text)
        if idx < 0:
            continue
        starts[span_id] = idx
        search_from = max(search_from, idx + len(text))
    return starts


def _known_mention_spans_in_markdown(
    markdown: str,
    *,
    known_entity_mentions: Mapping[str, Any] | Sequence[Mapping[str, Any]] | None,
    paragraph_text_by_span_id: Mapping[str, str] | None,
    identity_context: UnionProjectionIdentityContext,
    store: UnionSupergraphStore,
    diagnostics: list[dict[str, Any]] | None = None,
) -> list[tuple[int, int, str, str]]:
    """Convert paragraph-keyed known mentions into full-markdown chip spans.

    Fail closed when paragraph offsets cannot be remapped: never fall back to a
    global ``markdown.find(surface)`` (that can chip the wrong occurrence).
    Within the uniquely identified source paragraph, a unique exact surface hit
    is allowed; ambiguous or missing paragraph text skips the mention.
    """
    rows = _iter_known_entity_mention_rows(known_entity_mentions)
    if not rows:
        return []
    para_texts = dict(paragraph_text_by_span_id or {})
    para_starts = _paragraph_start_offsets(markdown, para_texts) if para_texts else {}
    matches: list[tuple[int, int, str, str]] = []
    for row in rows:
        node_id = str(row.get("canonical_entity_id") or "").strip()
        surface = str(row.get("surface_text") or "")
        if not node_id or not surface:
            continue
        resolved_node_id = resolve_projected_node_id(node_id, identity_context)
        node = store.nodes.get(resolved_node_id)
        if node is None or not is_projectable_union_node(node, identity_context):
            continue
        span_id = str(row.get("source_span_ref_id") or "").strip()
        start_offset = row.get("start_offset")
        end_offset = row.get("end_offset")
        global_start: int | None = None
        global_end: int | None = None
        if (
            span_id
            and span_id in para_starts
            and isinstance(start_offset, int)
            and isinstance(end_offset, int)
        ):
            para_text = para_texts.get(span_id) or ""
            if para_text[start_offset:end_offset] == surface:
                global_start = para_starts[span_id] + start_offset
                global_end = para_starts[span_id] + end_offset
        if global_start is None or global_end is None:
            para_text = para_texts.get(span_id) or ""
            para_start = para_starts.get(span_id)
            if span_id and para_text and para_start is not None:
                local_hits = [
                    idx
                    for idx in range(len(para_text))
                    if para_text.startswith(surface, idx)
                ]
                # Only accept a unique in-paragraph surface; never scan the full recap.
                if len(local_hits) == 1:
                    local = local_hits[0]
                    global_start = para_start + local
                    global_end = global_start + len(surface)
                else:
                    if diagnostics is not None:
                        diagnostics.append(
                            {
                                "code": "known_entity_mention_offset_unresolved",
                                "source_span_ref_id": span_id,
                                "surface_text": surface,
                                "canonical_entity_id": resolved_node_id,
                                "reason": (
                                    "ambiguous_in_paragraph"
                                    if len(local_hits) > 1
                                    else "surface_missing_in_paragraph"
                                ),
                            }
                        )
                    continue
            else:
                if diagnostics is not None:
                    diagnostics.append(
                        {
                            "code": "known_entity_mention_offset_unresolved",
                            "source_span_ref_id": span_id or None,
                            "surface_text": surface,
                            "canonical_entity_id": resolved_node_id,
                            "reason": "paragraph_remap_unavailable",
                        }
                    )
                continue
        if markdown[global_start:global_end] != surface:
            if diagnostics is not None:
                diagnostics.append(
                    {
                        "code": "known_entity_mention_offset_unresolved",
                        "source_span_ref_id": span_id or None,
                        "surface_text": surface,
                        "canonical_entity_id": resolved_node_id,
                        "reason": "remapped_slice_mismatch",
                    }
                )
            continue
        matches.append((global_start, global_end, surface, resolved_node_id))
    matches.sort(key=lambda item: (item[0], -(item[1] - item[0])))
    return matches


def _project_markdown_mentions(
    store: UnionSupergraphStore,
    markdown: str | None,
    *,
    identity_context: UnionProjectionIdentityContext | None = None,
    paragraph_text_by_span_id: Mapping[str, str] | None = None,
    known_entity_mentions: Mapping[str, Any] | Sequence[Mapping[str, Any]] | None = None,
    diagnostics: list[dict[str, Any]] | None = None,
) -> tuple[str | None, list[RecapProjectionMention], int]:
    if not markdown:
        return markdown, [], 0

    context = identity_context or build_union_projection_identity_context(store)
    matches: list[tuple[int, int, str, str]] = []
    occupied: list[tuple[int, int]] = []

    # Prefer deterministic known-entity mention spans (registry-backed).
    known_mention_diagnostics: list[dict[str, Any]] = []
    for start, end, label, node_id in _known_mention_spans_in_markdown(
        markdown,
        known_entity_mentions=known_entity_mentions,
        paragraph_text_by_span_id=paragraph_text_by_span_id,
        identity_context=context,
        store=store,
        diagnostics=known_mention_diagnostics,
    ):
        if any(start < used_end and end > used_start for used_start, used_end in occupied):
            continue
        occupied.append((start, end))
        matches.append((start, end, label, node_id))
    if diagnostics is not None and known_mention_diagnostics:
        for item in known_mention_diagnostics:
            diagnostics.append(
                UnionProjectionIdentityDiagnostic(
                    code=str(item.get("code") or "known_entity_mention_offset_unresolved"),
                    message=(
                        f"Skipped known-entity chip for {item.get('surface_text')!r} "
                        f"({item.get('canonical_entity_id')}) "
                        f"reason={item.get('reason')}"
                    ),
                    severity="warning",
                )
            )

    # Retain alias-store matching for novel / non-known entities.
    known_chip_node_ids = {
        resolve_projected_node_id(str(row.get("canonical_entity_id") or ""), context)
        for row in _iter_known_entity_mention_rows(known_entity_mentions)
        if str(row.get("canonical_entity_id") or "").strip()
    }
    aliases = sorted(store.aliases.items(), key=lambda item: len(item[0]), reverse=True)
    for alias, node_id in aliases:
        resolved_node_id = resolve_projected_node_id(node_id, context)
        if resolved_node_id in known_chip_node_ids:
            # Known entities are chip-sourced only from the mention sidecar.
            continue
        node = store.nodes.get(resolved_node_id)
        if node is None or not is_projectable_union_node(node, context):
            continue
        pattern = re.compile(rf"(?<![\w\\[]){re.escape(alias)}(?![\w\\]])", re.IGNORECASE)
        for match in pattern.finditer(markdown):
            start, end = match.span()
            if any(start < used_end and end > used_start for used_start, used_end in occupied):
                continue
            occupied.append((start, end))
            matches.append((start, end, match.group(0), resolved_node_id))

    matches.sort(key=lambda item: item[0])
    projected, offsets = splice_node_link_spans(markdown, matches)

    mentions: list[RecapProjectionMention] = []
    mention_targets_resolved = 0
    for (start, end, label, node_id), offset in zip(matches, offsets):
        if offset is None:
            continue
        node = store.nodes[node_id]
        mention_kwargs: dict[str, object] = {
            "mention_id": f"mention:{node_id}:{start}",
            "node_id": node_id,
            "label": label,
            "start_offset": offset[0],
            "end_offset": offset[1],
            "evidence_ref_ids": list(node.evidence_ref_ids),
        }
        mentions.append(RecapProjectionMention(**mention_kwargs))

    return projected, mentions, mention_targets_resolved


def _build_node_adjacency(
    store: UnionSupergraphStore,
    node_id: str,
    *,
    focus_session_id: str | None,
    identity_context: UnionProjectionIdentityContext,
    paragraph_text_by_span_id: Mapping[str, str] | None = None,
) -> tuple[list[GraphProjectionAdjacencyCandidate], int]:
    adjacency: list[GraphProjectionAdjacencyCandidate] = []
    edge_endpoints_resolved = 0
    seen_edge_ids: set[str] = set()

    def append_adjacency(
        edge_id: str,
        adjacent_node_id: str,
        direction: str,
        *,
        anchored_to_focus_session: bool,
        raw_adjacent_node_id: str | None = None,
    ) -> None:
        nonlocal edge_endpoints_resolved
        if edge_id in seen_edge_ids:
            return
        edge = store.edges.get(edge_id)
        if edge is None or not is_projectable_union_edge(edge, identity_context):
            return

        resolved_adjacent_node_id = resolve_projected_node_id(adjacent_node_id, identity_context)
        if raw_adjacent_node_id and resolved_adjacent_node_id != raw_adjacent_node_id:
            edge_endpoints_resolved += 1

        adjacent_node = store.nodes.get(resolved_adjacent_node_id)
        if adjacent_node is None or not is_projectable_union_node(adjacent_node, identity_context):
            return

        seen_edge_ids.add(edge_id)
        adjacency.append(
            _build_adjacency_candidate(
                store,
                edge_id,
                resolved_adjacent_node_id,
                direction,
                anchored_to_focus_session,
                identity_context=identity_context,
                paragraph_text_by_span_id=paragraph_text_by_span_id,
            )
        )

    for item in store.adjacency.get(node_id, []):
        append_adjacency(
            item.edge_id,
            item.node_id,
            item.direction,
            anchored_to_focus_session=item.anchored_to_focus_session,
            raw_adjacent_node_id=item.node_id,
        )

    for edge_id, edge in store.edges.items():
        if edge_id in seen_edge_ids or not is_projectable_union_edge(edge, identity_context):
            continue
        resolved_source_id = resolve_projected_node_id(edge.source_node_id, identity_context)
        resolved_target_id = resolve_projected_node_id(edge.target_node_id, identity_context)
        anchored = bool(focus_session_id and focus_session_id in edge.session_ids)
        if resolved_source_id == node_id and resolved_target_id != node_id:
            append_adjacency(
                edge_id,
                resolved_target_id,
                edge.direction or "outgoing",
                anchored_to_focus_session=anchored,
                raw_adjacent_node_id=edge.target_node_id,
            )
        elif resolved_target_id == node_id and resolved_source_id != node_id:
            append_adjacency(
                edge_id,
                resolved_source_id,
                "incoming",
                anchored_to_focus_session=anchored,
                raw_adjacent_node_id=edge.source_node_id,
            )

    return adjacency, edge_endpoints_resolved


def _build_evidence_badge(
    store: UnionSupergraphStore,
    evidence_ref_id: str,
    focus_session_id: str | None,
) -> GraphProjectionEvidenceBadge:
    evidence = store.evidence[evidence_ref_id]
    source_domain = str(evidence.source_domain)
    evidence_extra = evidence.model_extra or {}
    stored_label = evidence_extra.get("label")
    if isinstance(stored_label, str) and stored_label.strip():
        badge_label = stored_label.strip()
    else:
        badge_label = evidence.evidence_role.replace("_", " ")
    return GraphProjectionEvidenceBadge(
        evidence_ref_id=evidence.evidence_ref_id,
        source_artifact_id=evidence.source_artifact_id,
        source_domain=source_domain,
        evidence_role=evidence.evidence_role,
        is_focus_session_evidence=evidence.session_id == focus_session_id,
        can_open_source=evidence.can_open_source,
        can_highlight_span=evidence.can_highlight_span,
        label=badge_label,
        session_id=evidence.session_id,
        source_span_ref_id=evidence.source_span_ref_id,
    )


def _build_adjacency_candidate(
    store: UnionSupergraphStore,
    edge_id: str,
    adjacent_node_id: str,
    direction: str,
    anchored_to_focus_session: bool,
    *,
    identity_context: UnionProjectionIdentityContext | None = None,
    paragraph_text_by_span_id: Mapping[str, str] | None = None,
) -> GraphProjectionAdjacencyCandidate:
    context = identity_context or build_union_projection_identity_context(store)
    edge = store.edges[edge_id]
    resolved_source_id = resolve_projected_node_id(edge.source_node_id, context)
    resolved_target_id = resolve_projected_node_id(edge.target_node_id, context)
    adjacent_node = store.nodes[adjacent_node_id]
    edge_label = edge.label.strip() if isinstance(edge.label, str) and edge.label.strip() else None
    resolved_excerpt = _resolve_evidence_source_excerpt(
        store,
        edge.evidence_ref_ids,
        paragraph_text_by_span_id=paragraph_text_by_span_id,
    )
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
        edge_label=edge_label,
        session_ids=list(edge.session_ids),
        source_node_id=resolved_source_id,
        target_node_id=resolved_target_id,
        related_summary=_node_projection_summary(adjacent_node),
        source_excerpt=resolved_excerpt.text,
        source_excerpt_is_full_paragraph=resolved_excerpt.is_full_paragraph,
        source_excerpt_highlight_spans=resolved_excerpt.highlight_spans,
    )


def _edge_ids_touching_node(
    store: UnionSupergraphStore,
    node_id: str,
    *,
    identity_context: UnionProjectionIdentityContext | None = None,
) -> list[str]:
    context = identity_context or build_union_projection_identity_context(store)
    return [
        edge_id
        for edge_id, edge in store.edges.items()
        if is_projectable_union_edge(edge, context)
        and (
            edge.source_node_id == node_id
            or edge.target_node_id == node_id
            or resolve_projected_node_id(edge.source_node_id, context) == node_id
            or resolve_projected_node_id(edge.target_node_id, context) == node_id
        )
    ]


def _adjacent_node_degree(store: UnionSupergraphStore, node_id: str) -> int:
    return len(store.adjacency.get(node_id, []))


def _expansion_rank_reason(
    candidate: GraphProjectionAdjacencyCandidate,
    adjacent_degree: int,
) -> str:
    if candidate.anchored_to_focus_session:
        return "current session"
    if len(candidate.evidence_ref_ids) >= 2:
        return "more evidence"
    if adjacent_degree >= 3:
        return "connected hub"
    return "connected thread"


def _expansion_sort_key(
    store: UnionSupergraphStore,
    candidate: GraphProjectionAdjacencyCandidate,
) -> tuple[int, int, int, str]:
    focus_score = 1 if candidate.anchored_to_focus_session else 0
    evidence_score = len(candidate.evidence_ref_ids)
    degree_score = _adjacent_node_degree(store, candidate.node_id)
    return (
        -focus_score,
        -evidence_score,
        -degree_score,
        candidate.label.lower(),
    )


def _build_suggested_expansions(
    store: UnionSupergraphStore,
    adjacency: list[GraphProjectionAdjacencyCandidate],
) -> list[GraphProjectionSuggestedExpansion]:
    ranked = sorted(adjacency, key=lambda item: _expansion_sort_key(store, item))
    expansions: list[GraphProjectionSuggestedExpansion] = []
    for index, candidate in enumerate(ranked, start=1):
        adjacent_degree = _adjacent_node_degree(store, candidate.node_id)
        expansions.append(
            GraphProjectionSuggestedExpansion(
                edge_id=candidate.edge_id,
                node_id=candidate.node_id,
                label=candidate.label,
                kind=candidate.kind,
                predicate=candidate.predicate,
                direction=candidate.direction,
                anchored_to_focus_session=candidate.anchored_to_focus_session,
                source_domains=list(candidate.source_domains),
                evidence_ref_ids=list(candidate.evidence_ref_ids),
                edge_label=candidate.edge_label,
                session_ids=list(candidate.session_ids),
                rank=index,
                rank_reason=_expansion_rank_reason(candidate, adjacent_degree),
            )
        )
    return expansions
