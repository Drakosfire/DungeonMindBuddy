"""Provider-only Plan work; saved ownership remains in existing host records."""
from copy import deepcopy

REQUIRED = frozenset({'committed_plan_blocks', 'session_evidence',
    'dialogue_reference', 'authored_sources', 'requested_work'})
OPTIONAL = frozenset({'current_page_draft', 'focused_edit_target', 'selected_references', 'related_authored_pages'})


def is_semantic_frame(frame):
    return isinstance(frame, dict) and REQUIRED <= set(frame) <= REQUIRED | OPTIONAL


def semantic_frame(host, execution):
    """Project explicit field roles, without changing bodies or host selectors."""
    from .plan_jev_graph_packet import NATIVE_WORK_SCHEMA
    if host.get('schema') != NATIVE_WORK_SCHEMA:
        raise ValueError('Semantic Plan work requires its existing host frame')
    if set(host) - (REQUIRED | {'schema', 'current_page_draft', 'focused_edit_target', 'authored_references', 'related_authored_pages'}):
        raise ValueError('Unclassified native Plan work fields')
    view = {key: deepcopy(host[key]) for key in ('committed_plan_blocks',
        'dialogue_reference', 'requested_work')}
    view['session_evidence'] = [
        {key: deepcopy(session[key]) for key in ('title', 'ended_at') if key in session}
        | {'sources': [{key: deepcopy(source[key]) for key in ('kind', 'text_blocks') if key in source}
            for source in session['sources']]}
        for session in host['session_evidence']]
    # One ordered input-local catalog, matching the existing authored block owner.
    groups = [view['committed_plan_blocks']] + [source['text_blocks']
        for session in view['session_evidence'] for source in session['sources']]
    aliases = {}
    for blocks in groups:
        for row in blocks:
            original = row['selection_id']
            if original is not None:
                if original in aliases:
                    raise ValueError('Plan work repeats an authored selection')
                row['selection_id'] = aliases[original] = f'work{len(aliases)}'
    view['authored_sources'] = []
    for source in host['authored_sources']:
        blocks = host
        for key in source['body_path']:
            blocks = blocks[key]
        view['authored_sources'].append(dict(source_kind=source['source_kind'],
            source_name=source['source_name'], selection_ids=[aliases[row['selection_id']]
                for row in blocks if row['selection_id'] is not None]))
    if 'current_page_draft' in host:
        draft = host['current_page_draft']
        if set(draft) - {'state', 'primary_authoring_context', 'body_path', 'markdown'}:
            raise ValueError('Unclassified current Plan draft fields')
        view['current_page_draft'] = {key: deepcopy(draft[key])
            for key in ('state', 'primary_authoring_context', 'markdown') if key in draft}
        if 'body_path' in draft:
            if draft['body_path'] != ['committed_plan_blocks']:
                raise ValueError('Unknown saved Plan body reuse')
            view['current_page_draft']['uses_committed_plan'] = True
    if 'focused_edit_target' in host:
        target = host['focused_edit_target']
        if set(target) - {'kind', 'location', 'selected_text', 'playable_body'}:
            raise ValueError('Unclassified Plan edit target fields')
        view['focused_edit_target'] = deepcopy(target)
    from .authored_graph_references import model_reference_choices
    references = model_reference_choices(execution)
    if references is not None:
        view['selected_references'] = references
    if 'related_authored_pages' in host:
        view['related_authored_pages'] = {'role': host['related_authored_pages']['role'],
            'pages': [{'read_id': f'page{i}', 'title': row['page']['title'], 'markdown': row['markdown']}
                for i,row in enumerate(host['related_authored_pages']['pages'])]}
    return view


def frame_in_request(body):
    """Choose the disjoint current codec; never parse nested source/user text."""
    from .source_writer_output import strict_json
    from .plan_jev_graph_packet import NATIVE_WORK_SCHEMA
    candidates, historical = [], 0
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
        elif {'committed_plan_blocks', 'session_evidence', 'requested_work'}.intersection(value):
            if not is_semantic_frame(value) or message.get('role') != 'user':
                raise ValueError('Malformed semantic Plan surface work')
            candidates.append(value)
    if len(candidates) > 1 or candidates and historical:
        raise ValueError('Ambiguous semantic Plan surface work')
    return candidates[0] if candidates else None


def resolve_related_read_alias(value, reads):
    """The same input-local order as the provider work projection, no new ledger."""
    aliases={f'page{i}':str(read.read_id) for i,read in enumerate(reads)}
    if value not in aliases:
        raise ValueError('Related Plan selection names an unincluded saved page')
    return aliases[value]
