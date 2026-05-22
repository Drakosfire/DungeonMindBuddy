from __future__ import annotations

from evals.c1s4_preplanning_vertical_slice.planner_surface_coverage import build_planner_surface_rows
from evals.c1s4_preplanning_vertical_slice.planner_prompt_payload import (
    find_forbidden_prompt_material,
    build_planner_prompt_payload,
)
from evals.c1s4_preplanning_vertical_slice.step2_build_question_context_packets import build_summary


def test_prior_only_support_required_rows_are_policy_correct() -> None:
    rows = build_planner_surface_rows(
        modes=("prior_only",),
        include_evaluator_only=False,
        include_generated_answer=False,
    )
    support_required = [
        r
        for r in rows
        if r.get("support_required") and int(r.get("question_number") or 0) in {4, 10, 11, 13, 20, 22, 25, 28}
    ]

    assert support_required
    assert {r["support_policy_status"] for r in support_required} == {"support_required_policy_suppressed_expected"}
    assert {r["retrieval_sufficiency_class"] for r in support_required} == {"policy_correct"}
    assert {r["next_failure_surface"] for r in support_required} == {"support_required_policy_suppressed_expected"}


def test_family_a_support_modes_find_required_support() -> None:
    rows = build_planner_surface_rows(
        modes=("prior_plus_support_content_only", "prior_plus_support_content_plus_lexical_hints"),
        include_evaluator_only=False,
        include_generated_answer=False,
    )
    family_rows = [r for r in rows if int(r.get("question_number") or 0) in {10, 11, 20}]
    assert len(family_rows) == 6
    for row in family_rows:
        assert row["first_support_candidate_rank"] is not None
        assert row["first_support_admitted_rank"] is not None
        assert row["support_context_rendered"] is True
        assert row["next_failure_surface"] == "ok_or_later_stage"


def test_planner_prompt_payload_remains_clean_with_affordances() -> None:
    summary = build_summary(
        mode="prior_plus_support_content_plus_lexical_hints",
        question_number=10,
        max_hits=50,
    )
    payload = build_planner_prompt_payload(context_packet=summary["packets"][0])
    blob = str(payload)

    assert find_forbidden_prompt_material(payload) == []
    assert "usable_for_questions" not in blob
    assert "expected_retrieval_context" not in blob
    assert "oracle_risk" not in blob
    assert "c1s4_beat_question_targets" not in blob
    assert "Planner affordances:" not in blob
