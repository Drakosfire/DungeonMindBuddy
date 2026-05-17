from evals.c1s4_preplanning_vertical_slice.context_renderer import render_context_packet


def _packet(mode="prior_plus_support_content_only"):
    return {
        "question_number": 5,
        "question_id": "q05",
        "question": "What should we do in Hempholm?",
        "retrieval_mode": mode,
        "admission_policy": "budgeted_v1",
        "known_context_gaps": ["Route details uncertain"],
        "admitted_context": [
            {"ref": "prior:stone_bridge", "source_kind": "session_memory", "presentation_lane": "prior_campaign_memory", "snippet": "Stone Bridge events", "candidate_rank": 1, "admitted_rank": 1},
            {"ref": "support:hempholm", "source_kind": "support_knowledge_card", "presentation_lane": "support_knowledge", "snippet": "Hempholm metallic tree", "candidate_rank": 2, "admitted_rank": 2},
        ],
    }


def test_renderer_groups_support_context():
    out = render_context_packet(_packet())
    support = next(s for s in out["sections"] if s["section_id"] == "support_knowledge")
    assert support["title"] == "Support / Adaptation Context"
    assert "support:hempholm" in support["refs"]


def test_renderer_excludes_support_in_prior_only():
    out = render_context_packet(_packet(mode="prior_only"))
    support = next(s for s in out["sections"] if s["section_id"] == "support_knowledge")
    assert support["refs"] == []
    assert "Hempholm metallic tree" not in out["rendered_text"]


def test_renderer_places_known_gaps_near_top():
    out = render_context_packet(_packet())
    text = out["rendered_text"]
    assert text.index("# Known Gaps and Safety Constraints") < text.index("# Support / Adaptation Context")


def test_renderer_preserves_provenance():
    out = render_context_packet(_packet())
    p = out["provenance_map"]["support:hempholm"]
    assert p["candidate_rank"] == 2
    assert p["admitted_rank"] == 2
    assert p["presentation_lane"] == "support_knowledge"


def test_renderer_classifies_realish_session_item_without_kind_or_lane_as_prior():
    packet = {
        "question_number": 1,
        "question_id": "q01",
        "question": "Who are the NPCs?",
        "retrieval_mode": "prior_only",
        "admission_policy": "budgeted_v1",
        "admitted_context": [
            {"unit_id": "u-L0034-01", "snippet": "Ready for some rest...StoneBridge with Pippa..."}
        ],
    }
    out = render_context_packet(packet)
    prior = next(s for s in out["sections"] if s["section_id"] == "prior_campaign_memory")
    assert "u-L0034-01" in prior["refs"]
