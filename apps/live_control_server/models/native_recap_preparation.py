"""Explicit review choices over an immutable saved Recap, not a publication command."""

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


class RecordSelection(Closed):
    kind: Literal["node", "edge", "beat"]
    record_id: Text
    action: Literal["create", "use_existing", "defer", "reject"]
    entity_id: Text | None = None
    facts: list[SelectedFact] = Field(default_factory=list)
    metadata: ReviewedMetadata | None = None

    @model_validator(mode="after")
    def explicit_operation(self):
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


class NativeRecapPrepareRequest(Closed):
    managed_world_id: Text
    campaign_id: Text
    run_id: Text
    expected_run_revision: int = Field(ge=1, strict=True)
    candidate_sha256: Digest
    source_admission_run_id: Text
    expected_parent_revision_id: Text
    expected_source_authority_epoch: int = Field(ge=1, strict=True)
    selections: list[RecordSelection]

    @model_validator(mode="after")
    def unique_records(self):
        keys = [(item.kind, item.record_id) for item in self.selections]
        if len(set(keys)) != len(keys):
            raise ValueError("duplicate record selection")
        return self
