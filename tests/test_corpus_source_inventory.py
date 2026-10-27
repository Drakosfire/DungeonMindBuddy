"""Actual native source repositories with no Graph repository or evidence."""
from datetime import datetime, timezone
from hashlib import sha256
from types import SimpleNamespace
import pytest
from dungeonmind.contracts.evidence import SourceArtifactV2, SourceRevision, SourceStatus
from dungeonmind.infrastructure.memory import InMemorySourceRepository
from apps.live_control_server.integrations.dungeonmind.corpus_source_inventory import collect_source_view, verify_registry_source_origin

TEXT = '# Unconnected workshop\r\n## Accounts\r\nA sleeping fox lies beneath the black arch.\r\n## Appendix\r\nUnrelated blue flowers.\r\n'


def registry(*, world='native-park', text=TEXT, current='orphan:r1'):
    repo = InMemorySourceRepository()
    now = datetime(2026, 10, 27, tzinfo=timezone.utc)
    artifact = SourceArtifactV2(source_artifact_id='artifact:orphan', source_domain_key='worldbuilding',
        source_domain='worldbuilding', world_id=world, campaign_id=None, session_id=None,
        uri=None, current_revision_id=current, authority=None, visibility='gm', artifact_kind=None,
        document_class=None, review_state=None, source_visibility_state=None, workspace_document_ref=None,
        lineage={'source_name': 'Unconnected workshop'}, status='active', created_at=now, updated_at=now)
    revision = SourceRevision(source_artifact_id=artifact.source_artifact_id, source_revision_id='orphan:r1',
        content_sha256=sha256(text.encode()).hexdigest(), body_storage='postgres', created_at=now)
    repo.put_artifact(artifact); repo.put_revision(revision)
    return SimpleNamespace(binding=SimpleNamespace(world_id=world), bundle=SimpleNamespace(sources=repo)), artifact, revision


def test_actual_registry_snapshot_needs_no_graph_and_never_guesses_current():
    services, artifact, revision = registry(current=None)
    data = collect_source_view(services, native_world_id='native-park')
    assert data['members'] == [{'artifact': artifact.model_dump(mode='json'), 'revision': revision.model_dump(mode='json')}]
    assert data['members'][0]['artifact']['current_revision_id'] is None
    assert not data['gaps'] and 'text' not in data and 'markdown' not in data
    assert not hasattr(services, 'retrieval')  # an accidental Graph dependency fails


@pytest.mark.parametrize('change', ['foreign', 'inactive', 'visibility', 'drift', 'missing', 'revision_ownership'])
def test_inventory_refuses_bad_metadata_and_preserves_drift(monkeypatch, change):
    services, artifact, _ = registry()
    repo = services.bundle.sources
    if change == 'foreign':
        monkeypatch.setattr(repo, 'list_artifacts_for_world', lambda _: [artifact.model_copy(update={'world_id':'foreign'})])
        with pytest.raises(ValueError, match='foreign'):collect_source_view(services, native_world_id='native-park')
        return
    if change in {'inactive', 'visibility'}:
        repo._artifacts[artifact.source_artifact_id] = artifact.model_copy(update={
            'status':SourceStatus.RETRACTED} if change == 'inactive' else {'visibility':None})
    else:
        original = repo.get_provenance_snapshot
        def snapshot(**kwargs):
            if change == 'missing':repo._artifacts.clear()
            elif change == 'revision_ownership':
                record=repo.get_revision('orphan:r1')
                repo._revisions['orphan:r1']=record.model_copy(update={'source_artifact_id':'foreign'})
            else:repo._artifacts[artifact.source_artifact_id] = artifact.model_copy(update={'lineage':{'source_name':'Changed'}})
            return original(**kwargs)
        monkeypatch.setattr(repo, 'get_provenance_snapshot', snapshot)
    data = collect_source_view(services, native_world_id='native-park')
    assert not data['members'] and data['gaps']


@pytest.mark.parametrize('change', ['world', 'visibility', 'status', 'revision', 'digest'])
def test_registry_reopen_checks_exact_metadata_not_latest(change):
    services, artifact, revision = registry()
    proof = {'schema':'dmb_registry_source_origin_v1', 'search_event_id':'unused', 'source_view_sha256':'a'*64,
        'artifact':artifact.model_dump(mode='json'), 'revision':revision.model_dump(mode='json')}
    origin = verify_registry_source_origin(services, native_world_id='native-park', proof=proof)
    assert origin.donor_event_id is None and origin.native_source_revision_id == 'orphan:r1'
    repo = services.bundle.sources
    if change in {'revision', 'digest'}:
        repo._revisions[revision.source_revision_id] = revision.model_copy(update={
            'source_revision_id':'other'} if change == 'revision' else {'content_sha256':'b'*64})
    else:
        value = {'world':{'world_id':'foreign'}, 'visibility':{'visibility':None},
                 'status':{'status':SourceStatus.RETRACTED}, 'current':{'current_revision_id':'new'}}[change]
        repo._artifacts[artifact.source_artifact_id] = artifact.model_copy(update=value)
    with pytest.raises(ValueError):verify_registry_source_origin(services, native_world_id='native-park', proof=proof)


def test_historical_source_keeps_exact_bytes_when_current_pointer_advances():
    services, artifact, revision = registry()
    proof = {'schema':'dmb_registry_source_origin_v1', 'search_event_id':'unused', 'source_view_sha256':'a'*64,
        'artifact':artifact.model_dump(mode='json'), 'revision':revision.model_dump(mode='json')}
    repo = services.bundle.sources
    repo.put_revision(revision.model_copy(update={'source_revision_id':'orphan:r2', 'content_sha256':'b'*64}))
    repo._artifacts[artifact.source_artifact_id] = artifact.model_copy(update={'current_revision_id':'orphan:r2'})
    origin = verify_registry_source_origin(services, native_world_id='native-park', proof=proof)
    assert origin.native_source_revision_id == 'orphan:r1' and origin.content_sha256 == revision.content_sha256
