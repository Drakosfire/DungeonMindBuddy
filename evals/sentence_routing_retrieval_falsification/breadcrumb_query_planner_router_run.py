#!/usr/bin/env python3
"""Planner retrieval-router benchmark runner (router-first, escalate on insufficient).

For each scenario in ``breadcrumb_query_natural_v1.json`` (or any compatible
``dmb_breadcrumb_query_natural_gold_v1`` file):

1. Run :func:`src.agent.planner_retrieval_router.run_retrieval_first_decision`
   over the same JSONL the benchmark grader uses.
2. **Answer-now** path: synthesize a grounded answer from the retrieved hit
   context with the existing harness LLM
   (:func:`evals.sentence_routing_retrieval_falsification.breadcrumb_query_llm.synthesize_answer_from_hit_context`)
   and grade with :func:`grade_natural_scenario`.
3. **Escalation** path: run a full planner turn via
   :func:`src.agent.planner.run_planning_turn_detailed`, extract the
   ``message`` from the strict planner JSON envelope, and grade that text.

Outputs include:

* per-scenario router decision + machine-readable failure reasons,
* ``answer_now`` vs ``escalated`` cohort splits,
* per-scenario cost split (router LLM synthesis vs planner escalation), and
* aggregate cost-as-signal totals comparable to ``breadcrumb_query_run`` and
  ``breadcrumb_query_planner_discovery_run``.

Default artifact paths:
- ``artifacts/runs/<today>/breadcrumb_query_planner_router_report.json``
- mirrored to ``artifacts/last_breadcrumb_query_planner_router_report.json``

Examples::

  uv run python -m evals.sentence_routing_retrieval_falsification.breadcrumb_query_planner_router_run \\
    --records-jsonl evals/sentence_routing_retrieval_falsification/artifacts/runs/<date>/session20.jsonl \\
    --corpus-root corpus/eldyrwild-markdown \\
    --gold evals/sentence_routing_retrieval_falsification/gold/breadcrumb_query_natural_v1.json

  # Standalone router (no escalation): caps cost; useful for threshold tuning.
  uv run python -m evals.sentence_routing_retrieval_falsification.breadcrumb_query_planner_router_run \\
    --records-jsonl ... --corpus-root corpus/eldyrwild-markdown --no-escalation
"""

from __future__ import annotations

import argparse
import json
from contextlib import contextmanager
from dataclasses import replace
from datetime import date
from pathlib import Path
from typing import Any

from evals.sentence_routing_retrieval_falsification.breadcrumb_normalize import (
    normalize_breadcrumb_artifact,
    write_records_jsonl,
)
from evals.sentence_routing_retrieval_falsification.breadcrumb_natural_scoring import (
    build_hit_context_text,
    index_records_by_unit_id,
)
from evals.sentence_routing_retrieval_falsification.breadcrumb_query_grader import (
    grade_natural_scenario,
    load_gold,
)
from evals.sentence_routing_retrieval_falsification.breadcrumb_query_llm import (
    resolve_breadcrumb_query_llm_model,
    synthesize_answer_from_hit_context,
)
from evals.sentence_routing_retrieval_falsification.breadcrumb_query_planner_discovery_run import (
    _session_memory_env_jsonl,
    planner_message_from_final_text,
    query_session_memory_call_count,
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
from src.agent.planner_retrieval_router import (
    DECISION_ANSWER_NOW,
    DECISION_NEED_MORE_CONTEXT,
    SufficiencyConfig,
    run_retrieval_first_decision,
)
from src.agent.planner_telemetry import router_telemetry_row
from src.agent.synthesis import _load_api_key
from src.bootstrap_env import load_dungeonmindbuddy_dotenv


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


def _build_scenario(
    scenario: dict[str, Any],
    *,
    default_campaign: str,
    default_spec: dict[str, Any],
) -> dict[str, Any]:
    scen = dict(scenario)
    scen["campaign_id"] = str(scen.get("campaign_id") or default_campaign)
    merged_spec = {**default_spec, **(scen.get("query_spec") or {})}
    merged_spec["query"] = str(scen["question"])
    scen["query_spec"] = merged_spec
    return scen


def _config_from_args(args: argparse.Namespace) -> SufficiencyConfig:
    return SufficiencyConfig(
        min_matched_records=int(args.cfg_min_matched),
        min_hits=int(args.cfg_min_hits),
        min_top_hit_score=int(args.cfg_min_top_hit_score),
        min_route_anchor_recall=float(args.cfg_min_route_recall),
        min_context_density=float(args.cfg_min_context_density),
        max_expansion_fill_ratio=float(args.cfg_max_expansion_fill),
    )


@contextmanager
def _maybe_session_memory(path: Path | None):
    """Mirror discovery harness env helper for ``query_session_memory`` tool wiring."""
    with _session_memory_env_jsonl(path):
        yield


def _safe_float(x: Any) -> float:
    try:
        return float(x or 0)
    except (TypeError, ValueError):
        return 0.0


def _summarize_planner_tool_trace(
    tool_trace: list[dict[str, Any]],
    *,
    max_excerpt_chars: int = 1200,
) -> list[dict[str, Any]]:
    """Compact tool rows for canvas / handoff (paths + truncated tool output)."""
    out: list[dict[str, Any]] = []
    for row in tool_trace or []:
        if not isinstance(row, dict):
            continue
        tool = str(row.get("tool") or "")
        args = row.get("arguments") or {}
        path = ""
        if isinstance(args, dict):
            path = str(args.get("path") or "").strip()
        excerpt = str(row.get("output_excerpt") or "")
        if len(excerpt) > max_excerpt_chars:
            oc = row.get("output_chars")
            excerpt = (
                excerpt[:max_excerpt_chars]
                + f"\n...[truncated, total_output_chars={oc}]"
            )
        out.append(
            {
                "tool": tool,
                "path": path,
                "output_preview": excerpt,
            }
        )
    return out


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
        help="Report JSON path (default: artifacts/runs/<today>/breadcrumb_query_planner_router_report.json)",
    )
    parser.add_argument("--planner-model", type=str, default=None)
    parser.add_argument(
        "--breadcrumb-llm-model",
        type=str,
        default=None,
        help="Model for hit-context synthesis (answer_now path).",
    )
    parser.add_argument(
        "--no-escalation",
        action="store_true",
        help="Do not run a planner turn even when the router asks for more context.",
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
            "If set, exports DUNGEONMIND_SESSION_MEMORY_RECORDS_JSONL for the planner process so "
            "query_session_memory is registered when the router escalates (ablation)."
        ),
    )
    parser.add_argument(
        "--cache-root",
        type=Path,
        default=None,
        help="Planner instruction cache root (default: repo out/planner_eval_cache)",
    )
    parser.add_argument(
        "--required-route-anchors-from-gold",
        action="store_true",
        help=(
            "Treat each scenario's expect_route_substrings as router-required anchors. Off by default "
            "to avoid leaking grader gold into the sufficiency policy."
        ),
    )
    parser.add_argument("--cfg-min-matched", type=int, default=2)
    parser.add_argument("--cfg-min-hits", type=int, default=3)
    parser.add_argument("--cfg-min-top-hit-score", type=int, default=3)
    parser.add_argument("--cfg-min-route-recall", type=float, default=1.0)
    parser.add_argument("--cfg-min-context-density", type=float, default=0.5)
    parser.add_argument("--cfg-max-expansion-fill", type=float, default=1.0)
    args = parser.parse_args()

    if args.planner_session_memory_records is not None:
        smchk = Path(args.planner_session_memory_records).resolve()
        if not smchk.is_file():
            raise SystemExit(f"--planner-session-memory-records not found or not a file: {smchk}")

    suite_dir = Path(__file__).resolve().parent
    default_out = (
        suite_dir / "artifacts" / "runs" / str(date.today()) / "breadcrumb_query_planner_router_report.json"
    )
    out_path = args.output or default_out
    default_records_written = out_path.with_suffix(".records.jsonl")

    records, records_path = _resolve_records(
        records_jsonl=args.records_jsonl,
        breadcrumb_md=args.breadcrumb_md,
        corpus_root=args.corpus_root,
        default_records_out=default_records_written,
    )

    if args.corpus_root is None and not args.no_escalation:
        raise SystemExit("--corpus-root is required to run planner escalation; pass --no-escalation otherwise")

    gold = load_gold(Path(args.gold).resolve())
    sch = str(gold.get("schema") or "")
    if sch != "dmb_breadcrumb_query_natural_gold_v1":
        raise SystemExit(f"This harness expects dmb_breadcrumb_query_natural_gold_v1; got {sch!r}")

    filter_ids = {s.strip() for s in args.scenario_ids.split(",") if s.strip()}

    load_dungeonmindbuddy_dotenv()
    if not (_load_api_key() or "").strip():
        raise SystemExit(
            "OPENAI_API_KEY missing after loading .env / .env.development "
            "(see src/bootstrap_env.py). Required for hit-context synthesis and planner escalation."
        )

    from openai import OpenAI

    client = OpenAI()
    planner_model = _resolve_planner_model(args.planner_model)
    breadcrumb_llm_model = (args.breadcrumb_llm_model or "").strip() or resolve_breadcrumb_query_llm_model()
    config = _config_from_args(args)

    default_campaign = str(gold.get("campaign_id") or "")
    default_spec = gold.get("default_query_spec") or {}

    by_unit = index_records_by_unit_id(records)

    rows: list[dict[str, Any]] = []
    aggregate_router_synth_usd = 0.0
    aggregate_planner_usd = 0.0
    aggregate_statblock_usd = 0.0
    decision_counts: dict[str, int] = {DECISION_ANSWER_NOW: 0, DECISION_NEED_MORE_CONTEXT: 0}
    failure_reason_counts: dict[str, int] = {}
    answer_now_pass_count = 0
    escalated_pass_count = 0

    cache_root = Path(args.cache_root).resolve() if args.cache_root else None
    sm_path = (
        Path(args.planner_session_memory_records).resolve()
        if args.planner_session_memory_records
        else None
    )
    corpus_path = Path(args.corpus_root).resolve() if args.corpus_root else None

    instructions: str | None = None
    corpus_fp: str | None = None
    tools: list[dict[str, Any]] = []
    ref_index: dict[str, str] = {}
    if not args.no_escalation and corpus_path is not None:
        with _maybe_session_memory(sm_path):
            instructions, corpus_fp = load_or_build_planner_instructions(corpus_path, cache_root=cache_root)
            tools = _planner_tools_responses()
            ref_index = build_corpus_path_ref_index(corpus_path)

    for scenario in gold.get("scenarios") or []:
        sid = str(scenario.get("id") or "").strip()
        if filter_ids and sid not in filter_ids:
            continue

        scen = _build_scenario(scenario, default_campaign=default_campaign, default_spec=default_spec)
        question = str(scen["question"]).strip()
        required_anchors: list[str] = []
        if args.required_route_anchors_from_gold:
            required_anchors = [str(x) for x in (scen.get("expect_route_substrings") or [])]

        decision = run_retrieval_first_decision(
            query=question,
            records=records,
            campaign_id=str(scen.get("campaign_id") or default_campaign),
            query_spec=dict(scen.get("query_spec") or {}),
            config=config,
            required_route_anchors=required_anchors,
        )
        decision_counts[decision.decision] = decision_counts.get(decision.decision, 0) + 1
        for r in decision.failure_reasons:
            failure_reason_counts[r] = failure_reason_counts.get(r, 0) + 1

        # Recover the bundle (CandidateQueryResult lookalike + hit context text) for grading.
        hit_context = build_hit_context_text(decision.evidence.hits, by_unit)
        bundle_for_grade = (_FakeCandidateResult(decision.evidence.hits, decision.evidence.trace, scen.get("campaign_id") or default_campaign, question), hit_context)

        # Phase: router answer-now path.
        router_synth_text: str | None = None
        router_synth_cost_usd = 0.0
        router_synth_usage: dict[str, int] = {}
        router_grade: dict[str, Any] | None = None
        router_parse_err: str | None = None

        if decision.decision == DECISION_ANSWER_NOW:
            router_synth_text, router_synth_cost_usd, router_synth_usage = synthesize_answer_from_hit_context(
                question=question,
                hit_context=hit_context,
                model=breadcrumb_llm_model,
            )
            aggregate_router_synth_usd += router_synth_cost_usd
            router_grade = grade_natural_scenario(
                records=records,
                scenario=scen,
                llm_answer=router_synth_text,
                cached_retrieval=bundle_for_grade,
            )
            if router_grade.get("ok"):
                answer_now_pass_count += 1

        # Phase: escalation path.
        escalation_run: dict[str, Any] | None = None
        if decision.decision == DECISION_NEED_MORE_CONTEXT and not args.no_escalation:
            assert corpus_path is not None and instructions is not None  # checked above
            with _maybe_session_memory(sm_path):
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
                detail = run_planning_turn_detailed(
                    client=client,
                    model_id=planner_model,
                    instructions=instructions,
                    tools=tools,
                    corpus_path=corpus_path,
                    user_line=question,
                    previous_response_id=None,
                    dispatch_tool=dispatch,
                    telemetry_context={
                        "scenario_id": sid,
                        "suite": "breadcrumb_query_planner_router",
                        "router_decision": decision.decision,
                        "router_failure_reasons": list(decision.failure_reasons),
                        "corpus_fingerprint": corpus_fp,
                    },
                    corpus_path_ref_index=ref_index,
                )
            statblock_usd = sum(_safe_float(x.get("total_usd")) for x in tool_cost_sink)
            tc = dict(detail.telemetry_cost or {})
            planner_usd = _safe_float(tc.get("planner_estimated_cost_usd"))
            tc["statblock_tool_estimated_cost_usd"] = round(statblock_usd, 6)
            tc["scenario_estimated_cost_usd"] = round(planner_usd + statblock_usd, 6)
            detail = replace(detail, telemetry_cost=tc)
            aggregate_planner_usd += planner_usd
            aggregate_statblock_usd += statblock_usd

            planner_msg, planner_parse_err = planner_message_from_final_text(detail.final_text or "")
            planner_grade = grade_natural_scenario(
                records=records,
                scenario=scen,
                llm_answer=planner_msg,
                cached_retrieval=bundle_for_grade,
            )
            if planner_grade.get("ok"):
                escalated_pass_count += 1
            escalation_run = {
                "planner_message_preview": planner_msg[:1200],
                "planner_final_text_parse_error": planner_parse_err,
                "planner_read_paths": read_paths_from_tool_trace(detail.tool_trace),
                "planner_tool_trace": _summarize_planner_tool_trace(detail.tool_trace),
                "planner_query_session_memory_unit_ids": unit_ids_from_query_session_memory_trace(
                    detail.tool_trace
                ),
                "query_session_memory_call_count": query_session_memory_call_count(detail.tool_trace),
                "planner_telemetry_cost": tc,
                "planner_grade": {
                    k: planner_grade[k]
                    for k in (
                        "ok",
                        "violations",
                        "llm_semantic_verdict",
                        "llm_context_support_ratio",
                        "context_support_ratio",
                        "semantic_verdict",
                        "failure_surface",
                        "llm_failure_surface",
                        "hit_count",
                    )
                    if k in planner_grade
                },
                "planner_hit_tool_round_limit": detail.hit_tool_round_limit,
            }

        decision_payload = decision.as_json_dict()

        escalation_planner_usd = 0.0
        escalation_statblock_usd = 0.0
        if (
            escalation_run
            and isinstance(escalation_run.get("planner_telemetry_cost"), dict)
        ):
            etc = escalation_run["planner_telemetry_cost"]
            escalation_planner_usd = _safe_float(etc.get("planner_estimated_cost_usd"))
            escalation_statblock_usd = _safe_float(etc.get("statblock_tool_estimated_cost_usd"))
        scenario_telemetry_cost = router_telemetry_row(
            decision=decision.decision,
            failure_reasons=list(decision.failure_reasons),
            confidence_features=decision.confidence_features,
            router_synth_cost_usd=router_synth_cost_usd,
            planner_estimated_cost_usd=escalation_planner_usd,
            statblock_tool_estimated_cost_usd=escalation_statblock_usd,
            escalated=bool(escalation_run is not None),
        )
        scenario_total_cost_usd = scenario_telemetry_cost["scenario_estimated_cost_usd"]

        rows.append(
            {
                "scenario_id": sid,
                "question": question,
                "router_decision": decision.decision,
                "router_failure_reasons": list(decision.failure_reasons),
                "router_confidence_features": decision.confidence_features,
                "scenario_telemetry_cost": scenario_telemetry_cost,
                "router_evidence_summary": {
                    "matched_records": decision.evidence.matched_records,
                    "returned_hits": decision.evidence.returned_hits,
                    "top_hit_score": decision.evidence.top_hit_score,
                    "route_anchor_recall": decision.evidence.route_anchor_recall,
                    "context_density": decision.evidence.context_density,
                    "expansion_fill_ratio": decision.evidence.expansion_fill_ratio,
                    "why_matched_tokens": list(decision.evidence.why_matched_tokens),
                },
                "router_required_route_anchors": list(required_anchors),
                "router_decision_payload": decision_payload,
                "router_synth_model": (
                    breadcrumb_llm_model if decision.decision == DECISION_ANSWER_NOW else None
                ),
                "router_synth_cost_usd": (
                    router_synth_cost_usd if decision.decision == DECISION_ANSWER_NOW else None
                ),
                "router_synth_usage": (
                    router_synth_usage if decision.decision == DECISION_ANSWER_NOW else {}
                ),
                "router_synth_answer_preview": (
                    (router_synth_text or "")[:1200]
                    if decision.decision == DECISION_ANSWER_NOW
                    else None
                ),
                "router_grade": (
                    {
                        k: router_grade[k]
                        for k in (
                            "ok",
                            "violations",
                            "llm_semantic_verdict",
                            "llm_context_support_ratio",
                            "context_support_ratio",
                            "semantic_verdict",
                            "failure_surface",
                            "llm_failure_surface",
                            "hit_count",
                        )
                        if k in router_grade
                    }
                    if router_grade is not None
                    else None
                ),
                "escalation_run": escalation_run,
                "escalation_skipped": bool(args.no_escalation and decision.decision == DECISION_NEED_MORE_CONTEXT),
                "scenario_estimated_cost_usd": round(scenario_total_cost_usd, 6),
            }
        )

    cohort_pass_count = answer_now_pass_count + escalated_pass_count
    cohort_total = len(rows)

    report: dict[str, Any] = {
        "harness": "breadcrumb_query_planner_router_v1",
        "records_source": str(records_path),
        "gold": str(Path(args.gold).resolve()),
        "corpus_root": str(corpus_path) if corpus_path else None,
        "corpus_fingerprint": corpus_fp,
        "planner_model": planner_model,
        "router_synth_model": breadcrumb_llm_model,
        "no_escalation": bool(args.no_escalation),
        "planner_session_memory_jsonl": str(sm_path) if sm_path else None,
        "router_config": {
            "min_matched_records": int(config.min_matched_records),
            "min_hits": int(config.min_hits),
            "min_top_hit_score": int(config.min_top_hit_score),
            "min_route_anchor_recall": float(config.min_route_anchor_recall),
            "min_context_density": float(config.min_context_density),
            "max_expansion_fill_ratio": float(config.max_expansion_fill_ratio),
            "required_route_anchors_from_gold": bool(args.required_route_anchors_from_gold),
        },
        "decision_counts": decision_counts,
        "failure_reason_counts": failure_reason_counts,
        "cohort_pass_count": cohort_pass_count,
        "cohort_pass_count_answer_now": answer_now_pass_count,
        "cohort_pass_count_escalated": escalated_pass_count,
        "cohort_total": cohort_total,
        "aggregate_router_synth_cost_usd": round(aggregate_router_synth_usd, 6),
        "aggregate_planner_cost_usd": round(aggregate_planner_usd, 6),
        "aggregate_statblock_tool_cost_usd": round(aggregate_statblock_usd, 6),
        "aggregate_scenario_cost_usd": round(
            aggregate_router_synth_usd + aggregate_planner_usd + aggregate_statblock_usd, 6
        ),
        "results": rows,
    }

    last_mirror = suite_dir / "artifacts" / "last_breadcrumb_query_planner_router_report.json"
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(json.dumps(report, indent=2), encoding="utf-8")
    last_mirror.parent.mkdir(parents=True, exist_ok=True)
    last_mirror.write_text(json.dumps(report, indent=2), encoding="utf-8")

    print(
        json.dumps(
            {
                "wrote": str(out_path),
                "mirror": str(last_mirror),
                "scenario_count": cohort_total,
                "decision_counts": decision_counts,
                "cohort_pass_count": cohort_pass_count,
                "cohort_pass_count_answer_now": answer_now_pass_count,
                "cohort_pass_count_escalated": escalated_pass_count,
                "aggregate_router_synth_cost_usd": report["aggregate_router_synth_cost_usd"],
                "aggregate_planner_cost_usd": report["aggregate_planner_cost_usd"],
                "aggregate_scenario_cost_usd": report["aggregate_scenario_cost_usd"],
            },
            indent=2,
        )
    )


class _FakeCandidateResult:
    """Minimal duck-typed stand-in for ``CandidateQueryResult`` used to feed
    :func:`grade_natural_scenario` via ``cached_retrieval`` without re-running
    retrieval. The grader only reads ``hits`` and serializes via
    ``as_json_dict`` / accesses ``trace``; it never inspects the schema string.
    """

    def __init__(self, hits: list[dict[str, Any]], trace: dict[str, Any], campaign_id: str, query: str) -> None:
        self.hits = list(hits)
        self.trace = dict(trace or {})
        self.campaign_id = str(campaign_id)
        self.query = str(query)
        self.schema = "dmb_query_session_memory_result_v1"
        self.contract = "candidate_mode_v1"

    def as_json_dict(self) -> dict[str, Any]:
        return {
            "schema": self.schema,
            "contract": self.contract,
            "campaign_id": self.campaign_id,
            "query": self.query,
            "hits": list(self.hits),
            "trace": dict(self.trace),
        }


if __name__ == "__main__":
    main()
