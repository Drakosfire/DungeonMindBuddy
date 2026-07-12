"""Stable status/prepare/confirm routes for the Eldyrwild bootstrap."""

from __future__ import annotations

from typing import Any

from fastapi import APIRouter, Request
from fastapi.exceptions import RequestValidationError
from fastapi.routing import APIRoute
from fastapi.responses import JSONResponse

from apps.live_control_server.models.world_graph_bootstrap import (
    BootstrapDiagnostic,
    WorldGraphBootstrapConfirmRequest,
    WorldGraphBootstrapConfirmResponse,
    WorldGraphBootstrapPrepareRequest,
    WorldGraphBootstrapPrepareResponse,
    WorldGraphBootstrapStatusResponse,
)
from apps.live_control_server.services.world_graph_bootstrap import (
    WorldGraphBootstrapError,
    confirm_world_graph_bootstrap,
    get_world_graph_bootstrap_status,
    prepare_world_graph_bootstrap,
)


def _request_validation_error_response(exc: RequestValidationError) -> JSONResponse:
    errors = exc.errors()
    if any(error.get("type") == "extra_forbidden" for error in errors):
        code = "invalid_request"
        message = "Bootstrap request contains unsupported fields."
    elif any("actor" in {str(item) for item in error.get("loc", ())} for error in errors):
        code = "invalid_actor"
        message = "Bootstrap actor is required and must be a bounded non-blank string."
    else:
        code = "invalid_request"
        message = "Bootstrap request does not match the required contract."
    return _error_response(
        WorldGraphBootstrapError(
            message,
            code=code,
            status_code=422,
            bootstrap_state="error",
            diagnostics=[BootstrapDiagnostic(code=code, message=message)],
        )
    )


class _BootstrapAPIRoute(APIRoute):
    def get_route_handler(self):
        route_handler = super().get_route_handler()

        async def wrapped_route_handler(request: Request):
            try:
                return await route_handler(request)
            except RequestValidationError as exc:
                return _request_validation_error_response(exc)

        return wrapped_route_handler


router = APIRouter(
    prefix="/api/live/world-graph-bootstrap",
    tags=["world-graph-bootstrap"],
    route_class=_BootstrapAPIRoute,
)


def _error_response(exc: WorldGraphBootstrapError) -> JSONResponse:
    return JSONResponse(
        status_code=exc.status_code,
        content=exc.response().model_dump(mode="json", by_alias=True),
    )


def _reject_selector_query(request: Request) -> None:
    if request.query_params:
        raise WorldGraphBootstrapError(
            "Bootstrap routes do not accept query parameters.",
            code="invalid_request",
            status_code=422,
            bootstrap_state="error",
            diagnostics=[
                BootstrapDiagnostic(
                    code="invalid_request",
                    message="Bootstrap routes do not accept query parameters.",
                )
            ],
        )


@router.get("/status", response_model=WorldGraphBootstrapStatusResponse)
def get_bootstrap_status(request: Request) -> dict[str, Any] | JSONResponse:
    try:
        _reject_selector_query(request)
    except WorldGraphBootstrapError as exc:
        return _error_response(exc)
    try:
        response = get_world_graph_bootstrap_status()
    except Exception:
        return _error_response(
            WorldGraphBootstrapError(
                "The Eldyrwild bootstrap status operation failed unexpectedly.",
                code="bootstrap_internal_error",
                status_code=500,
                bootstrap_state="error",
            )
        )
    return response.model_dump(mode="json", by_alias=True)


@router.post(
    "/prepare",
    response_model=WorldGraphBootstrapPrepareResponse,
)
def post_bootstrap_prepare(
    request_context: Request,
    request: WorldGraphBootstrapPrepareRequest,
) -> dict[str, Any] | JSONResponse:
    try:
        _reject_selector_query(request_context)
        response = prepare_world_graph_bootstrap(request)
    except WorldGraphBootstrapError as exc:
        return _error_response(exc)
    except Exception:
        return _error_response(
            WorldGraphBootstrapError(
                "The Eldyrwild bootstrap prepare operation failed unexpectedly.",
                code="bootstrap_internal_error",
                status_code=500,
                bootstrap_state="error",
            )
        )
    return response.model_dump(mode="json", by_alias=True)


@router.post(
    "/confirm",
    response_model=WorldGraphBootstrapConfirmResponse,
)
def post_bootstrap_confirm(
    request_context: Request,
    request: WorldGraphBootstrapConfirmRequest,
) -> dict[str, Any] | JSONResponse:
    try:
        _reject_selector_query(request_context)
        response = confirm_world_graph_bootstrap(request)
    except WorldGraphBootstrapError as exc:
        return _error_response(exc)
    except Exception:
        return _error_response(
            WorldGraphBootstrapError(
                "The Eldyrwild bootstrap confirm operation failed unexpectedly.",
                code="bootstrap_internal_error",
                status_code=500,
                bootstrap_state="error",
            )
        )
    return response.model_dump(mode="json", by_alias=True)


__all__ = ["router"]
