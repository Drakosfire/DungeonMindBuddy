"""Run category-decomposed graph extraction study across models (default: S22)."""
from __future__ import annotations

import argparse
import json
import sys
from datetime import date
from pathlib import Path

from evals.graph_memory_layer.category_graph_model_study import (
    DEFAULT_MODELS,
    STUDY_SCHEMA,
    STUDY_VERSION,
    _slug_model,
    artifacts_dir_for_today,
    ensure_s22_run_bundle,
    repo_root,
    run_category_pipeline,
    verified_s22_source,
    write_run_artifacts,
)
from src.agent.synthesis import _load_api_key
from src.bootstrap_env import load_dungeonmindbuddy_dotenv


def main() -> None:
    ap = argparse.ArgumentParser(description="Category-decomposed graph model study")
    ap.add_argument("--session", type=int, default=22)
    ap.add_argument("--models", nargs="+", default=list(DEFAULT_MODELS))
    ap.add_argument("--n", type=int, default=1, help="Runs per model")
    ap.add_argument("--out-root", type=Path, default=None)
    ap.add_argument("--allow-overwrite-bundle", action="store_true")
    ap.add_argument("-q", "--quiet", action="store_true")
    args = ap.parse_args()

    if args.session != 22:
        print("Only session 22 is supported in this proving slice.", file=sys.stderr)
        sys.exit(2)

    load_dungeonmindbuddy_dotenv()
    if not (_load_api_key() or "").strip():
        print(
            "OPENAI_API_KEY missing after loading .env / .env.development "
            "(see src/bootstrap_env.py).",
            file=sys.stderr,
        )
        sys.exit(2)

    from openai import OpenAI

    client = OpenAI()
    ensure_s22_run_bundle(allow_overwrite=args.allow_overwrite_bundle)
    verified = verified_s22_source()
    out_root = args.out_root or artifacts_dir_for_today()
    out_root.mkdir(parents=True, exist_ok=True)

    cohort: list[dict] = []
    for model_id in args.models:
        for run_idx in range(max(1, args.n)):
            slug = _slug_model(model_id)
            run_dir = out_root / f"session_22_{slug}_run{run_idx + 1}"
            if not args.quiet:
                print(f"[category-study] model={model_id} run={run_idx + 1}/{args.n}", file=sys.stderr)
            result = run_category_pipeline(client, model_id, verified, session=args.session)
            write_run_artifacts(result, run_dir)
            scores = result["comparison"].get("scores") or {}
            row = {
                "model_id": model_id,
                "run_index": run_idx,
                "run_dir": str(run_dir.relative_to(repo_root())),
                "scenario_estimated_cost_usd": result["scenario_estimated_cost_usd"],
                "node_recall": scores.get("node_recall"),
                "edge_recall": scores.get("edge_recall"),
                "beat_recall": scores.get("beat_recall"),
                "canonical_ir_valid": result["validation"].get("canonical_ir_valid"),
            }
            cohort.append(row)
            if not args.quiet:
                print(
                    f"  cost=${result['scenario_estimated_cost_usd']:.4f} "
                    f"node_recall={scores.get('node_recall')} edge_recall={scores.get('edge_recall')}",
                    file=sys.stderr,
                )

    costs = [float(r["scenario_estimated_cost_usd"]) for r in cohort]
    summary = {
        "schema": STUDY_SCHEMA,
        "version": STUDY_VERSION,
        "session": args.session,
        "date": date.today().isoformat(),
        "models": args.models,
        "runs_per_model": args.n,
        "runs": cohort,
        "aggregate": {
            "cost_usd": {
                "min": round(min(costs), 6),
                "max": round(max(costs), 6),
                "mean": round(sum(costs) / len(costs), 6),
                "sum": round(sum(costs), 6),
            },
        },
    }
    summary_path = out_root / "cohort_summary.json"
    summary_path.write_text(json.dumps(summary, indent=2) + "\n", encoding="utf-8")
  # mirror for discoverability
    mirror = Path(__file__).resolve().parents[1] / "artifacts" / "category_graph_model_study" / "last_cohort_summary.json"
    mirror.parent.mkdir(parents=True, exist_ok=True)
    mirror.write_text(json.dumps(summary, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(summary, indent=2))


if __name__ == "__main__":
    main()
