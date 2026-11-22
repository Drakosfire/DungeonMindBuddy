"""Authorized Review transport for a single existing Build image move."""

from typing import Annotated, Literal
from uuid import UUID

from fastapi import APIRouter, HTTPException, Request
from pydantic import BaseModel, ConfigDict, Field

from application_state.agent_conversation import AgentConversationService
from application_state.agent_conversation.rules_authority_types import canonical_sha256
from application_state.agent_conversation.types import BuildImageMoveCompletionV1
from application_state.build_proposal.image_move_review import BuildImageMoveReview, BuildImageMoveReviewService
from application_state.errors import ApplicationStateError, ApplicationStateNotFoundError

from .build_proposal_reviews import scope

router = APIRouter()
_PATH = "/worlds/{world_id}/build-image-moves/{action_id}/review"


class ImageMoveClaim(BaseModel):
    model_config = ConfigDict(extra="forbid")

    operation: Literal["claim"]
    expected_revision: int = Field(strict=True, ge=1)
    claim_id: UUID
    editor_json: str = Field(min_length=1, max_length=1_000_000)
    after_editor_json: str = Field(min_length=1, max_length=1_000_000)


class ImageMoveConfirm(BaseModel):
    model_config = ConfigDict(extra="forbid")

    operation: Literal["confirm"]
    claim_id: UUID


ImageMoveCommand = Annotated[ImageMoveClaim | ImageMoveConfirm, Field(discriminator="operation")]


class ImageMoveReviewResult(BaseModel):
    review: BuildImageMoveReview
    issued: bool = False


def _require_completed_source(world, action_id, review):
    turn = AgentConversationService().inspect_turn(world_id=world, turn_id=action_id)
    completion = turn.completion
    work = turn.provenance.primary_work
    if (turn.status != "completed" or type(completion) is not BuildImageMoveCompletionV1
            or completion.disposition != "ready" or completion.action_id != action_id
            or completion.placement_sha256 != canonical_sha256(review.placement)
            or turn.conversation_id != review.conversation_id
            or turn.provenance.surface_id != "build" or turn.provenance.world_id != world
            or work.kind != "build" or work.resolution != "resolved"
            or work.object_id != review.placement.basis.document_id):
        raise ApplicationStateNotFoundError("Image move Review does not match its completed Build turn")


@router.get(_PATH, response_model=ImageMoveReviewResult)
def get_image_move_review(world_id: str, action_id: UUID, request: Request):
    world = scope(world_id, request)
    try:
        review = BuildImageMoveReviewService().get(world, action_id)
        _require_completed_source(world, action_id, review)
        scope(world_id, request)
        return ImageMoveReviewResult(review=review)
    except ApplicationStateError as exc:
        raise HTTPException(exc.status_code, detail={"code": "image_move_review_unavailable"}) from exc


@router.post(_PATH, response_model=ImageMoveReviewResult)
def change_image_move_review(world_id: str, action_id: UUID, body: ImageMoveCommand, request: Request):
    world = scope(world_id, request)
    service = BuildImageMoveReviewService()

    def authorize(_conn, review):
        scope(world_id, request)
        _require_completed_source(world, action_id, review)

    try:
        if isinstance(body, ImageMoveClaim):
            review, issued = service.claim(
                world, action_id, body.expected_revision, body.claim_id, body.editor_json,
                body.after_editor_json, authorize=authorize,
            )
            return ImageMoveReviewResult(review=review, issued=issued)
        return ImageMoveReviewResult(review=service.confirm(world, action_id, body.claim_id, authorize=authorize))
    except ApplicationStateError as exc:
        raise HTTPException(exc.status_code,
                            detail={"code": "image_move_review_changed", "message": str(exc)}) from exc
