from pathlib import Path

from evals.c1s4_preplanning_vertical_slice.pr65_artifact_emit import write_pr65_artifacts


def test_pr65_artifacts_emit_summary_and_matrix(tmp_path: Path) -> None:
    summary = write_pr65_artifacts(output_dir=tmp_path / "pr65")
    out = tmp_path / "pr65"
    assert (out / "pr65_planner_surface_coverage_matrix.csv").exists()
    assert (out / "pr65_planner_surface_summary.json").exists()
    assert (out / "pr65_failure_surface_counts.csv").exists()
    assert (out / "pr65_question_mode_findings.json").exists()
    assert (out / "pr65_evaluator_only_skips.csv").exists()
    assert (out / "pr65_next_pr_recommendations.md").exists()
    assert summary["schema"] == "dmb_pr65_planner_surface_summary_v1"
    assert summary["planner_surface_rows"] == 111


def test_pr65_summary_reports_failure_surface_counts(tmp_path: Path) -> None:
    summary = write_pr65_artifacts(output_dir=tmp_path / "pr65")
    assert summary["failure_surface_counts"]
    assert sum(summary["failure_surface_counts"].values()) == 111
    assert summary["next_recommended_pr"]
