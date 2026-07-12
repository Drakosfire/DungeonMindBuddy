"""Stable status/prepare/confirm routes for the Eldyrwild bootstrap."""

from __future__ import annotations

from typing import Any

from fastapi import APIRouter, Request
from fastapi.responses import JSONResponse

from apps.live_control_server.models.world_graph_bootstrap import (
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

router = APIRouter(
    prefix="/api/live/world-graph-bootstrap",
    tags=["world-graph-bootstrap"],
)
_FORBIDDEN_SELECTOR_FIELDS = frozenset(
    {
        "root",
        "bundlePath",
        "bundleId",
        "bundleDigest",
        "worldId",
        "campaignId",
        "focusSessionId",
        "force",
        "skipValidation",
    }
)


def _error_response(exc: WorldGraphBootstrapError) -> JSONResponse:
    return JSONResponse(
        status_code=exc.status_code,
        content=exc.response().model_dump(mode="json", by_alias=True),
    )


def _reject_selector_query(request: Request) -> None:
    blocked = sorted(_FORBIDDEN_SELECTOR_FIELDS & set(request.query_params))
    if blocked:
        raise WorldGraphBootstrapError(
            "Bootstrap selectors are server-owned and cannot be submitted.",
            code="invalid_request",
            status_code=422,
            bootstrap_state="error",
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
