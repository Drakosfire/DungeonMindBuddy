import pytest

from apps.live_control_server.services.graph_ingest_run_registry import (
    GraphIngestRunRegistryError,
    discover_graph_ingest_runs,
    graph_ingest_output_root,
)


@pytest.mark.parametrize("configured", ["../outside", "file:outside", "out/runs", "{outside}"])
def test_discovery_rejects_traversal_uri_and_external_symlink(tmp_path, monkeypatch, configured):
    repo = tmp_path / "repo"
    repo.mkdir()
    outside = tmp_path / "outside"
    outside.mkdir()
    (repo / "out").symlink_to(outside, target_is_directory=True)
    monkeypatch.setenv("DUNGEONMIND_GRAPH_INGEST_RUNS_ROOT", configured.format(outside=outside))
    with pytest.raises(GraphIngestRunRegistryError, match="unsafe graph-ingest runs root"):
        discover_graph_ingest_runs(repo)
    assert not list(outside.iterdir())


def test_default_writer_root_stays_inside_owning_repo(tmp_path, monkeypatch):
    monkeypatch.delenv("DUNGEONMIND_GRAPH_INGEST_RUNS_ROOT", raising=False)
    assert graph_ingest_output_root(tmp_path) == tmp_path / "out/graph_memory/runs"


def test_registry_counts_manifest_once_when_search_roots_overlap(tmp_path, monkeypatch):
    from apps.live_control_server.services.graph_ingest_run_registry import (
        inspect_graph_ingest_registry_health,
    )

    monkeypatch.setenv("DUNGEONMIND_GRAPH_INGEST_RUNS_ROOT", "evals/graph_memory_layer")
    manifest = tmp_path / "evals/graph_memory_layer/runs/example/graph_ingest_run_manifest.json"
    manifest.parent.mkdir(parents=True)
    manifest.write_text("[]", encoding="utf-8")

    health = inspect_graph_ingest_registry_health(tmp_path, include_eval_roots=True)
    assert health.manifest_files_found == health.invalid_manifests == 1
    assert discover_graph_ingest_runs(tmp_path, include_eval_roots=True) == []
