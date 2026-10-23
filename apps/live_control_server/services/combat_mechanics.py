"""Read-only current association preview and exact snapshot verification."""
import json
from contextlib import contextmanager
from application_state.combat_encounters.types import AcceptedCombatMechanicsSelection, AcceptedCombatMechanicsSnapshot
from application_state.errors import ApplicationStateIntegrityError
from apps.live_control_server.config import artifact_data_root, repo_root
from apps.live_control_server.services.threat_draft_store import get_threat_draft, locked_threat_drafts
from apps.live_control_server.services.statblock_acceptance_reconciliation import list_acceptance_operations_for_draft
from apps.live_control_server.integrations.dungeonmind_statblocks.definition_digest import source_definition_digest_from_body
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



def prepare_accepted_snapshot(*, world_id: str, selection: AcceptedCombatMechanicsSelection):
    """Prepare exact accepted bytes before taking any final admission lock.

    No Graph identity or association is inferred. Consumers may retain the returned
    immutable snapshot without re-reading mutable draft or provider state later.
    """
    root = artifact_data_root(default=repo_root())
    draft = get_threat_draft(root, str(selection.draft_id))
    if (draft.schema_name != 'dmb_threat_draft_v2' or draft.world_id != world_id
        or draft.version != selection.draft_version):
        raise ApplicationStateConflictError('Saved mechanics changed or belong to another World; refresh and select again')
    accepted = draft.accepted_mechanics_ref
    if draft.workflow_state != 'mechanics_saved' or accepted is None:
        raise ApplicationStateConflictError('Select saved accepted mechanics')
    matches = [op for op in list_acceptance_operations_for_draft(root, draft_id=draft.draft_id) if (
        op.authority_state == 'reconciled' and op.materialization.draft_ref == 'attached'
        and op.source_draft_id == draft.draft_id
        and op.source_draft_version == accepted.accepted_from_draft_version
        and op.source_candidate_id == accepted.accepted_from_candidate_id
        and op.validation_receipt_digest == accepted.definition_digest
        and source_definition_digest_from_body(op.request_body['definition']) == accepted.definition_digest
        and op.locator is not None and same_mechanics_locator(op.locator, accepted.to_mechanics_locator())
    )]
    if len(matches) != 1:
        raise ApplicationStateIntegrityError('Accepted mechanics have no unique attached acceptance proof')
    op = matches[0]
    client = build_statblock_v1_client()
    try:
        exact = client.get_exact_revision(accepted.statblock_id, accepted.revision_id)
        verify_exact_revision_mechanics_integrity(exact)
        if not same_mechanics_locator(locator_from_exact_revision(exact), accepted.to_mechanics_locator()):
            raise ApplicationStateIntegrityError('Exact mechanics differ from saved acceptance')
        resource = exact.model_dump(mode='json')
        resource['definition'] = json.loads(exact.canonical_definition)
    finally:
        client.close()
    payload = dict(origin='world_accepted_mechanics_v1', managed_world_id=world_id,
        draft_id=str(selection.draft_id), draft_version=draft.version,
        acceptance_operation_id=op.operation_id, acceptance_request_digest=op.create_request_digest,
        accepted_from_draft_version=op.source_draft_version, accepted_from_candidate_id=op.source_candidate_id,
        locator=accepted.to_mechanics_locator().model_dump(mode='json'), resource=resource)
    snapshot = AcceptedCombatMechanicsSnapshot(**payload,
        snapshot_digest=AcceptedCombatMechanicsSnapshot.digest_payload(payload))
    return draft, snapshot


@contextmanager
def accepted_drafts_guard(drafts):
    """Recheck every saved draft under one short store lock through APP CAS."""
    if not drafts:
        yield
        return
    root = artifact_data_root(default=repo_root())
    with locked_threat_drafts(root, [draft.draft_id for draft in drafts]) as current:
        if any(current[draft.draft_id] != draft for draft in drafts):
            raise ApplicationStateConflictError('Saved mechanics changed during verification; refresh and select again')
        yield


def preview_accepted(*, world_id: str, selection: AcceptedCombatMechanicsSelection):
    draft, snapshot = prepare_accepted_snapshot(world_id=world_id, selection=selection)
    with accepted_drafts_guard([draft]):
        return snapshot


def prepare_saved_override(*,world_id,draft_id,locator):
    from apps.live_control_server.services.statblock_saved_revision import resolve_saved_source
    from application_state.combat_encounters.types import SavedCombatMechanicsSnapshot
    draft,origin,anchor,operation,exact=resolve_saved_source(artifact_data_root(default=repo_root()),
        world_id=world_id,draft_id=draft_id,locator=locator)
    if exact.validation_receipt.status=='invalid' or any(issue.severity=='error' for issue in exact.validation_receipt.issues or []):
        raise ApplicationStateIntegrityError('Selected mechanics have an invalid validation receipt')
    resource=exact.model_dump(mode='json');resource['definition']=json.loads(exact.canonical_definition)
    payload=dict(origin='buddy_saved_mechanics_override_v1',managed_world_id=world_id,draft_id=str(draft_id),
        origin_acceptance_operation_id=str(anchor),revision_operation_id=str(operation) if operation else None,
        locator=locator.model_dump(mode='json'),resource=resource)
    snapshot=SavedCombatMechanicsSnapshot(**payload,snapshot_digest=SavedCombatMechanicsSnapshot.digest_payload(payload))
    return draft,origin,snapshot


def preview_saved_override(*,world_id,draft_id,locator):
    from application_state.combat_encounters.adoption import numeric_defaults
    from application_state.combat_encounters.adoption_types import AdoptionPreview
    draft,_origin,snapshot=prepare_saved_override(world_id=world_id,draft_id=draft_id,locator=locator)
    with accepted_drafts_guard([draft]):
        ac,hp=numeric_defaults(snapshot)
        return AdoptionPreview(snapshot=snapshot,armor_class=ac,hit_points=hp)


def adopt_saved_override(*,world_id,encounter_id,request,scope=None):
    from application_state.combat_encounters import adoption
    replay=adoption.inspect(world_id=world_id,encounter_id=encounter_id,operation_id=request.operation_id,request=request,scope=scope)
    if replay is not None:return replay
    draft,origin,snapshot=prepare_saved_override(world_id=world_id,draft_id=request.draft_id,locator=request.locator)
    with accepted_drafts_guard([draft]):
        return adoption.apply_verified(world_id=world_id,encounter_id=encounter_id,request=request,snapshot=snapshot,origin=origin,scope=scope)
