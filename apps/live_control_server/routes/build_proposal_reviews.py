"""Authenticated author review; no provider call or source writer is reachable."""

from functools import partial
from uuid import UUID
from fastapi import APIRouter, HTTPException, Request
from application_state.build_proposal.review import (
    BuildReviewCommand,
    BuildProposalReviewService,
)
from application_state.errors import ApplicationStateError
from apps.live_control_server.services import hosted_auth
from apps.live_control_server.services.agent_graph_auth import enforce_native_graph_gm

router = APIRouter()


def scope(world_id, request):
    from .agent import _verified_world_id

    from apps.live_control_server.services.hosted_native_graph_access import require_conversation_access

    require_conversation_access(request, world_id, authorize_local=enforce_native_graph_gm)
    verified = _verified_world_id(world_id)
    if request.query_params:
        raise HTTPException(422, detail="Review accepts no query selectors")
    return verified


@router.get("/worlds/{world_id}/build-proposals/{action_id}/review")
def get_review(world_id: str, action_id: UUID, request: Request):
    world = scope(world_id, request)
    try:
        review = BuildProposalReviewService().get(world, action_id)
        if hosted_auth.deployment_environment() not in hosted_auth.LOCAL_ENVIRONMENTS:
            scope(world_id, request)
        return review
    except ApplicationStateError as exc:
        raise HTTPException(
            exc.status_code, detail={"code": "proposal_review_unavailable"}
        ) from exc


@router.post("/worlds/{world_id}/build-proposals/{action_id}/review")
def change_review(
    world_id: str, action_id: UUID, body: BuildReviewCommand, request: Request
):
    world = scope(world_id, request)
    try:
        from apps.live_control_server.services.build_document_proposal import _source, BuildComposeError
        def validate_source(capability):
            try:
                _source(capability)
            except BuildComposeError as exc:
                from application_state.errors import ApplicationStateConflictError
                raise ApplicationStateConflictError(str(exc)) from exc
        authorize_world = None
        if hosted_auth.deployment_environment() not in hosted_auth.LOCAL_ENVIRONMENTS:
            authorize_world = partial(scope, world_id, request)
        review = BuildProposalReviewService(validate_source=validate_source).execute(
            world, action_id, body, authorize_world=authorize_world,
        )
        if authorize_world is not None:
            authorize_world()
        return review
    except ApplicationStateError as exc:
        raise HTTPException(
            exc.status_code,
            detail={"code": "proposal_review_changed", "message": str(exc)},
        ) from exc
