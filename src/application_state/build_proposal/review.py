"""Mutable author review, separate from immutable generated proposal evidence.

Apply receipts describe a client-observed editor transaction, never durable Save.
"""

from datetime import datetime, timezone
from hashlib import sha256
from typing import Literal
from uuid import UUID

from pydantic import ConfigDict, Field, model_validator
from psycopg.types.json import Jsonb

from application_state.agent_conversation.service import _lock_pointer, _ready_dsn
from application_state.build_proposal.types import StrictModel
from application_state.build_proposal.service import _load, _save
from application_state.errors import (
    ApplicationStateConflictError,
    ApplicationStateNotFoundError,
)
from application_state.unit_of_work import unit_of_work

Digest = str


def digest(text):
    return sha256(text.encode()).hexdigest()


class ReviewApply(StrictModel):
    placement_caret: int = Field(strict=True, ge=0)
    apply_id: UUID
    before_editor_sha256: str = Field(pattern=r"^[a-f0-9]{64}$")
    after_editor_sha256: str = Field(pattern=r"^[a-f0-9]{64}$")
    before_draft_sha256: str = Field(pattern=r"^[a-f0-9]{64}$")
    after_draft_sha256: str = Field(pattern=r"^[a-f0-9]{64}$")
    reviewed_sha256: str = Field(pattern=r"^[a-f0-9]{64}$")


class BuildProposalReview(StrictModel):
    model_config = ConfigDict(
        extra="forbid", populate_by_name=True, serialize_by_alias=True
    )
    schema_version: Literal["dmb_build_proposal_review_v2"] = Field(
        default="dmb_build_proposal_review_v2", alias="schema"
    )
    world_id: str
    action_id: UUID
    reservation_sha256: str = Field(pattern=r"^[a-f0-9]{64}$")
    revision: int = Field(strict=True, ge=1)
    placement_caret: int = Field(strict=True, ge=0)
    state: Literal["editing", "discarded", "applying", "applied"]
    markdown: str = Field(min_length=1)
    markdown_sha256: str = Field(pattern=r"^[a-f0-9]{64}$")
    apply: ReviewApply | None = None
    updated_at: datetime

    @model_validator(mode="after")
    def validate_digest(self):
        if self.markdown_sha256 != digest(self.markdown):
            raise ValueError("Review Markdown digest differs")
        if (self.state in {"applying", "applied"}) != (self.apply is not None):
            raise ValueError("Review apply state requires its exact receipt")
        if self.apply and (
            self.apply.reviewed_sha256 != self.markdown_sha256
            or self.apply.placement_caret != self.placement_caret
        ):
            raise ValueError("Insertion differs from reviewed Markdown")
        return self


class BuildReviewCommand(StrictModel):
    operation: Literal["open", "save", "move", "discard", "prepare", "confirm"]
    expected_revision: int = Field(strict=True, ge=0)
    placement_caret: int | None = Field(default=None, strict=True, ge=0)
    markdown: str | None = None
    apply_id: UUID | None = None
    after_editor_sha256: str | None = Field(default=None, pattern=r"^[a-f0-9]{64}$")
    after_draft_sha256: str | None = Field(default=None, pattern=r"^[a-f0-9]{64}$")

    @model_validator(mode="after")
    def exact_fields(self):
        required = {
            "save": {"markdown"},
            "move": {"placement_caret"},
            "prepare": {"apply_id", "after_editor_sha256", "after_draft_sha256"},
            "confirm": {"apply_id"},
        }.get(self.operation, set())
        present = {
            name
            for name in (
                "markdown",
                "placement_caret",
                "apply_id",
                "after_editor_sha256",
                "after_draft_sha256",
            )
            if getattr(self, name) is not None
        }
        if present != required or (self.operation == "open") != (
            self.expected_revision == 0
        ):
            raise ValueError("Review command has different fields or revision")
        if self.markdown is not None and not self.markdown.strip():
            raise ValueError("A suggestion must contain text")
        return self


class BuildProposalReviewService:
    def get(self, world_id, action_id):
        with unit_of_work(_ready_dsn()) as conn:
            row = conn.execute(
                "SELECT payload FROM agent.build_proposal_review WHERE world_id=%s AND action_id=%s",
                (world_id, action_id),
            ).fetchone()
            if row is None:
                raise ApplicationStateNotFoundError("Proposal review unavailable")
            return BuildProposalReview.model_validate(row[0])

    def execute(self, world_id, action_id, command):
        with unit_of_work(_ready_dsn()) as conn:
            pointer = _lock_pointer(conn, world_id)
            row = conn.execute(
                "SELECT payload FROM agent.build_proposal WHERE world_id=%s AND action_id=%s FOR UPDATE",
                (world_id, action_id),
            ).fetchone()
            if row is None:
                raise ApplicationStateNotFoundError("Proposal unavailable")
            proposal = _load(row)
            row = conn.execute(
                "SELECT payload FROM agent.build_proposal_review WHERE world_id=%s AND action_id=%s FOR UPDATE",
                (world_id, action_id),
            ).fetchone()
            previous = BuildProposalReview.model_validate(row[0]) if row else None
            if command.operation == "open" and previous:
                return previous
            if (
                proposal.state != "proposed"
                or not proposal.reservation.basis.editor_sha256
                or pointer.active_conversation_id
                != proposal.reservation.conversation_id
                or pointer.revision != proposal.reservation.expected_pointer_revision
            ):
                raise ApplicationStateConflictError("Proposal review scope changed")
            now = datetime.now(timezone.utc)
            if command.operation == "open":
                if proposal.inserted_in_draft:
                    raise ApplicationStateConflictError("Proposal was already inserted")
                result = BuildProposalReview(
                    world_id=world_id,
                    action_id=action_id,
                    reservation_sha256=proposal.request_fingerprint,
                    revision=1,
                    state="editing",
                    placement_caret=proposal.reservation.basis.caret,
                    markdown=proposal.proposal.replacement_markdown,
                    markdown_sha256=digest(proposal.proposal.replacement_markdown),
                    updated_at=now,
                )
                conn.execute(
                    "INSERT INTO agent.build_proposal_review(action_id,world_id,revision,payload) VALUES(%s,%s,1,%s)",
                    (action_id, world_id, Jsonb(result.model_dump(mode="json"))),
                )
                return result
            if (
                previous is None
                or previous.reservation_sha256 != proposal.request_fingerprint
            ):
                raise ApplicationStateConflictError(
                    "Open the exact proposal review first"
                )
            if (
                command.operation in {"prepare", "confirm"}
                and previous.apply
                and previous.apply.apply_id == command.apply_id
            ):
                if command.operation == "prepare":
                    if (
                        previous.apply.after_editor_sha256
                        != command.after_editor_sha256
                        or previous.apply.after_draft_sha256
                        != command.after_draft_sha256
                    ):
                        raise ApplicationStateConflictError(
                            "Insertion identity has different bytes"
                        )
                    return previous
                if previous.state == "applied":
                    return previous
            if previous.revision != command.expected_revision:
                raise ApplicationStateConflictError(
                    "The saved suggestion changed; your local text is retained"
                )
            update = {"revision": previous.revision + 1, "updated_at": now}
            if (
                command.operation in {"save", "move", "discard", "prepare"}
                and previous.state != "editing"
            ):
                raise ApplicationStateConflictError(
                    "This review is terminal or its insertion is uncertain"
                )
            if command.operation == "save":
                update.update(
                    markdown=command.markdown, markdown_sha256=digest(command.markdown)
                )
            elif command.operation == "move":
                update["placement_caret"] = command.placement_caret
            elif command.operation == "discard":
                update["state"] = "discarded"
            elif command.operation == "prepare":
                if proposal.inserted_in_draft:
                    raise ApplicationStateConflictError("Proposal was already inserted")
                basis = proposal.reservation.basis
                update.update(
                    state="applying",
                    apply=ReviewApply(
                        placement_caret=previous.placement_caret,
                        apply_id=command.apply_id,
                        before_editor_sha256=basis.editor_sha256,
                        before_draft_sha256=basis.draft_sha256,
                        after_editor_sha256=command.after_editor_sha256,
                        after_draft_sha256=command.after_draft_sha256,
                        reviewed_sha256=previous.markdown_sha256,
                    ),
                )
            elif command.operation == "confirm":
                if (
                    previous.state != "applying"
                    or previous.apply.apply_id != command.apply_id
                ):
                    raise ApplicationStateConflictError("The insertion receipt differs")
                update["state"] = "applied"
                _save(
                    conn,
                    proposal,
                    {
                        **proposal.model_dump(mode="python"),
                        "inserted_in_draft": True,
                        "revision": proposal.revision + 1,
                        "updated_at": now,
                    },
                )
            else:
                raise ApplicationStateConflictError("Unsupported review transition")
            result = BuildProposalReview.model_validate(
                {**previous.model_dump(mode="python"), **update}
            )
            changed = conn.execute(
                "UPDATE agent.build_proposal_review SET revision=%s,payload=%s WHERE world_id=%s AND action_id=%s AND revision=%s",
                (
                    result.revision,
                    Jsonb(result.model_dump(mode="json")),
                    world_id,
                    action_id,
                    previous.revision,
                ),
            )
            if changed.rowcount != 1:
                raise ApplicationStateConflictError("The saved suggestion changed")
            return result
