from __future__ import annotations

from evals.c1s4_preplanning_vertical_slice.campaign_corpus_materializer import load_campaign_corpus_records_for_c1s4
from evals.c1s4_preplanning_vertical_slice.step2_build_question_context_packets import build_summary
from evals.c1s4_preplanning_vertical_slice.visibility_provenance import infer_c1s4_visibility, is_planner_visible_for_c1s4_preplanning


def test_hempholm_location_hub_not_planner_visible_for_c1s4() -> None:
    sample = {
        "source_path": "corpus/eldyrwild-markdown/Longmont Campaign/Campaign 1/Locations/hempholm/README.md",
        "source_kind": "location_hub",
        "title": "Hempholm",
    }
    visibility = infer_c1s4_visibility(sample)
    assert visibility.get("planner_visible") is False
    assert not is_planner_visible_for_c1s4_preplanning(sample)


def test_hempholm_hub_not_in_c1s4_materialized_corpus() -> None:
    records = load_campaign_corpus_records_for_c1s4()
    paths = {str(r.get("source_path") or r.get("source_recap_path") or "").lower() for r in records}
    assert not any("/locations/hempholm/readme.md" in p for p in paths)


def test_q5_support_still_renders_in_support_mode() -> None:
    packet = build_summary(mode="prior_plus_support_content_plus_lexical_hints", question_number=5, max_hits=50)["packets"][0]
    rendered = packet.get("rendered_context_packet") or {}
    text = str(rendered.get("rendered_text") or "").lower()
    assert "support" in text or any(
        str(item.get("source_kind") or "") == "support_knowledge_card"
        for item in (packet.get("admitted_context") or [])
    )
