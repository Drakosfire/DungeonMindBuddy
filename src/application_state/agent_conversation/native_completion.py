"""Shared native answer normalization through existing evidence/capture owners.

Pure component proof, not Turn admission. Actual surface work, Rules composition,
atomic persistence, historical readers and caller cutover remain activation gates.
"""
from hashlib import sha256
from typing import Annotated, Literal
from uuid import UUID
from types import SimpleNamespace

from pydantic import Field, model_validator

from . import types as t
from . import native_corpus as bodies
from . import native_plan_statements as statements
from . import native_plan_assertions as assertions
from .native_writer import verify_input_records
from .native_statement_input import Strict
from .native_rules_output import verify_captured_text
from .rules_authority_types import canonical_bytes, canonical_sha256
from .source_writer_output import require_captured_answer, strict_json, RequestedDetailGap, gap_messages, LIMITATIONS
from .surface_evidence_answer import (native_fact_segment, status_for, _limit,
    authored_block_index, authored_selected_segment, validate_authored_shape)

NativeSegment = Annotated[
    t.SourcePassageClaimV1 | t.NativeAssertionClaimV1 | t.SurfaceAuthoredExcerptV1 | t.SessionSummaryV1
    | t.PlanWorldGraphProposalSegmentV1 | t.SurfaceLimitationV1,
    Field(discriminator='kind'),
]


class SurfaceNativeCompletionV1(Strict):
    schema_: Literal['dmb_surface_native_completion_v1'] = Field(default='dmb_surface_native_completion_v1', alias='schema')
    surface_id: Literal['build', 'plan', 'play']
    context_receipt_sha256: str = Field(pattern=r'^[a-f0-9]{64}$')
    producing_provider_attempt_id: UUID
    answer_basis: Literal['mixed_evidence'] = 'mixed_evidence'
    answer_context_status: t.SurfaceEvidenceStatusV1
    answer_segments: list[NativeSegment] = Field(min_length=1, max_length=128)
    native_body_citations: list[t.NativeBodyExcerptCitationV1] = Field(max_length=t.MAX_CITATION_SOURCE_READ_IDS)
    native_clause_citations: list[t.NativeStatementClauseCitationV1] = Field(max_length=t.MAX_CITATION_SOURCE_READ_IDS)
    native_assertion_citations: list[t.NativeAssertionCitationV1] = Field(max_length=t.MAX_CITATION_SOURCE_READ_IDS)

    @model_validator(mode='after')
    def supported_shape(self):
        validate_authored_shape(self.answer_segments)
        authored=[support for segment in self.answer_segments for support in
            (segment.supports if isinstance(segment,t.SessionSummaryV1) else [segment])
            if isinstance(support,t.SurfaceAuthoredQuoteV1)]
        if authored and (self.surface_id != 'plan' or any(s.source_kind not in {'plan','session'} for s in authored)):
            raise ValueError('Shared authored excerpts require their actual Plan or session owner')
        if any(not s.text.strip() for s in self.answer_segments) or self.answer_context_status != status_for(self.answer_segments):
            raise ValueError('Native completion status differs from its typed segments')
        source = {i for i,s in enumerate(self.answer_segments) if isinstance(s,t.SourcePassageClaimV1)}
        graph = {i for i,s in enumerate(self.answer_segments) if isinstance(s,t.NativeAssertionClaimV1)}
        if source != {c.segment_index for c in [*self.native_body_citations,*self.native_clause_citations]}:
            raise ValueError('Native source claims require their exact source citation family')
        if graph != {c.segment_index for c in self.native_assertion_citations}:
            raise ValueError('Native assertions require their exact assertion citation family')
        keys = []
        for c in self.native_body_citations:
            keys.append(('body',c.segment_index,c.read_event_id))
            if (c.text_sha256 != sha256(self.answer_segments[c.segment_index].text.encode()).hexdigest()
                    or c.line_end < c.line_start):
                raise ValueError('Native body citation changed its segment text or extent')
        keys += [('statement',c.segment_index,c.statement_id) for c in self.native_clause_citations]
        keys += [('assertion',c.segment_index,c.read_event_id,c.assertion_id,c.evidence_ref_id) for c in self.native_assertion_citations]
        if len(keys) != len(set(keys)):
            raise ValueError('Native completion repeats a citation')
        for segment in self.answer_segments:
            if isinstance(segment,t.SurfaceLimitationV1) and segment != _limit(segment.code,segment.question_phrase):
                raise ValueError('Native limitation prose must come from its owner')
        if len(canonical_bytes(self)) > 1_048_576:
            raise ValueError('Native completion exceeds the existing storage budget')
        return self


def _validate_citations(completion, receipt, execution, auth, evidence):
    # Evidence is freshly reconstructed by this module's entry point, never an
    # arbitrary caller-supplied list or a second persisted inclusion manifest.
    statements.validate_citation_records(completion, receipt, auth,
        {read.support.statement_id:read for _,_,read in evidence.native_statements})
    assertions.validate_citation_records(completion, receipt, auth,
        {(event.event_id,read.assertion.assertion_id):(event,read) for _,event,read in evidence.native_assertions})
    bodies.validate_body_support_citations(completion, evidence.body_excerpts,
        producer=auth.provider_attempt_id,envelope_sha256=auth.envelope_sha256,before_sequence=auth.sequence)
    bindings = [e for e in execution.events if isinstance(e,t.CompletionBindingEventV1)]
    if bindings and (len(bindings) != 1 or bindings[0].provider_attempt_id != auth.provider_attempt_id
            or bindings[0].completion_sha256 != canonical_sha256(completion) or bindings[0].claim_graph_event_ids):
        raise ValueError('Native completion changed its stored producer binding')


def normalize_output(receipt, execution, authorization, *, prepared_request_json, raw_output_json,
                     capture, trace, world_id, conversation_id, turn_id, attempt,
                     provenance, idempotency_key, work_proof):
    """Reconstruct completion from exact producing input and final captured SDK text.

    The caller supplies its locked Turn identity and protected trace. This helper
    grants no read, write, publication, Rules or authored-work authority.
    """
    evidence = verify_input_records(receipt,execution,authorization,prepared_request_json,
        provenance=provenance,idempotency_key=idempotency_key,work_proof=work_proof,
        world_id=world_id,conversation_id=conversation_id,turn_id=turn_id,attempt=attempt)
    responses = [e for e in execution.events if isinstance(e,t.ProviderOutcomeEventV1)
        and e.provider_attempt_id == authorization.provider_attempt_id and e.outcome == 'response_received']
    if (len(responses) != 1 or not responses[0].request_id
            or responses[0].request_id != getattr(capture,'api_request_id',None)
            or any(not isinstance(e,t.CompletionBindingEventV1) for e in execution.events if e.sequence > responses[0].sequence)):
        raise ValueError('Native completion requires its final acknowledged SDK response')
    if (getattr(capture,'provider',None),getattr(capture,'model',None),getattr(capture,'api_mode',None)) != (
            authorization.provider,authorization.model,authorization.api_mode):
        raise ValueError('Native completion capture differs from its actual writer')
    if not isinstance(getattr(capture,'authorization_id',None),str) or not capture.authorization_id.strip():
        raise ValueError('Native completion lacks its actual SDK capture identity')
    verify_captured_text(capture,authorization_id=capture.authorization_id,api_request_id=responses[0].request_id,
        request_envelope_sha256=authorization.envelope_sha256,prepared_request_json=prepared_request_json,
        raw_output_json=raw_output_json,raw_output_sha256=sha256(raw_output_json.encode()).hexdigest(),
        raw_output_utf8_bytes=len(raw_output_json.encode()),response_sha256=responses[0].response_sha256)
    require_captured_answer(trace,world_id=world_id,conversation_id=conversation_id,turn_id=turn_id,
        attempt=attempt,provider_attempt_id=authorization.provider_attempt_id,
        context_receipt_sha256=receipt.context_receipt_sha256,raw_output_json=raw_output_json)
    return normalize_candidate(strict_json(raw_output_json),receipt,execution,authorization,evidence)


def normalize_candidate(candidate, receipt, execution, authorization, evidence):
    """Normalize the actual parsed partition after its producer/input proof.

    Mixed Rules responses have one captured outer body. Their base partition
    uses this same algorithm without manufacturing a second provider response.
    """
    if (not isinstance(candidate,dict) or set(candidate) != {'schema','answer_segments','limitations','requested_detail_gaps'}
            or candidate['schema'] != evidence.frame['answer_policy'] or not isinstance(candidate['answer_segments'],list)):
        raise ValueError('Native completion requires its exact producing answer policy')
    segments, body_cites, statement_cites, assertion_cites = [], [], [], []
    blocks,selectors=authored_block_index(evidence.authored,str(evidence.idempotency_key))
    selected_blocks=set()
    for row in candidate['answer_segments']:
        if (not isinstance(row,dict) or row.get('kind') != 'authored_excerpt'
                and (not isinstance(row.get('text'),str) or not row['text'].strip())):
            raise ValueError('Native completion contains an invalid segment')
        if row.get('kind') in {'authored_excerpt','session_summary'}:
            segments.append(authored_selected_segment(row,blocks=blocks,selectors=selectors,selected_blocks=selected_blocks))
        elif row.get('kind') == 'proposal':
            segments.append(t.PlanWorldGraphProposalSegmentV1.model_validate(row))
        else:
            segment, body, statement, assertion = native_fact_segment(row,policy=candidate['schema'],
                receipt=receipt,auth=authorization,support=evidence,index=len(segments))
            segments.append(segment)
            body_cites.extend(body)
            statement_cites.extend(statement)
            assertion_cites.extend(assertion)
    codes = candidate['limitations']
    if (not isinstance(codes,list) or any(not isinstance(code,str) or code not in LIMITATIONS for code in codes)
            or len(codes) != len(set(codes)) or not isinstance(candidate['requested_detail_gaps'],list)):
        raise ValueError('Native completion contains an invalid limitation')
    gaps = [RequestedDetailGap.model_validate(g) for g in candidate['requested_detail_gaps']]
    gap_messages(SimpleNamespace(requested_detail_gaps=gaps), {'user_question':execution.policy.action.intent.message})
    codes = list(codes)
    if gaps and 'missing_requested_details' not in codes:
        codes.append('missing_requested_details')
    if evidence.frame['input_status'] == 'partial' and 'partial_retrieval' not in codes:
        codes.append('partial_retrieval')
    segments += [_limit(code) for code in codes] + [_limit('missing_requested_details',g.question_phrase) for g in gaps]
    if not segments:
        segments = [_limit('missing_requested_details')]
    completion = SurfaceNativeCompletionV1(surface_id=execution.policy.action.surface_id,
        context_receipt_sha256=receipt.context_receipt_sha256,producing_provider_attempt_id=authorization.provider_attempt_id,
        answer_context_status=status_for(segments),answer_segments=segments,
        native_body_citations=body_cites,native_clause_citations=statement_cites,native_assertion_citations=assertion_cites)
    _validate_citations(completion,receipt,execution,authorization,evidence)
    return completion


def verify_completion(completion, receipt, execution, authorization, **producing_proof):
    """No stored or caller-mutated completion can replace exact output reconstruction."""
    expected = normalize_output(receipt,execution,authorization,**producing_proof)
    if type(completion) is not SurfaceNativeCompletionV1 or canonical_sha256(completion) != canonical_sha256(expected):
        raise ValueError('Native completion differs from its exact producing output')
    return expected
