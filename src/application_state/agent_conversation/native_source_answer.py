"""Source-only section citations from exact producing input; never Graph authority."""
from dataclasses import dataclass
from hashlib import sha256

from . import types as t
from .native_source_input import prove_input, section_handle, source_name, CAPABILITIES


@dataclass(frozen=True)
class NativeSectionSupport:
    handle: str
    read: t.NativeSourceSectionObservedV1
    source_name: str


def producing_sections(turn, authorization, raw):
    execution = turn.graph_context_execution
    if not isinstance(execution.policy,CAPABILITIES):
        return ()
    witnesses = [e for e in execution.events if isinstance(e,t.NativeSourceProviderInclusionV1)
        and e.provider_attempt_id == authorization.provider_attempt_id]
    if not witnesses:
        if any(isinstance(e,t.NativeSourceSectionObservedV1) and e.outcome == 'complete'
                for e in execution.events):
            raise ValueError('Native section output lacks its actual input witness')
        return ()
    if len(witnesses) != 1:
        raise ValueError('Native section output has ambiguous producing inclusion')
    stored = witnesses[0]
    derived = prove_input(turn,authorization,raw,sequence=stored.sequence,event_id=stored.event_id)
    if derived != stored:
        raise ValueError('Native section output differs from its actual producing input')
    reads = {e.event_id:e for e in execution.events if isinstance(e,t.NativeSourceSectionObservedV1)}
    handle_for=section_handle
    if isinstance(authorization,t.PlanJevWriterAuthorizedV1):
        from .plan_jev_graph_packet import frame_in_request
        from .plan_source_selectors import FRAME_SCHEMA, source_selector
        if frame_in_request(raw).get('schema') in {FRAME_SCHEMA,'dmb_plan_jev_writer_frame_v4'}:
            handle_for=lambda read:source_selector(turn,read)
    return tuple(NativeSectionSupport(handle_for(reads[identity]),reads[identity],
        source_name(execution,reads[identity])) for identity in stored.read_event_ids)


def citation(section, *, index, text, producer, envelope_sha256):
    read = section.read
    return t.NativeSourceSectionCitationV1(segment_index=index,text_sha256=sha256(text.encode()).hexdigest(),
        provider_attempt_id=producer,envelope_sha256=envelope_sha256,read_event_id=read.event_id,
        catalog_event_id=read.catalog_event_id,source_artifact_id=read.source_artifact_id,
        native_source_revision_id=read.native_source_revision_id,app_source_revision_id=read.app_source_revision_id,
        content_sha256=read.content_sha256,excerpt_sha256=read.excerpt_sha256,
        section_id=read.section.section_id,selector_policy='markdown_sections_v1',
        source_name=section.source_name,section_title=read.section.label,
        line_start=read.section.line_start,line_end=read.section.line_end)


def validate_citations(completion, receipt, execution, producer):
    if not isinstance(completion,t.SurfaceEvidenceCompletionV3):return
    if not isinstance(execution.policy,CAPABILITIES):
        raise ValueError('Native source completion requires its explicit frozen capability')
    witnesses = [e for e in execution.events if isinstance(e,t.NativeSourceProviderInclusionV1)
        and e.provider_attempt_id == producer]
    reads = {e.event_id:e for e in execution.events if isinstance(e,t.NativeSourceSectionObservedV1)
        and e.outcome == 'complete'}
    for row in completion.native_source_citations:
        read = reads.get(row.read_event_id)
        if (len(witnesses) != 1 or read is None or read.event_id not in witnesses[0].read_event_ids
                or row.provider_attempt_id != producer or row.envelope_sha256 != witnesses[0].envelope_sha256):
            raise ValueError('Native citation lacks its exact successful producing input')
        expected = citation(NativeSectionSupport(section_handle(read),read,source_name(execution,read)),
            index=row.segment_index,text=completion.answer_segments[row.segment_index].text,
            producer=producer,envelope_sha256=witnesses[0].envelope_sha256)
        if row != expected:
            raise ValueError('Native citation changed source name, range or immutable identity')
