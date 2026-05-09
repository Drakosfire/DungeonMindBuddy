#!/usr/bin/env python3
"""Build a breadcrumb_query_run-shaped report without calling OpenAI (offline).

Uses each scenario's ``expected_answer`` as the stand-in ``llm_answer`` so retrieval,
route gates, and LLM-context gates can be exercised deterministically. Intended for:

* CI / sandboxes without API access
* Canvas refresh of ``c1s2-breadcrumb-query-benchmark-review.canvas.tsx`` before a
  live 3-run cohort is recorded

**Cost:** ``scenario_estimated_cost_usd`` is ``0.0``. Replace with real harness
reports for the 3-run acceptance gate (see suite README).

Example::

  uv run python -m evals.sentence_routing_retrieval_falsification.c1s2_offline_benchmark_report_build \\
    --output evals/sentence_routing_retrieval_falsification/artifacts/runs/2026-05-05/breadcrumb_query_natural_c1s2_report_offline.json
"""

from __future__ import annotations

import argparse
import json
from datetime import date
from pathlib import Path
from typing import Any

from evals.sentence_routing_retrieval_falsification.breadcrumb_normalize import normalize_breadcrumb_artifact
from evals.sentence_routing_retrieval_falsification.breadcrumb_natural_scoring import (
    build_hit_context_text,
    index_records_by_unit_id,
)
from evals.sentence_routing_retrieval_falsification.breadcrumb_query_grader import (
    aggregate_context_evidence_metrics,
    grade_natural_scenario,
    load_gold,
    natural_retrieval_bundle,
)
from evals.sentence_routing_retrieval_falsification.breadcrumb_query_llm import format_synthesis_user_message

_PROMOTED_CONTEXT_MAX_LEXICAL_UNITS_DEFAULT = 8
_PROMOTED_CONTEXT_MAX_CHARS_DEFAULT = 2400


def build_offline_report(
    *,
    breadcrumb_md: Path,
    corpus_root: Path,
    gold_path: Path,
) -> dict[str, Any]:
    art_text = breadcrumb_md.read_text(encoding="utf-8")
    rec_objs, meta = normalize_breadcrumb_artifact(artifact_text=art_text, corpus_root=corpus_root)
    records = [r.to_json_dict() for r in rec_objs]
    gold = load_gold(gold_path)
    default_campaign = str(gold.get("campaign_id") or "")
    default_spec = gold.get("default_query_spec") or {}
    results: list[dict[str, Any]] = []
    for scenario in gold.get("scenarios") or []:
        scen = dict(scenario)
        scen["campaign_id"] = str(scen.get("campaign_id") or default_campaign)
        merged_spec = {**default_spec, **(scen.get("query_spec") or {})}
        merged_spec["query"] = str(scen["question"])
        scen["query_spec"] = merged_spec
        bundle = natural_retrieval_bundle(records=records, scenario=scen)
        result, _hit_ctx = bundle
        by_unit = index_records_by_unit_id(records)
        hit_ctx_full = build_hit_context_text(
            result.hits,
            by_unit,
            include_normalized_route_lines=True,
        )
        hit_ctx_llm = build_hit_context_text(
            result.hits,
            by_unit,
            include_normalized_route_lines=False,
            exclude_path_like_lexical_units=True,
            query_tokens=[str(x) for x in (result.trace.get("query_tokens") or [])],
            max_lexical_units=int(
                scen.get("llm_promoted_context_max_units") or _PROMOTED_CONTEXT_MAX_LEXICAL_UNITS_DEFAULT
            ),
            max_chars=int(
                scen.get("llm_promoted_context_max_chars") or _PROMOTED_CONTEXT_MAX_CHARS_DEFAULT
            ),
            order_mode=str(scen.get("llm_promoted_context_order") or "ranked"),
        )
        llm_user_message = format_synthesis_user_message(
            question=str(scen["question"]),
            hit_context=hit_ctx_llm,
        )
        llm_text = str(scen.get("expected_answer") or "")
        row = grade_natural_scenario(
            records=records,
            scenario=scen,
            llm_answer=llm_text,
            cached_retrieval=bundle,
            breadcrumb_artifact_text=art_text,
            lexicon=None,
        )
        preview_n = int(scen.get("llm_answer_preview_chars", 1200))
        row["llm_answer_preview"] = llm_text[:preview_n]
        row["retrieved_context"] = hit_ctx_llm
        row["retrieval_hit_context_full"] = hit_ctx_full
        row["llm_user_message"] = llm_user_message
        row["llm_cost_usd"] = 0.0
        row["llm_usage"] = {}
        row["llm_model"] = "offline_expected_answer_stub"
        row["shadow_token_resolution"] = {
            "schema": "dmb_token_resolver_shadow_v1",
            "error": "offline_stub_no_shadow_lexicon",
        }
        results.append(row)

    sch = str(gold.get("schema") or "")
    return {
        "offline_stub": True,
        "records_source": str(breadcrumb_md.resolve()),
        "gold": str(gold_path.resolve()),
        "gold_schema": sch,
        "llm_enabled": True,
        "llm_model": "offline_expected_answer_stub",
        "aggregate_llm_cost_usd": 0.0,
        "scenario_estimated_cost_usd": 0.0,
        "shadow_token_resolution_build": {"ok": False, "error": "offline_stub", "lexicon": None},
        "all_ok": all(r.get("ok") for r in results),
        "results": results,
        "context_evidence_aggregate": aggregate_context_evidence_metrics(results),
    }


def main() -> None:
    p = argparse.ArgumentParser(description=__doc__)
    suite = Path(__file__).resolve().parent
    p.add_argument(
        "--breadcrumb-md",
        type=Path,
        default=suite / "manual_labels" / "Session 2 - Finishing the Job.breadcrumbed.md",
    )
    p.add_argument("--corpus-root", type=Path, default=Path("corpus/eldyrwild-markdown"))
    p.add_argument(
        "--gold",
        type=Path,
        default=suite / "gold" / "breadcrumb_query_natural_c1s2_v1.json",
    )
    p.add_argument(
        "--output",
        type=Path,
        default=None,
    )
    args = p.parse_args()
    out = args.output or suite / "artifacts" / "runs" / str(date.today()) / "breadcrumb_query_natural_c1s2_report_offline.json"
    report = build_offline_report(
        breadcrumb_md=args.breadcrumb_md,
        corpus_root=args.corpus_root,
        gold_path=args.gold,
    )
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(report, indent=2), encoding="utf-8")
    print(json.dumps({"wrote": str(out), "all_ok": report["all_ok"]}, indent=2))


if __name__ == "__main__":
    main()
