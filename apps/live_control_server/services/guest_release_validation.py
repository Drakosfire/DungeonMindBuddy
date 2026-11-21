"""Fresh native proof validation for an owner-reviewed candidate."""
from __future__ import annotations

from uuid import UUID

from application_state import guest_release
from application_state.guest_release_example import validate_example
from apps.live_control_server.services.guest_release_evidence import verify_source_citation
from apps.live_control_server.services.guest_release_native_graph import read_owner_graph
from apps.live_control_server.services.guest_release_assertions import select_node, select_relationship


class GuestReleaseValidationError(ValueError):
    """The candidate cannot be validated at the native source cutoff."""


def validate_candidate(*, world_id: str, subject: str, release_id: UUID, digest: str) -> int:
    """Revalidate explicit selections against one fresh private owner view.

    Return the Core source epoch for private publication accounting. The caller
    must atomically recheck APP ownership, visibility and pointer CAS afterward.
    """
    material = guest_release.validation_material(world_id=world_id, subject=subject,
                                                  release_id=release_id, digest=digest)
    binding, context, support, access = read_owner_graph(managed_world_id=world_id,
                                                          revision_id=material["graph_revision"])
    if (binding.native_world_id != material["native_world_id"]
        or binding.binding_version != material["binding_version"]):
        raise GuestReleaseValidationError("Native Graph binding or projection changed")
    graph = material["manifest"].get("graph", {})
    public_nodes = {node["id"]: node for node in graph.get("nodes", [])}
    public_edges = {edge["id"]: edge for edge in graph.get("edges", [])}
    sources = {source["id"]: source for source in material["manifest"].get("sources", [])}
    source_bindings = {str(item[0]): item for item in material["source_bindings"]}
    validate_example(material["manifest"], material["source_bindings"])
    node_bindings = {str(item[0]): item for item in material["node_bindings"]}
    evidence_bindings = {str(local): (native, evidence, str(excerpt))
                         for local, native, evidence, excerpt in material["evidence_bindings"]}
    if (len(public_nodes) != len(graph.get("nodes", [])) or len(public_edges) != len(graph.get("edges", []))
        or len(node_bindings) != len(material["node_bindings"]) or len(evidence_bindings) != len(material["evidence_bindings"])
        or set(public_nodes) != set(node_bindings) or set(public_edges) != set(evidence_bindings)
        or set(sources) != set(source_bindings)):
        raise GuestReleaseValidationError("Release binding closure failed")
    for excerpt_id, source_binding in source_bindings.items():
        verify_source_citation(evidence_id=source_binding[10], access=access, excerpt=sources[excerpt_id],
            source_binding=source_binding[:9], expected_native_world_id=binding.native_world_id,
            expected_graph_revision=material["graph_revision"])
    def citation(evidence_id, excerpt_id):
        key = str(excerpt_id)
        if key not in sources or key not in source_bindings or source_bindings[key][10] != evidence_id:
            raise GuestReleaseValidationError("Selected citation binding changed")
        return evidence_id, sources[key], source_bindings[key][:9]

    common = dict(context=context, admitted_ids=set(support.listing.admitted_assertion_ids), access=access,
                  native_world_id=binding.native_world_id, revision_id=material["graph_revision"])
    local_ids = {item[1]: local_id for local_id, item in node_bindings.items()}
    if len(local_ids) != len(node_bindings):
        raise GuestReleaseValidationError("Duplicate native Graph node")
    for local_id, item in node_bindings.items():
        _, entity, name, name_ev, name_excerpt, kind, kind_ev, kind_excerpt = item
        expected, _ = select_node(**common, entity_id=entity, name_assertion_id=name, kind_assertion_id=kind,
            name_evidence=citation(name_ev, name_excerpt), kind_evidence=citation(kind_ev, kind_excerpt),
            local_id=UUID(local_id))
        if public_nodes[local_id] != expected:
            raise GuestReleaseValidationError("Released Graph node is no longer admitted")
    for local_id, (native_id, evidence_id, excerpt_id) in evidence_bindings.items():
        native = context.parsed.get_assertion(native_id)
        if native is None:
            raise GuestReleaseValidationError("Released relationship is no longer admitted")
        expected, _ = select_relationship(**common, assertion_id=native_id, subject_id=native.subject_entity_id,
            predicate=native.predicate, node_ids=local_ids, evidence=citation(evidence_id, excerpt_id),
            local_id=UUID(local_id))
        if public_edges[local_id] != expected:
            raise GuestReleaseValidationError("Released relationship differs from native Graph")
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
