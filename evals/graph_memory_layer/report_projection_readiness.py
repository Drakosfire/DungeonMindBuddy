from __future__ import annotations

import argparse
from pathlib import Path

from src.graph_memory.projection_readiness import assess_projection_readiness, render_projection_readiness_report
from src.graph_memory.session_memory_materialize import materialize_session_memory_jsonl

REPO_ROOT = Path(__file__).resolve().parents[2]
DEFAULT_INPUT_PATH = REPO_ROOT / "evals" / "graph_memory_layer" / "examples" / "session_memory_sentence_units_minimal.jsonl"


def main() -> int:
    parser = argparse.ArgumentParser(description="Render a diagnostic projection-readiness report for one explicit session-memory JSONL file.")
    parser.add_argument("--input", type=Path, default=DEFAULT_INPUT_PATH)
    args = parser.parse_args()
    bundle = materialize_session_memory_jsonl(args.input)
    print(render_projection_readiness_report(assess_projection_readiness(bundle)), end="")
    return 0

if __name__ == "__main__":
    raise SystemExit(main())
