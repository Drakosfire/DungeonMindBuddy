"""Plan-owned author working copies and exact, recoverable application attempts.

The generated result never changes. This ledger does not apply editor content or
save a Plan; confirmation reads the existing Content owner's immutable history.
"""

from __future__ import annotations

from datetime import datetime
from typing import Annotated, Literal
from uuid import UUID

from pydantic import Field, TypeAdapter, model_validator

from application_state.agent_conversation.plan_authoring import (
    Frozen,
    PlanAuthoringCaptureV1,
    PlanActionAuthoringResultV1,
    text_digest,
    strict_json,
    validate_stored_authoring_result,
)
from application_state.errors import (
    ApplicationStateConflictError,
    ApplicationStateIntegrityError,
    ApplicationStateNotFoundError,
    ApplicationStateValidationError,
)

Digest = Annotated[str, Field(pattern=r"^[a-f0-9]{64}$")]


class PlanReviewApplicationV1(Frozen):
    application_id: UUID
    capture: PlanAuthoringCaptureV1
    markdown: str = Field(min_length=1)
    markdown_sha256: Digest
    after_editor_json: str
    after_editor_sha256: Digest
    after_markdown: str
    after_draft_sha256: Digest
    base_work_revision_id: UUID
    base_revision_n: int = Field(strict=True, ge=1)
    outcome: Literal["applying", "saved", "not_applied"] = "applying"
    saved_work_revision_id: UUID | None = None
    saved_revision_n: int | None = Field(default=None, strict=True, ge=1)

    @model_validator(mode="after")
    def exact_attempt(self):
        editor = strict_json(self.after_editor_json)
        if (
            text_digest(self.markdown) != self.markdown_sha256
            or not self.markdown.strip()
            or text_digest(self.after_editor_json) != self.after_editor_sha256
            or text_digest(self.after_markdown) != self.after_draft_sha256
            or not isinstance(editor, dict)
            or editor.get("type") != "doc"
            or not isinstance(editor.get("content", []), list)
        ):
            raise ValueError("Plan application differs from its complete working copy")
        if (
            (self.outcome == "saved") != (self.saved_work_revision_id is not None)
            or (self.saved_work_revision_id is None) != (self.saved_revision_n is None)
            or (
                self.saved_revision_n is not None
                and self.saved_revision_n < self.base_revision_n
            )
        ):
            raise ValueError("Saved Plan application needs its exact Content revision")
        return self


class PlanAuthoringReviewV1(Frozen):
    schema_: Literal["dmb_plan_authoring_review_v1"] = Field(
        default="dmb_plan_authoring_review_v1", alias="schema"
    )
    world_id: str
    action_id: UUID
    origin_sha256: Digest
    revision: int = Field(strict=True, ge=1)
    state: Literal["editing", "applying", "applied", "discarded"]
    markdown: str
    markdown_sha256: Digest
    capture: PlanAuthoringCaptureV1
    applications: tuple[PlanReviewApplicationV1, ...] = ()
    last_command_id: UUID
    last_command_sha256: Digest
    updated_at: datetime

    @model_validator(mode="after")
    def exact_review(self):
        if (
            self.capture.world_id != self.world_id
            or text_digest(self.markdown) != self.markdown_sha256
        ):
            raise ValueError("Plan review differs from its owner or working copy")
        if len({item.application_id for item in self.applications}) != len(
            self.applications
        ):
            raise ValueError("Plan review repeats an application identity")
        if any(
            item.capture.world_id != self.world_id
            or item.capture.document_id != self.capture.document_id
            for item in self.applications
        ):
            raise ValueError("Plan review application belongs to another page")
        pending = [
            index
            for index, item in enumerate(self.applications)
            if item.outcome == "applying"
        ]
        if pending != (
            [len(self.applications) - 1] if self.state == "applying" else []
        ):
            raise ValueError(
                "Uncertain Plan application must remain the current attempt"
            )
        if self.state in {"applying", "applied"}:
            if not self.applications:
                raise ValueError("Plan review has no application")
            last = self.applications[-1]
            if (
                last.capture != self.capture
                or last.markdown != self.markdown
                or last.outcome != ("saved" if self.state == "applied" else "applying")
            ):
                raise ValueError(
                    "Plan review state differs from its current exact application"
                )
        return self


class ReviewCommand(Frozen):
    command_id: UUID
    origin_sha256: Digest
    expected_revision: int = Field(strict=True, ge=0)


class OpenReview(ReviewCommand):
    operation: Literal["open"]


class SaveReview(ReviewCommand):
    operation: Literal["save"]
    markdown: str


class MoveReview(ReviewCommand):
    operation: Literal["move"]
    capture: PlanAuthoringCaptureV1


class PrepareReview(ReviewCommand):
    operation: Literal["prepare"]
    application_id: UUID
    after_editor_json: str
    after_editor_sha256: Digest
    after_markdown: str
    after_draft_sha256: Digest


class ConfirmReview(ReviewCommand):
    operation: Literal["confirm"]
    application_id: UUID


class ResolveBeforeReview(ReviewCommand):
    operation: Literal["resolve_before"]
    application_id: UUID
    capture: PlanAuthoringCaptureV1


class DiscardReview(ReviewCommand):
    operation: Literal["discard"]


PlanReviewCommand = Annotated[
    OpenReview
    | SaveReview
    | MoveReview
    | PrepareReview
    | ConfirmReview
    | ResolveBeforeReview
    | DiscardReview,
    Field(discriminator="operation"),
]
command_adapter = TypeAdapter(PlanReviewCommand)


def _locked_capture(conn, capture):
    from application_state.agent_conversation import repository as agent
    from application_state.content import repository as content

    pointer = agent.lock_world_state(conn, capture.world_id)
    conversation = agent.lock_conversation(
        conn, capture.world_id, capture.conversation_id
    )
    if (
        pointer.active_conversation_id != capture.conversation_id
        or pointer.revision != capture.expected_pointer_revision
        or conversation is None
        or conversation.status != "active"
    ):
        raise ApplicationStateConflictError(
            "The conversation changed; capture a current Plan placement before applying"
        )
    obj = content.lock_work_object(conn, UUID(capture.document_id))
    revision = (
        content.get_work_revision(conn, obj.current_revision_id)
        if obj and obj.current_revision_id
        else None
    )
    if (
        obj is None
        or obj.kind != "plan"
        or obj.status != "active"
        or obj.world_id != capture.world_id
        or obj.campaign_id is not None
        or obj.object_revision != capture.base_revision
        or revision is None
        or revision.content_sha256 != capture.base_content_sha256
        or revision.world_id != capture.world_id
        or revision.work_object_id != obj.work_object_id
    ):
        raise ApplicationStateConflictError(
            "The saved Plan changed; retain the suggestion and choose its current placement"
        )
    return revision


def _owner(conn, world_id, action_id, *, lock):
    from application_state.plan_action_dialogue import repository as actions
    from application_state.agent_conversation import repository as agent

    action = actions._get_by_id(conn, action_id, lock=lock)
    if action is None or action.basis.world_id != world_id:
        raise ApplicationStateNotFoundError("Plan proposal not found in this World")
    if action.status != "completed" or not isinstance(
        action.authoring_origin, PlanActionAuthoringResultV1
    ):
        raise ApplicationStateValidationError(
            "Only a completed authored Plan proposal has a review"
        )
    turn = agent.get_turn(conn, world_id, action.authoring_origin.turn_id)
    proposal = validate_stored_authoring_result(action, turn)
    review = action.authoring_review
    if review is not None and (
        review.action_id != action_id
        or review.world_id != world_id
        or review.origin_sha256 != proposal.origin.sha256
        or review.capture.document_id != proposal.capture.document_id
    ):
        raise ApplicationStateIntegrityError(
            "Plan review has a different immutable proposal owner"
        )
    return action, proposal, review


def read_review(world_id, action_id):
    from application_state.agent_conversation.service import _ready_dsn
    from application_state.unit_of_work import unit_of_work

    with unit_of_work(_ready_dsn()) as conn:
        conn.execute("SET TRANSACTION READ ONLY")
        return _owner(conn, world_id, action_id, lock=False)[2]

