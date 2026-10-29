"""Mutable author review, separate from immutable generated proposal evidence.

Apply receipts describe a client-observed editor transaction, never durable Save.
"""

from datetime import datetime, timezone
from hashlib import sha256
from typing import Literal
from uuid import UUID

from pydantic import ConfigDict, Field, model_validator, model_serializer
from psycopg.types.json import Jsonb

from application_state.agent_conversation.service import _lock_pointer, _ready_dsn
from application_state.build_proposal.types import StrictModel, BuildProposalBasis, BuildPageBodyOffer
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
    page_body_target: BuildPageBodyOffer | None = None
    placement_caret: int = Field(strict=True, ge=0)
    apply_id: UUID
    before_editor_sha256: str = Field(pattern=r"^[a-f0-9]{64}$")
    after_editor_sha256: str = Field(pattern=r"^[a-f0-9]{64}$")
    before_draft_sha256: str = Field(pattern=r"^[a-f0-9]{64}$")
    after_draft_sha256: str = Field(pattern=r"^[a-f0-9]{64}$")
    reviewed_sha256: str = Field(pattern=r"^[a-f0-9]{64}$")


    @model_serializer(mode="wrap")
    def preserve_historical_apply(self, serialize):
        value = serialize(self)
        if self.page_body_target is None:
            value.pop("page_body_target", None)
        return value


class PlacementCapability(StrictModel):
    command_id: UUID
    conversation_id: UUID
    expected_pointer_revision: int = Field(strict=True, ge=1)
    basis: BuildProposalBasis
    draft_markdown: str

    @model_validator(mode="after")
    def exact_draft(self):
        if not self.basis.editor_sha256 or digest(self.draft_markdown) != self.basis.draft_sha256:
            raise ValueError("Fresh placement requires exact captured draft and editor")
        return self


class RetiredPlacement(StrictModel):
    basis: BuildProposalBasis
    markdown: str
    markdown_sha256: str
    apply: ReviewApply | None
    command_id: UUID | None
    disposition: Literal["superseded_unresolved", "superseded_unapplied"]

    @model_validator(mode="after")
    def honest_receipt(self):
        if (digest(self.markdown) != self.markdown_sha256
            or (self.apply is not None) != (self.disposition == "superseded_unresolved")
            or (self.apply is not None and (self.apply.reviewed_sha256 != self.markdown_sha256
                or self.apply.before_editor_sha256 != self.basis.editor_sha256
                or self.apply.before_draft_sha256 != self.basis.draft_sha256
                or self.apply.placement_caret != self.basis.caret))):
            raise ValueError("Retired placement differs from its original receipt")
        return self


class BuildProposalReview(StrictModel):
    model_config = ConfigDict(
        extra="forbid", populate_by_name=True, serialize_by_alias=True
    )
    schema_version: Literal["dmb_build_proposal_review_v2", "dmb_build_proposal_review_v3"] = Field(
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
    page_body_target: BuildPageBodyOffer | None = None
    placement: PlacementCapability | None = None
    retired_placements: list[RetiredPlacement] = Field(default_factory=list)

    @model_serializer(mode="wrap")
    def preserve_historical_review(self, serialize):
        value = serialize(self)
        if self.page_body_target is None:
            value.pop("page_body_target", None)
        if self.schema_version == "dmb_build_proposal_review_v2":
            value.pop("placement", None)
            value.pop("retired_placements", None)
        return value

    @model_validator(mode="after")
    def validate_digest(self):
        if self.schema_version == "dmb_build_proposal_review_v2":
            if self.placement is not None or self.retired_placements:
                raise ValueError("Historical review cannot carry fresh placement authority")
        elif (self.placement is None or not self.retired_placements
              or self.placement.basis.world_id != self.world_id
              or any(p.basis.world_id != self.world_id or p.basis.document_id != self.placement.basis.document_id for p in self.retired_placements)
              or len({p.command_id for p in self.retired_placements if p.command_id is not None}) != sum(p.command_id is not None for p in self.retired_placements)
              or any(p.command_id == self.placement.command_id for p in self.retired_placements)):
            raise ValueError("Fresh placement requires its distinct retained predecessors")
        if self.placement and self.apply and (
                self.apply.before_editor_sha256 != self.placement.basis.editor_sha256
                or self.apply.before_draft_sha256 != self.placement.basis.draft_sha256):
            raise ValueError("Apply differs from its fresh placement basis")
        if self.page_body_target is not None and (self.placement is not None or self.retired_placements):
            raise ValueError("Whole-page target cannot gain another placement")
        if self.apply and self.apply.page_body_target != self.page_body_target:
            raise ValueError("Apply differs from resolved whole-page target")
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
    operation: Literal["open", "save", "move", "discard", "prepare", "confirm", "replace_placement"]
    expected_revision: int = Field(strict=True, ge=0)
    placement_caret: int | None = Field(default=None, strict=True, ge=0)
    markdown: str | None = None
    apply_id: UUID | None = None
    after_editor_sha256: str | None = Field(default=None, pattern=r"^[a-f0-9]{64}$")
    after_draft_sha256: str | None = Field(default=None, pattern=r"^[a-f0-9]{64}$")

    placement: PlacementCapability | None = None

    @model_validator(mode="after")
    def exact_fields(self):
        required = {
            "replace_placement": {"placement"},
            "save": {"markdown"},
            "move": {"placement_caret"},
            "prepare": {"apply_id", "after_editor_sha256", "after_draft_sha256"},
            "confirm": {"apply_id"},
        }.get(self.operation, set())
        present = {
            name
            for name in (
                "markdown",
                "placement",
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
    def __init__(self, validate_source=None):
        self.validate_source = validate_source

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
            expected_body = proposal.reservation.page_body_offer if proposal.proposal and proposal.proposal.target == "page_body" else None
            if previous and (previous.reservation_sha256 != proposal.request_fingerprint
                    or previous.page_body_target != expected_body
                    or expected_body is not None and previous.placement_caret != proposal.reservation.basis.caret):
                raise ApplicationStateConflictError("Review differs from immutable target")
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
                    page_body_target=proposal.reservation.page_body_offer if proposal.proposal.target == "page_body" else None,
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
            expected_body = proposal.reservation.page_body_offer if proposal.proposal.target == "page_body" else None
            if previous.page_body_target != expected_body:
                raise ApplicationStateConflictError("Review differs from immutable target")
            if expected_body is not None and command.operation in {"move", "replace_placement"}:
                raise ApplicationStateConflictError("Whole-page revision stays at its captured body. Request a new revision on the changed page.")
            if expected_body is not None and previous.placement_caret != proposal.reservation.basis.caret:
                raise ApplicationStateConflictError("Whole-page editor basis changed")
            if command.operation == "replace_placement":
                if previous.placement and previous.placement.command_id == command.placement.command_id:
                    if previous.placement != command.placement:
                        raise ApplicationStateConflictError("Placement command has different bytes")
                    return previous
                if any(p.command_id == command.placement.command_id for p in previous.retired_placements):
                    raise ApplicationStateConflictError("Placement command was superseded")
            if command.apply_id and any(p.apply and p.apply.apply_id == command.apply_id for p in previous.retired_placements):
                raise ApplicationStateConflictError("Insertion attempt was superseded")
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
            basis = previous.placement.basis if previous.placement else proposal.reservation.basis
            if previous.placement and (basis.world_id != world_id or basis.document_id != proposal.reservation.basis.document_id):
                raise ApplicationStateConflictError("Fresh placement belongs to another page")
            if command.operation == "replace_placement":
                cap = command.placement
                if (previous.state not in {"editing", "applying"} or proposal.inserted_in_draft
                    or cap.basis.world_id != world_id or cap.basis.document_id != proposal.reservation.basis.document_id
                    or cap.conversation_id != pointer.active_conversation_id or cap.conversation_id != proposal.reservation.conversation_id
                    or cap.expected_pointer_revision != pointer.revision):
                    raise ApplicationStateConflictError("Fresh placement scope changed")
                if previous.apply and cap.basis.draft_sha256 in {
                        previous.apply.before_draft_sha256, previous.apply.after_draft_sha256}:
                    raise ApplicationStateConflictError("Reconcile the exact original insertion before choosing a new placement")
                if self.validate_source is None:
                    raise ApplicationStateConflictError("Current source validation is unavailable")
                self.validate_source(cap)
                retired = RetiredPlacement(basis=basis.model_copy(update={"caret":previous.placement_caret}), markdown=previous.markdown,
                    markdown_sha256=previous.markdown_sha256, apply=previous.apply,
                    command_id=previous.placement.command_id if previous.placement else None,
                    disposition="superseded_unresolved" if previous.apply else "superseded_unapplied")
                update.update(schema="dmb_build_proposal_review_v3", placement=cap,
                    retired_placements=[*previous.retired_placements, retired],
                    placement_caret=cap.basis.caret, state="editing", apply=None)
            elif command.operation == "save":
                update.update(
                    markdown=command.markdown, markdown_sha256=digest(command.markdown)
                )
            elif command.operation == "move":
                if basis.selection is not None:
                    raise ApplicationStateConflictError("A revision stays at its captured selection. Select another passage for a new revision.")
                update["placement_caret"] = command.placement_caret
            elif command.operation == "discard":
                update["state"] = "discarded"
            elif command.operation == "prepare":
                if previous.placement:
                    if self.validate_source is None:
                        raise ApplicationStateConflictError("Current source validation is unavailable")
                    self.validate_source(previous.placement)
                if proposal.inserted_in_draft:
                    raise ApplicationStateConflictError("Proposal was already inserted")
                if basis.selection is not None and previous.placement_caret != basis.caret:
                    raise ApplicationStateConflictError("The revision target differs from its captured selection")
                update.update(
                    state="applying",
                    apply=ReviewApply(
                        page_body_target=previous.page_body_target,
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
