"""Read-model adapter for layering authored graph overlay into graph review projection."""

from __future__ import annotations

import hashlib
import re
from pathlib import Path
from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field, ValidationError

from apps.live_control_server.models.graph_authoring_overlay import (
    AuthoredGraphAssertion,
    AuthoredGraphLinkExistingAssertion,
    AuthoredGraphMergeObjectsAssertion,
    AuthoredGraphObjectAssertion,
    AuthoredGraphObjectRef,
    AuthoredGraphOverlay,
    AuthoredGraphRelationshipAssertion,
    GraphAuthoringSourceAnchor,
    GraphVisibilityPolicy,
)
from apps.live_control_server.services.graph_authoring_overlay_store import (
    GraphAuthoringOverlayStore,
    GraphAuthoringOverlayStoreError,
)
from apps.live_control_server.services.graph_authoring_visibility import (
    GraphAudience,
    filter_authored_overlay_for_audience,
    visibility_policy_from_projection_object,
    visibility_policy_projection_fields,
)
from graph_memory.projection.node_view import (
    GraphProjectionAdjacencyCandidate,
    GraphProjectionNodeView,
)
from graph_memory.projection.recap_projection import (
    RecapGraphProjection,
    RecapProjectionMention,
    splice_node_link_spans,
)

AUTHORED_SOURCE_DOMAIN = "authored_overlay"
_LINK_EXISTING_MENTION_OPERATIONS = frozenset({"alias", "link_existing", "reference"})
_DMB_NODE_LINK_PATTERN = re.compile(r"\[([^\]]*)\]\(dmb-node:([^)]+)\)")


class GraphAuthoringOverlayDiagnostic(BaseModel):
    model_config = ConfigDict(extra="forbid")

    code: str
    message: str
    assertion_id: str | None = None
    severity: Literal["info", "warning", "error"] = "warning"


class AuthoredOverlayProjectionSummary(BaseModel):
    model_config = ConfigDict(extra="forbid")

    loaded: bool
    overlay_path: str | None = None
    assertion_count: int = 0
    projected_node_count: int = 0
    projected_link_existing_count: int = 0
    projected_relationship_count: int = 0
    projected_merge_objects_count: int = 0
    diagnostics: list[GraphAuthoringOverlayDiagnostic] = Field(default_factory=list)


def authored_object_node_id(assertion_id: str) -> str:
    return f"authored:{assertion_id}"


def authored_manual_node_id(label: str, kind: str | None = None) -> str:
    key = f"{label.strip().lower()}|{(kind or '').strip().lower()}"
    digest = hashlib.sha256(key.encode("utf-8")).hexdigest()[:16]
    return f"authored:manual:{digest}"


def authored_relationship_edge_id(assertion_id: str) -> str:
    return f"authored-rel:{assertion_id}"


def _resolve_store(corpus_root: Path | None) -> GraphAuthoringOverlayStore:
    if corpus_root is None:
        from src.live_play.recap_stage_paths import corpus_root as default_corpus_root

        return GraphAuthoringOverlayStore(default_corpus_root())
    return GraphAuthoringOverlayStore(corpus_root)


def load_authored_overlay_for_review(
    *,
    campaign_id: str,
    campaign_rel: str | None = None,
    corpus_root: Path | None = None,
) -> tuple[AuthoredGraphOverlay | None, AuthoredOverlayProjectionSummary]:
    store = _resolve_store(corpus_root)
    overlay_path = store.overlay_path(campaign_id, campaign_rel=campaign_rel)
    if not overlay_path.is_file():
        return None, AuthoredOverlayProjectionSummary(
            loaded=False,
            overlay_path=str(overlay_path),
            diagnostics=[
                GraphAuthoringOverlayDiagnostic(
                    code="authored_overlay_missing",
                    message="No authored overlay file committed for this campaign yet.",
                    severity="info",
                )
            ],
        )
    try:
        overlay = store.load_overlay(campaign_id, campaign_rel=campaign_rel)
    except (GraphAuthoringOverlayStoreError, ValidationError) as exc:
        return None, AuthoredOverlayProjectionSummary(
            loaded=False,
            overlay_path=str(overlay_path),
            diagnostics=[
                GraphAuthoringOverlayDiagnostic(
                    code="authored_overlay_schema_error",
                    message=str(exc),
                    severity="error",
                )
            ],
        )
    active_assertions = [item for item in overlay.assertions if item.status == "authored"]
    return overlay, AuthoredOverlayProjectionSummary(
        loaded=True,
        overlay_path=str(overlay_path),
        assertion_count=len(active_assertions),
    )


def _existing_graph_node_refs_from_assertion(
    assertion: AuthoredGraphAssertion,
) -> list[AuthoredGraphObjectRef]:
    if assertion.assertion_kind == "link_existing":
        return [assertion.existing_object_ref]
    if assertion.assertion_kind == "relationship":
        return [assertion.source_object_ref, assertion.target_object_ref]
    if assertion.assertion_kind == "merge_objects":
        return [assertion.survivor_object_ref, *assertion.merged_object_refs]
    return []


def _materialize_external_existing_node_view(
    ref: AuthoredGraphObjectRef,
    *,
    assertion: AuthoredGraphAssertion,
    source_anchor_text: str | None = None,
    initial_aliases: list[str] | None = None,
) -> GraphProjectionNodeView:
    return _authored_node_view(
        node_id=ref.node_id or "",
        label=ref.label,
        kind=ref.kind,
        role=ref.role,
        aliases=list(initial_aliases or []),
        summary=None,
        assertion_id=assertion.assertion_id,
        visibility_policy=assertion.visibility,
        graph_scope=list(assertion.graph_scope),
        source_anchor_text=source_anchor_text,
    )


def _local_proposal_node_map(
    assertions: list[AuthoredGraphAssertion],
) -> dict[str, str]:
    mapping: dict[str, str] = {}
    for assertion in assertions:
        if assertion.assertion_kind != "object" or assertion.status != "authored":
            continue
        local_proposal_id = assertion.object_ref.local_proposal_id
        if local_proposal_id:
            mapping[local_proposal_id] = authored_object_node_id(assertion.assertion_id)
    return mapping


def _resolve_object_ref_node_id(
    ref: AuthoredGraphObjectRef,
    *,
    existing_node_ids: set[str],
    local_proposal_nodes: dict[str, str],
    diagnostics: list[GraphAuthoringOverlayDiagnostic],
    assertion_id: str,
    context: str,
) -> str | None:
    if ref.ref_kind == "existing_graph_node":
        if ref.node_id and ref.node_id in existing_node_ids:
            return ref.node_id
        diagnostics.append(
            GraphAuthoringOverlayDiagnostic(
                code="authored_overlay_assertion_unresolved_ref",
                message=f"{context}: existing graph node {ref.node_id!r} was not found in projection.",
                assertion_id=assertion_id,
            )
        )
        return None
    if ref.ref_kind == "local_proposal":
        if ref.local_proposal_id and ref.local_proposal_id in local_proposal_nodes:
            node_id = local_proposal_nodes[ref.local_proposal_id]
            if node_id in existing_node_ids:
                return node_id
        diagnostics.append(
            GraphAuthoringOverlayDiagnostic(
                code="authored_overlay_assertion_unresolved_ref",
                message=f"{context}: local proposal ref {ref.local_proposal_id!r} could not be resolved.",
                assertion_id=assertion_id,
            )
        )
        return None
    if ref.ref_kind == "authored_node":
        if ref.authored_node_id and ref.authored_node_id in existing_node_ids:
            return ref.authored_node_id
        if ref.authored_node_id and ref.authored_node_id.startswith("authored:"):
            return ref.authored_node_id
        diagnostics.append(
            GraphAuthoringOverlayDiagnostic(
                code="authored_overlay_assertion_unresolved_ref",
                message=f"{context}: authored node ref {ref.authored_node_id!r} was not found.",
                assertion_id=assertion_id,
            )
        )
        return None
    if ref.ref_kind == "manual_ref":
        return authored_manual_node_id(ref.label, ref.kind)
    return None


def _authored_node_view(
    *,
    node_id: str,
    label: str,
    kind: str | None,
    role: str | None,
    aliases: list[str],
    summary: str | None,
    assertion_id: str,
    visibility_policy: GraphVisibilityPolicy,
    graph_scope: list[str],
    source_anchor_text: str | None = None,
) -> GraphProjectionNodeView:
    extras: dict[str, Any] = {
        "source": AUTHORED_SOURCE_DOMAIN,
        "authored": True,
        "assertion_id": assertion_id,
        "graph_scope": graph_scope,
        **visibility_policy_projection_fields(visibility_policy),
    }
    if source_anchor_text:
        extras["source_anchor_text"] = source_anchor_text
    return GraphProjectionNodeView(
        node_id=node_id,
        label=label,
        kind=kind or "entity",
        role=role or "authored",
        aliases=list(aliases),
        source_domains=[AUTHORED_SOURCE_DOMAIN],
        evidence_badges=[],
        adjacency=[],
        suggested_expansions=[],
        anchored_to_focus_session=False,
        summary=summary,
        **extras,
    )


def build_authored_projection_node_views(
    overlay: AuthoredGraphOverlay,
    *,
    base_node_views: dict[str, GraphProjectionNodeView] | None = None,
    existing_node_ids: set[str] | None = None,
    diagnostics: list[GraphAuthoringOverlayDiagnostic] | None = None,
) -> dict[str, GraphProjectionNodeView]:
    node_views: dict[str, GraphProjectionNodeView] = {}
    unresolved = diagnostics if diagnostics is not None else []
    known_ids = set(existing_node_ids or ())
    base_views = base_node_views or {}
    active_assertions = [item for item in overlay.assertions if item.status == "authored"]

    for assertion in active_assertions:
        for ref in _existing_graph_node_refs_from_assertion(assertion):
            if ref.ref_kind != "existing_graph_node" or not ref.node_id or ref.node_id in known_ids:
                continue
            if ref.node_id in base_views:
                node_views[ref.node_id] = base_views[ref.node_id]
            elif ref.node_id not in node_views:
                node_views[ref.node_id] = _materialize_external_existing_node_view(
                    ref,
                    assertion=assertion,
                )
            known_ids.add(ref.node_id)

    for assertion in active_assertions:
        if assertion.assertion_kind != "object":
            continue
        node_id = authored_object_node_id(assertion.assertion_id)
        node_views[node_id] = _authored_node_view(
            node_id=node_id,
            label=assertion.object_ref.label,
            kind=assertion.object_ref.kind,
            role=assertion.object_ref.role,
            aliases=list(assertion.aliases),
            summary=assertion.summary,
            assertion_id=assertion.assertion_id,
            visibility_policy=assertion.visibility,
            graph_scope=list(assertion.graph_scope),
            source_anchor_text=(
                assertion.source_anchor.normalized_selected_text
                if assertion.source_anchor
                else None
            ),
        )
        known_ids.add(node_id)

    for assertion in active_assertions:
        if assertion.assertion_kind != "link_existing":
            continue
        link_assertion: AuthoredGraphLinkExistingAssertion = assertion
        ref = link_assertion.existing_object_ref
        alias_text = (link_assertion.alias_text or link_assertion.normalized_selected_text).strip()
        if ref.ref_kind == "existing_graph_node" and ref.node_id and ref.node_id in known_ids:
            existing = node_views.get(ref.node_id) or base_views.get(ref.node_id)
            if existing is None:
                continue
            updated_aliases = list(existing.aliases)
            if alias_text and alias_text not in updated_aliases:
                updated_aliases.append(alias_text)
            source_domains = list(existing.source_domains)
            if AUTHORED_SOURCE_DOMAIN not in source_domains:
                source_domains.append(AUTHORED_SOURCE_DOMAIN)
            node_views[ref.node_id] = existing.model_copy(
                update={
                    "aliases": updated_aliases,
                    "source_domains": source_domains,
                    "authored": True,
                    "assertion_id": link_assertion.assertion_id,
                    "source_anchor_text": link_assertion.normalized_selected_text,
                    **visibility_policy_projection_fields(link_assertion.visibility),
                }
            )
            continue
        manual_node_id = _resolve_object_ref_node_id(
            ref,
            existing_node_ids=known_ids,
            local_proposal_nodes=_local_proposal_node_map(active_assertions),
            diagnostics=unresolved,
            assertion_id=link_assertion.assertion_id,
            context="link_existing",
        )
        if manual_node_id is None:
            continue
        aliases = [alias_text] if alias_text else []
        if ref.label not in aliases:
            aliases.insert(0, ref.label)
        node_views[manual_node_id] = _authored_node_view(
            node_id=manual_node_id,
            label=ref.label,
            kind=ref.kind,
            role=ref.role,
            aliases=aliases,
            summary=None,
            assertion_id=link_assertion.assertion_id,
            visibility_policy=link_assertion.visibility,
            graph_scope=list(link_assertion.graph_scope),
            source_anchor_text=link_assertion.normalized_selected_text,
        )
        known_ids.add(manual_node_id)

    return node_views


def build_authored_projection_relationship_views(
    overlay: AuthoredGraphOverlay,
    node_views: dict[str, GraphProjectionNodeView],
    *,
    diagnostics: list[GraphAuthoringOverlayDiagnostic] | None = None,
) -> list[GraphProjectionAdjacencyCandidate]:
    unresolved = diagnostics if diagnostics is not None else []
    active_assertions = [item for item in overlay.assertions if item.status == "authored"]
    local_proposal_nodes = _local_proposal_node_map(active_assertions)
    existing_node_ids = set(node_views.keys())
    relationships: list[GraphProjectionAdjacencyCandidate] = []

    for assertion in active_assertions:
        if assertion.assertion_kind != "relationship":
            continue
        rel_assertion: AuthoredGraphRelationshipAssertion = assertion
        source_id = _resolve_object_ref_node_id(
            rel_assertion.source_object_ref,
            existing_node_ids=existing_node_ids,
            local_proposal_nodes=local_proposal_nodes,
            diagnostics=unresolved,
            assertion_id=rel_assertion.assertion_id,
            context="relationship source",
        )
        target_id = _resolve_object_ref_node_id(
            rel_assertion.target_object_ref,
            existing_node_ids=existing_node_ids,
            local_proposal_nodes=local_proposal_nodes,
            diagnostics=unresolved,
            assertion_id=rel_assertion.assertion_id,
            context="relationship target",
        )
        if not source_id or not target_id:
            unresolved.append(
                GraphAuthoringOverlayDiagnostic(
                    code="authored_overlay_relationship_skipped",
                    message=(
                        f"Skipped relationship {rel_assertion.relationship_type} "
                        f"from {rel_assertion.source_object_ref.label} to "
                        f"{rel_assertion.target_object_ref.label} due to unresolved endpoint."
                    ),
                    assertion_id=rel_assertion.assertion_id,
                )
            )
            continue
        if source_id not in node_views or target_id not in node_views:
            unresolved.append(
                GraphAuthoringOverlayDiagnostic(
                    code="authored_overlay_relationship_skipped",
                    message=(
                        f"Skipped relationship {rel_assertion.relationship_type} because "
                        f"endpoint nodes were missing from node views."
                    ),
                    assertion_id=rel_assertion.assertion_id,
                )
            )
            continue
        target_view = node_views[target_id]
        edge_id = authored_relationship_edge_id(rel_assertion.assertion_id)
        predicate = rel_assertion.relationship_type
        edge_label = rel_assertion.relationship_label or (
            f"{node_views[source_id].label} {predicate} {target_view.label}"
        )
        relationships.append(
            GraphProjectionAdjacencyCandidate(
                edge_id=edge_id,
                node_id=target_id,
                label=target_view.label,
                kind=target_view.kind,
                predicate=predicate,
                direction="outgoing",
                anchored_to_focus_session=False,
                source_domains=[AUTHORED_SOURCE_DOMAIN],
                evidence_ref_ids=[],
                edge_label=edge_label,
                session_ids=[rel_assertion.session_id] if rel_assertion.session_id else [],
                source=AUTHORED_SOURCE_DOMAIN,
                authored=True,
                assertion_id=rel_assertion.assertion_id,
                summary=rel_assertion.summary,
                **visibility_policy_projection_fields(rel_assertion.visibility),
            )
        )
    return relationships


def _spans_overlap(left: tuple[int, int], right: tuple[int, int]) -> bool:
    return left[0] < right[1] and left[1] > right[0]


def _collect_dmb_node_link_spans(markdown: str) -> list[tuple[int, int, str, str]]:
    return [
        (match.start(), match.end(), match.group(1), match.group(2))
        for match in _DMB_NODE_LINK_PATTERN.finditer(markdown)
    ]


def _occupied_spans_from_markdown(markdown: str) -> list[tuple[int, int]]:
    return [(start, end) for start, end, _, _ in _collect_dmb_node_link_spans(markdown)]


def _link_existing_node_id(
    assertion: AuthoredGraphLinkExistingAssertion,
    *,
    merged_node_views: dict[str, GraphProjectionNodeView],
    local_proposal_nodes: dict[str, str],
    diagnostics: list[GraphAuthoringOverlayDiagnostic],
) -> str | None:
    ref = assertion.existing_object_ref
    if ref.ref_kind == "existing_graph_node" and ref.node_id and ref.node_id in merged_node_views:
        return ref.node_id
    return _resolve_object_ref_node_id(
        ref,
        existing_node_ids=set(merged_node_views.keys()),
        local_proposal_nodes=local_proposal_nodes,
        diagnostics=diagnostics,
        assertion_id=assertion.assertion_id,
        context="link_existing mention",
    )


def _normalize_context_text(text: str) -> str:
    return re.sub(r"\s+", " ", text.strip().lower())


def _context_tokens(text: str, *, from_end: bool, count: int = 8) -> str:
    tokens = [token for token in _normalize_context_text(text).split(" ") if token]
    if not tokens:
        return ""
    clipped = tokens[-count:] if from_end else tokens[:count]
    return " ".join(clipped)


def _context_match_score(
    markdown: str,
    span: tuple[int, int],
    *,
    source_anchor: GraphAuthoringSourceAnchor | None,
) -> float:
    if source_anchor is None:
        return 0.0
    before = (source_anchor.surrounding_text_before or "").strip()
    after = (source_anchor.surrounding_text_after or "").strip()
    if not before and not after:
        return 0.0

    start, end = span
    prefix = _normalize_context_text(markdown[max(0, start - 180) : start])
    suffix = _normalize_context_text(markdown[end : min(len(markdown), end + 180)])
    score = 0.0

    norm_before = _normalize_context_text(before)
    if norm_before:
        if norm_before in prefix:
            score += 100 + len(norm_before)
        else:
            before_tail = _context_tokens(before, from_end=True)
            if before_tail and before_tail in prefix:
                score += 60 + len(before_tail)

    norm_after = _normalize_context_text(after)
    if norm_after:
        if norm_after in suffix:
            score += 100 + len(norm_after)
        else:
            after_head = _context_tokens(after, from_end=False)
            if after_head and after_head in suffix:
                score += 60 + len(after_head)

    return score


def _context_prefers_span(
    markdown: str,
    span: tuple[int, int],
    *,
    source_anchor: GraphAuthoringSourceAnchor | None,
) -> bool:
    return _context_match_score(markdown, span, source_anchor=source_anchor) > 0


def _paragraph_spans(markdown: str) -> list[tuple[int, int]]:
    spans: list[tuple[int, int]] = []
    cursor = 0
    for part in re.split(r"(\n\s*\n+)", markdown):
        if not part or not part.strip():
            cursor += len(part)
            continue
        start = cursor
        end = cursor + len(part)
        spans.append((start, end))
        cursor = end
    return spans


def _span_in_paragraph(span: tuple[int, int], paragraph: tuple[int, int]) -> bool:
    return span[0] >= paragraph[0] and span[1] <= paragraph[1]


def _filter_candidates_by_paragraph_ordinal(
    candidates: list[tuple[int, int]],
    markdown: str,
    *,
    paragraph_ordinal: int | None,
) -> list[tuple[int, int]]:
    if paragraph_ordinal is None or paragraph_ordinal < 1:
        return candidates
    paragraphs = _paragraph_spans(markdown)
    if not paragraphs:
        return candidates
    index = min(paragraph_ordinal, len(paragraphs)) - 1
    paragraph = paragraphs[index]
    filtered = [span for span in candidates if _span_in_paragraph(span, paragraph)]
    return filtered or candidates


def _source_anchor_has_context(source_anchor: GraphAuthoringSourceAnchor | None) -> bool:
    if source_anchor is None:
        return False
    return bool((source_anchor.surrounding_text_before or "").strip()) or bool(
        (source_anchor.surrounding_text_after or "").strip()
    )


def _find_authored_alias_span_in_markdown(
    markdown: str,
    selected_text: str,
    *,
    source_anchor: GraphAuthoringSourceAnchor | None,
    occupied: list[tuple[int, int]],
) -> tuple[tuple[int, int] | None, str | None]:
    """Resolve a prose span for an authored alias mention.

    Returns ``(span, diagnostic_code)``. ``diagnostic_code`` is set when the
    span is ``None`` due to ambiguous or ungrounded source-anchor resolution.
    """
    selected = selected_text.strip()
    if not selected or not markdown:
        return None, None

    pattern = re.compile(rf"(?<![\w\[]){re.escape(selected)}(?![\w\]])", re.IGNORECASE)
    candidates: list[tuple[int, int]] = []
    for match in pattern.finditer(markdown):
        span = match.span()
        if any(_spans_overlap(span, used) for used in occupied):
            continue
        candidates.append(span)

    if not candidates:
        return None, None

    if source_anchor is not None and source_anchor.paragraph_ordinal is not None:
        candidates = _filter_candidates_by_paragraph_ordinal(
            candidates,
            markdown,
            paragraph_ordinal=source_anchor.paragraph_ordinal,
        )

    if len(candidates) == 1:
        return candidates[0], None

    if _source_anchor_has_context(source_anchor):
        scored = [
            (span, _context_match_score(markdown, span, source_anchor=source_anchor))
            for span in candidates
        ]
        scored.sort(key=lambda item: item[1], reverse=True)
        best_span, best_score = scored[0]
        second_score = scored[1][1] if len(scored) > 1 else -1.0
        if best_score > 0 and best_score > second_score:
            return best_span, None
        if best_score > 0:
            top_scorers = [span for span, score in scored if score == best_score]
            if len(top_scorers) == 1:
                return top_scorers[0], None
        return None, "authored_alias_mention_ungrounded"

    return None, "authored_alias_mention_ambiguous"


def _eligible_link_existing_for_mention(
    assertion: AuthoredGraphAssertion,
) -> AuthoredGraphLinkExistingAssertion | None:
    if assertion.assertion_kind != "link_existing" or assertion.status != "authored":
        return None
    link_assertion: AuthoredGraphLinkExistingAssertion = assertion
    if link_assertion.operation not in _LINK_EXISTING_MENTION_OPERATIONS:
        return None
    selected = (
        link_assertion.normalized_selected_text
        or link_assertion.selected_text
        or (
            link_assertion.source_anchor.normalized_selected_text
            if link_assertion.source_anchor
            else None
        )
        or (
            link_assertion.source_anchor.selected_text
            if link_assertion.source_anchor
            else None
        )
    )
    if not (selected or "").strip():
        return None
    return link_assertion


def _resolve_merge_target(node_id: str, merge_map: dict[str, str]) -> str:
    seen: set[str] = set()
    current = node_id
    while current in merge_map and current not in seen:
        seen.add(current)
        current = merge_map[current]
    return current


def _transitive_merge_map(raw_map: dict[str, str]) -> dict[str, str]:
    if not raw_map:
        return {}
    resolved: dict[str, str] = {}
    for merged_id in raw_map:
        survivor = _resolve_merge_target(merged_id, raw_map)
        if survivor != merged_id:
            resolved[merged_id] = survivor
    return resolved


def _build_merge_node_id_map(
    overlay: AuthoredGraphOverlay,
    *,
    merged_node_views: dict[str, GraphProjectionNodeView],
    diagnostics: list[GraphAuthoringOverlayDiagnostic],
) -> dict[str, str]:
    active_assertions = [item for item in overlay.assertions if item.status == "authored"]
    local_proposal_nodes = _local_proposal_node_map(active_assertions)
    existing_node_ids = set(merged_node_views.keys())
    raw_map: dict[str, str] = {}

    for assertion in active_assertions:
        if assertion.assertion_kind != "merge_objects":
            continue
        merge_assertion: AuthoredGraphMergeObjectsAssertion = assertion
        survivor_id = _resolve_object_ref_node_id(
            merge_assertion.survivor_object_ref,
            existing_node_ids=existing_node_ids,
            local_proposal_nodes=local_proposal_nodes,
            diagnostics=diagnostics,
            assertion_id=merge_assertion.assertion_id,
            context="merge survivor",
        )
        if not survivor_id:
            continue
        for merged_ref in merge_assertion.merged_object_refs:
            merged_id = _resolve_object_ref_node_id(
                merged_ref,
                existing_node_ids=existing_node_ids,
                local_proposal_nodes=local_proposal_nodes,
                diagnostics=diagnostics,
                assertion_id=merge_assertion.assertion_id,
                context="merge merged-away",
            )
            if not merged_id or merged_id == survivor_id:
                continue
            raw_map[merged_id] = survivor_id

    return _transitive_merge_map(raw_map)


def _merge_node_view_into_survivor(
    survivor: GraphProjectionNodeView,
    merged: GraphProjectionNodeView,
) -> GraphProjectionNodeView:
    merged_aliases = list(survivor.aliases)
    for alias in merged.aliases:
        if alias not in merged_aliases:
            merged_aliases.append(alias)
    if merged.label and merged.label not in merged_aliases and merged.label != survivor.label:
        merged_aliases.append(merged.label)

    merged_evidence = list(survivor.evidence_badges)
    seen_evidence = {badge.evidence_ref_id for badge in merged_evidence}
    for badge in merged.evidence_badges:
        if badge.evidence_ref_id in seen_evidence:
            continue
        merged_evidence.append(badge)
        seen_evidence.add(badge.evidence_ref_id)

    merged_domains = list(survivor.source_domains)
    for domain in merged.source_domains:
        if domain not in merged_domains:
            merged_domains.append(domain)

    merged_adjacency = list(survivor.adjacency)
    existing_edge_ids = {item.edge_id for item in merged_adjacency}
    for adj in merged.adjacency:
        if adj.edge_id not in existing_edge_ids:
            merged_adjacency.append(adj)
            existing_edge_ids.add(adj.edge_id)

    summary = survivor.summary or merged.summary
    return survivor.model_copy(
        update={
            "aliases": merged_aliases,
            "evidence_badges": merged_evidence,
            "source_domains": merged_domains,
            "adjacency": merged_adjacency,
            "summary": summary,
            "authored": getattr(survivor, "authored", False) or getattr(merged, "authored", False),
        }
    )


def _redirect_markdown_node_links(markdown: str, merge_map: dict[str, str]) -> str:
    if not merge_map:
        return markdown

    def replace_node_id(match: re.Match[str]) -> str:
        label = match.group(1)
        node_id = match.group(2)
        redirected = _resolve_merge_target(node_id, merge_map)
        if redirected == node_id:
            return match.group(0)
        return f"[{label}](dmb-node:{redirected})"

    return _DMB_NODE_LINK_PATTERN.sub(replace_node_id, markdown)


def _apply_merge_map_to_node_views(
    merged_node_views: dict[str, GraphProjectionNodeView],
    merge_map: dict[str, str],
) -> dict[str, GraphProjectionNodeView]:
    if not merge_map:
        return merged_node_views

    result = dict(merged_node_views)
    for merged_id, survivor_id in merge_map.items():
        if merged_id not in result or survivor_id not in result:
            continue
        survivor = result[survivor_id]
        merged = result[merged_id]
        result[survivor_id] = _merge_node_view_into_survivor(survivor, merged)

    for merged_id in merge_map:
        result.pop(merged_id, None)

    return result


def _apply_merge_map_to_projection(
    projection: RecapGraphProjection,
    merge_map: dict[str, str],
    merged_node_views: dict[str, GraphProjectionNodeView],
) -> tuple[RecapGraphProjection, dict[str, GraphProjectionNodeView], int]:
    if not merge_map:
        return projection, merged_node_views, 0

    updated_views = _apply_merge_map_to_node_views(merged_node_views, merge_map)
    redirected_markdown = _redirect_markdown_node_links(projection.markdown, merge_map)
    updated_mentions = [
        mention.model_copy(
            update={
                "node_id": _resolve_merge_target(mention.node_id, merge_map),
            }
        )
        for mention in projection.mentions
    ]

    return (
        projection.model_copy(
            update={
                "markdown": redirected_markdown,
                "mentions": updated_mentions,
            }
        ),
        updated_views,
        len(merge_map),
    )


def _eligible_object_for_mention(
    assertion: AuthoredGraphAssertion,
) -> tuple[AuthoredGraphObjectAssertion, str] | None:
    if assertion.assertion_kind != "object" or assertion.status != "authored":
        return None
    object_assertion: AuthoredGraphObjectAssertion = assertion
    anchor = object_assertion.source_anchor
    if anchor is None:
        return None
    selected = (
        anchor.normalized_selected_text
        or anchor.selected_text
        or ""
    ).strip()
    if not selected:
        return None
    return object_assertion, selected


def _queue_authored_prose_mention(
    *,
    markdown: str,
    selected: str,
    node_id: str,
    assertion: AuthoredGraphAssertion,
    source_anchor: GraphAuthoringSourceAnchor | None,
    occupied: list[tuple[int, int]],
    pending_spans: list[tuple[int, int, str, str, AuthoredGraphAssertion, str]],
    diagnostics: list[GraphAuthoringOverlayDiagnostic],
) -> None:
    span, resolution_code = _find_authored_alias_span_in_markdown(
        markdown,
        selected,
        source_anchor=source_anchor,
        occupied=occupied,
    )
    if span is None:
        if resolution_code == "authored_alias_mention_ambiguous":
            diagnostics.append(
                GraphAuthoringOverlayDiagnostic(
                    code="authored_alias_mention_ambiguous",
                    message=(
                        f"Skipped authored mention {selected!r} because the selected text appears "
                        f"multiple times and source-anchor context did not identify exactly one occurrence."
                    ),
                    assertion_id=assertion.assertion_id,
                )
            )
            return
        if resolution_code == "authored_alias_mention_ungrounded":
            diagnostics.append(
                GraphAuthoringOverlayDiagnostic(
                    code="authored_alias_mention_ungrounded",
                    message=(
                        f"Skipped authored mention {selected!r} because source-anchor context did not "
                        f"match any occurrence in the recap prose."
                    ),
                    assertion_id=assertion.assertion_id,
                )
            )
            return
        conflicting_link = next(
            (
                linked_node_id
                for _start, _end, link_label, linked_node_id in _collect_dmb_node_link_spans(
                    markdown
                )
                if linked_node_id != node_id
                and link_label.strip().lower() == selected.lower()
            ),
            None,
        )
        if conflicting_link is not None:
            diagnostics.append(
                GraphAuthoringOverlayDiagnostic(
                    code="authored_alias_mention_conflict",
                    message=(
                        f"Skipped authored mention {selected!r} because prose span already links to "
                        f"{conflicting_link!r}."
                    ),
                    assertion_id=assertion.assertion_id,
                )
            )
        else:
            diagnostics.append(
                GraphAuthoringOverlayDiagnostic(
                    code="authored_alias_mention_skipped",
                    message=(
                        f"Could not safely locate selected text {selected!r} for authored recap mention."
                    ),
                    assertion_id=assertion.assertion_id,
                    severity="info",
                )
            )
        return

    existing_node_at_span = next(
        (
            linked_node_id
            for start, end, _link_label, linked_node_id in _collect_dmb_node_link_spans(markdown)
            if _spans_overlap(span, (start, end))
        ),
        None,
    )
    if existing_node_at_span is not None:
        if existing_node_at_span == node_id:
            return
        diagnostics.append(
            GraphAuthoringOverlayDiagnostic(
                code="authored_alias_mention_conflict",
                message=(
                    f"Skipped authored mention {selected!r} because prose span already links to "
                    f"{existing_node_at_span!r}."
                ),
                assertion_id=assertion.assertion_id,
            )
        )
        return

    operation = "create"
    if assertion.assertion_kind == "link_existing":
        operation = assertion.operation
    pending_spans.append((span[0], span[1], selected, node_id, assertion, operation))
    occupied.append(span)


def _apply_authored_link_existing_mentions(
    projection: RecapGraphProjection,
    overlay: AuthoredGraphOverlay,
    *,
    merged_node_views: dict[str, GraphProjectionNodeView],
    diagnostics: list[GraphAuthoringOverlayDiagnostic],
) -> tuple[RecapGraphProjection, int]:
    markdown = projection.markdown
    if not markdown:
        return projection, 0

    active_assertions = [item for item in overlay.assertions if item.status == "authored"]
    local_proposal_nodes = _local_proposal_node_map(active_assertions)
    occupied = _occupied_spans_from_markdown(markdown)
    pending_spans: list[tuple[int, int, str, str, AuthoredGraphAssertion, str]] = []

    for assertion in active_assertions:
        link_assertion = _eligible_link_existing_for_mention(assertion)
        if link_assertion is not None:
            selected = (
                link_assertion.normalized_selected_text
                or link_assertion.selected_text
                or (
                    link_assertion.source_anchor.normalized_selected_text
                    if link_assertion.source_anchor
                    else ""
                )
                or (
                    link_assertion.source_anchor.selected_text
                    if link_assertion.source_anchor
                    else ""
                )
            ).strip()
            node_id = _link_existing_node_id(
                link_assertion,
                merged_node_views=merged_node_views,
                local_proposal_nodes=local_proposal_nodes,
                diagnostics=diagnostics,
            )
            if not node_id:
                continue
            _queue_authored_prose_mention(
                markdown=markdown,
                selected=selected,
                node_id=node_id,
                assertion=link_assertion,
                source_anchor=link_assertion.source_anchor,
                occupied=occupied,
                pending_spans=pending_spans,
                diagnostics=diagnostics,
            )
            continue

        object_mention = _eligible_object_for_mention(assertion)
        if object_mention is None:
            continue
        object_assertion, selected = object_mention
        node_id = authored_object_node_id(object_assertion.assertion_id)
        if node_id not in merged_node_views:
            continue
        _queue_authored_prose_mention(
            markdown=markdown,
            selected=selected,
            node_id=node_id,
            assertion=object_assertion,
            source_anchor=object_assertion.source_anchor,
            occupied=occupied,
            pending_spans=pending_spans,
            diagnostics=diagnostics,
        )

    if not pending_spans:
        return projection, 0

    splice_input = [
        (start, end, label, node_id) for start, end, label, node_id, _, _ in pending_spans
    ]
    projected_markdown, projected_offsets = splice_node_link_spans(markdown, splice_input)

    existing_mentions = list(projection.mentions)
    new_mentions: list[RecapProjectionMention] = []
    grounded_count = 0

    for (start, end, label, node_id, mention_assertion, operation), offset in zip(
        pending_spans,
        projected_offsets,
        strict=False,
    ):
        if offset is None:
            continue
        grounded_count += 1
        mention_kwargs: dict[str, Any] = {
            "mention_id": f"authored-mention:{mention_assertion.assertion_id}:{start}",
            "node_id": node_id,
            "label": label,
            "start_offset": offset[0],
            "end_offset": offset[1],
            "evidence_ref_ids": [],
            "source": AUTHORED_SOURCE_DOMAIN,
            "authored": True,
            "assertion_id": mention_assertion.assertion_id,
            "operation": operation,
            "alias_text": label,
        }
        if mention_assertion.assertion_kind == "link_existing":
            mention_kwargs["target_label"] = mention_assertion.existing_object_ref.label
        elif mention_assertion.assertion_kind == "object":
            mention_kwargs["target_label"] = mention_assertion.object_ref.label
        new_mentions.append(RecapProjectionMention(**mention_kwargs))

    if grounded_count == 0:
        return projection, 0

    return (
        projection.model_copy(
            update={
                "markdown": projected_markdown,
                "mentions": [*existing_mentions, *new_mentions],
            }
        ),
        grounded_count,
    )


def apply_authored_overlay_to_graph_review_projection(
    projection: RecapGraphProjection,
    overlay: AuthoredGraphOverlay | None,
    *,
    summary: AuthoredOverlayProjectionSummary | None = None,
    audience: GraphAudience | None = None,
) -> tuple[RecapGraphProjection, AuthoredOverlayProjectionSummary]:
    if overlay is None:
        return projection, summary or AuthoredOverlayProjectionSummary(loaded=False)

    overlay_for_projection = (
        filter_authored_overlay_for_audience(overlay, audience)
        if audience is not None
        else overlay
    )

    diagnostics: list[GraphAuthoringOverlayDiagnostic] = list(summary.diagnostics if summary else [])
    merged_node_views = dict(projection.node_views)
    authored_nodes = build_authored_projection_node_views(
        overlay_for_projection,
        base_node_views=merged_node_views,
        existing_node_ids=set(merged_node_views.keys()),
        diagnostics=diagnostics,
    )
    for node_id, authored_view in authored_nodes.items():
        if node_id in merged_node_views:
            existing = merged_node_views[node_id]
            merged_aliases = list(existing.aliases)
            for alias in authored_view.aliases:
                if alias not in merged_aliases:
                    merged_aliases.append(alias)
            source_domains = list(existing.source_domains)
            if AUTHORED_SOURCE_DOMAIN not in source_domains:
                source_domains.append(AUTHORED_SOURCE_DOMAIN)
            merged_node_views[node_id] = existing.model_copy(
                update={
                    "aliases": merged_aliases,
                    "source_domains": source_domains,
                    "authored": True,
                    "assertion_id": getattr(authored_view, "assertion_id", None),
                    "source_anchor_text": getattr(authored_view, "source_anchor_text", None),
                    **visibility_policy_projection_fields(
                        visibility_policy_from_projection_object(authored_view)
                    ),
                }
            )
        else:
            merged_node_views[node_id] = authored_view

    relationship_views = build_authored_projection_relationship_views(
        overlay_for_projection,
        merged_node_views,
        diagnostics=diagnostics,
    )
    for relationship in relationship_views:
        source_candidates = [
            assertion
            for assertion in overlay_for_projection.assertions
            if assertion.assertion_kind == "relationship"
            and assertion.status == "authored"
            and authored_relationship_edge_id(assertion.assertion_id) == relationship.edge_id
        ]
        if not source_candidates:
            continue
        rel_assertion = source_candidates[0]
        assert isinstance(rel_assertion, AuthoredGraphRelationshipAssertion)
        source_id = _resolve_object_ref_node_id(
            rel_assertion.source_object_ref,
            existing_node_ids=set(merged_node_views.keys()),
            local_proposal_nodes=_local_proposal_node_map(
                [item for item in overlay_for_projection.assertions if item.status == "authored"]
            ),
            diagnostics=diagnostics,
            assertion_id=rel_assertion.assertion_id,
            context="relationship source",
        )
        if not source_id or source_id not in merged_node_views:
            continue
        source_view = merged_node_views[source_id]
        if any(item.edge_id == relationship.edge_id for item in source_view.adjacency):
            continue
        merged_node_views[source_id] = source_view.model_copy(
            update={"adjacency": [*source_view.adjacency, relationship]}
        )

    projection_with_mentions, _grounded_alias_count = _apply_authored_link_existing_mentions(
        projection,
        overlay_for_projection,
        merged_node_views=merged_node_views,
        diagnostics=diagnostics,
    )

    merge_map = _build_merge_node_id_map(
        overlay_for_projection,
        merged_node_views=merged_node_views,
        diagnostics=diagnostics,
    )
    projection_with_mentions, merged_node_views, projected_merge_count = _apply_merge_map_to_projection(
        projection_with_mentions,
        merge_map,
        merged_node_views,
    )

    active_count = sum(
        1 for item in overlay_for_projection.assertions if item.status == "authored"
    )
    projected_object_count = sum(
        1
        for item in overlay_for_projection.assertions
        if item.status == "authored" and item.assertion_kind == "object"
    )
    projected_link_existing_count = sum(
        1
        for item in overlay_for_projection.assertions
        if item.status == "authored" and item.assertion_kind == "link_existing"
    )
    projected_merge_assertion_count = sum(
        1
        for item in overlay_for_projection.assertions
        if item.status == "authored" and item.assertion_kind == "merge_objects"
    )
    result_summary = AuthoredOverlayProjectionSummary(
        loaded=True,
        overlay_path=summary.overlay_path if summary else None,
        assertion_count=active_count,
        projected_node_count=projected_object_count,
        projected_link_existing_count=projected_link_existing_count,
        projected_relationship_count=len(relationship_views),
        projected_merge_objects_count=projected_merge_count or projected_merge_assertion_count,
        diagnostics=diagnostics,
    )
    return projection_with_mentions.model_copy(update={"node_views": merged_node_views}), result_summary


def enrich_projection_payload_with_authored_overlay(
    payload: dict[str, Any],
    *,
    campaign_id: str,
    campaign_rel: str | None = None,
    corpus_root: Path | None = None,
) -> dict[str, Any]:
    projection = RecapGraphProjection.model_validate(payload)
    overlay, summary = load_authored_overlay_for_review(
        campaign_id=campaign_id,
        campaign_rel=campaign_rel,
        corpus_root=corpus_root,
    )
    enriched, overlay_summary = apply_authored_overlay_to_graph_review_projection(
        projection,
        overlay,
        summary=summary,
    )
    result = enriched.model_dump(mode="json")
    result["authored_overlay"] = overlay_summary.model_dump(mode="json")
    return result
