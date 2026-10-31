"""Canonical input spans use the exact body owner, never a registry file."""
import hashlib
import json
from pathlib import Path

import psycopg
import pytest

from apps.live_control_server.services import source_artifact_registry as registry
from graph_memory.source_span import build_source_span_index_for_text, source_span_index_to_dict

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
    assert not mirror.exists()
    assert registry.load_source_span_index(tmp_path, artifact.source_artifact_id) == expected
    mirror.parent.mkdir(parents=True)
    mirror.write_text('{"source_artifact_id":"foreign","spans":[]}')
    monkeypatch.setattr(Path, "read_bytes", lambda *a, **k: pytest.fail("source index read a file"))
    monkeypatch.setattr(Path, "read_text", lambda *a, **k: pytest.fail("source index read a file"))
    assert registry.load_source_span_index(tmp_path, artifact.source_artifact_id) == expected
    assert registry.get_source_artifact(tmp_path, artifact.source_artifact_id) == artifact


def _write_valid_old_mirror(root, artifact):
    mirror = registry.source_span_index_path(root, artifact.source_artifact_id)
    index = registry.load_source_span_index(root, artifact.source_artifact_id)
    mirror.parent.mkdir(parents=True)
    mirror.write_text(json.dumps(source_span_index_to_dict(index)))


def test_missing_body_cannot_use_valid_mirror(tmp_path, application_state_dsn):
    artifact = registered(tmp_path)
    _write_valid_old_mirror(tmp_path, artifact)
    with psycopg.connect(application_state_dsn) as conn:
        conn.execute("DELETE FROM source.revision WHERE source_artifact_id=%s", (artifact.source_artifact_id,))
    with pytest.raises(registry.SourceArtifactRegistryError, match="missing from the database"):
        registry.load_source_span_index(tmp_path, artifact.source_artifact_id)


def test_corrupt_body_cannot_use_valid_mirror(tmp_path, application_state_dsn):
    artifact = registered(tmp_path)
    _write_valid_old_mirror(tmp_path, artifact)
    with psycopg.connect(application_state_dsn) as conn:
        conn.execute("UPDATE source.revision SET markdown=%s WHERE source_artifact_id=%s",
            ("# Corrupt\n", artifact.source_artifact_id))
    with pytest.raises(registry.SourceArtifactRegistryError, match="digest mismatch") as exc:
        registry.load_source_span_index(tmp_path, artifact.source_artifact_id)
    assert exc.value.status_code == 409


@pytest.mark.parametrize("domain", ["recap", "worldbuilding"])
def test_registration_needs_no_span_index_directory(tmp_path, monkeypatch, domain):
    original_mkdir = Path.mkdir

    def refuse_span_directory(path, *args, **kwargs):
        if "source_span_indexes" in path.parts:
            raise OSError("synthetic span mirror unavailable")
        return original_mkdir(path, *args, **kwargs)

    monkeypatch.setattr(Path, "mkdir", refuse_span_directory)
    if domain == "recap":
        artifact = registered(tmp_path)
        expected = BODY.encode()
    else:
        from tests.test_graph_preview_runner import _admit_worldbuilding
        source = _admit_worldbuilding(tmp_path, BODY)
        artifact = registry.get_source_artifact(tmp_path, source.source_artifact_id)
        expected = source.source_text.encode()

    assert registry.load_registered_source_artifact_bytes(tmp_path, artifact.source_artifact_id) == (
        artifact, expected,
    )
    index = registry.load_source_span_index(tmp_path, artifact.source_artifact_id)
    assert index == build_source_span_index_for_text(
        source_artifact_id=artifact.source_artifact_id,
        content_sha256=hashlib.sha256(expected).hexdigest(), text=expected.decode(),
    )
    assert not (tmp_path / registry.DEFAULT_SOURCE_SPAN_INDEX_DIR_REL).exists()
