from evals.c1s4_preplanning_vertical_slice.context_renderer import provenance_matches_expected, render_context_packet
from evals.c1s4_preplanning_vertical_slice.step2_build_question_context_packets import build_summary


def _packet(mode="prior_plus_support_content_only"):
    return {
        "question_number": 5,
        "question_id": "q05",
        "question": "What should we do in Hempholm?",
        "retrieval_mode": mode,
        "admission_policy": "budgeted_v1",
        "source_derived_context_gaps": [
            {
                "gap_id": "source_gap:test:0",
                "gap": "Route details uncertain",
                "source": "deterministic_absence_analysis",
                "evidence_scope": "allowed_prior_context",
                "presentation_lane": "known_gap",
                "source_kind": "source_derived_gap",
            }
        ],
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


def test_renderer_provenance_includes_rendered_section_id_for_fallback_item():
    packet = {
        "question_number": 1,
        "question_id": "q01",
        "question": "Who are the NPCs?",
        "retrieval_mode": "prior_only",
        "admission_policy": "budgeted_v1",
        "admitted_context": [
            {"unit_id": "u-L0034-01", "snippet": "Ready for some rest...StoneBridge with Pippa...", "presentation_lane": "unknown"}
        ],
    }
    out = render_context_packet(packet)
    prov = out["provenance_map"]["u-L0034-01"]
    assert prov["presentation_lane"] == "unknown"
    assert prov["rendered_section_id"] == "prior_campaign_memory"


def test_renderer_routes_party_timeline_to_character_party_behavior() -> None:
    packet = {
        "question_number": 1,
        "question_id": "test",
        "question": "Who are the NPCs?",
        "retrieval_mode": "prior_only",
        "admission_policy": "lane_budgeted_v1",
        "admission_budget": {"candidate_depth": 50},
        "known_context_gaps": [],
        "admitted_context": [
            {
                "unit_id": "corpus:npc:grishna:summary",
                "source_path": "corpus/eldyrwild-markdown/Longmont Campaign/Campaign 1/NPCs/grishna/grishna_character_dossier.md",
                "source_kind": "npc_dossier",
                "source_layer": "campaign_corpus",
                "subject_class": "npc",
                "presentation_lane": "party_timeline",
                "admission_budget_lane": "prior_campaign_memory",
                "admission_reason": "preserved_character_party_behavior_npc_grishna",
                "snippet": "Grishna runs the River's Edge Pub.",
            }
        ],
    }

    rendered = render_context_packet(packet)
    prov = rendered["provenance_map"]["corpus:npc:grishna:summary"]

    assert prov["rendered_section_id"] == "character_party_behavior"
    assert str(prov["source_path"]).endswith("/NPCs/grishna/grishna_character_dossier.md")
    assert prov["route_reason"] == "presentation_lane_party_timeline"


def test_renderer_routes_location_context_to_location_worldbuilding() -> None:
    packet = {
        "question_number": 3,
        "question_id": "test",
        "question": "How far is Stone Bridge?",
        "retrieval_mode": "prior_only",
        "admission_policy": "lane_budgeted_v1",
        "admitted_context": [
            {
                "unit_id": "corpus:location:stone_bridge:summary",
                "source_path": "corpus/eldyrwild-markdown/Longmont Campaign/Campaign 1/Locations/stone_bridge/README.md",
                "source_kind": "location_hub",
                "presentation_lane": "location_context",
                "snippet": "Stone Bridge hub",
            }
        ],
    }
    rendered = render_context_packet(packet)
    prov = rendered["provenance_map"]["corpus:location:stone_bridge:summary"]
    assert prov["rendered_section_id"] == "location_worldbuilding"


def test_renderer_preserves_source_path_in_provenance_map() -> None:
    out = render_context_packet(_packet())
    prov = out["provenance_map"]["prior:stone_bridge"]
    assert prov.get("source_path") is None or isinstance(prov.get("source_path"), str)
    packet = _packet()
    packet["admitted_context"][0]["source_path"] = "corpus/example/session_recap.md"
    out2 = render_context_packet(packet)
    assert out2["provenance_map"]["prior:stone_bridge"]["source_path"] == "corpus/example/session_recap.md"


def test_renderer_preserves_source_reference_in_provenance_map() -> None:
    packet = _packet()
    packet["admitted_context"][1]["source_reference"] = {"card_id": "hempholm_tree"}
    out = render_context_packet(packet)
    assert out["provenance_map"]["support:hempholm"]["source_reference"] == {"card_id": "hempholm_tree"}


def test_renderer_uses_presentation_lane_before_session_memory_fallback() -> None:
    packet = {
        "question_number": 1,
        "question_id": "q01",
        "question": "Who are the NPCs?",
        "retrieval_mode": "prior_only",
        "admission_policy": "lane_budgeted_v1",
        "admitted_context": [
            {
                "unit_id": "u-test",
                "source_kind": "session_memory",
                "presentation_lane": "party_timeline",
                "snippet": "A character-relevant memory.",
            }
        ],
    }

    rendered = render_context_packet(packet)
    assert rendered["provenance_map"]["u-test"]["rendered_section_id"] == "character_party_behavior"


def test_renderer_includes_render_diagnostics() -> None:
    out = render_context_packet(_packet())
    diag = out.get("render_diagnostics") or {}
    assert diag.get("schema") == "dmb_context_render_diagnostics_v1"
    assert isinstance(diag.get("section_route_counts"), dict)
    assert isinstance(diag.get("items"), list)


def test_provenance_matches_expected_uses_source_path() -> None:
    prov = {
        "source_path": "corpus/eldyrwild-markdown/Longmont Campaign/Campaign 1/NPCs/grishna/README.md",
        "unit_id": "corpus:npc:grishna:package-notes",
    }
    assert provenance_matches_expected(prov, "NPCs/grishna/README.md")


def test_q1_character_rows_render_in_character_party_behavior_after_pr62() -> None:
    summary = build_summary(mode="prior_only", question_number=1, max_hits=50)
    packet = summary["packets"][0]
    rendered = render_context_packet(packet)
    character = next(s for s in rendered["sections"] if s["section_id"] == "character_party_behavior")
    refs = " ".join(character["refs"]).lower()
    assert "grishna" in refs
    assert "pippa" in refs
    assert "bubbles" in refs


def test_q1_grishna_rendered_section_hit_after_pr62() -> None:
    summary = build_summary(mode="prior_only", question_number=1, max_hits=50)
    packet = summary["packets"][0]
    rendered = render_context_packet(packet)
    prov = rendered["provenance_map"].get("corpus:npc:grishna:summary")
    assert prov is not None
    assert prov["rendered_section_id"] == "character_party_behavior"
    assert provenance_matches_expected(prov, "NPCs/grishna/grishna_character_dossier.md")


def test_q5_support_still_renders_in_support_section() -> None:
    summary = build_summary(mode="prior_plus_support_content_only", question_number=5, max_hits=50)
    packet = summary["packets"][0]
    rendered = render_context_packet(packet)
    support = next(s for s in rendered["sections"] if s["section_id"] == "support_knowledge")
    assert any("hempholm" in ref.lower() for ref in support["refs"])


def test_q5_prior_only_still_suppresses_support_section_items() -> None:
    summary = build_summary(mode="prior_only", question_number=5, max_hits=50)
    packet = summary["packets"][0]
    rendered = render_context_packet(packet)
    support = next(s for s in rendered["sections"] if s["section_id"] == "support_knowledge")
    assert support["refs"] == []


def test_q3_location_rows_still_render_in_location_worldbuilding() -> None:
    summary = build_summary(mode="prior_only", question_number=3, max_hits=50)
    packet = summary["packets"][0]
    rendered = render_context_packet(packet)
    location = next(s for s in rendered["sections"] if s["section_id"] == "location_worldbuilding")
    refs = " ".join(location["refs"]).lower()
    assert "stone" in refs or "mirathorn" in refs or location["refs"]


def test_planner_packet_does_not_leak_gold_known_gaps_into_rendered_text() -> None:
    summary = build_summary(mode="prior_only", question_number=3, max_hits=50)
    packet = summary["packets"][0]
    assert "known_context_gaps" not in packet
    rendered = render_context_packet(packet)
    text = rendered["rendered_text"]
    assert "exact Stone Bridge-to-Mirathorn route gazetteer" not in text
    assert "intermediate settlements" not in text
    assert "day-by-day travel route" not in text
    assert "route-specific ecology" not in text


def test_q3_renderer_can_show_source_derived_gap_only() -> None:
    packet = {
        "question_number": 3,
        "question_id": "q03",
        "question": "How far away is Mirathorn?",
        "retrieval_mode": "prior_only",
        "admission_policy": "lane_budgeted_v1",
        "admitted_context": [
            {
                "unit_id": "u-session-travel",
                "source_kind": "session_memory",
                "presentation_lane": "prior_campaign_memory",
                "snippet": "Party traveled toward Mirathorn after Stone Bridge.",
            }
        ],
        "source_derived_context_gaps": [
            {
                "schema": "dmb_source_derived_context_gap_v1",
                "gap_id": "source_gap:mirathorn_exact_route_gap",
                "gap": "Retrieved prior context supports Stone Bridge and Mirathorn but does not establish the exact route.",
                "source": "deterministic_absence_analysis",
                "evidence_scope": "allowed_prior_context",
                "presentation_lane": "known_gap",
                "source_kind": "source_derived_gap",
                "subject_class": "route_gap",
            }
        ],
    }
    rendered = render_context_packet(packet)
    gaps = next(s for s in rendered["sections"] if s["section_id"] == "known_gaps_and_safety_constraints")
    assert "does not establish" in gaps["text"]
    assert "route gazetteer" not in rendered["rendered_text"].lower()
    prov = rendered["provenance_map"]["source_gap:mirathorn_exact_route_gap"]
    assert prov["rendered_section_id"] == "known_gaps_and_safety_constraints"
    assert prov["route_reason"] == "source_derived_context_gap"


def test_q3_rendered_text_contains_source_derived_gap() -> None:
    summary = build_summary(mode="prior_only", question_number=3, max_hits=50)
    packet = summary["packets"][0]
    rendered = render_context_packet(packet)
    assert "source_gap:mirathorn_exact_route_gap" in rendered["rendered_text"]
    assert "does not establish" in rendered["rendered_text"].lower()


def test_q3_rendered_text_does_not_contain_gold_gap_phrases() -> None:
    summary = build_summary(mode="prior_only", question_number=3, max_hits=50)
    rendered = render_context_packet(summary["packets"][0])
    text = rendered["rendered_text"]
    assert "exact Stone Bridge-to-Mirathorn route gazetteer" not in text
    assert "intermediate settlements" not in text
    assert "day-by-day travel route" not in text
    assert "route-specific ecology" not in text
