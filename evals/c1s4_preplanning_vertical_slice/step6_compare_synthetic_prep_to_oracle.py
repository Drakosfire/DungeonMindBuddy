from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from evals.c1s4_preplanning_vertical_slice.oracle_comparison_harness import (
    build_oracle_comparison_report,
    load_oracle_policy,
    load_oracle_text,
    validate_oracle_comparison_report,
)
from evals.c1s4_preplanning_vertical_slice.step5_build_synthetic_prep_packet import C1S4BoundaryError, build_summary as build_step5_summary


def build_summary(*, mode: str, generator: str, oracle_policy_path: Path | None = None) -> dict:
    step5 = build_step5_summary(mode=mode, generator=generator)
    prep_packet = step5["prep_packet"]
    oracle_policy = load_oracle_policy(oracle_policy_path)
    oracle_text_bundle = load_oracle_text(oracle_policy)
    report = build_oracle_comparison_report(prep_packet=prep_packet, oracle_policy=oracle_policy, oracle_text_bundle=oracle_text_bundle)
    validation_errors = validate_oracle_comparison_report(report)
    return {
        "schema": "dmb_c1s4_step6_oracle_comparison_summary_v1",
        "campaign_id": prep_packet.get("campaign_id", "longmont-c1"),
        "retrieval_mode": mode,
        "generator": generator,
        "oracle_visibility": "step6_only",
        "comparison_status": "scaffold_coarse_comparison",
        "counts": {
            "sections_compared": report["summary"]["sections_compared"],
            "sections_with_overlap": report["summary"]["sections_with_overlap"],
            "unsupported_claims_found": report["summary"]["unsupported_claims_found"],
            "oracle_sensitive_terms_found": report["summary"]["oracle_sensitive_terms_found"],
            "validation_errors": len(validation_errors),
        },
        "validation_errors": validation_errors,
        "report": report,
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--mode", required=True, choices=["prior_only", "prior_plus_support_content_only", "prior_plus_support_content_plus_lexical_hints"])
    parser.add_argument("--generator", default="template_stub", choices=["template_stub"])
    parser.add_argument("--oracle-policy", type=Path)
    parser.add_argument("--output-json", type=Path)
    args = parser.parse_args()

    try:
        summary = build_summary(mode=args.mode, generator=args.generator, oracle_policy_path=args.oracle_policy)
    except C1S4BoundaryError as exc:
        print(json.dumps({"schema": "dmb_c1s4_step6_oracle_comparison_summary_v1", "error": str(exc)}, indent=2))
        return 1

    if args.output_json:
        args.output_json.write_text(json.dumps(summary, indent=2), encoding="utf-8")
    print(json.dumps(summary, indent=2))
    return 1 if summary["validation_errors"] else 0


if __name__ == "__main__":
    raise SystemExit(main())
