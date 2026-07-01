from __future__ import annotations

import json
from pathlib import Path

import pytest

import apps.live_control_server.services.graph_ingest_run_registry as registry_module
from apps.live_control_server.services.graph_ingest_run_registry import (
    GRAPH_INGEST_RUNS_ENV,
    GraphIngestRunRegistryError,
    discover_graph_ingest_runs,
    resolve_latest_preview_union_graph_ingest_run,
)
from evals.graph_memory_layer.graph_preview_runner import (
    GraphPreviewRunnerOptions,
    run_graph_preview_extraction,
)
from graph_memory.ingestion import GraphIngestRunStatus
from graph_memory.union_supergraph.preview_run_materialize import (
    PreviewUnionMaterializeOptions,
    materialize_preview_union_store_from_graph_ingest_run,
)

FIXTURE_DIR = (
    Path(__file__).resolve().parents[1]
    / "tests/fixtures/graph_memory/category_preview_runner"
)
ROOT = Path(__file__).resolve().parents[1]
RECAP_PATH = FIXTURE_DIR / "session_24_normalized_recap.md"
CANDIDATE_PATH = FIXTURE_DIR / "candidate_graph_fixture.json"


def test_registry_discovers_preview_union_store_ready_run(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    result = _preview_union_ready_run(
        tmp_path, monkeypatch, "out/graph_memory/runs/ready"
    )

    runs = discover_graph_ingest_runs(tmp_path, require_preview_union_store=True)

    assert len(runs) == 1
    run = runs[0]
    assert run.manifest_path == result.manifest_path.relative_to(tmp_path).as_posix()
    assert run.campaign_id == "longmont-c2"
    assert run.session_id == "session-24"
    assert run.status == "preview_union_store_ready"
    assert run.preview_union_store_path
    assert run.preview_union_store_valid is True
    assert run.node_count > 0
    assert run.edge_count >= 0
    assert run.evidence_ref_count > 0


def test_registry_filters_by_campaign_and_session(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    _preview_union_ready_run(
        tmp_path,
        monkeypatch,
        "out/graph_memory/runs/a",
        campaign_id="longmont-c2",
        session_id="session-24",
    )
    _preview_union_ready_run(
        tmp_path,
        monkeypatch,
        "out/graph_memory/runs/b",
        campaign_id="other",
        session_id="session-99",
    )

    runs = discover_graph_ingest_runs(
        tmp_path, campaign_id="longmont-c2", session_id="session-24"
    )

    assert [run.session_id for run in runs] == ["session-24"]


def test_registry_filters_to_preview_union_store_ready(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    _candidate_ready_run(tmp_path, monkeypatch, "out/graph_memory/runs/candidate")
    _preview_union_ready_run(tmp_path, monkeypatch, "out/graph_memory/runs/ready")

    runs = discover_graph_ingest_runs(tmp_path, require_preview_union_store=True)

    assert len(runs) == 1
    assert runs[0].status == "preview_union_store_ready"


def test_registry_latest_prefers_newer_updated_at_or_mtime(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    older = _preview_union_ready_run(
        tmp_path, monkeypatch, "out/graph_memory/runs/older"
    )
    newer = _preview_union_ready_run(
        tmp_path, monkeypatch, "out/graph_memory/runs/newer"
    )
    _set_manifest_time(older.manifest_path, "2026-06-28T10:00:00Z")
    _set_manifest_time(newer.manifest_path, "2026-06-28T11:00:00Z")

    latest = resolve_latest_preview_union_graph_ingest_run(
        tmp_path, campaign_id="longmont-c2", session_id="session-24"
    )

    assert latest.manifest_path == newer.manifest_path.relative_to(tmp_path).as_posix()


def test_registry_rejects_unsafe_runs_root_env(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setattr(registry_module, "repo_root", lambda: tmp_path)
    monkeypatch.setenv(GRAPH_INGEST_RUNS_ENV, "../escape")

    with pytest.raises(GraphIngestRunRegistryError) as excinfo:
        discover_graph_ingest_runs()

    assert excinfo.value.status_code == 422
    assert "unsafe graph-ingest runs root" in str(excinfo.value)


def test_registry_skips_invalid_manifest_without_crashing_listing(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    _preview_union_ready_run(tmp_path, monkeypatch, "out/graph_memory/runs/valid")
    bad_dir = tmp_path / "out/graph_memory/runs/bad"
    bad_dir.mkdir(parents=True)
    (bad_dir / "graph_ingest_run_manifest.json").write_text("{bad", encoding="utf-8")

    runs = discover_graph_ingest_runs(tmp_path)

    assert len(runs) == 1
    assert runs[0].run_dir == "out/graph_memory/runs/valid"


def test_registry_latest_raises_when_no_ready_run(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    _candidate_ready_run(tmp_path, monkeypatch, "out/graph_memory/runs/candidate")

    with pytest.raises(GraphIngestRunRegistryError) as excinfo:
        resolve_latest_preview_union_graph_ingest_run(
            tmp_path, campaign_id="longmont-c2", session_id="session-24"
        )

    assert excinfo.value.status_code == 404
    assert "no preview_union_store_ready graph-ingest run found" in str(excinfo.value)


def test_registry_discovers_checked_in_session_1_eval_dogfood() -> None:
    runs = discover_graph_ingest_runs(
        ROOT,
        campaign_id="longmont-c1",
        session_id="session-1",
        require_preview_union_store=True,
        include_eval_roots=True,
    )
    assert runs
    assert runs[0].manifest_path.endswith(
        "session_1_vocabulary_ablation_projection_dogfood/graph_ingest_run_manifest.json"
    )
    assert runs[0].node_count >= 30
    assert runs[0].edge_count >= 20


def _candidate_ready_run(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    output_dir: str,
    *,
    campaign_id: str = "longmont-c2",
    session_id: str = "session-24",
):
    monkeypatch.chdir(tmp_path)
    source = tmp_path / f"{output_dir.replace('/', '_')}_recap.md"
    candidate = tmp_path / f"{output_dir.replace('/', '_')}_candidate.json"
    source.write_text(RECAP_PATH.read_text(encoding="utf-8"), encoding="utf-8")
    candidate.write_text(CANDIDATE_PATH.read_text(encoding="utf-8"), encoding="utf-8")
    result = run_graph_preview_extraction(
        GraphPreviewRunnerOptions(
            campaign_id=campaign_id,
            session_id=session_id,
            normalized_recap_path=source,
            output_dir=Path(output_dir),
            candidate_graph_path=candidate,
        )
    )
    assert result.status == GraphIngestRunStatus.CANDIDATE_VALIDATION_READY
    return result


def _preview_union_ready_run(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, output_dir: str, **kwargs
):
    runner_result = _candidate_ready_run(tmp_path, monkeypatch, output_dir, **kwargs)
    result = materialize_preview_union_store_from_graph_ingest_run(
        PreviewUnionMaterializeOptions(manifest_path=runner_result.manifest_path)
    )
    assert result.status == GraphIngestRunStatus.PREVIEW_UNION_STORE_READY
    return result


def _set_manifest_time(manifest_path: Path, updated_at: str) -> None:
    payload = json.loads(manifest_path.read_text(encoding="utf-8"))
    payload["updated_at"] = updated_at
    manifest_path.write_text(json.dumps(payload), encoding="utf-8")


def test_build_recap_graph_preview_bundle_threads_profile_without_extraction(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    from apps.live_control_server.services.recap_graph_preview_ingest import (
        build_recap_graph_preview_bundle,
    )

    monkeypatch.chdir(tmp_path)
    source = tmp_path / "normalized.md"
    source.write_text(RECAP_PATH.read_text(encoding="utf-8"), encoding="utf-8")

    status = build_recap_graph_preview_bundle(
        repo_root=tmp_path,
        campaign_id="longmont-c2",
        session=24,
        normalized_recap_path=str(source),
        force_graph_run=True,
        extract_graph=False,
        graph_extraction_profile="category_encounter_job_preview",
    )

    assert status["status"] == GraphIngestRunStatus.SOURCE_SPAN_BUNDLE_READY.value
    assert status["candidate_graph_path"] is None
    assert status["graph_extraction_profile"] == "category_encounter_job_preview"
    assert status["graph_extraction_profile_options"]["enable_encounter_job_pass"] is True
    manifest = json.loads((tmp_path / status["manifest_path"]).read_text(encoding="utf-8"))
    assert manifest["diagnostics"]["candidate_extraction"] is False
    assert not (tmp_path / status["run_dir"] / "pass_outputs.json").exists()


def test_build_recap_graph_preview_bundle_unknown_profile_fails_closed(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    from apps.live_control_server.services.recap_graph_preview_ingest import (
        build_recap_graph_preview_bundle,
    )

    monkeypatch.chdir(tmp_path)
    source = tmp_path / "normalized.md"
    source.write_text(RECAP_PATH.read_text(encoding="utf-8"), encoding="utf-8")

    with pytest.raises(ValueError, match="unsupported graph_extraction_profile: surprise_me"):
        build_recap_graph_preview_bundle(
            repo_root=tmp_path,
            campaign_id="longmont-c2",
            session=24,
            normalized_recap_path=str(source),
            force_graph_run=True,
            extract_graph=True,
            graph_extraction_profile="surprise_me",
        )

    assert not list((tmp_path / "out/graph_memory/runs").glob("**/candidate_graph.json"))
