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


def _fingerprint(value: object) -> str:
    encoded = json.dumps(value, sort_keys=True, separators=(",", ":"), default=str)
    return hashlib.sha256(encoded.encode("utf-8")).hexdigest()


def request_fingerprint(value: BaseModel) -> str:
    """Hash a typed request for idempotency; request JSON is never persisted."""

    return _fingerprint(value.model_dump(mode="json", exclude={"command_id", "idempotency_key"}))


def turn_idempotency_fingerprint(
    world_id: str, user_text: str, provenance: "TurnProvenance"
) -> str:
    """Fingerprint turn meaning, independent of conversation routing and CAS revision."""

    return _fingerprint(
        {
            "world_id": world_id,
            "user_text": user_text,
            "provenance": provenance.model_dump(mode="json"),
        }
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

    @model_validator(mode="after")
    def validate_resolution(self) -> "HistoricalReference":
        if self.resolution == "resolved":
            if not self.kind or not self.kind.strip() or not self.object_id or not self.object_id.strip():
                raise ValueError("resolved references require kind and object_id")
        elif self.resolution == "absent" and any(
            value is not None
            for value in (self.kind, self.object_id, self.revision, self.content_sha256)
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
    primary_work: HistoricalReference
    supporting_work: list[HistoricalReference] = Field(default_factory=list, max_length=32)
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
        return self


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

    @model_validator(mode="after")
    def validate_submission(self) -> "TurnSubmission":
        if not self.world_id.strip():
            raise ValueError("world_id is required")
        if not self.user_text.strip():
            raise ValueError("user_text is required")
        if self.provenance.world_id != self.world_id:
            raise ValueError("turn provenance World does not match request World")
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
    attempt: int = Field(ge=0)
    accepted_at: datetime
    completed_at: datetime | None
    updated_at: datetime


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
            raise ValueError("every legacy turn must exactly match the verified World ID")
        return self


class LegacyImportReceipt(StrictModel):
    world_id: str
    source_import_key: str
    conversation_id: UUID
    active_conversation_id: UUID | None
    pointer_revision: int
    imported_turn_count: int
    recorded_at: datetime
