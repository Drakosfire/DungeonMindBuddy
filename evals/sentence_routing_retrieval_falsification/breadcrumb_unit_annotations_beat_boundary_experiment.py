#!/usr/bin/env python3
"""Run C1S13 beat-boundary prompt ablations and emit a comparison summary.

Each variant runs one full unit-annotation ingest against the same recap, gold, and model.
Per-variant artifacts land under ``artifacts/runs/<date>/``; the summary defaults to
``artifacts/beat_boundary_experiment_c1s13_summary.json``.
"""

from __future__ import annotations

import argparse
import json
import sys
from datetime import date, datetime, timezone
from pathlib import Path
from typing import Any

from evals.sentence_routing_retrieval_falsification.breadcrumb_unit_annotations_prompt import (
    BEAT_BOUNDARY_EXPERIMENT_VARIANTS,
)
from evals.sentence_routing_retrieval_falsification.breadcrumb_unit_annotations_run import (
    _resolve_breadcrumb_ingest_model,
    run_unit_annotations_ingest,
)

_TRACKED_GOLD_BEATS = (
    "c1s13-b001-plan-academy-departure",
    "c1s13-b002-street-meat-incident",
    "c1s13-b004-stormspire-options-and-split",
    "c1s13-b008-basement-morgue-speak-with-dead",
    "c1s13-b012-post-ambush-empty-room-tunnel",
)
_TRACKED_SPLIT_UNITS = (
    "u-L0009-01",
    "u-L0009-02",
    "u-L0011-01",
    "u-L0011-02",
    "u-L0011-03",
)


def _default_summary_path() -> Path:
    return (
        Path(__file__).resolve().parent
        / "artifacts"
        / "beat_boundary_experiment_c1s13_summary.json"
    )


def _default_variant_output_path(*, variant: str) -> Path:
    today = date.today().isoformat()
    stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    return (
        Path(__file__).resolve().parent
        / "artifacts"
        / "runs"
        / today
        / f"unit_annotations_c1s13--{variant}--{stamp}.json"
    )


def _unit_to_beat_map(parsed: dict[str, Any]) -> dict[str, str | None]:
    out: dict[str, str | None] = {}
    for row in parsed.get("unit_annotations") or []:
        unit_id = str(row.get("unit_id") or "").strip()
        if not unit_id:
            continue
        beat_id = row.get("beat_id")
        out[unit_id] = str(beat_id).strip() if beat_id else None
    return out


def _summarize_variant_report(report: dict[str, Any]) -> dict[str, Any]:
    gold_compare = report.get("gold_compare") or {}
    per_beat = {row["beat_id"]: row for row in gold_compare.get("per_beat") or []}
    tracked_beats = {
        beat_id: {
            "unit_ids_match": per_beat.get(beat_id, {}).get("unit_ids_match"),
            "best_model_unit_span_match": per_beat.get(beat_id, {}).get(
                "best_model_unit_span_match"
            ),
        }
        for beat_id in _TRACKED_GOLD_BEATS
    }
    unit_to_beat = _unit_to_beat_map(report.get("parsed") or {})
    split_unit_beats = {unit_id: unit_to_beat.get(unit_id) for unit_id in _TRACKED_SPLIT_UNITS}
    split_unit_beat_ids = sorted({bid for bid in split_unit_beats.values() if bid})
    return {
        "prompt_variant": report.get("prompt_variant"),
        "model": report.get("model"),
        "validation_error": report.get("validation_error"),
        "scenario_estimated_cost_usd": (report.get("telemetry_cost") or {}).get(
            "scenario_estimated_cost_usd"
        ),
        "model_beat_count": gold_compare.get("model_beat_count"),
        "gold_beat_count": gold_compare.get("gold_beat_count"),
        "dimension_pass_rates": gold_compare.get("dimension_pass_rates"),
        "unit_span_alignment": gold_compare.get("unit_span_alignment"),
        "missing_beats": gold_compare.get("missing_beats"),
        "extra_beats": gold_compare.get("extra_beats"),
        "tracked_gold_beats": tracked_beats,
        "split_unit_beats": split_unit_beats,
        "split_unit_distinct_model_beats": split_unit_beat_ids,
    }


def run_beat_boundary_experiment(
    *,
    corpus_root: Path,
    recap_md: Path,
    frontmatter_seed_md: Path,
    gold_md: Path,
    model: str,
    variants: tuple[str, ...],
    skip_semantic: bool,
    output_dir: Path | None,
) -> dict[str, Any]:
    variant_rows: list[dict[str, Any]] = []
    artifact_paths: list[str] = []
    cost_sum = 0.0

    for variant in variants:
        report = run_unit_annotations_ingest(
            recap_md=recap_md,
            frontmatter_seed_md=frontmatter_seed_md,
            corpus_root=corpus_root,
            model=model,
            variant=variant,
            gold_md=gold_md,
            skip_semantic=skip_semantic,
        )
        out_path = (
            output_dir / f"unit_annotations_c1s13--{variant}.json"
            if output_dir is not None
            else _default_variant_output_path(variant=variant)
        )
        out_path.parent.mkdir(parents=True, exist_ok=True)
        out_path.write_text(json.dumps(report, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
        artifact_paths.append(str(out_path))
        row = _summarize_variant_report(report)
        row["artifact_path"] = str(out_path)
        variant_rows.append(row)
        cost_sum += float(row.get("scenario_estimated_cost_usd") or 0.0)

    return {
        "schema": "dmb_unit_annotations_beat_boundary_experiment_v1",
        "source_recap_path": variant_rows[0].get("artifact_path") if variant_rows else None,
        "model": model,
        "variants": list(variants),
        "skip_semantic": skip_semantic,
        "aggregate": {
            "variant_count": len(variant_rows),
            "scenario_estimated_cost_usd_sum": round(cost_sum, 6),
        },
        "variant_summaries": variant_rows,
        "artifact_paths": artifact_paths,
    }


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--corpus-root", type=Path, required=True)
    parser.add_argument("--ingest-recap-md", type=Path, required=True)
    parser.add_argument("--ingest-frontmatter-seed-md", type=Path, required=True)
    parser.add_argument(
        "--gold-md",
        type=Path,
        default=Path(
            "evals/sentence_routing_retrieval_falsification/manual_labels/"
            "Session 13 - The Meaty and the Dead.gold.beats.breadcrumbed.md"
        ),
    )
    parser.add_argument("--ingest-model", type=str, default=None)
    parser.add_argument(
        "--variant",
        action="append",
        dest="variants",
        help="Run only this variant (repeatable). Default: all beat-boundary experiment variants.",
    )
    parser.add_argument("--skip-semantic", action="store_true")
    parser.add_argument(
        "--output-dir",
        type=Path,
        default=None,
        help="Directory for per-variant artifacts (filenames include variant id).",
    )
    parser.add_argument("--summary-output", type=Path, default=None)
    args = parser.parse_args()

    model = _resolve_breadcrumb_ingest_model(args.ingest_model)
    variants = tuple(args.variants) if args.variants else BEAT_BOUNDARY_EXPERIMENT_VARIANTS
    unknown = [v for v in variants if v not in BEAT_BOUNDARY_EXPERIMENT_VARIANTS]
    if unknown:
        raise SystemExit(f"unknown beat-boundary experiment variant(s): {unknown}")

    summary = run_beat_boundary_experiment(
        corpus_root=args.corpus_root,
        recap_md=args.ingest_recap_md,
        frontmatter_seed_md=args.ingest_frontmatter_seed_md,
        gold_md=args.gold_md,
        model=model,
        variants=variants,
        skip_semantic=bool(args.skip_semantic),
        output_dir=args.output_dir,
    )
    summary_path = args.summary_output or _default_summary_path()
    summary_path.parent.mkdir(parents=True, exist_ok=True)
    summary_path.write_text(json.dumps(summary, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    print(json.dumps(summary, indent=2, ensure_ascii=False))
    failures = [row["prompt_variant"] for row in summary["variant_summaries"] if row.get("validation_error")]
    if failures:
        print(f"validation_error on variant(s): {', '.join(failures)}", file=sys.stderr)
        raise SystemExit(1)


if __name__ == "__main__":
    main()
