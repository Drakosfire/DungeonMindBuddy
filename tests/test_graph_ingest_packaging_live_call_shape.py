"""Characterization coverage for the live recap-ingest GraphIngest packaging call shape.

``apps/live_control_server/services/recap_graph_preview_ingest.py`` packages the
production ``ExtractionRun`` candidate with a very specific call shape:
``allow_llm=False``, a supplied ``candidate_graph_path``, and the immutable
``source_span_index`` / ``source_artifact_id`` produced by the production
SourceArtifact admission pipeline (never the legacy ``artifact:recap:...`` ids).

This test pins the packaging output for exactly that call shape so the packaging
implementation can be relocated out of ``evals/graph_memory_layer/graph_preview_runner.py``
into a production-owned module without silently changing manifest status,
artifact keys/kinds, candidate digests, or validation-report presence.

Import note: the suite runs the same live call shape twice —

1. through ``evals.graph_memory_layer.graph_preview_runner`` (compatibility shim /
   pre-move entry point), and
2. through ``src.graph_memory.extraction.graph_ingest_packaging`` (production-owned
   module the live service imports).

Identical assertions on both paths prove the production implementation executes
successfully, not merely that the service AST-names it.
"""

from __future__ import annotations

import hashlib
import json
from collections.abc import Callable
from pathlib import Path
from typing import Any, Protocol

import pytest

from graph_memory.ingestion import (
    GraphIngestArtifactKind,
    GraphIngestRunStatus,
    validate_graph_ingest_run_manifest,
)

REPO_ROOT = Path(__file__).resolve().parents[1]
FIXTURE_DIR = REPO_ROOT / "tests/fixtures/graph_memory/category_preview_runner"
RECAP_PATH = FIXTURE_DIR / "session_24_normalized_recap.md"
CANDIDATE_PATH = FIXTURE_DIR / "candidate_graph_fixture.json"

_EXPECTED_ARTIFACT_KINDS = {
    "normalized_recap": GraphIngestArtifactKind.NORMALIZED_RECAP,
    "source_span_bundle": GraphIngestArtifactKind.SOURCE_SPAN_BUNDLE,
    "source_span_index": GraphIngestArtifactKind.SOURCE_SPAN_INDEX,
    "provenance_index": GraphIngestArtifactKind.PROVENANCE_INDEX,
    "candidate_graph": GraphIngestArtifactKind.CANDIDATE_GRAPH,
    "candidate_validation_report": GraphIngestArtifactKind.CANDIDATE_VALIDATION_REPORT,
    "known_entity_mentions": GraphIngestArtifactKind.KNOWN_ENTITY_MENTIONS,
}


class _PackagingApi(Protocol):
    GraphPreviewRunnerOptions: type[Any]
    run_graph_preview_extraction: Callable[..., Any]
    _with_candidate_graph_identity: Callable[..., dict[str, Any]]


def _sha256_file(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _evals_shim_api() -> _PackagingApi:
    from evals.graph_memory_layer import graph_preview_runner as api

    return api


def _production_api() -> _PackagingApi:
    from src.graph_memory.extraction import graph_ingest_packaging as api

    return api


@pytest.fixture(params=["evals_shim", "production_module"], ids=["evals_shim", "production_module"])
def packaging_api(request: pytest.FixtureRequest) -> _PackagingApi:
    if request.param == "evals_shim":
        return _evals_shim_api()
    return _production_api()


def _run_live_call_shape(
    tmp_path: Path,
    packaging: _PackagingApi,
    *,
    output_dir: Path,
    category_client: object | None = None,
) -> tuple[dict, Path]:
    """Reproduce the exact call shape recap_graph_preview_ingest.py uses in production.

    ``allow_llm=False`` with a supplied ``candidate_graph_path`` plus the immutable
    ``source_span_index`` / ``source_artifact_id`` from SourceArtifact admission.
    """
    from apps.live_control_server.services.source_artifact_registry import (
        create_recap_source_artifact,
        load_source_span_index,
    )
    from src.graph_memory.source_span import source_span_index_to_dict

    source = tmp_path / "session_24_normalized_recap.md"
    candidate = tmp_path / "candidate_graph_fixture.json"
    source.write_text(RECAP_PATH.read_text())
    candidate.write_text(CANDIDATE_PATH.read_text())

    artifact = create_recap_source_artifact(
        tmp_path,
        campaign_id="longmont-c2",
        session_id="session-24",
        recap_path=source,
    )
    span_payload = source_span_index_to_dict(
        load_source_span_index(tmp_path, artifact.source_artifact_id)
    )
    graph = packaging._with_candidate_graph_identity(
        json.loads(candidate.read_text(encoding="utf-8")),
        campaign_id="longmont-c2",
        session_id="session-24",
        source_artifact_id=artifact.source_artifact_id,
    )
    candidate.write_text(json.dumps(graph, indent=2, sort_keys=True) + "\n", encoding="utf-8")

    options_kwargs: dict[str, Any] = {
        "campaign_id": "longmont-c2",
        "session_id": "session-24",
        "normalized_recap_path": source,
        "output_dir": output_dir,
        "allow_llm": False,
        "candidate_graph_path": candidate,
        "source_span_index": span_payload,
        "source_artifact_id": artifact.source_artifact_id,
    }
    if category_client is not None:
        options_kwargs["category_client"] = category_client

    result = packaging.run_graph_preview_extraction(
        packaging.GraphPreviewRunnerOptions(**options_kwargs)
    )
    assert result.status == GraphIngestRunStatus.CANDIDATE_VALIDATION_READY
    manifest = json.loads(result.manifest_path.read_text(encoding="utf-8"))
    return manifest, result.manifest_path.parent


def test_live_call_shape_manifest_status_and_schema(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, packaging_api: _PackagingApi
) -> None:
    monkeypatch.chdir(tmp_path)
    manifest, _run_dir = _run_live_call_shape(
        tmp_path, packaging_api, output_dir=Path("runs/live_call_shape")
    )

    assert manifest["status"] == "candidate_validation_ready"
    report = validate_graph_ingest_run_manifest(manifest)
    assert report["valid"] is True
    assert report["errors"] == []


def test_live_call_shape_artifact_keys_and_kinds(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, packaging_api: _PackagingApi
) -> None:
    monkeypatch.chdir(tmp_path)
    manifest, _run_dir = _run_live_call_shape(
        tmp_path, packaging_api, output_dir=Path("runs/live_call_shape")
    )

    artifacts = manifest["artifacts"]
    assert set(_EXPECTED_ARTIFACT_KINDS) <= set(artifacts)
    for key, expected_kind in _EXPECTED_ARTIFACT_KINDS.items():
        assert artifacts[key]["kind"] == expected_kind.value, key


def test_live_call_shape_candidate_digest_matches_packaged_bytes(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, packaging_api: _PackagingApi
) -> None:
    monkeypatch.chdir(tmp_path)
    manifest, run_dir = _run_live_call_shape(
        tmp_path, packaging_api, output_dir=Path("runs/live_call_shape")
    )

    candidate_ref = manifest["artifacts"]["candidate_graph"]
    candidate_path = (run_dir / "candidate_graph.json").resolve()
    assert candidate_path.is_file()
    on_disk_digest = f"sha256:{_sha256_file(candidate_path)}"
    assert candidate_ref["sha256"] == on_disk_digest

    span_ref = manifest["artifacts"]["source_span_index"]
    span_path = (run_dir / "source_span_index.json").resolve()
    assert span_ref["sha256"] == f"sha256:{_sha256_file(span_path)}"


def test_live_call_shape_validation_report_present_and_valid(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, packaging_api: _PackagingApi
) -> None:
    monkeypatch.chdir(tmp_path)
    manifest, run_dir = _run_live_call_shape(
        tmp_path, packaging_api, output_dir=Path("runs/live_call_shape")
    )

    report_ref = manifest["artifacts"]["candidate_validation_report"]
    report_path = (run_dir / "candidate_validation_report.json").resolve()
    assert report_path.is_file()
    report = json.loads(report_path.read_text(encoding="utf-8"))
    assert report["valid"] is True
    assert report["errors"] == []
    assert report_ref["sha256"] == f"sha256:{_sha256_file(report_path)}"


def test_live_call_shape_threads_immutable_source_artifact_identity(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, packaging_api: _PackagingApi
) -> None:
    """The packaged manifest must carry the production SourceArtifact id, never a legacy id."""
    monkeypatch.chdir(tmp_path)
    manifest, _run_dir = _run_live_call_shape(
        tmp_path, packaging_api, output_dir=Path("runs/live_call_shape")
    )

    source_artifact_id = manifest["source"]["source_artifact_id"]
    assert source_artifact_id != "artifact:recap:longmont-c2:session-24"
    assert manifest["diagnostics"]["candidate_extraction"] is True
    assert manifest["diagnostics"]["extraction_mode"] == "fixture"


def test_live_call_shape_allow_llm_stays_false_no_second_model_call(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, packaging_api: _PackagingApi
) -> None:
    """Guard: supplying a candidate_graph_path must never trigger LLM extraction."""

    class ExplodingClient:
        def run_pass(self, *args: object, **kwargs: object) -> dict:
            raise AssertionError("packaging must not call the category graph pass client")

    monkeypatch.chdir(tmp_path)
    result_manifest, _run_dir = _run_live_call_shape(
        tmp_path,
        packaging_api,
        output_dir=Path("runs/live_call_shape_no_llm"),
        category_client=ExplodingClient(),
    )
    assert result_manifest["status"] == "candidate_validation_ready"


def test_graph_ingest_packaging_live_call_shape_production_module(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Explicit named proof: production module executes the live packaging path.

    Complements the parametrized suite so a grep for the promised test name finds
    a real direct-import exercise of ``graph_ingest_packaging``.
    """
    production = _production_api()
    monkeypatch.chdir(tmp_path)
    manifest, run_dir = _run_live_call_shape(
        tmp_path, production, output_dir=Path("runs/live_call_shape_production")
    )

    assert production.run_graph_preview_extraction.__module__ == (
        "src.graph_memory.extraction.graph_ingest_packaging"
    )
    assert production.GraphPreviewRunnerOptions.__module__ == (
        "src.graph_memory.extraction.graph_ingest_packaging"
    )
    assert manifest["status"] == "candidate_validation_ready"
    report = validate_graph_ingest_run_manifest(manifest)
    assert report["valid"] is True
    assert report["errors"] == []
    candidate_path = (run_dir / "candidate_graph.json").resolve()
    assert candidate_path.is_file()
    assert manifest["artifacts"]["candidate_graph"]["sha256"] == (
        f"sha256:{_sha256_file(candidate_path)}"
    )
