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
from graph_memory.projection_load_telemetry import projection_load_trace, timed_stage


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


_THREAD_KINDS = frozenset({"mystery", "thread", "quest", "clue", "plot_thread"})
_THREAD_SINGLE_TOKEN_STOPWORDS = frozenset(
    {
        "river",
        "stone",
        "bridge",
        "town",
        "flood",
        "panic",
        "rescue",
        "goat",
        "float",
        "artifact",
        "mysterious",
        "possible",
        "next",
        "destination",
        "recovery",
        "rebuilding",
        "remains",
        "unfinished",
        "unnamed",
        "upriver",
        "settlement",
        "unseasonable",
        "torrential",
        "rains",
        "escalating",
        "during",
        "celebration",
        "mentioned",
        "appears",
        "containing",
    }
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


def _session_number_from_id(session_id: str) -> int | str:
    raw = (session_id or "").strip()
    match = re.search(r"(\d+)$", raw)
    return int(match.group(1)) if match else raw


def _durable_id_for_known_entity(kind: str, slug: str) -> str:
    cleaned = (slug or "").strip().replace("_", "-")
    if kind == "pc":
        # World head uses colon namespace for roster PCs (pc:stafl).
        return f"pc:{slug.strip()}"
    if kind == "companion":
        return f"node:{cleaned}"
    return f"node:{cleaned}"


def _surface_appears_in_markdown(surface: str, markdown: str) -> bool:
    pattern = re.compile(
        rf"(?<![\w\\[]){re.escape(surface)}(?![\w\\]])",
        re.IGNORECASE,
    )
    return pattern.search(markdown) is not None


def _thread_chip_surfaces(label: str, markdown: str) -> list[str]:
    """Derive short chip surfaces for mystery/thread nodes that appear in prose.

    Full GM summary labels almost never appear verbatim in recap text, so
    alias-only chipping leaves threads invisible. Prefer multi-word phrases,
    then distinctive proper nouns.
    """
    text = (label or "").strip()
    if not text or not markdown:
        return []

    candidates: list[str] = []
    if ":" in text:
        after = text.split(":", 1)[1].strip()
        if after:
            candidates.append(after)
    candidates.extend(re.findall(r"[\"']([^\"']{4,48})[\"']", text))
    candidates.extend(
        re.findall(r"\b(?:[A-Z][a-z]+(?:\s+[A-Za-z][a-z]+){1,4})\b", text)
    )
    candidates.extend(re.findall(r"\b([A-Z][a-z]{4,})\b", text))

    accepted: list[str] = []
    seen: set[str] = set()
    for raw in candidates:
        surface = raw.strip(" .,;:\"'")
        if len(surface) < 4:
            continue
        words = surface.split()
        if len(words) == 1 and surface.casefold() in _THREAD_SINGLE_TOKEN_STOPWORDS:
            continue
        if len(words) == 1 and len(surface) < 6:
            continue
        key = surface.casefold()
        if key in seen:
            continue
        if not _surface_appears_in_markdown(surface, markdown):
            continue
        seen.add(key)
        accepted.append(surface)

    accepted.sort(key=len, reverse=True)
    return accepted[:3]


def _reserved_non_thread_surfaces(
    nodes: list[WorldGraphProjectionNodeView],
) -> set[str]:
    """Surfaces already owned by people/places/things — threads must not steal them."""
    reserved: set[str] = set()
    for node in nodes:
        kind = (node.kind or "").strip().casefold()
        if kind in _THREAD_KINDS:
            continue
        for raw in (node.label, *node.aliases):
            surface = (raw or "").strip()
            if surface:
                reserved.add(surface.casefold())
    return reserved


def _enrich_thread_aliases_from_markdown(
    nodes: list[WorldGraphProjectionNodeView],
    markdown: str,
) -> list[WorldGraphProjectionNodeView]:
    """Attach prose-grounded chip aliases onto mystery/thread nodes."""
    reserved = _reserved_non_thread_surfaces(nodes)
    enriched: list[WorldGraphProjectionNodeView] = []
    for node in nodes:
        kind = (node.kind or "").strip().casefold()
        if kind not in _THREAD_KINDS:
            enriched.append(node)
            continue
        surfaces = [
            surface
            for surface in _thread_chip_surfaces(node.label, markdown)
            if surface.casefold() not in reserved
        ]
        if not surfaces:
            enriched.append(node)
            continue
        alias_set = {a.casefold(): a for a in node.aliases if a}
        for surface in surfaces:
            alias_set.setdefault(surface.casefold(), surface)
        enriched.append(
            node.model_copy(update={"aliases": list(alias_set.values())})
        )
    return enriched


def _merge_registry_standing_into_nodes(
    nodes: list[WorldGraphProjectionNodeView],
    *,
    campaign_id: str,
    session_id: str,
    world_standing_nodes: list[WorldGraphProjectionNodeView] | None = None,
) -> list[WorldGraphProjectionNodeView]:
    """Ensure party-roster PCs/companions are available for recap chipping.

    Campaign-scoped world projection can omit standing PCs that live under
    another campaign_scope (common for C1 dogfood against a C2-scoped roster
    seed). Prefer full world-scoped standing nodes (with adjacency) over empty
    stubs so opened PC cards still show related threads.
    """
    try:
        from graph_memory.extraction.known_entity_registry import (
            build_known_entity_registry,
        )
    except Exception:
        return nodes

    try:
        registry = build_known_entity_registry(
            campaign_id,
            _session_number_from_id(session_id),
        )
    except Exception:
        return nodes

    standing_by_id = {
        node.node_id: node for node in (world_standing_nodes or [])
    }

    by_id = {node.node_id: node for node in nodes}
    slug_to_node: dict[str, WorldGraphProjectionNodeView] = {}
    for node in nodes:
        node_id = str(node.node_id or "")
        if node_id.startswith("pc:"):
            slug_to_node[node_id.split(":", 1)[1].replace("-", "_")] = node
        elif node_id.startswith("node:"):
            slug_to_node[node_id.split(":", 1)[1].replace("-", "_")] = node

    merged: list[WorldGraphProjectionNodeView] = list(nodes)
    for entity in registry.entities:
        if entity.kind not in {"pc", "companion"}:
            continue
        slug = entity.slug.strip()
        preferred_id = _durable_id_for_known_entity(entity.kind, slug)
        existing = by_id.get(preferred_id) or slug_to_node.get(slug.replace("-", "_"))
        standing = standing_by_id.get(preferred_id)
        surfaces = [
            surface
            for surface, _method in entity.match_terms
            if (surface or "").strip()
        ]
        if entity.display_name.strip():
            surfaces.insert(0, entity.display_name.strip())

        base = existing or standing
        if base is not None:
            alias_set = {a.casefold(): a for a in base.aliases if a}
            for surface in surfaces:
                if surface.casefold() not in alias_set:
                    alias_set[surface.casefold()] = surface
            label = base.label or entity.display_name
            if label.casefold() not in alias_set:
                alias_set[label.casefold()] = label
            # Prefer standing adjacency when campaign projection omitted the PC.
            updated = (standing or base).model_copy(
                update={"aliases": list(alias_set.values())}
            )
            if existing is not None:
                for index, node in enumerate(merged):
                    if node.node_id == existing.node_id:
                        merged[index] = updated
                        break
            else:
                merged.append(updated)
            by_id[updated.node_id] = updated
            continue

        stub = WorldGraphProjectionNodeView(
            node_id=preferred_id,
            label=entity.display_name or slug,
            kind=entity.kind,
            role="character" if entity.kind == "pc" else "companion",
            aliases=list(dict.fromkeys(surfaces)),
            source_domains=["party_registry"],
            evidence_ref_ids=[],
            anchored_to_focus_session=False,
            summary=None,
            campaign_scope=campaign_id,
        )
        merged.append(stub)
        by_id[preferred_id] = stub

    return merged


def _needed_standing_durable_ids(campaign_id: str, session_id: str) -> set[str]:
    """Return durable node ids for registry PCs/companions, or empty on failure."""
    try:
        from graph_memory.extraction.known_entity_registry import (
            build_known_entity_registry,
        )
    except Exception:
        return set()
    try:
        registry = build_known_entity_registry(
            campaign_id,
            _session_number_from_id(session_id),
        )
    except Exception:
        return set()
    return {
        _durable_id_for_known_entity(entity.kind, entity.slug)
        for entity in registry.entities
        if entity.kind in {"pc", "companion"}
    }


def _world_standing_nodes_for_request(
    request: WorldGraphProjectionRequest,
    *,
    root: Path | None,
    campaign_nodes: list[WorldGraphProjectionNodeView],
    campaign_id: str,
    session_id: str,
) -> list[WorldGraphProjectionNodeView]:
    """Load world-scoped roster nodes when campaign projection omitted them."""
    needed = _needed_standing_durable_ids(campaign_id, session_id)
    campaign_ids = {node.node_id for node in campaign_nodes}
    if not needed or needed.issubset(campaign_ids):
        return []
    if request.scope_mode == "world":
        return []

    world_request = request.model_copy(update={"scope_mode": "world"})
    try:
        world = project_world_graph(world_request, root=root)
    except Exception:
        return []
    return [node for node in world.nodes if node.node_id in needed]


_STANDING_CHARACTER_KINDS = frozenset({"pc", "companion"})
_PARTY_MEMBERSHIP_PREDICATES = frozenset({"member_of", "belongs_to", "part_of"})
_PARTY_NODE_ID_HINTS = ("party", "heroes", "questionable-company")
_HEROES_PARTY_NODE_ID = "node:heroes-party"


def _node_mentioned_in_markdown(
    node: WorldGraphProjectionNodeView,
    markdown: str,
) -> bool:
    for surface in (node.label, *node.aliases):
        if surface and _surface_appears_in_markdown(surface, markdown):
            return True
    return False


def _is_party_membership_adjacency(
    candidate: WorldGraphProjectionAdjacencyCandidate,
) -> bool:
    predicate = (candidate.predicate or "").strip().casefold()
    if predicate in _PARTY_MEMBERSHIP_PREDICATES:
        return True
    node_id = (candidate.node_id or "").strip().casefold()
    return any(hint in node_id for hint in _PARTY_NODE_ID_HINTS)


def _union_session_ids(existing: list[str], session_id: str) -> list[str]:
    merged: list[str] = []
    seen: set[str] = set()
    for value in [*existing, session_id]:
        cleaned = (value or "").strip()
        if not cleaned:
            continue
        key = cleaned.casefold()
        if key in seen:
            continue
        seen.add(key)
        merged.append(cleaned)
    return merged


def _stamp_focus_session_on_mentioned_standing(
    nodes: list[WorldGraphProjectionNodeView],
    *,
    session_id: str,
    campaign_id: str,
    markdown: str,
) -> list[WorldGraphProjectionNodeView]:
    """Ensure mentioned roster PCs show the focus session on party membership.

    Standing PCs are often seeded under another campaign_scope and only gain
    membership edges from later extracts. Recap chips still name them in early
    sessions; without a focus-session stamp, Related objects timelines skip the
    session the GM is looking at.
    """
    focus = (session_id or "").strip()
    if not focus or not markdown:
        return nodes

    stamped: list[WorldGraphProjectionNodeView] = []
    for node in nodes:
        kind = (node.kind or "").strip().casefold()
        if kind not in _STANDING_CHARACTER_KINDS:
            stamped.append(node)
            continue
        if not _node_mentioned_in_markdown(node, markdown):
            stamped.append(node)
            continue

        adjacency = list(node.adjacency)
        touched = False
        for index, candidate in enumerate(adjacency):
            if not _is_party_membership_adjacency(candidate):
                continue
            session_ids = _union_session_ids(list(candidate.session_ids), focus)
            if session_ids == list(candidate.session_ids) and candidate.anchored_to_focus_session:
                continue
            adjacency[index] = candidate.model_copy(
                update={
                    "session_ids": session_ids,
                    "anchored_to_focus_session": True,
                }
            )
            touched = True

        if not touched:
            adjacency.insert(
                0,
                WorldGraphProjectionAdjacencyCandidate(
                    edge_id=f"edge:recap-focus-presence:{node.node_id}:{focus}",
                    node_id=_HEROES_PARTY_NODE_ID,
                    label="Heroes / party",
                    kind="party",
                    predicate="member_of",
                    direction="outbound",
                    anchored_to_focus_session=True,
                    source_domains=["recap_focus_presence"],
                    evidence_ref_ids=[],
                    session_ids=[focus],
                    campaign_scope=campaign_id,
                ),
            )
            touched = True

        stamped.append(
            node.model_copy(update={"adjacency": adjacency}) if touched else node
        )
    return stamped


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

    with projection_load_trace(
        "world_graph_recap_projection",
        world_id=request.world_id,
        campaign_id=campaign_id,
        focus_session_id=session_id,
        scope_mode=getattr(request, "scope_mode", "campaign"),
    ) as trace:
        # Prefer a single world-scope projection when standing PCs are expected
        # to be missing from campaign scope — avoids paying for campaign+world
        # full builds on the cold path (~2× build_nodes).
        projection_request = request
        if request.scope_mode != "world":
            needed_standing = _needed_standing_durable_ids(campaign_id, session_id)
            if needed_standing:
                projection_request = request.model_copy(update={"scope_mode": "world"})
                trace.set_meta(recap_projection_scope="world_for_standing")

        with timed_stage("world_projection"):
            world = project_world_graph(projection_request, root=root)

        markdown = corpus_markdown
        if markdown is None:
            with timed_stage("load_recap_markdown"):
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

        with timed_stage("standing_nodes") as standing_extras:
            # When we already projected world-scope above, standing nodes are
            # present in ``world.nodes`` and this helper returns [].
            standing_nodes = _world_standing_nodes_for_request(
                request,
                root=root,
                campaign_nodes=list(world.nodes),
                campaign_id=campaign_id,
                session_id=session_id,
            )
            standing_extras["standing_node_count"] = len(standing_nodes)
            standing_extras["second_projection"] = bool(standing_nodes)
        with timed_stage("merge_standing"):
            chip_nodes = _merge_registry_standing_into_nodes(
                list(world.nodes),
                campaign_id=campaign_id,
                session_id=session_id,
                world_standing_nodes=standing_nodes,
            )
        with timed_stage("enrich_aliases"):
            chip_nodes = _enrich_thread_aliases_from_markdown(chip_nodes, markdown)
        with timed_stage("stamp_focus"):
            chip_nodes = _stamp_focus_session_on_mentioned_standing(
                chip_nodes,
                session_id=session_id,
                campaign_id=campaign_id,
                markdown=markdown,
            )
        with timed_stage("markdown_mentions") as mention_extras:
            projected_markdown, mentions = project_world_markdown_mentions(
                markdown, chip_nodes
            )
            mention_extras["mention_count"] = len(mentions)
        with timed_stage("adapt_node_views") as adapt_extras:
            node_views = {
                node.node_id: adapt_world_node_to_recap_view(node) for node in chip_nodes
            }
            adapt_extras["node_view_count"] = len(node_views)

        trace.bump("node_views", len(node_views))
        trace.bump("mentions", len(mentions))
        trace.set_meta(
            revision_id=world.snapshot.revision_id,
            markdown_chars=len(projected_markdown or ""),
        )

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
