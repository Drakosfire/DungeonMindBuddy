"""Deterministic current native answer normalization, shared by runtime and APP.

A parsed base partition is not an actual captured provider response. General
input/output proof and atomic acceptance remain mandatory at their owners.
"""
from __future__ import annotations

import re
from typing import Annotated, Protocol
from uuid import UUID
from urllib.parse import urlencode

from pydantic import TypeAdapter, ValidationError

from . import types as t
from .source_writer_output import strict_json
from .rules_authority_types import canonical_bytes

MAX_NATIVE_OUTPUT_BYTES = 262144


class NativeAnswerError(ValueError):
    def __init__(self, stage: str, reason: str):
        super().__init__('Native answer failed its pinned evidence contract')
        self.stage, self.reason = stage, reason


class GraphClaimSupport(Protocol):
    """Parent-derived target closure for the exact actual producing envelope."""
    provider_attempt_id: UUID
    envelope_sha256: str
    context_receipt_sha256: str
    graph_revision: str
    closures: tuple[tuple[str, str, tuple[str, ...]], ...]


def _target_claim(segment, support, receipt, auth):
    if set(segment) != {'kind','claim_id','text','target_kind','target_id'}:
        raise ValueError('Graph claim must select a target without evidence metadata')
    if (support is None or support.provider_attempt_id != auth.provider_attempt_id
            or support.envelope_sha256 != auth.envelope_sha256
            or support.context_receipt_sha256 != receipt.context_receipt_sha256
            or support.graph_revision != receipt.graph_authority.graph_revision):
        raise ValueError('Graph support differs from the actual producing envelope')
    matches={refs for kind,target,refs in support.closures
        if kind==segment['target_kind'] and target==segment['target_id']}
    if len(matches)!=1:
        raise ValueError('Graph target has absent or ambiguous complete evidence')
    return {**segment,'graph_revision':support.graph_revision,'evidence_ref_ids':list(next(iter(matches)))}


def parse_native_answer(raw: str, turn: t.Turn, producer: UUID, *, support: GraphClaimSupport | None = None):
    if not isinstance(raw,str):
        raise NativeAnswerError('json','invalid_json')
    try:
        size=len(raw.encode('utf-8'))
    except UnicodeError as exc:
        raise NativeAnswerError('json','invalid_json') from exc
    if size>MAX_NATIVE_OUTPUT_BYTES:
        raise NativeAnswerError('json','output_limit')
    try:
        candidate=strict_json(raw)
    except (ValueError,TypeError,RecursionError) as exc:
        raise NativeAnswerError('json','invalid_json') from exc
    return normalize_native_answer(candidate,turn,producer,support=support)


def normalize_native_answer(candidate, turn: t.Turn, producer: UUID, *, support: GraphClaimSupport | None = None):
    """Normalize an actual parsed base object; no SQL/SDK/corpus reads or writes."""
    receipt,execution=turn.graph_context_receipt,turn.graph_context_execution
    play=isinstance(receipt,t.PlayWorldGraphContextReceiptV1) and isinstance(execution,t.PlayWorldGraphExecutionV1)
    plan=isinstance(receipt,t.PlanWorldGraphContextReceiptV1) and isinstance(execution,t.PlanWorldGraphExecutionV3)
    if not (play or plan):
        raise NativeAnswerError('authority','native_owner_missing')
    from .surface_evidence_answer import POLICY, normalize as normalize_evidence
    if isinstance(candidate, dict) and candidate.get('schema') in {POLICY,'dmb_surface_evidence_answer_v1'}:
        try:
            return normalize_evidence(candidate, turn, producer, support)
        except (ValueError, KeyError, TypeError, StopIteration) as exc:
            raise NativeAnswerError('binding', 'mixed_evidence_binding') from exc
    if getattr(support, 'current_policy', False):
        raise NativeAnswerError('shape', 'current_evidence_contract_required')
    if isinstance(candidate, dict) and candidate.get('schema') == 'dmb_surface_source_answer_v1':
        from .surface_source_answer import normalize_surface_answer
        try:
            return normalize_surface_answer(candidate, turn, producer, support)
        except (ValueError, KeyError, TypeError, StopIteration) as exc:
            raise NativeAnswerError('binding', 'source_passage_binding') from exc
    stage,reason='shape','top_level_shape'
    try:
        two={'answer_context_status','answer_segments'}
        target_only=isinstance(candidate,dict) and set(candidate)==two
        if not target_only and (play or not isinstance(candidate,dict) or set(candidate)!=two|{'citation_map'}):
            raise ValueError('Native answer has unknown top-level fields')
        if len(canonical_bytes(candidate))>MAX_NATIVE_OUTPUT_BYTES:
            raise ValueError('Native parsed base exceeds its UTF8 bound')
        stage,reason='evidence','producing_attempt_missing'
        auth=next(e for e in execution.events if isinstance(e,t.ProviderAttemptAuthorizedEventV3) and e.provider_attempt_id==producer)
        segments=candidate['answer_segments']
        stage,reason='shape','segment_shape'
        if not isinstance(segments,list):raise ValueError('Native answer segments must be a list')
        normalized=[]
        for segment in segments:
            if not isinstance(segment,dict):raise ValueError('Native answer segment must be an object')
            row=dict(segment)
            if row.get('kind')=='graph_claim' and target_only:
                row=_target_claim(row,support,receipt,auth)
            if plan and row.get('kind')=='plan_claim':
                stage,reason='typed','segment_attribution'
                if row.get('plan_content_sha256') not in {None,receipt.plan_basis.content_sha256}:
                    raise ValueError('Plan claim used another content digest')
                row['plan_content_sha256']=receipt.plan_basis.content_sha256
            if plan and row.get('kind')=='session_evidence_claim':
                matching=[ref for ref in turn.provenance.supporting_work if ref.kind=='session_evidence_v1'
                    and ref.object_id==row.get('run_id') and ref.revision==str(row.get('review_revision'))]
                if len(matching)!=1 or row.get('evidence_sha256') not in {None,matching[0].content_sha256}:
                    raise ValueError('Session evidence is not frozen on this turn')
                row['evidence_sha256']=matching[0].content_sha256
                url='/play?'+urlencode({'world':turn.world_id,'run':matching[0].object_id,'evidence_revision':int(matching[0].revision)})
                if (support is None or support.provider_attempt_id != auth.provider_attempt_id
                        or support.envelope_sha256 != auth.envelope_sha256
                        or support.context_receipt_sha256 != receipt.context_receipt_sha256
                        or support.graph_revision != receipt.graph_authority.graph_revision):
                    raise ValueError('Session citation lacks its actual producing input')
                titles = {title for run, revision, title in getattr(support, 'session_titles', ())
                    if (run, revision) == (matching[0].object_id, matching[0].revision)}
                if len(titles) != 1:
                    raise ValueError('Session citation has no unique frozen source title')
                title = next(iter(titles))
                title = re.sub(r'([\\\[\]])', r'\\\1', title.replace('\n', ' '))
                link = f'[{title} — notes and reflections]({url})'
                pattern = r'\[[^\]\n]*\]\(\s*' + re.escape(url) + r'\s*\)'
                text, count = re.subn(pattern, lambda _match: link, row.get('text', ''))
                row['text'] = text if count else text + ' ' + link
            normalized.append(row)
        if target_only:
            entries=[{**{key:row[key] for key in ('claim_id','target_kind','target_id','graph_revision','evidence_ref_ids')},
                'source_opened':False} for row in normalized if row.get('kind')=='graph_claim']
            citations={'entries':entries} if entries else None
        else:citations=candidate['citation_map']
        stage,reason='typed','citation_shape'
        if citations is not None:
            if not isinstance(citations,dict) or set(citations)!={'entries'}:raise ValueError('Unknown citation map fields')
            entries=citations['entries']
            if not isinstance(entries,list):raise ValueError('Citation entries must be a list')
            included=set(t.included_passage_event_ids(auth))
            reads=[read for event in execution.events if isinstance(event,t.SOURCE_PASSAGE_EVENTS)
                and event.event_id in included for read in event.receipts
                if read.outcome in {'enough','partial','truncated'} and read.content_sha256 is not None and read.returned_chars>0]
            derived=[]
            for entry in entries:
                if (not isinstance(entry,dict) or set(entry)!={'claim_id','target_kind','target_id','graph_revision','evidence_ref_ids','source_opened'}
                        or entry['source_opened'] is not False):raise ValueError('Model cannot assert source opening')
                refs=entry['evidence_ref_ids']
                ids=sorted({read.source_read_id for read in reads if isinstance(refs,list) and read.evidence_ref_id in refs})
                derived.append({**entry,'source_opened':bool(ids),'source_read_ids':ids})
            citations={'schema':'dmb_graph_citation_map_v2','context_receipt_sha256':receipt.context_receipt_sha256,'entries':derived}
        cls=t.PlayWorldGraphCompletionV1 if play else t.PlanWorldGraphCompletionV2
        fields=cls.model_fields
        stage,reason='typed','completion_schema'
        TypeAdapter(fields['answer_context_status'].annotation).validate_python(candidate['answer_context_status'])
        stage,reason='typed','segment_schema'
        field=fields['answer_segments']
        typed=TypeAdapter(Annotated[field.annotation,*field.metadata]).validate_python(normalized)
        stage,reason='typed','citation_schema'
        citations=TypeAdapter(fields['citation_map'].annotation).validate_python(citations)
        stage,reason='evidence','producing_attempt_missing'
        operations={e.event_id:e for e in execution.events if isinstance(e,t.ValidatedGraphOperationEventV1)}
        bindings={}
        for segment in typed:
            if not isinstance(segment,t.PlanWorldGraphClaimSegmentV1):continue
            initial=receipt.assembled_input.dispatched_assertion_ids if segment.target_kind=='assertion' else receipt.assembled_input.dispatched_relationship_ids
            initial_support=segment.target_id in initial and set(segment.evidence_ref_ids).issubset(receipt.assembled_input.dispatched_evidence_ref_ids)
            supported=[identity for identity in auth.included_graph_event_ids if identity in operations
                and segment.target_id in (operations[identity].assertion_ids if segment.target_kind=='assertion' else operations[identity].relationship_ids)
                and set(segment.evidence_ref_ids).issubset(operations[identity].evidence_ref_ids)]
            if not initial_support and not supported:raise ValueError('Graph claim lacks producing-envelope support')
            bindings[segment.claim_id]=[] if initial_support else supported[:1]
        stage,reason='binding','completion_binding'
        status=t.derive_graph_execution_evidence_status_for_scope(context_receipt_sha256=receipt.context_receipt_sha256,
            answer_segments=typed,citation_map=citations,inputs=t._ask_graph_validation_inputs(receipt),execution=execution,
            producing_provider_attempt_id=producer,claim_graph_event_ids=bindings,source_scope=execution.policy.source_read_scope)
        if play:status={'plan_only_graph_unused':'play_only_graph_unused','plan_only_insufficient_evidence':'play_only_insufficient_evidence'}.get(status,status)
        stage,reason='typed','completion_schema'
        completion=cls.model_validate({'schema':'dmb_play_world_graph_completion_v1' if play else 'dmb_plan_world_graph_completion_v2',
            'context_receipt_sha256':receipt.context_receipt_sha256,'answer_basis':t.play_answer_basis(typed) if play else t.plan_answer_basis(typed),
            'answer_context_status':status,'answer_segments':typed,'citation_map':citations})
        stage,reason='binding','completion_binding'
        t.validate_execution_completion(completion,receipt,execution,producer,bindings)
        if plan:t.validate_session_evidence_claims(completion.answer_segments,turn.provenance)
        return completion,bindings,'\n'.join(segment.text for segment in completion.answer_segments)
    except (ValueError,KeyError,StopIteration,TypeError) as exc:
        if isinstance(exc,ValidationError) and (stage,reason)==('typed','completion_schema'):
            roots={str(e['loc'][0]) for e in exc.errors(include_input=False) if e['loc']}
            reason='segment_schema' if 'answer_segments' in roots else 'citation_schema' if 'citation_map' in roots else reason
        elif (isinstance(exc,t.GraphCompletionValidationError) and isinstance(exc.rejection_code,t.GraphCompletionRejectionCode)
                and (stage,reason)==('binding','completion_binding')):
            reason=exc.rejection_code.value
        raise NativeAnswerError(stage,reason) from exc
