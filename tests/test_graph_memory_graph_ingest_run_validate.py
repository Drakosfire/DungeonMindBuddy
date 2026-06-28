from __future__ import annotations

import copy
import json
from pathlib import Path

from graph_memory.ingestion import validate_graph_ingest_run_manifest

FIXTURE_DIR = Path("tests/fixtures/graph_memory/ingestion")


def load_fixture(name: str) -> dict:
    return json.loads((FIXTURE_DIR / name).read_text())


def test_minimal_source_ready_manifest_validates() -> None:
    report = validate_graph_ingest_run_manifest(
        load_fixture("graph_ingest_run_manifest_minimal.json")
    )

    assert report["valid"] is True
    assert report["errors"] == []
    assert report["campaign_id"] == "longmont-c2"
    assert report["status"] == "source_ready"
    assert report["preview_only"] is True


def test_ready_for_projection_manifest_validates() -> None:
    report = validate_graph_ingest_run_manifest(
        load_fixture("graph_ingest_run_manifest_ready_for_projection.json")
    )

    assert report["valid"] is True
    assert report["errors"] == []
    assert "candidate_graph" in report["artifact_kinds"]
    assert "preview_union_store" in report["artifact_kinds"]
    assert report["projection_ready"] is True


def test_invalid_promoted_manifest_fails_validation() -> None:
    report = validate_graph_ingest_run_manifest(
        load_fixture("graph_ingest_run_manifest_invalid_promoted.json")
    )

    assert report["valid"] is False
    assert "forbidden diagnostic flag is true: canon_promotion" in report["errors"]
    assert (
        "forbidden diagnostic flag is true: approved_memory_write" in report["errors"]
    )
    assert "forbidden diagnostic flag is true: corpus_mutation" in report["errors"]
    assert "forbidden diagnostic flag is true: production_retrieval" in report["errors"]


def test_ready_for_projection_requires_preview_union_store() -> None:
    payload = load_fixture("graph_ingest_run_manifest_ready_for_projection.json")
    del payload["artifacts"]["preview_union_store"]

    report = validate_graph_ingest_run_manifest(payload)

    assert report["valid"] is False
    assert (
        "ready_for_projection requires a preview_union_store artifact"
        in report["errors"]
    )


def test_ready_for_projection_requires_projection_locator() -> None:
    payload = load_fixture("graph_ingest_run_manifest_ready_for_projection.json")
    payload["projection"] = None

    report = validate_graph_ingest_run_manifest(payload)

    assert report["valid"] is False
    assert "ready_for_projection requires a projection locator" in report["errors"]


def test_repo_relative_paths_pass_validation() -> None:
    payload = load_fixture("graph_ingest_run_manifest_ready_for_projection.json")

    report = validate_graph_ingest_run_manifest(payload)

    assert report["valid"] is True
    assert not any("unsafe repo-relative path" in error for error in report["errors"])


def test_absolute_paths_fail_validation() -> None:
    payload = load_fixture("graph_ingest_run_manifest_ready_for_projection.json")
    payload["artifacts"]["preview_union_store"]["uri"] = (
        "/tmp/preview_union_supergraph.json"
    )

    report = validate_graph_ingest_run_manifest(payload)

    assert report["valid"] is False
    assert any("unsafe repo-relative path" in error for error in report["errors"])


def test_traversal_paths_fail_validation() -> None:
    payload = load_fixture("graph_ingest_run_manifest_ready_for_projection.json")
    payload["source"]["source_span_bundle_uri"] = "evals/../secret"

    report = validate_graph_ingest_run_manifest(payload)

    assert report["valid"] is False
    assert any("unsafe repo-relative path" in error for error in report["errors"])


def test_non_json_safe_values_fail_validation() -> None:
    payload = load_fixture("graph_ingest_run_manifest_minimal.json")
    payload["warnings"] = {"not", "json", "safe"}

    report = validate_graph_ingest_run_manifest(payload)

    assert report["valid"] is False
    assert any(error.startswith("non-JSON-safe value") for error in report["errors"])


def test_diagnostics_preview_only_is_enforced() -> None:
    payload = load_fixture("graph_ingest_run_manifest_ready_for_projection.json")
    payload["diagnostics"]["preview_only"] = False

    report = validate_graph_ingest_run_manifest(payload)

    assert report["valid"] is False
    assert "diagnostics.preview_only must be true" in report["errors"]


def test_unknown_schema_fails_validation() -> None:
    payload = copy.deepcopy(load_fixture("graph_ingest_run_manifest_minimal.json"))
    payload["schema"] = "unknown"

    report = validate_graph_ingest_run_manifest(payload)

    assert report["valid"] is False
    assert "unknown schema" in report["errors"]
