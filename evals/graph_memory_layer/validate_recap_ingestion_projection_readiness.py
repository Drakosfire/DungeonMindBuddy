from __future__ import annotations

import json
import sys

from evals.graph_memory_layer.report_recap_ingestion_source_artifact_materializer import DEFAULT_INPUTS
from src.graph_memory.recap_ingestion_materialize import SCHEMA as MATERIALIZER_SCHEMA, SOURCE_FAMILY, RecapIngestionMaterializerInput, materialize_recap_ingestion_source_artifacts
from src.graph_memory.recap_ingestion_materializer_report import REPORT_SCHEMA, analyze_recap_ingestion_materializer_output
from src.graph_memory.recap_ingestion_projection_readiness import READINESS_SCHEMA, READINESS_VERSION, ANCHOR_CHECKS, ARTIFACT_CHECKS, EVIDENCE_CHECKS, SAFETY_CHECKS, UNIT_CHECKS, REQUIRED_CHECK_IDS, assess_recap_ingestion_projection_readiness, recap_ingestion_projection_readiness_to_dict, render_recap_ingestion_projection_readiness_report


def _require(condition: bool, message: str) -> None:
    if not condition:
        raise AssertionError(message)


def main() -> int:
    print("Graph Memory recap-ingestion projection-readiness validation")
    materialization = materialize_recap_ingestion_source_artifacts([RecapIngestionMaterializerInput(k, v) for k, v in DEFAULT_INPUTS.items()])
    print("- explicit input materializer: ready")
    materializer_report = analyze_recap_ingestion_materializer_output(materialization)
    print("- materializer report: ready")
    report = assess_recap_ingestion_projection_readiness(materialization, materializer_report)
    data = recap_ingestion_projection_readiness_to_dict(report)
    rendered = render_recap_ingestion_projection_readiness_report(report)
    by_id = {check.check_id: check for check in report.checks}
    print("- projection-readiness analyzer: ready")
    _require(report.schema == READINESS_SCHEMA and report.version == READINESS_VERSION, "bad readiness schema/version")
    _require(report.source_family == SOURCE_FAMILY, "bad source family")
    _require(report.materializer_schema == MATERIALIZER_SCHEMA, "bad materializer schema")
    _require(report.materializer_report_schema == REPORT_SCHEMA, "bad materializer report schema")
    print(f"- schema: {READINESS_SCHEMA}")
    _require(set(REQUIRED_CHECK_IDS).issubset(by_id), "missing required checks")
    for group, label in ((ARTIFACT_CHECKS, "artifact coverage checks"), (ANCHOR_CHECKS, "anchor coverage checks"), (UNIT_CHECKS, "unit coverage checks"), (EVIDENCE_CHECKS, "evidence boundary checks"), (SAFETY_CHECKS - {"no_raw_ingestion_internal_paths"}, "safety boundary checks")):
        _require(all(by_id[c].status == "ready" for c in group if c in by_id), f"{label} not ready")
        print(f"- {label}: ready")
    source_ref_gap = any(not unit.source_ref.get("source_ref_id") for unit in materialization.units)
    provenance_gap = any(not prov.get("source_ref_id") for unit in materialization.units for prov in unit.provenance)
    _require((not source_ref_gap) or by_id["all_source_refs_have_stable_source_ref_id"].status == "blocked", "source_ref_id gap not blocked")
    _require((not provenance_gap) or by_id["all_provenance_records_link_to_source_ref_id"].status == "blocked", "provenance link gap not blocked")
    _require((not (source_ref_gap or provenance_gap)) or report.readiness_status == "blocked", "overall status should be blocked")
    print("- source-ref/provenance readiness gaps: surfaced")
    print(f"- readiness status: {report.readiness_status}")
    serialized = json.dumps(data, sort_keys=True) + rendered
    for path in DEFAULT_INPUTS.values():
        _require(path.read_text(encoding="utf-8").strip() not in serialized, f"raw contents leaked: {path.name}")
    for forbidden in ("/workspace/", "adapter_payload_field_leak", "plan_payload_field_leak", "agent_interaction_payload_field_leak"):
        _require(forbidden not in serialized, f"forbidden payload/leak appeared: {forbidden}")
    for phrase in ("# Recap-Ingestion Projection-Readiness Report", "Overall status", "## Readiness Summary", "## Checks", "## Issues", "## Blocked Items", "## Deferred Work", "not a production adapter contract", "does not connect `/plan`", "does not connect Agent Interaction"):
        _require(phrase in rendered, f"rendered report missing: {phrase}")
    print("- no adapter/runtime payload leakage: ready")
    print("- recap-ingestion projection-readiness: ready")
    return 0


if __name__ == "__main__":
    try:
        sys.exit(main())
    except (AssertionError, json.JSONDecodeError, ValueError) as exc:
        print(f"- recap-ingestion projection-readiness: blocked ({exc})", file=sys.stderr)
        sys.exit(1)
