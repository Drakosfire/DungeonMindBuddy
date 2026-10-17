"""Genuine saved Build proposal basis; no Plan revision or Graph authority."""
from __future__ import annotations

from datetime import datetime
from hashlib import sha256
import json
from typing import Literal
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, model_validator

Digest = str


class StrictModel(BaseModel):
    model_config = ConfigDict(extra="forbid")


class BuildProposalBasis(StrictModel):
    world_id: str = Field(min_length=1, max_length=128)
    document_id: str = Field(min_length=1, max_length=128)
    registry_revision: int = Field(strict=True, ge=1)
    content_sha256: str = Field(pattern=r"^[a-f0-9]{64}$")
    visibility: Literal["internal", "player_safe"]
    draft_sha256: str = Field(pattern=r"^[a-f0-9]{64}$")
    caret: int = Field(strict=True, ge=0, le=1_000_000)
    draft_generation: int = Field(strict=True, ge=0)
    selection_generation: int = Field(strict=True, ge=0)


class BuildProposalReservation(StrictModel):
    idempotency_key: UUID
    conversation_id: UUID
    expected_pointer_revision: int = Field(strict=True, ge=1)
    basis: BuildProposalBasis
    instruction: str = Field(min_length=1, max_length=4000)

    @property
    def fingerprint(self) -> str:
        return sha256(json.dumps(self.model_dump(mode="json"), ensure_ascii=False,
            sort_keys=True, separators=(",", ":")).encode()).hexdigest()


class BuildGeneratedProposal(StrictModel):
    replacement_markdown: str = Field(min_length=1, max_length=12_000)
    summary: str = Field(min_length=1, max_length=1000)
    assumptions: list[str] = Field(max_length=20)


class BuildProviderAuthorization(StrictModel):
    provider_attempt_id: UUID
    provider: Literal["openai"] = "openai"
    model: str = Field(min_length=1, max_length=128)
    api_mode: Literal["responses"] = "responses"
    payload_sha256: str = Field(pattern=r"^[a-f0-9]{64}$")
    payload_utf8_bytes: int = Field(strict=True, gt=0, le=262144)
    evidence_id: UUID | None = None
    serializer_version: Literal["openai-sdk-json-v1"] = "openai-sdk-json-v1"


class BuildProposalRecord(StrictModel):
    schema_version: Literal["dmb_build_document_proposal_v1"] = "dmb_build_document_proposal_v1"
    action_id: UUID
    reservation: BuildProposalReservation
    request_fingerprint: str = Field(pattern=r"^[a-f0-9]{64}$")
    after_turn_sequence: int = Field(strict=True, ge=0)
    revision: int = Field(strict=True, ge=1)
    state: Literal["reserved", "authorized", "sdk_entered", "response_received", "proposed", "failed", "unknown"]
    created_at: datetime
    updated_at: datetime
    claim_expires_at: datetime
    authorization: BuildProviderAuthorization | None = None
    proposal: BuildGeneratedProposal | None = None
    failure_code: str | None = Field(default=None, pattern=r"^[a-z][a-z0-9_]{0,63}$")
    raw_response: str | None = Field(default=None, max_length=32_000)
    observation: dict | None = None
    inserted_in_draft: bool = False

    @model_validator(mode="after")
    def validate_receipt(self):
        if self.request_fingerprint != self.reservation.fingerprint:
            raise ValueError("Build proposal fingerprint differs from its frozen reservation")
        if self.state in {"authorized", "sdk_entered", "response_received", "proposed", "unknown"} and self.authorization is None:
            raise ValueError("Build provider lifecycle requires durable authorization")
        if (self.state == "proposed") != (self.proposal is not None):
            raise ValueError("Only a completed Build proposal carries generated Markdown")
        if self.inserted_in_draft and self.proposal is None:
            raise ValueError("Only a reviewed proposal can be reported inserted in the draft")
        return self
