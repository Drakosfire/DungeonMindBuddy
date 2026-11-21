"""Revision-pinned World Graph projection routes (PR007A + PR380A recap)."""

from __future__ import annotations

from typing import Any

from fastapi import APIRouter, Depends, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from fastapi.routing import APIRoute

from apps.live_control_server.services.world_graph_projection import (
    WorldGraphProjectionServiceError,
)
from apps.live_control_server.services.managed_world_graph_projection import (
    ManagedWorldGraphProjectionRequest,
    ManagedWorldGraphProjectionResponse,
    project_managed_world_graph,
)
from apps.live_control_server.services.hosted_native_graph_access import native_graph_explorer_dependency, require_explorer_access
from apps.live_control_server.services.agent_graph_auth import (
    NativeGraphPrincipal,
    native_graph_gm_dependency,
)
from graph_memory.projection.world_projection import (
    WorldGraphProjection,
    WorldGraphProjectionDiagnostic,
    WorldGraphProjectionRequest,
)
from graph_memory.projection.world_recap_projection import WorldGraphRecapProjection


def _request_validation_error_response(exc: RequestValidationError) -> JSONResponse:
    errors = exc.errors()
    if any(error.get("type") == "extra_forbidden" for error in errors):
        message = "Projection request contains unsupported fields."
    else:
        message = "Projection request does not match the required contract."
    return _error_response(
        WorldGraphProjectionServiceError(
            message,
            code="invalid_request",
            status_code=422,
            diagnostics=[
                WorldGraphProjectionDiagnostic(
                    code="invalid_request",
                    message=message,
                    severity="error",
                )
            ],
        )
    )


class _ProjectionAPIRoute(APIRoute):
    def get_route_handler(self):
        route_handler = super().get_route_handler()

        async def wrapped_route_handler(request: Request):
            try:
                return await route_handler(request)
            except RequestValidationError as exc:
                return _request_validation_error_response(exc)

        return wrapped_route_handler


router = APIRouter(
    prefix="/api/live/world-graph",
    tags=["world-graph-projection"],
    route_class=_ProjectionAPIRoute,
)


def _error_response(exc: WorldGraphProjectionServiceError) -> JSONResponse:
    return JSONResponse(
        status_code=exc.status_code,
        content=exc.response().model_dump(mode="json", by_alias=True),
    )


def _reject_query_params(request: Request) -> None:
    if request.query_params:
        raise WorldGraphProjectionServiceError(
            "Projection routes do not accept query parameters.",
            code="invalid_request",
            status_code=422,
            diagnostics=[
                WorldGraphProjectionDiagnostic(
                    code="invalid_request",
                    message="Projection routes do not accept query parameters.",
                    severity="error",
                )
            ],
        )


@router.post("/projection", response_model=WorldGraphProjection, dependencies=[Depends(native_graph_gm_dependency)])
def post_world_graph_projection(
    request_context: Request,
    request: WorldGraphProjectionRequest,
) -> dict[str, Any] | JSONResponse:
    try:
        _reject_query_params(request_context)
        raise WorldGraphProjectionServiceError(
            "Select a managed World to inspect its native graph.",
            code="legacy_projection_retired", status_code=410,
        )
    except WorldGraphProjectionServiceError as exc:
        return _error_response(exc)
    except Exception:
        return _error_response(
            WorldGraphProjectionServiceError(
                "World graph projection failed unexpectedly.",
                code="projection_internal_error",
                status_code=500,
            )
        )


@router.post(
    "/managed-projection",
    response_model=ManagedWorldGraphProjectionResponse,
)
def post_managed_world_graph_projection(
    request_context: Request,
    request: ManagedWorldGraphProjectionRequest,
    principal: NativeGraphPrincipal = Depends(native_graph_explorer_dependency),
) -> dict[str, Any] | JSONResponse:
    """Read a managed World through Buddy's private native Graph binding."""
    require_explorer_access(principal, request.managed_world_id)
    try:
        _reject_query_params(request_context)
        response = project_managed_world_graph(request)
    except WorldGraphProjectionServiceError as exc:
        return _error_response(exc)
    except Exception:
        return _error_response(
            WorldGraphProjectionServiceError(
                "Managed World graph projection failed unexpectedly.",
                code="projection_internal_error",
                status_code=500,
            )
        )
    result = response.model_dump(mode="json", by_alias=True)
    require_explorer_access(principal, response.managed_world_id)
    return result


@router.post("/recap-projection", response_model=WorldGraphRecapProjection, dependencies=[Depends(native_graph_gm_dependency)])
def post_world_graph_recap_projection(
    request_context: Request,
    request: WorldGraphProjectionRequest,
) -> dict[str, Any] | JSONResponse:
    """Exact World Graph snapshot + canonical recap → versioned recap projection."""
    try:
        _reject_query_params(request_context)
        raise WorldGraphProjectionServiceError(
            "Select a managed World to inspect its native graph.",
            code="legacy_projection_retired", status_code=410,
        )
    except WorldGraphProjectionServiceError as exc:
        return _error_response(exc)
    except Exception:
        return _error_response(
            WorldGraphProjectionServiceError(
                "World graph recap projection failed unexpectedly.",
                code="projection_internal_error",
                status_code=500,
            )
        )


__all__ = ["router"]
