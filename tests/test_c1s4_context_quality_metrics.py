from evals.c1s4_preplanning_vertical_slice.context_quality_metrics import compute_packet_quality_metrics


def _row():
    return {
        "retrieval_mode": "prior_plus_support_content_only",
        "retrieved_context": [{"unit_id": "r1"}] * 9,
        "candidate_context": ([{"unit_id": f"c{i}", "source_kind": "session_memory"} for i in range(1, 27)] + [{"unit_id": "support:1", "source_kind": "support_knowledge_card"}] + [{"unit_id": f"c{i}", "source_kind": "session_memory"} for i in range(28, 51)]),
        "admitted_context": ([{"unit_id": f"u{i}", "source_kind": "session_memory"} for i in range(1, 40)] + [{"unit_id": f"s{i}", "source_kind": "support_knowledge_card", "presentation_lane": "support_knowledge"} for i in range(1, 6)]),
        "rendered_context_packet": {"sections": [{"section": "Known Gaps and Safety Constraints"}, {"section": "Support Knowledge"}]},
        "required_context_groups": 1,
        "required_context_groups_hit": 1,
        "forbidden_context_groups_hit": [],
        "known_gap_expectations_hit": ["gap"],
        "matched_groups": [{"ok": True, "matched_context_refs": ["s1"]}],
    }


def test_metrics_distinguish_context_surfaces():
    m = compute_packet_quality_metrics(row=_row(), gold_question=None)
    assert m["context_surfaces"]["retrieved_context_count"] == 9
    assert m["context_surfaces"]["candidate_context_count"] == 50
    assert m["context_surfaces"]["admitted_context_count"] == 44


def test_metrics_detect_support_burial_and_unknown_ratio():
    m = compute_packet_quality_metrics(row=_row(), gold_question=None)
    assert m["support"]["first_support_admitted_rank"] == 40
    assert m["support"]["support_burial_depth"] == 39
    assert "support_buried_after_rank_20" in m["flags"]
    assert round(m["presentation_lanes"]["unknown_lane_ratio"], 2) == 0.89
    assert "high_unknown_lane_ratio" in m["flags"]


def test_metrics_detect_prior_only_support_leakage():
    row = _row()
    row["retrieval_mode"] = "prior_only"
    m = compute_packet_quality_metrics(row=row, gold_question=None)
    assert "prior_only_support_leakage" in m["flags"]
