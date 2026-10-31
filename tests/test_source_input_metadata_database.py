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
