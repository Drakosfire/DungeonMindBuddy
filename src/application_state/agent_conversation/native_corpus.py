"""Native source inspection pins, distinct from Graph and assertion support."""
from __future__ import annotations

from hashlib import sha256
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, model_validator
from dungeonmind.contracts.vnext.source import SourceArtifactV3, SourceRevisionV2
from .native_statement_input import NativeAuthorityRefV1


class Strict(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)


class NativeCorpusAuthorityV1(Strict):
    schema_version: Literal["dmb_native_corpus_authority_v1"] = "dmb_native_corpus_authority_v1"
    managed_world_id: str = Field(min_length=1)
    native_world_id: str = Field(min_length=1)
    binding_version: int = Field(gt=0, strict=True)
    provisioning_id: str | None = None
    revision_id: str = Field(min_length=1)
    domain_ref: NativeAuthorityRefV1
    profile_ref: NativeAuthorityRefV1
    acquisition_epoch: int = Field(ge=0, strict=True)
    scope: Literal["gm_world_cross_campaign_source_inspection"] = "gm_world_cross_campaign_source_inspection"
    role: Literal["gm"] = "gm"


class NativeCorpusMemberV1(Strict):
    """One authorized body with its original access interval, not a new fact."""
    artifact: SourceArtifactV3
    revision: SourceRevisionV2
    evidence_ref_id: str = Field(min_length=1)
    access_span_id: str = Field(min_length=1)
    access_start_byte: int = Field(ge=0, strict=True)
    access_end_byte: int = Field(gt=0, strict=True)
    access_slice_sha256: str = Field(pattern=r"^[a-f0-9]{64}$")
    proof_epoch: int = Field(ge=0, strict=True)
    campaign_scope: Literal["unestablished"] = "unestablished"
    session_scope: Literal["unestablished"] = "unestablished"

    @model_validator(mode="after")
    def exact_source_pair(self):
        if (self.artifact.status != "active"
                or self.artifact.source_artifact_id != self.revision.source_artifact_id
                or self.artifact.current_revision_id != self.revision.source_revision_id
                or self.revision.body_storage != "dm_native_utf8_body_v1"
                or self.access_start_byte >= self.access_end_byte):
            raise ValueError("Native corpus member requires its exact active source pair")
        return self

    def verify_body(self, text: str) -> None:
        body = text.encode("utf-8")
        if (sha256(body).hexdigest() != self.revision.content_sha256
                or self.access_end_byte > len(body)):
            raise ValueError("Native corpus body differs from its source revision")
        selected = body[self.access_start_byte:self.access_end_byte]
        selected.decode("utf-8", errors="strict")
        if sha256(selected).hexdigest() != self.access_slice_sha256:
            raise ValueError("Native corpus original access interval differs")
