from __future__ import annotations

from evals.c1s4_preplanning_vertical_slice.pr67_required_group_diagnostics import (
    Q3_DISTANCE_GROUP_ID,
    build_pr67_required_group_diagnostics,
    build_q3_prior_distance_probe,
    build_required_group_row,
)
from evals.c1s4_preplanning_vertical_slice.step2_build_question_context_packets import build_summary
from evals.c1s4_preplanning_vertical_slice.expected_context_benchmark import load_expected_context_gold


def _q3_gold_group() -> dict:
    gold = load_expected_context_gold()
    q3 = next(q for q in gold["questions"] if int(q["question_number"]) == 3)
    for mode in ("prior_only", "prior_plus_support_content_only", "prior_plus_support_content_plus_lexical_hints"):
        groups = (q3.get("expectations_by_mode") or {}).get(mode, {}).get("required_context_groups") or []
        group = next(g for g in groups if g.get("group_id") == Q3_DISTANCE_GROUP_ID)
        return group
    raise AssertionError("Q3 distance group not found")


def test_q3_probe_distinguishes_raw_navigation_from_session_evidence() -> None:
    packet = build_summary(mode="prior_plus_support_content_plus_lexical_hints", question_number=3, max_hits=50)["packets"][0]
    probe = build_q3_prior_distance_probe(
        packet=packet,
        query_variant_diagnostics=packet.get("query_variant_diagnostics"),
    )
    lineage = probe.get("lineage") or {}
    raw = lineage.get("first_raw_text_match") or {}
    session = lineage.get("first_session_memory_or_recap_match")

    assert probe.get("schema") == "dmb_pr67_q3_prior_distance_probe_v2"
    assert raw.get("ref")

    if session is not None:
        ref = str(session.get("ref") or "").lower()
        assert "retrieval-keywords" not in ref
        assert "retrieval_keywords" not in ref
        assert session.get("source_kind") in {"session_recap", "session_memory"} or session.get("subject_class") == "session_memory"
        assert session.get("admittable") is True
    else:
        assert probe.get("failure_stage") in {"no_session_evidence", "retrieval", "admission", "render", "grading"}


def test_q3_variant_literal_or_alias_ranks_populated_when_hits_exist() -> None:
    packet = build_summary(mode="prior_plus_support_content_plus_lexical_hints", question_number=3, max_hits=50)["packets"][0]
    variant_diag = packet.get("query_variant_diagnostics") or {}
    has_hits = any((entry.get("hits") or []) for entry in variant_diag.get("variant_hit_counts") or [])
    probe = build_q3_prior_distance_probe(packet=packet, query_variant_diagnostics=variant_diag)
    literal = probe.get("variant_literal_first_match")
    alias = probe.get("variant_route_alias_first_match")
    if has_hits:
        assert literal is not None or alias is not None


def test_required_group_row_admission_reason_matches_admitted_lineage() -> None:
    diagnostics = build_pr67_required_group_diagnostics(max_hits=50)
    for row in diagnostics.get("rows") or []:
        admission = row.get("admission_surface") or {}
        grading = row.get("grading_surface") or {}
        lineage = row.get("lineage") or {}
        admitted_match = lineage.get("first_admitted_match")

        if admission.get("admitted"):
            assert admitted_match is not None
            assert admitted_match.get("admission_reason") == "admitted"
            assert admission.get("admission_rejection_reason") == "admitted"
        if grading.get("lane_aware_accepted"):
            assert grading.get("lane_aware_rejection_reason") is None


def test_q3_distance_row_does_not_classify_navigation_as_lane_accepted() -> None:
    gold = load_expected_context_gold()
    q3 = next(q for q in gold["questions"] if int(q["question_number"]) == 3)
    group = _q3_gold_group()
    packet = build_summary(mode="prior_plus_support_content_plus_lexical_hints", question_number=3, max_hits=50)["packets"][0]
    row = build_required_group_row(
        packet=packet,
        gold_question=q3,
        mode="prior_plus_support_content_plus_lexical_hints",
        group=group,
    )
    lineage = row.get("lineage") or {}
    raw_ref = str((lineage.get("first_raw_match") or {}).get("ref") or "").lower()
    if "retrieval-keywords" in raw_ref or "stone_bridge" in raw_ref:
        assert row.get("miss_root_cause") != "ok"
        assert lineage.get("first_lane_accepted_match") is None or row.get("grading_surface", {}).get("lane_aware_accepted") is False


def test_source_derived_known_gap_rows_report_ok_root_cause() -> None:
    diagnostics = build_pr67_required_group_diagnostics(max_hits=50)
    gap_rows = [
        r
        for r in diagnostics.get("rows") or []
        if r.get("group_id") == "mirathorn_exact_route_gap"
    ]
    assert gap_rows
    for row in gap_rows:
        grading = row.get("grading_surface") or {}
        lineage = row.get("lineage") or {}
        assert grading.get("lane_aware_accepted") is True
        assert row.get("miss_root_cause") == "ok"
        source_gap = lineage.get("first_source_derived_gap_match") or {}
        assert source_gap.get("ref") == "source_gap:mirathorn_exact_route_gap"
        assert source_gap.get("source_kind") == "source_derived_gap"
        assert source_gap.get("rendered_section") == "known_gaps_and_safety_constraints"


def test_pr67_diagnostics_include_q3_distance_rows() -> None:
    diagnostics = build_pr67_required_group_diagnostics(max_hits=50)
    assert diagnostics.get("schema") == "dmb_pr67_required_group_admission_diagnostics_v2"
    q3_rows = [r for r in diagnostics.get("rows") or [] if int(r.get("question_number") or 0) == 3]
    assert q3_rows
    assert any(r.get("group_id") == Q3_DISTANCE_GROUP_ID for r in q3_rows)
    assert diagnostics.get("q3_prior_distance_probe_by_mode")
