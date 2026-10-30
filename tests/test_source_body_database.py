"""Canonical source bodies come from the existing database, never a file mirror."""
from __future__ import annotations

import hashlib

import psycopg
import pytest

from application_state.source import service as sources
from apps.live_control_server.services import source_artifact_registry as registry


@pytest.fixture
def registered_source(tmp_path, monkeypatch, application_state_dsn):
    monkeypatch.setenv("DMB_ARTIFACT_DATA_ROOT", str(tmp_path))
    artifact = registry.create_recap_source_artifact(
        tmp_path, world_id="source-world", campaign_id="source-campaign",
        session_id="session-1", recap_text="# Source\n\nMira’s journal.\n",
    )
    raw = (tmp_path / artifact.uri.removeprefix("repo://")).read_bytes()
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
    root, artifact, raw, _ = registered_source
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
