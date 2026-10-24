"""Authored working-copy identity; never a saved-source or World evidence receipt.

The browser owns the editor snapshot. APP can prove that its Markdown and identity
match the accepted turn, not that unsaved text was independently authored or saved.
"""
from __future__ import annotations

from hashlib import sha256
import json
from typing import Literal
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, model_validator

POLICY = "captured_build_working_draft_context_v1"
ROLE = "authored_working_draft_not_world_or_played_truth"


def digest(value) -> str:
    return sha256(json.dumps(value, ensure_ascii=False, sort_keys=True,
        separators=(",", ":"), allow_nan=False).encode()).hexdigest()


class _Frozen(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True, populate_by_name=True)


class BuildDraftSnapshotV1(_Frozen):
    schema_: Literal["dmb_build_draft_snapshot_v1"] = Field(
        default="dmb_build_draft_snapshot_v1", alias="schema")
    world_id: str = Field(min_length=1)
    document_id: str = Field(min_length=1)
    registry_revision: int = Field(strict=True, ge=1)
    content_sha256: str = Field(pattern=r"^[a-f0-9]{64}$")
    visibility: Literal["internal", "player_safe"]
    draft_markdown: str
    draft_sha256: str = Field(pattern=r"^[a-f0-9]{64}$")
    editor_sha256: str = Field(pattern=r"^[a-f0-9]{64}$")
    draft_generation: int = Field(strict=True, ge=0)

    @model_validator(mode="after")
    def exact_markdown(self):
        if sha256(self.draft_markdown.encode("utf-8", errors="strict")).hexdigest() != self.draft_sha256:
            raise ValueError("Working draft differs from its captured Markdown digest")
        return self

    def saved_basis(self) -> dict:
        return {key: getattr(self, key) for key in (
            "world_id", "document_id", "registry_revision", "content_sha256", "visibility")}

    @property
    def snapshot_sha256(self) -> str:
        return digest(self.model_dump(mode="json", by_alias=True))

    def reference(self) -> dict:
        """Routing identity deliberately omits the page body and write authority."""
        return {"policy": POLICY, "snapshot_sha256": self.snapshot_sha256,
            "document_id": self.document_id, "draft_sha256": self.draft_sha256}


class BuildDraftContextRequestV1(_Frozen):
    snapshot: BuildDraftSnapshotV1
    conversation_id: UUID
    expected_pointer_revision: int = Field(strict=True, ge=0)


class BuildDraftContextRecordV1(_Frozen):
    schema_: Literal["dmb_build_draft_context_record_v1"] = Field(
        default="dmb_build_draft_context_record_v1", alias="schema")
    record_id: UUID
    turn_id: UUID
    conversation_id: UUID
    attempt: int = Field(strict=True, ge=1)
    request_fingerprint: str = Field(pattern=r"^[a-f0-9]{64}$")
    role: Literal["authored_working_draft_not_world_or_played_truth"] = ROLE
    snapshot: BuildDraftSnapshotV1


def validate_record(record: BuildDraftContextRecordV1, turn) -> None:
    """Reconstruct the accepted identity at APP's owning boundary, without IO."""
    execution = turn.graph_context_execution
    receipt = turn.graph_context_receipt
    if (execution is None or receipt is None
        or getattr(execution.policy, "working_draft_context_policy", None) != POLICY
        or getattr(execution.policy, "working_draft_snapshot_sha256", None) != record.snapshot.snapshot_sha256):
        raise ValueError("Working draft lacks its frozen context capability")
    if (record.turn_id != turn.turn_id or record.conversation_id != turn.conversation_id
        or record.attempt != turn.attempt or record.request_fingerprint != turn.request_fingerprint
        or record.snapshot.world_id != turn.world_id
        or record.snapshot.saved_basis() != receipt.source_basis.model_dump(mode="json", by_alias=True)):
        raise ValueError("Working draft differs from its accepted turn and saved basis")


def writer_reference(record: BuildDraftContextRecordV1) -> dict:
    """One complete body, separate from cited sources and historical dialogue."""
    return {"policy": POLICY, "role": ROLE, "record_id": str(record.record_id),
        "snapshot_sha256": record.snapshot.snapshot_sha256,
        "draft_markdown": record.snapshot.draft_markdown}


def validate_writer_reference(value, record: BuildDraftContextRecordV1, turn) -> None:
    validate_record(record, turn)
    if value != writer_reference(record):
        raise ValueError("Writer working draft differs from its included context record")
