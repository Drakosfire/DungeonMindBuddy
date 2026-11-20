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


def test_latest_preview_matches_ranked_discovery(monkeypatch):
    from types import SimpleNamespace

    from apps.live_control_server.services import graph_ingest_run_registry as registry

    candidates = [
        (SimpleNamespace(updated_at="2026-01-01", created_at="", manifest_path="a"), 99),
        (SimpleNamespace(updated_at="2026-02-01", created_at="", manifest_path="b"), 10),
        (SimpleNamespace(updated_at="2026-02-01", created_at="", manifest_path="a"), 10),
        (SimpleNamespace(updated_at="2026-02-01", created_at="", manifest_path="c"), 1),
    ]
    monkeypatch.setattr(registry, "_iter_ingest_candidates", lambda *a, **kw: iter(candidates))
    ranked = registry.discover_graph_ingest_runs(require_preview_union_store=True)
    assert ranked[0].manifest_path == "a"
    assert registry.resolve_latest_preview_union_graph_ingest_run(
        campaign_id="campaign", session_id="session"
    ) is ranked[0]


@pytest.mark.parametrize("status", [None, 404, 503])
def test_discovery_reuses_descriptor_digest_only_within_one_scan(tmp_path, monkeypatch, status):
    from types import SimpleNamespace

    from apps.live_control_server.services import graph_ingest_run_registry as registry
    from apps.live_control_server.services import source_artifact_registry as descriptors

    digest = "a" * 64
    paths = [tmp_path / name for name in ("first", "second")]
    for path in paths:
        path.touch()
    calls = []

    def lookup(artifact_id):
        calls.append(artifact_id)
        if status == 404 or (status == 503 and len(calls) == 1):
            raise descriptors.SourceArtifactRegistryError("lookup failed", status_code=status)
        return SimpleNamespace(content_sha256=digest)

    monkeypatch.setattr(descriptors, "get_source_artifact", lookup)
    monkeypatch.setattr(registry, "_iter_manifest_paths", lambda *a, **kw: iter(paths))
    monkeypatch.setattr(
        registry,
        "_summarize_manifest",
        lambda repo, path: (
            SimpleNamespace(updated_at="", created_at="", manifest_path=path.name),
            {"source": {"source_artifact_id": "shared"}},
        ),
    )

    for scan in (1, 2):
        rows = registry.discover_graph_ingest_runs(tmp_path, source_recap_sha256=digest)
        assert len(rows) == (0 if status == 404 else 1 if status == 503 and scan == 1 else 2)
        assert calls == ["shared"] * (scan + (status == 503))
