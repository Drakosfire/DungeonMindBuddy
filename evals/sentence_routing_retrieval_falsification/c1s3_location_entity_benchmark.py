#!/usr/bin/env python3
"""Focused C1S3 benchmark for location-entity list retrieval behavior.

This runner isolates the StoneBridge NPC roster scenario and emits a compact report
showing exactly how deterministic retrieval behaves:

- query mode chosen by the retriever
- location route resolved from the natural-language question
- aggregated co-tagged NPC/NewHubCandidate routes
- supporting unit IDs and lexical snippets

By default this is an offline deterministic harness:
``expected_answer`` is used as the stand-in LLM output, and cost is ``0.0``.
"""

from __future__ import annotations

import argparse
import json
from datetime import date, datetime, timezone
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
_DEFAULT_SCENARIO_ID = "c1s3_stonebridge_npc_roster_associated"


def _scenario_by_id(gold: dict[str, Any], scenario_id: str) -> dict[str, Any]:
    for scen in gold.get("scenarios") or []:
        if str(scen.get("id") or "") == scenario_id:
            return dict(scen)
    raise ValueError(f"scenario id not found in gold: {scenario_id!r}")


def _merge_scenario_query_spec(gold: dict[str, Any], scenario: dict[str, Any]) -> dict[str, Any]:
    default_campaign = str(gold.get("campaign_id") or "")
    default_spec = gold.get("default_query_spec") or {}
    scen = dict(scenario)
    scen["campaign_id"] = str(scen.get("campaign_id") or default_campaign)
    merged_spec = {**default_spec, **(scen.get("query_spec") or {})}
    merged_spec["query"] = str(scen.get("question") or "")
    scen["query_spec"] = merged_spec
    return scen


def _location_entity_routes(summary: dict[str, Any] | None) -> list[str]:
    if not isinstance(summary, dict):
        return []
    out: list[str] = []
    for ent in summary.get("entities") or []:
        if isinstance(ent, dict):
            out.append(str(ent.get("normalized_route") or ""))
    return sorted(set(out), key=str.lower)


def build_c1s3_location_entity_report(
    *,
    breadcrumb_md: Path,
    corpus_root: Path,
    gold_path: Path,
    scenario_id: str = _DEFAULT_SCENARIO_ID,
) -> dict[str, Any]:
    art_text = breadcrumb_md.read_text(encoding="utf-8")
    rec_objs, _meta = normalize_breadcrumb_artifact(artifact_text=art_text, corpus_root=corpus_root)
    records = [r.to_json_dict() for r in rec_objs]
    gold = load_gold(gold_path)
    scenario = _merge_scenario_query_spec(gold, _scenario_by_id(gold, scenario_id))

    bundle = natural_retrieval_bundle(records=records, scenario=scenario)
    result, _ = bundle
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
            scenario.get("llm_promoted_context_max_units") or _PROMOTED_CONTEXT_MAX_LEXICAL_UNITS_DEFAULT
        ),
        max_chars=int(
            scenario.get("llm_promoted_context_max_chars") or _PROMOTED_CONTEXT_MAX_CHARS_DEFAULT
        ),
        order_mode=str(scenario.get("llm_promoted_context_order") or "ranked"),
    )
    llm_user_message = format_synthesis_user_message(
        question=str(scenario.get("question") or ""),
        hit_context=hit_ctx_llm,
    )
    llm_text = str(scenario.get("expected_answer") or "")
    row = grade_natural_scenario(
        records=records,
        scenario=scenario,
        llm_answer=llm_text,
        cached_retrieval=bundle,
        breadcrumb_artifact_text=art_text,
        lexicon=None,
    )
    row["llm_answer_preview"] = llm_text[:1200]
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

    trace = result.trace if isinstance(result.trace, dict) else {}
    summary = trace.get("location_entity_summary")
    out = {
        "schema": "dmb_c1s3_location_entity_benchmark_v1",
        "offline_stub": True,
        "records_source": str(breadcrumb_md.resolve()),
        "gold": str(gold_path.resolve()),
        "gold_schema": str(gold.get("schema") or ""),
        "scenario_id": scenario_id,
        "all_ok": bool(row.get("ok")),
        "results": [row],
        "context_evidence_aggregate": aggregate_context_evidence_metrics([row]),
        "aggregate_llm_cost_usd": 0.0,
        "scenario_estimated_cost_usd": 0.0,
        "query_mode": str(trace.get("query_mode") or ""),
        "location_entity_summary": summary if isinstance(summary, dict) else None,
        "location_entity_routes": _location_entity_routes(summary if isinstance(summary, dict) else None),
        "how_it_works": [
            "Normalize breadcrumb markdown into sentence-unit records with routes.",
            "Run deterministic query_session_memory_candidate with the natural question.",
            "If the query is roster-like and a location slug is resolvable, switch query_mode to location_entity_list.",
            "Aggregate NPC/NewHubCandidate routes co-tagged on records carrying the resolved location route.",
            "Report relation confidence as co_tagged_with_location (association, not residency).",
        ],
    }
    return out


def _default_output_path(suite_dir: Path) -> Path:
    stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    run_dir = suite_dir / "artifacts" / "runs" / str(date.today())
    return run_dir / f"c1s3_location_entity_benchmark--{stamp}.json"


def main() -> None:
    suite = Path(__file__).resolve().parent
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument(
        "--breadcrumb-md",
        type=Path,
        default=suite / "manual_labels" / "Session 3 - The Stone Bridge Flood.breadcrumbed.md",
    )
    p.add_argument("--corpus-root", type=Path, default=Path("corpus/eldyrwild-markdown"))
    p.add_argument(
        "--gold",
        type=Path,
        default=suite / "gold" / "breadcrumb_query_natural_c1s3_v1.json",
    )
    p.add_argument("--scenario-id", type=str, default=_DEFAULT_SCENARIO_ID)
    p.add_argument("--output", type=Path, default=None)
    args = p.parse_args()

    out = args.output or _default_output_path(suite)
    report = build_c1s3_location_entity_report(
        breadcrumb_md=args.breadcrumb_md,
        corpus_root=args.corpus_root,
        gold_path=args.gold,
        scenario_id=str(args.scenario_id),
    )
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(report, indent=2), encoding="utf-8")

    mirror = suite / "artifacts" / "last_c1s3_location_entity_benchmark.json"
    mirror.parent.mkdir(parents=True, exist_ok=True)
    mirror.write_text(json.dumps(report, indent=2), encoding="utf-8")

    print(
        json.dumps(
            {
                "wrote": str(out),
                "mirror": str(mirror),
                "all_ok": bool(report.get("all_ok")),
                "query_mode": report.get("query_mode"),
                "location_entity_routes": report.get("location_entity_routes"),
            },
            indent=2,
        )
    )


if __name__ == "__main__":
    main()
