"""Local guest graph API mounted on Buddy's existing index surface."""

from __future__ import annotations

import json
from typing import Any, Callable

import psycopg
from dungeonmind.domain.errors import (
    PersistenceIntegrityError,
    PersistenceUnavailableError,
)
from fastapi import APIRouter, HTTPException, Request
from fastapi.responses import JSONResponse, Response
from starlette.concurrency import run_in_threadpool

from application_state.errors import ApplicationStateUnavailableError
from application_state.index_graph.sessions import (
    COOKIE_PATH,
    SESSION_TTL,
    IndexGraphSession,
    IndexGraphSessionError,
    create_session,
    csrf_token,
    local_profile,
    lookup_session,
    read_cookie_credential,
    request_session,
    require_index_graph_boundary,
)
from application_state.index_graph.store import IndexGraphStoreUnavailable
from apps.live_control_server.native_graph_demo import DemoError, NativeGraphDemoService
from apps.live_control_server.services.index_graph import open_index_graph_service


router = APIRouter(prefix="/api/live/index-graph", tags=["index-graph"])
MAX_REQUEST_BYTES = 16 * 1024
SESSION_NOTICE = (
    "This graph belongs to this private browser session. The session cookie is its only "
    "recovery link; if it is lost or expires, the graph remains stored but cannot be "
    "reattached automatically."
)


def _error(code: str, message: str, status: int) -> JSONResponse:
    response = JSONResponse({"code": code, "error": message}, status_code=status)
    response.headers["Cache-Control"] = "no-store"
    return response


def _http_exception(exc: HTTPException) -> JSONResponse:
    detail = exc.detail
    if isinstance(detail, dict):
        code = detail.get("code", "request_rejected")
        message = detail.get("message", "The graph request was rejected.")
    else:
        code = "request_rejected"
        message = (
            str(detail)
            if isinstance(detail, str)
            else "The graph request was rejected."
        )
    return _error(str(code), str(message), exc.status_code)


def _require_no_query(request: Request) -> None:
    if request.url.query:
        raise HTTPException(
            status_code=400,
            detail={
                "code": "query_not_supported",
                "message": "This endpoint does not accept query parameters.",
            },
        )


def _resolve_session(
    request: Request, *, unsafe: bool
) -> tuple[str, IndexGraphSession]:
    require_index_graph_boundary(request, unsafe=unsafe)
    _require_no_query(request)
    return request_session(request, unsafe=unsafe)


def _with_service(
    request: Request,
    *,
    unsafe: bool,
    action: Callable[[NativeGraphDemoService], dict[str, Any]],
) -> JSONResponse:
    try:
        _credential, session = _resolve_session(request, unsafe=unsafe)
        with open_index_graph_service(session) as service:
            result = action(service)
        response = JSONResponse(result)
        response.headers["Cache-Control"] = "no-store"
        return response
    except HTTPException as exc:
        return _http_exception(exc)
    except IndexGraphSessionError as exc:
        return _error(exc.code, str(exc), exc.status)
    except DemoError as exc:
        return _error(exc.code, str(exc), exc.status)
    except (
        IndexGraphStoreUnavailable,
        ApplicationStateUnavailableError,
        psycopg.Error,
    ):
        return _error(
            "application_state_unavailable",
            "Buddy application state is unavailable, so the graph operation outcome could not be verified. Check the same operation ID before trying again.",
            503,
        )
    except PersistenceUnavailableError:
        return _error(
            "native_authority_unavailable",
            "DungeonMind native readback is unavailable. A durable reservation or source admission may already exist. Check this same operation ID and use it for any recovery attempt; do not create a replacement operation.",
            503,
        )
    except PersistenceIntegrityError:
        return _error(
            "native_authority_integrity_failure",
            "DungeonMind could not verify its saved native evidence. The operation outcome may be uncertain. Check this same operation ID before recovery; do not create a replacement or assume it was committed.",
            503,
        )
    except (OSError, TypeError, ValueError):
        # Adapter failures can occur before or after service work, so the
        # response preserves uncertainty instead of claiming no write occurred.
        return _error(
            "native_authority_unavailable",
            "The configured DungeonMind graph authority could not be verified. The operation outcome may be uncertain; check the same operation ID before trying again.",
            503,
        )


def _reject_body_size(request: Request) -> None:
    lengths = request.headers.getlist("content-length")
    if len(lengths) > 1:
        raise HTTPException(
            400,
            detail={
                "code": "invalid_request",
                "message": "The request body is malformed.",
            },
        )
    if lengths:
        declared = lengths[0].strip()
        if not declared.isascii() or not declared.isdecimal():
            raise HTTPException(
                400,
                detail={
                    "code": "invalid_request",
                    "message": "The request body is malformed.",
                },
            )
        if int(declared) > MAX_REQUEST_BYTES:
            raise HTTPException(
                413,
                detail={
                    "code": "limit_exceeded",
                    "message": "The request body is too large.",
                },
            )


async def _read_json(request: Request) -> dict[str, Any] | JSONResponse:
    _reject_body_size(request)
    content_lengths = request.headers.getlist("content-length")
    transfer_encodings = request.headers.getlist("transfer-encoding")
    if (
        len(transfer_encodings) > 1
        or (content_lengths and transfer_encodings)
        or (transfer_encodings and transfer_encodings[0].strip().lower() != "chunked")
    ):
        return _error("invalid_request", "The request body is malformed.", 400)
    content_types = request.headers.getlist("content-type")
    media_type = (
        content_types[0].partition(";")[0].strip().lower()
        if len(content_types) == 1
        else ""
    )
    if media_type != "application/json":
        return _error("invalid_request", "Send a JSON request body.", 415)
    raw = bytearray()
    async for chunk in request.stream():
        raw.extend(chunk)
        if len(raw) > MAX_REQUEST_BYTES:
            return _error("limit_exceeded", "The request body is too large.", 413)

    def unique_keys(pairs: list[tuple[str, Any]]) -> dict[str, Any]:
        result: dict[str, Any] = {}
        for key, value in pairs:
            if key in result:
                raise ValueError("duplicate JSON key")
            result[key] = value
        return result

    try:
        payload = json.loads(raw, object_pairs_hook=unique_keys)
    except (json.JSONDecodeError, UnicodeDecodeError, ValueError):
        return _error("invalid_request", "The request body must be valid JSON.", 400)
    if not isinstance(payload, dict):
        return _error("invalid_request", "The request body must be a JSON object.", 400)
    return payload


@router.post("/session")
async def start_or_resume_session(request: Request) -> Response:
    try:
        require_index_graph_boundary(request, unsafe=True)
        _require_no_query(request)
        _reject_body_size(request)
        if request.headers.getlist("transfer-encoding"):
            return _error(
                "invalid_request",
                "Session bootstrap does not accept a request body.",
                400,
            )
        body = bytearray()
        async for chunk in request.stream():
            body.extend(chunk)
            if body:
                return _error(
                    "invalid_request",
                    "Session bootstrap does not accept a request body.",
                    400,
                )
        _origin, _host, cookie_name = local_profile()
        cookies = request.headers.getlist("cookie")
        if len(cookies) > 1:
            raise IndexGraphSessionError(
                "session_cookie_invalid", "The guest session cookie is ambiguous."
            )
        # A supplied unknown or expired credential is never silently replaced
        # with a new graph.
        credential = read_cookie_credential(request, cookie_name)
        if credential is None:
            credential, session = create_session()
            created = True
        else:
            session = lookup_session(credential)
            created = False
        payload = {
            "csrf_token": csrf_token(credential, session.session_id),
            "notice": SESSION_NOTICE,
        }
        response = JSONResponse(payload, headers={"Cache-Control": "no-store"})
        if created:
            response.set_cookie(
                cookie_name,
                credential,
                max_age=int(SESSION_TTL.total_seconds()),
                path=COOKIE_PATH,
                secure=False,
                httponly=True,
                samesite="strict",
            )
        return response
    except HTTPException as exc:
        return _http_exception(exc)
    except IndexGraphSessionError as exc:
        return _error(exc.code, str(exc), exc.status)


@router.get("/graph")
def get_graph(request: Request) -> Response:
    return _with_service(request, unsafe=False, action=lambda service: service.graph())


@router.get("/operations/{operation_id}")
def get_operation(operation_id: str, request: Request) -> Response:
    return _with_service(
        request,
        unsafe=False,
        action=lambda service: service.operation(operation_id),
    )


@router.post("/prepare")
async def prepare_operation(request: Request) -> Response:
    try:
        payload = await _read_json(request)
    except HTTPException as exc:
        return _http_exception(exc)
    if isinstance(payload, Response):
        return payload
    try:
        require_index_graph_boundary(request, unsafe=True)
        _require_no_query(request)
    except HTTPException as exc:
        return _http_exception(exc)
    return await run_in_threadpool(
        _with_service,
        request,
        unsafe=True,
        action=lambda service: service.prepare(payload),
    )


@router.post("/confirm")
async def confirm_operation(request: Request) -> Response:
    try:
        payload = await _read_json(request)
    except HTTPException as exc:
        return _http_exception(exc)
    if isinstance(payload, Response):
        return payload
    if set(payload) != {"operation_id"} or not isinstance(payload["operation_id"], str):
        return _error(
            "invalid_request",
            "Confirm requires only the prepared operation_id.",
            400,
        )
    try:
        require_index_graph_boundary(request, unsafe=True)
        _require_no_query(request)
    except HTTPException as exc:
        return _http_exception(exc)
    return await run_in_threadpool(
        _with_service,
        request,
        unsafe=True,
        action=lambda service: service.confirm(payload["operation_id"]),
    )
