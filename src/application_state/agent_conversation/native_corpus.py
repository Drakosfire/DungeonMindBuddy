"""Native source inspection pins, distinct from Graph and assertion support."""
from __future__ import annotations

from dataclasses import dataclass

from hashlib import sha256
from typing import Annotated, Literal
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator
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
    registered_campaign_id: str | None = Field(default=None, min_length=1,
        exclude_if=lambda value: value is None)
    session_scope: Literal["unestablished"] | Annotated[int, Field(gt=0, strict=True)] = "unestablished"
    # Omission preserves already committed historical catalogs and SDK bytes.
    # Every current acquisition supplies a name or explicit unavailable label.
    presentation_name: str | None = Field(default=None, min_length=1,
        exclude_if=lambda value: value is None)

    @field_validator("presentation_name")
    @classmethod
    def readable_name(cls, value):
        if value is not None and (not value.strip() or value != value.strip()):
            raise ValueError("Captured source name must be nonblank and trimmed")
        return value

    @model_validator(mode="after")
    def exact_source_pair(self):
        artifact = self.artifact
        if canonical(artifact) != self.artifact_json:
            raise ValueError("Native corpus metadata requires canonical immutable bytes")
        revision = self.revision
        if canonical(revision) != self.revision_json:
            raise ValueError("Native corpus metadata requires canonical immutable bytes")
        if (artifact.status != "active"
                or artifact.source_artifact_id != revision.source_artifact_id
                or artifact.current_revision_id != revision.source_revision_id
                or revision.body_storage != "dm_native_utf8_body_v1"
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


PositiveLine = Annotated[int, Field(gt=0, strict=True)]


class NativeCorpusPlanningRangesV1(Strict):
    schema_version: Literal["dmb_native_recap_planning_ranges_v1"] = "dmb_native_recap_planning_ranges_v1"
    lines: tuple[tuple[PositiveLine, PositiveLine], ...]


class NativeCorpusExcerptV1(Strict):
    """Selected body text; neither an APP source nor an admitted assertion span."""
    schema_version: Literal["dmb_native_body_excerpt_v1"] = "dmb_native_body_excerpt_v1"
    catalog_sha256: str = Field(pattern=r"^[a-f0-9]{64}$")
    selector_policy: Literal["markdown_sections_v1", "native_full_document_v1"]
    section: NativeCorpusSectionV1
    text: str = Field(min_length=1)
    excerpt_sha256: str = Field(pattern=r"^[a-f0-9]{64}$")

    planning_ranges: NativeCorpusPlanningRangesV1 | None = Field(
        default=None, exclude_if=lambda value: value is None)

    @model_validator(mode="after")
    def exact_excerpt(self):
        raw = self.text.encode("utf-8")
        if (not self.text.strip()
                or len(self.text) != self.section.char_end - self.section.char_start
                or len(raw) != self.section.byte_end - self.section.byte_start
                or sha256(raw).hexdigest() != self.excerpt_sha256):
            raise ValueError("Native body excerpt differs from its selected extent")
        if self.planning_ranges is not None:
            previous = self.section.line_start - 2
            for start, end in self.planning_ranges.lines:
                if not previous + 1 < start <= end <= self.section.line_end:
                    raise ValueError("Native recap planning ranges differ from the selected extent")
                previous = end
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


def _recap_planning_ranges(catalog, markdown, section):
    if catalog.source.session_scope == "unestablished":
        return None
    from graph_memory.extraction.recap_source_authority import recap_planning_lines

    ranges = []
    for line in sorted(recap_planning_lines(markdown)):
        if section.line_start <= line <= section.line_end:
            if ranges and ranges[-1][1] + 1 == line:
                ranges[-1] = (ranges[-1][0], line)
            else:
                ranges.append((line, line))
    return NativeCorpusPlanningRangesV1(lines=tuple(ranges))


def select_native_body_excerpt(catalog, markdown, section_id):
    """Revalidate the source and catalog before selecting any writer text."""
    actual = build_native_body_catalog(catalog.authority, catalog.source, markdown)
    if actual != catalog:
        raise ValueError("Native catalog differs from the exact source body")
    section = next((row for row in catalog.sections if row.section_id == section_id), None)
    if section is None:
        raise ValueError("Selected native body section is not in its catalog")
    if section.byte_start == 0 and section.byte_end == catalog.body_bytes:
        raise ValueError("An explicit full-document decision is required for whole-body exposure")
    text = markdown[section.char_start:section.char_end]
    return NativeCorpusExcerptV1(catalog_sha256=catalog.catalog_sha256,
        selector_policy="markdown_sections_v1", section=section,
        text=text, excerpt_sha256=sha256(text.encode()).hexdigest(),
        planning_ranges=_recap_planning_ranges(catalog, markdown, section))


def bounded_body_section(catalog, excerpt, *, line_start: int, line_end: int):
    """Derive a citable extent from an already validated source read."""
    parent = excerpt.section
    lines = excerpt.text.splitlines(keepends=True)
    if (type(line_start) is not int or type(line_end) is not int
            or excerpt.catalog_sha256 != catalog.catalog_sha256
            or len(lines) != parent.line_end - parent.line_start + 1
            or not parent.line_start <= line_start <= line_end <= parent.line_end):
        raise ValueError("Selected lines are outside their producing source read")
    before = "".join(lines[:line_start - parent.line_start])
    text = "".join(lines[line_start - parent.line_start:line_end - parent.line_start + 1])
    char_start = parent.char_start + len(before)
    byte_start = parent.byte_start + len(before.encode("utf-8"))
    byte_end = byte_start + len(text.encode("utf-8"))
    if not text.strip() or (byte_start == 0 and byte_end == catalog.body_bytes):
        raise ValueError("Writer passage must be nonblank and shorter than the full source")
    identity = dict(catalog_sha256=catalog.catalog_sha256, line_start=line_start, line_end=line_end)
    return NativeCorpusSectionV1(
        section_id=sha256(canonical(identity).encode()).hexdigest(),
        label=parent.label, line_start=line_start, line_end=line_end,
        char_start=char_start, char_end=char_start + len(text),
        byte_start=byte_start, byte_end=byte_end,
    ), text


def full_document_section(catalog):
    source, revision = catalog.source.artifact, catalog.source.revision
    identity = {"selector_policy": "native_full_document_v1",
        "source_artifact_id": source.source_artifact_id,
        "source_revision_id": revision.source_revision_id,
        "content_sha256": revision.content_sha256}
    return NativeCorpusSectionV1(section_id=sha256(canonical(identity).encode()).hexdigest(),
        label="Full document", line_start=1, line_end=catalog.sections[-1].line_end,
        char_start=0, char_end=catalog.body_chars, byte_start=0, byte_end=catalog.body_bytes)


def select_native_full_document(catalog, markdown):
    """Only the explicit full-document action may call this producing selector."""
    if build_native_body_catalog(catalog.authority, catalog.source, markdown) != catalog:
        raise ValueError("Native catalog differs from the exact source body")
    section = full_document_section(catalog)
    return NativeCorpusExcerptV1(catalog_sha256=catalog.catalog_sha256,
        selector_policy="native_full_document_v1", section=section,
        text=markdown, excerpt_sha256=sha256(markdown.encode()).hexdigest(),
        planning_ranges=_recap_planning_ranges(catalog, markdown, section))


class NativeBodyEvent(Strict):
    event_id: UUID
    sequence: int = Field(ge=0, strict=True)


class NativeBodySearchAuthorizedV1(NativeBodyEvent):
    kind: Literal["native_body_search_authorized_v1"] = "native_body_search_authorized_v1"
    provider_attempt_id: UUID
    context_receipt_sha256: str = Field(pattern=r"^[a-f0-9]{64}$")
    execution_policy_sha256: str = Field(pattern=r"^[a-f0-9]{64}$")
    authority: NativeCorpusAuthorityV1
    query_sha256: str = Field(pattern=r"^[a-f0-9]{64}$")


class NativeInitialSourceSearchAuthorizedV1(NativeBodyEvent):
    """Readonly work authorizes host discovery, never model body exposure."""
    kind: Literal["native_initial_source_search_authorized_v1"] = "native_initial_source_search_authorized_v1"
    work_selection_event_id: UUID
    context_receipt_sha256: str = Field(pattern=r"^[a-f0-9]{64}$")
    execution_policy_sha256: str = Field(pattern=r"^[a-f0-9]{64}$")
    authority: NativeCorpusAuthorityV1
    query_sha256: str = Field(pattern=r"^[a-f0-9]{64}$")


class NativePlanRequestSearchAuthorizedV1(NativeBodyEvent):
    """Actual admitted World request authorizes discovery before its first SDK."""
    kind: Literal['native_plan_request_search_authorized_v1'] = 'native_plan_request_search_authorized_v1'
    request_manifest_sha256: str = Field(pattern=r'^[a-f0-9]{64}$')
    context_receipt_sha256: str = Field(pattern=r'^[a-f0-9]{64}$')
    execution_policy_sha256: str = Field(pattern=r'^[a-f0-9]{64}$')
    authority: NativeCorpusAuthorityV1
    query_sha256: str = Field(pattern=r'^[a-f0-9]{64}$')


def request_source_discovery_enabled(context, execution):
    from .native_context import NativePlanRequestAdmissionV1, SurfaceNativeContextReceiptV1
    from .native_execution import NativePlanActionV2, NativePlanActionV3
    return (type(context) is SurfaceNativeContextReceiptV1
        and type(context.assembled_input) is NativePlanRequestAdmissionV1
        and type(execution.policy.action) in (NativePlanActionV2, NativePlanActionV3))


def validate_request_source_search(execution, grant):
    from . import types as t
    from .native_execution import NativePlanActionV2, NativePlanActionV3
    from .native_plan_opening import NativePlanAuthorScopeObservedV1
    from .native_retrieval import NativePlanAuthorScopeAuthorizedV1

    prefix = execution.events[:grant.sequence]
    action = execution.policy.action
    prior_attempts = [event for event in prefix if isinstance(event, t.ProviderAttemptAuthorizedEventV1)]
    from .native_plan_graph_need import (
        NativePlanGraphNeedObservedV1, NativePlanGraphQueryClosedV1, NativePlanGraphQuerySettledV1,
        validate_graph_need_intent_prefix,
    )
    from .native_retrieval import NativePlanGraphNeedAuthorizedV1

    graph_attempts = [event for event in prior_attempts if type(event) is NativePlanGraphNeedAuthorizedV1]
    if graph_attempts:
        graph = graph_attempts[0]
        decisions = [event for event in prefix if type(event) is NativePlanGraphNeedObservedV1
                     and event.controller_attempt_id == graph.provider_attempt_id]
        terminal = [event for event in prefix if type(event) in
                    (NativePlanGraphQueryClosedV1, NativePlanGraphQuerySettledV1)]
        if (len(graph_attempts) != 1 or len(decisions) != 1 or len(terminal) != 1
                or (type(terminal[0]) is NativePlanGraphQueryClosedV1
                    and terminal[0].need_event_id != decisions[0].event_id)
                or not graph.sequence < decisions[0].sequence < terminal[0].sequence):
            raise ValueError('Request discovery requires settled Plan Graph work')
        validate_graph_need_intent_prefix(execution, prefix[:graph.sequence])
        prior_attempts = [event for event in prior_attempts if event is not graph]
    scope_observations = [event for event in prefix if type(event) is NativePlanAuthorScopeObservedV1]
    if any(event.scope_observation.source_use == "conversation_only" for event in scope_observations):
        raise ValueError("Conversation-only Plan intent cannot authorize source discovery")
    scope_attempt_ids = [event.controller_attempt_id for event in scope_observations]
    after_author_scope = (
        (type(action) is NativePlanActionV3 or all(getattr(event, "intent_opening", None) is True for event in prior_attempts))
        and all(type(event) is NativePlanAuthorScopeAuthorizedV1 for event in prior_attempts)
        and [event.provider_attempt_id for event in prior_attempts] == scope_attempt_ids
    )
    if (type(action) not in (NativePlanActionV2, NativePlanActionV3)
            or grant.context_receipt_sha256 != execution.context_receipt_sha256
            or grant.execution_policy_sha256 != execution.execution_policy_sha256
            or t.canonical_sha256(grant.authority) != execution.policy.source_authority_sha256
            or grant.query_sha256 != sha256(action.intent.message.encode()).hexdigest()
            or (prior_attempts and not after_author_scope)
            or any(isinstance(e, (NativeBodySearchAuthorizedV1,
                NativeInitialSourceSearchAuthorizedV1, NativePlanRequestSearchAuthorizedV1)) for e in prefix)):
        raise ValueError('Request discovery requires its actual first admitted Plan request')


def initial_source_discovery_enabled(execution):
    from .plan_contextual_targets import is_question
    if is_question(execution):
        return False
    from .native_execution import NativePlanActionV2, NativePlanActionV3, NATIVE_PLAN_WORK_SELECTION_TYPES, SurfaceNativeExecutionV1
    return (type(execution) is SurfaceNativeExecutionV1
        and type(execution.policy.action) in (NativePlanActionV2, NativePlanActionV3)
        and any(type(event) in NATIVE_PLAN_WORK_SELECTION_TYPES
            and event.requested_work in {"discuss", "clarify"} for event in execution.events))


def validate_initial_source_search(execution, grant):
    from .native_execution import NativePlanActionV2, NativePlanActionV3, NativePlanRequestedWorkSelectedV3
    from .native_retrieval import NativeRetrievalAuthorizedV1
    action = execution.policy.action
    prefix = execution.events[:grant.sequence]
    work = next((event for event in prefix if event.event_id == grant.work_selection_event_id), None)
    if (type(action) not in (NativePlanActionV2, NativePlanActionV3)
            or type(work) is not NativePlanRequestedWorkSelectedV3
            or work.requested_work not in {"discuss", "clarify"}
            or grant.context_receipt_sha256 != execution.context_receipt_sha256
            or grant.execution_policy_sha256 != execution.execution_policy_sha256
            or grant.query_sha256 != sha256(action.intent.message.encode()).hexdigest()
            or sha256(canonical(grant.authority).encode()).hexdigest() != execution.policy.source_authority_sha256
            or any(isinstance(event, (NativeRetrievalAuthorizedV1, NativeBodySearchAuthorizedV1,
                NativeInitialSourceSearchAuthorizedV1)) for event in prefix)):
        raise ValueError("Initial source discovery requires its unique original readonly work and question")


class NativeBodySectionMatchV1(Strict):
    catalog_sha256: str = Field(pattern=r"^[a-f0-9]{64}$")
    section_id: str = Field(pattern=r"^[a-f0-9]{64}$")
    matched_terms: tuple[str, ...] = Field(min_length=1)
    distinctiveness_rank: int | None = Field(default=None, gt=0)


class NativeBodySearchObservedV1(NativeBodyEvent):
    kind: Literal["native_body_search_observed_v1"] = "native_body_search_observed_v1"
    authorization_event_id: UUID
    catalogs: tuple[NativeCorpusCatalogV1, ...]
    matches: tuple[NativeBodySectionMatchV1, ...]
    unavailable_source_count: int = Field(ge=0, strict=True)
    global_completeness: Literal["not_established"] = "not_established"


class NativeBodyReadAuthorizedV1(NativeBodyEvent):
    kind: Literal["native_body_read_authorized_v1"] = "native_body_read_authorized_v1"
    provider_attempt_id: UUID
    search_event_id: UUID
    catalog_sha256: str = Field(pattern=r"^[a-f0-9]{64}$")
    retrieval_kind: Literal["section", "full_document"]
    section_id: str | None

    @model_validator(mode="after")
    def explicit_extent_kind(self):
        if (self.retrieval_kind == "section") != (self.section_id is not None):
            raise ValueError("A section and a full-document decision have distinct selectors")
        return self


class NativeBodyReadObservedV1(NativeBodyEvent):
    kind: Literal["native_body_read_observed_v1"] = "native_body_read_observed_v1"
    authorization_event_id: UUID
    excerpt: NativeCorpusExcerptV1 | None
    failure_code: Literal["native_body_unavailable", "native_body_integrity_error"] | None

    @model_validator(mode="after")
    def exact_outcome(self):
        if (self.excerpt is None) != (self.failure_code is not None):
            raise ValueError("Native body read requires either exact text or a recorded failure")
        return self


class NativeDirectSourceAuthorizedV1(NativeBodyEvent):
    """Controller-selected full source; catalogue labels grant no read authority."""
    kind: Literal["native_direct_source_authorized_v1"] = "native_direct_source_authorized_v1"
    provider_attempt_id: UUID
    authority: NativeCorpusAuthorityV1
    source_artifact_id: str = Field(min_length=1)
    source_revision_id: str = Field(min_length=1)
    content_sha256: str = Field(pattern=r"^[a-f0-9]{64}$")


class NativeDirectSourceObservedV1(NativeBodyReadObservedV1):
    kind: Literal["native_direct_source_observed_v1"] = "native_direct_source_observed_v1"
    catalog: NativeCorpusCatalogV1 | None

    @model_validator(mode="after")
    def complete_source(self):
        if (self.catalog is None) != (self.excerpt is None):
            raise ValueError("Direct source result requires its exact catalogue and excerpt together")
        if self.excerpt is not None and (
                self.excerpt.catalog_sha256 != self.catalog.catalog_sha256
                or self.excerpt.selector_policy != "native_full_document_v1"
                or self.excerpt.section != full_document_section(self.catalog)
                or self.excerpt.excerpt_sha256 != self.catalog.source.revision.content_sha256):
            raise ValueError("Direct source read must cover its exact full source revision")
        return self


def native_direct_source_handle(authority, source_artifact_id, source_revision_id, content_sha256):
    identity = dict(authority=authority.model_dump(mode="json", exclude={"acquisition_epoch"}),
        source_artifact_id=source_artifact_id, source_revision_id=source_revision_id,
        content_sha256=content_sha256)
    return "native-direct-source:" + sha256(canonical(identity).encode()).hexdigest()


class NativeAuthoredSourceReadV1(NativeBodyEvent):
    """A human-selected read; its retained input is the grant, never a provider vote."""
    kind: Literal['native_authored_source_read_v1'] = 'native_authored_source_read_v1'
    capture_event_id: UUID
    reference_index: int = Field(ge=0, strict=True)
    catalog: NativeCorpusCatalogV1
    excerpt: NativeCorpusExcerptV1


class NativeBodyProviderIncludedV1(NativeBodyEvent):
    kind: Literal["native_body_provider_included_v1"] = "native_body_provider_included_v1"
    provider_attempt_id: UUID
    envelope_sha256: str = Field(pattern=r"^[a-f0-9]{64}$")
    read_event_ids: tuple[UUID, ...]
    frame_sha256: str = Field(pattern=r"^[a-f0-9]{64}$")


NATIVE_BODY_EVENTS = (NativeBodySearchAuthorizedV1, NativeInitialSourceSearchAuthorizedV1, NativePlanRequestSearchAuthorizedV1, NativeBodySearchObservedV1,
    NativeBodyReadAuthorizedV1, NativeBodyReadObservedV1, NativeBodyProviderIncludedV1, NativeAuthoredSourceReadV1,
    NativeDirectSourceAuthorizedV1, NativeDirectSourceObservedV1)


def native_body_handle(catalog_sha256, section_id):
    return "native-body:" + catalog_sha256 + ":" + section_id


def native_full_document_handle(catalog_sha256):
    return "native-full-document:" + catalog_sha256


def native_corpus_search_handle(query_sha256):
    return "native-corpus-search:" + query_sha256


def body_frame(reads):
    """Only actual selected excerpts are writer evidence; catalogs are navigation."""
    return {"schema": "dmb_native_body_frame_v1", "excerpts": [
        {"read_event_id": str(row.event_id),
         "section_handle": (native_full_document_handle(row.excerpt.catalog_sha256)
             if row.excerpt.selector_policy == "native_full_document_v1" else
             native_body_handle(row.excerpt.catalog_sha256, row.excerpt.section.section_id)),
         "excerpt": row.excerpt.model_dump(mode="json")}
        for row in reads]}


def validate_native_body_events(execution):
    """One authorized search, unique reads and inclusion tied to actual providers."""
    from . import types as t
    from .native_execution import BuildPendingExecutionV1, NativeBuildSourceSettledV1
    if type(execution) is BuildPendingExecutionV1:
        settlements = [e for e in execution.events if type(e) is NativeBuildSourceSettledV1]
        if len(settlements) != 1:
            raise ValueError('Pending body validation requires its actual source settlement')
        source_authority_sha256 = sha256(canonical(settlements[0].source_authority).encode()).hexdigest()
    else:
        source_authority_sha256 = None
    def authority_commitment():
        # Legacy policies need this field only for the same search/direct-read
        # branches that required it before pending Build was introduced.
        if source_authority_sha256 is not None:
            return source_authority_sha256
        return execution.policy.source_authority_sha256
    grant = search = None
    reads, authorizations, selected_sections = {}, {}, set()
    provider = outcome = None
    pending = None
    writer = False
    selection = None
    body_selection = None
    def selected(handle):
        return (selection is not None and selection.controller_attempt_id == provider
            and selection.operation == "select_candidates" and handle in selection.selected_handles)
    for event in execution.events:
        if body_selection is not None and isinstance(event, (NativeBodySearchAuthorizedV1, NativeInitialSourceSearchAuthorizedV1, NativePlanRequestSearchAuthorizedV1,
                NativeBodySearchObservedV1, NativeBodyReadAuthorizedV1, NativeBodyReadObservedV1, NativeAuthoredSourceReadV1, NativeDirectSourceAuthorizedV1)):
            raise ValueError("Native body acquisition cannot change after writer evidence selection")
        if isinstance(event, t.BuildWriterEvidenceSelectionV2):
            validate_body_selection(execution, event)
            body_selection = event
        if isinstance(event, t.ProviderAttemptAuthorizedEventV1):
            if grant is not None and search is None:
                raise ValueError("Provider cannot proceed with an unresolved native source search")
            if set(authorizations) != {row.authorization_event_id for row in reads.values() if isinstance(row, NativeBodyReadObservedV1)}:
                raise ValueError("Provider cannot proceed with an unresolved native body read")
            if pending is not None:
                if (event.provider_attempt_id != pending.provider_attempt_id
                        or event.envelope_sha256 != pending.envelope_sha256
                        or (event.provider, event.model, event.api_mode) != execution.policy.provider_roles.writer.identity()):
                    raise ValueError("Native body inclusion requires its exact authorized writer")
                pending = None
            provider, outcome = event.provider_attempt_id, None
            writer = (event.provider, event.model, event.api_mode) == execution.policy.provider_roles.writer.identity()
            if event.kind in {"native_writer_authorized_v1", "native_build_writer_authorized_v2"}:
                from .native_execution import NativeWriterAuthorizedV1, NATIVE_WRITER_TYPES
                if type(event) not in NATIVE_WRITER_TYPES or not writer:
                    raise ValueError("Shared native inclusion requires its exact writer role")
                # New native turns carry inclusion once on the actual writer.
                # The root closes IDs across all families; this owner closes
                # body grants and explicit whole-document exposure.
                validate_source_exposure(execution, tuple(row for row in reads.values()
                    if row.excerpt is not None))
        elif isinstance(event, t.ProviderOutcomeEventV1) and event.provider_attempt_id == provider:
            outcome = event.outcome
        elif isinstance(event, t.PlanJevRetrievalSelectionV1):
            selection = event
        elif isinstance(event, NativeAuthoredSourceReadV1):
            if writer:
                raise ValueError('Human source acquisition cannot follow the writer')
            from .authored_graph_references import validate_native_source_read
            validate_native_source_read(execution, event)
            if any(isinstance(row, NativeAuthoredSourceReadV1) and row.reference_index == event.reference_index
                    for row in reads.values()):
                raise ValueError('The selected source extent was acquired twice')
            reads[event.event_id] = event
        elif isinstance(event, NativeDirectSourceAuthorizedV1):
            handle = native_direct_source_handle(event.authority, event.source_artifact_id,
                event.source_revision_id, event.content_sha256)
            key = (event.source_artifact_id, event.source_revision_id, event.content_sha256)
            if (writer or outcome != "response_received" or provider != event.provider_attempt_id
                    or not selected(handle) or key in selected_sections
                    or sha256(canonical(event.authority).encode()).hexdigest()
                        != authority_commitment()):
                raise ValueError("Direct source read requires its unique acknowledged controller selection")
            authorizations[event.event_id] = event
            selected_sections.add(key)
        elif isinstance(event, NativeDirectSourceObservedV1):
            authorized = authorizations.get(event.authorization_event_id)
            if (not isinstance(authorized, NativeDirectSourceAuthorizedV1) or writer
                    or outcome != "response_received" or authorized.provider_attempt_id != provider
                    or any(isinstance(row, NativeBodyReadObservedV1)
                        and row.authorization_event_id == event.authorization_event_id for row in reads.values())):
                raise ValueError("Direct source observation lacks its current unique authorization")
            if event.catalog is not None:
                catalog, authority = event.catalog, authorized.authority
                if (catalog.authority.model_dump(exclude={"acquisition_epoch"})
                            != authority.model_dump(exclude={"acquisition_epoch"})
                        or catalog.authority.acquisition_epoch < authority.acquisition_epoch
                        or (catalog.source.artifact.source_artifact_id,
                            catalog.source.revision.source_revision_id, catalog.source.revision.content_sha256)
                            != (authorized.source_artifact_id, authorized.source_revision_id, authorized.content_sha256)):
                    raise ValueError("Direct source result changed its selected source or authority")
            reads[event.event_id] = event
        elif isinstance(event, NativePlanRequestSearchAuthorizedV1):
            validate_request_source_search(execution, event)
            if grant is not None or writer:
                raise ValueError('Request source discovery cannot repeat or follow the writer')
            grant = event
        elif isinstance(event, NativeInitialSourceSearchAuthorizedV1):
            validate_initial_source_search(execution, event)
            if grant is not None or writer:
                raise ValueError("Initial source discovery cannot repeat or follow the writer")
            grant = event
        elif isinstance(event, NativeBodySearchAuthorizedV1):
            if (grant is not None or writer or provider != event.provider_attempt_id
                    or outcome != "response_received"
                    or event.context_receipt_sha256 != execution.context_receipt_sha256
                    or event.execution_policy_sha256 != execution.execution_policy_sha256
                    or not selected(native_corpus_search_handle(event.query_sha256))
                    or sha256(canonical(event.authority).encode()).hexdigest()
                        != authority_commitment()):
                raise ValueError("Native search requires its unique acknowledged current controller")
            grant = event
        elif isinstance(event, NativeBodySearchObservedV1):
            if (grant is None or search is not None or event.authorization_event_id != grant.event_id
                    or writer or (isinstance(grant, NativeBodySearchAuthorizedV1)
                        and (outcome != "response_received" or provider != grant.provider_attempt_id))):
                raise ValueError("Native search observation lacks its current authorization")
            pairs, catalogs = set(), {}
            for catalog in event.catalogs:
                pair = (catalog.source.artifact.source_artifact_id, catalog.source.revision.source_revision_id)
                same_authority = catalog.authority == grant.authority
                if not same_authority and type(execution) is BuildPendingExecutionV1:
                    same_authority = (catalog.authority.model_dump(mode='json', exclude={'acquisition_epoch'})
                        == grant.authority.model_dump(mode='json', exclude={'acquisition_epoch'})
                        and catalog.authority.acquisition_epoch >= grant.authority.acquisition_epoch)
                if not same_authority or pair in pairs:
                    raise ValueError("Native search repeated or changed its source authority")
                pairs.add(pair)
                catalogs[catalog.catalog_sha256] = {section.section_id for section in catalog.sections}
            matches = [(row.catalog_sha256, row.section_id) for row in event.matches]
            if len(matches) != len(set(matches)) or any(
                    sid not in catalogs.get(cid, set()) for cid, sid in matches):
                raise ValueError("Native search matches differ from its actual section catalogs")
            search = event
        elif isinstance(event, NativeBodyReadAuthorizedV1):
            key = (event.catalog_sha256, event.retrieval_kind, event.section_id)
            full = event.retrieval_kind == "full_document"
            handle = native_full_document_handle(event.catalog_sha256) if full else native_body_handle(event.catalog_sha256, event.section_id)
            eligible = search is not None and (any(row.catalog_sha256 == event.catalog_sha256 for row in search.matches)
                if full else any((row.catalog_sha256, row.section_id) == (event.catalog_sha256, event.section_id)
                    for row in search.matches))
            if (search is None or writer or outcome != "response_received"
                    or event.provider_attempt_id != provider or event.search_event_id != search.event_id
                    or not selected(handle) or key in selected_sections or not eligible):
                raise ValueError("Native body read lacks its unique current selected source section")
            authorizations[event.event_id] = event
            selected_sections.add(key)
        elif isinstance(event, NativeBodyReadObservedV1):
            authorized = authorizations.get(event.authorization_event_id)
            if (not isinstance(authorized, NativeBodyReadAuthorizedV1) or writer or outcome != "response_received"
                    or authorized.provider_attempt_id != provider
                    or any(isinstance(row, NativeBodyReadObservedV1) and row.authorization_event_id == event.authorization_event_id for row in reads.values())):
                raise ValueError("Native body observation lacks its current unique authorization")
            if event.excerpt is not None:
                catalog = next(row for row in search.catalogs if row.catalog_sha256 == authorized.catalog_sha256)
                full = authorized.retrieval_kind == "full_document"
                section = full_document_section(catalog) if full else next(
                    row for row in catalog.sections if row.section_id == authorized.section_id)
                expected_policy = "native_full_document_v1" if full else "markdown_sections_v1"
                if (event.excerpt.catalog_sha256 != catalog.catalog_sha256 or event.excerpt.section != section
                        or event.excerpt.selector_policy != expected_policy
                        or not full and section.byte_start == 0 and section.byte_end == catalog.body_bytes):
                    raise ValueError("Native body text differs from its explicitly authorized extent")
            reads[event.event_id] = event
        elif isinstance(event, NativeBodyProviderIncludedV1):
            if (pending is not None or writer or outcome != "response_received"
                    or len(event.read_event_ids) != len(set(event.read_event_ids))):
                raise ValueError("Native body inclusion must be unique and precede the writer")
            included = [reads.get(identity) for identity in event.read_event_ids]
            if any(row is None or row.excerpt is None for row in included):
                raise ValueError("Native body inclusion references unavailable or unknown reads")
            validate_source_exposure(execution, included)
            expected = sha256(canonical(body_frame(included)).encode()).hexdigest()
            if expected != event.frame_sha256:
                raise ValueError("Native body inclusion frame differs from selected excerpts")
            pending = event


def acquired_body_reads(execution):
    """All successful acquisitions, including those subsequently excluded."""
    return tuple(event for event in execution.events
        if isinstance(event, (NativeBodyReadObservedV1, NativeAuthoredSourceReadV1)) and event.excerpt is not None)


def acquired_body_catalogs(execution):
    catalogs = {catalog.catalog_sha256: catalog for event in execution.events
        if isinstance(event, NativeBodySearchObservedV1) for catalog in event.catalogs}
    catalogs.update({event.catalog.catalog_sha256: event.catalog for event in execution.events
                    if isinstance(event, (NativeAuthoredSourceReadV1, NativeDirectSourceObservedV1))
                    and event.catalog is not None})
    return catalogs


def resolve_retained_body_citation(execution, citation):
    """Resolve a typed citation against its own already validated execution."""
    from .retained_conversation import native_supports
    retained = native_supports(execution)
    reads = [event for event in acquired_body_reads(execution) if event.event_id == citation.read_event_id]
    reads += [support.read for support in retained if support.read.event_id == citation.read_event_id]
    if len(reads) != 1:
        raise ValueError("Native body citation lacks its unique retained read")
    excerpt = reads[0].excerpt
    catalog = acquired_body_catalogs(execution).get(excerpt.catalog_sha256)
    if catalog is None:
        catalog = next((support.catalog for support in retained
                        if support.read.event_id == citation.read_event_id), None)
    if catalog is None:
        raise ValueError("Native body citation lacks its retained catalog")
    if (citation.catalog_sha256 != catalog.catalog_sha256
            or citation.source_artifact_id != catalog.source.artifact.source_artifact_id
            or citation.native_source_revision_id != catalog.source.revision.source_revision_id
            or citation.content_sha256 != catalog.source.revision.content_sha256
            or citation.selector_policy != excerpt.selector_policy):
        raise ValueError("Native body citation differs from the retained source identity")
    section, text = excerpt.section, excerpt.text
    if citation.section_id != section.section_id:
        section, text = bounded_body_section(
            catalog, excerpt, line_start=citation.line_start, line_end=citation.line_end,
        )
    if (citation.section_id != section.section_id
            or (citation.line_start, citation.line_end) != (section.line_start, section.line_end)
            or sha256(text.encode()).hexdigest() != citation.excerpt_sha256):
        raise ValueError("Native body citation differs from the retained extent")
    return catalog, section, text


class PriorBodyCitationReferenceV1(Strict):
    turn_id: UUID
    completion_sha256: str = Field(pattern=r"^[0-9a-f]{64}$")
    citation_index: int = Field(ge=0, le=16383, strict=True)


def is_prior_conversation_work(label, source_scope, *, allow_discussion=False):
    return ((label == "review_lore_page_from_conversation" and source_scope in {"anchored", "uncertain"})
            or (allow_discussion and label == "discuss" and source_scope == "anchored"))


def prior_conversation_work(events, *, allow_discussion=False):
    from .types import BuildRequestedWorkResolutionV1

    work = [event for event in events if isinstance(event, BuildRequestedWorkResolutionV1)]
    if (len(work) == 1 and is_prior_conversation_work(work[0].requested_work, work[0].resolution.get("source_scope"), allow_discussion=allow_discussion)
            and work[0].resolution.get("barrier") is None):
        return work[0]
    return None


def conversation_route_can_admit(receipt, execution):
    from .native_context import BuildPendingContextReceiptV1
    if type(receipt) is BuildPendingContextReceiptV1:
        from .build_source_free import pending_conversation_route_can_admit
        return pending_conversation_route_can_admit(receipt, execution)
    from .native_context import NativeBuildQueryPendingV1
    from .native_execution import NativeBuildActionV1, NativeBuildQuerySettledV1
    from .native_plan_statements import NativePlanQueryUnavailableV1

    if any(isinstance(event, NativeBuildQuerySettledV1) for event in execution.events):
        return False
    query = getattr(receipt, "native_query", None)
    if isinstance(query, NativeBuildQueryPendingV1):
        return True

    source = getattr(receipt, "source_authority", None)
    action = getattr(execution.policy, "action", None)
    if (type(query) is not NativePlanQueryUnavailableV1
            or query.reason != "native_graph_binding_unavailable"
            or type(source) is not NativeCorpusAuthorityV1
            or type(action) is not NativeBuildActionV1):
        return False
    intent = action.intent
    if (query.managed_world_id != source.managed_world_id
            or intent.world_id != source.managed_world_id
            or intent.reviewed_step is not None
            or getattr(intent, "authored_references", None) is not None
            or getattr(intent.graph_request, "revision_pin", None) is not None):
        return False

    # Unavailable queries bypass the pending-query validator. Preserve its
    # no-acquisition invariant here, including checks after prior admission.
    from . import types as t
    from .native_retrieval import NativeRetrievalAuthorizedV1, NativeRetrievalSelectedV1, NativeRetrievalSelectedV2

    return not any(isinstance(event, (*t.NATIVE_BODY_EVENTS, NativeRetrievalAuthorizedV1,
        NativeRetrievalSelectedV1, NativeRetrievalSelectedV2, t.RelatedPageRead))
        for event in execution.events)


def resolve_prior_body_citation(current, prior, reference, *, history_turn_ids):
    """Only the frozen dialogue window can lend exact support to the current turn."""
    from . import types as t
    from .rules_authority_reads import MixedCompletedTurnV1

    if isinstance(prior, MixedCompletedTurnV1):
        if prior.base_projection.kind != "approved":
            raise ValueError("Prior citation requires an approved completion")
        prior = prior.base_projection.turn
    if (prior.turn_id != reference.turn_id or prior.turn_id not in history_turn_ids
            or prior.world_id != current.world_id or prior.conversation_id != current.conversation_id
            or prior.sequence >= current.sequence or prior.status != "completed"):
        raise ValueError("Prior citation is outside the completed conversation history")
    completion = prior.completion
    if (completion is None or prior.graph_context_execution is None
            or t.canonical_sha256(completion) != reference.completion_sha256):
        raise ValueError("Prior citation differs from its retained completion")
    citations = getattr(completion, "native_body_citations", ())
    if reference.citation_index >= len(citations):
        raise ValueError("Prior citation ordinal is unavailable")
    citation = citations[reference.citation_index]
    _, _, passage = resolve_retained_body_citation(prior.graph_context_execution, citation)
    return completion.answer_segments[citation.segment_index].text, passage


def selected_batch_covering_reads(execution, selection, handle, *, before_sequence=None, require_passage=False):
    """Exact source extent already obtained by this acknowledged read batch."""
    if (not handle.startswith('native-body:') or selection.operation != 'select_candidates'
            or handle not in selection.selected_handles):
        return ()
    events = execution.events if before_sequence is None else execution.events[:before_sequence]
    searches = [e for e in events if isinstance(e, NativeBodySearchObservedV1)]
    from .native_execution import NativePlanActionV2, NativePlanActionV3

    plan = type(getattr(getattr(execution, "policy", None), "action", None)) in (NativePlanActionV2, NativePlanActionV3)
    catalogs = acquired_body_catalogs(execution)
    candidates = searches[0].catalogs if searches else ()
    if plan:
        candidates = tuple(catalogs.values()) + tuple(candidates)
    catalog = next((c for c in candidates for section in c.sections
        if handle == native_body_handle(c.catalog_sha256, section.section_id)), None)
    if catalog is None:
        return ()
    section = next(s for s in catalog.sections if handle == native_body_handle(catalog.catalog_sha256, s.section_id))
    def identity(c):
        return (c.source.artifact.source_artifact_id,
            c.source.revision.source_revision_id, c.source.revision.content_sha256)
    return tuple(e.event_id for e in events if isinstance(e, (NativeBodyReadObservedV1, NativeAuthoredSourceReadV1))
        and e.excerpt is not None
        and (e.sequence > selection.sequence or (
            plan and e.excerpt.selector_policy == 'native_full_document_v1'
            and section.byte_end - section.byte_start < catalog.body_bytes))
        and identity(catalogs[e.excerpt.catalog_sha256]) == identity(catalog)
        and (not require_passage or _is_writer_passage(e, catalogs[e.excerpt.catalog_sha256])
             or (plan and section.byte_end - section.byte_start < catalog.body_bytes))
        and e.excerpt.section.byte_start <= section.byte_start
        and e.excerpt.section.byte_end >= section.byte_end)


def body_selection_unit_id(read):
    return "body:" + str(read.event_id)


def validate_body_selection(execution, selection):
    """Body relevance cannot manufacture an acquisition or hide an unresolved read."""
    acquired = {body_selection_unit_id(e) for e in execution.events[:selection.sequence]
                if isinstance(e, NativeBodyReadObservedV1) and e.excerpt is not None}
    def body_ids(values):
        return {key for key in values if key.startswith("body:")}
    included = {key for key in acquired if selection.judgments.get(key) != "irrelevant"}
    if (body_ids(selection.judgments) != acquired
            or body_ids(selection.requested_unit_ids) != included
            or body_ids(selection.expanded_unit_ids) != included
            or body_ids(selection.omitted_unit_ids) != acquired - included):
        raise ValueError("Native body selection differs from its complete acquired extent closure")


def selected_body_reads(execution):
    from .types import BuildWriterEvidenceSelectionV2
    reads = acquired_body_reads(execution)
    votes = [event for event in execution.events if isinstance(event, BuildWriterEvidenceSelectionV2)]
    if not votes:
        return reads  # Historical V1/Plan inputs retain their original meaning.
    if len(votes) != 1:
        raise ValueError("Native body writer requires its unique evidence selection")
    vote = votes[0]
    validate_body_selection(execution, vote)
    return tuple(read for read in reads if isinstance(read, NativeAuthoredSourceReadV1)
                 or body_selection_unit_id(read) in vote.expanded_unit_ids)


def _is_writer_passage(read, catalog):
    excerpt = read.excerpt
    return (excerpt.selector_policy != "native_full_document_v1"
            and (excerpt.section.byte_start, excerpt.section.byte_end) != (0, catalog.body_bytes))


def writer_passage_reads(execution):
    """Keep exploration-only whole recaps out of the citation catalogue."""
    catalogs = acquired_body_catalogs(execution)
    return tuple(
        read for read in selected_body_reads(execution)
        if _is_writer_passage(read, catalogs[read.excerpt.catalog_sha256])
    )


def writer_passage_supports(execution, selector):
    """Bind ordinary section votes to exact acquired text, including covering reads."""
    from .native_retrieval import native_selection_types

    catalogs = acquired_body_catalogs(execution)
    reads = {read.event_id: read for read in selected_body_reads(execution)}
    supports = [NativeBodySupport(selector(read), read, catalogs[read.excerpt.catalog_sha256])
                for read in writer_passage_reads(execution)]
    exact = {support.handle for support in supports}
    sections = {native_body_handle(catalog.catalog_sha256, section.section_id): section
                for catalog in catalogs.values() for section in catalog.sections}
    for selection in execution.events:
        if not isinstance(selection, native_selection_types()):
            continue
        for handle in selection.selected_handles:
            section = sections.get(handle)
            if section is None or handle in exact:
                continue
            covering = selected_batch_covering_reads(execution, selection, handle)
            read = next((reads[key] for key in covering if key in reads), None)
            if read is None:
                continue
            catalog = catalogs[read.excerpt.catalog_sha256]
            if (section.byte_start, section.byte_end) == (0, catalog.body_bytes):
                continue
            support = NativeBodySupport(handle, read, catalog, (section.line_start, section.line_end))
            recovered, _ = support.passage()
            if (recovered.byte_start, recovered.byte_end) != (section.byte_start, section.byte_end):
                raise ValueError("Covering source read changed its selected passage extent")
            supports.append(support)
            exact.add(handle)
    return tuple(supports)


def body_selector(turn, read):
    """Current-input address only; the durable read retains source authority."""
    from .plan_source_selectors import _scope
    return 'b' + _scope(turn) + ':' + str(read.sequence)


def model_body_frame(turn):
    """Expose selected text once; Core metadata and receipt IDs remain host-only."""
    from . import types as t
    receipt, execution = turn.graph_context_receipt, turn.graph_context_execution
    if not isinstance(receipt, t.PlanSourceContextReceiptV1) or not isinstance(execution, t.PlanSourceExecutionV1):
        raise ValueError('Native body writer frame requires its source-capable Plan owner')
    from .plan_source_context import validate_source_execution_binding
    validate_source_execution_binding(receipt, execution)
    return model_body_frame_records(receipt.source_authority, execution,
        lambda read: body_selector(turn, read))


def model_body_frame_records(source_authority, execution, selector, *, passages_only=False):
    """Expose only selected body extents; producing-prefix admission is caller-owned."""
    searches = [event for event in execution.events if isinstance(event, NativeBodySearchObservedV1)]
    search = searches[0] if searches else None
    catalogs = acquired_body_catalogs(execution)
    pairs = []
    reads = writer_passage_reads(execution) if passages_only else selected_body_reads(execution)
    for read in reads:
        catalog = catalogs.get(read.excerpt.catalog_sha256)
        if catalog is None:
            raise ValueError('Native body writer read lacks its exact observed catalog')
        pairs.append((read, catalog))
    return model_body_frame_rows(source_authority, pairs, selector,
        search=search, catalog_count=len(catalogs),
        passage_supports=writer_passage_supports(execution, selector) if passages_only else None)


def body_source_name(catalog):
    # Old records must reconstruct the exact historical producing request.
    # Current acquisitions always freeze presentation_name before cataloguing.
    return catalog.source.presentation_name or catalog.sections[0].label


def model_body_frame_rows(source_authority, pairs, selector, *, search=None, catalog_count=None,
                          passage_supports=None):
    """Pure shared presentation of already owner-verified reads, not a read grant.

    Play can prepare its first request from actual Core reads before APP accepts
    the turn. Its producing owner later reconstructs these same rows from the
    persisted human read events. No provisional ledger or model vote is needed.
    """
    if passage_supports is None:
        passage_supports = (NativeBodySupport(selector(read), read, catalog)
                            for read, catalog in pairs)
    rows = []
    for support in passage_supports:
        excerpt, catalog = support.read.excerpt, support.catalog
        section, passage = support.passage()
        row = dict(excerpt_handle=support.handle, source_name=body_source_name(catalog),
            section_title=section.label,
            extent_kind='full_document' if support.selected_lines is None
                and excerpt.selector_policy == 'native_full_document_v1' else 'section',
            line_start=section.line_start, line_end=section.line_end,
            campaign_scope=catalog.source.campaign_scope, session_scope=catalog.source.session_scope,
            text=passage)
        if excerpt.planning_ranges:
            ranges = [[max(start, section.line_start), min(end, section.line_end)]
                      for start, end in excerpt.planning_ranges.lines
                      if start <= section.line_end and section.line_start <= end]
            if ranges:
                row["planning_line_ranges"] = ranges
        rows.append(row)
    return dict(schema='dmb_native_body_writer_evidence_v1',
        scope='GM whole-World cross-campaign source inspection; not campaign fact publication',
        source_authority_status='available' if isinstance(source_authority, NativeCorpusAuthorityV1) else 'unavailable',
        excerpts=rows, coverage=dict(search_performed=search is not None,
            accessible_source_count=catalog_count if search else None,
            unavailable_source_count=search.unavailable_source_count if search else None,
            semantic_recall='not_established', global_completeness='not_established'))


def prove_body_writer_input(turn, authorization, raw, *, sequence, event_id):
    """Reconstruct inclusion from exact actual SDK bytes under the locked owner."""
    from . import types as t
    from .plan_jev_graph_packet import frame_in_request
    from .rules_authority_types import canonical_sha256
    if not isinstance(authorization, t.PlanJevWriterAuthorizedV1):
        raise ValueError('Native body inclusion requires its exact Plan writer')
    if sha256(raw.encode()).hexdigest() != authorization.envelope_sha256:
        raise ValueError('Native body inclusion differs from actual SDK bytes')
    frame = frame_in_request(raw)
    if (frame.get('schema') not in {'dmb_plan_jev_writer_frame_v6', 'dmb_plan_jev_writer_frame_v7', 'dmb_plan_jev_writer_frame_v8'}
            or canonical_sha256(frame) != authorization.frame_sha256
            or frame.get('native_body_evidence') != model_body_frame(turn)):
        raise ValueError('Native body actual writer frame changed selected bytes or extent')
    reads = selected_body_reads(turn.graph_context_execution)
    return NativeBodyProviderIncludedV1(kind='native_body_provider_included_v1',
        event_id=event_id, sequence=sequence, provider_attempt_id=authorization.provider_attempt_id,
        envelope_sha256=authorization.envelope_sha256, read_event_ids=tuple(read.event_id for read in reads),
        frame_sha256=canonical_sha256(body_frame(reads)))



@dataclass(frozen=True)
class NativeBodySupport:
    handle: str
    read: NativeBodyReadObservedV1 | NativeAuthoredSourceReadV1
    catalog: NativeCorpusCatalogV1
    selected_lines: tuple[int, int] | None = None

    def passage(self) -> tuple[NativeCorpusSectionV1, str]:
        excerpt = self.read.excerpt
        if self.selected_lines is None:
            return excerpt.section, excerpt.text
        start, end = self.selected_lines
        return bounded_body_section(self.catalog, excerpt, line_start=start, line_end=end)


def body_passage_choices(execution):
    """Assign request-local aliases in retained read order."""
    return {f"r{index}": read for index, read in enumerate(acquired_body_reads(execution))}


def resolve_body_passages(execution, selections):
    """Resolve local read aliases and line ranges against the producing prefix."""
    catalogs = acquired_body_catalogs(execution)
    reads = body_passage_choices(execution)
    supports = []
    seen = set()
    selected_ranges = {}
    for alias, start, end in selections:
        read = reads.get(alias)
        if read is None:
            raise ValueError("Writer passage refers to an unavailable source read")
        catalog = catalogs[read.excerpt.catalog_sha256]
        support = NativeBodySupport(f"p{len(supports)}", read, catalog, (start, end))
        section, _ = support.passage()
        selected_ranges.setdefault(alias, []).append((start, end))
        revision = catalog.source.revision
        identity = (revision.source_artifact_id, revision.source_revision_id,
                    revision.content_sha256, section.byte_start, section.byte_end)
        if identity not in seen:
            seen.add(identity)
            supports.append(support)
    for alias, ranges in selected_ranges.items():
        excerpt = reads[alias].excerpt
        catalog = catalogs[excerpt.catalog_sha256]
        if excerpt.section.byte_start != 0 or excerpt.section.byte_end != catalog.body_bytes:
            continue
        material_lines = (
            number for number, line in enumerate(
                excerpt.text.splitlines(keepends=True), excerpt.section.line_start
            ) if line.strip()
        )
        if all(any(start <= number <= end for start, end in ranges) for number in material_lines):
            raise ValueError("Writer passage selections must omit material from a full source")
    return tuple(supports)


def producing_bodies(turn, authorization, raw):
    """Only the exact producing inclusion supplies eligible body selectors."""
    from . import types as t
    if isinstance(turn.graph_context_receipt, t.PlayWorldGraphContextReceiptV1):
        if turn.graph_context_receipt.authored_source_context is None:
            return ()
        from .play_authored_sources import producing_bodies as play_bodies
        return play_bodies(turn, authorization, raw)
    if not isinstance(turn.graph_context_receipt, t.PlanSourceContextReceiptV1):
        return ()
    execution = turn.graph_context_execution
    witnesses = [event for event in execution.events if isinstance(event, NativeBodyProviderIncludedV1)
        and event.provider_attempt_id == authorization.provider_attempt_id]
    if len(witnesses) != 1:
        raise ValueError('Native body output requires its unique producing inclusion')
    stored = witnesses[0]
    if prove_body_writer_input(turn, authorization, raw, sequence=stored.sequence, event_id=stored.event_id) != stored:
        raise ValueError('Native body output differs from actual producing bytes')
    catalogs = acquired_body_catalogs(execution)
    reads = {event.event_id: event for event in selected_body_reads(execution)}
    return tuple(NativeBodySupport(body_selector(turn, reads[identity]), reads[identity],
        catalogs[reads[identity].excerpt.catalog_sha256]) for identity in stored.read_event_ids)


@dataclass(frozen=True)
class PriorBodyWriterSupport:
    handle: str
    admission: object
    support: object

    def frame(self):
        citation = self.support.original_citation
        return dict(excerpt_handle=self.handle, source_name=citation.source_name,
            section_title=citation.section_title, extent_kind="section",
            line_start=citation.line_start, line_end=citation.line_end,
            campaign_scope="unestablished", session_scope="unestablished",
            text=self.support.passage, prior_claim=self.support.claim_text)


def prior_body_writer_supports(execution):
    from .types import BuildPriorBodyEvidenceAdmittedV1

    return tuple(PriorBodyWriterSupport(f"prior{i}", event, support)
        for event in execution.events if isinstance(event, BuildPriorBodyEvidenceAdmittedV1)
        for i, support in enumerate(event.supports))


def body_citation(support, *, index, text, producer, envelope_sha256):
    from . import types as t
    if isinstance(support, PriorBodyWriterSupport):
        return support.support.original_citation.model_copy(update={
            "segment_index": index, "text_sha256": sha256(text.encode()).hexdigest(),
            "provider_attempt_id": producer, "envelope_sha256": envelope_sha256,
            "prior_reference": support.support.reference,
        })
    read, catalog = support.read, support.catalog
    excerpt = read.excerpt
    section, passage = support.passage()
    return t.NativeBodyExcerptCitationV1(segment_index=index, text_sha256=sha256(text.encode()).hexdigest(),
        provider_attempt_id=producer, envelope_sha256=envelope_sha256, read_event_id=read.event_id,
        catalog_sha256=catalog.catalog_sha256, source_artifact_id=catalog.source.artifact.source_artifact_id,
        native_source_revision_id=catalog.source.revision.source_revision_id,
        content_sha256=catalog.source.revision.content_sha256, excerpt_sha256=sha256(passage.encode()).hexdigest(),
        section_id=section.section_id, selector_policy=excerpt.selector_policy,
        source_name=body_source_name(catalog), section_title=section.label,
        line_start=section.line_start, line_end=section.line_end)


def validate_body_citations(completion, receipt, execution, producer):
    from . import types as t
    play = (isinstance(receipt, t.PlayWorldGraphContextReceiptV1)
        and isinstance(execution, t.PlayWorldGraphExecutionV1)
        and receipt.authored_source_context is not None)
    if not isinstance(completion, t.SurfaceEvidenceCompletionV5):
        if isinstance(receipt, t.PlanSourceContextReceiptV1) or play:
            raise ValueError('Source-capable turn requires its native body completion contract')
        return
    if play:
        from .play_authored_sources import validate_binding
        validate_binding(receipt, execution)
        if completion.surface_id != 'play':
            raise ValueError('Play body completion cannot borrow a Plan owner')
    elif (not isinstance(receipt, t.PlanSourceContextReceiptV1) or not isinstance(execution, t.PlanSourceExecutionV1)
            or completion.native_source_citations):
        raise ValueError('Native body completion cannot inherit another source family')
    witnesses = [event for event in execution.events if isinstance(event, NativeBodyProviderIncludedV1)
        and event.provider_attempt_id == producer]
    if len(witnesses) != 1:
        raise ValueError('Native body completion lacks its unique producing inclusion')
    witness = witnesses[0]
    catalogs = acquired_body_catalogs(execution)
    reads = {event.event_id: event for event in selected_body_reads(execution)}
    supports = tuple(NativeBodySupport('', read, catalogs[read.excerpt.catalog_sha256])
        for identity, read in reads.items() if identity in witness.read_event_ids)
    validate_body_support_citations(completion, supports, producer=producer,
        envelope_sha256=witness.envelope_sha256, before_sequence=witness.sequence)


def validate_body_support_citations(completion, supports, *, producer, envelope_sha256, before_sequence):
    """Use only exact supports verified by the actual producing-input owner."""
    reads = {
        (support.read.event_id, support.passage()[0].section_id): support
        for support in supports if not isinstance(support, PriorBodyWriterSupport)
    }
    prior = {support.support.reference: support for support in supports
             if isinstance(support, PriorBodyWriterSupport)}
    for citation in completion.native_body_citations:
        if citation.prior_reference is None:
            support = reads.get((citation.read_event_id, citation.section_id))
            from .retained_conversation import RetainedBodySupport
            read = (support.admission if isinstance(support, RetainedBodySupport) else support.read
                    ) if support is not None else None
        else:
            support = prior.get(citation.prior_reference)
            read = support.admission if support is not None else None
        if read is None or read.sequence >= before_sequence:
            raise ValueError('Native body citation was not included in its producing writer')
        expected = body_citation(support, index=citation.segment_index,
            text=completion.answer_segments[citation.segment_index].text,
            producer=producer, envelope_sha256=envelope_sha256)
        if citation != expected:
            raise ValueError('Native body citation changed its exact source, extent or producer')


def body_input_partial(execution):
    return any(isinstance(event, NativeBodySearchObservedV1) and event.unavailable_source_count > 0
        or isinstance(event, NativeBodyReadObservedV1) and event.excerpt is None for event in execution.events)


def validate_source_exposure(execution, body_reads):
    """Keep source extents consistent across independently authorized read kinds.

    Each read already closes its exact controller grant and source extent. Their
    union does not need a second grant, even when it covers the complete source.
    A single whole-body read still requires its explicit full-document selector.
    """
    from .native_plan_statements import NativePlanStatementReadObservedV1
    catalogs = acquired_body_catalogs(execution)
    sizes = {}
    def include(pair, start, end, size):
        if size <= 0 or start < 0 or end <= start or end > size:
            raise ValueError('Source exposure interval exceeds the exact body')
        if pair in sizes and sizes[pair] != size:
            raise ValueError('Native evidence kinds disagree on original body size')
        sizes[pair] = size
    for row in body_reads:
        excerpt = row.excerpt
        catalog = catalogs[excerpt.catalog_sha256]
        pair = (catalog.source.artifact.source_artifact_id, catalog.source.revision.source_revision_id,
            catalog.source.revision.content_sha256)
        include(pair, excerpt.section.byte_start, excerpt.section.byte_end, catalog.body_bytes)
    for event in execution.events:
        if isinstance(event, NativePlanStatementReadObservedV1):
            for read in event.reads:
                s = read.support
                include((s.source_artifact_id, s.source_revision_id, s.source_body_sha256),
                    s.clause_start_byte, s.clause_end_byte, read.source_body_bytes)
