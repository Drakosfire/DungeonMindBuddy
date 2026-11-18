"""Authenticated read-only source browsing, independent of object Graph availability."""

from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import JSONResponse
from dungeonmind.domain.errors import DungeonMindError
from apps.live_control_server.models.native_graph_inspection import InspectionScope
from apps.live_control_server.models.native_source_inspection import NativeSourceRead, PublishedRecapObjectsRead, PublishedRecapRead
from apps.live_control_server.services import native_source_inspection as service
from apps.live_control_server.services.native_graph_explorer import NativeGraphExplorerError, hosted_response_binding
from apps.live_control_server.routes.strict_json import StrictJSONRoute

from apps.live_control_server.services.hosted_native_graph_access import native_graph_explorer_dependency

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
def catalog(body: InspectionScope, principal=Depends(native_graph_explorer_dependency)):
    return _call(service.catalog, body, principal)


@router.post("/read")
def inspect(body: NativeSourceRead, principal=Depends(native_graph_explorer_dependency)):
    return _call(service.inspect, body, principal)

@router.post("/published-recap")
def published_recap(body: PublishedRecapRead, principal=Depends(native_graph_explorer_dependency)):
    try:
        with hosted_response_binding(principal, body.managed_world_id):
            return _call(service.published_recap, body, principal)
    except NativeGraphExplorerError as exc:
        raise HTTPException(status_code=exc.status, detail={"code": exc.code}) from None


@router.post("/published-recap/objects")
def published_recap_objects(body: PublishedRecapObjectsRead, principal=Depends(native_graph_explorer_dependency)):
    try:
        with hosted_response_binding(principal, body.managed_world_id):
            return _call(service.published_recap_objects, body, principal)
    except NativeGraphExplorerError as exc:
        raise HTTPException(status_code=exc.status, detail={"code": exc.code}) from None
