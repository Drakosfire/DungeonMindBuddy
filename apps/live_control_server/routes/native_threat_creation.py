"""Explicit GM review/confirmation of one proposed native creature."""
from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query
from dungeonmind.domain.errors import DungeonMindError
from psycopg import Error as DatabaseError
from worldkeeper.application.preparation import InvalidWorldChange
from worldkeeper.application.commit import (
    PreparedChangeIntegrityFailure, PreparedChangeStale, PreparedChangeConflict,
    CommitAuthorityIntegrityFailure, CommittedChangeOutcomeUnknown,
    CommittedChangeVerificationUnavailable, CommittedChangeVerificationIntegrityFailure,
)

from application_state.errors import ApplicationStateError
from apps.live_control_server.config import repo_root
from apps.live_control_server.models.native_threat_creation import PrepareNativeThreat, ConfirmNativeThreat
from apps.live_control_server.routes.statblock_storage import statblock_data_root
from apps.live_control_server.services.agent_graph_auth import NativeGraphPrincipal, native_graph_gm_dependency
from apps.live_control_server.services import native_threat_creation as service
from apps.live_control_server.services.graph_object_authoring_prepare import GraphObjectAuthoringError
from apps.live_control_server.services.threat_draft_store import ThreatDraftStoreError
from apps.live_control_server.services.world_graph_projection import WorldGraphProjectionServiceError

router = APIRouter()
WorldId = Annotated[str, Query(pattern=r"^[a-z][a-z0-9_-]{0,62}$")]


def call(operation, *args):
    try:
        return operation(statblock_data_root(repo_root()), *args)
    except (ApplicationStateError, ThreatDraftStoreError, GraphObjectAuthoringError,
            WorldGraphProjectionServiceError) as exc:
        raise HTTPException(status_code=exc.status_code, detail=str(exc)) from exc
    except (DatabaseError, CommittedChangeOutcomeUnknown, CommittedChangeVerificationUnavailable,
            CommittedChangeVerificationIntegrityFailure) as exc:
        raise HTTPException(status_code=503, detail="Native creature outcome needs recovery; keep the same review") from exc
    except (DungeonMindError, InvalidWorldChange, PreparedChangeIntegrityFailure, PreparedChangeStale,
            PreparedChangeConflict, CommitAuthorityIntegrityFailure, ValueError) as exc:
        raise HTTPException(status_code=409, detail="Native creature review changed or is unavailable; prepare it again") from exc


@router.get("/{draft_id}/native-creature")
def read(draft_id: UUID, world_id: WorldId,
         principal: NativeGraphPrincipal = Depends(native_graph_gm_dependency)):
    return call(service.status, draft_id, world_id, principal)


@router.post("/{draft_id}/native-creature/prepare")
def prepare(draft_id: UUID, body: PrepareNativeThreat,
            principal: NativeGraphPrincipal = Depends(native_graph_gm_dependency)):
    return call(service.prepare, draft_id, body, principal)


@router.post("/{draft_id}/native-creature/confirm")
def confirm(draft_id: UUID, body: ConfirmNativeThreat,
            principal: NativeGraphPrincipal = Depends(native_graph_gm_dependency)):
    return call(service.confirm, draft_id, body, principal)
