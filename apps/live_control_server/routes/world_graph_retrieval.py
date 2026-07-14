"""World Graph retrieval + source-anchor admission route (PR010A)."""

from __future__ import annotations

from typing import Any

from fastapi import APIRouter, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from fastapi.routing import APIRoute

from apps.live_control_server.services.world_graph_retrieval import (
    WorldGraphRetrievalServiceError,
    get_campaign_object,
    get_object_evidence,
    get_object_neighborhood,
    read_source_anchor,
    search_campaign_graph,
)
from graph_memory.retrieval.models import (
    WorldGraphEvidenceRequest,
    WorldGraphNeighborhoodRequest,
    WorldGraphObjectRequest,
    WorldGraphRetrievalDiagnostic,
    WorldGraphRetrievalResult,
    WorldGraphSearchRequest,
    WorldGraphSourceAnchorReadRequest,
    WorldGraphSourceAnchorReadResult,
)


def _request_validation_error_response(exc: RequestValidationError) -> JSONResponse:
    errors = exc.errors()
    if any(error.get("type") == "extra_forbidden" for error in errors):
        message = "Retrieval request contains unsupported fields."
    else:
        message = "Retrieval request does not match the required contract."
    return _error_response(
        WorldGraphRetrievalServiceError(
            message,
            code="invalid_request",
            status_code=422,
            diagnostics=[
                WorldGraphRetrievalDiagnostic(
                    code="invalid_request",
                    message=message,
                    severity="error",
                )
            ],
        )
    )


class _RetrievalAPIRoute(APIRoute):
    def get_route_handler(self):
        route_handler = super().get_route_handler()

        async def wrapped_route_handler(request: Request):
            try:
                return await route_handler(request)
            except RequestValidationError as exc:
                return _request_validation_error_response(exc)

        return wrapped_route_handler


router = APIRouter(
    prefix="/api/live/world-graph/retrieval",
    tags=["world-graph-retrieval"],
    route_class=_RetrievalAPIRoute,
)


def _error_response(exc: WorldGraphRetrievalServiceError) -> JSONResponse:
    return JSONResponse(
        status_code=exc.status_code,
        content=exc.response().model_dump(mode="json", by_alias=True),
    )


def _reject_query_params(request: Request) -> None:
    if request.query_params:
        raise WorldGraphRetrievalServiceError(
            "Retrieval routes do not accept query parameters.",
            code="invalid_request",
            status_code=422,
            diagnostics=[
                WorldGraphRetrievalDiagnostic(
                    code="invalid_request",
                    message="Retrieval routes do not accept query parameters.",
                    severity="error",
                )
            ],
        )


@router.post("/search", response_model=WorldGraphRetrievalResult)
def post_world_graph_retrieval_search(
    request_context: Request,
    request: WorldGraphSearchRequest,
) -> dict[str, Any] | JSONResponse:
    try:
        _reject_query_params(request_context)
        response = search_campaign_graph(request)
    except WorldGraphRetrievalServiceError as exc:
        return _error_response(exc)
    except Exception:
        return _error_response(
            WorldGraphRetrievalServiceError(
                "World graph retrieval failed unexpectedly.",
                code="retrieval_internal_error",
                status_code=500,
            )
        )
    return response.model_dump(mode="json", by_alias=True)


@router.post("/object", response_model=WorldGraphRetrievalResult)
def post_world_graph_retrieval_object(
    request_context: Request,
    request: WorldGraphObjectRequest,
) -> dict[str, Any] | JSONResponse:
    try:
        _reject_query_params(request_context)
        response = get_campaign_object(request)
    except WorldGraphRetrievalServiceError as exc:
        return _error_response(exc)
    except Exception:
        return _error_response(
            WorldGraphRetrievalServiceError(
                "World graph retrieval failed unexpectedly.",
                code="retrieval_internal_error",
                status_code=500,
            )
        )
    return response.model_dump(mode="json", by_alias=True)


@router.post("/neighborhood", response_model=WorldGraphRetrievalResult)
def post_world_graph_retrieval_neighborhood(
    request_context: Request,
    request: WorldGraphNeighborhoodRequest,
) -> dict[str, Any] | JSONResponse:
    try:
        _reject_query_params(request_context)
        response = get_object_neighborhood(request)
    except WorldGraphRetrievalServiceError as exc:
        return _error_response(exc)
    except Exception:
        return _error_response(
            WorldGraphRetrievalServiceError(
                "World graph retrieval failed unexpectedly.",
                code="retrieval_internal_error",
                status_code=500,
            )
        )
    return response.model_dump(mode="json", by_alias=True)


@router.post("/evidence", response_model=WorldGraphRetrievalResult)
def post_world_graph_retrieval_evidence(
    request_context: Request,
    request: WorldGraphEvidenceRequest,
) -> dict[str, Any] | JSONResponse:
    try:
        _reject_query_params(request_context)
        response = get_object_evidence(request)
    except WorldGraphRetrievalServiceError as exc:
        return _error_response(exc)
    except Exception:
        return _error_response(
            WorldGraphRetrievalServiceError(
                "World graph retrieval failed unexpectedly.",
                code="retrieval_internal_error",
                status_code=500,
            )
        )
    return response.model_dump(mode="json", by_alias=True)


@router.post("/source-anchor/read", response_model=WorldGraphSourceAnchorReadResult)
def post_world_graph_retrieval_source_anchor_read(
    request_context: Request,
    request: WorldGraphSourceAnchorReadRequest,
) -> dict[str, Any] | JSONResponse:
    try:
        _reject_query_params(request_context)
        response = read_source_anchor(request)
    except WorldGraphRetrievalServiceError as exc:
        return _error_response(exc)
    except Exception:
        return _error_response(
            WorldGraphRetrievalServiceError(
                "World graph retrieval failed unexpectedly.",
                code="retrieval_internal_error",
                status_code=500,
            )
        )
    return response.model_dump(mode="json", by_alias=True)


__all__ = ["router"]
