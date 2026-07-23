from __future__ import annotations

import json
from pathlib import Path

import pytest

from evals.graph_memory_layer.graph_preview_runner import (
    GraphPreviewRunnerOptions,
    run_graph_preview_extraction,
)
from graph_memory.ingestion import (
    GraphIngestRunStatus,
    validate_graph_ingest_run_manifest,
)
from graph_memory.union_supergraph.preview_run_materialize import (
    PreviewUnionMaterializeOptions,
    materialize_preview_union_store_from_graph_ingest_run,
)

REPO_ROOT = Path(__file__).resolve().parents[1]
FIXTURE_DIR = REPO_ROOT / "tests/fixtures/graph_memory/category_preview_runner"
RECAP_PATH = FIXTURE_DIR / "session_24_normalized_recap.md"
CANDIDATE_PATH = FIXTURE_DIR / "candidate_graph_fixture.json"


def _load_json(path: Path) -> dict:
    return json.loads(path.read_text())


def _copy_inputs(tmp_path: Path) -> tuple[Path, Path]:
    source = tmp_path / "session_24_normalized_recap.md"
    candidate = tmp_path / "candidate_graph_fixture.json"
    source.write_text(RECAP_PATH.read_text())
    candidate.write_text(CANDIDATE_PATH.read_text())
    return source, candidate


def _candidate_ready_run(tmp_path: Path) -> Path:
    from apps.live_control_server.services.source_artifact_registry import (
        create_recap_source_artifact,
        load_source_span_index,
    )
    from src.graph_memory.source_span import source_span_index_to_dict

    source, candidate = _copy_inputs(tmp_path)
    artifact = create_recap_source_artifact(
        tmp_path,
        campaign_id="longmont-c2",
        session_id="session-24",
        recap_path=source,
    )
    span_payload = source_span_index_to_dict(
        load_source_span_index(tmp_path, artifact.source_artifact_id)
    )
    # Stamp fixture candidate with the digest-qualified artifact identity.
    from evals.graph_memory_layer.graph_preview_runner import (
        _with_candidate_graph_identity,
    )

    graph = _with_candidate_graph_identity(
        json.loads(candidate.read_text(encoding="utf-8")),
        campaign_id="longmont-c2",
        session_id="session-24",
        source_artifact_id=artifact.source_artifact_id,
    )
    candidate.write_text(json.dumps(graph, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    result = run_graph_preview_extraction(
        GraphPreviewRunnerOptions(
            campaign_id="longmont-c2",
            session_id="session-24",
            normalized_recap_path=source,
            output_dir=Path("runs/candidate_ready"),
            candidate_graph_path=candidate,
            source_span_index=span_payload,
            source_artifact_id=artifact.source_artifact_id,
        )
    )
    assert result.status == GraphIngestRunStatus.CANDIDATE_VALIDATION_READY
    return result.manifest_path


def test_materializer_writes_preview_union_store_from_candidate_ready_manifest(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.chdir(tmp_path)
    manifest_path = _candidate_ready_run(tmp_path)

    result = materialize_preview_union_store_from_graph_ingest_run(
        PreviewUnionMaterializeOptions(manifest_path=manifest_path)
    )
    manifest = _load_json(result.manifest_path)

    assert result.status == GraphIngestRunStatus.PREVIEW_UNION_STORE_READY
    assert result.preview_union_store_path.exists()
    assert manifest["status"] == "preview_union_store_ready"
    assert "preview_union_store" in manifest["artifacts"]
    assert validate_graph_ingest_run_manifest(manifest)["valid"] is True


def test_materializer_preserves_preview_only_diagnostics(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.chdir(tmp_path)
    manifest_path = _candidate_ready_run(tmp_path)

    result = materialize_preview_union_store_from_graph_ingest_run(
        PreviewUnionMaterializeOptions(manifest_path=manifest_path)
    )
    diagnostics = _load_json(result.manifest_path)["diagnostics"]

    assert diagnostics["preview_only"] is True
    assert diagnostics["candidate_extraction"] is True
    assert diagnostics["preview_import"] is True
    assert diagnostics["canon_promotion"] is False
    assert diagnostics["approved_memory_write"] is False
    assert diagnostics["corpus_mutation"] is False
    assert diagnostics["production_retrieval"] is False
    assert diagnostics["runtime_projection_connected"] is False


def test_materializer_updates_health_counts_from_union_store(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.chdir(tmp_path)
    manifest_path = _candidate_ready_run(tmp_path)

    result = materialize_preview_union_store_from_graph_ingest_run(
        PreviewUnionMaterializeOptions(manifest_path=manifest_path)
    )
    manifest = _load_json(result.manifest_path)
    store = _load_json(result.preview_union_store_path)

    assert manifest["health"]["preview_union_store_valid"] is True
    assert manifest["health"]["node_count"] == len(store["nodes"]) == result.node_count
    assert manifest["health"]["edge_count"] == len(store["edges"]) == result.edge_count
    assert (
        manifest["health"]["evidence_ref_count"]
        == len(store["evidence"])
        == result.evidence_ref_count
    )
    assert manifest["health"]["resolvable_evidence_ref_count"] == len(store["evidence"])


def test_materializer_rejects_source_span_only_manifest(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.chdir(tmp_path)
    source = tmp_path / "session_24_normalized_recap.md"
    source.write_text(RECAP_PATH.read_text())
    runner_result = run_graph_preview_extraction(
        GraphPreviewRunnerOptions(
            campaign_id="longmont-c2",
            session_id="session-24",
            normalized_recap_path=source,
            output_dir=Path("runs/source_span_only"),
        )
    )

    with pytest.raises(ValueError, match="candidate_validation_ready"):
        materialize_preview_union_store_from_graph_ingest_run(
            PreviewUnionMaterializeOptions(manifest_path=runner_result.manifest_path)
        )
    assert not (runner_result.output_dir / "preview_union_supergraph.json").exists()


def test_materializer_rejects_failed_candidate_manifest(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    from apps.live_control_server.services.source_artifact_registry import (
        create_recap_source_artifact,
        load_source_span_index,
    )
    from evals.graph_memory_layer.graph_preview_runner import (
        _with_candidate_graph_identity,
    )
    from src.graph_memory.source_span import source_span_index_to_dict

    monkeypatch.chdir(tmp_path)
    source, candidate = _copy_inputs(tmp_path)
    artifact = create_recap_source_artifact(
        tmp_path,
        campaign_id="longmont-c2",
        session_id="session-24",
        recap_path=source,
    )
    span_payload = source_span_index_to_dict(
        load_source_span_index(tmp_path, artifact.source_artifact_id)
    )
    payload = _with_candidate_graph_identity(
        _load_json(candidate),
        campaign_id="longmont-c2",
        session_id="session-24",
        source_artifact_id=artifact.source_artifact_id,
    )
    payload["diagnostics"]["canon_promotion"] = True
    candidate.write_text(json.dumps(payload))
    runner_result = run_graph_preview_extraction(
        GraphPreviewRunnerOptions(
            campaign_id="longmont-c2",
            session_id="session-24",
            normalized_recap_path=source,
            output_dir=Path("runs/failed_candidate"),
            candidate_graph_path=candidate,
            source_span_index=span_payload,
            source_artifact_id=artifact.source_artifact_id,
        )
    )

    with pytest.raises(
        ValueError,
        match="invalid input graph-ingest manifest|candidate_validation_ready",
    ):
        materialize_preview_union_store_from_graph_ingest_run(
            PreviewUnionMaterializeOptions(manifest_path=runner_result.manifest_path)
        )
    assert not (runner_result.output_dir / "preview_union_supergraph.json").exists()


def test_materializer_rejects_forbidden_candidate_diagnostics(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    import hashlib

    monkeypatch.chdir(tmp_path)
    manifest_path = _candidate_ready_run(tmp_path)
    manifest = _load_json(manifest_path)
    candidate_path = tmp_path / manifest["artifacts"]["candidate_graph"]["uri"]
    candidate = _load_json(candidate_path)
    candidate["diagnostics"]["production_retrieval"] = True
    candidate_path.write_text(json.dumps(candidate))
    candidate_digest = f"sha256:{hashlib.sha256(candidate_path.read_bytes()).hexdigest()}"
    manifest["artifacts"]["candidate_graph"]["sha256"] = candidate_digest
    report_uri = manifest["artifacts"]["candidate_validation_report"]["uri"]
    report_path = tmp_path / report_uri
    report = _load_json(report_path)
    report["candidate_graph_sha256"] = candidate_digest
    report_path.write_text(json.dumps(report, indent=2, sort_keys=True) + "\n")
    manifest["artifacts"]["candidate_validation_report"]["sha256"] = (
        f"sha256:{hashlib.sha256(report_path.read_bytes()).hexdigest()}"
    )
    manifest_path.write_text(json.dumps(manifest, indent=2, sort_keys=True) + "\n")

    with pytest.raises(ValueError, match="candidate graph diagnostics|forbidden lifecycle|production_retrieval"):
        materialize_preview_union_store_from_graph_ingest_run(
            PreviewUnionMaterializeOptions(manifest_path=manifest_path)
        )
    assert not (manifest_path.parent / "preview_union_supergraph.json").exists()


def test_materializer_rejects_mutated_packaged_recap_bytes(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Evidence gate must bind SourceSpanIndex to packaged recap bytes, not claims alone."""
    monkeypatch.chdir(tmp_path)
    manifest_path = _candidate_ready_run(tmp_path)
    manifest = _load_json(manifest_path)
    packaged_recap = tmp_path / manifest["source"]["normalized_recap_path"]
    assert packaged_recap.is_file()
    original = packaged_recap.read_text(encoding="utf-8")
    packaged_recap.write_text(original + "\nMutated after packaging.\n", encoding="utf-8")

    with pytest.raises(
        ValueError,
        match="packaged recap bytes|candidate-ready GraphIngest evidence|normalized recap sha256",
    ):
        materialize_preview_union_store_from_graph_ingest_run(
            PreviewUnionMaterializeOptions(manifest_path=manifest_path, repo_root=tmp_path)
        )
    assert not (manifest_path.parent / "preview_union_supergraph.json").exists()


def test_materializer_does_not_set_ready_for_projection_or_projection_locator(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.chdir(tmp_path)
    manifest_path = _candidate_ready_run(tmp_path)

    result = materialize_preview_union_store_from_graph_ingest_run(
        PreviewUnionMaterializeOptions(manifest_path=manifest_path)
    )
    manifest = _load_json(result.manifest_path)

    assert manifest["status"] == "preview_union_store_ready"
    assert manifest["projection"] is None
    assert manifest["next_actions"] == ["open_projection_preview"]


def test_materializer_store_source_artifacts_do_not_reference_temp_paths(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.chdir(tmp_path)
    manifest_path = _candidate_ready_run(tmp_path)

    result = materialize_preview_union_store_from_graph_ingest_run(
        PreviewUnionMaterializeOptions(manifest_path=manifest_path)
    )
    store = _load_json(result.preview_union_store_path)
    artifacts = store["source_artifacts"].values()
    uris = [artifact["uri"] for artifact in artifacts]

    assert all("preview-union-materialize-" not in uri for uri in uris)
    assert all(Path(uri).is_absolute() is False for uri in uris)
    for uri in uris:
        if uri.startswith("fixture://"):
            continue
        assert (tmp_path / uri).exists()
    assert (manifest_path.parent / "candidate_graph_import_input.json").exists()


def test_recap_mutated_after_snapshot_verify_uses_verified_text(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Union evidence must come from verified snapshot recap text, not a later disk read."""
    monkeypatch.chdir(tmp_path)
    manifest_path = _candidate_ready_run(tmp_path)
    manifest = _load_json(manifest_path)
    packaged_recap = tmp_path / manifest["source"]["normalized_recap_path"]
    assert packaged_recap.is_file()

    original_read_bytes = Path.read_bytes
    recap_reads = {"n": 0}

    def guarded_read_bytes(self: Path, *args: object, **kwargs: object) -> bytes:
        try:
            resolved = self.resolve()
        except OSError:
            resolved = self
        if resolved == packaged_recap.resolve():
            recap_reads["n"] += 1
            content = original_read_bytes(self, *args, **kwargs)
            if recap_reads["n"] > 1:
                return content + b"\n\nMUTATED_RECAP_MARKER_B\n"
            return content
        return original_read_bytes(self, *args, **kwargs)

    monkeypatch.setattr(Path, "read_bytes", guarded_read_bytes)

    result = materialize_preview_union_store_from_graph_ingest_run(
        PreviewUnionMaterializeOptions(manifest_path=manifest_path, repo_root=tmp_path)
    )
    store = _load_json(result.preview_union_store_path)
    evidence_blob = json.dumps(store.get("evidence", {}))
    assert "MUTATED_RECAP_MARKER_B" not in evidence_blob
    assert recap_reads["n"] == 1
