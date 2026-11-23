"""Genuine saved Build proposal basis; no Plan revision or Graph authority."""

from __future__ import annotations

import re

from datetime import datetime
from hashlib import sha256
import json
from typing import Literal
from uuid import UUID

from markdown_it import MarkdownIt
from pydantic import BaseModel, ConfigDict, Field, model_validator, model_serializer

from .boundary_markdown import split_boundary_callout

Digest = str
BuildImageMoveDisposition = Literal[
    "ready", "discussion", "ambiguous", "missing", "different_row",
    "unsupported", "unresolved", "occupied", "unavailable", "changes_reading_order",
]


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


class BuildProseBoundaryTarget(StrictModel):
    """An offered host boundary, independent of the actual author caret."""

    model_config = ConfigDict(extra="forbid", frozen=True, populate_by_name=True, serialize_by_alias=True)
    schema_version: Literal["dmb_build_prose_boundary_target_v1"] = Field(
        default="dmb_build_prose_boundary_target_v1", alias="schema",
    )
    catalog_sha256: str = Field(pattern=r"^[a-f0-9]{64}$")
    alias: str = Field(pattern=r"^passage[1-9][0-9]*:insert_(?:before|after)$", max_length=128)
    operation: Literal["insert_before", "insert_after"]
    from_: int = Field(alias="from", strict=True, ge=0)
    to: int = Field(strict=True, ge=0)
    before_text_sha256: str = Field(pattern=r"^[a-f0-9]{64}$")

    @model_validator(mode="after")
    def exact_boundary(self):
        if self.from_ != self.to or not self.alias.endswith(f":{self.operation}"):
            raise ValueError("Build prose target requires one exact offered boundary")
        return self


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

    @model_validator(mode="after")
    def body_requires_exact_editor(self):
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


class BuildBoundaryResolution(StrictModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    disposition: Literal["unique", "ambiguous", "missing", "unresolved", "discuss",
                         "different_destination", "explicit_page_end", "explicit_page_body"]
    target: BuildProseBoundaryTarget | None = None

    @model_validator(mode="after")
    def exact_target(self):
        if (self.disposition == "unique") != (self.target is not None):
            raise ValueError("Only one resolved Build boundary carries placement authority")
        return self


class BuildProseBoundaryReservation(BuildProposalReservation):
    prose_target: BuildProseBoundaryTarget

    @model_validator(mode="after")
    def exact_editor_without_other_authority(self):
        if (not self.basis.editor_sha256 or self.basis.selection is not None
                or self.page_body_offer is not None or self.page_end_offer is not None
                or self.reference_image_id is not None):
            raise ValueError("Build prose nomination requires its exact editor without a competing target")
        return self


class BuildWriteCapability(BuildProposalReservation):
    """Browser-captured target; no model chooses insertion authority."""
    instruction: str = ""
    draft_markdown: str
    boundary_editor_json: str | None = Field(default=None, exclude_if=lambda value: value is None)

    @model_validator(mode="after")
    def validate_capability(self):
        encoded = self.draft_markdown.encode("utf-8", errors="strict")
        if self.instruction or self.origin is not None:
            raise ValueError("The model instruction and tool origin are parent-owned")
        if sha256(encoded).hexdigest() != self.basis.draft_sha256:
            raise ValueError("Captured draft differs from its digest")
        if self.boundary_editor_json is not None:
            if self.reference_image_id is not None or self.basis.selection is not None:
                raise ValueError("A Build prose offer cannot replace an authored selection or image target")
            from .prose_catalog import freeze_build_prose_catalog

            catalog = freeze_build_prose_catalog(self.basis, self.boundary_editor_json, self.draft_markdown)
            if any(offer is not None and offer.end != catalog.editor_size
                   for offer in (self.page_body_offer, self.page_end_offer)):
                raise ValueError("Build page-wide offer differs from the exact editor extent")
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


class BuildComposeError(ValueError):
    pass


class BuildComposeTargetMismatch(BuildComposeError):
    """Host-owned refusal; its public code never contains provider prose."""


class BuildComposeOutput(BuildGeneratedProposal):
    """New writer output requires an explicit disposition over frozen host targets."""

    replacement_markdown: str = Field(max_length=12_000)
    destination: Literal["current_page", "different_page", "unresolved"]
    target: Literal["captured", "page_body", "page_end", "unavailable"]


def explicit_build_page_target(capability, selection) -> Literal["page_end", "page_body"] | None:
    placement = getattr(selection, "paragraph_placement", None)
    if capability is None or placement is None or selection.operation != "propose_build_insertion":
        return None
    if placement.disposition == "explicit_page_end" and capability.page_end_offer is not None:
        return "page_end"
    if placement.disposition == "explicit_page_body" and capability.page_body_offer is not None:
        return "page_body"
    return None


def normalize_proposal_output(text, page_body_offer=None, page_end_offer=None, *, required_target=None):
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
    if required_target is not None and wire.target != required_target:
        raise BuildComposeTargetMismatch("build_compose_target_mismatch")
    output = BuildGeneratedProposal.model_validate(wire.model_dump(exclude={"destination"}))
    _require_inert_markdown(output.replacement_markdown)
    return output


def _require_inert_markdown(markdown: str) -> None:
    if re.search(r"(?m)^ {0,3}(?:`{3,}|~{3,})dmb-work-plan-v1(?:[ \t]|$)", markdown):
        raise BuildComposeError("build_compose_unsupported_markdown")
    if (re.search(r"<[^>]*>|dmb-node:|graphNodeReference|dmb-playable-element:|\bnode:[a-z0-9_-]+", markdown, re.I)
            or re.search(r"\[[^\]]+\]\((?:file:|\.{1,2}/|/)", markdown, re.I)):
        raise BuildComposeError("build_compose_unsupported_markdown")


_BOUNDARY_MARKDOWN = MarkdownIt("commonmark").enable(("table", "strikethrough"))


def _is_boundary_prose_or_callouts(text: str) -> bool:
    lines = text.replace("\r\n", "\n").replace("\r", "\n").split("\n")
    env = {}
    tokens = _BOUNDARY_MARKDOWN.parse(text, env)
    if env.get("references"):
        return False
    for token in tokens:
        if token.type == "blockquote_open":
            if token.level != 0 or token.map is None:
                return False
            start, end = token.map
            callout = split_boundary_callout(lines[start:end])
            if callout is None or not callout[2].strip():
                return False
        elif token.type == "inline":
            if any(child.type in {"image", "html_inline"} for child in token.children or ()):
                return False
        elif token.type not in {"paragraph_open", "paragraph_close", "blockquote_close"}:
            return False
    return bool(tokens)


def admit_build_boundary_fragment(markdown: str) -> None:
    _require_inert_markdown(markdown)
    text = markdown.strip()
    if (not text or "\n" in text or "\r" in text or "![" in text
            or re.match(r"^(?:#{1,6}\s|[-+*>]\s|[0-9]+[.)]\s|```|~~~|\|)", text)
            or re.fullmatch(r"(?:[*_-]\s*){3,}", text)) and not _is_boundary_prose_or_callouts(markdown):
        raise BuildComposeError("build_compose_boundary_requires_prose_or_callouts")


class BuildProseBoundaryProposal(BuildGeneratedProposal):
    target: Literal["prose_target"]

    @model_validator(mode="after")
    def exact_fragment(self):
        admit_build_boundary_fragment(self.replacement_markdown)
        return self


class BuildProseBoundaryOutput(BuildProseBoundaryProposal):
    destination: Literal["current_page"]


def normalize_boundary_proposal_output(text: str) -> BuildProseBoundaryProposal:
    def unique(pairs):
        value = {}
        for key, item in pairs:
            if key in value:
                raise BuildComposeError("build_compose_duplicate_output_field")
            value[key] = item
        return value

    wire = BuildProseBoundaryOutput.model_validate(json.loads(text, object_pairs_hook=unique))
    return BuildProseBoundaryProposal.model_validate(wire.model_dump(exclude={"destination"}))


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


class BuildProseBoundaryProposalRecord(BuildProposalRecord):
    schema_version: Literal["dmb_build_document_proposal_v3"] = "dmb_build_document_proposal_v3"
    reservation: BuildProseBoundaryReservation
    proposal: BuildProseBoundaryProposal | None = None


BUILD_MARKDOWN_PROPOSAL_CODECS = {
    "dmb_build_document_proposal_v1": BuildProposalRecord,
    "dmb_build_document_proposal_v3": BuildProseBoundaryProposalRecord,
}


def decode_build_markdown_proposal(payload) -> BuildProposalRecord:
    codec = BUILD_MARKDOWN_PROPOSAL_CODECS.get(payload.get("schema_version")) if isinstance(payload, dict) else None
    if codec is None:
        raise ValueError("Unknown Build Markdown proposal")
    return codec.model_validate(payload)


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
