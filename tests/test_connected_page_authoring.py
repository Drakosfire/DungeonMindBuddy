"""Mounted APP page recovery plus actual Core/WorldKeeper native publication."""
from tests.page_fixtures import page_text, save_page
from apps.live_control_server.services.workspace_document_registry import get_workspace_document
import hashlib
import json
import uuid
from concurrent.futures import ThreadPoolExecutor
from copy import deepcopy

import pytest

from tests.test_graph_document_source import case as source_case  # noqa: F401
from apps.live_control_server.services.workspace_document_registry import (list_workspace_documents, get_workspace_document_snapshot, discard_workspace_document)
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
    from dataclasses import asdict
    from datetime import UTC, datetime
    from dungeonmind.infrastructure.memory.vnext_sources import InMemoryNativeSourceEvidenceRepository
    from dungeonmind.contracts.vnext.knowledge import PublishKnowledgeRevisionCommand
    from tests.test_con_ready_play_worldkeeper_consumer import _repository, SPACE_ID
    from apps.live_control_server.services.managed_world_graph_projection import ManagedWorldSourceIdentity
    from apps.live_control_server.integrations.dungeonmind import native_registry_source as native, native_world_source_admission as admission
    from apps.live_control_server.services.agent_graph_auth import NativeGraphPrincipal
    c.principal = NativeGraphPrincipal('local-operator', 'gm', 'local_operator')
    c.native_binding = ManagedWorldSourceIdentity(c.record.world_id, c.binding.native_world_id, 1, '')
    c.bound = asdict(c.native_binding); c.bound.pop('provisioning_id')
    seed = _repository(evidence=False)
    original = seed.get_revision(SPACE_ID, seed.get_head(SPACE_ID).head_revision_id)
    c.repo = InMemoryNativeSourceEvidenceRepository()
    c.repo.publish_revision(PublishKnowledgeRevisionCommand(
        space_id=c.binding.native_world_id, operation_ids=['fixture-genesis'],
        graph_schema=original.revision.graph_schema, graph_payload=original.graph_payload,
        domain_contract_ref=original.revision.domain_contract_ref,
        semantic_profile_ref=original.revision.semantic_profile_ref, created_at=datetime.now(UTC)))
    monkeypatch.setattr(native, 'binding', lambda world: deepcopy(c.bound) if world == c.record.world_id else (_ for _ in ()).throw(ValueError('Foreign World')))
    monkeypatch.setattr(native, 'repository', lambda: c.repo)
    monkeypatch.setattr(native, 'read_repository', lambda: c.repo)
    monkeypatch.setattr(admission, '_repository', lambda: c.repo)
    monkeypatch.setattr(admission, '_source_world_binding', lambda root, world: c.native_binding)
    c.legacy_authority = c.authority
    class NativePublicationCount:
        @property
        def publish_calls(self):
            return sum(key[1].startswith('dmb-connected-page:') for key in c.repo._prospective_results)
    c.authority = NativePublicationCount()
    return c


@pytest.fixture
def legacy_case(case):
    case.legacy_adoption = True
    case.authority = case.legacy_authority
    return case


def _legacy_prepare(c, request):
    # Frozen historical input for the explicit offline adopter; no live route
    # is allowed to execute this retired publication path.
    from apps.live_control_server.services.graph_object_authoring_prepare import prepare_graph_object_authoring_write, GraphObjectAuthoringPrepareRequest
    from application_state.content.connected_pages import locked_operation
    intent = owner.parse_connected_page_intent(request)
    state = dict(schema=owner.legacy_operation_schema(intent), intent=intent.model_dump(mode='json'),
        intent_sha256=owner._sha(owner._json(intent.model_dump(mode='json'))), page_id=str(uuid.uuid4()),
        phase='created', initial_markdown=owner._initial_markdown(intent, c.record),
        working_text_sha256=owner.verify_origin_capture(intent.origin), saved_source=None,
        graph_request=None, prepared=None, receipt=None)
    state['saved_source'] = owner._save_initial(c.root, state, intent)
    state['graph_request'] = owner._legacy_graph_request(c.root, state, intent)
    state['prepared'] = prepare_graph_object_authoring_write(GraphObjectAuthoringPrepareRequest.model_validate(state['graph_request']), corpus_root=c.root).model_dump(mode='json')
    state['phase'] = 'prepared'
    with locked_operation(intent.operation_id) as journal:
        journal.save(state)
    return owner._response(c.root, state)


def prepare(c, request=None):
    if getattr(c, 'legacy_adoption', False):
        return _legacy_prepare(c, request or c.request)
    response = c.client.post('/api/live/connected-pages/prepare', json=request or c.request)
    assert response.status_code == 200, response.text
    return response.json()


def confirm(c, operation):
    if getattr(c, 'legacy_adoption', False) and operation['phase'] != 'complete':
        from apps.live_control_server.services.graph_object_authoring_prepare import GraphObjectAuthoringCommitRequest
        from apps.live_control_server.services.graph_object_authoring_commit import commit_graph_object_authoring_write
        from application_state.content.connected_pages import locked_operation
        with locked_operation(operation['operation_id']) as journal:
            state = journal.read()
            state['receipt'] = commit_graph_object_authoring_write(
                GraphObjectAuthoringCommitRequest.model_validate({**state['graph_request'], 'confirmToken': state['prepared']['confirm_token']}), corpus_root=c.root).model_dump(mode='json')
            state['phase'] = 'complete'
            journal.save(state)
        return get(c)
    return c.client.post('/api/live/connected-pages/confirm', json={
        'operation_id': operation['operation_id'], 'world_id': c.record.world_id,
        'confirm_token': operation['prepared']['confirm_token']})


def get(c):
    return c.client.get('/api/live/connected-pages/' + c.request['operation_id'], params={'world_id': c.record.world_id})


def test_create_initial_page_real_connections_and_reopen(case):
    c = case
    before = (page_text(c.root, c.record.document_id).encode("utf-8"), get_workspace_document(c.root, c.record.document_id))
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
    assert (page_text(c.root, c.record.document_id).encode("utf-8"), get_workspace_document(c.root, c.record.document_id)) == before
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


@pytest.mark.parametrize('failure_point', ['create', 'save', 'evidence', 'prepare', 'publish'])
def test_response_loss_retries_one_reserved_page(case, monkeypatch, failure_point):
    c = case
    functions = {'create': 'create_workspace_document', 'save': 'commit_tiptap_markdown_write',
        'evidence': 'publish_native_source_evidence_extension', 'prepare': 'prepare', 'publish': 'confirm'}
    name = functions[failure_point]
    boundary = owner.native_graph if failure_point in ('evidence', 'prepare', 'publish') else owner
    original = getattr(boundary, name)
    failed = False
    def lose_response(*args, **kwargs):
        nonlocal failed
        result = original(*args, **kwargs)
        if not failed:
            failed = True
            raise owner.ConnectedPageError('Simulated lost response')
        return result
    monkeypatch.setattr(boundary, name, lose_response)
    if failure_point == 'publish':
        operation = prepare(c)
        assert confirm(c, operation).status_code == 409
        monkeypatch.setattr(boundary, name, original)
        assert confirm(c, operation).status_code == 200
    else:
        assert c.client.post('/api/live/connected-pages/prepare', json=c.request).status_code == 409
        retained = get(c)
        assert retained.status_code == 200, retained.text
        assert retained.json()['page'], retained.text
        monkeypatch.setattr(boundary, name, original)
        operation = prepare(c)
        assert confirm(c, operation).status_code == 200
    assert len(list_workspace_documents(c.root, kind='worldbuilding_source')) == 2
    assert c.authority.publish_calls == 1


def test_later_page_edits_and_source_edits_survive_exact_recovery(case):
    operation = prepare(case)
    result = confirm(case, operation)
    assert result.status_code == 200
    page = operation['page']
    save_page(case.root, page['document_id'], '# Author kept writing\n')
    get_workspace_document(case.root, page['document_id'])
    save_page(case.root, case.record.document_id, 'The source changed too.\n')
    get_workspace_document(case.root, case.record.document_id)
    recovered = prepare(case)
    assert recovered['phase'] == 'complete'
    assert confirm(case, recovered).status_code == 200
    assert page_text(case.root, page['document_id']) == '# Author kept writing\n'
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
        results = list(pool.map(lambda _: owner.prepare_connected_page(case.root, intent, principal=case.principal), range(2)))
    assert results[0]['page']['document_id'] == results[1]['page']['document_id']
    assert len(list_workspace_documents(case.root, kind='worldbuilding_source')) == 2


@pytest.mark.parametrize('target', ['source', 'page'])
def test_discard_refuses_confirmation_without_native_write(case, target):
    operation = prepare(case)
    document_id = case.record.document_id if target == 'source' else operation['page']['document_id']
    discard_workspace_document(case.root, document_id)
    assert confirm(case, operation).status_code == 409
    assert case.authority.publish_calls == 0


def seed_existing(c):
    from datetime import UTC, datetime
    from dungeonmind.application.vnext import publish_native_source_evidence_extension
    from dungeonmind.contracts.vnext.native_source import NativeSourceEvidenceExtensionV1
    from apps.live_control_server.integrations.dungeonmind import native_world_source_admission as admission, native_registry_source as native
    from apps.live_control_server.integrations.worldkeeper import registry_standing_consumer as transport
    from worldkeeper.application import contracts as wk
    from graph_memory.vnext.domain_runtime import GM_LABEL, PLAYER_LABEL
    snapshot = get_workspace_document_snapshot(c.root, c.record.document_id)
    a = admission.admit_native_world_source(c.root, c.record.document_id,
        expected_revision=snapshot.loaded_revision, expected_body_sha256=snapshot.content_sha256)
    context, _ = native.access_context(c.repo, c.binding.native_world_id)
    domain, profile = native.descriptors(c.repo, c.binding.native_world_id, context['revision_id'])
    raw=snapshot.markdown.encode(); quote=raw.rstrip(b'\n')
    extension=publish_native_source_evidence_extension(repository=c.repo,
        request=NativeSourceEvidenceExtensionV1(space_id=c.binding.native_world_id, extension_id='fixture:identities',
            original_admission_id=a.admission_id, source_artifact_id=a.source_artifact_id, source_revision_id=a.source_revision_id,
            expected_body_sha256=a.body_sha256, expected_parent_revision_id=context['revision_id'],
            expected_source_authority_epoch=context['source_epoch'], created_at=datetime.now(UTC),
            spans=[dict(client_ref='statement',evidence_role='support',start_byte=0,end_byte=len(quote),expected_slice_sha256=hashlib.sha256(quote).hexdigest())]),
        domain_contract=domain,semantic_profile=profile,audience_labels=(GM_LABEL,PLAYER_LABEL))
    meta=wk.AssertionMetadata(scope=(),visibility=wk.Visibility('labels_any',(GM_LABEL,)),epistemic_basis='asserted',
        claim_mode='dungeonbuddy.claim:fact',standing='established',evidence_ref_ids=(extension.bindings[0].evidence_ref_id,),temporal_scope=wk.TemporalScope(kind='unknown'))
    ops=tuple(wk.CreateObject(key,(
        wk.CreateFact(key+'.name','dnd5e:name',wk.LiteralFactValue(label),meta),
        wk.CreateFact(key+'.kind','dnd5e:classification',wk.TermRefFactValue(kind),meta)))
        for key,label,kind in [('person','Brin','dungeonbuddy:character'),('place','Brin’s Blacksmithy','dnd5e:location')])
    runtime=transport.runtime(c.repo,domain,profile,now=datetime.now(UTC),operation_id='fixture:existing-identities')
    result=runtime.commit_prepared_change(runtime.prepare_change(wk.WorldChangeIntent(c.binding.native_world_id,'fixture',ops)),confirmed_by='fixture')
    return {r.client_op_id:r.durable_object_id for r in result.object_results}


def test_existing_identity_must_match_current_world_label_and_kind(case, monkeypatch):
    monkeypatch.setattr('apps.live_control_server.services.managed_world_graph_projection.project_managed_world_graph',
        lambda *_args,**_kwargs:pytest.fail('Retired projection called'))
    request = deepcopy(case.request)
    request['person']['node_id'] = 'foreign-brin'
    response = case.client.post('/api/live/connected-pages/prepare', json=request)
    assert response.status_code == 409
    assert len(list_workspace_documents(case.root, kind='worldbuilding_source')) == 1


def test_reuse_existing_person_and_location_keeps_exact_node_identities(case, monkeypatch):
    identities = seed_existing(case)
    case.request['person']['node_id'] = identities['person']
    case.request['place']['node_id'] = identities['place']
    operation = prepare(case)
    result = confirm(case, operation)
    assert result.status_code == 200, result.text
    assert result.json()['connections']['person_node_id'] == identities['person']
    assert result.json()['connections']['place_node_id'] == identities['place']
    assert result.json()['receipt']['created_node_ids'] == {}
    assert case.authority.publish_calls == 1
    from apps.live_control_server.integrations.dungeonmind import native_registry_source as native
    from dungeonmind.application.vnext import EntityReadService
    read, *_ = native.read_context(case.repo,case.binding.native_world_id,case.repo.get_head(case.binding.native_world_id).head_revision_id,None,'gm',scope_mode='world')
    person = EntityReadService().get_complete_entity(read, identities['person'])
    assert {a.value.term for a in person.assertions if a.predicate=='dnd5e:classification'} == {'dungeonbuddy:character'}


@pytest.mark.parametrize('existing', [False, True])
def test_page_without_person_is_a_scaffold_and_can_describe_existing_location(case, monkeypatch, existing):
    case.request.update(person=None, relationships=[], mode='scaffold')
    if existing:
        case.request['place']['node_id'] = seed_existing(case)['place']
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
    save_page(case.root, page['document_id'], '# My newer writing\n')
    get_workspace_document(case.root, page['document_id'])
    monkeypatch.setattr(owner, 'prepare_tiptap_markdown_write', original)
    response = case.client.post('/api/live/connected-pages/prepare', json=case.request)
    assert response.status_code == 409
    assert page_text(case.root, page['document_id']) == '# My newer writing\n'
    assert get(case).json()['page']['document_id'] == page['document_id']
    assert case.authority.publish_calls == 0


def test_native_mapping_drift_refuses_and_keeps_created_page(case):
    operation = prepare(case)
    case.bound['native_world_id'] = 'other-world'
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
    from application_state.unit_of_work import unit_of_work
    with unit_of_work() as conn:
        conn.execute('DELETE FROM content.connected_page_operation WHERE operation_id=%s', (case.request['operation_id'],))
    response = get(case)
    assert response.status_code == 409
    retry = case.client.post('/api/live/connected-pages/prepare', json=case.request)
    assert retry.status_code == 409
    assert len(list_workspace_documents(case.root, kind='worldbuilding_source')) == 2
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
    before=(page_text(c.root, c.record.document_id).encode("utf-8"),get_workspace_document(c.root,c.record.document_id))
    operation=prepare(c)
    assert operation['schema']=='dmb_connected_page_operation_v3'
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
    assert (page_text(c.root, c.record.document_id).encode("utf-8"),get_workspace_document(c.root,c.record.document_id))==before


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
    save_page(c.root, c.record.document_id, text)
    record=get_workspace_document(c.root, c.record.document_id)
    snapshot=get_workspace_document_snapshot(c.root,record.document_id)
    c.request['origin'].update(revision=snapshot.loaded_revision,content_sha256=snapshot.content_sha256,line_start=3,line_end=5,selected_text='\n'.join(text.splitlines()[2:5]))
    operation=prepare(c)
    created=get_workspace_document_snapshot(c.root,operation['page']['document_id'])
    assert '> | Name | Task |' in created.markdown
    assert '> | Copper 🔨 | Repair lantern hook before dusk |' in created.markdown
    assert page_text(c.root, c.record.document_id)==text


def test_saved_excerpt_retry_preserves_origin_after_source_and_created_page_change(saved_case):
    c=saved_case;operation=prepare(c)
    assert confirm(c,operation).status_code==200
    pass;save_page(c.root, operation['page']['document_id'], '# Author kept writing\n')
    get_workspace_document(c.root, operation['page']['document_id'])
    save_page(c.root, c.record.document_id, 'Source changed after initial reservation.\n');get_workspace_document(c.root, c.record.document_id)
    replay=prepare(c)
    assert replay['intent']['origin']==operation['intent']['origin']
    assert replay['page']['document_id']==operation['page']['document_id']
    assert page_text(c.root, operation['page']['document_id'])=='# Author kept writing\n'
    assert get(c).json()['phase']=='complete'
    assert c.authority.publish_calls==1
    changed=deepcopy(c.request);changed['origin']['selected_text']='New request for the same operation'
    assert c.client.post('/api/live/connected-pages/prepare',json=changed).status_code==409


def test_saved_origin_cannot_be_reinterpreted_as_historical_working_capture(saved_case):
    c=saved_case;operation=prepare(c)
    from application_state.unit_of_work import unit_of_work
    with unit_of_work() as conn:
        conn.execute("UPDATE content.connected_page_operation SET payload=jsonb_set(payload,'{schema}', '\"dmb_connected_page_operation_v1\"') WHERE operation_id=%s", (operation['operation_id'],))
    assert get(c).status_code==409
    assert c.authority.publish_calls==0


def test_saved_origin_concurrent_retry_has_one_retained_page(saved_case):
    from apps.live_control_server.models.connected_page import parse_connected_page_intent
    c=saved_case;intent=parse_connected_page_intent(c.request)
    with ThreadPoolExecutor(max_workers=2) as pool:
        results=list(pool.map(lambda _:owner.prepare_connected_page(c.root,intent,principal=c.principal),range(2)))
    assert results[0]['page']['document_id']==results[1]['page']['document_id']
    assert len(list_workspace_documents(c.root,kind='worldbuilding_source'))==2
    assert c.authority.publish_calls==0


def test_saved_origin_partial_graph_prepare_recovers_without_source_reread_or_duplicate(saved_case,monkeypatch):
    c=saved_case;original=owner.native_graph.prepare
    monkeypatch.setattr(owner.native_graph,'prepare',lambda *_args,**_kwargs:(_ for _ in ()).throw(owner.ConnectedPageError('Interrupted after source save')))
    assert c.client.post('/api/live/connected-pages/prepare',json=c.request).status_code==409
    retained=get(c).json();assert retained['phase']=='saved'
    save_page(c.root, c.record.document_id, 'A newer source after reservation.\n');get_workspace_document(c.root, c.record.document_id)
    monkeypatch.setattr(owner.native_graph,'prepare',original)
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


def test_saved_excerpt_uses_coherent_committed_owner_projection(saved_case, monkeypatch):
    c = saved_case
    original = get_workspace_document_snapshot(c.root, c.record.document_id)
    projection = original.model_copy(update={"file_exists": False,
        "record": original.record.model_copy(update={"target_relpath": None})})
    monkeypatch.setattr(owner, "get_committed_page_snapshot", lambda *args: projection)
    intent = owner.parse_connected_page_intent(c.request)
    assert owner.verify_saved_excerpt(c.root, intent) == c.selector.content_sha256
    for changes in ({"content_status": "draft"}, {"document_id": str(uuid.uuid4())},
                    {"world_id": "foreign"}, {"revision": original.loaded_revision + 1},
                    {"status": "discarded"}):
        projection.record = original.record.model_copy(update=changes)
        with pytest.raises(owner.ConnectedPageError):
            owner.verify_saved_excerpt(c.root, intent)
    assert c.authority.publish_calls == 0


def _export_operation(c):
    from application_state.content.connected_pages import locked_operation
    with locked_operation(c.request['operation_id']) as journal:
        state = journal.read()
    path = c.root / (c.request['operation_id'] + '.json')
    path.write_text(json.dumps(state))
    return path, state


def _delete_operation(c):
    from application_state.unit_of_work import unit_of_work
    with unit_of_work() as conn:
        conn.execute('DELETE FROM content.connected_page_operation WHERE operation_id=%s', (c.request['operation_id'],))


def test_operation_files_are_not_live_recovery_authority(legacy_case):
    case = legacy_case
    operation = confirm(case, prepare(case)).json()
    path, _ = _export_operation(case)
    historical = case.root / 'out/registries/connected_pages' / path.name
    historical.parent.mkdir(parents=True)
    historical.write_bytes(path.read_bytes())
    _delete_operation(case)
    assert get(case).status_code == 409
    assert historical.exists()
    adopted = owner.adopt_connected_page_operation(case.root, historical)
    assert adopted == operation
    assert owner.adopt_connected_page_operation(case.root, historical) == operation
    assert get(case).json() == operation
    assert case.authority.publish_calls == 1
    assert len(list_workspace_documents(case.root, kind='worldbuilding_source')) == 2


def test_adoption_never_overwrites_newer_operation_or_page(legacy_case):
    case = legacy_case
    operation = prepare(case)
    path, _ = _export_operation(case)
    complete = confirm(case, operation).json()
    save_page(case.root, operation['page']['document_id'], '# Newer writing\n')
    with pytest.raises(owner.ConnectedPageError, match='overwrite'):
        owner.adopt_connected_page_operation(case.root, path)
    assert get(case).json()['phase'] == complete['phase'] == 'complete'
    assert page_text(case.root, operation['page']['document_id']) == '# Newer writing\n'
    assert case.authority.publish_calls == 1


@pytest.mark.parametrize('change', ['intent', 'page', 'symlink'])
def test_adoption_rejects_inconsistent_or_foreign_record(legacy_case, change):
    case = legacy_case
    prepare(case)
    path, state = _export_operation(case)
    _delete_operation(case)
    if change == 'intent':
        state['intent']['world_id'] = 'foreign'
        path.write_text(json.dumps(state))
    elif change == 'page':
        state['page_id'] = case.record.document_id
        path.write_text(json.dumps(state))
    else:
        link = path.with_name(str(uuid.uuid4()) + '.json')
        link.symlink_to(path)
        path = link
    with pytest.raises(owner.ConnectedPageError):
        owner.adopt_connected_page_operation(case.root, path)
    assert get(case).status_code == 409
    assert case.authority.publish_calls == 0


def test_database_operation_does_not_create_registry_directory(case):
    operation = prepare(case)
    assert confirm(case, operation).status_code == 200
    assert not (case.root / 'out/registries/connected_pages').exists()


@pytest.mark.parametrize('change', ['receipt', 'source', 'request', 'prepared', 'missing_publication', 'incomplete'])
def test_adoption_requires_exact_authoritative_completed_publication(legacy_case, change):
    case = legacy_case
    operation = prepare(case)
    if change != 'incomplete':
        assert confirm(case, operation).status_code == 200
    path, state = _export_operation(case)
    _delete_operation(case)
    calls = case.authority.publish_calls
    if change == 'receipt':
        state['receipt']['created_node_ids']['place'] = 'node:forged'
    elif change == 'source':
        state['saved_source']['documentId'] = case.record.document_id
    elif change == 'request':
        state['graph_request']['proposals'][0]['objectRef']['label'] = 'Forged label'
    elif change == 'prepared':
        state['prepared']['confirm_token'] = 'forged-token'
    elif change == 'missing_publication':
        case.authority.receipts.clear()
    path.write_text(json.dumps(state))
    with pytest.raises(owner.ConnectedPageError):
        owner.adopt_connected_page_operation(case.root, path)
    assert get(case).status_code == 409
    assert case.authority.publish_calls == calls


@pytest.mark.parametrize('field', ['label', 'kind'])
def test_native_existing_identity_never_falls_back_to_new_object(case, field):
    identities=seed_existing(case)
    case.request['person']['node_id']=identities['person'] if field=='label' else identities['place']
    if field=='label':
        case.request['person']['label']='A different person'
    response=case.client.post('/api/live/connected-pages/prepare',json=case.request)
    assert response.status_code==409
    assert len(list_workspace_documents(case.root,kind='worldbuilding_source'))==1
    assert case.authority.publish_calls==0


def test_stale_native_parent_is_reprepared_only_on_explicit_retry(case):
    operation=prepare(case)
    seed_existing(case)
    assert confirm(case,operation).status_code==409
    assert case.authority.publish_calls==0
    retry=prepare(case)
    assert retry['operation_id']==operation['operation_id']
    assert retry['page']['document_id']==operation['page']['document_id']
    assert confirm(case,operation).status_code==409
    assert confirm(case,retry).status_code==200
    assert case.authority.publish_calls==1
    assert len(list_workspace_documents(case.root,kind='worldbuilding_source'))==2


def test_unknown_native_commit_recovers_before_requiring_page_freshness(case,monkeypatch):
    operation=prepare(case)
    actual=owner.native_graph.confirm
    def lose(*args,**kwargs):
        actual(*args,**kwargs)
        raise owner.ConnectedPageError('Lost commit response')
    monkeypatch.setattr(owner.native_graph,'confirm',lose)
    assert confirm(case,operation).status_code==409
    assert case.authority.publish_calls==1
    save_page(case.root,operation['page']['document_id'],'# Newer writing after committed response loss\n')
    save_page(case.root,case.record.document_id,'# Newer source\n')
    monkeypatch.setattr(owner.native_graph,'confirm',actual)
    assert confirm(case,operation).status_code==200
    assert case.authority.publish_calls==1
    assert page_text(case.root,operation['page']['document_id'])=='# Newer writing after committed response loss\n'


def test_retired_writer_cannot_resume_incomplete_historical_operation(legacy_case):
    c=legacy_case;operation=prepare(c)
    assert c.client.post('/api/live/connected-pages/prepare',json=c.request).status_code==409
    response=c.client.post('/api/live/connected-pages/confirm',json=dict(operation_id=operation['operation_id'],world_id=c.record.world_id,confirm_token=operation['prepared']['confirm_token']))
    assert response.status_code==409
    assert c.authority.publish_calls==0
    assert len(list_workspace_documents(c.root,kind='worldbuilding_source'))==2


def test_native_confirmation_requires_the_reviewing_principal(case):
    from apps.live_control_server.services.agent_graph_auth import NativeGraphPrincipal
    operation=prepare(case)
    with pytest.raises(owner.native_graph.ConnectedGraphError,match='exact review'):
        owner.confirm_connected_page(case.root,operation['operation_id'],case.record.world_id,
            operation['prepared']['confirm_token'],principal=NativeGraphPrincipal('different-operator','gm','local_operator'))
    assert case.authority.publish_calls==0


def test_native_denied_source_cannot_publish(case,monkeypatch):
    from types import SimpleNamespace
    operation=prepare(case)
    monkeypatch.setattr(owner.native_graph,'open_admitted_native_text',lambda *_:SimpleNamespace(status='unavailable'))
    response=confirm(case,operation)
    assert response.status_code==409
    assert case.authority.publish_calls==0
    assert get(case).json()['phase']=='prepared'
