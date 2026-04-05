from __future__ import annotations

from typing import Any


def render_report(
    *,
    run_id: str,
    surface: str,
    aggregate_metrics: dict[str, Any],
    entity_results: list[dict[str, Any]],
    fact_results: list[dict[str, Any]],
) -> str:
    entity_pass = sum(1 for row in entity_results if row.get("passed"))
    fact_pass = sum(1 for row in fact_results if row.get("passed"))
    lines = [
        "# Extraction Lab Report",
        "",
        f"- run_id: `{run_id}`",
        f"- surface: `{surface}`",
        "",
        "## Aggregate Metrics",
        f"- entity_anchor_recall: `{aggregate_metrics.get('entity_anchor_recall', 0.0):.4f}`",
        f"- fact_anchor_recall: `{aggregate_metrics.get('fact_anchor_recall', 0.0):.4f}`",
        f"- unresolved_core_anchors: `{aggregate_metrics.get('unresolved_core_anchors', 0)}`",
        f"- total_entity_count: `{aggregate_metrics.get('total_entity_count', 0)}`",
        f"- total_fact_count: `{aggregate_metrics.get('total_fact_count', 0)}`",
        "",
        "## Resolution Summary",
        f"- entity anchors passed: `{entity_pass}/{len(entity_results)}`",
        f"- fact anchors passed: `{fact_pass}/{len(fact_results)}`",
    ]
    return "\n".join(lines) + "\n"
