"""Explicit session-bound authorization for ordinary guest Build documents."""
from __future__ import annotations

import re
import os
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
_PLANS = "/api/live/workspace-documents/world-plans"
_PLAN_VIEW = "/api/live/plan-view"
_PLAY_ROOT = "/api/live/world-play-runs/v2"
_PLAY_RUN = re.compile(r"^/api/live/world-play-runs/v2/([0-9a-f-]{36})(/progress|/reference-manifest|/content|/creation)?$")
_PLAN_REVISION = re.compile(r"^/api/live/workspace-documents/([0-9a-f-]{36})/committed-revision(?:/[1-9][0-9]*)?$")
_MEDIA_ROOT = "/api/live/media/images"
_MEDIA_ASSET = re.compile(r"^/api/live/media/images/([0-9a-f-]{36})(/metadata|/original)?$")
_CONVERSATION = re.compile(r"^/api/live/agent/worlds/(guest-[0-9a-f]{32})/conversation(/new)?$")
_CONVERSATION_CITATION = re.compile(
    r"^/api/live/agent/worlds/(guest-[0-9a-f]{32})/conversation/turns/"
    r"[0-9a-f-]{36}/(?:native-source-clauses|native-assertion-sources|native-body-excerpts|native-source-sections|source-passages)/[0-9]+$"
)
_CONVERSATION_MESSAGES = re.compile(r"^/api/live/agent/worlds/(guest-[0-9a-f]{32})/conversations/active/messages$")
MAX_GUEST_PAGES = 32
MAX_GUEST_REVISIONS = 256
MAX_GUEST_SAVED_BYTES = 16 * 1024 * 1024
MAX_GUEST_RUNS = 16
MAX_GUEST_CONVERSATIONS = 16
MAX_GUEST_TURNS = 100
MAX_GUEST_TURN_BYTES = 16 * 1024
MAX_GUEST_CONVERSATION_BYTES = 32 * 1024 * 1024


def matches_guest_conversation_route(method: str, path: str) -> bool:
    """Recognize the initial conversation paths; admission is separately gated."""
    match = _CONVERSATION.fullmatch(path)
    if method == "GET" and (_CONVERSATION_CITATION.fullmatch(path) or _CONVERSATION_MESSAGES.fullmatch(path)):
        return True
    if (method == "POST" and path == "/api/live/agent/turn"
            and os.getenv("DMB_HOSTED_GUEST_TURN_ENABLED") == "1"):
        return True
    return bool(match and ((method == "GET" and match.group(2) is None)
                           or (method == "POST" and match.group(2) == "/new")))


async def admit_guest_conversation_request(request: Request) -> str:
    """Bind a conversation request to the session's own copied World."""
    if os.getenv("DMB_HOSTED_GUEST_CONVERSATION_ENABLED") != "1" or not hosted_guest_world_enabled():
        raise HTTPException(403, detail={"code": "guest_world_forbidden"})
    match = (_CONVERSATION.fullmatch(request.url.path) or _CONVERSATION_CITATION.fullmatch(request.url.path)
             or _CONVERSATION_MESSAGES.fullmatch(request.url.path))
    is_turn = request.url.path == "/api/live/agent/turn"
    if not matches_guest_conversation_route(request.method, request.url.path):
        raise HTTPException(403, detail={"code": "guest_world_forbidden"})
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
    if match is not None and match.group(1) != world_id:
        raise HTTPException(403, detail={"code": "guest_world_forbidden"})
    query = request.query_params.multi_items()
    if len({key for key, _ in query}) != len(query):
        raise HTTPException(400, detail={"code": "invalid_guest_request"})
    if request.method == "GET":
        allowed_query = (set() if _CONVERSATION_CITATION.fullmatch(request.url.path)
                         else {"limit", "before_sequence"} if _CONVERSATION_MESSAGES.fullmatch(request.url.path)
                         else {"limit", "before_sequence", "include_turn_correlation"})
        if set(key for key, _ in query) - allowed_query or await request.body():
            raise HTTPException(400, detail={"code": "invalid_guest_request"})
    elif query:
        raise HTTPException(400, detail={"code": "invalid_guest_request"})
    if is_turn:
        from apps.live_control_server.models.agent_turn import AgentTurnRequest, AgentTurnWorldOwner
        from apps.live_control_server.services.hosted_auth import request_world_ids

        if request.headers.get("accept") == "text/event-stream":
            raise HTTPException(403, detail={"code": "guest_stream_unavailable"})
        requested_worlds = await request_world_ids(request)
        try:
            body = AgentTurnRequest.model_validate(await request.json())
        except (ValidationError, ValueError, TypeError):
            raise HTTPException(400, detail={"code": "invalid_guest_request"}) from None
        if (not isinstance(body.owner_scope, AgentTurnWorldOwner)
                or body.owner_scope.world_id != world_id
                or requested_worlds - {world_id}):
            raise HTTPException(403, detail={"code": "guest_world_forbidden"})
        from application_state.agent_conversation.types import PlanContextPolicyV2

        index_discussion = (body.surface.surface_id == "index" and body.primary_work is None
                            and body.graph_request.mode == "none" and body.plan_context_policy is None
                            and body.plan_requested_operation is None)
        plan_discussion = (body.surface.surface_id == "plan" and body.primary_work is not None
                           and body.primary_work.kind == "plan" and body.graph_request.mode == "none"
                           and type(body.plan_context_policy) is PlanContextPolicyV2
                           and body.plan_requested_operation in (None, "discuss"))
        from application_state.agent_conversation.authored_graph_references import AuthoredGraphReferenceV1
        references = body.authored_references
        guest_graph_references = (plan_discussion and references is not None
            and all(isinstance(ref, AuthoredGraphReferenceV1) and ref.managed_world_id == world_id
                    for ref in references.references))
        # Other action families stay closed until their independent persistence
        # owners are bound to the guest lifecycle.
        if (not (index_discussion or plan_discussion) or body.graph_selection is not None
                or body.selected_knowledge is not None or body.native_statement_selection is not None
                or body.build_write_capability is not None or body.build_image_move_capture is not None
                or body.build_draft_context is not None or body.build_authored_references is not None
                or (references is not None and not guest_graph_references)
                or body.retry_of is not None or body.reviewed_step is not None
                or body.plan_authoring_capture is not None
                or body.plan_placement_catalog is not None or body.playable_target is not None
                or body.play_target is not None):
            raise HTTPException(403, detail={"code": "guest_turn_capability_unavailable"})
    request.state.guest_build_world = world_id
    request.state.guest_build_session = session.session_id
    request.state.guest_conversation_world = world_id
    await run_in_threadpool(require_guest_build_world, request, world_id)
    return world_id


def matches_guest_build_route(method: str, path: str) -> bool:
    if (method == "GET" and _PLAN_REVISION.fullmatch(path)
            and os.getenv("DMB_HOSTED_GUEST_PLAN_ENABLED") == "1"
            and os.getenv("DMB_HOSTED_GUEST_CONVERSATION_ENABLED") == "1"):
        return True
    if os.getenv("DMB_HOSTED_GUEST_MEDIA_ENABLED") == "1":
        if (method == "GET" and (path in {_MEDIA_ROOT + "/capabilities", _MEDIA_ROOT + "/library"} or _MEDIA_ASSET.fullmatch(path))
                or method == "POST" and path == _MEDIA_ROOT + "/generate"):
            return True
    if os.getenv("DMB_HOSTED_GUEST_PLAY_ENABLED") == "1" and os.getenv("DMB_HOSTED_GUEST_PLAN_ENABLED") == "1":
        match = _PLAY_RUN.fullmatch(path)
        if (method == "GET" and (path in {_PLAY_ROOT, _PLAY_ROOT + "/active", "/api/live/workspace-documents/world-runbooks"} or _PLAN_REVISION.fullmatch(path) or (match and match.group(2) != "/progress"))
                or method == "POST" and path == _PLAY_ROOT + "/preparation"
                or method == "PUT" and (path == _PLAY_ROOT + "/active" or match and match.group(2) in (None, "/progress"))):
            return True
    return ((method == "GET" and (path == _INVENTORY or _DOCUMENT.fullmatch(path) is not None))
            or (method == "POST" and (path == _CREATE or path in _WRITE))
            or (os.getenv("DMB_HOSTED_GUEST_PLAN_ENABLED") == "1" and
                ((method == "GET" and path in {_PLANS, _PLAN_VIEW}) or (method == "POST" and path == _PLANS))))


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


def _document_world(document_id: str) -> tuple[str, str]:
    from apps.live_control_server.config import repo_root
    from apps.live_control_server.services.workspace_document_registry import get_workspace_document, WorkspaceDocumentRegistryError
    try:
        if str(UUID(document_id)) != document_id:
            raise ValueError
        record = get_workspace_document(repo_root(), document_id)
    except (ValueError, WorkspaceDocumentRegistryError):
        raise HTTPException(403, detail={"code": "guest_document_forbidden"}) from None
    if not record.world_id or not ((record.kind == "worldbuilding_source" and record.campaign_id == record.world_id)
                                   or (os.getenv("DMB_HOSTED_GUEST_PLAN_ENABLED") == "1" and record.kind == "plan" and record.campaign_id is None)):
        raise HTTPException(403, detail={"code": "guest_document_forbidden"})
    return record.world_id, record.kind


async def admit_guest_build_request(request: Request) -> str:
    """Authorize only the selected existing Build APIs for one guest World."""
    from apps.live_control_server.services import hosted_auth
    from apps.live_control_server.services.workspace_document_registry import CreateWorkspaceDocumentRequest
    from apps.live_control_server.services.workspace_document_registry import CreateWorldOwnedPlanRequestV2
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
        plan_revision = _PLAN_REVISION.fullmatch(path)
        play_run = _PLAY_RUN.fullmatch(path)
        asset = _MEDIA_ASSET.fullmatch(path)
        if path in {_MEDIA_ROOT + "/capabilities", _MEDIA_ROOT + "/library", _MEDIA_ROOT + "/generate"}:
            allowed = {"world_id", "before_time", "before_id"} if path.endswith("/library") else {"world_id"}
            if set(key for key, _ in query) - allowed or request.query_params.get("world_id") != world_id:
                raise HTTPException(403, detail={"code": "guest_world_forbidden"})
            if request.method == "GET" and await request.body():
                raise HTTPException(400, detail={"code": "invalid_guest_request"})
            if path.endswith("/generate"):
                from apps.live_control_server.routes.media_images import ImagePreviewRequest
                if ImagePreviewRequest.model_validate(await request.json()).preparation_id is not None:
                    raise HTTPException(403, detail={"code": "guest_media_forbidden"})
            request.state.hosted_plan_context_world = world_id
        elif asset:
            from application_state import media
            from apps.live_control_server.services.hosted_native_graph_access import hosted_world_media_owner
            if query or await request.body() or str(UUID(asset.group(1))) != asset.group(1):
                raise HTTPException(403, detail={"code": "guest_media_forbidden"})
            try:
                await run_in_threadpool(media.get_asset, asset.group(1), hosted_world_media_owner(world_id))
            except ApplicationStateError:
                raise HTTPException(403, detail={"code": "guest_media_forbidden"}) from None
            request.state.hosted_saved_artwork = (asset.group(1), world_id)
        elif plan_revision:
            if query or await request.body() or await run_in_threadpool(_document_world, plan_revision.group(1)) != (world_id, "plan"):
                raise HTTPException(403, detail={"code": "guest_document_forbidden"})
            request.state.hosted_plan_context_world = world_id
        elif path in {_PLAY_ROOT, _PLAY_ROOT + "/active", _PLAY_ROOT + "/preparation", "/api/live/workspace-documents/world-runbooks"} or play_run:
            allowed = {"world_id", "entry_scene_id"} if path == _PLAY_ROOT + "/preparation" else {"world_id"}
            if set(key for key, _ in query) - allowed or request.query_params.get("world_id") != world_id:
                raise HTTPException(403, detail={"code": "guest_world_forbidden"})
            if request.method == "GET" and await request.body():
                raise HTTPException(400, detail={"code": "invalid_guest_request"})
            request.state.hosted_plan_context_world = world_id
        elif path == _INVENTORY:
            if (set(key for key, _ in query) - {"world_id", "campaign_id", "status", "limit", "before_updated_at", "before_document_id"}
                    or request.query_params.get("world_id") != world_id
                    or request.query_params.get("campaign_id", world_id) != world_id
                    or await request.body()):
                raise HTTPException(403, detail={"code": "guest_world_forbidden"})
            request.state.hosted_build_page_inventory_world = world_id
        elif path in {_PLANS, _PLAN_VIEW}:
            if request.method == "GET":
                allowed = {"world_id"} if path == _PLANS else {"world_id", "scope_mode"}
                if set(key for key, _ in query) != allowed or request.query_params.get("world_id") != world_id or (path == _PLAN_VIEW and request.query_params.get("scope_mode") != "world") or await request.body():
                    raise HTTPException(403, detail={"code": "guest_world_forbidden"})
            else:
                body = CreateWorldOwnedPlanRequestV2.model_validate(await request.json())
                if query or body.world_id != world_id:
                    raise HTTPException(403, detail={"code": "guest_world_forbidden"})
            request.state.hosted_plan_context_world = world_id
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
            document_world, kind = await run_in_threadpool(_document_world, body.document_id)
            if query or document_world != world_id or (kind == "worldbuilding_source" and body.world_id is not None) or (kind == "plan" and body.world_id != world_id):
                raise HTTPException(403, detail={"code": "guest_document_forbidden"})
            request.state.hosted_build_page_world = world_id
            if kind == "plan": request.state.hosted_plan_context_world = world_id
        else:
            match = _DOCUMENT.fullmatch(path)
            if match is None or (query and not (match.group(2) and query == [("view", "committed")])) or await request.body():
                raise HTTPException(403, detail={"code": "guest_document_forbidden"})
            document_world, kind = await run_in_threadpool(_document_world, match.group(1))
            if document_world != world_id: raise HTTPException(403, detail={"code": "guest_document_forbidden"})
            request.state.hosted_build_page_world = world_id
            if kind == "plan": request.state.hosted_plan_context_world = world_id
    except (ValidationError, ValueError, TypeError):
        raise HTTPException(400, detail={"code": "invalid_guest_request"}) from None
    await run_in_threadpool(require_guest_build_world, request, world_id)
    return world_id


def _check_guest_session(request: Request, conn, world_id: str, *, lock: bool) -> None:
    """Check the session on the transaction connection; lock for writes."""
    from application_state.errors import ApplicationStateConflictError

    session_id = getattr(request.state, "guest_build_session", None)
    if not session_id or getattr(request.state, "guest_build_world", None) != world_id:
        raise ApplicationStateConflictError("Guest session no longer matches this World")
    try:
        expected_world = f"guest-{UUID(session_id).hex}"
    except (TypeError, ValueError, AttributeError):
        raise ApplicationStateConflictError("Guest session is no longer active") from None
    if world_id != expected_world:
        raise ApplicationStateConflictError("Guest session is no longer active")
    sql = ("SELECT 1 FROM application_state.index_graph_sessions "
           "WHERE session_id = %s::uuid AND expires_at > clock_timestamp()")
    if lock:
        sql += " FOR UPDATE"
    row = conn.execute(sql, (session_id,)).fetchone()
    if row is None:
        raise ApplicationStateConflictError("Guest session is no longer active")


def _lock_guest_session(request: Request, conn, world_id: str) -> None:
    """Serialize a guest-owned write with session expiry and reset."""
    _check_guest_session(request, conn, world_id, lock=True)


def guest_conversation_capacity(request: Request, conn, world_id: str) -> None:
    """Bound retained conversations while holding the guest lifecycle lock."""
    _lock_guest_session(request, conn, world_id)
    count = conn.execute("SELECT count(*) FROM agent.conversation WHERE world_id = %s", (world_id,)).fetchone()[0]
    if count >= MAX_GUEST_CONVERSATIONS:
        raise ApplicationStateConflictError("This guest World has reached its conversation limit")


def guest_turn_capacity(request: Request, conn, world_id: str, submission) -> None:
    """Bound new guest turns without preventing exact idempotent replay."""
    _lock_guest_session(request, conn, world_id)
    if submission.world_id != world_id or len(submission.user_text.encode("utf-8")) > MAX_GUEST_TURN_BYTES:
        raise ApplicationStateConflictError("Guest turn exceeds its session limit")
    count = conn.execute("SELECT count(*) FROM agent.turn WHERE world_id = %s", (world_id,)).fetchone()[0]
    if count >= MAX_GUEST_TURNS:
        raise ApplicationStateConflictError("This guest World has reached its turn limit")


def guest_conversation_bytes(request: Request, conn, world_id: str) -> int:
    """Bound logical JSON bytes in the current transaction before it commits.

    This measures decoded row contents, not indexes, dead tuples, or WAL.
    The guest session row must already be locked by the transaction guard.
    """
    if getattr(request.state, 'guest_build_world', None) != world_id:
        raise ApplicationStateConflictError('Guest conversation World changed')
    conn.execute("SET LOCAL statement_timeout = '5s'")
    total = conn.execute("""
        WITH turns AS MATERIALIZED (SELECT * FROM agent.turn WHERE world_id=%s),
             drafts AS MATERIALIZED (SELECT * FROM agent.composer_draft WHERE world_id=%s),
             sizes AS (
          SELECT coalesce(sum(octet_length(to_jsonb(x)::text)),0) AS n FROM turns x
          UNION ALL SELECT coalesce(sum(octet_length(to_jsonb(x)::text)),0) FROM agent.world_state x WHERE world_id=%s
          UNION ALL SELECT coalesce(sum(octet_length(to_jsonb(x)::text)),0) FROM agent.conversation x WHERE world_id=%s
          UNION ALL SELECT coalesce(sum(octet_length(to_jsonb(x)::text)),0) FROM agent.command_receipt x WHERE world_id=%s
          UNION ALL SELECT coalesce(sum(octet_length(to_jsonb(x)::text)),0) FROM agent.command_resolution x WHERE world_id=%s
          UNION ALL SELECT coalesce(sum(octet_length(to_jsonb(x)::text)),0) FROM agent.import_receipt x WHERE world_id=%s
          UNION ALL SELECT coalesce(sum(octet_length(to_jsonb(x)::text)),0) FROM drafts x
          UNION ALL SELECT coalesce(sum(octet_length(to_jsonb(x)::text)),0) FROM agent.draft_reference x JOIN drafts d USING (draft_id)
          UNION ALL SELECT coalesce(sum(octet_length(to_jsonb(x)::text)),0) FROM agent.turn_reference x JOIN turns t USING (turn_id)
          UNION ALL SELECT coalesce(sum(octet_length(to_jsonb(x)::text)),0) FROM agent.turn_retry x WHERE world_id=%s
          UNION ALL SELECT coalesce(sum(octet_length(to_jsonb(x)::text)),0) FROM agent.turn_context_trace x JOIN turns t USING (turn_id)
          UNION ALL SELECT coalesce(sum(octet_length(to_jsonb(x)::text)),0) FROM agent.turn_rules_execution x JOIN turns t USING (turn_id)
          UNION ALL SELECT coalesce(sum(octet_length(to_jsonb(x)::text)),0) FROM agent.turn_reviewed_action x JOIN turns t USING (turn_id)
          UNION ALL SELECT coalesce(sum(octet_length(to_jsonb(x)::text)),0) FROM agent.plan_execution_checkpoint x JOIN turns t USING (turn_id)
          UNION ALL SELECT coalesce(sum(octet_length(to_jsonb(x)::text)),0) FROM agent.plan_execution_event x JOIN turns t USING (turn_id)
          UNION ALL SELECT coalesce(sum(octet_length(to_jsonb(x)::text)),0) FROM agent.conversation_draft_revision x WHERE world_id=%s
        ) SELECT coalesce(sum(n),0) FROM sizes
    """, (world_id,) * 9).fetchone()[0]
    if total > MAX_GUEST_CONVERSATION_BYTES:
        raise ApplicationStateConflictError('This guest World has reached its conversation storage limit')
    return int(total)


def guest_play_capacity(request: Request, conn, world_id: str, replay: bool) -> None:
    """Bind Run creation to the live guest session and bound retained Runs."""
    from application_state.errors import ApplicationStateConflictError

    _lock_guest_session(request, conn, world_id)
    if not replay:
        count = conn.execute("SELECT count(*) FROM play.run WHERE world_id = %s", (world_id,)).fetchone()[0]
        if count >= MAX_GUEST_RUNS:
            raise ApplicationStateConflictError("This guest World has reached its session limit")


def guest_write_capacity(request: Request, conn, world_id: str, *, creating: bool = False,
                         content_bytes: int = 0, replay: bool = False) -> None:
    """Lock guest lifecycle and enforce bounded durable page storage atomically."""
    from application_state.errors import ApplicationStateConflictError

    _lock_guest_session(request, conn, world_id)
    conn.execute("SELECT pg_advisory_xact_lock(hashtextextended(%s, 0))", ("guest-build:" + world_id,))
    if creating:
        pages = conn.execute(
            "SELECT count(*) FROM content.work_object WHERE world_id = %s AND kind IN ('worldbuilding_source', 'plan')",
            (world_id,),
        ).fetchone()[0]
        if pages >= MAX_GUEST_PAGES:
            raise ApplicationStateConflictError("This guest World has reached its document limit")
    if not creating and not replay:
        revisions, total = conn.execute(
            "SELECT count(*), coalesce(sum(octet_length(r.markdown)), 0) "
            "FROM content.work_revision r JOIN content.work_object o ON o.work_object_id = r.work_object_id "
            "WHERE o.world_id = %s AND o.kind IN ('worldbuilding_source', 'plan')", (world_id,),
        ).fetchone()
        if revisions >= MAX_GUEST_REVISIONS or total + content_bytes > MAX_GUEST_SAVED_BYTES:
            raise ApplicationStateConflictError("This guest World has reached its saved content limit")
