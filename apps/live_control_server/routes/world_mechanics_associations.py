"""GM-authorized explicit World-object mechanics associations."""
from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, HTTPException, Query, Request
from application_state.errors import ApplicationStateError
from application_state.world_mechanics import service as state
from application_state.world_mechanics.types import (
    AssociateWorldMechanicsRequest, AssociateWorldMechanicsResponse, WorldMechanicsAssociation,
)
from apps.live_control_server.integrations.dungeonmind_statblocks.errors import StatblockIntegrationError
from apps.live_control_server.services.agent_graph_auth import NativeGraphPrincipal, enforce_native_graph_gm
from apps.live_control_server.services.managed_world_graph_projection import resolve_managed_world_binding
from apps.live_control_server.services.world_graph_projection import WorldGraphProjectionServiceError
from apps.live_control_server.services.statblock_acceptance_reconciliation import AcceptanceReconciliationError
from apps.live_control_server.services.threat_draft_store import ThreatDraftStoreError
from apps.live_control_server.services.world_mechanics_associations import associate
from apps.live_control_server.services import world_creature_selection as creatures

router = APIRouter(prefix="/api/live/world-mechanics/associations", tags=["world-mechanics"])
WorldId = Annotated[str, Query(pattern=r"^[a-z][a-z0-9_-]{0,62}$")]


@router.get("/creatures")
def list_creatures(world_id: WorldId, request: Request):
    _authorize_world_read(request, world_id)
    try:
        result = creatures.catalog(world_id).response()
        _authorize_world_read(request, world_id)
        return result
    except ApplicationStateError as exc:
        raise HTTPException(status_code=exc.status_code, detail=str(exc)) from exc


def _authorize_world_read(request: Request, world_id: str):
    from apps.live_control_server.services import hosted_auth
    from apps.live_control_server.services.agent_graph_auth import enforce_native_graph_gm
    from apps.live_control_server.services.hosted_native_graph_access import require_hosted_plan_world_context

    if hosted_auth.deployment_environment() == hosted_auth.PRODUCTION_ENVIRONMENT:
        require_hosted_plan_world_context(request, world_id)
    else:
        enforce_native_graph_gm(request)


@router.get("", response_model=list[WorldMechanicsAssociation])
def get_associations(world_id: WorldId, request: Request):
    _authorize_world_read(request, world_id)
    return list_associations(world_id)


def list_associations(world_id: str, principal: NativeGraphPrincipal | None = None):
    try:
        resolve_managed_world_binding(world_id)
        return state.list_current(world_id=world_id)
    except (ApplicationStateError, WorldGraphProjectionServiceError) as exc:
        raise HTTPException(status_code=exc.status_code, detail=str(exc)) from exc


@router.get("/requests/{request_id}", response_model=WorldMechanicsAssociation | None)
def association_request(request_id: UUID, world_id: WorldId, request: Request):
    _authorize_world_read(request, world_id)
    try:
        resolve_managed_world_binding(world_id)
        result = state.find_request(world_id=world_id, request_id=request_id)
        _authorize_world_read(request, world_id)
        return result
    except (ApplicationStateError, WorldGraphProjectionServiceError) as exc:
        raise HTTPException(status_code=exc.status_code, detail=str(exc)) from exc


@router.post("", response_model=AssociateWorldMechanicsResponse)
def associate_route(world_id: WorldId, body: AssociateWorldMechanicsRequest, request: Request):
    from apps.live_control_server.services.hosted_native_graph_access import (
        conversation_graph_principal, require_conversation_access,
    )

    principal = conversation_graph_principal(request, world_id, authorize_local=enforce_native_graph_gm)
    if body.target.managed_world_id != world_id:
        raise HTTPException(status_code=409, detail="Selected creature belongs to a different World")
    def authorize():
        require_conversation_access(request, world_id, authorize_local=enforce_native_graph_gm)

    guard = authorize if principal.auth_method == "hosted_owner" else None
    return _associate_for_principal(body, principal, authorize=guard)


def _associate_for_principal(body, principal, *, authorize=None):
    try:
        guard = {"authorize": authorize} if authorize is not None else {}
        return associate(request=body, actor=principal.subject, **guard)
    except (ApplicationStateError, WorldGraphProjectionServiceError,
            ThreatDraftStoreError, AcceptanceReconciliationError) as exc:
        raise HTTPException(status_code=exc.status_code, detail=str(exc)) from exc
    except StatblockIntegrationError as exc:
        raise HTTPException(status_code=503, detail="Exact accepted mechanics could not be verified") from exc
