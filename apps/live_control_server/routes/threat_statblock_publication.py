"""SBW09a: browser-safe publication-operation begin/read/reconcile/cancel routes."""
from __future__ import annotations

from typing import Any

from fastapi import APIRouter, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from fastapi.routing import APIRoute

from apps.live_control_server.config import repo_root, world_graph_root
from apps.live_control_server.models.threat_statblock_publication import (
    BeginThreatStatblockPublicationRequestV1,
    CancelThreatStatblockPublicationRequestV1,
    ReconcileThreatStatblockPublicationRequestV1,
    ThreatStatblockPublicationDiagnosticV1,
    ThreatStatblockPublicationOperationResponseV1,
)
from apps.live_control_server.services.threat_statblock_publication import (
    ThreatStatblockPublicationError,
    begin_or_resume_publication_operation,
    cancel_publication_operation,
    map_store_error,
    read_publication_operation,
    reconcile_publication_operation,
)
from apps.live_control_server.services.threat_statblock_publication_store import (
    ThreatStatblockPublicationStoreError,
)

router = APIRouter(prefix="/api/live/threat-drafts", tags=["threat-statblock-publication"])


def _error_response(exc: ThreatStatblockPublicationError) -> JSONResponse:
    body = exc.response().model_dump(mode="json", by_alias=True, exclude_none=True)
    return JSONResponse(status_code=exc.status_code, content=body)


def _store_error_response(exc: ThreatStatblockPublicationStoreError) -> JSONResponse:
    return _error_response(map_store_error(exc))


def _request_validation_error_response(exc: RequestValidationError) -> JSONResponse:
    errors = exc.errors()
    if any(error.get("type") == "extra_forbidden" for error in errors):
        message = "Publication-operation request contains unsupported fields."
    else:
        message = "Publication-operation request does not match the required contract."
    return _error_response(
        ThreatStatblockPublicationError(
            message,
            code="invalid_request",
            status_code=422,
            diagnostics=[
                ThreatStatblockPublicationDiagnosticV1(code="invalid_request", message=message)
            ],
        )
    )


class _ThreatStatblockPublicationAPIRoute(APIRoute):
    def get_route_handler(self):
        route_handler = super().get_route_handler()

        async def wrapped_route_handler(request: Request):
            try:
                return await route_handler(request)
            except RequestValidationError as exc:
                return _request_validation_error_response(exc)

        return wrapped_route_handler


publication_router = APIRouter(route_class=_ThreatStatblockPublicationAPIRoute)


def _reject_selector_query(request: Request) -> None:
    if request.query_params:
        raise ThreatStatblockPublicationError(
            "Publication-operation routes do not accept query parameters.",
            code="invalid_request",
            status_code=422,
        )


def _ok_response(response: ThreatStatblockPublicationOperationResponseV1) -> dict[str, Any]:
    return response.model_dump(mode="json", by_alias=True)


@publication_router.post(
    "/{draft_id}/publication-operations",
    response_model=None,
)
def post_begin_publication_operation(
    request: Request,
    draft_id: str,
    body: BeginThreatStatblockPublicationRequestV1,
):
    try:
        _reject_selector_query(request)
        result = begin_or_resume_publication_operation(
            repo_root(),
            draft_id=draft_id,
            request=body,
            graph_root=world_graph_root(),
        )
        return _ok_response(result)
    except ThreatStatblockPublicationError as exc:
        return _error_response(exc)
    except ThreatStatblockPublicationStoreError as exc:
        return _store_error_response(exc)


@publication_router.get(
    "/{draft_id}/publication-operations/{operation_id}",
    response_model=None,
)
def get_publication_operation_route(
    request: Request,
    draft_id: str,
    operation_id: str,
):
    try:
        _reject_selector_query(request)
        result = read_publication_operation(
            repo_root(),
            draft_id=draft_id,
            operation_id=operation_id,
        )
        return _ok_response(result)
    except ThreatStatblockPublicationError as exc:
        return _error_response(exc)
    except ThreatStatblockPublicationStoreError as exc:
        return _store_error_response(exc)


@publication_router.post(
    "/{draft_id}/publication-operations/{operation_id}:reconcile",
    response_model=None,
)
def post_reconcile_publication_operation(
    request: Request,
    draft_id: str,
    operation_id: str,
    body: ReconcileThreatStatblockPublicationRequestV1,
):
    try:
        _reject_selector_query(request)
        result = reconcile_publication_operation(
            repo_root(),
            draft_id=draft_id,
            operation_id=operation_id,
            request=body,
            graph_root=world_graph_root(),
        )
        return _ok_response(result)
    except ThreatStatblockPublicationError as exc:
        return _error_response(exc)
    except ThreatStatblockPublicationStoreError as exc:
        return _store_error_response(exc)


@publication_router.post(
    "/{draft_id}/publication-operations/{operation_id}:cancel",
    response_model=None,
)
def post_cancel_publication_operation(
    request: Request,
    draft_id: str,
    operation_id: str,
    body: CancelThreatStatblockPublicationRequestV1,
):
    try:
        _reject_selector_query(request)
        result = cancel_publication_operation(
            repo_root(),
            draft_id=draft_id,
            operation_id=operation_id,
            request=body,
        )
        return _ok_response(result)
    except ThreatStatblockPublicationError as exc:
        return _error_response(exc)
    except ThreatStatblockPublicationStoreError as exc:
        return _store_error_response(exc)


router.include_router(publication_router)
