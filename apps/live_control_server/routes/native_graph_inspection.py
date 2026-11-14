"""Authenticated read-only native Graph inspection, separate from old write DTOs."""

from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import JSONResponse
from dungeonmind.domain.errors import DungeonMindError
from apps.live_control_server.models.native_graph_inspection import (
    InspectionPin,
    InspectionRead,
    InspectionScope,
)
from apps.live_control_server.services import native_graph_inspection as service
from apps.live_control_server.services.agent_graph_auth import (
    native_graph_gm_dependency,
)
from apps.live_control_server.routes.strict_json import StrictJSONRoute
from apps.live_control_server.services.hosted_native_graph_access import (
    native_graph_explorer_dependency,
)
from apps.live_control_server.services.native_graph_explorer import (
    NativeGraphExplorerError,
    hosted_response_binding,
)

router = APIRouter(
    prefix="/api/live/native-graph-inspection",
    tags=["native-graph-inspection"],
    route_class=StrictJSONRoute,
)


def _call(fn, body, principal):
    try:
        return JSONResponse(fn(body, principal))
    except (ValueError, DungeonMindError) as exc:
        raise HTTPException(
            getattr(exc, "status_code", 409),
            detail={
                "code": getattr(exc, "code", "native_inspection_unavailable"),
                "message": "The selected reviewed Graph material is unavailable. Refresh and inspect again.",
            },
        ) from exc


@router.post("/catalog")
def catalog(body: InspectionPin | InspectionScope, principal=Depends(native_graph_gm_dependency)):
    return _call(service.catalog, body, principal)


@router.post("/authoring-identities")
def authoring_identities(
    body: InspectionPin | InspectionScope,
    principal=Depends(native_graph_gm_dependency),
):
    return _call(service.authoring_identities, body, principal)


@router.post("/read")
def inspect(body: InspectionRead, principal=Depends(native_graph_explorer_dependency)):
    try:
        with hosted_response_binding(principal, body.scope.managed_world_id):
            return _call(service.inspect, body, principal)
    except NativeGraphExplorerError as exc:
        raise HTTPException(
            status_code=exc.status,
            detail={
                "code": exc.code,
                "message": "The selected reviewed Graph material is unavailable. Refresh and inspect again.",
            },
        ) from None


@router.post("/complete-object")
def complete_object(
    body: service.NativeCompleteObjectRead,
    principal=Depends(native_graph_gm_dependency),
):
    return _call(service.complete_object, body, principal)
