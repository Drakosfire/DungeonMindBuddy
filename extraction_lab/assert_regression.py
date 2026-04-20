from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any

NO_WARNING_THRESHOLD = float("inf")

_KNOWN_SURFACES = {"core_extraction", "vertical_slice", "recap_lane", "working_set"}


def _read_json(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8"))


def _pct_drop(current: float, baseline: float) -> float:
    if baseline <= 0.0:
        return 0.0
    return ((baseline - current) / baseline) * 100.0


def _pct_drift(current: float, baseline: float) -> float:
    if baseline == 0.0:
        return 0.0 if current == 0.0 else 100.0
    return abs(((current - baseline) / baseline) * 100.0)


def evaluate_regression(
    *,
    surface: str,
    current_metrics: dict[str, Any],
    baseline_metrics: dict[str, Any] | None,
    thresholds: dict[str, Any],
) -> dict[str, Any]:
    if surface not in _KNOWN_SURFACES:
        return {
            "surface": surface,
            "pass": True,
            "failures": [],
            "warnings": ["unknown_surface"],
        }

    surface_thresholds = thresholds.get(surface, {})
    hard_fail = surface_thresholds.get("hard_fail", {})
    warning = surface_thresholds.get("warning", {})
    failures: list[str] = []
    warnings: list[str] = []

    if surface == "core_extraction":
        # Absolute floor — evaluated even when there is no baseline.
        absolute_floor = surface_thresholds.get("absolute_floor", {})
        if absolute_floor:
            entity_floor = float(absolute_floor.get("entity_anchor_recall_min", 0.0))
            fact_floor = float(absolute_floor.get("fact_anchor_recall_min", 0.0))
            current_entity = float(current_metrics.get("entity_anchor_recall", 0.0))
            current_fact = float(current_metrics.get("fact_anchor_recall", 0.0))
            if current_entity < entity_floor:
                failures.append(
                    f"entity_anchor_recall_below_floor:{current_entity:.3f}<{entity_floor:.3f}"
                )
            if current_fact < fact_floor:
                failures.append(
                    f"fact_anchor_recall_below_floor:{current_fact:.3f}<{fact_floor:.3f}"
                )

        if baseline_metrics is None:
            warnings.append("no_baseline_for_surface")
            return {
                "surface": surface,
                "pass": len(failures) == 0,
                "failures": failures,
                "warnings": warnings,
            }

        entity_drop = _pct_drop(
            float(current_metrics.get("entity_anchor_recall", 0.0)),
            float(baseline_metrics.get("entity_anchor_recall", 0.0)),
        )
        if entity_drop > float(hard_fail.get("entity_anchor_recall_drop_pct", 0.0)):
            failures.append(f"entity_anchor_recall_drop_pct:{entity_drop:.2f}")

        fact_drop = _pct_drop(
            float(current_metrics.get("fact_anchor_recall", 0.0)),
            float(baseline_metrics.get("fact_anchor_recall", 0.0)),
        )
        if fact_drop > float(hard_fail.get("fact_anchor_recall_drop_pct", 0.0)):
            failures.append(f"fact_anchor_recall_drop_pct:{fact_drop:.2f}")

        unresolved_increase = int(current_metrics.get("unresolved_core_anchors", 0)) - int(
            baseline_metrics.get("unresolved_core_anchors", 0)
        )
        if unresolved_increase > int(hard_fail.get("unresolved_core_anchors_increase", 0)):
            failures.append(f"unresolved_core_anchors_increase:{unresolved_increase}")

        entity_drift = _pct_drift(
            float(current_metrics.get("total_entity_count", 0)),
            float(baseline_metrics.get("total_entity_count", 0)),
        )
        if entity_drift > float(warning.get("total_entity_count_drift_pct", NO_WARNING_THRESHOLD)):
            warnings.append(f"total_entity_count_drift_pct:{entity_drift:.2f}")

        fact_drift = _pct_drift(
            float(current_metrics.get("total_fact_count", 0)),
            float(baseline_metrics.get("total_fact_count", 0)),
        )
        if fact_drift > float(warning.get("total_fact_count_drift_pct", NO_WARNING_THRESHOLD)):
            warnings.append(f"total_fact_count_drift_pct:{fact_drift:.2f}")

    elif surface in ("vertical_slice", "recap_lane", "working_set"):
        if baseline_metrics is None:
            warnings.append("no_baseline_for_surface")
            return {
                "surface": surface,
                "pass": True,
                "failures": [],
                "warnings": warnings,
            }

        if surface == "vertical_slice":
            drop = _pct_drop(
                float(current_metrics.get("question_pass_rate", 0.0)),
                float(baseline_metrics.get("question_pass_rate", 0.0)),
            )
            threshold = float(warning.get("question_pass_rate_drop_pct", NO_WARNING_THRESHOLD))
            if drop > threshold:
                warnings.append(f"question_pass_rate_drop_pct:{drop:.2f}")

        elif surface == "recap_lane":
            drop = _pct_drop(
                float(current_metrics.get("event_record_recall", 0.0)),
                float(baseline_metrics.get("event_record_recall", 0.0)),
            )
            threshold = float(warning.get("event_record_recall_drop_pct", NO_WARNING_THRESHOLD))
            if drop > threshold:
                warnings.append(f"event_record_recall_drop_pct:{drop:.2f}")

        # working_set: no thresholds currently defined; pass through.

    return {
        "surface": surface,
        "pass": len(failures) == 0,
        "failures": failures,
        "warnings": warnings,
    }


def _parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Assert extraction baseline regression thresholds.")
    parser.add_argument("--surface", required=True)
    parser.add_argument("--current", type=Path, required=True, help="Current aggregate_metrics.json")
    parser.add_argument("--baseline", type=Path, default=None, help="Baseline aggregate_metrics.json")
    parser.add_argument("--thresholds", type=Path, required=True)
    parser.add_argument("--out", type=Path, default=None, help="Optional regression result output path")
    return parser.parse_args()


def main() -> int:
    args = _parse_args()
    current_metrics = _read_json(args.current)
    baseline_metrics = _read_json(args.baseline) if args.baseline else None
    thresholds = _read_json(args.thresholds)
    result = evaluate_regression(
        surface=args.surface,
        current_metrics=current_metrics,
        baseline_metrics=baseline_metrics,
        thresholds=thresholds,
    )
    if args.out:
        args.out.parent.mkdir(parents=True, exist_ok=True)
        args.out.write_text(json.dumps(result, indent=2, sort_keys=True), encoding="utf-8")
    print(json.dumps(result, indent=2, sort_keys=True))
    return 0 if result["pass"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
