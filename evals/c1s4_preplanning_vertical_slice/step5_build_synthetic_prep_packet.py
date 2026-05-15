from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from evals.c1s4_preplanning_vertical_slice.step4_generate_answer_packets import C1S4BoundaryError, build_summary as build_step4_summary
from evals.c1s4_preplanning_vertical_slice.synthetic_prep_packet_harness import build_synthetic_prep_packet, validate_synthetic_prep_packet


def build_summary(*, mode: str, generator: str) -> dict:
    step4 = build_step4_summary(mode=mode, generator=generator)
    packet = build_synthetic_prep_packet(
        answer_packets=step4["answer_packets"],
        skipped_questions=step4["skipped_questions"],
        retrieval_mode=mode,
        generator=generator,
    )
    validation_errors = validate_synthetic_prep_packet(packet)
    leaks = packet["oracle_leakage_check"]
    unsupported = packet["safety_summary"].get("unsupported_claim_warnings", 0)
    return {
        "schema": "dmb_c1s4_step5_synthetic_prep_packet_summary_v1",
        "campaign_id": packet.get("campaign_id", "longmont-c1"),
        "retrieval_mode": mode,
        "generator": generator,
        "prep_packet_built": len(validation_errors) == 0,
        "counts": {
            "answer_packets_seen": len(step4["answer_packets"]),
            "sections_built": len(packet["sections"]),
            "questions_skipped": len(step4["skipped_questions"]),
            "sections_with_known_gaps": sum(1 for s in packet["sections"] if s.get("section_known_gaps")),
            "packets_with_oracle_leakage": step4["counts"]["packets_with_oracle_leakage"],
            "packets_with_unsupported_forbidden_terms": unsupported,
            "validation_errors": len(validation_errors),
        },
        "skipped_questions": step4["skipped_questions"],
        "oracle_leakage_check": leaks,
        "validation_errors": validation_errors,
        "prep_packet": packet,
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--mode", required=True, choices=["prior_only", "prior_plus_support_content_only", "prior_plus_support_content_plus_lexical_hints"])
    parser.add_argument("--generator", default="template_stub", choices=["template_stub"])
    parser.add_argument("--output-json", type=Path)
    args = parser.parse_args()

    try:
        summary = build_summary(mode=args.mode, generator=args.generator)
    except C1S4BoundaryError as exc:
        print(json.dumps({"schema": "dmb_c1s4_step5_synthetic_prep_packet_summary_v1", "error": str(exc)}, indent=2))
        return 1

    if args.output_json:
        args.output_json.write_text(json.dumps(summary, indent=2), encoding="utf-8")
    print(json.dumps(summary, indent=2))

    leaks = summary["oracle_leakage_check"]["forbidden_path_hits"] or summary["oracle_leakage_check"]["forbidden_session_hits"]
    counts = summary["counts"]
    return 1 if leaks or counts["validation_errors"] or counts["packets_with_unsupported_forbidden_terms"] or summary["prep_packet_built"] is False else 0


if __name__ == "__main__":
    raise SystemExit(main())
