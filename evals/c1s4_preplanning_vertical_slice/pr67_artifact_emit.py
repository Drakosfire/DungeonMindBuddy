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

from evals.c1s4_preplanning_vertical_slice.pr67_required_group_diagnostics import build_pr67_required_group_diagnostics

MATRIX_COLUMNS = [
    "question_number",
    "question_id",
    "mode",
    "group_id",
    "required_lane",
    "expected_rendered_section",
    "candidate_match_count",
    "first_candidate_rank",
    "first_candidate_ref",
    "first_candidate_source_kind",
    "visibility_excluded",
    "admitted",
    "first_admitted_rank",
    "admission_rejection_reason",
    "rendered",
    "rendered_section",
    "legacy_match",
    "lane_aware_accepted",
    "lane_aware_rejection_reason",
    "miss_root_cause",
    "grading_context_kind",
    "effective_grading_surface",
]


def _matrix_row(row: dict[str, Any]) -> dict[str, Any]:
    match_surface = row.get("match_surface") or {}
    admission_surface = row.get("admission_surface") or {}
    render_surface = row.get("render_surface") or {}
    grading_surface = row.get("grading_surface") or {}
    return {
        "question_number": row.get("question_number"),
        "question_id": row.get("question_id"),
        "mode": row.get("mode"),
        "group_id": row.get("group_id"),
        "required_lane": row.get("required_lane"),
        "expected_rendered_section": row.get("expected_rendered_section"),
        "candidate_match_count": match_surface.get("candidate_match_count"),
        "first_candidate_rank": match_surface.get("first_candidate_rank"),
        "first_candidate_ref": match_surface.get("first_candidate_ref"),
        "first_candidate_source_kind": match_surface.get("first_candidate_source_kind"),
        "visibility_excluded": match_surface.get("visibility_excluded"),
        "admitted": admission_surface.get("admitted"),
        "first_admitted_rank": admission_surface.get("first_admitted_rank"),
        "admission_rejection_reason": admission_surface.get("admission_rejection_reason"),
        "rendered": render_surface.get("rendered"),
        "rendered_section": render_surface.get("rendered_section"),
        "legacy_match": grading_surface.get("legacy_match"),
        "lane_aware_accepted": grading_surface.get("lane_aware_accepted"),
        "lane_aware_rejection_reason": grading_surface.get("lane_aware_rejection_reason"),
        "miss_root_cause": row.get("miss_root_cause"),
        "grading_context_kind": grading_surface.get("grading_context_kind"),
        "effective_grading_surface": grading_surface.get("effective_grading_surface"),
    }


def build_next_pr_recommendations_markdown(diagnostics: dict[str, Any]) -> str:
    causes = diagnostics.get("tier_a_miss_root_causes") or {}
    q3 = diagnostics.get("q3_prior_distance_probe_by_mode") or {}
    lines = [
        "# PR67 next PR recommendations",
        "",
        "## Tier A miss root causes",
        "",
    ]
    for cause, count in sorted(causes.items(), key=lambda kv: -kv[1]):
        lines.append(f"- `{cause}`: {count}")
    lines.extend(["", "## Q3 prior-distance probe (mirathorn + week)", ""])
    for mode, probe in sorted(q3.items()):
        lines.append(
            f"- **{mode}**: merged_rank={probe.get('merged_candidate_first_rank')} "
            f"admitted_rank={probe.get('admitted_rank')} failure_stage={probe.get('failure_stage')}"
        )
    lines.extend(
        [
            "",
            "## Recommended follow-ups",
            "",
            "1. If Q3 `failure_stage=admission` persists after route-event preservation, inspect lane budgets for `prior_campaign_memory`.",
            "2. Q5 should pass strict gold in support modes after visibility-contract gold realignment; do not admit Hempholm campaign hub.",
            "3. Keep legacy `top_k=9` labeled as preview/scoring shim only (`grading_surface_labels`).",
            "",
        ]
    )
    return "\n".join(lines)


def write_pr67_artifacts(*, output_dir: Path) -> dict[str, Any]:
    output_dir.mkdir(parents=True, exist_ok=True)
    diagnostics = build_pr67_required_group_diagnostics()
    (output_dir / "pr67_required_group_admission_diagnostics.json").write_text(
        json.dumps(diagnostics, indent=2),
        encoding="utf-8",
    )
    matrix_rows = [_matrix_row(r) for r in diagnostics.get("rows") or []]
    with (output_dir / "pr67_required_group_admission_matrix.csv").open("w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=MATRIX_COLUMNS)
        writer.writeheader()
        writer.writerows(matrix_rows)
    (output_dir / "pr67_next_pr_recommendations.md").write_text(
        build_next_pr_recommendations_markdown(diagnostics),
        encoding="utf-8",
    )
    (output_dir / "README.md").write_text(
        "PR67 admission-decision diagnostics for strict-gold required groups (tier A focus).\n",
        encoding="utf-8",
    )
    return diagnostics


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--output-dir",
        type=Path,
        default=Path("evals/c1s4_preplanning_vertical_slice/artifacts/pr67"),
    )
    args = parser.parse_args()
    diagnostics = write_pr67_artifacts(output_dir=args.output_dir)
    print(json.dumps({"schema": diagnostics.get("schema"), "row_count": diagnostics.get("row_count")}, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
