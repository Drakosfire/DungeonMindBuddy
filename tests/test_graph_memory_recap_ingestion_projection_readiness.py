from __future__ import annotations

import subprocess
import sys
from pathlib import Path

from evals.graph_memory_layer.report_recap_ingestion_source_artifact_materializer import DEFAULT_INPUTS
from src.graph_memory.recap_ingestion_materialize import SCHEMA as MATERIALIZER_SCHEMA, SOURCE_FAMILY, RecapIngestionMaterializerInput, materialize_recap_ingestion_source_artifacts
from src.graph_memory.recap_ingestion_materializer_report import REPORT_SCHEMA, analyze_recap_ingestion_materializer_output
from src.graph_memory.recap_ingestion_projection_readiness import READINESS_SCHEMA, READINESS_VERSION, ANCHOR_CHECKS, ARTIFACT_CHECKS, EVIDENCE_CHECKS, REQUIRED_CHECK_IDS, SAFETY_CHECKS, UNIT_CHECKS, assess_recap_ingestion_projection_readiness, render_recap_ingestion_projection_readiness_report

REPO_ROOT = Path(__file__).resolve().parents[1]
DESIGN_REPORT = REPO_ROOT / "Docs" / "Reports" / "archive" / "2026-06-28" / "graph-memory" / "GRAPH-MEMORY-RECAP-INGESTION-PROJECTION-READINESS.md"


def _materialization():
    return materialize_recap_ingestion_source_artifacts([RecapIngestionMaterializerInput(k, v) for k, v in DEFAULT_INPUTS.items()])


def _report():
    materialization = _materialization()
    return assess_recap_ingestion_projection_readiness(materialization, analyze_recap_ingestion_materializer_output(materialization))


def test_validator_exits_zero() -> None:
    result = subprocess.run([sys.executable, "-m", "evals.graph_memory_layer.validate_recap_ingestion_projection_readiness"], cwd=REPO_ROOT, text=True, capture_output=True)
    assert result.returncode == 0, result.stdout + result.stderr
    assert "recap-ingestion projection-readiness: ready" in result.stdout


def test_report_cli_exits_zero() -> None:
    result = subprocess.run([sys.executable, "-m", "evals.graph_memory_layer.report_recap_ingestion_projection_readiness"], cwd=REPO_ROOT, text=True, capture_output=True)
    assert result.returncode == 0, result.stdout + result.stderr
    assert "# Recap-Ingestion Projection-Readiness Report" in result.stdout


def test_schema_and_materializer_references() -> None:
    report = _report()
    assert report.schema == READINESS_SCHEMA
    assert report.version == READINESS_VERSION
    assert report.source_family == SOURCE_FAMILY
    assert report.materializer_schema == MATERIALIZER_SCHEMA
    assert report.materializer_report_schema == REPORT_SCHEMA


def test_required_checks_and_expected_ready_groups() -> None:
    by_id = {check.check_id: check for check in _report().checks}
    assert set(REQUIRED_CHECK_IDS).issubset(by_id)
    for check_id in ARTIFACT_CHECKS | ANCHOR_CHECKS | UNIT_CHECKS | EVIDENCE_CHECKS | SAFETY_CHECKS:
        assert by_id[check_id].status == "ready"


def test_source_ref_and_provenance_linkage_are_ready() -> None:
    report = _report()
    by_id = {check.check_id: check for check in report.checks}
    assert by_id["all_source_refs_have_stable_source_ref_id"].status == "ready"
    assert by_id["all_provenance_records_link_to_source_ref_id"].status == "ready"
    assert not any(issue.code == "missing_source_ref_id" and issue.severity == "blocker" for issue in report.issues)
    assert not any(issue.code == "missing_provenance_source_ref_link" and issue.severity == "blocker" for issue in report.issues)
    assert report.readiness_status == "ready"


def test_rendered_report_sections_and_no_leaks() -> None:
    rendered = render_recap_ingestion_projection_readiness_report(_report())
    for phrase in ("## Readiness Summary", "## Checks", "## Blocked Items", "## Issues", "## Deferred Work", "not a production adapter", "does not connect `/plan`", "does not connect Agent Interaction"):
        assert phrase in rendered
    assert "/workspace/" not in rendered
    for path in DEFAULT_INPUTS.values():
        assert path.read_text(encoding="utf-8").strip() not in rendered


def test_design_report_states_boundaries() -> None:
    text = DESIGN_REPORT.read_text(encoding="utf-8")
    assert "After hardening" in text
    for phrase in ("does not implement a projection adapter", "does not mean production-ready", "does not connect `/plan`", "does not connect Agent Interaction", "does not perform graph retrieval", "does not mutate corpus files", "does not infer entities", "does not resolve aliases", "does not infer relationships", "does not promote facts", "does not promote canon"):
        assert phrase in text
