"""Verify existing accepted mechanics and World identity before APP association."""
from __future__ import annotations

from pathlib import Path

from application_state.errors import ApplicationStateConflictError, ApplicationStateIntegrityError, ApplicationStateUnavailableError
from apps.live_control_server.config import ArtifactDataRootError, artifact_data_root, repo_root
from application_state.world_mechanics import service as state
from application_state.world_mechanics.types import (
    AcceptedMechanicsProof, AssociateWorldMechanicsRequest,
    AssociateWorldMechanicsResponse, WorldMechanicsTarget,
)
from apps.live_control_server.integrations.dungeonmind_statblocks.client import (
    build_statblock_v1_client, verify_exact_revision_mechanics_integrity,
)
from apps.live_control_server.integrations.dungeonmind_statblocks.definition_digest import source_definition_digest_from_body
from apps.live_control_server.integrations.dungeonmind_statblocks.mechanics_locator import (
    locator_from_exact_revision, same_mechanics_locator,
)
from apps.live_control_server.services.managed_world_graph_projection import (
    ManagedWorldGraphProjectionRequest, project_managed_world_graph,
    resolve_managed_world_binding,
)
from apps.live_control_server.services.statblock_acceptance_reconciliation import list_acceptance_operations_for_draft
from apps.live_control_server.services.threat_draft_store import get_threat_draft, locked_threat_draft


def associate(*, root: Path | None = None, request: AssociateWorldMechanicsRequest, actor: str,
              client=None) -> AssociateWorldMechanicsResponse:
    # Lost acknowledgements must not repeat external work or become fresh writes.
    previous = state.replay(request)
    if previous is not None:
        return AssociateWorldMechanicsResponse(association=previous, replayed=True)
    if root is None:
        try:
            root = artifact_data_root(default=repo_root())
        except ArtifactDataRootError as exc:
            raise ApplicationStateUnavailableError("Accepted mechanics storage is unavailable") from exc
    draft = get_threat_draft(root, str(request.draft_id))
    if draft.schema_name != "dmb_threat_draft_v2" or draft.world_id != request.target.managed_world_id:
        raise ApplicationStateConflictError("Accepted draft belongs to a different World or scope")
    if draft.version != request.expected_draft_version:
        raise ApplicationStateConflictError("Saved mechanics draft changed; reopen before associating")
    accepted = draft.accepted_mechanics_ref
    if draft.workflow_state != "mechanics_saved" or accepted is None:
        raise ApplicationStateConflictError("Save accepted mechanics before associating a creature")
    operations = list_acceptance_operations_for_draft(root, draft_id=draft.draft_id)
    matches = [operation for operation in operations if (
        operation.authority_state == "reconciled" and operation.materialization.draft_ref == "attached"
        and operation.source_draft_id == draft.draft_id
        and operation.source_draft_version == accepted.accepted_from_draft_version
        and operation.source_candidate_id == accepted.accepted_from_candidate_id
        and operation.validation_receipt_digest == accepted.definition_digest
        and source_definition_digest_from_body(operation.request_body["definition"]) == accepted.definition_digest
        and operation.locator is not None
        and same_mechanics_locator(operation.locator, accepted.to_mechanics_locator())
    )]
    if len(matches) != 1:
        raise ApplicationStateIntegrityError("Accepted mechanics have no unique reconciled acceptance proof")
    operation = matches[0]
    owned = client is None
    exact_client = build_statblock_v1_client() if owned else client
    try:
        revision = exact_client.get_exact_revision(accepted.statblock_id, accepted.revision_id)
        verify_exact_revision_mechanics_integrity(revision)
        if not same_mechanics_locator(locator_from_exact_revision(revision), accepted.to_mechanics_locator()):
            raise ApplicationStateIntegrityError("Exact mechanics revision does not match accepted identity")
    finally:
        if owned:
            exact_client.close()
    target = request.target
    view = project_managed_world_graph(ManagedWorldGraphProjectionRequest(
        schema="dmb_managed_world_graph_projection_request_v1", managed_world_id=target.managed_world_id,
    ))
    node = next((item for item in view.projection.nodes if item.node_id == target.node_id), None)
    if (node is None or not view.projection.snapshot.is_head
        or view.projection.snapshot.revision_id != target.graph_revision_id):
        raise ApplicationStateConflictError("World contents changed; load creatures and confirm again")
    verified = WorldMechanicsTarget(
        managed_world_id=view.managed_world_id, native_world_id=view.native_world_id,
        binding_version=view.binding_version, graph_revision_id=view.projection.snapshot.revision_id,
        node_id=node.node_id, label=node.label, kind=node.kind, role=node.role,
        campaign_scope=node.campaign_scope,
    )
    eligible = {"npc", "threat", "creature", "monster"}
    if verified != target or not ({node.kind.casefold(), node.role.casefold()} & eligible):
        raise ApplicationStateConflictError("Selected creature identity is not valid in this World")
    binding = resolve_managed_world_binding(target.managed_world_id)
    if (binding.native_world_id, binding.binding_version) != (target.native_world_id, target.binding_version):
        raise ApplicationStateConflictError("World mapping changed; load creatures and confirm again")
    with locked_threat_draft(root, draft.draft_id) as current:
        if current != draft:
            raise ApplicationStateConflictError("Saved mechanics draft changed during verification; reopen it")
        # The draft CAS is held through APP append; Graph observation remains
        # historical evidence rather than a distributed head lock.
        return state.append_verified(request=request, actor=actor, proof=AcceptedMechanicsProof(
            locator=accepted.to_mechanics_locator().model_dump(mode="json"),
            acceptance_operation_id=operation.operation_id,
            accepted_from_draft_version=operation.source_draft_version,
            accepted_from_candidate_id=operation.source_candidate_id,
            acceptance_request_digest=operation.create_request_digest,
        ))
