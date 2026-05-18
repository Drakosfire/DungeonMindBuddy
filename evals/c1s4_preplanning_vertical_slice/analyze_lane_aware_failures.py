from __future__ import annotations

import argparse
import csv
import json
from collections import Counter, defaultdict
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from evals.c1s4_preplanning_vertical_slice.expected_context_benchmark import match_context_item

TARGET_Q = {1, 3, 5}


def _find_gold_question(gold: dict, question_id: str) -> dict:
    for row in gold.get("questions", []):
        if row.get("question_id") == question_id:
            return row
    return {}


def _group_match_count(items: list[dict], match: dict) -> int:
    return sum(1 for item in items if match_context_item(item, match))


def _first_rank(items: list[dict], match: dict) -> int | None:
    for idx, item in enumerate(items, start=1):
        if match_context_item(item, match):
            return idx
    return None


def _classify(*, mode: str, reasons: list[str], retrieved: int, candidate: int, admitted: int, rendered: int) -> tuple[str, str]:
    if "navigation_only_context" in reasons:
        return "navigation_only_rejected", "navigation_only_context"
    if any(r in {"incompatible_required_lane", "wrong_subject_class", "disallowed_subject_class"} for r in reasons):
        return "wrong_lane_or_subject", next(r for r in reasons if r in {"incompatible_required_lane", "wrong_subject_class", "disallowed_subject_class"})
    if "wrong_rendered_section" in reasons:
        return "wrong_rendered_section", "wrong_rendered_section"
    if "support_mode_policy" in reasons:
        return "support_mode_policy", "support_mode_policy"
    if retrieved == 0:
        return "retrieval_miss", "no_group_match_in_retrieved_context"
    if candidate == 0:
        return "candidate_present_admission_miss", "retrieved_match_not_in_candidate_context"
    if admitted == 0:
        return "candidate_present_admission_miss", "candidate_match_not_in_admitted_context"
    if rendered == 0:
        return "admitted_not_rendered", "admitted_match_missing_in_rendered_packet"
    if mode == "prior_only" and rendered > 0 and "support" in " ".join(reasons):
        return "support_mode_policy", "support_signal_in_prior_only"
    return "retrieval_tuning_deferred", "ambiguous_after_surface_scan"


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--input-json", type=Path, required=True)
    ap.add_argument("--output-dir", type=Path, required=True)
    ap.add_argument("--gold-json", type=Path, default=Path("evals/c1s4_preplanning_vertical_slice/gold/c1s4_expected_context_gold.json"))
    args = ap.parse_args()

    data = json.loads(args.input_json.read_text())
    gold = json.loads(args.gold_json.read_text())
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
            qgold = _find_gold_question(gold, row.get("question_id", ""))
            mode_expectations = (qgold.get("expectations_by_mode") or {}).get(mode, {})
            required_by_gid = {
                g.get("group_id"): g
                for g in mode_expectations.get("required_context_groups", [])
            }
            diag = row.get("lane_aware_diagnostics", {})
            group_results = {g["group_id"]: g for g in diag.get("required_group_results", [])}

            for gid in row.get("missing_required_groups", []):
                grp = required_by_gid.get(gid, {})
                match = grp.get("match", {})
                gr = group_results.get(gid, {"group_id": gid, "accepted_matches": [], "rejected_matches": []})
                rejected = gr.get("rejected_matches", [])
                accepted = gr.get("accepted_matches", [])

                retrieved_items = row.get("retrieved_context") or row.get("retrieved_context_preview") or []
                candidate_items = row.get("candidate_context") or []
                admitted_items = row.get("admitted_context") or []

                rendered_refs = set((row.get("rendered_context_packet", {}).get("provenance_map") or {}).keys())
                rendered_matches = [m for m in accepted if m.get("context_ref") in rendered_refs]

                retrieved_count = _group_match_count(retrieved_items, match) if match else 0
                candidate_count = _group_match_count(candidate_items, match) if match else len(accepted) + len(rejected)
                admitted_count = _group_match_count(admitted_items, match) if match else len(accepted)
                rendered_count = len(rendered_matches)

                reasons = [r.get("reason", "") for r in rejected]
                fclass, reason = _classify(mode=mode, reasons=reasons, retrieved=retrieved_count, candidate=candidate_count, admitted=admitted_count, rendered=rendered_count)

                r0 = rejected[0] if rejected else {}
                rows.append({
                    "mode": mode,
                    "question_number": qn,
                    "question_id": row.get("question_id"),
                    "group_id": gid,
                    "required_lane": grp.get("required_lane", r0.get("required_lane", "")),
                    "expected_rendered_section": grp.get("expected_rendered_section", r0.get("expected_rendered_section", "")),
                    "legacy_hit": gid in diag.get("legacy_would_have_hit_groups", []),
                    "lane_aware_hit": False,
                    "failure_class": fclass,
                    "primary_reason": reason,
                    "retrieved_text_match_count": retrieved_count,
                    "candidate_match_count": candidate_count,
                    "admitted_match_count": admitted_count,
                    "rendered_match_count": rendered_count,
                    "accepted_match_count": len(accepted),
                    "rejected_match_count": len(rejected),
                    "top_rejected_reason": reasons[0] if reasons else "",
                    "first_candidate_rank": _first_rank(candidate_items, match) if match else "",
                    "first_admitted_rank": _first_rank(admitted_items, match) if match else "",
                    "rendered_section_seen": r0.get("rendered_section", ""),
                    "source_kind_seen": r0.get("source_kind", ""),
                    "subject_class_seen": r0.get("subject_class", ""),
                    "notes": "",
                })
                counts_by_mode[mode][fclass] += 1
                counts_by_class[fclass] += 1
                q_summary[str(qn)][mode].append({"group_id": gid, "failure_class": fclass, "reason": reason})

    fields = list(rows[0].keys()) if rows else []
    with (out / "pr56_q1_q3_q5_failure_matrix.csv").open("w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=fields)
        w.writeheader()
        w.writerows(rows)

    summary = {
        "schema": "dmb_pr56_lane_aware_failure_summary_v1",
        "source_report": str(args.input_json),
        "counts_by_mode": {k: dict(v) for k, v in counts_by_mode.items()},
        "counts_by_failure_class": dict(counts_by_class),
        "question_summaries": {k: dict(v) for k, v in q_summary.items()},
        "recommendations": [
            "retrieval_indexing: verify C1S4 index build includes session_memory, npc_hub, and location_hub artifacts referenced by Q1/Q3/Q5 groups.",
            "retrieval_indexing: audit path aliases/canonicalization for Stone Bridge, Mirathorn, and Hempholm so group tokens match indexable fields.",
            "retrieval_indexing: add a diagnostic check in Step2C to fail fast when retrieved_context_count==0 for all three modes on gold questions.",
            "admission_budgeting (deferred): only evaluate lane-floor/budget tuning after non-zero candidate_match_count appears for failed groups.",
            "rendering_or_provenance (deferred): only evaluate section-routing fixes after admitted_match_count becomes non-zero.",
        ],
    }
    (out / "pr56_step2c_lane_aware_summary.json").write_text(json.dumps(summary, indent=2), encoding="utf-8")

    (out / "README.md").write_text("# PR56 artifacts\n\nGenerated from Step 2C multimode lane-aware report with group-level surface scans (retrieved/candidate/admitted/rendered).\n", encoding="utf-8")
    (out / "pr56_next_pr_recommendations.md").write_text(
        "# PR57 recommendations\n\n"
        "1. **Retrieval indexing**: verify index population for `session_memory`, `npc_hub`, `location_hub` sources used by Q1/Q3/Q5 required groups.\n"
        "2. **Path/canonicalization audit**: validate source-path aliases for Stone Bridge, Mirathorn, and Hempholm to ensure retriever term/path hits.\n"
        "3. **Guardrail diagnostic**: add a Step2C warning/error path when all three modes return zero retrieved context for benchmark questions.\n"
        "4. **Admission tuning deferred**: do not tune lane budgets until candidate matches are non-zero for missing groups.\n"
        "5. **Rendering tuning deferred**: do not tune section mapping until admitted matches are non-zero.\n",
        encoding="utf-8",
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
