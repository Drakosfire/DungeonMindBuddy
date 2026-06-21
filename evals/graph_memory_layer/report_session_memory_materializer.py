from __future__ import annotations

import argparse
import sys
from pathlib import Path

from src.graph_memory.report import render_graph_report_markdown
from src.graph_memory.session_memory_materialize import (
    load_session_memory_jsonl,
    materialize_validate_and_report_session_memory,
    session_memory_coverage,
)

REPO_ROOT = Path(__file__).resolve().parents[2]
DEFAULT_INPUT_PATH = REPO_ROOT / "evals" / "graph_memory_layer" / "examples" / "session_memory_sentence_units_minimal.jsonl"
TAXONOMY_REGISTRY_PATH = REPO_ROOT / "evals" / "graph_memory_layer" / "taxonomy_registry.json"
GATE_MANIFEST_PATH = REPO_ROOT / "evals" / "graph_memory_layer" / "real_structure_materialization_gate.json"
BLOCKING_SEVERITIES = {"error", "fatal"}


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Report an explicit session-memory JSONL materializer run.")
    parser.add_argument("--input", type=Path, default=DEFAULT_INPUT_PATH, help="Explicit session-memory JSONL path to read.")
    parser.add_argument("--limit", type=int, default=None, help="Maximum JSONL records to read.")
    return parser


def _coverage_markdown(input_path: Path, limit: int | None) -> str:
    coverage = session_memory_coverage(load_session_memory_jsonl(input_path, limit=limit))
    return "\n".join([
        "## Session-Memory Coverage",
        "",
        "| Metric | Count |",
        "|---|---:|",
        f"| Input records | {coverage.input_record_count} |",
        f"| Source documents | {coverage.source_document_count} |",
        f"| Source units | {coverage.source_unit_count} |",
        f"| Records with routes | {coverage.records_with_routes} |",
        f"| Total route mentions | {coverage.total_route_mentions} |",
        f"| Proposed route mentions | {coverage.proposed_route_mentions} |",
        f"| Explicit route mentions | {coverage.explicit_route_mentions} |",
        "",
    ])


def main(argv: list[str] | None = None) -> int:
    args = _parser().parse_args(argv)
    _bundle, report, records, issues = materialize_validate_and_report_session_memory(
        args.input,
        TAXONOMY_REGISTRY_PATH,
        gate_manifest_path=GATE_MANIFEST_PATH,
        limit=args.limit,
    )
    print(render_graph_report_markdown(report, records), end="")
    print(_coverage_markdown(args.input, args.limit), end="")
    return 1 if any(issue.severity in BLOCKING_SEVERITIES for issue in issues) else 0


if __name__ == "__main__":
    sys.exit(main())
