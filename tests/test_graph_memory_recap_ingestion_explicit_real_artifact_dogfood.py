from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

from evals.graph_memory_layer.recap_ingestion_real_artifact_dogfood import MANIFEST_SCHEMA, MANIFEST_VERSION, build_dogfood_materializer_inputs, dogfood_fixture_dir, load_dogfood_manifest
from evals.graph_memory_layer.validate_recap_ingestion_explicit_real_artifact_dogfood import FORBIDDEN_FIELDS, build_dogfood_projection_payload, validate_dogfood
from src.graph_memory.recap_ingestion_materialize import INPUT_MODE, SOURCE_FAMILY, materialize_recap_ingestion_source_artifacts
from src.graph_memory.recap_ingestion_materializer_report import KNOWN_ARTIFACT_FAMILIES, analyze_recap_ingestion_materializer_output, recap_ingestion_materializer_report_to_dict
from src.graph_memory.recap_ingestion_projection_readiness import assess_recap_ingestion_projection_readiness, recap_ingestion_projection_readiness_to_dict


def test_validator_and_report_cli_exit_zero() -> None:
    for module in (
        "evals.graph_memory_layer.validate_recap_ingestion_explicit_real_artifact_dogfood",
        "evals.graph_memory_layer.report_recap_ingestion_explicit_real_artifact_dogfood",
    ):
        completed = subprocess.run([sys.executable, "-m", module], check=False, text=True, capture_output=True)
        assert completed.returncode == 0, completed.stderr


def test_dogfood_manifest_contract() -> None:
    manifest_path = dogfood_fixture_dir() / "dogfood_manifest.json"
    assert manifest_path.is_file()
    manifest = load_dogfood_manifest()
    assert manifest["schema"] == MANIFEST_SCHEMA
    assert manifest["version"] == MANIFEST_VERSION
    assert manifest["source_family"] == SOURCE_FAMILY
    assert manifest["input_mode"] == INPUT_MODE
    artifact_inputs = manifest["artifact_inputs"]
    assert isinstance(artifact_inputs, list) and len(artifact_inputs) == 5
    assert {item["admitted_artifact_id"] for item in artifact_inputs} == KNOWN_ARTIFACT_FAMILIES
    for item in artifact_inputs:
        rel = Path(item["relative_path"])
        assert not rel.is_absolute()
        assert ".." not in rel.parts


def test_dogfood_materializer_and_projection_chain() -> None:
    inputs = build_dogfood_materializer_inputs()
    assert len(inputs) == 5
    materialization = materialize_recap_ingestion_source_artifacts(inputs)
    assert len(materialization.artifacts) == 5
    assert len(materialization.units) == 5
    for unit in materialization.units:
        assert unit.source_ref.get("source_ref_id")
        assert all(record.get("source_ref_id") == unit.source_ref["source_ref_id"] for record in unit.provenance)
    report = analyze_recap_ingestion_materializer_output(materialization)
    readiness = assess_recap_ingestion_projection_readiness(materialization, report)
    assert readiness.readiness_status == "ready"
    payload = build_dogfood_projection_payload()
    assert len(payload["payload_units"]) == 5
    validate_dogfood()


def test_reports_and_payloads_preserve_boundaries() -> None:
    inputs = build_dogfood_materializer_inputs()
    materialization = materialize_recap_ingestion_source_artifacts(inputs)
    report = analyze_recap_ingestion_materializer_output(materialization)
    readiness = assess_recap_ingestion_projection_readiness(materialization, report)
    payload = build_dogfood_projection_payload()
    serialized = json.dumps({"report": recap_ingestion_materializer_report_to_dict(report), "readiness": recap_ingestion_projection_readiness_to_dict(readiness), "payload": payload}, sort_keys=True)
    for explicit_input in inputs:
        assert explicit_input.path.read_text(encoding="utf-8").strip() not in serialized
    assert "/workspace/" not in serialized
    assert "/home/" not in serialized
    assert "/mnt/" not in serialized
    keys = set()
    def walk(obj: object) -> None:
        if isinstance(obj, dict):
            keys.update(str(k) for k in obj)
            for value in obj.values():
                walk(value)
        elif isinstance(obj, list):
            for value in obj:
                walk(value)
    walk(payload)
    assert not (keys & FORBIDDEN_FIELDS)


def test_design_report_exists_and_states_boundaries() -> None:
    text = Path("Docs/Reports/archive/2026-06-28/graph-memory/GRAPH-MEMORY-RECAP-INGESTION-EXPLICIT-REAL-ARTIFACT-DOGFOOD.md").read_text(encoding="utf-8")
    for phrase in (
        "This dogfood fixture tests the explicit-input recap-ingestion materializer and projection payload chain against one manually selected real or real-derived artifact bundle.",
        "This is not directory scanning, not corpus scanning, not runtime ingestion, not a production adapter, not a `/plan` payload, not an Agent Interaction payload, and not a retrieval result.",
        "The fixture may contain dogfood input text, but reports and projection payloads must not copy full raw file contents.",
        "This dogfood does not infer entities, does not resolve aliases, does not infer relationships, does not promote facts, and does not promote canon.",
    ):
        assert phrase in text
