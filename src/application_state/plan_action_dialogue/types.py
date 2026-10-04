"""Typed Plan action records, reservations, and allowlisted projections."""

from __future__ import annotations

import hashlib
import json
from datetime import datetime
from typing import Literal
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, model_validator

ActionStatus = Literal["pending", "completed", "failed", "indeterminate"]
ActionType = Literal["compose", "revise"]
TargetKind = Literal["replace_selection", "insert_at_caret", "replace_playable_body"]


class StrictModel(BaseModel):
    model_config = ConfigDict(extra="forbid", str_strip_whitespace=False)


class PlanActionBasis(StrictModel):
    world_id: str = Field(min_length=1, max_length=128)
    document_id: str = Field(min_length=1, max_length=128)
    object_revision: int = Field(strict=True, ge=1)
    work_revision_id: UUID
    revision_n: int = Field(strict=True, ge=1)
    content_sha256: str = Field(pattern=r"^[0-9a-f]{64}$")


class PlanActionPlayableTargetReceipt(StrictModel):
    schema_version: Literal["dmb_plan_playable_target_receipt_v1"]
    kind: Literal["scene", "beat", "choice", "option"]
    id: str = Field(pattern=r"^(scene|beat|choice|option):[a-z0-9][a-z0-9._-]{0,127}$")
    marker_grammar_version: Literal["v1", "v2"]
    body_scope: Literal["heading_body", "beat_direct_body", "option_item_content"]
    range_semantics_version: Literal["plan-playable-ranges-v1"]
    body_serialization_version: Literal["plan-playable-body-markdown-v1"]
    target_body_sha256: str = Field(pattern=r"^[0-9a-f]{64}$")

    @model_validator(mode="after")
    def validate_typed_scope(self):
        if self.id.split(":", 1)[0] != self.kind:
            raise ValueError("Playable target receipt kind must match its ID prefix")
        if self.marker_grammar_version == "v1":
            valid_scope = self.body_scope == "heading_body"
        elif self.kind == "option":
            valid_scope = self.body_scope == "option_item_content"
        elif self.kind == "beat":
            valid_scope = self.body_scope == "beat_direct_body"
        else:
            valid_scope = self.body_scope == "heading_body"
        if not valid_scope:
            raise ValueError("Playable target receipt scope does not match its grammar and kind")
        return self


class PlanActionReservation(StrictModel):
    idempotency_key: UUID
    request_fingerprint: str = Field(pattern=r"^[0-9a-f]{64}$")
    action_type: ActionType
    basis: PlanActionBasis
    draft_matches_basis: bool
    draft_sha256: str = Field(pattern=r"^[0-9a-f]{64}$")
    target_kind: TargetKind
    selected_text_sha256: str | None = Field(default=None, pattern=r"^[0-9a-f]{64}$")
    playable_target_receipt: PlanActionPlayableTargetReceipt | None = None
    instruction: str = Field(min_length=1, max_length=4000)

    @model_validator(mode="after")
    def validate_target_witness(self):
        if self.target_kind == "replace_playable_body":
            if self.action_type != "revise" or self.selected_text_sha256 is not None or self.playable_target_receipt is None:
                raise ValueError("Playable body actions require a revise action and one typed target receipt")
        elif self.playable_target_receipt is not None:
            raise ValueError("Only Playable body actions may carry a typed target receipt")
        elif self.target_kind == "replace_selection" and self.selected_text_sha256 is None:
            raise ValueError("replace_selection requires a selected-text digest")
        elif self.target_kind == "insert_at_caret" and self.selected_text_sha256 is not None:
            raise ValueError("insert_at_caret cannot carry a selected-text digest")
        return self


class PlanActionRecord(StrictModel):
    action_id: UUID
    idempotency_key: UUID
    request_fingerprint: str
    action_type: ActionType
    basis: PlanActionBasis
    draft_matches_basis: bool
    draft_sha256: str
    target_kind: TargetKind
    selected_text_sha256: str | None
    playable_target_receipt: PlanActionPlayableTargetReceipt | None
    instruction: str
    status: ActionStatus
    assistant_summary: str | None
    failure_code: str | None
    dispatch_token: UUID | None
    fence: int
    action_sequence: int
    accepted_at: datetime
    completed_at: datetime | None
    lease_expires_at: datetime | None


class PlanActionProjection(StrictModel):
    action_id: UUID
    action_type: ActionType
    status: ActionStatus
    basis: PlanActionBasis
    instruction: str
    assistant_summary: str | None
    action_sequence: int
    accepted_at: datetime
    completed_at: datetime | None
    playable_target_receipt: PlanActionPlayableTargetReceipt | None


class PlanActionProjectionPage(StrictModel):
    schema_version: Literal["dmb_world_plan_action_projection_v1"] = (
        "dmb_world_plan_action_projection_v1"
    )
    basis: PlanActionBasis
    actions: list[PlanActionProjection] = Field(max_length=50)


class CompletedPlanActionContext(StrictModel):
    action_id: UUID
    action_type: ActionType
    basis: PlanActionBasis
    instruction: str
    assistant_summary: str = Field(min_length=1)
    action_sequence: int
    accepted_at: datetime


def request_fingerprint(payload: object) -> str:
    encoded = json.dumps(payload, ensure_ascii=False, sort_keys=True, separators=(",", ":"))
    return hashlib.sha256(encoded.encode("utf-8")).hexdigest()
