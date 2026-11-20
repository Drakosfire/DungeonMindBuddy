"""Create a closed, release-local graph projection from an authorized snapshot.

This module does not load or authorize source data and cannot publish a release.
Callers must obtain the player-admissible projection from the verified WorldGraph
binding and require explicit owner selections before calling it.
"""
from __future__ import annotations

from uuid import UUID, uuid4

from graph_memory.projection.world_projection import WorldGraphProjection
from apps.live_control_server.services.guest_release_evidence import verify_relationship_citation
from apps.live_control_server.services.guest_release_sources import contains_unsupported_destination


class GuestReleaseProjectionError(ValueError):
    """The selected graph cannot be safely closed into a release."""


def project_selected_graph(
    projection: WorldGraphProjection,
    *,
    expected_world_id: str,
    expected_revision: str,
    selected_node_ids: set[str],
    selected_edge_ids: set[str],
    citation_selections: dict | None = None,
    source_access=None,
    private_evidence_bindings: list | None = None,
    private_node_bindings: list | None = None,
) -> dict:
    """Copy selected nodes and relationships without host IDs or metadata.

    Every selected relationship must have an exact admitted supporting excerpt.
    """
    snapshot = projection.snapshot
    if (not expected_world_id or not expected_revision
        or snapshot.world_id != expected_world_id
        or snapshot.revision_id != expected_revision
        or snapshot.admissibility != "player" or snapshot.scope_mode != "world"
        or projection.summary.projection_truncated):
        raise GuestReleaseProjectionError("Graph snapshot is unavailable or incomplete")
    if len(selected_node_ids) > 500 or len(selected_edge_ids) > 1000:
        raise GuestReleaseProjectionError("Graph selection is too large")
    nodes = {item.node_id: item for item in projection.nodes}
    edges = {item.edge_id: item for item in projection.relationships}
    if (len(nodes) != len(projection.nodes) or len(edges) != len(projection.relationships)
        or not selected_node_ids <= nodes.keys() or not selected_edge_ids <= edges.keys()):
        raise GuestReleaseProjectionError("Graph selection is not present in snapshot")
    selections = citation_selections or {}
    if set(selections) != selected_edge_ids or (selected_edge_ids and source_access is None):
        raise GuestReleaseProjectionError("Every relationship requires verified supporting evidence")
    local_ids = {node_id: str(uuid4()) for node_id in sorted(selected_node_ids)}
    if private_node_bindings is not None:
        private_node_bindings.extend((UUID(local_ids[node_id]), node_id) for node_id in sorted(selected_node_ids))
    result_nodes = []
    for node_id in sorted(selected_node_ids):
        node = nodes[node_id]
        # Native presentation falls back to the private entity ID when no name
        # is admitted. Such a fallback is not a release-safe label.
        if (not node.label or node.label == node_id or not node.kind
            or contains_unsupported_destination(node.label) or contains_unsupported_destination(node.kind)
            or len(node.label) > 500 or len(node.kind) > 100):
            raise GuestReleaseProjectionError("Graph node label is invalid")
        result_nodes.append({"id": local_ids[node_id], "label": node.label, "kind": node.kind})
    result_edges = []
    for edge_id in sorted(selected_edge_ids):
        edge = edges[edge_id]
        if (edge.source_node_id not in local_ids or edge.target_node_id not in local_ids
            or not edge.label or len(edge.label) > 500 or contains_unsupported_destination(edge.label)):
            raise GuestReleaseProjectionError("Graph relationship is not closed")
        evidence_id, excerpt, source_binding = selections[edge_id]
        citation = verify_relationship_citation(edge=edge, evidence_id=evidence_id, access=source_access,
            excerpt=excerpt, source_binding=source_binding, expected_native_world_id=expected_world_id,
            expected_graph_revision=expected_revision)
        local_edge_id = uuid4()
        if private_evidence_bindings is not None:
            private_evidence_bindings.append((local_edge_id, edge_id, evidence_id, citation))
        result_edges.append({"id": str(local_edge_id), "source": local_ids[edge.source_node_id],
                             "target": local_ids[edge.target_node_id], "label": edge.label,
                             "citations": [citation]})
    return {"nodes": result_nodes, "edges": result_edges}
