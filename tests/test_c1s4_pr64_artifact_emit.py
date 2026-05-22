from pathlib import Path

from evals.c1s4_preplanning_vertical_slice.pr64_artifact_emit import write_pr64_artifacts


def test_pr64_summary_reports_clean_prompt_boundary(tmp_path: Path) -> None:
    summary = write_pr64_artifacts(output_dir=tmp_path / "pr64")
    assert (tmp_path / "pr64" / "pr64_prompt_payload_boundary_matrix.csv").exists()
    assert (tmp_path / "pr64" / "pr64_prompt_payload_examples.json").exists()
    assert summary["schema"] == "dmb_pr64_prompt_control_split_summary_v1"
    assert summary["planner_prompt_payloads_built"] == 9
    assert summary["planner_prompt_payloads_valid"] == 9
    assert summary["forbidden_prompt_key_hits"] == 0
    assert summary["forbidden_prompt_value_hits"] == 0
    assert summary["generated_answer_expected_behavior_leaks"] == 0
    assert summary["generated_answer_authority_label_leaks"] == 0
    assert summary["generated_answer_oracle_risk_leaks"] == 0
