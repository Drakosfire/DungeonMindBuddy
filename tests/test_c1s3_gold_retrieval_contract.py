from __future__ import annotations

from pathlib import Path

from evals.sentence_routing_retrieval_falsification.breadcrumb_normalize import normalize_breadcrumb_artifact
from evals.sentence_routing_retrieval_falsification.breadcrumb_query_grader import (
    grade_natural_scenario,
    load_gold,
)


def test_c1s3_natural_gold_retrieval_with_expected_answer_stand_in() -> None:
    """Deterministic contract: retrieval + grading passes when LLM output matches gold expected_answer."""
    repo = Path(__file__).resolve().parents[1]
    md = repo / "evals/sentence_routing_retrieval_falsification/manual_labels/Session 3 - The Stone Bridge Flood.breadcrumbed.md"
    gold_path = repo / "evals/sentence_routing_retrieval_falsification/gold/breadcrumb_query_natural_c1s3_v1.json"
    art = md.read_text(encoding="utf-8")
    recs, _ = normalize_breadcrumb_artifact(artifact_text=art, corpus_root=repo / "corpus/eldyrwild-markdown")
    records = [r.to_json_dict() for r in recs if not str(r.unit_id).startswith("meta")]
    gold = load_gold(gold_path)
    default_campaign = gold["campaign_id"]
    default_spec = gold.get("default_query_spec") or {}
    for scenario in gold["scenarios"]:
        scen = dict(scenario)
        scen["campaign_id"] = str(scen.get("campaign_id") or default_campaign)
        merged = {**default_spec, **(scen.get("query_spec") or {})}
        merged["query"] = str(scen["question"])
        scen["query_spec"] = merged
        out = grade_natural_scenario(
            records=records,
            scenario=scen,
            llm_answer=str(scen["expected_answer"]),
            breadcrumb_artifact_text=art,
        )
        assert out["ok"], (scen["id"], out["violations"])
