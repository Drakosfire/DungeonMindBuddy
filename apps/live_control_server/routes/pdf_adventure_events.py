"""Local GM review and publication of PDF-backed adventure Events."""
from typing import Annotated

from dungeonmind.application.vnext.errors import KnowledgePublicationOutcomeUnknownError
from dungeonmind.domain.errors import DungeonMindError
from fastapi import APIRouter, Depends, HTTPException
from worldkeeper.application.commit import (
    CommitAuthorityIntegrityFailure,
    CommittedChangeOutcomeUnknown,
    CommittedChangeVerificationIntegrityFailure,
    CommittedChangeVerificationUnavailable,
    PreparedChangeConflict,
    PreparedChangeIntegrityFailure,
    PreparedChangeStale,
)
from worldkeeper.application.preparation import InvalidWorldChange

from application_state.errors import ApplicationStateError
from apps.live_control_server.routes.strict_json import StrictJSONRoute
from apps.live_control_server.services import pdf_adventure_event_review as service
from apps.live_control_server.services.agent_graph_auth import (
    NativeGraphPrincipal,
    native_graph_gm_dependency,
)
from apps.live_control_server.services.graph_object_authoring_prepare import GraphObjectAuthoringError
from apps.live_control_server.services.managed_world_graph_projection import WorldGraphProjectionServiceError

router = APIRouter(
    prefix="/api/live/worlds/{world_id}/pdf-adventure-events",
    route_class=StrictJSONRoute,
)
GM = Annotated[NativeGraphPrincipal, Depends(native_graph_gm_dependency)]


def _invoke(action, world_id, body, principal):
    try:
        return action(world_id, body, principal)
    except (
        KnowledgePublicationOutcomeUnknownError,
        CommittedChangeOutcomeUnknown,
        CommittedChangeVerificationUnavailable,
        CommittedChangeVerificationIntegrityFailure,
    ) as exc:
        raise HTTPException(503, detail={
            "code": "event_publication_outcome_unknown",
            "message": "Retry the exact confirmation to recover publication.",
        }) from exc
    except (ApplicationStateError, GraphObjectAuthoringError, WorldGraphProjectionServiceError) as exc:
        raise HTTPException(exc.status_code, detail={
            "code": getattr(exc, "code", "event_publication_refused"), "message": str(exc),
        }) from exc
    except CommitAuthorityIntegrityFailure as exc:
        raise HTTPException(503, detail={
            "code": "event_publication_unavailable",
            "message": "Publication authority could not be verified. Retain this confirmation.",
        }) from exc
    except (
        ValueError, DungeonMindError, InvalidWorldChange, PreparedChangeStale,
        PreparedChangeConflict, PreparedChangeIntegrityFailure,
    ) as exc:
        raise HTTPException(409, detail={
            "code": getattr(exc, "code", "event_publication_refused"), "message": str(exc),
        }) from exc


@router.post("/prepare")
def prepare(world_id: str, body: service.EventDraft, principal: GM):
    return _invoke(service.prepare, world_id, body, principal)


@router.post("/confirm")
def confirm(world_id: str, body: service.EventConfirmation, principal: GM):
    return _invoke(service.confirm, world_id, body, principal)
