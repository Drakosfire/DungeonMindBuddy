"""Revision-pinned World Graph projection routes (PR007A + PR380A recap)."""

from __future__ import annotations

from typing import Annotated, Any

from fastapi import APIRouter, Query, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from fastapi.routing import APIRoute

from apps.live_control_server.services.world_graph_projection import (
    WorldGraphProjectionServiceError,
    project_world_graph,
)
from apps.live_control_server.services.world_graph_recap_projection import (
    build_world_graph_recap_projection_payload,
)
from apps.live_control_server.services.world_graph_sessions import (
    DEFAULT_WORLD_ID,
    WorldGraphSessionsResponse,
    list_world_graph_sessions,
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


@router.get("/sessions", response_model=WorldGraphSessionsResponse)
def get_world_graph_sessions(
    world_id: Annotated[str, Query()] = DEFAULT_WORLD_ID,
    campaign_id: Annotated[str | None, Query()] = None,
) -> dict[str, Any]:
    """Browse catalog: sessions present in active World Graph contributions."""
    return list_world_graph_sessions(
        world_id=world_id,
        campaign_id=campaign_id,
    ).model_dump(mode="json")


@router.post("/projection", response_model=WorldGraphProjection)
def post_world_graph_projection(
    request_context: Request,
    request: WorldGraphProjectionRequest,
) -> dict[str, Any] | JSONResponse:
    try:
        _reject_query_params(request_context)
        response = project_world_graph(request)
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
    return response.model_dump(mode="json", by_alias=True)


@router.post("/recap-projection", response_model=WorldGraphRecapProjection)
def post_world_graph_recap_projection(
    request_context: Request,
    request: WorldGraphProjectionRequest,
) -> dict[str, Any] | JSONResponse:
    """Exact World Graph snapshot + canonical recap → versioned recap projection."""
    try:
        _reject_query_params(request_context)
        return build_world_graph_recap_projection_payload(request)
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
