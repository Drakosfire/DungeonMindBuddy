from __future__ import annotations

from evals.c1s4_preplanning_vertical_slice.context_admission import build_lane_budgeted_admission
from evals.c1s4_preplanning_vertical_slice.query_lane_router import build_lane_plan
from evals.c1s4_preplanning_vertical_slice.step2_build_question_context_packets import build_summary


def test_q3_packet_has_admission_decision_diagnostics_all_modes() -> None:
    for mode in (
        "prior_only",
        "prior_plus_support_content_only",
        "prior_plus_support_content_plus_lexical_hints",
    ):
        packet = build_summary(mode=mode, question_number=3, max_hits=50)["packets"][0]
        assert packet.get("candidate_context")
        assert packet.get("admitted_context") is not None
        diag = packet.get("admission_decision_diagnostics") or {}
        assert diag.get("schema") == "dmb_admission_decision_diagnostics_v1"
        attempts = diag.get("attempts") or []
        assert len(attempts) == len(packet.get("candidate_context") or [])
        for attempt in attempts:
            assert attempt.get("reason") not in {None, "", "not_evaluated"}


def test_lane_budgeted_admission_records_skip_reasons() -> None:
    lane_plan = build_lane_plan(
        question_text="How far is Mirathorn?",
        retrieval_mode="prior_only",
        candidate_depth=5,
        total_budget_chars=8000,
    )
    candidates = [
        {"unit_id": f"c{i}", "source_kind": "session_memory", "snippet": "mirathorn week travel", "title": "t"}
        for i in range(1, 6)
    ]
    result = build_lane_budgeted_admission(
        question_text="How far is Mirathorn?",
        retrieval_mode="prior_only",
        candidates=candidates,
        lane_plan=lane_plan,
        candidate_depth=5,
        total_budget_chars=8000,
    )
    attempts = (result.get("admission_decision_diagnostics") or {}).get("attempts") or []
    assert len(attempts) == 5
    assert any(a.get("admitted") for a in attempts)
