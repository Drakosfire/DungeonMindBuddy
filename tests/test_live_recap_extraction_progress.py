from __future__ import annotations

from pathlib import Path

from fastapi.testclient import TestClient

from apps.live_control_server.config import repo_root
from apps.live_control_server.main import create_app
from apps.live_control_server.services.recap_extraction_progress import (
    LIVE_EXTRACTION_PROGRESS_SCHEMA,
    read_live_extraction_progress,
    write_live_extraction_progress,
)
from src.graph_memory.extraction.category_candidate_graph_extractor import (
    count_category_pass_edges_so_far,
    count_category_pass_nodes_so_far,
    planned_category_pass_names,
)


def test_write_and_read_live_extraction_progress(tmp_path: Path, monkeypatch) -> None:
    monkeypatch.setenv("DUNGEONMIND_GRAPH_INGEST_RUNS_ROOT", str(tmp_path / "runs"))
    payload = write_live_extraction_progress(
        tmp_path,
        campaign_id="longmont-c2",
        session=22,
        phase="extracting",
        current_pass="location_pass",
        current_label="Extracting locations",
        completed_passes=["actor_pass"],
        pass_index=2,
        pass_total=7,
        nodes_so_far=14,
        edges_so_far=0,
    )
    assert payload["schema"] == LIVE_EXTRACTION_PROGRESS_SCHEMA
    assert payload["nodes_so_far"] == 14

    loaded = read_live_extraction_progress(
        tmp_path, campaign_id="longmont-c2", session=22
    )
    assert loaded["phase"] == "extracting"
    assert loaded["current_pass"] == "location_pass"
    assert loaded["pass_index"] == 2
    assert loaded["nodes_so_far"] == 14
    assert (tmp_path / "runs/longmont-c2/session-22/live_extraction_progress.json").is_file()


def test_read_missing_progress_returns_idle(tmp_path: Path, monkeypatch) -> None:
    monkeypatch.setenv("DUNGEONMIND_GRAPH_INGEST_RUNS_ROOT", str(tmp_path / "runs"))
    loaded = read_live_extraction_progress(
        tmp_path, campaign_id="longmont-c2", session=9
    )
    assert loaded["phase"] == "idle"
    assert loaded["nodes_so_far"] == 0


def test_category_pass_count_helpers() -> None:
    outputs = {
        "actor_pass": {"observation_nodes": [{"node_id": "a"}, {"node_id": "b"}]},
        "location_pass": {"observation_nodes": [{"node_id": "l1"}]},
        "edge_pass": {"observation_edges": [{"edge_id": "e1"}, {"edge_id": "e2"}]},
    }
    assert count_category_pass_nodes_so_far(outputs) == 3
    assert count_category_pass_edges_so_far(outputs) == 2
    assert len(planned_category_pass_names(enable_encounter_job_pass=False)) == 7
    assert len(planned_category_pass_names(enable_encounter_job_pass=True)) == 8


def test_extraction_progress_get_endpoint(tmp_path: Path, monkeypatch) -> None:
    monkeypatch.setenv("DUNGEONMIND_GRAPH_INGEST_RUNS_ROOT", str(tmp_path / "runs"))
    # Point repo_root resolution via writing under the real repo's env root override.
    # The route uses apps.live_control_server.config.repo_root(); progress path uses env.
    write_live_extraction_progress(
        repo_root(),
        campaign_id="longmont-c2",
        session=22,
        phase="normalizing",
        current_label="Normalizing recap",
    )
    client = TestClient(create_app())
    response = client.get(
        "/api/live/recap-ingest/extraction-progress",
        params={"campaign_id": "longmont-c2", "session": 22},
    )
    assert response.status_code == 200
    body = response.json()
    assert body["schema"] == LIVE_EXTRACTION_PROGRESS_SCHEMA
    assert body["phase"] == "normalizing"
    assert body["current_label"] == "Normalizing recap"
