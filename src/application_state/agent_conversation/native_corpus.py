"""Native source inspection pins, distinct from Graph and assertion support."""
from __future__ import annotations

from hashlib import sha256
from typing import Literal
from uuid import UUID

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
    selector_policy: Literal["markdown_sections_v1", "native_full_document_v1"]
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
    if section.byte_start == 0 and section.byte_end == catalog.body_bytes:
        raise ValueError("An explicit full-document decision is required for whole-body exposure")
    text = markdown[section.char_start:section.char_end]
    return NativeCorpusExcerptV1(catalog_sha256=catalog.catalog_sha256,
        selector_policy="markdown_sections_v1", section=section,
        text=text, excerpt_sha256=sha256(text.encode()).hexdigest())


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
    return NativeCorpusExcerptV1(catalog_sha256=catalog.catalog_sha256,
        selector_policy="native_full_document_v1", section=full_document_section(catalog),
        text=markdown, excerpt_sha256=sha256(markdown.encode()).hexdigest())


def covers_full_document(intervals, body_bytes):
    """Union coverage includes disjoint, overlapping and accumulated excerpts."""
    cursor = 0
    ordered = sorted(intervals)
    if body_bytes <= 0 or any(start < 0 or end <= start or end > body_bytes for start, end in ordered):
        raise ValueError("Source exposure interval exceeds the exact body")
    for start, end in ordered:
        if start > cursor:
            return False
        cursor = max(cursor, end)
    return cursor == body_bytes


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


class NativeBodySectionMatchV1(Strict):
    catalog_sha256: str = Field(pattern=r"^[a-f0-9]{64}$")
    section_id: str = Field(pattern=r"^[a-f0-9]{64}$")
    matched_terms: tuple[str, ...] = Field(min_length=1)


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


class NativeBodyProviderIncludedV1(NativeBodyEvent):
    kind: Literal["native_body_provider_included_v1"] = "native_body_provider_included_v1"
    provider_attempt_id: UUID
    envelope_sha256: str = Field(pattern=r"^[a-f0-9]{64}$")
    read_event_ids: tuple[UUID, ...]
    frame_sha256: str = Field(pattern=r"^[a-f0-9]{64}$")


NATIVE_BODY_EVENTS = (NativeBodySearchAuthorizedV1, NativeBodySearchObservedV1,
    NativeBodyReadAuthorizedV1, NativeBodyReadObservedV1, NativeBodyProviderIncludedV1)


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
    """One selected search, unique reads and inclusion tied to actual providers."""
    from . import types as t
    grant = search = None
    reads, authorizations, selected_sections = {}, {}, set()
    provider = outcome = None
    pending = None
    writer = False
    selection = None
    def selected(handle):
        return (selection is not None and selection.controller_attempt_id == provider
            and selection.operation == "select_candidates" and handle in selection.selected_handles)
    for event in execution.events:
        if isinstance(event, t.ProviderAttemptAuthorizedEventV1):
            if grant is not None and search is None:
                raise ValueError("Provider cannot proceed with an unresolved native source search")
            if set(authorizations) != {row.authorization_event_id for row in reads.values()}:
                raise ValueError("Provider cannot proceed with an unresolved native body read")
            if pending is not None:
                if (event.provider_attempt_id != pending.provider_attempt_id
                        or event.envelope_sha256 != pending.envelope_sha256
                        or (event.provider, event.model, event.api_mode) != execution.policy.provider_roles.writer.identity()):
                    raise ValueError("Native body inclusion requires its exact authorized writer")
                pending = None
            provider, outcome = event.provider_attempt_id, None
            writer = (event.provider, event.model, event.api_mode) == execution.policy.provider_roles.writer.identity()
            if event.kind == "native_writer_authorized_v1":
                from .native_execution import NativeWriterAuthorizedV1
                if type(event) is not NativeWriterAuthorizedV1 or not writer:
                    raise ValueError("Shared native inclusion requires its exact writer role")
                # New native turns carry inclusion once on the actual writer.
                # The root closes IDs across all families; this owner closes
                # body grants and explicit whole-document exposure.
                validate_combined_exposure(execution, tuple(row for row in reads.values()
                    if row.excerpt is not None))
        elif isinstance(event, t.ProviderOutcomeEventV1) and event.provider_attempt_id == provider:
            outcome = event.outcome
        elif isinstance(event, t.PlanJevRetrievalSelectionV1):
            selection = event
        elif isinstance(event, NativeBodySearchAuthorizedV1):
            if (grant is not None or writer or provider != event.provider_attempt_id
                    or outcome != "response_received"
                    or event.context_receipt_sha256 != execution.context_receipt_sha256
                    or event.execution_policy_sha256 != execution.execution_policy_sha256
                    or not selected(native_corpus_search_handle(event.query_sha256))
                    or sha256(canonical(event.authority).encode()).hexdigest()
                        != execution.policy.source_authority_sha256):
                raise ValueError("Native search requires its unique acknowledged current controller")
            grant = event
        elif isinstance(event, NativeBodySearchObservedV1):
            if (grant is None or search is not None or event.authorization_event_id != grant.event_id
                    or writer or outcome != "response_received" or provider != grant.provider_attempt_id):
                raise ValueError("Native search observation lacks its current authorization")
            pairs, catalogs = set(), {}
            for catalog in event.catalogs:
                pair = (catalog.source.artifact.source_artifact_id, catalog.source.revision.source_revision_id)
                if catalog.authority != grant.authority or pair in pairs:
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
            if (authorized is None or writer or outcome != "response_received"
                    or authorized.provider_attempt_id != provider
                    or any(row.authorization_event_id == event.authorization_event_id for row in reads.values())):
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
            validate_combined_exposure(execution, included)
            expected = sha256(canonical(body_frame(included)).encode()).hexdigest()
            if expected != event.frame_sha256:
                raise ValueError("Native body inclusion frame differs from selected excerpts")
            pending = event


def selected_body_reads(execution):
    return tuple(event for event in execution.events
        if isinstance(event, NativeBodyReadObservedV1) and event.excerpt is not None)


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


def model_body_frame_records(source_authority, execution, selector):
    """Expose only selected body extents; producing-prefix admission is caller-owned."""
    searches = [event for event in execution.events if isinstance(event, NativeBodySearchObservedV1)]
    search = searches[0] if searches else None
    catalogs = {catalog.catalog_sha256: catalog for catalog in search.catalogs} if search else {}
    rows = []
    for read in selected_body_reads(execution):
        excerpt = read.excerpt
        catalog = catalogs.get(excerpt.catalog_sha256)
        if catalog is None:
            raise ValueError('Native body writer read lacks its exact observed catalog')
        rows.append(dict(excerpt_handle=selector(read), source_name=catalog.sections[0].label,
            section_title=excerpt.section.label,
            extent_kind='full_document' if excerpt.selector_policy == 'native_full_document_v1' else 'section',
            line_start=excerpt.section.line_start, line_end=excerpt.section.line_end,
            campaign_scope=catalog.source.campaign_scope, session_scope=catalog.source.session_scope,
            text=excerpt.text))
    return dict(schema='dmb_native_body_writer_evidence_v1',
        scope='GM whole-World cross-campaign source inspection; not campaign fact publication',
        source_authority_status='available' if isinstance(source_authority, NativeCorpusAuthorityV1) else 'unavailable',
        excerpts=rows, coverage=dict(search_performed=search is not None,
            accessible_source_count=len(catalogs) if search else None,
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


from dataclasses import dataclass

@dataclass(frozen=True)
class NativeBodySupport:
    handle: str
    read: NativeBodyReadObservedV1
    catalog: NativeCorpusCatalogV1


def producing_bodies(turn, authorization, raw):
    """Only the exact producing inclusion supplies eligible body selectors."""
    from . import types as t
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
    catalogs = {catalog.catalog_sha256: catalog for event in execution.events
        if isinstance(event, NativeBodySearchObservedV1) for catalog in event.catalogs}
    reads = {event.event_id: event for event in selected_body_reads(execution)}
    return tuple(NativeBodySupport(body_selector(turn, reads[identity]), reads[identity],
        catalogs[reads[identity].excerpt.catalog_sha256]) for identity in stored.read_event_ids)


def body_citation(support, *, index, text, producer, envelope_sha256):
    from . import types as t
    read, catalog = support.read, support.catalog
    excerpt = read.excerpt
    return t.NativeBodyExcerptCitationV1(segment_index=index, text_sha256=sha256(text.encode()).hexdigest(),
        provider_attempt_id=producer, envelope_sha256=envelope_sha256, read_event_id=read.event_id,
        catalog_sha256=catalog.catalog_sha256, source_artifact_id=catalog.source.artifact.source_artifact_id,
        native_source_revision_id=catalog.source.revision.source_revision_id,
        content_sha256=catalog.source.revision.content_sha256, excerpt_sha256=excerpt.excerpt_sha256,
        section_id=excerpt.section.section_id, selector_policy=excerpt.selector_policy,
        source_name=catalog.sections[0].label, section_title=excerpt.section.label,
        line_start=excerpt.section.line_start, line_end=excerpt.section.line_end)


def validate_body_citations(completion, receipt, execution, producer):
    from . import types as t
    if not isinstance(completion, t.SurfaceEvidenceCompletionV5):
        if isinstance(receipt, t.PlanSourceContextReceiptV1):
            raise ValueError('Source-capable Plan requires its native body completion contract')
        return
    if (not isinstance(receipt, t.PlanSourceContextReceiptV1) or not isinstance(execution, t.PlanSourceExecutionV1)
            or completion.native_source_citations):
        raise ValueError('Native body completion cannot inherit another source family')
    witnesses = [event for event in execution.events if isinstance(event, NativeBodyProviderIncludedV1)
        and event.provider_attempt_id == producer]
    if len(witnesses) != 1:
        raise ValueError('Native body completion lacks its unique producing inclusion')
    witness = witnesses[0]
    catalogs = {catalog.catalog_sha256: catalog for event in execution.events
        if isinstance(event, NativeBodySearchObservedV1) for catalog in event.catalogs}
    reads = {event.event_id: event for event in selected_body_reads(execution)}
    supports = tuple(NativeBodySupport('', read, catalogs[read.excerpt.catalog_sha256])
        for identity, read in reads.items() if identity in witness.read_event_ids)
    validate_body_support_citations(completion, supports, producer=producer,
        envelope_sha256=witness.envelope_sha256, before_sequence=witness.sequence)


def validate_body_support_citations(completion, supports, *, producer, envelope_sha256, before_sequence):
    """Use only exact supports verified by the actual producing-input owner."""
    reads = {support.read.event_id: support for support in supports}
    for citation in completion.native_body_citations:
        support = reads.get(citation.read_event_id)
        read = support.read if support is not None else None
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


def validate_combined_exposure(execution, body_reads):
    """One source-byte union guard across body and qualified-statement exposures."""
    from .native_plan_statements import NativePlanStatementReadObservedV1
    searches = [event for event in execution.events if isinstance(event, NativeBodySearchObservedV1)]
    catalogs = {c.catalog_sha256: c for search in searches for c in search.catalogs}
    exposures, sizes, explicit_full = {}, {}, set()
    def include(pair, start, end, size):
        if pair in sizes and sizes[pair] != size:
            raise ValueError('Native evidence kinds disagree on original body size')
        sizes[pair] = size
        exposures.setdefault(pair, []).append((start, end))
    for row in body_reads:
        excerpt = row.excerpt
        catalog = catalogs[excerpt.catalog_sha256]
        pair = (catalog.source.artifact.source_artifact_id, catalog.source.revision.source_revision_id,
            catalog.source.revision.content_sha256)
        include(pair, excerpt.section.byte_start, excerpt.section.byte_end, catalog.body_bytes)
        if excerpt.selector_policy == 'native_full_document_v1':
            explicit_full.add(pair)
    for event in execution.events:
        if isinstance(event, NativePlanStatementReadObservedV1):
            for read in event.reads:
                s = read.support
                include((s.source_artifact_id, s.source_revision_id, s.source_body_sha256),
                    s.clause_start_byte, s.clause_end_byte, read.source_body_bytes)
    if any(covers_full_document(ranges, sizes[pair]) and pair not in explicit_full
            for pair, ranges in exposures.items()):
        raise ValueError('Accumulated whole-document exposure requires an explicit full-document decision')
