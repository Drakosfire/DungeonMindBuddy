from __future__ import annotations

from evals.c1s4_preplanning_vertical_slice.campaign_corpus_materializer import (
    C1S4_CAMPAIGN_CORPUS_TARGET_RELPATHS,
    load_campaign_corpus_records_for_c1s4,
)
from evals.c1s4_preplanning_vertical_slice.context_classification import is_allowed_retrieval_corpus_path
from src.agent.session_memory_query import query_session_memory_candidate


def _paths(records: list[dict]) -> set[str]:
    return {str(r.get("source_path") or "") for r in records}


def _by_path(records: list[dict], needle: str) -> list[dict]:
    return [r for r in records if needle in str(r.get("source_path") or "")]


def test_materializer_emits_target_family_records() -> None:
    records = load_campaign_corpus_records_for_c1s4()
    assert records
    paths = _paths(records)
    for relpath in C1S4_CAMPAIGN_CORPUS_TARGET_RELPATHS:
        assert f"corpus/eldyrwild-markdown/{relpath}" in paths


def test_npc_records_have_npc_metadata() -> None:
    records = load_campaign_corpus_records_for_c1s4()
    pippa = _by_path(records, "NPCs/pippa/")
    assert pippa
    assert all(r.get("subject_class") == "npc" for r in pippa)
    assert all(r.get("source_kind") in {"npc_hub", "npc_dossier"} for r in pippa)
    evidence = [r for r in pippa if r.get("evidence_role") == "evidence"]
    assert evidence
    assert any(r.get("planner_lane_hint") == "character_party_behavior" for r in evidence)


def test_location_records_have_location_metadata() -> None:
    records = load_campaign_corpus_records_for_c1s4()
    stone = _by_path(records, "Locations/stone_bridge/README.md")
    assert stone
    assert all(r.get("source_kind") == "location_hub" for r in stone)
    assert all(r.get("subject_class") == "location" for r in stone)
    assert any(r.get("planner_lane_hint") == "location_worldbuilding" for r in stone)


def test_navigation_and_alias_sections_marked_non_evidence() -> None:
    records = load_campaign_corpus_records_for_c1s4()
    stone = _by_path(records, "Locations/stone_bridge/README.md")
    nav = [r for r in stone if "npc" in str(r.get("section_heading") or "").lower() and "anchor" in str(r.get("section_heading") or "").lower()]
    assert nav
    assert all(r.get("evidence_role") == "navigation_only" for r in nav)
    alias = [r for r in stone if str(r.get("section_heading") or "").lower() == "retrieval keywords"]
    assert alias
    assert alias[0].get("evidence_role") == "alias"


def test_no_denied_paths_materialized() -> None:
    records = load_campaign_corpus_records_for_c1s4()
    for record in records:
        path = str(record.get("source_path") or "")
        assert is_allowed_retrieval_corpus_path(path)
        assert "evals/" not in path.lower()
        assert "session 4" not in path.lower()


def test_materializer_skips_empty_title_only_h1_sections() -> None:
    records = load_campaign_corpus_records_for_c1s4()
    stone = _by_path(records, "Locations/stone_bridge/README.md")
    title_only = [r for r in stone if str(r.get("section_heading") or "").startswith("Stone Bridge — Campaign 1")]
    assert not title_only


def test_materialized_records_are_queryable() -> None:
    records = load_campaign_corpus_records_for_c1s4()
    pippa_hits = query_session_memory_candidate(
        records=records,
        query="Pippa Goldwhistle",
        campaign_id="longmont-c1",
        session_min=0,
        session_max=3,
        max_hits=10,
    ).hits
    assert any("NPCs/pippa/" in str(h.get("source_recap_path") or "") for h in pippa_hits)

    recap_hits = query_session_memory_candidate(
        records=records,
        query="Mirathorn week on foot",
        campaign_id="longmont-c1",
        session_min=0,
        session_max=3,
        max_hits=10,
    ).hits
    assert any("Session 3 - The Stone Bridge Flood.md" in str(h.get("source_recap_path") or "") for h in recap_hits)
