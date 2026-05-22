from __future__ import annotations

from evals.c1s4_preplanning_vertical_slice.planner_surface_coverage import (
    RETRIEVAL_MODES,
    TIER_A_QUESTIONS,
    build_planner_surface_rows,
    summarize_planner_surface_rows,
)


def test_planner_surface_counts_37_questions_111_rows() -> None:
    rows = build_planner_surface_rows()
    planner_rows = [r for r in rows if r["planner_facing"]]
    assert len(planner_rows) == 111
    assert {r["question_number"] for r in planner_rows} == set(range(1, 39)) - {35}


def test_q35_is_evaluator_only_and_skipped_from_planner_surface() -> None:
    rows = build_planner_surface_rows(include_evaluator_only=True)
    q35 = [r for r in rows if r["question_number"] == 35]
    assert len(q35) == len(RETRIEVAL_MODES)
    assert all(r["planner_facing"] is False for r in q35)
    assert all(r["next_failure_surface"] == "evaluator_only_not_planner_facing" for r in q35)


def test_all_planner_surface_rows_build_valid_prompt_payloads() -> None:
    rows = build_planner_surface_rows()
    planner_rows = [r for r in rows if r["planner_facing"]]
    assert planner_rows
    assert all(r["prompt_payload_valid"] is True for r in planner_rows)


def test_planner_surface_rows_have_no_forbidden_prompt_material() -> None:
    rows = build_planner_surface_rows()
    planner_rows = [r for r in rows if r["planner_facing"]]
    assert all(int(r["forbidden_prompt_key_hits"]) == 0 for r in planner_rows)
    assert all(int(r["forbidden_prompt_value_hits"]) == 0 for r in planner_rows)


def test_planner_surface_rows_have_no_known_context_gap_leakage() -> None:
    rows = build_planner_surface_rows()
    planner_rows = [r for r in rows if r["planner_facing"]]
    assert all(r["known_context_gaps_leaked"] is False for r in planner_rows)


def test_planner_surface_rows_have_no_must_not_terms_in_prompt_payload() -> None:
    rows = build_planner_surface_rows()
    planner_rows = [r for r in rows if r["planner_facing"]]
    assert all(not r["must_not_include_terms_in_prompt_payload"] for r in planner_rows)


def test_prior_only_rows_do_not_render_support_section_items() -> None:
    rows = build_planner_surface_rows()
    prior_rows = [r for r in rows if r["planner_facing"] and r["mode"] == "prior_only"]
    assert all(r["support_context_rendered"] is False for r in prior_rows)


def test_planner_surface_rows_have_no_generated_answer_control_leaks() -> None:
    rows = build_planner_surface_rows()
    planner_rows = [r for r in rows if r["planner_facing"]]
    assert all(r["generated_answer_control_leak"] is False for r in planner_rows)


def test_tier_a_q1_q3_q5_green_after_pr67() -> None:
    rows = build_planner_surface_rows()
    tier_a = [r for r in rows if r["question_number"] in TIER_A_QUESTIONS]
    assert len(tier_a) == 9
    assert all(r["next_failure_surface"] == "ok_or_later_stage" for r in tier_a)


def test_summarize_planner_surface_rows_reports_expected_schema() -> None:
    summary = summarize_planner_surface_rows(build_planner_surface_rows(include_evaluator_only=True))
    assert summary["schema"] == "dmb_pr65_planner_surface_summary_v1"
    assert summary["planner_facing_questions"] == 37
    assert summary["planner_surface_rows"] == 111
    assert summary["evaluator_only_questions"] == 1
    assert summary["hard_boundary_failures"]["forbidden_prompt_key_hits"] == 0
    assert "coverage_by_class" in summary
    assert summary["tier_a_ok_rows"] == 9
