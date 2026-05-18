from __future__ import annotations

import argparse, csv, json
from collections import Counter, defaultdict
from pathlib import Path

TARGET_Q = {1,3,5}


def _classify(group_result: dict, row: dict, mode: str) -> tuple[str,str]:
    rej = group_result.get("rejected_matches", [])
    acc = group_result.get("accepted_matches", [])
    reasons = [r.get("reason","") for r in rej]
    if any(r == "navigation_only_context" for r in reasons):
        return "navigation_only_rejected", "navigation_only_context"
    if any(r in {"incompatible_required_lane", "wrong_subject_class", "disallowed_subject_class"} for r in reasons):
        return "wrong_lane_or_subject", next(r for r in reasons if r in {"incompatible_required_lane", "wrong_subject_class", "disallowed_subject_class"})
    if any(r == "wrong_rendered_section" for r in reasons):
        return "wrong_rendered_section", "wrong_rendered_section"
    if any(r == "support_mode_policy" for r in reasons) or (mode == "prior_only" and any("support" in (m.get("inferred_lane") or "") for m in rej)):
        return "support_mode_policy", "support_mode_policy"
    if acc and not row.get("rendered_context_packet", {}).get("provenance_map"):
        return "admitted_not_rendered", "accepted_match_missing_provenance"
    cand = row.get("candidate_context") or []
    adm = row.get("admitted_context") or []
    if cand and not adm:
        return "candidate_present_admission_miss", "candidate_context_present_but_not_admitted"
    if not cand and not rej and not acc:
        return "retrieval_miss", "no_candidate_or_lane_aware_matches"
    if row.get("known_gap_expectations_hit") and "known_gap" in group_result.get("group_id",""):
        return "known_gap_visibility", "known_gap_expectation_partial"
    return "retrieval_tuning_deferred", "ambiguous"


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--input-json", type=Path, required=True)
    ap.add_argument("--output-dir", type=Path, required=True)
    args = ap.parse_args()

    data = json.loads(args.input_json.read_text())
    out = args.output_dir
    out.mkdir(parents=True, exist_ok=True)

    rows = []
    counts_by_mode = defaultdict(Counter)
    counts_by_class = Counter()
    q_summary = defaultdict(lambda: defaultdict(list))

    for mode, report in data["reports_by_mode"].items():
        for row in report.get("results", []):
            qn = row.get("question_number")
            if qn not in TARGET_Q:
                continue
            diag = row.get("lane_aware_diagnostics", {})
            group_results = {g["group_id"]: g for g in diag.get("required_group_results", [])}
            for gid in row.get("missing_required_groups", []):
                gr = group_results.get(gid, {"group_id": gid, "accepted_matches": [], "rejected_matches": []})
                fclass, reason = _classify(gr, row, mode)
                rejected = gr.get("rejected_matches", [])
                accepted = gr.get("accepted_matches", [])
                top_rej = rejected[0].get("reason") if rejected else ""
                r0 = rejected[0] if rejected else {}
                a0 = accepted[0] if accepted else {}
                rows.append({
                    "mode": mode,
                    "question_number": qn,
                    "question_id": row.get("question_id"),
                    "group_id": gid,
                    "required_lane": r0.get("required_lane", ""),
                    "expected_rendered_section": r0.get("expected_rendered_section", ""),
                    "legacy_hit": gid in diag.get("legacy_would_have_hit_groups", []),
                    "lane_aware_hit": False,
                    "failure_class": fclass,
                    "primary_reason": reason,
                    "candidate_match_count": len(accepted)+len(rejected),
                    "accepted_match_count": len(accepted),
                    "rejected_match_count": len(rejected),
                    "top_rejected_reason": top_rej,
                    "first_candidate_rank": r0.get("candidate_rank", ""),
                    "first_admitted_rank": a0.get("admitted_rank", ""),
                    "rendered_section_seen": r0.get("rendered_section", a0.get("rendered_section", "")),
                    "source_kind_seen": r0.get("source_kind", a0.get("source_kind", "")),
                    "subject_class_seen": r0.get("subject_class", a0.get("subject_class", "")),
                    "notes": "",
                })
                counts_by_mode[mode][fclass] += 1
                counts_by_class[fclass] += 1
                q_summary[str(qn)][mode].append({"group_id": gid, "failure_class": fclass, "reason": reason})

    csv_path = out / "pr56_q1_q3_q5_failure_matrix.csv"
    fields = list(rows[0].keys()) if rows else []
    with csv_path.open("w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=fields)
        w.writeheader(); w.writerows(rows)

    summary = {
        "schema": "dmb_pr56_lane_aware_failure_summary_v1",
        "source_report": str(args.input_json),
        "counts_by_mode": {k: dict(v) for k,v in counts_by_mode.items()},
        "counts_by_failure_class": dict(counts_by_class),
        "question_summaries": {k: dict(v) for k,v in q_summary.items()},
        "recommendations": [
            "retrieval_indexing: retrieved/candidate counts are often zero; verify indexing and route expansion for session memory, npc_hub, location_hub artifacts.",
            "admission_budgeting: if candidate>admitted in future reruns, add lane floors per required lane before tuning ranker.",
            "rendering_or_provenance: if accepted matches appear without provenance, audit section map/provenance emission.",
        ],
    }
    (out / "pr56_step2c_lane_aware_summary.json").write_text(json.dumps(summary, indent=2), encoding="utf-8")

    (out / "README.md").write_text("# PR56 artifacts\n\nGenerated from Step 2C multimode lane-aware report.\n", encoding="utf-8")
    (out / "pr56_next_pr_recommendations.md").write_text("# PR57 recommendations\n\n- retrieval_indexing\n- admission_budgeting\n- rendering_or_provenance\n", encoding="utf-8")
    (out / "pr56_step2c_failure_analysis.md").write_text("# PR56 Step 2C Lane-Aware Failure Analysis\n\n## Scope\nQ1/Q3/Q5 across all retrieval modes.\n\n## Commands Run\n- `uv run python evals/c1s4_preplanning_vertical_slice/step2c_expected_context_benchmark.py --all-modes --output-json /tmp/c1s4_pr56_lane_aware_step2c_multimode_report.json`\n- `uv run python evals/c1s4_preplanning_vertical_slice/analyze_lane_aware_failures.py --input-json /tmp/c1s4_pr56_lane_aware_step2c_multimode_report.json --output-dir evals/c1s4_preplanning_vertical_slice/artifacts/pr56`\n\n## Summary Counts\n" + json.dumps(summary["counts_by_failure_class"], indent=2) + "\n", encoding="utf-8")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
