from evals.c1s4_preplanning_vertical_slice.context_quality_metrics import compute_packet_quality_metrics
from evals.c1s4_preplanning_vertical_slice.context_renderer import render_context_packet


def _base_row():
    admitted = [
        {"unit_id": "a1", "source_kind": "session_memory", "presentation_lane": "unknown", "snippet": "normal memory"},
        {"unit_id": "s1", "source_kind": "support_knowledge_card", "presentation_lane": "support_knowledge", "snippet": "support fact"},
    ]
    return {
        "question_number": 1,
        "question_id": "q01",
        "question": "q",
        "retrieval_mode": "prior_plus_support_content_only",
        "required_context_groups": 1,
        "required_context_groups_hit": 1,
        "matched_groups": [{"matched_context_refs": ["s1"]}],
        "known_context_gaps": ["unknown route"],
        "expected_known_context_gaps_eval_only": ["unknown route"],
        "retrieved_context": admitted + [{"unit_id": "r3", "source_kind": "session_memory"}],
        "candidate_context": admitted,
        "admitted_context": admitted,
    }


def test_metrics_surface_counts_and_schema():
    row = _base_row()
    rendered = render_context_packet(row)
    m = compute_packet_quality_metrics(row=row, rendered_context_packet=rendered)
    assert m["schema"] == "dmb_packet_quality_metrics_v1"
    assert m["context_surfaces"]["retrieved_context_count"] == 3
    assert m["context_surfaces"]["candidate_context_count"] == 2
    assert m["context_surfaces"]["admitted_context_count"] == 2


def test_metrics_flags_support_burial_unknown_lane_and_prior_leakage():
    admitted = [{"unit_id": f"m{i}", "source_kind": "session_memory", "presentation_lane": "unknown", "snippet": "x"} for i in range(21)]
    admitted.append({"unit_id": "support-deep", "source_kind": "support_knowledge_card", "presentation_lane": "unknown", "snippet": "support"})
    row = _base_row()
    row.update({"retrieval_mode": "prior_only", "admitted_context": admitted, "candidate_context": admitted, "retrieved_context": admitted})
    m = compute_packet_quality_metrics(row=row, rendered_context_packet=render_context_packet(row))
    assert "support_buried_after_rank_20" in m["flags"]
    assert "prior_only_support_leakage" in m["flags"]
    assert "high_unknown_lane_ratio" in m["flags"]


def test_metrics_detect_hygiene_risks_and_known_gap_position():
    row = _base_row()
    row["admitted_context"] = [
        {"unit_id": "n1", "source_kind": "session_memory", "presentation_lane": "unknown", "snippet": "Retrieval keywords: foo", "source_reference": "evals/c1s4_preplanning_vertical_slice/artifacts/pr53/report.json"},
        {"unit_id": "n2", "source_kind": "session_memory", "presentation_lane": "location_context", "snippet": "location_hub npc anchors"},
    ]
    row["candidate_context"] = row["admitted_context"]
    row["retrieved_context"] = row["admitted_context"]
    rendered = {"sections": [{"section_id": "support_knowledge", "estimated_tokens": 20, "chars": 80, "refs": ["n1"]}], "provenance_map": {}}
    m = compute_packet_quality_metrics(row=row, rendered_context_packet=rendered)
    assert m["hygiene"]["eval_or_plan_source_leakage"] is True
    assert m["hygiene"]["navigation_only_evidence_count"] >= 1
    assert m["hygiene"]["location_hub_npc_continuity_risk_count"] >= 1
    assert "known_gaps_not_near_top" in m["flags"]


def test_support_burial_depth_is_items_before_first_support():
    row = _base_row()
    row["admitted_context"] = [
        {"unit_id": "m1", "source_kind": "session_memory", "presentation_lane": "prior_campaign_memory", "snippet": "a"},
        {"unit_id": "m2", "source_kind": "session_memory", "presentation_lane": "prior_campaign_memory", "snippet": "b"},
        {"unit_id": "s1", "source_kind": "support_knowledge_card", "presentation_lane": "support_knowledge", "snippet": "support"},
    ]
    row["candidate_context"] = row["admitted_context"]
    row["retrieved_context"] = row["admitted_context"]
    m = compute_packet_quality_metrics(row=row, rendered_context_packet=render_context_packet(row))
    assert m["support"]["first_support_admitted_rank"] == 3
    assert m["support"]["support_burial_depth"] == 2
