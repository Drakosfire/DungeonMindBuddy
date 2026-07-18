"""Unit tests for resolve_promotable_ingest_run (PR011A1)."""

from __future__ import annotations

import hashlib
import json
from pathlib import Path

import pytest

from apps.live_control_server.services.graph_ingest_run_registry import (
    GRAPH_INGEST_RUNS_ENV,
)
from apps.live_control_server.services.promotable_ingest_run import (
    PromotableIngestRunError,
    assess_manifest_promotability,
    is_under_ingest_runs,
    is_under_world_store,
    resolve_promotable_ingest_run,
)
from tests.test_live_extract_promote_api import (
    CAMPAIGN_ID,
    SESSION_ID,
    _write_promotable_run,
)

def test_resolve_promotable_ingest_run_happy(tmp_path: Path, monkeypatch) -> None:
    repo = tmp_path / "repo"
    repo.mkdir()
    monkeypatch.setenv(GRAPH_INGEST_RUNS_ENV, "out/graph_memory/runs")
    run_id, digest, source = _write_promotable_run(repo)

    resolved = resolve_promotable_ingest_run(run_id, root=repo)
    assert resolved.run_id == run_id
    assert resolved.campaign_id == CAMPAIGN_ID
    assert resolved.session_id == SESSION_ID
    assert resolved.source_revision_id == digest
    assert resolved.source_artifact_id == "artifact:recap:longmont-c2:session-22"
    assert resolved.extraction_profile == "category_v1"
    assert resolved.normalized_recap_path == source.resolve()
    assert resolved.candidate_graph_path.is_file()
    assert resolved.preview_union_store_path.is_file()
    assert resolved.sealed_source_uri.startswith("repo://out/graph_memory/runs/")
    assert is_under_ingest_runs(resolved.normalized_recap_path, root=repo)


def test_resolve_unknown_run(tmp_path: Path, monkeypatch) -> None:
    repo = tmp_path / "repo"
    repo.mkdir()
    monkeypatch.setenv(GRAPH_INGEST_RUNS_ENV, "out/graph_memory/runs")
    _write_promotable_run(repo)
    with pytest.raises(PromotableIngestRunError) as exc:
        resolve_promotable_ingest_run("graph-ingest:missing", root=repo)
    assert exc.value.code == "run_not_found"
    assert exc.value.status_code == 404


def test_resolve_scope_mismatch(tmp_path: Path, monkeypatch) -> None:
    repo = tmp_path / "repo"
    repo.mkdir()
    monkeypatch.setenv(GRAPH_INGEST_RUNS_ENV, "out/graph_memory/runs")
    mismatched = "graph-ingest:other:session-1:x"
    _write_promotable_run(repo, run_id=mismatched)
    with pytest.raises(PromotableIngestRunError) as exc:
        resolve_promotable_ingest_run(mismatched, root=repo)
    assert exc.value.code == "run_scope_mismatch"


def test_resolve_rejects_artifact_outside_run_dir(
    tmp_path: Path, monkeypatch
) -> None:
    repo = tmp_path / "repo"
    repo.mkdir()
    monkeypatch.setenv(GRAPH_INGEST_RUNS_ENV, "out/graph_memory/runs")
    run_id, _digest, _source = _write_promotable_run(repo)
    escape = repo / "out/graph_memory/runs/longmont-c2/other/escaped.md"
    escape.parent.mkdir(parents=True, exist_ok=True)
    escape.write_text("escaped\n", encoding="utf-8")
    manifest_path = (
        repo
        / "out/graph_memory/runs/longmont-c2/session-22/fixture-promote"
        / "graph_ingest_run_manifest.json"
    )
    payload = json.loads(manifest_path.read_text(encoding="utf-8"))
    payload["artifacts"]["normalized_recap"]["uri"] = (
        "out/graph_memory/runs/longmont-c2/other/escaped.md"
    )
    payload["source"]["normalized_recap_path"] = (
        "out/graph_memory/runs/longmont-c2/other/escaped.md"
    )
    payload["source"]["normalized_recap_sha256"] = (
        f"sha256:{hashlib.sha256(escape.read_bytes()).hexdigest()}"
    )
    manifest_path.write_text(json.dumps(payload), encoding="utf-8")

    with pytest.raises(PromotableIngestRunError) as exc:
        resolve_promotable_ingest_run(run_id, root=repo)
    assert exc.value.code == "run_not_promotable"
    assert any("escapes" in d for d in exc.value.diagnostics) or "escapes" in str(
        exc.value
    )


def test_resolve_rejects_missing_source_artifact_id(
    tmp_path: Path, monkeypatch
) -> None:
    repo = tmp_path / "repo"
    repo.mkdir()
    monkeypatch.setenv(GRAPH_INGEST_RUNS_ENV, "out/graph_memory/runs")
    run_id, _digest, _source = _write_promotable_run(
        repo, omit_source_artifact_id=True
    )
    with pytest.raises(PromotableIngestRunError) as exc:
        resolve_promotable_ingest_run(run_id, root=repo)
    assert exc.value.code == "run_not_promotable"
    assert "source_artifact_id" in str(exc.value)


def test_resolve_rejects_missing_preview_union_store(
    tmp_path: Path, monkeypatch
) -> None:
    repo = tmp_path / "repo"
    repo.mkdir()
    monkeypatch.setenv(GRAPH_INGEST_RUNS_ENV, "out/graph_memory/runs")
    run_id, _digest, _source = _write_promotable_run(repo, omit_preview=True)
    with pytest.raises(PromotableIngestRunError) as exc:
        resolve_promotable_ingest_run(run_id, root=repo)
    assert exc.value.code == "run_not_promotable"
    assert "preview_union_store" in str(exc.value)


def test_resolve_rejects_deleted_preview_union_store(
    tmp_path: Path, monkeypatch
) -> None:
    repo = tmp_path / "repo"
    repo.mkdir()
    monkeypatch.setenv(GRAPH_INGEST_RUNS_ENV, "out/graph_memory/runs")
    run_id, _digest, _source = _write_promotable_run(repo)
    resolved = resolve_promotable_ingest_run(run_id, root=repo)
    resolved.preview_union_store_path.unlink()
    with pytest.raises(PromotableIngestRunError) as exc:
        resolve_promotable_ingest_run(run_id, root=repo)
    assert exc.value.code == "run_not_promotable"


def test_resolve_admits_configured_non_default_registry_root(
    tmp_path: Path, monkeypatch
) -> None:
    repo = tmp_path / "repo"
    repo.mkdir()
    custom_rel = "sandbox/custom_ingest_runs"
    monkeypatch.setenv(GRAPH_INGEST_RUNS_ENV, custom_rel)
    run_id = "graph-ingest:longmont-c2:session-22:custom-root"
    _write_promotable_run(repo, run_id=run_id, runs_rel=custom_rel)
    resolved = resolve_promotable_ingest_run(run_id, root=repo)
    assert custom_rel in resolved.sealed_source_uri
    assert is_under_ingest_runs(resolved.normalized_recap_path, root=repo) is True


def test_configured_root_artifact_not_under_default_when_env_differs(
    tmp_path: Path, monkeypatch
) -> None:
    repo = tmp_path / "repo"
    repo.mkdir()
    custom_rel = "sandbox/custom_ingest_runs"
    monkeypatch.setenv(GRAPH_INGEST_RUNS_ENV, custom_rel)
    run_id = "graph-ingest:longmont-c2:session-22:custom-root"
    _write_promotable_run(repo, run_id=run_id, runs_rel=custom_rel)
    resolved = resolve_promotable_ingest_run(run_id, root=repo)
    source = resolved.normalized_recap_path
    # Default hard-coded root must not admit a custom-root artifact when env differs.
    monkeypatch.setenv(GRAPH_INGEST_RUNS_ENV, "out/graph_memory/runs")
    assert is_under_ingest_runs(source, root=repo) is False


def test_world_store_detection(tmp_path: Path, monkeypatch) -> None:
    repo = tmp_path / "repo"
    repo.mkdir()
    worlds = repo / "out/graph_memory/worlds/eldyrwild/head.json"
    worlds.parent.mkdir(parents=True, exist_ok=True)
    worlds.write_text("{}\n", encoding="utf-8")
    runs = repo / "out/graph_memory/runs/x/y/z.md"
    runs.parent.mkdir(parents=True, exist_ok=True)
    runs.write_text("ok\n", encoding="utf-8")

    monkeypatch.setattr(
        "apps.live_control_server.services.promotable_ingest_run.world_graph_root",
        lambda: repo / "out/graph_memory/worlds",
    )
    assert is_under_world_store(worlds, root=repo) is True
    assert is_under_world_store(runs, root=repo) is False
    assert is_under_ingest_runs(runs, root=repo) is True


def test_assess_manifest_promotability_uses_prepare_resolver_seam(
    tmp_path: Path, monkeypatch
) -> None:
    repo = tmp_path / "repo"
    repo.mkdir()
    monkeypatch.setenv(GRAPH_INGEST_RUNS_ENV, "out/graph_memory/runs")
    run_id, _digest, _source = _write_promotable_run(repo)
    resolved = resolve_promotable_ingest_run(run_id, root=repo)
    payload = json.loads(resolved.manifest_path.read_text(encoding="utf-8"))
    registry_root = (repo / "out/graph_memory/runs").resolve()

    ok, reason = assess_manifest_promotability(
        repo=repo,
        manifest_path=resolved.manifest_path,
        payload=payload,
        registry_root=registry_root,
    )
    assert ok is True
    assert reason is None

    # Missing candidate artifact: health flags alone must not advertise promotable.
    payload["artifacts"].pop("candidate_graph", None)
    resolved.candidate_graph_path.unlink(missing_ok=True)
    bad, bad_reason = assess_manifest_promotability(
        repo=repo,
        manifest_path=resolved.manifest_path,
        payload=payload,
        registry_root=registry_root,
    )
    assert bad is False
    assert bad_reason is not None
    assert "candidate_graph" in bad_reason
