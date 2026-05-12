from __future__ import annotations

from pathlib import Path

from evals.sentence_routing_retrieval_falsification.breadcrumb_tagging_scorer import (
    read_tagging_sentinels,
    score_artifact,
)


def test_c1s3_tagging_sentinels_pass_on_current_breadcrumb_artifact() -> None:
    repo = Path(__file__).resolve().parents[1]
    md = repo / "corpus/eldyrwild-markdown/Longmont Campaign/Campaign 1/Session Recaps/_breadcrumbed/Session 03 - The Stone Bridge Flood.breadcrumbed.md"
    sent_path = repo / "evals/sentence_routing_retrieval_falsification/gold/breadcrumb_tagging_sentinels_c1s3.json"
    corpus = repo / "corpus/eldyrwild-markdown"
    out = score_artifact(
        artifact_path=md,
        corpus_root=corpus,
        sentinels=read_tagging_sentinels(sent_path),
        baseline_artifact_path=None,
    )
    assert out["normalize"]["ok"] is True
    summary = out["sentinels"]["summary"]
    assert summary["positive_passed"] == summary["positive_total"]
    assert summary["negative_passed"] == summary["negative_total"]
