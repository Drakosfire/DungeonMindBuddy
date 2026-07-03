"""Read-only existing-object resolver suggestions for graph review cards."""

from __future__ import annotations

import difflib
import re
from pathlib import Path
from typing import Any, Literal

from pydantic import BaseModel, Field

from apps.live_control_server.config import repo_root
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


class GraphReviewExistingObjectResolverResponse(BaseModel):
    schema: Literal["dmb_graph_review_existing_object_resolver_response_v1"] = RESPONSE_SCHEMA
    campaign_id: str
    session_id: str
    selected_node_id: str
    selected_label: str
    candidates: list[GraphReviewExistingObjectCandidate] = Field(default_factory=list)
    warnings: list[str] = Field(default_factory=list)


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


def resolve_existing_object_candidates(
    request: GraphReviewExistingObjectResolverRequest,
    *,
    root: Path | None = None,
) -> GraphReviewExistingObjectResolverResponse:
    repo = (root or repo_root()).resolve()
    warnings: list[str] = []
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
        warnings.append("No resolver sources were available; no campaign-wide identity search was performed.")
    candidates: list[GraphReviewExistingObjectCandidate] = []
    selected_source = "gold_fixture" if request.lane_role == "gold" else "live_projection"
    for row in source_rows:
        if row["candidate_id"] == request.selected_node.node_id and row["source"] == selected_source:
            continue
        score, matched, reasons = _score(request.selected_node, row)
        if score < 0.2:
            continue
        candidates.append(GraphReviewExistingObjectCandidate(
            candidate_id=row["candidate_id"], label=row["label"], kind=row.get("kind"), role=row.get("role"),
            confidence=_confidence(score), score=round(score, 2),
            reason=", ".join(reasons) if reasons else "deterministic v1 heuristic match",
            source=row.get("source", "unknown"), suggested_action=_suggested_action(score),
            existing_object_ref={"source": str(row.get("source", "unknown")), "object_id": row["candidate_id"]},
            matched_features=matched,
        ))
    candidates.sort(key=lambda c: (-c.score, c.label))
    if not candidates and source_rows:
        warnings.append("Resolver sources were available, but no likely existing objects passed the v1 heuristic threshold.")
    return GraphReviewExistingObjectResolverResponse(
        campaign_id=request.campaign_id, session_id=request.session_id,
        selected_node_id=request.selected_node.node_id, selected_label=request.selected_node.label,
        candidates=candidates[:8], warnings=warnings,
    )
