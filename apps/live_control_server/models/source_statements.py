"""Selected source meaning, never an assertion that its embedded event happened."""

from datetime import datetime
from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field, model_validator


class Strict(BaseModel):
    model_config = ConfigDict(
        extra="forbid", frozen=True, strict=True, str_strip_whitespace=False
    )


class SourceOrder(Strict):
    """A reviewed pair of disjoint byte extents, not fictional chronology."""

    before_start: int = Field(ge=0, strict=True)
    before_end: int = Field(gt=0, strict=True)
    before_sha256: str = Field(pattern=r"^[0-9a-f]{64}$")
    after_start: int = Field(ge=0, strict=True)
    after_end: int = Field(gt=0, strict=True)
    after_sha256: str = Field(pattern=r"^[0-9a-f]{64}$")

    @model_validator(mode="after")
    def source_forward_only(self):
        if not self.before_start < self.before_end <= self.after_start < self.after_end:
            raise ValueError("source order must be disjoint forward byte extents")
        return self


class StatementSelection(Strict):
    managed_world_id: str = Field(min_length=1)
    campaign_id: str = Field(min_length=1)
    expected_parent_revision_id: str = Field(min_length=1)
    source_admission_id: str | None = Field(default=None, min_length=1)
    source_evidence_extension_id: str | None = Field(default=None, min_length=1)
    evidence_ref_id: str = Field(min_length=1)
    source_sha256: str = Field(pattern=r"^[0-9a-f]{64}$")
    start_byte: int = Field(ge=0, strict=True)
    end_byte: int = Field(gt=0, strict=True)
    clause_sha256: str = Field(pattern=r"^[0-9a-f]{64}$")
    meaning: str = Field(min_length=1)
    mode: Literal["narrator", "reported", "uncertain"]
    reporter: str | None = Field(default=None, pattern=r"^ent:.+")
    referents: list[str] = Field(min_length=1)
    uncertainty: list[str]
    qualifications: dict[str, str] = Field(min_length=1)
    episode: str = Field(min_length=1)
    source_order: list[SourceOrder]
    embedded_content_factive: Literal[False] = False
    assertion_target: Literal["source_statement"] = "source_statement"

    @model_validator(mode="after")
    def closed_meaning(self):
        if (self.source_admission_id is None) == (self.source_evidence_extension_id is None):
            raise ValueError("choose exactly one original admission or evidence extension")
        if self.end_byte <= self.start_byte:
            raise ValueError("nonempty source clause required")
        if self.mode == "reported" and not self.reporter:
            raise ValueError("reported statement requires reviewed reporter")
        for values in (self.referents, self.uncertainty):
            if len(values) != len(set(values)) or any(not v.strip() for v in values):
                raise ValueError("blank or duplicate qualification values")
        if any(not v.startswith("ent:") for v in self.referents):
            raise ValueError("reviewed native referents required")
        if any(not k.strip() or not v.strip() for k, v in self.qualifications.items()):
            raise ValueError("complete qualifications required")
        for value in (self.meaning, self.episode, self.campaign_id):
            if not value.strip():
                raise ValueError("blank statement field")
        pairs = []
        for order in self.source_order:
            before = (order.before_start, order.before_end, order.before_sha256)
            after = (order.after_start, order.after_end, order.after_sha256)
            if (self.start_byte, self.end_byte, self.clause_sha256) not in (
                before,
                after,
            ):
                raise ValueError("source order must include the selected clause")
            pairs.append((before, after))
        if len(pairs) != len(set(pairs)):
            raise ValueError("duplicate source order pair")
        return self


class ConfirmStatement(Strict):
    envelope: dict[str, Any]
    prepared: dict[str, Any]
    token: str


class EvidenceInterval(Strict):
    client_ref: str = Field(min_length=1)
    evidence_role: Literal["support", "contradiction", "context"]
    start_byte: int = Field(ge=0)
    end_byte: int = Field(gt=0)
    expected_slice_sha256: str = Field(pattern=r"^[0-9a-f]{64}$")

    @model_validator(mode="after")
    def nonempty(self):
        if self.end_byte <= self.start_byte:
            raise ValueError("nonempty source interval required")
        return self


class ExtendSourceEvidence(Strict):
    managed_world_id: str = Field(min_length=1)
    extension_id: str = Field(min_length=1)
    original_admission_id: str = Field(min_length=1)
    source_artifact_id: str = Field(min_length=1)
    source_revision_id: str = Field(min_length=1)
    expected_body_sha256: str = Field(pattern=r"^[0-9a-f]{64}$")
    expected_parent_revision_id: str = Field(min_length=1)
    expected_source_authority_epoch: int = Field(ge=1)
    created_at: str = Field(min_length=1)
    spans: list[EvidenceInterval] = Field(min_length=1)

    @model_validator(mode="after")
    def aware_timestamp(self):
        if datetime.fromisoformat(self.created_at).utcoffset() is None:
            raise ValueError("timezone-aware created_at required")
        return self
