from __future__ import annotations

import argparse
import json
from pathlib import Path

from evals.graph_memory_layer.live_vs_gold_compare import compare_live_candidate_file


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--candidate-output", required=True)
    ap.add_argument("--reconciled-json", help="optional reconciled candidate graph JSON path")
    args = ap.parse_args()
    reconciled = None
    if args.reconciled_json:
        reconciled = json.loads(Path(args.reconciled_json).read_text(encoding="utf-8"))
    report = compare_live_candidate_file(Path(args.candidate_output), reconciled_graph=reconciled)
    print("# Live vs Gold Comparison Report")
    for key, val in report["scores"].items():
        print(f"- {key}: {val}")
    print(f"- soft_misses: {len(report['soft_misses'])}")
    print(f"- hard_failures: {len(report['hard_failures'])}")


if __name__ == "__main__":
    main()
