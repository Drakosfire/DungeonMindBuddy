"""When a second LLM pass is justified after single-pass unit-annotation ingest."""

from __future__ import annotations

from typing import Any, Literal

SecondPassDecision = Literal["single_pass_sufficient", "second_pass_recommended", "insufficient_data"]

# Measured dimensions for C1S13-style gold comparison (shape vs semantic split).
MEASUREMENT_DIMENSIONS: tuple[str, ...] = (
    "shape_validity",
    "beat_unit_membership",
    "beat_contiguity",
    "location_routes_and_labels",
    "present_population",
    "mentioned_only_population",
    "route_tag_recall",
)

# Dominant failure modes that may justify a specialized second pass (first pass stays scaffold).
SECOND_PASS_FAILURE_MODES: tuple[str, ...] = (
    "population_carry",
    "beat_boundary_drift",
    "location_roster_specialist",
)

# Minimum pass rate on a dimension before treating single-pass as closed (N>=3 trials).
DEFAULT_DIMENSION_PASS_FLOOR = 0.8

# Second pass only when one mode dominates misses and route tagging does not regress.
SECOND_PASS_DOMINANCE_SHARE = 0.6


def evaluate_second_pass_need(
    report: dict[str, Any],
    *,
    dimension_pass_floor: float = DEFAULT_DIMENSION_PASS_FLOOR,
    dominance_share: float = SECOND_PASS_DOMINANCE_SHARE,
) -> dict[str, Any]:
    """Return recommendation from a cohort report with per-dimension pass rates and failure counts."""
    dimensions = report.get("dimension_pass_rates") or {}
    failures_by_mode = report.get("failures_by_mode") or {}
    route_regression = bool(report.get("route_tag_regression_vs_baseline"))

    if not dimensions:
        return {
            "decision": "insufficient_data",
            "rationale": "missing dimension_pass_rates",
            "failure_mode": None,
        }

    weak = [d for d in MEASUREMENT_DIMENSIONS if float(dimensions.get(d, 0.0)) < dimension_pass_floor]
    if not weak:
        return {
            "decision": "single_pass_sufficient",
            "rationale": "all measured dimensions at or above pass floor",
            "failure_mode": None,
        }

    if route_regression:
        return {
            "decision": "single_pass_sufficient",
            "rationale": "route tagging regressed; do not add a second pass until single-pass routes recover",
            "failure_mode": None,
        }

    total_failures = sum(int(failures_by_mode.get(m, 0)) for m in SECOND_PASS_FAILURE_MODES)
    if total_failures <= 0:
        return {
            "decision": "single_pass_sufficient",
            "rationale": "weak dimensions without separable second-pass failure modes",
            "failure_mode": None,
        }

    dominant = max(SECOND_PASS_FAILURE_MODES, key=lambda m: int(failures_by_mode.get(m, 0)))
    dominant_count = int(failures_by_mode.get(dominant, 0))
    if dominant_count / total_failures < dominance_share:
        return {
            "decision": "single_pass_sufficient",
            "rationale": "no single failure mode dominates; tighten unified prompt first",
            "failure_mode": None,
        }

    return {
        "decision": "second_pass_recommended",
        "rationale": (
            f"dominant separable failure mode {dominant!r} "
            f"({dominant_count}/{total_failures} classified failures)"
        ),
        "failure_mode": dominant,
    }
