from __future__ import annotations

import sys
from pathlib import Path

from src.graph_memory.report import materialize_validate_and_report, render_graph_report_markdown

REPO_ROOT = Path(__file__).resolve().parents[2]
TAXONOMY_REGISTRY_PATH = REPO_ROOT / "evals" / "graph_memory_layer" / "taxonomy_registry.json"
MATERIALIZER_INPUT_PATH = REPO_ROOT / "evals" / "graph_memory_layer" / "examples" / "materializer_input_minimal.json"
BLOCKING_SEVERITIES = {"error", "fatal"}


def _require(condition: bool, message: str) -> None:
    if not condition:
        raise AssertionError(message)


def main() -> int:
    print("Graph Memory materializer report validation")
    _require(TAXONOMY_REGISTRY_PATH.is_file(), "taxonomy registry missing")
    print("- taxonomy registry: found")
    _require(MATERIALIZER_INPUT_PATH.is_file(), "materializer input missing")
    print("- materializer input: found")

    _bundle, report, records, issues = materialize_validate_and_report(MATERIALIZER_INPUT_PATH, TAXONOMY_REGISTRY_PATH)
    print("- report: built")
    _require(report.node_count == 2, "expected 2 nodes")
    print(f"- nodes: {report.node_count}")
    _require(report.edge_count == 1, "expected 1 edge")
    print(f"- edges: {report.edge_count}")
    _require(report.provenance_ref_count > 0, "expected provenance refs")
    print("- provenance refs: present")
    _require(report.source_ref_count > 0, "expected source refs")
    print("- source refs: present")
    _require(report.lifecycle_states == {"candidate": 3}, "expected candidate lifecycle states")
    _require(report.visibility_states == {"internal_diagnostic": 3}, "expected internal diagnostic visibility states")
    _require(report.evidence_roles == {"diagnostic_only": 3}, "expected diagnostic-only evidence roles")
    blocking = [issue for issue in issues if issue.severity in BLOCKING_SEVERITIES]
    _require(not blocking, "expected no blocking validation issues")
    print("- validation issues: no blocking issues")
    rendered = render_graph_report_markdown(report, records)
    for heading in [
        "# Graph Memory Materializer Report",
        "## Summary",
        "## Node Kinds",
        "## Edge Predicate Families",
        "## Lifecycle States",
        "## Visibility States",
        "## Evidence Roles",
        "## Authority States",
        "## Validation Issues",
        "## Records",
    ]:
        _require(heading in rendered, f"missing rendered heading: {heading}")
    print("- materializer report: ready")
    return 0


if __name__ == "__main__":
    try:
        sys.exit(main())
    except AssertionError as exc:
        print(f"- materializer report: blocked ({exc})")
        sys.exit(1)
