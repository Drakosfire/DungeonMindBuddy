"""Strict source-backed manual review packets; no client-selected metadata policy."""

from datetime import datetime
from hashlib import sha256
from dungeonmind.domain.canonical import canonical_sha256
from typing import Annotated, Literal
from uuid import UUID

from pydantic import Field, field_validator, model_validator

from dungeonmind.contracts.vnext.domain import DomainContractRef
from dungeonmind.contracts.semantic_profile import SemanticProfileRef
from dungeonmind.contracts.vnext.native_source_publication import (
    GovernedNativeSourcePublicationV1,
)
from apps.live_control_server.models.native_profile_transition import Closed, Identifier

Digest = Annotated[str, Field(pattern=r"^[0-9a-f]{64}$")]


class ManualSource(Closed):
    managed_world_id: Identifier
    native_world_id: Identifier
    binding_version: int = Field(ge=1, strict=True)
    document_id: UUID
    document_revision: int = Field(ge=1, strict=True)
    body_sha256: Digest
    run_id: UUID
    run_revision: int = Field(ge=1, strict=True)
    app_source_artifact_id: Identifier
    app_source_revision_id: UUID
    span_index_sha256: Digest


class ManualContextRequest(Closed):
    schema_: Literal["dmb_native_manual_context_v1"] = Field(alias="schema")
    managed_world_id: Identifier
    document_id: UUID
    document_revision: int = Field(ge=1, strict=True)
    body_sha256: Digest
    run_id: UUID
    run_revision: int = Field(ge=1, strict=True)


class ManualWitness(Closed):
    source_span_ref_id: Identifier
    start_byte: int = Field(ge=0, strict=True)
    end_byte: int = Field(gt=0, strict=True)
    slice_sha256: Digest

    @model_validator(mode="after")
    def ordered(self):
        if self.end_byte <= self.start_byte:
            raise ValueError("witness must be nonempty")
        return self


class ManualObject(Closed):
    kind: Literal["object"]
    object_kind: Identifier
    name: str = Field(min_length=1)
    role: str | None = None
    aliases: list[str] = Field(default_factory=list)
    description: str | None = None

    @field_validator("name")
    @classmethod
    def nonblank(cls, value):
        if not value.strip():
            raise ValueError("name must not be blank")
        return value


class ManualEndpoint(Closed):
    entity_id: Identifier
    name: str = Field(min_length=1)
    object_kind: Identifier


class ManualRelationship(Closed):
    kind: Literal["relationship"]
    source: ManualEndpoint
    target: ManualEndpoint
    predicate: Identifier
    label: str | None = None
    description: str | None = None

    @model_validator(mode="after")
    def distinct(self):
        if self.source.entity_id == self.target.entity_id:
            raise ValueError("choose distinct endpoints")
        return self


class ManualPrepareRequest(Closed):
    schema_: Literal["dmb_native_manual_prepare_v1"] = Field(alias="schema")
    source: ManualSource
    operation_id: UUID
    created_at: datetime

    @field_validator("created_at")
    @classmethod
    def aware_time(cls, value):
        if value.utcoffset() is None:
            raise ValueError("created_at must be timezone-aware and retained on retry")
        return value

    expected_parent_revision_id: Identifier
    expected_source_authority_epoch: int = Field(ge=0, strict=True)
    witness: ManualWitness
    operation: Annotated[ManualObject | ManualRelationship, Field(discriminator="kind")]


class ManualPlanContent(Closed):
    schema_: Literal["dmb_native_manual_plan_v1"] = Field(
        default="dmb_native_manual_plan_v1", alias="schema"
    )
    review: ManualPrepareRequest
    publication: GovernedNativeSourcePublicationV1
    prepared_change_json: str
    domain_contract_ref: DomainContractRef
    semantic_profile_ref: SemanticProfileRef
    prepared_by: Identifier
    expires_at: datetime

    @model_validator(mode="after")
    def correlated(self):
        p, r = self.publication, self.review
        if (
            p.space_id != r.source.native_world_id
            or p.publication_id != str(r.operation_id)
            or p.expected_parent_revision_id != r.expected_parent_revision_id
            or p.expected_source_authority_epoch != r.expected_source_authority_epoch
            or p.expected_body_sha256 != r.source.body_sha256
            or p.created_at != r.created_at
        ):
            raise ValueError("publication must match reviewed source and operation")
        original = [
            d.payload
            for d in p.contribution.diagnostics
            if isinstance(d.payload, dict) and "manual_review_sha256" in d.payload
        ]
        expected = {
            "manual_review_sha256": canonical_sha256(
                r.model_dump(mode="json", by_alias=True)
            ),
            "prepared_by": self.prepared_by,
            "prepared_change_sha256": sha256(
                self.prepared_change_json.encode()
            ).hexdigest(),
        }
        if original != [expected]:
            raise ValueError(
                "Core intent must bind the complete original manual packet"
            )
        if self.expires_at.utcoffset() is None or self.expires_at <= p.created_at:
            raise ValueError("expiry must be aware and follow preparation")
        return self


class SignedManualPlan(ManualPlanContent):
    token: str = Field(min_length=1, max_length=65536)

    @field_validator("token")
    @classmethod
    def ascii_token(cls, value):
        if not value.isascii():
            raise ValueError("manual token must contain only ASCII characters")
        return value


class ManualConfirmRequest(Closed):
    schema_: Literal["dmb_native_manual_confirm_v1"] = Field(alias="schema")
    plan: SignedManualPlan
