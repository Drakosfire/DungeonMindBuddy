from __future__ import annotations

import json
import statistics
from collections import Counter
from pathlib import Path
from typing import Any

from extraction_lab.compare_experiment_runs import METRIC_FIELDS


QUALIFICATION_SCHEMA = "dmb_extraction_repeat_qualification_v1"
LIMITATIONS = [
    "Every pair executes in fixed baseline then candidate order.",
    "Two or three repetitions are a small sample; statistics are descriptive only.",
    "No confidence, significance, winner, readiness, or promotion claim is made.",
    "Every repetition uses isolated cold local caches.",
]


def _read_json(path: str | Path) -> Any:
    return json.loads(Path(path).read_text(encoding="utf-8"))


def _stats(values: list[float | int]) -> dict[str, Any]:
    return {
        "values": values,
        "mean": statistics.fmean(values),
        "min": min(values),
        "max": max(values),
        "pstdev": statistics.pstdev(values),
    }


def _benchmark_contract(receipt: dict[str, Any], side: str) -> dict[str, Any]:
    run = Path(receipt["variants"][side]["extraction_lab_run_path"])
    return _read_json(run / "benchmark_contract.json")


def execution_identity(receipt: dict[str, Any]) -> dict[str, Any]:
    contracts = {
        side: _benchmark_contract(receipt, side) for side in ("baseline", "candidate")
    }
    return {
        "pair_manifest_sha256": receipt["manifest_sha256"],
        "repository_sha": receipt["repository_sha"],
        "surface": receipt["surface"],
        "sources": receipt["sources"],
        "gold": receipt["gold"],
        "model_policy_sha256": receipt["model_policy_sha256"],
        "observed_models": {
            side: receipt["variants"][side]["observed_models"]
            for side in ("baseline", "candidate")
        },
        "benchmark_fingerprints": {
            side: {
                "corpus": contracts[side]["corpus"]["fingerprint"],
                "gold": contracts[side]["gold"]["fingerprint"],
            }
            for side in ("baseline", "candidate")
        },
    }


def identity_mismatch_reason(
    expected: dict[str, Any], actual: dict[str, Any]
) -> str | None:
    checks = (
        ("pair_manifest_sha256", "repeat_pair_manifest_changed"),
        ("repository_sha", "repeat_repository_identity_mismatch"),
        ("sources", "repeat_source_identity_mismatch"),
        ("gold", "repeat_gold_identity_mismatch"),
        ("model_policy_sha256", "repeat_model_policy_mismatch"),
        ("surface", "repeat_surface_mismatch"),
        ("observed_models", "repeat_observed_model_mismatch"),
        ("benchmark_fingerprints", "repeat_benchmark_identity_mismatch"),
    )
    for field, reason in checks:
        if expected[field] != actual[field]:
            return reason
    return None


def _anchor_summary(comparisons: list[dict[str, Any]], kind: str) -> list[dict[str, Any]]:
    grouped: dict[str, list[dict[str, Any]]] = {}
    for comparison in comparisons:
        for row in comparison["anchor_transitions"][kind]:
            grouped.setdefault(row["anchor_id"], []).append(row)
    result = []
    for anchor_id, rows in sorted(grouped.items()):
        baseline_passes = sum(row["baseline_passed"] is True for row in rows)
        candidate_passes = sum(row["candidate_passed"] is True for row in rows)
        result.append(
            {
                "anchor_id": anchor_id,
                "baseline": {
                    "pass_count": baseline_passes,
                    "pass_rate": baseline_passes / len(rows),
                    "fail_buckets": dict(
                        sorted(Counter(row["baseline_fail_bucket"] for row in rows if row["baseline_passed"] is False).items())
                    ),
                },
                "candidate": {
                    "pass_count": candidate_passes,
                    "pass_rate": candidate_passes / len(rows),
                    "fail_buckets": dict(
                        sorted(Counter(row["candidate_fail_bucket"] for row in rows if row["candidate_passed"] is False).items())
                    ),
                },
                "transitions": dict(sorted(Counter(row["transition"] for row in rows).items())),
            }
        )
    return result


def _telemetry(receipts: list[dict[str, Any]]) -> dict[str, Any]:
    mapping = {
        "cost_usd": ("cost_estimate", "estimated_cost_usd"),
        "elapsed_seconds": ("run_window", "elapsed_seconds"),
        "input_tokens": ("tokens", "input_tokens"),
        "output_tokens": ("tokens", "output_tokens"),
        "cached_tokens": ("tokens", "cached_tokens"),
        "api_calls": ("api_calls", "total"),
    }
    sides: dict[str, Any] = {}
    for side in ("baseline", "candidate"):
        side_metrics = {}
        for name, (group, field) in mapping.items():
            values = [r["variants"][side]["telemetry"][group][field] for r in receipts]
            side_metrics[name] = {**_stats(values), "total": sum(values)}
        sides[side] = side_metrics
    pair_costs = [
        sum(r["variants"][side]["telemetry"]["cost_estimate"]["estimated_cost_usd"] for side in ("baseline", "candidate"))
        for r in receipts
    ]
    pair_runtimes = [
        sum(r["variants"][side]["telemetry"]["run_window"]["elapsed_seconds"] for side in ("baseline", "candidate"))
        for r in receipts
    ]
    return {
        **sides,
        "pair": {
            "cost_usd": {**_stats(pair_costs), "total": sum(pair_costs)},
            "runtime_seconds": {**_stats(pair_runtimes), "total": sum(pair_runtimes)},
        },
    }


def qualify_repetitions(receipts: list[dict[str, Any]]) -> dict[str, Any]:
    comparisons = [_read_json(r["comparison"]["artifact_path"]) for r in receipts]
    metrics = {}
    for field in METRIC_FIELDS:
        baseline = [c["metric_deltas"][field]["baseline"] for c in comparisons]
        candidate = [c["metric_deltas"][field]["candidate"] for c in comparisons]
        deltas = [c["metric_deltas"][field]["delta"] for c in comparisons]
        metrics[field] = {
            "baseline": _stats(baseline),
            "candidate": _stats(candidate),
            "delta": {
                **_stats(deltas),
                "sign_counts": {
                    "negative": sum(value < 0 for value in deltas),
                    "zero": sum(value == 0 for value in deltas),
                    "positive": sum(value > 0 for value in deltas),
                },
            },
        }
    identity = execution_identity(receipts[0])
    return {
        "schema": QUALIFICATION_SCHEMA,
        "repetition_count": len(receipts),
        "benchmark_identity": identity["benchmark_fingerprints"],
        "execution_identity": identity,
        "metrics": metrics,
        "anchors": {
            kind: _anchor_summary(comparisons, kind) for kind in ("entity", "fact")
        },
        "telemetry": _telemetry(receipts),
        "limitations": LIMITATIONS,
    }


def render_report(qualification: dict[str, Any]) -> str:
    lines = [
        "# Repeated extraction pair qualification",
        "",
        f"- repetitions: `{qualification['repetition_count']}`",
        "- interpretation: descriptive variability only",
        "",
        "## Metric variability",
    ]
    for field, row in qualification["metrics"].items():
        lines.append(
            f"- `{field}` delta: values `{row['delta']['values']}`, mean `{row['delta']['mean']}`, "
            f"range `{row['delta']['min']}..{row['delta']['max']}`, pstdev `{row['delta']['pstdev']}`"
        )
    lines.extend(["", "## Anchor stability"])
    for kind in ("entity", "fact"):
        lines.append(f"### {kind.title()}")
        for row in qualification["anchors"][kind]:
            lines.append(
                f"- `{row['anchor_id']}`: baseline {row['baseline']['pass_count']}/{qualification['repetition_count']}; "
                f"candidate {row['candidate']['pass_count']}/{qualification['repetition_count']}; transitions {row['transitions']}"
            )
    lines.extend(["", "## Limitations"])
    lines.extend(f"- {item}" for item in qualification["limitations"])
    return "\n".join(lines) + "\n"
