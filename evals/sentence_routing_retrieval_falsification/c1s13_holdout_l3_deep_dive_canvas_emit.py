from __future__ import annotations

import argparse
import json
from pathlib import Path

_REPO_ROOT = Path(__file__).resolve().parents[2]
DEFAULT_BASELINE_REPORT = _REPO_ROOT / "evals/sentence_routing_retrieval_falsification/artifacts/baselines/cohort_l3_ab_scenario_report_c1s13_v1_baseline.json"
DEFAULT_EQ_REPORT = _REPO_ROOT / "evals/sentence_routing_retrieval_falsification/artifacts/baselines/cohort_l3_ab_scenario_report_c1s13_v1_equivalence.json"


def build_payload(*, baseline_report: dict, equivalence_report: dict) -> dict:
    return {
        "cohort_lane_labels": {
            "promoted_default": "Promoted Equivalence Default",
            "legacy_diagnostics": "Legacy Baseline (diagnostics)",
        },
        "comparison": {
            "promoted_default": equivalence_report,
            "legacy_diagnostics": baseline_report,
        },
        "backcompat": {
            "baseline": baseline_report,
            "equivalence": equivalence_report,
        },
    }


def emit_payload(*, baseline_path: Path = DEFAULT_BASELINE_REPORT, equivalence_path: Path = DEFAULT_EQ_REPORT) -> dict:
    baseline_report = json.loads(baseline_path.read_text(encoding="utf-8"))
    equivalence_report = json.loads(equivalence_path.read_text(encoding="utf-8"))
    return build_payload(baseline_report=baseline_report, equivalence_report=equivalence_report)


def main() -> int:
    parser = argparse.ArgumentParser(description="Build C1S13 holdout L3 deep dive payload")
    parser.add_argument("--baseline", type=Path, default=DEFAULT_BASELINE_REPORT)
    parser.add_argument("--equivalence", type=Path, default=DEFAULT_EQ_REPORT)
    parser.add_argument("--output", type=Path, default=None)
    args = parser.parse_args()
    payload = emit_payload(baseline_path=args.baseline, equivalence_path=args.equivalence)
    text = json.dumps(payload, indent=2, ensure_ascii=False) + "\n"
    if args.output is None:
        print(text, end="")
    else:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(text, encoding="utf-8")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
