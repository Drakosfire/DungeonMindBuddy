"""Authenticated read-only source browsing, independent of object Graph availability."""

from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import JSONResponse
from dungeonmind.domain.errors import DungeonMindError
from apps.live_control_server.models.native_graph_inspection import InspectionScope
from apps.live_control_server.models.native_source_inspection import NativeSourceRead
from apps.live_control_server.services import native_source_inspection as service
from apps.live_control_server.services.agent_graph_auth import (
    native_graph_gm_dependency,
)
from apps.live_control_server.routes.strict_json import StrictJSONRoute

router = APIRouter(
    prefix="/api/live/native-source-inspection",
    tags=["native-source-inspection"],
    route_class=StrictJSONRoute,
)


def _call(fn, body, principal):
    try:
        return JSONResponse(fn(body, principal), headers={"Cache-Control": "no-store"})
    except (ValueError, DungeonMindError) as exc:
        raise HTTPException(
            getattr(exc, "status_code", 409),
            detail={
                "code": getattr(exc, "code", "native_source_inspection_unavailable"),
                "message": "The selected source is unavailable. Refresh and inspect again.",
            },
        ) from exc


@router.post("/catalog")
def catalog(body: InspectionScope, principal=Depends(native_graph_gm_dependency)):
    return _call(service.catalog, body, principal)


@router.post("/read")
def inspect(body: NativeSourceRead, principal=Depends(native_graph_gm_dependency)):
    return _call(service.inspect, body, principal)
