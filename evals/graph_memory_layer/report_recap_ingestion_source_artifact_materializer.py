from __future__ import annotations

import argparse
from pathlib import Path

from src.graph_memory.recap_ingestion_materialize import (
    RecapIngestionMaterializerInput,
    materialize_recap_ingestion_source_artifacts,
    render_recap_ingestion_materialization_report,
)

REPO_ROOT = Path(__file__).resolve().parents[2]
FIXTURE_DIR = REPO_ROOT / "evals" / "graph_memory_layer" / "examples" / "recap_ingestion_materializer_inputs"
DEFAULT_INPUTS = {
    "normalized_recap_markdown": FIXTURE_DIR / "normalized_recap_s01.md",
    "breadcrumbed_recap_markdown": FIXTURE_DIR / "breadcrumbed_recap_s01.md",
    "frontmatter_seed_markdown": FIXTURE_DIR / "frontmatter_seed_s01.md",
    "session_memory_jsonl_meta": FIXTURE_DIR / "session_memory_meta_s01.json",
    "corpus_impact_proof": FIXTURE_DIR / "corpus_impact_proof_s01.json",
}


def build_inputs(args: argparse.Namespace) -> list[RecapIngestionMaterializerInput]:
    paths = {
        "normalized_recap_markdown": args.normalized_recap or DEFAULT_INPUTS["normalized_recap_markdown"],
        "breadcrumbed_recap_markdown": args.breadcrumbed_recap or DEFAULT_INPUTS["breadcrumbed_recap_markdown"],
        "frontmatter_seed_markdown": args.frontmatter_seed or DEFAULT_INPUTS["frontmatter_seed_markdown"],
        "session_memory_jsonl_meta": args.session_memory_meta or DEFAULT_INPUTS["session_memory_jsonl_meta"],
        "corpus_impact_proof": args.corpus_impact_proof or DEFAULT_INPUTS["corpus_impact_proof"],
    }
    return [RecapIngestionMaterializerInput(artifact_id, Path(path)) for artifact_id, path in paths.items()]


def main() -> int:
    parser = argparse.ArgumentParser(description="Report explicit-input recap-ingestion source artifact materialization.")
    parser.add_argument("--normalized-recap", type=Path)
    parser.add_argument("--breadcrumbed-recap", type=Path)
    parser.add_argument("--frontmatter-seed", type=Path)
    parser.add_argument("--session-memory-meta", type=Path)
    parser.add_argument("--corpus-impact-proof", type=Path)
    args = parser.parse_args()
    materialization = materialize_recap_ingestion_source_artifacts(build_inputs(args))
    print(render_recap_ingestion_materialization_report(materialization), end="")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
