"""Typed Plan action records, reservations, and allowlisted projections."""

from __future__ import annotations

import hashlib
import json
from datetime import datetime
from typing import Literal
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field

ActionStatus = Literal["pending", "completed", "failed", "indeterminate"]
ActionType = Literal["compose", "revise"]
TargetKind = Literal["replace_selection", "insert_at_caret"]


class StrictModel(BaseModel):
    model_config = ConfigDict(extra="forbid", str_strip_whitespace=False)


class PlanActionBasis(StrictModel):
    world_id: str = Field(min_length=1, max_length=128)
    document_id: str = Field(min_length=1, max_length=128)
    object_revision: int = Field(strict=True, ge=1)
    work_revision_id: UUID
    revision_n: int = Field(strict=True, ge=1)
    content_sha256: str = Field(pattern=r"^[0-9a-f]{64}$")


class PlanActionReservation(StrictModel):
    idempotency_key: UUID
    request_fingerprint: str = Field(pattern=r"^[0-9a-f]{64}$")
    action_type: ActionType
    basis: PlanActionBasis
    draft_matches_basis: bool
    draft_sha256: str = Field(pattern=r"^[0-9a-f]{64}$")
    target_kind: TargetKind
    selected_text_sha256: str | None = Field(default=None, pattern=r"^[0-9a-f]{64}$")
    instruction: str = Field(min_length=1, max_length=4000)


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
