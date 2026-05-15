from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from evals.c1s4_preplanning_vertical_slice.answer_packet_harness import (
    build_stub_answer_packet,
    summarize_answer_packets,
    validate_answer_packet,
)
from evals.c1s4_preplanning_vertical_slice.step2_build_question_context_packets import C1S4BoundaryError, build_summary as build_step2_summary


def build_summary(*, mode: str, question_number: int | None = None, limit: int | None = None) -> dict:
    step2 = build_step2_summary(mode=mode, question_number=question_number, limit=limit)
    answer_packets = [build_stub_answer_packet(context_packet=p) for p in step2["packets"]]
    return summarize_answer_packets(answer_packets=answer_packets, skipped_questions=step2["skipped_questions"], retrieval_mode=mode)


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--mode", required=True, choices=["prior_only", "prior_plus_support_content_only", "prior_plus_support_content_plus_lexical_hints"])
    parser.add_argument("--question-number", type=int)
    parser.add_argument("--limit", type=int)
    parser.add_argument("--output-json", type=Path)
    args = parser.parse_args()
    try:
        summary = build_summary(mode=args.mode, question_number=args.question_number, limit=args.limit)
    except C1S4BoundaryError as exc:
        print(json.dumps({"schema": "dmb_c1s4_step3_stub_answer_packet_summary_v1", "error": str(exc)}, indent=2))
        return 1

    packet_errors = []
    has_non_stubbed_fields = False
    for packet in summary["answer_packets"]:
        errs = validate_answer_packet(packet)
        if errs:
            packet_errors.append({"question_number": packet.get("question_number"), "errors": errs})
        if packet.get("answer_text") is not None or packet.get("structured_answer") is not None:
            has_non_stubbed_fields = True

    if packet_errors:
        summary["validation_errors"] = packet_errors
    if args.output_json:
        args.output_json.write_text(json.dumps(summary, indent=2), encoding="utf-8")
    print(json.dumps(summary, indent=2))

    leaks = summary["oracle_leakage_check"]["forbidden_path_hits"] or summary["oracle_leakage_check"]["forbidden_session_hits"]
    return 1 if packet_errors or leaks or has_non_stubbed_fields else 0


if __name__ == "__main__":
    raise SystemExit(main())
