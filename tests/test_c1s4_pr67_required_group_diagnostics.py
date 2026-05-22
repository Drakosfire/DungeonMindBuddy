from __future__ import annotations

from evals.c1s4_preplanning_vertical_slice.pr67_required_group_diagnostics import (
    build_pr67_required_group_diagnostics,
    build_q3_prior_distance_probe,
)
from evals.c1s4_preplanning_vertical_slice.step2_build_question_context_packets import build_summary


def test_q3_prior_distance_probe_reports_admission_or_retrieval_stage() -> None:
    packet = build_summary(mode="prior_plus_support_content_plus_lexical_hints", question_number=3, max_hits=50)["packets"][0]
    probe = build_q3_prior_distance_probe(
        packet=packet,
        query_variant_diagnostics=packet.get("query_variant_diagnostics"),
    )
    assert "merged_candidate_first_rank" in probe
    assert probe.get("failure_stage") in {"ok", "retrieval", "admission", "render", "grading"}


def test_pr67_diagnostics_include_q3_distance_rows() -> None:
    diagnostics = build_pr67_required_group_diagnostics(max_hits=50)
    q3_rows = [r for r in diagnostics.get("rows") or [] if int(r.get("question_number") or 0) == 3]
    assert q3_rows
    assert any(r.get("group_id") == "mirathorn_distance_estimate_from_play" for r in q3_rows)
    assert diagnostics.get("q3_prior_distance_probe_by_mode")
