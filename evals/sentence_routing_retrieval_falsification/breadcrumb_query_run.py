#!/usr/bin/env python3
"""Run session-memory query grading (JSONL records + gold scenarios).

Gold schema ``dmb_breadcrumb_query_natural_gold_v1`` always runs OpenAI answer synthesis
over retrieved hit context, then grades LLM-backed gates (requires ``OPENAI_API_KEY``).

Writes a default artifact under ``artifacts/runs/<date>/`` unless ``--output`` is set.

Examples:

  uv run python -m evals.sentence_routing_retrieval_falsification.breadcrumb_query_run \\
    --breadcrumb-md evals/sentence_routing_retrieval_falsification/manual_labels/Session\\ 20\\ -\\ Recap.breadcrumbed.md \\
    --corpus-root corpus/eldyrwild-markdown

  uv run python -m evals.sentence_routing_retrieval_falsification.breadcrumb_query_run \\
    --records-jsonl /tmp/session20.jsonl \\
    --gold evals/sentence_routing_retrieval_falsification/gold/breadcrumb_query_closed_loop_v1.json

  # Ingestion loop: normalize → optional repair adjudication → JSONL → query grade + sentinel score

  uv run python -m evals.sentence_routing_retrieval_falsification.breadcrumb_query_run \\
    --breadcrumb-md evals/sentence_routing_retrieval_falsification/manual_labels/Session\\ 20\\ -\\ Recap.breadcrumbed.md \\
    --corpus-root corpus/eldyrwild-markdown \\
    --repair-adjudicate \\
    --tagging-sentinel-json evals/sentence_routing_retrieval_falsification/gold/breadcrumb_tagging_sentinels_session20.json \\
    --gold evals/sentence_routing_retrieval_falsification/gold/breadcrumb_query_natural_v1.json
"""

from __future__ import annotations

import argparse
import json
import os
from datetime import date
from pathlib import Path
from typing import Any

from evals.sentence_routing_retrieval_falsification.cursor_canvas_paths import default_cursor_canvas_path
from evals.sentence_routing_retrieval_falsification.breadcrumb_normalize import (
    NormalizedRecord,
    normalize_breadcrumb_artifact,
    write_records_jsonl,
)
from evals.sentence_routing_retrieval_falsification.breadcrumb_smoke import (
    parse_frontmatter_and_body,
)
from evals.sentence_routing_retrieval_falsification.breadcrumb_query_canvas_payload import (
    build_payload as build_canvas_payload,
    render_generated_block as render_canvas_block,
    update_canvas_text as update_canvas_text_block,
)
from evals.sentence_routing_retrieval_falsification.breadcrumb_query_grader import (
    aggregate_context_evidence_metrics,
    grade_natural_scenario,
    grade_scenario,
    load_gold,
    natural_retrieval_bundle,
)
from evals.sentence_routing_retrieval_falsification.breadcrumb_natural_scoring import (
    build_hit_context_text,
    index_records_by_unit_id,
)
from evals.sentence_routing_retrieval_falsification.breadcrumb_query_llm import (
    format_synthesis_user_message,
    resolve_breadcrumb_query_llm_model,
    synthesize_answer_from_hit_context,
)
from evals.sentence_routing_retrieval_falsification.breadcrumb_semantic_similarity import (
    EMBEDDING_MODEL_DEFAULT,
    compare_expected_to_output_with_embeddings,
)
from evals.sentence_routing_retrieval_falsification.breadcrumb_tagging_repair import (
    adjudicate_repairs_with_llm,
    apply_repair_patches,
    find_repair_candidates,
)
from evals.sentence_routing_retrieval_falsification.breadcrumb_tagging_scorer import (
    read_tagging_sentinels,
    score_normalized_records,
)
from src.agent.synthesis import _load_api_key
from src.bootstrap_env import load_dungeonmindbuddy_dotenv

_PROMOTED_CONTEXT_MAX_LEXICAL_UNITS_DEFAULT = 8
_PROMOTED_CONTEXT_MAX_CHARS_DEFAULT = 2400


def _resolve_repair_model(cli_model: str | None) -> str:
    return (
        (cli_model or "").strip()
        or os.environ.get("DMB_BREADCRUMB_REPAIR_MODEL", "").strip()
        or "gpt-5.4-mini"
    )


_DEFAULT_BREADCRUMB_QUERY_SEMANTIC_CANVAS = default_cursor_canvas_path("breadcrumb-query-semantic-review.canvas.tsx")


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--breadcrumb-md", type=Path, help="Breadcrumb markdown artifact")
    parser.add_argument("--corpus-root", type=Path, help="Corpus root (required with --breadcrumb-md)")
    parser.add_argument("--records-jsonl", type=Path, help="Pre-built JSONL records")
    parser.add_argument(
        "--gold",
        type=Path,
        default=Path("evals/sentence_routing_retrieval_falsification/gold/breadcrumb_query_closed_loop_v1.json"),
    )
    parser.add_argument(
        "--llm-model",
        type=str,
        default=None,
        help="Natural gold only: OpenAI model id (else DMB_BREADCRUMB_QUERY_LLM_MODEL or MODEL_POLICY ruleslawyer_response_synthesis).",
    )
    parser.add_argument(
        "--semantic-similarity",
        action="store_true",
        help="Natural gold only: embed expected_answer vs synthesized answer and record cosine similarity.",
    )
    parser.add_argument(
        "--embedding-model",
        type=str,
        default=EMBEDDING_MODEL_DEFAULT,
        help="Embedding model for --semantic-similarity (default: text-embedding-3-large).",
    )
    parser.add_argument("--output", type=Path, help="Write report JSON here")
    parser.add_argument(
        "--canvas-tsx",
        nargs="?",
        const=_DEFAULT_BREADCRUMB_QUERY_SEMANTIC_CANVAS,
        default=None,
        type=Path,
        help=(
            "After the report is written, regenerate the breadcrumb query semantic review canvas "
            "(breadcrumb_query_canvas_payload). Pass a path, or pass the flag alone to use the default "
            f"Cursor-managed file: {_DEFAULT_BREADCRUMB_QUERY_SEMANTIC_CANVAS} "
            "(override canvases parent with DMB_CURSOR_CANVAS_DIR). Omit the flag to skip."
        ),
    )
    parser.add_argument(
        "--canvas-baseline-report",
        type=Path,
        default=None,
        help="Baseline report JSON to compare against when refreshing the canvas (optional).",
    )
    parser.add_argument(
        "--canvas-deterministic-report",
        type=Path,
        default=None,
        help="Deterministic-only report JSON paired with the canvas refresh (optional).",
    )
    parser.add_argument(
        "--repair-adjudicate",
        action="store_true",
        help=(
            "After normalizing --breadcrumb-md, run deterministic repair candidates + "
            "one OpenAI Responses adjudication pass, then merge allowed patches into records."
        ),
    )
    parser.add_argument(
        "--pronoun-route-handles",
        action="store_true",
        help=(
            "When normalizing --breadcrumb-md, enrich pronoun-bearing records with "
            "route-derived lexical handles from their own breadcrumbs."
        ),
    )
    parser.add_argument(
        "--repair-model",
        type=str,
        default=None,
        help="Model for --repair-adjudicate (else DMB_BREADCRUMB_REPAIR_MODEL or gpt-5.4-mini).",
    )
    parser.add_argument(
        "--tagging-sentinel-json",
        type=Path,
        default=None,
        help=(
            "Optional sentinel gold (schema dmb_breadcrumb_tagging_sentinels_v1). "
            "Requires --breadcrumb-md. Adds tagging_score to the report."
        ),
    )
    parser.add_argument(
        "--tagging-baseline-md",
        type=Path,
        default=Path(
            "evals/sentence_routing_retrieval_falsification/manual_labels/"
            "Session 20 - Recap.breadcrumbed.md"
        ),
        help=(
            "Baseline breadcrumb markdown for precision/recall vs tagged markup "
            "(default: Session 20 manual baseline). Omitted after repair adds routes "
            "(markdown body was not rewritten)."
        ),
    )
    args = parser.parse_args()

    suite_dir = Path(__file__).resolve().parent
    default_out = suite_dir / "artifacts" / "runs" / str(date.today()) / "breadcrumb_query_run_report.json"

    rec_objs: list[NormalizedRecord] | None = None
    breadcrumb_art_text: str | None = None
    meta: dict[str, Any] = {}
    repair_report_json: dict[str, Any] | None = None
    repair_cost_usd = 0.0
    corpus_root_resolved: Path | None = None

    if args.records_jsonl:
        if args.repair_adjudicate:
            raise SystemExit("--repair-adjudicate requires --breadcrumb-md")
        if args.tagging_sentinel_json is not None:
            raise SystemExit("--tagging-sentinel-json requires --breadcrumb-md")
        records_path = args.records_jsonl
        lines = records_path.read_text(encoding="utf-8").splitlines()
        records = [json.loads(line) for line in lines if line.strip()]
    elif args.breadcrumb_md:
        if not args.corpus_root:
            raise SystemExit("--corpus-root is required with --breadcrumb-md")
        art = args.breadcrumb_md.read_text(encoding="utf-8")
        breadcrumb_art_text = art
        corpus_root_resolved = Path(args.corpus_root).resolve()
        rec_objs, meta = normalize_breadcrumb_artifact(
            artifact_text=art,
            corpus_root=corpus_root_resolved,
            enrich_pronoun_route_handles=bool(args.pronoun_route_handles),
        )

        if args.repair_adjudicate:
            load_dungeonmindbuddy_dotenv()
            if not (_load_api_key() or "").strip():
                raise SystemExit(
                    "OPENAI_API_KEY missing after loading .env / .env.development "
                    "(see src/bootstrap_env.py). Required for --repair-adjudicate."
                )
            from openai import OpenAI

            candidates = find_repair_candidates(rec_objs)
            repair_model = _resolve_repair_model(args.repair_model)
            if not candidates:
                repair_report_json = {
                    "enabled": True,
                    "skipped": "no_candidates",
                    "candidate_count": 0,
                    "cost_usd": 0.0,
                    "model": repair_model,
                }
            else:
                recap_path = corpus_root_resolved / rec_objs[0].source_recap_path
                recap_full = recap_path.read_text(encoding="utf-8")
                _rfm, recap_body = parse_frontmatter_and_body(recap_full)
                client = OpenAI()
                try:
                    patches, repair_cost_usd, telemetry, raw_text = adjudicate_repairs_with_llm(
                        client=client,
                        model=repair_model,
                        recap_body=recap_body,
                        candidates=candidates,
                    )
                except (json.JSONDecodeError, ValueError) as exc:
                    repair_report_json = {
                        "enabled": True,
                        "error": f"repair_parse_failed: {exc}",
                        "candidate_count": len(candidates),
                        "cost_usd": 0.0,
                        "model": repair_model,
                    }
                    patches = []
                    raw_text = ""
                    telemetry = {}
                else:
                    candidate_ids = {c.unit_id for c in candidates}
                    allowed_routes = {c.unit_id: set(c.nearby_subject_routes) for c in candidates}
                    apply_rep = apply_repair_patches(
                        rec_objs,
                        patches,
                        candidate_unit_ids=candidate_ids,
                        allowed_routes_by_unit=allowed_routes,
                    )
                    repair_report_json = {
                        "enabled": True,
                        "model": repair_model,
                        "candidate_count": len(candidates),
                        "cost_usd": repair_cost_usd,
                        "telemetry": telemetry,
                        "raw_response_preview": raw_text[:2000],
                        "apply_report": apply_rep.to_json_dict(),
                    }

        records = [r.to_json_dict() for r in rec_objs]
        meta_path = default_out.with_name(default_out.stem + "_records_meta.json")
        if args.output:
            meta_path = args.output.with_suffix(".records_meta.json")
        meta_path.parent.mkdir(parents=True, exist_ok=True)
        meta_path.write_text(json.dumps(meta, indent=2), encoding="utf-8")
        records_path = meta_path.with_suffix(".jsonl")
        write_records_jsonl(rec_objs, records_path)
    else:
        raise SystemExit("Provide --records-jsonl or (--breadcrumb-md and --corpus-root)")

    gold = load_gold(args.gold)
    sch = str(gold.get("schema") or "")
    results: list[dict[str, Any]] = []
    llm_model: str | None = None
    aggregate_llm_cost_usd = 0.0
    aggregate_embedding_cost_usd = 0.0

    if args.semantic_similarity and sch != "dmb_breadcrumb_query_natural_gold_v1":
        raise SystemExit(
            "--semantic-similarity requires gold schema dmb_breadcrumb_query_natural_gold_v1 "
            "(compares expected_answer to synthesized LLM output)."
        )

    if sch == "dmb_breadcrumb_query_natural_gold_v1":
        load_dungeonmindbuddy_dotenv()
        if not (_load_api_key() or "").strip():
            raise SystemExit(
                "OPENAI_API_KEY missing after loading .env / .env.development "
                "(see src/bootstrap_env.py). Required for natural gold runs (LLM synthesis)."
            )
        llm_model = (args.llm_model or "").strip() or resolve_breadcrumb_query_llm_model()
        default_campaign = str(gold.get("campaign_id") or "")
        default_spec = gold.get("default_query_spec") or {}
        for scenario in gold.get("scenarios") or []:
            scen = dict(scenario)
            scen["campaign_id"] = str(scen.get("campaign_id") or default_campaign)
            merged_spec = {**default_spec, **(scen.get("query_spec") or {})}
            merged_spec["query"] = str(scen["question"])
            scen["query_spec"] = merged_spec
            bundle = natural_retrieval_bundle(records=records, scenario=scen)
            result, hit_ctx = bundle
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
                    scen.get("llm_promoted_context_max_units")
                    or _PROMOTED_CONTEXT_MAX_LEXICAL_UNITS_DEFAULT
                ),
                max_chars=int(
                    scen.get("llm_promoted_context_max_chars")
                    or _PROMOTED_CONTEXT_MAX_CHARS_DEFAULT
                ),
                order_mode=str(scen.get("llm_promoted_context_order") or "ranked"),
            )
            llm_user_message = format_synthesis_user_message(
                question=str(scen["question"]),
                hit_context=hit_ctx_llm,
            )
            llm_text, llm_cost, llm_usage = synthesize_answer_from_hit_context(
                question=str(scen["question"]),
                hit_context=hit_ctx_llm,
                model=llm_model,
            )
            aggregate_llm_cost_usd += llm_cost
            row = grade_natural_scenario(
                records=records,
                scenario=scen,
                llm_answer=llm_text,
                cached_retrieval=bundle,
            )
            preview_n = int(scen.get("llm_answer_preview_chars", 1200))
            row["llm_answer_preview"] = llm_text[:preview_n]
            # Lexical-only context for synthesis + report mirror (route coverage still uses hit objects).
            row["retrieved_context"] = hit_ctx_llm
            # Full deterministic hit-context string (units + normalized route lines) for forensics.
            row["retrieval_hit_context_full"] = hit_ctx_full
            # Exact user message sent to the synthesis chat completion (question + promoted context).
            row["llm_user_message"] = llm_user_message
            row["llm_cost_usd"] = llm_cost
            row["llm_usage"] = llm_usage
            row["llm_model"] = llm_model
            if args.semantic_similarity:
                expected_answer = str(scen.get("expected_answer") or "").strip()
                if not expected_answer:
                    row["embedding_similarity_error"] = "scenario_missing_expected_answer"
                else:
                    sim = compare_expected_to_output_with_embeddings(
                        expected_answer=expected_answer,
                        output_answer=llm_text,
                        model=str(args.embedding_model),
                    )
                    aggregate_embedding_cost_usd += float(sim.get("cost_usd") or 0.0)
                    row["expected_answer"] = expected_answer
                    row["embedding_similarity"] = sim
            results.append(row)
    else:
        for scenario in gold.get("scenarios") or []:
            results.append(grade_scenario(records=records, scenario=scenario))

    tagging_score: dict[str, Any] | None = None
    if args.tagging_sentinel_json is not None:
        if rec_objs is None or corpus_root_resolved is None:
            raise SystemExit("--tagging-sentinel-json requires --breadcrumb-md")
        sentinels_data = read_tagging_sentinels(Path(args.tagging_sentinel_json).resolve())
        baseline_file = Path(args.tagging_baseline_md).resolve()
        baseline_for_score = baseline_file if baseline_file.is_file() else None
        skip_baseline_body = bool(
            repair_report_json
            and repair_report_json.get("apply_report")
            and int(repair_report_json["apply_report"].get("routes_added") or 0) > 0
        )
        tagging_score = score_normalized_records(
            records=rec_objs,
            corpus_root=corpus_root_resolved,
            artifact_path=str(Path(args.breadcrumb_md).resolve()),
            meta=meta,
            normalize_error=None,
            sentinels=sentinels_data,
            baseline_artifact_path=baseline_for_score,
            breadcrumb_full_text=None if skip_baseline_body else breadcrumb_art_text,
        )

    report: dict[str, Any] = {
        "records_source": str(records_path.resolve()),
        "gold": str(args.gold.resolve()),
        "gold_schema": sch,
        "all_ok": all(r["ok"] for r in results),
        "results": results,
        "context_evidence_aggregate": aggregate_context_evidence_metrics(results),
    }
    if repair_report_json is not None:
        report["repair_adjudication"] = repair_report_json
    if tagging_score is not None:
        report["tagging_score"] = tagging_score
    total_sidecar_cost_usd = (
        float(repair_cost_usd) + aggregate_llm_cost_usd + aggregate_embedding_cost_usd
    )
    if sch == "dmb_breadcrumb_query_natural_gold_v1":
        report["llm_enabled"] = True
        report["llm_model"] = llm_model
        report["aggregate_llm_cost_usd"] = aggregate_llm_cost_usd
    if args.semantic_similarity:
        report["embedding_similarity_enabled"] = True
        report["embedding_model"] = str(args.embedding_model)
        report["aggregate_embedding_cost_usd"] = aggregate_embedding_cost_usd
    if repair_cost_usd > 0 and "repair_adjudication" in report:
        report["repair_adjudication_cost_usd"] = float(repair_cost_usd)
    if total_sidecar_cost_usd > 0:
        report["scenario_estimated_cost_usd"] = total_sidecar_cost_usd

    out = args.output or default_out
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(report, indent=2), encoding="utf-8")
    print(json.dumps({"wrote": str(out), "all_ok": report["all_ok"]}, indent=2))

    if args.canvas_tsx is not None:
        _refresh_canvas(
            canvas_path=args.canvas_tsx,
            report=report,
            gold=gold,
            report_path=out,
            baseline_report_path=args.canvas_baseline_report,
            deterministic_report_path=args.canvas_deterministic_report,
            records_jsonl=records_path,
        )


def _refresh_canvas(
    *,
    canvas_path: Path,
    report: dict[str, Any],
    gold: dict[str, Any],
    report_path: Path,
    baseline_report_path: Path | None,
    deterministic_report_path: Path | None,
    records_jsonl: Path,
) -> None:
    """Regenerate the breadcrumb query canvas data block from the report just written."""
    from evals.sentence_routing_retrieval_falsification.breadcrumb_query_canvas_payload import (
        _load_records_text,
    )

    baseline = (
        json.loads(baseline_report_path.read_text(encoding="utf-8"))
        if baseline_report_path is not None
        else None
    )
    deterministic = (
        json.loads(deterministic_report_path.read_text(encoding="utf-8"))
        if deterministic_report_path is not None
        else None
    )
    report_for_records = dict(report)
    report_for_records.setdefault("records_source", str(records_jsonl.resolve()))
    records_text = _load_records_text(report_for_records, records_jsonl)
    payload = build_canvas_payload(
        report=report,
        gold=gold,
        baseline=baseline,
        deterministic=deterministic,
        records_text=records_text,
        report_path=str(report_path.resolve()),
        gold_path=str(report.get("gold") or ""),
        baseline_path=(str(baseline_report_path.resolve()) if baseline_report_path else None),
        deterministic_path=(
            str(deterministic_report_path.resolve()) if deterministic_report_path else None
        ),
    )
    block = render_canvas_block(payload)
    canvas_text = canvas_path.read_text(encoding="utf-8")
    new_text = update_canvas_text_block(canvas_text, block)
    if new_text != canvas_text:
        canvas_path.write_text(new_text, encoding="utf-8")
        print(json.dumps({"canvas_updated": str(canvas_path)}, indent=2))
    else:
        print(json.dumps({"canvas_unchanged": str(canvas_path)}, indent=2))

if __name__ == "__main__":
    main()
