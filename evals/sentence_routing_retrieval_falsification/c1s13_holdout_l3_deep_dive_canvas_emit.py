from __future__ import annotations

import argparse
import json
from pathlib import Path

_REPO_ROOT = Path(__file__).resolve().parents[2]
DEFAULT_EQ_REPORT = _REPO_ROOT / "evals/sentence_routing_retrieval_falsification/artifacts/baselines/cohort_l3_ab_scenario_report_c1s13_v1_equivalence.json"


def build_payload(*, equivalence_report: dict) -> dict:
    """JSON payload for C1S13 holdout L3 review tooling (default lane only).

    Legacy baseline reports are no longer embedded; use ``cohort_baseline_run
    --mode baseline`` when a diagnostics-only lane is required.
    """
    return {
        "cohort_lane_labels": {
            "promoted_default": "Default (equivalence-augmented ranking)",
        },
        "comparison": {
            "promoted_default": equivalence_report,
        },
    }


def emit_payload(*, equivalence_path: Path = DEFAULT_EQ_REPORT) -> dict:
    equivalence_report = json.loads(equivalence_path.read_text(encoding="utf-8"))
    return build_payload(equivalence_report=equivalence_report)


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Build C1S13 holdout L3 deep dive payload (default equivalence lane only)"
    )
    parser.add_argument("--equivalence", type=Path, default=DEFAULT_EQ_REPORT)
    parser.add_argument("--output", type=Path, default=None)
    args = parser.parse_args()
    payload = emit_payload(equivalence_path=args.equivalence)
    text = json.dumps(payload, indent=2, ensure_ascii=False) + "\n"
    if args.output is None:
        print(text, end="")
    else:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(text, encoding="utf-8")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
