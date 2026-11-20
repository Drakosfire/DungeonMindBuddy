"""Current World retrieval consumes native authority; recap-context remains separate."""

from __future__ import annotations

from typing import Any

from fastapi import APIRouter, Depends, HTTPException, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from fastapi.routing import APIRoute
from dungeonmind.domain.errors import PersistenceIntegrityError, PersistenceUnavailableError
from apps.live_control_server.services.world_graph_projection import WorldGraphProjectionServiceError


from apps.live_control_server.services.agent_graph_auth import (
    enforce_native_graph_gm,
    native_graph_gm_dependency,
)
from apps.live_control_server.routes.native_graph_inspection import (
    complete_object as native_complete_object,
)
from apps.live_control_server.models.native_graph_inspection import NativeCompleteObjectRead
from apps.live_control_server.services.native_graph_inspection import (
    InspectionUnavailable,
    open_neighborhood_anchor,
    shared_exact_object,
    shared_evidence,
    shared_neighborhood,
    shared_search,
)
from apps.live_control_server.models.world_graph_object_projection import (
    WorldGraphObjectProjectionRequest,
    WorldGraphObjectProjectionResult,
)
from apps.live_control_server.services.world_graph_retrieval import (
    WorldGraphRetrievalServiceError,
    list_recap_context_v2,
    read_recap_context_v2,
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
    RecapContextIndexRequestV2,
    RecapContextIndexResultV2,
    RecapContextReadRequestV2,
    RecapContextReadResultV2,
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
    dependencies=[Depends(native_graph_gm_dependency)],
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


def _native_failure_response(exc) -> JSONResponse:
    if isinstance(exc, PersistenceUnavailableError):
        status = 503
    elif isinstance(exc, PersistenceIntegrityError):
        status = 500
    else:
        status = getattr(exc, "status_code", 409)
    return _error_response(WorldGraphRetrievalServiceError(
        "The selected native Graph material is unavailable. Refresh and inspect again.",
        code=getattr(exc, "code", "native_inspection_unavailable"),
        status_code=status,
    ))


_NATIVE_READ_FAILURES = (
    InspectionUnavailable,
    WorldGraphProjectionServiceError,
    PersistenceIntegrityError,
    PersistenceUnavailableError,
)


@router.post("/search", response_model=WorldGraphRetrievalResult)
def post_world_graph_retrieval_search(
    request_context: Request,
    request: WorldGraphSearchRequest,
) -> dict[str, Any] | JSONResponse:
    try:
        _reject_query_params(request_context)
        response = shared_search(request, enforce_native_graph_gm(request_context))
    except WorldGraphRetrievalServiceError as exc:
        return _error_response(exc)
    except HTTPException:
        raise
    except _NATIVE_READ_FAILURES as exc:
        return _native_failure_response(exc)
    except Exception:
        return _error_response(WorldGraphRetrievalServiceError(
            "World graph retrieval failed unexpectedly.",
            code="retrieval_internal_error", status_code=500,
        ))
    return response.model_dump(mode="json", by_alias=True)


@router.post("/object", response_model=WorldGraphRetrievalResult)
def post_world_graph_retrieval_object(
    request_context: Request,
    request: WorldGraphObjectRequest,
) -> dict[str, Any] | JSONResponse:
    try:
        _reject_query_params(request_context)
        response = shared_exact_object(request, enforce_native_graph_gm(request_context))
    except WorldGraphRetrievalServiceError as exc:
        return _error_response(exc)
    except HTTPException:
        raise
    except _NATIVE_READ_FAILURES as exc:
        return _native_failure_response(exc)
    except Exception:
        return _error_response(WorldGraphRetrievalServiceError(
            "World graph retrieval failed unexpectedly.",
            code="retrieval_internal_error", status_code=500,
        ))
    return response.model_dump(mode="json", by_alias=True)


@router.post("/neighborhood", response_model=WorldGraphRetrievalResult)
def post_world_graph_retrieval_neighborhood(
    request_context: Request,
    request: WorldGraphNeighborhoodRequest,
) -> dict[str, Any] | JSONResponse:
    try:
        _reject_query_params(request_context)
        response = shared_neighborhood(request, enforce_native_graph_gm(request_context))
    except WorldGraphRetrievalServiceError as exc:
        return _error_response(exc)
    except HTTPException:
        raise
    except _NATIVE_READ_FAILURES as exc:
        return _native_failure_response(exc)
    except Exception:
        return _error_response(WorldGraphRetrievalServiceError(
            "World graph retrieval failed unexpectedly.",
            code="retrieval_internal_error", status_code=500,
        ))
    return response.model_dump(mode="json", by_alias=True)


@router.post("/evidence", response_model=WorldGraphRetrievalResult)
def post_world_graph_retrieval_evidence(
    request_context: Request,
    request: WorldGraphEvidenceRequest,
) -> dict[str, Any] | JSONResponse:
    try:
        _reject_query_params(request_context)
        response = shared_evidence(request, enforce_native_graph_gm(request_context))
    except WorldGraphRetrievalServiceError as exc:
        return _error_response(exc)
    except HTTPException:
        raise
    except _NATIVE_READ_FAILURES as exc:
        return _native_failure_response(exc)
    except Exception:
        return _error_response(WorldGraphRetrievalServiceError(
            "World graph retrieval failed unexpectedly.",
            code="retrieval_internal_error", status_code=500,
        ))
    return response.model_dump(mode="json", by_alias=True)


@router.post("/complete-object", response_model=WorldGraphObjectProjectionResult)
def post_world_graph_complete_object(
    request_context: Request,
    request: WorldGraphObjectProjectionRequest,
) -> dict[str, Any] | JSONResponse:
    try:
        _reject_query_params(request_context)
    except WorldGraphRetrievalServiceError as exc:
        return _error_response(exc)
    principal = enforce_native_graph_gm(request_context)
    return native_complete_object(NativeCompleteObjectRead(request=request), principal)


@router.post("/source-anchor/read", response_model=WorldGraphSourceAnchorReadResult)
def post_world_graph_retrieval_source_anchor_read(
    request_context: Request,
    request: WorldGraphSourceAnchorReadRequest,
) -> dict[str, Any] | JSONResponse:
    try:
        _reject_query_params(request_context)
        principal = enforce_native_graph_gm(request_context)
        if not request.anchor_id.startswith("native-neighborhood:"):
            response = WorldGraphSourceAnchorReadResult(outcome="empty", anchor_id=request.anchor_id)
        else:
            try:
                response = open_neighborhood_anchor(request, principal)
            except InspectionUnavailable as exc:
                # Ordinary unavailable support is withheld. Authority/infrastructure
                # failures must remain non-success, never an empty-read fallback.
                if exc.code not in {
                    "native_inspection_assertion_unavailable",
                    "native_inspection_evidence_unavailable",
                    "native_inspection_source_unavailable",
                }:
                    raise
                response = WorldGraphSourceAnchorReadResult(outcome="empty", anchor_id=request.anchor_id)
    except WorldGraphRetrievalServiceError as exc:
        return _error_response(exc)
    except HTTPException:
        raise
    except _NATIVE_READ_FAILURES as exc:
        return _native_failure_response(exc)
    except Exception:
        return _error_response(WorldGraphRetrievalServiceError(
            "World graph retrieval failed unexpectedly.",
            code="retrieval_internal_error", status_code=500,
        ))
    return response.model_dump(mode="json", by_alias=True)


@router.post("/recap-context/v2/index", response_model=RecapContextIndexResultV2)
def post_recap_context_index_v2(
    request_context: Request,
    request: RecapContextIndexRequestV2,
) -> dict[str, Any] | JSONResponse:
    try:
        _reject_query_params(request_context)
        response = list_recap_context_v2(request)
    except WorldGraphRetrievalServiceError as exc:
        return _error_response(exc)
    except Exception:
        return _error_response(WorldGraphRetrievalServiceError(
            "Recap context index failed unexpectedly.", code="retrieval_internal_error", status_code=500,
        ))
    return response.model_dump(mode="json", by_alias=True)


@router.post("/recap-context/v2/read", response_model=RecapContextReadResultV2)
def post_recap_context_read_v2(
    request_context: Request,
    request: RecapContextReadRequestV2,
) -> dict[str, Any] | JSONResponse:
    try:
        _reject_query_params(request_context)
        response = read_recap_context_v2(request)
    except WorldGraphRetrievalServiceError as exc:
        return _error_response(exc)
    except Exception:
        return _error_response(WorldGraphRetrievalServiceError(
            "Recap context read failed unexpectedly.", code="retrieval_internal_error", status_code=500,
        ))
    return response.model_dump(mode="json", by_alias=True)


__all__ = ["router"]
