"""Dedicated, writer-free review records for typed Build reference placement."""

from __future__ import annotations

from datetime import datetime, timezone
from hashlib import sha256
from typing import Annotated, Literal
from uuid import UUID

from psycopg.types.json import Jsonb
from pydantic import ConfigDict, Field, model_validator

from application_state.agent_conversation.service import _lock_pointer, _ready_dsn
from application_state.build_proposal.graph_reference import BuildGraphReferencePlacement
from application_state.build_proposal.types import StrictModel
from application_state.errors import ApplicationStateConflictError, ApplicationStateNotFoundError
from application_state.unit_of_work import unit_of_work


class BuildGraphReferenceApply(StrictModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    apply_id: UUID
    editor_sha256: str = Field(pattern=r"^[a-f0-9]{64}$")
    draft_sha256: str = Field(pattern=r"^[a-f0-9]{64}$")
    content_sha256: str = Field(pattern=r"^[a-f0-9]{64}$")
    presentation_sha256: str | None = Field(pattern=r"^[a-f0-9]{64}$")


class BuildGraphReferenceReview(StrictModel):
    model_config = ConfigDict(extra="forbid", frozen=True, populate_by_name=True, serialize_by_alias=True)

    schema_version: Literal["dmb_build_graph_reference_review_v1"] = Field(
        default="dmb_build_graph_reference_review_v1", alias="schema",
    )
    action_id: UUID
    conversation_id: UUID
    expected_pointer_revision: int = Field(strict=True, ge=1)
    placement: BuildGraphReferencePlacement
    revision: int = Field(strict=True, ge=1)
    state: Literal["editing", "applying", "applied", "discarded"]
    apply: BuildGraphReferenceApply | None = None
    saved_revision: int | None = Field(default=None, strict=True, ge=1)
    updated_at: datetime

    @model_validator(mode="after")
    def exact_state_receipts(self):
        if (self.state in {"applying", "applied"}) != (self.apply is not None):
            raise ValueError("Only a prepared Graph reference review carries the insertion postimage")
        if (self.state == "applied") != (self.saved_revision is not None):
            raise ValueError("Only a verified committed Graph reference review carries the saved revision")
        basis = self.placement.basis
        if self.apply is not None and (
            self.apply.editor_sha256 == basis.editor_sha256 or self.apply.draft_sha256 == basis.draft_sha256
            or self.apply.content_sha256 == basis.content_sha256
        ):
            raise ValueError("A Graph reference insertion must change its exact prepared postimage")
        if self.saved_revision is not None and self.saved_revision <= basis.registry_revision:
            raise ValueError("A Graph reference save must advance the captured page revision")
        return self


class _BuildGraphReferenceCommand(StrictModel):
    schema_version: Literal["dmb_build_graph_reference_command_v1"] = Field(alias="schema")


class BuildGraphReferencePrepare(_BuildGraphReferenceCommand):
    operation: Literal["prepare"]
    expected_revision: int = Field(strict=True, ge=1)
    apply: BuildGraphReferenceApply
    editor_json: str
    draft_markdown: str
    after_editor_json: str
    after_draft_markdown: str


class BuildGraphReferenceConfirm(_BuildGraphReferenceCommand):
    operation: Literal["confirm"]
    apply_id: UUID


class BuildGraphReferenceAuthorizeSave(_BuildGraphReferenceCommand):
    operation: Literal["authorize_save"]
    apply_id: UUID


class BuildGraphReferenceDiscard(_BuildGraphReferenceCommand):
    operation: Literal["discard"]
    expected_revision: int = Field(strict=True, ge=1)


BuildGraphReferenceCommand = Annotated[
    BuildGraphReferencePrepare | BuildGraphReferenceAuthorizeSave | BuildGraphReferenceConfirm | BuildGraphReferenceDiscard,
    Field(discriminator="operation"),
]


def _now():
    return datetime.now(timezone.utc)


def _digest(value: str) -> str:
    return sha256(value.encode("utf-8")).hexdigest()


def _read(conn, world_id, action_id, *, lock=False):
    query = "SELECT payload FROM agent.build_graph_reference_review WHERE world_id=%s AND action_id=%s"
    if lock:
        query += " FOR UPDATE"
    row = conn.execute(query, (world_id, action_id)).fetchone()
    return BuildGraphReferenceReview.model_validate(row[0]) if row else None


def _existing(conn, world_id, action_id):
    review = _read(conn, world_id, action_id, lock=True)
    if review is None:
        raise ApplicationStateNotFoundError("Graph reference review unavailable")
    return review


def _require_scope(pointer, review):
    if (pointer.active_conversation_id != review.conversation_id
            or pointer.revision != review.expected_pointer_revision):
        raise ApplicationStateConflictError("Graph reference review conversation changed")


def _change(conn, previous, **fields):
    result = BuildGraphReferenceReview.model_validate({
        **previous.model_dump(mode="python", by_alias=False), **fields,
        "revision": previous.revision + 1, "updated_at": _now(),
    })
    saved = conn.execute(
        """UPDATE agent.build_graph_reference_review SET payload=%s, revision=%s
           WHERE world_id=%s AND action_id=%s AND revision=%s""",
        (Jsonb(result.model_dump(mode="json", by_alias=True)), result.revision, result.placement.basis.world_id,
         result.action_id, previous.revision),
    )
    if saved.rowcount != 1:
        raise ApplicationStateConflictError("Graph reference review revision changed")
    return result


class BuildGraphReferenceReviewService:
    def get(self, world_id: str, action_id: UUID) -> BuildGraphReferenceReview:
        with unit_of_work(_ready_dsn()) as conn:
            review = _read(conn, world_id, action_id)
        if review is None:
            raise ApplicationStateNotFoundError("Graph reference review unavailable")
        return review

    def stage(self, action_id: UUID, conversation_id: UUID, expected_pointer_revision: int,
              placement: BuildGraphReferencePlacement, editor_json: str, draft: str, *, admit):
        """Called by the authorized action owner, never by a browser command."""
        with unit_of_work(_ready_dsn()) as conn:
            return self.stage_in_transaction(
                conn, action_id, conversation_id, expected_pointer_revision,
                placement, editor_json, draft, admit=admit,
            )

    def stage_in_transaction(self, conn, action_id: UUID, conversation_id: UUID,
                             expected_pointer_revision: int, placement: BuildGraphReferencePlacement,
                             editor_json: str, draft: str, *, admit) -> BuildGraphReferenceReview:
        """Stage the Review within the owner's transaction so admission and staging roll back together."""
        world_id = placement.basis.world_id
        placement.require_boundary(editor_json, draft)
        review = BuildGraphReferenceReview(
            action_id=action_id, conversation_id=conversation_id, expected_pointer_revision=expected_pointer_revision,
            placement=placement, revision=1, state="editing", updated_at=_now(),
        )
        pointer = _lock_pointer(conn, world_id)
        previous = _read(conn, world_id, action_id, lock=True)
        if previous is not None:
            if (previous.placement != placement or previous.conversation_id != conversation_id
                    or previous.expected_pointer_revision != expected_pointer_revision):
                raise ApplicationStateConflictError("Graph reference action has a different admitted request")
            return previous
        _require_scope(pointer, review)
        admit(conn, review)
        conn.execute(
            """INSERT INTO agent.build_graph_reference_review(action_id,world_id,conversation_id,revision,payload)
               VALUES (%s,%s,%s,1,%s)""",
            (action_id, world_id, conversation_id, Jsonb(review.model_dump(mode="json", by_alias=True))),
        )
        return review

    def prepare(self, world_id: str, action_id: UUID, expected_revision: int,
                receipt: BuildGraphReferenceApply, editor_json: str, draft: str,
                after_editor_json: str, after_draft: str, *, authorize_prepare):
        with unit_of_work(_ready_dsn()) as conn:
            pointer = _lock_pointer(conn, world_id)
            previous = _existing(conn, world_id, action_id)
            if previous.apply is not None and previous.apply.apply_id == receipt.apply_id:
                if previous.apply != receipt:
                    raise ApplicationStateConflictError("Graph reference apply has a different postimage")
                if previous.state == "applying":
                    _require_scope(pointer, previous)
                    _require_postimage(previous.placement, receipt, editor_json, draft, after_editor_json, after_draft)
                    authorize_prepare(previous, receipt)
                return previous
            _require_scope(pointer, previous)
            if previous.revision != expected_revision or previous.state != "editing":
                raise ApplicationStateConflictError("Graph reference review is no longer editable")
            _require_postimage(previous.placement, receipt, editor_json, draft, after_editor_json, after_draft)
            authorize_prepare(previous, receipt)
            return _change(conn, previous, state="applying", apply=receipt)

    def confirm(self, world_id: str, action_id: UUID, apply_id: UUID, *, observe_save):
        with unit_of_work(_ready_dsn()) as conn:
            previous = _existing(conn, world_id, action_id)
            if previous.apply is None or previous.apply.apply_id != apply_id:
                raise ApplicationStateConflictError("Graph reference save has a different apply receipt")
            if previous.state == "applied":
                return previous
            return _change(conn, previous, state="applied", saved_revision=observe_save(previous))

    def authorize_save(self, world_id: str, action_id: UUID, apply_id: UUID, *, authorize):
        with unit_of_work(_ready_dsn()) as conn:
            pointer = _lock_pointer(conn, world_id)
            review = _existing(conn, world_id, action_id)
            _require_scope(pointer, review)
            if review.state != "applying" or review.apply is None or review.apply.apply_id != apply_id:
                raise ApplicationStateConflictError("Graph reference Save requires its current prepared insertion")
            authorize(review)
            return review

    def discard(self, world_id: str, action_id: UUID, expected_revision: int, *, authorize_discard):
        with unit_of_work(_ready_dsn()) as conn:
            previous = _existing(conn, world_id, action_id)
            if previous.state == "discarded":
                return previous
            if previous.revision != expected_revision or previous.state != "editing":
                raise ApplicationStateConflictError("Only an inert Graph reference review can be discarded")
            authorize_discard()
            return _change(conn, previous, state="discarded")


def _require_postimage(placement, receipt, editor_json, draft, after_editor_json, after_draft):
    if receipt.editor_sha256 != _digest(after_editor_json) or receipt.draft_sha256 != _digest(after_draft):
        raise ApplicationStateConflictError("Graph reference apply differs from its exact editor and draft")
    index = placement.require_editor_insertion(editor_json, draft, after_editor_json)
    placement.require_draft_insertion(draft, after_draft, index)
