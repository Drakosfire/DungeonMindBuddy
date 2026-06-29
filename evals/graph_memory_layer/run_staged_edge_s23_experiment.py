#!/usr/bin/env python3
"""Run staged edge extraction experiment on Session 23 stored pass outputs.

Reuses non-edge category pass outputs from a prior graph ingest run, runs the
staged relation-observation → bind → normalize → assemble path live, and
compares against Session 23 gold.

Writes reports under ``out/graph_memory/experiments/staged_edge_s23/`` (local only).
"""
from __future__ import annotations

import argparse
import json
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from evals.graph_memory_layer.live_vs_gold_compare import compare_parts, parts_from_raw_graph
from evals.graph_memory_layer.session_23_candidate_graph_gold_fixture import (
    load_gold_candidate_graph_dict,
)
from src.graph_memory.extraction.category_candidate_graph_extractor import (
    EDGE_PASS_NAME,
    CategoryGraphExtractionOptions,
    FixtureCategoryGraphPassClient,
    consolidate_category_outputs,
    resolve_category_graph_model,
    sanitize_parts,
    source_packet_rows_from_span_index,
)
from src.graph_memory.extraction.staged_edge_extraction import run_staged_edge_extraction

DEFAULT_STORED_RUN = (
    "out/graph_memory/runs/longmont-c2/session-23/20260629T183113Z"
)
DEFAULT_OUTPUT_ROOT = Path("out/graph_memory/experiments/staged_edge_s23")
BASELINE_EDGE_RECALL = 0.381
BASELINE_MATCHED_EDGES = 8


def _utc_stamp() -> str:
    return datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")


def _allowed_span_refs(span_index: dict[str, Any], source_rows: list[dict[str, Any]]) -> set[str]:
    allowed = {r["source_span_ref_id"] for r in source_rows}
    for span in span_index.get("spans") or []:
        if isinstance(span, dict):
            for key in ("source_span_ref_id", "span_id"):
                val = span.get(key)
                if isinstance(val, str):
                    allowed.add(val)
    return allowed


def _binding_status_counts(bound_candidates: list[dict[str, Any]]) -> dict[str, int]:
    return dict(sorted(Counter(str(c.get("binding_status") or "unknown") for c in bound_candidates).items()))


def _predicate_status_counts(normalized: list[dict[str, Any]]) -> dict[str, int]:
    return dict(sorted(Counter(str(c.get("predicate_status") or "unknown") for c in normalized).items()))


def run_trial(
    *,
    stored_run_dir: Path,
    model_id: str | None,
    trial: int,
    output_root: Path,
) -> dict[str, Any]:
    run_dir = stored_run_dir.resolve()
    pass_outputs_path = run_dir / "pass_outputs.json"
    span_index_path = run_dir / "source_span_index.json"
    if not pass_outputs_path.is_file() or not span_index_path.is_file():
        raise FileNotFoundError(f"missing stored run artifacts under {run_dir}")

    pass_outputs = json.loads(pass_outputs_path.read_text(encoding="utf-8"))
    span_index = json.loads(span_index_path.read_text(encoding="utf-8"))
    # Drop prior one-shot edge pass; staged path replaces LLM edge emission.
    pass_outputs = dict(pass_outputs)
    pass_outputs[EDGE_PASS_NAME] = {"observation_edges": []}

    resolved_model = resolve_category_graph_model(model_id)
    source_rows = source_packet_rows_from_span_index(span_index)
    allowed = _allowed_span_refs(span_index, source_rows)

    consolidated = consolidate_category_outputs(
        pass_outputs,
        campaign_id="longmont-c2",
        session=23,
    )
    staged = run_staged_edge_extraction(
        model_id=resolved_model,
        source_rows=source_rows,
        consolidated=consolidated,
        allowed_span_refs=allowed,
    )

    merged_edges = list(consolidated.get("edges") or []) + list(staged.edges)
    consolidated_with_staged = {
        **consolidated,
        "edges": merged_edges,
    }
    sanitized, sanitize_diag = sanitize_parts(consolidated_with_staged, allowed)
    gold_parts = parts_from_raw_graph(load_gold_candidate_graph_dict())
    report = compare_parts(parts_from_raw_graph(sanitized), gold_parts)

    llm_edges = [e for e in sanitized.get("edges", []) if not e.get("context_anchor")]
    miss_diag = report["diagnostics"].get("edge_miss_diagnostics") or {}

    trial_report: dict[str, Any] = {
        "schema": "dmb_staged_edge_s23_experiment_report_v1",
        "trial": trial,
        "model_id": resolved_model,
        "stored_run_dir": str(run_dir),
        "baseline": {
            "edge_recall": BASELINE_EDGE_RECALL,
            "matched_edges": BASELINE_MATCHED_EDGES,
            "gold_edges_total": 21,
        },
        "scores": report["scores"],
        "coverage": {
            "matched_edges": report["coverage"].get("matched_edges"),
            "gold_edges_total": report["coverage"].get("gold_edges_total"),
            "candidate_edges_total": report["coverage"].get("candidate_edges_total"),
            "missing_gold_edge_ids": [
                m.get("id") if isinstance(m, dict) else m
                for m in report["coverage"].get("missing_gold_edges", [])
            ],
        },
        "staged_edge_counts": {
            "relation_candidates": len(staged.relation_candidates),
            "bound_bound": _binding_status_counts(staged.bound_candidates).get("bound", 0),
            "binding_status_counts": _binding_status_counts(staged.bound_candidates),
            "predicate_status_counts": _predicate_status_counts(staged.normalized_candidates),
            "assembled_llm_edges": len(staged.edges),
            "live_llm_edges_after_sanitize": len(llm_edges),
            "live_edges_total": len(sanitized.get("edges", [])),
        },
        "assembly_diagnostics": staged.assembly_diagnostics,
        "relation_observation_telemetry": staged.relation_observation_telemetry,
        "sanitize_diagnostics": sanitize_diag,
        "remaining_miss_reasons": dict(
            sorted(Counter(v.get("reason") for v in miss_diag.values()).items())
        ),
        "remaining_miss_by_rel": dict(
            sorted(Counter(v.get("gold_relationship_type") for v in miss_diag.values()).items())
        ),
        "improved_over_baseline": len(report["coverage"].get("matched_edges") or [])
        > BASELINE_MATCHED_EDGES,
    }

    out_dir = output_root / f"trial_{trial:02d}"
    out_dir.mkdir(parents=True, exist_ok=True)
    (out_dir / "trial_report.json").write_text(
        json.dumps(trial_report, indent=2),
        encoding="utf-8",
    )
    (out_dir / "relation_candidates.json").write_text(
        json.dumps(staged.relation_candidates, indent=2),
        encoding="utf-8",
    )
    (out_dir / "bound_candidates.json").write_text(
        json.dumps(staged.bound_candidates, indent=2),
        encoding="utf-8",
    )
    (out_dir / "assembled_edges.json").write_text(
        json.dumps(staged.edges, indent=2),
        encoding="utf-8",
    )
    return trial_report


def main() -> None:
    parser = argparse.ArgumentParser(description="Session 23 staged edge extraction experiment")
    parser.add_argument(
        "--stored-run-dir",
        default=DEFAULT_STORED_RUN,
        help="Prior graph ingest run with pass_outputs + source_span_index",
    )
    parser.add_argument(
        "--output-root",
        default=str(DEFAULT_OUTPUT_ROOT),
        help="Directory for experiment reports",
    )
    parser.add_argument(
        "--model-id",
        default=None,
        help="Model override (default: MODEL_POLICY graph_memory_category_extraction)",
    )
    parser.add_argument(
        "--trials",
        type=int,
        default=3,
        help="Number of mini-model trials (default 3)",
    )
    parser.add_argument(
        "--strong-trial",
        action="store_true",
        help="Also run one gpt-5.4 trial after mini trials",
    )
    args = parser.parse_args()

    stored = Path(args.stored_run_dir)
    output_root = Path(args.output_root)
    batch_dir = output_root / _utc_stamp()
    batch_dir.mkdir(parents=True, exist_ok=True)
    summaries: list[dict[str, Any]] = []

    for trial in range(1, args.trials + 1):
        print(f"Running mini trial {trial}/{args.trials}...")
        summaries.append(
            run_trial(
                stored_run_dir=stored,
                model_id=args.model_id,
                trial=trial,
                output_root=batch_dir,
            )
        )

    if args.strong_trial:
        print("Running strong-model trial...")
        summaries.append(
            run_trial(
                stored_run_dir=stored,
                model_id="gpt-5.4",
                trial=args.trials + 1,
                output_root=batch_dir,
            )
        )

    summary_path = batch_dir / "experiment_summary.json"
    summary = {
        "schema": "dmb_staged_edge_s23_experiment_summary_v1",
        "trials": summaries,
        "any_improved_over_baseline": any(t.get("improved_over_baseline") for t in summaries),
        "best_edge_recall": max(t["scores"]["edge_recall"] for t in summaries),
        "best_matched_edges": max(len(t["coverage"]["matched_edges"]) for t in summaries),
    }
    summary_path.write_text(json.dumps(summary, indent=2), encoding="utf-8")
    print(json.dumps(summary, indent=2))


if __name__ == "__main__":
    main()
