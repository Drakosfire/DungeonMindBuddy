from __future__ import annotations

import json
from pathlib import Path

from evals.sentence_routing_retrieval_falsification.c1s2_query_candidate_build import build_candidates_payload
from evals.sentence_routing_retrieval_falsification.breadcrumb_normalize import normalize_breadcrumb_artifact


def test_c1s2_candidate_payload_schema_and_gold_free(tmp_path: Path) -> None:
    repo = Path(__file__).resolve().parents[1]
    md = repo / "corpus/eldyrwild-markdown/Longmont Campaign/Campaign 1/Session Recaps/_breadcrumbed/Session 02 - Finishing the Job.breadcrumbed.md"
    corpus = repo / "corpus/eldyrwild-markdown"
    text = md.read_text(encoding="utf-8")
    records, _ = normalize_breadcrumb_artifact(artifact_text=text, corpus_root=corpus)
    payload = build_candidates_payload(
        records=records,
        source_breadcrumb_path=str(md.relative_to(repo)),
        campaign_id="longmont-c1",
        session_number=2,
    )
    assert payload["schema"] == "dmb_breadcrumb_query_candidates_v1"
    assert payload["session_number"] == 2
    assert len(payload["candidates"]) >= 1
    for c in payload["candidates"]:
        assert c["review_status"] == "pending"
        assert c["supporting_unit_ids"]
    out = tmp_path / "c.json"
    out.write_text(json.dumps(payload), encoding="utf-8")
    assert out.read_text(encoding="utf-8")
