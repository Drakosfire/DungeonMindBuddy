"""Authenticated read-only native Graph inspection, separate from old write DTOs."""

from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import JSONResponse
from pydantic import Field
from dungeonmind.domain.errors import DungeonMindError
from apps.live_control_server.models.native_graph_inspection import (
    Closed,
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


class NativeRecapPageRequest(Closed):
    read: InspectionRead
    max_chars: int = Field(default=4000, ge=1, le=16000)
    continuation: str | None = Field(default=None, max_length=128)


@router.post("/recap-page")
def recap_page(body: NativeRecapPageRequest, principal=Depends(native_graph_gm_dependency)):
    from apps.live_control_server.services.native_recap_pages import read_native_recap_page

    def read_page(request, caller):
        return read_native_recap_page(
            request.read, caller, max_chars=request.max_chars,
            continuation=request.continuation,
        )

    return _call(read_page, body, principal)


class NativeRelatedRecapsRequest(Closed):
    scope: InspectionPin
    assertion_id: str = Field(min_length=1, max_length=256)


@router.post("/related-recaps")
def related_recaps(body: NativeRelatedRecapsRequest, principal=Depends(native_graph_gm_dependency)):
    def discover(request, caller):
        return service.related_recaps(request.scope, caller, request.assertion_id)

    return _call(discover, body, principal)
