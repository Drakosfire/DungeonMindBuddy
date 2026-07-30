"""Eval entrypoint for TL01B temporal shadow cohort runs."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

from graph_memory.temporal_shadow_extraction import (
    TemporalShadowExtractionError,
    run_temporal_shadow_extraction,
)

DEFAULT_CASE = (
    "evals/graph_memory_layer/examples/temporal_shadow_cohort/temporal-case.json"
)


def _repo_root() -> Path:
    return Path(__file__).resolve().parents[2]


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Run TL01B temporal shadow cohort eval")
    parser.add_argument("--case", default=DEFAULT_CASE, help="Sealed case JSON path")
    parser.add_argument(
        "--output-dir",
        default="evals/graph_memory_layer/artifacts/temporal_shadow_cohort/latest",
        help="Run artifact directory",
    )
    parser.add_argument("--model-id", default=None)
    parser.add_argument("--overwrite", action="store_true")
    args = parser.parse_args(argv)

    try:
        run = run_temporal_shadow_extraction(
            args.case,
            args.output_dir,
            model_id=args.model_id,
            overwrite=args.overwrite,
            repo_root=_repo_root(),
        )
    except TemporalShadowExtractionError as exc:
        print(json.dumps({"ok": False, "code": exc.code, "error": str(exc)}))
        return 1

    print(
        json.dumps(
            {
                "ok": True,
                "case_id": run.case_id,
                "comparison_verdict": run.comparison_verdict,
                "overlay_id": run.overlay_id,
            }
        )
    )
    return 0 if run.comparison_verdict == "pass" else 2


if __name__ == "__main__":
    raise SystemExit(main())
