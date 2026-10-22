"""GM-authorized explicit World-object mechanics associations."""
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Query
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

router = APIRouter(prefix="/api/live/world-mechanics/associations", tags=["world-mechanics"])
WorldId = Annotated[str, Query(pattern=r"^[a-z][a-z0-9_-]{0,62}$")]


@router.get("", response_model=list[WorldMechanicsAssociation])
def list_associations(world_id: WorldId, principal: NativeGraphPrincipal = Depends(native_graph_gm_dependency)):
    try:
        resolve_managed_world_binding(world_id)
        return state.list_current(world_id=world_id)
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
