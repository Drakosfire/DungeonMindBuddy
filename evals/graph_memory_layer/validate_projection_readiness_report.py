from __future__ import annotations

import sys
from pathlib import Path

from src.graph_memory.projection_readiness import REQUIRED_FIELDS, assess_projection_readiness, projection_readiness_report_to_dict, render_projection_readiness_report
from src.graph_memory.session_memory_materialize import materialize_session_memory_jsonl

REPO_ROOT = Path(__file__).resolve().parents[2]
FIXTURE_PATH = REPO_ROOT / "evals" / "graph_memory_layer" / "examples" / "session_memory_sentence_units_minimal.jsonl"
FORBIDDEN_TEXT = ("lexical_plain", "full_text", "markdown_body", "raw_text", "recap_text", "Synthetic sentence-unit text", "A second synthetic sentence-unit record")
FORBIDDEN_INTERNALS = ("_normalized/", "_breadcrumbed/", ".records_meta.jsonl", "corpus_impact")


def _require(condition: bool, message: str) -> None:
    if not condition:
        raise AssertionError(message)


def main() -> int:
    try:
        _require(FIXTURE_PATH.is_file(), "fixture missing")
        bundle = materialize_session_memory_jsonl(FIXTURE_PATH)
        _require(bundle.nodes, "graph bundle has no nodes")
        source_units = [node for node in bundle.nodes if node.kind.term == "source_unit"]
        _require(source_units, "expected at least one source-unit record")
        report = assess_projection_readiness(bundle)
        data = projection_readiness_report_to_dict(report)
        rendered = render_projection_readiness_report(report)
        _require(report.schema == "dmb_projection_readiness_report_v0", "bad schema")
        _require(report.version == "0.1", "bad version")
        _require(report.source_family == "session_memory_jsonl_sentence_units", "bad source family")
        _require(report.total_source_units == len(source_units), "bad source-unit count")
        _require(report.ready_count + report.degraded_count + report.blocked_count == report.total_source_units, "counts do not add up")
        _require(len(report.records) == report.total_source_units, "missing per-record readiness rows")
        for record in report.records:
            _require(set(record.required_field_status) == set(REQUIRED_FIELDS), "required semantic envelope not fully checked")
            if not record.required_field_status["canon_state"]:
                _require(report.missing_field_counts["canon_state"] > 0, "missing canon_state not reported")
            _require(record.diagnostics.get("display_summary_status") == "not_evidence", "display summary counted as evidence")
        _require("payload_kind" not in str(data) and "source_unit_projection" not in str(data), "production adapter output detected")
        for forbidden in FORBIDDEN_TEXT:
            _require(forbidden not in rendered and forbidden not in str(data), f"full text leakage: {forbidden}")
        for forbidden in FORBIDDEN_INTERNALS:
            _require(forbidden not in rendered and forbidden not in str(data), f"raw ingestion internal exposed: {forbidden}")
    except Exception as exc:
        print(f"Graph Memory projection-readiness report validation failed: {exc}", file=sys.stderr)
        return 1
    print("Graph Memory projection-readiness report validation")
    print("- fixture: found")
    print("- session-memory materializer: ready")
    print("- graph bundle: ready")
    print("- source units: ready")
    print("- readiness assessment: ready")
    print("- required semantic envelope: checked")
    print("- missing fields: reported")
    print("- full text leakage: absent")
    print("- raw ingestion internals: absent")
    print("- projection-readiness report: ready")
    return 0

if __name__ == "__main__":
    raise SystemExit(main())
