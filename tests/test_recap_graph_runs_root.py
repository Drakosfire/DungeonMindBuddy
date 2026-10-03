from pathlib import Path

import pytest

from apps.live_control_server.services.graph_ingest_run_registry import (
    GraphIngestRunRegistryError,
    discover_graph_ingest_runs,
    graph_ingest_output_root,
)
from apps.live_control_server.services.recap_graph_preview_ingest import _new_run_dir


def test_configured_root_is_shared_by_writer_and_discovery(tmp_path, monkeypatch):
    repo = tmp_path / "repo"
    repo.mkdir()
    outside = tmp_path / "shared-out"
    outside.mkdir()
    (repo / "out").symlink_to(outside, target_is_directory=True)
    monkeypatch.setenv("DUNGEONMIND_GRAPH_INGEST_RUNS_ROOT", ".dogfood/recap-runs")
    run_dir = _new_run_dir(repo, "longmont-c2", 29)
    assert run_dir.is_relative_to(Path(".dogfood/recap-runs/longmont-c2/session-29"))
    (repo / run_dir).mkdir(parents=True)
    assert discover_graph_ingest_runs(repo) == []
    next_dir = _new_run_dir(repo, "longmont-c2", 29)
    assert next_dir != run_dir
    assert not list(outside.iterdir())


@pytest.mark.parametrize("configured", ["../outside", "file:outside", "out/runs", "{outside}"])
def test_writer_rejects_traversal_uri_and_external_symlink(tmp_path, monkeypatch, configured):
    repo = tmp_path / "repo"
    repo.mkdir()
    outside = tmp_path / "outside"
    outside.mkdir()
    (repo / "out").symlink_to(outside, target_is_directory=True)
    monkeypatch.setenv("DUNGEONMIND_GRAPH_INGEST_RUNS_ROOT", configured.format(outside=outside))
    with pytest.raises(GraphIngestRunRegistryError, match="unsafe graph-ingest runs root"):
        _new_run_dir(repo, "longmont-c2", 29)
    with pytest.raises(GraphIngestRunRegistryError, match="unsafe graph-ingest runs root"):
        discover_graph_ingest_runs(repo)
    assert not list(outside.iterdir())


def test_default_writer_root_stays_inside_owning_repo(tmp_path, monkeypatch):
    monkeypatch.delenv("DUNGEONMIND_GRAPH_INGEST_RUNS_ROOT", raising=False)
    assert graph_ingest_output_root(tmp_path) == tmp_path / "out/graph_memory/runs"
    assert _new_run_dir(tmp_path, "longmont-c2", 29).is_relative_to(Path("out/graph_memory/runs"))
