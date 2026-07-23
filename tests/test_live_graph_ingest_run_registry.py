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
    from apps.live_control_server.services.source_artifact_registry import (
        create_recap_source_artifact,
        load_source_span_index,
    )
    from src.graph_memory.source_span import source_span_index_to_dict

    monkeypatch.chdir(tmp_path)
    source = tmp_path / f"{output_dir.replace('/', '_')}_recap.md"
    candidate = tmp_path / f"{output_dir.replace('/', '_')}_candidate.json"
    source.write_text(RECAP_PATH.read_text(encoding="utf-8"), encoding="utf-8")
    candidate.write_text(CANDIDATE_PATH.read_text(encoding="utf-8"), encoding="utf-8")
    artifact = create_recap_source_artifact(
        tmp_path,
        campaign_id=campaign_id,
        session_id=session_id,
        recap_path=source,
    )
    span_payload = source_span_index_to_dict(
        load_source_span_index(tmp_path, artifact.source_artifact_id)
    )
    graph = json.loads(candidate.read_text(encoding="utf-8"))
    graph["source_artifact_ids"] = [artifact.source_artifact_id]
    candidate.write_text(json.dumps(graph, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    result = run_graph_preview_extraction(
        GraphPreviewRunnerOptions(
            campaign_id=campaign_id,
            session_id=session_id,
            normalized_recap_path=source,
            output_dir=Path(output_dir),
            candidate_graph_path=candidate,
            source_span_index=span_payload,
            source_artifact_id=artifact.source_artifact_id,
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
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    *,
    failure_kind: str | None = None,
):
    import apps.live_control_server.services.recap_graph_preview_ingest as ingest_service
    import hashlib
    from datetime import UTC, datetime

    from apps.live_control_server.services.graph_run_registry import (
        ExtractionRunRegistryDocument,
        extraction_runs_path,
    )
    from apps.live_control_server.services.source_artifact_registry import (
        create_recap_source_artifact,
        load_source_span_index,
    )
    from graph_memory.ingestion.extraction_run import (
        ExtractionRun,
        ExtractionRunComponentKind,
        ExtractionRunComponentRef,
        ExtractionRunStatus,
    )
    from src.graph_memory.extraction.graph_preview_runner import ProductionExtractionResult
    from src.graph_memory.source_span import source_span_index_to_dict

    actual_runner = ingest_service.run_graph_preview_extraction
    calls: list[GraphPreviewRunnerOptions] = []
    run_counter = {"n": 0}

    def _write_json(path: Path, payload: dict) -> None:
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(
            json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8"
        )

    def _file_sha256(path: Path) -> str:
        return hashlib.sha256(path.read_bytes()).hexdigest()

    def _append_extraction_run(run: ExtractionRun) -> None:
        path = extraction_runs_path(tmp_path)
        if path.is_file():
            document = ExtractionRunRegistryDocument.model_validate(
                json.loads(path.read_text(encoding="utf-8"))
            )
        else:
            document = ExtractionRunRegistryDocument()
        document.records.append(run)
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(
            json.dumps(document.model_dump(mode="json"), indent=2, sort_keys=True) + "\n",
            encoding="utf-8",
        )

    def fake_production(**kwargs):  # noqa: ANN003
        run_counter["n"] += 1
        run_id = f"er_service_fake_{run_counter['n']}"
        out = tmp_path / "out" / "graph_memory" / "runs" / "extraction" / run_id
        out.mkdir(parents=True, exist_ok=True)

        campaign_id = str(kwargs.get("campaign_id") or "longmont-c2")
        session_id = str(kwargs.get("session_id") or "session-24")
        recap_path = Path(kwargs["recap_path"])
        allow_llm = bool(kwargs.get("allow_llm"))
        artifact = create_recap_source_artifact(
            tmp_path,
            campaign_id=campaign_id,
            session_id=session_id,
            recap_path=recap_path,
        )
        span_payload = source_span_index_to_dict(
            load_source_span_index(tmp_path, artifact.source_artifact_id)
        )
        span_path = out / "source_span_index.json"
        _write_json(span_path, span_payload)

        candidate = json.loads(CANDIDATE_PATH.read_text(encoding="utf-8"))
        candidate["source_artifact_ids"] = [artifact.source_artifact_id]
        candidate_path = out / "candidate_graph.json"
        _write_json(candidate_path, candidate)

        now = datetime.now(UTC).isoformat().replace("+00:00", "Z")
        resolved_failure = failure_kind
        if not allow_llm and resolved_failure is None:
            run_status = ExtractionRunStatus.PREPARED
            packageable_candidate = None
        elif resolved_failure is not None:
            run_status = ExtractionRunStatus.FAILED
            packageable_candidate = candidate
        else:
            run_status = ExtractionRunStatus.REVIEWABLE
            packageable_candidate = candidate

        components = {
            ExtractionRunComponentKind.SOURCE_ARTIFACT.value: ExtractionRunComponentRef(
                kind=ExtractionRunComponentKind.SOURCE_ARTIFACT,
                uri=artifact.uri,
                sha256=artifact.content_sha256 or "",
                exists=True,
            ),
            ExtractionRunComponentKind.SOURCE_SPAN_INDEX.value: ExtractionRunComponentRef(
                kind=ExtractionRunComponentKind.SOURCE_SPAN_INDEX,
                uri=f"repo://{span_path.relative_to(tmp_path).as_posix()}",
                sha256=_file_sha256(span_path),
                exists=True,
            ),
        }
        if packageable_candidate is not None:
            components[ExtractionRunComponentKind.CANDIDATE_GRAPH.value] = (
                ExtractionRunComponentRef(
                    kind=ExtractionRunComponentKind.CANDIDATE_GRAPH,
                    uri=f"repo://{candidate_path.relative_to(tmp_path).as_posix()}",
                    sha256=_file_sha256(candidate_path),
                    exists=True,
                )
            )

        run = ExtractionRun(
            run_id=run_id,
            source_artifact_id=artifact.source_artifact_id,
            source_domain="recap",
            status=run_status,
            campaign_id=campaign_id,
            session_id=session_id,
            created_at=now,
            updated_at=now,
            components=components,
        )
        _append_extraction_run(run)
        return ProductionExtractionResult(
            run=run,
            candidate_graph=packageable_candidate,
            source_span_index=span_payload,
            known_entity_mentions={
                "schema": "dmb_known_entity_mention_sidecar_v0",
                "version": "0.1",
                "campaign_id": campaign_id,
                "session_id": session_id,
                "mentions": [],
                "ambiguous_surfaces": [],
                "diagnostics": {"mention_count": 0, "empty_contract": True},
            }
            if packageable_candidate is not None
            else None,
            failure_kind=resolved_failure,
            diagnostics=[f"forced failure: {resolved_failure}"] if resolved_failure else [],
            model_id="gpt-5.4-mini",
            profile_id="recap_session_default",
            profile_version="1.0.0",
        )

    def fake_runner(options: GraphPreviewRunnerOptions):
        calls.append(options)
        return actual_runner(options)

    monkeypatch.setattr(ingest_service, "run_recap_production_extraction", fake_production)
    monkeypatch.setattr(ingest_service, "run_graph_preview_extraction", fake_runner)
    return ingest_service, calls


def _bind_production_lineage(
    tmp_path: Path,
    result,
    *,
    source_artifact_id: str | None = None,
) -> str:
    """Register a real REVIEWABLE ExtractionRun bound to packaged digests."""
    import hashlib
    from datetime import UTC, datetime

    from apps.live_control_server.services.graph_run_registry import (
        ExtractionRunRegistryDocument,
        extraction_runs_path,
    )
    from apps.live_control_server.services.source_artifact_registry import (
        create_recap_source_artifact,
        load_source_span_index,
    )
    from graph_memory.ingestion.extraction_run import (
        ExtractionRun,
        ExtractionRunComponentKind,
        ExtractionRunComponentRef,
        ExtractionRunStatus,
    )
    from src.graph_memory.source_span import source_span_index_to_dict

    manifest = json.loads(result.manifest_path.read_text(encoding="utf-8"))
    artifacts = dict(manifest.get("artifacts") or {})
    source = dict(manifest.get("source") or {})
    campaign_id = str(manifest.get("campaign_id") or "longmont-c2")
    session_id = str(manifest.get("session_id") or "session-24")

    def _digest(path: Path) -> str:
        return hashlib.sha256(path.read_bytes()).hexdigest()

    packaged_recap_uri = source.get("normalized_recap_path") or (
        (artifacts.get("normalized_recap") or {}).get("uri")
    )
    assert isinstance(packaged_recap_uri, str) and packaged_recap_uri.strip()
    packaged_recap_path = tmp_path / packaged_recap_uri
    assert packaged_recap_path.is_file()

    artifact = create_recap_source_artifact(
        tmp_path,
        campaign_id=campaign_id,
        session_id=session_id,
        recap_path=packaged_recap_path,
    )
    if source_artifact_id is not None:
        assert artifact.source_artifact_id == source_artifact_id
    resolved_artifact_id = artifact.source_artifact_id
    immutable_path = tmp_path / artifact.uri.removeprefix("repo://")
    packaged_recap_path.write_text(immutable_path.read_text(encoding="utf-8"), encoding="utf-8")
    packaged_source_digest = _digest(packaged_recap_path)
    source["source_artifact_id"] = resolved_artifact_id
    source["normalized_recap_sha256"] = f"sha256:{packaged_source_digest}"
    manifest["source"] = source
    if "normalized_recap" in artifacts:
        artifacts["normalized_recap"] = {
            **artifacts["normalized_recap"],
            "sha256": f"sha256:{packaged_source_digest}",
        }

    span_payload = source_span_index_to_dict(
        load_source_span_index(tmp_path, resolved_artifact_id)
    )
    span_ref = dict(artifacts.get("source_span_index") or {})
    span_uri = span_ref.get("uri")
    assert isinstance(span_uri, str)
    span_path = tmp_path / span_uri
    span_path.write_text(
        json.dumps(span_payload, indent=2, sort_keys=True) + "\n", encoding="utf-8"
    )
    span_digest = _digest(span_path)
    artifacts["source_span_index"] = {
        **span_ref,
        "schema": "dmb_source_span_index_v1",
        "sha256": f"sha256:{span_digest}",
    }

    candidate_ref = dict(artifacts.get("candidate_graph") or {})
    candidate_uri = candidate_ref.get("uri")
    assert isinstance(candidate_uri, str)
    candidate_path = tmp_path / candidate_uri
    graph = json.loads(candidate_path.read_text(encoding="utf-8"))
    graph["source_artifact_ids"] = [resolved_artifact_id]
    candidate_path.write_text(
        json.dumps(graph, indent=2, sort_keys=True) + "\n", encoding="utf-8"
    )
    candidate_digest = _digest(candidate_path)
    artifacts["candidate_graph"] = {
        **candidate_ref,
        "sha256": f"sha256:{candidate_digest}",
    }

    known_ref = dict(artifacts.get("known_entity_mentions") or {})
    known_uri = known_ref.get("uri")
    if isinstance(known_uri, str) and known_uri.strip():
        known_path = tmp_path / known_uri
        if known_path.is_file():
            artifacts["known_entity_mentions"] = {
                **known_ref,
                "schema": known_ref.get("schema") or "dmb_known_entity_mention_sidecar_v0",
                "sha256": f"sha256:{_digest(known_path)}",
                "exists": True,
                "preview_only": True,
            }

    provenance_uri = source.get("provenance_index_uri")
    if isinstance(provenance_uri, str) and provenance_uri.strip():
        provenance_path = tmp_path / provenance_uri
        provenance = {
            "schema": "dmb_source_provenance_index_v0",
            "version": "0.1",
            "campaign_id": campaign_id,
            "session_id": session_id,
            "source_artifacts": [
                {
                    "artifact_id": resolved_artifact_id,
                    "uri": packaged_recap_uri,
                    "sha256": f"sha256:{packaged_source_digest}",
                    "preview_only": True,
                }
            ],
        }
        provenance_path.write_text(
            json.dumps(provenance, indent=2, sort_keys=True) + "\n", encoding="utf-8"
        )

    run_id = f"er_bound_{candidate_digest[:12]}"
    now = datetime.now(UTC).isoformat().replace("+00:00", "Z")
    run = ExtractionRun(
        run_id=run_id,
        source_artifact_id=resolved_artifact_id,
        source_domain="recap",
        status=ExtractionRunStatus.REVIEWABLE,
        campaign_id=campaign_id,
        session_id=session_id,
        created_at=now,
        updated_at=now,
        components={
            ExtractionRunComponentKind.SOURCE_ARTIFACT.value: ExtractionRunComponentRef(
                kind=ExtractionRunComponentKind.SOURCE_ARTIFACT,
                uri=artifact.uri,
                sha256=artifact.content_sha256 or "",
                exists=True,
            ),
            ExtractionRunComponentKind.SOURCE_SPAN_INDEX.value: ExtractionRunComponentRef(
                kind=ExtractionRunComponentKind.SOURCE_SPAN_INDEX,
                uri=f"repo://{span_path.relative_to(tmp_path).as_posix()}",
                sha256=span_digest,
                exists=True,
            ),
            ExtractionRunComponentKind.CANDIDATE_GRAPH.value: ExtractionRunComponentRef(
                kind=ExtractionRunComponentKind.CANDIDATE_GRAPH,
                uri=f"repo://{candidate_path.relative_to(tmp_path).as_posix()}",
                sha256=candidate_digest,
                exists=True,
            ),
        },
    )
    path = extraction_runs_path(tmp_path)
    if path.is_file():
        document = ExtractionRunRegistryDocument.model_validate(
            json.loads(path.read_text(encoding="utf-8"))
        )
    else:
        document = ExtractionRunRegistryDocument()
    document.records.append(run)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps(document.model_dump(mode="json"), indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )

    diagnostics = dict(manifest.get("diagnostics") or {})
    diagnostics["extraction_run_id"] = run_id
    diagnostics["extraction_run_status"] = ExtractionRunStatus.REVIEWABLE.value
    diagnostics["source_artifact_id"] = resolved_artifact_id
    manifest["diagnostics"] = diagnostics
    manifest["artifacts"] = artifacts
    result.manifest_path.write_text(
        json.dumps(manifest, indent=2, sort_keys=True) + "\n", encoding="utf-8"
    )
    return run_id


def _stamp_production_lineage(
    tmp_path: Path,
    result,
    *,
    source_artifact_id: str = "artifact:test:stamped-lineage:recap",
) -> None:
    """Fabricate lineage metadata only — must NOT satisfy the reuse gate."""
    manifest = json.loads(result.manifest_path.read_text(encoding="utf-8"))
    diagnostics = dict(manifest.get("diagnostics") or {})
    diagnostics["extraction_run_id"] = "er_stamped_lineage"
    diagnostics["extraction_run_status"] = "reviewable"
    diagnostics["source_artifact_id"] = source_artifact_id
    manifest["diagnostics"] = diagnostics
    artifacts = manifest.get("artifacts") or {}
    candidate_ref = artifacts.get("candidate_graph") or {}
    uri = candidate_ref.get("uri")
    assert isinstance(uri, str)
    candidate_path = tmp_path / uri
    graph = json.loads(candidate_path.read_text(encoding="utf-8"))
    graph["source_artifact_ids"] = [source_artifact_id]
    candidate_path.write_text(
        json.dumps(graph, indent=2, sort_keys=True) + "\n", encoding="utf-8"
    )
    result.manifest_path.write_text(
        json.dumps(manifest, indent=2, sort_keys=True) + "\n", encoding="utf-8"
    )


def _profiled_candidate_ready_run(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    output_dir: str,
    *,
    graph_extraction_profile: str | None = None,
):
    from apps.live_control_server.services.source_artifact_registry import (
        create_recap_source_artifact,
        load_source_span_index,
    )
    from src.graph_memory.source_span import source_span_index_to_dict

    monkeypatch.chdir(tmp_path)
    source = tmp_path / f"{output_dir.replace('/', '_')}_recap.md"
    candidate = tmp_path / f"{output_dir.replace('/', '_')}_candidate.json"
    source.write_text(RECAP_PATH.read_text(encoding="utf-8"), encoding="utf-8")
    candidate.write_text(CANDIDATE_PATH.read_text(encoding="utf-8"), encoding="utf-8")
    artifact = create_recap_source_artifact(
        tmp_path,
        campaign_id="longmont-c2",
        session_id="session-24",
        recap_path=source,
    )
    span_payload = source_span_index_to_dict(
        load_source_span_index(tmp_path, artifact.source_artifact_id)
    )
    graph = json.loads(candidate.read_text(encoding="utf-8"))
    graph["source_artifact_ids"] = [artifact.source_artifact_id]
    candidate.write_text(json.dumps(graph, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    result = run_graph_preview_extraction(
        GraphPreviewRunnerOptions(
            campaign_id="longmont-c2",
            session_id="session-24",
            normalized_recap_path=source,
            output_dir=Path(output_dir),
            candidate_graph_path=candidate,
            graph_extraction_profile=graph_extraction_profile,
            input_path_record=source.relative_to(tmp_path).as_posix(),
            source_span_index=span_payload,
            source_artifact_id=artifact.source_artifact_id,
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
    _bind_production_lineage(tmp_path, old_result)
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


def test_build_recap_graph_preview_bundle_skips_pre_migration_run_missing_extraction_lineage(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Candidate-ready legacy runs without ExtractionRun lineage must rebuild."""
    old_result, source = _profiled_candidate_ready_run(
        tmp_path,
        monkeypatch,
        "out/graph_memory/runs/pre_migration_no_lineage",
        graph_extraction_profile="category_encounter_job_preview",
    )
    ingest_service, calls = _service_fake_runner_with_candidate(tmp_path, monkeypatch)

    assert not ingest_service._manifest_has_production_lineage(
        tmp_path, old_result.manifest_path.relative_to(tmp_path).as_posix()
    )

    status = ingest_service.build_recap_graph_preview_bundle(
        repo_root=tmp_path,
        campaign_id="longmont-c2",
        session=24,
        normalized_recap_path=str(source),
        extract_graph=True,
        graph_extraction_profile="category_encounter_job_preview",
    )

    assert calls
    assert (
        status["manifest_path"]
        != old_result.manifest_path.relative_to(tmp_path).as_posix()
    )
    assert status["status"] == GraphIngestRunStatus.CANDIDATE_VALIDATION_READY.value
    assert status["extraction_run_status"] == "reviewable"
    assert ingest_service._manifest_has_production_lineage(
        tmp_path, status["manifest_path"]
    )


def test_build_recap_graph_preview_bundle_skips_fabricated_production_lineage(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Self-asserted manifest lineage without an ExtractionRun registry record must rebuild."""
    old_result, source = _profiled_candidate_ready_run(
        tmp_path,
        monkeypatch,
        "out/graph_memory/runs/fabricated_lineage",
        graph_extraction_profile="category_encounter_job_preview",
    )
    _stamp_production_lineage(tmp_path, old_result)
    ingest_service, calls = _service_fake_runner_with_candidate(tmp_path, monkeypatch)

    assert not ingest_service._manifest_has_production_lineage(
        tmp_path, old_result.manifest_path.relative_to(tmp_path).as_posix()
    )

    status = ingest_service.build_recap_graph_preview_bundle(
        repo_root=tmp_path,
        campaign_id="longmont-c2",
        session=24,
        normalized_recap_path=str(source),
        extract_graph=True,
        graph_extraction_profile="category_encounter_job_preview",
    )

    assert calls
    assert (
        status["manifest_path"]
        != old_result.manifest_path.relative_to(tmp_path).as_posix()
    )
    assert ingest_service._manifest_has_production_lineage(
        tmp_path, status["manifest_path"]
    )


def test_manifest_production_lineage_refuses_deleted_source_snapshot(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Reuse must fail when the immutable SourceArtifact snapshot is deleted."""
    old_result, source = _profiled_candidate_ready_run(
        tmp_path,
        monkeypatch,
        "out/graph_memory/runs/deleted_source_snapshot",
        graph_extraction_profile="category_encounter_job_preview",
    )
    _bind_production_lineage(tmp_path, old_result)
    ingest_service, _calls = _service_fake_runner_with_candidate(tmp_path, monkeypatch)
    manifest_rel = old_result.manifest_path.relative_to(tmp_path).as_posix()
    assert ingest_service._manifest_has_production_lineage(tmp_path, manifest_rel)

    from apps.live_control_server.services.source_artifact_registry import (
        get_source_artifact,
    )

    manifest = json.loads(old_result.manifest_path.read_text(encoding="utf-8"))
    artifact_id = manifest["diagnostics"]["source_artifact_id"]
    artifact = get_source_artifact(tmp_path, artifact_id)
    snapshot = tmp_path / artifact.uri.removeprefix("repo://")
    assert snapshot.is_file()
    snapshot.unlink()

    assert not ingest_service._manifest_has_production_lineage(tmp_path, manifest_rel)


def test_manifest_production_lineage_refuses_mutated_source_snapshot(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Reuse must fail when the immutable SourceArtifact snapshot bytes change."""
    old_result, source = _profiled_candidate_ready_run(
        tmp_path,
        monkeypatch,
        "out/graph_memory/runs/mutated_source_snapshot",
        graph_extraction_profile="category_encounter_job_preview",
    )
    _bind_production_lineage(tmp_path, old_result)
    ingest_service, _calls = _service_fake_runner_with_candidate(tmp_path, monkeypatch)
    manifest_rel = old_result.manifest_path.relative_to(tmp_path).as_posix()
    assert ingest_service._manifest_has_production_lineage(tmp_path, manifest_rel)

    from apps.live_control_server.services.source_artifact_registry import (
        get_source_artifact,
    )

    manifest = json.loads(old_result.manifest_path.read_text(encoding="utf-8"))
    artifact_id = manifest["diagnostics"]["source_artifact_id"]
    artifact = get_source_artifact(tmp_path, artifact_id)
    snapshot = tmp_path / artifact.uri.removeprefix("repo://")
    snapshot.write_text(snapshot.read_text(encoding="utf-8") + "MUTATED\n", encoding="utf-8")

    assert not ingest_service._manifest_has_production_lineage(tmp_path, manifest_rel)


def test_manifest_production_lineage_refuses_missing_span_artifact_entry(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Missing GraphIngest SourceSpanIndex artifact must fail closed, not skip digest checks."""
    old_result, source = _profiled_candidate_ready_run(
        tmp_path,
        monkeypatch,
        "out/graph_memory/runs/missing_span_artifact",
        graph_extraction_profile="category_encounter_job_preview",
    )
    _bind_production_lineage(tmp_path, old_result)
    ingest_service, _calls = _service_fake_runner_with_candidate(tmp_path, monkeypatch)
    manifest_rel = old_result.manifest_path.relative_to(tmp_path).as_posix()
    assert ingest_service._manifest_has_production_lineage(tmp_path, manifest_rel)

    manifest = json.loads(old_result.manifest_path.read_text(encoding="utf-8"))
    artifacts = dict(manifest.get("artifacts") or {})
    artifacts.pop("source_span_index", None)
    manifest["artifacts"] = artifacts
    # Corrupt the projection URI target after removing the artifact entry.
    span_uri = (manifest.get("source") or {}).get("source_span_index_uri")
    if isinstance(span_uri, str) and span_uri.strip():
        span_path = tmp_path / span_uri
        if span_path.is_file():
            span_path.write_text('{"schema":"tampered"}\n', encoding="utf-8")
    old_result.manifest_path.write_text(
        json.dumps(manifest, indent=2, sort_keys=True) + "\n", encoding="utf-8"
    )

    assert not ingest_service._manifest_has_production_lineage(tmp_path, manifest_rel)


def test_build_recap_graph_preview_bundle_packages_immutable_source_bytes(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Packaging must copy registered SourceArtifact bytes, not the mutable caller path."""
    import hashlib

    from apps.live_control_server.services.source_artifact_registry import (
        get_source_artifact,
    )

    monkeypatch.chdir(tmp_path)
    source = tmp_path / "mutable_normalized.md"
    # Multiple trailing newlines: admission normalizes; packaging must still use registry bytes.
    source.write_text(
        RECAP_PATH.read_text(encoding="utf-8").rstrip("\n") + "\n\n\n",
        encoding="utf-8",
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
    packaging_path = calls[0].normalized_recap_path
    assert packaging_path != source.resolve()
    artifact = get_source_artifact(tmp_path, status["source_artifact_id"])
    immutable = tmp_path / artifact.uri.removeprefix("repo://")
    assert packaging_path.resolve() == immutable.resolve()

    # Mutate the original caller path after production — packaged bytes must stay A.
    source.write_text(source.read_text(encoding="utf-8") + "POST_EXTRACT_MUTATION\n", encoding="utf-8")

    run_dir = tmp_path / status["run_dir"]
    packaged = run_dir / "normalized_recap_source.md"
    span_index = json.loads((run_dir / "source_span_index.json").read_text(encoding="utf-8"))
    provenance = json.loads((run_dir / "provenance_index.json").read_text(encoding="utf-8"))
    manifest = json.loads((tmp_path / status["manifest_path"]).read_text(encoding="utf-8"))

    registered_bytes = immutable.read_bytes()
    packaged_bytes = packaged.read_bytes()
    assert packaged_bytes == registered_bytes
    assert b"POST_EXTRACT_MUTATION" not in packaged_bytes
    digest = hashlib.sha256(packaged_bytes).hexdigest()
    assert digest == artifact.content_sha256
    assert digest == span_index["content_sha256"]
    assert digest == hashlib.sha256(
        packaging_path.read_bytes()
    ).hexdigest()
    assert manifest["source"]["normalized_recap_sha256"].removeprefix("sha256:") == digest
    assert all(
        str(row.get("sha256") or "").removeprefix("sha256:") == digest
        for row in provenance.get("source_artifacts") or []
        if isinstance(row, dict)
    )


def _assert_packaged_from_immutable_source(
    *,
    tmp_path: Path,
    source: Path,
    calls: list,
    status: dict,
) -> None:
    from apps.live_control_server.services.source_artifact_registry import (
        get_source_artifact,
    )

    assert calls
    packaging_path = Path(calls[0].normalized_recap_path)
    assert packaging_path.resolve() != source.resolve()
    artifact = get_source_artifact(tmp_path, status["source_artifact_id"])
    immutable = tmp_path / artifact.uri.removeprefix("repo://")
    assert packaging_path.resolve() == immutable.resolve()
    packaged = (tmp_path / status["run_dir"] / "normalized_recap_source.md").read_bytes()
    assert packaged == immutable.read_bytes()
    span_index = json.loads(
        (tmp_path / status["run_dir"] / "source_span_index.json").read_text(encoding="utf-8")
    )
    assert span_index["content_sha256"] == artifact.content_sha256


@pytest.mark.parametrize(
    ("extract_graph", "with_manual_candidate", "failure_kind", "expected_status"),
    [
        (False, False, None, GraphIngestRunStatus.SOURCE_SPAN_BUNDLE_READY.value),
        (False, True, None, GraphIngestRunStatus.CANDIDATE_VALIDATION_READY.value),
        (True, False, "refusal", GraphIngestRunStatus.SOURCE_SPAN_BUNDLE_READY.value),
        (True, False, "validation", GraphIngestRunStatus.SOURCE_SPAN_BUNDLE_READY.value),
    ],
)
def test_build_recap_graph_preview_bundle_packages_immutable_source_when_not_reviewable(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    extract_graph: bool,
    with_manual_candidate: bool,
    failure_kind: str | None,
    expected_status: str,
) -> None:
    """Newline-normalized packaging must use SourceArtifact bytes even without a reviewable candidate."""
    monkeypatch.chdir(tmp_path)
    source = tmp_path / "newline_normalized.md"
    source.write_text(
        RECAP_PATH.read_text(encoding="utf-8").rstrip("\n") + "\n\n\n",
        encoding="utf-8",
    )
    ingest_service, calls = _service_fake_runner_with_candidate(
        tmp_path, monkeypatch, failure_kind=failure_kind
    )
    manual_candidate = None
    if with_manual_candidate:
        manual_candidate = tmp_path / "manual_candidate.json"
        manual_candidate.write_text(
            CANDIDATE_PATH.read_text(encoding="utf-8"), encoding="utf-8"
        )

    status = ingest_service.build_recap_graph_preview_bundle(
        repo_root=tmp_path,
        campaign_id="longmont-c2",
        session=24,
        normalized_recap_path=str(source),
        extract_graph=extract_graph,
        force_graph_run=True,
        candidate_graph_path=(
            manual_candidate.relative_to(tmp_path).as_posix()
            if manual_candidate is not None
            else None
        ),
        graph_extraction_profile="category_encounter_job_preview",
    )

    assert status["status"] == expected_status
    if failure_kind is not None:
        assert status["extraction_mode"] == "llm_blocked"
    _assert_packaged_from_immutable_source(
        tmp_path=tmp_path, source=source, calls=calls, status=status
    )


def test_build_recap_graph_preview_bundle_rejects_reuse_when_recap_content_changes(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Edited bytes at the same path must not reuse a prior GraphIngest run."""
    old_result, source = _profiled_candidate_ready_run(
        tmp_path,
        monkeypatch,
        "out/graph_memory/runs/changed_recap_reuse",
        graph_extraction_profile="category_encounter_job_preview",
    )
    _bind_production_lineage(tmp_path, old_result)
    ingest_service, calls = _service_fake_runner_with_candidate(tmp_path, monkeypatch)

    reused = ingest_service.build_recap_graph_preview_bundle(
        repo_root=tmp_path,
        campaign_id="longmont-c2",
        session=24,
        normalized_recap_path=str(source),
        extract_graph=True,
        force_graph_run=False,
        graph_extraction_profile="category_encounter_job_preview",
    )
    assert calls == []
    assert (
        reused["manifest_path"]
        == old_result.manifest_path.relative_to(tmp_path).as_posix()
    )

    source.write_text(
        source.read_text(encoding="utf-8") + "\nEdited into recap B.\n",
        encoding="utf-8",
    )
    rebuilt = ingest_service.build_recap_graph_preview_bundle(
        repo_root=tmp_path,
        campaign_id="longmont-c2",
        session=24,
        normalized_recap_path=str(source),
        extract_graph=True,
        force_graph_run=False,
        graph_extraction_profile="category_encounter_job_preview",
    )
    assert calls
    assert (
        rebuilt["manifest_path"]
        != old_result.manifest_path.relative_to(tmp_path).as_posix()
    )


def test_manifest_production_lineage_refuses_missing_projection_span_uri(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Missing source.source_span_index_uri must fail closed even when artifacts entry is intact."""
    old_result, source = _profiled_candidate_ready_run(
        tmp_path,
        monkeypatch,
        "out/graph_memory/runs/missing_projection_span_uri",
        graph_extraction_profile="category_encounter_job_preview",
    )
    _bind_production_lineage(tmp_path, old_result)
    ingest_service, _calls = _service_fake_runner_with_candidate(tmp_path, monkeypatch)
    manifest_rel = old_result.manifest_path.relative_to(tmp_path).as_posix()
    assert ingest_service._manifest_has_production_lineage(tmp_path, manifest_rel)

    manifest = json.loads(old_result.manifest_path.read_text(encoding="utf-8"))
    source_block = dict(manifest.get("source") or {})
    source_block.pop("source_span_index_uri", None)
    manifest["source"] = source_block
    old_result.manifest_path.write_text(
        json.dumps(manifest, indent=2, sort_keys=True) + "\n", encoding="utf-8"
    )

    assert not ingest_service._manifest_has_production_lineage(tmp_path, manifest_rel)
    assert "source_span_index" in (manifest.get("artifacts") or {})


@pytest.mark.parametrize(
    "corrupt",
    [
        pytest.param(lambda p: p.write_text("", encoding="utf-8"), id="empty"),
        pytest.param(lambda p: p.write_text("   \n\t\n", encoding="utf-8"), id="whitespace"),
        pytest.param(lambda p: p.write_bytes(b"\xff\xfe invalid utf-8"), id="invalid-utf8"),
    ],
)
def test_build_and_inspect_refuse_reuse_when_current_recap_cannot_digest(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    corrupt,
) -> None:
    """Existing-but-invalid recap bytes must not path-match a prior run."""
    from apps.live_control_server.services.source_artifact_registry import (
        SourceArtifactRegistryError,
    )

    old_result, source = _profiled_candidate_ready_run(
        tmp_path,
        monkeypatch,
        "out/graph_memory/runs/invalid_current_recap",
        graph_extraction_profile="category_encounter_job_preview",
    )
    _bind_production_lineage(tmp_path, old_result)
    ingest_service, calls = _service_fake_runner_with_candidate(tmp_path, monkeypatch)
    old_manifest = old_result.manifest_path.relative_to(tmp_path).as_posix()

    reused = ingest_service.build_recap_graph_preview_bundle(
        repo_root=tmp_path,
        campaign_id="longmont-c2",
        session=24,
        normalized_recap_path=str(source),
        extract_graph=True,
        force_graph_run=False,
        graph_extraction_profile="category_encounter_job_preview",
    )
    assert calls == []
    assert reused["manifest_path"] == old_manifest

    corrupt(source)

    inspected = ingest_service.inspect_recap_graph_preview_status(
        repo_root=tmp_path,
        campaign_id="longmont-c2",
        session=24,
        normalized_recap_path=str(source),
    )
    assert inspected.get("manifest_path") != old_manifest

    with pytest.raises((ValueError, SourceArtifactRegistryError, OSError, UnicodeDecodeError)):
        ingest_service.build_recap_graph_preview_bundle(
            repo_root=tmp_path,
            campaign_id="longmont-c2",
            session=24,
            normalized_recap_path=str(source),
            extract_graph=True,
            force_graph_run=False,
            graph_extraction_profile="category_encounter_job_preview",
        )
    # Build must not silently reuse the prior run for the invalid current source.
    assert all(
        getattr(call, "input_path_record", None) != old_manifest for call in calls
    )


def test_manual_candidate_materialization_requires_projection_span_uri(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """extract_graph=False materialization must still require usable SourceSpanIndex linkage."""
    old_result, source = _profiled_candidate_ready_run(
        tmp_path,
        monkeypatch,
        "out/graph_memory/runs/manual_missing_span_uri",
        graph_extraction_profile="category_encounter_job_preview",
    )
    ingest_service, _calls = _service_fake_runner_with_candidate(tmp_path, monkeypatch)
    manifest_rel = old_result.manifest_path.relative_to(tmp_path).as_posix()
    assert ingest_service._manifest_has_known_entity_mentions(tmp_path, manifest_rel)
    assert ingest_service._manifest_has_usable_source_span_linkage(tmp_path, manifest_rel)
    assert ingest_service._manifest_is_manual_candidate_reusable(tmp_path, manifest_rel)

    manifest = json.loads(old_result.manifest_path.read_text(encoding="utf-8"))
    source_block = dict(manifest.get("source") or {})
    source_block.pop("source_span_index_uri", None)
    manifest["source"] = source_block
    old_result.manifest_path.write_text(
        json.dumps(manifest, indent=2, sort_keys=True) + "\n", encoding="utf-8"
    )
    assert not ingest_service._manifest_has_usable_source_span_linkage(tmp_path, manifest_rel)
    assert not ingest_service._manifest_is_manual_candidate_reusable(tmp_path, manifest_rel)

    status = ingest_service.materialize_recap_preview_supergraph(
        repo_root=tmp_path,
        campaign_id="longmont-c2",
        session=24,
        normalized_recap_path=str(source),
        manifest_path=manifest_rel,
        extract_graph=False,
        force_graph_run=False,
    )
    assert status["status"] == GraphIngestRunStatus.CANDIDATE_VALIDATION_READY.value
    assert "SourceSpanIndex" in (status.get("blocked_reason") or "")
    assert status.get("preview_union_store_path") is None


def test_usable_source_span_linkage_rejects_empty_or_foreign_index(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Malformed or foreign SourceSpanIndex files must not pass the shared gate."""
    import hashlib

    from graph_memory.ingestion.graph_ingest_validate import (
        validate_manifest_source_span_index_linkage,
    )

    old_result, source = _profiled_candidate_ready_run(
        tmp_path,
        monkeypatch,
        "out/graph_memory/runs/malformed_span_index",
        graph_extraction_profile="category_encounter_job_preview",
    )
    ingest_service, _calls = _service_fake_runner_with_candidate(tmp_path, monkeypatch)
    manifest_rel = old_result.manifest_path.relative_to(tmp_path).as_posix()
    assert ingest_service._manifest_has_usable_source_span_linkage(tmp_path, manifest_rel)

    manifest = json.loads(old_result.manifest_path.read_text(encoding="utf-8"))
    span_uri = manifest["artifacts"]["source_span_index"]["uri"]
    span_path = tmp_path / span_uri
    span_path.write_text("{}\n", encoding="utf-8")
    digest = hashlib.sha256(span_path.read_bytes()).hexdigest()
    manifest["artifacts"]["source_span_index"]["sha256"] = f"sha256:{digest}"
    old_result.manifest_path.write_text(
        json.dumps(manifest, indent=2, sort_keys=True) + "\n", encoding="utf-8"
    )
    assert validate_manifest_source_span_index_linkage(tmp_path, manifest)
    assert not ingest_service._manifest_has_usable_source_span_linkage(tmp_path, manifest_rel)

    status = ingest_service.materialize_recap_preview_supergraph(
        repo_root=tmp_path,
        campaign_id="longmont-c2",
        session=24,
        normalized_recap_path=str(source),
        manifest_path=manifest_rel,
        extract_graph=False,
        force_graph_run=False,
    )
    assert status.get("preview_union_store_path") is None
    assert "SourceSpanIndex" in (status.get("blocked_reason") or "")


def test_known_entity_sidecar_digest_invalidates_cached_projection(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Projection rebuild must reject digest-mismatched caches before restamping.

    Uses the real projection builder (no monkeypatch of the payload builder) and
    asserts chips/content reflect the new sidecar, not merely dependency metadata.
    """
    import hashlib

    import apps.live_control_server.services.recap_graph_preview_ingest as ingest_service

    old_result, _source = _profiled_candidate_ready_run(
        tmp_path,
        monkeypatch,
        "out/graph_memory/runs/known_entity_digest_projection",
        graph_extraction_profile="category_encounter_job_preview",
    )
    monkeypatch.setattr(
        "apps.live_control_server.services.union_supergraph_projection_adapter.repo_root",
        lambda: tmp_path,
    )
    materialize_preview_union_store_from_graph_ingest_run(
        PreviewUnionMaterializeOptions(
            manifest_path=old_result.manifest_path,
            repo_root=tmp_path,
        )
    )
    manifest_rel = old_result.manifest_path.relative_to(tmp_path).as_posix()
    manifest = json.loads(old_result.manifest_path.read_text(encoding="utf-8"))
    known_uri = manifest["artifacts"]["known_entity_mentions"]["uri"]
    known_path = tmp_path / known_uri
    span_uri = manifest["artifacts"]["source_span_index"]["uri"]
    span_index = json.loads((tmp_path / span_uri).read_text(encoding="utf-8"))
    body_span = next(
        span
        for span in span_index["spans"]
        if int(span["start_line"]) <= 3 and int(span["end_line"]) >= 4
    )
    span_ref = body_span["source_span_id"]
    recap_path = tmp_path / manifest["source"]["normalized_recap_path"]
    recap_lines = recap_path.read_text(encoding="utf-8").splitlines()
    paragraph = "\n".join(
        recap_lines[int(body_span["start_line"]) - 1 : int(body_span["end_line"])]
    )

    def _write_sidecar(*, surface: str, digest_into_manifest: bool = True) -> str:
        start = paragraph.index(surface)
        end = start + len(surface)
        sidecar = {
            "schema": "dmb_known_entity_mention_sidecar_v0",
            "version": "0.1",
            "campaign_id": "longmont-c2",
            "session_id": "session-24",
            "mentions": [
                {
                    "source_span_ref_id": span_ref,
                    "start_offset": start,
                    "end_offset": end,
                    "surface_text": surface,
                    "canonical_entity_id": "character_mira",
                    "entity_slug": "mira",
                    "entity_kind": "pc",
                    "match_method": "canonical",
                    "display_name": surface,
                }
            ],
            "ambiguous_surfaces": [],
            "diagnostics": {"surface": surface},
        }
        known_path.write_text(
            json.dumps(sidecar, indent=2, sort_keys=True) + "\n", encoding="utf-8"
        )
        digest = hashlib.sha256(known_path.read_bytes()).hexdigest()
        if digest_into_manifest:
            payload = json.loads(old_result.manifest_path.read_text(encoding="utf-8"))
            payload["artifacts"]["known_entity_mentions"]["sha256"] = f"sha256:{digest}"
            old_result.manifest_path.write_text(
                json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8"
            )
        return digest

    digest_s1 = _write_sidecar(surface="Mira")
    projection_s1 = ingest_service.ensure_graph_ingest_projection_payload(
        repo_root=tmp_path,
        manifest_path=manifest_rel,
        session_id="session-24",
    )
    assert projection_s1 is not None
    payload_s1 = json.loads(projection_s1.read_text(encoding="utf-8"))
    assert payload_s1.get("known_entity_mentions_sha256") == f"sha256:{digest_s1}"
    labels_s1 = {row.get("label") for row in payload_s1.get("mentions") or []}
    assert "Mira" in labels_s1
    assert "Longmont" not in labels_s1

    digest_s2 = _write_sidecar(surface="Longmont")
    assert digest_s2 != digest_s1
    projection_s2 = ingest_service.ensure_graph_ingest_projection_payload(
        repo_root=tmp_path,
        manifest_path=manifest_rel,
        session_id="session-24",
    )
    assert projection_s2 is not None
    payload_s2 = json.loads(projection_s2.read_text(encoding="utf-8"))
    assert payload_s2.get("known_entity_mentions_sha256") == f"sha256:{digest_s2}"
    labels_s2 = {row.get("label") for row in payload_s2.get("mentions") or []}
    assert "Longmont" in labels_s2
    assert "Mira" not in labels_s2


def test_empty_object_known_entity_sidecar_fails_validation(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Raw ``{}`` must not coerce into a valid empty known-entity contract."""
    import hashlib

    from graph_memory.ingestion.graph_ingest_validate import (
        validate_manifest_known_entity_mentions,
    )

    old_result, _source = _profiled_candidate_ready_run(
        tmp_path,
        monkeypatch,
        "out/graph_memory/runs/empty_known_entity_object",
        graph_extraction_profile="category_encounter_job_preview",
    )
    ingest_service, _calls = _service_fake_runner_with_candidate(tmp_path, monkeypatch)
    manifest_rel = old_result.manifest_path.relative_to(tmp_path).as_posix()
    manifest = json.loads(old_result.manifest_path.read_text(encoding="utf-8"))
    known_uri = manifest["artifacts"]["known_entity_mentions"]["uri"]
    known_path = tmp_path / known_uri
    known_path.write_text("{}\n", encoding="utf-8")
    digest = hashlib.sha256(known_path.read_bytes()).hexdigest()
    manifest["artifacts"]["known_entity_mentions"]["sha256"] = f"sha256:{digest}"
    old_result.manifest_path.write_text(
        json.dumps(manifest, indent=2, sort_keys=True) + "\n", encoding="utf-8"
    )

    errors = validate_manifest_known_entity_mentions(tmp_path, manifest)
    assert errors
    assert any("schema" in error for error in errors)
    assert not ingest_service._manifest_has_known_entity_mentions(tmp_path, manifest_rel)


def test_declared_sidecar_digest_mismatch_blocks_projection_rebuild(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Changing sidecar bytes without updating the manifest digest must fail closed."""
    import apps.live_control_server.services.recap_graph_preview_ingest as ingest_service

    old_result, _source = _profiled_candidate_ready_run(
        tmp_path,
        monkeypatch,
        "out/graph_memory/runs/sidecar_digest_mismatch_blocks",
        graph_extraction_profile="category_encounter_job_preview",
    )
    monkeypatch.setattr(
        "apps.live_control_server.services.union_supergraph_projection_adapter.repo_root",
        lambda: tmp_path,
    )
    materialize_preview_union_store_from_graph_ingest_run(
        PreviewUnionMaterializeOptions(
            manifest_path=old_result.manifest_path,
            repo_root=tmp_path,
        )
    )
    manifest_rel = old_result.manifest_path.relative_to(tmp_path).as_posix()
    first = ingest_service.ensure_graph_ingest_projection_payload(
        repo_root=tmp_path,
        manifest_path=manifest_rel,
        session_id="session-24",
    )
    assert first is not None

    manifest = json.loads(old_result.manifest_path.read_text(encoding="utf-8"))
    known_path = tmp_path / manifest["artifacts"]["known_entity_mentions"]["uri"]
    claimed = manifest["artifacts"]["known_entity_mentions"]["sha256"]
    mutated = json.loads(known_path.read_text(encoding="utf-8"))
    mutated["diagnostics"] = {**(mutated.get("diagnostics") or {}), "mutated": "S2"}
    known_path.write_text(
        json.dumps(mutated, indent=2, sort_keys=True) + "\n", encoding="utf-8"
    )
    # Leave manifest digest pointing at S1.
    assert claimed == json.loads(old_result.manifest_path.read_text(encoding="utf-8"))[
        "artifacts"
    ]["known_entity_mentions"]["sha256"]

    with pytest.raises(ValueError, match="known_entity_mentions unusable|sha256"):
        ingest_service.ensure_graph_ingest_projection_payload(
            repo_root=tmp_path,
            manifest_path=manifest_rel,
            session_id="session-24",
        )


def test_projection_payload_sha_mismatch_rejects_cache_reuse(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """artifacts.projection_payload.sha256 must bind actual projection file bytes."""
    import hashlib

    import apps.live_control_server.services.recap_graph_preview_ingest as ingest_service

    old_result, _source = _profiled_candidate_ready_run(
        tmp_path,
        monkeypatch,
        "out/graph_memory/runs/projection_sha_mismatch",
        graph_extraction_profile="category_encounter_job_preview",
    )
    monkeypatch.setattr(
        "apps.live_control_server.services.union_supergraph_projection_adapter.repo_root",
        lambda: tmp_path,
    )
    materialize_preview_union_store_from_graph_ingest_run(
        PreviewUnionMaterializeOptions(
            manifest_path=old_result.manifest_path,
            repo_root=tmp_path,
        )
    )
    manifest_rel = old_result.manifest_path.relative_to(tmp_path).as_posix()
    projection_path = ingest_service.ensure_graph_ingest_projection_payload(
        repo_root=tmp_path,
        manifest_path=manifest_rel,
        session_id="session-24",
    )
    assert projection_path is not None
    original = json.loads(projection_path.read_text(encoding="utf-8"))
    embedded_sidecar = original.get("known_entity_mentions_sha256")
    mutated = {
        **original,
        "mentions": [{"mention_id": "mutated", "node_id": "x", "label": "MUTATED_CACHE"}],
    }
    projection_path.write_text(
        json.dumps(mutated, indent=2, sort_keys=True) + "\n", encoding="utf-8"
    )
    # Preserve stale manifest SHA and embedded sidecar digest claim.
    manifest = json.loads(old_result.manifest_path.read_text(encoding="utf-8"))
    assert manifest["artifacts"]["projection_payload"]["sha256"]
    assert embedded_sidecar
    assert (
        hashlib.sha256(projection_path.read_bytes()).hexdigest()
        != manifest["artifacts"]["projection_payload"]["sha256"].removeprefix("sha256:")
    )

    rebuilt = ingest_service.ensure_graph_ingest_projection_payload(
        repo_root=tmp_path,
        manifest_path=manifest_rel,
        session_id="session-24",
    )
    assert rebuilt is not None
    after = json.loads(rebuilt.read_text(encoding="utf-8"))
    labels = {row.get("label") for row in after.get("mentions") or []}
    assert "MUTATED_CACHE" not in labels


def test_mutated_recap_full_text_does_not_poison_projection_excerpts(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Undigested bundle recap copies must not supply projection excerpts."""
    from apps.live_control_server.services.union_supergraph_projection_adapter import (
        build_plan_union_supergraph_projection,
    )

    old_result, _source = _profiled_candidate_ready_run(
        tmp_path,
        monkeypatch,
        "out/graph_memory/runs/mutated_bundle_recap_full_text",
        graph_extraction_profile="category_encounter_job_preview",
    )
    monkeypatch.setattr(
        "apps.live_control_server.services.union_supergraph_projection_adapter.repo_root",
        lambda: tmp_path,
    )
    materialize_preview_union_store_from_graph_ingest_run(
        PreviewUnionMaterializeOptions(
            manifest_path=old_result.manifest_path,
            repo_root=tmp_path,
        )
    )
    manifest = json.loads(old_result.manifest_path.read_text(encoding="utf-8"))
    bundle_uri = manifest["source"]["source_span_bundle_uri"]
    full_text = tmp_path / bundle_uri / "recap_full_text.md"
    assert full_text.is_file()
    full_text.write_text(
        full_text.read_text(encoding="utf-8") + "\nMUTATED_BUNDLE_TEXT\n",
        encoding="utf-8",
    )

    projection = build_plan_union_supergraph_projection(
        session_id="session-24",
        graph_run_manifest_path=old_result.manifest_path,
    )
    payload = projection.model_dump() if hasattr(projection, "model_dump") else projection
    if isinstance(payload, dict):
        blob = json.dumps(payload)
    else:
        blob = str(payload)
    assert "MUTATED_BUNDLE_TEXT" not in blob


def test_non_object_known_entity_mention_entries_fail_validation(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Malformed mention list entries must not coerce into an empty sidecar."""
    import hashlib

    from graph_memory.ingestion.graph_ingest_validate import (
        validate_manifest_known_entity_mentions,
    )

    old_result, _source = _profiled_candidate_ready_run(
        tmp_path,
        monkeypatch,
        "out/graph_memory/runs/corrupt_known_entity_mentions",
        graph_extraction_profile="category_encounter_job_preview",
    )
    manifest = json.loads(old_result.manifest_path.read_text(encoding="utf-8"))
    known_path = tmp_path / manifest["artifacts"]["known_entity_mentions"]["uri"]
    corrupt = {
        "schema": "dmb_known_entity_mention_sidecar_v0",
        "version": "0.1",
        "campaign_id": "longmont-c2",
        "session_id": "session-24",
        "mentions": ["corrupt entry"],
        "ambiguous_surfaces": [123],
    }
    known_path.write_text(
        json.dumps(corrupt, indent=2, sort_keys=True) + "\n", encoding="utf-8"
    )
    digest = hashlib.sha256(known_path.read_bytes()).hexdigest()
    manifest["artifacts"]["known_entity_mentions"]["sha256"] = f"sha256:{digest}"
    errors = validate_manifest_known_entity_mentions(tmp_path, manifest)
    assert any("mentions[0] must be an object" in error for error in errors)
    assert any("ambiguous_surfaces[0] must be a string" in error for error in errors)


def _materialized_projection_ready_run(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, output_dir: str
):
    old_result, _source = _profiled_candidate_ready_run(
        tmp_path,
        monkeypatch,
        output_dir,
        graph_extraction_profile="category_encounter_job_preview",
    )
    monkeypatch.setattr(
        "apps.live_control_server.services.union_supergraph_projection_adapter.repo_root",
        lambda: tmp_path,
    )
    materialize_preview_union_store_from_graph_ingest_run(
        PreviewUnionMaterializeOptions(
            manifest_path=old_result.manifest_path,
            repo_root=tmp_path,
        )
    )
    return old_result


def test_blank_known_entity_uri_rejects_projection(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    from apps.live_control_server.services.union_supergraph_projection_adapter import (
        build_plan_union_supergraph_projection,
    )

    old_result = _materialized_projection_ready_run(
        tmp_path, monkeypatch, "out/graph_memory/runs/blank_known_uri"
    )
    manifest = json.loads(old_result.manifest_path.read_text(encoding="utf-8"))
    manifest["artifacts"]["known_entity_mentions"]["uri"] = ""
    old_result.manifest_path.write_text(
        json.dumps(manifest, indent=2, sort_keys=True) + "\n", encoding="utf-8"
    )
    with pytest.raises(ValueError, match="known_entity_mentions|evidence"):
        build_plan_union_supergraph_projection(
            session_id="session-24",
            graph_run_manifest_path=old_result.manifest_path,
        )


def test_missing_source_span_uri_rejects_projection(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    from apps.live_control_server.services.union_supergraph_projection_adapter import (
        build_plan_union_supergraph_projection,
    )

    old_result = _materialized_projection_ready_run(
        tmp_path, monkeypatch, "out/graph_memory/runs/missing_span_uri"
    )
    manifest = json.loads(old_result.manifest_path.read_text(encoding="utf-8"))
    source = dict(manifest.get("source") or {})
    source.pop("source_span_index_uri", None)
    manifest["source"] = source
    old_result.manifest_path.write_text(
        json.dumps(manifest, indent=2, sort_keys=True) + "\n", encoding="utf-8"
    )
    with pytest.raises(
        ValueError, match="SourceSpanIndex|evidence|source_span_index_uri"
    ):
        build_plan_union_supergraph_projection(
            session_id="session-24",
            graph_run_manifest_path=old_result.manifest_path,
        )


def test_missing_source_span_file_rejects_projection(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    from apps.live_control_server.services.union_supergraph_projection_adapter import (
        build_plan_union_supergraph_projection,
    )

    old_result = _materialized_projection_ready_run(
        tmp_path, monkeypatch, "out/graph_memory/runs/missing_span_file"
    )
    manifest = json.loads(old_result.manifest_path.read_text(encoding="utf-8"))
    span_path = tmp_path / manifest["artifacts"]["source_span_index"]["uri"]
    span_path.unlink()
    with pytest.raises(ValueError, match="SourceSpanIndex|evidence|missing"):
        build_plan_union_supergraph_projection(
            session_id="session-24",
            graph_run_manifest_path=old_result.manifest_path,
        )


def test_mutated_source_span_index_with_stale_sha_rejects_projection_rebuild(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    import hashlib

    import apps.live_control_server.services.recap_graph_preview_ingest as ingest_service
    from apps.live_control_server.services.union_supergraph_projection_adapter import (
        build_plan_union_supergraph_projection,
    )

    old_result = _materialized_projection_ready_run(
        tmp_path, monkeypatch, "out/graph_memory/runs/mutated_span_index_stale_sha"
    )
    manifest_rel = old_result.manifest_path.relative_to(tmp_path).as_posix()
    projection_path = ingest_service.ensure_graph_ingest_projection_payload(
        repo_root=tmp_path,
        manifest_path=manifest_rel,
        session_id="session-24",
    )
    assert projection_path is not None

    manifest = json.loads(old_result.manifest_path.read_text(encoding="utf-8"))
    span_path = tmp_path / manifest["artifacts"]["source_span_index"]["uri"]
    mutated = json.loads(span_path.read_text(encoding="utf-8"))
    mutated["spans"] = [
        {
            **mutated["spans"][0],
            "text_excerpt": "FORGED_EVIDENCE_TEXT",
            "text": "FORGED_EVIDENCE_TEXT",
        }
    ]
    span_path.write_text(json.dumps(mutated, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    # Leave stale SourceSpanIndex SHA and corrupt projection cache SHA to force rebuild.
    projection_path.write_text(
        json.dumps({**json.loads(projection_path.read_text()), "mentions": []}, indent=2)
        + "\n",
        encoding="utf-8",
    )
    assert (
        hashlib.sha256(span_path.read_bytes()).hexdigest()
        != manifest["artifacts"]["source_span_index"]["sha256"].removeprefix("sha256:")
    )

    with pytest.raises(ValueError, match="SourceSpanIndex|evidence|sha256"):
        build_plan_union_supergraph_projection(
            session_id="session-24",
            graph_run_manifest_path=old_result.manifest_path,
        )


def test_mutated_candidate_graph_with_stale_sha_rejects_materialization(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    old_result, _source = _profiled_candidate_ready_run(
        tmp_path,
        monkeypatch,
        "out/graph_memory/runs/mutated_candidate_stale_sha",
        graph_extraction_profile="category_encounter_job_preview",
    )
    manifest = json.loads(old_result.manifest_path.read_text(encoding="utf-8"))
    candidate_path = tmp_path / manifest["artifacts"]["candidate_graph"]["uri"]
    candidate = json.loads(candidate_path.read_text(encoding="utf-8"))
    candidate["candidate_nodes"] = list(candidate.get("candidate_nodes") or []) + [
        {"id": "node:forged", "kind": "character", "label": "Forged", "evidence_refs": []}
    ]
    candidate_path.write_text(json.dumps(candidate, indent=2, sort_keys=True) + "\n", encoding="utf-8")

    with pytest.raises(ValueError, match="candidate_graph|evidence|sha256"):
        materialize_preview_union_store_from_graph_ingest_run(
            PreviewUnionMaterializeOptions(
                manifest_path=old_result.manifest_path,
                repo_root=tmp_path,
            )
        )


def test_mutated_preview_union_store_with_stale_sha_rejects_projection(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    from apps.live_control_server.services.union_supergraph_projection_adapter import (
        build_plan_union_supergraph_projection,
    )

    old_result = _materialized_projection_ready_run(
        tmp_path, monkeypatch, "out/graph_memory/runs/mutated_union_store"
    )
    # Force rebuild by deleting projection cache if present.
    projection = old_result.manifest_path.parent / "projection_payload.json"
    if projection.is_file():
        projection.unlink()
        manifest = json.loads(old_result.manifest_path.read_text(encoding="utf-8"))
        manifest.get("artifacts", {}).pop("projection_payload", None)
        old_result.manifest_path.write_text(
            json.dumps(manifest, indent=2, sort_keys=True) + "\n", encoding="utf-8"
        )

    manifest = json.loads(old_result.manifest_path.read_text(encoding="utf-8"))
    store_path = tmp_path / manifest["artifacts"]["preview_union_store"]["uri"]
    store = json.loads(store_path.read_text(encoding="utf-8"))
    store["nodes"]["character_forged"] = {
        "id": "character_forged",
        "kind": "character",
        "label": "Forged",
    }
    store_path.write_text(json.dumps(store, indent=2, sort_keys=True) + "\n", encoding="utf-8")

    with pytest.raises(ValueError, match="preview_union_store|evidence|sha256"):
        build_plan_union_supergraph_projection(
            session_id="session-24",
            graph_run_manifest_path=old_result.manifest_path,
        )


def test_restamped_union_store_invalidates_projection_cache(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Changing the union store with fully restamped digests must not reuse P1."""
    import hashlib

    import apps.live_control_server.services.recap_graph_preview_ingest as ingest_service

    old_result = _materialized_projection_ready_run(
        tmp_path, monkeypatch, "out/graph_memory/runs/restamped_union_cache"
    )
    manifest_rel = old_result.manifest_path.relative_to(tmp_path).as_posix()
    first = ingest_service.ensure_graph_ingest_projection_payload(
        repo_root=tmp_path,
        manifest_path=manifest_rel,
        session_id="session-24",
    )
    assert first is not None
    first_payload = json.loads(first.read_text(encoding="utf-8"))
    first_sha = hashlib.sha256(first.read_bytes()).hexdigest()

    manifest = json.loads(old_result.manifest_path.read_text(encoding="utf-8"))
    store_path = tmp_path / manifest["artifacts"]["preview_union_store"]["uri"]
    store = json.loads(store_path.read_text(encoding="utf-8"))
    # Mutate an existing projectable node so the store remains schema-valid.
    mira = store["nodes"]["character_mira"]
    mira["label"] = "RESTAMPED_MIRA"
    store_path.write_text(json.dumps(store, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    store_digest = hashlib.sha256(store_path.read_bytes()).hexdigest()
    manifest["artifacts"]["preview_union_store"]["sha256"] = f"sha256:{store_digest}"

    report_uri = manifest["artifacts"]["preview_union_validation_report"]["uri"]
    report_path = tmp_path / report_uri
    report = json.loads(report_path.read_text(encoding="utf-8"))
    report["preview_union_store_sha256"] = f"sha256:{store_digest}"
    report_path.write_text(json.dumps(report, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    report_digest = hashlib.sha256(report_path.read_bytes()).hexdigest()
    manifest["artifacts"]["preview_union_validation_report"]["sha256"] = (
        f"sha256:{report_digest}"
    )
    # Leave projection P1 and its SHA unchanged; sidecar unchanged.
    old_result.manifest_path.write_text(
        json.dumps(manifest, indent=2, sort_keys=True) + "\n", encoding="utf-8"
    )

    rebuilt = ingest_service.ensure_graph_ingest_projection_payload(
        repo_root=tmp_path,
        manifest_path=manifest_rel,
        session_id="session-24",
    )
    assert rebuilt is not None
    rebuilt_sha = hashlib.sha256(rebuilt.read_bytes()).hexdigest()
    assert rebuilt_sha != first_sha
    rebuilt_payload = json.loads(rebuilt.read_text(encoding="utf-8"))
    assert rebuilt_payload.get("projection_depends_on", {}).get(
        "preview_union_store_sha256"
    ) == f"sha256:{store_digest}"
    assert first_payload.get("projection_depends_on", {}).get(
        "preview_union_store_sha256"
    ) != f"sha256:{store_digest}"
    mira_view = rebuilt_payload.get("node_views", {}).get("character_mira") or {}
    assert mira_view.get("label") == "RESTAMPED_MIRA"

def test_requested_session_mismatch_rejects_manifest_projection(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    from apps.live_control_server.services.union_supergraph_projection_adapter import (
        build_plan_union_supergraph_projection,
    )

    old_result = _materialized_projection_ready_run(
        tmp_path, monkeypatch, "out/graph_memory/runs/session_mismatch"
    )
    with pytest.raises(ValueError, match="session_id|does not match"):
        build_plan_union_supergraph_projection(
            session_id="session-99",
            graph_run_manifest_path=old_result.manifest_path,
        )


def test_candidate_validation_report_requires_valid_true(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    import hashlib

    from graph_memory.ingestion.graph_ingest_validate import validate_manifest_candidate_graph

    old_result, _source = _profiled_candidate_ready_run(
        tmp_path,
        monkeypatch,
        "out/graph_memory/runs/invalid_candidate_report",
        graph_extraction_profile="category_encounter_job_preview",
    )
    manifest = json.loads(old_result.manifest_path.read_text(encoding="utf-8"))
    candidate_path = tmp_path / manifest["artifacts"]["candidate_graph"]["uri"]
    candidate = json.loads(candidate_path.read_text(encoding="utf-8"))
    candidate["candidate_nodes"] = list(candidate.get("candidate_nodes") or []) + [
        {"id": "node:c2", "kind": "character", "label": "C2", "evidence_refs": []}
    ]
    candidate_path.write_text(
        json.dumps(candidate, indent=2, sort_keys=True) + "\n", encoding="utf-8"
    )
    candidate_digest = hashlib.sha256(candidate_path.read_bytes()).hexdigest()
    manifest["artifacts"]["candidate_graph"]["sha256"] = f"sha256:{candidate_digest}"

    report_path = tmp_path / manifest["artifacts"]["candidate_validation_report"]["uri"]
    report_path.write_text(
        json.dumps(
            {
                "candidate_graph_sha256": f"sha256:{candidate_digest}",
                "valid": False,
            },
            indent=2,
            sort_keys=True,
        )
        + "\n",
        encoding="utf-8",
    )
    report_digest = hashlib.sha256(report_path.read_bytes()).hexdigest()
    manifest["artifacts"]["candidate_validation_report"]["sha256"] = (
        f"sha256:{report_digest}"
    )

    errors = validate_manifest_candidate_graph(tmp_path, manifest)
    assert any("valid must be true" in error for error in errors)
    assert any("schema" in error for error in errors)


def test_known_entity_mention_foreign_span_and_surface_mismatch_fail(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    import hashlib

    from graph_memory.ingestion.graph_ingest_validate import (
        validate_manifest_known_entity_mentions,
    )

    old_result, _source = _profiled_candidate_ready_run(
        tmp_path,
        monkeypatch,
        "out/graph_memory/runs/mention_span_semantics",
        graph_extraction_profile="category_encounter_job_preview",
    )
    manifest = json.loads(old_result.manifest_path.read_text(encoding="utf-8"))
    known_path = tmp_path / manifest["artifacts"]["known_entity_mentions"]["uri"]
    span_index = json.loads(
        (tmp_path / manifest["artifacts"]["source_span_index"]["uri"]).read_text(
            encoding="utf-8"
        )
    )
    body_span = next(
        span
        for span in span_index["spans"]
        if int(span["start_line"]) <= 3 and int(span["end_line"]) >= 4
    )
    recap_lines = (
        tmp_path / manifest["source"]["normalized_recap_path"]
    ).read_text(encoding="utf-8").splitlines()
    paragraph = "\n".join(
        recap_lines[int(body_span["start_line"]) - 1 : int(body_span["end_line"])]
    )
    surface = "Longmont"
    start = paragraph.index(surface)
    end = start + len(surface)

    foreign = {
        "schema": "dmb_known_entity_mention_sidecar_v0",
        "version": "0.1",
        "campaign_id": "longmont-c2",
        "session_id": "session-24",
        "mentions": [
            {
                "source_span_ref_id": "span:foreign:not-real",
                "start_offset": start,
                "end_offset": end,
                "surface_text": surface,
                "canonical_entity_id": "character_mira",
                "entity_slug": "mira",
                "entity_kind": "pc",
                "match_method": "canonical",
                "display_name": surface,
            }
        ],
        "ambiguous_surfaces": [],
    }
    known_path.write_text(json.dumps(foreign, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    manifest["artifacts"]["known_entity_mentions"]["sha256"] = (
        f"sha256:{hashlib.sha256(known_path.read_bytes()).hexdigest()}"
    )
    errors = validate_manifest_known_entity_mentions(tmp_path, manifest)
    assert any("not in SourceSpanIndex" in error for error in errors)

    mismatch = {
        **foreign,
        "mentions": [
            {
                **foreign["mentions"][0],
                "source_span_ref_id": body_span["source_span_id"],
                "surface_text": "NOT_IN_PARAGRAPH",
                "end_offset": start + len("NOT_IN_PARAGRAPH"),
            }
        ],
    }
    known_path.write_text(
        json.dumps(mismatch, indent=2, sort_keys=True) + "\n", encoding="utf-8"
    )
    manifest["artifacts"]["known_entity_mentions"]["sha256"] = (
        f"sha256:{hashlib.sha256(known_path.read_bytes()).hexdigest()}"
    )
    errors = validate_manifest_known_entity_mentions(tmp_path, manifest)
    assert any("surface_text does not match" in error for error in errors)

    oob = {
        **foreign,
        "mentions": [
            {
                **foreign["mentions"][0],
                "source_span_ref_id": body_span["source_span_id"],
                "start_offset": 0,
                "end_offset": len(paragraph) + 5,
                "surface_text": paragraph + "XXXXX",
            }
        ],
    }
    known_path.write_text(json.dumps(oob, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    manifest["artifacts"]["known_entity_mentions"]["sha256"] = (
        f"sha256:{hashlib.sha256(known_path.read_bytes()).hexdigest()}"
    )
    errors = validate_manifest_known_entity_mentions(tmp_path, manifest)
    assert any("exceed paragraph length" in error for error in errors)


def test_manifest_source_match_requires_full_digest_not_artifact_id_prefix(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Same-prefix SourceArtifact IDs must not count as content equality."""
    from apps.live_control_server.services.graph_ingest_run_registry import (
        _manifest_matches_source_recap,
    )

    old_result, source = _profiled_candidate_ready_run(
        tmp_path,
        monkeypatch,
        "out/graph_memory/runs/prefix_digest_collision",
        graph_extraction_profile="category_encounter_job_preview",
    )
    _bind_production_lineage(tmp_path, old_result)
    manifest = json.loads(old_result.manifest_path.read_text(encoding="utf-8"))
    artifact_id = str(manifest["source"]["source_artifact_id"])
    # Drop packaged digests so matching would have to rely on registry full digest
    # or (incorrectly) the ID prefix.
    manifest["source"]["normalized_recap_sha256"] = ""
    artifacts = dict(manifest.get("artifacts") or {})
    if "normalized_recap" in artifacts:
        artifacts["normalized_recap"] = {**artifacts["normalized_recap"], "sha256": ""}
    manifest["artifacts"] = artifacts
    # Point at a non-existent registry record that still embeds the digest prefix,
    # so the old substring matcher would incorrectly accept it.
    prefix = artifact_id.rsplit(":", 1)[-1]
    manifest["source"]["source_artifact_id"] = (
        f"artifact:recap:other-campaign:session-99:{prefix}"
    )
    assert prefix and prefix in manifest["source"]["source_artifact_id"]
    old_result.manifest_path.write_text(
        json.dumps(manifest, indent=2, sort_keys=True) + "\n", encoding="utf-8"
    )

    crafted = f"sha256:{prefix}{'0' * (64 - len(prefix))}"
    assert not _manifest_matches_source_recap(
        tmp_path,
        old_result.manifest_path,
        source_recap_path=source.relative_to(tmp_path).as_posix(),
        source_recap_sha256=crafted,
    )


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
    _bind_production_lineage(tmp_path, old_result)

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
    """An explicit candidate path must not reuse a prior run; production owns packaging."""
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
    # Reviewable production candidate is authoritative over a manual fixture path.
    assert calls[0].candidate_graph_path != explicit_candidate.resolve()
    assert calls[0].source_artifact_id
    assert str(calls[0].source_artifact_id).startswith("artifact:recap:")
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


def test_foreign_session_store_rejects_despite_matching_union_report(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Parsed store identity wins over a re-signed report that only mirrors the manifest."""
    import hashlib

    from apps.live_control_server.services.union_supergraph_projection_adapter import (
        build_plan_union_supergraph_projection,
    )

    old_result = _materialized_projection_ready_run(
        tmp_path, monkeypatch, "out/graph_memory/runs/foreign_session_store"
    )
    manifest = json.loads(old_result.manifest_path.read_text(encoding="utf-8"))
    store_path = tmp_path / manifest["artifacts"]["preview_union_store"]["uri"]
    store = json.loads(store_path.read_text(encoding="utf-8"))
    store["focus_session_id"] = "session-99"
    store_path.write_text(json.dumps(store, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    store_digest = hashlib.sha256(store_path.read_bytes()).hexdigest()
    manifest["artifacts"]["preview_union_store"]["sha256"] = f"sha256:{store_digest}"

    report_path = tmp_path / manifest["artifacts"]["preview_union_validation_report"]["uri"]
    report = json.loads(report_path.read_text(encoding="utf-8"))
    # Report continues to claim the *manifest* campaign/session identity.
    assert report["campaign_id"] == manifest["campaign_id"]
    assert report["session_id"] == manifest["session_id"]
    report["preview_union_store_sha256"] = f"sha256:{store_digest}"
    report_path.write_text(json.dumps(report, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    report_digest = hashlib.sha256(report_path.read_bytes()).hexdigest()
    manifest["artifacts"]["preview_union_validation_report"]["sha256"] = (
        f"sha256:{report_digest}"
    )
    old_result.manifest_path.write_text(
        json.dumps(manifest, indent=2, sort_keys=True) + "\n", encoding="utf-8"
    )

    with pytest.raises(ValueError, match="focus_session_id does not match"):
        build_plan_union_supergraph_projection(
            session_id="session-24",
            graph_run_manifest_path=old_result.manifest_path,
        )


def test_stale_union_after_candidate_restamp_fails_closed(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Valid C2 + candidate report with unchanged U1/report must not project."""
    import hashlib

    from apps.live_control_server.services.union_supergraph_projection_adapter import (
        build_plan_union_supergraph_projection,
    )

    old_result = _materialized_projection_ready_run(
        tmp_path, monkeypatch, "out/graph_memory/runs/stale_u1_after_c2"
    )
    manifest = json.loads(old_result.manifest_path.read_text(encoding="utf-8"))
    candidate_path = tmp_path / manifest["artifacts"]["candidate_graph"]["uri"]
    candidate = json.loads(candidate_path.read_text(encoding="utf-8"))
    nodes = list(candidate.get("candidate_nodes") or [])
    nodes.append(
        {
            "id": "node:c2-only",
            "kind": "character",
            "label": "C2Only",
            "evidence_refs": [],
        }
    )
    candidate["candidate_nodes"] = nodes
    candidate_path.write_text(
        json.dumps(candidate, indent=2, sort_keys=True) + "\n", encoding="utf-8"
    )
    candidate_digest = hashlib.sha256(candidate_path.read_bytes()).hexdigest()
    manifest["artifacts"]["candidate_graph"]["sha256"] = f"sha256:{candidate_digest}"

    report_path = tmp_path / manifest["artifacts"]["candidate_validation_report"]["uri"]
    report = json.loads(report_path.read_text(encoding="utf-8"))
    report["candidate_graph_sha256"] = f"sha256:{candidate_digest}"
    report_path.write_text(json.dumps(report, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    report_digest = hashlib.sha256(report_path.read_bytes()).hexdigest()
    manifest["artifacts"]["candidate_validation_report"]["sha256"] = (
        f"sha256:{report_digest}"
    )
    # Leave preview_union_store + preview_union_validation_report unchanged.
    old_result.manifest_path.write_text(
        json.dumps(manifest, indent=2, sort_keys=True) + "\n", encoding="utf-8"
    )

    with pytest.raises(
        ValueError,
        match="candidate_graph_sha256|does not match verified candidate",
    ):
        build_plan_union_supergraph_projection(
            session_id="session-24",
            graph_run_manifest_path=old_result.manifest_path,
        )


def test_verified_snapshot_does_not_reread_protected_union_store(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Consumers must use the read-once snapshot; a second store read must not occur."""
    from apps.live_control_server.services.union_supergraph_projection_adapter import (
        build_plan_union_supergraph_projection,
    )

    old_result = _materialized_projection_ready_run(
        tmp_path, monkeypatch, "out/graph_memory/runs/no_store_reread"
    )
    manifest = json.loads(old_result.manifest_path.read_text(encoding="utf-8"))
    store_path = (tmp_path / manifest["artifacts"]["preview_union_store"]["uri"]).resolve()
    reads = {"n": 0}
    original_read_bytes = Path.read_bytes

    def guarded_read_bytes(self: Path, *args: object, **kwargs: object) -> bytes:
        try:
            resolved = self.resolve()
        except OSError:
            resolved = self
        if resolved == store_path:
            reads["n"] += 1
            if reads["n"] > 1:
                raise AssertionError(
                    "preview_union_store reopened after verified snapshot read"
                )
        return original_read_bytes(self, *args, **kwargs)

    monkeypatch.setattr(Path, "read_bytes", guarded_read_bytes)
    projection = build_plan_union_supergraph_projection(
        session_id="session-24",
        graph_run_manifest_path=old_result.manifest_path,
    )
    assert projection.session_id == "session-24"
    assert reads["n"] == 1


def test_ensure_projection_cas_aborts_on_concurrent_manifest_change(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """CAS must refuse to persist when the manifest token changes mid-build."""
    import apps.live_control_server.services.recap_graph_preview_ingest as ingest_service
    import apps.live_control_server.services.union_supergraph_projection_adapter as adapter

    old_result = _materialized_projection_ready_run(
        tmp_path, monkeypatch, "out/graph_memory/runs/cas_abort"
    )
    manifest_rel = old_result.manifest_path.relative_to(tmp_path).as_posix()
    manifest_full = old_result.manifest_path
    marker = "2099-01-01T00:00:00Z"
    real_build = adapter.build_projection_payload_from_verified_snapshot

    def mutating_build(snapshot, **kwargs):
        payload = json.loads(manifest_full.read_text(encoding="utf-8"))
        payload["updated_at"] = marker
        manifest_full.write_text(
            json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8"
        )
        return real_build(snapshot, **kwargs)

    monkeypatch.setattr(
        adapter,
        "build_projection_payload_from_verified_snapshot",
        mutating_build,
    )

    with pytest.raises(ValueError, match="changed concurrently|refusing to overwrite"):
        ingest_service.ensure_graph_ingest_projection_payload(
            repo_root=tmp_path,
            manifest_path=manifest_rel,
            session_id="session-24",
        )

    after = json.loads(manifest_full.read_text(encoding="utf-8"))
    assert after.get("updated_at") == marker
    assert "projection_payload" not in (after.get("artifacts") or {})
    assert not (manifest_full.parent / "projection_payload.json").exists()


def test_old_projection_contract_version_forces_cache_miss_rebuild(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Persisted depends_on with an old projection_contract_version must rebuild."""
    import hashlib

    import apps.live_control_server.services.recap_graph_preview_ingest as ingest_service
    from graph_memory.ingestion.graph_ingest_verified_snapshot import (
        PROJECTION_CONTRACT_VERSION,
    )

    old_result = _materialized_projection_ready_run(
        tmp_path, monkeypatch, "out/graph_memory/runs/old_contract_version"
    )
    manifest_rel = old_result.manifest_path.relative_to(tmp_path).as_posix()
    first = ingest_service.ensure_graph_ingest_projection_payload(
        repo_root=tmp_path,
        manifest_path=manifest_rel,
        session_id="session-24",
    )
    assert first is not None
    first_sha = hashlib.sha256(first.read_bytes()).hexdigest()
    first_payload = json.loads(first.read_text(encoding="utf-8"))
    assert (
        first_payload.get("projection_depends_on", {}).get("projection_contract_version")
        == PROJECTION_CONTRACT_VERSION
    )

    stale_deps = dict(first_payload["projection_depends_on"])
    stale_deps["projection_contract_version"] = "0.9"
    first_payload["projection_depends_on"] = stale_deps
    first.write_text(
        json.dumps(first_payload, indent=2, sort_keys=True) + "\n", encoding="utf-8"
    )
    stale_sha = hashlib.sha256(first.read_bytes()).hexdigest()
    assert stale_sha != first_sha
    new_proj_digest = stale_sha

    manifest = json.loads(old_result.manifest_path.read_text(encoding="utf-8"))
    artifact = dict(manifest["artifacts"]["projection_payload"])
    artifact["sha256"] = f"sha256:{new_proj_digest}"
    artifact["depends_on"] = stale_deps
    manifest["artifacts"]["projection_payload"] = artifact
    old_result.manifest_path.write_text(
        json.dumps(manifest, indent=2, sort_keys=True) + "\n", encoding="utf-8"
    )

    rebuilt = ingest_service.ensure_graph_ingest_projection_payload(
        repo_root=tmp_path,
        manifest_path=manifest_rel,
        session_id="session-24",
    )
    assert rebuilt is not None
    rebuilt_sha = hashlib.sha256(rebuilt.read_bytes()).hexdigest()
    assert rebuilt_sha != stale_sha
    rebuilt_payload = json.loads(rebuilt.read_text(encoding="utf-8"))
    assert (
        rebuilt_payload.get("projection_depends_on", {}).get(
            "projection_contract_version"
        )
        == PROJECTION_CONTRACT_VERSION
    )