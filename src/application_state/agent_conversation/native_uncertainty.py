"""Current shared-native uncertainty wire; historical projection stays separate.

Typed references prove structure and citation ownership, never semantic absence
or contradiction. Raw declarations remain retained for independent assessment.
"""
from types import SimpleNamespace
from typing import Annotated, Literal

from pydantic import Field, TypeAdapter

from .native_statement_input import Strict
from .source_writer_output import RequestedDetailGap, gap_messages, surface_limitation

POLICY = 'dmb_surface_evidence_answer_v9'
FORMAT = 'surface_native_evidence_selectors_v2'
INSTRUCTIONS = '''Current answer policy: dmb_surface_evidence_answer_v9.
Return only {"schema":"dmb_surface_evidence_answer_v9","answer_segments":[...],
"uncertainties":[]} (or this object inside Rules base_output). Include collaboration
only when the strict schema offers it. Use only offered kinds and exact selectors.
Answer the current question directly from relevant supplied material. Dialogue and
entity labels are navigation/context, not independent evidence. Ground every factual
clause in its own selected supports; split statements with different support.

- native_body_claim: text plus excerpt_handles. Selected body excerpts are attributed
source text, not published Graph facts. Select every needed excerpt. An asked question
does not supply its answer; a plan to investigate does not establish a discovery.
- native_statement_report: text plus statement_handles. Preserve reporter, episodes,
uncertainty and nonfactive embedded content; what a source says is not proof it occurred.
- native_assertion_claim: text plus assertion_handles. Preserve claim_mode,
epistemic_basis, standing, temporal_scope, scope and all supplied qualifications.
- authored_excerpt: exact selection_id only. The host supplies literal saved text.
Do not emit quote text, offsets or formatting; select each ID at most once.
- session_summary: source-attributed text plus every needed session selection_id in
selection_ids. Only supplied session notes/reflections support this kind, not Plan
text, body excerpts or dialogue. It is a synthesis of GM recollections, not a quote
or publication of World facts. Prefer supported synthesis for a concise briefing.
- Offered Build draft_reference_claim, related_page_claim, saved_source_claim and
discussion follow their exact schema. Draft/page discussion does not establish World
facts; saved_source_claim requires its actual section_read_ids.
When the schema requires supporting_quotes, copy exact literal supporting text from
those selected saved reads; do not paraphrase, borrow draft text or invent a quote.
- proposal: explicitly hypothetical text with label invented_idea. For a requested
image prompt use label image_prompt and a complete visual prompt without citation
metadata or generation claims. Grounding discussion alone is not a generation request.

Determine an event's status from its supporting passage's heading, tense, speaker
and conditions, not the document's overall label or nearby retrospective prose.
A plan, proposal, belief or hypothetical does not by itself establish that its
described event occurred. Preserve local uncertainty and chronology; do not promote
uncertain occurrence to a played event. Textual order does not prove story chronology
or causality. Do not infer campaign/session scope from a title or filename. Notes and
reflections are not external recaps. Host citations supply source names and locators;
do not add inferred labels, citation URLs, revisions, hashes or authority metadata.
Only explicitly selected full_document rows represent complete documents. Partial
discovery, sections, lexical navigation or no matches never proves universal absence.

uncertainties is the sole uncertainty declaration channel:
- {"kind":"missing_detail","question_phrase":"exact phrase from user_question"}
only when supplied material does not establish that requested detail. Phrases must
occur exactly once in the question and be distinct and nonoverlapping. Check your
answer before declaring a gap: do not call a detail missing if your supported answer
already supplies it. Do not equate partial retrieval with an unanswered question.
- {"kind":"source_conflict","explanation_segment_index":0} only for genuinely
incompatible supported accounts. The index selects an existing answer_segments entry
whose cited prose identifies the competing accounts and their incompatibility.
Eligible kinds are native_body_claim, native_statement_report,
native_assertion_claim and saved_source_claim. Different plans, beliefs, times or
compatible qualifications are not automatically a conflict. Use each index once.
Indices are raw Base indices, not Rules indices, collaboration or host caveats.
The host derives retrieval qualification; never emit partial_retrieval, limitations,
requested_detail_gaps or answer_context_status. Do not duplicate warnings in uncited
prose. If no requested fact can be answered, use no unrelated filler and explicitly
declare the missing requested detail. A collaboration-only response needs no invented
gap. These declarations do not authorize edits or claim any action already happened.
'''
CONFLICT_KINDS = frozenset({
    'native_assertion_claim', 'native_body_claim', 'native_statement_report',
    'saved_source_claim',
})


def producing_policy(body):
    """Select the codec from bound producing bytes, never candidate JSON.

    Full schema equality belongs to producer authorization. Historical captures
    can omit a response format; a present format must identify a known codec and
    agree with its direct or Rules Base policy literal.
    """
    from .native_plan_assertions import POLICY as historical
    text = body.get('text', {})
    if not isinstance(text, dict):
        raise ValueError('Malformed native producing text options')
    if 'format' not in text:
        return historical
    format_ = text['format']
    if not isinstance(format_, dict):
        raise ValueError('Malformed native producing format')
    expected = {FORMAT: POLICY, 'surface_native_evidence_selectors_v1': historical}.get(format_.get('name'))
    schema = format_.get('schema')
    if (expected is None or format_.get('type') != 'json_schema'
            or format_.get('strict') is not True or not isinstance(schema, dict)):
        raise ValueError('Unknown native producing codec')
    def literal(value):
        properties = value.get('properties') if isinstance(value, dict) else None
        marker = properties.get('schema') if isinstance(properties, dict) else None
        return marker.get('const') if isinstance(marker, dict) else None
    if literal(schema) == 'dmb_rules_mixed_answer_v1':
        definitions = schema.get('$defs')
        schema = definitions.get('Base') if isinstance(definitions, dict) else None
    if literal(schema) != expected:
        raise ValueError('Native producing marker and policy disagree')
    return expected


class MissingDetail(Strict):
    kind: Literal['missing_detail']
    question_phrase: str = Field(strict=True, min_length=1, max_length=256)


class SourceConflict(Strict):
    kind: Literal['source_conflict']
    explanation_segment_index: int = Field(strict=True, ge=0)


Uncertainty = Annotated[MissingDetail | SourceConflict, Field(discriminator='kind')]
_items = TypeAdapter(list[Uncertainty])


def project_uncertainties(raw, *, raw_segments, citation_indices, user_question,
                          host_partial, empty_answer):
    """Render existing canonical flags once, without inventing missing details.

    Indices refer to raw Base segments before host caveats. Call only after the
    existing fact owners validate every segment and its citation bindings.
    """
    if not isinstance(raw, list):
        raise ValueError('Native uncertainties require an array')
    items = _items.validate_python(raw, strict=True)
    gaps = [RequestedDetailGap(question_phrase=item.question_phrase)
            for item in items if isinstance(item, MissingDetail)]
    # Reuse exact-question uniqueness, nonoverlap and display-safety validation.
    gap_messages(SimpleNamespace(requested_detail_gaps=gaps),
                 {'user_question': user_question})
    references = set()
    codes = []
    for item in items:
        if isinstance(item, MissingDetail):
            code = 'missing_requested_details'
        else:
            index = item.explanation_segment_index
            if (index in references or index >= len(raw_segments)
                    or raw_segments[index].get('kind') not in CONFLICT_KINDS
                    or index not in citation_indices):
                raise ValueError('Conflict requires a distinct cited factual Base segment')
            references.add(index)
            code = 'unresolved_conflict'
        if code not in codes:
            codes.append(code)
    if empty_answer and not gaps:
        raise ValueError('Empty native answer requires an explicit missing detail')
    if host_partial:
        codes.append('partial_retrieval')
    return [surface_limitation(code) for code in codes]
