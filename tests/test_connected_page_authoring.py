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
    from fastapi.testclient import TestClient
    token = 'synthetic-connected-page-operator-token-123456'
    monkeypatch.setenv('DMB_AGENT_GRAPH_AUTH_MODE', 'local_operator')
    monkeypatch.setenv('DMB_AGENT_GRAPH_AUTH_ENVIRONMENT', 'local')
    monkeypatch.setenv('DMB_AGENT_GRAPH_LOCAL_OPERATOR_TOKEN', token)
    c.client = TestClient(c.client.app, client=('127.0.0.1', 54000), headers={'Authorization': 'Bearer '+token})
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


@pytest.mark.parametrize('endpoint', ['prepare', 'confirm', 'read'])
def test_operation_requires_local_gm_before_any_operation_io(case, endpoint):
    from fastapi.testclient import TestClient
    client = TestClient(case.client.app, client=('127.0.0.1', 54001))
    if endpoint == 'prepare':
        response = client.post('/api/live/connected-pages/prepare', json=case.request)
    elif endpoint == 'confirm':
        response = client.post('/api/live/connected-pages/confirm', json={
            'operation_id': case.request['operation_id'], 'world_id': case.record.world_id, 'confirm_token': 'not-a-token'})
    else:
        response = client.get('/api/live/connected-pages/'+case.request['operation_id'], params={'world_id': case.record.world_id})
    assert response.status_code == 401
    assert not (case.root/'out/registries/connected_pages').exists()
    assert len(list_workspace_documents(case.root, kind='worldbuilding_source')) == 1
    assert case.authority.publish_calls == 0


def test_operation_rejects_non_loopback_even_with_operator_bearer(case):
    from fastapi.testclient import TestClient
    client = TestClient(case.client.app, client=('203.0.113.10', 54002), headers=dict(case.client.headers))
    response = client.post('/api/live/connected-pages/prepare', json=case.request)
    assert response.status_code == 403
    assert not (case.root/'out/registries/connected_pages').exists()
    assert case.authority.publish_calls == 0


def test_missing_operation_with_retained_page_is_not_reported_as_safe_absence(case):
    operation = prepare(case)
    path = owner._path(case.root, case.request['operation_id'])
    path.unlink()
    response = get(case)
    assert response.status_code == 409
    assert get_workspace_document(case.root, operation['page']['document_id']).status == 'active'
    assert case.authority.publish_calls == 0


@pytest.fixture
def saved_case(case):
    snapshot=get_workspace_document_snapshot(case.root,case.record.document_id)
    case.request['origin']={"kind":"saved_page_excerpt","document_id":case.record.document_id,
        "revision":snapshot.loaded_revision,"content_sha256":snapshot.content_sha256,
        "line_start":1,"line_end":1,"selected_text":snapshot.markdown.splitlines()[0]}
    return case


def test_exact_saved_excerpt_creates_connected_page_without_editor_fabrication(saved_case):
    c=saved_case
    before=(c.target.read_bytes(),get_workspace_document(c.root,c.record.document_id))
    operation=prepare(c)
    assert operation['schema']=='dmb_connected_page_operation_v2'
    assert operation['source_origin']=={'kind':'saved_page_excerpt','source_text_sha256':c.selector.content_sha256,'line_start':1,'line_end':1}
    assert 'editor_json' not in operation['intent']['origin']
    assert c.authority.publish_calls==0
    snapshot=get_workspace_document_snapshot(c.root,operation['page']['document_id'])
    assert 'saved revision' in snapshot.markdown and 'captured working copy' not in snapshot.markdown
    assert '> '+c.request['origin']['selected_text'] in snapshot.markdown
    result=confirm(c,operation)
    assert result.status_code==200,result.text
    assert result.json()['connections']['relationships']==['owns','operates']
    assert get(c).json()==result.json()
    assert prepare(c)['page']['document_id']==operation['page']['document_id']
    assert confirm(c,result.json()).status_code==200
    assert c.authority.publish_calls==1
    assert (c.target.read_bytes(),get_workspace_document(c.root,c.record.document_id))==before


@pytest.mark.parametrize('mutation',['quote','start','end','hash','revision','world','kind','mixed_editor','empty'])
def test_saved_origin_refuses_mismatch_before_reservation(saved_case,mutation):
    c=saved_case;request=deepcopy(c.request);origin=request['origin']
    if mutation=='quote':origin['selected_text']='Brin owns a different forge.'
    elif mutation=='start':origin['line_start']=0
    elif mutation=='end':origin['line_end']=2
    elif mutation=='hash':origin['content_sha256']='a'*64
    elif mutation=='revision':origin['revision']+=1
    elif mutation=='world':request['world_id']='foreign'
    elif mutation=='kind':origin['kind']='captured_working_copy'
    elif mutation=='mixed_editor':origin['editor_json']=c.editor
    else:origin['selected_text']=' '
    response=c.client.post('/api/live/connected-pages/prepare',json=request)
    assert response.status_code in {409,422},response.text
    assert len(list_workspace_documents(c.root,kind='worldbuilding_source'))==1
    assert not list((c.root/'out/registries/connected_pages').glob('*.json'))
    assert c.authority.publish_calls==0


def test_saved_excerpt_full_table_rows_preserve_exact_origin_and_source(saved_case):
    c=saved_case
    text='# Households\n\n| Name | Task |\n| --- | --- |\n| Copper 🔨 | Repair lantern hook before dusk |\n'
    c.target.write_text(text)
    record=mark_workspace_document_committed(c.root,c.record.document_id)
    snapshot=get_workspace_document_snapshot(c.root,record.document_id)
    c.request['origin'].update(revision=snapshot.loaded_revision,content_sha256=snapshot.content_sha256,line_start=3,line_end=5,selected_text='\n'.join(text.splitlines()[2:5]))
    operation=prepare(c)
    created=get_workspace_document_snapshot(c.root,operation['page']['document_id'])
    assert '> | Name | Task |' in created.markdown
    assert '> | Copper 🔨 | Repair lantern hook before dusk |' in created.markdown
    assert c.target.read_text()==text


def test_saved_excerpt_retry_preserves_origin_after_source_and_created_page_change(saved_case):
    c=saved_case;operation=prepare(c)
    assert confirm(c,operation).status_code==200
    created=c.root/operation['page']['target_relpath'];created.write_text('# Author kept writing\n')
    mark_workspace_document_committed(c.root,operation['page']['document_id'])
    c.target.write_text('Source changed after initial reservation.\n');mark_workspace_document_committed(c.root,c.record.document_id)
    replay=prepare(c)
    assert replay['intent']['origin']==operation['intent']['origin']
    assert replay['page']['document_id']==operation['page']['document_id']
    assert created.read_text()=='# Author kept writing\n'
    assert get(c).json()['phase']=='complete'
    assert c.authority.publish_calls==1
    changed=deepcopy(c.request);changed['origin']['selected_text']='New request for the same operation'
    assert c.client.post('/api/live/connected-pages/prepare',json=changed).status_code==409


def test_saved_origin_cannot_be_reinterpreted_as_historical_working_capture(saved_case):
    c=saved_case;operation=prepare(c)
    path=owner._path(c.root,operation['operation_id'])
    stored=json.loads(path.read_text());stored['schema']='dmb_connected_page_operation_v1';path.write_text(json.dumps(stored))
    assert get(c).status_code==409
    assert c.authority.publish_calls==0


def test_saved_origin_concurrent_retry_has_one_retained_page(saved_case):
    from apps.live_control_server.models.connected_page import parse_connected_page_intent
    c=saved_case;intent=parse_connected_page_intent(c.request)
    with ThreadPoolExecutor(max_workers=2) as pool:
        results=list(pool.map(lambda _:owner.prepare_connected_page(c.root,intent),range(2)))
    assert results[0]['page']['document_id']==results[1]['page']['document_id']
    assert len(list_workspace_documents(c.root,kind='worldbuilding_source'))==2
    assert c.authority.publish_calls==0


def test_saved_origin_partial_graph_prepare_recovers_without_source_reread_or_duplicate(saved_case,monkeypatch):
    c=saved_case;original=owner.prepare_graph_object_authoring_write
    monkeypatch.setattr(owner,'prepare_graph_object_authoring_write',lambda *_args,**_kwargs:(_ for _ in ()).throw(owner.ConnectedPageError('Interrupted after source save')))
    assert c.client.post('/api/live/connected-pages/prepare',json=c.request).status_code==409
    retained=get(c).json();assert retained['phase']=='saved'
    c.target.write_text('A newer source after reservation.\n');mark_workspace_document_committed(c.root,c.record.document_id)
    monkeypatch.setattr(owner,'prepare_graph_object_authoring_write',original)
    operation=prepare(c)
    assert operation['page']['document_id']==retained['page']['document_id']
    assert operation['intent']['origin']==retained['intent']['origin']
    assert confirm(c,operation).status_code==200
    assert len(list_workspace_documents(c.root,kind='worldbuilding_source'))==2
    assert c.authority.publish_calls==1


def test_saved_origin_requires_existing_operator_authority(saved_case):
    from fastapi.testclient import TestClient
    c=saved_case
    with TestClient(c.client.app,client=('127.0.0.1',54001)) as client:
        assert client.post('/api/live/connected-pages/prepare',json=c.request).status_code==401
    assert len(list_workspace_documents(c.root,kind='worldbuilding_source'))==1
    assert c.authority.publish_calls==0


def test_supported_connected_page_uses_database_source_spans(case, monkeypatch):
    from pathlib import Path
    case.request['relationships'] = ['owns']
    original_open = Path.open
    def guarded(path, *args, **kwargs):
        if 'graph_documents' in path.parts or path.name == 'source_span_index.json':
            pytest.fail('connected page reopened a source/span mirror')
        return original_open(path, *args, **kwargs)
    monkeypatch.setattr(Path, 'open', guarded)
    operation = prepare(case)
    response = confirm(case, operation)
    assert response.status_code == 200, response.text
    assert response.json()['connections']['relationships'] == ['owns']
    assert case.authority.publish_calls == 1
