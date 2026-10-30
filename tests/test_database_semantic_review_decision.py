"""The mounted semantic decision uses exact stored evidence, never file copies."""
from pathlib import Path

import psycopg
import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from apps.live_control_server.routes import extract_promote as routes
from apps.live_control_server.services import exact_run_evidence_correction as correction
from apps.live_control_server.services import graph_run_registry as registry
from apps.live_control_server.services.agent_graph_auth import NativeGraphPrincipal, native_graph_gm_dependency
from apps.live_control_server.services.recap_semantic_disposition import assess_recap_semantics
from tests.test_database_literal_correction_parent import _false_quote_parent

pytestmark = pytest.mark.usefixtures("application_state_dsn")


def _held_child(monkeypatch, root):
    parent, request = _false_quote_parent(monkeypatch, root)
    response = correction.correct_recap_run_evidence(request)
    child = registry.get_extraction_run(root, response.run_id)
    return parent, child, dict(expectedRevision=child.revision,
        candidateSha256=response.candidate_sha256, decision="accepted", reviewDecisionRef="review:synthetic-acceptance")


def _client():
    app = FastAPI()
    app.include_router(routes.router)
    # Explicit trusted GM fixture. The separate auth suite exercises the actual
    # HTTP authentication/CSRF and rejects forged reviewer fields.
    app.dependency_overrides[native_graph_gm_dependency] = lambda: NativeGraphPrincipal(
        subject="synthetic_operator", role="gm", auth_method="local_operator")
    return TestClient(app)


def test_mounted_acceptance_with_all_evidence_files_removed(monkeypatch, tmp_path):
    parent, child, body = _held_child(monkeypatch, tmp_path)
    before = registry.load_reviewable_extraction_data(tmp_path, child.run_id)
    with _client() as client:
        for path in tmp_path.rglob("*"):
            if path.is_file():
                path.unlink()
        with monkeypatch.context() as guard:
            guard.setattr(Path, "open", lambda *_a, **_k: pytest.fail("semantic acceptance opened a file"))
            response = client.post(f"/api/live/extract-promote/runs/{child.run_id}/semantic-disposition", json=body)
            replay = client.post(f"/api/live/extract-promote/runs/{child.run_id}/semantic-disposition", json=body)
            assert replay.status_code == 200 and replay.json() == response.json()
    assert response.status_code == 200, response.text
    result = response.json()
    assert result["state"] == "accepted" and result["reviewerId"] == "synthetic_operator"
    after = registry.load_reviewable_extraction_data(tmp_path, child.run_id)
    assert after.run.revision == child.revision + 1
    assert after.candidate_bytes == before.candidate_bytes
    assert after.source_bytes == before.source_bytes and after.span_bytes == before.span_bytes
    assert after.run.components == child.components
    assert assess_recap_semantics(after.run, parent=parent,
        source_revision_id=after.source_artifact.content_sha256).accepted
    assert registry.get_extraction_run(tmp_path, parent.run_id) == parent


@pytest.mark.parametrize("kind", ["source_artifact", "candidate_graph", "source_span_index"])
@pytest.mark.parametrize("violation", ["missing", "corrupt"])
def test_bad_stored_evidence_cannot_use_valid_mirrors(monkeypatch, tmp_path, application_state_dsn, kind, violation):
    _, child, body = _held_child(monkeypatch, tmp_path)
    with psycopg.connect(application_state_dsn) as conn:
        if kind == "source_artifact":
            if violation == "missing":
                conn.execute("DELETE FROM source.revision WHERE source_artifact_id=%s", (child.source_artifact_id,))
            else:
                conn.execute("UPDATE source.revision SET markdown='corrupt' WHERE source_artifact_id=%s", (child.source_artifact_id,))
        elif violation == "missing":
            conn.execute("DELETE FROM ingest.component_payload WHERE run_id=%s AND kind=%s", (child.run_id, kind))
        else:
            conn.execute("UPDATE ingest.component_payload SET payload=%s WHERE run_id=%s AND kind=%s", (b"corrupt", child.run_id, kind))
    with _client() as client:
        response = client.post(f"/api/live/extract-promote/runs/{child.run_id}/semantic-disposition", json=body)
    assert response.status_code == (500 if violation == "corrupt" and kind != "source_artifact" else 409), response.text
    assert registry.get_extraction_run(tmp_path, child.run_id) == child


@pytest.mark.parametrize("drift", ["revision", "candidate_digest"])
def test_stale_review_cannot_record_decision(monkeypatch, tmp_path, drift):
    _, child, body = _held_child(monkeypatch, tmp_path)
    if drift == "revision":
        body["expectedRevision"] -= 1
    else:
        body["candidateSha256"] = "f" * 64
    with _client() as client:
        response = client.post(f"/api/live/extract-promote/runs/{child.run_id}/semantic-disposition", json=body)
    assert response.status_code == 409, response.text
    assert registry.get_extraction_run(tmp_path, child.run_id) == child
