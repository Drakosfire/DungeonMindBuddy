"""Canonical input spans use the exact body owner, never a registry file."""
import hashlib
from pathlib import Path

import psycopg
import pytest

from apps.live_control_server.services import source_artifact_registry as registry
from graph_memory.source_span import build_source_span_index_for_text

pytestmark = pytest.mark.usefixtures("application_state_dsn")
BODY = "# Recap\n\nTalla’s remedies stayed dry.\n\nThe hinge was inspected.\n"


def registered(root):
    return registry.create_recap_source_artifact(
        root, world_id="span-test-world", campaign_id="span-test-campaign",
        session_id="session-8", recap_text=BODY,
    )


def test_canonical_spans_ignore_missing_or_forged_mirror(tmp_path, monkeypatch):
    artifact = registered(tmp_path)
    expected = build_source_span_index_for_text(
        source_artifact_id=artifact.source_artifact_id,
        content_sha256=hashlib.sha256(BODY.encode()).hexdigest(), text=BODY,
    )
    mirror = registry.source_span_index_path(tmp_path, artifact.source_artifact_id)
    mirror.unlink()
    assert registry.load_source_span_index(tmp_path, artifact.source_artifact_id) == expected
    mirror.write_text('{"source_artifact_id":"foreign","spans":[]}')
    monkeypatch.setattr(Path, "read_bytes", lambda *a, **k: pytest.fail("source index read a file"))
    monkeypatch.setattr(Path, "read_text", lambda *a, **k: pytest.fail("source index read a file"))
    assert registry.load_source_span_index(tmp_path, artifact.source_artifact_id) == expected
    assert registry.get_source_artifact(tmp_path, artifact.source_artifact_id) == artifact


def test_missing_body_cannot_use_valid_mirror(tmp_path, application_state_dsn):
    artifact = registered(tmp_path)
    assert registry.source_span_index_path(tmp_path, artifact.source_artifact_id).is_file()
    with psycopg.connect(application_state_dsn) as conn:
        conn.execute("DELETE FROM source.revision WHERE source_artifact_id=%s", (artifact.source_artifact_id,))
    with pytest.raises(registry.SourceArtifactRegistryError, match="missing from the database"):
        registry.load_source_span_index(tmp_path, artifact.source_artifact_id)


def test_corrupt_body_cannot_use_valid_mirror(tmp_path, application_state_dsn):
    artifact = registered(tmp_path)
    with psycopg.connect(application_state_dsn) as conn:
        conn.execute("UPDATE source.revision SET markdown=%s WHERE source_artifact_id=%s",
            ("# Corrupt\n", artifact.source_artifact_id))
    with pytest.raises(registry.SourceArtifactRegistryError, match="digest mismatch") as exc:
        registry.load_source_span_index(tmp_path, artifact.source_artifact_id)
    assert exc.value.status_code == 409
