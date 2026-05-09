"""Location-entity aggregation over co-tagged session-memory records (deterministic)."""

from __future__ import annotations

from src.agent.session_memory_query import (
    QUERY_MODE_LOCATION_ENTITY_LIST,
    QUERY_MODE_LEXICAL_ROUTE_OVERLAP,
    query_session_memory_candidate,
)


def _base_rec(
    *,
    unit_id: str,
    lexical: str,
    routes: list[dict],
    session_number: int = 3,
) -> dict:
    return {
        "schema": "dmb_session_memory_record_v1",
        "campaign_id": "longmont-test",
        "session_number": session_number,
        "source_recap_path": "Longmont Campaign/Campaign 1/Session Recaps/Session 3 - Test.md",
        "unit_id": unit_id,
        "line_start": 1,
        "line_end": 1,
        "text_blake3": "aa" * 32,
        "lexical_plain": lexical,
        "routes": routes,
    }


def test_location_entity_summary_aggregates_cotagged_npcs() -> None:
    loc = "Longmont Campaign/Campaign 1/Locations/stonebridge/"
    records = [
        _base_rec(
            unit_id="u-a",
            lexical="Pippa and Bubbles at the bridge.",
            routes=[
                {"subject_class": "Location", "normalized_route": loc, "proposed": True, "tag_kind": "inline"},
                {
                    "subject_class": "NewHubCandidate",
                    "normalized_route": "Longmont Campaign/Campaign 1/NPCs/pippa/",
                    "proposed": True,
                    "tag_kind": "inline",
                },
            ],
        ),
        _base_rec(
            unit_id="u-b",
            lexical="Grishna comps a round.",
            routes=[
                {"subject_class": "Location", "normalized_route": loc, "proposed": True, "tag_kind": "inline"},
                {
                    "subject_class": "NewHubCandidate",
                    "normalized_route": "Longmont Campaign/Campaign 1/NPCs/grishna/",
                    "proposed": True,
                    "tag_kind": "inline",
                },
            ],
        ),
        _base_rec(
            unit_id="u-c",
            lexical="Kirfan upriver only.",
            routes=[
                {
                    "subject_class": "NewHubCandidate",
                    "normalized_route": "Longmont Campaign/Campaign 1/NPCs/kirfan/",
                    "proposed": True,
                    "tag_kind": "inline",
                },
            ],
        ),
    ]
    res = query_session_memory_candidate(
        records=records,
        query="Give me a list of all NPCs that live in StoneBridge.",
        campaign_id="longmont-test",
        session_min=3,
        session_max=3,
        max_hits=5,
        tokenizer_mode="default",
    )
    assert res.trace.get("query_mode") == QUERY_MODE_LOCATION_ENTITY_LIST
    summ = res.trace.get("location_entity_summary")
    assert isinstance(summ, dict)
    assert summ.get("relation_confidence") == "co_tagged_with_location"
    blob = "\n".join(
        str(e.get("normalized_route", "")).lower() for e in (summ.get("entities") or []) if isinstance(e, dict)
    )
    assert "campaign 1/npcs/pippa" in blob
    assert "campaign 1/npcs/grishna" in blob
    assert "campaign 1/npcs/kirfan" not in blob
    assert summ.get("record_count_for_location") == 2


def test_non_roster_query_keeps_lexical_mode() -> None:
    loc = "Longmont Campaign/Campaign 1/Locations/stonebridge/"
    records = [
        _base_rec(
            unit_id="u-1",
            lexical="Flood at Stonebridge with Pippa.",
            routes=[
                {"subject_class": "Location", "normalized_route": loc, "proposed": True, "tag_kind": "inline"},
                {
                    "subject_class": "NPC",
                    "normalized_route": "Longmont Campaign/Campaign 1/NPCs/pippa/",
                    "proposed": False,
                    "tag_kind": "inline",
                },
            ],
        ),
    ]
    res = query_session_memory_candidate(
        records=records,
        query="What happened at Stonebridge with Pippa?",
        campaign_id="longmont-test",
        session_min=3,
        session_max=3,
        max_hits=5,
    )
    assert res.trace.get("query_mode") == QUERY_MODE_LEXICAL_ROUTE_OVERLAP
    assert "location_entity_summary" not in res.trace
