"""GM-authorized explicit World-object mechanics associations."""
from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, Request
from application_state.errors import ApplicationStateError
from application_state.world_mechanics import service as state
from application_state.world_mechanics.types import (
    AssociateWorldMechanicsRequest, AssociateWorldMechanicsResponse, WorldMechanicsAssociation,
)
from apps.live_control_server.integrations.dungeonmind_statblocks.errors import StatblockIntegrationError
from apps.live_control_server.services.agent_graph_auth import NativeGraphPrincipal, native_graph_gm_dependency
from apps.live_control_server.services.managed_world_graph_projection import resolve_managed_world_binding
from apps.live_control_server.services.world_graph_projection import WorldGraphProjectionServiceError
from apps.live_control_server.services.statblock_acceptance_reconciliation import AcceptanceReconciliationError
from apps.live_control_server.services.threat_draft_store import ThreatDraftStoreError
from apps.live_control_server.services.world_mechanics_associations import associate
from apps.live_control_server.services import world_creature_selection as creatures

router = APIRouter(prefix="/api/live/world-mechanics/associations", tags=["world-mechanics"])
WorldId = Annotated[str, Query(pattern=r"^[a-z][a-z0-9_-]{0,62}$")]


@router.get("/creatures")
def list_creatures(world_id: WorldId, principal: NativeGraphPrincipal = Depends(native_graph_gm_dependency)):
    try:
        return creatures.catalog(world_id).response()
    except ApplicationStateError as exc:
        raise HTTPException(status_code=exc.status_code, detail=str(exc)) from exc


@router.get("", response_model=list[WorldMechanicsAssociation])
def get_associations(world_id: WorldId, request: Request):
    from apps.live_control_server.services import hosted_auth
    from apps.live_control_server.services.agent_graph_auth import enforce_native_graph_gm
    from apps.live_control_server.services.hosted_native_graph_access import require_hosted_plan_world_context

    if hosted_auth.deployment_environment() == hosted_auth.PRODUCTION_ENVIRONMENT:
        require_hosted_plan_world_context(request, world_id)
    else:
        enforce_native_graph_gm(request)
    return list_associations(world_id)


def list_associations(world_id: str, principal: NativeGraphPrincipal | None = None):
    try:
        resolve_managed_world_binding(world_id)
        return state.list_current(world_id=world_id)
    except (ApplicationStateError, WorldGraphProjectionServiceError) as exc:
        raise HTTPException(status_code=exc.status_code, detail=str(exc)) from exc


@router.get("/requests/{request_id}", response_model=WorldMechanicsAssociation | None)
def association_request(request_id: UUID, world_id: WorldId,
                        principal: NativeGraphPrincipal = Depends(native_graph_gm_dependency)):
    try:
        resolve_managed_world_binding(world_id)
        return state.find_request(world_id=world_id, request_id=request_id)
    except (ApplicationStateError, WorldGraphProjectionServiceError) as exc:
        raise HTTPException(status_code=exc.status_code, detail=str(exc)) from exc


@router.post("", response_model=AssociateWorldMechanicsResponse)
def associate_route(world_id: WorldId, body: AssociateWorldMechanicsRequest,
                    principal: NativeGraphPrincipal = Depends(native_graph_gm_dependency)):
    if body.target.managed_world_id != world_id:
        raise HTTPException(status_code=409, detail="Selected creature belongs to a different World")
    try:
        return associate(request=body, actor=principal.subject)
    except (ApplicationStateError, WorldGraphProjectionServiceError,
            ThreatDraftStoreError, AcceptanceReconciliationError) as exc:
        raise HTTPException(status_code=exc.status_code, detail=str(exc)) from exc
    except StatblockIntegrationError as exc:
        raise HTTPException(status_code=503, detail="Exact accepted mechanics could not be verified") from exc
