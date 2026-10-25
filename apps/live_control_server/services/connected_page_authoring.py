"""Recoverable page + native connection saga. No inference and no source-page saves."""
from __future__ import annotations

import hashlib
import json
import os
import re
import uuid
from pathlib import Path
from urllib.parse import urlencode

from apps.live_control_server.config import artifact_data_root
from apps.live_control_server.models.connected_page import (ConnectedPageRequest, SavedConnectedPageIntent, SavedPageExcerptOrigin, parse_connected_page_intent)
from apps.live_control_server.services.graph_document_source import GraphDocumentSource, resolve_graph_document_source
from apps.live_control_server.services.graph_object_authoring_prepare import (
    GraphObjectAuthoringPrepareRequest, prepare_graph_object_authoring_write,
    GraphObjectAuthoringCommitRequest,
)
from apps.live_control_server.services.graph_object_authoring_commit import commit_graph_object_authoring_write
from apps.live_control_server.services.registry_file_lock import registry_mutation_lock
from apps.live_control_server.services.workspace_document_registry import (
    create_workspace_document, get_workspace_document, get_workspace_document_snapshot, list_workspace_documents,
)
from apps.live_control_server.services.tiptap_markdown_write import (
    TiptapMarkdownWritePrepareRequest, TiptapMarkdownWriteCommitRequest,
    prepare_tiptap_markdown_write, commit_tiptap_markdown_write,
)


class ConnectedPageError(ValueError):
    def __init__(self, message, *, status_code=409):
        super().__init__(message)
        self.status_code = status_code


def _sha(value: str) -> str:
    return hashlib.sha256(value.encode()).hexdigest()


def _json(value) -> str:
    return json.dumps(value, sort_keys=True, separators=(',', ':'), ensure_ascii=False)


def _units(value: str) -> int:
    return len(value.encode('utf-16-le')) // 2


def verify_origin_capture(origin) -> str:
    """ProseMirror positions count UTF-16 units and structural node boundaries."""
    try:
        if _sha(origin.editor_json) != origin.editor_sha256:
            raise ValueError('The captured editor snapshot differs from its digest')
        document = json.loads(origin.editor_json)
        if not isinstance(document, dict) or document.get('type') != 'doc':
            raise ValueError('document required')
        matches = []
        blocks = []

        def walk(node, position, depth=0):
            if depth > 80 or not isinstance(node, dict) or not isinstance(node.get('type'), str):
                raise ValueError('Invalid editor node')
            kind = node['type']
            if kind == 'text':
                if not isinstance(node.get('text'), str):
                    raise ValueError('Invalid text')
                return _units(node['text'])
            content = node.get('content', [])
            if not isinstance(content, list):
                raise ValueError('Invalid editor content')
            start = position if kind == 'doc' else position + 1
            if kind in ('paragraph', 'heading') and all(isinstance(child, dict) and child.get('type') == 'text' for child in content):
                text = ''.join(child['text'] for child in content)
                blocks.append(text)
                if start <= origin.selection_from < origin.selection_to <= start + _units(text):
                    raw = text.encode('utf-16-le')
                    matches.append(raw[(origin.selection_from-start)*2:(origin.selection_to-start)*2].decode('utf-16-le'))
            offset = start
            for child in content:
                offset += walk(child, offset, depth+1)
            if kind == 'doc':
                return offset
            # Empty text blocks are non-leaf ProseMirror nodes; atoms have size 1.
            return offset-start+2 if content or kind in ('paragraph', 'heading', 'codeBlock') else 1

        walk(document, 0)
        if matches != [origin.selected_text] or not origin.selected_text.strip():
            raise ValueError('Quote does not match the selected text block')
        return _sha('\n\n'.join(blocks))
    except (ValueError, TypeError, KeyError, UnicodeError, RecursionError) as exc:
        raise ConnectedPageError('Select text within one paragraph or heading; the captured quote and range must match') from exc


def _path(root, operation_id):
    path = root / 'out/registries/connected_pages' / (str(uuid.UUID(str(operation_id))) + '.json')
    if not path.resolve().is_relative_to(root.resolve()):
        raise ConnectedPageError('Connected page storage is outside its owner')
    return path


def _persist(path: Path, state):
    path.parent.mkdir(mode=0o700, parents=True, exist_ok=True)
    temporary = path.with_name('.' + path.name + '.' + uuid.uuid4().hex + '.tmp')
    try:
        with temporary.open('x', encoding='utf-8') as handle:
            os.chmod(temporary, 0o600)
            handle.write(_json(state))
            handle.flush()
            os.fsync(handle.fileno())
        temporary.replace(path)
        fd = os.open(path.parent, os.O_RDONLY | os.O_DIRECTORY)
        try:
            os.fsync(fd)
        finally:
            os.close(fd)
    finally:
        temporary.unlink(missing_ok=True)


def _read(path):
    if not path.exists():
        return None
    try:
        if path.is_symlink():
            raise ValueError('symlink operation')
        state = json.loads(path.read_text())
        intent = parse_connected_page_intent(state['intent'])
        if (set(state) != {'schema', 'intent', 'intent_sha256', 'page_id', 'phase', 'initial_markdown',
                          'working_text_sha256', 'saved_source', 'graph_request', 'prepared', 'receipt'}
                or state['schema'] != operation_schema(intent)
                or (isinstance(intent,SavedConnectedPageIntent) and state['working_text_sha256'] != intent.origin.content_sha256)
                or state['intent_sha256'] != _sha(_json(intent.model_dump(mode='json')))
                or str(intent.operation_id) != path.stem
                or state['phase'] not in ('reserved', 'created', 'saved', 'prepared', 'complete')):
            raise ValueError('invalid operation')
        uuid.UUID(state['page_id'])
        return state
    except (ValueError, TypeError, KeyError, OSError) as exc:
        raise ConnectedPageError('The retained connected-page operation is unavailable or changed') from exc


def operation_schema(intent):
    return 'dmb_connected_page_operation_v2' if isinstance(intent, SavedConnectedPageIntent) else 'dmb_connected_page_operation_v1'


def verify_saved_excerpt(root, intent):
    """The source owner verifies exact saved bytes; no invented editor selection."""
    source = _ownership(root, intent, initial=True)
    snapshot = get_workspace_document_snapshot(root, source.document_id)
    origin = intent.origin
    if (not snapshot.file_exists or source.content_status != 'committed'
            or source.source_domain != 'worldbuilding'
            or snapshot.loaded_revision != origin.revision
            or snapshot.content_sha256 != origin.content_sha256):
        raise ConnectedPageError('The exact saved source is unavailable or changed; review the current excerpt again')
    lines = snapshot.markdown.splitlines()
    if (origin.line_end > len(lines)
            or '\n'.join(lines[origin.line_start - 1:origin.line_end]) != origin.selected_text):
        raise ConnectedPageError('The excerpt does not match those exact saved lines')
    return snapshot.content_sha256


def _ownership(root, intent, *, initial=False):
    source = get_workspace_document(root, str(intent.origin.document_id))
    if (source.kind != 'worldbuilding_source' or source.status != 'active'
            or source.world_id != intent.world_id or source.campaign_id != intent.world_id):
        raise ConnectedPageError('The source page no longer belongs to this World')
    if initial:
        snapshot = get_workspace_document_snapshot(root, source.document_id)
        if snapshot.loaded_revision != intent.origin.revision or snapshot.content_sha256 != intent.origin.content_sha256:
            raise ConnectedPageError('The saved source base changed; capture the current selection again')
    return source


def _objects(intent, root):
    from apps.live_control_server.services.managed_world_graph_projection import (
        ManagedWorldGraphProjectionRequest, project_managed_world_graph,
    )
    for obj in [intent.place, *([intent.person] if intent.person else [])]:
        if obj.node_id:
            result = project_managed_world_graph(ManagedWorldGraphProjectionRequest(
                schema='dmb_managed_world_graph_projection_request_v1',
                managedWorldId=intent.world_id, queryText=obj.label), root=root)
            match = next((n for n in result.projection.nodes if n.node_id == obj.node_id), None)
            if match is None or match.label != obj.label or match.kind != obj.kind:
                raise ConnectedPageError('An existing person or location changed or is outside this World')


def _escape(text):
    return re.sub(r'([\\`*_{}\[\]<>])', r'\\\1', text)


def _declarations(intent):
    return ([f'{intent.person.label} {predicate} {intent.place.label}.' for predicate in intent.relationships]
            if intent.person else [f'{intent.place.label} is a location.'])


def _initial_markdown(intent, source):
    source_url = '/build?' + urlencode({'world': intent.world_id, 'documentId': str(intent.origin.document_id), 'campaign': intent.world_id})
    declaration = '\n\n'.join(_escape(sentence) for sentence in _declarations(intent))
    quote = '\n'.join('> ' + line for line in intent.origin.selected_text.splitlines())
    origin_label = (f'saved revision {intent.origin.revision}, lines {intent.origin.line_start}–{intent.origin.line_end}'
        if isinstance(intent.origin,SavedPageExcerptOrigin) else 'captured working copy')
    return (f'# {_escape(intent.title)}\n\n{declaration}\n\n'
        f'## At a glance\n\n_Add the details that matter at your table._\n\n'
        f'## People and activity\n\n_Who is here, and what are they doing?_\n\n'
        f'## The unexpected\n\n_A secret, tension, or possibility to develop._\n\n'
        f'## Origin\n\n[From {_escape(source.title)}]({source_url}) · {origin_label}\n\n{quote}\n')


def _save_initial(root, state, intent):
    page = create_workspace_document(root, title=intent.title, campaign_id=intent.world_id,
        kind='worldbuilding_source', world_id=intent.world_id, source_domain='worldbuilding',
        document_class='lore', authority_state='draft', visibility_state='internal',
        _connected_reservation=(state['page_id'], str(intent.operation_id)))
    snapshot = get_workspace_document_snapshot(root, page.document_id)
    if snapshot.record.content_status == 'committed':
        if snapshot.markdown != state['initial_markdown']:
            raise ConnectedPageError('The created page has newer writing. It is retained; initial creation will not overwrite it')
    else:
        if page.revision != 1 or snapshot.file_exists:
            raise ConnectedPageError('The reserved page changed before its initial save; the page is retained')
        prepared = prepare_tiptap_markdown_write(root=root, request=TiptapMarkdownWritePrepareRequest(
            document_id=page.document_id, expected_revision=page.revision,
            markdown=state['initial_markdown'], write_mode='source_import'))
        commit_tiptap_markdown_write(root=root, request=TiptapMarkdownWriteCommitRequest(
            document_id=page.document_id, expected_revision=page.revision, markdown=state['initial_markdown'],
            write_mode='source_import', writer_confirm_token=prepared.writer_confirm_token))
        snapshot = get_workspace_document_snapshot(root, page.document_id)
    selector = GraphDocumentSource(documentId=page.document_id, revision=snapshot.loaded_revision,
        contentSha256=snapshot.content_sha256)
    resolve_graph_document_source(root, selector, world_id=intent.world_id, campaign_id=intent.world_id)
    return selector.model_dump(mode='json', by_alias=True)


def _graph_request(root, state, intent):
    source = resolve_graph_document_source(root, GraphDocumentSource.model_validate(state['saved_source']),
        world_id=intent.world_id, campaign_id=intent.world_id)
    index = json.loads(source.source_span_index_path.read_text())
    lines = state['initial_markdown'].splitlines()
    def selection(sentence):
        target = _escape(sentence)
        spans = [span for span in index['spans'] if '\n'.join(lines[span['start_line']-1:span['end_line']]) == target]
        if len(spans) != 1:
            raise ConnectedPageError('The initial declaration has no unambiguous source span')
        return {'selectionKind': 'text_span', 'selectedText': target, 'normalizedSelectedText': target,
                'sourceSpanRefId': spans[0]['source_span_id']}
    proposals = []
    first = selection(_declarations(intent)[0])
    visibility = {'visibility': 'gm_private', 'revealState': 'unrevealed'}
    def ref(obj, key):
        if obj.node_id:
            return {'refKind': 'existing_graph_node', 'nodeId': obj.node_id, 'label': obj.label, 'kind': obj.kind}
        proposals.append({'localProposalId': key, 'proposalKind': 'object', 'status': 'staged_local',
            'selection': first, 'objectRef': {'label': obj.label, 'kind': obj.kind, 'aliases': [], 'summary': ''},
            'visibility': visibility, 'graphScopes': ['campaign_memory_graph']})
        return {'refKind': 'local_proposal', 'localProposalId': key, 'label': obj.label, 'kind': obj.kind}
    place = ref(intent.place, 'place')
    if intent.person:
        person = ref(intent.person, 'person')
        for predicate, sentence in zip(intent.relationships, _declarations(intent), strict=True):
            proposals.append({'localProposalId': predicate, 'proposalKind': 'relationship', 'status': 'staged_local',
                'selection': selection(sentence), 'sourceObjectRef': person, 'targetObjectRef': place,
                'relationshipType': predicate, 'direction': 'directed', 'visibility': visibility,
                'graphScopes': ['campaign_memory_graph']})
    # If a page describes an existing location with no new connections, a
    # reviewed exact mention links it through the same governed alias authority.
    if not proposals:
        proposals.append({'localProposalId': 'mention', 'proposalKind': 'link_existing', 'status': 'staged_local',
            'selection': first, 'selectedText': intent.place.label, 'normalizedSelectedText': intent.place.label,
            'existingObjectRef': place, 'aliasText': intent.place.label, 'operation': 'reference',
            'visibility': visibility, 'graphScopes': ['campaign_memory_graph']})
    for proposal in proposals:
        proposal['provenancePreview'] = {'operatorNote': 'Explicit connected-page author declaration'}
    return GraphObjectAuthoringPrepareRequest(worldId=intent.world_id, campaignId=intent.world_id,
        documentSource=state['saved_source'], proposals=proposals).model_dump(mode='json', by_alias=True)


def _response(root, state):
    page = (get_workspace_document(root, state['page_id']) if state['phase'] != 'reserved'
            else next((record for record in list_workspace_documents(root, kind='worldbuilding_source')
                       if record.document_id == state['page_id']), None))
    intent = parse_connected_page_intent(state['intent'])
    if page and (page.status != 'active' or page.kind != 'worldbuilding_source'
                 or page.world_id != intent.world_id or page.campaign_id != intent.world_id
                 or page.connected_page_operation_id != str(intent.operation_id)):
        raise ConnectedPageError('The retained created page changed ownership or was discarded')
    receipt = state['receipt']
    ids = receipt.get('created_node_ids', {}) if receipt else {}
    return {'schema': operation_schema(intent), 'operation_id': str(intent.operation_id),
        'phase': state['phase'], 'intent': state['intent'], 'page': page.model_dump(mode='json') if page else None,
        'source_origin': ({'kind':'saved_page_excerpt','source_text_sha256':state['working_text_sha256'],
            'line_start':intent.origin.line_start,'line_end':intent.origin.line_end}
            if isinstance(intent.origin,SavedPageExcerptOrigin) else {'kind': 'captured_working_copy', 'working_text_sha256': state['working_text_sha256']}),
        'initial_source': state['saved_source'],
        'prepared': state['prepared'], 'receipt': receipt,
        'connections': {'place_node_id': intent.place.node_id or ids.get('place'),
            'person_node_id': intent.person.node_id or ids.get('person') if intent.person else None,
            'relationships': intent.relationships} if receipt else None}


def prepare_connected_page(root: Path, intent: ConnectedPageRequest):
    root = artifact_data_root(root)
    working_hash = None if isinstance(intent,SavedConnectedPageIntent) else verify_origin_capture(intent.origin)
    path = _path(root, intent.operation_id)
    with registry_mutation_lock(path):
        state = _read(path)
        digest = _sha(_json(intent.model_dump(mode='json')))
        if state and state['intent_sha256'] != digest:
            raise ConnectedPageError('This operation already belongs to a different page request')
        source = _ownership(root, intent, initial=state is None)
        if state is None:
            working_hash = verify_saved_excerpt(root,intent) if isinstance(intent,SavedConnectedPageIntent) else working_hash
            _objects(intent, root)
            state = {'schema': operation_schema(intent), 'intent': intent.model_dump(mode='json'),
                'intent_sha256': digest, 'page_id': str(uuid.uuid4()), 'phase': 'reserved',
                'initial_markdown': _initial_markdown(intent, source), 'working_text_sha256': working_hash,
                'saved_source': None, 'graph_request': None, 'prepared': None, 'receipt': None}
            _persist(path, state)
        if state['phase'] == 'reserved':
            create_workspace_document(root, title=intent.title, campaign_id=intent.world_id,
                kind='worldbuilding_source', world_id=intent.world_id, source_domain='worldbuilding',
                document_class='lore', authority_state='draft', visibility_state='internal',
                _connected_reservation=(state['page_id'], str(intent.operation_id)))
            state['phase'] = 'created'
            _persist(path, state)
        if state['phase'] == 'created':
            state['saved_source'] = _save_initial(root, state, intent)
            state['phase'] = 'saved'
            _persist(path, state)
        if state['phase'] == 'saved':
            if state['graph_request'] is None:
                state['graph_request'] = _graph_request(root, state, intent)
                _persist(path, state)
            prepared = prepare_graph_object_authoring_write(
                GraphObjectAuthoringPrepareRequest.model_validate(state['graph_request']), corpus_root=root)
            if prepared.expressibility != 'EXPRESSIBLE' or not prepared.confirm_token:
                raise ConnectedPageError('The page is retained but its connections cannot be prepared')
            state['prepared'] = prepared.model_dump(mode='json')
            state['phase'] = 'prepared'
            _persist(path, state)
        return _response(root, state)


def get_connected_page(root: Path, operation_id, world_id: str):
    root = artifact_data_root(root)
    path = _path(root, operation_id)
    with registry_mutation_lock(path):
        state = _read(path)
        if state is None:
            if any(record.connected_page_operation_id == str(operation_id) and record.world_id == world_id
                   for record in list_workspace_documents(root, kind='worldbuilding_source', status=None)):
                raise ConnectedPageError('The created page is retained but its operation is unavailable')
            raise ConnectedPageError('Connected-page operation not found in this World', status_code=404)
        if state['intent']['world_id'] != world_id:
            raise ConnectedPageError('Connected-page operation not found in this World', status_code=404)
        _ownership(root, parse_connected_page_intent(state['intent']))
        return _response(root, state)


def confirm_connected_page(root: Path, operation_id, world_id: str, confirm_token: str):
    root = artifact_data_root(root)
    path = _path(root, operation_id)
    with registry_mutation_lock(path):
        state = _read(path)
        if state is None:
            if any(record.connected_page_operation_id == str(operation_id) and record.world_id == world_id
                   for record in list_workspace_documents(root, kind='worldbuilding_source', status=None)):
                raise ConnectedPageError('The created page is retained but its operation is unavailable')
            raise ConnectedPageError('Connected-page operation not found in this World', status_code=404)
        if state['intent']['world_id'] != world_id:
            raise ConnectedPageError('Connected-page operation not found in this World', status_code=404)
        _ownership(root, parse_connected_page_intent(state['intent']))
        _response(root, state)
        if not state['prepared'] or state['prepared']['confirm_token'] != confirm_token:
            raise ConnectedPageError('Confirm the exact reviewed connections for this operation')
        if state['receipt'] is None:
            request = GraphObjectAuthoringCommitRequest.model_validate({**state['graph_request'], 'confirmToken': confirm_token})
            receipt = commit_graph_object_authoring_write(request, corpus_root=root)
            if not receipt.committed:
                raise ConnectedPageError('The page is retained; native publication is not acknowledged')
            state['receipt'] = receipt.model_dump(mode='json')
            state['phase'] = 'complete'
            _persist(path, state)
        return _response(root, state)
