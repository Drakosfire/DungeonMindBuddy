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
