"""Selected native assertions for Plan; Core owns admission and source provenance."""
from __future__ import annotations

from hashlib import sha256
from typing import Literal
from uuid import UUID

from dungeonmind.contracts.vnext.domain import Assertion
from dungeonmind.contracts.vnext.source import EvidenceRefV3
from pydantic import Field, model_validator

from .native_statement_input import Strict, digest
from .native_plan_statements import NativePlanQueryV1

POLICY = 'dmb_surface_evidence_answer_v8'
INSTRUCTIONS = """Native assertions are reviewed Graph records, not independent proof of every event.
Use {"kind":"native_assertion_claim","text":"supported prose","assertion_handles":["exact exposed handle"]}.
Preserve claim_mode, epistemic_basis, standing, temporal_scope, scope and all domain
qualifications. Reported beliefs and uncertain accounts must stay attributed and
qualified. Entity labels are navigation only. Source coordinates are citations,
not source text you inspected; do not invent quotations or source chronology.
Select only relevant assertions. Partial retrieval never establishes absence.
"""


class NativePlanAssertionMatchV1(Strict):
    assertion_id: str = Field(min_length=1)
    subject_entity_id: str = Field(min_length=1)
    discovered_entity_ids: tuple[str, ...] = Field(min_length=1)
    assertion_sha256: str = Field(pattern=r'^[a-f0-9]{64}$')
    label: str = Field(min_length=1)


class NativePlanQueryV2(NativePlanQueryV1):
    schema_: Literal['dmb_native_plan_query_v2'] = Field(default='dmb_native_plan_query_v2', alias='schema')
    assertion_matches: tuple[NativePlanAssertionMatchV1, ...]

    @model_validator(mode='after')
    def assertion_closure(self):
        ids = [m.assertion_id for m in self.assertion_matches]
        if len(ids) != len(set(ids)) or any(not set(m.discovered_entity_ids) <= set(self.discovered_entity_ids)
                for m in self.assertion_matches):
            raise ValueError('Native assertion matches differ from discovered entities')
        return self


def selection_handle(query, match):
    return 'native-assertion:' + digest({'query': query.sha256, 'assertion': match.assertion_id})


class NativePlanAssertionReadAuthorizedV1(Strict):
    kind: Literal['native_plan_assertion_read_authorized_v1'] = 'native_plan_assertion_read_authorized_v1'
    event_id: UUID
    sequence: int = Field(ge=0, strict=True)
    provider_attempt_id: UUID
    query_sha256: str = Field(pattern=r'^[a-f0-9]{64}$')
    assertion_ids: tuple[str, ...] = Field(min_length=1)

    @model_validator(mode='after')
    def distinct(self):
        if len(self.assertion_ids) != len(set(self.assertion_ids)):
            raise ValueError('Assertion selection repeats an ID')
        return self


class NativeAssertionLocationV1(Strict):
    evidence_ref_id: str = Field(min_length=1)
    source_artifact_id: str = Field(min_length=1)
    source_revision_id: str = Field(min_length=1)
    body_sha256: str = Field(pattern=r'^[a-f0-9]{64}$')
    start_byte: int = Field(ge=0, strict=True)
    end_byte: int = Field(gt=0, strict=True)
    span_sha256: str = Field(pattern=r'^[a-f0-9]{64}$')


class NativeAssertionSpanV1(NativeAssertionLocationV1):
    text: str = Field(min_length=1)

    @model_validator(mode='after')
    def exact_bytes(self):
        if (self.end_byte - self.start_byte != len(self.text.encode())
                or sha256(self.text.encode()).hexdigest() != self.span_sha256):
            raise ValueError('Native assertion support span bytes differ')
        return self


class NativePlanAssertionReadV1(Strict):
    # Reuse Core's complete wire contracts, including every qualification.
    assertion: Assertion
    evidence: tuple[EvidenceRefV3, ...]
    spans: tuple[NativeAssertionSpanV1, ...] = Field(min_length=1)

    @model_validator(mode='after')
    def support_closure(self):
        refs = {e.evidence_ref_id: e for e in self.evidence}
        spans = {s.evidence_ref_id: s for s in self.spans}
        if (len(refs) != len(self.evidence) or len(spans) != len(self.spans)
                or set(refs) != set(self.assertion.metadata.evidence_ref_ids)
                or set(spans) != {i for i, e in refs.items() if e.evidence_role == 'support'}):
            raise ValueError('Native assertion evidence closure differs')
        for i, span in spans.items():
            ref = refs[i]
            if (not ref.can_open_source or not ref.can_highlight_span or not ref.source_span_ref_id
                    or (ref.source_artifact_id, ref.source_revision_id) != (span.source_artifact_id, span.source_revision_id)):
                raise ValueError('Native assertion requires exact openable supporting spans')
        return self


class NativePlanAssertionReadObservedV1(Strict):
    kind: Literal['native_plan_assertion_read_observed_v1'] = 'native_plan_assertion_read_observed_v1'
    event_id: UUID
    sequence: int = Field(ge=0, strict=True)
    authorization_event_id: UUID
    reads: tuple[NativePlanAssertionReadV1, ...]
    unavailable_assertion_ids: tuple[str, ...]
    status: Literal['complete', 'partial']

    @model_validator(mode='after')
    def inventory(self):
        ids = [r.assertion.assertion_id for r in self.reads]
        if (len(ids) != len(set(ids)) or len(self.unavailable_assertion_ids) != len(set(self.unavailable_assertion_ids))
                or set(ids) & set(self.unavailable_assertion_ids)
                or (self.status == 'partial') != bool(self.unavailable_assertion_ids)):
            raise ValueError('Native assertion read inventory differs')
        return self


def validate_execution(receipt, execution):
    from .native_plan_statements import validate_execution as validate_selected_reads
    validate_selected_reads(receipt, execution)


def selected_reads(turn):
    return tuple((e, r) for e in turn.graph_context_execution.events
        if isinstance(e, NativePlanAssertionReadObservedV1) for r in e.reads)


def model_frame(turn):
    query = turn.graph_context_receipt.native_query
    return {'schema': 'dmb_plan_native_assertion_frame_v1',
        'authority': query.authority.model_dump(mode='json', by_alias=True),
        'status': 'partial' if input_partial(turn) else 'complete',
        'gap_codes': list(query.gap_codes), 'universal_absence_claimed': False,
        'assertions': [{'assertion_handle': 'assertion:' + digest({'query': query.sha256,
            'read': str(event.event_id), 'assertion': read.assertion.assertion_id}),
            'assertion': read.assertion.model_dump(mode='json'),
            'evidence': [e.model_dump(mode='json') for e in read.evidence],
            'supporting_sources': [s.model_dump(exclude={'text'}) for s in read.spans]}
            for event, read in selected_reads(turn)]}


def input_partial(turn):
    query = getattr(turn.graph_context_receipt, 'native_query', None)
    return isinstance(query, NativePlanQueryV2) and (query.status == 'partial' or any(
        isinstance(e, NativePlanAssertionReadObservedV1) and e.status == 'partial'
        for e in turn.graph_context_execution.events))


def producing_reads(turn, authorization, raw):
    from . import types as t
    if not isinstance(getattr(turn.graph_context_receipt, 'native_query', None), NativePlanQueryV2):
        return ()
    from .plan_jev_graph_packet import frame_in_request
    frame = frame_in_request(raw)
    if (not isinstance(authorization, t.PlanNativeWriterAuthorizedV2)
            or sha256(raw.encode()).hexdigest() != authorization.envelope_sha256
            or digest(frame) != authorization.frame_sha256 or frame.get('native_assertions') != model_frame(turn)):
        raise ValueError('Native assertions differ from actual producing input')
    reads = selected_reads(turn)
    if set(authorization.native_assertion_read_event_ids) != {e.event_id for e in turn.graph_context_execution.events
            if isinstance(e, NativePlanAssertionReadObservedV1)}:
        raise ValueError('Native assertion exposure differs from producing authorization')
    return tuple((row['assertion_handle'], event, read) for row, (event, read)
        in zip(model_frame(turn)['assertions'], reads, strict=True))


class NativeAssertionCitationV1(NativeAssertionLocationV1):
    segment_index: int = Field(ge=0, strict=True)
    assertion_id: str = Field(min_length=1)
    read_event_id: UUID
    provider_attempt_id: UUID
    envelope_sha256: str = Field(pattern=r'^[a-f0-9]{64}$')
    context_receipt_sha256: str = Field(pattern=r'^[a-f0-9]{64}$')
    managed_world_id: str
    native_world_id: str
    read_revision_id: str
    assertion_sha256: str = Field(pattern=r'^[a-f0-9]{64}$')

    @model_validator(mode='after')
    def exact_bytes(self):
        if self.start_byte >= self.end_byte:
            raise ValueError('Empty native assertion citation')
        return self


def citation(receipt, authorization, event, read, span, *, index):
    authority = receipt.native_query.authority
    return NativeAssertionCitationV1(**span.model_dump(exclude={'text'}), segment_index=index,
        assertion_id=read.assertion.assertion_id, read_event_id=event.event_id,
        provider_attempt_id=authorization.provider_attempt_id, envelope_sha256=authorization.envelope_sha256,
        context_receipt_sha256=receipt.context_receipt_sha256, managed_world_id=authority.managed_world_id,
        native_world_id=authority.native_world_id, read_revision_id=authority.revision_id,
        assertion_sha256=digest(read.assertion))


def validate_citations(completion, receipt, execution, authorization):
    from . import types as t
    if not isinstance(getattr(receipt, 'native_query', None), NativePlanQueryV2):
        if getattr(completion, 'native_assertion_citations', ()):
            raise ValueError('Native assertion citations require their query')
        return
    if not isinstance(completion, t.SurfaceEvidenceCompletionV7):
        raise ValueError('Native assertion query requires its exact completion')
    validate_execution(receipt, execution)
    reads = {(e.event_id, r.assertion.assertion_id): (e, r) for e in execution.events
        if isinstance(e, NativePlanAssertionReadObservedV1) and e.event_id in authorization.native_assertion_read_event_ids for r in e.reads}
    seen, cited = set(), {}
    for item in completion.native_assertion_citations:
        key = item.segment_index, item.read_event_id, item.assertion_id, item.evidence_ref_id
        pair = reads.get((item.read_event_id, item.assertion_id))
        if key in seen or pair is None or item.segment_index >= len(completion.answer_segments):
            raise ValueError('Native assertion citation lacks exact included support')
        event, read = pair
        span = next((s for s in read.spans if s.evidence_ref_id == item.evidence_ref_id), None)
        segment = completion.answer_segments[item.segment_index]
        if (span is None or not isinstance(segment, t.NativeAssertionClaimV1)
                or item.assertion_id not in segment.assertion_ids
                or item != citation(receipt, authorization, event, read, span, index=item.segment_index)):
            raise ValueError('Native assertion citation changed original source support')
        seen.add(key)
        cited.setdefault(item.segment_index, set()).add(item.assertion_id)
    for i, segment in enumerate(completion.answer_segments):
        if isinstance(segment, t.NativeAssertionClaimV1):
            included = [reads[(c.read_event_id, c.assertion_id)][1] for c in completion.native_assertion_citations if c.segment_index == i]
            metadata = {digest(r.assertion.metadata): r.assertion.metadata for r in included}
            if (set(segment.assertion_ids) != cited.get(i, set())
                    or {digest(m) for m in segment.qualifications} != set(metadata)):
                raise ValueError('Native assertion claim omitted its support or qualifications')
            expected = {(i, event.event_id, read.assertion.assertion_id, span.evidence_ref_id)
                for event, read in reads.values() if read.assertion.assertion_id in segment.assertion_ids for span in read.spans}
            if {key for key in seen if key[0] == i} != expected:
                raise ValueError('Native assertion claim omitted a supporting span')
