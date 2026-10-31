"""Buddy's immutable APP-source/native-command correspondence. No body copy or effect authority."""

from __future__ import annotations
from datetime import datetime
from typing import Any, Literal
from uuid import UUID, NAMESPACE_URL, uuid5
from pydantic import BaseModel, ConfigDict, Field, model_validator
from dungeonmind.contracts.vnext import DomainContractRef
from dungeonmind.contracts.semantic_profile import SemanticProfileRef
from dungeonmind.contracts.vnext.native_source import (
    NativeSourceAdmissionReceiptV1,
    NativeTextSourceAdmissionV1,
)
from dungeonmind.domain.canonical import canonical_sha256

KEY = "native_recap_source"
PROFILE = "fresh_recap_native_source_v1"
# Frozen identity ingredient only; no normalization or provenance authority.
_ADMISSION_IDENTITY_TAG = "utf8-universal-newlines-terminal-lf-v1"


class Closed(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)


class SourceSelection(Closed):
    source_artifact_id: str = Field(pattern=r"^artifact:recap:v2:.+")
    source_revision_id: UUID
    content_sha256: str = Field(pattern=r"^[a-f0-9]{64}$")


class SourceScope(Closed):
    managed_world_id: str = Field(min_length=1)
    native_world_id: str = Field(min_length=1)
    binding_version: int = Field(ge=1)
    campaign_id: str = Field(min_length=1)


class Delivery(Closed):
    actor: str = Field(min_length=1)
    authority_basis: Literal["local_gm", "world_manage"]
    entered_at: datetime
    state: Literal["entered", "unknown", "stale", "committed"] = "entered"
    failure_code: str | None = None


class Command(Closed):
    # Complete Core wire except body_text, resolved only from the exact immutable APP UUID.
    request: dict[str, Any]
    domain_ref: DomainContractRef
    profile_ref: SemanticProfileRef
    sha256: str = Field(pattern=r"^[a-f0-9]{64}$")
    deliveries: list[Delivery] = Field(default_factory=list)

    @model_validator(mode="after")
    def closed_header(self):
        if set(self.request) != set(NativeTextSourceAdmissionV1.model_fields) - {
            "body_text"
        }:
            raise ValueError("Frozen source command header is incomplete")
        return self

    def resolve(self, markdown: str):
        request = NativeTextSourceAdmissionV1.model_validate(
            {**self.request, "body_text": markdown}
        )
        if (
            canonical_sha256(
                {
                    "request": request.model_dump(mode="json"),
                    "domain_ref": self.domain_ref.model_dump(mode="json"),
                    "profile_ref": self.profile_ref.model_dump(mode="json"),
                }
            )
            != self.sha256
        ):
            raise ValueError("Frozen source command changed")
        return request


class Record(Closed):
    schema_version: Literal["dmb_native_recap_source_record_v2"] = (
        "dmb_native_recap_source_record_v2"
    )
    managed_world_id: str = Field(min_length=1)
    native_world_id: str = Field(min_length=1)
    binding_version: int = Field(ge=1)
    campaign_id: str = Field(min_length=1)
    grouping_basis: Literal["exact_app_source_descriptor"] = "exact_app_source_descriptor"
    session_id: str = Field(pattern=r"^session-[1-9][0-9]*$")
    app_source_artifact_id: str = Field(pattern=r"^artifact:recap:v2:.+")
    app_source_revision_id: UUID
    app_body_sha256: str = Field(pattern=r"^[a-f0-9]{64}$")
    created_by: str = Field(min_length=1)
    created_authority_basis: Literal["local_gm", "world_manage"]
    created_at: datetime
    commands: list[Command] = Field(default_factory=list)
    receipt: NativeSourceAdmissionReceiptV1 | None = None
    preflight_failures: list[str] = Field(default_factory=list)

    @property
    def admission_id(self):
        return "dmb-recap-source:" + canonical_sha256(
            {
                k: _ADMISSION_IDENTITY_TAG
                if k == "normalization_policy"
                else str(self.app_source_revision_id)
                if k == "app_source_revision_id"
                else getattr(self, k)
                for k in (
                    "managed_world_id",
                    "native_world_id",
                    "campaign_id",
                    "session_id",
                    "app_source_artifact_id",
                    "app_source_revision_id",
                    "app_body_sha256",
                    "normalization_policy",
                )
            }
        )

    @property
    def run_id(self):
        return str(uuid5(NAMESPACE_URL, self.admission_id))

    @property
    def command(self):
        return self.commands[-1] if self.commands else None

    @property
    def state(self):
        if self.receipt:
            return "committed"
        return (
            self.command.deliveries[-1].state
            if self.command and self.command.deliveries
            else "reserved"
        )

    @model_validator(mode="after")
    def correspondence(self):
        for c in self.commands:
            r = c.request
            if (
                r.get("space_id") != self.native_world_id
                or r.get("admission_id") != self.admission_id
                or r.get("expected_body_sha256") != self.app_body_sha256
                or r.get("origin")
                != {
                    "namespace": "dungeonbuddy.app-recap-source.v1",
                    "object_id": self.app_source_artifact_id,
                    "revision_id": str(self.app_source_revision_id),
                }
            ):
                raise ValueError("Source command belongs to another immutable origin")
        if self.receipt and (
            self.receipt.admission_id != self.admission_id
            or self.receipt.space_id != self.native_world_id
            or not self.commands
            or self.receipt.origin is None
            or self.receipt.origin.model_dump() != self.command.request["origin"]
        ):
            raise ValueError("Source receipt belongs to another immutable origin")
        return self


class Resume(Closed):
    run_id: UUID
    expected_run_revision: int = Field(ge=1)
    command_sha256: str | None = Field(default=None, pattern=r"^[a-f0-9]{64}$")


class Opening(Closed):
    state: Literal["not_checked", "verified", "unavailable", "integrity_error"]
    body_sha256: str | None = None
    span_start_byte: int | None = None
    span_end_byte: int | None = None
    span_sha256: str | None = None
    read_revision_id: str | None = None
    acquisition_epoch: int | None = None


class StatusBody(Closed):
    operation: Literal["inspect_status"] = "inspect_status"
    native_recap_run_id: UUID
    managed_world_id: str = Field(min_length=1)
    campaign_id: str = Field(min_length=1)
    session: int = Field(ge=1)


class StatusRequest(Closed):
    method: Literal["POST"] = "POST"
    path: Literal["/api/live/recap-ingest"] = "/api/live/recap-ingest"
    body: StatusBody


class Status(Closed):
    schema_version: Literal["dmb_native_recap_source_status_v2"] = (
        "dmb_native_recap_source_status_v2"
    )
    state: Literal[
        "reserved", "dispatching", "admitted", "unavailable", "conflict", "unknown"
    ]
    run_id: UUID
    run_revision: int = Field(ge=1)
    operation: Literal["fresh_recap_native_source_v1"] = PROFILE
    managed_world_id: str
    native_world_id: str
    binding_version: int
    campaign_id: str
    grouping_basis: Literal["exact_app_source_descriptor"] = "exact_app_source_descriptor"
    session_id: str
    app_source_artifact_id: str
    app_source_revision_id: UUID
    app_body_sha256: str
    admission_id: str
    origin: dict[str, str]
    domain_ref: DomainContractRef | None
    profile_ref: SemanticProfileRef | None
    command_sha256: str | None
    expected_parent_revision_id: str | None
    native_receipt: NativeSourceAdmissionReceiptV1 | None
    published_revision_id: str | None
    source_artifact_id: str | None
    source_revision_id: str | None
    evidence_ref_id: str | None
    opening: Opening
    failure_code: str | None
    admission_committed: bool
    status_request: StatusRequest

    @model_validator(mode="after")
    def delivered(self):
        if self.admission_committed != (self.native_receipt is not None):
            raise ValueError("Commit state contradicts receipt")
        if self.state == "admitted" and (
            not self.admission_committed or self.opening.state != "verified"
        ):
            raise ValueError("Admitted status requires verified native opening")
        if self.native_receipt:
            r = self.native_receipt
            if (
                r.admission_id != self.admission_id
                or r.space_id != self.native_world_id
                or r.origin is None
                or r.origin.model_dump() != self.origin
                or len(r.bindings) != 1
                or (
                    self.published_revision_id,
                    self.source_artifact_id,
                    self.source_revision_id,
                    self.evidence_ref_id,
                )
                != (
                    r.published_revision_id,
                    r.source_artifact_id,
                    r.source_revision_id,
                    r.bindings[0].evidence_ref_id,
                )
            ):
                raise ValueError("Status receipt correspondence mismatch")
        elif any(
            (
                self.published_revision_id,
                self.source_artifact_id,
                self.source_revision_id,
                self.evidence_ref_id,
            )
        ):
            raise ValueError("Uncommitted status cannot assert source identities")
        if self.opening.state == "verified" and (
            self.opening.body_sha256 != self.app_body_sha256
            or self.opening.span_start_byte != 0
            or not self.opening.span_end_byte
            or self.opening.span_sha256 != self.app_body_sha256
            or self.opening.read_revision_id != self.published_revision_id
            or self.opening.acquisition_epoch is None
        ):
            raise ValueError("Verified opening requires exact source proof")
        b = self.status_request.body
        if (
            str(b.native_recap_run_id),
            b.managed_world_id,
            b.campaign_id,
            f"session-{b.session}",
        ) != (
            str(self.run_id),
            self.managed_world_id,
            self.campaign_id,
            self.session_id,
        ):
            raise ValueError("Status request scope changed")
        return self


def validate_change(old: Record, new: Record):
    if old.model_dump(
        exclude={"commands", "receipt", "preflight_failures"}
    ) != new.model_dump(exclude={"commands", "receipt", "preflight_failures"}):
        raise ValueError("Immutable source intent changed")
    if old.receipt is not None and old.receipt != new.receipt:
        raise ValueError("Committed receipt cannot change")
    if new.preflight_failures[: len(old.preflight_failures)] != old.preflight_failures:
        raise ValueError("Failures cannot be removed")
    if (
        len(new.commands) < len(old.commands)
        or len(new.commands) > len(old.commands) + 1
    ):
        raise ValueError("Invalid command history")
    if len(new.commands) > len(old.commands) and old.command and old.state != "stale":
        raise ValueError("Only definitive pre-write stale permits a new command")
    for before, after in zip(old.commands, new.commands):
        if before.model_dump(exclude={"deliveries"}) != after.model_dump(
            exclude={"deliveries"}
        ):
            raise ValueError("Frozen command changed")
        if len(after.deliveries) not in (
            len(before.deliveries),
            len(before.deliveries) + 1,
        ):
            raise ValueError("Invalid delivery history")
        if (
            after.deliveries[: max(0, len(before.deliveries) - 1)]
            != before.deliveries[:-1]
        ):
            raise ValueError("Prior delivery changed")
        if before.deliveries:
            last = before.deliveries[-1]
            replacement = after.deliveries[len(before.deliveries) - 1]
            if last != replacement and (
                last.state != "entered"
                or last.model_dump(exclude={"state", "failure_code"})
                != replacement.model_dump(exclude={"state", "failure_code"})
            ):
                raise ValueError("Settled delivery changed")
