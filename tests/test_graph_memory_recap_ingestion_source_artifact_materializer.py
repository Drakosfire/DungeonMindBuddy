from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path
from typing import Any

import pytest

from src.graph_memory.recap_ingestion_materialize import (
    CREATED_BY,
    INPUT_MODE,
    SCHEMA,
    SOURCE_FAMILY,
    VERSION,
    RecapIngestionMaterializerInput,
    materialize_recap_ingestion_source_artifacts,
    recap_ingestion_materialization_to_dict,
)

REPO_ROOT = Path(__file__).resolve().parents[1]
FIXTURE_DIR = REPO_ROOT / "evals" / "graph_memory_layer" / "examples" / "recap_ingestion_materializer_inputs"
FAMILY_GATE_PATH = REPO_ROOT / "evals" / "graph_memory_layer" / "recap_ingestion_source_family_gate.json"
GATE_PATH = REPO_ROOT / "evals" / "graph_memory_layer" / "recap_ingestion_source_artifact_materializer_gate.json"
REPORT_PATH = REPO_ROOT / "Docs" / "Reports" / "GRAPH-MEMORY-RECAP-INGESTION-SOURCE-ARTIFACT-MATERIALIZER.md"
FIXTURES = {
    "normalized_recap_markdown": FIXTURE_DIR / "normalized_recap_s01.md",
    "breadcrumbed_recap_markdown": FIXTURE_DIR / "breadcrumbed_recap_s01.md",
    "frontmatter_seed_markdown": FIXTURE_DIR / "frontmatter_seed_s01.md",
    "session_memory_jsonl_meta": FIXTURE_DIR / "session_memory_meta_s01.json",
    "corpus_impact_proof": FIXTURE_DIR / "corpus_impact_proof_s01.json",
}
ADAPTER_FIELDS = {"payload_kind", "source_unit_projection", "projection_card", "surface_owned_projection_kind", "plan_chip", "agent_interaction_payload"}


def _load(path: Path) -> dict[str, Any]:
    with path.open(encoding="utf-8") as handle:
        data = json.load(handle)
    assert isinstance(data, dict)
    return data


def _inputs() -> list[RecapIngestionMaterializerInput]:
    return [RecapIngestionMaterializerInput(artifact_id, path) for artifact_id, path in FIXTURES.items()]


def _materialized() -> dict[str, Any]:
    return recap_ingestion_materialization_to_dict(materialize_recap_ingestion_source_artifacts(_inputs()))


def _contains_key(obj: Any, keys: set[str]) -> bool:
    if isinstance(obj, dict):
        return any(key in keys or _contains_key(value, keys) for key, value in obj.items())
    if isinstance(obj, list):
        return any(_contains_key(item, keys) for item in obj)
    return False


def test_validator_exits_zero() -> None:
    result = subprocess.run([sys.executable, "-m", "evals.graph_memory_layer.validate_recap_ingestion_source_artifact_materializer"], cwd=REPO_ROOT, check=False, text=True, capture_output=True)
    assert result.returncode == 0, result.stdout + result.stderr
    assert "- recap-ingestion source artifact materializer: ready" in result.stdout


def test_report_cli_exits_zero() -> None:
    result = subprocess.run([sys.executable, "-m", "evals.graph_memory_layer.report_recap_ingestion_source_artifact_materializer"], cwd=REPO_ROOT, check=False, text=True, capture_output=True)
    assert result.returncode == 0, result.stdout + result.stderr
    assert "# Recap-Ingestion Source Artifact Materializer Report" in result.stdout


def test_synthetic_explicit_input_fixture_files_exist() -> None:
    assert all(path.is_file() for path in FIXTURES.values())


def test_materializer_rejects_empty_inputs() -> None:
    with pytest.raises(ValueError, match="requires at least one"):
        materialize_recap_ingestion_source_artifacts([])


def test_materializer_rejects_directory_input() -> None:
    with pytest.raises(ValueError, match="directory input"):
        materialize_recap_ingestion_source_artifacts([RecapIngestionMaterializerInput("normalized_recap_markdown", FIXTURE_DIR)])


def test_materializer_rejects_unknown_admitted_artifact_id() -> None:
    with pytest.raises(ValueError, match="unknown"):
        materialize_recap_ingestion_source_artifacts([RecapIngestionMaterializerInput("unknown", next(iter(FIXTURES.values())))])


def test_materializer_output_identity_fields_are_correct() -> None:
    data = _materialized()
    assert data["schema"] == SCHEMA
    assert data["version"] == VERSION
    assert data["source_family"] == SOURCE_FAMILY
    assert data["created_by"] == CREATED_BY
    assert data["input_mode"] == INPUT_MODE


def test_all_five_admitted_artifacts_are_materialized_from_explicit_inputs() -> None:
    assert {artifact["admitted_artifact_id"] for artifact in _materialized()["artifacts"]} == set(FIXTURES)


def test_semantic_defaults_match_family_gate_and_materializer_gate() -> None:
    family = {artifact["id"]: artifact for artifact in _load(FAMILY_GATE_PATH)["admitted_artifacts"]}
    gate = {artifact["admitted_artifact_id"]: artifact for artifact in _load(GATE_PATH)["allowed_input_artifacts"]}
    for artifact in _materialized()["artifacts"]:
        artifact_id = artifact["admitted_artifact_id"]
        for field in ["canon_state", "lifecycle_state", "evidence_role", "authority_state", "visibility_state"]:
            assert artifact[field] == family[artifact_id][f"default_{field}"] == gate[artifact_id][f"default_{field}"]


def test_every_artifact_has_at_least_one_anchor_and_unit() -> None:
    data = _materialized()
    anchors = {anchor["source_artifact_id"] for anchor in data["anchors"]}
    units = {unit["source_artifact_id"] for unit in data["units"]}
    for artifact in data["artifacts"]:
        assert artifact["artifact_id"] in anchors
        assert artifact["artifact_id"] in units


def test_every_unit_points_to_local_anchor_and_has_source_ref_provenance_and_canon_state() -> None:
    data = _materialized()
    anchor_ids = {anchor["source_anchor_id"] for anchor in data["anchors"]}
    for unit in data["units"]:
        assert unit["source_anchor_id"] in anchor_ids
        assert unit["source_ref"]
        assert unit["provenance"]
        assert unit["canon_state"]


def test_source_ref_ids_are_stable_unique_and_linked_to_provenance() -> None:
    data = _materialized()
    repeat = _materialized()
    source_ref_ids = [unit["source_ref"]["source_ref_id"] for unit in data["units"]]
    assert len(source_ref_ids) == len(set(source_ref_ids)) == len(data["units"])
    assert source_ref_ids == [unit["source_ref"]["source_ref_id"] for unit in repeat["units"]]
    for unit in data["units"]:
        source_ref_id = unit["source_ref"].get("source_ref_id")
        assert source_ref_id and source_ref_id.startswith("source-ref:")
        assert not any(token in source_ref_id for token in ["/workspace/", "/home/", "/mnt/", "C:\\"])
        for path in FIXTURES.values():
            assert path.read_text(encoding="utf-8").strip() not in source_ref_id
        assert all(provenance.get("source_ref_id") == source_ref_id for provenance in unit["provenance"])


def test_display_summary_is_not_evidence() -> None:
    for unit in _materialized()["units"]:
        assert unit["display_summary"]
        assert unit["diagnostics"]["display_summary_is_evidence"] is False
        assert "evidence" not in unit["display_summary"].lower()


def test_no_full_text_fields_raw_contents_absolute_paths_or_raw_internals_are_emitted() -> None:
    data = _materialized()
    output = json.dumps(data, sort_keys=True)
    assert '"full_text"' not in output and '"text"' not in output and '"content"' not in output
    for path in FIXTURES.values():
        assert path.read_text(encoding="utf-8").strip() not in output
    assert "/workspace/" not in output and "/home/" not in output and "/mnt/" not in output and "C:\\" not in output
    assert "_normalized/" not in output and "_breadcrumbed/" not in output and ".records_meta.jsonl" not in output


def test_no_adapter_payload_fields_or_forbidden_unit_kinds_are_emitted() -> None:
    data = _materialized()
    assert not _contains_key(data, ADAPTER_FIELDS)
    for unit in data["units"]:
        assert not any(part in unit["unit_kind"] for part in ["entity_fact", "relationship_fact", "alias", "promotion", "identity_merge"])


def test_artifact_specific_boundaries_are_preserved() -> None:
    artifacts = {artifact["admitted_artifact_id"]: artifact for artifact in _materialized()["artifacts"]}
    assert artifacts["normalized_recap_markdown"]["evidence_role"] == "source_evidence"
    assert artifacts["breadcrumbed_recap_markdown"]["evidence_role"] == "navigation_hint"
    assert artifacts["frontmatter_seed_markdown"]["canon_state"] != "played_canon"
    assert artifacts["corpus_impact_proof"]["canon_state"] == "diagnostic_only"
    assert artifacts["corpus_impact_proof"]["evidence_role"] == "diagnostic_only"


def test_normalized_recap_forbids_extracted_fact_shapes() -> None:
    normalized_units = [unit for unit in _materialized()["units"] if "normalized_recap_markdown" in unit["source_unit_id"]]
    assert normalized_units
    for unit in normalized_units:
        assert "fact" not in unit["unit_kind"]
        assert "relationship" not in unit["unit_kind"]


def test_design_report_exists_and_states_boundaries() -> None:
    text = REPORT_PATH.read_text(encoding="utf-8")
    assert "Source Ref / Provenance Linkage Hardening v0" in text
    assert "explicitly supplied" in text
    assert "does not discover files" in text
    assert "connect `/plan`" in text
    assert "connect Agent Interaction" in text
    assert "create adapter payloads" in text
    assert "infer entities" in text and "resolve aliases" in text and "infer relationships" in text
    assert "promote facts" in text and "promote canon" in text
