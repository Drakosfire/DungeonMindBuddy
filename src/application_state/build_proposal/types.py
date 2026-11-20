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


class BuildProposalSelection(StrictModel):
    """An author-selected text range; never a model-chosen replacement target."""
    end: int = Field(strict=True, ge=1)
    text: str = Field(min_length=1)

    @model_validator(mode="after")
    def require_text(self):
        if not self.text.strip():
            raise ValueError("Select a nonempty text passage to revise")
        return self


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
    selection: BuildProposalSelection | None = None

    @model_validator(mode="after")
    def require_forward_selection(self):
        if self.selection is not None and self.selection.end <= self.caret:
            raise ValueError("Replacement selection must end after its captured start")
        return self


    @model_serializer(mode="wrap")
    def preserve_historical_basis(self, serialize):
        value = serialize(self)
        if self.editor_sha256 is None:
            value.pop("editor_sha256", None)
        if self.selection is None:
            value.pop("selection", None)
        return value


class BuildProposalOrigin(StrictModel):
    client_turn_id: UUID
    durable_turn_id: UUID
    turn_attempt: int = Field(strict=True, ge=1)
    broker_operation_id: str = Field(min_length=1, max_length=256)
    arguments_sha256: str = Field(pattern=r"^[a-f0-9]{64}$")


class BuildPageBodyOffer(StrictModel):
    """Host-frozen body extent; common basis still records the actual selection."""
    end: int = Field(strict=True, ge=1)


class BuildPageEndOffer(StrictModel):
    """Host-frozen append boundary; never a replacement range or a moved caret."""
    end: int = Field(strict=True, ge=1)


class BuildProseTarget(StrictModel):
    """Host-admitted occurrence binding, never a model-provided text offset."""
    model_config = ConfigDict(extra="forbid", frozen=True, populate_by_name=True, serialize_by_alias=True)
    schema_version: Literal["dmb_build_prose_target_v1"] = Field(default="dmb_build_prose_target_v1", alias="schema")
    catalog_sha256: str = Field(pattern=r"^[a-f0-9]{64}$")
    alias: str = Field(min_length=1, max_length=128)
    operation: Literal["replace_paragraph"]
    from_: int = Field(alias="from", strict=True, ge=1)
    to: int = Field(strict=True, ge=2)
    before_text_sha256: str = Field(pattern=r"^[a-f0-9]{64}$")

    @model_validator(mode="after")
    def forward_range(self):
        if self.to <= self.from_:
            raise ValueError("Prose target requires one nonempty forward text extent")
        return self


class BuildProseBoundaryTarget(BuildProseTarget):
    """Host-selected root boundary; digest describes its anchor paragraph."""
    schema_version: Literal["dmb_build_prose_boundary_target_v1"] = Field(default="dmb_build_prose_boundary_target_v1", alias="schema")
    operation: Literal["insert_before", "insert_after"]
    from_: int = Field(alias="from", strict=True, ge=0)
    to: int = Field(strict=True, ge=0)

    @model_validator(mode="after")
    def forward_range(self):
        if self.to != self.from_:
            raise ValueError("Prose boundary requires an exact zero-width position")
        return self


def admit_single_prose_paragraph(markdown: str) -> None:
    # Deliberately narrow isolated proof: one inline Markdown paragraph, not new
    # block authority. The mounted editor separately validates its schema/content.
    content = markdown.strip()
    if (not content or "\n" in content or "\r" in content
            or re.match(r"^\s*(?:#{1,6}\s|[-+*>]\s|[0-9]+[.)]\s|```|~~~|\|)", content)
            or "![" in content):
        raise ValueError("Prose replacement must remain one nonempty paragraph")


class BuildProposalReservation(StrictModel):
    idempotency_key: UUID
    conversation_id: UUID
    expected_pointer_revision: int = Field(strict=True, ge=1)
    basis: BuildProposalBasis
    instruction: str = Field(min_length=1)
    origin: BuildProposalOrigin | None = None
    page_body_offer: BuildPageBodyOffer | None = None
    page_end_offer: BuildPageEndOffer | None = None
    reference_image_id: UUID | None = None
    prose_target: BuildProseTarget | BuildProseBoundaryTarget | None = None

    @model_validator(mode="after")
    def body_requires_exact_editor(self):
        if self.prose_target is not None and (self.basis.selection is not None
                or not self.basis.editor_sha256 or self.page_body_offer is not None
                or self.page_end_offer is not None or self.reference_image_id is not None):
            raise ValueError("Prose nomination requires exact editor basis and no author selection or competing target")
        if self.reference_image_id is not None and (
            self.basis.selection is None or not self.basis.editor_sha256
            or self.page_body_offer is not None or self.page_end_offer is not None
        ):
            raise ValueError("A reference image requires an exact selected passage")
        if (self.page_body_offer is not None or self.page_end_offer is not None) and not self.basis.editor_sha256:
            raise ValueError("Offered page targets require their exact editor basis")
        return self

    @model_serializer(mode="wrap")
    def preserve_historical_reservation(self, serialize):
        value = serialize(self)
        if self.page_body_offer is None:
            value.pop("page_body_offer", None)
        if self.page_end_offer is None:
            value.pop("page_end_offer", None)
        if self.reference_image_id is None:
            value.pop("reference_image_id", None)
        if self.prose_target is None:
            value.pop("prose_target", None)
        return value

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


class BuildWriteCapability(BuildProposalReservation):
    """Browser-captured target; no model chooses insertion authority."""
    instruction: str = ""
    draft_markdown: str

    @model_validator(mode="after")
    def validate_capability(self):
        encoded = self.draft_markdown.encode("utf-8", errors="strict")
        if self.instruction or self.origin is not None:
            raise ValueError("The model instruction and tool origin are parent-owned")
        if sha256(encoded).hexdigest() != self.basis.draft_sha256:
            raise ValueError("Captured draft differs from its digest")
        return self


class BuildGeneratedProposal(StrictModel):
    replacement_markdown: str = Field(min_length=1, max_length=12_000)
    summary: str = Field(min_length=1, max_length=1000)
    assumptions: list[str] = Field(max_length=20)
    target: Literal["captured", "page_body", "page_end"] | None = None

    @model_serializer(mode="wrap")
    def preserve_historical_proposal(self, serialize):
        value = serialize(self)
        if self.target is None:
            value.pop("target", None)
        return value


class BuildProseGeneratedProposal(BuildGeneratedProposal):
    target: Literal["prose_target"]

    @model_validator(mode="after")
    def one_paragraph(self):
        admit_single_prose_paragraph(self.replacement_markdown)
        return self


class BuildProseComposeOutput(BuildProseGeneratedProposal):
    destination: Literal["current_page"]


def normalize_prose_proposal_output(text):
    def unique(pairs):
        value = {}
        for key, item in pairs:
            if key in value:
                raise ValueError("Duplicate prose output field")
            value[key] = item
        return value
    wire = BuildProseComposeOutput.model_validate(json.loads(text, object_pairs_hook=unique))
    # Reuse legacy inert-content checks, without expanding its public writer schema.
    legacy = {**wire.model_dump(), "target": "captured"}
    normalize_proposal_output(json.dumps(legacy))
    return BuildProseGeneratedProposal.model_validate(wire.model_dump(exclude={"destination"}))


class BuildComposeError(ValueError):
    pass


class BuildComposeTargetMismatch(BuildComposeError):
    """Host-owned refusal; its public code never contains provider prose."""


class BuildComposeOutput(BuildGeneratedProposal):
    """New writer output requires an explicit disposition over frozen host targets."""

    replacement_markdown: str = Field(max_length=12_000)
    destination: Literal["current_page", "different_page", "unresolved"]
    target: Literal["captured", "page_body", "page_end", "unavailable"]


def normalize_proposal_output(text, page_body_offer=None, page_end_offer=None):
    def unique(pairs):
        value = {}
        for key, item in pairs:
            if key in value:
                raise BuildComposeError("build_compose_duplicate_output_field")
            value[key] = item
        return value
    wire = BuildComposeOutput.model_validate(json.loads(text, object_pairs_hook=unique))
    if wire.destination != "current_page":
        raise BuildComposeTargetMismatch("build_compose_target_mismatch")
    if wire.target == "unavailable":
        if wire.replacement_markdown:
            raise BuildComposeError("build_compose_unavailable_content")
        raise BuildComposeTargetMismatch("build_compose_target_unavailable")
    if wire.target == "page_body" and page_body_offer is None:
        raise BuildComposeTargetMismatch("build_compose_target_not_offered")
    if wire.target == "page_end" and page_end_offer is None:
        raise BuildComposeTargetMismatch("build_compose_target_not_offered")
    output = BuildGeneratedProposal.model_validate(wire.model_dump(exclude={"destination"}))
    markdown = output.replacement_markdown
    if re.search(r"(?m)^ {0,3}(?:`{3,}|~{3,})dmb-work-plan-v1(?:[ \t]|$)", markdown):
        raise BuildComposeError("build_compose_unsupported_markdown")
    if (re.search(r"<[^>]*>|dmb-node:|graphNodeReference|dmb-playable-element:|\bnode:[a-z0-9_-]+", markdown, re.I)
            or re.search(r"\[[^\]]+\]\((?:file:|\.{1,2}/|/)", markdown, re.I)):
        raise BuildComposeError("build_compose_unsupported_markdown")
    return output


class BuildProviderAuthorization(StrictModel):
    provider_attempt_id: UUID
    provider: Literal["openai"] = "openai"
    model: str = Field(min_length=1, max_length=128)
    api_mode: Literal["responses"] = "responses"
    payload_sha256: str = Field(pattern=r"^[a-f0-9]{64}$")
    # This receipt records the size of an already prepared, digest-checked
    # request. It does not own transport or prompt capture limits.
    payload_utf8_bytes: int = Field(strict=True, gt=0)
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
        nominated = self.reservation.prose_target is not None
        expected_version = ("dmb_build_document_proposal_v3" if isinstance(self.reservation.prose_target, BuildProseBoundaryTarget) else "dmb_build_document_proposal_v2") if nominated else "dmb_build_document_proposal_v1"
        if self.schema_version != expected_version:
            raise ValueError("Prose provenance requires its explicit versioned record")
        if self.proposal and (self.proposal.target == "prose_target") != nominated:
            raise ValueError("Generated proposal target differs from its admitted provenance")
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
        if self.proposal and self.proposal.target is None and (self.reservation.page_body_offer is not None or self.reservation.page_end_offer is not None):
            raise ValueError("An offered target requires an explicit generated target choice")
        if self.proposal and self.proposal.target == "page_body" and self.reservation.page_body_offer is None:
            raise ValueError("Whole-page result requires its frozen offered target")
        if self.proposal and self.proposal.target == "page_end" and self.reservation.page_end_offer is None:
            raise ValueError("Page-end result requires its frozen offered target")
        if self.inserted_in_draft and self.proposal is None:
            raise ValueError(
                "Only a reviewed proposal can be reported inserted in the draft"
            )
        return self


class BuildProseProposalRecord(BuildProposalRecord):
    """Explicit proof codec; legacy/history readers remain v1-only."""

    schema_version: Literal["dmb_build_document_proposal_v2"] = "dmb_build_document_proposal_v2"
    proposal: BuildProseGeneratedProposal | None = None


class BuildProseBoundaryProposalRecord(BuildProseProposalRecord):
    schema_version: Literal["dmb_build_document_proposal_v3"] = "dmb_build_document_proposal_v3"


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
