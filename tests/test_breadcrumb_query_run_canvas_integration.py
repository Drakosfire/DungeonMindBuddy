"""Integration checks for benchmark run ↔ canvas refresh wiring (no LLM)."""

from __future__ import annotations

import json
from pathlib import Path

from evals.sentence_routing_retrieval_falsification.c1s1_benchmark_canvas_emit import (
    BLOCK_BEGIN,
    BLOCK_END,
    c1s1_canvas_refresh_auto_enabled,
    refresh_c1s1_benchmark_canvases,
)
from evals.sentence_routing_retrieval_falsification.c1s2_benchmark_canvas_emit import (
    BLOCK_BEGIN as C1S2_BLOCK_BEGIN,
    BLOCK_END as C1S2_BLOCK_END,
    c1s2_canvas_refresh_auto_enabled,
    refresh_c1s2_benchmark_canvases,
)
from evals.sentence_routing_retrieval_falsification.c1s3_benchmark_canvas_emit import (
    BLOCK_BEGIN as C1S3_BLOCK_BEGIN,
    BLOCK_END as C1S3_BLOCK_END,
    c1s3_canvas_refresh_auto_enabled,
    refresh_c1s3_benchmark_canvases,
)
from evals.sentence_routing_retrieval_falsification.c1s13_benchmark_canvas_emit import (
    BLOCK_BEGIN as C1S13_BLOCK_BEGIN,
    BLOCK_END as C1S13_BLOCK_END,
    c1s13_canvas_refresh_auto_enabled,
    refresh_c1s13_benchmark_canvases,
)


def test_c1s1_refresh_matches_breadcrumb_query_run_policy(tmp_path: Path) -> None:
    """Same eligibility + refresh primitive the runner uses after building a report."""
    gold_path = tmp_path / "breadcrumb_query_natural_c1s1_v1.json"
    gold = {
        "schema": "dmb_breadcrumb_query_natural_gold_v1",
        "campaign_id": "longmont-c1",
        "default_query_spec": {},
        "scenarios": [
            {
                "id": "c1s1_party_roster_origin",
                "question": "Q?",
                "expected_answer": "A.",
                "must_hit_tokens": ["a"],
            },
        ],
    }
    gold_path.write_text(json.dumps(gold), encoding="utf-8")
    assert c1s1_canvas_refresh_auto_enabled(gold_path=gold_path, gold=gold) is True

    canvas = tmp_path / "bench.canvas.tsx"
    canvas.write_text(f"head\n{BLOCK_BEGIN}\nold\n{BLOCK_END}\ntail\n", encoding="utf-8")
    report_path = tmp_path / "report.json"
    report = {
        "results": [
            {
                "scenario_id": "c1s1_party_roster_origin",
                "ok": True,
                "violations": [],
                "llm_answer_preview": "p",
                "retrieved_context": "c",
                "retrieval_hit_context_full": "f",
                "llm_user_message": "u",
                "context_support_ratio": 1.0,
                "llm_context_support_ratio": 1.0,
                "llm_semantic_verdict": None,
                "llm_semantic_must_hits": [],
                "full_result": {"hits": [], "trace": {"query_tokens": [], "returned_hits": 0}},
            },
            {
                "scenario_id": "c1s1_karsemine_spider_reveal",
                "ok": True,
                "violations": [],
                "llm_answer_preview": "",
                "retrieved_context": "",
                "retrieval_hit_context_full": "",
                "llm_user_message": "",
                "context_support_ratio": None,
                "llm_context_support_ratio": None,
                "llm_semantic_verdict": None,
                "llm_semantic_must_hits": [],
                "full_result": {"hits": [], "trace": {"query_tokens": [], "returned_hits": 0}},
            },
        ],
        "llm_model": "m",
    }
    summary = refresh_c1s1_benchmark_canvases(
        report=report,
        gold=gold,
        report_path=report_path,
        canvas_paths=[canvas],
    )
    assert not summary["errors"]
    assert summary["updated"] == [str(canvas.resolve())]


def test_c1s2_refresh_matches_breadcrumb_query_run_policy(tmp_path: Path) -> None:
    gold_path = tmp_path / "breadcrumb_query_natural_c1s2_v1.json"
    gold = {
        "schema": "dmb_breadcrumb_query_natural_gold_v1",
        "campaign_id": "longmont-c1",
        "default_query_spec": {},
        "scenarios": [
            {
                "id": "c1s2_glowkindle_stash_deal",
                "question": "Q?",
                "expected_answer": "A.",
                "must_hit_tokens": ["a"],
            },
        ],
    }
    gold_path.write_text(json.dumps(gold), encoding="utf-8")
    assert c1s2_canvas_refresh_auto_enabled(gold_path=gold_path, gold=gold) is True

    canvas = tmp_path / "bench.canvas.tsx"
    canvas.write_text(f"head\n{C1S2_BLOCK_BEGIN}\nold\n{C1S2_BLOCK_END}\ntail\n", encoding="utf-8")
    report_path = tmp_path / "report.json"
    report = {
        "results": [
            {
                "scenario_id": "c1s2_glowkindle_stash_deal",
                "ok": True,
                "violations": [],
                "llm_answer_preview": "p",
                "retrieved_context": "c",
                "retrieval_hit_context_full": "f",
                "llm_user_message": "u",
                "context_support_ratio": 1.0,
                "llm_context_support_ratio": 1.0,
                "llm_semantic_verdict": "pass_updated",
                "llm_semantic_must_hits": [],
                "full_result": {"hits": [], "trace": {"query_tokens": [], "returned_hits": 0}},
            },
        ],
        "llm_model": "m",
    }
    summary = refresh_c1s2_benchmark_canvases(
        report=report,
        gold=gold,
        report_path=report_path,
        canvas_paths=[canvas],
    )
    assert not summary["errors"]
    assert summary["updated"] == [str(canvas.resolve())]


def test_c1s3_refresh_matches_breadcrumb_query_run_policy(tmp_path: Path) -> None:
    gold_path = tmp_path / "breadcrumb_query_natural_c1s3_v1.json"
    gold = {
        "schema": "dmb_breadcrumb_query_natural_gold_v1",
        "campaign_id": "longmont-c1",
        "default_query_spec": {},
        "scenarios": [
            {
                "id": "c1s3_bubbles_mage_hand_beat",
                "question": "Q?",
                "expected_answer": "A.",
                "must_hit_tokens": ["a"],
            },
        ],
    }
    gold_path.write_text(json.dumps(gold), encoding="utf-8")
    assert c1s3_canvas_refresh_auto_enabled(gold_path=gold_path, gold=gold) is True

    canvas = tmp_path / "bench.canvas.tsx"
    canvas.write_text(f"head\n{C1S3_BLOCK_BEGIN}\nold\n{C1S3_BLOCK_END}\ntail\n", encoding="utf-8")
    report_path = tmp_path / "report.json"
    report = {
        "results": [
            {
                "scenario_id": "c1s3_bubbles_mage_hand_beat",
                "ok": True,
                "violations": [],
                "llm_answer_preview": "p",
                "retrieved_context": "c",
                "retrieval_hit_context_full": "f",
                "llm_user_message": "u",
                "context_support_ratio": 1.0,
                "llm_context_support_ratio": 1.0,
                "llm_semantic_verdict": "pass_updated",
                "llm_semantic_must_hits": [],
                "full_result": {"hits": [], "trace": {"query_tokens": [], "returned_hits": 0}},
            },
        ],
        "llm_model": "m",
    }
    summary = refresh_c1s3_benchmark_canvases(
        report=report,
        gold=gold,
        report_path=report_path,
        canvas_paths=[canvas],
    )
    assert not summary["errors"]
    assert summary["updated"] == [str(canvas.resolve())]


def test_c1s13_refresh_matches_breadcrumb_query_run_policy(tmp_path: Path) -> None:
    gold_path = tmp_path / "breadcrumb_query_natural_c1s13_v1.json"
    gold = {
        "schema": "dmb_breadcrumb_query_natural_gold_v1",
        "campaign_id": "longmont-c1",
        "default_query_spec": {},
        "scenarios": [
            {
                "id": "c1s13_wolf_admits_target",
                "question": "Q?",
                "expected_answer": "A.",
                "must_hit_tokens": ["wolf"],
            },
        ],
    }
    gold_path.write_text(json.dumps(gold), encoding="utf-8")
    assert c1s13_canvas_refresh_auto_enabled(gold_path=gold_path, gold=gold) is True

    canvas = tmp_path / "bench.canvas.tsx"
    canvas.write_text(f"head\n{C1S13_BLOCK_BEGIN}\nold\n{C1S13_BLOCK_END}\ntail\n", encoding="utf-8")
    report_path = tmp_path / "report.json"
    report = {
        "results": [
            {
                "scenario_id": "c1s13_wolf_admits_target",
                "ok": True,
                "violations": [],
                "llm_answer_preview": "p",
                "retrieved_context": "c",
                "retrieval_hit_context_full": "f",
                "llm_user_message": "u",
                "context_support_ratio": 1.0,
                "llm_context_support_ratio": 1.0,
                "llm_semantic_verdict": "pass_updated",
                "llm_semantic_must_hits": [],
                "full_result": {"hits": [], "trace": {"query_tokens": [], "returned_hits": 0}},
            },
        ],
        "llm_model": "m",
    }
    summary = refresh_c1s13_benchmark_canvases(
        report=report,
        gold=gold,
        report_path=report_path,
        canvas_paths=[canvas],
    )
    assert not summary["errors"]
    assert summary["updated"] == [str(canvas.resolve())]


def test_c1s13_canvas_refresh_emits_beat_scene_metrics(tmp_path: Path) -> None:
    """Emitter attaches records beat map, per-query trace, and harness scene fields."""
    records = tmp_path / "session.records_meta.jsonl"
    records.write_text(
        json.dumps(
            {
                "unit_id": "u-hit-1",
                "beat_id": "beat-alpha",
                "routes": [{"normalized_route": "Longmont Campaign/Campaign 1/NPCs/wolf/"}],
            }
        )
        + "\n",
        encoding="utf-8",
    )
    gold_path = tmp_path / "breadcrumb_query_natural_c1s13_v1.json"
    gold = {
        "schema": "dmb_breadcrumb_query_natural_gold_v1",
        "campaign_id": "longmont-c1",
        "default_query_spec": {},
        "scenarios": [
            {
                "id": "wolf_head_why_academy",
                "gold_beat_id": "c1s13-b001-plan-academy-departure",
                "question": "Q?",
                "expected_answer": "A.",
                "must_hit_tokens": ["wolf"],
            },
        ],
    }
    gold_path.write_text(json.dumps(gold), encoding="utf-8")
    assert c1s13_canvas_refresh_auto_enabled(gold_path=gold_path, gold=gold) is True

    canvas = tmp_path / "bench.canvas.tsx"
    canvas.write_text(f"head\n{C1S13_BLOCK_BEGIN}\nold\n{C1S13_BLOCK_END}\ntail\n", encoding="utf-8")
    report_path = tmp_path / "report.json"
    report = {
        "records_source": str(records),
        "results": [
            {
                "scenario_id": "wolf_head_why_academy",
                "ok": True,
                "violations": [],
                "llm_answer_preview": "p",
                "retrieved_context": "c",
                "retrieval_hit_context_full": "f",
                "llm_user_message": "u",
                "context_support_ratio": 1.0,
                "llm_context_support_ratio": 1.0,
                "llm_semantic_verdict": "pass_updated",
                "llm_semantic_must_hits": [],
                "scene_beat_expansion": {"enabled": True, "note": "harness"},
                "scene_beat_packets": {
                    "enabled": True,
                    "qualified_count": 2,
                    "units_added": 1,
                    "packets": [
                        {
                            "beat_id": "b-packet-1",
                            "score": 3,
                            "first_pass_unit_ids": ["u1"],
                            "packet_unit_ids": ["u1", "u2"],
                        }
                    ],
                },
                "full_result": {
                    "hits": [
                        {
                            "unit_id": "u-hit-1",
                            "line_start": 10,
                            "line_end": 11,
                            "score": 9,
                            "source_recap_path": "Longmont Campaign/.../Session 13.md",
                            "routes": [{"normalized_route": "Longmont Campaign/Campaign 1/NPCs/wolf/"}],
                            "why_matched": ["lexical_token:wolf"],
                        }
                    ],
                    "trace": {
                        "expand_same_beat_limit": 4,
                        "expand_adjacent_window": 1,
                        "expand_context": True,
                        "expansion": {
                            "added_same_beat": 2,
                            "added_adjacent": 0,
                            "added_shared_route": 0,
                            "added_route_family": 0,
                        },
                        "scene_beat_packets": {
                            "qualified_count": 1,
                            "units_added": 2,
                            "packets": [],
                        },
                    },
                },
            },
        ],
        "llm_model": "m",
    }
    summary = refresh_c1s13_benchmark_canvases(
        report=report,
        gold=gold,
        report_path=report_path,
        canvas_paths=[canvas],
    )
    assert not summary["errors"]
    text = canvas.read_text(encoding="utf-8")
    assert "corpusBeatStats" in text
    assert "recordsSource" in text
    assert "query_trace_beat_scene" in text
    assert "scene_beat_expansion" in text
    assert "scene_beat_packets" in text
    assert "beat-alpha" in text
    assert "beat_retrieval_rollups" in text
    assert "gold_beat_id" in text
    assert "is_primary_gold_beat" in text
    assert "beat_rollup_diagnostic" in text
