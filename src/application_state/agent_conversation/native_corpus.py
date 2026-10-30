"""Native source inspection pins, distinct from Graph and assertion support."""
from __future__ import annotations

from hashlib import sha256
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, model_validator
from dungeonmind.contracts.vnext.source import SourceArtifactV3, SourceRevisionV2
from .native_statement_input import NativeAuthorityRefV1, canonical


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
    artifact_json: str
    revision_json: str

    @property
    def artifact(self) -> SourceArtifactV3:
        # Core models contain mutable nested fields. Expose a fresh validated
        # copy while the authoritative metadata remains immutable JSON bytes.
        return SourceArtifactV3.model_validate_json(self.artifact_json)

    @property
    def revision(self) -> SourceRevisionV2:
        return SourceRevisionV2.model_validate_json(self.revision_json)

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
        if canonical(self.artifact) != self.artifact_json or canonical(self.revision) != self.revision_json:
            raise ValueError("Native corpus metadata requires canonical immutable bytes")
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


class NativeCorpusSectionV1(Strict):
    section_id: str = Field(pattern=r"^[a-f0-9]{64}$")
    label: str = Field(min_length=1)
    line_start: int = Field(gt=0, strict=True)
    line_end: int = Field(gt=0, strict=True)
    char_start: int = Field(ge=0, strict=True)
    char_end: int = Field(gt=0, strict=True)
    byte_start: int = Field(ge=0, strict=True)
    byte_end: int = Field(gt=0, strict=True)

    @model_validator(mode="after")
    def valid_extent(self):
        if (self.line_end < self.line_start or self.char_end <= self.char_start
                or self.byte_end <= self.byte_start):
            raise ValueError("Native body section has an invalid extent")
        return self


class NativeCorpusCatalogV1(Strict):
    schema_version: Literal["dmb_native_body_catalog_v1"] = "dmb_native_body_catalog_v1"
    authority: NativeCorpusAuthorityV1
    source: NativeCorpusMemberV1
    selector_policy: Literal["markdown_sections_v1"] = "markdown_sections_v1"
    sections: tuple[NativeCorpusSectionV1, ...]
    body_chars: int = Field(gt=0, strict=True)
    body_bytes: int = Field(gt=0, strict=True)
    catalog_sha256: str = Field(pattern=r"^[a-f0-9]{64}$")

    @model_validator(mode="after")
    def exact_catalog(self):
        line, char, byte = 0, 0, 0
        artifact, revision = self.source.artifact, self.source.revision
        for section in self.sections:
            expected = {"selector_policy": self.selector_policy,
                "source_artifact_id": artifact.source_artifact_id,
                "native_source_revision_id": revision.source_revision_id,
                "content_sha256": revision.content_sha256,
                "line_start": section.line_start, "line_end": section.line_end}
            if (section.section_id != sha256(canonical(expected).encode()).hexdigest()
                    or section.line_start != line + 1 or section.char_start != char
                    or section.byte_start != byte):
                raise ValueError("Native body catalog is not an exact contiguous sequence")
            line, char, byte = section.line_end, section.char_end, section.byte_end
        if not self.sections or char != self.body_chars or byte != self.body_bytes:
            raise ValueError("Native body catalog does not cover its complete body")
        if self.source.proof_epoch > self.authority.acquisition_epoch:
            raise ValueError("Native catalog source proof postdates its captured source view")
        payload = self.model_dump(mode="json", exclude={"catalog_sha256"})
        if sha256(canonical(payload).encode()).hexdigest() != self.catalog_sha256:
            raise ValueError("Native body catalog digest differs")
        return self


class NativeCorpusExcerptV1(Strict):
    """Selected body text; neither an APP source nor an admitted assertion span."""
    schema_version: Literal["dmb_native_body_excerpt_v1"] = "dmb_native_body_excerpt_v1"
    catalog_sha256: str = Field(pattern=r"^[a-f0-9]{64}$")
    section: NativeCorpusSectionV1
    text: str = Field(min_length=1)
    excerpt_sha256: str = Field(pattern=r"^[a-f0-9]{64}$")

    @model_validator(mode="after")
    def exact_excerpt(self):
        raw = self.text.encode("utf-8")
        if (not self.text.strip()
                or len(self.text) != self.section.char_end - self.section.char_start
                or len(raw) != self.section.byte_end - self.section.byte_start
                or sha256(raw).hexdigest() != self.excerpt_sha256):
            raise ValueError("Native body excerpt differs from its selected extent")
        return self


def build_native_body_catalog(authority, source, markdown):
    """Reuse the existing Markdown selector over a verified native source body."""
    from .native_source_catalog import section_catalog
    source.verify_body(markdown)
    artifact, revision = source.artifact, source.revision
    selected = section_catalog(markdown, source_artifact_id=artifact.source_artifact_id,
        native_source_revision_id=revision.source_revision_id,
        content_sha256=revision.content_sha256)
    sections, cursor = [], 0
    for row in selected:
        end = cursor + len(markdown[row.char_start:row.char_end].encode("utf-8"))
        sections.append(row.model_dump(mode="json") | {"byte_start": cursor, "byte_end": end})
        cursor = end
    payload = dict(schema_version="dmb_native_body_catalog_v1",
        authority=authority.model_dump(mode="json"), source=source.model_dump(mode="json"),
        selector_policy="markdown_sections_v1", sections=sections,
        body_chars=len(markdown), body_bytes=len(markdown.encode("utf-8")))
    return NativeCorpusCatalogV1.model_validate(payload | {
        "catalog_sha256": sha256(canonical(payload).encode()).hexdigest()})


def select_native_body_excerpt(catalog, markdown, section_id):
    """Revalidate the source and catalog before selecting any writer text."""
    actual = build_native_body_catalog(catalog.authority, catalog.source, markdown)
    if actual != catalog:
        raise ValueError("Native catalog differs from the exact source body")
    section = next((row for row in catalog.sections if row.section_id == section_id), None)
    if section is None:
        raise ValueError("Selected native body section is not in its catalog")
    text = markdown[section.char_start:section.char_end]
    return NativeCorpusExcerptV1(catalog_sha256=catalog.catalog_sha256,
        section=section, text=text, excerpt_sha256=sha256(text.encode()).hexdigest())
