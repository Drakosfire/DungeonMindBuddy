"""Authenticated author review; no provider call or source writer is reachable."""

from uuid import UUID
from fastapi import APIRouter, HTTPException, Request
from application_state.build_proposal.review import (
    BuildReviewCommand,
    BuildProposalReviewService,
)
from application_state.errors import ApplicationStateError
from apps.live_control_server.services.agent_graph_auth import enforce_native_graph_gm

router = APIRouter()


def scope(world_id, request):
    from .agent import _verified_world_id

    enforce_native_graph_gm(request)
    verified = _verified_world_id(world_id)
    if request.query_params:
        raise HTTPException(422, detail="Review accepts no query selectors")
    return verified


@router.get("/worlds/{world_id}/build-proposals/{action_id}/review")
def get_review(world_id: str, action_id: UUID, request: Request):
    world = scope(world_id, request)
    try:
        return BuildProposalReviewService().get(world, action_id)
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
        return BuildProposalReviewService().execute(world, action_id, body)
    except ApplicationStateError as exc:
        raise HTTPException(
            exc.status_code,
            detail={"code": "proposal_review_changed", "message": str(exc)},
        ) from exc
