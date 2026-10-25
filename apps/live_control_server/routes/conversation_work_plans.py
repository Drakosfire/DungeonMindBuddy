"""Authenticated review/continuation; no provider dispatch in these routes."""

from uuid import UUID
from fastapi import APIRouter, Request
from application_state.agent_conversation import work_plan
from .conversation_library import scope, call

router = APIRouter(
    prefix="/api/live/agent/worlds/{world_id}/conversations/{conversation_id}/work-plans",
    tags=["conversation work plans"],
)


@router.get("/{source_turn_id}")
def read(world_id: str, conversation_id: UUID, source_turn_id: UUID, request: Request):
    return call(
        work_plan.read, scope(request, world_id, ()), conversation_id, source_turn_id
    )


@router.put("/{source_turn_id}")
def save(
    world_id: str,
    conversation_id: UUID,
    source_turn_id: UUID,
    body: work_plan.ReviewV2 | work_plan.Review,
    request: Request,
):
    return call(
        work_plan.save,
        scope(request, world_id, ()),
        conversation_id,
        source_turn_id,
        body,
    )


@router.post("/{source_turn_id}/continue")
def continue_step(
    world_id: str,
    conversation_id: UUID,
    source_turn_id: UUID,
    body: work_plan.Continue,
    request: Request,
):
    return call(
        work_plan.continue_step,
        scope(request, world_id, ()),
        conversation_id,
        source_turn_id,
        body,
    )
