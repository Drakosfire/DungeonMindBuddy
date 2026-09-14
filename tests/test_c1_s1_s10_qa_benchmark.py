"""Tests for the Campaign 1 Sessions 1–10 QA Benchmark runner and artifacts."""

from __future__ import annotations

import importlib.util
import json
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
TOOL_PATH = REPO_ROOT / "tools/run_c1_s1_s10_benchmark.py"

spec = importlib.util.spec_from_file_location("run_c1_s1_s10_benchmark", TOOL_PATH)
assert spec is not None and spec.loader is not None
bench = importlib.util.module_from_spec(spec)
import sys
sys.modules[spec.name] = bench
spec.loader.exec_module(bench)


def test_parse_benchmark_gold() -> None:
    gold_path = Path("evals/graph_benchmark_gold/qa/longmont-c1/sessions-01-10-v1.md")
    assert gold_path.is_file(), f"Gold file missing at {gold_path}"

    questions = bench.parse_benchmark_gold(gold_path)
    assert len(questions) == 16, f"Expected 16 questions, got {len(questions)}"

    qids = [q.qid for q in questions]
    expected_qids = [f"Q{i:02d}" for i in range(1, 17)]
    assert qids == expected_qids

    for q in questions:
        assert q.difficulty in {1, 2, 3, 4, 5}
        assert len(q.question) > 10
        assert len(q.gold_answer) > 10
        assert len(q.must_include) >= 1
        assert len(q.oracle_searches) >= 1


def test_scoring_logic_discriminative() -> None:
    gold_path = Path("evals/graph_benchmark_gold/qa/longmont-c1/sessions-01-10-v1.md")
    questions = {q.qid: q for q in bench.parse_benchmark_gold(gold_path)}

    q01 = questions["Q01"]
    credit, met, miss, viol = bench.score_text_against_gold("The meat was from another plane of existence.", q01)
    assert credit == "full"
    assert "the meat is from another plane / extraplanar" in met

    credit, met, miss, viol = bench.score_text_against_gold("The meat was found in the cold room.", q01)
    assert credit == "fail"
    assert "the meat is from another plane / extraplanar" in miss

    q02 = questions["Q02"]
    credit, met, miss, viol = bench.score_text_against_gold("Take them to the Head Alchemist at Stormspire Academy.", q02)
    assert credit == "full"
    assert len(met) == 2


def test_benchmark_artifacts_exist_and_consistent() -> None:
    benchmark_dir = Path("out/stage4l_c1_s1_s10_chronological_graph_rehearsal/pc_identity_repair/benchmark")
    manifest_path = benchmark_dir / "MANIFEST.json"
    summary_path = benchmark_dir / "summary.json"
    results_path = benchmark_dir / "results.json"
    report_path = benchmark_dir / "REPORT.md"

    assert manifest_path.is_file(), f"Missing {manifest_path}"
    assert summary_path.is_file(), f"Missing {summary_path}"
    assert results_path.is_file(), f"Missing {results_path}"
    assert report_path.is_file(), f"Missing {report_path}"

    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    summary = json.loads(summary_path.read_text(encoding="utf-8"))
    results = json.loads(results_path.read_text(encoding="utf-8"))
    report = report_path.read_text(encoding="utf-8")

    assert manifest["benchmark_id"] == "longmont-c1-sessions-01-10-graph-query-v1"
    assert manifest["pr_head"] == bench.DEFAULT_PR_HEAD
    assert manifest["authoritative_world_revision"] == bench.DEFAULT_REVISION
    assert manifest["question_count"] == 16
    assert manifest["oracle_full_credit"] == 7

    assert summary["metadata"]["git_commit_head"] == bench.DEFAULT_PR_HEAD
    assert summary["metadata"]["authoritative_revision_id"] == bench.DEFAULT_REVISION
    assert summary["scores"]["oracle"]["full_credit"] == 7
    assert summary["scores"]["oracle"]["partial_credit"] == 8
    assert summary["scores"]["oracle"]["fail"] == 1
    assert summary["scores"]["oracle"]["any_credit_rate"] == 0.9375
    assert summary["scores"]["agent"]["any_credit_rate"] == 0.875

    assert len(results) == 16
    assert f"PR Head:** `{bench.DEFAULT_PR_HEAD}`" in report
    assert f"World Revision:** `{bench.DEFAULT_REVISION}`" in report
