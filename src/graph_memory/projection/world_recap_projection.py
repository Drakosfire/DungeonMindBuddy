"""World Graph → focus-session recap projection contracts (PR380A / PR #412).

Pure models and deterministic mention/adaptation helpers. No corpus I/O, no
registry enrichment, no world-scope widening, no synthetic graph facts.
"""

from __future__ import annotations

import re
from typing import Literal

from pydantic import Field

from graph_memory.projection.recap_projection import splice_node_link_spans
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
AMBIGUOUS_MENTION_DIAGNOSTIC = "ambiguous_mention_surface"


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


def _is_line_start(markdown: str, index: int) -> bool:
    return index == 0 or markdown[index - 1] == "\n"


def _skip_link_label(markdown: str, index: int) -> int | None:
    """Advance past a Markdown link/image label ``[...]`` starting at ``[``.

    Nested brackets are tracked by depth so ``[The [old] Caelynn Story]`` is
    one label, not a premature close at the inner ``]``.
    """
    if index >= len(markdown) or markdown[index] != "[":
        return None
    depth = 0
    i = index
    while i < len(markdown):
        ch = markdown[i]
        if ch == "\\":
            i += 2
            continue
        if ch == "\n":
            return None
        if ch == "[":
            depth += 1
        elif ch == "]":
            depth -= 1
            if depth == 0:
                return i + 1
        i += 1
    return None


def _skip_balanced_parens(markdown: str, index: int) -> int | None:
    """Advance past a ``(...)`` destination with nested parentheses."""
    if index >= len(markdown) or markdown[index] != "(":
        return None
    depth = 0
    i = index
    while i < len(markdown):
        ch = markdown[i]
        if ch == "\\":
            i += 2
            continue
        if ch == "(":
            depth += 1
        elif ch == ")":
            depth -= 1
            if depth == 0:
                return i + 1
        elif ch == "\n":
            return None
        i += 1
    return None


def _normalize_reference_label(label: str) -> str:
    return re.sub(r"\s+", " ", label.strip()).casefold()


# CommonMark link reference definition: label, `:`, optional blanks (spaces/tabs
# and at most one line ending), then destination. Shared by label discovery and
# protected-range consumption so the two cannot drift.
_REFERENCE_DEFINITION_RE = re.compile(
    r"(?m)^[ \t]{0,3}\[((?:[^\]\\]|\\.)+)\]:"
    r"[ \t]*(?:\n[ \t]*)?"
    r"\S+[^\n]*"
)

# CommonMark absolute URI scheme: ASCII letter + 1–31 of [A-Za-z0-9+.-], then `:`.
_URI_AUTOLINK_SCHEME_RE = re.compile(r"^[A-Za-z][A-Za-z0-9+.-]{1,31}:")


def _reference_definition_labels(markdown: str) -> set[str]:
    """Labels defined by CommonMark ``[label]: destination`` definitions."""
    return {
        _normalize_reference_label(match.group(1))
        for match in _REFERENCE_DEFINITION_RE.finditer(markdown)
    }


def _match_reference_definition_at(markdown: str, index: int) -> re.Match[str] | None:
    if not _is_line_start(markdown, index):
        return None
    return _REFERENCE_DEFINITION_RE.match(markdown, index)


def _skip_autolink(markdown: str, index: int) -> int | None:
    """Advance past a CommonMark URI or email autolink ``<...>``."""
    if index >= len(markdown) or markdown[index] != "<":
        return None
    close = markdown.find(">", index + 1)
    if close < 0:
        return None
    inner = markdown[index + 1 : close]
    if not inner:
        return None
    for ch in inner:
        # Spaces, ASCII controls, and nested angle brackets are not allowed.
        if ch.isspace() or ch == "<" or ord(ch) < 32:
            return None
    if _URI_AUTOLINK_SCHEME_RE.match(inner):
        return close + 1
    if "@" in inner and "/" not in inner:
        return close + 1
    return None


def _skip_reference_definition_line(markdown: str, index: int) -> int | None:
    """Advance past a full CommonMark link reference definition."""
    match = _match_reference_definition_at(markdown, index)
    if match is None:
        return None
    return match.end()

def _protected_ranges(markdown: str) -> list[tuple[int, int]]:
    """Ranges that must not receive mention rewrites: fences, code, links."""
    ranges: list[tuple[int, int]] = []
    ref_labels = _reference_definition_labels(markdown)
    i = 0
    n = len(markdown)
    while i < n:
        if _is_line_start(markdown, i):
            fence_match = re.match(r"[ \t]{0,3}(```+|~~~+)", markdown[i:])
            if fence_match:
                marker = fence_match.group(1)[0]
                fence_len = len(fence_match.group(1))
                start = i
                after_opener = i + fence_match.end()
                nl = markdown.find("\n", after_opener)
                scan_from = n if nl < 0 else nl + 1
                close_re = re.compile(
                    rf"(?m)^[ \t]{{0,3}}{re.escape(marker * fence_len)}+?[ \t]*$",
                )
                close = close_re.search(markdown, scan_from)
                end = n if close is None else close.end()
                ranges.append((start, end))
                i = end
                continue

            after_def = _skip_reference_definition_line(markdown, i)
            if after_def is not None:
                ranges.append((i, after_def))
                i = after_def
                continue

        # Matching-backtick code spans may contain line breaks (conservative).
        if markdown[i] == "`":
            run = 1
            while i + run < n and markdown[i + run] == "`":
                run += 1
            closer = markdown.find("`" * run, i + run)
            if closer != -1:
                end = closer + run
                ranges.append((i, end))
                i = end
                continue

        after_auto = _skip_autolink(markdown, i)
        if after_auto is not None:
            ranges.append((i, after_auto))
            i = after_auto
            continue

        if markdown[i] == "[" or (
            markdown[i] == "!" and i + 1 < n and markdown[i + 1] == "["
        ):
            start = i
            label_at = i + 1 if markdown[i] == "!" else i
            after_label = _skip_link_label(markdown, label_at)
            if after_label is not None:
                if after_label < n and markdown[after_label] == "(":
                    after_dest = _skip_balanced_parens(markdown, after_label)
                    if after_dest is not None:
                        ranges.append((start, after_dest))
                        i = after_dest
                        continue
                if after_label < n and markdown[after_label] == "[":
                    after_ref = _skip_link_label(markdown, after_label)
                    if after_ref is not None:
                        ranges.append((start, after_ref))
                        i = after_ref
                        continue
                # Shortcut reference link: [label] with a later [label]: def.
                label_text = markdown[label_at + 1 : after_label - 1]
                if _normalize_reference_label(label_text) in ref_labels:
                    # Do not consume a following non-link character.
                    ranges.append((start, after_label))
                    i = after_label
                    continue

        i += 1

    ranges.sort()
    return ranges


def _overlaps_protected(start: int, end: int, protected: list[tuple[int, int]]) -> bool:
    return any(start < used_end and end > used_start for used_start, used_end in protected)


def _surface_owners(
    nodes: list[WorldGraphProjectionNodeView],
) -> dict[str, set[str]]:
    owners: dict[str, set[str]] = {}
    for node in nodes:
        for raw in (node.label, *node.aliases):
            surface = (raw or "").strip()
            if not surface:
                continue
            key = surface.casefold()
            owners.setdefault(key, set()).add(node.node_id)
    return owners


def project_world_markdown_mentions(
    markdown: str,
    nodes: list[WorldGraphProjectionNodeView],
) -> tuple[str, list[WorldGraphRecapMention], list[WorldGraphProjectionDiagnostic]]:
    """Splice unique label/alias surfaces into ``dmb-node:`` links.

    Ambiguous surfaces (same case-insensitive text owned by multiple projected
    nodes) are left unchanged and emit ``ambiguous_mention_surface``.
    Protected Markdown/code ranges are never rewritten.
    """
    owners = _surface_owners(nodes)
    protected = _protected_ranges(markdown)
    diagnostics: list[WorldGraphProjectionDiagnostic] = []
    ambiguous_reported: set[str] = set()

    unique_surfaces: list[tuple[str, str]] = []
    for node in nodes:
        for raw in (node.label, *node.aliases):
            surface = (raw or "").strip()
            if not surface:
                continue
            key = surface.casefold()
            node_ids = owners.get(key, set())
            if len(node_ids) != 1:
                continue
            if node_ids != {node.node_id}:
                continue
            unique_surfaces.append((surface, node.node_id))

    unique_surfaces.sort(key=lambda item: (-len(item[0]), item[0].casefold(), item[1]))
    seen_keys: set[str] = set()
    ordered: list[tuple[str, str]] = []
    for surface, node_id in unique_surfaces:
        key = surface.casefold()
        if key in seen_keys:
            continue
        seen_keys.add(key)
        ordered.append((surface, node_id))

    occupied: list[tuple[int, int]] = []
    matches: list[tuple[int, int, str, str]] = []
    for surface, node_id in ordered:
        pattern = re.compile(
            rf"(?<![\w\\[]){re.escape(surface)}(?![\w\\]])",
            re.IGNORECASE,
        )
        for match in pattern.finditer(markdown):
            start, end = match.span()
            if _overlaps_protected(start, end, protected):
                continue
            if any(start < used_end and end > used_start for used_start, used_end in occupied):
                continue
            occupied.append((start, end))
            matches.append((start, end, match.group(0), node_id))

    for key, node_ids in owners.items():
        if len(node_ids) < 2 or key in ambiguous_reported:
            continue
        sample = next(
            (
                (raw or "").strip()
                for node in nodes
                for raw in (node.label, *node.aliases)
                if (raw or "").strip().casefold() == key
            ),
            key,
        )
        pattern = re.compile(
            rf"(?<![\w\\[]){re.escape(sample)}(?![\w\\]])",
            re.IGNORECASE,
        )
        for match in pattern.finditer(markdown):
            start, end = match.span()
            if _overlaps_protected(start, end, protected):
                continue
            ambiguous_reported.add(key)
            diagnostics.append(
                WorldGraphProjectionDiagnostic(
                    code=AMBIGUOUS_MENTION_DIAGNOSTIC,
                    message=(
                        f"Mention surface {sample!r} matches multiple projected "
                        f"nodes ({', '.join(sorted(node_ids))}); left unlinked."
                    ),
                    severity="warning",
                )
            )
            break

    matches.sort(key=lambda item: item[0])
    projected, offsets = splice_node_link_spans(markdown, matches)
    mentions: list[WorldGraphRecapMention] = []
    for (start, _end, label, node_id), offset in zip(matches, offsets, strict=True):
        if offset is None:
            continue
        mentions.append(
            WorldGraphRecapMention(
                mention_id=f"mention:{node_id}:{start}",
                node_id=node_id,
                label=label,
                start_offset=offset[0],
                end_offset=offset[1],
                evidence_ref_ids=[],
            )
        )
    return projected, mentions, diagnostics


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
