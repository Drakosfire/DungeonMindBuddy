from __future__ import annotations

import json
from pathlib import Path

from evals.sentence_routing_retrieval_falsification.c1s2_benchmark_canvas_emit import (
    BLOCK_BEGIN,
    BLOCK_END,
    refresh_c1s2_benchmark_canvases,
)


def test_c1s2_benchmark_canvas_refresh(tmp_path: Path) -> None:
    canvas = tmp_path / "bench.canvas.tsx"
    canvas.write_text(f"head\n{BLOCK_BEGIN}\nold\n{BLOCK_END}\ntail\n", encoding="utf-8")
    gold_path = tmp_path / "gold.json"
    gold = {
        "schema": "dmb_breadcrumb_query_natural_gold_v1",
        "campaign_id": "longmont-c1",
        "default_query_spec": {},
        "scenarios": [
            {
                "id": "c1s2_glowkindle_stash_deal",
                "question": "Q?",
                "expected_answer": "A.",
                "must_hit_tokens": ["Glowkindle"],
            },
        ],
    }
    gold_path.write_text(json.dumps(gold), encoding="utf-8")
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
    text = canvas.read_text(encoding="utf-8")
    assert "c1s2HarnessCanvasGenerated" in text
    assert "scenarioDesignGenerated" in text
