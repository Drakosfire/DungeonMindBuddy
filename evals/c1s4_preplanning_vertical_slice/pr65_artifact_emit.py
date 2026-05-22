from __future__ import annotations

import argparse
import csv
import json
import sys
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from evals.c1s4_preplanning_vertical_slice.planner_surface_coverage import (
    build_next_pr_recommendations_markdown,
    build_planner_surface_rows,
    summarize_planner_surface_rows,
)

MATRIX_COLUMNS = [
    "question_number",
    "question_id",
    "beat_id",
    "beat_number",
    "mode",
    "planner_facing",
    "authority_label",
    "oracle_risk",
    "expected_mode_behavior",
    "prompt_payload_valid",
    "forbidden_prompt_key_hits",
    "forbidden_prompt_value_hits",
    "rendered_context_present",
    "admitted_context_count",
    "rendered_section_count",
    "estimated_rendered_tokens",
    "support_knowledge_allowed",
    "support_required",
    "support_context_rendered",
    "first_support_candidate_rank",
    "first_support_admitted_rank",
    "support_token_share",
    "source_derived_gap_count",
    "known_context_gaps_leaked",
    "must_not_include_term_count",
    "must_not_include_terms_in_prompt_payload",
    "generated_answer_control_leak",
    "retrieval_sufficiency_class",
    "next_failure_surface",
]


def _matrix_row(row: dict[str, Any]) -> dict[str, Any]:
    out = {col: row.get(col) for col in MATRIX_COLUMNS}
    prompt_terms = row.get("must_not_include_terms_in_prompt_payload") or []
    out["must_not_include_terms_in_prompt_payload"] = "|".join(str(t) for t in prompt_terms)
    return out


def write_pr65_artifacts(*, output_dir: Path, include_evaluator_only: bool = True) -> dict[str, Any]:
    output_dir.mkdir(parents=True, exist_ok=True)
    rows = build_planner_surface_rows(include_evaluator_only=include_evaluator_only)
    summary = summarize_planner_surface_rows(rows)

    matrix_rows = [_matrix_row(r) for r in rows if r.get("planner_facing")]
    with (output_dir / "pr65_planner_surface_coverage_matrix.csv").open("w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=MATRIX_COLUMNS)
        writer.writeheader()
        writer.writerows(matrix_rows)

    evaluator_rows = [r for r in rows if not r.get("planner_facing")]
    with (output_dir / "pr65_evaluator_only_skips.csv").open("w", newline="", encoding="utf-8") as f:
        if evaluator_rows:
            fields = ["question_number", "question_id", "mode", "planner_facing", "next_failure_surface", "expected_mode_behavior"]
            writer = csv.DictWriter(f, fieldnames=fields)
            writer.writeheader()
            for row in evaluator_rows:
                writer.writerow({k: row.get(k) for k in fields})

    failure_counts = summary.get("failure_surface_counts") or {}
    with (output_dir / "pr65_failure_surface_counts.csv").open("w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=["failure_surface", "count"])
        writer.writeheader()
        for surface, count in sorted(failure_counts.items(), key=lambda kv: (-kv[1], kv[0])):
            writer.writerow({"failure_surface": surface, "count": count})

    findings = {
        "schema": "dmb_pr65_question_mode_findings_v1",
        "rows_by_next_failure_surface": {},
        "rows_by_retrieval_sufficiency_class": {},
    }
    for row in rows:
        if not row.get("planner_facing"):
            continue
        surface = str(row.get("next_failure_surface") or "unknown")
        cls = str(row.get("retrieval_sufficiency_class") or "unknown")
        findings["rows_by_next_failure_surface"].setdefault(surface, []).append(
            {"question_number": row.get("question_number"), "question_id": row.get("question_id"), "mode": row.get("mode")}
        )
        findings["rows_by_retrieval_sufficiency_class"].setdefault(cls, []).append(
            {"question_number": row.get("question_number"), "question_id": row.get("question_id"), "mode": row.get("mode")}
        )
    (output_dir / "pr65_question_mode_findings.json").write_text(json.dumps(findings, indent=2), encoding="utf-8")
    (output_dir / "pr65_planner_surface_summary.json").write_text(json.dumps(summary, indent=2), encoding="utf-8")
    (output_dir / "pr65_next_pr_recommendations.md").write_text(
        build_next_pr_recommendations_markdown(summary, rows),
        encoding="utf-8",
    )
    (output_dir / "README.md").write_text(
        "# PR65 planner-surface coverage artifacts\n\n"
        "Broad Tier B coverage audit for all 37 planner-facing C1S4 questions across three retrieval modes.\n"
        "Hard prompt/control boundaries are gated in tests; retrieval insufficiency is classified, not repaired.\n",
        encoding="utf-8",
    )
    return summary


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--output-dir",
        type=Path,
        default=Path("evals/c1s4_preplanning_vertical_slice/artifacts/pr65"),
    )
    args = parser.parse_args()
    summary = write_pr65_artifacts(output_dir=args.output_dir)
    print(json.dumps(summary, indent=2))
    hard = summary.get("hard_boundary_failures") or {}
    if any(hard.values()):
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
