"""Plan-owned author working copies and exact, recoverable application attempts.

The generated result never changes. An explicit confirmation commits the sealed
Plan working copy and its application receipt in the same Content transaction.
"""

from __future__ import annotations

from datetime import UTC, datetime
from typing import Annotated, Literal
from uuid import UUID

from pydantic import Field, TypeAdapter, model_validator

from application_state.agent_conversation.plan_authoring import (
    Frozen,
    PlanAuthoringCaptureV1,
    PlanActionAuthoringResultV1,
    digest,
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
    after_title: str = Field(min_length=1)
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
            or not self.after_title.strip()
            or self.after_title != self.after_title.strip()
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
    after_title: str = Field(min_length=1)
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



def _persist_review(conn, action, review, *, expected_revision):
    from application_state.plan_action_dialogue import repository as actions

    return actions.write_authoring_review(
        conn, action_id=action.action_id, world_id=review.world_id,
        review=review, expected_revision=expected_revision,
    )


def execute_review_command(world_id, action_id, command):
    """One explicit review command, action-locked and fenced by revision/identity.

    Prepare seals the complete after-copy before editor mutation. Confirm saves
    those exact bytes and its receipt on one connection. A lost reply therefore
    reads/replays the same receipt rather than regenerating or applying again.
    """
    from application_state.agent_conversation.service import _ready_dsn
    from application_state.content.service import commit_plan_in_connection
    from application_state.content.types import normalize_markdown
    from application_state.unit_of_work import unit_of_work

    command = command_adapter.validate_python(command)
    command_sha = digest(command.model_dump(mode="json", by_alias=True))
    with unit_of_work(_ready_dsn()) as conn:
        action, proposal, review = _owner(conn, world_id, action_id, lock=True)
        if command.origin_sha256 != proposal.origin.sha256:
            raise ApplicationStateConflictError("The generated Plan proposal changed")
        if review is not None and review.last_command_id == command.command_id:
            if review.last_command_sha256 != command_sha:
                raise ApplicationStateConflictError("The Plan review command identity was reused")
            return review
        revision = review.revision if review is not None else 0
        if command.expected_revision != revision:
            raise ApplicationStateConflictError(
                "The Plan review changed; retain local edits and reconcile its newer copy"
            )
        common = dict(
            revision=revision + 1, last_command_id=command.command_id,
            last_command_sha256=command_sha, updated_at=datetime.now(UTC),
        )
        if review is None:
            if not isinstance(command, OpenReview):
                raise ApplicationStateConflictError("Open the generated Plan suggestion before editing")
            candidate = PlanAuthoringReviewV1(
                world_id=world_id, action_id=action_id,
                origin_sha256=proposal.origin.sha256, state="editing",
                markdown=proposal.replacement_markdown,
                markdown_sha256=text_digest(proposal.replacement_markdown),
                capture=proposal.capture, **common,
            )
        else:
            updates = dict(common)
            if isinstance(command, ConfirmReview):
                if (review.state != "applying"
                    or review.applications[-1].application_id != command.application_id):
                    raise ApplicationStateConflictError("This Plan application is not pending")
                application = review.applications[-1]
                current = _locked_capture(conn, application.capture)
                if (current.work_revision_id != application.base_work_revision_id
                    or current.revision_n != application.base_revision_n):
                    raise ApplicationStateConflictError("The Plan application base changed")
                saved, saved_revision = commit_plan_in_connection(
                    conn, application.capture.document_id, application.after_markdown,
                    expected_revision=application.capture.base_revision,
                    expected_world_id=world_id, title=application.after_title,
                )
                if (saved_revision.content_sha256 != application.after_draft_sha256
                    or saved.title != application.after_title):
                    raise ApplicationStateIntegrityError("Content Save differs from the sealed Plan copy")
                completed = application.model_copy(update={
                    "outcome": "saved",
                    "saved_work_revision_id": saved_revision.work_revision_id,
                    "saved_revision_n": saved_revision.revision_n,
                })
                updates.update(state="applied", applications=review.applications[:-1] + (completed,))
            elif isinstance(command, ResolveBeforeReview):
                if (review.state != "applying"
                    or review.applications[-1].application_id != command.application_id):
                    raise ApplicationStateConflictError("This Plan application is not pending")
                application = review.applications[-1]
                capture = command.capture
                if (capture.world_id != world_id
                    or capture.document_id != proposal.capture.document_id
                    or capture.draft_sha256 != application.capture.draft_sha256
                    or capture.editor_sha256 != application.capture.editor_sha256):
                    raise ApplicationStateConflictError(
                        "The editor does not prove the unchanged before-copy; retain the application"
                    )
                current = _locked_capture(conn, capture)
                if (current.work_revision_id != application.base_work_revision_id
                    or current.revision_n != application.base_revision_n):
                    raise ApplicationStateConflictError("The saved Plan no longer proves the before-copy")
                cancelled = application.model_copy(update={"outcome": "not_applied"})
                updates.update(state="editing", capture=capture,
                    applications=review.applications[:-1] + (cancelled,))
            else:
                if review.state == "applying":
                    raise ApplicationStateConflictError(
                        "Resolve the existing Plan application before changing or discarding it"
                    )
                if review.state == "applied":
                    raise ApplicationStateConflictError("This Plan suggestion is already saved")
                if isinstance(command, OpenReview):
                    updates.update(state="editing")
                elif isinstance(command, DiscardReview):
                    updates.update(state="discarded")
                else:
                    if review.state != "editing":
                        raise ApplicationStateConflictError("Reopen the discarded Plan suggestion first")
                    if isinstance(command, SaveReview):
                        updates.update(markdown=command.markdown,
                            markdown_sha256=text_digest(command.markdown))
                    elif isinstance(command, MoveReview):
                        capture = command.capture
                        if (capture.world_id != world_id
                            or capture.document_id != proposal.capture.document_id):
                            raise ApplicationStateConflictError("Plan placement belongs to another page")
                        _locked_capture(conn, capture)
                        updates.update(capture=capture)
                    elif isinstance(command, PrepareReview):
                        if any(a.application_id == command.application_id for a in review.applications):
                            raise ApplicationStateConflictError("Plan application identity was already used")
                        current = _locked_capture(conn, review.capture)
                        if normalize_markdown(command.after_markdown) != command.after_markdown:
                            raise ApplicationStateValidationError("Plan application requires canonical newlines")
                        application = PlanReviewApplicationV1(
                            application_id=command.application_id,
                            capture=review.capture, markdown=review.markdown,
                            markdown_sha256=review.markdown_sha256,
                            after_editor_json=command.after_editor_json,
                            after_editor_sha256=command.after_editor_sha256,
                            after_markdown=command.after_markdown,
                            after_title=command.after_title,
                            after_draft_sha256=command.after_draft_sha256,
                            base_work_revision_id=current.work_revision_id,
                            base_revision_n=current.revision_n,
                        )
                        updates.update(state="applying", applications=review.applications + (application,))
            candidate = PlanAuthoringReviewV1.model_validate(
                review.model_dump(mode="python", by_alias=True) | updates
            )
        return _persist_review(conn, action, candidate, expected_revision=revision)
