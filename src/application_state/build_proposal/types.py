"""Genuine saved Build proposal basis; no Plan revision or Graph authority."""

from __future__ import annotations

import re

from datetime import datetime
from hashlib import sha256
import json
from typing import Literal
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, model_validator, model_serializer

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
    # Old reservations are readable, but do not gain original-position authority.
    editor_sha256: str | None = Field(default=None, pattern=r"^[a-f0-9]{64}$")
    caret: int = Field(strict=True, ge=0, le=1_000_000)
    draft_generation: int = Field(strict=True, ge=0)
    selection_generation: int = Field(strict=True, ge=0)


    @model_serializer(mode="wrap")
    def preserve_historical_basis(self, serialize):
        value = serialize(self)
        if self.editor_sha256 is None:
            value.pop("editor_sha256", None)
        return value


class BuildProposalOrigin(StrictModel):
    client_turn_id: UUID
    durable_turn_id: UUID
    turn_attempt: int = Field(strict=True, ge=1)
    broker_operation_id: str = Field(min_length=1, max_length=256)
    arguments_sha256: str = Field(pattern=r"^[a-f0-9]{64}$")


class BuildProposalReservation(StrictModel):
    idempotency_key: UUID
    conversation_id: UUID
    expected_pointer_revision: int = Field(strict=True, ge=1)
    basis: BuildProposalBasis
    instruction: str = Field(min_length=1)
    origin: BuildProposalOrigin | None = None

    @property
    def fingerprint(self) -> str:
        return sha256(
            json.dumps(
                self.model_dump(mode="json", exclude_none=True),
                ensure_ascii=False,
                sort_keys=True,
                separators=(",", ":"),
            ).encode()
        ).hexdigest()


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
    schema_version: Literal["dmb_build_document_proposal_v1"] = (
        "dmb_build_document_proposal_v1"
    )
    action_id: UUID
    reservation: BuildProposalReservation
    request_fingerprint: str = Field(pattern=r"^[a-f0-9]{64}$")
    after_turn_sequence: int = Field(strict=True, ge=0)
    revision: int = Field(strict=True, ge=1)
    state: Literal[
        "reserved",
        "authorized",
        "sdk_entered",
        "response_received",
        "proposed",
        "failed",
        "unknown",
    ]
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
            raise ValueError(
                "Build proposal fingerprint differs from its frozen reservation"
            )
        if (
            self.state
            in {"authorized", "sdk_entered", "response_received", "proposed", "unknown"}
            and self.authorization is None
        ):
            raise ValueError("Build provider lifecycle requires durable authorization")
        if (self.state == "proposed") != (self.proposal is not None):
            raise ValueError(
                "Only a completed Build proposal carries generated Markdown"
            )
        if self.inserted_in_draft and self.proposal is None:
            raise ValueError(
                "Only a reviewed proposal can be reported inserted in the draft"
            )
        return self


class BuildImageWriterProof(StrictModel):
    authorization: BuildProviderAuthorization
    request_json: str = Field(min_length=1, max_length=262144)
    raw_response: str = Field(min_length=1, max_length=32000)


class BuildImagePreparation(StrictModel):
    """Inert image direction, not a Markdown/prose provider result."""

    schema_version: Literal["dmb_build_image_preparation_v2"] = (
        "dmb_build_image_preparation_v2"
    )
    action_id: UUID
    reservation: BuildProposalReservation
    request_fingerprint: str = Field(pattern=r"^[a-f0-9]{64}$")
    owner_id: str = Field(min_length=1)
    revision: int = Field(strict=True, ge=1)
    state: Literal["prepared"] = "prepared"
    after_turn_sequence: int = Field(strict=True, ge=0)
    created_at: datetime
    updated_at: datetime
    prompt: str = Field(min_length=1, max_length=16000)
    alt: str = Field(min_length=1, max_length=500)
    purpose: Literal["illustration", "map"] | None = None
    asset_id: UUID | None = None
    writer_proof: BuildImageWriterProof | None = None

    @model_validator(mode="after")
    def validate_binding(self):
        if (
            self.action_id != self.reservation.idempotency_key
            or self.request_fingerprint != self.reservation.fingerprint
        ):
            raise ValueError("Image preparation differs from its captured reservation")
        if (
            not self.prompt.strip()
            or not self.alt.strip()
            or "\n" in self.alt
            or "\r" in self.alt
        ):
            raise ValueError("Image prompt and single-line alt text are required")
        if self.reservation.origin is None:
            raise ValueError("Image preparation requires its Harness origin")
        return self


class ImageDirection(StrictModel):
    prompt: str = Field(min_length=1, max_length=16000)
    alt: str = Field(min_length=1, max_length=500)

    @model_validator(mode="after")
    def validate_inert(self):
        if (
            not self.prompt.strip()
            or not self.alt.strip()
            or "\n" in self.alt
            or "\r" in self.alt
            or re.search(
                r"https?://|dmb-(?:media|node):|<\s*/?\w+[^>]*>",
                self.prompt + self.alt,
                re.I,
            )
        ):
            raise ValueError(
                "Image direction must be inert prompt and single-line alt text"
            )
        return self


class ImageDirectionV2(ImageDirection):
    """Explicit purpose for new writers; legacy prompt/alt proof remains valid."""

    purpose: Literal["illustration", "map"]
