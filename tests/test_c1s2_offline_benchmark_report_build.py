from __future__ import annotations

from pathlib import Path

from evals.sentence_routing_retrieval_falsification.c1s2_offline_benchmark_report_build import (
    build_offline_report,
)


def test_c1s2_offline_report_all_ok() -> None:
    repo = Path(__file__).resolve().parents[1]
    md = repo / "corpus/eldyrwild-markdown/Longmont Campaign/Campaign 1/Session Recaps/_breadcrumbed/Session 02 - Finishing the Job.breadcrumbed.md"
    gold = repo / "evals/sentence_routing_retrieval_falsification/gold/breadcrumb_query_natural_c1s2_v1.json"
    corpus = repo / "corpus/eldyrwild-markdown"
    report = build_offline_report(breadcrumb_md=md, corpus_root=corpus, gold_path=gold)
    assert report["offline_stub"] is True
    assert report["all_ok"] is True
    assert len(report["results"]) == 15
    assert report.get("scenario_estimated_cost_usd") == 0.0
