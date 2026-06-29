"""Write analysis markdown for category graph model study cohort artifacts."""
from __future__ import annotations

import json
import sys
from pathlib import Path

from evals.graph_memory_layer.category_graph_model_study import (
    assemble_envelope,
    compare_to_s22_gold,
    consolidate_category_outputs,
    repair_edge_evidence_refs,
    sanitize_parts,
    verified_s22_source,
    s22_run_bundle_dir,
)
from evals.graph_memory_layer.live_extractor_prompt_harness import source_packet_rows
from evals.graph_memory_layer.reconcile_live_candidate import validate_live_candidate_output

BASELINE_NODE_RECALL = 0.72
BASELINE_EDGE_RECALL = 0.44
ONESHOT_MODEL = "gpt-5.4"


def _rescore_run_dir(run_dir: Path, allowed: set[str]) -> dict:
    pass_outputs = json.loads((run_dir / "pass_outputs.json").read_text(encoding="utf-8"))
    telemetry = json.loads((run_dir / "pass_telemetry.json").read_text(encoding="utf-8"))
    consolidated = consolidate_category_outputs(pass_outputs, session=22)
    repair_diag = repair_edge_evidence_refs(consolidated, allowed)
    sanitized, sanitize_diag = sanitize_parts(consolidated, allowed)
    envelope = assemble_envelope(sanitized)
    validation = validate_live_candidate_output(
        envelope,
        run_bundle=s22_run_bundle_dir(),
        allowed_span_refs=allowed,
    )
    comparison = compare_to_s22_gold(envelope)
    cost = float(json.loads((run_dir / "run_summary.json").read_text()).get("scenario_estimated_cost_usd") or 0)
    return {
        "model_id": json.loads((run_dir / "run_summary.json").read_text()).get("model_id"),
        "scenario_estimated_cost_usd": cost,
        "pass_telemetry": telemetry,
        "consolidation_diagnostics": {
            **consolidated["consolidation_diagnostics"],
            **repair_diag,
            **sanitize_diag,
        },
        "validation": validation,
        "comparison": comparison,
        "counts": {
            "nodes": len(sanitized["nodes"]),
            "edges": len(sanitized["edges"]),
            "beats": len(sanitized["beats"]),
        },
    }


def build_markdown_report(cohort_dir: Path, runs: list[dict]) -> str:
    lines = [
        "# Category Graph Model Study — Session 22",
        "",
        f"Artifact root: `{cohort_dir}`",
        "",
        "## Baseline (one-shot)",
        "",
        f"- Model: `{ONESHOT_MODEL}`",
        f"- Node recall: **{BASELINE_NODE_RECALL}**",
        f"- Edge recall: **{BASELINE_EDGE_RECALL}**",
        "",
        "## Category-decomposed smoke (N=1 per model)",
        "",
        "| Model | Cost USD | Nodes | Edges | Node recall | Node prec. | Edge recall | Beat recall | Valid IR |",
        "|---|---:|---:|---:|---:|---:|---:|---:|:---:|",
    ]
    for row in runs:
        scores = row["comparison"]["scores"]
        lines.append(
            f"| {row['model_id']} | {row['scenario_estimated_cost_usd']:.4f} | "
            f"{row['counts']['nodes']} | {row['counts']['edges']} | "
            f"{scores.get('node_recall')} | {scores.get('node_precision_proxy')} | "
            f"{scores.get('edge_recall')} | {scores.get('beat_recall')} | "
            f"{row['validation']['canonical_ir_valid']} |"
        )
    costs = [r["scenario_estimated_cost_usd"] for r in runs]
    lines.extend(
        [
            "",
            "## Cost",
            "",
            f"- Cohort sum: **${sum(costs):.4f}** (min ${min(costs):.4f}, mean ${sum(costs)/len(costs):.4f}, max ${max(costs):.4f})",
            f"- Compare to one-shot baseline envelope (not re-run here); category path is ~7 LLM calls per model.",
            "",
            "## Failure-mode notes",
            "",
            "- Node recall now reflects span-overlap matching: candidate paragraph sprefs and gold curated"
            " anchors resolve to the same line range, so divergent phrasing over a shared span is matched"
            " (see `identity_resolution.node_match_score`). Companion anchors (Thrin, Lysandra) are seeded"
            " from party context, not re-extracted.",
            "- Residual node misses are real: e.g. `gpt-5.4-mini` omits Grobnok (actor pass miss), and the"
            " `event`-vs-`mystery` storm node drifts across the thread/phenomenon class boundary (gold types"
            " it `event`, models type it `mystery`).",
            "- Object pass over-extracts (node precision well below recall): rockie-talkie, wagon, stick,"
            " road sign, chalkboard menu — table props gold omits. Prompt-addressable (plot-bearing only).",
            "- Edge recall is ~0: the edge pass builds a thread\u2192location grounding graph rather than gold's"
            " entity\u2194entity relational graph (kinship/membership/authority/social). Endpoints are mostly"
            " present; the model chose the wrong edge ontology. Prompt-addressable.",
            "- Models often emit `session-22:pNNN` without the `spref:` prefix; sanitize canonicalizes.",
            "",
            "## Recommendation",
            "",
        ]
    )
    best = max(runs, key=lambda r: r["comparison"]["scores"].get("node_recall") or 0)
    best_recall = best["comparison"]["scores"].get("node_recall") or 0
    if best_recall >= 0.85:
        verdict = "promote category decomposition"
    elif best_recall > BASELINE_NODE_RECALL:
        verdict = "modify category decomposition (promising node recall but not at mini-model bar)"
    else:
        verdict = "reject or heavily revise (no model beat one-shot node recall on this smoke)"
    lines.append(f"**{verdict}** — best node recall `{best['model_id']}` at {best_recall}.")
    lines.append("")
    return "\n".join(lines)


def main() -> None:
    cohort_dir = Path(sys.argv[1]) if len(sys.argv) > 1 else None
    if cohort_dir is None:
        from evals.graph_memory_layer.category_graph_model_study import artifacts_dir_for_today

        cohort_dir = artifacts_dir_for_today()
    if not cohort_dir.is_dir():
        print(f"cohort dir missing: {cohort_dir}", file=sys.stderr)
        sys.exit(2)

    verified = verified_s22_source()
    allowed = {r["source_span_ref_id"] for r in source_packet_rows(verified)}
    run_dirs = sorted(p for p in cohort_dir.iterdir() if p.is_dir() and p.name.startswith("session_22_"))
    runs = [_rescore_run_dir(p, allowed) for p in run_dirs]
    report_md = build_markdown_report(cohort_dir, runs)
    out_path = cohort_dir / "analysis_report.md"
    out_path.write_text(report_md + "\n", encoding="utf-8")
    mirror = Path(__file__).resolve().parents[1] / "artifacts" / "category_graph_model_study" / "last_analysis_report.md"
    mirror.parent.mkdir(parents=True, exist_ok=True)
    mirror.write_text(report_md + "\n", encoding="utf-8")
    print(report_md)
    print(f"\n(wrote {out_path})")


if __name__ == "__main__":
    main()
