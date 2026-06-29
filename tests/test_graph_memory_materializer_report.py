from __future__ import annotations

import subprocess
import sys
from pathlib import Path

from src.graph_memory.report import materialize_validate_and_report, render_graph_report_markdown

REPO_ROOT = Path(__file__).resolve().parents[1]
FIXTURE_PATH = REPO_ROOT / "evals" / "graph_memory_layer" / "examples" / "materializer_input_minimal.json"
TAXONOMY_REGISTRY_PATH = REPO_ROOT / "evals" / "graph_memory_layer" / "taxonomy_registry.json"
REPORT_SOURCE_PATH = REPO_ROOT / "src" / "graph_memory" / "report.py"

FORBIDDEN_IMPORT_SNIPPETS = {
    "src.agent.session_memory_query",
    "src.agent.planner_retrieval_router",
    "src.live_play.manifest_context_query",
    "src.session_memory.capture",
    "src.session_memory.breadcrumb_normalize",
    "openai",
    "anthropic",
}


def report_parts():
    return materialize_validate_and_report(FIXTURE_PATH, TAXONOMY_REGISTRY_PATH)


def test_report_cli_exits_zero() -> None:
    result = subprocess.run(
        [sys.executable, "-m", "evals.graph_memory_layer.report_materializer"],
        cwd=REPO_ROOT,
        check=False,
        text=True,
        capture_output=True,
    )
    assert result.returncode == 0, result.stdout + result.stderr
    assert "# Graph Memory Materializer Report" in result.stdout
    assert "Bundle: `example:materializer:minimal-input:graph-bundle`" in result.stdout


def test_report_validator_exits_zero() -> None:
    result = subprocess.run(
        [sys.executable, "-m", "evals.graph_memory_layer.validate_materializer_report"],
        cwd=REPO_ROOT,
        check=False,
        text=True,
        capture_output=True,
    )
    assert result.returncode == 0, result.stdout + result.stderr
    assert "- materializer report: ready" in result.stdout


def test_report_functions_return_expected_counts_and_distributions() -> None:
    _bundle, report, _records, issues = report_parts()
    assert report.node_count == 2
    assert report.edge_count == 1
    assert report.node_kinds == {"source_document": 1, "source_unit": 1}
    assert report.edge_predicate_families == {"source_derivation": 1}
    assert report.lifecycle_states == {"candidate": 3}
    assert report.visibility_states == {"internal_diagnostic": 3}
    assert report.evidence_roles == {"diagnostic_only": 3}
    assert report.authority_states == {"system_derived": 3}
    assert report.provenance_ref_count == 3
    assert report.source_ref_count == 3
    assert report.validation_issue_count == 3
    assert report.validation_issue_severities == {"info": 3}
    assert report.validation_issue_codes == {"non_admissible_evidence_role": 3}
    assert not [issue for issue in issues if issue.severity in {"error", "fatal"}]


def test_record_summaries_include_provenance_and_sources() -> None:
    _bundle, _report, records, _issues = report_parts()
    assert len(records) == 3
    assert [record.record_type for record in records] == ["edge", "node", "node"]
    for record in records:
        assert record.provenance_count == 1
        assert record.source_ref_count == 1
        assert record.lifecycle_state == "candidate"
        assert record.visibility_state == "internal_diagnostic"


def test_rendered_markdown_includes_expected_sections_and_bundle_id() -> None:
    _bundle, report, records, _issues = report_parts()
    rendered = render_graph_report_markdown(report, records)
    for expected in [
        "# Graph Memory Materializer Report",
        "Bundle: `example:materializer:minimal-input:graph-bundle`",
        "## Summary",
        "## Node Kinds",
        "## Edge Predicate Families",
        "## Lifecycle States",
        "## Visibility States",
        "## Evidence Roles",
        "## Authority States",
        "## Validation Issues",
        "## Records",
        "| Nodes | 2 |",
        "| Edges | 1 |",
        "| source_document | 1 |",
        "| source_unit | 1 |",
        "| source_derivation | 1 |",
        "| candidate | 3 |",
        "| internal_diagnostic | 3 |",
        "| diagnostic_only | 3 |",
    ]:
        assert expected in rendered


def test_report_source_does_not_import_production_retrieval_session_memory_or_llm_modules() -> None:
    source = REPORT_SOURCE_PATH.read_text(encoding="utf-8")
    for snippet in FORBIDDEN_IMPORT_SNIPPETS:
        assert snippet not in source


def test_validation_issue_rows_use_actual_severity_code_pairs() -> None:
    from src.graph_memory.report import build_graph_report
    from src.graph_memory.validation_rules import ValidationIssue

    bundle, _report, records, _issues = report_parts()
    issues = [
        ValidationIssue(severity="info", code="non_admissible_evidence_role", message="info", record_id=None, field=None),
        ValidationIssue(severity="error", code="source_evidence_without_source_ref", message="error", record_id=None, field=None),
    ]
    mixed_report = build_graph_report(bundle, issues)
    rendered = render_graph_report_markdown(mixed_report, records)

    assert mixed_report.validation_issue_pairs == {
        "error/source_evidence_without_source_ref": 1,
        "info/non_admissible_evidence_role": 1,
    }
    assert "| info | non_admissible_evidence_role | 1 |" in rendered
    assert "| error | source_evidence_without_source_ref | 1 |" in rendered
    assert "| info | source_evidence_without_source_ref |" not in rendered
    assert "| error | non_admissible_evidence_role |" not in rendered
