"""Verify one selected saved revision and native creature before APP association."""
from __future__ import annotations

from pathlib import Path

from application_state.errors import ApplicationStateConflictError, ApplicationStateUnavailableError
from apps.live_control_server.config import ArtifactDataRootError, artifact_data_root, repo_root
from application_state.world_mechanics import service as state
from application_state.world_mechanics.types import (
    SavedMechanicsProof, AssociateWorldMechanicsRequest, AssociateWorldMechanicsResponse,
)
from apps.live_control_server.services import world_creature_selection as creatures
from apps.live_control_server.services.statblock_saved_revision import resolve_saved_source
from apps.live_control_server.services.threat_draft_store import locked_threat_draft


def associate(*, root: Path | None = None, request: AssociateWorldMechanicsRequest, actor: str,
              client=None) -> AssociateWorldMechanicsResponse:
    previous = state.replay(request)
    if previous is not None:
        return AssociateWorldMechanicsResponse(association=previous, replayed=True)
    if root is None:
        try:
            root = artifact_data_root(default=repo_root())
        except ArtifactDataRootError as exc:
            raise ApplicationStateUnavailableError("Saved mechanics storage is unavailable") from exc
    draft, origin, anchor, revision_operation, _ = resolve_saved_source(
        root, world_id=request.target.managed_world_id, draft_id=str(request.draft_id),
        locator=request.locator, client=client,
    )
    if draft.version != request.expected_draft_version:
        raise ApplicationStateConflictError("Saved mechanics draft changed; reopen before associating")
    view = creatures.catalog(request.target.managed_world_id)
    creatures.require_target(request.target, view, head=True)
    with locked_threat_draft(root, draft.draft_id) as current:
        if current != draft:
            raise ApplicationStateConflictError("Saved mechanics draft changed during verification; reopen it")
        return state.append_verified(request=request, actor=actor, proof=SavedMechanicsProof(
            locator=request.locator, origin_locator=origin.model_dump(mode="json"),
            origin_acceptance_operation_id=anchor, revision_operation_id=revision_operation,
        ))
