"""Fresh native proof validation for an owner-reviewed candidate."""
from __future__ import annotations

from uuid import UUID

from application_state import guest_release
from apps.live_control_server.services.guest_release_evidence import verify_relationship_citation, verify_source_citation
from apps.live_control_server.services.guest_release_native_graph import read_player_graph
from apps.live_control_server.services.guest_release_sources import contains_unsupported_destination


class GuestReleaseValidationError(ValueError):
    """The candidate cannot be validated at the native source cutoff."""


def validate_candidate(*, world_id: str, subject: str, release_id: UUID, digest: str) -> int:
    """Revalidate selected Graph and citations against one fresh player view.

    Return the Core source epoch for private publication accounting. The caller
    must atomically recheck APP ownership, visibility and pointer CAS afterward.
    """
    material = guest_release.validation_material(world_id=world_id, subject=subject,
                                                  release_id=release_id, digest=digest)
    binding, projection, access = read_player_graph(managed_world_id=world_id,
                                                     revision_id=material["graph_revision"])
    if (binding.native_world_id != material["native_world_id"]
        or binding.binding_version != material["binding_version"]
        or projection.snapshot.admissibility != "player" or projection.summary.projection_truncated):
        raise GuestReleaseValidationError("Native Graph binding or projection changed")
    native_nodes = {node.node_id: node for node in projection.nodes}
    native_edges = {edge.edge_id: edge for edge in projection.relationships}
    graph = material["manifest"].get("graph", {})
    public_nodes = {node["id"]: node for node in graph.get("nodes", [])}
    public_edges = {edge["id"]: edge for edge in graph.get("edges", [])}
    sources = {source["id"]: source for source in material["manifest"].get("sources", [])}
    source_bindings = {str(item[0]): item for item in material["source_bindings"]}
    node_bindings = {str(local): native for local, native in material["node_bindings"]}
    evidence_bindings = {str(local): (native, evidence, str(excerpt))
                         for local, native, evidence, excerpt in material["evidence_bindings"]}
    if (len(native_nodes) != len(projection.nodes) or len(native_edges) != len(projection.relationships)
        or set(public_nodes) != set(node_bindings) or set(public_edges) != set(evidence_bindings)
        or set(sources) != set(source_bindings)):
        raise GuestReleaseValidationError("Release binding closure failed")
    for excerpt_id, source_binding in source_bindings.items():
        verify_source_citation(evidence_id=source_binding[10], access=access, excerpt=sources[excerpt_id],
            source_binding=source_binding[:9], expected_native_world_id=binding.native_world_id,
            expected_graph_revision=material["graph_revision"])
    for local_id, native_id in node_bindings.items():
        native = native_nodes.get(native_id)
        public = public_nodes[local_id]
        if (native is None or native.label == native_id or not native.label or not native.kind
            or contains_unsupported_destination(native.label) or contains_unsupported_destination(native.kind)
            or public != {"id": local_id, "label": native.label, "kind": native.kind}):
            raise GuestReleaseValidationError("Released Graph node is no longer admitted")
    for local_id, (native_id, evidence_id, excerpt_id) in evidence_bindings.items():
        native = native_edges.get(native_id)
        public = public_edges[local_id]
        if native is None or excerpt_id not in sources or excerpt_id not in source_bindings:
            raise GuestReleaseValidationError("Released relationship is no longer admitted")
        expected_source = next((key for key, value in node_bindings.items() if value == native.source_node_id), None)
        expected_target = next((key for key, value in node_bindings.items() if value == native.target_node_id), None)
        if (expected_source is None or expected_target is None or contains_unsupported_destination(native.label)
            or public != {"id": local_id, "source": expected_source, "target": expected_target,
                          "label": native.label, "citations": [excerpt_id]}):
            raise GuestReleaseValidationError("Released relationship differs from native Graph")
        verify_relationship_citation(edge=native, evidence_id=evidence_id, access=access,
            excerpt=sources[excerpt_id], source_binding=source_bindings[excerpt_id][:9],
            expected_native_world_id=binding.native_world_id, expected_graph_revision=material["graph_revision"])
    return access.source_view.epoch


def publish_candidate(*, world_id: str, subject: str, release_id: UUID, digest: str,
                      expected_version: int, operation_id: UUID) -> tuple[UUID, int]:
    """Validate a fresh cutoff, then atomically commit or recover publication."""
    previous = guest_release.recover_publication(world_id=world_id, subject=subject, release_id=release_id,
        digest=digest, expected_version=expected_version, operation_id=operation_id)
    if previous is not None:
        return previous
    try:
        epoch = validate_candidate(world_id=world_id, subject=subject, release_id=release_id, digest=digest)
    except Exception:
        # An identical concurrent attempt may have committed after the first
        # receipt lookup, causing candidate validation to see published state.
        previous = guest_release.recover_publication(world_id=world_id, subject=subject, release_id=release_id,
            digest=digest, expected_version=expected_version, operation_id=operation_id)
        if previous is not None:
            return previous
        raise
    return guest_release.commit_validated_promotion(world_id=world_id, subject=subject, release_id=release_id,
        digest=digest, expected_version=expected_version, operation_id=operation_id, source_epoch=epoch)
