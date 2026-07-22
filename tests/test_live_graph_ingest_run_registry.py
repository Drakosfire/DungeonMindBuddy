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
    assert (
        status["graph_extraction_profile_options"]["enable_encounter_job_pass"] is True
    )
    manifest = json.loads(
        (tmp_path / status["manifest_path"]).read_text(encoding="utf-8")
    )
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

    with pytest.raises(
        ValueError, match="unsupported graph_extraction_profile: surprise_me"
    ):
        build_recap_graph_preview_bundle(
            repo_root=tmp_path,
            campaign_id="longmont-c2",
            session=24,
            normalized_recap_path=str(source),
            force_graph_run=True,
            extract_graph=True,
            graph_extraction_profile="surprise_me",
        )

    assert not list(
        (tmp_path / "out/graph_memory/runs").glob("**/candidate_graph.json")
    )


def _service_fake_runner_with_candidate(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
):
    import apps.live_control_server.services.recap_graph_preview_ingest as ingest_service

    actual_runner = ingest_service.run_graph_preview_extraction
    calls: list[GraphPreviewRunnerOptions] = []

    def fake_runner(options: GraphPreviewRunnerOptions):
        calls.append(options)
        candidate = tmp_path / "service_fake_candidate.json"
        candidate.write_text(
            CANDIDATE_PATH.read_text(encoding="utf-8"), encoding="utf-8"
        )
        return actual_runner(
            GraphPreviewRunnerOptions(
                campaign_id=options.campaign_id,
                session_id=options.session_id,
                normalized_recap_path=options.normalized_recap_path,
                output_dir=options.output_dir,
                source_label=options.source_label,
                model_id=options.model_id,
                allow_llm=False,
                comparison_mode=options.comparison_mode,
                candidate_graph_path=candidate,
                input_path_record=options.input_path_record,
                graph_extraction_profile=options.graph_extraction_profile,
            )
        )

    monkeypatch.setattr(ingest_service, "run_graph_preview_extraction", fake_runner)
    return ingest_service, calls


def _profiled_candidate_ready_run(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    output_dir: str,
    *,
    graph_extraction_profile: str | None = None,
):
    monkeypatch.chdir(tmp_path)
    source = tmp_path / f"{output_dir.replace('/', '_')}_recap.md"
    candidate = tmp_path / f"{output_dir.replace('/', '_')}_candidate.json"
    source.write_text(RECAP_PATH.read_text(encoding="utf-8"), encoding="utf-8")
    candidate.write_text(CANDIDATE_PATH.read_text(encoding="utf-8"), encoding="utf-8")
    result = run_graph_preview_extraction(
        GraphPreviewRunnerOptions(
            campaign_id="longmont-c2",
            session_id="session-24",
            normalized_recap_path=source,
            output_dir=Path(output_dir),
            candidate_graph_path=candidate,
            graph_extraction_profile=graph_extraction_profile,
            input_path_record=source.relative_to(tmp_path).as_posix(),
        )
    )
    assert result.status == GraphIngestRunStatus.CANDIDATE_VALIDATION_READY
    return result, source


def test_build_recap_graph_preview_bundle_skips_mismatched_profile_reuse(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    old_result, source = _profiled_candidate_ready_run(
        tmp_path, monkeypatch, "out/graph_memory/runs/default_profile"
    )
    ingest_service, calls = _service_fake_runner_with_candidate(tmp_path, monkeypatch)

    status = ingest_service.build_recap_graph_preview_bundle(
        repo_root=tmp_path,
        campaign_id="longmont-c2",
        session=24,
        normalized_recap_path=str(source),
        extract_graph=True,
        graph_extraction_profile="category_encounter_job_preview",
    )

    assert calls
    assert calls[0].graph_extraction_profile == "category_encounter_job_preview"
    assert (
        status["manifest_path"]
        != old_result.manifest_path.relative_to(tmp_path).as_posix()
    )
    assert status["graph_extraction_profile"] == "category_encounter_job_preview"


def test_build_recap_graph_preview_bundle_reuses_matching_profile_run(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    old_result, source = _profiled_candidate_ready_run(
        tmp_path,
        monkeypatch,
        "out/graph_memory/runs/encounter_profile",
        graph_extraction_profile="category_encounter_job_preview",
    )
    ingest_service, calls = _service_fake_runner_with_candidate(tmp_path, monkeypatch)

    status = ingest_service.build_recap_graph_preview_bundle(
        repo_root=tmp_path,
        campaign_id="longmont-c2",
        session=24,
        normalized_recap_path=str(source),
        extract_graph=True,
        graph_extraction_profile="category_encounter_job_preview",
    )

    assert calls == []
    assert (
        status["manifest_path"]
        == old_result.manifest_path.relative_to(tmp_path).as_posix()
    )
    assert status["graph_extraction_profile"] == "category_encounter_job_preview"


def test_build_recap_graph_preview_bundle_legacy_manifest_matches_only_current_default(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    old_result, source = _profiled_candidate_ready_run(
        tmp_path, monkeypatch, "out/graph_memory/runs/legacy_profile"
    )
    manifest = json.loads(old_result.manifest_path.read_text(encoding="utf-8"))
    manifest["diagnostics"].pop("graph_extraction_profile", None)
    manifest["diagnostics"].pop("graph_extraction_profile_options", None)
    old_result.manifest_path.write_text(
        json.dumps(manifest, indent=2, sort_keys=True), encoding="utf-8"
    )

    ingest_service, calls = _service_fake_runner_with_candidate(tmp_path, monkeypatch)
    default_status = ingest_service.build_recap_graph_preview_bundle(
        repo_root=tmp_path,
        campaign_id="longmont-c2",
        session=24,
        normalized_recap_path=str(source),
        extract_graph=True,
    )
    assert calls == []
    assert (
        default_status["manifest_path"]
        == old_result.manifest_path.relative_to(tmp_path).as_posix()
    )

    encounter_status = ingest_service.build_recap_graph_preview_bundle(
        repo_root=tmp_path,
        campaign_id="longmont-c2",
        session=24,
        normalized_recap_path=str(source),
        extract_graph=True,
        graph_extraction_profile="category_encounter_job_preview",
    )
    assert calls
    assert (
        encounter_status["manifest_path"]
        != old_result.manifest_path.relative_to(tmp_path).as_posix()
    )
    assert (
        encounter_status["graph_extraction_profile"] == "category_encounter_job_preview"
    )


def test_build_recap_graph_preview_bundle_candidate_path_does_not_reuse_existing_run(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    old_result, source = _profiled_candidate_ready_run(
        tmp_path, monkeypatch, "out/graph_memory/runs/existing_candidate"
    )
    ingest_service, calls = _service_fake_runner_with_candidate(tmp_path, monkeypatch)
    explicit_candidate = tmp_path / "explicit_candidate.json"
    explicit_candidate.write_text(
        CANDIDATE_PATH.read_text(encoding="utf-8"), encoding="utf-8"
    )

    status = ingest_service.build_recap_graph_preview_bundle(
        repo_root=tmp_path,
        campaign_id="longmont-c2",
        session=24,
        normalized_recap_path=str(source),
        candidate_graph_path=explicit_candidate.relative_to(tmp_path).as_posix(),
        extract_graph=True,
        graph_extraction_profile="category_encounter_job_preview",
    )

    assert calls
    assert calls[0].candidate_graph_path == explicit_candidate.resolve()
    assert (
        status["manifest_path"]
        != old_result.manifest_path.relative_to(tmp_path).as_posix()
    )
    assert status["graph_extraction_profile"] == "category_encounter_job_preview"


def test_build_recap_graph_preview_bundle_force_graph_run_ignores_matching_reuse(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    old_result, source = _profiled_candidate_ready_run(
        tmp_path,
        monkeypatch,
        "out/graph_memory/runs/force_existing",
        graph_extraction_profile="category_encounter_job_preview",
    )
    ingest_service, calls = _service_fake_runner_with_candidate(tmp_path, monkeypatch)

    status = ingest_service.build_recap_graph_preview_bundle(
        repo_root=tmp_path,
        campaign_id="longmont-c2",
        session=24,
        normalized_recap_path=str(source),
        extract_graph=True,
        force_graph_run=True,
        graph_extraction_profile="category_encounter_job_preview",
    )

    assert calls
    assert (
        status["manifest_path"]
        != old_result.manifest_path.relative_to(tmp_path).as_posix()
    )
    assert status["graph_extraction_profile"] == "category_encounter_job_preview"


def test_build_recap_graph_preview_bundle_skips_pre_repair_run_missing_known_entity_mentions(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Default (non-forced) ingest must not reuse chipless pre-repair ready runs."""
    import apps.live_control_server.services.recap_graph_preview_ingest as ingest_service

    old_result, source = _profiled_candidate_ready_run(
        tmp_path,
        monkeypatch,
        "out/graph_memory/runs/pre_repair_missing_sidecar",
        graph_extraction_profile="category_encounter_job_preview",
    )
    # Simulate a pre-repair manifest: strip the known_entity_mentions contract.
    manifest = json.loads(old_result.manifest_path.read_text(encoding="utf-8"))
    artifacts = manifest.get("artifacts") or {}
    sidecar = artifacts.pop("known_entity_mentions", None)
    old_result.manifest_path.write_text(
        json.dumps(manifest, indent=2, sort_keys=True), encoding="utf-8"
    )
    if isinstance(sidecar, dict) and isinstance(sidecar.get("uri"), str):
        sidecar_path = tmp_path / sidecar["uri"]
        if sidecar_path.is_file():
            sidecar_path.unlink()

    assert not ingest_service._manifest_has_known_entity_mentions(
        tmp_path, old_result.manifest_path.relative_to(tmp_path).as_posix()
    )

    service, calls = _service_fake_runner_with_candidate(tmp_path, monkeypatch)
    status = service.build_recap_graph_preview_bundle(
        repo_root=tmp_path,
        campaign_id="longmont-c2",
        session=24,
        normalized_recap_path=str(source),
        extract_graph=True,
        force_graph_run=False,
        graph_extraction_profile="category_encounter_job_preview",
    )

    assert calls, "expected a new sidecar-capable run instead of reusing pre-repair"
    assert (
        status["manifest_path"]
        != old_result.manifest_path.relative_to(tmp_path).as_posix()
    )
    assert ingest_service._manifest_has_known_entity_mentions(
        tmp_path, status["manifest_path"]
    )


def test_registry_summary_exposes_graph_review_run_metadata(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    result = _preview_union_ready_run(
        tmp_path, monkeypatch, "out/graph_memory/runs/metadata"
    )
    payload = _read_manifest(result.manifest_path)
    payload["source"]["source_label"] = "Session 24 recap"
    payload["health"]["model_id"] = "gpt-test"
    payload["metadata"] = {
        "extraction_profile": "anchor_quote_n3",
        "provider": "openai",
    }
    payload["runner_options"] = {"vocabulary_mode": "node", "temperature": 0.2}
    payload["warnings"] = ["check this"]
    payload["errors"] = []
    payload["next_actions"] = ["review projection"]
    _write_manifest(result.manifest_path, payload)

    run = discover_graph_ingest_runs(tmp_path, require_preview_union_store=True)[0]

    assert run.run_id == payload["run_id"]
    assert run.generated_at == payload["updated_at"]
    assert run.model_id == "gpt-test"
    assert run.model_provider == "openai"
    assert run.extraction_profile == "anchor_quote_n3"
    assert run.vocabulary_mode.value == "node"
    assert run.runner_options_summary["temperature"] == 0.2
    assert run.diagnostics_summary["preview_only"] is True
    assert run.diagnostics_summary["warnings_count"] == 1
    assert run.diagnostics_summary["next_actions_count"] == 1
    assert run.preview_union_available is True
    assert run.promotable is True
    assert run.promotable_reason is None
    assert (
        run.run_label
        == "Session 24 recap · anchor_quote_n3 · vocab:node · gpt-test · preview_union_store_ready"
    )
    assert str(tmp_path) not in run.run_label


def test_registry_summary_defaults_missing_metadata_to_unknown(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    result = _candidate_ready_run(
        tmp_path, monkeypatch, "out/graph_memory/runs/defaults"
    )
    payload = _read_manifest(result.manifest_path)
    payload["health"].pop("model_id", None)
    _write_manifest(result.manifest_path, payload)

    run = discover_graph_ingest_runs(tmp_path)[0]

    assert run.run_id == payload["run_id"]
    assert run.model_id is None
    assert run.model_provider is None
    assert run.extraction_profile is None
    assert run.vocabulary_mode.value == "unknown"
    assert run.runner_options_summary == {}
    assert run.preview_union_available is False
    assert run.promotable is False
    assert run.promotable_reason is not None
    assert "None" not in run.run_label


@pytest.mark.parametrize(
    ("metadata", "expected"),
    [
        ({"vocabulary_mode": "dynamic"}, "dynamic"),
        ({"node_vocabulary": True, "edge_vocabulary": True}, "node_and_edge"),
        ({"node_vocabulary_enabled": True}, "node"),
        ({"use_edge_vocabulary": True}, "edge"),
        ({"use_vocabulary": False}, "none"),
        ({"vocabulary_path": "contains-vocabulary-word"}, "unknown"),
    ],
)
def test_registry_summary_infers_vocabulary_modes(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    metadata: dict[str, object],
    expected: str,
) -> None:
    result = _candidate_ready_run(
        tmp_path,
        monkeypatch,
        f"out/graph_memory/runs/vocab-{expected.replace('_', '-')}",
    )
    payload = _read_manifest(result.manifest_path)
    payload["metadata"] = metadata
    _write_manifest(result.manifest_path, payload)

    run = discover_graph_ingest_runs(tmp_path)[0]

    assert run.vocabulary_mode.value == expected


def test_registry_summary_sanitizes_runner_options_and_diagnostics(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    result = _candidate_ready_run(
        tmp_path, monkeypatch, "out/graph_memory/runs/sanitize"
    )
    payload = _read_manifest(result.manifest_path)
    payload["runner_options"] = {
        "model_id": "gpt-test",
        "max_passes": 3,
        "prompt": "do not expose",
        "source_text": "also do not expose",
        "extraction_profile": "category_encounter_job_preview",
        "long": "x" * 241,
        "nested": {"model_provider": "openai", "prompt": "nope"},
        "nodes": [{"id": "n1"}],
    }
    payload["diagnostics"] = {
        **payload["diagnostics"],
        "candidate_extraction": False,
        "runner_options": {"temperature": 0.1, "prompt": "nope"},
    }
    payload.pop("extraction", None)
    payload["diagnostics"].pop("extraction_mode", None)
    payload["warnings"] = ["warning one", "warning two"]
    payload["errors"] = ["error one"]
    _write_manifest(result.manifest_path, payload)

    run = discover_graph_ingest_runs(tmp_path)[0]

    assert run.extraction_mode == "none"
    assert run.runner_options_summary == {
        "model_id": "gpt-test",
        "max_passes": 3,
        "extraction_profile": "category_encounter_job_preview",
        "nested.model_provider": "openai",
        "temperature": 0.1,
    }
    assert run.diagnostics_summary["candidate_extraction"] is False
    assert run.diagnostics_summary["warnings_count"] == 2
    assert run.diagnostics_summary["errors_count"] == 1
    assert "prompt" not in run.runner_options_summary
    assert "source_text" not in run.runner_options_summary
    assert "long" not in run.runner_options_summary


def test_registry_summary_ignores_malformed_optional_metadata(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    result = _candidate_ready_run(
        tmp_path, monkeypatch, "out/graph_memory/runs/malformed-metadata"
    )
    payload = _read_manifest(result.manifest_path)
    payload["metadata"] = ["not", "a", "dict"]
    payload["runner_options"] = {"extraction_profile": {"not": "scalar"}}
    payload["vocabulary"] = {"mode": ["dynamic"]}
    _write_manifest(result.manifest_path, payload)

    runs = discover_graph_ingest_runs(tmp_path)

    assert len(runs) == 1
    assert runs[0].extraction_profile is None
    assert runs[0].vocabulary_mode.value == "unknown"


def _read_manifest(manifest_path: Path) -> dict[str, object]:
    return json.loads(manifest_path.read_text(encoding="utf-8"))


def _write_manifest(manifest_path: Path, payload: dict[str, object]) -> None:
    manifest_path.write_text(json.dumps(payload), encoding="utf-8")


def test_registry_summary_not_promotable_when_candidate_artifact_missing(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Ready health flags alone must not advertise promotable without a candidate file."""
    from tests.test_live_extract_promote_api import _write_promotable_run

    repo = tmp_path / "repo"
    repo.mkdir()
    monkeypatch.setenv(GRAPH_INGEST_RUNS_ENV, "out/graph_memory/runs")
    run_id = "graph-ingest:longmont-c2:session-22:missing-candidate"
    _write_promotable_run(repo, run_id=run_id, omit_candidate=True)

    runs = discover_graph_ingest_runs(repo, require_preview_union_store=True)
    assert runs
    assert runs[0].run_id == run_id
    assert runs[0].preview_union_available is True
    assert runs[0].promotable is False
    assert runs[0].promotable_reason is not None
    assert "candidate_graph" in runs[0].promotable_reason


def test_registry_summary_not_promotable_when_normalized_recap_missing(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    from tests.test_live_extract_promote_api import _write_promotable_run

    repo = tmp_path / "repo"
    repo.mkdir()
    monkeypatch.setenv(GRAPH_INGEST_RUNS_ENV, "out/graph_memory/runs")
    run_id = "graph-ingest:longmont-c2:session-22:missing-source"
    _write_promotable_run(repo, run_id=run_id)
    source = (
        repo
        / "out/graph_memory/runs/longmont-c2/session-22/fixture-promote"
        / "normalized_recap_source.md"
    )
    assert source.is_file()
    source.unlink()

    runs = discover_graph_ingest_runs(repo, require_preview_union_store=True)
    assert runs
    assert runs[0].run_id == run_id
    assert runs[0].promotable is False
    assert runs[0].promotable_reason is not None
    assert "normalized_recap" in runs[0].promotable_reason


def test_registry_summary_not_promotable_on_run_id_scope_mismatch(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    from tests.test_live_extract_promote_api import _write_promotable_run

    repo = tmp_path / "repo"
    repo.mkdir()
    monkeypatch.setenv(GRAPH_INGEST_RUNS_ENV, "out/graph_memory/runs")
    mismatched = "graph-ingest:other-campaign:session-1:scope-mismatch"
    _write_promotable_run(repo, run_id=mismatched)

    runs = discover_graph_ingest_runs(repo, require_preview_union_store=True)
    assert runs
    assert runs[0].run_id == mismatched
    assert runs[0].promotable is False
    assert runs[0].promotable_reason is not None
    assert "campaign/session" in runs[0].promotable_reason

def test_registry_stamps_projection_authority_from_world_head_sessions(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    _preview_union_ready_run(
        tmp_path,
        monkeypatch,
        "out/graph_memory/runs/on-head",
        campaign_id="longmont-c2",
        session_id="session-24",
    )
    _preview_union_ready_run(
        tmp_path,
        monkeypatch,
        "out/graph_memory/runs/not-on-head",
        campaign_id="longmont-c2",
        session_id="session-99",
    )

    def fake_sessions(*, campaign_id: str, world_id: str = "eldyrwild", graph_root=None):
        assert campaign_id == "longmont-c2"
        assert world_id == "eldyrwild"
        return {"session-24"}

    monkeypatch.setattr(
        "graph_memory.interaction.latest_recap.session_ids_in_world_graph_head",
        fake_sessions,
    )

    runs = discover_graph_ingest_runs(tmp_path, require_preview_union_store=True)
    by_session = {run.session_id: run.projection_authority for run in runs}
    assert by_session["session-24"] == "world_graph"
    assert by_session["session-99"] == "preview_union"


def test_graph_session_ids_from_store_reads_artifacts_and_edges() -> None:
    from graph_memory.interaction.latest_recap import graph_session_ids_from_store

    store = {
        "source_artifacts": {
            "a1": {"campaign_id": "longmont-c2", "session_id": "session-24"},
            "a2": {"campaign_id": "longmont-c1", "session_id": "session-3"},
        },
        "edges": {
            "e1": {
                "state": {"campaign_scope": "longmont-c2"},
                "session_ids": ["22", "session-25"],
            },
        },
    }
    assert graph_session_ids_from_store(store, "longmont-c2") == [
        "session-22",
        "session-24",
        "session-25",
    ]
