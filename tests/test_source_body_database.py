"""Canonical source bodies come from the existing database, never a file mirror."""
from __future__ import annotations

import hashlib

import psycopg
import pytest

from application_state.source import service as sources
from apps.live_control_server.services import source_artifact_registry as registry
from graph_memory.evidence.source_artifact import GraphMemorySourceArtifact


@pytest.fixture
def registered_source(tmp_path, monkeypatch, application_state_dsn):
    monkeypatch.setenv("DMB_ARTIFACT_DATA_ROOT", str(tmp_path))
    raw = "# Source\n\nMira’s journal.\n".encode()
    artifact = GraphMemorySourceArtifact(
        source_artifact_id="artifact:recap:retained-database-body-fixture",
        source_domain="recap", world_id="source-world", campaign_id="source-campaign",
        session_id="session-1", uri="repo://retained-source.md",
        content_sha256=hashlib.sha256(raw).hexdigest(),
    )
    artifact = registry._register_source_input(artifact=artifact, content=raw.decode())
    # Explicit historical file, not a side effect of current registration.
    (tmp_path / "retained-source.md").write_bytes(raw)
    return tmp_path, artifact, raw, application_state_dsn


def persist(artifact, raw):
    return sources.persist_source_markdown(
        source_artifact_id=artifact.source_artifact_id,
        content_sha256=artifact.content_sha256,
        source_domain=str(artifact.source_domain), world_id=artifact.world_id,
        campaign_id=artifact.campaign_id, session_id=artifact.session_id,
        markdown=raw.decode("utf-8"),
    )


def test_source_body_survives_removed_file(registered_source, monkeypatch):
    root, artifact, raw, _ = registered_source
    saved = persist(artifact, raw)
    (root / artifact.uri.removeprefix("repo://")).unlink()
    monkeypatch.setattr(registry, "_read_exact_repo_uri_bytes", lambda *a: pytest.fail("file body read"))
    actual, content = registry.load_registered_source_artifact_bytes(root, artifact.source_artifact_id)
    assert actual == artifact
    assert content == raw == saved.markdown.encode("utf-8")
    assert hashlib.sha256(content).hexdigest() == artifact.content_sha256


def test_missing_database_body_does_not_fall_back_to_valid_file(registered_source):
    root, artifact, raw, dsn = registered_source
    with psycopg.connect(dsn) as conn:
        conn.execute("DELETE FROM source.revision WHERE source_artifact_id=%s", (artifact.source_artifact_id,))
    assert (root / artifact.uri.removeprefix("repo://")).read_bytes() == raw
    with pytest.raises(registry.SourceArtifactRegistryError, match="database"):
        registry.load_registered_source_artifact_bytes(root, artifact.source_artifact_id)


def test_corrupt_database_body_does_not_fall_back_to_valid_file(registered_source):
    root, artifact, raw, dsn = registered_source
    saved = persist(artifact, raw)
    with psycopg.connect(dsn) as conn:
        conn.execute("UPDATE source.revision SET markdown=%s WHERE source_revision_id=%s", ("wrong body", saved.source_revision_id))
    with pytest.raises(registry.SourceArtifactRegistryError, match="digest"):
        registry.load_registered_source_artifact_bytes(root, artifact.source_artifact_id)


@pytest.mark.parametrize("field", ["world_id", "campaign_id", "session_id", "source_domain"])
def test_descriptor_cannot_retarget_database_body(registered_source, monkeypatch, field):
    root, artifact, raw, _ = registered_source
    persist(artifact, raw)
    changed = artifact.model_copy(update={field: "foreign"})
    monkeypatch.setattr(registry, "get_source_artifact", lambda *a: changed)
    with pytest.raises(registry.SourceArtifactRegistryError, match="scope"):
        registry.load_registered_source_artifact_bytes(root, artifact.source_artifact_id)


def test_database_body_read_does_not_interpret_file_locator(registered_source, monkeypatch):
    root, artifact, raw, _ = registered_source
    persist(artifact, raw)
    changed = artifact.model_copy(update={"uri": "file:///unrelated/private/file"})
    monkeypatch.setattr(registry, "get_source_artifact", lambda *a: changed)
    assert registry.load_registered_source_artifact_bytes(root, artifact.source_artifact_id)[1] == raw


def test_registration_persists_body_before_run_or_provider_call(registered_source):
    root, artifact, raw, _ = registered_source
    stored = sources.get_source_markdown(
        source_artifact_id=artifact.source_artifact_id,
        content_sha256=artifact.content_sha256,
    )
    assert stored is not None
    assert stored.markdown.encode("utf-8") == raw
    (root / artifact.uri.removeprefix("repo://")).unlink()
    assert registry.load_registered_source_artifact_text(root, artifact.source_artifact_id) == (artifact, raw.decode("utf-8"))


def test_database_persistence_failure_does_not_register_source(tmp_path, monkeypatch, application_state_dsn):
    from application_state.errors import ApplicationStateConflictError
    monkeypatch.setenv("DMB_ARTIFACT_DATA_ROOT", str(tmp_path))

    def reject(**kwargs):
        raise ApplicationStateConflictError("source conflict")

    monkeypatch.setattr(sources, "persist_source_markdown", reject)
    with pytest.raises(registry.SourceArtifactRegistryError, match="source body persistence"):
        registry.create_recap_source_artifact(
            tmp_path, world_id="source-world", campaign_id="source-campaign",
            session_id="session-1", recap_text="Source\n",
        )
    assert sources.get_source_input_descriptors(source_artifact_ids=["missing"]) == {}
    assert not (tmp_path / "out/registries/source_artifacts.json").exists()


def test_text_reader_preserves_exact_database_crlf(registered_source, monkeypatch):
    root, artifact, _, _ = registered_source
    raw = b"First\r\n\r\nSecond\r\n"
    digest = hashlib.sha256(raw).hexdigest()
    exact = artifact.model_copy(update={"content_sha256": digest})
    sources.persist_source_markdown(
        source_artifact_id=artifact.source_artifact_id, source_domain=str(artifact.source_domain),
        world_id=artifact.world_id, campaign_id=artifact.campaign_id,
        session_id=artifact.session_id, markdown=raw.decode(), content_sha256=digest,
    )
    monkeypatch.setattr(registry, "get_source_artifact", lambda *args: exact)
    assert registry.load_registered_source_artifact_text(root, artifact.source_artifact_id)[1].encode() == raw
