"""Registered-document source → real occurrence verifier → governed native port."""
import hashlib
import json
from types import SimpleNamespace

import pytest
from fastapi.testclient import TestClient
from pydantic import ValidationError

from apps.live_control_server.services.graph_document_source import (
    GraphDocumentSource, frozen_document_source, resolve_graph_document_source,
)
from apps.live_control_server.services.graph_object_authoring_prepare import (
    GRAPH_REVIEW_PREPARE_BINDING_KEY_ENV,
)
from apps.live_control_server.services.workspace_document_registry import (
    create_workspace_document, mark_workspace_document_committed,
    discard_workspace_document,
)
from apps.live_control_server.services.source_artifact_registry import SourceArtifactRegistryError
from tests.test_graph_object_authoring_prepare import FakeSourceAdmission, FakeWorldGraphAuthority, object_proposal, relationship_proposal

WORLD = 'eldyrwild'
TEXT = "Brin owns and operates Brin’s Blacksmithy.\n"


@pytest.fixture
def case(tmp_path, monkeypatch):
    monkeypatch.setenv('DMB_ARTIFACT_DATA_ROOT', str(tmp_path))
    monkeypatch.setenv(GRAPH_REVIEW_PREPARE_BINDING_KEY_ENV, 'document-source-test-key')
    monkeypatch.setattr('apps.live_control_server.config.repo_root', lambda: tmp_path)
    (tmp_path / 'corpus/eldyrwild-markdown').mkdir(parents=True)
    record = create_workspace_document(tmp_path, title='Brin’s Blacksmithy', campaign_id=WORLD,
        kind='worldbuilding_source', world_id=WORLD, source_domain='worldbuilding',
        document_class='lore', authority_state='draft', visibility_state='internal')
    target = tmp_path / record.target_relpath
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(TEXT)
    record = mark_workspace_document_committed(tmp_path, record.document_id)
    selector = GraphDocumentSource(documentId=record.document_id, revision=record.revision,
        contentSha256=hashlib.sha256(TEXT.encode()).hexdigest())
    binding = SimpleNamespace(managed_world_id=WORLD, native_world_id='native:eldyrwild', binding_version=1)
    monkeypatch.setattr('apps.live_control_server.services.managed_world_graph_projection.resolve_managed_world_binding', lambda _: binding)
    # File-backed Build source, not an APP source. Never touch retained APP state.
    monkeypatch.setattr('apps.live_control_server.services.worldbuilding_source_span_read._read_durable_source', lambda **_: None)
    authority, admission = FakeWorldGraphAuthority(), FakeSourceAdmission()
    monkeypatch.setattr('apps.live_control_server.ports.world_graph_authority_access.get_world_graph_authority', lambda: authority)
    monkeypatch.setattr('apps.live_control_server.ports.world_graph_source_admission_access.get_world_graph_source_admission_authority', lambda: admission)
    from apps.live_control_server.main import create_app
    return SimpleNamespace(root=tmp_path, record=record, target=target, selector=selector, binding=binding,
        authority=authority, admission=admission, client=TestClient(create_app()))


def resolve(c):
    return resolve_graph_document_source(c.root, c.selector, world_id=WORLD, campaign_id=WORLD)


def payload(c):
    source = resolve(c)
    index = json.loads(source.source_span_index_path.read_text())
    selection = {'selectionKind': 'text_span', 'selectedText': TEXT.strip(),
        'normalizedSelectedText': TEXT.strip(), 'sourceSpanRefId': index['spans'][0]['source_span_id']}
    def obj(pid, label, kind):
        return object_proposal(localProposalId=pid, selection=selection,
            objectRef={'label': label, 'kind': kind, 'aliases': [], 'summary': ''})
    person = {'refKind': 'local_proposal', 'localProposalId': 'brin', 'label': 'Brin', 'kind': 'npc'}
    place = {'refKind': 'local_proposal', 'localProposalId': 'shop', 'label': 'Brin’s Blacksmithy', 'kind': 'location'}
    return {'worldId': WORLD, 'campaignId': WORLD, 'documentSource': c.selector.model_dump(by_alias=True),
        'proposals': [obj('brin', 'Brin', 'npc'), obj('shop', 'Brin’s Blacksmithy', 'location'),
            *[relationship_proposal(localProposalId=predicate, selection=selection,
                sourceObjectRef=person, targetObjectRef=place, relationshipType=predicate)
                for predicate in ['owns', 'operates']]]}


def prepare(c):
    request = payload(c)
    response = c.client.post('/api/live/graph-authoring/prepare', json=request)
    assert response.status_code == 200, response.text
    return {**request, 'confirmToken': response.json()['confirm_token']}


def test_exact_source_objects_relationships_and_one_native_publication(case):
    request = prepare(case)
    first = case.client.post('/api/live/graph-authoring/commit', json=request)
    assert first.status_code == 200, first.text
    again = case.client.post('/api/live/graph-authoring/commit', json=request)
    assert again.status_code == 200, again.text
    assert case.authority.publish_calls == 1
    contribution = case.authority.published_requests[0].contribution
    assert contribution.world_id == 'native:eldyrwild'
    assert len(contribution.accepted_assertions) == 4
    assert case.target.read_text() == TEXT


def test_immutable_source_survives_later_save_and_lost_confirmation_response(case):
    request = prepare(case)
    source = resolve(case)
    case.authority.fail_publish_after_store = True
    # Native response loss is recovered by the owner; then discard that HTTP
    # response as a browser disconnect would and resume from the retained request.
    assert case.client.post('/api/live/graph-authoring/commit', json=request).status_code == 200
    case.target.write_text('The shop has changed.\n')
    mark_workspace_document_committed(case.root, case.record.document_id)
    assert resolve(case).sealed_source_uri == source.sealed_source_uri
    retry = case.client.post('/api/live/graph-authoring/commit', json=request)
    assert retry.status_code == 200, retry.text
    assert case.authority.publish_calls == 1
    from apps.live_control_server.services.worldbuilding_source_span_read import read_admitted_worldbuilding_span
    index = json.loads(source.source_span_index_path.read_text())
    opened = read_admitted_worldbuilding_span(root=case.root, source_artifact_id=source.source_artifact_id,
        source_span_ref_id=index['spans'][0]['source_span_id'], graph_content_sha256=case.selector.content_sha256,
        max_chars=1000, anchor_id='historical-proof', graph_artifact=source.source_artifact)
    assert opened.content == TEXT.strip()


@pytest.mark.parametrize('extra', [{'sourceRunId': 'run'}, {'recapArtifactId': 'recap'}])
def test_mixed_selectors_refuse_before_native_io(case, extra):
    request = payload(case)
    response = case.client.post('/api/live/graph-authoring/prepare', json={**request, **extra})
    assert response.status_code == 422
    assert response.json()['detail']['code'] == 'source_selector_conflict'
    assert case.authority.recover_calls == case.authority.publish_calls == 0


@pytest.mark.parametrize('field,value', [('revision', 999), ('contentSha256', 'ab' * 32)])
def test_stale_initial_source_does_not_freeze(case, field, value):
    changed = {**case.selector.model_dump(by_alias=True), field: value}
    with pytest.raises((SourceArtifactRegistryError, ValueError)):
        resolve_graph_document_source(case.root, GraphDocumentSource.model_validate(changed), world_id=WORLD, campaign_id=WORLD)
    assert not list((case.root / 'out/registries/source_content').glob('**/source.md'))


@pytest.mark.parametrize('component', ['body', 'index'])
def test_corrupt_frozen_source_refuses_confirmation(case, component):
    request = prepare(case)
    source = resolve(case)
    path = case.root / source.sealed_source_uri.removeprefix('repo://') if component == 'body' else source.source_span_index_path
    path.write_text('corrupted')
    response = case.client.post('/api/live/graph-authoring/commit', json=request)
    assert response.status_code == 409
    assert case.authority.recover_calls == case.authority.publish_calls == 0


def test_selector_tamper_refuses_before_native_recovery(case):
    request = prepare(case)
    request['documentSource']['revision'] += 1
    response = case.client.post('/api/live/graph-authoring/commit', json=request)
    assert response.status_code == 409
    assert response.json()['detail']['code'] == 'confirmation_invalid'
    assert case.authority.recover_calls == 0


@pytest.mark.parametrize('change', ['world', 'discard', 'mapping'])
def test_ownership_or_mapping_drift_refuses(case, change):
    request = prepare(case)
    if change == 'world':
        request['worldId'] = 'foreign'
    elif change == 'discard':
        discard_workspace_document(case.root, case.record.document_id)
    else:
        case.binding.native_world_id = 'other-native'
    response = case.client.post('/api/live/graph-authoring/commit', json=request)
    assert response.status_code == 409
    assert case.authority.recover_calls == case.authority.publish_calls == 0


@pytest.mark.parametrize('value', [True, '2', 0, -1])
def test_revision_is_a_real_positive_integer(value):
    with pytest.raises(ValidationError):
        GraphDocumentSource(documentId='source', revision=value, contentSha256='ab' * 32)


@pytest.mark.parametrize('mutation', ['missing', 'duplicate', 'mixed'])
def test_invalid_local_reference_bundle_has_no_native_publication(case, mutation):
    request = payload(case)
    if mutation == 'missing':
        request['proposals'][2]['sourceObjectRef']['localProposalId'] = 'not-in-bundle'
    elif mutation == 'duplicate':
        request['proposals'][1]['localProposalId'] = 'brin'
    else:
        request['proposals'][2]['sourceObjectRef']['nodeId'] = 'injected-node'
    response = case.client.post('/api/live/graph-authoring/prepare', json=request)
    # Invalid structure may be rejected outright or be a nonconfirmable preview.
    assert response.status_code in (200, 422)
    if response.status_code == 200:
        assert response.json()['expressibility'] == 'INEXPRESSIBLE'
    assert case.authority.recover_calls == case.authority.publish_calls == 0


def test_unretained_source_revision_change_refuses(case):
    from apps.live_control_server.services.workspace_document_registry import update_workspace_document_metadata
    # A registry revision change is not permission to accept arbitrary caller bytes.
    update_workspace_document_metadata(case.root, case.record.document_id,
        title='Renamed', expected_revision=case.record.revision)
    with pytest.raises(SourceArtifactRegistryError):
        resolve(case)


def test_frozen_components_and_source_not_overwritten_on_retry(case):
    source = resolve(case)
    body, index = frozen_document_source(case.root, source.source_artifact)
    before = (body.read_bytes(), index.read_bytes(), body.stat().st_mtime_ns, index.stat().st_mtime_ns)
    resolve(case)
    assert (body.read_bytes(), index.read_bytes(), body.stat().st_mtime_ns, index.stat().st_mtime_ns) == before


@pytest.mark.parametrize('published', [False, True])
def test_expired_confirmation_recovers_only_already_published_receipt(case, published):
    from datetime import UTC, datetime, timedelta
    from unittest.mock import Mock
    from apps.live_control_server.services.graph_object_authoring_prepare import decode_publication_intent, sign_publication_intent
    request = prepare(case)
    if published:
        assert case.client.post('/api/live/graph-authoring/commit', json=request).status_code == 200
    intent = decode_publication_intent(request['confirmToken'])
    intent['expires_at'] = (datetime.now(UTC) - timedelta(days=2)).isoformat()
    request['confirmToken'] = sign_publication_intent(intent)
    case.authority.current_head = Mock(side_effect=AssertionError('Expired confirmation must not reach fresh publication'))
    response = case.client.post('/api/live/graph-authoring/commit', json=request)
    if published:
        assert response.status_code == 200, response.text
        assert case.authority.publish_calls == 1
    else:
        assert response.status_code == 409
        assert response.json()['detail']['code'] == 'confirmation_expired'
        assert case.authority.publish_calls == 0
    case.authority.current_head.assert_not_called()
