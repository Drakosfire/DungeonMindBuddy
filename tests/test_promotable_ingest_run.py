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
    preview = (
        repo
        / "out/graph_memory/runs/longmont-c2/session-22/fixture-promote"
        / "preview_union_supergraph.json"
    )
    preview.unlink()
    with pytest.raises(PromotableIngestRunError) as exc:
        resolve_promotable_ingest_run(run_id, root=repo)
    assert exc.value.code == "run_not_promotable"


def test_resolve_and_admit_configured_registry_root(
    tmp_path: Path, monkeypatch
) -> None:
    repo = tmp_path / "repo"
    repo.mkdir()
    # Outside corpus/Docs/evals/tmp so admission cannot cheat via path allowlist.
    custom_rel = "sandbox/custom_ingest_runs"
    monkeypatch.setenv(GRAPH_INGEST_RUNS_ENV, custom_rel)
    run_id, _digest, source = _write_promotable_run(
        repo, runs_rel=custom_rel, extraction_profile="custom_root_profile"
    )
    resolved = resolve_promotable_ingest_run(run_id, root=repo)
    assert resolved.extraction_profile == "custom_root_profile"
    assert resolved.source_artifact_id == "artifact:recap:longmont-c2:session-22"
    assert is_under_ingest_runs(source, root=repo) is True
    assert resolved.sealed_source_uri.startswith(f"repo://{custom_rel}/")
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


def test_assess_manifest_promotability_requires_preview_ready_and_source(
    tmp_path: Path, monkeypatch
) -> None:
    from apps.live_control_server.services.promotable_ingest_run import (
        assess_manifest_promotability,
    )
    from graph_memory.ingestion.graph_ingest_run import GraphIngestRunManifest

    repo = tmp_path / "repo"
    repo.mkdir()
    monkeypatch.setenv(GRAPH_INGEST_RUNS_ENV, "out/graph_memory/runs")
    run_id, _digest, _source = _write_promotable_run(repo)
    resolved = resolve_promotable_ingest_run(run_id, root=repo)
    payload = json.loads(resolved.manifest_path.read_text(encoding="utf-8"))
    manifest = GraphIngestRunManifest.model_validate(payload)

    ok, reason = assess_manifest_promotability(
        manifest,
        preview_union_store_path=str(resolved.preview_union_store_path),
    )
    assert ok is True
    assert reason is None

    bad, bad_reason = assess_manifest_promotability(
        manifest, preview_union_store_path=None
    )
    assert bad is False
    assert bad_reason == "preview union store path is missing"

    payload["health"]["candidate_graph_valid"] = False
    invalid = GraphIngestRunManifest.model_validate(payload)
    bad2, reason2 = assess_manifest_promotability(
        invalid,
        preview_union_store_path=str(resolved.preview_union_store_path),
    )
    assert bad2 is False
    assert reason2 == "candidate graph is not valid"
