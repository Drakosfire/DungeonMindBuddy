"""Partition candidate graphs into recap-owned vs party-registry standing context.

Standing context (heroes-party, empty-evidence context anchors, member_of edges)
must not ride the recap source_extraction promote path. Partition while
``context_anchor`` is still present (extract-time), or via durable warning /
node-id fallback (promote-time for older runs).
"""

from __future__ import annotations

from copy import deepcopy
from pathlib import Path
from typing import Any, Mapping

from graph_memory.session_graph_context import PARTY_COLLECTIVE_NODE_ID

STANDING_WARNING = "context_anchor_no_session_evidence"
PARTY_REGISTRY_ARTIFACT_PREFIX = "artifact:party-registry:"
# Hybrid edges stay on the recap partition; drop if still evidence-less.
_HYBRID_RELATIONSHIP_TYPES = frozenset({"pursues", "participates_in"})


def party_registry_artifact_id(campaign_id: str) -> str:
    campaign = (campaign_id or "").strip() or "unknown"
    return f"{PARTY_REGISTRY_ARTIFACT_PREFIX}{campaign}"


def _evidence_refs(obj: Mapping[str, Any]) -> list[Any]:
    refs = obj.get("evidence_refs")
    return list(refs) if isinstance(refs, list) else []


def _warnings(obj: Mapping[str, Any]) -> list[str]:
    raw = obj.get("warnings") or []
    if not isinstance(raw, list):
        return []
    return [str(w) for w in raw]


def is_standing_context_node(node: Mapping[str, Any]) -> bool:
    """True when the node is registry standing context (not recap-evidenced)."""
    if _evidence_refs(node):
        return False
    if node.get("context_anchor") is True:
        return True
    if STANDING_WARNING in _warnings(node):
        return True
    if str(node.get("node_id") or "") == PARTY_COLLECTIVE_NODE_ID:
        return True
    return False


def is_standing_context_edge(
    edge: Mapping[str, Any],
    *,
    standing_node_ids: set[str],
) -> bool:
    """True for deterministic standing edges that only connect standing nodes."""
    if _evidence_refs(edge):
        return False
    rel = str(edge.get("relationship_type") or "").strip()
    if rel in _HYBRID_RELATIONSHIP_TYPES:
        return False
    from_id = str(edge.get("from_node_id") or "")
    to_id = str(edge.get("to_node_id") or "")
    if from_id not in standing_node_ids or to_id not in standing_node_ids:
        return False
    if edge.get("context_anchor") is True:
        return True
    if STANDING_WARNING in _warnings(edge):
        return True
    # Promote-time fallback: membership into heroes-party with empty evidence.
    if rel == "member_of" and to_id == PARTY_COLLECTIVE_NODE_ID:
        return True
    return False


def _clone_parts(parts: Mapping[str, Any]) -> dict[str, Any]:
    return {
        "nodes": [deepcopy(n) for n in (parts.get("nodes") or []) if isinstance(n, Mapping)],
        "edges": [deepcopy(e) for e in (parts.get("edges") or []) if isinstance(e, Mapping)],
        "beats": [deepcopy(b) for b in (parts.get("beats") or []) if isinstance(b, Mapping)],
        "proposed_writes": [
            deepcopy(w) for w in (parts.get("proposed_writes") or []) if isinstance(w, Mapping)
        ],
        "ignored_items": [
            deepcopy(i) for i in (parts.get("ignored_items") or []) if isinstance(i, Mapping)
        ],
        "deferred_items": [
            deepcopy(d) for d in (parts.get("deferred_items") or []) if isinstance(d, Mapping)
        ],
        "consolidation_diagnostics": dict(parts.get("consolidation_diagnostics") or {}),
    }


def partition_candidate_parts_by_provenance(
    parts: Mapping[str, Any],
) -> tuple[dict[str, Any], dict[str, Any], dict[str, Any]]:
    """Split sanitized parts into (recap_parts, standing_parts, diagnostics).

    Hybrid empty-evidence participation edges are dropped from the recap
    partition (not moved into standing — their targets are recap-owned).
    """
    nodes = [n for n in (parts.get("nodes") or []) if isinstance(n, Mapping)]
    edges = [e for e in (parts.get("edges") or []) if isinstance(e, Mapping)]

    standing_nodes = [n for n in nodes if is_standing_context_node(n)]
    standing_ids = {str(n.get("node_id") or "") for n in standing_nodes}
    standing_ids.discard("")
    pure_standing_ids = set(standing_ids)

    standing_edges: list[Mapping[str, Any]] = []
    recap_edges: list[Mapping[str, Any]] = []
    dropped_hybrid: list[str] = []
    member_from_ids: set[str] = set()
    for edge in edges:
        rel = str(edge.get("relationship_type") or "").strip()
        from_id = str(edge.get("from_node_id") or "")
        to_id = str(edge.get("to_node_id") or "")
        # All membership edges into the standing collective travel with standing
        # provenance (include from-node copies below for endpoint closure).
        if rel == "member_of" and to_id in pure_standing_ids:
            standing_edges.append(edge)
            if from_id:
                member_from_ids.add(from_id)
            continue
        if is_standing_context_edge(edge, standing_node_ids=pure_standing_ids):
            standing_edges.append(edge)
            continue
        empty = not _evidence_refs(edge)
        is_hybrid = rel in _HYBRID_RELATIONSHIP_TYPES and (
            edge.get("context_anchor") is True or STANDING_WARNING in _warnings(edge)
        )
        if empty and is_hybrid:
            dropped_hybrid.append(str(edge.get("edge_id") or ""))
            continue
        if from_id in pure_standing_ids or to_id in pure_standing_ids:
            if from_id in pure_standing_ids and to_id in pure_standing_ids:
                standing_edges.append(edge)
            else:
                dropped_hybrid.append(str(edge.get("edge_id") or ""))
            continue
        recap_edges.append(edge)

    # Endpoint closure: copy member PCs into standing even when they also remain
    # on the recap partition (mention-evidenced). Standing merges first; recap
    # identity gate then resolves_existing.
    standing_id_set = set(pure_standing_ids)
    nodes_by_id = {str(n.get("node_id") or ""): n for n in nodes}
    for mid in member_from_ids:
        if mid in standing_id_set:
            continue
        src = nodes_by_id.get(mid)
        if src is None:
            continue
        standing_nodes.append(src)
        standing_id_set.add(mid)

    recap_nodes = [n for n in nodes if str(n.get("node_id") or "") not in pure_standing_ids]

    base = _clone_parts(parts)
    recap = {
        **base,
        "nodes": [deepcopy(n) for n in recap_nodes],
        "edges": [deepcopy(e) for e in recap_edges],
    }
    standing = {
        **base,
        "nodes": [deepcopy(n) for n in standing_nodes],
        "edges": [deepcopy(e) for e in standing_edges],
        "beats": [],
        "proposed_writes": [],
        "ignored_items": [],
        "deferred_items": [],
    }
    diag = {
        "standing_node_ids": sorted(standing_id_set),
        "pure_standing_node_ids": sorted(pure_standing_ids),
        "standing_edge_ids": sorted(
            str(e.get("edge_id") or "") for e in standing_edges if e.get("edge_id")
        ),
        "dropped_hybrid_edge_ids": [eid for eid in dropped_hybrid if eid],
        "recap_node_count": len(recap_nodes),
        "standing_node_count": len(standing_nodes),
    }
    return recap, standing, diag


def partition_candidate_graph_by_provenance(
    graph: Mapping[str, Any],
) -> tuple[dict[str, Any], dict[str, Any], dict[str, Any]]:
    """Partition a full candidate graph dict (promote-time fallback for old runs)."""
    parts = {
        "nodes": list(graph.get("nodes") or []),
        "edges": list(graph.get("edges") or []),
        "beats": list(graph.get("beats") or []),
        "proposed_writes": list(graph.get("proposed_writes") or []),
        "ignored_items": list(graph.get("ignored_items") or []),
        "deferred_items": list(graph.get("deferred_items") or []),
        "consolidation_diagnostics": {},
    }
    recap_parts, standing_parts, diag = partition_candidate_parts_by_provenance(parts)
    recap_graph = dict(graph)
    standing_graph = dict(graph)
    for key in (
        "nodes",
        "edges",
        "beats",
        "proposed_writes",
        "ignored_items",
        "deferred_items",
    ):
        recap_graph[key] = recap_parts[key]
        standing_graph[key] = standing_parts[key]
    return recap_graph, standing_graph, diag


def stamp_standing_registry_evidence(
    graph: dict[str, Any],
    *,
    source_artifact_id: str,
) -> dict[str, Any]:
    """Stamp honest registry-artifact evidence on every standing node/edge.

    Replaces any prior evidence (including recap mention refs on PC nodes copied
    for membership endpoint closure) so the standing contribution verifies against
    a single party-registry artifact.
    """
    artifact = (source_artifact_id or "").strip()
    if not artifact:
        raise ValueError("source_artifact_id is required for standing registry evidence")
    ref = {
        "source_ref_id": f"source-ref:{artifact}",
        "source_artifact_id": artifact,
        "source_anchor_id": f"anchor:{artifact}:standing",
        "label": "party_registry",
        "evidence_role": "source_evidence",
        "can_open_source": True,
        "can_highlight_span": True,
        "source_span_ref_id": f"{artifact}:standing",
        "anchor_quotes": ["_party_registry.json"],
    }
    for key in ("nodes", "edges"):
        for item in graph.get(key) or []:
            if not isinstance(item, dict):
                continue
            item["evidence_refs"] = [dict(ref)]
            warnings = _warnings(item)
            if STANDING_WARNING not in warnings:
                warnings.append(STANDING_WARNING)
            item["warnings"] = warnings
    return graph


def ensure_standing_warning(graph: dict[str, Any]) -> dict[str, Any]:
    """Ensure every standing-graph object keeps a durable warning token."""
    for key in ("nodes", "edges"):
        for item in graph.get(key) or []:
            if not isinstance(item, dict):
                continue
            warnings = _warnings(item)
            if STANDING_WARNING not in warnings:
                warnings.append(STANDING_WARNING)
            item["warnings"] = warnings
    return graph


def resolve_party_registry_uri(
    campaign_id: str,
    *,
    repo_root: Path,
) -> tuple[Path, str, str]:
    """Return (absolute_path, artifact_id, repo:// relative URI) for the party registry."""
    from graph_memory.party_context import (
        party_registry_path,
        resolve_campaign_corpus,
    )

    root = repo_root.resolve()
    corpus_root, campaign_rel = resolve_campaign_corpus(campaign_id)
    # corpus_root may be relative to repo
    if not corpus_root.is_absolute():
        corpus_root = (root / corpus_root).resolve()
    path = party_registry_path(corpus_root, campaign_rel).resolve()
    if not path.is_file():
        raise FileNotFoundError(f"party registry not found: {path}")
    try:
        rel = path.relative_to(root).as_posix()
    except ValueError as exc:
        raise ValueError(f"party registry escapes repo root: {path}") from exc
    artifact_id = party_registry_artifact_id(campaign_id)
    return path, artifact_id, f"repo://{rel}"
