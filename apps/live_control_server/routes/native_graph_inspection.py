"""Authenticated read-only native Graph inspection, separate from old write DTOs."""

from fastapi import APIRouter, Depends, HTTPException
from dungeonmind.domain.errors import DungeonMindError
from apps.live_control_server.models.native_graph_inspection import (
    InspectionRead,
    InspectionScope,
)
from apps.live_control_server.services import native_graph_inspection as service
from apps.live_control_server.services.agent_graph_auth import (
    native_graph_gm_dependency,
)
from apps.live_control_server.routes.strict_json import StrictJSONRoute

router = APIRouter(
    prefix="/api/live/native-graph-inspection",
    tags=["native-graph-inspection"],
    route_class=StrictJSONRoute,
)


def _call(fn, body, principal):
    try:
        return fn(body, principal)
    except (ValueError, DungeonMindError) as exc:
        raise HTTPException(
            getattr(exc, "status_code", 409),
            detail={
                "code": getattr(exc, "code", "native_inspection_unavailable"),
                "message": "The selected reviewed Graph material is unavailable. Refresh and inspect again.",
            },
        ) from exc


@router.post("/catalog")
def catalog(body: InspectionScope, principal=Depends(native_graph_gm_dependency)):
    return _call(service.catalog, body, principal)


@router.post("/read")
def inspect(body: InspectionRead, principal=Depends(native_graph_gm_dependency)):
    return _call(service.inspect, body, principal)
