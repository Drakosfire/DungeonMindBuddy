"""Read-only existing-object resolver suggestions for graph review cards."""

from __future__ import annotations

import difflib
import re
from pathlib import Path
from typing import Any, Literal

from pydantic import BaseModel, Field

from apps.live_control_server.config import repo_root
from apps.live_control_server.services.graph_object_candidate_sources import (
    GraphObjectCandidate,
    GraphObjectCandidateDiagnostic,
    GraphObjectCandidateScope,
    GraphObjectCandidateSearchContext,
    SCOPE_SOURCE_LABELS,
    resolve_campaign_rel_for_search,
    search_cross_scope_candidates,
)
from apps.live_control_server.services.graph_gold_review import (
    GraphGoldReviewError,
    _build_gold_node_views,
    _resolved_anchor_lookup,
    _session_entry,
    load_live_candidate_graph_dict,
)
from evals.graph_memory_layer.live_vs_gold_compare import parts_from_raw_graph

REQUEST_SCHEMA = "dmb_graph_review_existing_object_resolver_request_v1"
RESPONSE_SCHEMA = "dmb_graph_review_existing_object_resolver_response_v1"


class GraphReviewResolverSelectedNode(BaseModel):
    node_id: str
    label: str
    kind: str | None = None
    role: str | None = None
    aliases: list[str] = Field(default_factory=list)
    summary: str | None = None
    source_domains: list[str] = Field(default_factory=list)
    adjacent_labels: list[str] = Field(default_factory=list)
    evidence_ref_ids: list[str] = Field(default_factory=list)


class GraphReviewExistingObjectResolverRequest(BaseModel):
    schema: Literal["dmb_graph_review_existing_object_resolver_request_v1"] = REQUEST_SCHEMA
    campaign_id: str
    session_id: str
    lane_role: Literal["gold", "live"]
    selected_node: GraphReviewResolverSelectedNode
    projection_graph_id: str | None = None
    live_run_manifest_path: str | None = None
    query: str | None = None
    node_views: dict[str, Any] | None = None
    scopes: list[GraphObjectCandidateScope] | None = None
    include_authored_overlay: bool = True
    include_current_projection: bool = True
    include_worldbuilding: bool = True
    include_party_pc: bool = True
    include_gm_private: bool = True
    include_campaign_memory: bool = True
    max_results_per_scope: int = 12


class GraphReviewExistingObjectCandidate(BaseModel):
    candidate_id: str
    label: str
    kind: str | None = None
    role: str | None = None
    confidence: Literal["high", "medium", "low"]
    score: float
    reason: str
    source: Literal[
        "gold_fixture",
        "live_projection",
        "union_supergraph",
        "manual_review_variant",
        "unknown",
    ]
    suggested_action: Literal[
        "link_existing_later",
        "create_new_later",
        "manual_review_needed",
    ]
    existing_object_ref: dict[str, str] | None = None
    matched_features: list[str] = Field(default_factory=list)
    graph_scope: GraphObjectCandidateScope | None = None
    source_label: str | None = None
    source_path: str | None = None
    source_graph_id: str | None = None
    visibility: str | None = None
    aliases: list[str] = Field(default_factory=list)
    authored: bool = False


class GraphReviewExistingObjectResolverResponse(BaseModel):
    schema: Literal["dmb_graph_review_existing_object_resolver_response_v1"] = RESPONSE_SCHEMA
    campaign_id: str
    session_id: str
    selected_node_id: str
    selected_label: str
    candidates: list[GraphReviewExistingObjectCandidate] = Field(default_factory=list)
    warnings: list[str] = Field(default_factory=list)
    scopes_searched: list[GraphObjectCandidateScope] = Field(default_factory=list)
    diagnostics: list[GraphObjectCandidateDiagnostic] = Field(default_factory=list)


def _norm(value: str | None) -> str:
    return re.sub(r"[^a-z0-9]+", " ", (value or "").lower()).strip()


def _confidence(score: float) -> Literal["high", "medium", "low"]:
    if score >= 0.85:
        return "high"
    if score >= 0.55:
        return "medium"
    return "low"


def _suggested_action(score: float) -> Literal["link_existing_later", "create_new_later", "manual_review_needed"]:
    if score >= 0.85:
        return "link_existing_later"
    if score >= 0.35:
        return "manual_review_needed"
    return "create_new_later"


def _score(selected: GraphReviewResolverSelectedNode, candidate: dict[str, Any]) -> tuple[float, list[str], list[str]]:
    score = 0.0
    matched: list[str] = []
    reasons: list[str] = []
    selected_label = _norm(selected.label)
    candidate_label = _norm(str(candidate.get("label") or ""))
    candidate_aliases = [_norm(str(a)) for a in candidate.get("aliases") or []]
    if selected_label and selected_label == candidate_label:
        score += 0.62; matched.append("exact label match"); reasons.append("exact label match")
    elif selected_label and selected_label in candidate_aliases:
        score += 0.56; matched.append("alias match"); reasons.append("selected label matches a candidate alias")
    else:
        ratio = difflib.SequenceMatcher(None, selected_label, candidate_label).ratio()
        if ratio >= 0.72:
            score += 0.38; matched.append("similar label"); reasons.append("similar label")
        elif ratio < 0.28:
            score -= 0.15; reasons.append("weak label similarity")
    kind = _norm(selected.kind)
    candidate_kind = _norm(str(candidate.get("kind") or candidate.get("node_type") or ""))
    if kind and candidate_kind:
        if kind == candidate_kind:
            score += 0.18; matched.append("same kind"); reasons.append("same kind")
        else:
            score -= 0.18; reasons.append("different kind")
    role = _norm(selected.role)
    candidate_role = _norm(str(candidate.get("role") or (candidate.get("semantic_state") or {}).get("evidence_role") or ""))
    if role and candidate_role and (role == candidate_role or role in candidate_role or candidate_role in role):
        score += 0.08; matched.append("compatible role"); reasons.append("compatible role")
    adjacent = {_norm(v) for v in selected.adjacent_labels if _norm(v)}
    candidate_adjacent = {_norm(v) for v in candidate.get("adjacent_labels") or [] if _norm(v)}
    shared_adjacent = sorted(adjacent & candidate_adjacent)
    if shared_adjacent:
        score += min(0.12, 0.04 * len(shared_adjacent)); matched.append("shared adjacent labels"); reasons.append("shared adjacent object")
    domains = {_norm(v) for v in selected.source_domains if _norm(v)}
    cand_domains = {_norm(v) for v in candidate.get("source_domains") or [] if _norm(v)}
    if domains & cand_domains:
        score += 0.05; matched.append("overlapping source domains"); reasons.append("overlapping source domains")
    score += 0.08; matched.append("same session/campaign"); reasons.append("same session/campaign")
    return max(0.0, min(1.0, score)), matched, reasons


def _candidate_dicts_from_gold(session_id: str) -> list[dict[str, Any]]:
    entry = _session_entry(session_id)
    graph = entry["load_gold_graph_dict"]()
    parts = parts_from_raw_graph(graph)
    views = _build_gold_node_views(parts, _resolved_anchor_lookup(entry["fixture_key"]), session_id=session_id)
    return [
        {
            "candidate_id": view.node_id,
            "label": view.label,
            "kind": view.kind,
            "role": view.role,
            "aliases": view.aliases,
            "source_domains": view.source_domains,
            "adjacent_labels": [adj.label for adj in view.adjacency],
            "source": "gold_fixture",
        }
        for view in views.values()
    ]


def _candidate_dicts_from_live(repo: Path, manifest_path: str | None) -> list[dict[str, Any]]:
    if not manifest_path:
        return []
    graph = load_live_candidate_graph_dict(repo, manifest_path)
    parts = parts_from_raw_graph(graph)
    nodes = [n for n in parts.get("nodes", []) if isinstance(n, dict)]
    return [
        {
            "candidate_id": str(n.get("node_id") or n.get("id") or n.get("label")),
            "label": str(n.get("label") or n.get("node_id") or ""),
            "kind": str(n.get("kind") or n.get("node_type") or "") or None,
            "role": str(n.get("role") or (n.get("semantic_state") or {}).get("evidence_role") or "") or None,
            "aliases": [str(a) for a in n.get("aliases") or []],
            "source_domains": ["live_projection"],
            "adjacent_labels": [],
            "source": "live_projection",
        }
        for n in nodes
    ]


def _legacy_source_for_scope(scope: GraphObjectCandidateScope) -> Literal[
    "gold_fixture",
    "live_projection",
    "union_supergraph",
    "manual_review_variant",
    "unknown",
]:
    if scope == GraphObjectCandidateScope.current_recap_projection:
        return "live_projection"
    if scope == GraphObjectCandidateScope.authored_overlay:
        return "union_supergraph"
    if scope in {
        GraphObjectCandidateScope.worldbuilding,
        GraphObjectCandidateScope.campaign_memory,
        GraphObjectCandidateScope.party_pc,
        GraphObjectCandidateScope.gm_private,
    }:
        return "union_supergraph"
    return "unknown"


def _candidate_from_cross_scope(row: GraphObjectCandidate) -> GraphReviewExistingObjectCandidate:
    return GraphReviewExistingObjectCandidate(
        candidate_id=row.node_id,
        label=row.label,
        kind=row.kind,
        role=row.role,
        confidence=_confidence(row.score),
        score=round(row.score, 2),
        reason=row.match_reason,
        source=_legacy_source_for_scope(row.source.scope),
        suggested_action=_suggested_action(row.score),
        existing_object_ref={
            "source": row.source.scope.value,
            "object_id": row.node_id,
            "source_label": row.source.source_label,
        },
        matched_features=[row.match_reason],
        graph_scope=row.source.scope,
        source_label=row.source.source_label,
        source_path=row.source.source_path,
        source_graph_id=row.source.source_graph_id,
        visibility=row.source.visibility,
        aliases=list(row.aliases),
        authored=row.authored,
    )


def _merge_candidates(
    legacy: list[GraphReviewExistingObjectCandidate],
    cross_scope: list[GraphReviewExistingObjectCandidate],
) -> list[GraphReviewExistingObjectCandidate]:
    merged: dict[tuple[str, str], GraphReviewExistingObjectCandidate] = {}
    for candidate in legacy:
        scope_key = candidate.graph_scope.value if candidate.graph_scope else candidate.source
        merged[(scope_key, candidate.candidate_id)] = candidate
    for candidate in cross_scope:
        scope_key = candidate.graph_scope.value if candidate.graph_scope else candidate.source
        key = (scope_key, candidate.candidate_id)
        existing = merged.get(key)
        if existing is None or candidate.score > existing.score:
            merged[key] = candidate
    return sorted(merged.values(), key=lambda item: (-item.score, item.label.lower()))


def resolve_existing_object_candidates(
    request: GraphReviewExistingObjectResolverRequest,
    *,
    root: Path | None = None,
) -> GraphReviewExistingObjectResolverResponse:
    repo = (root or repo_root()).resolve()
    warnings: list[str] = []
    diagnostics: list[GraphObjectCandidateDiagnostic] = []
    scopes_searched: list[GraphObjectCandidateScope] = []
    entry = _session_entry(request.session_id)
    if entry["campaign_id"] is not None and entry["campaign_id"] != request.campaign_id:
        raise GraphGoldReviewError(
            f"session {request.session_id} belongs to {entry['campaign_id']}, not {request.campaign_id}",
            status_code=422,
        )
    source_rows: list[dict[str, Any]] = []
    try:
        source_rows.extend(_candidate_dicts_from_gold(request.session_id))
    except GraphGoldReviewError as exc:
        warnings.append(f"Gold fixture source unavailable: {exc}")
    try:
        source_rows.extend(_candidate_dicts_from_live(repo, request.live_run_manifest_path))
    except GraphGoldReviewError as exc:
        warnings.append(f"Live projection source unavailable: {exc}")
    if not source_rows:
        warnings.append("No same-session gold/live resolver sources were available.")
    legacy_candidates: list[GraphReviewExistingObjectCandidate] = []
    selected_source = "gold_fixture" if request.lane_role == "gold" else "live_projection"
    for row in source_rows:
        if row["candidate_id"] == request.selected_node.node_id and row["source"] == selected_source:
            continue
        score, matched, reasons = _score(request.selected_node, row)
        if score < 0.2:
            continue
        legacy_candidates.append(GraphReviewExistingObjectCandidate(
            candidate_id=row["candidate_id"], label=row["label"], kind=row.get("kind"), role=row.get("role"),
            confidence=_confidence(score), score=round(score, 2),
            reason=", ".join(reasons) if reasons else "deterministic v1 heuristic match",
            source=row.get("source", "unknown"), suggested_action=_suggested_action(score),
            existing_object_ref={"source": str(row.get("source", "unknown")), "object_id": row["candidate_id"]},
            matched_features=matched,
            graph_scope=GraphObjectCandidateScope.current_recap_projection
            if row.get("source") == "live_projection"
            else None,
            source_label=SCOPE_SOURCE_LABELS.get(GraphObjectCandidateScope.current_recap_projection)
            if row.get("source") == "live_projection"
            else None,
            aliases=[str(alias) for alias in row.get("aliases") or []],
        ))
    legacy_candidates.sort(key=lambda c: (-c.score, c.label))

    search_query = (request.query or request.selected_node.label or "").strip()
    cross_scope_candidates: list[GraphReviewExistingObjectCandidate] = []
    if search_query:
        cross_rows, cross_diag, scopes_searched = search_cross_scope_candidates(
            GraphObjectCandidateSearchContext(
                campaign_id=request.campaign_id,
                session_id=request.session_id,
                query=search_query,
                node_views=request.node_views,
                live_run_manifest_path=request.live_run_manifest_path,
                campaign_rel=resolve_campaign_rel_for_search(request.campaign_id),
                scopes=request.scopes,
                include_authored_overlay=request.include_authored_overlay,
                include_current_projection=request.include_current_projection,
                include_worldbuilding=request.include_worldbuilding,
                include_party_pc=request.include_party_pc,
                include_gm_private=request.include_gm_private,
                include_campaign_memory=request.include_campaign_memory,
                max_results_per_scope=request.max_results_per_scope,
                corpus_root=None,
                repo_root=repo,
            )
        )
        diagnostics.extend(cross_diag)
        cross_scope_candidates = [_candidate_from_cross_scope(row) for row in cross_rows]

    candidates = _merge_candidates(legacy_candidates, cross_scope_candidates)
    if not candidates and (source_rows or scopes_searched):
        warnings.append(
            "Resolver sources were available, but no likely existing objects matched the search query."
        )
    return GraphReviewExistingObjectResolverResponse(
        campaign_id=request.campaign_id, session_id=request.session_id,
        selected_node_id=request.selected_node.node_id, selected_label=request.selected_node.label,
        candidates=candidates[: max(8, request.max_results_per_scope * 2)],
        warnings=warnings,
        scopes_searched=scopes_searched,
        diagnostics=diagnostics,
    )
