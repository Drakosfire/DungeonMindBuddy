from __future__ import annotations

import hashlib
import json
import shutil
from pathlib import Path

import tests.test_live_recap_ingest_graph_preview_api as shared_ingest
from apps.live_control_server.config import SESSION_DIR_ENV
from apps.live_control_server.main import create_app
from apps.live_control_server.services.graph_run_registry import (
    load_reviewable_extraction_data,
    get_reviewable_extraction_run,
)
from apps.live_control_server.services.source_artifact_registry import get_source_artifact
from apps.live_control_server.routes import recap_ingest as recap_ingest_route
from apps.live_control_server.services import recap_ingest_context
from fastapi.testclient import TestClient
import pytest


@pytest.fixture
def process_client_env(
    application_state_dsn: str,
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> tuple[TestClient, Path]:
    """Own all recap/run artifacts under tmp_path and APP-STATE under its disposable DSN."""
    seed_session = shared_ingest.ROOT / "evals/c2_live_prep/live/session_22"
    monkeypatch.setattr(shared_ingest, "ROOT", tmp_path)
    monkeypatch.setattr(recap_ingest_route, "repo_root", lambda: tmp_path)
    monkeypatch.setattr(
        "apps.live_control_server.routes.graph_preview.repo_root", lambda: tmp_path
    )
    monkeypatch.setenv("DMB_ARTIFACT_DATA_ROOT", str(tmp_path))
    graph_root = tmp_path / "out"
    graph_root.mkdir(parents=True, exist_ok=True)
    monkeypatch.setenv("DUNGEONMIND_WORLD_GRAPH_ROOT", str(graph_root))
    monkeypatch.setenv("DUNGEONMIND_GRAPH_INGEST_RUNS_ROOT", "out/graph_memory/runs")
    for name in ("live_packet.json", "surface_layout.json", "current_state.json"):
        shutil.copy2(seed_session / name, tmp_path / name)
    (tmp_path / "event_log.jsonl").write_text("", encoding="utf-8")
    (tmp_path / "job_queue.jsonl").write_text("", encoding="utf-8")
    monkeypatch.setenv(SESSION_DIR_ENV, str(tmp_path))

    class FakeContext:
        def as_lineage(self) -> dict[str, object]:
            return {
                "schema": "dm_world_campaign_ingest_context_v1",
                "managed_world_id": "elderwyld",
                "native_world_id": "world:elderwyld",
                "binding_version": 3,
                "campaign_id": "longmont-c2",
                "head_revision_id": "rev:observed-head",
                "graph_schema": "dm_graph_v1",
                "graph_payload_sha256": "a" * 64,
            }

    monkeypatch.setattr(
        recap_ingest_context,
        "read_recap_ingest_context",
        lambda **_kwargs: FakeContext(),
    )
    corpus = tmp_path / "corpus/eldyrwild-markdown"
    campaign = corpus / "Longmont Campaign/Campaign 2"
    (campaign / "_ingest_staging").mkdir(parents=True)
    (campaign / "Session Recaps").mkdir(parents=True)
    monkeypatch.setenv("DUNGEONMIND_RECAP_INGEST_CORPUS_ROOT", str(corpus))

    from tests.test_recap_managed_standing_context import seed_binding
    monkeypatch.setenv("DMB_MANAGED_WORLD_DATA_ROOT", str(tmp_path))
    seed_binding(tmp_path, "elderwyld", "world:elderwyld", version=3)
    return TestClient(create_app(), client=("127.0.0.1", 50000)), corpus


def test_ordinary_process_candidate_evidence_survives_fresh_exact_run_review_client(
    process_client_env: tuple[TestClient, Path],
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """A fresh exact-run reader recovers the Process source and evidence without rerunning."""
    client, corpus = process_client_env
    shared_ingest._patch_fake_category_extract(monkeypatch)

    raw_text = (
        "Session 29 Recap\n\n"
        "Bonogo scouts the Mireward road and regroups at dusk."
    )
    request = {
        "operation": "generate_recap_memory",
        "campaign_id": "longmont-c2",
        "managed_world_id": "elderwyld",
        "session": 29,
        "raw_text": raw_text,
        "slug": "Process review fixture",
        "title": "Session 29 - Process review fixture",
        "include_graph_extraction": True,
        "graph_model_id": "deepseek/deepseek-v4.1-flash-1017",
    }
    processed = client.post("/api/live/recap-ingest", json=request)
    assert processed.status_code == 200, processed.text
    result = processed.json()
    assert "graph_candidate_ready" in result["states"]
    graph = result["ingest_report"]["graph_preview"]
    assert graph["status"] == "candidate_validation_ready"
    run_id = graph["extraction_run_id"]
    source_artifact_id = graph["source_artifact_id"]
    assert run_id and source_artifact_id

    root = shared_ingest.ROOT
    run = get_reviewable_extraction_run(root, run_id)
    artifact = get_source_artifact(root, source_artifact_id)
    assert run.run_id == run_id
    assert run.source_artifact_id == source_artifact_id
    assert run.source_domain == artifact.source_domain == "recap"
    assert run.campaign_id == artifact.campaign_id == "longmont-c2"
    assert run.session_id == artifact.session_id == "session-29"
    assert artifact.world_id == "world:elderwyld"

    data = load_reviewable_extraction_data(root, run_id)
    candidate = json.loads(data.candidate_bytes)
    span_index = json.loads(data.span_bytes)
    spans = {
        str(row.get("source_span_id") or row.get("source_span_ref_id") or row.get("span_id"))
        for row in span_index.get("spans", [])
        if isinstance(row, dict)
    }
    evidence = [
        ref
        for collection in ("nodes", "edges", "beats")
        for item in candidate.get(collection, [])
        if isinstance(item, dict)
        for ref in item.get("evidence_refs", [])
        if isinstance(ref, dict)
    ]
    assert evidence
    assert candidate["source_artifact_ids"] == [source_artifact_id]
    for ref in evidence:
        assert ref["source_artifact_id"] == source_artifact_id
        assert ref.get("source_span_ref_id") in spans
    assert "manifest_path" not in graph and "candidate_graph_path" not in graph

    normalized = Path(result["paths"]["normalized_recap"])
    if not normalized.is_absolute():
        normalized = corpus / normalized
    normalized_text = normalized.read_text(encoding="utf-8")
    assert artifact.content_sha256 == hashlib.sha256(normalized.read_bytes()).hexdigest()

    shutil.rmtree(root / "out/graph_memory", ignore_errors=True)
    # A new client must reload the same canonical APP-STATE run and durable source.
    client.close()
    fresh = TestClient(create_app(), client=("127.0.0.1", 50000))
    try:
        reloaded_run = fresh.get(f"/api/live/graph-preview/extraction-runs/{run_id}")
        assert reloaded_run.status_code == 200, reloaded_run.text
        run_body = reloaded_run.json()
        assert run_body["run_id"] == run_id
        assert run_body["source_artifact_id"] == source_artifact_id
        assert run_body["campaign_id"] == "longmont-c2"
        assert run_body["session_id"] == "session-29"
        assert run_body["status"] == "reviewable"

        inspection = fresh.get(
            f"/api/live/graph-preview/extraction-runs/{run_id}/recap-inspection"
        )
        assert inspection.status_code == 200, inspection.text
        source = inspection.json()
        assert source["runId"] == run_id
        assert source["sourceArtifactId"] == source_artifact_id
        assert source["sourceStatus"] == "available"
        assert source["campaignId"] == "longmont-c2"
        assert source["sessionId"] == "session-29"
        assert source["sourceSha256"].removeprefix("sha256:") == artifact.content_sha256
        assert source["sourceProse"] == normalized_text

        status = fresh.post(
            "/api/live/recap-ingest",
            json={
                "operation": "inspect_status",
                "campaign_id": "longmont-c2",
                "managed_world_id": "elderwyld",
                "session": 29,
            },
        )
        assert status.status_code == 200, status.text
        preview = status.json()["ingest_report"]["graph_preview"]
        assert preview["extraction_run_id"] == run_id
        assert preview["source_artifact_id"] == source_artifact_id
        assert preview["status"] == "candidate_validation_ready"
    finally:
        fresh.close()
