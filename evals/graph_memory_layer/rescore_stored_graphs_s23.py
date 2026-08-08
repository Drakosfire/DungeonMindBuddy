#!/usr/bin/env python3
"""Re-score stored Session 23 graphs against gold without new LLM calls.

Isolates comparator changes (e.g. identity_resolution alias signals) from
extraction changes by re-running ``compare_parts`` on:

1. the stored one-shot candidate graph from a prior ingest run, and
2. each stored staged-edge trial (``assembled_edges.json``) re-merged onto the
   stored consolidated pass outputs, mirroring ``run_staged_edge_s23_experiment``
   but reusing the trial's stored staged edges instead of re-calling the model.

Usage:

    uv run python -m evals.graph_memory_layer.rescore_stored_graphs_s23 \
        --stored-run-dir out/graph_memory/runs/longmont-c2/session-23/20260629T183113Z \
        --trials-root out/graph_memory/experiments/staged_edge_s23
"""
from __future__ import annotations

import argparse
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from evals.graph_memory_layer.live_vs_gold_compare import compare_parts, parts_from_raw_graph
from evals.graph_memory_layer.session_23_candidate_graph_gold_fixture import (
    load_gold_candidate_graph_dict,
)
from src.graph_memory.extraction.category_candidate_graph_extractor import (
    EDGE_PASS_NAME,
    consolidate_category_outputs,
    sanitize_parts,
    source_packet_rows_from_span_index,
)

# Gold edges whose comparator miss is attributed to label divergence on the
# "Edge Survivors" (live) vs "Edge refugees" (gold) endpoint.
TARGET_GOLD_LABEL_HINTS = ("survivor", "refugee")


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


def _target_edge_detail(report: dict[str, Any], gold_parts: dict[str, Any]) -> list[dict[str, Any]]:
    """Per-target-gold-edge diagnostics: matched or miss reason."""
    gold_edges = [
        e for e in gold_parts.get("edges", [])
        if any(h in str(e.get("label", "")).lower() for h in TARGET_GOLD_LABEL_HINTS)
        or any(
            h in str(e.get("relationship_type", "")).lower()
            for h in ("leads", "displaced_from")
        )
    ]
    miss_diag = report["diagnostics"].get("edge_miss_diagnostics") or {}
    matched_ids = set(report["coverage"].get("matched_edges") or [])
    out = []
    for edge in gold_edges:
        eid = str(edge.get("edge_id", ""))
        entry: dict[str, Any] = {
            "edge_id": eid,
            "label": edge.get("label"),
            "relationship_type": edge.get("relationship_type"),
            "matched": eid in matched_ids,
        }
        if eid in miss_diag:
            entry["miss"] = miss_diag[eid]
        out.append(entry)
    return out


def _summarize(report: dict[str, Any], gold_parts: dict[str, Any]) -> dict[str, Any]:
    coverage = report["coverage"]
    matched = coverage.get("matched_edges") or []
    return {
        "edge_recall": report["scores"].get("edge_recall"),
        "node_recall": report["scores"].get("node_recall"),
        "matched_edges_count": len(matched),
        "gold_edges_total": coverage.get("gold_edges_total"),
        "missing_gold_edge_ids": [
            m.get("id") if isinstance(m, dict) else m
            for m in coverage.get("missing_gold_edges", [])
        ],
        "target_edges": _target_edge_detail(report, gold_parts),
    }


def rescore_one_shot(stored_run_dir: Path, gold_parts: dict[str, Any]) -> dict[str, Any]:
    candidate = json.loads((stored_run_dir / "candidate_graph.json").read_text(encoding="utf-8"))
    report = compare_parts(parts_from_raw_graph(candidate), gold_parts)
    return _summarize(report, gold_parts)


def rescore_staged_trial(
    stored_run_dir: Path,
    trial_dir: Path,
    gold_parts: dict[str, Any],
) -> dict[str, Any]:
    pass_outputs = json.loads((stored_run_dir / "pass_outputs.json").read_text(encoding="utf-8"))
    span_index = json.loads((stored_run_dir / "source_span_index.json").read_text(encoding="utf-8"))
    staged_edges = json.loads((trial_dir / "assembled_edges.json").read_text(encoding="utf-8"))

    pass_outputs = dict(pass_outputs)
    pass_outputs[EDGE_PASS_NAME] = {"observation_edges": []}
    source_rows = source_packet_rows_from_span_index(span_index)
    allowed = _allowed_span_refs(span_index, source_rows)

    consolidated = consolidate_category_outputs(
        pass_outputs,
        campaign_id="longmont-c2",
        session=23,
    )
    merged = {**consolidated, "edges": list(consolidated.get("edges") or []) + list(staged_edges)}
    sanitized, _diag = sanitize_parts(merged, allowed)
    report = compare_parts(parts_from_raw_graph(sanitized), gold_parts)
    return _summarize(report, gold_parts)


def main() -> None:
    parser = argparse.ArgumentParser(description="Re-score stored S23 graphs against gold (no LLM)")
    parser.add_argument("--stored-run-dir", required=True)
    parser.add_argument("--trials-root", default=None, help="Root containing <batch>/trial_NN dirs")
    parser.add_argument("--out", default=None, help="Write full JSON report here")
    args = parser.parse_args()

    stored_run_dir = Path(args.stored_run_dir).resolve()
    gold_parts = parts_from_raw_graph(load_gold_candidate_graph_dict())

    results: dict[str, Any] = {
        "schema": "dmb_rescore_stored_graphs_s23_v1",
        "scored_at": _utc_stamp(),
        "stored_run_dir": str(stored_run_dir),
        "one_shot": rescore_one_shot(stored_run_dir, gold_parts),
        "staged_trials": {},
    }

    if args.trials_root:
        root = Path(args.trials_root)
        for trial_json in sorted(root.glob("*/trial_*/assembled_edges.json")):
            trial_dir = trial_json.parent
            key = f"{trial_dir.parent.name}/{trial_dir.name}"
            results["staged_trials"][key] = rescore_staged_trial(stored_run_dir, trial_dir, gold_parts)

    text = json.dumps(results, indent=2)
    if args.out:
        out_path = Path(args.out)
        out_path.parent.mkdir(parents=True, exist_ok=True)
        out_path.write_text(text, encoding="utf-8")
    print(text)


if __name__ == "__main__":
    main()
