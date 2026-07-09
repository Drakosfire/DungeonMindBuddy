"""Import missing session-scoped edges from sibling ingest union stores."""

from __future__ import annotations

from pathlib import Path

from graph_memory.union_supergraph.load import load_union_supergraph_store
from graph_memory.union_supergraph.merge_reconciliation import (
    MergeAssertionPlan,
    ReconciliationDiagnostic,
)
from graph_memory.union_supergraph.model import (
    UnionSupergraphEdge,
    UnionSupergraphEvidence,
    UnionSupergraphNode,
    UnionSupergraphStore,
)


_GENERIC_CLUSTER_TOKENS = frozenset(
    {
        "party",
        "node",
        "character",
        "location",
        "organization",
        "thread",
        "item",
        "group",
        "authored",
        "edge",
        "loc",
        "pc",
        "npc",
    }
)


def _distinctive_cluster_tokens(cluster_tokens: set[str]) -> set[str]:
    return {token for token in cluster_tokens if token not in _GENERIC_CLUSTER_TOKENS}


def _normalize_label(value: str) -> str:
    return " ".join(value.split()).casefold()


def _slug_tokens(*values: str) -> set[str]:
    tokens: set[str] = set()
    for value in values:
        for part in value.replace(":", "_").replace("-", "_").split("_"):
            normalized = part.strip().casefold()
            if len(normalized) >= 4:
                tokens.add(normalized)
    return tokens


def _cluster_identity_tokens(
    assertion_plan: MergeAssertionPlan,
    store: UnionSupergraphStore,
) -> set[str]:
    tokens: set[str] = set()
    candidate_ids = [
        assertion_plan.survivor_node_id,
        *assertion_plan.merged_away_node_ids,
        *assertion_plan.merged_away_original_refs,
    ]
    tokens.update(_slug_tokens(*candidate_ids))
    for node_id in candidate_ids:
        node = store.nodes.get(node_id)
        if node is None:
            continue
        tokens.add(_normalize_label(node.label))
        for alias in node.aliases:
            tokens.add(_normalize_label(alias))
    return {token for token in tokens if token}


def _node_matches_cluster(
    node_id: str,
    node: UnionSupergraphNode,
    cluster_tokens: set[str],
) -> bool:
    distinctive_tokens = _distinctive_cluster_tokens(cluster_tokens)
    if any(token in node_id.casefold() for token in distinctive_tokens):
        return True
    labels = {_normalize_label(node.label)}
    labels.update(_normalize_label(alias) for alias in node.aliases)
    return bool(labels & cluster_tokens)


def _peer_union_store_paths(
    union_store_path: Path,
    *,
    limit: int = 8,
) -> list[Path]:
    session_dir = union_store_path.parent.parent
    if not session_dir.is_dir():
        return []
    peers: list[Path] = []
    for candidate in sorted(session_dir.glob("*/preview_union_supergraph.json")):
        if candidate.resolve() == union_store_path.resolve():
            continue
        peers.append(candidate)
    peers.sort(key=lambda path: path.stat().st_mtime, reverse=True)
    return peers[:limit]


def _edge_endpoint_key(edge: UnionSupergraphEdge) -> tuple[str, str, str]:
    return (edge.source_node_id, edge.predicate, edge.target_node_id)


def _import_node_if_missing(
    store: UnionSupergraphStore,
    peer: UnionSupergraphStore,
    node_id: str,
) -> None:
    if node_id in store.nodes:
        return
    peer_node = peer.nodes.get(node_id)
    if peer_node is None:
        return
    store.nodes[node_id] = peer_node.model_copy(deep=True)


def _import_evidence_if_missing(
    store: UnionSupergraphStore,
    peer: UnionSupergraphStore,
    evidence_ref_id: str,
) -> None:
    if evidence_ref_id in store.evidence:
        return
    peer_evidence = peer.evidence.get(evidence_ref_id)
    if peer_evidence is None:
        return
    store.evidence[evidence_ref_id] = UnionSupergraphEvidence.model_validate(
        peer_evidence.model_dump(mode="json")
    )


def supplement_identity_cluster_edges_from_session_peers(
    store: UnionSupergraphStore,
    assertion_plan: MergeAssertionPlan,
    *,
    union_store_path: Path | None = None,
) -> tuple[int, list[ReconciliationDiagnostic]]:
    """Backfill cluster edges from richer sibling session union stores when missing."""
    if union_store_path is None:
        return 0, []

    cluster_tokens = _cluster_identity_tokens(assertion_plan, store)
    if not cluster_tokens:
        return 0, []

    diagnostics: list[ReconciliationDiagnostic] = []
    imported = 0
    existing_endpoint_keys = {
        _edge_endpoint_key(edge)
        for edge in store.edges.values()
        if edge.state.get("memory_state") != "rewired_from_merged_away"
    }

    for peer_path in _peer_union_store_paths(union_store_path):
        peer = load_union_supergraph_store(peer_path)
        for edge in peer.edges.values():
            if edge.state.get("memory_state") == "rewired_from_merged_away":
                continue

            source_node = peer.nodes.get(edge.source_node_id)
            target_node = peer.nodes.get(edge.target_node_id)
            if source_node is None or target_node is None:
                continue

            rewire_source = edge.source_node_id
            rewire_target = edge.target_node_id
            touches_cluster = False

            if _node_matches_cluster(edge.source_node_id, source_node, cluster_tokens):
                touches_cluster = True
                rewire_source = assertion_plan.survivor_node_id
            if _node_matches_cluster(edge.target_node_id, target_node, cluster_tokens):
                touches_cluster = True
                rewire_target = assertion_plan.survivor_node_id

            if not touches_cluster:
                continue

            endpoint_key = (rewire_source, edge.predicate, rewire_target)
            if endpoint_key in existing_endpoint_keys:
                continue

            _import_node_if_missing(store, peer, edge.source_node_id)
            _import_node_if_missing(store, peer, edge.target_node_id)
            _import_node_if_missing(store, peer, rewire_source)
            _import_node_if_missing(store, peer, rewire_target)
            for evidence_ref_id in edge.evidence_ref_ids:
                _import_evidence_if_missing(store, peer, evidence_ref_id)

            new_edge_id = (
                f"edge:imported:{assertion_plan.assertion_id}:"
                f"{rewire_source}:{edge.predicate}:{rewire_target}:{edge.edge_id}"
            )
            if new_edge_id in store.edges:
                continue

            store.edges[new_edge_id] = UnionSupergraphEdge(
                edge_id=new_edge_id,
                source_node_id=rewire_source,
                target_node_id=rewire_target,
                predicate=edge.predicate,
                label=edge.label,
                direction=edge.direction,
                source_domains=list(edge.source_domains),
                session_ids=list(edge.session_ids),
                evidence_ref_ids=list(edge.evidence_ref_ids),
                state={
                    "memory_state": "graph_read_model",
                    "imported_from_peer_store": str(peer_path),
                    "imported_from_edge_id": edge.edge_id,
                    "merge_assertion_id": assertion_plan.assertion_id,
                },
            )
            existing_endpoint_keys.add(endpoint_key)
            imported += 1

    if imported:
        diagnostics.append(
            ReconciliationDiagnostic(
                severity="info",
                code="merge_apply_imported_session_peer_edges",
                message=(
                    f"Imported {imported} session edge(s) for survivor "
                    f"{assertion_plan.survivor_node_id} from sibling union stores"
                ),
                assertion_id=assertion_plan.assertion_id,
                node_id=assertion_plan.survivor_node_id,
            )
        )

    return imported, diagnostics
