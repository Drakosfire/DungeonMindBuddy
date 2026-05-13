"""Session-memory query index (candidate mode) — deterministic, no API."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from src.agent.corpus_path_tools import unit_ids_from_query_session_memory_trace
from src.agent.planner import make_tool_dispatcher
from src.agent.session_memory_query import (
    query_session_memory_candidate,
    load_session_memory_records_jsonl,
)


def _minimal_records() -> list[dict]:
    return [
        {
            "schema": "dmb_session_memory_record_v1",
            "campaign_id": "longmont-c2",
            "session_number": 20,
            "source_recap_path": "Longmont Campaign/Campaign 2/Session Recaps/Session 20 - Recap.md",
            "unit_id": "u-L0100-01",
            "line_start": 100,
            "line_end": 100,
            "text_blake3": "aa" * 32,
            "lexical_plain": "Captain Lysandra hears voices near the tower forest.",
            "routes": [
                {
                    "subject_class": "NPC",
                    "normalized_route": "Longmont Campaign/Campaign 2/NPCs/captain_lysandra_ironveil/",
                    "proposed": False,
                    "tag_kind": "inline",
                }
            ],
        },
        {
            "schema": "dmb_session_memory_record_v1",
            "campaign_id": "longmont-c2",
            "session_number": 20,
            "source_recap_path": "Longmont Campaign/Campaign 2/Session Recaps/Session 20 - Recap.md",
            "unit_id": "u-L0200-01",
            "line_start": 200,
            "line_end": 200,
            "text_blake3": "bb" * 32,
            "lexical_plain": "Unrelated mossford sheriff patrol beats.",
            "routes": [],
        },
    ]


def test_query_session_memory_candidate_ranking() -> None:
    res = query_session_memory_candidate(
        records=_minimal_records(),
        query="Lysandra voices tower",
        campaign_id="longmont-c2",
        session_min=20,
        session_max=20,
        max_hits=5,
    )
    assert res.hits
    assert res.hits[0]["unit_id"] == "u-L0100-01"
    assert any("captain_lysandra_ironveil" in str(r.get("normalized_route", "")) for r in res.hits[0]["routes"])
    assert res.trace["trace_schema"] == "dmb_query_session_memory_trace_v1"
    assert "expand_context" not in res.trace


def _three_unit_adjacency_records() -> list[dict]:
    recap = "Longmont Campaign/Campaign 2/Session Recaps/Session 20 - Recap.md"
    route = "Longmont Campaign/Campaign 2/NPCs/captain_lysandra_ironveil/"
    base = {
        "schema": "dmb_session_memory_record_v1",
        "campaign_id": "longmont-c2",
        "session_number": 20,
        "source_recap_path": recap,
        "text_blake3": "cc" * 32,
        "routes": [{"subject_class": "NPC", "normalized_route": route, "proposed": False, "tag_kind": "inline"}],
    }
    return [
        {**base, "unit_id": "u-adj-01", "line_start": 10, "line_end": 10, "lexical_plain": "noise alpha"},
        {**base, "unit_id": "u-adj-02", "line_start": 11, "line_end": 11, "lexical_plain": "target beta match"},
        {**base, "unit_id": "u-adj-03", "line_start": 12, "line_end": 12, "lexical_plain": "noise gamma"},
    ]


def test_expand_adjacent_pulls_lexically_adjacent_unit() -> None:
    res = query_session_memory_candidate(
        records=_three_unit_adjacency_records(),
        query="beta match",
        campaign_id="longmont-c2",
        session_min=20,
        session_max=20,
        max_hits=3,
        expand_context=True,
        expand_seed_hits=1,
        expand_adjacent_window=1,
        expand_shared_route_limit=0,
        expand_route_family_limit=0,
    )
    uids = [str(h["unit_id"]) for h in res.hits]
    assert uids[0] == "u-adj-02"
    assert "u-adj-01" in uids and "u-adj-03" in uids
    assert any(any(str(w).startswith("expanded_adjacent:") for w in (h.get("why_matched") or [])) for h in res.hits)


def test_expand_shared_route_pulls_same_route_record() -> None:
    recap = "Longmont Campaign/Campaign 2/Session Recaps/Session 20 - Recap.md"
    route = "Longmont Campaign/Campaign 2/NPCs/shared_npc/"
    rinfo = {"subject_class": "NPC", "normalized_route": route, "proposed": False, "tag_kind": "inline"}
    records = [
        {
            "schema": "dmb_session_memory_record_v1",
            "campaign_id": "longmont-c2",
            "session_number": 20,
            "source_recap_path": recap,
            "unit_id": "u-sr-a",
            "line_start": 1,
            "line_end": 1,
            "text_blake3": "dd" * 32,
            "lexical_plain": "uniquekeyword alpha slice",
            "routes": [rinfo],
        },
        {
            "schema": "dmb_session_memory_record_v1",
            "campaign_id": "longmont-c2",
            "session_number": 20,
            "source_recap_path": recap,
            "unit_id": "u-sr-b",
            "line_start": 99,
            "line_end": 99,
            "text_blake3": "ee" * 32,
            "lexical_plain": "unrelated prose without query tokens",
            "routes": [rinfo],
        },
    ]
    res = query_session_memory_candidate(
        records=records,
        query="uniquekeyword alpha",
        campaign_id="longmont-c2",
        session_min=20,
        session_max=20,
        max_hits=2,
        expand_context=True,
        expand_seed_hits=1,
        expand_adjacent_window=0,
        expand_shared_route_limit=3,
        expand_route_family_limit=0,
    )
    uids = [str(h["unit_id"]) for h in res.hits]
    assert uids[0] == "u-sr-a"
    assert "u-sr-b" in uids
    assert any(
        any(str(w).startswith("expanded_shared_route:") for w in (h.get("why_matched") or [])) for h in res.hits
    )


def test_expand_route_family_prefix_pulls_child_route_record() -> None:
    recap = "Longmont Campaign/Campaign 2/Session Recaps/Session 20 - Recap.md"
    parent = "Longmont Campaign/Campaign 2/Locations/site_q7/"
    child = "Longmont Campaign/Campaign 2/Locations/site_q7/sub_k2/"
    records = [
        {
            "schema": "dmb_session_memory_record_v1",
            "campaign_id": "longmont-c2",
            "session_number": 20,
            "source_recap_path": recap,
            "unit_id": "u-fam-seed",
            "line_start": 1,
            "line_end": 1,
            "text_blake3": "ff" * 32,
            "lexical_plain": "seedtoken unusualword hub",
            "routes": [{"subject_class": "Location", "normalized_route": parent, "proposed": False, "tag_kind": "inline"}],
        },
        {
            "schema": "dmb_session_memory_record_v1",
            "campaign_id": "longmont-c2",
            "session_number": 20,
            "source_recap_path": recap,
            "unit_id": "u-fam-child",
            "line_start": 50,
            "line_end": 50,
            "text_blake3": "00" * 32,
            "lexical_plain": "no lexical overlap with the query keywords",
            "routes": [{"subject_class": "Location", "normalized_route": child, "proposed": False, "tag_kind": "inline"}],
        },
    ]
    res = query_session_memory_candidate(
        records=records,
        query="seedtoken unusualword",
        campaign_id="longmont-c2",
        session_min=20,
        session_max=20,
        max_hits=2,
        expand_context=True,
        expand_seed_hits=1,
        expand_adjacent_window=0,
        expand_shared_route_limit=0,
        expand_route_family_limit=3,
    )
    uids = [str(h["unit_id"]) for h in res.hits]
    assert uids[0] == "u-fam-seed"
    assert "u-fam-child" in uids
    assert any(
        any(str(w).startswith("expanded_route_family:") for w in (h.get("why_matched") or [])) for h in res.hits
    )


def test_expansion_round_robin_exercises_all_types() -> None:
    recap = "Longmont Campaign/Campaign 2/Session Recaps/Session 20 - Recap.md"
    parent = "Longmont Campaign/Campaign 2/Locations/site_q7/"
    child = "Longmont Campaign/Campaign 2/Locations/site_q7/sub_k2/"
    base = {
        "schema": "dmb_session_memory_record_v1",
        "campaign_id": "longmont-c2",
        "session_number": 20,
        "source_recap_path": recap,
        "text_blake3": "11" * 32,
    }
    records = [
        {
            **base,
            "unit_id": "u-00-seed",
            "line_start": 100,
            "line_end": 100,
            "lexical_plain": "seedtoken uncommonphrase",
            "routes": [{"subject_class": "Location", "normalized_route": parent, "proposed": False, "tag_kind": "inline"}],
        },
        {
            **base,
            "unit_id": "u-01-adj-a",
            "line_start": 99,
            "line_end": 99,
            "lexical_plain": "plain adjacent record",
            "routes": [{"subject_class": "Location", "normalized_route": parent, "proposed": False, "tag_kind": "inline"}],
        },
        {
            **base,
            "unit_id": "u-01-adj-b",
            "line_start": 101,
            "line_end": 101,
            "lexical_plain": "plain adjacent record b",
            "routes": [{"subject_class": "Location", "normalized_route": parent, "proposed": False, "tag_kind": "inline"}],
        },
        {
            **base,
            "unit_id": "u-02-shared",
            "line_start": 140,
            "line_end": 140,
            "lexical_plain": "shared route far away",
            "routes": [{"subject_class": "Location", "normalized_route": parent, "proposed": False, "tag_kind": "inline"}],
        },
        {
            **base,
            "unit_id": "u-03-family",
            "line_start": 200,
            "line_end": 200,
            "lexical_plain": "family route far away",
            "routes": [{"subject_class": "Location", "normalized_route": child, "proposed": False, "tag_kind": "inline"}],
        },
    ]
    greedy = query_session_memory_candidate(
        records=records,
        query="seedtoken uncommonphrase",
        campaign_id="longmont-c2",
        session_min=20,
        session_max=20,
        max_hits=4,
        expand_context=True,
        expand_seed_hits=1,
        expand_adjacent_window=2,
        expand_shared_route_limit=3,
        expand_route_family_limit=3,
        expand_first_pass_cap=1,
        expansion_allocation_mode="greedy",
    )
    rr = query_session_memory_candidate(
        records=records,
        query="seedtoken uncommonphrase",
        campaign_id="longmont-c2",
        session_min=20,
        session_max=20,
        max_hits=4,
        expand_context=True,
        expand_seed_hits=1,
        expand_adjacent_window=2,
        expand_shared_route_limit=3,
        expand_route_family_limit=3,
        expand_first_pass_cap=1,
        expansion_allocation_mode="round_robin",
    )
    g = greedy.trace["expansion"]
    r = rr.trace["expansion"]
    assert g["added_adjacent"] == 3 and g["added_shared_route"] == 0 and g["added_route_family"] == 0
    assert r["added_adjacent"] == 1 and r["added_shared_route"] == 1 and r["added_route_family"] == 1


def test_restrained_tokenizer_drops_function_words_but_keeps_domain_tokens() -> None:
    records = [
        {
            "schema": "dmb_session_memory_record_v1",
            "campaign_id": "longmont-c2",
            "session_number": 20,
            "source_recap_path": "Longmont Campaign/Campaign 2/Session Recaps/Session 20 - Recap.md",
            "unit_id": "u-noise",
            "line_start": 10,
            "line_end": 10,
            "text_blake3": "22" * 32,
            "lexical_plain": "the and for where which this that",
            "routes": [],
        },
        {
            "schema": "dmb_session_memory_record_v1",
            "campaign_id": "longmont-c2",
            "session_number": 20,
            "source_recap_path": "Longmont Campaign/Campaign 2/Session Recaps/Session 20 - Recap.md",
            "unit_id": "u-domain",
            "line_start": 11,
            "line_end": 11,
            "text_blake3": "33" * 32,
            "lexical_plain": "tealeaf stormspire academy relay",
            "routes": [],
        },
    ]
    default_res = query_session_memory_candidate(
        records=records,
        query="what and where tealeaf",
        campaign_id="longmont-c2",
        session_min=20,
        session_max=20,
        max_hits=5,
        tokenizer_mode="default",
    )
    restrained_res = query_session_memory_candidate(
        records=records,
        query="what and where tealeaf",
        campaign_id="longmont-c2",
        session_min=20,
        session_max=20,
        max_hits=5,
        tokenizer_mode="restrained",
    )
    default_uids = [str(h["unit_id"]) for h in default_res.hits]
    restrained_uids = [str(h["unit_id"]) for h in restrained_res.hits]
    assert "u-noise" in default_uids
    assert "u-noise" not in restrained_uids
    assert restrained_uids[0] == "u-domain"
    assert restrained_res.trace["tokenizer_mode"] == "restrained"
    assert restrained_res.trace["query_tokens"] == ["tealeaf"]


def test_load_jsonl_fixture_roundtrip(tmp_path: Path) -> None:
    path = tmp_path / "mem.jsonl"
    path.write_text("\n".join(json.dumps(r) for r in _minimal_records()) + "\n", encoding="utf-8")
    loaded = load_session_memory_records_jsonl(path)
    assert len(loaded) == 2


def test_planner_dispatch_query_session_memory(tmp_path: Path) -> None:
    dispatch = make_tool_dispatcher(
        tmp_path / "corpus",
        client=object(),
        model_id="gpt-mock",
        session_memory_records=_minimal_records(),
    )
    raw = dispatch(
        "query_session_memory",
        json.dumps(
            {
                "query": "voices tower",
                "campaign_id": "longmont-c2",
                "session_min": 20,
                "session_max": 20,
                "mode": "candidate",
            }
        ),
    )
    payload = json.loads(raw)
    assert payload["ok"] is True
    trace_row = {
        "tool": "query_session_memory",
        "arguments": {},
        "output_excerpt": raw,
    }
    uids = unit_ids_from_query_session_memory_trace([trace_row])
    assert "u-L0100-01" in uids


@pytest.mark.skipif(
    not Path("corpus/eldyrwild-markdown").is_dir(),
    reason="corpus not checked out",
)
def test_session20_normalize_and_gold_grades() -> None:
    from evals.sentence_routing_retrieval_falsification.breadcrumb_normalize import (
        normalize_breadcrumb_artifact,
    )
    from evals.sentence_routing_retrieval_falsification.breadcrumb_query_grader import (
        grade_scenario,
        load_gold,
    )

    corpus = Path("corpus/eldyrwild-markdown")
    art = Path(
        "corpus/eldyrwild-markdown/Longmont Campaign/Campaign 2/Session Recaps/_breadcrumbed/Session 20 - Gnat Swarm Marla Lysandra.breadcrumbed.md"
    )
    if not art.is_file():
        pytest.skip("Session 20 breadcrumb fixture missing")
    recs, _meta = normalize_breadcrumb_artifact(artifact_text=art.read_text(encoding="utf-8"), corpus_root=corpus)
    records = [r.to_json_dict() for r in recs]
    gold = load_gold(Path("evals/sentence_routing_retrieval_falsification/gold/breadcrumb_query_closed_loop_v1.json"))
    for scenario in gold["scenarios"]:
        g = grade_scenario(records=records, scenario=scenario)
        assert g["ok"], g

def test_same_beat_expansion_opt_in_and_marked() -> None:
    recap = "Longmont Campaign/Campaign 2/Session Recaps/Session 20 - Recap.md"
    records = [
        {"schema": "dmb_session_memory_record_v1", "campaign_id": "longmont-c2", "session_number": 20, "source_recap_path": recap, "unit_id": "u-seed", "line_start": 10, "line_end": 10, "text_blake3": "aa" * 32, "lexical_plain": "rareterm", "beat_id": "beat-1", "routes": []},
        {"schema": "dmb_session_memory_record_v1", "campaign_id": "longmont-c2", "session_number": 20, "source_recap_path": recap, "unit_id": "u-sib", "line_start": 11, "line_end": 11, "text_blake3": "bb" * 32, "lexical_plain": "other", "beat_id": "beat-1", "routes": []},
    ]
    off = query_session_memory_candidate(records=records, query="rareterm", campaign_id="longmont-c2", max_hits=2, expand_context=True, expand_adjacent_window=0, expand_shared_route_limit=0, expand_route_family_limit=0)
    on = query_session_memory_candidate(records=records, query="rareterm", campaign_id="longmont-c2", max_hits=2, expand_context=True, expand_same_beat_limit=2, expand_adjacent_window=0, expand_shared_route_limit=0, expand_route_family_limit=0)
    assert [h["unit_id"] for h in off.hits] == ["u-seed"]
    assert [h["unit_id"] for h in on.hits] == ["u-seed", "u-sib"]
    assert any("expanded_same_beat:beat-1" in (h.get("why_matched") or []) for h in on.hits)


def test_scene_beat_packets_score_from_first_pass_only() -> None:
    recap = "Longmont Campaign/Campaign 2/Session Recaps/Session 20 - Recap.md"
    records = [
        {"schema": "dmb_session_memory_record_v1", "campaign_id": "longmont-c2", "session_number": 20, "source_recap_path": recap, "unit_id": "u-a1", "line_start": 1, "line_end": 1, "text_blake3": "aa"*32, "lexical_plain": "alpha alpha", "beat_id": "beat-a", "routes": []},
        {"schema": "dmb_session_memory_record_v1", "campaign_id": "longmont-c2", "session_number": 20, "source_recap_path": recap, "unit_id": "u-a2", "line_start": 2, "line_end": 2, "text_blake3": "ab"*32, "lexical_plain": "alpha", "beat_id": "beat-a", "routes": []},
        {"schema": "dmb_session_memory_record_v1", "campaign_id": "longmont-c2", "session_number": 20, "source_recap_path": recap, "unit_id": "u-b1", "line_start": 3, "line_end": 3, "text_blake3": "ba"*32, "lexical_plain": "alpha alpha alpha", "beat_id": "beat-b", "routes": []},
        {"schema": "dmb_session_memory_record_v1", "campaign_id": "longmont-c2", "session_number": 20, "source_recap_path": recap, "unit_id": "u-b2", "line_start": 4, "line_end": 4, "text_blake3": "bb"*32, "lexical_plain": "alpha alpha alpha", "beat_id": "beat-b", "routes": []},
    ]
    result = query_session_memory_candidate(
        records=records, query="alpha", campaign_id="longmont-c2", max_hits=1,
        scene_beat_packet_mode=True, scene_beat_packet_threshold=4, scene_beat_packet_max_packets=1, scene_beat_packet_unit_limit=3
    )
    packet_trace = result.trace.get("scene_beat_packets") or {}
    assert packet_trace.get("qualified_count") == 1
    assert packet_trace.get("packets")[0]["beat_id"] == "beat-a"


def test_scene_beat_packets_replay_intent_stitches_adjacent_beats() -> None:
    recap = "Longmont Campaign/Campaign 1/Session Recaps/Session 13 - Recap.md"
    records = [
        {"schema": "dmb_session_memory_record_v1", "campaign_id": "longmont-c1", "session_number": 13, "source_recap_path": recap, "unit_id": "u-010-a", "line_start": 10, "line_end": 10, "text_blake3": "aa"*32, "lexical_plain": "morgue ambush fight replay", "beat_id": "c1s13-b010", "routes": []},
        {"schema": "dmb_session_memory_record_v1", "campaign_id": "longmont-c1", "session_number": 13, "source_recap_path": recap, "unit_id": "u-009-a", "line_start": 9, "line_end": 9, "text_blake3": "bb"*32, "lexical_plain": "sewer lead in", "beat_id": "c1s13-b009", "routes": []},
        {"schema": "dmb_session_memory_record_v1", "campaign_id": "longmont-c1", "session_number": 13, "source_recap_path": recap, "unit_id": "u-011-a", "line_start": 11, "line_end": 11, "text_blake3": "cc"*32, "lexical_plain": "aftermath", "beat_id": "c1s13-b011", "routes": []},
    ]
    result = query_session_memory_candidate(
        records=records, query="Create a beat by beat replay of the morgue ambush fight.", campaign_id="longmont-c1", max_hits=3,
        scene_beat_packet_mode=True, scene_beat_packet_threshold=4, scene_beat_packet_top_k=2, scene_beat_packet_unit_limit=5, scene_beat_packet_max_packets=1
    )
    packet_trace = result.trace.get("scene_beat_packets") or {}
    assert packet_trace.get("qualified_count") == 1
    packet = packet_trace.get("packets")[0]
    assert packet["beat_id"] == "c1s13-b010"
    assert packet["packet_unit_ids"] == ["u-010-a", "u-009-a", "u-011-a"]


def test_scene_beat_packets_non_replay_keeps_single_beat_behavior() -> None:
    recap = "Longmont Campaign/Campaign 1/Session Recaps/Session 13 - Recap.md"
    records = [
        {"schema": "dmb_session_memory_record_v1", "campaign_id": "longmont-c1", "session_number": 13, "source_recap_path": recap, "unit_id": "u-010-a", "line_start": 10, "line_end": 10, "text_blake3": "aa"*32, "lexical_plain": "morgue scene", "beat_id": "c1s13-b010", "routes": []},
        {"schema": "dmb_session_memory_record_v1", "campaign_id": "longmont-c1", "session_number": 13, "source_recap_path": recap, "unit_id": "u-009-a", "line_start": 9, "line_end": 9, "text_blake3": "bb"*32, "lexical_plain": "adjacent context", "beat_id": "c1s13-b009", "routes": []},
    ]
    result = query_session_memory_candidate(
        records=records, query="morgue scene summary", campaign_id="longmont-c1", max_hits=2,
        scene_beat_packet_mode=True, scene_beat_packet_threshold=2, scene_beat_packet_top_k=1, scene_beat_packet_unit_limit=5, scene_beat_packet_max_packets=1
    )
    packet = (result.trace.get("scene_beat_packets") or {}).get("packets")[0]
    assert packet["packet_unit_ids"] == ["u-010-a"]
