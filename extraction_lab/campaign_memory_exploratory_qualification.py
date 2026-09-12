from __future__ import annotations

import json
from pathlib import Path
from typing import Any


HUMAN_REVIEW_ONLY = "human_review_only"


def _read(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8"))


def qualify_arm(row: dict[str, Any]) -> dict[str, Any]:
    if row.get("status") != "completed":
        raise ValueError("qualification refuses partial/provenance-invalid arm results")
    lab = Path(row["lab_run_path"])
    entities = _read(lab / "entity_results.json")
    facts = _read(lab / "fact_results.json")
    metrics = _read(lab / "aggregate_metrics.json")
    forbidden = {"identity_anchor_recall", "temporal_anchor_recall", "identity_score", "temporal_score"}
    if forbidden.intersection(metrics):
        raise ValueError("identity/temporal human witnesses must not be converted into numeric scores")
    return {
        "model": row["model"],
        "status": row["status"],
        "metrics": metrics,
        "entity_results": entities,
        "fact_results": facts,
        "telemetry": row["telemetry"],
        "counts": row["counts"],
        "identity_temporal_scoring": HUMAN_REVIEW_ONLY,
    }


def qualify_screen(
    receipt: dict[str, Any],
    *,
    allow_stopped: bool = False,
    seven_source_census: dict[str, Any] | None = None,
    full_corpus_census: dict[str, Any] | None = None,
) -> dict[str, Any]:
    arms = receipt.get("arms") or []
    incomplete = (
        receipt.get("status") == "failed"
        or len(arms) != 3
        or any(row.get("status") != "completed" for row in arms)
    )
    if incomplete:
        if allow_stopped:
            return {
                "status": "stopped",
                "failure": receipt.get("failure"),
                "arms": arms,
                "total_cost_usd": receipt.get("total_cost_usd"),
                "identity_temporal_scoring": HUMAN_REVIEW_ONLY,
            }
        raise ValueError("qualification refuses partial/provenance-invalid results")
    if len(arms) != 3:
        raise ValueError("qualification requires exactly three completed model arms")
    models = [row.get("model") for row in arms]
    if models != ["gpt-5.6-luna", "gpt-5.6-terra", "gpt-5.6-sol"]:
        raise ValueError("qualification requires Luna → Terra → Sol order")
    qualified = {row["model"]: qualify_arm(row) for row in arms}
    seven_units = (seven_source_census or {}).get("evidence_unit_count") or 0
    full_units = (full_corpus_census or {}).get("evidence_unit_count") or 0
    scale = (full_units / seven_units) if seven_units else None
    projections = {}
    for model, row in qualified.items():
        cost = float(row["telemetry"]["cost_usd"])
        projections[model] = {
            "seven_source_cost_usd": cost,
            "projected_full_corpus_cost_usd": round(cost * scale, 2) if scale else None,
            "scale_factor_evidence_units": scale,
            "caveats": [
                "single-run uncertainty",
                "seven-source semantic mix may not represent all source classes",
                "output/evidence-unit can vary by document type",
                "cache behavior can vary at corpus scale",
                "planning math, not a guaranteed invoice",
            ],
        }
    return {
        "status": "completed",
        "arms": qualified,
        "projections": projections,
        "identity_temporal_scoring": HUMAN_REVIEW_ONLY,
        "single_run_directional_only": True,
    }
