"""Explicit saved candidate review and confirmation of its exact WK preparation."""

from typing import Annotated, Literal
from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field, JsonValue, model_validator
from worldkeeper.application import DomainMetadata, TemporalScope, Visibility

Text = Annotated[str, Field(min_length=1, pattern=r"\S")]
Digest = Annotated[str, Field(pattern=r"^[0-9a-f]{64}$")]


class Closed(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)


class ReviewedTemporal(Closed):
    kind: Text
    valid_from: datetime | None = None
    valid_until: datetime | None = None
    schema_term: Text | None = None
    payload: JsonValue = None

    def native(self):
        return TemporalScope(**self.model_dump())


class ReviewedDomainMetadata(Closed):
    schema_term: Text
    payload: JsonValue

    def native(self):
        return DomainMetadata.from_json(self.schema_term, self.payload)


class ReviewedMetadata(Closed):
    evidence_ref_ids: list[Text] = Field(min_length=1)
    # Scope is server-bound; selected evidence IDs are resolved through Core.
    visibility: Visibility
    epistemic_basis: Text
    claim_mode: Text
    standing: Text
    temporal_scope: ReviewedTemporal
    domain_metadata: list[ReviewedDomainMetadata] = Field(default_factory=list)


class SelectedFact(Closed):
    field: Literal["label", "node_type", "description", "session_actions", "title", "summary"]
    index: int | None = Field(default=None, ge=0, strict=True)
    metadata: ReviewedMetadata

    @model_validator(mode="after")
    def indexed_action(self):
        if (self.index is not None) != (self.field == "session_actions"):
            raise ValueError("only session_actions requires an explicit index")
        return self


class DescriptionExtent(Closed):
    start_byte: int = Field(ge=0, strict=True)
    end_byte: int = Field(gt=0, strict=True)
    expected_slice_sha256: Digest

    @model_validator(mode="after")
    def nonempty(self):
        if self.end_byte <= self.start_byte:
            raise ValueError("description extent must be nonempty")
        return self


class SelectedDescriptionExtent(Closed):
    # A separate variant keeps old whole-field signed envelopes unchanged.
    field: Literal["description"]
    index: None = None
    extent: DescriptionExtent
    metadata: ReviewedMetadata


class RecordSelection(Closed):
    kind: Literal["node", "edge", "beat"]
    record_id: Text
    action: Literal["create", "use_existing", "defer", "reject"]
    entity_id: Text | None = None
    facts: list[SelectedFact | SelectedDescriptionExtent] = Field(default_factory=list)
    metadata: ReviewedMetadata | None = None

    @model_validator(mode="after")
    def explicit_operation(self):
        if self.kind != "node" and any(isinstance(f, SelectedDescriptionExtent) for f in self.facts):
            raise ValueError("description extents require a node selection")
        if (self.entity_id is not None) != (self.action == "use_existing"):
            raise ValueError("only use_existing requires an explicit durable entity ID")
        if self.action in {"defer", "reject"}:
            if self.facts or self.metadata:
                raise ValueError("deferred/rejected records cannot carry selected facts")
        elif self.kind == "edge":
            if self.action != "create" or self.facts or self.metadata is None:
                raise ValueError("edges require create and explicit relationship metadata")
        elif self.metadata is not None or (self.action == "create" and not self.facts):
            raise ValueError("objects require per-fact review; create cannot be empty")
        keys = [(fact.field, fact.index) for fact in self.facts]
        if len(set(keys)) != len(keys):
            raise ValueError("duplicate selected field")
        return self


class _CandidatePrepareRequest(Closed):
    managed_world_id: Text
    run_id: Text
    expected_run_revision: int = Field(ge=1, strict=True)
    candidate_sha256: Digest
    expected_parent_revision_id: Text
    expected_source_authority_epoch: int = Field(ge=1, strict=True)
    selections: list[RecordSelection]

    @model_validator(mode="after")
    def unique_records(self):
        keys = [(item.kind, item.record_id) for item in self.selections]
        if len(set(keys)) != len(keys):
            raise ValueError("duplicate record selection")
        return self


class NativeRecapPrepareRequest(_CandidatePrepareRequest):
    campaign_id: Text
    source_admission_run_id: Text


class NativeWorldbuildingPrepareRequest(_CandidatePrepareRequest):
    workspace_document_id: Text
    workspace_document_revision: int = Field(ge=1, strict=True)


class NativeRecapReviewEnvelope(Closed):
    purpose: Literal["dmb_native_recap_confirm_v1", "dmb_native_worldbuilding_confirm_v1"]
    producer: Literal["dungeonbuddy:reviewed-recap", "dungeonbuddy:reviewed-worldbuilding"]
    principal: Text
    binding: dict[str, JsonValue] = Field(min_length=1)
    parent_context: dict[str, JsonValue] = Field(min_length=1)
    review: NativeRecapPrepareRequest | NativeWorldbuildingPrepareRequest
    prepared_change_id: Text
    prepared_digest: Digest
    expires_at: datetime

    @model_validator(mode="after")
    def aware_expiry(self):
        domain = "recap" if isinstance(self.review, NativeRecapPrepareRequest) else "worldbuilding"
        if self.purpose != f"dmb_native_{domain}_confirm_v1" or self.producer != f"dungeonbuddy:reviewed-{domain}":
            raise ValueError("review purpose and producer must match the reviewed source scope")
        if self.expires_at.utcoffset() is None:
            raise ValueError("review expiry must be timezone-aware")
        return self


class NativeRecapConfirmRequest(Closed):
    envelope: NativeRecapReviewEnvelope
    prepared: dict[str, JsonValue]
    token: Text
