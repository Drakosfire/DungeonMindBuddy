from __future__ import annotations

import argparse
from pathlib import Path

from evals.graph_memory_layer.report_recap_ingestion_source_artifact_materializer import DEFAULT_INPUTS, build_inputs
from src.graph_memory.recap_ingestion_materialize import materialize_recap_ingestion_source_artifacts
from src.graph_memory.recap_ingestion_materializer_report import (
    analyze_recap_ingestion_materializer_output,
    render_recap_ingestion_materializer_report,
)


def main() -> int:
    parser = argparse.ArgumentParser(description="Report diagnostic coverage for explicit-input recap-ingestion source artifact materialization.")
    parser.add_argument("--normalized-recap", type=Path)
    parser.add_argument("--breadcrumbed-recap", type=Path)
    parser.add_argument("--frontmatter-seed", type=Path)
    parser.add_argument("--session-memory-meta", type=Path)
    parser.add_argument("--corpus-impact-proof", type=Path)
    args = parser.parse_args()
    materialization = materialize_recap_ingestion_source_artifacts(build_inputs(args))
    report = analyze_recap_ingestion_materializer_output(materialization)
    print(render_recap_ingestion_materializer_report(report), end="")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
