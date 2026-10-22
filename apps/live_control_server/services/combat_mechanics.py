"""Read-only current association preview and exact snapshot verification."""
import json
from application_state.combat_encounters.types import CombatMechanicsSelection, CombatMechanicsSnapshot
from application_state.errors import ApplicationStateConflictError
from application_state.world_mechanics import service as associations
from apps.live_control_server.services.managed_world_graph_projection import ManagedWorldGraphProjectionRequest, project_managed_world_graph, resolve_managed_world_binding
from apps.live_control_server.integrations.dungeonmind_statblocks.client import build_statblock_v1_client, verify_exact_revision_mechanics_integrity
from apps.live_control_server.integrations.dungeonmind_statblocks.mechanics_locator import locator_from_exact_revision, same_mechanics_locator


def preview(*, world_id: str, selection: CombatMechanicsSelection, records=None, projection=None):
    if selection.target.managed_world_id != world_id:
        raise ApplicationStateConflictError("Creature belongs to a different World")
    records = associations.list_current(world_id=world_id) if records is None else records
    record = next((r for r in records if r.association_id == selection.association_id), None)
    if (record is None or record.version != selection.association_version
        or record.request.target.model_dump() != selection.target.model_dump()):
        raise ApplicationStateConflictError("Creature mechanics changed; load and confirm again")
    view = projection or project_managed_world_graph(ManagedWorldGraphProjectionRequest(
        schema="dmb_managed_world_graph_projection_request_v1", managed_world_id=world_id))
    target = selection.target
    node = next((n for n in view.projection.nodes if n.node_id == target.node_id), None)
    binding = resolve_managed_world_binding(world_id)
    if (view.managed_world_id != world_id or view.native_world_id != target.native_world_id
        or view.binding_version != target.binding_version or not view.projection.snapshot.is_head
        or view.projection.snapshot.revision_id != target.graph_revision_id
        or (binding.native_world_id, binding.binding_version) != (target.native_world_id,target.binding_version)
        or node is None or (node.label,node.kind,node.role,node.campaign_scope) != (target.label,target.kind,target.role,target.campaign_scope)):
        raise ApplicationStateConflictError("World contents changed; re-associate creature mechanics before adding")
    client = build_statblock_v1_client()
    try:
        exact = client.get_exact_revision(record.proof.locator.statblock_id, record.proof.locator.revision_id)
        verify_exact_revision_mechanics_integrity(exact)
        if not same_mechanics_locator(locator_from_exact_revision(exact), record.proof.locator.model_dump(mode="json")):
            raise ApplicationStateConflictError("Exact accepted mechanics identity changed")
        resource = exact.model_dump(mode="json")
        resource["definition"] = json.loads(exact.canonical_definition)
    finally:
        client.close()
    payload = dict(association_id=str(record.association_id),association_version=record.version,
        target=selection.target.model_dump(mode="json"),locator=record.proof.locator.model_dump(mode="json"),resource=resource)
    return CombatMechanicsSnapshot(**payload,snapshot_digest=CombatMechanicsSnapshot.digest_payload(payload))
