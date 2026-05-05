"""Unit tests for breadcrumb_query_planner_discovery_run helpers (no API)."""

from __future__ import annotations

import json

from evals.sentence_routing_retrieval_falsification.breadcrumb_query_planner_discovery_run import (
    flatten_normalized_routes_from_hits,
    load_planner_discovery_gold,
    paths_cover_substrings,
    planner_message_from_final_text,
    query_session_memory_call_count,
)


def test_paths_cover_substrings_partial():
    paths = ["Longmont Campaign/Campaign 2/NPCs/captain_lysandra_ironveil/README.md"]
    needles = ["NPCs/captain_lysandra_ironveil", "NPCs/missing_slug"]
    out = paths_cover_substrings(paths, needles)
    assert out["covered_count"] == 1
    assert out["needle_count"] == 2
    assert abs(out["recall"] - 0.5) < 1e-9


def test_flatten_normalized_routes_from_hits_order_and_dedupe():
    hits = [
        {
            "routes": [
                {"normalized_route": "a/B"},
                {"normalized_route": "a/b"},
            ]
        },
        {"routes": [{"normalized_route": "c/d"}]},
        {"routes": [{"normalized_route": "a/B"}]},
    ]
    flat = flatten_normalized_routes_from_hits(hits)
    assert flat == ["a/B", "c/d"]


def test_planner_message_from_final_text_strict_json():
    msg = "Hello **GM**"
    blob = json.dumps({"user_intent": "lore_lookup", "message": msg, "unsure_queue": None})
    extracted, err = planner_message_from_final_text(blob)
    assert err is None
    assert extracted == msg


def test_load_planner_discovery_gold(tmp_path):
    p = tmp_path / "pd.json"
    p.write_text(
        json.dumps(
            {
                "schema": "dmb_breadcrumb_query_planner_discovery_gold_v1",
                "scenarios": [
                    {"id": "s1", "expected_open_paths": ["Session 20", "NPCs/foo"]},
                ],
            }
        ),
        encoding="utf-8",
    )
    m = load_planner_discovery_gold(p)
    assert m["s1"]["expected_open_paths"] == ["Session 20", "NPCs/foo"]


def test_query_session_memory_call_count():
    trace = [
        {"tool": "read_corpus_file"},
        {"tool": "query_session_memory"},
        {"tool": "query_session_memory"},
    ]
    assert query_session_memory_call_count(trace) == 2


def test_planner_message_from_final_text_fenced():
    msg = "Tower clue"
    inner = json.dumps({"user_intent": None, "message": msg, "unsure_queue": None})
    fenced = "```json\n" + inner + "\n```"
    extracted, err = planner_message_from_final_text(fenced)
    assert err is None
    assert extracted == msg
