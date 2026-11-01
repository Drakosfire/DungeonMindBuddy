"""Native mixed evidence: exact source selections, authored quotes, closed limits.

No retrieval, provider call, SQL, or semantic entailment judge. Input proof remains
with the native producer; quote support is reconstructed from that exact envelope.
"""
from dataclasses import dataclass
from hashlib import sha256
from types import SimpleNamespace
import json

from . import types as t
from .rules_authority_types import canonical_sha256, canonical_bytes
from .source_writer_output import LIMITATIONS, RequestedDetailGap, gap_messages, strict_json

HISTORICAL_POLICY = 'dmb_surface_evidence_answer_v1'
POLICY = 'dmb_surface_evidence_answer_v2'
HISTORICAL_INSTRUCTIONS = '''Current answer policy: dmb_surface_evidence_answer_v1.
Return only {"schema":"dmb_surface_evidence_answer_v1","answer_segments":[...],
"limitations":[],"requested_detail_gaps":[]} (or this object inside Rules base_output).
Use the actual supplied evidence, never dialogue as independent authority.
Every factual segment must use exactly one of these shapes:
- {"kind":"graph_claim","claim_id":"claim:1","text":"prose","target_kind":"assertion or relationship","target_id":"exact complete admitted target","passage_handles":[]}.
Graph prose must describe that specific admitted fact. Select only opened passage handles
that actually support this claim and belong to its evidence; [] explicitly means an unopened
Graph fact. A location or family edge does not support an entity's entire history.
- {"kind":"source_passage_claim","text":"prose","passage_handles":["exact supplied passage_handle"]}.
Use this for corpus/background/motives/branches learned from opened passages, even when
Graph records are also available. Split claims with different support. Cite every passage
needed by a composite claim; prefer separately readable, precisely supported statements.
- {"kind":"authored_quote","text":"literal exact substring of selected frozen body","source_handle":"exact authored_sources handle, or Play manifest source_id"}.
Authored quotes are literal excerpts, not paraphrases. A Plan's presence never makes source
facts Plan material. Never use plan_claim, session_evidence_claim or play_context_claim.
- {"kind":"proposal","text":"explicitly hypothetical creative suggestion","label":"invented_idea"}.
For a requested image prompt use {"kind":"proposal","label":"image_prompt","text":"complete visual prompt"} and only the complete visual
prompt in text, without citation metadata or generation claims. Grounding discussion alone
is not a request to prepare or generate an image. No action tool ran.
No connective segments or arbitrary uncited explanatory facts. Keep uncertainty/beliefs,
authored possibilities and played recollections distinct in the properly cited claim prose.
Select limitation codes only from missing_requested_details, partial_retrieval,
unresolved_conflict. The host renders their wording. Do not claim corpus completeness.
requested_detail_gaps selects exact unique nonoverlapping question_phrase strings from
user_question only for requested details not established by these excerpts; include
missing_requested_details for these gaps. No paraphrased gap prose or byte offsets.
Do not emit revisions, hashes, citation maps, source-opening flags or authority metadata.
'''

INSTRUCTIONS = '''Current answer policy: dmb_surface_evidence_answer_v2.
Return only {"schema":"dmb_surface_evidence_answer_v2","answer_segments":[...],
"limitations":[],"requested_detail_gaps":[]} (or this object inside Rules base_output).
Use the actual supplied evidence, never dialogue as independent authority.
Use only segment kinds and selectors offered by the strict output schema.
The examples below apply only when their kind and selectors are offered; later
capability instructions describe additional offered kinds.
- {"kind":"graph_claim","claim_id":"claim:1","text":"prose","target_kind":"assertion or relationship","target_id":"exact complete admitted target","passage_handles":[]}.
Graph prose must describe that specific admitted fact. Select only opened passage handles
that actually support this claim and belong to its evidence; [] explicitly means an unopened
Graph fact. A location or family edge does not support an entity's entire history.
- {"kind":"source_passage_claim","text":"prose","passage_handles":["exact supplied passage_handle"]}.
Use this for corpus/background/motives/branches learned from opened passages, even when
Graph records are also available. Split claims with different support. Cite every passage
needed by a composite claim; prefer separately readable, precisely supported statements.
- {"kind":"authored_excerpt","block_handle":"exact supplied block_handle"}.
Select one exposed authored block; the host supplies its saved literal text. Do not write
text, offsets, source handles or formatting in this segment. Select multiple blocks as
separate segments. Do not paraphrase authored material as a quote. A Plan's presence never makes source
facts Plan material. Never use plan_claim, session_evidence_claim or play_context_claim.
- {"kind":"proposal","text":"explicitly hypothetical creative suggestion","label":"invented_idea"}.
For a requested image prompt use {"kind":"proposal","label":"image_prompt","text":"complete visual prompt"} and only the complete visual
prompt in text, without citation metadata or generation claims. Grounding discussion alone
is not a request to prepare or generate an image. No action tool ran.
No connective segments or arbitrary uncited explanatory facts. Keep uncertainty/beliefs,
authored possibilities and played recollections distinct in the properly cited claim prose.
Select limitation codes only from missing_requested_details, partial_retrieval,
unresolved_conflict. The host renders their wording. Do not claim corpus completeness.
requested_detail_gaps is an array of objects, each exactly
{"question_phrase":"exact phrase from user_question"}; never an array of strings.
Select exact unique nonoverlapping phrases only for requested details not established
by the supplied evidence. The host derives missing_requested_details from validated gaps.
No paraphrased gap prose or byte offsets. If no requested fact is supported, return
answer_segments:[] with the applicable limitations and these typed gap objects;
never invent evidence or quote unrelated authored material to fill the answer.
Do not emit revisions, hashes, citation maps, source-opening flags or authority metadata.
'''

NATIVE_POLICY = 'dmb_surface_evidence_answer_v3'
NATIVE_INSTRUCTIONS = INSTRUCTIONS.replace(POLICY,NATIVE_POLICY) + """
Native source sections are separate authored corpus evidence. For a claim supported
by these supplied sections use {"kind":"native_source_claim","text":"source-attributed prose",
"section_handles":["exact exposed section_handle"]}. Select every section needed.
These handles never support graph_claim or authored_excerpt; do not invent Graph
anchors, source names, revisions or citation metadata. Preserve the source's
conditional possibilities and distinguish them from played session outcomes.
"""

SELECTOR_POLICY = 'dmb_surface_evidence_answer_v4'
SELECTOR_INSTRUCTIONS = NATIVE_INSTRUCTIONS.replace(NATIVE_POLICY,SELECTOR_POLICY).replace(
    '"block_handle":"exact supplied block_handle"','"selection_id":"exact supplied selection_id"') + """
Authored selections use only selection_id values from the current supplied input.
Copy each ID exactly and select each at most once. Never emit internal block handles
or reuse an ID from a prior input. The host resolves exact saved text and ownership.
"""

PLAN_POLICY = 'dmb_surface_evidence_answer_v5'
PLAN_INSTRUCTIONS = SELECTOR_INSTRUCTIONS.replace(SELECTOR_POLICY, PLAN_POLICY) + """
For concise synthesis of supplied saved Scene notes or closing reflections use
{"kind":"session_summary","text":"source-attributed summary prose","selection_ids":["exact supplied session selection_id"]}.
Select every session block needed for that statement; split statements with different support.
Only supplied session entries support this kind, never Plan text, native source sections or dialogue.
This is a summary of GM-authored recollections, not a literal quote or a publication of World facts.
Preserve rehearsal labels, uncertainty and unresolved possibilities; never invent a causal or
chronological connection. Recommendations belong in separate explicitly hypothetical proposals.
For a requested concise briefing prefer supported synthesis over repeating entire notes.
Do not append citation URLs, source names, hashes or locator metadata; the host derives them.
"""

from .native_plan_statements import POLICY as STATEMENT_POLICY
from .native_plan_assertions import POLICY as ASSERTION_POLICY
BODY_POLICY = 'dmb_surface_evidence_answer_v6'
BODY_INSTRUCTIONS = PLAN_INSTRUCTIONS.replace(PLAN_POLICY, BODY_POLICY).replace(
    '"kind":"native_source_claim"', '"kind":"native_body_claim"').replace(
    '"section_handles":["exact exposed section_handle"]',
    '"excerpt_handles":["exact exposed excerpt_handle"]') + """
Selected native body excerpts are source-attributed text, not published Graph facts.
Use {"kind":"native_body_claim","text":"source-attributed prose",
"excerpt_handles":["exact supplied excerpt_handle"]} for their factual claims.
Select every excerpt needed and split claims with different support. These selectors
cannot support graph_claim, authored_excerpt or session_summary. Source campaign/session
scope may be unestablished; do not infer it from a title or filename. Preserve beliefs,
conditional possibilities, chronology and the distinction between proposed and played events.
Only explicitly selected full_document rows represent complete documents. Partial sections
and lexical navigation never establish corpus completeness. Do not mint citation metadata.
"""

@dataclass(frozen=True)
class AuthoredSupport:
    handle: str
    source_kind: str
    source_name: str
    object_id: str
    revision: str
    body_sha256: str
    owner_sha256: str
    text: str
    entry_identity: str | None = None
    source_ordinal: int | None = None
    entry_kind: str | None = None
    element_id: str | None = None
    checkpoint_content_sha256: str | None = None


def authored_support(kind, name, object_id, revision, owner_sha, text, entry_identity=None, *,
                     source_ordinal=None, entry_kind=None, element_id=None, checkpoint_content_sha256=None):
    if not isinstance(text, str) or not text.strip():
        raise ValueError('Authored source body must be nonblank')
    body_sha = sha256(text.encode()).hexdigest()
    identity = dict(source_kind=kind, object_id=object_id, revision=str(revision),
                    body_sha256=body_sha, owner_sha256=owner_sha)
    if entry_identity is not None:
        identity['entry_identity'] = entry_identity
    return AuthoredSupport('q' + canonical_sha256(identity), kind, name,
                          object_id, str(revision), body_sha, owner_sha, text, entry_identity,
                          source_ordinal, entry_kind, element_id, checkpoint_content_sha256)


def plan_authored_sources(turn, markdown, sessions, *, block_policy=False):
    return plan_authored_source_records(turn.graph_context_receipt.plan_basis,
        turn.provenance.supporting_work, markdown, sessions, block_policy=block_policy)


def plan_authored_source_records(basis, supporting_work, markdown, sessions, *, block_policy=False):
    """Use actual work pins, without manufacturing a Plan Turn or Graph scope."""
    if sha256(markdown.encode()).hexdigest() != basis.content_sha256:
        raise ValueError('Authored Plan differs from the frozen committed body')
    result = [authored_support('plan', 'Committed Plan', basis.document_id,
              str(basis.work_revision_id), basis.content_sha256, markdown)] if markdown.strip() else []
    frozen = {(r.object_id, r.revision): r.content_sha256 for r in supporting_work
              if r.kind == 'session_evidence_v1'}
    return tuple(result) + session_sources(sessions, frozen, block_policy=block_policy)


def session_authored_sources(turn, sessions, *, block_policy=True):
    frozen = {(r.object_id, r.revision): r.content_sha256 for r in turn.provenance.supporting_work
              if r.kind == 'session_evidence_v1'}
    return session_sources(sessions, frozen, block_policy=block_policy)


def session_sources(sessions, frozen, *, block_policy=True):
    result = []
    for session in sessions:
        key = (session['run_id'], str(session['review_revision']))
        if key not in frozen:
            raise ValueError('Session quote source lacks frozen ownership')
        for ordinal, source in enumerate(session.get('sources', [])):
            text = source.get('text', '')
            if text.strip():
                result.append(authored_support('session', session['title'] + ' — notes and reflections',
                    key[0], key[1], frozen[key], text,
                    canonical_sha256({'kind':source.get('kind'),'element_id':source.get('element_id'),'ordinal':ordinal}) if block_policy else None,
                    source_ordinal=ordinal, entry_kind=source.get('kind'), element_id=source.get('element_id'),
                    checkpoint_content_sha256=session.get('session_content_sha256')))
    return tuple(result)


def authored_frame_rows(sources, sessions):
    # Point to bodies already present once in the frame; no duplicate text or model-side hashing.
    paths = []
    if sources and sources[0].source_kind == 'plan':
        paths.append(['committed_plan_markdown'])
    paths.extend(['session_evidence', i, 'sources', j, 'text']
        for i, session in enumerate(sessions) for j, source in enumerate(session.get('sources', []))
        if source.get('text', '').strip())
    return [{'handle':s.handle, 'source_kind':s.source_kind, 'source_name':s.source_name,
             'body_path':path} for s, path in zip(sources, paths, strict=True)]



def producing_plan_authored_records(basis, supporting_work, frame, idempotency_key, *, short=True):
    """Reconstruct exact producing authored bodies using their existing owner."""
    from .authored_excerpt_blocks import restore_blocks, verify_blocks, selection_catalog, restore_selection_blocks, verify_selection_blocks
    restore=restore_selection_blocks if short else restore_blocks
    from copy import deepcopy
    sessions = deepcopy(frame['session_evidence'])
    markdown = restore(frame['committed_plan_blocks'])
    for session in sessions:
        for source in session.get('sources',[]):
            source['text'] = restore(source.pop('text_blocks'))
    result = plan_authored_source_records(basis,supporting_work,markdown,sessions,block_policy=True)
    expected = authored_frame_rows(result,sessions)
    expected = [{**row,'body_path':[('committed_plan_blocks' if x=='committed_plan_markdown' else 'text_blocks' if x=='text' else x) for x in row['body_path']]} for row in expected]
    if frame.get('authored_sources') != expected:
        raise ValueError('Authored source selectors changed their exact body/owner join')
    catalog=selection_catalog(((source.handle,source.text) for source in result),str(idempotency_key)) if short else ()
    for source,row in zip(result,expected,strict=True):
        blocks=frame
        for key in row['body_path']: blocks=blocks[key]
        if short:verify_selection_blocks(blocks,source.text,source.handle,catalog)
        else:verify_blocks(blocks,source.text,source.handle)
    return result

def producing_authored(turn, auth, raw):
    if sha256(raw.encode()).hexdigest() != auth.envelope_sha256:
        raise ValueError('Authored sources differ from the actual producer')
    if isinstance(auth, t.PlanJevWriterAuthorizedV1):
        from .plan_jev_graph_packet import frame_in_request
        frame = frame_in_request(raw)
        if canonical_sha256(frame) != auth.frame_sha256:
            raise ValueError('Authored frame changed after admission')
        if frame.get('schema') in {'dmb_plan_jev_writer_frame_v2','dmb_plan_jev_writer_frame_v3','dmb_plan_jev_writer_frame_v4','dmb_plan_jev_writer_frame_v5','dmb_plan_jev_writer_frame_v6','dmb_plan_jev_writer_frame_v7','dmb_plan_jev_writer_frame_v8'}:
            short=frame['schema'] in {'dmb_plan_jev_writer_frame_v3','dmb_plan_jev_writer_frame_v4','dmb_plan_jev_writer_frame_v5','dmb_plan_jev_writer_frame_v6','dmb_plan_jev_writer_frame_v7','dmb_plan_jev_writer_frame_v8'}
            result=producing_plan_authored_records(turn.graph_context_receipt.plan_basis,
                turn.provenance.supporting_work,frame,turn.idempotency_key,short=short)
        else:
            result = plan_authored_sources(turn, frame['committed_plan_markdown'], frame['session_evidence'])
            if frame.get('authored_sources') != authored_frame_rows(result, frame['session_evidence']):
                raise ValueError('Authored source selectors changed their exact body/owner join')
        return result
    from .play_graph_input import _user_texts
    carriers = []
    for text in _user_texts(strict_json(raw), auth.api_mode):
        try: row = strict_json(text)
        except (ValueError, TypeError): continue
        if isinstance(row, dict) and row.get('schema') in {'dmb_native_play_input_v2','dmb_native_play_input_v3','dmb_native_play_input_v4','dmb_native_play_input_v5','dmb_native_play_input_v6'}:
            from .play_graph_input import NativePlayInputV2,NativePlayInputV3,NativePlayInputV4,NativePlayInputV5,NativePlayInputV6
            carrier = ({'dmb_native_play_input_v2':NativePlayInputV2,'dmb_native_play_input_v3':NativePlayInputV3,'dmb_native_play_input_v4':NativePlayInputV4,'dmb_native_play_input_v5':NativePlayInputV5,'dmb_native_play_input_v6':NativePlayInputV6}[row['schema']]).model_validate_json(json.dumps(row))
            if carrier.submission_id == turn.idempotency_key:
                carriers.append(carrier)
    if len(carriers) != 1:
        return ()
    frame = carriers[0].resolved_source_frame() if hasattr(carriers[0],"resolved_source_frame") else carriers[0].source_frame
    receipt = turn.graph_context_receipt
    if frame.manifest != receipt.play_sources or canonical_sha256(frame) != receipt.play_source_frame_sha256:
        raise ValueError('Play quotes differ from the included frozen source frame')
    result = []
    for source, entry in zip(frame.sources, frame.manifest.entries, strict=True):
        candidate = AuthoredSupport(entry.source_id, 'play',
            'Saved scene note' if source.source_kind == 'scene_note' else 'Saved Play scene',
            source.locator.run_id, str(source.locator.run_revision), entry.text_sha256,
            entry.payload_sha256, source.text)
        result.append(candidate)
    if hasattr(carriers[0], 'resolved_sessions'):
        sessions = carriers[0].resolved_sessions()
        from .play_session_input import validate_turn_packets
        validate_turn_packets(turn,sessions)
        result.extend(session_authored_sources(turn,sessions))
    return tuple(result)


def require_current_policy(turn, auth, raw):
    body = strict_json(raw)
    if isinstance(auth, t.PlanJevWriterAuthorizedV1):
        from .plan_jev_graph_packet import frame_in_request
        frame=frame_in_request(raw)
        policy=frame.get('answer_policy')
        if frame.get('schema') == 'dmb_plan_jev_writer_frame_v8':
            if policy != ASSERTION_POLICY: raise ValueError('Native assertion frame requires its own answer policy')
        elif frame.get('schema') == 'dmb_plan_jev_writer_frame_v7':
            if policy != STATEMENT_POLICY: raise ValueError('Native query frame requires its own answer policy')
        elif frame.get('schema') == 'dmb_plan_jev_writer_frame_v6':
            if policy != BODY_POLICY: raise ValueError('Native body frame requires its exact source answer policy')
        elif frame.get('schema') == 'dmb_plan_jev_writer_frame_v5':
            if policy != PLAN_POLICY: raise ValueError('Current Plan frame requires its session summary policy')
        elif frame.get('schema') in {'dmb_plan_jev_writer_frame_v3','dmb_plan_jev_writer_frame_v4'}:
            if policy != SELECTOR_POLICY: raise ValueError('Retained Plan frame changed its selector policy')
        elif policy in {SELECTOR_POLICY, PLAN_POLICY, BODY_POLICY, STATEMENT_POLICY, ASSERTION_POLICY}:
            raise ValueError('Selector policy requires its exact Plan frame')
        return policy if policy in {ASSERTION_POLICY,STATEMENT_POLICY,BODY_POLICY,PLAN_POLICY,SELECTOR_POLICY,NATIVE_POLICY,POLICY,HISTORICAL_POLICY} else False
    from .play_graph_input import _user_texts
    policies = {_current_carrier(text, turn.idempotency_key) for text in _user_texts(body, auth.api_mode)} - {False}
    if len(policies)>1: raise ValueError('Ambiguous current answer policy')
    return next(iter(policies),False)


def _current_carrier(text, submission_id):
    try: row = strict_json(text)
    except (ValueError, TypeError): return False
    if not isinstance(row,dict): return False
    # Retained user carriers describe earlier turns, never the current policy.
    from uuid import UUID
    try:
        if UUID(str(row.get('submission_id'))) != submission_id: return False
    except ValueError:
        return False
    return PLAN_POLICY if row.get('schema')=='dmb_native_play_input_v6' else SELECTOR_POLICY if row.get('schema')=='dmb_native_play_input_v5' else NATIVE_POLICY if row.get('schema')=='dmb_native_play_input_v4' else POLICY if row.get('schema')=='dmb_native_play_input_v3' else HISTORICAL_POLICY if row.get('schema')=='dmb_native_play_input_v2' else False


def _limit(code, phrase=None):
    if code not in LIMITATIONS: raise ValueError('Unknown limitation code')
    text = LIMITATIONS[code]
    if phrase is not None:
        data = SimpleNamespace(requested_detail_gaps=[RequestedDetailGap(question_phrase=phrase)])
        text = gap_messages(data, {'user_question': phrase})[0]['text']
    return t.SurfaceLimitationV1(kind='limitation', code=code, text=text, question_phrase=phrase)


def status_for(segments):
    partial = any(isinstance(s, t.SurfaceLimitationV1) for s in segments)
    if any(isinstance(s, (t.PlanWorldGraphClaimSegmentV1, t.NativeAssertionClaimV1)) for s in segments): base = 'graph_grounded'
    elif any(isinstance(s, t.SourcePassageClaimV1) for s in segments): base = 'source_grounded'
    elif any(isinstance(s, (t.SurfaceAuthoredQuoteV1, t.SessionSummaryV1)) for s in segments): base = 'authored_grounded'
    elif any(isinstance(s, t.PlanWorldGraphProposalSegmentV1) for s in segments): return 'creative_proposal'
    else: return 'insufficient_evidence'
    return base + ('_partial' if partial else '')


def validate_authored_shape(segments):
    blocks=[s.block_handle for s in segments if isinstance(s,t.SurfaceAuthoredExcerptV1)]
    if len(set(blocks))!=len(blocks):raise ValueError('Repeated authored block')
    for s in segments:
        if isinstance(s,t.SurfaceAuthoredQuoteV1) and (not s.source_name.strip() or not s.object_id.strip() or not s.revision.strip()):
            raise ValueError('Authored quote requires exact source identity')


def validate_shape(c):
    validate_authored_shape(c.answer_segments)
    if any(not s.text.strip() for s in c.answer_segments): raise ValueError('Blank evidence segment')
    if c.answer_context_status != status_for(c.answer_segments): raise ValueError('Evidence status differs from typed support')
    claims = {i: s for i, s in enumerate(c.answer_segments) if isinstance(s, t.PlanWorldGraphClaimSegmentV1)}
    source = {i: s for i, s in enumerate(c.answer_segments) if isinstance(s, t.SourcePassageClaimV1)}
    entries = c.citation_map.entries if c.citation_map else []
    if (len({s.claim_id for s in claims.values()}) != len(claims) or len(entries) != len(claims)
        or {e.claim_id for e in entries} != {s.claim_id for s in claims.values()}
        or bool(claims) != bool(c.citation_map)):
        raise ValueError('Graph citations differ from exact mixed claims')
    for i, s in claims.items():
        entry = next(e for e in entries if e.claim_id == s.claim_id)
        if any(getattr(entry, key) != getattr(s, key) for key in ('target_kind','target_id','graph_revision','evidence_ref_ids')):
            raise ValueError('Graph citation differs from claim authority')
        selected = sorted({x.receipt.source_read_id for x in c.source_citations if x.segment_index == i})
        if entry.source_read_ids != selected or entry.source_opened != bool(selected):
            raise ValueError('Graph opening differs from explicitly selected passages')
    if c.citation_map and c.citation_map.context_receipt_sha256 != c.context_receipt_sha256:
        raise ValueError('Graph citations differ from owning receipt')
    if not set(source) <= {x.segment_index for x in [*c.source_citations,*getattr(c,'native_source_citations',()),*getattr(c,'native_body_citations',()),*getattr(c,'native_clause_citations',())]}: raise ValueError('Uncited source fact')
    keys = set()
    for x in c.source_citations:
        if x.segment_index not in claims and x.segment_index not in source: raise ValueError('Citation attached to unrelated segment')
        key = (x.segment_index, x.read_event_id, x.receipt.source_read_id)
        if key in keys: raise ValueError('Repeated passage citation')
        keys.add(key)
        if x.text_sha256 != sha256(c.answer_segments[x.segment_index].text.encode()).hexdigest(): raise ValueError('Citation text changed')
        from .surface_source_answer import eligible
        if not eligible(x.receipt) or not x.source_name.strip(): raise ValueError('Incomplete source claim')
        if x.segment_index in claims and x.receipt.evidence_ref_id not in claims[x.segment_index].evidence_ref_ids:
            raise ValueError('Selected passage does not belong to Graph target')
    native_keys = set()
    for x in getattr(c,'native_source_citations',()):
        if x.segment_index not in source:raise ValueError('Native section cannot donate Graph or authored authority')
        key = (x.segment_index,x.read_event_id)
        if key in native_keys:raise ValueError('Repeated native section citation')
        native_keys.add(key)
        if (x.text_sha256 != sha256(c.answer_segments[x.segment_index].text.encode()).hexdigest()
                or not x.source_name.strip() or not x.section_title.strip() or x.line_end < x.line_start):
            raise ValueError('Native section citation changed its text or display locator')
    body_keys = set()
    for x in getattr(c, 'native_body_citations', ()):
        key = (x.segment_index, x.read_event_id)
        if (x.segment_index not in source or key in body_keys
                or x.text_sha256 != sha256(c.answer_segments[x.segment_index].text.encode()).hexdigest()
                or x.line_end < x.line_start):
            raise ValueError('Native body citation changed its supported segment or extent')
        body_keys.add(key)
    for s in c.answer_segments:
        if isinstance(s, t.SurfaceLimitationV1) and s != _limit(s.code, s.question_phrase):
            raise ValueError('Model-authored limitation prose is not admitted')
    if len(canonical_bytes(c)) > 1_048_576: raise ValueError('Completion exceeds existing storage budget')


def graph_bindings(segments, receipt, execution, auth):
    operations = {e.event_id:e for e in execution.events if isinstance(e, t.ValidatedGraphOperationEventV1)}
    from .plan_source_context import capability_bases
    graph = capability_bases(receipt).graph if isinstance(receipt, t.PlanSourceContextReceiptV1) else receipt
    bindings = {}
    for s in segments:
        if not isinstance(s, t.PlanWorldGraphClaimSegmentV1): continue
        if graph is None: raise ValueError('Graph claim requires a genuine Graph capability')
        initial = graph.assembled_input.dispatched_assertion_ids if s.target_kind == 'assertion' else graph.assembled_input.dispatched_relationship_ids
        supplied = auth.included_assertion_ids if s.target_kind == 'assertion' else auth.included_relationship_ids
        if s.target_id not in supplied or not set(s.evidence_ref_ids) <= set(auth.included_evidence_ref_ids):
            raise ValueError('Graph claim not included in actual producing input')
        initial_support = s.target_id in initial and set(s.evidence_ref_ids) <= set(graph.assembled_input.dispatched_evidence_ref_ids)
        events = [identity for identity in auth.included_graph_event_ids if identity in operations
            and s.target_id in (operations[identity].assertion_ids if s.target_kind == 'assertion' else operations[identity].relationship_ids)
            and set(s.evidence_ref_ids) <= set(operations[identity].evidence_ref_ids)]
        if not initial_support and not events: raise ValueError('Graph claim lacks admitted operation')
        bindings[s.claim_id] = [] if initial_support else events[:1]
    return bindings



def authored_block_index(sources, scope):
    from .authored_excerpt_blocks import partition, selection_catalog
    blocks={block.block_handle:(source,block) for source in sources for block in partition(source.text,source.handle)}
    selectors={row.selection_id:row.block.block_handle for row in selection_catalog(
        ((source.handle,source.text) for source in sources),scope)} if scope is not None else {}
    return blocks,selectors


def authored_selected_segment(row, *, blocks, selectors, selected_blocks, short=True):
    """Resolve model choices through the existing exact saved/session block owner."""
    from .authored_excerpt_blocks import PARTITION
    kind=row.get('kind')
    if kind=='session_summary':
        ids = row.get('selection_ids')
        if (set(row) != {'kind', 'text', 'selection_ids'} or not isinstance(ids, list) or not ids
                or any(not isinstance(value, str) for value in ids) or len(set(ids)) != len(ids)):
            raise ValueError('Session summary requires distinct exact session selections')
        resolved = []
        for identity in ids:
            handle = selectors.get(identity)
            if handle not in blocks: raise ValueError('Session summary selection was not supplied')
            source, block = blocks[handle]
            if source.source_kind != 'session': raise ValueError('Non-session material cannot support a session summary')
            resolved.append(t.SessionSummarySupportV1(kind='authored_excerpt', text=block.text,
                source_handle=source.handle, source_kind='session', source_name=source.source_name,
                object_id=source.object_id, revision=source.revision, body_sha256=source.body_sha256,
                owner_sha256=source.owner_sha256, entry_identity=source.entry_identity,
                block_handle=block.block_handle, partition_version=PARTITION, byte_start=block.byte_start,
                byte_end=block.byte_end, block_sha256=block.block_sha256, source_ordinal=source.source_ordinal,
                entry_kind=source.entry_kind, element_id=source.element_id,
                checkpoint_content_sha256=source.checkpoint_content_sha256))
        return t.SessionSummaryV1(kind='session_summary', text=row['text'], supports=resolved)
    if kind=='authored_excerpt':
        field='selection_id' if short else 'block_handle'
        if set(row)!={'kind',field} or not isinstance(row.get(field),str):
            raise ValueError('Unknown or model-authored block selection')
        handle=selectors.get(row[field]) if short else row[field]
        if handle not in blocks or handle in selected_blocks:
            raise ValueError('Unknown, repeated or model-authored block selection')
        selected_blocks.add(handle)
        a,block=blocks[handle]
        return t.SurfaceAuthoredExcerptV1(kind=kind,text=block.text,source_handle=a.handle,
            source_kind=a.source_kind,source_name=a.source_name,object_id=a.object_id,revision=a.revision,
            body_sha256=a.body_sha256,owner_sha256=a.owner_sha256,entry_identity=a.entry_identity,
            block_handle=block.block_handle,partition_version=PARTITION,byte_start=block.byte_start,
            byte_end=block.byte_end,block_sha256=block.block_sha256)
    raise ValueError('Unknown authored selection kind')

def native_fact_segment(row, *, policy, receipt, auth, support, index):
    """Resolve native fact selectors once for legacy and shared producing owners."""
    kind = row.get('kind')
    producer = auth.provider_attempt_id
    statement_available = {handle: read for handle, _, read in getattr(support, 'native_statements', ())}
    assertion_available = {handle: (event, read) for handle, event, read in getattr(support, 'native_assertions', ())}
    body_available = {item.handle: item for item in getattr(support, 'body_excerpts', ())}
    assertion_citations, statement_citations, body_citations = [], [], []
    if kind == 'native_assertion_claim' and policy == ASSERTION_POLICY:
        handles = row.get('assertion_handles')
        if (set(row) != {'kind', 'text', 'assertion_handles'} or not isinstance(handles, list) or not handles
                or any(not isinstance(h, str) or h not in assertion_available for h in handles)
                or len(handles) != len(set(handles))):
            raise ValueError('Native Graph claim requires exact included assertion handles')
        from .native_plan_assertions import citation as assertion_citation
        selected = [assertion_available[h] for h in handles]
        metadata = {canonical_sha256(r.assertion.metadata): r.assertion.metadata for _, r in selected}
        labels = sorted({m.claim_mode.rsplit(':', 1)[-1] + ' / ' + m.epistemic_basis + ' / ' + m.standing for m in metadata.values()})
        text = 'Graph records (' + '; '.join(labels) + '): ' + row['text']
        segment = t.NativeAssertionClaimV1(text=text,
            assertion_ids=sorted(r.assertion.assertion_id for _, r in selected),
            qualifications=[metadata[k] for k in sorted(metadata)])
        assertion_citations.extend(assertion_citation(receipt, auth, event, read, span, index=index)
            for event, read in selected for span in read.spans)
    elif kind == 'native_statement_report' and policy in {STATEMENT_POLICY, ASSERTION_POLICY}:
        handles = row.get('statement_handles')
        if (set(row) != {'kind', 'text', 'statement_handles'} or not isinstance(handles, list) or not handles
                or any(not isinstance(h, str) or h not in statement_available for h in handles)
                or len(handles) != len(set(handles))):
            raise ValueError('Native source report requires exact included statement handles')
        from .native_plan_statements import citation
        text = 'Source reports: ' + row['text']
        segment = t.SourcePassageClaimV1(kind='source_passage_claim', text=text)
        statement_citations.extend(citation(receipt, auth, statement_available[h], index=index) for h in handles)
    elif kind == 'native_body_claim' and policy in {ASSERTION_POLICY, BODY_POLICY, STATEMENT_POLICY}:
        handles = row.get('excerpt_handles')
        if (set(row) != {'kind','text','excerpt_handles'} or not isinstance(handles, list) or not handles
                or any(not isinstance(handle, str) or handle not in body_available for handle in handles)
                or len(set(handles)) != len(handles)):
            raise ValueError('Native body claim requires exact producing excerpt selections')
        from .native_corpus import body_citation
        segment = t.SourcePassageClaimV1(kind='source_passage_claim', text=row['text'])
        body_citations.extend(body_citation(body_available[handle], index=index, text=row['text'],
            producer=producer, envelope_sha256=auth.envelope_sha256) for handle in handles)
    else:
        raise ValueError('Native fact is not offered by the producing policy')
    return segment, body_citations, statement_citations, assertion_citations


def normalize(candidate, turn, producer, support):
    if not isinstance(candidate, dict) or set(candidate) != {'schema','answer_segments','limitations','requested_detail_gaps'} or candidate['schema'] not in {ASSERTION_POLICY,STATEMENT_POLICY,BODY_POLICY,PLAN_POLICY,SELECTOR_POLICY,NATIVE_POLICY,POLICY,HISTORICAL_POLICY}:
        raise ValueError('Invalid current mixed evidence answer')
    receipt, execution = turn.graph_context_receipt, turn.graph_context_execution
    auth = next(e for e in execution.events if isinstance(e, t.ProviderAttemptAuthorizedEventV3) and e.provider_attempt_id == producer)
    from .plan_source_context import capability_bases
    graph = capability_bases(receipt).graph if isinstance(receipt, t.PlanSourceContextReceiptV1) else receipt
    graph_revision = graph.graph_authority.graph_revision if graph is not None else None
    if (support is None or support.provider_attempt_id != producer or support.envelope_sha256 != auth.envelope_sha256
        or support.context_receipt_sha256 != receipt.context_receipt_sha256 or support.graph_revision != graph_revision):
        raise ValueError('Mixed evidence differs from actual producer')
    selected_policy = getattr(support,'current_policy',False)
    if isinstance(selected_policy,str) and candidate['schema'] != selected_policy:
        raise ValueError('Answer differs from the actual producing policy')
    native = candidate['schema'] in {ASSERTION_POLICY,STATEMENT_POLICY,BODY_POLICY,PLAN_POLICY,SELECTOR_POLICY,NATIVE_POLICY}
    current = candidate['schema'] in {ASSERTION_POLICY,STATEMENT_POLICY,BODY_POLICY,PLAN_POLICY,SELECTOR_POLICY,NATIVE_POLICY,POLICY}
    if current and selected_policy != candidate['schema']:
        raise ValueError('Block selection requires its actual current input policy')
    blocks,selectors=authored_block_index(getattr(support,'authored',()),str(turn.idempotency_key)
        if candidate['schema'] in {ASSERTION_POLICY,STATEMENT_POLICY,BODY_POLICY,PLAN_POLICY,SELECTOR_POLICY} else None)
    selected_blocks=set()
    available = {}
    for passage in getattr(support, 'passages', ()): available.setdefault(passage.handle, passage)
    authored = {s.handle:s for s in getattr(support, 'authored', ())}
    native_available = {s.handle:s for s in getattr(support,'native_sections',())}
    statement_citations = []
    assertion_citations = []
    segments, citations, native_citations, body_citations, entries = [], [], [], [], []
    for row in candidate['answer_segments']:
        if not isinstance(row,dict): raise ValueError('Invalid evidence segment')
        if row.get('kind')!='authored_excerpt' and (not isinstance(row.get('text'),str) or not row['text'].strip()): raise ValueError('Invalid evidence segment')
        kind = row.get('kind'); index = len(segments)
        if kind in {'graph_claim', 'source_passage_claim'}:
            expected = {'kind','text','passage_handles'} | ({'claim_id','target_kind','target_id'} if kind == 'graph_claim' else set())
            handles = row.get('passage_handles')
            if (set(row) != expected or not isinstance(handles, list) or any(not isinstance(h,str) for h in handles)
                or len(set(handles)) != len(handles) or any(h not in available for h in handles) or kind == 'source_passage_claim' and not handles):
                raise ValueError('Fact requires exact distinct eligible passage selections')
            if kind == 'graph_claim':
                from .native_answer_output import _target_claim
                segment = t.PlanWorldGraphClaimSegmentV1.model_validate(_target_claim({k:v for k,v in row.items() if k != 'passage_handles'}, support, receipt, auth))
                selected_ids = sorted({available[h].receipt.source_read_id for h in handles})
                entries.append(t.PlanWorldGraphCitationV2(claim_id=segment.claim_id, target_kind=segment.target_kind,
                    target_id=segment.target_id, graph_revision=segment.graph_revision, evidence_ref_ids=segment.evidence_ref_ids,
                    source_opened=bool(selected_ids), source_read_ids=selected_ids))
            else: segment = t.SourcePassageClaimV1(kind=kind, text=row['text'])
            segments.append(segment)
            for handle in handles:
                p = available[handle]
                citations.append(t.SurfaceSourcePassageCitationV1(segment_index=index, text_sha256=sha256(row['text'].encode()).hexdigest(),
                    provider_attempt_id=producer, envelope_sha256=auth.envelope_sha256, read_event_id=p.event_id, receipt=p.receipt, source_name=p.source_name))
        elif (kind == 'native_assertion_claim' and candidate['schema'] == ASSERTION_POLICY
                or kind == 'native_statement_report' and candidate['schema'] in {STATEMENT_POLICY, ASSERTION_POLICY}
                or kind == 'native_body_claim' and candidate['schema'] in {ASSERTION_POLICY, BODY_POLICY, STATEMENT_POLICY}):
            segment, body, statement, assertion = native_fact_segment(row, policy=candidate['schema'],
                receipt=receipt, auth=auth, support=support, index=index)
            segments.append(segment)
            body_citations.extend(body)
            statement_citations.extend(statement)
            assertion_citations.extend(assertion)
        elif kind == 'native_source_claim' and native:
            handles = row.get('section_handles')
            if (set(row) != {'kind','text','section_handles'} or not isinstance(handles,list) or not handles
                    or any(not isinstance(h,str) or h not in native_available for h in handles)
                    or len(set(handles)) != len(handles)):
                raise ValueError('Native claim requires exact exposed section handles')
            from .native_source_answer import citation
            segments.append(t.SourcePassageClaimV1(kind='source_passage_claim',text=row['text']))
            native_citations.extend(citation(native_available[h],index=index,text=row['text'],
                producer=producer,envelope_sha256=auth.envelope_sha256) for h in handles)
        elif (kind == 'session_summary' and candidate['schema'] in {ASSERTION_POLICY,STATEMENT_POLICY,BODY_POLICY,PLAN_POLICY}
                or kind == 'authored_excerpt' and current):
            segments.append(authored_selected_segment(row,blocks=blocks,selectors=selectors,selected_blocks=selected_blocks,
                short=candidate['schema'] in {ASSERTION_POLICY,STATEMENT_POLICY,BODY_POLICY,PLAN_POLICY,SELECTOR_POLICY}))
        elif kind == 'authored_quote' and not current:
            if set(row) != {'kind','text','source_handle'} or not isinstance(row['source_handle'],str) or row['source_handle'] not in authored: raise ValueError('Unknown authored source')
            a = authored[row['source_handle']]
            if row['text'] not in a.text: raise ValueError('Authored claim must be a literal frozen excerpt')
            segments.append(t.SurfaceAuthoredQuoteV1(kind=kind, text=row['text'], source_handle=a.handle, source_kind=a.source_kind,
                source_name=a.source_name, object_id=a.object_id, revision=a.revision, body_sha256=a.body_sha256, owner_sha256=a.owner_sha256))
        elif kind == 'proposal': segments.append(t.PlanWorldGraphProposalSegmentV1.model_validate(row))
        else: raise ValueError('Unbound factual or connective segment is not admitted')
    codes = candidate['limitations']
    if not isinstance(codes,list) or any(not isinstance(code,str) or code not in LIMITATIONS for code in codes) or len(set(codes)) != len(codes): raise ValueError('Unknown or duplicate limitation')
    gaps = [RequestedDetailGap.model_validate(g) for g in candidate['requested_detail_gaps']]
    gap_messages(SimpleNamespace(requested_detail_gaps=gaps), {'user_question':turn.user_text})
    codes = list(codes)
    if gaps and 'missing_requested_details' not in codes:
        if not current: raise ValueError('Gaps require missing-details limitation')
        # Validated exact selections already establish this closed display flag.
        codes.append('missing_requested_details')
    bindings = graph_bindings(segments, receipt, execution, auth)
    citation_map = t.PlanWorldGraphCitationMapV2(context_receipt_sha256=receipt.context_receipt_sha256, entries=entries) if entries else None
    if entries:
        derived = t.derive_graph_execution_evidence_status_for_scope(context_receipt_sha256=receipt.context_receipt_sha256,
            answer_segments=segments, citation_map=citation_map, inputs=_graph_inputs(receipt), execution=execution,
            producing_provider_attempt_id=producer, claim_graph_event_ids=bindings, source_scope=execution.policy.source_read_scope)
        partial = derived != 'graph_grounded'
    else: partial = getattr(support, 'source_partial', False)
    if partial and 'partial_retrieval' not in codes: codes.append('partial_retrieval')
    segments += [_limit(code) for code in codes] + [_limit('missing_requested_details', g.question_phrase) for g in gaps]
    if not segments: segments = [_limit('missing_requested_details')]
    c = (t.SurfaceEvidenceCompletionV7 if candidate['schema'] == ASSERTION_POLICY else t.SurfaceEvidenceCompletionV6 if candidate['schema'] == STATEMENT_POLICY else t.SurfaceEvidenceCompletionV5 if candidate['schema'] in {ASSERTION_POLICY, BODY_POLICY, STATEMENT_POLICY} else t.SurfaceEvidenceCompletionV4 if candidate['schema'] == PLAN_POLICY else t.SurfaceEvidenceCompletionV3 if native else t.SurfaceEvidenceCompletionV2 if current else t.SurfaceEvidenceCompletionV1)(surface_id=turn.provenance.surface_id, context_receipt_sha256=receipt.context_receipt_sha256,
        answer_context_status=status_for(segments), answer_segments=segments, citation_map=citation_map, source_citations=citations,
        **({'native_source_citations':native_citations} if native else {}),
        **({'native_body_citations':body_citations} if candidate['schema'] in {ASSERTION_POLICY, BODY_POLICY, STATEMENT_POLICY} else {}),
        **({'native_clause_citations':statement_citations} if candidate['schema'] in {STATEMENT_POLICY, ASSERTION_POLICY} else {}),
        **({'native_assertion_citations':assertion_citations} if candidate['schema'] == ASSERTION_POLICY else {}))
    validate_completion(c, receipt, execution, producer, bindings)
    return c, bindings, '\n'.join(s.text for s in c.answer_segments)


def validate_completion(c, receipt, execution, producer, bindings):
    if (c.surface_id != ('play' if isinstance(receipt,t.PlayWorldGraphContextReceiptV1) else 'plan')
        or c.context_receipt_sha256 != receipt.context_receipt_sha256 or execution.context_receipt_sha256 != receipt.context_receipt_sha256):
        raise ValueError('Mixed evidence differs from owning receipt')
    t.validate_selected_source_binding(receipt, execution)
    auths = [e for e in execution.events if isinstance(e,t.ProviderAttemptAuthorizedEventV3) and e.provider_attempt_id == producer]
    if len(auths) != 1: raise ValueError('Mixed evidence lacks unique producing authorization')
    auth = auths[0]
    from .native_plan_statements import validate_citations
    validate_citations(c, receipt, execution, auth)
    from .native_plan_assertions import validate_citations as validate_assertion_citations
    validate_assertion_citations(c, receipt, execution, auth)
    responses = [e for e in execution.events if isinstance(e,t.ProviderOutcomeEventV1) and e.provider_attempt_id == producer and e.outcome == 'response_received']
    if len(responses) != 1 or any(not isinstance(e,t.CompletionBindingEventV1) for e in execution.events if e.sequence > responses[0].sequence):
        raise ValueError('Mixed evidence requires final acknowledged response without later acquisition')
    if graph_bindings(c.answer_segments, receipt, execution, auth) != bindings: raise ValueError('Mixed Graph binding changed')
    t.validate_graph_execution_source_citations(c.citation_map, execution, producer)
    reads = {e.event_id:e for e in execution.events if isinstance(e,t.SOURCE_PASSAGE_EVENTS) and e.event_id in t.included_passage_event_ids(auth)}
    for citation in c.source_citations:
        event = reads.get(citation.read_event_id)
        if (citation.provider_attempt_id != producer or citation.envelope_sha256 != auth.envelope_sha256 or event is None
            or event.sequence >= auth.sequence or citation.receipt not in event.receipts): raise ValueError('Source citation differs from included producing read')
    for s in (support for segment in c.answer_segments for support in
              (segment.supports if isinstance(segment,t.SessionSummaryV1) else [segment])):
        if not isinstance(s,t.SurfaceAuthoredQuoteV1): continue
        if s.source_kind == 'session' and c.surface_id == 'play':
            if not isinstance(receipt,t.PlayWorldGraphContextReceiptV1) or s.object_id != receipt.play_basis.run_id or isinstance(s,t.SessionSummarySupportV1) and s.checkpoint_content_sha256 != receipt.play_basis.content_sha256:
                raise ValueError('Session reflections differ from their frozen Play owner')
        if s.source_kind == 'play' and c.surface_id != 'play':
            raise ValueError('Play quote cannot be rebound to Plan authority')
        if s.source_kind == 'plan':
            basis = getattr(receipt,'plan_basis',None)
            if (basis is None or (s.object_id,s.revision,s.owner_sha256,s.body_sha256) !=
                (basis.document_id,str(basis.work_revision_id),basis.content_sha256,basis.content_sha256)):
                raise ValueError('Plan quote differs from committed owner')
        if s.source_kind == 'play':
            entries = [e for e in receipt.play_sources.entries if e.source_id == s.source_handle]
            if len(entries) != 1 or (s.body_sha256,s.owner_sha256,s.object_id,s.revision) != (entries[0].text_sha256,entries[0].payload_sha256,entries[0].locator.run_id,str(entries[0].locator.run_revision)):
                raise ValueError('Play quote differs from frozen source manifest')
    from .native_source_answer import validate_citations
    validate_citations(c,receipt,execution,producer)
    from .native_corpus import validate_body_citations
    validate_body_citations(c,receipt,execution,producer)
    existing = [e for e in execution.events if isinstance(e,t.CompletionBindingEventV1)]
    if existing and (len(existing) != 1 or existing[0].provider_attempt_id != producer or existing[0].completion_sha256 != canonical_sha256(c)
        or existing[0].claim_graph_event_ids != bindings): raise ValueError('Stored mixed evidence changed its completion binding')


def _graph_inputs(receipt):
    from .plan_source_context import require_graph
    graph = require_graph(receipt) if isinstance(receipt, t.PlanSourceContextReceiptV1) else receipt
    return t._ask_graph_validation_inputs(graph).model_copy(update={"context_receipt_sha256": receipt.context_receipt_sha256})
