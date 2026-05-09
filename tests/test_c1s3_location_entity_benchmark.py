from __future__ import annotations

from pathlib import Path

from evals.sentence_routing_retrieval_falsification.c1s3_location_entity_benchmark import (
    build_c1s3_location_entity_report,
)


def test_c1s3_location_entity_report_routes_and_mode() -> None:
    repo = Path(__file__).resolve().parents[1]
    md = (
        repo
        / "evals/sentence_routing_retrieval_falsification/manual_labels/Session 3 - The Stone Bridge Flood.breadcrumbed.md"
    )
    gold = repo / "evals/sentence_routing_retrieval_falsification/gold/breadcrumb_query_natural_c1s3_v1.json"
    corpus = repo / "corpus/eldyrwild-markdown"
    report = build_c1s3_location_entity_report(
        breadcrumb_md=md,
        corpus_root=corpus,
        gold_path=gold,
    )
    assert report["offline_stub"] is True
    assert report["all_ok"] is True
    assert report["scenario_estimated_cost_usd"] == 0.0
    assert report["query_mode"] == "location_entity_list"
    summary = report.get("location_entity_summary")
    assert isinstance(summary, dict)
    assert summary.get("relation_confidence") == "co_tagged_with_location"
    blob = "\n".join(str(x).lower() for x in (report.get("location_entity_routes") or []))
    assert "campaign 1/npcs/pippa" in blob
    assert "campaign 1/npcs/bubbles_the_float_goat" in blob
    assert "campaign 1/npcs/grishna" in blob
    assert "campaign 1/npcs/kirfan" not in blob
