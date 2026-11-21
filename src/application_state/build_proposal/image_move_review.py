"""Durable, single-use editor authority for typed Build image moves."""

from datetime import datetime, timezone
from typing import Literal
from uuid import UUID

from psycopg.types.json import Jsonb
from pydantic import ConfigDict, Field, model_validator

from application_state.agent_conversation.plan_authoring import strict_json
from application_state.agent_conversation.rules_authority_types import canonical_sha256
from application_state.agent_conversation.service import _lock_pointer, _ready_dsn
from application_state.build_proposal.image_move import BuildImageMovePlacement
from application_state.build_proposal.types import StrictModel
from application_state.content import pages, repository
from application_state.content.page_presentation import Digest
from application_state.content.types import sha256_utf8
from application_state.errors import ApplicationStateConflictError, ApplicationStateNotFoundError
from application_state.unit_of_work import unit_of_work


class BuildImageMoveReview(StrictModel):
    model_config = ConfigDict(extra="forbid", frozen=True, populate_by_name=True, serialize_by_alias=True)

    schema_version: Literal["dmb_build_image_move_review_v1"] = Field(
        default="dmb_build_image_move_review_v1", alias="schema"
    )
    action_id: UUID
    conversation_id: UUID
    expected_pointer_revision: int = Field(ge=1)
    placement: BuildImageMovePlacement
    after_editor_sha256: Digest
    after_presentation_sha256: Digest
    state: Literal["editing", "claimed", "saved"]
    claim_id: UUID | None = None
    saved_revision: int | None = Field(default=None, ge=1)
    revision: int = Field(ge=1)
    updated_at: datetime

    @model_validator(mode="after")
    def exact_lifecycle(self):
        if (self.state == "editing") != (self.claim_id is None):
            raise ValueError("Only an unused image move can remain editable")
        if (self.state == "saved") != (self.saved_revision is not None):
            raise ValueError("Only a verified image move carries a saved revision")
        if self.saved_revision is not None and self.saved_revision <= self.placement.basis.registry_revision:
            raise ValueError("The image move must advance the saved Page revision")
        if self.after_presentation_sha256 == self.placement.presentation_sha256:
            raise ValueError("The projected presentation must change")
        return self


def _now():
    return datetime.now(timezone.utc)


def _read(conn, world_id, action_id, *, lock=False):
    statement = "SELECT payload FROM agent.build_image_move_review WHERE world_id=%s AND action_id=%s"
    if lock:
        statement += " FOR UPDATE"
    row = conn.execute(statement, (world_id, action_id)).fetchone()
    return BuildImageMoveReview.model_validate(row[0]) if row else None


def _existing(conn, world_id, action_id, *, lock=False):
    review = _read(conn, world_id, action_id, lock=lock)
    if review is None:
        raise ApplicationStateNotFoundError("Image move Review unavailable")
    return review


def _require_scope(pointer, conversation_id, revision):
    if pointer.active_conversation_id != conversation_id or pointer.revision != revision:
        raise ApplicationStateConflictError("Image move Review conversation changed")


def _page_snapshot(conn, placement):
    basis = placement.basis
    state = pages._state(conn, basis.document_id, basis.world_id, lock=True)
    if state.page.status != "active" or state.metadata.visibility_state != "internal":
        raise ApplicationStateConflictError("Image move requires the editable internal Page")
    return pages._committed_snapshot(conn, state)


def _project(conn, placement, editor_json):
    basis = placement.basis
    saved = _page_snapshot(conn, placement)
    if (
        saved.page.object_revision != basis.registry_revision
        or saved.revision is None
        or saved.presentation is None
        or saved.revision.content_sha256 != basis.content_sha256
    ):
        raise ApplicationStateConflictError("The captured saved Page changed")
    copy = repository.get_working_copy(conn, saved.page.work_object_id)
    if copy is not None and copy.content_sha256 != saved.revision.content_sha256:
        raise ApplicationStateConflictError("The Page has a divergent working copy")
    presentation, asset_id = placement.project_saved_move(saved.presentation, saved.revision.markdown)
    return placement.project_editor_move(editor_json, saved.presentation, saved.revision.markdown, asset_id), presentation


def _change(conn, review, **fields):
    changed = BuildImageMoveReview.model_validate({
        **review.model_dump(mode="python", by_alias=False),
        **fields, "revision": review.revision + 1, "updated_at": _now(),
    })
    conn.execute(
        "UPDATE agent.build_image_move_review SET revision=%s,payload=%s WHERE world_id=%s AND action_id=%s",
        (changed.revision, Jsonb(changed.model_dump(mode="json")), review.placement.basis.world_id, review.action_id),
    )
    return changed


class BuildImageMoveReviewService:
    def get(self, world_id: str, action_id: UUID) -> BuildImageMoveReview:
        with unit_of_work(_ready_dsn()) as conn:
            return _existing(conn, world_id, action_id)

    def stage_in_transaction(
        self, conn, action_id, conversation_id, expected_pointer_revision, placement, editor_json, *, admit,
    ) -> BuildImageMoveReview:
        """Joins the native authorized turn's transaction; cannot write the author's Page."""
        world_id = placement.basis.world_id
        if sha256_utf8(editor_json) != placement.basis.editor_sha256:
            raise ApplicationStateConflictError("The captured editor changed")
        pointer = _lock_pointer(conn, world_id)
        _require_scope(pointer, conversation_id, expected_pointer_revision)
        previous = _read(conn, world_id, action_id, lock=True)
        if previous is not None:
            if (previous.conversation_id, previous.expected_pointer_revision, previous.placement) != (
                conversation_id, expected_pointer_revision, placement,
            ):
                raise ApplicationStateConflictError("Image move action has different admitted inputs")
            admit(conn, previous)
            return previous
        editor, presentation = _project(conn, placement, editor_json)
        review = BuildImageMoveReview(
            action_id=action_id, conversation_id=conversation_id, expected_pointer_revision=expected_pointer_revision,
            placement=placement, after_editor_sha256=canonical_sha256(editor),
            after_presentation_sha256=presentation.fingerprint(), state="editing", revision=1, updated_at=_now(),
        )
        admit(conn, review)
        conn.execute(
            """INSERT INTO agent.build_image_move_review(action_id,world_id,conversation_id,revision,payload)
               VALUES (%s,%s,%s,1,%s)""",
            (action_id, world_id, conversation_id, Jsonb(review.model_dump(mode="json"))),
        )
        return review

    def claim(self, world_id, action_id, expected_revision, claim_id, editor_json, after_editor_json, *, authorize):
        """Consume editor authority once. An acknowledged retry never grants a second apply."""
        with unit_of_work(_ready_dsn()) as conn:
            pointer = _lock_pointer(conn, world_id)
            review = _existing(conn, world_id, action_id, lock=True)
            _require_scope(pointer, review.conversation_id, review.expected_pointer_revision)
            authorize(conn, review)
            try:
                after = strict_json(after_editor_json)
            except ValueError as error:
                raise ApplicationStateConflictError("Image move editor postimage is invalid") from error
            if canonical_sha256(after) != review.after_editor_sha256:
                raise ApplicationStateConflictError("Image move editor postimage differs from the offered move")
            if review.claim_id == claim_id:
                return review, False
            if review.state != "editing" or review.revision != expected_revision:
                raise ApplicationStateConflictError("Image move Review has already been consumed or changed")
            editor, layout = _project(conn, review.placement, editor_json)
            if editor != after or layout.fingerprint() != review.after_presentation_sha256:
                raise ApplicationStateConflictError("Image move no longer matches the offered postimage")
            return _change(conn, review, state="claimed", claim_id=claim_id), True

    def confirm(self, world_id, action_id, claim_id, *, authorize) -> BuildImageMoveReview:
        """Observe the Page owner's explicit Save; never write Page content here."""
        with unit_of_work(_ready_dsn()) as conn:
            pointer = _lock_pointer(conn, world_id)
            review = _existing(conn, world_id, action_id, lock=True)
            _require_scope(pointer, review.conversation_id, review.expected_pointer_revision)
            authorize(conn, review)
            if review.claim_id is None or review.claim_id != claim_id:
                raise ApplicationStateConflictError("Image move Save has a different claim")
            if review.state == "saved":
                return review
            saved = _page_snapshot(conn, review.placement)
            basis = review.placement.basis
            if (
                saved.page.object_revision != basis.registry_revision + 1
                or saved.revision is None
                or saved.revision.content_sha256 != basis.content_sha256
                or saved.presentation is None
                or saved.presentation.fingerprint() != review.after_presentation_sha256
                or saved.layout_writer_profile != pages.PAGE_LAYOUT_WRITER_PROFILE
            ):
                raise ApplicationStateConflictError("The exact image move is not the committed Page")
            return _change(conn, review, state="saved", saved_revision=saved.page.object_revision)
