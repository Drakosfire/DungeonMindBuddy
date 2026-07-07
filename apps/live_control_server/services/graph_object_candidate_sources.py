"""Cross-scope graph object candidate loaders for existing-object resolution (A7)."""

from __future__ import annotations

import re
from enum import Enum
from pathlib import Path
from typing import Any, Literal

from pydantic import BaseModel, Field

from apps.live_control_server.services.graph_authoring_overlay_projection import (
    build_authored_projection_node_views,
    load_authored_overlay_for_review,
)
from apps.live_control_server.services.graph_gold_review import (
    GraphGoldReviewError,
    _session_entry,
    load_live_candidate_graph_dict,
)
from apps.live_control_server.services.party_registry_surface import (
    build_party_registry_surface,
)
from apps.live_control_server.services.union_supergraph_projection_adapter import (
    load_preview_union_store_from_graph_run_manifest,
)
from evals.graph_memory_layer.live_vs_gold_compare import parts_from_raw_graph
from graph_memory.union_supergraph.load import (
    DEFAULT_FIXTURE_PATH,
    load_union_supergraph_store,
)
from src.graph_memory.party_context import resolve_campaign_corpus
from src.live_play.recap_stage_paths import corpus_root


class GraphObjectCandidateScope(str, Enum):
    current_recap_projection = "current_recap_projection"
    authored_overlay = "authored_overlay"
    campaign_memory = "campaign_memory"
    worldbuilding = "worldbuilding"
    party_pc = "party_pc"
    gm_private = "gm_private"


SCOPE_SOURCE_LABELS: dict[GraphObjectCandidateScope, str] = {
    GraphObjectCandidateScope.current_recap_projection: "Current recap",
    GraphObjectCandidateScope.authored_overlay: "Authored memory",
    GraphObjectCandidateScope.campaign_memory: "Campaign memory",
    GraphObjectCandidateScope.worldbuilding: "Worldbuilding",
    GraphObjectCandidateScope.party_pc: "Party / PCs",
    GraphObjectCandidateScope.gm_private: "GM private",
}

WORLDBUILDING_SOURCE_DOMAINS = frozenset(
    {"worldbuilding", "location_note", "faction_note", "npc_note", "item_note"}
)
CAMPAIGN_MEMORY_SOURCE_DOMAINS = frozenset({"session_memory", "recap", "manual_seed"})


class GraphObjectCandidateSource(BaseModel):
    scope: GraphObjectCandidateScope
    source_label: str
    source_path: str | None = None
    source_graph_id: str | None = None
    visibility: str | None = None


class GraphObjectCandidateDiagnostic(BaseModel):
    code: str
    message: str
    scope: GraphObjectCandidateScope | None = None
    severity: Literal["info", "warning", "error"] = "info"


class GraphObjectCandidate(BaseModel):
    node_id: str
    label: str
    kind: str | None = None
    role: str | None = None
    aliases: list[str] = Field(default_factory=list)
    summary: str | None = None
    source: GraphObjectCandidateSource
    match_reason: str
    score: float
    authored: bool = False


class GraphObjectCandidateSearchContext(BaseModel):
    campaign_id: str
    session_id: str
    query: str
    node_views: dict[str, Any] | None = None
    live_run_manifest_path: str | None = None
    campaign_rel: str | None = None
    scopes: list[GraphObjectCandidateScope] | None = None
    include_authored_overlay: bool = True
    include_current_projection: bool = True
    include_worldbuilding: bool = True
    include_party_pc: bool = True
    include_gm_private: bool = True
    include_campaign_memory: bool = True
    max_results_per_scope: int = 12
    corpus_root: Path | None = None
    repo_root: Path | None = None


def normalize_candidate_text(text: str) -> str:
    return re.sub(r"[^a-z0-9]+", " ", (text or "").lower()).strip()


def score_query_match(
    query: str,
    *,
    label: str,
    aliases: list[str] | None = None,
    source_anchors: list[str] | None = None,
) -> tuple[float, str] | None:
    normalized_query = normalize_candidate_text(query)
    if not normalized_query:
        return None

    normalized_label = normalize_candidate_text(label)
    normalized_aliases = [normalize_candidate_text(alias) for alias in (aliases or []) if alias]
    normalized_anchors = [
        normalize_candidate_text(anchor) for anchor in (source_anchors or []) if anchor
    ]

    if normalized_query == normalized_label:
        return 1.0, "Exact label match"
    for alias in normalized_aliases:
        if normalized_query == alias:
            return 0.95, f"Alias match: {alias}"
    if normalized_label and normalized_query in normalized_label:
        return 0.65, "Substring label match"
    for alias in normalized_aliases:
        if alias and normalized_query in alias:
            return 0.6, f"Substring alias match: {alias}"
    for anchor in normalized_anchors:
        if anchor and normalized_query == anchor:
            return 0.55, f"Matched authored source anchor: {anchor}"
    if normalized_label and normalized_label in normalized_query:
        return 0.85, "Normalized label match"
    for alias in normalized_aliases:
        if alias and alias in normalized_query:
            return 0.8, f"Normalized alias match: {alias}"
    return None


def _dedupe_key(scope: GraphObjectCandidateScope, node_id: str) -> tuple[str, str]:
    return (scope.value, node_id)


def _rank_and_cap(
    rows: list[GraphObjectCandidate],
    *,
    max_results: int,
) -> list[GraphObjectCandidate]:
    rows.sort(key=lambda row: (-row.score, row.label.lower(), row.node_id))
    return rows[:max_results]


def _load_union_supergraph_store(
    *,
    campaign_id: str,
    live_run_manifest_path: str | None,
    repo: Path,
) -> Any | None:
    if live_run_manifest_path:
        try:
            return load_preview_union_store_from_graph_run_manifest(Path(live_run_manifest_path))
        except (FileNotFoundError, ValueError, GraphGoldReviewError):
            pass
    if campaign_id == "longmont-c2" and DEFAULT_FIXTURE_PATH.is_file():
        return load_union_supergraph_store(DEFAULT_FIXTURE_PATH)
    return None


def _session_number(session_id: str) -> int | None:
    try:
        entry = _session_entry(session_id)
    except GraphGoldReviewError:
        return None
    return entry.get("session_number")


def _is_authored_projection_node(raw: dict[str, Any]) -> bool:
    if raw.get("authored") is True:
        return True
    source_domains = raw.get("source_domains") or []
    if isinstance(source_domains, list) and "authored_overlay" in source_domains:
        return True
    node_id = str(raw.get("node_id") or "")
    return node_id.startswith("authored:")


def _rows_from_node_views(
    node_views: dict[str, Any],
    *,
    scope: GraphObjectCandidateScope,
    source_graph_id: str | None = None,
) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for node_id, raw in node_views.items():
        if not isinstance(raw, dict):
            continue
        label = str(raw.get("label") or node_id)
        rows.append(
            {
                "node_id": str(raw.get("node_id") or node_id),
                "label": label,
                "kind": raw.get("kind"),
                "role": raw.get("role"),
                "aliases": [str(alias) for alias in raw.get("aliases") or []],
                "summary": raw.get("summary"),
                "authored": _is_authored_projection_node(raw),
                "source_anchors": [raw.get("source_anchor_text")]
                if raw.get("source_anchor_text")
                else [],
                "scope": scope,
                "source_graph_id": source_graph_id,
            }
        )
    return rows


def _authored_projection_node_views(node_views: dict[str, Any] | None) -> dict[str, Any]:
    if not node_views:
        return {}
    return {
        node_id: raw
        for node_id, raw in node_views.items()
        if isinstance(raw, dict) and _is_authored_projection_node(raw)
    }


def _recap_projection_node_views(node_views: dict[str, Any] | None) -> dict[str, Any]:
    if not node_views:
        return {}
    return {
        node_id: raw
        for node_id, raw in node_views.items()
        if isinstance(raw, dict) and not _is_authored_projection_node(raw)
    }


def _load_current_recap_rows(context: GraphObjectCandidateSearchContext) -> tuple[list[dict[str, Any]], list[GraphObjectCandidateDiagnostic]]:
    diagnostics: list[GraphObjectCandidateDiagnostic] = []
    if context.node_views:
        recap_views = _recap_projection_node_views(context.node_views)
        if not recap_views:
            diagnostics.append(
                GraphObjectCandidateDiagnostic(
                    code="candidate_scope_empty",
                    message="Current recap projection has no non-authored node views.",
                    scope=GraphObjectCandidateScope.current_recap_projection,
                )
            )
        return (
            _rows_from_node_views(
                recap_views,
                scope=GraphObjectCandidateScope.current_recap_projection,
            ),
            diagnostics,
        )
    if not context.live_run_manifest_path or context.repo_root is None:
        diagnostics.append(
            GraphObjectCandidateDiagnostic(
                code="candidate_scope_unavailable",
                message="Current recap projection node views were not provided.",
                scope=GraphObjectCandidateScope.current_recap_projection,
            )
        )
        return [], diagnostics
    try:
        graph = load_live_candidate_graph_dict(context.repo_root, context.live_run_manifest_path)
    except GraphGoldReviewError as exc:
        diagnostics.append(
            GraphObjectCandidateDiagnostic(
                code="candidate_scope_load_failed",
                message=f"Current recap projection unavailable: {exc}",
                scope=GraphObjectCandidateScope.current_recap_projection,
                severity="warning",
            )
        )
        return [], diagnostics
    parts = parts_from_raw_graph(graph)
    node_views = {
        str(node.get("node_id") or node.get("id") or node.get("label")): node
        for node in parts.get("nodes", [])
        if isinstance(node, dict)
    }
    if not node_views:
        diagnostics.append(
            GraphObjectCandidateDiagnostic(
                code="candidate_scope_empty",
                message="Current recap projection has no node views.",
                scope=GraphObjectCandidateScope.current_recap_projection,
            )
        )
    return (
        _rows_from_node_views(
            node_views,
            scope=GraphObjectCandidateScope.current_recap_projection,
        ),
        diagnostics,
    )


def _load_authored_overlay_rows(
    context: GraphObjectCandidateSearchContext,
) -> tuple[list[dict[str, Any]], list[GraphObjectCandidateDiagnostic]]:
    diagnostics: list[GraphObjectCandidateDiagnostic] = []
    rows = _rows_from_node_views(
        _authored_projection_node_views(context.node_views),
        scope=GraphObjectCandidateScope.authored_overlay,
        source_graph_id=f"{context.campaign_id}:authored-overlay-projection",
    )
    overlay, summary = load_authored_overlay_for_review(
        campaign_id=context.campaign_id,
        campaign_rel=context.campaign_rel,
        corpus_root=context.corpus_root,
    )
    if overlay is None:
        for item in summary.diagnostics:
            if item.code == "authored_overlay_missing":
                diagnostics.append(
                    GraphObjectCandidateDiagnostic(
                        code="authored_overlay_missing",
                        message=item.message,
                        scope=GraphObjectCandidateScope.authored_overlay,
                    )
                )
            else:
                diagnostics.append(
                    GraphObjectCandidateDiagnostic(
                        code=item.code,
                        message=item.message,
                        scope=GraphObjectCandidateScope.authored_overlay,
                        severity=item.severity,
                    )
                )
        if not rows:
            return [], diagnostics
        return rows, diagnostics
    node_views = build_authored_projection_node_views(overlay, existing_node_ids=set())
    rows.extend(
        _rows_from_node_views(
            {node_id: view.model_dump(mode="python") for node_id, view in node_views.items()},
            scope=GraphObjectCandidateScope.authored_overlay,
            source_graph_id=f"{context.campaign_id}:authored-overlay",
        )
    )
    if not rows:
        diagnostics.append(
            GraphObjectCandidateDiagnostic(
                code="candidate_scope_empty",
                message="Authored overlay loaded but has no authored assertions to search.",
                scope=GraphObjectCandidateScope.authored_overlay,
            )
        )
    return rows, diagnostics


def _load_party_pc_rows(
    context: GraphObjectCandidateSearchContext,
) -> tuple[list[dict[str, Any]], list[GraphObjectCandidateDiagnostic]]:
    diagnostics: list[GraphObjectCandidateDiagnostic] = []
    session_number = _session_number(context.session_id)
    if session_number is None:
        diagnostics.append(
            GraphObjectCandidateDiagnostic(
                code="candidate_scope_unavailable",
                message="Party / PC registry requires a numbered session.",
                scope=GraphObjectCandidateScope.party_pc,
            )
        )
        return [], diagnostics
    try:
        surface = build_party_registry_surface(
            campaign_id=context.campaign_id,
            session=session_number,
        )
    except (ValueError, FileNotFoundError) as exc:
        diagnostics.append(
            GraphObjectCandidateDiagnostic(
                code="party_graph_missing",
                message=f"Party / PC registry unavailable: {exc}",
                scope=GraphObjectCandidateScope.party_pc,
                severity="warning",
            )
        )
        return [], diagnostics
    rows: list[dict[str, Any]] = []
    for party_name in surface.party_names:
        rows.append(
            {
                "node_id": f"party:{normalize_candidate_text(party_name).replace(' ', '_')}",
                "label": party_name,
                "kind": "party",
                "role": "party",
                "aliases": [],
                "summary": None,
                "authored": False,
                "source_anchors": [],
                "scope": GraphObjectCandidateScope.party_pc,
                "source_path": surface.registry_relpath,
            }
        )
    for member in surface.members:
        rows.append(
            {
                "node_id": f"party:{member.slug}",
                "label": member.display_name,
                "kind": member.kind,
                "role": member.kind,
                "aliases": [member.slug] if member.slug.lower() != member.display_name.lower() else [],
                "summary": member.player,
                "authored": False,
                "source_anchors": [],
                "scope": GraphObjectCandidateScope.party_pc,
                "source_path": member.hub_rel_path or surface.registry_relpath,
            }
        )
    if not rows:
        diagnostics.append(
            GraphObjectCandidateDiagnostic(
                code="candidate_scope_empty",
                message="Party / PC registry loaded but returned no members.",
                scope=GraphObjectCandidateScope.party_pc,
            )
        )
    return rows, diagnostics


def _union_supergraph_rows_for_scope(
    store: Any,
    *,
    scope: GraphObjectCandidateScope,
) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    focus_session_id = getattr(store, "focus_session_id", None)
    for node_id, node in store.nodes.items():
        source_domains = set(getattr(node, "source_domains", []) or [])
        if scope == GraphObjectCandidateScope.worldbuilding:
            if not source_domains & WORLDBUILDING_SOURCE_DOMAINS:
                continue
        elif scope == GraphObjectCandidateScope.campaign_memory:
            if not source_domains & CAMPAIGN_MEMORY_SOURCE_DOMAINS:
                continue
            if focus_session_id and focus_session_id in (getattr(node, "evidence_ref_ids", []) or []):
                pass
        elif scope == GraphObjectCandidateScope.gm_private:
            visibility = _node_visibility(store, node)
            if visibility != "gm_private":
                continue
        else:
            continue
        rows.append(
            {
                "node_id": node_id,
                "label": node.label,
                "kind": node.kind,
                "role": node.role,
                "aliases": list(node.aliases or []),
                "summary": None,
                "authored": False,
                "source_anchors": [],
                "scope": scope,
                "source_graph_id": getattr(store, "graph_id", None),
                "visibility": _node_visibility(store, node),
            }
        )
    return rows


def _node_visibility(store: Any, node: Any) -> str | None:
    for evidence_ref_id in getattr(node, "evidence_ref_ids", []) or []:
        evidence = store.evidence.get(evidence_ref_id)
        if evidence is None:
            continue
        visibility = getattr(evidence, "visibility_state", None)
        if isinstance(visibility, str) and visibility:
            return visibility
        model_extra = getattr(evidence, "model_extra", None) or {}
        if isinstance(model_extra, dict):
            extra_visibility = model_extra.get("visibility_state")
            if isinstance(extra_visibility, str) and extra_visibility:
                return extra_visibility
    artifact_ids = {
        getattr(store.evidence.get(ref_id), "source_artifact_id", None)
        for ref_id in getattr(node, "evidence_ref_ids", []) or []
    }
    for artifact_id in artifact_ids:
        if not artifact_id:
            continue
        artifact = store.source_artifacts.get(artifact_id)
        if artifact is None:
            continue
        visibility = getattr(artifact, "visibility_state", None)
        if isinstance(visibility, str) and visibility:
            return visibility
    return None


def _load_union_scope_rows(
    context: GraphObjectCandidateSearchContext,
    scope: GraphObjectCandidateScope,
) -> tuple[list[dict[str, Any]], list[GraphObjectCandidateDiagnostic]]:
    diagnostics: list[GraphObjectCandidateDiagnostic] = []
    if context.repo_root is None:
        diagnostics.append(
            GraphObjectCandidateDiagnostic(
                code="candidate_scope_unavailable",
                message=f"{SCOPE_SOURCE_LABELS[scope]} search requires a repo root.",
                scope=scope,
            )
        )
        return [], diagnostics
    store = _load_union_supergraph_store(
        campaign_id=context.campaign_id,
        live_run_manifest_path=context.live_run_manifest_path,
        repo=context.repo_root,
    )
    if store is None:
        code = {
            GraphObjectCandidateScope.worldbuilding: "worldbuilding_graph_missing",
            GraphObjectCandidateScope.campaign_memory: "candidate_scope_unavailable",
            GraphObjectCandidateScope.gm_private: "gm_private_graph_missing",
        }.get(scope, "candidate_scope_unavailable")
        diagnostics.append(
            GraphObjectCandidateDiagnostic(
                code=code,
                message=f"{SCOPE_SOURCE_LABELS[scope]} graph store is not available for this campaign.",
                scope=scope,
            )
        )
        return [], diagnostics
    rows = _union_supergraph_rows_for_scope(store, scope=scope)
    if not rows:
        diagnostics.append(
            GraphObjectCandidateDiagnostic(
                code="candidate_scope_empty",
                message=f"{SCOPE_SOURCE_LABELS[scope]} graph loaded but returned no searchable nodes.",
                scope=scope,
            )
        )
    return rows, diagnostics


def _resolve_enabled_scopes(context: GraphObjectCandidateSearchContext) -> list[GraphObjectCandidateScope]:
    if context.scopes:
        return list(context.scopes)
    enabled: list[GraphObjectCandidateScope] = []
    if context.include_current_projection:
        enabled.append(GraphObjectCandidateScope.current_recap_projection)
    if context.include_authored_overlay:
        enabled.append(GraphObjectCandidateScope.authored_overlay)
    if context.include_party_pc:
        enabled.append(GraphObjectCandidateScope.party_pc)
    if context.include_worldbuilding:
        enabled.append(GraphObjectCandidateScope.worldbuilding)
    if context.include_campaign_memory:
        enabled.append(GraphObjectCandidateScope.campaign_memory)
    if context.include_gm_private:
        enabled.append(GraphObjectCandidateScope.gm_private)
    return enabled


def search_cross_scope_candidates(
    context: GraphObjectCandidateSearchContext,
) -> tuple[list[GraphObjectCandidate], list[GraphObjectCandidateDiagnostic], list[GraphObjectCandidateScope]]:
    enabled_scopes = _resolve_enabled_scopes(context)
    all_rows: list[dict[str, Any]] = []
    diagnostics: list[GraphObjectCandidateDiagnostic] = []
    scopes_searched: list[GraphObjectCandidateScope] = []

    for scope in enabled_scopes:
        scopes_searched.append(scope)
        if scope == GraphObjectCandidateScope.current_recap_projection:
            rows, scope_diag = _load_current_recap_rows(context)
        elif scope == GraphObjectCandidateScope.authored_overlay:
            rows, scope_diag = _load_authored_overlay_rows(context)
        elif scope == GraphObjectCandidateScope.party_pc:
            rows, scope_diag = _load_party_pc_rows(context)
        elif scope in {
            GraphObjectCandidateScope.worldbuilding,
            GraphObjectCandidateScope.campaign_memory,
            GraphObjectCandidateScope.gm_private,
        }:
            rows, scope_diag = _load_union_scope_rows(context, scope)
        else:
            rows, scope_diag = [], [
                GraphObjectCandidateDiagnostic(
                    code="candidate_scope_unavailable",
                    message=f"Unsupported candidate scope: {scope.value}",
                    scope=scope,
                )
            ]
        diagnostics.extend(scope_diag)
        all_rows.extend(rows)

    by_key: dict[tuple[str, str], GraphObjectCandidate] = {}

    for row in all_rows:
        scope = row.get("scope")
        if not isinstance(scope, GraphObjectCandidateScope):
            continue
        scored = score_query_match(
            context.query,
            label=str(row.get("label") or ""),
            aliases=list(row.get("aliases") or []),
            source_anchors=list(row.get("source_anchors") or []),
        )
        if scored is None:
            continue
        score, match_reason = scored
        node_id = str(row.get("node_id") or row.get("label"))
        key = _dedupe_key(scope, node_id)
        candidate = GraphObjectCandidate(
            node_id=node_id,
            label=str(row.get("label") or node_id),
            kind=row.get("kind"),
            role=row.get("role"),
            aliases=list(row.get("aliases") or []),
            summary=row.get("summary"),
            source=GraphObjectCandidateSource(
                scope=scope,
                source_label=SCOPE_SOURCE_LABELS[scope],
                source_path=row.get("source_path"),
                source_graph_id=row.get("source_graph_id"),
                visibility=row.get("visibility"),
            ),
            match_reason=match_reason,
            score=score,
            authored=bool(row.get("authored")),
        )
        existing = by_key.get(key)
        if existing is None or candidate.score > existing.score:
            by_key[key] = candidate

    grouped: dict[GraphObjectCandidateScope, list[GraphObjectCandidate]] = {
        scope: [] for scope in enabled_scopes
    }
    for candidate in by_key.values():
        grouped[candidate.source.scope].append(candidate)

    merged: list[GraphObjectCandidate] = []
    for scope in enabled_scopes:
        merged.extend(_rank_and_cap(grouped[scope], max_results=context.max_results_per_scope))
    return merged, diagnostics, scopes_searched


def resolve_campaign_rel_for_search(campaign_id: str) -> str | None:
    try:
        _, rel = resolve_campaign_corpus(campaign_id, corpus_root=corpus_root())
        return rel
    except ValueError:
        return None
