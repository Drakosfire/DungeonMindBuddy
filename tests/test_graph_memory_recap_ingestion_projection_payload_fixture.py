from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

from evals.graph_memory_layer.build_recap_ingestion_projection_payload_fixture import FIXTURE_PATH, SCHEMA, VERSION
from evals.graph_memory_layer.report_recap_ingestion_source_artifact_materializer import DEFAULT_INPUTS
from src.graph_memory.recap_ingestion_materialize import SOURCE_FAMILY, RecapIngestionMaterializerInput, materialize_recap_ingestion_source_artifacts
from src.graph_memory.recap_ingestion_materializer_report import analyze_recap_ingestion_materializer_output
from src.graph_memory.recap_ingestion_projection_readiness import assess_recap_ingestion_projection_readiness

REPO_ROOT = Path(__file__).resolve().parents[1]
DESIGN_REPORT = REPO_ROOT / "Docs" / "Reports" / "GRAPH-MEMORY-RECAP-INGESTION-PROJECTION-PAYLOAD-FIXTURE.md"
EXPECTED_ARTIFACTS = {"normalized_recap_markdown", "breadcrumbed_recap_markdown", "frontmatter_seed_markdown", "session_memory_jsonl_meta", "corpus_impact_proof"}
REQUIRED_FIELDS = {"payload_unit_id", "source_unit_id", "source_ref_id", "admitted_artifact_id", "artifact_kind", "projection_kind", "display_label", "display_summary", "semantic_state", "source_handle", "provenance", "safety"}
SEMANTIC_FIELDS = {"canon_state", "lifecycle_state", "evidence_role", "authority_state", "visibility_state"}
FORBIDDEN = {"full_text", "raw_text", "content", "raw_content", "file_contents", "plan_chip", "plan_card", "agent_payload", "agent_interaction", "runtime_ui_payload", "ui_payload", "entity", "entities", "alias", "aliases", "relationship", "relationships", "fact", "facts", "canon_promotion", "fact_promotion"}


def _fixture() -> dict[str, object]:
    return json.loads(FIXTURE_PATH.read_text(encoding="utf-8"))


def _materialization():
    return materialize_recap_ingestion_source_artifacts([RecapIngestionMaterializerInput(k, v) for k, v in DEFAULT_INPUTS.items()])


def test_validator_exits_zero() -> None:
    result = subprocess.run([sys.executable, "-m", "evals.graph_memory_layer.validate_recap_ingestion_projection_payload_fixture"], cwd=REPO_ROOT, text=True, capture_output=True)
    assert result.returncode == 0, result.stdout + result.stderr
    assert "recap-ingestion projection payload fixture: ready" in result.stdout


def test_report_cli_exits_zero() -> None:
    result = subprocess.run([sys.executable, "-m", "evals.graph_memory_layer.report_recap_ingestion_projection_payload_fixture"], cwd=REPO_ROOT, text=True, capture_output=True)
    assert result.returncode == 0, result.stdout + result.stderr
    assert "# Recap-Ingestion Projection Payload Fixture Report" in result.stdout


def test_static_fixture_schema_and_artifact_coverage() -> None:
    fixture = _fixture()
    assert FIXTURE_PATH.is_file()
    assert fixture["schema"] == SCHEMA
    assert fixture["version"] == VERSION
    assert fixture["source_family"] == SOURCE_FAMILY
    units = fixture["payload_units"]
    assert {unit["admitted_artifact_id"] for unit in units} == EXPECTED_ARTIFACTS


def test_payload_units_are_linked_and_surface_safe() -> None:
    fixture = _fixture()
    source_ref_ids = {unit.source_ref["source_ref_id"] for unit in _materialization().units}
    serialized = json.dumps(fixture, sort_keys=True)
    for unit in fixture["payload_units"]:
        assert REQUIRED_FIELDS.issubset(unit)
        assert unit["source_ref_id"]
        assert unit["source_ref_id"] in source_ref_ids
        assert unit["provenance"]["source_ref_id"] == unit["source_ref_id"]
        assert SEMANTIC_FIELDS.issubset(unit["semantic_state"])
        assert unit["display_summary"]
        assert unit["safety"]["display_summary_is_evidence"] is False
        assert unit["source_handle"]["handle_id"].startswith("opaque-source-handle:")
        assert "/workspace/" not in json.dumps(unit["source_handle"], sort_keys=True)
    for path in DEFAULT_INPUTS.values():
        assert path.read_text(encoding="utf-8").strip() not in serialized
    assert "/workspace/" not in serialized
    assert not any(f'"{field}"' in serialized for field in FORBIDDEN)


def test_readiness_status_must_be_ready_before_fixture_is_accepted() -> None:
    materialization = _materialization()
    readiness = assess_recap_ingestion_projection_readiness(materialization, analyze_recap_ingestion_materializer_output(materialization))
    assert readiness.readiness_status == "ready"


def test_design_report_states_boundaries() -> None:
    text = DESIGN_REPORT.read_text(encoding="utf-8")
    for phrase in ("not a production adapter", "not a `/plan` payload", "not an Agent Interaction payload", "not a retrieval result", "does not mutate corpus files", "does not infer entities", "does not resolve aliases", "does not infer relationships", "does not promote facts", "does not promote canon"):
        assert phrase in text
