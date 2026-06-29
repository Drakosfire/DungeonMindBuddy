from __future__ import annotations

import subprocess
import sys
from pathlib import Path

from evals.graph_memory_layer.report_recap_ingestion_source_artifact_materializer import DEFAULT_INPUTS
from src.graph_memory.recap_ingestion_materialize import (
    CREATED_BY,
    SCHEMA as MATERIALIZER_SCHEMA,
    SOURCE_FAMILY,
    RecapIngestionMaterializerInput,
    materialize_recap_ingestion_source_artifacts,
)
from src.graph_memory.recap_ingestion_materializer_report import (
    REPORT_SCHEMA,
    REPORT_VERSION,
    analyze_recap_ingestion_materializer_output,
    recap_ingestion_materializer_report_to_dict,
    render_recap_ingestion_materializer_report,
)

REPO_ROOT = Path(__file__).resolve().parents[1]
DESIGN_REPORT = REPO_ROOT / "Docs" / "Reports" / "archive" / "2026-06-28" / "graph-memory" / "GRAPH-MEMORY-RECAP-INGESTION-SOURCE-ARTIFACT-MATERIALIZER-REPORT.md"


def _materialization():
    inputs = [RecapIngestionMaterializerInput(artifact_id, path) for artifact_id, path in DEFAULT_INPUTS.items()]
    return materialize_recap_ingestion_source_artifacts(inputs)


def _report():
    return analyze_recap_ingestion_materializer_output(_materialization())


def test_validator_exits_zero() -> None:
    result = subprocess.run([sys.executable, "-m", "evals.graph_memory_layer.validate_recap_ingestion_source_artifact_materializer_report"], cwd=REPO_ROOT, text=True, capture_output=True)
    assert result.returncode == 0, result.stdout + result.stderr
    assert "recap-ingestion source artifact materializer report: ready" in result.stdout


def test_report_cli_exits_zero() -> None:
    result = subprocess.run([sys.executable, "-m", "evals.graph_memory_layer.report_recap_ingestion_source_artifact_materializer_diagnostics"], cwd=REPO_ROOT, text=True, capture_output=True)
    assert result.returncode == 0, result.stdout + result.stderr
    assert "# Recap-Ingestion Source Artifact Materializer Diagnostics Report" in result.stdout


def test_analyzer_identity_and_materializer_reference() -> None:
    report = _report()
    assert report.schema == REPORT_SCHEMA
    assert report.version == REPORT_VERSION
    assert report.source_family == SOURCE_FAMILY
    assert report.materializer_schema == MATERIALIZER_SCHEMA
    assert report.materializer_created_by == CREATED_BY


def test_artifact_rows_totals_and_states_match_materializer() -> None:
    materialization = _materialization()
    report = analyze_recap_ingestion_materializer_output(materialization)
    assert {row.admitted_artifact_id for row in report.artifact_rows} == set(DEFAULT_INPUTS)
    assert report.total_artifacts == len(materialization.artifacts)
    assert report.total_anchors == len(materialization.anchors)
    assert report.total_units == len(materialization.units)
    assert report.total_source_refs == len(materialization.units)
    assert report.total_provenance_records == sum(len(unit.provenance) for unit in materialization.units)
    observed_states = set()
    for counts in report.state_counts.values():
        observed_states.update(counts)
    assert {"source_evidence", "navigation_hint", "not_evidence", "diagnostic_only", "played_canon", "planning_scaffold", "candidate_extraction"}.issubset(observed_states)


def test_structural_coverage_and_boundaries() -> None:
    report = _report()
    required = {
        "all_artifacts_have_anchor",
        "all_artifacts_have_unit",
        "all_units_have_source_ref",
        "all_units_have_provenance",
        "all_units_have_canon_state",
        "all_units_have_display_summary",
        "all_units_have_display_summary_marked_non_evidence",
        "all_units_have_source_ref_id",
        "all_provenance_records_link_to_source_ref_id",
        "absolute_path_leak_count",
        "full_text_field_count",
        "adapter_payload_field_count",
        "forbidden_unit_kind_count",
    }
    assert required.issubset(report.structural_coverage)
    assert report.structural_coverage["all_artifacts_have_anchor"] is True
    assert report.structural_coverage["all_artifacts_have_unit"] is True
    assert report.structural_coverage["all_units_have_source_ref"] is True
    assert report.structural_coverage["all_units_have_provenance"] is True
    assert report.structural_coverage["all_units_have_canon_state"] is True
    assert report.structural_coverage["all_units_have_display_summary_marked_non_evidence"] is True
    assert report.structural_coverage["full_text_field_count"] == 0
    assert report.structural_coverage["absolute_path_leak_count"] == 0
    assert report.structural_coverage["adapter_payload_field_count"] == 0
    assert report.structural_coverage["forbidden_unit_kind_count"] == 0


def test_source_ref_and_provenance_linkage_are_ready() -> None:
    report = _report()
    assert report.structural_coverage["all_units_have_source_ref_id"] is True
    assert report.structural_coverage["all_provenance_records_link_to_source_ref_id"] is True
    assert report.issue_counts.get("missing_source_ref_id", 0) == 0
    assert report.issue_counts.get("missing_provenance_source_ref_link", 0) == 0


def test_rendered_report_contains_sections_and_no_raw_contents() -> None:
    report = _report()
    rendered = render_recap_ingestion_materializer_report(report)
    for phrase in ("## Summary", "## Artifact Rows", "## State Counts", "## Structural Coverage", "## Issues", "display_summary is not evidence", "not a production adapter payload"):
        assert phrase in rendered
    serialized = str(recap_ingestion_materializer_report_to_dict(report)) + rendered
    assert "\'full_text\':" not in serialized
    assert "\"full_text\":" not in serialized
    assert "/workspace/" not in serialized
    for path in DEFAULT_INPUTS.values():
        assert path.read_text(encoding="utf-8").strip() not in serialized


def test_design_report_states_boundaries() -> None:
    text = DESIGN_REPORT.read_text(encoding="utf-8")
    assert "Source Ref / Provenance Linkage Hardening v0" in text
    assert "does not implement projection-readiness" in text
    assert "does not create adapter payloads" in text
    assert "does not connect `/plan`" in text
    assert "does not change runtime behavior" in text
    assert "`display_summary` is not evidence." in text
