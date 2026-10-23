"""Real prepare/confirm occurrence proofs route managed Build ownership to native authority."""
import hashlib
import json
from copy import deepcopy
from types import SimpleNamespace
from unittest.mock import Mock

import pytest

from apps.live_control_server.services.graph_object_authoring_binding import resolve_publication_context
from apps.live_control_server.services.graph_object_authoring_commit import commit_graph_object_authoring_write
from apps.live_control_server.services.graph_object_authoring_prepare import (
    GRAPH_REVIEW_PREPARE_BINDING_KEY_ENV, GraphObjectAuthoringCommitRequest,
    GraphObjectAuthoringError, prepare_graph_object_authoring_write,
)
from graph_memory.source_span import build_source_span_index_for_text, source_span_index_to_dict
from tests.test_graph_object_authoring_prepare import (
    CAMPAIGN_ID, FakeSourceAdmission, FakeWorldGraphAuthority, fake_resolved_source,
    object_proposal, prepare_request,
)


@pytest.fixture
def case(tmp_path, monkeypatch):
    monkeypatch.setenv('DMB_ARTIFACT_DATA_ROOT', str(tmp_path))
    monkeypatch.setenv(GRAPH_REVIEW_PREPARE_BINDING_KEY_ENV, 'synthetic-world-binding-key')
    text = 'Mara keeps the copper bell.\n'
    (tmp_path / 'source.md').write_text(text)
    digest = hashlib.sha256(text.encode()).hexdigest()
    resolved = fake_resolved_source()
    artifact = resolved.source_artifact
    artifact.uri, artifact.content_sha256 = 'repo://source.md', digest
    artifact.workspace_document_id, artifact.workspace_document_revision = 'document-one', 2
    resolved.source_revision_id, resolved.source_domain = 'sha256:' + digest, 'worldbuilding'
    resolved.session_id = None
    index = build_source_span_index_for_text(source_artifact_id=artifact.source_artifact_id,
                                            content_sha256=digest, text=text)
    path = tmp_path / 'index.json'
    path.write_text(json.dumps(source_span_index_to_dict(index)))
    resolved.source_span_index_path = path
    resolved.source_span_index_sha256 = hashlib.sha256(path.read_bytes()).hexdigest()
    request = prepare_request(worldId=CAMPAIGN_ID, sourceRunId='exact-run', proposals=[object_proposal(selection={
        'selectionKind': 'text_span', 'selectedText': 'Mara', 'normalizedSelectedText': 'Mara',
        'sourceSpanRefId': index.spans[0].source_span_id,
    })])
    document = SimpleNamespace(kind='worldbuilding_source', status='active', world_id=CAMPAIGN_ID)
    binding = SimpleNamespace(managed_world_id=CAMPAIGN_ID, native_world_id='native-world-distinct', binding_version=3)
    # Load the reader before patching the separate ownership resolver: its
    # module-level imports must not retain a test-only document getter.
    from apps.live_control_server.services import worldbuilding_source_span_read  # noqa: F401
    monkeypatch.setattr('apps.live_control_server.services.workspace_document_registry.get_workspace_document',
                        lambda root, document_id: document)
    monkeypatch.setattr('apps.live_control_server.services.managed_world_graph_projection.resolve_managed_world_binding',
                        lambda managed: binding)
    monkeypatch.setattr('apps.live_control_server.services.worldbuilding_source_span_read.read_admitted_worldbuilding_span',
                        Mock(return_value=SimpleNamespace(outcome='enough', content=text.strip())))
    admission = FakeSourceAdmission()
    admission.prove_or_admit = Mock(wraps=admission.prove_or_admit)
    admission.prove = Mock(wraps=admission.prove)
    authority = FakeWorldGraphAuthority()
    authority.current_head = Mock(wraps=authority.current_head)
    return SimpleNamespace(root=tmp_path, resolved=resolved, artifact=artifact, document=document,
                           binding=binding, request=request, admission=admission, authority=authority)


def prepare(c):
    return prepare_graph_object_authoring_write(c.request, corpus_root=c.root,
        authority=c.authority, source_admission=c.admission, resolved_source=c.resolved)


def confirm(c, prepared):
    request = GraphObjectAuthoringCommitRequest.model_validate({
        **c.request.model_dump(mode='json', by_alias=True), 'confirmToken': prepared.confirm_token})
    return commit_graph_object_authoring_write(request, corpus_root=c.root, authority=c.authority,
        source_admission=c.admission, resolved_source=c.resolved)


def test_managed_source_native_publication_and_exact_retry(case):
    c = case
    original = deepcopy(vars(c.artifact))
    prepared = prepare(c)
    assert prepared.world_id == c.binding.native_world_id
    c.authority.current_head.assert_called_once_with(c.binding.native_world_id)
    transport = c.admission.prove_or_admit.call_args.args[0]
    assert transport.world_id == c.binding.native_world_id
    assert transport.campaign_id is None
    assert transport.source_artifact.world_id == c.binding.native_world_id
    assert transport.source_artifact.campaign_id is None
    assert vars(c.artifact) == original
    assert confirm(c, prepared).published_revision_id == 'rev:d1'
    published = c.authority.published_requests[0]
    assert published.world_id == c.binding.native_world_id
    assert published.contribution.world_id == c.binding.native_world_id
    assert published.contribution.campaign_scope is None
    assert all(item.campaign_scope is None for item in published.contribution.accepted_assertions)
    assert c.admission.prove.call_args.kwargs['world_id'] == c.binding.native_world_id
    assert confirm(c, prepared).idempotency_status == 'already_applied'
    assert c.authority.publish_calls == 1
    assert vars(c.artifact) == original


@pytest.mark.parametrize('field,value', [
    ('native_world_id', 'another-native-world'), ('binding_version', 4),
])
def test_mapping_drift_refuses_before_native_prove_or_recovery(case, field, value):
    prepared = prepare(case)
    setattr(case.binding, field, value)
    with pytest.raises(GraphObjectAuthoringError) as error:
        confirm(case, prepared)
    assert error.value.code == 'world_binding_changed'
    case.admission.prove.assert_not_called()
    assert case.authority.recover_calls == case.authority.publish_calls == 0


@pytest.mark.parametrize('field,value', [('world_id', 'foreign-world'), ('status', 'trashed'), ('kind', 'plan')])
def test_document_ownership_drift_refuses(case, field, value):
    prepared = prepare(case)
    setattr(case.document, field, value)
    with pytest.raises(GraphObjectAuthoringError) as error:
        confirm(case, prepared)
    assert error.value.code == 'world_binding_changed'
    assert case.authority.publish_calls == case.authority.recover_calls == 0


@pytest.mark.parametrize('change', ['missing_world', 'campaign', 'artifact_owner', 'missing_document', 'source_revision'])
def test_unproved_or_foreign_build_source_refuses(case, change):
    if change == 'missing_world':
        case.request.world_id = None
    elif change == 'campaign':
        case.artifact.campaign_id = 'genuine-campaign'
    elif change == 'artifact_owner':
        case.artifact.world_id = 'foreign-world'
    elif change == 'missing_document':
        case.artifact.workspace_document_id = None
    else:
        case.resolved.source_revision_id = 'sha256:' + 'ff' * 32
    with pytest.raises(GraphObjectAuthoringError):
        prepare(case)
    case.admission.prove_or_admit.assert_not_called()
    assert case.authority.publish_calls == 0


def test_missing_binding_fails_closed(case, monkeypatch):
    from apps.live_control_server.services.world_graph_projection import WorldGraphProjectionServiceError
    monkeypatch.setattr('apps.live_control_server.services.managed_world_graph_projection.resolve_managed_world_binding',
        Mock(side_effect=WorldGraphProjectionServiceError('No binding', code='managed_world_unverified', status_code=409)))
    with pytest.raises(GraphObjectAuthoringError) as error:
        prepare(case)
    assert error.value.code == 'world_binding_required'
    case.admission.prove_or_admit.assert_not_called()


def test_exact_source_document_revision_is_sealed(case):
    prepared = prepare(case)
    case.artifact.workspace_document_revision = 3
    with pytest.raises(GraphObjectAuthoringError) as error:
        confirm(case, prepared)
    assert error.value.code == 'world_binding_changed'
    assert case.authority.recover_calls == 0


def test_recap_keeps_explicit_native_world_and_campaign(case):
    case.artifact.source_domain = 'session_recap'
    context = resolve_publication_context(case.request, case.resolved, source_root=case.root)
    assert context.world_id == CAMPAIGN_ID and context.campaign_scope == CAMPAIGN_ID
    assert context.binding is None
    assert context.transport_artifact(case.artifact) is case.artifact


def test_native_prepare_confirm_never_resolves_legacy_campaign_store(case, monkeypatch):
    from apps.live_control_server.services.graph_authoring_overlay_store import GraphAuthoringOverlayStore
    store_access = Mock(side_effect=AssertionError("Legacy campaign overlay accessed"))
    monkeypatch.setattr(GraphAuthoringOverlayStore, "__init__", store_access)
    owner = "unregistered-managed-world"
    case.request.world_id = case.request.campaign_id = owner
    case.resolved.world_id = case.resolved.campaign_id = owner
    case.artifact.world_id = case.artifact.campaign_id = owner
    case.document.world_id = case.binding.managed_world_id = owner
    prepared = prepare(case)
    assert prepared.overlay_path is prepared.event_log_path is prepared.current_overlay_token is None
    assert prepared.overlay_summary.existing_assertion_count == 0
    assert confirm(case, prepared).committed
    assert confirm(case, prepared).idempotency_status == "already_applied"
    store_access.assert_not_called()


def test_overlay_free_native_prepare_still_refuses_stale_parent(case):
    prepared = prepare(case)
    case.authority.revision_id = "rev:someone-else"
    with pytest.raises(GraphObjectAuthoringError) as error:
        confirm(case, prepared)
    assert error.value.code == "stale_parent"
    assert case.authority.publish_calls == 0
