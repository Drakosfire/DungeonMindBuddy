"""CLI for TL01B temporal shadow extraction runs."""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

from graph_memory.temporal_shadow_extraction import (
    TemporalShadowExtractionError,
    run_temporal_shadow_extraction,
)


def _repo_root() -> Path:
    return Path(__file__).resolve().parents[2]


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="Run evidence-bound temporal shadow extraction for a sealed case."
    )
    parser.add_argument(
        "--case",
        required=True,
        help="Path to temporal shadow extraction case JSON",
    )
    parser.add_argument(
        "--output-dir",
        required=True,
        help="Directory for run artifacts",
    )
    parser.add_argument(
        "--model-id",
        default=None,
        help="Optional OpenAI model override",
    )
    parser.add_argument(
        "--overwrite",
        action="store_true",
        help="Replace existing run artifacts in output-dir",
    )
    args = parser.parse_args(argv)

    try:
        run_temporal_shadow_extraction(
            args.case,
            args.output_dir,
            model_id=args.model_id,
            overwrite=args.overwrite,
            repo_root=_repo_root(),
        )
    except TemporalShadowExtractionError as exc:
        print(f"temporal_shadow_extraction failed [{exc.code}]: {exc}", file=sys.stderr)
        for line in exc.diagnostics:
            print(f"  - {line}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
