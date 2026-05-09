"""Tests for C1S1 benchmark canvas block builder and patch helpers."""

from __future__ import annotations

import json
from pathlib import Path

from evals.sentence_routing_retrieval_falsification.c1s1_benchmark_canvas_emit import (
    BLOCK_BEGIN,
    BLOCK_END,
    build_c1s1_canvas_block,
    c1s1_canvas_refresh_auto_enabled,
    patch_c1s1_canvas_paths,
    refresh_c1s1_benchmark_canvases,
)


def _minimal_gold() -> dict:
    return {
        "schema": "dmb_breadcrumb_query_natural_gold_v1",
        "campaign_id": "longmont-c1",
        "default_query_spec": {},
        "scenarios": [
            {
                "id": "c1s1_party_roster_origin",
                "question": "Who was at Stonebridge?",
                "expected_answer": "The party.",
                "must_hit_tokens": ["party"],
            },
        ],
    }


def _minimal_result_row(*, sid: str = "c1s1_party_roster_origin") -> dict:
    return {
        "scenario_id": sid,
        "ok": True,
        "violations": [],
        "llm_answer_preview": "They reached Stonebridge together.",
        "retrieved_context": "lexical context",
        "retrieval_hit_context_full": "full context",
        "llm_user_message": "user message",
        "context_support_ratio": 1.0,
        "llm_context_support_ratio": 1.0,
        "llm_semantic_verdict": "pass_updated",
        "llm_semantic_must_hits": [],
        "full_result": {
            "hits": [
                {
                    "unit_id": "u-1",
                    "score": 3,
                    "line_start": 1,
                    "line_end": 2,
                    "source_recap_path": "Longmont Campaign/Session Recaps/Session 1 - Recap.md",
                    "routes": [{"normalized_route": "Campaign 1/PCs/karsemine"}],
                    "why_matched": ["lex"],
                }
            ],
            "trace": {"query_tokens": ["stonebridge"], "returned_hits": 1},
        },
    }


def _minimal_report() -> dict:
    return {
        "results": [_minimal_result_row()],
        "llm_model": "test-model",
        "scenario_estimated_cost_usd": 0.01,
        "aggregate_embedding_cost_usd": None,
        "embedding_similarity_enabled": False,
    }


def test_build_c1s1_canvas_block_is_deterministic() -> None:
    gold = _minimal_gold()
    report = _minimal_report()
    rp = Path("/tmp/fake_report.json")
    a = build_c1s1_canvas_block(report, gold, report_path=rp)
    b = build_c1s1_canvas_block(report, gold, report_path=rp)
    assert a == b
    assert BLOCK_BEGIN in a
    assert BLOCK_END in a
    assert "c1s1HarnessCanvasGenerated" in a


def test_c1s1_canvas_refresh_auto_enabled_by_filename_and_scenario_prefix(tmp_path: Path) -> None:
    gold_nat = dict(_minimal_gold())
    gold_nat["scenarios"] = [
        {
            "id": "nat_party_at_stonebridge",
            "question": "Who was at Stonebridge?",
            "expected_answer": "The party.",
            "must_hit_tokens": ["party"],
        }
    ]
    p_natural = tmp_path / "breadcrumb_query_natural_v1.json"
    p_natural.write_text(json.dumps(gold_nat), encoding="utf-8")
    assert c1s1_canvas_refresh_auto_enabled(gold_path=p_natural, gold=gold_nat) is False

    gold = _minimal_gold()
    p_c1 = tmp_path / "breadcrumb_query_natural_c1s1_v1.json"
    p_c1.write_text("{}", encoding="utf-8")
    assert c1s1_canvas_refresh_auto_enabled(gold_path=p_c1, gold=gold) is True

    gold2 = dict(gold)
    gold2["scenarios"] = [{"id": "other_lane", "question": "q"}]
    p2 = tmp_path / "other.json"
    assert c1s1_canvas_refresh_auto_enabled(gold_path=p2, gold=gold2) is False

    gold3 = dict(gold)
    gold3["scenarios"] = [{"id": "c1s1_other", "question": "q"}]
    assert c1s1_canvas_refresh_auto_enabled(gold_path=p2, gold=gold3) is True


def test_patch_c1s1_canvas_paths_missing_markers_reports_error(tmp_path: Path) -> None:
    canvas = tmp_path / "noop.canvas.tsx"
    canvas.write_text("// no markers here\n", encoding="utf-8")
    block = build_c1s1_canvas_block(_minimal_report(), _minimal_gold(), report_path=tmp_path / "r.json")
    out = patch_c1s1_canvas_paths(block, [canvas])
    assert len(out) == 1
    assert "error" in out[0]
    assert BLOCK_BEGIN in out[0]["error"]


def test_patch_c1s1_canvas_paths_updates_then_unchanged(tmp_path: Path) -> None:
    canvas = tmp_path / "c.canvas.tsx"
    canvas.write_text(
        f"import x from 'y';\n{BLOCK_BEGIN}\nold\n{BLOCK_END}\nexport default function C() {{}}\n",
        encoding="utf-8",
    )
    report = _minimal_report()
    gold = _minimal_gold()
    rp = tmp_path / "report.json"
    block = build_c1s1_canvas_block(report, gold, report_path=rp)
    first = patch_c1s1_canvas_paths(block, [canvas])
    assert first == [{"canvas_updated": str(canvas.resolve())}]
    text_after = canvas.read_text(encoding="utf-8")
    assert "old" not in text_after
    second = patch_c1s1_canvas_paths(block, [canvas])
    assert second == [{"canvas_unchanged": str(canvas.resolve())}]


def test_refresh_c1s1_benchmark_canvases_aggregate_keys(tmp_path: Path) -> None:
    canvas = tmp_path / "c.canvas.tsx"
    canvas.write_text(
        f"preamble\n{BLOCK_BEGIN}\nx\n{BLOCK_END}\ntrailer\n",
        encoding="utf-8",
    )
    rp = tmp_path / "out.json"
    summary = refresh_c1s1_benchmark_canvases(
        report=_minimal_report(),
        gold=_minimal_gold(),
        report_path=rp,
        canvas_paths=[canvas],
    )
    assert summary["enabled"] is True
    assert summary["updated"]
    assert summary["errors"] == []
    assert summary["scenario_count"] == 1
