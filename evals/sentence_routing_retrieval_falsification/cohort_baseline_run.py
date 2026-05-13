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
COHORT_L3_DELTA_SCHEMA_V1 = "dmb_breadcrumb_query_cohort_l3_delta_v1"
COHORT_L3_QUESTION_DELTA_SCHEMA_V1 = "dmb_breadcrumb_query_cohort_l3_question_delta_v1"
COHORT_SCENE_BEAT_QUESTION_DELTA_SCHEMA_V1 = "dmb_breadcrumb_query_cohort_scene_beat_question_delta_v1"
_DEFAULT_DELTA = Path("evals/sentence_routing_retrieval_falsification/artifacts/baselines/cohort_l3_ab_delta_c1s1_to_c1s3_v1.json")
_DEFAULT_QUESTION_DELTA = Path("evals/sentence_routing_retrieval_falsification/artifacts/baselines/cohort_l3_ab_question_delta_c1s1_to_c1s3_v1.json")


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


def run_one_scenario(*, scenario: dict[str, Any], route_equivalence_jsonl: Sequence[Path], workspace_root: Path, per_scenario_out: Path, use_route_equivalence_for_ranking: bool = False, records_jsonl_override: Path | None = None, use_scene_beat_expansion: bool = False, use_scene_beat_packets: bool = False, scene_beat_packet_threshold: int = 16, scene_beat_packet_top_k: int = 3, scene_beat_packet_unit_limit: int = 8, scene_beat_packet_max_packets: int = 2) -> dict[str, Any]:
    cmd = [
        "uv", "run", "python", "-m", "evals.sentence_routing_retrieval_falsification.breadcrumb_query_run",
        "--records-jsonl", str(records_jsonl_override or scenario["records_jsonl"]),
        "--gold", scenario["gold"],
        "--retrieval-only",
        "--output", str(per_scenario_out),
    ]
    for route_path in route_equivalence_jsonl:
        cmd.extend(["--route-equivalence-jsonl", str(route_path)])
    skip_flag = f"--skip-{scenario['scenario_id']}-canvas-refresh"
    if skip_flag in {"--skip-c1s1-canvas-refresh", "--skip-c1s2-canvas-refresh", "--skip-c1s3-canvas-refresh", "--skip-c1s13-canvas-refresh"}:
        cmd.append(skip_flag)
    if use_route_equivalence_for_ranking:
        cmd.append("--use-route-equivalence-for-ranking")
    if use_scene_beat_expansion:
        cmd.extend(["--use-scene-beat-expansion", "--scene-beat-expand-limit", "8"])
    if use_scene_beat_packets:
        cmd.extend(["--use-scene-beat-packets", "--scene-beat-packet-threshold", str(scene_beat_packet_threshold), "--scene-beat-packet-top-k", str(scene_beat_packet_top_k), "--scene-beat-packet-unit-limit", str(scene_beat_packet_unit_limit), "--scene-beat-packet-max-packets", str(scene_beat_packet_max_packets)])
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


def _build_l3_delta(*, manifest: dict[str, Any], baseline_reports: list[dict[str, Any]], equivalence_reports: list[dict[str, Any]], manifest_path: Path, route_paths: list[Path], workspace_root: Path) -> dict[str, Any]:
    scenarios: list[dict[str, Any]] = []
    for scenario, base, with_eq in zip(manifest["scenarios"], baseline_reports, equivalence_reports, strict=True):
        base_violations = sorted({v for row in base["results"] for v in row.get("violations", [])})
        eq_violations = sorted({v for row in with_eq["results"] for v in row.get("violations", [])})
        scenarios.append({
            "scenario_id": scenario["scenario_id"],
            "baseline_all_ok": bool(base.get("all_ok")),
            "with_equivalence_all_ok": bool(with_eq.get("all_ok")),
            "baseline_violations": base_violations,
            "with_equivalence_violations": eq_violations,
            "delta_violation_count": len(eq_violations) - len(base_violations),
        })
    changed = [s for s in scenarios if s["delta_violation_count"] != 0]
    return {
        "schema_id": COHORT_L3_DELTA_SCHEMA_V1,
        "cohort_manifest": _workspace_relative_posix(manifest_path, workspace_root),
        "baseline_schema": COHORT_SUMMARY_SCHEMA_V2,
        "route_equivalence_jsonl": [_workspace_relative_posix(p, workspace_root) for p in route_paths],
        "scenarios": scenarios,
        "delta_summary": {
            "total_scenarios": len(scenarios),
            "scenarios_changed": len(changed),
            "scenarios_improved": sum(1 for s in scenarios if s["delta_violation_count"] < 0),
            "scenarios_regressed": sum(1 for s in scenarios if s["delta_violation_count"] > 0),
            "baseline_all_ok_count": sum(1 for s in scenarios if s["baseline_all_ok"]),
            "with_equivalence_all_ok_count": sum(1 for s in scenarios if s["with_equivalence_all_ok"]),
        },
    }



def _top_hits(row: dict[str, Any], *, limit: int = 5) -> list[dict[str, Any]]:
    hits = list((row.get("full_result") or {}).get("hits") or [])
    out = []
    for h in hits[:limit]:
        out.append({
            "unit_id": str(h.get("unit_id") or ""),
            "score": int(h.get("score") or 0),
            "line_start": int(h.get("line_start") or 0),
            "line_end": int(h.get("line_end") or 0),
            "routes": sorted(str(r.get("normalized_route") or "") for r in (h.get("routes") or []) if isinstance(r, dict)),
            "why_matched": sorted(str(x) for x in (h.get("why_matched") or [])),
        })
    return out


def _classify_question_delta_failure(
    *,
    verdict: str,
    expected_route_substrings: list[str],
    baseline_route_breakdown: dict[str, bool],
    equivalence_route_breakdown: dict[str, bool],
    required_must_hits: list[str],
    baseline_hits: list[str],
    equivalence_hits: list[str],
    min_context_support_ratio: float,
    baseline_context_support_ratio: float,
    equivalence_context_support_ratio: float,
) -> dict[str, object]:
    baseline_missing_route_substrings = [s for s in expected_route_substrings if not baseline_route_breakdown.get(s, False)]
    with_equivalence_missing_route_substrings = [s for s in expected_route_substrings if not equivalence_route_breakdown.get(s, False)]
    lost_route_substrings = [
        s for s in expected_route_substrings if baseline_route_breakdown.get(s, False) and not equivalence_route_breakdown.get(s, False)
    ]
    baseline_required_hits = set(required_must_hits).issubset(set(baseline_hits))
    equivalence_required_hits = set(required_must_hits).issubset(set(equivalence_hits))
    baseline_support_ok = baseline_context_support_ratio >= min_context_support_ratio
    equivalence_support_ok = equivalence_context_support_ratio >= min_context_support_ratio
    reasons: list[str] = []
    if verdict == "unchanged_pass":
        return {
            "bucket": "passed",
            "reasons": ["both_modes_pass"],
            "baseline_missing_route_substrings": baseline_missing_route_substrings,
            "with_equivalence_missing_route_substrings": with_equivalence_missing_route_substrings,
        }
    if verdict == "improved":
        return {
            "bucket": "equivalence_helped",
            "reasons": ["equivalence_mode_passed"],
            "baseline_missing_route_substrings": baseline_missing_route_substrings,
            "with_equivalence_missing_route_substrings": with_equivalence_missing_route_substrings,
        }
    if verdict == "regressed" or lost_route_substrings or (
        baseline_required_hits and not equivalence_required_hits
    ) or (baseline_support_ok and not equivalence_support_ok):
        if verdict == "regressed":
            reasons.append("verdict_regressed")
        if lost_route_substrings:
            reasons.append("equivalence_lost_route_substrings")
        if baseline_required_hits and not equivalence_required_hits:
            reasons.append("equivalence_lost_required_must_hits")
        if baseline_support_ok and not equivalence_support_ok:
            reasons.append("equivalence_lost_context_support_ratio")
        return {
            "bucket": "ranking_regression",
            "reasons": sorted(reasons),
            "baseline_missing_route_substrings": baseline_missing_route_substrings,
            "with_equivalence_missing_route_substrings": with_equivalence_missing_route_substrings,
        }
    if with_equivalence_missing_route_substrings:
        return {
            "bucket": "missing_lexical_handle",
            "reasons": ["equivalence_missing_expected_route_substrings"],
            "baseline_missing_route_substrings": baseline_missing_route_substrings,
            "with_equivalence_missing_route_substrings": with_equivalence_missing_route_substrings,
        }
    if (not equivalence_required_hits) or (not equivalence_support_ok):
        if not equivalence_required_hits:
            reasons.append("equivalence_missing_required_must_hits")
        if not equivalence_support_ok:
            reasons.append("equivalence_context_support_ratio_below_minimum")
        return {
            "bucket": "retriever_support_gap",
            "reasons": sorted(reasons),
            "baseline_missing_route_substrings": baseline_missing_route_substrings,
            "with_equivalence_missing_route_substrings": with_equivalence_missing_route_substrings,
        }
    return {
        "bucket": "gold_or_rubric_gap",
        "reasons": ["no_deterministic_failure_explanation_found"],
        "baseline_missing_route_substrings": baseline_missing_route_substrings,
        "with_equivalence_missing_route_substrings": with_equivalence_missing_route_substrings,
    }


def _build_question_delta(*, manifest: dict[str, Any], baseline_reports: list[dict[str, Any]], equivalence_reports: list[dict[str, Any]], manifest_path: Path, scenario_level_delta_path: Path, workspace_root: Path, include_scene_beat_metadata: bool = False) -> dict[str, Any]:
    scenarios=[]
    summary={"regressed":0,"improved":0,"unchanged_pass":0,"unchanged_fail":0}
    total_q=0
    failure_diagnostic_summary = {
        "passed": 0,
        "equivalence_helped": 0,
        "ranking_regression": 0,
        "missing_lexical_handle": 0,
        "retriever_support_gap": 0,
        "gold_or_rubric_gap": 0,
    }
    for scenario,base,eq in zip(manifest["scenarios"], baseline_reports, equivalence_reports, strict=True):
        gold_path = _resolve_workspace_path(str(scenario["gold"]), workspace_root)
        gold_payload = json.loads(gold_path.read_text(encoding="utf-8"))
        gold_queries = gold_payload.get("queries") or gold_payload.get("scenarios") or []
        gold_by_id = {str(item.get("id") or ""): item for item in gold_queries}
        qrows=[]
        for brow, erow in zip(base["results"], eq["results"], strict=True):
            b_ok=bool(brow.get("ok")); e_ok=bool(erow.get("ok"))
            verdict = "unchanged_pass" if (b_ok and e_ok) else "unchanged_fail" if ((not b_ok) and (not e_ok)) else "improved" if (not b_ok and e_ok) else "regressed"
            summary[verdict]+=1
            question_id = str(brow.get("scenario_id") or "")
            gold_query = gold_by_id.get(question_id) or {}
            required_must_hits = [str(x) for x in (gold_query.get("must_hit_tokens") or [])]
            baseline_hits = sorted(str(x) for x in (brow.get("context_must_hits") or []))
            equivalence_hits = sorted(str(x) for x in (erow.get("context_must_hits") or []))
            b_tokens=set(((brow.get("full_result") or {}).get("trace") or {}).get("query_tokens") or [])
            e_tokens=set(((erow.get("full_result") or {}).get("trace") or {}).get("query_tokens") or [])
            b_units=[h["unit_id"] for h in _top_hits(brow)]
            e_units=[h["unit_id"] for h in _top_hits(erow)]
            b_units_full = [
                str(h.get("unit_id") or "")
                for h in (((brow.get("full_result") or {}).get("hits") or []))
                if str(h.get("unit_id") or "")
            ]
            e_units_full = [
                str(h.get("unit_id") or "")
                for h in (((erow.get("full_result") or {}).get("hits") or []))
                if str(h.get("unit_id") or "")
            ]
            b_break={str(i.get("substring") or ""): bool(i.get("matched")) for i in (brow.get("expected_route_substring_breakdown") or [])}
            e_break={str(i.get("substring") or ""): bool(i.get("matched")) for i in (erow.get("expected_route_substring_breakdown") or [])}
            all_sub=sorted(set(b_break)|set(e_break))
            expected_route_substrings = [str(x) for x in (gold_query.get("expect_route_substrings") or brow.get("expected_route_substrings") or [])]
            failure_diagnostic = _classify_question_delta_failure(
                verdict=verdict,
                expected_route_substrings=expected_route_substrings,
                baseline_route_breakdown=b_break,
                equivalence_route_breakdown=e_break,
                required_must_hits=required_must_hits,
                baseline_hits=baseline_hits,
                equivalence_hits=equivalence_hits,
                min_context_support_ratio=float(gold_query.get("min_context_support_ratio") or brow.get("min_context_support_ratio") or 0.0),
                baseline_context_support_ratio=float(brow.get("context_support_ratio") or 0.0),
                equivalence_context_support_ratio=float(erow.get("context_support_ratio") or 0.0),
            )
            failure_diagnostic_summary[str(failure_diagnostic["bucket"])] += 1
            qrows.append({
                "question_id": question_id,
                "question": str(gold_query.get("question") or brow.get("question") or ""),
                "expected_answer": str(gold_query.get("expected_answer") or brow.get("expected_answer") or ""),
                "must_hit_tokens": required_must_hits,
                "expected_route_substrings": expected_route_substrings,
                "min_context_support_ratio": float(gold_query.get("min_context_support_ratio") or brow.get("min_context_support_ratio") or 0.0),
                "baseline": {
                    "ok": b_ok, "violations": sorted(str(x) for x in (brow.get("violations") or [])),
                    "context_support_ratio": float(brow.get("context_support_ratio") or 0.0),
                    "context_must_hits": baseline_hits,
                    "context_must_hits_missing": [tok for tok in required_must_hits if tok not in set(baseline_hits)],
                    "semantic_verdict": str(brow.get("llm_semantic_verdict") or ""),
                    "expected_route_substring_breakdown": list(brow.get("expected_route_substring_breakdown") or []),
                    "hit_count": len(((brow.get("full_result") or {}).get("hits") or [])),
                    "ranking_augmented_by_equivalences": bool(brow.get("ranking_augmented_by_equivalences")),
                    "top_hits": _top_hits(brow),
                },
                "with_equivalence": {
                    "ok": e_ok, "violations": sorted(str(x) for x in (erow.get("violations") or [])),
                    "context_support_ratio": float(erow.get("context_support_ratio") or 0.0),
                    "context_must_hits": equivalence_hits,
                    "context_must_hits_missing": [tok for tok in required_must_hits if tok not in set(equivalence_hits)],
                    "semantic_verdict": str(erow.get("llm_semantic_verdict") or ""),
                    "expected_route_substring_breakdown": list(erow.get("expected_route_substring_breakdown") or []),
                    "hit_count": len(((erow.get("full_result") or {}).get("hits") or [])),
                    "ranking_augmented_by_equivalences": bool(erow.get("ranking_augmented_by_equivalences")),
                    **({"scene_beat_expansion": erow.get("scene_beat_expansion")} if include_scene_beat_metadata else {}),
                    **({"scene_beat_packets": erow.get("scene_beat_packets")} if include_scene_beat_metadata else {}),
                    "top_hits": _top_hits(erow),
                },
                "delta": {
                    "verdict": verdict,
                    "support_ratio_delta": round(float(erow.get("context_support_ratio") or 0.0)-float(brow.get("context_support_ratio") or 0.0),4),
                    "tokens_added_by_equivalences": sorted(str(x) for x in (e_tokens-b_tokens)),
                    "tokens_removed_by_equivalences": sorted(str(x) for x in (b_tokens-e_tokens)),
                    "topk_units_swapped_in": sorted(set(e_units)-set(b_units)),
                    "topk_units_swapped_out": sorted(set(b_units)-set(e_units)),
                    "full_units_swapped_in": sorted(set(e_units_full) - set(b_units_full)),
                    "full_units_swapped_out": sorted(set(b_units_full) - set(e_units_full)),
                    "substrings_flipped_lost": sorted(s for s in all_sub if b_break.get(s, False) and not e_break.get(s, False)),
                    "substrings_flipped_gained": sorted(s for s in all_sub if (not b_break.get(s, False)) and e_break.get(s, False)),
                },
                "failure_diagnostic": failure_diagnostic,
            })
        total_q += len(qrows)
        scenarios.append({
            "scenario_id": scenario["scenario_id"],
            "question_count": len(qrows),
            "baseline_pass_count": sum(1 for q in qrows if q["baseline"]["ok"]),
            "with_equivalence_pass_count": sum(1 for q in qrows if q["with_equivalence"]["ok"]),
            "questions": qrows,
        })
    return {
        "schema_id": COHORT_L3_QUESTION_DELTA_SCHEMA_V1,
        "cohort_manifest": _workspace_relative_posix(manifest_path, workspace_root),
        "scenario_level_delta_path": _workspace_relative_posix(scenario_level_delta_path, workspace_root),
        "baseline_schema": COHORT_SUMMARY_SCHEMA_V2,
        "question_count": total_q,
        "summary": summary,
        "failure_diagnostic_summary": failure_diagnostic_summary,
        "scenarios": scenarios,
    }

def main() -> int:
    parser = argparse.ArgumentParser(description="Cohort baseline runner")
    mode = parser.add_mutually_exclusive_group()
    mode.add_argument("--write", action="store_true", help="Run the cohort and write the baseline (default).")
    mode.add_argument("--check", action="store_true", help="Run the cohort into a tempdir and byte-compare against --baseline.")
    parser.add_argument("--manifest", type=Path, default=_DEFAULT_MANIFEST)
    parser.add_argument("--baseline", type=Path, default=_DEFAULT_BASELINE)
    parser.add_argument("--delta", type=Path, default=_DEFAULT_DELTA)
    parser.add_argument("--mode", choices=["baseline", "with-equivalence", "both"], default="baseline")
    parser.add_argument("--write-delta", nargs="?", const=str(_DEFAULT_DELTA), default=None)
    parser.add_argument("--check-delta", action="store_true")
    parser.add_argument("--write-question-delta", nargs="?", const=str(_DEFAULT_QUESTION_DELTA), default=None)
    parser.add_argument("--check-question-delta", nargs="?", const=str(_DEFAULT_QUESTION_DELTA), default=None)
    parser.add_argument("--per-scenario-out-dir", type=Path, default=None)
    parser.add_argument("--scene-beat-records-jsonl", type=Path, default=None)
    parser.add_argument("--write-scene-beat-question-delta", type=Path, default=None)
    parser.add_argument("--use-scene-beat-packets", action="store_true")
    parser.add_argument("--scene-beat-packet-threshold", type=int, default=16)
    parser.add_argument("--scene-beat-packet-top-k", type=int, default=3)
    parser.add_argument("--scene-beat-packet-unit-limit", type=int, default=8)
    parser.add_argument("--scene-beat-packet-max-packets", type=int, default=2)
    args = parser.parse_args()
    try:
        if args.check_delta:
            with tempfile.TemporaryDirectory() as tmp:
                tmp_delta = Path(tmp) / "delta.json"
                cmd = [sys.executable, "-m", "evals.sentence_routing_retrieval_falsification.cohort_baseline_run", "--manifest", str(args.manifest), "--mode", "both", "--write-delta", str(tmp_delta)]
                subprocess.run(cmd, cwd=str(_HARNESS_WORKSPACE_ROOT), check=True, capture_output=True, text=True)
                delta_path = (_HARNESS_WORKSPACE_ROOT / args.delta).resolve() if not args.delta.is_absolute() else args.delta
                if tmp_delta.read_bytes() != delta_path.read_bytes():
                    print(f"MISMATCH {_workspace_relative_posix(delta_path, _HARNESS_WORKSPACE_ROOT)}")
                    return 1
                print(f"OK {_workspace_relative_posix(delta_path, _HARNESS_WORKSPACE_ROOT)}")
                return 0
        if args.check:
            return _check_mode(manifest_path=args.manifest, baseline_path=args.baseline, workspace_root=_HARNESS_WORKSPACE_ROOT)
        if args.check_question_delta:
            with tempfile.TemporaryDirectory() as tmp:
                tmp_q = Path(tmp) / "qdelta.json"
                qpath = (_HARNESS_WORKSPACE_ROOT / Path(args.check_question_delta)).resolve() if not Path(args.check_question_delta).is_absolute() else Path(args.check_question_delta)
                expected_qdelta = json.loads(qpath.read_text(encoding="utf-8"))
                active_delta = Path(str(expected_qdelta.get("scenario_level_delta_path") or args.delta))
                cmd = [sys.executable, "-m", "evals.sentence_routing_retrieval_falsification.cohort_baseline_run", "--manifest", str(args.manifest), "--mode", "both", "--write-question-delta", str(tmp_q), "--delta", str(active_delta)]
                subprocess.run(cmd, cwd=str(_HARNESS_WORKSPACE_ROOT), check=True, capture_output=True, text=True)
                if tmp_q.read_bytes() != qpath.read_bytes():
                    print(f"MISMATCH {_workspace_relative_posix(qpath, _HARNESS_WORKSPACE_ROOT)}")
                    return 1
                print(f"OK {_workspace_relative_posix(qpath, _HARNESS_WORKSPACE_ROOT)}")
                return 0
        if args.write_scene_beat_question_delta:
            if args.scene_beat_records_jsonl is None:
                raise ValueError("--write-scene-beat-question-delta requires --scene-beat-records-jsonl")
            manifest_path = (_HARNESS_WORKSPACE_ROOT / args.manifest).resolve() if not args.manifest.is_absolute() else args.manifest
            manifest = load_cohort_manifest(manifest_path)
            route_paths = [_resolve_workspace_path(p, _HARNESS_WORKSPACE_ROOT) for p in manifest["route_equivalence_jsonl"]]
            baseline_reports = []
            scene_reports = []
            with tempfile.TemporaryDirectory() as tmp:
                td = Path(tmp)
                for scenario in manifest["scenarios"]:
                    baseline_reports.append(
                        run_one_scenario(
                            scenario=scenario,
                            route_equivalence_jsonl=route_paths,
                            workspace_root=_HARNESS_WORKSPACE_ROOT,
                            per_scenario_out=td / f"{scenario['scenario_id']}_base.json",
                        )
                    )
                    scene_reports.append(
                        run_one_scenario(
                            scenario=scenario,
                            route_equivalence_jsonl=route_paths,
                            workspace_root=_HARNESS_WORKSPACE_ROOT,
                            per_scenario_out=td / f"{scenario['scenario_id']}_scene.json",
                            records_jsonl_override=args.scene_beat_records_jsonl,
                            use_scene_beat_expansion=True,
                            use_scene_beat_packets=bool(args.use_scene_beat_packets),
                            scene_beat_packet_threshold=int(args.scene_beat_packet_threshold),
                            scene_beat_packet_top_k=int(args.scene_beat_packet_top_k),
                            scene_beat_packet_unit_limit=int(args.scene_beat_packet_unit_limit),
                            scene_beat_packet_max_packets=int(args.scene_beat_packet_max_packets),
                        )
                    )
            qdelta = _build_question_delta(
                manifest=manifest,
                baseline_reports=baseline_reports,
                equivalence_reports=scene_reports,
                manifest_path=manifest_path,
                scenario_level_delta_path=args.write_scene_beat_question_delta,
                workspace_root=_HARNESS_WORKSPACE_ROOT,
                include_scene_beat_metadata=True,
            )
            qdelta["schema_id"] = COHORT_SCENE_BEAT_QUESTION_DELTA_SCHEMA_V1
            qdelta["manifest"] = qdelta.pop("cohort_manifest")
            qdelta["baseline_records_jsonl"] = str(manifest["scenarios"][0]["records_jsonl"]) if manifest.get("scenarios") else None
            qdelta["scene_beat_records_jsonl"] = _workspace_relative_posix(args.scene_beat_records_jsonl, _HARNESS_WORKSPACE_ROOT)
            packet_ids=set(); q_qual=0; q_added=0; total_added=0
            for scen in qdelta.get("scenarios", []):
                scen["with_scene_beats_pass_count"] = scen.pop("with_equivalence_pass_count")
                for q in scen.get("questions", []):
                    q["with_scene_beats"] = q.pop("with_equivalence")
                    pkt=(q.get("with_scene_beats",{}).get("scene_beat_packets") or ((q.get("with_scene_beats",{}).get("full_result") or {}).get("trace") or {}).get("scene_beat_packets") or {})
                    if int(pkt.get("qualified_count") or 0)>0: q_qual+=1
                    if int(pkt.get("units_added") or 0)>0: q_added+=1
                    total_added += int(pkt.get("units_added") or 0)
                    for p in (pkt.get("packets") or []):
                        if isinstance(p, dict) and p.get("beat_id"): packet_ids.add(str(p.get("beat_id")))
            qdelta["scene_beat_packet_summary"]={"questions_with_qualified_packets":q_qual,"questions_with_packet_units_added":q_added,"total_packet_units_added":total_added,"packet_beat_ids":sorted(packet_ids)}
            outp = (_HARNESS_WORKSPACE_ROOT / args.write_scene_beat_question_delta).resolve() if not args.write_scene_beat_question_delta.is_absolute() else args.write_scene_beat_question_delta
            outp.parent.mkdir(parents=True, exist_ok=True)
            outp.write_text(json.dumps(qdelta, indent=2) + "\n", encoding="utf-8")
            return 0
        if args.mode == "both" or args.write_delta or args.write_question_delta:
            manifest_path = (_HARNESS_WORKSPACE_ROOT / args.manifest).resolve() if not args.manifest.is_absolute() else args.manifest
            manifest = load_cohort_manifest(manifest_path)
            route_paths = [_resolve_workspace_path(p, _HARNESS_WORKSPACE_ROOT) for p in manifest["route_equivalence_jsonl"]]
            baseline_reports = []
            equivalence_reports = []
            with tempfile.TemporaryDirectory() as tmp:
                td = Path(tmp)
                for scenario in manifest["scenarios"]:
                    baseline_reports.append(run_one_scenario(scenario=scenario, route_equivalence_jsonl=route_paths, workspace_root=_HARNESS_WORKSPACE_ROOT, per_scenario_out=td / f"{scenario['scenario_id']}_base.json"))
                    equivalence_reports.append(run_one_scenario(scenario=scenario, route_equivalence_jsonl=route_paths, workspace_root=_HARNESS_WORKSPACE_ROOT, per_scenario_out=td / f"{scenario['scenario_id']}_eq.json", use_route_equivalence_for_ranking=True))
            delta = _build_l3_delta(manifest=manifest, baseline_reports=baseline_reports, equivalence_reports=equivalence_reports, manifest_path=manifest_path, route_paths=route_paths, workspace_root=_HARNESS_WORKSPACE_ROOT)
            delta_out_path = Path(args.write_delta) if args.write_delta else args.delta
            delta_out_path = (_HARNESS_WORKSPACE_ROOT / delta_out_path).resolve() if not delta_out_path.is_absolute() else delta_out_path
            if args.write_delta:
                out = delta_out_path
                out.parent.mkdir(parents=True, exist_ok=True)
                out.write_text(json.dumps(delta, indent=2) + "\n", encoding="utf-8")
            if args.write_question_delta:
                qout = Path(args.write_question_delta)
                qout = (_HARNESS_WORKSPACE_ROOT / qout).resolve() if not qout.is_absolute() else qout
                qout.parent.mkdir(parents=True, exist_ok=True)
                qdelta = _build_question_delta(manifest=manifest, baseline_reports=baseline_reports, equivalence_reports=equivalence_reports, manifest_path=manifest_path, scenario_level_delta_path=delta_out_path, workspace_root=_HARNESS_WORKSPACE_ROOT)
                qout.write_text(json.dumps(qdelta, indent=2) + "\n", encoding="utf-8")
            if args.mode == "both":
                return 0
        per_scenario_dir = args.per_scenario_out_dir or _default_per_scenario_dir(args.manifest)
        return _write_mode(manifest_path=args.manifest, baseline_out=args.baseline, per_scenario_out_dir=per_scenario_dir, workspace_root=_HARNESS_WORKSPACE_ROOT)
    except (OSError, ValueError) as exc:
        print(str(exc), file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
