from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from evals.c1s4_preplanning_vertical_slice.generated_answer_harness import generate_answer_packet, validate_generated_answer_packet
from evals.c1s4_preplanning_vertical_slice.planner_prompt_payload import (
    build_evaluator_control_metadata,
    build_planner_prompt_payload,
)
from evals.c1s4_preplanning_vertical_slice.step2_build_question_context_packets import C1S4BoundaryError, build_summary as build_step2_summary


def build_summary(*, mode: str, question_number: int | None = None, limit: int | None = None, generator: str = "template_stub") -> dict:
    step2 = build_step2_summary(mode=mode, question_number=question_number, limit=limit)
    answer_packets = []
    for p in step2["packets"]:
        prompt = build_planner_prompt_payload(context_packet=p)
        meta = build_evaluator_control_metadata(context_packet=p)
        answer_packets.append(
            generate_answer_packet(
                planner_prompt_payload=prompt,
                evaluator_control_metadata=meta,
                retrieval_mode=mode,
                generator=generator,
            )
        )
    packet_errors = []
    unsupported_forbidden = 0
    for p in answer_packets:
        errs = validate_generated_answer_packet(p)
        if errs:
            packet_errors.append({"question_number": p.get("question_number"), "errors": errs})
        if not (p.get("safety_checks") or {}).get("oracle_sensitive_terms_supported_or_absent", True):
            unsupported_forbidden += 1

    oracle_path_hits = sorted(
        {
            h
            for p in answer_packets
            for h in ((p.get("evaluator_control_metadata") or {}).get("oracle_leakage_check") or {}).get(
                "forbidden_path_hits", []
            )
        }
    )
    oracle_session_hits = sorted(
        {
            h
            for p in answer_packets
            for h in ((p.get("evaluator_control_metadata") or {}).get("oracle_leakage_check") or {}).get(
                "forbidden_session_hits", []
            )
        }
    )
    return {
        "schema": "dmb_c1s4_step4_generated_answer_packet_summary_v1",
        "campaign_id": step2.get("campaign_id", "longmont-c1"),
        "retrieval_mode": mode,
        "generator": generator,
        "answer_generation_status": "generated",
        "counts": {
            "context_packets_seen": len(answer_packets) + len(step2["skipped_questions"]),
            "answer_packets_built": len(answer_packets),
            "questions_skipped": len(step2["skipped_questions"]),
            "packets_with_oracle_leakage": sum(
                1
                for p in answer_packets
                if ((p.get("evaluator_control_metadata") or {}).get("oracle_leakage_check") or {}).get(
                    "forbidden_path_hits"
                )
                or ((p.get("evaluator_control_metadata") or {}).get("oracle_leakage_check") or {}).get(
                    "forbidden_session_hits"
                )
            ),
            "packets_with_unsupported_forbidden_terms": unsupported_forbidden,
            "packets_with_validation_errors": len(packet_errors),
        },
        "skipped_questions": step2["skipped_questions"],
        "oracle_leakage_check": {"forbidden_path_hits": oracle_path_hits, "forbidden_session_hits": oracle_session_hits},
        "validation_errors": packet_errors,
        "answer_packets": answer_packets,
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--mode", required=True, choices=["prior_only", "prior_plus_support_content_only", "prior_plus_support_content_plus_lexical_hints"])
    parser.add_argument("--question-number", type=int)
    parser.add_argument("--limit", type=int)
    parser.add_argument("--generator", default="template_stub", choices=["template_stub"])
    parser.add_argument("--output-json", type=Path)
    args = parser.parse_args()
    try:
        summary = build_summary(mode=args.mode, question_number=args.question_number, limit=args.limit, generator=args.generator)
    except C1S4BoundaryError as exc:
        print(json.dumps({"schema": "dmb_c1s4_step4_generated_answer_packet_summary_v1", "error": str(exc)}, indent=2))
        return 1

    if args.output_json:
        args.output_json.write_text(json.dumps(summary, indent=2), encoding="utf-8")
    print(json.dumps(summary, indent=2))

    leaks = summary["oracle_leakage_check"]["forbidden_path_hits"] or summary["oracle_leakage_check"]["forbidden_session_hits"]
    counts = summary["counts"]
    return 1 if leaks or counts["packets_with_validation_errors"] or counts["packets_with_unsupported_forbidden_terms"] else 0


if __name__ == "__main__":
    raise SystemExit(main())
