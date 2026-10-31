"""Correction preflight reads the exact APP parent snapshot, never locators."""
from dataclasses import replace
from hashlib import sha256
import json
from pathlib import Path

import psycopg
import pytest

from apps.live_control_server.services import graph_run_registry as registry
from apps.live_control_server.services import promotable_ingest_run as resolution
from apps.live_control_server.services import recap_semantic_candidate_correction as correction
from tests.test_graph_preview_runner import FixtureClient, _run_recap_extraction

pytestmark = pytest.mark.usefixtures("application_state_dsn")


def _case(root, *, custom_span=False):
    _, result = _run_recap_extraction(root, client=FixtureClient())
    data = registry.load_reviewable_extraction_data(root, result.run.run_id)
    if custom_span:
        from graph_memory.source_span import build_stable_source_span_id
        from tests._cutover_d3a_blocker_safe_fixtures import _reseal_extraction_component_digest
        index = json.loads(data.span_bytes)
        span = index["spans"][0].copy()
        span["start_line"], span["end_line"] = 1, len(data.source_bytes.decode().splitlines())
        span["source_span_id"] = build_stable_source_span_id(
            source_artifact_id=data.run.source_artifact_id,
            content_sha256=data.source_artifact.content_sha256,
            start_line=span["start_line"], end_line=span["end_line"],
        )
        assert span["source_span_id"] not in {row["source_span_id"] for row in index["spans"]}
        index["spans"] = [span]
        payload = json.dumps(index, sort_keys=True).encode()
        _reseal_extraction_component_digest(data.run.run_id, kind="source_span_index",
            digest=sha256(payload).hexdigest(), payload=payload)
        data = registry.load_reviewable_extraction_data(root, data.run.run_id)
    return data, resolution.resolve_promotable_ingest_run(data.run.run_id, root=root)


@pytest.mark.parametrize("custom_span", [False, True])
def test_preflight_survives_deleted_files_and_preserves_exact_run_spans(monkeypatch, tmp_path, custom_span):
    data, resolved = _case(tmp_path, custom_span=custom_span)
    for path in tmp_path.rglob("*"):
        if path.is_file():
            path.unlink()
    # Resolver removal is a separate slice; exercise its already-resolved DTO.
    with monkeypatch.context() as guard:
        guard.setattr(Path, "open", lambda *_a, **_k: pytest.fail("preflight opened a file mirror"))
        artifact, candidate, source, spans, index, scope = correction._preflight_source_snapshot(
            data.run, resolved, tmp_path)
    assert (artifact, candidate, source, spans, index) == (
        data.source_artifact, data.candidate_bytes, data.source_bytes, data.span_bytes, data.span_index)
    assert scope == correction._frozen_recap_world_lineage(data.run)


@pytest.mark.parametrize("kind", ["source_artifact", "candidate_graph", "source_span_index"])
@pytest.mark.parametrize("violation", ["missing", "corrupt"])
def test_valid_files_cannot_rescue_missing_or_corrupt_database_snapshot(tmp_path, application_state_dsn, kind, violation):
    data, resolved = _case(tmp_path)
    with psycopg.connect(application_state_dsn) as conn:
        if kind == "source_artifact":
            if violation == "missing":
                conn.execute("DELETE FROM source.revision WHERE source_artifact_id=%s", (data.run.source_artifact_id,))
            else:
                conn.execute("UPDATE source.revision SET markdown='corrupt' WHERE source_artifact_id=%s", (data.run.source_artifact_id,))
        elif violation == "missing":
            conn.execute("DELETE FROM ingest.component_payload WHERE run_id=%s AND kind=%s", (data.run.run_id, kind))
        else:
            conn.execute("UPDATE ingest.component_payload SET payload=%s WHERE run_id=%s AND kind=%s",
                         (b"corrupt", data.run.run_id, kind))
    with pytest.raises(correction.ExtractPromoteError):
        correction._preflight_source_snapshot(data.run, resolved, tmp_path)
    assert registry.get_extraction_run(tmp_path, data.run.run_id) == data.run


@pytest.mark.parametrize("field,value", [("run_id", "foreign-run"), ("source_artifact_id", "foreign-source"),
    ("world_id", "foreign-world"), ("campaign_id", "foreign-campaign"), ("session_id", "foreign-session"),
    ("source_domain", "worldbuilding"), ("source_revision_id", "f" * 64)])
def test_resolved_identity_drift_stays_closed(tmp_path, field, value):
    data, resolved = _case(tmp_path)
    with pytest.raises(correction.ExtractPromoteError):
        correction._preflight_source_snapshot(data.run, replace(resolved, **{field: value}), tmp_path)


def test_changed_parent_metadata_is_not_used_as_a_current_snapshot(tmp_path):
    data, resolved = _case(tmp_path)
    with pytest.raises(correction.ExtractPromoteError, match="snapshot changed"):
        correction._preflight_source_snapshot(
            data.run.model_copy(update={"revision": data.run.revision + 1}), resolved, tmp_path)
