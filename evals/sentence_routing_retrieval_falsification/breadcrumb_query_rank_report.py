#!/usr/bin/env python3
"""Measure target-unit retrieval ranks for natural breadcrumb query scenarios.

This deterministic helper is the pronoun-resolution experiment's rank gate. It
uses the same natural gold and query function as ``breadcrumb_query_run.py`` but
does not call an LLM. It reports where targeted units appear in raw retrieval
and in the configured expanded retrieval path.
"""

from __future__ import annotations

import argparse
import json
from datetime import date
from pathlib import Path
from typing import Any

from evals.sentence_routing_retrieval_falsification.breadcrumb_normalize import (
    normalize_breadcrumb_artifact,
    write_records_jsonl,
)
from evals.sentence_routing_retrieval_falsification.breadcrumb_query_grader import (
    load_gold,
    merge_natural_benchmark_scenario,
    query_session_memory_for_scenario,
)

RANK_TARGETS_SCHEMA = "dmb_breadcrumb_query_rank_targets_v1"


def _prepare_scenario(gold: dict[str, Any], scenario_id: str) -> dict[str, Any]:
    for scenario in gold.get("scenarios") or []:
        if str(scenario.get("id")) != scenario_id:
            continue
        return merge_natural_benchmark_scenario(dict(scenario), gold)
    raise ValueError(f"scenario_id {scenario_id!r} not found in natural gold")


def _rank_row(
    *,
    records: list[dict[str, Any]],
    scenario: dict[str, Any],
    unit_id: str,
    expanded: bool,
    rank_budget: int,
) -> dict[str, Any]:
    scen = dict(scenario)
    qspec = dict(scen.get("query_spec") or {})
    qspec["expand_context"] = bool(expanded)
    qspec["max_hits"] = max(int(qspec.get("max_hits") or 1), int(rank_budget))
    if not expanded:
        qspec.pop("query_token_aliases", None)
    scen["query_spec"] = qspec
    result = query_session_memory_for_scenario(records=records, scenario=scen)
    hits = result.hits
    ids = [str(h.get("unit_id") or "") for h in hits]
    rank = ids.index(unit_id) + 1 if unit_id in ids else None
    hit = hits[rank - 1] if rank is not None else None
    return {
        "rank": rank,
        "hit_count": len(hits),
        "score": (hit or {}).get("score"),
        "why_matched": (hit or {}).get("why_matched") or [],
        "top_unit_id": ids[0] if ids else None,
        "query_tokens": (result.trace or {}).get("query_tokens") or [],
        "trace": result.trace,
    }


def _load_records(args: argparse.Namespace) -> tuple[list[dict[str, Any]], Path, dict[str, Any]]:
    if args.records_jsonl is not None:
        rows = [
            json.loads(line)
            for line in args.records_jsonl.read_text(encoding="utf-8").splitlines()
            if line.strip()
        ]
        return rows, args.records_jsonl, {}
    if args.breadcrumb_md is None or args.corpus_root is None:
        raise SystemExit("Provide --records-jsonl or (--breadcrumb-md and --corpus-root)")
    rec_objs, meta = normalize_breadcrumb_artifact(
        artifact_text=args.breadcrumb_md.read_text(encoding="utf-8"),
        corpus_root=args.corpus_root.resolve(),
        enrich_pronoun_route_handles=bool(args.pronoun_route_handles),
    )
    records_path = args.output.with_suffix(".records.jsonl") if args.output else Path(
        f"evals/sentence_routing_retrieval_falsification/artifacts/runs/{date.today()}/"
        "breadcrumb_query_rank_report.records.jsonl"
    )
    write_records_jsonl(rec_objs, records_path)
    return [r.to_json_dict() for r in rec_objs], records_path, meta


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--records-jsonl", type=Path)
    parser.add_argument("--breadcrumb-md", type=Path)
    parser.add_argument("--corpus-root", type=Path)
    parser.add_argument(
        "--pronoun-route-handles",
        action="store_true",
        help="Normalize breadcrumb markdown with pronoun route lexical enrichment.",
    )
    parser.add_argument(
        "--gold",
        type=Path,
        default=Path(
            "evals/sentence_routing_retrieval_falsification/gold/"
            "breadcrumb_query_natural_v1.json"
        ),
    )
    parser.add_argument(
        "--rank-targets",
        type=Path,
        default=Path(
            "evals/sentence_routing_retrieval_falsification/gold/"
            "breadcrumb_pronoun_rank_targets_session20.json"
        ),
    )
    parser.add_argument("--rank-budget", type=int, default=80)
    parser.add_argument("--output", type=Path)
    args = parser.parse_args()

    out_path = args.output or Path(
        f"evals/sentence_routing_retrieval_falsification/artifacts/runs/{date.today()}/"
        "breadcrumb_query_rank_report.json"
    )
    out_path.parent.mkdir(parents=True, exist_ok=True)
    records, records_path, normalize_meta = _load_records(args)
    gold = load_gold(args.gold)
    targets = json.loads(args.rank_targets.read_text(encoding="utf-8"))
    if targets.get("schema") != RANK_TARGETS_SCHEMA:
        raise SystemExit(
            f"--rank-targets must declare schema {RANK_TARGETS_SCHEMA}; got {targets.get('schema')!r}"
        )

    rows: list[dict[str, Any]] = []
    for target in targets.get("targets") or []:
        scenario_id = str(target["scenario_id"])
        unit_id = str(target["unit_id"])
        scenario = _prepare_scenario(gold, scenario_id)
        raw = _rank_row(
            records=records,
            scenario=scenario,
            unit_id=unit_id,
            expanded=False,
            rank_budget=args.rank_budget,
        )
        expanded = _rank_row(
            records=records,
            scenario=scenario,
            unit_id=unit_id,
            expanded=True,
            rank_budget=args.rank_budget,
        )
        desired = target.get("desired_max_rank")
        desired_rank = int(desired) if desired is not None else None
        rows.append(
            {
                "scenario_id": scenario_id,
                "unit_id": unit_id,
                "reason": target.get("reason"),
                "desired_max_rank": desired_rank,
                "raw": raw,
                "expanded": expanded,
                "raw_pass": bool(desired_rank and raw["rank"] and raw["rank"] <= desired_rank),
                "expanded_pass": bool(
                    desired_rank and expanded["rank"] and expanded["rank"] <= desired_rank
                ),
            }
        )

    report = {
        "schema": "dmb_breadcrumb_query_rank_report_v1",
        "records_source": str(records_path.resolve()),
        "gold": str(args.gold.resolve()),
        "rank_targets": str(args.rank_targets.resolve()),
        "pronoun_route_handles": bool(args.pronoun_route_handles),
        "normalize_meta": normalize_meta,
        "rank_budget": int(args.rank_budget),
        "targets": rows,
        "summary": {
            "target_count": len(rows),
            "raw_pass_count": sum(1 for row in rows if row["raw_pass"]),
            "expanded_pass_count": sum(1 for row in rows if row["expanded_pass"]),
        },
    }
    out_path.write_text(json.dumps(report, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    print(json.dumps({"wrote": str(out_path), "summary": report["summary"]}, indent=2))


if __name__ == "__main__":
    main()
