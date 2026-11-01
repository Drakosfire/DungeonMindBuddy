"""Input metadata is transactional APP storage, never file or Graph admission authority."""
from pathlib import Path
import hashlib
import json

import psycopg
import pytest

from application_state.errors import ApplicationStateConflictError
from application_state.source import service as sources, repository
from apps.live_control_server.services import source_artifact_registry as registry
from graph_memory.evidence.source_artifact import GraphMemorySourceArtifact

pytestmark = pytest.mark.usefixtures("application_state_dsn")


@pytest.fixture
def source(tmp_path, monkeypatch):
    monkeypatch.setenv("DMB_ARTIFACT_DATA_ROOT", str(tmp_path))
    text = "# Exact input\n\nMira found a key.\n"
    artifact = registry.create_recap_source_artifact(
        tmp_path, world_id="input-world", campaign_id="input-campaign",
        session_id="session-1", recap_text=text,
    )
    return tmp_path, artifact, text


def test_metadata_is_exact_and_body_free_with_file_reads_denied(source, monkeypatch):
    root, artifact, _ = source
    monkeypatch.setattr(repository, "get_source_markdown", lambda *a, **k: pytest.fail("metadata opened body"))
    original = Path.open
    def no_data_files(path, *args, **kwargs):
        if path.suffix in {".md", ".json"}:
            pytest.fail("metadata opened file")
        return original(path, *args, **kwargs)
    monkeypatch.setattr(Path, "open", no_data_files)
    assert registry.get_source_artifact(root, artifact.source_artifact_id) == artifact
    assert registry.get_source_artifacts(root, {artifact.source_artifact_id, "unknown"}) == {artifact.source_artifact_id: artifact}


def test_json_cannot_register_or_override_input(source):
    root, artifact, _ = source
    path = root / "out/registries/source_artifacts.json"
    path.parent.mkdir(parents=True, exist_ok=True)
    foreign = artifact.model_copy(update={"source_artifact_id": "old:json:only", "world_id": "foreign"})
    path.write_text(json.dumps({"records": [foreign.model_dump(mode="json")]}))
    assert registry.get_source_artifact(root, artifact.source_artifact_id) == artifact
    with pytest.raises(registry.SourceArtifactRegistryError, match="not registered in database"):
        registry.get_source_artifact(root, foreign.source_artifact_id)


def test_atomic_failure_rolls_back_body_and_descriptor(tmp_path, monkeypatch, application_state_dsn):
    def reject(*args):
        raise ApplicationStateConflictError("injected descriptor write failure")
    monkeypatch.setattr(repository, "set_input_descriptor", reject)
    with pytest.raises(registry.SourceArtifactRegistryError, match="descriptor write failure"):
        registry.create_recap_source_artifact(tmp_path, world_id="input-world", campaign_id="input-campaign", session_id="session-1", recap_text="Input\n")
    with psycopg.connect(application_state_dsn) as conn:
        assert conn.execute("SELECT count(*) FROM source.artifact").fetchone()[0] == 0
        assert conn.execute("SELECT count(*) FROM source.revision").fetchone()[0] == 0


def test_idempotent_registration_keeps_frozen_metadata(source):
    root, artifact, text = source
    moved = artifact.model_copy(update={"uri": "file:///never-opened", "created_at": "later", "updated_at": "later"})
    assert registry._register_source_input(artifact=moved, content=text) == artifact
    assert registry.create_recap_source_artifact(root, world_id="input-world", campaign_id="input-campaign", session_id="session-1", recap_text=text) == artifact


@pytest.mark.parametrize("change", [{"world_id": "other"}, {"campaign_id": "other"}, {"workspace_document_revision": 2}, {"content_sha256": "changed"}])
def test_conflicting_input_never_overwrites_or_leaves_new_body(tmp_path, application_state_dsn, change):
    text = "Original\n"
    artifact = GraphMemorySourceArtifact(source_artifact_id="producer:exact:1", source_domain="worldbuilding", world_id="input-world", campaign_id="campaign",
        uri="historical:locator", content_sha256=hashlib.sha256(text.encode()).hexdigest(), workspace_document_id="doc-1", workspace_document_revision=1)
    registry._register_source_input(artifact=artifact, content=text)
    updates = dict(change)
    new_text = text
    if "content_sha256" in updates:
        new_text = "Different\n"
        updates["content_sha256"] = hashlib.sha256(new_text.encode()).hexdigest()
    with pytest.raises(registry.SourceArtifactRegistryError):
        registry._register_source_input(artifact=artifact.model_copy(update=updates), content=new_text)
    assert registry.get_source_artifact(tmp_path, artifact.source_artifact_id) == artifact
    with psycopg.connect(application_state_dsn) as conn:
        assert conn.execute("SELECT count(*) FROM source.revision WHERE source_artifact_id=%s", (artifact.source_artifact_id,)).fetchone()[0] == 1


def test_unregistered_body_is_not_discovered_as_an_input(application_state_dsn, tmp_path):
    sources.persist_source_markdown(source_artifact_id="body-only", source_domain="worldbuilding", campaign_id=None, session_id=None, world_id="input-world", markdown="Body\n")
    assert registry.get_source_artifacts(tmp_path, {"body-only"}) == {}


def test_malformed_or_retargeted_metadata_fails_closed(source, application_state_dsn):
    root, artifact, _ = source
    with psycopg.connect(application_state_dsn) as conn:
        conn.execute("UPDATE source.artifact SET input_descriptor=jsonb_set(input_descriptor, '{world_id}', '\"foreign\"') WHERE source_artifact_id=%s", (artifact.source_artifact_id,))
    with pytest.raises(registry.SourceArtifactRegistryError, match="invalid registered source input"):
        registry.get_source_artifact(root, artifact.source_artifact_id)


def test_explicit_adoption_uses_existing_body_and_defaults_to_no_write(tmp_path):
    from scripts.adopt_source_input_descriptors import adopt
    text = "Imported source\n"
    artifact = GraphMemorySourceArtifact(source_artifact_id="imported:1", source_domain="worldbuilding", world_id="input-world", uri="file:///must-not-open", content_sha256=hashlib.sha256(text.encode()).hexdigest())
    sources.persist_source_markdown(source_artifact_id=artifact.source_artifact_id, source_domain="worldbuilding", campaign_id=None, session_id=None, world_id=artifact.world_id, markdown=text)
    path = tmp_path / "explicit-export.json"
    path.write_text(json.dumps({"schema_version": "dmb_source_artifact_registry_v1", "records": [artifact.model_dump(mode="json")]}))
    assert adopt(path)[0]["status"] == "verified_no_write"
    assert registry.get_source_artifacts(tmp_path, {artifact.source_artifact_id}) == {}
    assert adopt(path, apply=True)[0]["status"] == "adopted"
    assert registry.get_source_artifact(tmp_path, artifact.source_artifact_id) == artifact


def test_adoption_preview_works_in_read_only_transaction(source, monkeypatch):
    from contextlib import contextmanager
    root, artifact, text = source
    normal = sources.unit_of_work
    @contextmanager
    def read_only(dsn):
        with normal(dsn) as conn:
            conn.execute("SET TRANSACTION READ ONLY")
            yield conn
    monkeypatch.setattr(sources, "unit_of_work", read_only)
    sources.persist_source_markdown(source_artifact_id=artifact.source_artifact_id, source_domain=str(artifact.source_domain),
        campaign_id=artifact.campaign_id, session_id=artifact.session_id, world_id=artifact.world_id,
        markdown=text, input_descriptor=artifact.model_dump(mode="json"), dry_run=True)


def test_malformed_descriptor_digest_is_not_metadata_authority(source, application_state_dsn):
    root, artifact, _ = source
    with psycopg.connect(application_state_dsn) as conn:
        conn.execute("UPDATE source.artifact SET input_descriptor=jsonb_set(input_descriptor, '{content_sha256}', '\"bad\"') WHERE source_artifact_id=%s", (artifact.source_artifact_id,))
    with pytest.raises(registry.SourceArtifactRegistryError, match="invalid registered source input"):
        registry.get_source_artifact(root, artifact.source_artifact_id)


def _source_rows(dsn):
    with psycopg.connect(dsn) as conn:
        return (
            conn.execute('SELECT to_jsonb(a) FROM source.artifact a ORDER BY source_artifact_id').fetchall(),
            conn.execute('SELECT to_jsonb(r) FROM source.revision r ORDER BY source_revision_id').fetchall(),
        )


def _save_scope(artifact, text, world, **extra):
    return sources.persist_source_markdown(
        source_artifact_id=artifact.source_artifact_id, source_domain=artifact.source_domain,
        campaign_id=artifact.campaign_id, session_id=artifact.session_id,
        world_id=world, markdown=text, content_sha256=hashlib.sha256(text.encode()).hexdigest(),
        **extra,
    )


@pytest.fixture
def unassigned(tmp_path, monkeypatch):
    monkeypatch.setenv('DMB_ARTIFACT_DATA_ROOT', str(tmp_path))
    text = '# Exact retained input\r\n\r\nA towér and its key.\r\n\r\n'
    artifact = GraphMemorySourceArtifact(
        source_artifact_id='artifact:recap:membership:session-1:retained', source_domain='recap',
        campaign_id='membership', session_id='session-1', world_id=None,
        uri='historical:inert', artifact_kind='recap_markdown',
        content_sha256=hashlib.sha256(text.encode()).hexdigest(),
        lineage={'original_extraction': 'unchanged'}, created_at='2026-01-01T00:00:00Z',
    )
    first = _save_scope(artifact, text, None, input_descriptor=artifact.model_dump(mode='json'),
                        lineage={'original_body': 'unchanged'})
    return tmp_path, artifact, text, first


@pytest.mark.parametrize('supply_descriptor', [True, False])
def test_null_world_assignment_is_coherent_exact_and_previewable(unassigned, application_state_dsn, supply_descriptor):
    root, artifact, text, first = unassigned
    before = _source_rows(application_state_dsn)
    moved = artifact.model_copy(update={'world_id': 'world-one', 'uri': 'new:ignored',
                                       'created_at': 'later', 'updated_at': 'later'})
    extra = {'input_descriptor': moved.model_dump(mode='json')} if supply_descriptor else {}
    preview = _save_scope(artifact, text, 'world-one', dry_run=True,
                          source_revision_id=first.source_revision_id, **extra)
    assert preview.world_id == 'world-one'
    assert preview.source_revision_id == first.source_revision_id
    assert _source_rows(application_state_dsn) == before
    applied = _save_scope(artifact, text, 'world-one', source_revision_id=first.source_revision_id, **extra)
    assert applied.model_copy(update={'world_id': None}) == first
    assert applied.markdown.encode() == text.encode()
    assert registry.get_source_artifact(root, artifact.source_artifact_id) == artifact.model_copy(update={'world_id': 'world-one'})
    after = _source_rows(application_state_dsn)
    assert after[1] == before[1]
    assert _save_scope(artifact, text, 'world-one', **extra) == applied
    assert _source_rows(application_state_dsn) == after
    # Omitting scope cannot unbind an already assigned artifact.
    assert _save_scope(artifact, text, None).world_id == 'world-one'
    assert _source_rows(application_state_dsn) == after
    with pytest.raises(ApplicationStateConflictError, match='different World'):
        _save_scope(artifact, text, 'foreign-world', **extra)
    assert _source_rows(application_state_dsn) == after


def test_assignment_preserves_absent_descriptor(application_state_dsn):
    artifact = GraphMemorySourceArtifact(source_artifact_id='unregistered:body', source_domain='recap',
        campaign_id='membership', session_id='session-1', uri='inert:body')
    text = 'Exact body\r\n'
    first = _save_scope(artifact, text, None)
    applied = _save_scope(artifact, text, 'world-one')
    assert applied.source_revision_id == first.source_revision_id
    assert applied.world_id == 'world-one'
    assert sources.get_source_input_descriptors(source_artifact_ids=[artifact.source_artifact_id]) == {}


def test_assignment_covers_all_revisions_without_changing_input_revision(unassigned, application_state_dsn):
    root, artifact, text, first = unassigned
    later = _save_scope(artifact, text + 'Second exact revision.\r\n', None, lineage={'later': True})
    assert later.source_revision_id != first.source_revision_id
    before = _source_rows(application_state_dsn)
    preview = _save_scope(artifact, later.markdown, 'world-one', dry_run=True)
    assert preview.world_id == 'world-one' and preview.source_revision_id == later.source_revision_id
    assert _source_rows(application_state_dsn) == before
    _save_scope(artifact, later.markdown, 'world-one')
    assert _source_rows(application_state_dsn)[1] == before[1]
    for record in [first, later]:
        current = sources.get_source_markdown(source_artifact_id=record.source_artifact_id,
            content_sha256=record.content_sha256, source_revision_id=record.source_revision_id)
        assert current.model_copy(update={'world_id': None}) == record
    # The descriptor still identifies its original producer input, not the later body.
    assert registry.get_source_artifact(root, artifact.source_artifact_id) == artifact.model_copy(update={'world_id': 'world-one'})


@pytest.mark.parametrize('change', [
    {'campaign_id': 'foreign'}, {'session_id': 'session-2'}, {'source_domain': 'manual'},
    {'content_sha256': '0' * 64}, {'workspace_document_revision': 2}, {'lineage': {'changed': True}},
])
def test_assignment_descriptor_conflicts_roll_back_and_preview_identically(unassigned, application_state_dsn, change):
    _, artifact, text, first = unassigned
    before = _source_rows(application_state_dsn)
    descriptor = artifact.model_copy(update={'world_id': 'world-one', **change}).model_dump(mode='json')
    failures = []
    for dry_run in [True, False]:
        with pytest.raises(ApplicationStateConflictError) as failure:
            _save_scope(artifact, text, 'world-one', source_revision_id=first.source_revision_id,
                        input_descriptor=descriptor, dry_run=dry_run)
        failures.append(str(failure.value))
        assert _source_rows(application_state_dsn) == before
    assert failures[0] == failures[1]


@pytest.mark.parametrize('existing', [True, False])
def test_conflicting_world_assignment_is_serialized(application_state_dsn, monkeypatch, existing):
    from concurrent.futures import ThreadPoolExecutor
    from threading import Barrier
    artifact = GraphMemorySourceArtifact(source_artifact_id='concurrent:source', source_domain='recap',
        campaign_id='membership', session_id='session-1', uri='inert:concurrent',
        content_sha256=hashlib.sha256(b'Exact concurrent bytes\r\n').hexdigest())
    text = 'Exact concurrent bytes\r\n'
    original = _save_scope(artifact, text, None, input_descriptor=artifact.model_dump(mode='json')) if existing else None
    barrier = Barrier(2)
    read = repository.get_source_artifact
    def concurrent_read(conn, identity, **options):
        if identity != artifact.source_artifact_id or options.get('lock') != 'update':
            return read(conn, identity, **options)
        if existing:
            barrier.wait(timeout=10)
        value = read(conn, identity, **options)
        if not existing:
            assert value is None
            barrier.wait(timeout=10)
        return value
    monkeypatch.setattr(repository, 'get_source_artifact', concurrent_read)
    def assign(world):
        try:
            result = _save_scope(artifact, text, world,
                input_descriptor=artifact.model_copy(update={'world_id': world}).model_dump(mode='json'))
            return ('ok', world, result.source_revision_id)
        except ApplicationStateConflictError:
            return ('conflict', world, None)
    with ThreadPoolExecutor(max_workers=2) as pool:
        outcomes = list(pool.map(assign, ['world-one', 'world-two']))
    assert sorted(row[0] for row in outcomes) == ['conflict', 'ok']
    winner = next(row for row in outcomes if row[0] == 'ok')
    current = sources.get_source_markdown(source_artifact_id=artifact.source_artifact_id,
                                           content_sha256=artifact.content_sha256)
    assert current.world_id == winner[1]
    assert current.source_revision_id == winner[2]
    if original is not None:
        assert current.model_copy(update={'world_id': None}) == original
    descriptor = sources.get_source_input_descriptors(source_artifact_ids=[artifact.source_artifact_id])[artifact.source_artifact_id]
    assert descriptor['world_id'] == winner[1]
    with psycopg.connect(application_state_dsn) as conn:
        assert conn.execute('SELECT count(*) FROM source.artifact').fetchone() == (1,)
        assert conn.execute('SELECT count(*) FROM source.revision').fetchone() == (1,)
