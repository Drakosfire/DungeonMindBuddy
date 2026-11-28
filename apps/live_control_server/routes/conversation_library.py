"""Authenticated conversation history and explicit APP-owned continuation."""

from collections import OrderedDict
from hashlib import sha256
import json
import logging
from threading import Lock
from time import monotonic
from typing import Literal
from uuid import UUID
from fastapi import APIRouter, BackgroundTasks, HTTPException, Query, Request, Response
from application_state.agent_conversation import library
from application_state.errors import ApplicationStateError
from application_state.agent_conversation.retry import AuthoringRetryRequiredError
from apps.live_control_server.services.agent_graph_auth import enforce_native_graph_gm
from apps.live_control_server.services.hosted_native_graph_access import require_conversation_access
from apps.live_control_server.routes.agent import _verified_world_id, _conversation_service
from application_state.agent_conversation.types import (
    ArchiveCommand, ConversationCommandReceipt, ConversationDeleteCommand, ConversationTrashCommand, ReopenCommand,
)
from apps.live_control_server.services.conversation_erasure import finish_conversation_erasure

router = APIRouter(
    prefix="/api/live/agent/worlds/{world_id}/conversations",
    tags=["conversation library"],
)


def scope(request, world, allowed):
    require_conversation_access(request, world, authorize_local=enforce_native_graph_gm)
    if set(request.query_params) - set(allowed) or any(
        len(request.query_params.getlist(k)) != 1 for k in request.query_params
    ):
        raise HTTPException(422, detail="Unexpected or repeated conversation selector")
    return _verified_world_id(world)


def call(function, *args, **kwargs):
    try:
        return function(*args, **kwargs)
    except AuthoringRetryRequiredError as exc:
        raise HTTPException(exc.status_code, detail={"code":"build_authoring_retry_required","message":str(exc)}) from exc
    except ApplicationStateError as exc:
        raise HTTPException(exc.status_code, detail=str(exc)) from exc


@router.get("")
def list_conversations(
    world_id: str,
    request: Request,
    status: str = Query("all", pattern="^(all|recent|archived|explicitly_archived|trashed)$"),
    limit: int = Query(25, ge=1, le=50),
    before: str | None = Query(None, max_length=100),
):
    world = scope(request, world_id, {"status", "limit", "before"})
    return call(library.list_library, world, status=status, limit=limit, before=before)


_dialogue_warmup_lock = Lock()
_dialogue_warmup_snapshots = OrderedDict()
_DIALOGUE_WARMUP_SNAPSHOT_LIMIT = 16
_dialogue_warmup_logger = logging.getLogger("uvicorn.error")


def _warm_build_dialogue(service, world, conversation, pointer_revision, slots):
    if not _dialogue_warmup_lock.acquire(blocking=False):
        return
    started = monotonic()
    key = (world, conversation, pointer_revision, slots)
    try:
        if key in _dialogue_warmup_snapshots:
            return
        pointer = service.get_world_pointer(world)
        if (pointer.active_conversation_id, pointer.revision) != (conversation, pointer_revision):
            return
        service.list_build_dialogue(world, conversation)
        _dialogue_warmup_snapshots[key] = None
        if len(_dialogue_warmup_snapshots) > _DIALOGUE_WARMUP_SNAPSHOT_LIMIT:
            _dialogue_warmup_snapshots.popitem(last=False)
        _dialogue_warmup_logger.info(
            "buddy_build_dialogue_warmup status=ready elapsed_ms=%.1f",
            (monotonic() - started) * 1000,
        )
    except Exception as exc:
        _dialogue_warmup_logger.warning(
            "buddy_build_dialogue_warmup status=error error_type=%s elapsed_ms=%.1f",
            type(exc).__name__, (monotonic() - started) * 1000,
        )
    finally:
        _dialogue_warmup_lock.release()


@router.get("/active/messages")
def active_messages(
    world_id: str,
    request: Request,
    background_tasks: BackgroundTasks,
    limit: int = Query(50, ge=1, le=100),
    before_sequence: int | None = Query(None, gt=0),
):
    world = scope(request, world_id, {"limit", "before_sequence"})
    page = call(
        library.read_active_messages,
        world,
        limit=limit,
        before_sequence=before_sequence,
    )

    if before_sequence is None and limit >= 6 and page.get("active_conversation_id"):
        rows = page["messages"][-6:]
        if rows and rows[-1]["status"] not in {"accepted", "running"} and any(
            row["status"] == "completed" and row["provenance"]["surface_id"] == "build"
            for row in rows
        ):
            background_tasks.add_task(
                _warm_build_dialogue,
                _conversation_service(request),
                world,
                UUID(page["active_conversation_id"]),
                page["pointer_revision"],
                tuple((row["turn_id"], row["revision"], row["status"]) for row in rows),
            )
    return page


@router.get("/{conversation_id:uuid}/messages")
def messages(
    world_id: str,
    conversation_id: UUID,
    request: Request,
    limit: int = Query(50, ge=1, le=100),
    before_sequence: int | None = Query(None, gt=0),
):
    world = scope(request, world_id, {"limit", "before_sequence"})
    return call(library.read_messages, world, conversation_id, limit=limit, before_sequence=before_sequence)


@router.get("/{conversation_id}/turns")
def turns(
    world_id: str,
    conversation_id: UUID,
    request: Request,
    limit: int = Query(50, ge=1, le=100),
    before_sequence: int | None = Query(None, gt=0),
    view: Literal["full", "digest"] | None = Query(None),
):
    world = scope(request, world_id, {"limit", "before_sequence", "view"})
    page = call(
        library.read_turns,
        world,
        conversation_id,
        limit=limit,
        before_sequence=before_sequence,
    )

    if view is None:
        return page
    encoded = json.dumps(page, sort_keys=True, separators=(",", ":"), ensure_ascii=True)
    digest = sha256(encoded.encode("ascii")).hexdigest()
    if view == "full":
        return {**page, "page_sha256": digest}
    return {
        "schema": "dmb_conversation_library_turn_digest_v1",
        "world_id": page["world_id"],
        "conversation_id": page["conversation_id"],
        "next_before_sequence": page["next_before_sequence"],
        "page_sha256": digest,
    }


@router.get("/{conversation_id}/name")
def name(world_id: str, conversation_id: UUID, request: Request):
    return call(library.get_name, scope(request, world_id, ()), conversation_id)


@router.put("/{conversation_id}/name")
def rename(
    world_id: str, conversation_id: UUID, body: library.NameChange, request: Request
):
    world = scope(request, world_id, ())
    from apps.live_control_server.services import hosted_auth

    if hosted_auth.deployment_environment() in hosted_auth.LOCAL_ENVIRONMENTS:
        return call(library.rename, world, conversation_id, body)

    def recheck_owner():
        require_conversation_access(request, world, authorize_local=enforce_native_graph_gm)

    return call(library.rename, world, conversation_id, body, authorize_write=recheck_owner)


@router.get("/{conversation_id}/retry-context")
def retry_context(
    world_id: str, conversation_id: UUID, request: Request, turn_ids: str
):
    from application_state.agent_conversation.retry import read_context

    world = scope(request, world_id, {"turn_ids"})
    parts = turn_ids.split(",")
    if not 1 <= len(parts) <= 100:
        raise HTTPException(422, detail="Select one to 100 turns")
    try:
        ids = [UUID(value) for value in parts]
    except ValueError as exc:
        raise HTTPException(422, detail="Invalid retry turn identity") from exc
    return call(read_context, world, conversation_id, ids)


@router.get("/{conversation_id}/turns/{turn_id}/retry-attempts")
def retry_attempts(
    world_id: str,
    conversation_id: UUID,
    turn_id: UUID,
    request: Request,
    limit: int = Query(50, ge=1, le=50),
    before_sequence: int | None = Query(None, gt=0),
):
    world = scope(request, world_id, {"limit", "before_sequence"})
    result = call(
        library.read_retry_attempts,
        world,
        conversation_id,
        turn_id,
        limit=limit,
        before_sequence=before_sequence,
    )
    require_conversation_access(request, world, authorize_local=enforce_native_graph_gm)
    return result


@router.get("/{conversation_id}/turns/{turn_id}/discussion-retry-input")
def discussion_retry_input(world_id: str, conversation_id: UUID, turn_id: UUID, request: Request, response: Response, revision: int = Query(..., ge=1)):
    from application_state.agent_conversation.retry import read_discussion_retry_input
    from apps.live_control_server.services import hosted_auth

    result = call(read_discussion_retry_input, scope(request, world_id, {"revision"}), conversation_id, turn_id, revision)
    if hosted_auth.deployment_environment() not in hosted_auth.LOCAL_ENVIRONMENTS:
        require_conversation_access(request, world_id, authorize_local=enforce_native_graph_gm)
    response.headers["Cache-Control"] = "no-store"
    return result


@router.post("/{conversation_id}/resume", response_model=ConversationCommandReceipt)
def resume(world_id: str, conversation_id: UUID, body: ReopenCommand, request: Request):
    world = scope(request, world_id, ())
    if body.world_id != world or body.conversation_id != conversation_id:
        raise HTTPException(422, detail="Resume command differs from this World or conversation")
    from apps.live_control_server.services import hosted_auth

    service = _conversation_service(request)
    if hosted_auth.deployment_environment() in hosted_auth.LOCAL_ENVIRONMENTS:
        return call(service.reopen_conversation, body)

    def recheck_owner():
        require_conversation_access(request, world, authorize_local=enforce_native_graph_gm)

    result = call(service.reopen_conversation, body, authorize_write=recheck_owner)
    recheck_owner()
    return result


@router.post("/{conversation_id}/archive", response_model=ConversationCommandReceipt)
def archive(world_id: str, conversation_id: UUID, body: ArchiveCommand, request: Request):
    world = scope(request, world_id, ())
    if body.world_id != world or body.conversation_id != conversation_id:
        raise HTTPException(422, detail="Archive command differs from this World or conversation")
    from apps.live_control_server.services import hosted_auth

    service = _conversation_service(request)
    if hosted_auth.deployment_environment() in hosted_auth.LOCAL_ENVIRONMENTS:
        return call(service.archive_conversation, body)

    def recheck_owner():
        require_conversation_access(request, world, authorize_local=enforce_native_graph_gm)

    result = call(service.archive_conversation, body, authorize_write=recheck_owner)
    recheck_owner()
    return result


@router.post("/{conversation_id}/trash", response_model=ConversationCommandReceipt)
@router.post("/{conversation_id}/restore", response_model=ConversationCommandReceipt)
def set_trash(world_id: str, conversation_id: UUID, body: ConversationTrashCommand, request: Request):
    world = scope(request, world_id, ())
    if body.world_id != world or body.conversation_id != conversation_id:
        raise HTTPException(422, detail="Lifecycle command differs from this World or conversation")
    from apps.live_control_server.services import hosted_auth

    service = _conversation_service(request)
    restore = request.url.path.endswith("/restore")
    if hosted_auth.deployment_environment() in hosted_auth.LOCAL_ENVIRONMENTS:
        return call(service.set_conversation_trash, body, restore=restore)

    def recheck_owner():
        require_conversation_access(request, world, authorize_local=enforce_native_graph_gm)

    result = call(service.set_conversation_trash, body, restore=restore, authorize_write=recheck_owner)
    recheck_owner()
    return result


@router.post("/{conversation_id}/delete", response_model=ConversationCommandReceipt)
def delete_conversation(world_id: str, conversation_id: UUID, body: ConversationDeleteCommand, request: Request):
    world = scope(request, world_id, ())
    if body.world_id != world or body.conversation_id != conversation_id:
        raise HTTPException(422, detail="Delete command differs from this World or conversation")
    service = _conversation_service(request)

    def recheck_owner():
        require_conversation_access(request, world, authorize_local=enforce_native_graph_gm)

    result = call(service.delete_conversation, body, authorize_write=recheck_owner)
    call(finish_conversation_erasure, conversation_id)
    recheck_owner()
    return result
