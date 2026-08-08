"""CLI for claimed-fill and open-PC-extract ablations."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
for _path in (REPO_ROOT, REPO_ROOT / "src"):
    value = str(_path)
    if value not in sys.path:
        sys.path.insert(0, value)

from evals.graph_memory_layer.pc_claimed_fill_experiment import (
    run_experiment,
    run_open_pc_extract_experiment,
)

DEFAULT_RUN_DIR = (
    "out/graph_memory/runs/longmont-c2/session-25/20260808T010341Z"
)


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--run-dir", default=DEFAULT_RUN_DIR)
    parser.add_argument("--out-dir", default=None)
    parser.add_argument("--model-id", default=None)
    parser.add_argument("--reasoning-effort", default=None)
    parser.add_argument(
        "--arm",
        choices=("claimed_fill", "open_pc_extract"),
        default="claimed_fill",
    )
    parser.add_argument(
        "--rebuild-mentions",
        action="store_true",
        help="Rebuild known_entity_mentions from current party registry.",
    )
    parser.add_argument("--campaign-id", default=None)
    parser.add_argument("--session-number", type=int, default=None)
    parser.add_argument(
        "--prompt-only",
        action="store_true",
        help="claimed_fill only: build claims/prompt without calling the model.",
    )
    args = parser.parse_args()
    common = {
        "run_dir": Path(args.run_dir),
        "out_dir": Path(args.out_dir) if args.out_dir else None,
        "model_id": args.model_id,
        "reasoning_effort": args.reasoning_effort,
        "rebuild_mentions": args.rebuild_mentions,
        "campaign_id": args.campaign_id,
        "session_number": args.session_number,
    }
    if args.arm == "open_pc_extract":
        report = run_open_pc_extract_experiment(**common)
    else:
        report = run_experiment(**common, dry_run_prompt_only=args.prompt_only)
    print(json.dumps(report, indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
