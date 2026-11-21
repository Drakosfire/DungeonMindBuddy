"""Read current native Graph identity before accepting typed Build placement."""

from __future__ import annotations

from application_state.build_proposal.graph_reference import BuildGraphReferencePlacement
from application_state.errors import ApplicationStateConflictError
from apps.live_control_server.models.native_graph_inspection import InspectionPin, InspectionScope

from .agent_graph_auth import NativeGraphPrincipal
from .native_graph_inspection import InspectionUnavailable, authoring_identities


def require_current_build_graph_reference(
    placement: BuildGraphReferencePlacement, principal: NativeGraphPrincipal,
) -> None:
    reference = placement.reference
    try:
        graph = authoring_identities(InspectionScope(managed_world_id=placement.basis.world_id), principal)
    except InspectionUnavailable as error:
        raise ApplicationStateConflictError("The current Graph identity is unavailable") from error
    expected = InspectionPin(
        managed_world_id=reference.managed_world_id,
        native_world_id=reference.native_world_id,
        binding_version=reference.binding_version,
        revision_id=reference.graph_revision,
    )
    if graph["scope"] != expected.model_dump(mode="json"):
        raise ApplicationStateConflictError("The selected Graph identity belongs to a different or changed Graph")
    matches = [row for row in graph["identities"] if row["node_id"] == reference.node_id]
    if (len(matches) != 1 or not matches[0]["selectable"]
            or matches[0]["kind"] != placement.entity_kind or matches[0]["label"] != reference.label):
        raise ApplicationStateConflictError("The selected Graph identity or classification changed")
