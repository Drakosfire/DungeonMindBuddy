"""Gold beat rollup helpers for C1S13 benchmark review canvas."""

from __future__ import annotations

from pathlib import Path

from evals.sentence_routing_retrieval_falsification.c1s13_benchmark_canvas_emit import (
    _annotate_rollups_table_metrics,
    _beat_rollup_diagnostic,
    _build_rows,
    _load_gold_beat_unit_map,
    _rollup_retrieval_hits_by_gold_beat,
    _tag_rollups_primary_gold_beat,
)


def test_load_gold_beat_unit_map_maps_arrival_units() -> None:
    root = Path(__file__).resolve().parents[1]
    path = (
        root
        / "evals/sentence_routing_retrieval_falsification/manual_labels"
        / "Session 13 - The Meaty and the Dead.gold.scene_span_v1.breadcrumbed.md"
    )
    m = _load_gold_beat_unit_map(path)
    assert m["u-L0007-01"] == "c1s13-b003-stormspire-arrival-desk"
    assert m["u-L0007-02"] == "c1s13-b003-stormspire-arrival-desk"


def test_rollup_sorts_by_summed_score_desc() -> None:
    unit_map = {
        "u-a": "beat-a",
        "u-b": "beat-b",
        "u-c": "beat-a",
    }
    hits = [
        {"unit_id": "u-a", "score": 2, "line_start": 1, "line_end": 1},
        {"unit_id": "u-b", "score": 10, "line_start": 2, "line_end": 2},
        {"unit_id": "u-c", "score": 3, "line_start": 1, "line_end": 1},
    ]
    roll = _rollup_retrieval_hits_by_gold_beat(hits, unit_map)
    assert [r["beat_id"] for r in roll] == ["beat-b", "beat-a"]
    assert roll[0]["summed_score"] == 10
    assert roll[1]["summed_score"] == 5
    assert roll[0]["hits"][0]["rank"] == 2


def test_rollup_meta_and_unmapped_buckets() -> None:
    hits = [
        {"unit_id": "meta-session-0013-locations", "score": 8, "line_start": 0, "line_end": 0},
        {"unit_id": "u-unknown", "score": 1, "line_start": 99, "line_end": 99},
    ]
    roll = _rollup_retrieval_hits_by_gold_beat(hits, {})
    by_id = {r["beat_id"]: r for r in roll}
    assert by_id["__session_meta__"]["summed_score"] == 8
    assert by_id["__unmapped__"]["summed_score"] == 1


def test_tag_rollups_primary_gold_beat_marks_matching_row() -> None:
    roll = [
        {"beat_id": "c1s13-b003-stormspire-arrival-desk", "summed_score": 11, "hit_count": 1, "hits": []},
        {"beat_id": "c1s13-b001-plan-academy-departure", "summed_score": 10, "hit_count": 1, "hits": []},
    ]
    out = _tag_rollups_primary_gold_beat(roll, "c1s13-b003-stormspire-arrival-desk")
    assert out[0]["is_primary_gold_beat"] is True
    assert out[1]["is_primary_gold_beat"] is False


def test_tag_rollups_primary_gold_beat_false_when_no_gold() -> None:
    roll = [{"beat_id": "c1s13-b003-stormspire-arrival-desk", "summed_score": 11, "hit_count": 1, "hits": []}]
    out = _tag_rollups_primary_gold_beat(roll, None)
    assert out[0]["is_primary_gold_beat"] is False


def test_annotate_rollups_table_metrics_sets_rank_delta_ratio() -> None:
    roll = [
        {"beat_id": "a", "summed_score": 10, "hit_count": 1, "hits": []},
        {"beat_id": "b", "summed_score": 4, "hit_count": 1, "hits": []},
    ]
    _annotate_rollups_table_metrics(roll)
    assert roll[0]["rollup_rank"] == 1 and roll[0]["delta_from_table_top"] == 0 and roll[0]["ratio_to_table_top"] == 1.0
    assert roll[1]["rollup_rank"] == 2 and roll[1]["delta_from_table_top"] == 6 and roll[1]["ratio_to_table_top"] == 0.4


def test_beat_rollup_diagnostic_gold_top() -> None:
    roll = [
        {"beat_id": "c1s13-b003-stormspire-arrival-desk", "summed_score": 11, "hit_count": 1, "hits": []},
        {"beat_id": "other", "summed_score": 3, "hit_count": 1, "hits": []},
    ]
    d = _beat_rollup_diagnostic(roll, "c1s13-b003-stormspire-arrival-desk")
    assert d["promotion_hint"] == "gold_top"
    assert d["gold_rank"] == 1
    assert d["gold_rank_non_meta"] == 1
    assert d["delta_table_top_minus_gold"] == 0


def test_beat_rollup_diagnostic_meta_leads_table() -> None:
    roll = [
        {"beat_id": "__session_meta__", "summed_score": 9, "hit_count": 1, "hits": []},
        {"beat_id": "c1s13-b007-escaped-meat-second-split", "summed_score": 2, "hit_count": 1, "hits": []},
    ]
    d = _beat_rollup_diagnostic(roll, "c1s13-b007-escaped-meat-second-split")
    assert d["meta_is_table_top"] is True
    assert d["promotion_hint"] == "gold_top_non_meta_meta_leads_table"
    assert d["gold_rank_non_meta"] == 1
    assert d["gold_rank"] == 2


def test_beat_rollup_diagnostic_meta_leads_table_gold_not_first_non_meta() -> None:
    roll = [
        {"beat_id": "__session_meta__", "summed_score": 9, "hit_count": 1, "hits": []},
        {"beat_id": "c1s13-b004-stormspire-options-and-split", "summed_score": 5, "hit_count": 1, "hits": []},
        {"beat_id": "c1s13-b007-escaped-meat-second-split", "summed_score": 2, "hit_count": 1, "hits": []},
    ]
    d = _beat_rollup_diagnostic(roll, "c1s13-b007-escaped-meat-second-split")
    assert d["meta_is_table_top"] is True
    assert d["promotion_hint"] == "meta_leads_table"
    assert d["gold_rank_non_meta"] == 2


def test_build_rows_includes_beat_rollup_diagnostic() -> None:
    report = {
        "results": [
            {
                "scenario_id": "rollup_gold_beat_probe",
                "ok": True,
                "violations": [],
                "full_result": {"hits": []},
            }
        ],
        "records_source": "",
    }
    gold = {
        "scenarios": [
            {
                "id": "rollup_gold_beat_probe",
                "gold_beat_id": "c1s13-b003-stormspire-arrival-desk",
                "question": "q",
                "expected_answer": "",
                "must_hit_tokens": [],
                "expect_route_substrings": [],
            }
        ]
    }
    rows, _ = _build_rows(report=report, gold=gold)
    assert len(rows) == 1
    assert rows[0]["gold_beat_id"] == "c1s13-b003-stormspire-arrival-desk"
    assert rows[0]["beat_retrieval_rollups"] == []
    assert rows[0]["beat_rollup_diagnostic"]["promotion_hint"] == "no_rollups"
