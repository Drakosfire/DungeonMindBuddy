"""Authenticated review/continuation; no provider dispatch in these routes."""

from functools import partial
from uuid import UUID
from fastapi import APIRouter, Request
from application_state.agent_conversation import work_plan
from apps.live_control_server.services import hosted_auth
from .conversation_library import scope, call

router = APIRouter(
    prefix="/api/live/agent/worlds/{world_id}/conversations/{conversation_id}/work-plans",
    tags=["conversation work plans"],
)


@router.get("/{source_turn_id}")
def read(world_id: str, conversation_id: UUID, source_turn_id: UUID, request: Request):
    world = scope(request, world_id, ())
    result = call(work_plan.read, world, conversation_id, source_turn_id)
    if hosted_auth.deployment_environment() not in hosted_auth.LOCAL_ENVIRONMENTS:
        scope(request, world_id, ())
    return result


@router.put("/{source_turn_id}")
def save(
    world_id: str,
    conversation_id: UUID,
    source_turn_id: UUID,
    body: work_plan.ReviewV3 | work_plan.ReviewV2 | work_plan.Review,
    request: Request,
):
    world = scope(request, world_id, ())
    authorize_world = None
    if hosted_auth.deployment_environment() not in hosted_auth.LOCAL_ENVIRONMENTS:
        authorize_world = partial(scope, request, world_id, ())
    result = call(
        work_plan.save, world, conversation_id, source_turn_id, body,
        authorize_world=authorize_world,
    )
    if authorize_world is not None:
        authorize_world()
    return result


@router.post("/{source_turn_id}/continue")
def continue_step(
    world_id: str,
    conversation_id: UUID,
    source_turn_id: UUID,
    body: work_plan.Continue,
    request: Request,
):
    world = scope(request, world_id, ())
    authorize_world = None
    if hosted_auth.deployment_environment() not in hosted_auth.LOCAL_ENVIRONMENTS:
        authorize_world = partial(scope, request, world_id, ())
    result = call(
        work_plan.continue_step, world, conversation_id, source_turn_id, body,
        authorize_world=authorize_world,
    )
    if authorize_world is not None:
        authorize_world()
    return result
