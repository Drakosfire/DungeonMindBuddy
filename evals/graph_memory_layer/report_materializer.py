from __future__ import annotations

import sys
from pathlib import Path

from src.graph_memory.report import materialize_validate_and_report, render_graph_report_markdown

REPO_ROOT = Path(__file__).resolve().parents[2]
TAXONOMY_REGISTRY_PATH = REPO_ROOT / "evals" / "graph_memory_layer" / "taxonomy_registry.json"
MATERIALIZER_INPUT_PATH = REPO_ROOT / "evals" / "graph_memory_layer" / "examples" / "materializer_input_minimal.json"
BLOCKING_SEVERITIES = {"error", "fatal"}


def main() -> int:
    _bundle, report, records, issues = materialize_validate_and_report(MATERIALIZER_INPUT_PATH, TAXONOMY_REGISTRY_PATH)
    print(render_graph_report_markdown(report, records), end="")
    return 1 if any(issue.severity in BLOCKING_SEVERITIES for issue in issues) else 0


if __name__ == "__main__":
    sys.exit(main())
