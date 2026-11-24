"""Provider-only Build work. Existing captured work records retain all authority."""
from copy import deepcopy
import re
from uuid import UUID

_OPTIONAL = frozenset({'working_draft_context', 'response_contract', 'captured_editor',
    'reviewed_discussion_scope', 'plan_output_contract', 'related_authored_pages',
    'authored_references', 'saved_statblocks', 'retained_authored_context'})

SOURCE_ANSWER_POLICY = 'typed_supplied_source_answer_v1'
SOURCE_ANSWER_FORMAT = 'surface_native_build_source_answer_v1'
LORE_LIMITATION_POLICY = 'validated_lore_review_generic_gaps_v1'
LORE_LIMITATION_FORMAT = 'surface_native_lore_review_limitations_v1'
BUILD_REPLY_FORMAT = 'build_reply'


def semantic_reply_eligible(host, execution):
    """Ordinary Build only; Rules eligibility is checked by its existing owner."""
    from .native_execution import NativeBuildActionV1
    return (type(getattr(execution.policy, 'action', None)) is NativeBuildActionV1
            and not variant_sources(host) and not lore_outcome_eligible(host, execution))


def source_backed_discussion(host, execution):
    """Use captured work/scope and actual supplied reads, never lexical guessing."""
    from .native_execution import NativeBuildActionV1
    from .types import BuildRequestedWorkResolutionV1
    if type(getattr(execution.policy, 'action', None)) is not NativeBuildActionV1:
        return False
    choices = [event for event in execution.events if isinstance(event, BuildRequestedWorkResolutionV1)]
    return (len(choices) == 1 and choices[0].requested_work == 'discuss'
            and choices[0].resolution.get('source_scope') == 'source_lookup'
            and not variant_sources(host)
            and bool(host['artifact_under_edit']['sections']
                     or host.get('related_authored_pages', {}).get('pages')))


def lore_page_reply(host, execution):
    """Only an admitted, unblocked lore review can offer this presentation policy."""
    from .native_execution import NativeBuildActionV1
    from .types import BuildRequestedWorkResolutionV1
    if type(getattr(execution.policy, 'action', None)) is not NativeBuildActionV1:
        return False
    choices = [event for event in execution.events if isinstance(event, BuildRequestedWorkResolutionV1)]
    contract = host.get('response_contract', {})
    return (len(choices) == 1
            and choices[0].requested_work in {'review_lore_page', 'review_lore_page_from_conversation', 'review_blank_lore_page'}
            and contract.get('requested_work') == choices[0].requested_work
            and contract.get('barrier') is None and not variant_sources(host))


def lore_request_reference_eligible(host, execution):
    """Current populated/blank menu, or conversation work with fixed content mode.

    Retrying an older conversation admission may use a fresh reference contract;
    historical writer readback still reconstructs its captured format explicitly.
    An older ambiguous blank/populated choice cannot acquire new semantics.
    """
    from .build_intentional_response import _menu_work
    from .types import BuildRequestedWorkResolutionV1
    if not lore_page_reply(host, execution):
        return False
    choice, = [event for event in execution.events
               if isinstance(event, BuildRequestedWorkResolutionV1)]
    return (choice.requested_work == 'review_lore_page_from_conversation'
            or 'review_blank_lore_page' in _menu_work(choice.menu_sha256))


def lore_outcome_eligible(host, execution):
    from .build_intentional_response import menu_offers_lore_outcomes
    from .types import BuildRequestedWorkResolutionV1
    if not lore_page_reply(host, execution):
        return False
    choice, = [event for event in execution.events
               if isinstance(event, BuildRequestedWorkResolutionV1)]
    return (menu_offers_lore_outcomes(choice.menu_sha256)
            and choice.requested_work in {'review_lore_page', 'review_lore_page_from_conversation'})


def selection_aliases(host):
    """One deterministic local domain from the complete prewriter work catalog."""
    identities = [str(UUID(row['read_id'])) for row in host['artifact_under_edit']['sections']]
    identities += [str(UUID(row['read_id']))
        for row in host.get('related_authored_pages', {}).get('pages', [])]
    if len(set(identities)) != len(identities):
        raise ValueError('Ambiguous Build work source identities')
    aliases = {identity: f'source{i}' for i, identity in enumerate(sorted(identities))}
    draft = host.get('working_draft_context')
    if draft is not None:
        identity = str(UUID(draft['record_id']))
        if identity in aliases:
            raise ValueError('Build draft identity collides with saved source')
        aliases[identity] = 'draft0'
    return aliases


def resolve_selectors(row, host):
    """Resolve only typed selector slots; literal prose and quotes are untouched."""
    inverse = {alias: identity for identity, alias in selection_aliases(host).items()}
    def resolve(value):
        if not isinstance(value, str) or value not in inverse:
            raise ValueError('Unknown Build work selection')
        return inverse[value]
    result = deepcopy(row)
    for key in ('draft_record_id', 'read_id'):
        if key in result:
            result[key] = resolve(result[key])
    if 'section_read_ids' in result:
        values = result['section_read_ids']
        if not isinstance(values, list):
            raise ValueError('Build section selections require an array')
        result['section_read_ids'] = [resolve(value) for value in values]
    return result


def is_semantic_frame(value):
    return (isinstance(value, dict) and set(value) == {'build_work'}
        and isinstance(value['build_work'], dict)
        and {'source_class', 'saved_sections'} <= set(value['build_work']))


VARIANT_WRITER_FORMAT = "surface_native_evidence_selectors_v3"
VARIANT_EDITS_FORMAT = "surface_native_evidence_selectors_v4"
VARIANT_VISIBLE_REPLY_FORMAT = "surface_native_evidence_selectors_v5"
VARIANT_WITNESS_FORMAT = "surface_native_evidence_selectors_v6"
VARIANT_CARRIED_CONDITION_FORMAT = "surface_native_evidence_selectors_v8"


VARIANT_PASSAGE_REVIEW_FORMAT = "surface_native_evidence_selectors_v9"
VARIANT_TRIGGER_RETENTION_FORMAT = "surface_native_evidence_selectors_v10"
VARIANT_PASSAGE_WITNESS_FORMAT = "surface_native_evidence_selectors_v11"
VARIANT_PASSAGE_FORMATS = frozenset({
    VARIANT_PASSAGE_REVIEW_FORMAT, VARIANT_TRIGGER_RETENTION_FORMAT, VARIANT_PASSAGE_WITNESS_FORMAT,
})


def variant_draft_passages(work_frame):
    """Offer ordered local handles over the exact authored draft text."""
    markdown = work_frame.get("working_draft_context", {}).get("draft_markdown", "")
    passages = (
        passage for passage in re.split(r"\r?\n[ \t]*\r?\n(?:[ \t]*\r?\n)*", markdown)
        if passage.strip()
    )
    return {f"p{index}": passage for index, passage in enumerate(passages, 1)}


def variant_output_version(work_frame):
    return 11 if variant_draft_passages(work_frame) else 8


def semantic_frame(host, execution, *, include_variant=False, variant_edits=False,
                   variant_passage_review=False, bind_lore_page=False,
                   retained_raw_markdown=False, supplied_source_references=False,
                   typed_source_answer=False, lore_page_limitations=False, lore_request_reference=False, lore_outcome=False,
                   semantic_reply=False):
    from .build_primary_context import NATIVE_WORK_SCHEMA
    from .model_markdown import project_model_markdown, project_retained_source_markdown

    def authored_text(value):
        if supplied_source_references:
            return project_retained_source_markdown(value)
        return value if retained_raw_markdown else project_model_markdown(value)

    if (host.get('schema') != NATIVE_WORK_SCHEMA
            or set(host) - ({'schema', 'source_basis', 'artifact_under_edit'} | _OPTIONAL)):
        raise ValueError('Unclassified native Build work fields')
    aliases = selection_aliases(host)
    def section(row):
        if set(row) not in ({'read_id', 'line_start', 'line_end', 'text'},
                            {'read_id', 'line_start', 'line_end', 'text_ref'}):
            raise ValueError('Unclassified Build saved section')
        result = {'selection': aliases[row['read_id']],
            **{key: deepcopy(row[key]) for key in ('line_start', 'line_end', 'text') if key in row}}
        if 'text' in result:
            result['text'] = authored_text(result['text'])
        if 'text_ref' in row:
            if row['text_ref'] != 'working_draft_context' or 'working_draft_context' not in host:
                raise ValueError('Unknown Build body reuse')
            result['body_ref'] = 'current_draft'
        return result
    work = {'source_class': 'authored_context_not_played_events',
        'visibility': host['source_basis']['visibility'],
        'saved_sections': [section(row) for row in host['artifact_under_edit']['sections']]}
    if supplied_source_references:
        work['citation_policy'] = 'supplied_source_references_v1'
    if typed_source_answer and source_backed_discussion(host, execution):
        if not supplied_source_references:
            raise ValueError('Typed source answers require supplied references')
        work['source_answer_policy'] = SOURCE_ANSWER_POLICY
    if lore_page_limitations and lore_page_reply(host, execution):
        if not supplied_source_references:
            raise ValueError('Lore review limitations require supplied references')
        work['lore_limitation_policy'] = LORE_LIMITATION_POLICY
    if 'retained_authored_context' in host:
        work['retained_authored_context'] = deepcopy(host['retained_authored_context'])
    if 'working_draft_context' in host:
        draft = host['working_draft_context']
        work['current_draft'] = {'selection': aliases[draft['record_id']],
            **({'passages': {alias: authored_text(text) for alias, text in variant_draft_passages(host).items()}}
               if variant_passage_review else {'markdown': authored_text(draft['draft_markdown'])})}
    if 'response_contract' in host:
        contract = host['response_contract']
        allowed = {'policy', 'requested_work', 'intent_family', 'operation', 'purpose',
            'barrier', 'barrier_detail', 'capabilities', 'available_followups', 'contract_sha256'}
        if set(contract) != allowed:
            raise ValueError('Unclassified Build response contract')
        work['requested_work'] = {key: deepcopy(contract[key]) for key in
            ('requested_work', 'intent_family', 'operation', 'purpose', 'barrier',
             'barrier_detail', 'capabilities')}
        work['requested_work']['available_followups'] = [row['description']
            for row in contract['available_followups']]
        if lore_request_reference and lore_request_reference_eligible(host, execution):
            work['lore_page_destination'] = {'request': 'current_author_request'}
        if lore_outcome:
            if (not lore_outcome_eligible(host, execution)
                    or work.get('lore_page_destination') != {'request': 'current_author_request'}
                    or not supplied_source_references or not lore_page_limitations):
                raise ValueError('Lore outcome requires its admitted populated request and host policies')
            # The producing format/admission owns these flags; models receive task context.
            del work['citation_policy']
            del work['lore_limitation_policy']
        if bind_lore_page and 'lore_page_destination' not in work and contract['requested_work'] in ('review_lore_page', 'review_lore_page_from_conversation') and not contract['barrier']:
            from .lore_page_review import explicit_lore_page_witness

            try:
                witness = explicit_lore_page_witness(execution.policy.action.intent.message,
                    conversational=contract["requested_work"] == "review_lore_page_from_conversation")
            except ValueError:
                # A follow-up or ambiguous request has no new explicit title to bind.
                pass
            else:
                work['lore_page_destination'] = witness.model_dump(mode='json')
    if 'captured_editor' in host:
        editor = host['captured_editor']
        if set(editor)-{'idempotency_key','conversation_id','expected_pointer_revision','basis',
                'instruction','origin','page_body_offer','page_end_offer','draft_markdown','reference_image_id',
                'boundary_editor_json'}:
            raise ValueError('Unclassified Build editor fields')
        basis = editor['basis']
        if set(basis)-{'world_id','document_id','registry_revision','content_sha256','visibility',
                'draft_sha256','editor_sha256','caret','draft_generation','selection_generation','selection'}:
            raise ValueError('Unclassified Build editor basis')
        if 'boundary_editor_json' in editor:
            work['edit_target'] = {"kind": "contextual_paragraph"}
        else:
            work['edit_target'] = {key: deepcopy(basis[key]) for key in ('caret', 'selection') if key in basis}
            for key in ('page_body_offer', 'page_end_offer'):
                if key in editor:
                    work['edit_target'][key] = deepcopy(editor[key])
        if 'draft_markdown' in editor:
            work['editor_markdown'] = authored_text(editor['draft_markdown'])
    if 'reviewed_discussion_scope' in host:
        scope = host['reviewed_discussion_scope']['scope']
        work['reviewed_task'] = {'objective': scope['objective_context'],
            'task': {key: deepcopy(scope['task'][key]) for key in ('kind', 'text')},
            'siblings': [{key: deepcopy(row[key]) for key in
                ('text', 'kind', 'selected', 'status', 'earlier_reply')}
                for row in scope['sibling_context']]}
    if 'plan_output_contract' in host:
        from .plan_objective import SELECTION_GUIDANCE
        work['plan_requirements'] = SELECTION_GUIDANCE
    if 'related_authored_pages' in host:
        related = host['related_authored_pages']
        work['related_pages'] = [{'selection': aliases[row['read_id']],
            'title': row['page']['title'], 'visibility': row['page']['visibility'],
            'markdown': authored_text(row['markdown'])} for row in related['pages']]
        work['related_page_availability'] = [{'title': row['page']['title'],
            'visibility': row['page']['visibility'], 'acquisition': row['acquisition']}
            for row in related['availability']]
        work['related_page_scope'] = 'Saved active worldbuilding pages in this World, excluding the current page.'
        work['related_page_absence'] = 'This catalog does not prove that other pages do not exist.'
    if 'saved_statblocks' in host:
        mechanics_fields = (
            'identity', 'abilities', 'challenge', 'communication', 'defenses',
            'flavor_text', 'lair', 'movement', 'phases', 'proficiencies',
            'resources', 'rule_elements', 'senses', 'vitality',
        )
        work['saved_statblocks'] = []
        sources = variant_sources(host) if include_variant else {}
        if sources:
            work["statblock_variant_guidance"] = (
                "For a requested statblock variant, choose its variant_source and return the complete "
                "definition in statblock_variant. Preserve inherited mechanics except where the GM "
                "asked for a change. Include the agreed traits and mechanics in the definition itself. "
                "Keep the conversation draft consistent with that definition. Use null when the "
                "requested draft is unrelated to a statblock."
            )
        if sources and variant_edits:
            work["statblock_variant_guidance"] = (
                "Choose the verified variant_source. Return new rule elements in add_rules. "
                "Use replace_rules only for explicitly requested changes to existing rules, "
                "and keep each replaced rule's key. Buddy carries forward all other mechanics. "
                "Use null when a statblock variant was not requested."
            )
        for statblock_index, row in enumerate(host['saved_statblocks']):
            statblock = {'mechanics': {key: deepcopy(row['definition'][key])
                                      for key in mechanics_fields if key in row['definition']}}
            alias = f"statblock{statblock_index}"
            if alias in sources:
                statblock["variant_source"] = alias
                if "ruleset" in row["definition"]:
                    statblock["mechanics"]["ruleset"] = deepcopy(row["definition"]["ruleset"])
            excerpts = [excerpt for index, excerpt in statblock_pdf_excerpts(host)
                        if index == statblock_index]
            if excerpts:
                statblock['reviewed_pdf_excerpts'] = excerpts
            work['saved_statblocks'].append(statblock)
    from .authored_graph_references import model_reference_choices
    references = model_reference_choices(execution)
    if references is not None:
        work['selected_references'] = references
    if semantic_reply:
        if (not semantic_reply_eligible(host, execution) or not supplied_source_references
                or not typed_source_answer or not lore_page_limitations or not lore_request_reference):
            raise ValueError('Semantic Build reply requires its captured work and host policies')
        # Exact producing format selects these host checks, never model-returned flags.
        for key in ('citation_policy', 'source_answer_policy', 'lore_limitation_policy'):
            work.pop(key, None)
    return {'build_work': work}


def frame_in_request(body):
    """Find the disjoint work carrier, without inspecting literal source text."""
    from .source_writer_output import strict_json
    from .build_primary_context import NATIVE_WORK_SCHEMA
    frames, historical = [], 0
    for message in body.get('input', []) if isinstance(body.get('input'), list) else []:
        if not isinstance(message, dict) or not isinstance(message.get('content'), str):
            continue
        try:
            value = strict_json(message['content'])
        except ValueError:
            continue
        if not isinstance(value, dict):
            continue
        if value.get('schema') == NATIVE_WORK_SCHEMA:
            historical += 1
        elif 'build_work' in value:
            if not is_semantic_frame(value) or message.get('role') != 'user':
                raise ValueError('Malformed semantic Build work carrier')
            frames.append(value)
    if len(frames) > 1 or frames and historical:
        raise ValueError('Ambiguous Build work carriers')
    return frames[0] if frames else None


def variant_sources(work_frame):
    """Return local aliases only for an admitted conversation-draft task."""
    contract = work_frame.get("response_contract", {})
    if (
        contract.get("requested_work") != "draft_in_conversation"
        or contract.get("operation") != "answer_from_sources"
        or contract.get("barrier") is not None
    ):
        return {}
    return {
        f"statblock{index}": row
        for index, row in enumerate(work_frame.get("saved_statblocks", ()))
    }


def statblock_pdf_excerpts(work_frame):
    for statblock_index, row in enumerate(work_frame.get('saved_statblocks', ())):
        for crop_index, crop in enumerate((row.get('pdf_support') or {}).get('support', ())):
            if crop['text'].strip():
                yield statblock_index, {'source': f'pdf{statblock_index}:{crop_index}', 'text': crop['text']}


def resolve_statblock_pdf_quote(work_frame, alias, quote):
    """Return the pinned crop only when the writer quotes that exact excerpt."""
    from .source_quote_binding import CURRENT_POLICY, validate_selected_quotes

    if not isinstance(alias, str) or not isinstance(quote, str):
        raise ValueError("A PDF citation requires a source selector and exact quote")
    for statblock_index, row in enumerate(work_frame.get('saved_statblocks', ())):
        support = row.get('pdf_support') or {}
        for crop_index, crop in enumerate(support.get('support', ())):
            if alias != f'pdf{statblock_index}:{crop_index}' or not crop['text'].strip():
                continue
            validate_selected_quotes([alias], [quote], {alias: crop['text']},
                                     policy=CURRENT_POLICY)
            return support['scope'], crop['assertion_id'], crop['evidence_ref_id']
    raise ValueError("PDF citation was not offered to this writer")
