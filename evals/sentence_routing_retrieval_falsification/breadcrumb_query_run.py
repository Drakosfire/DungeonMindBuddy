#!/usr/bin/env python3
"""Run deterministic session-memory query grading (JSONL records + gold scenarios).

Writes a default artifact under ``artifacts/runs/<date>/`` unless ``--output`` is set.

Examples:

  uv run python -m evals.sentence_routing_retrieval_falsification.breadcrumb_query_run \\
    --breadcrumb-md evals/sentence_routing_retrieval_falsification/manual_labels/Session\\ 20\\ -\\ Recap.breadcrumbed.md \\
    --corpus-root corpus/eldyrwild-markdown

  uv run python -m evals.sentence_routing_retrieval_falsification.breadcrumb_query_run \\
    --records-jsonl /tmp/session20.jsonl \\
    --gold evals/sentence_routing_retrieval_falsification/gold/breadcrumb_query_closed_loop_v1.json
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
from evals.sentence_routing_retrieval_falsification.breadcrumb_query_canvas_payload import (
    build_payload as build_canvas_payload,
    render_generated_block as render_canvas_block,
    update_canvas_text as update_canvas_text_block,
)
from evals.sentence_routing_retrieval_falsification.breadcrumb_query_grader import (
    grade_natural_scenario,
    grade_scenario,
    load_gold,
    natural_retrieval_bundle,
)
from evals.sentence_routing_retrieval_falsification.breadcrumb_query_llm import (
    resolve_breadcrumb_query_llm_model,
    synthesize_answer_from_hit_context,
)
from evals.sentence_routing_retrieval_falsification.breadcrumb_semantic_similarity import (
    EMBEDDING_MODEL_DEFAULT,
    compare_expected_to_output_with_embeddings,
)
from src.agent.synthesis import _load_api_key
from src.bootstrap_env import load_dungeonmindbuddy_dotenv


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
        "--llm",
        action="store_true",
        help="Natural gold only: synthesize answers with OpenAI over hit context, then grade llm_semantic_verdict.",
    )
    parser.add_argument(
        "--llm-model",
        type=str,
        default=None,
        help="OpenAI model id (else DMB_BREADCRUMB_QUERY_LLM_MODEL or MODEL_POLICY ruleslawyer_response_synthesis).",
    )
    parser.add_argument(
        "--semantic-similarity",
        action="store_true",
        help="LLM path only: embed expected_answer vs LLM answer and record cosine similarity.",
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
        type=Path,
        default=None,
        help=(
            "Optional canvas .tsx path. After the report is written, regenerate the canvas "
            "data block with breadcrumb_query_canvas_payload."
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
    args = parser.parse_args()

    suite_dir = Path(__file__).resolve().parent
    default_out = suite_dir / "artifacts" / "runs" / str(date.today()) / "breadcrumb_query_run_report.json"

    if args.records_jsonl:
        records_path = args.records_jsonl
        lines = records_path.read_text(encoding="utf-8").splitlines()
        records = [json.loads(line) for line in lines if line.strip()]
    elif args.breadcrumb_md:
        if not args.corpus_root:
            raise SystemExit("--corpus-root is required with --breadcrumb-md")
        art = args.breadcrumb_md.read_text(encoding="utf-8")
        rec_objs, meta = normalize_breadcrumb_artifact(artifact_text=art, corpus_root=args.corpus_root)
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

    if args.llm and sch != "dmb_breadcrumb_query_natural_gold_v1":
        raise SystemExit("--llm requires gold schema dmb_breadcrumb_query_natural_gold_v1")
    if args.semantic_similarity and not args.llm:
        raise SystemExit("--semantic-similarity requires --llm because it compares expected_answer to LLM output")

    if args.llm or args.semantic_similarity:
        load_dungeonmindbuddy_dotenv()
        if not (_load_api_key() or "").strip():
            raise SystemExit(
                "OPENAI_API_KEY missing after loading .env / .env.development "
                "(see src/bootstrap_env.py). Required for --llm / --semantic-similarity."
            )
    if args.llm:
        llm_model = (args.llm_model or "").strip() or resolve_breadcrumb_query_llm_model()

    if sch == "dmb_breadcrumb_query_natural_gold_v1":
        default_campaign = str(gold.get("campaign_id") or "")
        default_spec = gold.get("default_query_spec") or {}
        for scenario in gold.get("scenarios") or []:
            scen = dict(scenario)
            scen["campaign_id"] = str(scen.get("campaign_id") or default_campaign)
            merged_spec = {**default_spec, **(scen.get("query_spec") or {})}
            merged_spec["query"] = str(scen["question"])
            scen["query_spec"] = merged_spec
            if args.llm:
                bundle = natural_retrieval_bundle(records=records, scenario=scen)
                _, hit_ctx = bundle
                llm_text, llm_cost, llm_usage = synthesize_answer_from_hit_context(
                    question=str(scen["question"]),
                    hit_context=hit_ctx,
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
                row["retrieved_context"] = hit_ctx
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
                results.append(grade_natural_scenario(records=records, scenario=scen))
    else:
        for scenario in gold.get("scenarios") or []:
            results.append(grade_scenario(records=records, scenario=scenario))

    report: dict[str, Any] = {
        "records_source": str(records_path.resolve()),
        "gold": str(args.gold.resolve()),
        "gold_schema": sch,
        "all_ok": all(r["ok"] for r in results),
        "results": results,
    }
    if args.llm:
        report["llm_enabled"] = True
        report["llm_model"] = llm_model
        report["aggregate_llm_cost_usd"] = aggregate_llm_cost_usd
        report["scenario_estimated_cost_usd"] = aggregate_llm_cost_usd + aggregate_embedding_cost_usd
    if args.semantic_similarity:
        report["embedding_similarity_enabled"] = True
        report["embedding_model"] = str(args.embedding_model)
        report["aggregate_embedding_cost_usd"] = aggregate_embedding_cost_usd

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
