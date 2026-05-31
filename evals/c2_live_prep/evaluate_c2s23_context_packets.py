#!/usr/bin/env python3
"""Evaluate C2S23 enriched planning context packets against evidence-reference gold."""

from __future__ import annotations

import argparse
import json
from datetime import date, datetime, timezone
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[2]

DEFAULT_GOLD = ROOT / "evals/c2_live_prep/benchmarks/c2s23_route_evidence_gold.json"
DEFAULT_PACKET_DIR = ROOT / "evals/c2_live_prep/artifacts/runs" / str(date.today())
DEFAULT_SUMMARY = DEFAULT_PACKET_DIR / "c2s23_manifest_context_benchmark_summary.json"


def _utc_now_z() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def load_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def _norm(path: str) -> str:
    return path.strip().replace("\\", "/").lower().lstrip("./")


def check_claim_expectation(packet: dict[str, Any], claim: dict[str, Any]) -> tuple[bool, list[str]]:
    violations: list[str] = []
    admitted = list(packet.get("admitted_evidence") or [])
    rejected = list(packet.get("rejected_evidence") or [])
    claims = list(packet.get("claims") or [])
    capability = dict(packet.get("capability_status") or {})
    blocked = list(packet.get("blocked_or_missing") or [])
    excerpt = str(packet.get("source_excerpt") or "")

    required_auth = set(claim.get("required_authority_any") or [])
    if required_auth:
        seen_auth = {str(e.get("authority") or "") for e in admitted}
        if not (required_auth & seen_auth):
            violations.append(f"missing_required_authority_any:{sorted(required_auth)}")

    forbidden_roles = set(claim.get("forbidden_evidence_roles") or [])
    for e in admitted:
        role = str(e.get("source_role") or "")
        if role in forbidden_roles:
            violations.append(f"forbidden_role_admitted:{role}")

    path_contains = [str(x) for x in claim.get("acceptable_path_contains_any") or []]
    if path_contains:
        admitted_paths = [_norm(str(e.get("path") or "")) for e in admitted]
        found = False
        for needle in path_contains:
            n = _norm(needle)
            if any(n in p for p in admitted_paths):
                found = True
                break
        if not found:
            violations.append("missing_acceptable_path_contains_any")

    required_states_any = set(claim.get("required_state_flags_any") or [])
    if required_states_any:
        corpus_checks = packet.get("corpus_preconditions", {}).get("checks", [])
        observed = {str(c.get("key") or "") for c in corpus_checks if c.get("exists")}
        if not (required_states_any & observed):
            violations.append("missing_required_state_flags_any")

    required_capability_status_any = set(claim.get("required_capability_status_any") or [])
    if required_capability_status_any:
        got = str(capability.get("status") or "")
        if got not in required_capability_status_any:
            violations.append(f"capability_status_unexpected:{got}")

    if bool(claim.get("must_report_blocker")) and not blocked:
        violations.append("missing_blocked_or_missing_entry")

    required_verdict_contains_any = [str(x) for x in claim.get("required_verdict_contains_any") or []]
    if required_verdict_contains_any:
        if not any(token in excerpt for token in required_verdict_contains_any):
            violations.append("missing_required_verdict_phrase")

    # Basic packet hygiene checks for all claims
    if not claims:
        violations.append("missing_claims")
    if not admitted and not rejected:
        violations.append("missing_evidence_lists")

    return (len(violations) == 0), violations


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--gold", type=Path, default=DEFAULT_GOLD)
    parser.add_argument("--packet-dir", type=Path, default=DEFAULT_PACKET_DIR)
    parser.add_argument("--summary", type=Path, default=DEFAULT_SUMMARY)
    parser.add_argument(
        "--output",
        type=Path,
        default=ROOT / "evals/c2_live_prep/artifacts/last_c2s23_context_packet_eval.json",
    )
    args = parser.parse_args()

    gold = load_json(args.gold.resolve())
    summary = load_json(args.summary.resolve())
    packet_dir = args.packet_dir.resolve()

    if str(gold.get("schema") or "") != "dmb_c2s23_route_evidence_gold_v1":
        raise SystemExit("unexpected gold schema")
    if str(summary.get("schema") or "") != "dmb_c2s23_manifest_context_benchmark_run_v1":
        raise SystemExit("unexpected packet summary schema")

    by_question = {
        str(q.get("question_id") or ""): q for q in list(gold.get("questions") or []) if isinstance(q, dict)
    }
    rows: list[dict[str, Any]] = []
    passed = 0
    failed = 0

    for qid, spec in by_question.items():
        packet_path = packet_dir / f"c2s23_context_packet_{qid}.json"
        if not packet_path.is_file():
            rows.append(
                {
                    "question_id": qid,
                    "passed": False,
                    "violations": ["missing_packet_file"],
                }
            )
            failed += 1
            continue

        packet = load_json(packet_path)
        claim_specs = list(spec.get("claim_expectations") or [])
        all_violations: list[str] = []
        for c in claim_specs:
            ok, violations = check_claim_expectation(packet, c)
            if not ok:
                all_violations.extend(violations)

        is_pass = len(all_violations) == 0
        rows.append({"question_id": qid, "passed": is_pass, "violations": all_violations})
        if is_pass:
            passed += 1
        else:
            failed += 1

    out = {
        "schema": "dmb_c2s23_context_packet_eval_v1",
        "generated_at": _utc_now_z(),
        "gold_path": str(args.gold.resolve().relative_to(ROOT)),
        "packet_dir": str(packet_dir.relative_to(ROOT)),
        "questions_total": len(rows),
        "questions_passed": passed,
        "questions_failed": failed,
        "rows": rows,
    }
    args.output.resolve().write_text(json.dumps(out, indent=2, ensure_ascii=False), encoding="utf-8")
    print(json.dumps(out, indent=2, ensure_ascii=False))
    return 0 if failed == 0 else 1


if __name__ == "__main__":
    raise SystemExit(main())
