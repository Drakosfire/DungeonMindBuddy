"""Scope-B: run the corpus planner with writes enabled against a pre-state corpus.

Wire-up target: ``evals/planner_slice/live_eval.evaluate_scenario_detail`` (see
``evals/npc_voice_vertical_slice/`` and ``evals/lysandra_vertical_slice/``).
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

_REPO_ROOT = str(Path(__file__).resolve().parents[2])
if _REPO_ROOT not in sys.path:
    sys.path.insert(0, _REPO_ROOT)

from evals.session_recap_ingest_vertical_slice.step0_pre_state import (  # noqa: E402
    build_pre_state_corpus,
)


def main() -> None:
    parser = argparse.ArgumentParser(description="Prepare pre-state corpus (stub runner).")
    parser.add_argument(
        "--print-root",
        action="store_true",
        help="Copy corpus, apply manifest, print tmp corpus root and exit.",
    )
    args = parser.parse_args()
    if args.print_root:
        root = build_pre_state_corpus()
        print(root)
        return
    raise SystemExit(
        "Live planner wiring is not implemented here yet. "
        "Use --print-root to obtain a tmp corpus, then run the planner with "
        "DUNGEONMIND_PLANNER_ALLOW_WRITES=1 and that corpus root. "
        "See README.md in this directory."
    )


if __name__ == "__main__":
    main()
