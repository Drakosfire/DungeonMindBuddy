from __future__ import annotations

import subprocess
import sys
from pathlib import Path

from src.graph_memory.projection_readiness import REQUIRED_FIELDS, assess_projection_readiness, projection_readiness_report_to_dict, render_projection_readiness_report
from src.graph_memory.session_memory_materialize import materialize_session_memory_jsonl

REPO_ROOT = Path(__file__).resolve().parents[1]
FIXTURE_PATH = REPO_ROOT / "evals" / "graph_memory_layer" / "examples" / "session_memory_sentence_units_minimal.jsonl"
DOC_PATH = REPO_ROOT / "Docs" / "Reports" / "GRAPH-MEMORY-PROJECTION-READINESS-REPORT.md"


def _report():
    return assess_projection_readiness(materialize_session_memory_jsonl(FIXTURE_PATH))


def test_validator_exits_zero() -> None:
    result = subprocess.run([sys.executable, "-m", "evals.graph_memory_layer.validate_projection_readiness_report"], cwd=REPO_ROOT, text=True, capture_output=True, check=False)
    assert result.returncode == 0, result.stderr
    assert "projection-readiness report: ready" in result.stdout


def test_report_cli_exits_zero() -> None:
    result = subprocess.run([sys.executable, "-m", "evals.graph_memory_layer.report_projection_readiness"], cwd=REPO_ROOT, text=True, capture_output=True, check=False)
    assert result.returncode == 0, result.stderr
    assert "# Projection Readiness Report" in result.stdout


def test_readiness_report_shape_counts_and_rows() -> None:
    report = _report()
    assert report.schema == "dmb_projection_readiness_report_v0"
    assert report.version == "0.1"
    assert report.source_family == "session_memory_jsonl_sentence_units"
    assert report.total_source_units > 0
    assert report.ready_count + report.degraded_count + report.blocked_count == report.total_source_units
    assert len(report.records) == report.total_source_units


def test_every_record_checks_required_fields() -> None:
    for record in _report().records:
        assert tuple(record.required_field_status) == REQUIRED_FIELDS
        assert set(record.required_field_status) == set(REQUIRED_FIELDS)


def test_missing_required_fields_are_reported_not_invented() -> None:
    report = _report()
    assert report.missing_field_counts["canon_state"] == report.total_source_units
    assert all(not record.required_field_status["canon_state"] for record in report.records)
    assert all(record.diagnostics["canon_state"] is None for record in report.records)


def test_display_summaries_are_never_counted_as_evidence() -> None:
    for record in _report().records:
        assert record.diagnostics["display_summary_status"] == "not_evidence"
        assert record.diagnostics["evidence_role"] == "diagnostic_only"


def test_no_full_text_or_raw_ingestion_internals_in_report_output() -> None:
    rendered = render_projection_readiness_report(_report())
    data = str(projection_readiness_report_to_dict(_report()))
    forbidden = ["lexical_plain", "full_text", "markdown_body", "raw_text", "recap_text", "Synthetic sentence-unit text", "A second synthetic sentence-unit record", "_normalized/", "_breadcrumbed/", ".records_meta.jsonl", "corpus_impact"]
    for marker in forbidden:
        assert marker not in rendered
        assert marker not in data


def test_graph_node_ids_are_report_identifiers_only() -> None:
    report = _report()
    for record in report.records:
        assert record.node_id.startswith("session-memory:source-unit:")
        assert "session-memory:source-unit:" not in record.ref_id
        assert "session-memory:source-unit:" not in record.label


def test_report_doc_exists_and_states_boundaries() -> None:
    text = DOC_PATH.read_text(encoding="utf-8")
    assert "This report measures whether materialized graph/source-unit records are ready to become projection-safe surface payloads. It does not implement a projection adapter and does not produce runtime UI payloads." in text
    assert "runtime behavior" in text
    assert "Agent Interaction" in text
    assert "/plan" in text
    for state in ("ready", "degraded", "blocked"):
        assert f"`{state}`" in text
