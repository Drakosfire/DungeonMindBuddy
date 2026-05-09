#!/usr/bin/env python3
"""Planner discovery vs JSONL retrieval (natural gold).

For each scenario in ``breadcrumb_query_natural_v1.json``:

1. **Benchmark arm** — same deterministic retrieval + optional synthesis + grading as
   ``breadcrumb_query_run`` (fixed hit context passed to the synthesis LLM).
2. **Planner arm** — one live planner turn with ``user_line`` = the natural ``question``
   only (no fixture provisioning). Records which corpus paths were opened via
   ``read_corpus_file`` / ``load_context_markdown`` and optionally ``query_session_memory``.

Writes a default JSON artifact under ``artifacts/runs/<date>/`` unless ``--output`` is set,
and mirrors to ``artifacts/last_breadcrumb_query_planner_discovery_report.json``.

Examples::

  uv run python -m evals.sentence_routing_retrieval_falsification.breadcrumb_query_planner_discovery_run \\
    --records-jsonl evals/sentence_routing_retrieval_falsification/artifacts/runs/<date>/session20.jsonl \\
    --corpus-root corpus/eldyrwild-markdown \\
    --gold evals/sentence_routing_retrieval_falsification/gold/breadcrumb_query_natural_v1.json

  # Save benchmark LLM cost: retrieval + grading only for harness synthesis arm
  uv run python -m evals.sentence_routing_retrieval_falsification.breadcrumb_query_planner_discovery_run \\
    --records-jsonl ... --corpus-root corpus/eldyrwild-markdown --skip-benchmark-llm

  # Ablation: expose ``query_session_memory`` with the same JSONL the grader uses
  uv run python -m evals.sentence_routing_retrieval_falsification.breadcrumb_query_planner_discovery_run \\
    --records-jsonl ... --corpus-root corpus/eldyrwild-markdown --planner-session-memory-records same.jsonl
"""

from __future__ import annotations

import argparse
import json
import os
from contextlib import contextmanager
from dataclasses import replace
from datetime import date
from pathlib import Path
from typing import Any

from evals.sentence_routing_retrieval_falsification.breadcrumb_normalize import (
    normalize_breadcrumb_artifact,
    write_records_jsonl,
)
from evals.sentence_routing_retrieval_falsification.breadcrumb_query_grader import (
    grade_natural_scenario,
    load_gold,
    merge_natural_benchmark_scenario,
    natural_retrieval_bundle,
)
from evals.sentence_routing_retrieval_falsification.breadcrumb_query_llm import (
    resolve_breadcrumb_query_llm_model,
    synthesize_answer_from_hit_context,
)
from src.agent.corpus_path_tools import (
    read_paths_from_tool_trace,
    unit_ids_from_query_session_memory_trace,
)
from src.agent.planner import (
    _planner_tools_responses,
    _resolve_planner_model,
    build_corpus_path_ref_index,
    make_tool_dispatcher,
    run_planning_turn_detailed,
)
from src.agent.planner_cache import load_or_build_planner_instructions
from src.agent.synthesis import _load_api_key
from src.bootstrap_env import load_dungeonmindbuddy_dotenv


def norm_rel_path(path: str) -> str:
    return path.strip().replace("\\", "/").lower().lstrip("./")


def paths_cover_substrings(paths: list[str], needles: list[str]) -> dict[str, Any]:
    """Return per-needle coverage against corpus-relative paths (substring match, lowercased)."""
    norm_paths = [norm_rel_path(p) for p in paths if str(p).strip()]
    details: list[dict[str, Any]] = []
    for needle in needles:
        n = str(needle).strip().lower().replace("\\", "/")
        matched = [p for p in norm_paths if n in p]
        details.append({"needle": needle, "covered": bool(matched), "matching_paths": matched[:8]})
    covered_count = sum(1 for d in details if d["covered"])
    return {
        "details": details,
        "recall": covered_count / max(len(needles), 1),
        "covered_count": covered_count,
        "needle_count": len(needles),
    }


def flatten_normalized_routes_from_hits(hits: list[dict[str, Any]]) -> list[str]:
    """Distinct route display strings from benchmark hits (order preserved)."""
    out: list[str] = []
    seen: set[str] = set()
    for h in hits:
        for r in h.get("routes") or []:
            if isinstance(r, dict):
                nr = str(r.get("normalized_route") or r.get("route") or "").strip()
            else:
                nr = str(r).strip()
            if not nr:
                continue
            low = nr.lower()
            if low in seen:
                continue
            seen.add(low)
            out.append(nr)
    return out


def _strip_markdown_json_fence(text: str) -> str:
    s = text.strip()
    if not s.startswith("```"):
        return s
    lines = s.splitlines()
    if len(lines) < 3:
        return s
    if not lines[-1].strip().startswith("```"):
        return s
    first = lines[0].strip().lower()
    if first not in ("```", "```json"):
        return s
    return "\n".join(lines[1:-1]).strip()


_SCHEMA_PLANNER_DISCOVERY_GOLD = "dmb_breadcrumb_query_planner_discovery_gold_v1"
_DEFAULT_PLANNER_DISCOVERY_GOLD = Path(
    "evals/sentence_routing_retrieval_falsification/gold/breadcrumb_query_planner_discovery_v1.json"
)


def load_planner_discovery_gold(path: Path) -> dict[str, dict[str, Any]]:
    """Map scenario id → ``expected_open_paths`` needles + optional notes."""
    data = json.loads(path.read_text(encoding="utf-8"))
    sch = str(data.get("schema") or "")
    if sch != _SCHEMA_PLANNER_DISCOVERY_GOLD:
        raise ValueError(
            f"unexpected planner discovery gold schema {sch!r} in {path}; "
            f"expected {_SCHEMA_PLANNER_DISCOVERY_GOLD!r}"
        )
    out: dict[str, dict[str, Any]] = {}
    for raw in data.get("scenarios") or []:
        if not isinstance(raw, dict):
            continue
        sid = str(raw.get("id") or "").strip()
        if not sid:
            continue
        needles = raw.get("expected_open_paths") or []
        if not isinstance(needles, list):
            raise ValueError(f"{path}: scenario {sid!r} expected_open_paths must be a list")
        out[sid] = {
            "expected_open_paths": [str(x).strip() for x in needles if str(x).strip()],
            "notes": raw.get("notes"),
        }
    return out


def query_session_memory_call_count(tool_trace: list[dict[str, Any]]) -> int:
    return sum(1 for row in tool_trace if str(row.get("tool", "")) == "query_session_memory")


def planner_message_from_final_text(final_text: str) -> tuple[str, str | None]:
    """Extract ``message`` from planner strict JSON; fallback to full text."""
    raw = _strip_markdown_json_fence(final_text or "")
    try:
        obj = json.loads(raw)
    except json.JSONDecodeError as exc:
        return (final_text or "").strip(), f"invalid_json:{exc}"
    if isinstance(obj, dict) and isinstance(obj.get("message"), str):
        return obj["message"].strip(), None
    return (final_text or "").strip(), "missing_message_key"


@contextmanager
def _session_memory_env_jsonl(path: Path | None):
    key = "DUNGEONMIND_SESSION_MEMORY_RECORDS_JSONL"
    prev = os.environ.get(key)
    if path is not None:
        os.environ[key] = str(path.resolve())
    try:
        yield
    finally:
        if path is None:
            return
        if prev is None:
            os.environ.pop(key, None)
        else:
            os.environ[key] = prev


def _resolve_records(
    *,
    records_jsonl: Path | None,
    breadcrumb_md: Path | None,
    corpus_root: Path | None,
    default_records_out: Path,
) -> tuple[list[dict[str, Any]], Path]:
    if records_jsonl is not None:
        p = records_jsonl.resolve()
        lines = p.read_text(encoding="utf-8").splitlines()
        records = [json.loads(line) for line in lines if line.strip()]
        return records, p
    if breadcrumb_md is not None and corpus_root is not None:
        art = breadcrumb_md.read_text(encoding="utf-8")
        root = corpus_root.resolve()
        rec_objs, _meta = normalize_breadcrumb_artifact(artifact_text=art, corpus_root=root)
        default_records_out.parent.mkdir(parents=True, exist_ok=True)
        write_records_jsonl(rec_objs, default_records_out)
        return [r.to_json_dict() for r in rec_objs], default_records_out.resolve()
    raise SystemExit("Provide --records-jsonl or (--breadcrumb-md and --corpus-root)")


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--records-jsonl", type=Path, default=None)
    parser.add_argument("--breadcrumb-md", type=Path, default=None)
    parser.add_argument("--corpus-root", type=Path, default=None)
    parser.add_argument(
        "--gold",
        type=Path,
        default=Path("evals/sentence_routing_retrieval_falsification/gold/breadcrumb_query_natural_v1.json"),
    )
    parser.add_argument(
        "--output",
        type=Path,
        default=None,
        help="Report JSON path (default: artifacts/runs/<today>/breadcrumb_query_planner_discovery_report.json)",
    )
    parser.add_argument(
        "--cache-root",
        type=Path,
        default=None,
        help="Planner instruction cache root (default: repo out/planner_eval_cache)",
    )
    parser.add_argument("--planner-model", type=str, default=None, help="OpenAI model id for planner turn")
    parser.add_argument(
        "--breadcrumb-llm-model",
        type=str,
        default=None,
        help="Model for benchmark-arm synthesis (default: resolve_breadcrumb_query_llm_model)",
    )
    parser.add_argument(
        "--skip-benchmark-llm",
        action="store_true",
        help="Do not call synthesize_answer_from_hit_context; benchmark arm uses retrieval-only grading",
    )
    parser.add_argument(
        "--scenario-ids",
        type=str,
        default="",
        help="Comma-separated scenario ids (default: all gold scenarios)",
    )
    parser.add_argument(
        "--planner-session-memory-records",
        type=Path,
        default=None,
        help=(
            "If set, exports DUNGEONMIND_SESSION_MEMORY_RECORDS_JSONL for the planner process "
            "so query_session_memory is available (ablation)."
        ),
    )
    parser.add_argument(
        "--compare-hit-route-count",
        type=int,
        default=24,
        help="Max distinct benchmark hit routes to compare against planner reads (default: 24)",
    )
    parser.add_argument(
        "--planner-discovery-gold",
        type=Path,
        default=_DEFAULT_PLANNER_DISCOVERY_GOLD,
        help=(
            "Gold with expected_open_paths per scenario (schema "
            f"{_SCHEMA_PLANNER_DISCOVERY_GOLD}). If the default file is missing, discovery-path scoring is skipped."
        ),
    )
    args = parser.parse_args()

    if args.planner_session_memory_records is not None:
        smchk = Path(args.planner_session_memory_records).resolve()
        if not smchk.is_file():
            raise SystemExit(f"--planner-session-memory-records not found or not a file: {smchk}")

    suite_dir = Path(__file__).resolve().parent
    default_out = (
        suite_dir / "artifacts" / "runs" / str(date.today()) / "breadcrumb_query_planner_discovery_report.json"
    )
    out_path = args.output or default_out
    default_records_written = out_path.with_suffix(".records.jsonl")

    records, records_path = _resolve_records(
        records_jsonl=args.records_jsonl,
        breadcrumb_md=args.breadcrumb_md,
        corpus_root=args.corpus_root,
        default_records_out=default_records_written,
    )

    if args.corpus_root is None:
        raise SystemExit("--corpus-root is required for planner corpus reads")
    corpus_path = Path(args.corpus_root).resolve()

    gold = load_gold(Path(args.gold).resolve())
    sch = str(gold.get("schema") or "")
    if sch != "dmb_breadcrumb_query_natural_gold_v1":
        raise SystemExit(f"This harness expects dmb_breadcrumb_query_natural_gold_v1; got {sch!r}")

    pd_path = args.planner_discovery_gold.expanduser().resolve()
    planner_discovery_by_id: dict[str, dict[str, Any]] = {}
    if pd_path.is_file():
        planner_discovery_by_id = load_planner_discovery_gold(pd_path)
    elif pd_path != _DEFAULT_PLANNER_DISCOVERY_GOLD.expanduser().resolve():
        raise SystemExit(f"--planner-discovery-gold not found: {pd_path}")

    filter_ids = {s.strip() for s in args.scenario_ids.split(",") if s.strip()}

    load_dungeonmindbuddy_dotenv()
    if not (_load_api_key() or "").strip():
        raise SystemExit(
            "OPENAI_API_KEY missing after loading .env / .env.development "
            "(see src/bootstrap_env.py). Required for planner and optional benchmark LLM."
        )

    from openai import OpenAI

    client = OpenAI()
    planner_model = _resolve_planner_model(args.planner_model)
    breadcrumb_llm_model = (args.breadcrumb_llm_model or "").strip() or resolve_breadcrumb_query_llm_model()

    aggregate_benchmark_llm_usd = 0.0
    aggregate_planner_usd = 0.0
    aggregate_statblock_usd = 0.0
    rows: list[dict[str, Any]] = []

    cache_root = Path(args.cache_root).resolve() if args.cache_root else None

    sm_path = Path(args.planner_session_memory_records).resolve() if args.planner_session_memory_records else None

    with _session_memory_env_jsonl(sm_path):
        instructions, corpus_fp = load_or_build_planner_instructions(corpus_path, cache_root=cache_root)
        tools = _planner_tools_responses()
        ref_index = build_corpus_path_ref_index(corpus_path)

        for scenario in gold.get("scenarios") or []:
            sid = str(scenario.get("id") or "").strip()
            if filter_ids and sid not in filter_ids:
                continue

            scen = merge_natural_benchmark_scenario(dict(scenario), gold)

            bundle = natural_retrieval_bundle(records=records, scenario=scen)
            result_obj, hit_ctx = bundle
            benchmark_hits = list(result_obj.hits)

            benchmark_llm_text: str | None = None
            benchmark_llm_cost = 0.0
            benchmark_llm_usage: dict[str, Any] = {}
            if args.skip_benchmark_llm:
                benchmark_row = grade_natural_scenario(
                    records=records,
                    scenario=scen,
                    llm_answer=None,
                    cached_retrieval=bundle,
                )
            else:
                benchmark_llm_text, benchmark_llm_cost, benchmark_llm_usage = synthesize_answer_from_hit_context(
                    question=str(scen["question"]),
                    hit_context=hit_ctx,
                    model=breadcrumb_llm_model,
                )
                aggregate_benchmark_llm_usd += benchmark_llm_cost
                benchmark_row = grade_natural_scenario(
                    records=records,
                    scenario=scen,
                    llm_answer=benchmark_llm_text,
                    cached_retrieval=bundle,
                )

            hit_routes = flatten_normalized_routes_from_hits(benchmark_hits)[
                : max(1, int(args.compare_hit_route_count))
            ]
            expect_routes = [str(x) for x in (scen.get("expect_route_substrings") or [])]

            tool_cost_sink: list[dict[str, Any]] = []
            dispatch = make_tool_dispatcher(
                corpus_path,
                client,
                planner_model,
                statblock_stub=None,
                tool_cost_sink=tool_cost_sink,
                corpus_path_ref_index=ref_index,
                session_memory_records=records if sm_path is not None else None,
            )

            user_line = str(scen["question"]).strip()
            detail = run_planning_turn_detailed(
                client=client,
                model_id=planner_model,
                instructions=instructions,
                tools=tools,
                corpus_path=corpus_path,
                user_line=user_line,
                previous_response_id=None,
                dispatch_tool=dispatch,
                telemetry_context={
                    "scenario_id": sid,
                    "suite": "breadcrumb_query_planner_discovery",
                    "corpus_fingerprint": corpus_fp,
                },
                corpus_path_ref_index=ref_index,
            )
            statblock_usd = sum(float(x.get("total_usd", 0) or 0) for x in tool_cost_sink)
            tc = dict(detail.telemetry_cost or {})
            planner_usd = float(tc.get("planner_estimated_cost_usd", 0) or 0)
            tc["statblock_tool_estimated_cost_usd"] = round(statblock_usd, 6)
            tc["scenario_estimated_cost_usd"] = round(planner_usd + statblock_usd, 6)
            detail = replace(detail, telemetry_cost=tc)
            scenario_planner_usd = float(tc["scenario_estimated_cost_usd"])
            aggregate_planner_usd += planner_usd
            aggregate_statblock_usd += statblock_usd

            read_paths = read_paths_from_tool_trace(detail.tool_trace)
            memory_unit_ids = unit_ids_from_query_session_memory_trace(detail.tool_trace)
            qsm_calls = query_session_memory_call_count(detail.tool_trace)

            pd_spec = planner_discovery_by_id.get(sid, {})
            open_needles: list[str] = list(pd_spec.get("expected_open_paths") or [])
            open_cov: dict[str, Any] | None = (
                paths_cover_substrings(read_paths, open_needles) if open_needles else None
            )
            open_full: bool | None = (
                bool(open_cov and float(open_cov["recall"]) >= 1.0 - 1e-12) if open_cov else None
            )

            planner_msg, planner_parse_err = planner_message_from_final_text(detail.final_text or "")
            planner_grade = grade_natural_scenario(
                records=records,
                scenario=scen,
                llm_answer=planner_msg,
                cached_retrieval=bundle,
            )

            discovery = {
                "planner_read_paths": read_paths,
                "planner_query_session_memory_unit_ids": memory_unit_ids,
                "query_session_memory_call_count": qsm_calls,
                "expected_open_paths": open_needles,
                "expected_open_paths_coverage": open_cov,
                "expected_open_paths_full_coverage": open_full,
                "expect_route_substrings_coverage_on_reads": paths_cover_substrings(read_paths, expect_routes),
                "benchmark_hit_routes_compared": hit_routes,
                "benchmark_hit_route_coverage_on_reads": paths_cover_substrings(read_paths, hit_routes),
                "planner_final_text_parse_error": planner_parse_err,
                "planner_hit_tool_round_limit": detail.hit_tool_round_limit,
            }

            rows.append(
                {
                    "scenario_id": sid,
                    "question": user_line,
                    "benchmark_retrieval_ok": benchmark_row.get("ok"),
                    "benchmark_violations": benchmark_row.get("violations"),
                    "benchmark_llm_skipped": bool(args.skip_benchmark_llm),
                    "benchmark_llm_model": None if args.skip_benchmark_llm else breadcrumb_llm_model,
                    "benchmark_llm_cost_usd": None if args.skip_benchmark_llm else benchmark_llm_cost,
                    "benchmark_llm_usage": benchmark_llm_usage if not args.skip_benchmark_llm else {},
                    "benchmark_grade": {
                        k: benchmark_row[k]
                        for k in (
                            "llm_semantic_verdict",
                            "llm_context_support_ratio",
                            "context_support_ratio",
                            "semantic_verdict",
                            "hit_count",
                            "failure_surface",
                            "llm_failure_surface",
                        )
                        if k in benchmark_row
                    },
                    "planner_scenario_estimated_cost_usd": scenario_planner_usd,
                    "planner_telemetry_cost": tc,
                    "planner_discovery": discovery,
                    "planner_grade_vs_benchmark_retrieval": {
                        k: planner_grade[k]
                        for k in (
                            "ok",
                            "violations",
                            "llm_semantic_verdict",
                            "llm_context_support_ratio",
                            "failure_surface",
                            "llm_failure_surface",
                        )
                        if k in planner_grade
                    },
                    "planner_message_preview": planner_msg[:1200],
                    "benchmark_llm_answer_preview": (
                        None if args.skip_benchmark_llm else (benchmark_llm_text or "")[:1200]
                    ),
                }
            )

    last_mirror = suite_dir / "artifacts" / "last_breadcrumb_query_planner_discovery_report.json"

    open_recalls = [
        float(r["planner_discovery"]["expected_open_paths_coverage"]["recall"])
        for r in rows
        if r["planner_discovery"].get("expected_open_paths_coverage") is not None
    ]
    open_full_n = sum(
        1
        for r in rows
        if r["planner_discovery"].get("expected_open_paths_full_coverage") is True
    )
    qsm_total_calls = sum(
        int(r["planner_discovery"].get("query_session_memory_call_count") or 0) for r in rows
    )
    qsm_scenarios = sum(
        1 for r in rows if int(r["planner_discovery"].get("query_session_memory_call_count") or 0) > 0
    )

    report: dict[str, Any] = {
        "harness": "breadcrumb_query_planner_discovery_v1",
        "records_source": str(records_path),
        "gold": str(Path(args.gold).resolve()),
        "planner_discovery_gold": str(pd_path) if pd_path.is_file() else None,
        "corpus_root": str(corpus_path),
        "corpus_fingerprint": corpus_fp,
        "planner_model": planner_model,
        "planner_session_memory_jsonl": str(sm_path) if sm_path else None,
        "benchmark_llm_model": None if args.skip_benchmark_llm else breadcrumb_llm_model,
        "skip_benchmark_llm": bool(args.skip_benchmark_llm),
        "compare_hit_route_count": int(args.compare_hit_route_count),
        "aggregate_benchmark_llm_cost_usd": round(aggregate_benchmark_llm_usd, 6),
        "aggregate_planner_cost_usd": round(aggregate_planner_usd, 6),
        "aggregate_statblock_tool_cost_usd": round(aggregate_statblock_usd, 6),
        "aggregate_scenario_planner_cost_usd": round(aggregate_planner_usd + aggregate_statblock_usd, 6),
        "planner_discovery_aggregate": {
            "expected_open_paths_recall_mean": (
                round(sum(open_recalls) / len(open_recalls), 6) if open_recalls else None
            ),
            "expected_open_paths_full_coverage_scenarios": open_full_n,
            "expected_open_paths_scored_scenarios": len(open_recalls),
            "query_session_memory_total_calls": qsm_total_calls,
            "query_session_memory_scenarios_with_calls": qsm_scenarios,
        },
        "results": rows,
    }

    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(json.dumps(report, indent=2), encoding="utf-8")
    last_mirror.parent.mkdir(parents=True, exist_ok=True)
    last_mirror.write_text(json.dumps(report, indent=2), encoding="utf-8")

    print(
        json.dumps(
            {
                "wrote": str(out_path),
                "mirror": str(last_mirror),
                "scenario_count": len(rows),
                "aggregate_benchmark_llm_cost_usd": report["aggregate_benchmark_llm_cost_usd"],
                "aggregate_scenario_planner_cost_usd": report["aggregate_scenario_planner_cost_usd"],
                "planner_discovery_aggregate": report["planner_discovery_aggregate"],
            },
            indent=2,
        )
    )


if __name__ == "__main__":
    main()
