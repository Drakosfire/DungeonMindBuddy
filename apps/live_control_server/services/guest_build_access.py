"""Explicit session-bound authorization for ordinary guest Build documents."""
from __future__ import annotations

import re
from uuid import UUID

from fastapi import HTTPException, Request
from pydantic import ValidationError
from starlette.concurrency import run_in_threadpool

from application_state.errors import ApplicationStateConflictError, ApplicationStateError
from application_state.index_graph.managed_world import bind_initialized_guest_world
from application_state.index_graph.sessions import (
    IndexGraphSessionError, hosted_guest_world_enabled, request_session,
    require_index_graph_boundary,
)

_DOCUMENT = re.compile(r"^/api/live/workspace-documents/([0-9a-f-]{36})(/snapshot)?$")
_WRITE = frozenset({"/api/live/tiptap/markdown-write/prepare", "/api/live/tiptap/markdown-write/commit"})
_INVENTORY = "/api/live/workspace-documents/pages/inventory"
_CREATE = "/api/live/workspace-documents"
MAX_GUEST_PAGES = 32
MAX_GUEST_REVISIONS = 256
MAX_GUEST_SAVED_BYTES = 16 * 1024 * 1024


def matches_guest_build_route(method: str, path: str) -> bool:
    return ((method == "GET" and (path == _INVENTORY or _DOCUMENT.fullmatch(path) is not None))
            or (method == "POST" and (path == _CREATE or path in _WRITE)))


def require_guest_build_world(request: Request, world_id: str) -> None:
    """Revalidate the cookie and exact managed binding, including after effects."""
    if not hosted_guest_world_enabled() or getattr(request.state, "guest_build_world", None) != world_id:
        raise HTTPException(403, detail={"code": "guest_world_forbidden"})
    try:
        require_index_graph_boundary(request, unsafe=request.method not in {"GET", "HEAD"})
        _, session = request_session(request, unsafe=request.method not in {"GET", "HEAD"})
        world = bind_initialized_guest_world(session)
    except IndexGraphSessionError as exc:
        raise HTTPException(exc.status, detail={"code": exc.code}) from None
    except ApplicationStateConflictError:
        raise HTTPException(403, detail={"code": "guest_world_forbidden"}) from None
    except ApplicationStateError:
        raise HTTPException(503, detail={"code": "guest_world_unavailable"}) from None
    if world.record.world_id != world_id or session.session_id != getattr(request.state, "guest_build_session", None):
        raise HTTPException(403, detail={"code": "guest_world_forbidden"})


def _document_world(document_id: str) -> str:
    from apps.live_control_server.config import repo_root
    from apps.live_control_server.services.workspace_document_registry import get_workspace_document, WorkspaceDocumentRegistryError
    try:
        if str(UUID(document_id)) != document_id:
            raise ValueError
        record = get_workspace_document(repo_root(), document_id)
    except (ValueError, WorkspaceDocumentRegistryError):
        raise HTTPException(403, detail={"code": "guest_document_forbidden"}) from None
    if record.kind != "worldbuilding_source" or not record.world_id or record.campaign_id != record.world_id:
        raise HTTPException(403, detail={"code": "guest_document_forbidden"})
    return record.world_id


async def admit_guest_build_request(request: Request) -> str:
    """Authorize only the selected existing Build APIs for one guest World."""
    from apps.live_control_server.services import hosted_auth
    from apps.live_control_server.services.workspace_document_registry import CreateWorkspaceDocumentRequest
    from apps.live_control_server.services.tiptap_markdown_write import TiptapMarkdownWritePrepareRequest, TiptapMarkdownWriteCommitRequest

    require_index_graph_boundary(request, unsafe=request.method != "GET")
    try:
        _, session = await run_in_threadpool(request_session, request, unsafe=request.method != "GET")
        world = await run_in_threadpool(bind_initialized_guest_world, session)
    except IndexGraphSessionError as exc:
        raise HTTPException(exc.status, detail={"code": exc.code}) from None
    except ApplicationStateConflictError:
        raise HTTPException(403, detail={"code": "guest_world_forbidden"}) from None
    except ApplicationStateError:
        raise HTTPException(503, detail={"code": "guest_world_unavailable"}) from None
    world_id = world.record.world_id
    request.state.guest_build_world = world_id
    request.state.guest_build_session = session.session_id
    requested = await hosted_auth.request_world_ids(request)
    if requested and requested != frozenset({world_id}):
        raise HTTPException(403, detail={"code": "guest_world_forbidden"})
    query = request.query_params.multi_items()
    if len({key for key, _ in query}) != len(query):
        raise HTTPException(400, detail={"code": "invalid_guest_request"})
    path = request.url.path
    try:
        if path == _INVENTORY:
            if (set(key for key, _ in query) - {"world_id", "campaign_id", "status", "limit", "before_updated_at", "before_document_id"}
                    or request.query_params.get("world_id") != world_id
                    or request.query_params.get("campaign_id", world_id) != world_id
                    or await request.body()):
                raise HTTPException(403, detail={"code": "guest_world_forbidden"})
            request.state.hosted_build_page_inventory_world = world_id
        elif path == _CREATE:
            create = CreateWorkspaceDocumentRequest.model_validate(await request.json())
            if (query or create.world_id != world_id or create.campaign_id != world_id
                    or create.kind != "worldbuilding_source" or create.target_session is not None
                    or create.target_relpath is not None or create.authority_state not in (None, "draft")
                    or create.visibility_state not in (None, "internal")):
                raise HTTPException(403, detail={"code": "guest_world_forbidden"})
            request.state.hosted_build_page_world = world_id
        elif path in _WRITE:
            model = TiptapMarkdownWritePrepareRequest if path.endswith("/prepare") else TiptapMarkdownWriteCommitRequest
            body = model.model_validate(await request.json())
            if query or body.world_id is not None or await run_in_threadpool(_document_world, body.document_id) != world_id:
                raise HTTPException(403, detail={"code": "guest_document_forbidden"})
            request.state.hosted_build_page_world = world_id
        else:
            match = _DOCUMENT.fullmatch(path)
            if (match is None or (query and not (match.group(2) and query == [("view", "committed")]))
                    or await request.body() or await run_in_threadpool(_document_world, match.group(1)) != world_id):
                raise HTTPException(403, detail={"code": "guest_document_forbidden"})
            request.state.hosted_build_page_world = world_id
    except (ValidationError, ValueError, TypeError):
        raise HTTPException(400, detail={"code": "invalid_guest_request"}) from None
    await run_in_threadpool(require_guest_build_world, request, world_id)
    return world_id


def guest_write_capacity(request: Request, conn, world_id: str, *, creating: bool = False,
                         content_bytes: int = 0, replay: bool = False) -> None:
    """Lock guest lifecycle and enforce bounded durable page storage atomically."""
    from application_state.errors import ApplicationStateConflictError

    session_id = getattr(request.state, "guest_build_session", None)
    if not session_id or getattr(request.state, "guest_build_world", None) != world_id:
        raise ApplicationStateConflictError("Guest session no longer matches this World")
    row = conn.execute(
        "SELECT 1 FROM application_state.index_graph_sessions "
        "WHERE session_id = %s::uuid AND expires_at > clock_timestamp() FOR UPDATE", (session_id,),
    ).fetchone()
    if row is None or world_id != f"guest-{UUID(session_id).hex}":
        raise ApplicationStateConflictError("Guest session is no longer active")
    conn.execute("SELECT pg_advisory_xact_lock(hashtextextended(%s, 0))", ("guest-build:" + world_id,))
    if creating:
        pages = conn.execute(
            "SELECT count(*) FROM content.work_object WHERE world_id = %s AND kind = 'worldbuilding_source'",
            (world_id,),
        ).fetchone()[0]
        if pages >= MAX_GUEST_PAGES:
            raise ApplicationStateConflictError("This guest World has reached its document limit")
    if not creating and not replay:
        revisions, total = conn.execute(
            "SELECT count(*), coalesce(sum(octet_length(r.markdown)), 0) "
            "FROM content.work_revision r JOIN content.work_object o ON o.work_object_id = r.work_object_id "
            "WHERE o.world_id = %s AND o.kind = 'worldbuilding_source'", (world_id,),
        ).fetchone()
        if revisions >= MAX_GUEST_REVISIONS or total + content_bytes > MAX_GUEST_SAVED_BYTES:
            raise ApplicationStateConflictError("This guest World has reached its saved content limit")
