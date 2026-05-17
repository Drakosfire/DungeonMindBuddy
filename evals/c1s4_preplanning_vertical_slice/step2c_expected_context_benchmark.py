from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from evals.c1s4_preplanning_vertical_slice.expected_context_benchmark import (
    LEAKAGE_TOKENS,
    RETRIEVAL_MODES,
    build_expected_context_report,
    build_multimode_expected_context_report,
    load_expected_context_gold,
    validate_expected_context_gold,
    validate_expected_context_report,
)
from evals.c1s4_preplanning_vertical_slice.step2_build_question_context_packets import C1S4BoundaryError, build_summary


def _assert_no_retrieved_context_leakage(packets: list[dict]) -> None:
    for packet in packets:
        qn = packet.get("question_number")
        qid = packet.get("question_id")
        for idx, item in enumerate(packet.get("retrieved_context", [])):
            dumped = json.dumps(item, sort_keys=True).lower()
            for token in LEAKAGE_TOKENS:
                if token.lower() in dumped:
                    raise RuntimeError(
                        f"retrieved_context leakage detected for q{qn} ({qid}) item {idx}: {token}"
                    )


def _run_mode(mode: str, gold_path: Path | None, question_number: int | None, top_k: int | None) -> dict:
    step2 = build_summary(mode=mode, question_number=question_number)
    step2_diag = build_summary(mode=mode, question_number=question_number, max_hits=50)
    for packet in step2.get("packets", []):
        forbidden = {"expected_retrieval_context_eval_only", "expected_retrieval_modes", "required_context_groups", "forbidden_context_groups", "expectations_by_mode"}
        if forbidden.intersection(packet):
            raise RuntimeError("eval-only fields leaked into planner packet")
    _assert_no_retrieved_context_leakage(step2.get("packets", []))
    gold = load_expected_context_gold(gold_path)
    errs = validate_expected_context_gold(gold)
    if errs:
        raise RuntimeError(f"invalid gold schema: {errs}")
    report = build_expected_context_report(
        packets=step2["packets"],
        diagnostic_packets=step2_diag["packets"],
        gold=gold,
        retrieval_mode=mode,
        top_k=top_k,
    )
    rerrs = validate_expected_context_report(report)
    if rerrs:
        raise RuntimeError(f"invalid report shape: {rerrs}")
    return report


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--mode", choices=RETRIEVAL_MODES, default="prior_only")
    parser.add_argument("--all-modes", action="store_true")
    parser.add_argument("--gold", type=Path)
    parser.add_argument("--question-number", type=int)
    parser.add_argument("--top-k", type=int)
    parser.add_argument("--output-json", type=Path)
    parser.add_argument("--fail-on-benchmark-failure", action="store_true")
    args = parser.parse_args()
    try:
        if args.all_modes:
            reports_by_mode = {m: _run_mode(m, args.gold, args.question_number, args.top_k) for m in RETRIEVAL_MODES}
            report = build_multimode_expected_context_report(reports_by_mode=reports_by_mode)
            fail_rows = sum(x["counts"]["rows_failed"] for x in reports_by_mode.values())
        else:
            report = _run_mode(args.mode, args.gold, args.question_number, args.top_k)
            fail_rows = report["counts"]["rows_failed"]
    except (RuntimeError, C1S4BoundaryError) as exc:
        print(json.dumps({"error": str(exc)}, indent=2))
        return 1
    if args.output_json:
        args.output_json.write_text(json.dumps(report, indent=2), encoding="utf-8")
    print(json.dumps(report, indent=2))
    if args.fail_on_benchmark_failure and fail_rows:
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
