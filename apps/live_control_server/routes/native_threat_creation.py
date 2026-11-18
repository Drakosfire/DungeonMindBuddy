"""Explicit GM review/confirmation of one proposed native creature."""
from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, HTTPException, Query, Request
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
from apps.live_control_server.services.agent_graph_auth import enforce_native_graph_gm
from apps.live_control_server.services import native_threat_creation as service
from apps.live_control_server.services.graph_object_authoring_prepare import GraphObjectAuthoringError
from apps.live_control_server.services.threat_draft_store import ThreatDraftStoreError
from apps.live_control_server.services.world_graph_projection import WorldGraphProjectionServiceError

router = APIRouter()
WorldId = Annotated[str, Query(pattern=r"^[a-z][a-z0-9_-]{0,62}$")]


def call(operation, *args, **kwargs):
    try:
        return operation(statblock_data_root(repo_root()), *args, **kwargs)
    except (ApplicationStateError, ThreatDraftStoreError, GraphObjectAuthoringError,
            WorldGraphProjectionServiceError) as exc:
        raise HTTPException(status_code=exc.status_code, detail=str(exc)) from exc
    except (DatabaseError, CommittedChangeOutcomeUnknown, CommittedChangeVerificationUnavailable,
            CommittedChangeVerificationIntegrityFailure) as exc:
        raise HTTPException(status_code=503, detail="Native creature outcome needs recovery; keep the same review") from exc
    except (DungeonMindError, InvalidWorldChange, PreparedChangeIntegrityFailure, PreparedChangeStale,
            PreparedChangeConflict, CommitAuthorityIntegrityFailure, ValueError) as exc:
        raise HTTPException(status_code=409, detail="Native creature review changed or is unavailable; prepare it again") from exc


def _authorized_call(operation, request: Request, world_id: str, *args):
    from apps.live_control_server.services.hosted_native_graph_access import (
        conversation_graph_principal, require_conversation_access,
    )

    principal = conversation_graph_principal(request, world_id, authorize_local=enforce_native_graph_gm)

    def authorize_write():
        require_conversation_access(request, world_id, authorize_local=enforce_native_graph_gm)

    guard = {"authorize_write": authorize_write} if principal.auth_method == "hosted_owner" else {}
    return call(operation, *args, principal, **guard)


@router.get("/{draft_id}/native-creature")
def read(draft_id: UUID, world_id: WorldId, request: Request):
    return _authorized_call(service.status, request, world_id, draft_id, world_id)


@router.post("/{draft_id}/native-creature/prepare")
def prepare(draft_id: UUID, body: PrepareNativeThreat, request: Request):
    return _authorized_call(service.prepare, request, body.world_id, draft_id, body)


@router.post("/{draft_id}/native-creature/confirm")
def confirm(draft_id: UUID, body: ConfirmNativeThreat, request: Request):
    return _authorized_call(service.confirm, request, body.review.world_id, draft_id, body)
