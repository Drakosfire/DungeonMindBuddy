from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any


COMPARISON_SCHEMA_VERSION = 1
METRIC_FIELDS = (
    "entity_anchor_recall",
    "fact_anchor_recall",
    "unresolved_core_anchors",
    "total_entity_count",
    "total_fact_count",
)


def _read_json(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8"))


def _benchmark_contract(
    run_dir: Path, manifest: dict[str, Any]
) -> tuple[dict[str, Any] | None, bool]:
    path = run_dir / "benchmark_contract.json"
    manifest_value = manifest.get("benchmark_contract")
    if path.exists():
        file_value = _read_json(path)
        return file_value, isinstance(
            manifest_value, dict
        ) and file_value != manifest_value
    return (manifest_value if isinstance(manifest_value, dict) else None), False


def _pipeline_differences(
    left: Any, right: Any, prefix: str = ""
) -> list[dict[str, Any]]:
    if isinstance(left, dict) and isinstance(right, dict):
        differences: list[dict[str, Any]] = []
        for key in sorted(set(left) | set(right)):
            field = f"{prefix}.{key}" if prefix else key
            differences.extend(
                _pipeline_differences(left.get(key), right.get(key), field)
            )
        return differences
    if left == right:
        return []
    return [{"field": prefix, "baseline": left, "candidate": right}]


def _anchor_transitions(
    baseline: list[dict[str, Any]], candidate: list[dict[str, Any]]
) -> list[dict[str, Any]]:
    before = {str(row.get("anchor_id")): row for row in baseline}
    after = {str(row.get("anchor_id")): row for row in candidate}
    transitions: list[dict[str, Any]] = []
    for anchor_id in sorted(set(before) | set(after)):
        left = before.get(anchor_id)
        right = after.get(anchor_id)
        left_passed = left.get("passed") if left else None
        right_passed = right.get("passed") if right else None
        if left_passed is False and right_passed is True:
            transition = "improved"
        elif left_passed is True and right_passed is False:
            transition = "regressed"
        else:
            transition = "unchanged"
        transitions.append(
            {
                "anchor_id": anchor_id,
                "transition": transition,
                "baseline_passed": left_passed,
                "candidate_passed": right_passed,
                "baseline_fail_bucket": left.get("fail_bucket")
                if left
                else "anchor_missing",
                "candidate_fail_bucket": right.get("fail_bucket")
                if right
                else "anchor_missing",
            }
        )
    return transitions


def _benchmark_qualification_reasons(
    side: str, manifest: dict[str, Any], contract: dict[str, Any]
) -> list[str]:
    reasons: list[str] = []
    if contract.get("contract_version") != 1:
        reasons.append(f"{side}_benchmark_contract_version_unsupported")
    if manifest.get("surface") != contract.get("surface"):
        reasons.append(f"{side}_benchmark_surface_manifest_mismatch")
    corpus = contract.get("corpus", {})
    if not corpus.get("available") or not corpus.get("fingerprint"):
        reasons.append(f"{side}_benchmark_corpus_identity_unavailable")
    gold = contract.get("gold", {})
    if not gold.get("fingerprint"):
        reasons.append(f"{side}_benchmark_gold_identity_unavailable")
    return reasons


def _render_report(comparison: dict[str, Any]) -> str:
    lines = [
        "# Extraction experiment comparison",
        "",
        f"- baseline: `{comparison['baseline_run_id']}`",
        f"- candidate: `{comparison['candidate_run_id']}`",
        f"- comparable: `{str(comparison['comparable']).lower()}`",
    ]
    if not comparison["comparable"]:
        lines.extend(["", "## Not comparable"])
        lines.extend(f"- {reason}" for reason in comparison["non_comparable_reasons"])
        return "\n".join(lines) + "\n"

    lines.extend(["", "## Pipeline contract differences"])
    differences = comparison["pipeline_contract_differences"]
    lines.extend(
        f"- `{row['field']}`: `{row['baseline']}` → `{row['candidate']}`"
        for row in differences
    )
    if not differences:
        lines.append("- none")
    lines.extend(["", "## Metric deltas"])
    for field, row in comparison["metric_deltas"].items():
        lines.append(
            f"- `{field}`: `{row['baseline']}` → `{row['candidate']}` (delta `{row['delta']}`)"
        )
    for kind in ("entity", "fact"):
        lines.extend(["", f"## {kind.title()} anchor transitions"])
        rows = comparison["anchor_transitions"][kind]
        for row in rows:
            lines.append(
                f"- `{row['anchor_id']}`: **{row['transition']}** "
                f"(`{row['baseline_fail_bucket']}` → `{row['candidate_fail_bucket']}`)"
            )
        if not rows:
            lines.append("- none")
    return "\n".join(lines) + "\n"


def compare_experiment_runs(
    *, baseline_dir: Path, candidate_dir: Path
) -> dict[str, Any]:
    baseline_manifest = _read_json(baseline_dir / "run_manifest.json")
    candidate_manifest = _read_json(candidate_dir / "run_manifest.json")
    baseline_benchmark, baseline_stamp_mismatch = _benchmark_contract(
        baseline_dir, baseline_manifest
    )
    candidate_benchmark, candidate_stamp_mismatch = _benchmark_contract(
        candidate_dir, candidate_manifest
    )
    reasons: list[str] = []
    if baseline_stamp_mismatch:
        reasons.append("baseline_benchmark_contract_stamp_mismatch")
    if candidate_stamp_mismatch:
        reasons.append("candidate_benchmark_contract_stamp_mismatch")
    if baseline_benchmark is None:
        reasons.append("baseline_missing_benchmark_contract_rerun_required")
    if candidate_benchmark is None:
        reasons.append("candidate_missing_benchmark_contract_rerun_required")
    if baseline_benchmark is not None and candidate_benchmark is not None:
        reasons.extend(
            _benchmark_qualification_reasons(
                "baseline", baseline_manifest, baseline_benchmark
            )
        )
        reasons.extend(
            _benchmark_qualification_reasons(
                "candidate", candidate_manifest, candidate_benchmark
            )
        )
        if baseline_benchmark.get("surface") != candidate_benchmark.get("surface"):
            reasons.append("benchmark_surface_mismatch")
        if baseline_benchmark.get("corpus", {}).get(
            "fingerprint"
        ) != candidate_benchmark.get("corpus", {}).get("fingerprint"):
            reasons.append("benchmark_corpus_mismatch")
        if baseline_benchmark.get("gold", {}).get(
            "fingerprint"
        ) != candidate_benchmark.get("gold", {}).get("fingerprint"):
            reasons.append("benchmark_gold_intent_mismatch")

    baseline_pipeline = _read_json(baseline_dir / "pipeline_contract.json")
    candidate_pipeline = _read_json(candidate_dir / "pipeline_contract.json")
    comparison: dict[str, Any] = {
        "schema_version": COMPARISON_SCHEMA_VERSION,
        "baseline_run_id": baseline_manifest.get("run_id"),
        "candidate_run_id": candidate_manifest.get("run_id"),
        "comparable": not reasons,
        "non_comparable_reasons": sorted(set(reasons)),
        "benchmark_identity": {
            "baseline": baseline_benchmark,
            "candidate": candidate_benchmark,
        },
        "pipeline_contract_differences": _pipeline_differences(
            baseline_pipeline, candidate_pipeline
        ),
    }
    if reasons:
        return comparison

    baseline_metrics = _read_json(baseline_dir / "aggregate_metrics.json")
    candidate_metrics = _read_json(candidate_dir / "aggregate_metrics.json")
    comparison["metric_deltas"] = {
        field: {
            "baseline": baseline_metrics.get(field),
            "candidate": candidate_metrics.get(field),
            "delta": candidate_metrics.get(field, 0) - baseline_metrics.get(field, 0),
        }
        for field in METRIC_FIELDS
    }
    comparison["anchor_transitions"] = {
        "entity": _anchor_transitions(
            _read_json(baseline_dir / "entity_results.json"),
            _read_json(candidate_dir / "entity_results.json"),
        ),
        "fact": _anchor_transitions(
            _read_json(baseline_dir / "fact_results.json"),
            _read_json(candidate_dir / "fact_results.json"),
        ),
    }
    return comparison


def write_comparison(
    *, baseline_dir: Path, candidate_dir: Path, out_dir: Path
) -> dict[str, Any]:
    comparison = compare_experiment_runs(
        baseline_dir=baseline_dir, candidate_dir=candidate_dir
    )
    out_dir.mkdir(parents=True, exist_ok=True)
    (out_dir / "comparison.json").write_text(
        json.dumps(comparison, indent=2, sort_keys=True), encoding="utf-8"
    )
    (out_dir / "report.md").write_text(_render_report(comparison), encoding="utf-8")
    return comparison


def _parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Compare two benchmark-qualified Extraction Lab runs."
    )
    parser.add_argument("--baseline", type=Path, required=True)
    parser.add_argument("--candidate", type=Path, required=True)
    parser.add_argument("--out-dir", type=Path, required=True)
    return parser.parse_args()


def main() -> int:
    args = _parse_args()
    result = write_comparison(
        baseline_dir=args.baseline, candidate_dir=args.candidate, out_dir=args.out_dir
    )
    print(
        f"Comparison artifacts written to {args.out_dir}; comparable={str(result['comparable']).lower()}"
    )
    return 0 if result["comparable"] else 2


if __name__ == "__main__":
    raise SystemExit(main())
