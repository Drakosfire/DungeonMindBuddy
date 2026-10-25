"""Mounted page/registry/Tiptap/native-publication saga; native ports only are fakes."""
import hashlib
import json
import uuid
from concurrent.futures import ThreadPoolExecutor
from copy import deepcopy

import pytest

from tests.test_graph_document_source import case as source_case  # noqa: F401
from apps.live_control_server.services.workspace_document_registry import (
    list_workspace_documents, get_workspace_document, get_workspace_document_snapshot,
    mark_workspace_document_committed, discard_workspace_document,
)
from apps.live_control_server.services import connected_page_authoring as owner
from apps.live_control_server.models.connected_page import ConnectedPageIntent


@pytest.fixture
def case(request, monkeypatch):
    c = request.getfixturevalue("source_case")
    monkeypatch.setattr('apps.live_control_server.routes.workspace_documents._managed_world_root', lambda: c.root)
    text = 'Brin’s Blacksmithy: Repairs gear and makes practical metalwork.'
    c.editor = json.dumps({'type': 'doc', 'content': [{'type': 'paragraph', 'content': [
        {'type': 'text', 'text': text, 'marks': [{'type': 'bold'}]}]}]}, ensure_ascii=False)
    c.request = {'operation_id': str(uuid.uuid4()), 'world_id': c.record.world_id, 'title': 'Brin’s Blacksmithy',
        'origin': {'document_id': c.record.document_id, 'revision': c.selector.revision,
            'content_sha256': c.selector.content_sha256, 'editor_json': c.editor,
            'editor_sha256': hashlib.sha256(c.editor.encode()).hexdigest(),
            'selection_from': 1, 'selection_to': 1+len('Brin’s Blacksmithy'), 'selected_text': 'Brin’s Blacksmithy'},
        'place': {'label': 'Brin’s Blacksmithy', 'kind': 'location'},
        'person': {'label': 'Brin', 'kind': 'npc'}, 'relationships': ['owns', 'operates'],
        'mode': 'build_out', 'instructions': 'A practical forge with room for future secrets.'}
    return c


def prepare(c, request=None):
    response = c.client.post('/api/live/connected-pages/prepare', json=request or c.request)
    assert response.status_code == 200, response.text
    return response.json()


def confirm(c, operation):
    return c.client.post('/api/live/connected-pages/confirm', json={
        'operation_id': operation['operation_id'], 'world_id': c.record.world_id,
        'confirm_token': operation['prepared']['confirm_token']})


def get(c):
    return c.client.get('/api/live/connected-pages/' + c.request['operation_id'], params={'world_id': c.record.world_id})


def test_create_initial_page_real_connections_and_reopen(case):
    c = case
    before = (c.target.read_bytes(), get_workspace_document(c.root, c.record.document_id))
    operation = prepare(c)
    assert operation['phase'] == 'prepared'
    assert c.authority.publish_calls == 0
    page = operation['page']
    snapshot = get_workspace_document_snapshot(c.root, page['document_id'])
    assert snapshot.record.authority_state == 'draft'
    assert snapshot.record.content_status == 'committed'
    assert 'Brin owns Brin’s Blacksmithy.' in snapshot.markdown
    assert 'Brin operates Brin’s Blacksmithy.' in snapshot.markdown
    assert c.record.document_id in snapshot.markdown
    assert 'captured working copy' in snapshot.markdown
    result = confirm(c, operation)
    assert result.status_code == 200, result.text
    complete = result.json()
    assert complete['phase'] == 'complete'
    assert complete['connections']['place_node_id']
    assert complete['connections']['person_node_id']
    assert complete['connections']['relationships'] == ['owns', 'operates']
    assert get(c).json() == complete
    assert prepare(c)['page']['document_id'] == page['document_id']
    assert confirm(c, complete).status_code == 200
    assert c.authority.publish_calls == 1
    assert (c.target.read_bytes(), get_workspace_document(c.root, c.record.document_id)) == before
    assert len(list_workspace_documents(c.root, kind='worldbuilding_source')) == 2


@pytest.mark.parametrize('mutation', ['quote', 'range', 'digest', 'json', 'world', 'revision'])
def test_inconsistent_or_foreign_origin_refuses_before_creation(case, mutation):
    request = deepcopy(case.request)
    if mutation == 'quote':
        request['origin']['selected_text'] = 'A forged occurrence'
    elif mutation == 'range':
        request['origin']['selection_from'] += 1
    elif mutation == 'digest':
        request['origin']['editor_sha256'] = 'ab'*32
    elif mutation == 'json':
        request['origin']['editor_json'] = '{}'
        request['origin']['editor_sha256'] = hashlib.sha256(b'{}').hexdigest()
    elif mutation == 'world':
        request['world_id'] = 'foreign'
    else:
        request['origin']['revision'] += 1
    response = case.client.post('/api/live/connected-pages/prepare', json=request)
    assert response.status_code == 409, response.text
    assert len(list_workspace_documents(case.root, kind='worldbuilding_source')) == 1
    assert case.authority.publish_calls == 0


def test_utf16_selection_and_marks_are_verified(case):
    document = {'type': 'doc', 'content': [{'type': 'paragraph', 'content': [
        {'type': 'text', 'text': '🔨 '}, {'type': 'text', 'text': 'Brin’s Blacksmithy', 'marks': [{'type': 'bold'}]}]}]}
    request = deepcopy(case.request)
    request['origin'].update(editor_json=json.dumps(document, ensure_ascii=False), selection_from=4,
        selection_to=4+len('Brin’s Blacksmithy'))
    request['origin']['editor_sha256'] = hashlib.sha256(request['origin']['editor_json'].encode()).hexdigest()
    assert prepare(case, request)['phase'] == 'prepared'
    request['operation_id'] = str(uuid.uuid4())
    request['origin']['selection_from'] = 3
    assert case.client.post('/api/live/connected-pages/prepare', json=request).status_code == 409


@pytest.mark.parametrize('failure_point', ['create', 'save', 'prepare', 'publish'])
def test_response_loss_retries_one_reserved_page(case, monkeypatch, failure_point):
    c = case
    functions = {'create': 'create_workspace_document', 'save': 'commit_tiptap_markdown_write',
        'prepare': 'prepare_graph_object_authoring_write', 'publish': 'commit_graph_object_authoring_write'}
    name = functions[failure_point]
    original = getattr(owner, name)
    failed = False
    def lose_response(*args, **kwargs):
        nonlocal failed
        result = original(*args, **kwargs)
        if not failed:
            failed = True
            raise owner.ConnectedPageError('Simulated lost response')
        return result
    monkeypatch.setattr(owner, name, lose_response)
    if failure_point == 'publish':
        operation = prepare(c)
        assert confirm(c, operation).status_code == 409
        monkeypatch.setattr(owner, name, original)
        assert confirm(c, operation).status_code == 200
    else:
        assert c.client.post('/api/live/connected-pages/prepare', json=c.request).status_code == 409
        retained = get(c)
        assert retained.status_code == 200, retained.text
        assert retained.json()['page'], retained.text
        monkeypatch.setattr(owner, name, original)
        operation = prepare(c)
        assert confirm(c, operation).status_code == 200
    assert len(list_workspace_documents(c.root, kind='worldbuilding_source')) == 2
    assert c.authority.publish_calls == 1


def test_later_page_edits_and_source_edits_survive_exact_recovery(case):
    operation = prepare(case)
    result = confirm(case, operation)
    assert result.status_code == 200
    page = operation['page']
    target = case.root / page['target_relpath']
    target.write_text('# Author kept writing\n')
    mark_workspace_document_committed(case.root, page['document_id'])
    case.target.write_text('The source changed too.\n')
    mark_workspace_document_committed(case.root, case.record.document_id)
    recovered = prepare(case)
    assert recovered['phase'] == 'complete'
    assert confirm(case, recovered).status_code == 200
    assert target.read_text() == '# Author kept writing\n'
    assert get(case).json()['intent']['origin']['editor_json'] == case.editor
    assert case.authority.publish_calls == 1


def test_same_operation_changed_intent_conflicts(case):
    first = prepare(case)
    request = deepcopy(case.request)
    request['title'] = 'Different page'
    assert case.client.post('/api/live/connected-pages/prepare', json=request).status_code == 409
    assert get(case).json()['page']['document_id'] == first['page']['document_id']
    assert len(list_workspace_documents(case.root, kind='worldbuilding_source')) == 2


def test_concurrent_same_operation_creates_one_page(case):
    intent = ConnectedPageIntent.model_validate(case.request)
    with ThreadPoolExecutor(max_workers=2) as pool:
        results = list(pool.map(lambda _: owner.prepare_connected_page(case.root, intent), range(2)))
    assert results[0]['page']['document_id'] == results[1]['page']['document_id']
    assert len(list_workspace_documents(case.root, kind='worldbuilding_source')) == 2


@pytest.mark.parametrize('target', ['source', 'page'])
def test_discard_refuses_confirmation_without_native_write(case, target):
    operation = prepare(case)
    document_id = case.record.document_id if target == 'source' else operation['page']['document_id']
    discard_workspace_document(case.root, document_id)
    assert confirm(case, operation).status_code == 409
    assert case.authority.publish_calls == 0


def test_existing_identity_must_match_current_world_label_and_kind(case, monkeypatch):
    from types import SimpleNamespace
    def projection(*args, **kwargs):
        return SimpleNamespace(projection=SimpleNamespace(nodes=[]))
    monkeypatch.setattr('apps.live_control_server.services.managed_world_graph_projection.project_managed_world_graph', projection)
    request = deepcopy(case.request)
    request['person']['node_id'] = 'foreign-brin'
    response = case.client.post('/api/live/connected-pages/prepare', json=request)
    assert response.status_code == 409
    assert len(list_workspace_documents(case.root, kind='worldbuilding_source')) == 1


def test_reuse_existing_person_and_location_keeps_exact_node_identities(case, monkeypatch):
    from types import SimpleNamespace
    nodes = [SimpleNamespace(node_id='person:brin', label='Brin', kind='npc'),
             SimpleNamespace(node_id='location:forge', label='Brin’s Blacksmithy', kind='location')]
    monkeypatch.setattr('apps.live_control_server.services.managed_world_graph_projection.project_managed_world_graph',
        lambda *args, **kwargs: SimpleNamespace(projection=SimpleNamespace(nodes=nodes)))
    case.request['person']['node_id'] = 'person:brin'
    case.request['place']['node_id'] = 'location:forge'
    operation = prepare(case)
    result = confirm(case, operation)
    assert result.status_code == 200, result.text
    assert result.json()['connections']['person_node_id'] == 'person:brin'
    assert result.json()['connections']['place_node_id'] == 'location:forge'
    assert result.json()['receipt']['created_node_ids'] == {}
    assert case.authority.publish_calls == 1


@pytest.mark.parametrize('existing', [False, True])
def test_page_without_person_is_a_scaffold_and_can_describe_existing_location(case, monkeypatch, existing):
    from types import SimpleNamespace
    case.request.update(person=None, relationships=[], mode='scaffold')
    if existing:
        case.request['place']['node_id'] = 'existing:place'
        monkeypatch.setattr('apps.live_control_server.services.managed_world_graph_projection.project_managed_world_graph',
            lambda *args, **kwargs: SimpleNamespace(projection=SimpleNamespace(nodes=[
                SimpleNamespace(node_id='existing:place', label='Brin’s Blacksmithy', kind='location')])))
    operation = prepare(case)
    result = confirm(case, operation)
    assert result.status_code == 200, result.text
    assert result.json()['connections']['person_node_id'] is None
    assert result.json()['connections']['place_node_id']


def test_created_page_edited_during_partial_save_is_retained_without_overwrite(case, monkeypatch):
    original = owner.prepare_tiptap_markdown_write
    monkeypatch.setattr(owner, 'prepare_tiptap_markdown_write', lambda **_: (_ for _ in ()).throw(owner.ConnectedPageError('Paused before initial save')))
    assert case.client.post('/api/live/connected-pages/prepare', json=case.request).status_code == 409
    operation = get(case).json()
    page = operation['page']
    target = case.root / page['target_relpath']
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text('# My newer writing\n')
    mark_workspace_document_committed(case.root, page['document_id'])
    monkeypatch.setattr(owner, 'prepare_tiptap_markdown_write', original)
    response = case.client.post('/api/live/connected-pages/prepare', json=case.request)
    assert response.status_code == 409
    assert target.read_text() == '# My newer writing\n'
    assert get(case).json()['page']['document_id'] == page['document_id']
    assert case.authority.publish_calls == 0


def test_native_mapping_drift_refuses_and_keeps_created_page(case):
    operation = prepare(case)
    case.binding.native_world_id = 'other-world'
    response = confirm(case, operation)
    assert response.status_code == 409
    assert get(case).json()['page']['document_id'] == operation['page']['document_id']
    assert case.authority.publish_calls == 0
