from __future__ import annotations

import json
import sys

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

REQUIRED_COVERAGE_KEYS = {
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
EXPECTED_STATES = {"source_evidence", "navigation_hint", "not_evidence", "diagnostic_only", "played_canon", "planning_scaffold", "candidate_extraction"}


def _require(condition: bool, message: str) -> None:
    if not condition:
        raise AssertionError(message)


def main() -> int:
    print("Graph Memory recap-ingestion source artifact materializer report validation")
    inputs = [RecapIngestionMaterializerInput(artifact_id, path) for artifact_id, path in DEFAULT_INPUTS.items()]
    materialization = materialize_recap_ingestion_source_artifacts(inputs)
    print("- explicit input materializer: ready")
    report = analyze_recap_ingestion_materializer_output(materialization)
    data = recap_ingestion_materializer_report_to_dict(report)
    rendered = render_recap_ingestion_materializer_report(report)
    print("- report analyzer: ready")
    _require(report.schema == REPORT_SCHEMA and report.version == REPORT_VERSION, "bad report schema/version")
    _require(report.source_family == SOURCE_FAMILY, "bad source family")
    _require(report.materializer_schema == MATERIALIZER_SCHEMA, "bad materializer schema")
    _require(report.materializer_created_by == CREATED_BY, "bad materializer created_by")
    print(f"- schema: {REPORT_SCHEMA}")
    _require({row.admitted_artifact_id for row in report.artifact_rows} == set(DEFAULT_INPUTS), "not all artifact families represented")
    _require(len(report.artifact_rows) == len(materialization.artifacts), "per-artifact rows missing")
    print("- artifact coverage: ready")
    _require(report.total_artifacts == len(materialization.artifacts), "artifact total mismatch")
    _require(report.total_anchors == len(materialization.anchors), "anchor total mismatch")
    _require(report.total_units == len(materialization.units), "unit total mismatch")
    _require(report.total_source_refs == len(materialization.units), "source ref total mismatch")
    _require(report.total_provenance_records == sum(len(unit.provenance) for unit in materialization.units), "provenance total mismatch")
    _require(report.total_diagnostics == len(materialization.diagnostics), "diagnostic total mismatch")
    print("- summary totals: ready")
    observed_states = set()
    for counts in report.state_counts.values():
        observed_states.update(counts)
    _require(EXPECTED_STATES.issubset(observed_states), "expected semantic states missing")
    print("- state counts: ready")
    _require(REQUIRED_COVERAGE_KEYS.issubset(report.structural_coverage), "coverage keys missing")
    _require(report.structural_coverage["all_artifacts_have_anchor"], "artifact anchor coverage missing")
    _require(report.structural_coverage["all_artifacts_have_unit"], "artifact unit coverage missing")
    _require(report.structural_coverage["all_units_have_source_ref"], "source ref coverage missing")
    _require(report.structural_coverage["all_units_have_provenance"], "provenance coverage missing")
    _require(report.structural_coverage["all_units_have_canon_state"], "canon state coverage missing")
    _require(report.structural_coverage["all_units_have_display_summary_marked_non_evidence"], "display_summary evidence boundary missing")
    print("- structural coverage: ready")
    source_ref_gap = not report.structural_coverage["all_units_have_source_ref_id"]
    provenance_gap = not report.structural_coverage["all_provenance_records_link_to_source_ref_id"]
    _require((not source_ref_gap) or report.issue_counts.get("missing_source_ref_id", 0) > 0, "source_ref_id gap not surfaced")
    _require((not provenance_gap) or report.issue_counts.get("missing_provenance_source_ref_link", 0) > 0, "provenance linkage gap not surfaced")
    print("- issue classification: ready")
    _require(report.structural_coverage["full_text_field_count"] == 0, "full text field leak")
    output = json.dumps(data, sort_keys=True) + rendered
    for path in DEFAULT_INPUTS.values():
        _require(path.read_text(encoding="utf-8").strip() not in output, f"raw file contents leaked: {path.name}")
    print("- no full text leakage: ready")
    _require(report.structural_coverage["absolute_path_leak_count"] == 0, "absolute path leak")
    print("- no absolute path leakage: ready")
    _require(report.structural_coverage["adapter_payload_field_count"] == 0, "adapter payload leak")
    _require(report.structural_coverage["forbidden_unit_kind_count"] == 0, "forbidden unit kind")
    print("- no adapter payload leakage: ready")
    for phrase in ("# Recap-Ingestion Source Artifact Materializer Diagnostics Report", "## Summary", "## Artifact Rows", "## State Counts", "## Structural Coverage", "## Issues", "display_summary is not evidence", "not a production adapter payload"):
        _require(phrase in rendered, f"rendered report missing: {phrase}")
    print("- recap-ingestion source artifact materializer report: ready")
    return 0


if __name__ == "__main__":
    try:
        sys.exit(main())
    except (AssertionError, json.JSONDecodeError, ValueError) as exc:
        print(f"- recap-ingestion source artifact materializer report: blocked ({exc})", file=sys.stderr)
        sys.exit(1)
