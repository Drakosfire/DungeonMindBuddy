from __future__ import annotations

import argparse
from pathlib import Path

from evals.graph_memory_layer.report_recap_ingestion_source_artifact_materializer import build_inputs
from src.graph_memory.recap_ingestion_materialize import materialize_recap_ingestion_source_artifacts
from src.graph_memory.recap_ingestion_materializer_report import analyze_recap_ingestion_materializer_output
from src.graph_memory.recap_ingestion_projection_readiness import assess_recap_ingestion_projection_readiness, render_recap_ingestion_projection_readiness_report


def main() -> int:
    parser = argparse.ArgumentParser(description="Report projection-readiness for explicit-input recap-ingestion materializer output.")
    parser.add_argument("--normalized-recap", type=Path)
    parser.add_argument("--breadcrumbed-recap", type=Path)
    parser.add_argument("--frontmatter-seed", type=Path)
    parser.add_argument("--session-memory-meta", type=Path)
    parser.add_argument("--corpus-impact-proof", type=Path)
    args = parser.parse_args()
    materialization = materialize_recap_ingestion_source_artifacts(build_inputs(args))
    materializer_report = analyze_recap_ingestion_materializer_output(materialization)
    readiness = assess_recap_ingestion_projection_readiness(materialization, materializer_report)
    print(render_recap_ingestion_projection_readiness_report(readiness), end="")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
