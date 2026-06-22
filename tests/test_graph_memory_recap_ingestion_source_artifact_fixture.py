from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path
from typing import Any

REPO_ROOT = Path(__file__).resolve().parents[1]
GATE_PATH = REPO_ROOT / "evals" / "graph_memory_layer" / "recap_ingestion_source_family_gate.json"
FIXTURE_PATH = REPO_ROOT / "evals" / "graph_memory_layer" / "examples" / "recap_ingestion_source_artifacts_minimal.json"
REPORT_PATH = REPO_ROOT / "Docs" / "Reports" / "GRAPH-MEMORY-RECAP-INGESTION-SOURCE-ARTIFACT-FIXTURE.md"
EXPECTED_ARTIFACT_IDS = {
    "normalized_recap_markdown",
    "breadcrumbed_recap_markdown",
    "frontmatter_seed_markdown",
    "session_memory_jsonl_meta",
    "corpus_impact_proof",
}
SEMANTIC_FIELDS = {"canon_state", "lifecycle_state", "evidence_role", "authority_state", "visibility_state"}
FORBIDDEN_FULL_TEXT_FIELDS = {"lexical_plain", "full_text", "markdown_body", "raw_text", "recap_text"}
FORBIDDEN_UNIT_KINDS = {"entity_fact", "relationship_fact", "alias_merge", "promotion_record"}


def _load(path: Path) -> dict[str, Any]:
    with path.open(encoding="utf-8") as handle:
        data = json.load(handle)
    assert isinstance(data, dict)
    return data


def _fixture() -> dict[str, Any]:
    return _load(FIXTURE_PATH)


def _gate_artifacts() -> dict[str, dict[str, Any]]:
    return {artifact["id"]: artifact for artifact in _load(GATE_PATH)["admitted_artifacts"]}


def _artifacts() -> dict[str, dict[str, Any]]:
    return {artifact["admitted_artifact_id"]: artifact for artifact in _fixture()["artifacts"]}


def _walk(value: Any):
    if isinstance(value, dict):
        for key, child in value.items():
            yield key, child
            yield from _walk(child)
    elif isinstance(value, list):
        for child in value:
            yield from _walk(child)


def test_fixture_file_exists() -> None:
    assert FIXTURE_PATH.is_file()


def test_validator_exits_zero() -> None:
    result = subprocess.run(
        [sys.executable, "-m", "evals.graph_memory_layer.validate_recap_ingestion_source_artifact_fixture"],
        cwd=REPO_ROOT,
        check=False,
        text=True,
        capture_output=True,
    )
    assert result.returncode == 0, result.stdout + result.stderr
    assert "- recap-ingestion source artifact fixture: ready" in result.stdout


def test_fixture_identity_fields_are_correct() -> None:
    fixture = _fixture()
    assert fixture["schema"] == "dmb_recap_ingestion_source_artifact_fixture_v0"
    assert fixture["version"] == "0.1"
    assert fixture["source_family"] == "recap_ingestion_source_artifacts"


def test_fixture_covers_all_gate_admitted_artifacts() -> None:
    assert EXPECTED_ARTIFACT_IDS.issubset(set(_artifacts()))


def test_every_fixture_artifact_is_gate_admitted() -> None:
    assert set(_artifacts()).issubset(set(_gate_artifacts()))


def test_every_artifact_includes_required_semantic_envelope_fields() -> None:
    required = {"artifact_id", "admitted_artifact_id", "artifact_kind", "source_layer", "label", *SEMANTIC_FIELDS, "locator", "anchors", "units", "forbidden_interpretations"}
    for artifact in _artifacts().values():
        assert required.issubset(artifact)


def test_every_artifact_semantic_defaults_match_gate_manifest() -> None:
    gate = _gate_artifacts()
    for admitted_id, artifact in _artifacts().items():
        for field in SEMANTIC_FIELDS:
            assert artifact[field] == gate[admitted_id][f"default_{field}"]


def test_every_artifact_has_anchor_and_unit() -> None:
    for artifact in _artifacts().values():
        assert artifact["anchors"]
        assert artifact["units"]


def test_every_unit_points_to_anchor_in_same_artifact() -> None:
    for artifact in _artifacts().values():
        anchor_ids = {anchor["source_anchor_id"] for anchor in artifact["anchors"]}
        for unit in artifact["units"]:
            assert unit["source_anchor_id"] in anchor_ids


def test_every_unit_has_source_ref_and_provenance_and_canon_state() -> None:
    for artifact in _artifacts().values():
        for unit in artifact["units"]:
            assert unit["source_ref"]["source_artifact_id"] == artifact["artifact_id"]
            assert unit["source_ref"]["source_anchor_id"] == unit["source_anchor_id"]
            assert unit["provenance"]
            assert "canon_state" in unit


def test_display_summary_is_not_evidence() -> None:
    for artifact in _artifacts().values():
        for unit in artifact["units"]:
            assert unit["display_summary"]
            assert unit["display_summary"] != unit["evidence_role"]


def test_corpus_impact_proof_is_diagnostic_only() -> None:
    artifact = _artifacts()["corpus_impact_proof"]
    assert artifact["canon_state"] == "diagnostic_only"
    assert artifact["evidence_role"] == "diagnostic_only"


def test_frontmatter_seed_is_not_played_canon() -> None:
    assert _artifacts()["frontmatter_seed_markdown"]["canon_state"] != "played_canon"


def test_breadcrumbed_recap_is_navigation_hint_not_source_evidence() -> None:
    assert _artifacts()["breadcrumbed_recap_markdown"]["evidence_role"] == "navigation_hint"
    assert _artifacts()["breadcrumbed_recap_markdown"]["evidence_role"] != "source_evidence"


def test_normalized_recap_forbids_extracted_fact_shapes() -> None:
    forbidden = set(_artifacts()["normalized_recap_markdown"]["forbidden_interpretations"])
    assert FORBIDDEN_UNIT_KINDS.issubset(forbidden)


def test_no_full_text_or_absolute_local_paths_or_raw_internals() -> None:
    for key, value in _walk(_fixture()):
        assert key not in FORBIDDEN_FULL_TEXT_FIELDS
        assert key not in {"_normalized", "_breadcrumbed", ".records_meta.jsonl", "corpus_impact"}
        if isinstance(value, str):
            assert "/workspace/" not in value and "/home/" not in value and "C:\\" not in value
            assert "_normalized/" not in value and "_breadcrumbed/" not in value
            assert ".records_meta.jsonl" not in value


def test_no_unit_kind_is_forbidden_fact_alias_or_promotion() -> None:
    for artifact in _artifacts().values():
        for unit in artifact["units"]:
            assert unit["unit_kind"] not in FORBIDDEN_UNIT_KINDS


def test_report_doc_exists() -> None:
    assert REPORT_PATH.is_file()


def test_report_doc_states_boundaries() -> None:
    text = REPORT_PATH.read_text(encoding="utf-8")
    assert "does not read real recap-ingestion outputs" in text
    assert "does not implement a materializer" in text
    assert "does not implement an adapter" in text
    assert "does not change runtime behavior" in text
    assert "`display_summary` is a display convenience. It is not evidence." in text
    assert "`corpus_impact_proof` is proof of ingestion behavior, not proof of narrative truth." in text
