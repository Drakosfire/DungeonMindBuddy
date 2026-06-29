from __future__ import annotations

import shutil
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from apps.live_control_server.config import SESSION_DIR_ENV
from apps.live_control_server.main import create_app

ROOT = Path(__file__).resolve().parents[1]
SEED_SESSION = ROOT / "evals/c2_live_prep/live/session_22"
CORPUS_ENV = "DUNGEONMIND_RECAP_INGEST_CORPUS_ROOT"
FIXTURE_DIR = ROOT / "tests/fixtures/graph_memory/category_preview_runner"
CANDIDATE_FIXTURE = FIXTURE_DIR / "candidate_graph_fixture.json"


@pytest.fixture
def client_env(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> tuple[TestClient, Path, Path]:
    for name in ("live_packet.json", "surface_layout.json", "current_state.json"):
        shutil.copy2(SEED_SESSION / name, tmp_path / name)
    (tmp_path / "event_log.jsonl").write_text("", encoding="utf-8")
    (tmp_path / "job_queue.jsonl").write_text("", encoding="utf-8")
    monkeypatch.setenv(SESSION_DIR_ENV, str(tmp_path))

    corpus = tmp_path / "external-corpus"
    graph_runs = ROOT / "out/graph_memory/runs/longmont-c2/session-22"
    shutil.rmtree(graph_runs, ignore_errors=True)
    campaign = corpus / "Longmont Campaign/Campaign 2"
    (campaign / "_ingest_staging").mkdir(parents=True, exist_ok=True)
    (campaign / "Session Recaps").mkdir(parents=True, exist_ok=True)
    monkeypatch.setenv(CORPUS_ENV, str(corpus))
    monkeypatch.setenv("DUNGEONMIND_GRAPH_INGEST_RUNS_ROOT", "out/graph_memory/runs")

    candidate = ROOT / "out/test_recap_ingest_graph_preview/candidate_graph_fixture.json"
    candidate.parent.mkdir(parents=True, exist_ok=True)
    candidate.write_text(CANDIDATE_FIXTURE.read_text(encoding="utf-8"), encoding="utf-8")
    try:
        yield TestClient(create_app()), corpus, candidate
    finally:
        shutil.rmtree(graph_runs, ignore_errors=True)


def _prepare_normalized(client: TestClient) -> None:
    raw = "Session 22 Recap\n\nThe group scouts the Mireward road and regroups at dusk."
    stage = client.post(
        "/api/live/recap-ingest",
        json={
            "operation": "stage_preview",
            "campaign_id": "longmont-c2",
            "session": 22,
            "raw_text": raw,
            "slug": "Mireward Road Dogfood",
        },
    )
    assert stage.status_code == 200
    apply = client.post(
        "/api/live/recap-ingest",
        json={
            "operation": "apply_normalize",
            "campaign_id": "longmont-c2",
            "session": 22,
            "slug": "Mireward Road Dogfood",
        },
    )
    assert apply.status_code == 200


def test_recap_ingest_build_graph_preview_bundle_from_normalized_recap(client_env: tuple[TestClient, Path, Path]) -> None:
    client, _corpus, _candidate = client_env
    _prepare_normalized(client)

    response = client.post(
        "/api/live/recap-ingest",
        json={"operation": "build_graph_preview_bundle", "campaign_id": "longmont-c2", "session": 22},
    )

    assert response.status_code == 200
    body = response.json()
    graph = body["ingest_report"]["graph_preview"]
    assert graph["status"] == "source_span_bundle_ready"
    assert (ROOT / graph["manifest_path"]).is_file()
    assert "graph_source_bundle_ready" in body["states"]
    assert "Candidate graph extraction has not run yet" in graph["blocked_reason"]


def test_recap_ingest_materialize_preview_supergraph_blocks_without_candidate_graph(client_env: tuple[TestClient, Path, Path]) -> None:
    client, _corpus, _candidate = client_env
    _prepare_normalized(client)
    client.post(
        "/api/live/recap-ingest",
        json={"operation": "build_graph_preview_bundle", "campaign_id": "longmont-c2", "session": 22},
    )

    response = client.post(
        "/api/live/recap-ingest",
        json={"operation": "materialize_preview_supergraph", "campaign_id": "longmont-c2", "session": 22},
    )

    assert response.status_code == 200
    graph = response.json()["ingest_report"]["graph_preview"]
    assert "Candidate graph extraction has not run yet" in graph["blocked_reason"]
    assert graph["preview_union_store_path"] is None


def test_recap_ingest_materialize_preview_supergraph_with_candidate_graph_path(client_env: tuple[TestClient, Path, Path]) -> None:
    client, _corpus, candidate = client_env
    _prepare_normalized(client)

    response = client.post(
        "/api/live/recap-ingest",
        json={
            "operation": "materialize_preview_supergraph",
            "campaign_id": "longmont-c2",
            "session": 22,
            "candidate_graph_path": candidate.relative_to(ROOT).as_posix(),
        },
    )

    assert response.status_code == 200
    body = response.json()
    graph = body["ingest_report"]["graph_preview"]
    assert graph["status"] == "preview_union_store_ready"
    assert graph["can_open_union_graph"] is True
    assert (ROOT / graph["preview_union_store_path"]).is_file()
    assert "preview_union_store_ready" in body["states"]


def test_recap_ingest_rejects_unsafe_candidate_graph_path(client_env: tuple[TestClient, Path, Path]) -> None:
    client, _corpus, _candidate = client_env
    _prepare_normalized(client)

    response = client.post(
        "/api/live/recap-ingest",
        json={
            "operation": "build_graph_preview_bundle",
            "campaign_id": "longmont-c2",
            "session": 22,
            "candidate_graph_path": "../escape.json",
        },
    )

    assert response.status_code == 422


def _live_extraction_payload() -> dict:
    return {
        "candidate_nodes": [
            {"id": "node:mireward-road", "kind": "location", "label": "Mireward Road", "evidence_refs": ["ev:1"]}
        ],
        "candidate_edges": [],
        "session_beats": [
            {"id": "beat:1", "summary": "The group scouts the Mireward road.", "evidence_refs": ["ev:1"]}
        ],
        "ignored_or_deferred_candidates": [],
        "diagnostics": {
            "preview_only": True,
            "canon_promotion": False,
            "approved_memory_write": False,
            "corpus_mutation": False,
            "production_retrieval": False,
        },
        "source_artifacts": [],
        "evidence_refs": [{"id": "ev:1", "span_id": "session-22:recap:full_text"}],
    }


def test_recap_ingest_build_graph_preview_bundle_with_extract_graph_fake_client(
    client_env: tuple[TestClient, Path, Path], monkeypatch: pytest.MonkeyPatch
) -> None:
    import evals.graph_memory_layer.graph_preview_runner as runner
    from src.graph_memory.extraction.preview_candidate_graph_extractor import PreviewCandidateGraphExtractionResult

    client, _corpus, _candidate = client_env
    _prepare_normalized(client)

    def fake_extract(options, *, client=None):  # noqa: ANN001
        return PreviewCandidateGraphExtractionResult(
            candidate_graph=_live_extraction_payload(),
            raw_model_response="{}",
            model_id=options.model_id,
            diagnostics={"extraction_mode": "llm"},
        )

    monkeypatch.setattr(runner, "extract_preview_candidate_graph", fake_extract)

    response = client.post(
        "/api/live/recap-ingest",
        json={
            "operation": "build_graph_preview_bundle",
            "campaign_id": "longmont-c2",
            "session": 22,
            "extract_graph": True,
            "graph_model_id": "gpt-5-mini",
        },
    )

    assert response.status_code == 200
    graph = response.json()["ingest_report"]["graph_preview"]
    assert graph["status"] == "candidate_validation_ready"
    assert graph["extraction_mode"] == "llm"
    assert graph["model_id"] == "gpt-5-mini"
    assert graph["candidate_node_count"] == 1
    assert (ROOT / graph["candidate_graph_path"]).is_file()


def test_recap_ingest_materialize_preview_supergraph_extracts_without_candidate_path(
    client_env: tuple[TestClient, Path, Path], monkeypatch: pytest.MonkeyPatch
) -> None:
    import evals.graph_memory_layer.graph_preview_runner as runner
    from src.graph_memory.extraction.preview_candidate_graph_extractor import PreviewCandidateGraphExtractionResult

    client, _corpus, _candidate = client_env
    _prepare_normalized(client)

    def fake_extract(options, *, client=None):  # noqa: ANN001
        return PreviewCandidateGraphExtractionResult(
            candidate_graph=_live_extraction_payload(),
            raw_model_response="{}",
            model_id=options.model_id,
            diagnostics={"extraction_mode": "llm"},
        )

    monkeypatch.setattr(runner, "extract_preview_candidate_graph", fake_extract)

    response = client.post(
        "/api/live/recap-ingest",
        json={
            "operation": "materialize_preview_supergraph",
            "campaign_id": "longmont-c2",
            "session": 22,
            "extract_graph": True,
            "materialize_after_extract": True,
        },
    )

    assert response.status_code == 200
    graph = response.json()["ingest_report"]["graph_preview"]
    assert graph["status"] == "preview_union_store_ready"
    assert graph["can_open_union_graph"] is True
    assert graph["extraction_mode"] == "llm"
    assert graph["candidate_graph_path"] is not None
    assert (ROOT / graph["preview_union_store_path"]).is_file()


def test_recap_ingest_extract_graph_missing_api_key_returns_llm_blocked(
    client_env: tuple[TestClient, Path, Path], monkeypatch: pytest.MonkeyPatch
) -> None:
    client, _corpus, _candidate = client_env
    _prepare_normalized(client)
    monkeypatch.delenv("OPENAI_API_KEY", raising=False)

    response = client.post(
        "/api/live/recap-ingest",
        json={
            "operation": "build_graph_preview_bundle",
            "campaign_id": "longmont-c2",
            "session": 22,
            "extract_graph": True,
            "force_graph_run": True,
        },
    )

    assert response.status_code == 200
    graph = response.json()["ingest_report"]["graph_preview"]
    assert graph["status"] == "source_span_bundle_ready"
    assert graph["extraction_mode"] == "llm_blocked"
    assert graph["blocked_reason"]
    assert graph["can_open_union_graph"] is False


def test_recap_ingest_rejects_candidate_path_with_extract_graph(
    client_env: tuple[TestClient, Path, Path]
) -> None:
    client, _corpus, candidate = client_env
    _prepare_normalized(client)

    response = client.post(
        "/api/live/recap-ingest",
        json={
            "operation": "build_graph_preview_bundle",
            "campaign_id": "longmont-c2",
            "session": 22,
            "candidate_graph_path": candidate.relative_to(ROOT).as_posix(),
            "extract_graph": True,
        },
    )

    assert response.status_code == 422
    assert "cannot be combined" in response.json()["detail"]


def test_recap_ingest_generate_recap_memory_without_graph_extraction(
    client_env: tuple[TestClient, Path, Path]
) -> None:
    client, _corpus, _candidate = client_env

    response = client.post(
        "/api/live/recap-ingest",
        json={
            "operation": "generate_recap_memory",
            "campaign_id": "longmont-c2",
            "session": 22,
            "raw_text": "Session 22 Recap\n\nThe group scouts the Mireward road.",
            "slug": "Mireward Road Dogfood",
            "check": True,
            "include_graph_extraction": False,
        },
    )

    assert response.status_code == 200
    body = response.json()
    assert body["status"] == "ready_for_planning_activation"
    assert "session_memory_materialized" in body["states"]
    assert "graph_preview" not in body["ingest_report"]


def test_recap_ingest_generate_recap_memory_with_graph_extraction_fake_client(
    client_env: tuple[TestClient, Path, Path], monkeypatch: pytest.MonkeyPatch
) -> None:
    import evals.graph_memory_layer.graph_preview_runner as runner
    from src.graph_memory.extraction.preview_candidate_graph_extractor import PreviewCandidateGraphExtractionResult

    client, _corpus, _candidate = client_env

    def fake_extract(options, *, client=None):  # noqa: ANN001
        return PreviewCandidateGraphExtractionResult(
            candidate_graph=_live_extraction_payload(),
            raw_model_response="{}",
            model_id=options.model_id,
            diagnostics={"extraction_mode": "llm"},
        )

    monkeypatch.setattr(runner, "extract_preview_candidate_graph", fake_extract)

    response = client.post(
        "/api/live/recap-ingest",
        json={
            "operation": "generate_recap_memory",
            "campaign_id": "longmont-c2",
            "session": 22,
            "raw_text": "Session 22 Recap\n\nThe group scouts the Mireward road.",
            "slug": "Mireward Road Dogfood",
            "check": True,
            "include_graph_extraction": True,
            "graph_model_id": "gpt-5-mini",
        },
    )

    assert response.status_code == 200
    body = response.json()
    assert body["status"] == "ready_for_planning_activation"
    assert "session_memory_materialized" in body["states"]
    assert "preview_union_store_ready" in body["states"]
    graph = body["ingest_report"]["graph_preview"]
    assert graph["status"] == "preview_union_store_ready"
    assert graph["extraction_mode"] == "llm"
    assert graph["model_id"] == "gpt-5-mini"
    assert graph["can_open_union_graph"] is True


def test_generate_recap_memory_reuses_staged_notes_and_still_materializes_graph(
    client_env: tuple[TestClient, Path, Path], monkeypatch: pytest.MonkeyPatch
) -> None:
    import evals.graph_memory_layer.graph_preview_runner as runner
    from src.graph_memory.extraction.preview_candidate_graph_extractor import PreviewCandidateGraphExtractionResult

    client, corpus, _candidate = client_env
    staged = corpus / "Longmont Campaign/Campaign 2/_ingest_staging/session_22_raw_notes.md"
    staged.write_text(
        "Session 22 Recap\n\nThe group scouts the Mireward road and regroups at dusk.",
        encoding="utf-8",
    )

    def fake_extract(options, *, client=None):  # noqa: ANN001
        return PreviewCandidateGraphExtractionResult(
            candidate_graph=_live_extraction_payload(),
            raw_model_response="{}",
            model_id=options.model_id,
            diagnostics={"extraction_mode": "llm"},
        )

    monkeypatch.setattr(runner, "extract_preview_candidate_graph", fake_extract)

    response = client.post(
        "/api/live/recap-ingest",
        json={
            "operation": "generate_recap_memory",
            "campaign_id": "longmont-c2",
            "session": 22,
            "raw_text": "Different pasted text should not replace staged notes.",
            "slug": "Mireward Road Dogfood",
            "check": True,
            "include_graph_extraction": True,
            "graph_model_id": "gpt-5-mini",
        },
    )

    assert response.status_code == 200
    body = response.json()
    assert body["status"] == "ready_for_planning_activation"
    assert "staged_raw_notes_conflict" in body["states"]
    assert "session_memory_materialized" in body["states"]
    assert "preview_union_store_ready" in body["states"]
    assert body["ingest_report"]["staged_raw_notes_reused_existing"] is True
    assert "Different pasted text" not in staged.read_text(encoding="utf-8")
    graph = body["ingest_report"]["graph_preview"]
    assert graph["status"] == "preview_union_store_ready"
    assert graph["can_open_union_graph"] is True


def test_recap_ingest_generate_recap_memory_with_blocked_graph_preserves_recap_success(
    client_env: tuple[TestClient, Path, Path], monkeypatch: pytest.MonkeyPatch
) -> None:
    import evals.graph_memory_layer.graph_preview_runner as runner

    client, _corpus, _candidate = client_env
    shutil.rmtree(ROOT / "out/graph_memory/runs/longmont-c2/session-22", ignore_errors=True)

    def fake_extract_blocked(*_args, **_kwargs):  # noqa: ANN002, ANN003
        raise RuntimeError("test llm blocked")

    monkeypatch.setattr(runner, "extract_preview_candidate_graph", fake_extract_blocked)

    response = client.post(
        "/api/live/recap-ingest",
        json={
            "operation": "generate_recap_memory",
            "campaign_id": "longmont-c2",
            "session": 22,
            "raw_text": "Session 22 Recap\n\nThe group scouts the Mireward road.",
            "slug": "Mireward Road Dogfood",
            "check": True,
            "include_graph_extraction": True,
        },
    )

    assert response.status_code == 200
    body = response.json()
    assert body["status"] == "ready_for_planning_activation"
    assert "session_memory_materialized" in body["states"]
    graph = body["ingest_report"]["graph_preview"]
    assert graph["status"] == "source_span_bundle_ready"
    assert graph["extraction_mode"] == "llm_blocked"
    assert graph["blocked_reason"] == "test llm blocked"
    assert any("preview graph extraction blocked" in warning for warning in body["warnings"])
