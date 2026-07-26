"""Stable status/prepare/confirm routes for extract → World Supergraph promote."""

from __future__ import annotations

import logging
import uuid
from typing import Any

from fastapi import APIRouter, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from fastapi.routing import APIRoute

from apps.live_control_server.models.extract_promote import (
    ExtractPromoteConfirmReceipt,
    ExtractPromoteConfirmRequest,
    ExtractPromoteDiagnostic,
    ExtractPromotePrepareRequest,
    ExtractPromotePrepareResponse,
    ExactRunReviewPackage,
    ExtractPromoteStatusResponse,
    WorldbuildingWritePlanConfirmReceipt,
    WorldbuildingWritePlanConfirmRequest,
    WorldbuildingWritePlanPrepareRequest,
    WorldbuildingWritePlanResponse,
)
from apps.live_control_server.services.extract_promote import (
    ExtractPromoteError,
    confirm,
    confirm_worldbuilding,
    get_exact_run_review_package,
    get_status,
    prepare,
    prepare_worldbuilding,
)

logger = logging.getLogger(__name__)


def _error_response(exc: ExtractPromoteError) -> JSONResponse:
    body = exc.response().model_dump(mode="json", by_alias=True, exclude_none=True)
    # Interim dogfood inspect until review-package returns inspectable 200s for
    # binding failures (Backlog: false_anchor / run_not_promotable).
    logger.warning(
        "extract-promote error code=%s status=%s message=%s diagnostics=%s",
        exc.code,
        exc.status_code,
        str(exc),
        [
            {"code": item.code, "message": item.message, "severity": item.severity}
            for item in exc.diagnostics
        ],
    )
    return JSONResponse(status_code=exc.status_code, content=body)


def _request_validation_error_response(exc: RequestValidationError) -> JSONResponse:
    errors = exc.errors()
    if any(error.get("type") == "extra_forbidden" for error in errors):
        code = "invalid_request"
        message = "Extract-promote request contains unsupported fields."
    elif any(
        "confirming_principal" in {str(item) for item in error.get("loc", ())}
        or "prepared_by" in {str(item) for item in error.get("loc", ())}
        for error in errors
    ):
        code = "invalid_principal"
        message = "Prepared-by / confirming principal must be a bounded non-blank string."
    else:
        code = "invalid_request"
        message = "Extract-promote request does not match the required contract."
    return _error_response(
        ExtractPromoteError(
            message,
            code=code,
            status_code=422,
            diagnostics=[ExtractPromoteDiagnostic(code=code, message=message)],
        )
    )


class _ExtractPromoteAPIRoute(APIRoute):
    def get_route_handler(self):
        route_handler = super().get_route_handler()

        async def wrapped_route_handler(request: Request):
            try:
                return await route_handler(request)
            except RequestValidationError as exc:
                return _request_validation_error_response(exc)

        return wrapped_route_handler


router = APIRouter(
    prefix="/api/live/extract-promote",
    tags=["extract-promote"],
    route_class=_ExtractPromoteAPIRoute,
)


def _reject_selector_query(request: Request) -> None:
    if request.query_params:
        raise ExtractPromoteError(
            "Extract-promote routes do not accept query parameters.",
            code="invalid_request",
            status_code=422,
            diagnostics=[
                ExtractPromoteDiagnostic(
                    code="invalid_request",
                    message="Extract-promote routes do not accept query parameters.",
                )
            ],
        )


@router.get("/status", response_model=ExtractPromoteStatusResponse)
def get_extract_promote_status(request: Request) -> dict[str, Any] | JSONResponse:
    try:
        _reject_selector_query(request)
        response = get_status()
    except ExtractPromoteError as exc:
        return _error_response(exc)
    except Exception:
        return _error_response(
            ExtractPromoteError(
                "The extract-promote status operation failed unexpectedly.",
                code="extract_promote_internal_error",
                status_code=500,
            )
        )
    return response.model_dump(mode="json", by_alias=True)


@router.get("/runs/{run_id}/review-package", response_model=ExactRunReviewPackage)
def get_extract_promote_exact_run_review(
    request: Request,
    run_id: str,
) -> dict[str, Any] | JSONResponse:
    """Server-owned exact-run source/evidence projection (no sealed proposal)."""
    try:
        _reject_selector_query(request)
        response = get_exact_run_review_package(run_id)
    except ExtractPromoteError as exc:
        return _error_response(exc)
    except Exception:
        return _error_response(
            ExtractPromoteError(
                "The exact-run review package operation failed unexpectedly.",
                code="extract_promote_internal_error",
                status_code=500,
            )
        )
    return response.model_dump(mode="json", by_alias=True)


@router.post("/prepare", response_model=ExtractPromotePrepareResponse)
def post_extract_promote_prepare(
    request_context: Request,
    request: ExtractPromotePrepareRequest,
) -> dict[str, Any] | JSONResponse:
    try:
        _reject_selector_query(request_context)
        response = prepare(request)
    except ExtractPromoteError as exc:
        return _error_response(exc)
    except Exception:
        # Log the full traceback server-side; never echo exception text to clients.
        correlation_id = uuid.uuid4().hex[:12]
        logger.exception(
            "extract-promote prepare failed unexpectedly correlation_id=%s",
            correlation_id,
        )
        return _error_response(
            ExtractPromoteError(
                "The extract-promote prepare operation failed unexpectedly.",
                code="extract_promote_internal_error",
                status_code=500,
                diagnostics=[
                    ExtractPromoteDiagnostic(
                        code="internal_error",
                        message=f"Internal error. Reference: {correlation_id}",
                        severity="error",
                    )
                ],
            )
        )
    return response.model_dump(mode="json", by_alias=True)


@router.post(
    "/worldbuilding/prepare",
    response_model=WorldbuildingWritePlanResponse,
)
def post_worldbuilding_write_plan_prepare(
    request_context: Request,
    request: WorldbuildingWritePlanPrepareRequest,
) -> dict[str, Any] | JSONResponse:
    try:
        _reject_selector_query(request_context)
        response = prepare_worldbuilding(request)
    except ExtractPromoteError as exc:
        return _error_response(exc)
    except Exception:
        correlation_id = uuid.uuid4().hex[:12]
        logger.exception(
            "worldbuilding write-plan prepare failed unexpectedly correlation_id=%s",
            correlation_id,
        )
        return _error_response(
            ExtractPromoteError(
                "The worldbuilding write-plan prepare operation failed unexpectedly.",
                code="extract_promote_internal_error",
                status_code=500,
                diagnostics=[
                    ExtractPromoteDiagnostic(
                        code="internal_error",
                        message=f"Internal error. Reference: {correlation_id}",
                        severity="error",
                    )
                ],
            )
        )
    return response.model_dump(mode="json", by_alias=True)


@router.post(
    "/worldbuilding/confirm",
    response_model=WorldbuildingWritePlanConfirmReceipt,
)
def post_worldbuilding_write_plan_confirm(
    request_context: Request,
    request: WorldbuildingWritePlanConfirmRequest,
) -> dict[str, Any] | JSONResponse:
    try:
        _reject_selector_query(request_context)
        response = confirm_worldbuilding(request)
    except ExtractPromoteError as exc:
        return _error_response(exc)
    except Exception:
        correlation_id = uuid.uuid4().hex[:12]
        logger.exception(
            "worldbuilding write-plan confirm failed unexpectedly correlation_id=%s",
            correlation_id,
        )
        return _error_response(
            ExtractPromoteError(
                "The worldbuilding write-plan confirm operation failed unexpectedly.",
                code="extract_promote_internal_error",
                status_code=500,
                diagnostics=[
                    ExtractPromoteDiagnostic(
                        code="internal_error",
                        message=f"Internal error. Reference: {correlation_id}",
                        severity="error",
                    )
                ],
            )
        )
    return response.model_dump(mode="json", by_alias=True)


@router.post("/confirm", response_model=ExtractPromoteConfirmReceipt)
def post_extract_promote_confirm(
    request_context: Request,
    request: ExtractPromoteConfirmRequest,
) -> dict[str, Any] | JSONResponse:
    try:
        _reject_selector_query(request_context)
        response = confirm(request)
    except ExtractPromoteError as exc:
        return _error_response(exc)
    except Exception:
        correlation_id = uuid.uuid4().hex[:12]
        logger.exception(
            "extract-promote confirm failed unexpectedly correlation_id=%s",
            correlation_id,
        )
        return _error_response(
            ExtractPromoteError(
                "The extract-promote confirm operation failed unexpectedly.",
                code="extract_promote_internal_error",
                status_code=500,
                diagnostics=[
                    ExtractPromoteDiagnostic(
                        code="internal_error",
                        message=f"Internal error. Reference: {correlation_id}",
                        severity="error",
                    )
                ],
            )
        )
    return response.model_dump(mode="json", by_alias=True)
