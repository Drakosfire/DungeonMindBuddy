"""Typed records and commands for provider-neutral Agent conversations."""

from __future__ import annotations

import hashlib
import json
from datetime import datetime
from typing import Literal
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, model_validator

Resolution = Literal["resolved", "absent", "unresolved", "unavailable"]
ConversationStatus = Literal["active", "archived"]
TurnStatus = Literal["accepted", "running", "completed", "failed", "interrupted"]
CommandKind = Literal["new", "archive", "reopen"]
TurnClaimDisposition = Literal["claimed", "pending", "completed"]


def _fingerprint(value: object) -> str:
    encoded = json.dumps(value, sort_keys=True, separators=(",", ":"), default=str)
    return hashlib.sha256(encoded.encode("utf-8")).hexdigest()


def _fingerprint_compatible_payload(value: object) -> object:
    """Omit only new null provenance fields to keep pre-0012 hashes stable."""
    if isinstance(value, list):
        return [_fingerprint_compatible_payload(item) for item in value]
    if isinstance(value, dict):
        is_provenance = {
            "surface_resolution",
            "primary_work",
            "selected_object",
        }.issubset(value)
        is_reference = {
            "resolution",
            "kind",
            "object_id",
            "revision",
            "content_sha256",
        }.issubset(value)
        return {
            key: _fingerprint_compatible_payload(item)
            for key, item in value.items()
            if not (
                item is None
                and (
                    (key == "surface_instance_id" and is_provenance)
                    or (
                        key in {"object_revision", "work_revision_id", "revision_n"}
                        and is_reference
                    )
                )
            )
        }
    return value


def request_fingerprint(value: BaseModel) -> str:
    """Hash a typed request for idempotency; request JSON is never persisted."""
    payload = value.model_dump(
        mode="json",
        exclude={"command_id", "idempotency_key", "submitted_intent_v1"},
    )
    return _fingerprint(_fingerprint_compatible_payload(payload))


def turn_idempotency_fingerprint(
    world_id: str, user_text: str, provenance: "TurnProvenance"
) -> str:
    """Fingerprint turn meaning, independent of conversation routing and CAS revision."""

    return _fingerprint(
        _fingerprint_compatible_payload(
            {
                "world_id": world_id,
                "user_text": user_text,
                "provenance": provenance.model_dump(mode="json"),
            }
        )
    )


class StrictModel(BaseModel):
    model_config = ConfigDict(extra="forbid", str_strip_whitespace=False)


class HistoricalReference(StrictModel):
    """Historical typed identity; never a current-context or permission grant."""

    resolution: Resolution
    kind: str | None = None
    object_id: str | None = None
    revision: str | None = None
    content_sha256: str | None = Field(default=None, pattern=r"^[0-9a-fA-F]{64}$")
    object_revision: int | None = Field(default=None, strict=True, ge=1)
    work_revision_id: UUID | None = None
    revision_n: int | None = Field(default=None, strict=True, ge=1)

    @model_validator(mode="after")
    def validate_resolution(self) -> "HistoricalReference":
        typed_content_revision = (
            self.object_revision,
            self.work_revision_id,
            self.revision_n,
        )
        has_typed_content_revision = any(
            value is not None for value in typed_content_revision
        )
        if has_typed_content_revision and not all(
            value is not None for value in typed_content_revision
        ):
            raise ValueError(
                "Content object revision, WorkRevision ID, and revision number must be supplied together"
            )
        if has_typed_content_revision and (
            self.resolution != "resolved" or self.content_sha256 is None
        ):
            raise ValueError(
                "typed Content revisions require a resolved reference and full content digest"
            )
        if self.resolution == "resolved":
            if (
                not self.kind
                or not self.kind.strip()
                or not self.object_id
                or not self.object_id.strip()
            ):
                raise ValueError("resolved references require kind and object_id")
        elif self.resolution == "absent" and any(
            value is not None
            for value in (
                self.kind,
                self.object_id,
                self.revision,
                self.content_sha256,
                self.object_revision,
                self.work_revision_id,
                self.revision_n,
            )
        ):
            raise ValueError("absent references cannot carry an object identity")
        if self.kind is not None and not self.kind.strip():
            raise ValueError("reference kind cannot be blank")
        if self.object_id is not None and not self.object_id.strip():
            raise ValueError("reference object_id cannot be blank")
        return self


class TurnProvenance(StrictModel):
    world_id: str
    surface_resolution: Resolution
    surface_id: str | None = None
    surface_instance_id: str | None = None
    primary_work: HistoricalReference
    supporting_work: list[HistoricalReference] = Field(
        default_factory=list, max_length=32
    )
    selected_object: HistoricalReference

    @model_validator(mode="after")
    def validate_provenance(self) -> "TurnProvenance":
        if not self.world_id.strip():
            raise ValueError("world_id is required")
        if self.surface_resolution == "resolved":
            if not self.surface_id or not self.surface_id.strip():
                raise ValueError("resolved surface requires surface_id")
        elif self.surface_resolution == "absent" and self.surface_id is not None:
            raise ValueError("absent surface cannot carry surface_id")
        if self.surface_id is not None and not self.surface_id.strip():
            raise ValueError("surface_id cannot be blank")
        if self.surface_instance_id is not None:
            if not self.surface_instance_id.strip():
                raise ValueError("surface_instance_id cannot be blank")
            if self.surface_resolution != "resolved":
                raise ValueError(
                    "surface instance identity requires a resolved surface"
                )
        if self.surface_resolution == "absent" and self.surface_instance_id is not None:
            raise ValueError("absent surface cannot carry surface_instance_id")
        return self


class SubmittedPrimaryWorkIntentV1(StrictModel):
    kind: Literal["plan", "build", "run", "combat"]
    object_id: str = Field(min_length=1, max_length=128)
    expected_revision: int = Field(strict=True, ge=1)
    expected_revision_n: int | None = Field(default=None, strict=True, ge=1)
    expected_content_sha256: str | None = Field(
        default=None, pattern=r"^[0-9a-f]{64}$"
    )

    @model_validator(mode="after")
    def validate_plan_basis(self) -> "SubmittedPrimaryWorkIntentV1":
        has_revision_n = self.expected_revision_n is not None
        has_digest = self.expected_content_sha256 is not None
        if has_revision_n != has_digest:
            raise ValueError("submitted Plan revision and digest must be supplied together")
        if self.kind != "plan" and (has_revision_n or has_digest):
            raise ValueError("submitted Plan basis is only valid for Plan work")
        return self


class SubmittedGraphFocusIntentV1(StrictModel):
    kind: Literal["none", "session"]
    session_id: str | None = Field(default=None, max_length=128)
    campaign_id: str | None = Field(default=None, max_length=128)

    @model_validator(mode="after")
    def validate_focus(self) -> "SubmittedGraphFocusIntentV1":
        if self.kind == "none" and (
            self.session_id is not None or self.campaign_id is not None
        ):
            raise ValueError("none submitted graph focus cannot carry identities")
        if self.kind == "session" and not self.session_id:
            raise ValueError("session submitted graph focus requires session_id")
        return self


class SubmittedGraphRequestIntentV1(StrictModel):
    mode: Literal["none", "world", "campaign"]
    world_id: str | None = Field(default=None, max_length=128)
    campaign_id: str | None = Field(default=None, max_length=128)
    revision_pin: str | None = Field(default=None, max_length=256)
    focus: SubmittedGraphFocusIntentV1 | None = None

    @model_validator(mode="after")
    def validate_scope(self) -> "SubmittedGraphRequestIntentV1":
        if self.mode == "none" and any(
            value is not None
            for value in (self.world_id, self.campaign_id, self.revision_pin, self.focus)
        ):
            raise ValueError("none submitted graph request cannot carry scope or focus")
        if self.mode == "world" and (not self.world_id or self.focus is None):
            raise ValueError("world submitted graph request requires World and focus")
        if self.mode == "campaign" and (not self.campaign_id or self.focus is None):
            raise ValueError("campaign submitted graph request requires campaign and focus")
        return self


class SubmittedGraphSelectionIntentV1(StrictModel):
    node_id: str = Field(min_length=1, max_length=256)


class SubmittedTurnIntentV1(StrictModel):
    """Stable, normalized caller intent; excludes resolver output and routing CAS."""

    schema_: Literal["dmb_agent_submitted_turn_intent_v1"] = Field(
        default="dmb_agent_submitted_turn_intent_v1", alias="schema"
    )
    world_id: str = Field(min_length=1, max_length=128)
    client_thread_id: str = Field(min_length=1, max_length=128)
    message: str = Field(min_length=1, max_length=8000)
    surface_id: str = Field(min_length=1, max_length=64)
    surface_instance_id: str = Field(min_length=1, max_length=128)
    client_work_state: Literal["none", "saved_clean", "saved_dirty", "new_unsaved"]
    primary_work: SubmittedPrimaryWorkIntentV1 | None
    graph_request: SubmittedGraphRequestIntentV1
    graph_selection: SubmittedGraphSelectionIntentV1 | None

    @model_validator(mode="after")
    def validate_identity(self) -> "SubmittedTurnIntentV1":
        if not self.world_id.strip() or not self.client_thread_id.strip() or not self.message.strip():
            raise ValueError("submitted World, client thread, and message must be non-blank")
        if not self.surface_id.strip() or not self.surface_instance_id.strip():
            raise ValueError("submitted surface identities must be non-blank")
        if (
            self.surface_id == "plan"
            and self.primary_work is not None
            and self.primary_work.kind == "plan"
            and self.primary_work.expected_revision_n is None
        ):
            raise ValueError("Plan content turns require the exact committed content pin")
        if (
            self.graph_request.mode == "world"
            and self.graph_request.world_id != self.world_id
        ):
            raise ValueError("submitted graph World must match submitted turn World")
        if self.graph_selection is not None and self.graph_request.mode == "none":
            raise ValueError("submitted graph selection requires a graph request")
        return self


def submitted_turn_intent_fingerprint_v1(intent: SubmittedTurnIntentV1) -> str:
    """Hash canonical submitted semantics, never current resolver output."""
    return _fingerprint(
        intent.model_dump(
            mode="json", by_alias=True, exclude={"client_thread_id"}
        )
    )


class WorldPointer(StrictModel):
    world_id: str
    active_conversation_id: UUID | None
    revision: int = Field(ge=0)


class Conversation(StrictModel):
    conversation_id: UUID
    world_id: str
    status: ConversationStatus
    revision: int = Field(ge=1)
    next_turn_sequence: int = Field(ge=1)
    created_at: datetime
    updated_at: datetime
    archived_at: datetime | None


class ConversationCommand(StrictModel):
    world_id: str
    command_id: UUID
    expected_pointer_revision: int = Field(ge=0)
    expected_active_conversation_id: UUID | None

    @model_validator(mode="after")
    def validate_world(self) -> "ConversationCommand":
        if not self.world_id.strip():
            raise ValueError("world_id is required")
        return self


class ArchiveCommand(ConversationCommand):
    conversation_id: UUID


class ReopenCommand(ConversationCommand):
    conversation_id: UUID


class ConversationCommandReceipt(StrictModel):
    world_id: str
    command_id: UUID
    command_kind: CommandKind
    conversation_id: UUID
    active_conversation_id: UUID | None
    pointer_revision: int = Field(ge=0)
    recorded_at: datetime


class TurnSubmission(StrictModel):
    world_id: str
    conversation_id: UUID
    idempotency_key: UUID
    expected_conversation_revision: int = Field(ge=1)
    user_text: str
    provenance: TurnProvenance
    submitted_intent_v1: SubmittedTurnIntentV1 | None = None

    @model_validator(mode="after")
    def validate_submission(self) -> "TurnSubmission":
        if not self.world_id.strip():
            raise ValueError("world_id is required")
        if not self.user_text.strip():
            raise ValueError("user_text is required")
        if self.provenance.world_id != self.world_id:
            raise ValueError("turn provenance World does not match request World")
        if self.submitted_intent_v1 is not None and (
            self.submitted_intent_v1.world_id != self.world_id
            or self.submitted_intent_v1.message != self.user_text
        ):
            raise ValueError("submitted intent World/message must match the turn")
        return self


class Turn(StrictModel):
    turn_id: UUID
    conversation_id: UUID
    world_id: str
    idempotency_key: UUID
    sequence: int = Field(ge=1)
    revision: int = Field(ge=1)
    status: TurnStatus
    user_text: str
    assistant_text: str | None
    failure_code: str | None
    provenance: TurnProvenance
    submitted_intent_fingerprint_v1: str | None = Field(
        default=None, pattern=r"^[0-9a-f]{64}$"
    )
    attempt: int = Field(ge=0)
    claim_expires_at: datetime | None = None
    accepted_at: datetime
    completed_at: datetime | None
    updated_at: datetime

    @model_validator(mode="after")
    def validate_claim_expiry(self) -> "Turn":
        if self.status != "running" and self.claim_expires_at is not None:
            raise ValueError("only a running turn can carry an active claim expiry")
        return self


class TurnResult(StrictModel):
    world_id: str
    conversation_id: UUID
    turn_id: UUID
    expected_revision: int = Field(ge=1)
    assistant_text: str

    @model_validator(mode="after")
    def validate_text(self) -> "TurnResult":
        if not self.assistant_text.strip():
            raise ValueError("assistant_text is required")
        return self


class TurnFailure(StrictModel):
    world_id: str
    conversation_id: UUID
    turn_id: UUID
    expected_revision: int = Field(ge=1)
    failure_code: str

    @model_validator(mode="after")
    def validate_code(self) -> "TurnFailure":
        if not self.failure_code.strip():
            raise ValueError("failure_code is required")
        return self


class TurnClaimReceipt(StrictModel):
    disposition: TurnClaimDisposition
    turn: Turn


class DraftSave(StrictModel):
    world_id: str
    conversation_id: UUID
    draft_id: UUID
    expected_revision: int = Field(ge=0)
    body: str
    provenance: TurnProvenance
    explicitly_revalidated_source: bool = False

    @model_validator(mode="after")
    def validate_draft(self) -> "DraftSave":
        if not self.world_id.strip():
            raise ValueError("world_id is required")
        if self.provenance.world_id != self.world_id:
            raise ValueError("draft provenance World does not match request World")
        return self


class Draft(StrictModel):
    world_id: str
    conversation_id: UUID
    draft_id: UUID
    revision: int = Field(ge=1)
    body: str
    provenance: TurnProvenance
    retired_at: datetime | None
    created_at: datetime
    updated_at: datetime


class DraftSubmit(StrictModel):
    world_id: str
    conversation_id: UUID
    draft_id: UUID
    expected_draft_revision: int = Field(ge=1)
    idempotency_key: UUID
    expected_conversation_revision: int = Field(ge=1)
    provenance: TurnProvenance

    @model_validator(mode="after")
    def validate_submit(self) -> "DraftSubmit":
        if not self.world_id.strip():
            raise ValueError("world_id is required")
        if self.provenance.world_id != self.world_id:
            raise ValueError("submission provenance World does not match request World")
        return self


class DraftSubmitReceipt(StrictModel):
    turn: Turn
    draft_id: UUID
    retired_draft_revision: int = Field(ge=1)
    retired_at: datetime


class LegacyTurn(StrictModel):
    source_turn_id: str
    world_id: str
    user_text: str
    assistant_text: str | None
    provenance: TurnProvenance

    @model_validator(mode="after")
    def validate_legacy_turn(self) -> "LegacyTurn":
        if not self.source_turn_id.strip():
            raise ValueError("source_turn_id is required")
        if not self.world_id.strip() or self.provenance.world_id != self.world_id:
            raise ValueError("legacy turn must carry the exact verified World ID")
        if not self.user_text.strip():
            raise ValueError("legacy user_text is required")
        return self


class LegacyImport(StrictModel):
    world_id: str
    source_import_key: str
    source_thread_id: str
    expected_pointer_revision: int = Field(ge=0)
    expected_active_conversation_id: UUID | None
    activate: bool
    turns: list[LegacyTurn] = Field(min_length=1, max_length=20)

    @model_validator(mode="after")
    def validate_import(self) -> "LegacyImport":
        if not self.world_id.strip():
            raise ValueError("world_id is required")
        if not self.source_import_key.strip() or not self.source_thread_id.strip():
            raise ValueError("source import key and thread ID are required")
        if any(turn.world_id != self.world_id for turn in self.turns):
            raise ValueError(
                "every legacy turn must exactly match the verified World ID"
            )
        return self


class LegacyImportReceipt(StrictModel):
    world_id: str
    source_import_key: str
    conversation_id: UUID
    active_conversation_id: UUID | None
    pointer_revision: int
    imported_turn_count: int
    recorded_at: datetime
