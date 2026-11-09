"""Provider-only Build work. Existing captured work records retain all authority."""
from copy import deepcopy
from uuid import UUID

_OPTIONAL = frozenset({'working_draft_context', 'response_contract', 'captured_editor',
    'reviewed_discussion_scope', 'plan_output_contract', 'related_authored_pages',
    'authored_references'})


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


def semantic_frame(host, execution):
    from .build_primary_context import NATIVE_WORK_SCHEMA
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
        if 'text_ref' in row:
            if row['text_ref'] != 'working_draft_context' or 'working_draft_context' not in host:
                raise ValueError('Unknown Build body reuse')
            result['body_ref'] = 'current_draft'
        return result
    work = {'source_class': 'authored_context_not_played_events',
        'visibility': host['source_basis']['visibility'],
        'saved_sections': [section(row) for row in host['artifact_under_edit']['sections']]}
    if 'working_draft_context' in host:
        draft = host['working_draft_context']
        work['current_draft'] = {'selection': aliases[draft['record_id']],
            'markdown': draft['draft_markdown']}
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
    if 'captured_editor' in host:
        editor = host['captured_editor']
        if set(editor)-{'idempotency_key','conversation_id','expected_pointer_revision','basis',
                'instruction','origin','page_body_offer','page_end_offer','draft_markdown'}:
            raise ValueError('Unclassified Build editor fields')
        basis = editor['basis']
        if set(basis)-{'world_id','document_id','registry_revision','content_sha256','visibility',
                'draft_sha256','editor_sha256','caret','draft_generation','selection_generation','selection'}:
            raise ValueError('Unclassified Build editor basis')
        work['edit_target'] = {key: deepcopy(basis[key]) for key in ('caret', 'selection') if key in basis}
        for key in ('page_body_offer', 'page_end_offer'):
            if key in editor:
                work['edit_target'][key] = deepcopy(editor[key])
        if 'draft_markdown' in editor:
            work['editor_markdown'] = editor['draft_markdown']
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
            'markdown': row['markdown']} for row in related['pages']]
        work['related_page_availability'] = [{'title': row['page']['title'],
            'visibility': row['page']['visibility'], 'acquisition': row['acquisition']}
            for row in related['availability']]
        work['related_page_scope'] = 'Saved active worldbuilding pages in this World, excluding the current page.'
        work['related_page_absence'] = 'This catalog does not prove that other pages do not exist.'
    from .authored_graph_references import model_reference_choices
    references = model_reference_choices(execution)
    if references is not None:
        work['selected_references'] = references
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
