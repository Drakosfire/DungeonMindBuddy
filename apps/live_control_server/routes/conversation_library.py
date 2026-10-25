"""Explicit authenticated conversation library; no active-pointer mutation."""

from uuid import UUID
from fastapi import APIRouter, HTTPException, Query, Request
from application_state.agent_conversation import library
from application_state.errors import ApplicationStateError
from apps.live_control_server.services.agent_graph_auth import enforce_native_graph_gm
from apps.live_control_server.routes.agent import _verified_world_id

router = APIRouter(
    prefix="/api/live/agent/worlds/{world_id}/conversations",
    tags=["conversation library"],
)


def scope(request, world, allowed):
    enforce_native_graph_gm(request)
    if set(request.query_params) - set(allowed) or any(
        len(request.query_params.getlist(k)) != 1 for k in request.query_params
    ):
        raise HTTPException(422, detail="Unexpected or repeated conversation selector")
    return _verified_world_id(world)


def call(function, *args, **kwargs):
    try:
        return function(*args, **kwargs)
    except ApplicationStateError as exc:
        raise HTTPException(exc.status_code, detail=str(exc)) from exc


@router.get("")
def list_conversations(
    world_id: str,
    request: Request,
    status: str = Query("all", pattern="^(all|archived)$"),
    limit: int = Query(25, ge=1, le=50),
    before: UUID | None = None,
):
    world = scope(request, world_id, {"status", "limit", "before"})
    return call(library.list_library, world, status=status, limit=limit, before=before)


@router.get("/{conversation_id}/turns")
def turns(
    world_id: str,
    conversation_id: UUID,
    request: Request,
    limit: int = Query(50, ge=1, le=100),
    before_sequence: int | None = Query(None, gt=0),
):
    world = scope(request, world_id, {"limit", "before_sequence"})
    return call(
        library.read_turns,
        world,
        conversation_id,
        limit=limit,
        before_sequence=before_sequence,
    )


@router.get("/{conversation_id}/name")
def name(world_id: str, conversation_id: UUID, request: Request):
    return call(library.get_name, scope(request, world_id, ()), conversation_id)


@router.put("/{conversation_id}/name")
def rename(
    world_id: str, conversation_id: UUID, body: library.NameChange, request: Request
):
    return call(library.rename, scope(request, world_id, ()), conversation_id, body)


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
    return call(
        library.read_retry_attempts,
        world,
        conversation_id,
        turn_id,
        limit=limit,
        before_sequence=before_sequence,
    )
