from __future__ import annotations

import argparse
import json
import subprocess
import sys
import tempfile
from datetime import UTC, datetime
from pathlib import Path
from typing import Any, Sequence

from evals.sentence_routing_retrieval_falsification.route_equivalence_shadow import (
    load_route_equivalence_shadow_records,
)
from src.lexicon_phase_b.schemas import RouteEquivalenceRecord

_HARNESS_WORKSPACE_ROOT = Path(__file__).resolve().parents[2]
_DEFAULT_MANIFEST = Path("evals/sentence_routing_retrieval_falsification/cohorts/c1s1_to_c1s3_v1.json")
_DEFAULT_BASELINE = Path("evals/sentence_routing_retrieval_falsification/artifacts/baselines/cohort_baseline_c1s1_to_c1s3_v2.json")

COHORT_MANIFEST_SCHEMA_V1 = "dmb_breadcrumb_query_cohort_manifest_v1"
COHORT_SUMMARY_SCHEMA_V2 = "dmb_breadcrumb_query_cohort_summary_v2"


def _workspace_relative_posix(path: Path, workspace_root: Path) -> str:
    try:
        return path.resolve().relative_to(workspace_root.resolve()).as_posix()
    except ValueError:
        return path.name


def _resolve_workspace_path(path_text: str, workspace_root: Path) -> Path:
    path = Path(path_text)
    if path.is_absolute():
        raise ValueError(f"manifest path must be workspace-relative: {path_text}")
    return workspace_root / path


def load_cohort_manifest(manifest_path: Path) -> dict[str, Any]:
    data = json.loads(manifest_path.read_text(encoding="utf-8"))
    if data.get("schema") != COHORT_MANIFEST_SCHEMA_V1:
        raise ValueError(f"unsupported cohort manifest schema: {data.get('schema')!r}")
    for route_path in data.get("route_equivalence_jsonl", []):
        resolved = _resolve_workspace_path(route_path, _HARNESS_WORKSPACE_ROOT)
        if not resolved.is_file():
            raise ValueError(f"missing route equivalence jsonl: {route_path}")
    for scenario in data.get("scenarios", []):
        for key in ("gold", "records_jsonl"):
            resolved = _resolve_workspace_path(str(scenario[key]), _HARNESS_WORKSPACE_ROOT)
            if not resolved.is_file():
                raise ValueError(f"missing scenario path ({scenario['scenario_id']}:{key}): {scenario[key]}")
    return data


def run_one_scenario(*, scenario: dict[str, Any], route_equivalence_jsonl: Sequence[Path], workspace_root: Path, per_scenario_out: Path) -> dict[str, Any]:
    cmd = [
        "uv", "run", "python", "-m", "evals.sentence_routing_retrieval_falsification.breadcrumb_query_run",
        "--records-jsonl", scenario["records_jsonl"],
        "--gold", scenario["gold"],
        "--retrieval-only",
        "--output", str(per_scenario_out),
    ]
    for route_path in route_equivalence_jsonl:
        cmd.extend(["--route-equivalence-jsonl", str(route_path)])
    cmd.extend(["--skip-c1s1-canvas-refresh", "--skip-c1s2-canvas-refresh", "--skip-c1s3-canvas-refresh"])
    try:
        subprocess.run(cmd, capture_output=True, text=True, cwd=str(workspace_root), check=True)
    except subprocess.CalledProcessError as exc:
        print(exc.stderr, file=sys.stderr)
        raise ValueError(f"scenario {scenario['scenario_id']} failed") from exc
    return json.loads(per_scenario_out.read_text(encoding="utf-8"))


def _normalize_substring_to_slug(s: str) -> str:
    return s.split("/")[-1].strip().lower().replace("_", "-")


def _equivalence_can_rescue(slug: str, records: list[RouteEquivalenceRecord]) -> bool:
    if not slug:
        return False
    return any(slug in record.from_route_id.lower() or slug in record.to_route_id.lower() for record in records)


def _aggregate_question_breakdowns(per_question_breakdowns: list[list[dict[str, Any]]]) -> list[dict[str, Any]]:
    ordered_substrings: list[str] = []
    matched_by_substring: dict[str, bool] = {}
    for question_breakdown in per_question_breakdowns:
        for item in question_breakdown:
            substring = str(item.get("substring") or "")
            if substring not in matched_by_substring:
                ordered_substrings.append(substring)
                matched_by_substring[substring] = False
            matched_by_substring[substring] = matched_by_substring[substring] or bool(item.get("matched"))
    return [{"substring": substring, "matched": matched_by_substring[substring]} for substring in ordered_substrings]


def _compute_recall_via_equivalence(*, breakdown: list[dict[str, Any]], records: list[RouteEquivalenceRecord]) -> dict[str, Any] | None:
    missed_substrings = sorted({str(item.get("substring") or "") for item in breakdown if not bool(item.get("matched"))})
    if not missed_substrings:
        return None
    rescued_substrings = sorted(
        substring for substring in missed_substrings if _equivalence_can_rescue(_normalize_substring_to_slug(substring), records)
    )
    still_missing_substrings = sorted(set(missed_substrings) - set(rescued_substrings))
    missed_count = len(missed_substrings)
    rescued_count = len(rescued_substrings)
    return {
        "missed_substrings": missed_substrings,
        "rescued_substrings": rescued_substrings,
        "still_missing_substrings": still_missing_substrings,
        "missed_count": missed_count,
        "rescued_count": rescued_count,
        "recall": round(rescued_count / missed_count, 4),
    }


def build_cohort_summary(*, manifest: dict[str, Any], per_scenario_reports: list[dict[str, Any]], workspace_root: Path, manifest_path: Path, route_equivalence_records: list[RouteEquivalenceRecord]) -> dict[str, Any]:
    scenarios_out: list[dict[str, Any]] = []
    for scenario, report in zip(manifest["scenarios"], per_scenario_reports, strict=True):
        results = report["results"]
        first_shadow = results[0].get("shadow_route_equivalences") if results else None
        for row in results:
            if row.get("shadow_route_equivalences") != first_shadow:
                raise ValueError(f"scenario {scenario['scenario_id']} has inconsistent shadow_route_equivalences")
        pass_count = sum(1 for row in results if row["ok"])
        fail_count = len(results) - pass_count
        scenario_recall = _compute_recall_via_equivalence(
            breakdown=_aggregate_question_breakdowns([list(row.get("expected_route_substring_breakdown") or []) for row in results]),
            records=route_equivalence_records,
        )
        scenarios_out.append({
            "scenario_id": scenario["scenario_id"],
            "gold": scenario["gold"],
            "records_jsonl": scenario["records_jsonl"],
            "session_number": scenario["session_number"],
            "gold_schema": report["gold_schema"],
            "all_ok": report["all_ok"],
            "scenario_count": len(results),
            "pass_count": pass_count,
            "fail_count": fail_count,
            "violations": [
                {"scenario_id": row["scenario_id"], "ok": row["ok"], "violations": sorted(row["violations"])}
                for row in results
            ],
            "shadow_route_equivalences": first_shadow,
            "recall_via_equivalence": scenario_recall,
        })
    total_questions = sum(item["scenario_count"] for item in scenarios_out)
    total_pass = sum(item["pass_count"] for item in scenarios_out)
    total_fail = sum(item["fail_count"] for item in scenarios_out)
    scenario_recalls = [item["recall_via_equivalence"]["recall"] for item in scenarios_out if item["recall_via_equivalence"] is not None]
    return {
        "schema": COHORT_SUMMARY_SCHEMA_V2,
        "cohort_id": manifest["cohort_id"],
        "manifest": _workspace_relative_posix(manifest_path, workspace_root),
        "campaign_id": manifest["campaign_id"],
        "route_equivalence_jsonl": list(manifest["route_equivalence_jsonl"]),
        "retrieval_only": True,
        "llm_enabled": False,
        "scenarios": scenarios_out,
        "aggregate": {
            "total_questions": total_questions,
            "total_pass": total_pass,
            "total_fail": total_fail,
            "all_scenarios_all_ok": all(item["all_ok"] for item in scenarios_out),
        },
        "recall_via_equivalence_aggregate": {
            "scenarios_with_misses": len(scenario_recalls),
            "min": min(scenario_recalls) if scenario_recalls else None,
            "mean": round(sum(scenario_recalls) / len(scenario_recalls), 4) if scenario_recalls else None,
            "max": max(scenario_recalls) if scenario_recalls else None,
        },
    }


def _default_per_scenario_dir(manifest: Path) -> Path:
    cohort_id = json.loads(manifest.read_text(encoding="utf-8"))["cohort_id"]
    day = datetime.now(UTC).date().isoformat()
    return Path(f"evals/sentence_routing_retrieval_falsification/artifacts/runs/{day}/cohort_{cohort_id}")


def _write_mode(*, manifest_path: Path, baseline_out: Path, per_scenario_out_dir: Path, workspace_root: Path) -> int:
    manifest_path = (workspace_root / manifest_path).resolve() if not manifest_path.is_absolute() else manifest_path
    baseline_out = (workspace_root / baseline_out).resolve() if not baseline_out.is_absolute() else baseline_out
    per_scenario_out_dir = (workspace_root / per_scenario_out_dir).resolve() if not per_scenario_out_dir.is_absolute() else per_scenario_out_dir
    manifest = load_cohort_manifest(manifest_path)
    route_paths = [_resolve_workspace_path(p, workspace_root) for p in manifest["route_equivalence_jsonl"]]
    route_equivalence_records = load_route_equivalence_shadow_records(route_paths)
    per_scenario_out_dir.mkdir(parents=True, exist_ok=True)
    reports = []
    for scenario in manifest["scenarios"]:
        out_file = per_scenario_out_dir / f"{scenario['scenario_id']}_retrieval_baseline.json"
        reports.append(run_one_scenario(scenario=scenario, route_equivalence_jsonl=route_paths, workspace_root=workspace_root, per_scenario_out=out_file))
    summary = build_cohort_summary(
        manifest=manifest,
        per_scenario_reports=reports,
        workspace_root=workspace_root,
        manifest_path=manifest_path,
        route_equivalence_records=route_equivalence_records,
    )
    baseline_out.parent.mkdir(parents=True, exist_ok=True)
    baseline_out.write_text(json.dumps(summary, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    return 0


def _check_mode(*, manifest_path: Path, baseline_path: Path, workspace_root: Path) -> int:
    baseline_path = (workspace_root / baseline_path).resolve() if not baseline_path.is_absolute() else baseline_path
    if not baseline_path.exists():
        print(f"MISSING {_workspace_relative_posix(baseline_path, workspace_root)}", file=sys.stderr)
        return 1
    with tempfile.TemporaryDirectory() as tmp:
        tmp_dir = Path(tmp)
        generated = tmp_dir / baseline_path.name
        per_scenario_tmp = tmp_dir / "per_scenario"
        per_scenario_tmp.mkdir()
        _write_mode(manifest_path=manifest_path, baseline_out=generated, per_scenario_out_dir=per_scenario_tmp, workspace_root=workspace_root)
        if generated.read_bytes() != baseline_path.read_bytes():
            print(f"MISMATCH {_workspace_relative_posix(baseline_path, workspace_root)}")
            return 1
        print(f"OK {_workspace_relative_posix(baseline_path, workspace_root)}")
        return 0


def main() -> int:
    parser = argparse.ArgumentParser(description="Cohort baseline runner")
    mode = parser.add_mutually_exclusive_group()
    mode.add_argument("--write", action="store_true", help="Run the cohort and write the baseline (default).")
    mode.add_argument("--check", action="store_true", help="Run the cohort into a tempdir and byte-compare against --baseline.")
    parser.add_argument("--manifest", type=Path, default=_DEFAULT_MANIFEST)
    parser.add_argument("--baseline", type=Path, default=_DEFAULT_BASELINE)
    parser.add_argument("--per-scenario-out-dir", type=Path, default=None)
    args = parser.parse_args()
    try:
        if args.check:
            return _check_mode(manifest_path=args.manifest, baseline_path=args.baseline, workspace_root=_HARNESS_WORKSPACE_ROOT)
        per_scenario_dir = args.per_scenario_out_dir or _default_per_scenario_dir(args.manifest)
        return _write_mode(manifest_path=args.manifest, baseline_out=args.baseline, per_scenario_out_dir=per_scenario_dir, workspace_root=_HARNESS_WORKSPACE_ROOT)
    except (OSError, ValueError) as exc:
        print(str(exc), file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
