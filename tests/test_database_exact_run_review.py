"""Ordinary exact-run review opens bound APP bytes, never artifact files."""
from pathlib import Path

import psycopg
import pytest
from fastapi.testclient import TestClient

from apps.live_control_server.main import create_app
from apps.live_control_server.services import extract_promote, graph_run_registry
from tests.test_graph_preview_runner import FixtureClient, _run_recap_extraction

pytestmark = pytest.mark.usefixtures("application_state_dsn")


def _review_client(monkeypatch, tmp_path):
    monkeypatch.setenv("DMB_DEPLOYMENT_ENVIRONMENT", "local")
    monkeypatch.setenv("DMB_AUTH_MODE", "local_operator")
    monkeypatch.setattr(extract_promote, "repo_root", lambda: tmp_path)
    return TestClient(create_app(), client=("127.0.0.1", 50000))


def test_ordinary_review_survives_deleted_files_and_denied_file_reads(monkeypatch, tmp_path):
    source, result = _run_recap_extraction(tmp_path, client=FixtureClient())
    run = graph_run_registry.get_extraction_run(tmp_path, result.run.run_id)
    assert run.status.value == "reviewable"
    with _review_client(monkeypatch, tmp_path) as client:
        for path in tmp_path.rglob("*"):
            if path.is_file():
                path.unlink()
        def denied(*args, **kwargs):
            raise AssertionError("exact review must not open files")
        with monkeypatch.context() as guard:
            for name in ("read_bytes", "read_text", "open"):
                guard.setattr(Path, name, denied)
            response = client.get(f"/api/live/extract-promote/runs/{run.run_id}/review-package")
        assert response.status_code == 200, response.text
    review = response.json()
    assert review["sourceProse"] == source.source_text
    assert review["sourceArtifactId"] == source.source_artifact_id
    assert review["worldId"] == "world:elderwyld"
    assert review["inspectionStatus"] == "ready"
    assert review["assertions"]
    assert graph_run_registry.get_extraction_run(tmp_path, run.run_id) == run


@pytest.mark.parametrize("kind", ["candidate_graph", "source_span_index"])
@pytest.mark.parametrize("corrupt", [False, True])
def test_valid_mirrors_cannot_rescue_missing_or_corrupt_database_outputs(
    application_state_dsn, monkeypatch, tmp_path, kind, corrupt
):
    _, result = _run_recap_extraction(tmp_path, client=FixtureClient())
    with psycopg.connect(application_state_dsn) as conn:
        if corrupt:
            conn.execute("UPDATE ingest.component_payload SET payload=%s WHERE run_id=%s AND kind=%s",
                         (b"corrupt", result.run.run_id, kind))
        else:
            conn.execute("DELETE FROM ingest.component_payload WHERE run_id=%s AND kind=%s", (result.run.run_id, kind))
    with _review_client(monkeypatch, tmp_path) as client:
        response = client.get(f"/api/live/extract-promote/runs/{result.run.run_id}/review-package")
    assert response.status_code == (500 if corrupt else 422), response.text
    assert "digest mismatch" in response.text if corrupt else "not durable" in response.text


def test_nonreviewable_run_cannot_be_reviewed(monkeypatch, tmp_path):
    from tests._cutover_d3a_blocker_safe_fixtures import _patch_extraction_run
    from graph_memory.ingestion.extraction_run import ExtractionRunStatus

    _, result = _run_recap_extraction(tmp_path, client=FixtureClient())
    _patch_extraction_run(result.run.run_id, status=ExtractionRunStatus.VALIDATED)
    with _review_client(monkeypatch, tmp_path) as client:
        response = client.get(f"/api/live/extract-promote/runs/{result.run.run_id}/review-package")
    assert response.status_code == 422
    assert "not reviewable" in response.text


def test_run_specific_span_index_is_not_recomputed(monkeypatch, tmp_path):
    from tests._cutover_d3a_blocker_safe_fixtures import _write_reviewable_extraction_run
    from apps.live_control_server.services.source_artifact_registry import load_source_span_index

    run_id, _ = _write_reviewable_extraction_run(tmp_path, pin_noncanonical_span_index=True)
    expected = graph_run_registry.load_reviewable_extraction_data(tmp_path, run_id)
    canonical = load_source_span_index(tmp_path, expected.run.source_artifact_id)
    assert expected.span_index != canonical
    for path in tmp_path.rglob("*"):
        if path.is_file():
            path.unlink()
    with monkeypatch.context() as guard:
        guard.setattr(Path, "open", lambda *_a, **_k: pytest.fail("file read"))
        actual = graph_run_registry.load_reviewable_extraction_data(tmp_path, run_id)
    assert actual.span_bytes == expected.span_bytes
    assert actual.span_index == expected.span_index


@pytest.mark.parametrize("violation", ["campaign", "source_digest", "span_identity"])
def test_wrong_scope_or_source_binding_fails_closed(tmp_path, violation):
    import hashlib
    import json
    from tests._cutover_d3a_blocker_safe_fixtures import (
        _patch_extraction_run, _reseal_extraction_component_digest,
    )

    _, result = _run_recap_extraction(tmp_path, client=FixtureClient())
    run = result.run
    if violation == "campaign":
        _patch_extraction_run(run.run_id, campaign_id="foreign-campaign")
    elif violation == "source_digest":
        _reseal_extraction_component_digest(run.run_id, kind="source_artifact", digest="a" * 64)
    else:
        data = graph_run_registry.load_reviewable_extraction_data(tmp_path, run.run_id)
        index = json.loads(data.span_bytes)
        index["source_artifact_id"] = "source:foreign"
        payload = json.dumps(index).encode()
        _reseal_extraction_component_digest(run.run_id, kind="source_span_index",
            digest=hashlib.sha256(payload).hexdigest(), payload=payload)
    with pytest.raises(graph_run_registry.GraphRunRegistryError) as error:
        graph_run_registry.load_reviewable_extraction_data(tmp_path, run.run_id)
    assert error.value.status_code == 422
    assert any(word in str(error.value) for word in ("campaign_id", "digest", "bound"))
