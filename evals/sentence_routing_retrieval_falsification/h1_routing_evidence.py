"""Hypothesis 1 tooling — classify ``route_sentence_units_to_hubs`` failures (legacy: Stage B) and compute directional scorecards.

See plan: Reanchor on Goals + Hypothesis 1 (party vs generic group vs named PCs).

Run::

    uv run python -m evals.sentence_routing_retrieval_falsification.h1_routing_evidence scan-artifacts

    uv run python -m evals.sentence_routing_retrieval_falsification.h1_routing_evidence scorecard \\
        --sidecar evals/sentence_routing_retrieval_falsification/artifacts/runs/.../....json \\
        --scenario-json evals/sentence_routing_retrieval_falsification/gold/scenario_c1_session1_pc.json

    uv run python -m evals.sentence_routing_retrieval_falsification.h1_routing_evidence summarize-cohort \\
        evals/sentence_routing_retrieval_falsification/artifacts/runs/2026-04-25/sentence_routing_stage_b_cohort_summary--....json
"""

from __future__ import annotations

import argparse
import json
import re
from collections import Counter
from pathlib import Path
from typing import Any

_VIOL_UNIT_RE = re.compile(r"unit '([^']+)'")
_PARTY_KW_RE = re.compile(
    r"\b(team|teammates|first combat|bring the team together|our team)\b",
    re.IGNORECASE,
)
_GENERIC_GROUP_RE = re.compile(r"\bthe group\b", re.IGNORECASE)
_PRONOUN_LED_RE = re.compile(r"^\s*(he|she|they)\b", re.IGNORECASE)


FailureBucket = str  # keep as plain str for JSON dumps


def classify_stage_b_violation(violation: str, *, unit_text: str = "") -> FailureBucket:
    """Map a single ``violations.stage_b`` string into an H1 evidence bucket."""
    v = (violation or "").strip()
    ut = (unit_text or "").strip()
    ut_lower = ut.lower()
    party_kw = bool(_PARTY_KW_RE.search(ut_lower))
    generic_group = bool(_GENERIC_GROUP_RE.search(ut_lower)) and not party_kw
    pronoun_led = bool(_PRONOUN_LED_RE.match(ut)) and not party_kw

    if v.startswith("B0:"):
        return "schema_row_integrity"
    if v.startswith("B2:") and "needs_new_hub_candidate" in v:
        return "out_of_manifest_candidate"
    if v.startswith("B1:") and "missing expected hubs" in v:
        if party_kw:
            return "party_reference_boundary"
        if pronoun_led:
            return "pronoun_carryover"
        return "named_pc_omission"
    if v.startswith("B1:") and "over-route" in v:
        return "party_reference_boundary"
    if v.startswith("B2:") and "hubs > max_assigned_hubs" in v:
        if generic_group or party_kw:
            return "party_reference_boundary"
        return "named_pc_omission"
    return "named_pc_omission"


def _unit_text_by_id(sidecar: dict[str, Any]) -> dict[str, str]:
    out: dict[str, str] = {}
    for u in sidecar.get("sentence_units") or []:
        if not isinstance(u, dict):
            continue
        uid = str(u.get("unit_id") or "").strip()
        if uid:
            out[uid] = str(u.get("text") or "")
    return out


def classify_sidecar_violations(sidecar: dict[str, Any]) -> list[tuple[str, FailureBucket]]:
    """Return (violation, bucket) for each ``stage_b`` violation."""
    vb = sidecar.get("violations") or {}
    raw = vb.get("stage_b") if isinstance(vb, dict) else None
    if not isinstance(raw, list):
        return []
    by_uid = _unit_text_by_id(sidecar)
    out: list[tuple[str, FailureBucket]] = []
    for line in raw:
        if not isinstance(line, str):
            continue
        m = _VIOL_UNIT_RE.search(line)
        uid = m.group(1) if m else ""
        ut = by_uid.get(uid, "")
        out.append((line, classify_stage_b_violation(line, unit_text=ut)))
    return out


def h1_decision_from_counts(counts: Counter[str]) -> tuple[str, str]:
    """Return (verdict, one_line_rationale) for Hypothesis 1."""
    party = int(counts.get("party_reference_boundary", 0))
    named = int(counts.get("named_pc_omission", 0))
    schema = int(counts.get("schema_row_integrity", 0))
    total = sum(counts.values()) or 1
    if schema > party and schema >= named:
        return (
            "REJECT_H1",
            "schema_row_integrity dominates; failures are not primarily party-vs-group boundary confusion.",
        )
    if party > named and party >= max(1, total // 4):
        return (
            "ACCEPT_H1",
            "party_reference_boundary is the plurality vs named_pc_omission; boundary confusion is the dominant failure mode.",
        )
    if named > party:
        return (
            "REJECT_H1",
            "named_pc_omission dominates; tighten named affected/listener PC routing before party-language rules.",
        )
    return (
        "INCONCLUSIVE",
        "no clear plurality between party_reference_boundary and named_pc_omission; gather more runs or refine gold rows.",
    )


def compute_directional_scorecard(
    *,
    scenario: dict[str, Any],
    sidecar: dict[str, Any],
    whole_party_min_expected: int = 4,
) -> dict[str, Any]:
    """Soft metrics alongside binary PASS/FAIL (diagnostic only)."""
    from evals.sentence_routing_retrieval_falsification.grader import normalize_gold_routing_matches
    from evals.sentence_routing_retrieval_falsification.route_schema import (
        HubManifestEntry,
        manifest_slug_set,
        parse_routes_envelope,
    )

    units = list(sidecar.get("sentence_units") or [])
    gold_raw = dict((scenario.get("gold_routing") or {}))
    gold_norm, gold_errors = normalize_gold_routing_matches(gold_raw, units)
    manifest = list((scenario.get("input") or {}).get("hub_manifest") or [])
    manifest_slugs = manifest_slug_set([HubManifestEntry.model_validate(x) for x in manifest])

    routes_payload = {"schema": "sentence_hub_routes_v1", "routes": sidecar.get("routes") or []}
    envelope = parse_routes_envelope(routes_payload)
    by_id = {r.unit_id: r for r in envelope.routes}

    must_route = [g for g in (gold_norm.get("must_route") or []) if isinstance(g, dict)]
    must_abstain = [g for g in (gold_norm.get("must_abstain") or []) if isinstance(g, dict)]

    party_rows: list[dict[str, Any]] = []
    named_rows: list[dict[str, Any]] = []
    for g in must_route:
        exp = [str(x).strip() for x in (g.get("expected_hubs") or []) if str(x).strip()]
        uid = str(g.get("unit_id") or "").strip()
        if len(exp) >= whole_party_min_expected:
            party_rows.append({"unit_id": uid, "expected": exp})
        elif exp:
            named_rows.append({"unit_id": uid, "expected": exp})

    def _slot_recall(rows: list[dict[str, Any]]) -> float | None:
        if not rows:
            return None
        slots_ok = 0
        slots_total = 0
        for row in rows:
            uid = row["unit_id"]
            exp = row["expected"]
            r = by_id.get(uid)
            if r is None:
                slots_total += len(exp)
                continue
            assigned = set(r.assigned_hubs)
            for h in exp:
                slots_total += 1
                if h in assigned:
                    slots_ok += 1
        return round(slots_ok / slots_total, 6) if slots_total else None

    abstain_strict = 0
    abstain_total = 0
    abstain_candidate_pin_ok = 0
    abstain_candidate_pin_total = 0
    for g in must_abstain:
        uid = str(g.get("unit_id") or "").strip()
        max_a = int(g.get("max_assigned_hubs", 0))
        r = by_id.get(uid)
        if r is None:
            continue
        abstain_total += 1
        if max_a == 0 and len(r.assigned_hubs) == 0:
            abstain_strict += 1
        if g.get("needs_new_hub_candidate") is False:
            abstain_candidate_pin_total += 1
            if not r.needs_new_hub_candidate:
                abstain_candidate_pin_ok += 1

    by_uid_text = _unit_text_by_id(sidecar)
    generic_group_abstain = 0
    generic_group_abstain_ok = 0
    for g in must_abstain:
        uid = str(g.get("unit_id") or "").strip()
        if int(g.get("max_assigned_hubs", 0)) != 0:
            continue
        ut = by_uid_text.get(uid, "")
        if not (
            bool(_GENERIC_GROUP_RE.search(ut.lower()))
            and not bool(_PARTY_KW_RE.search(ut.lower()))
        ):
            continue
        generic_group_abstain += 1
        r = by_id.get(uid)
        if r is not None and len(r.assigned_hubs) == 0:
            generic_group_abstain_ok += 1

    named_pc_recall = _slot_recall(named_rows)
    party_slot = _slot_recall(party_rows)
    party_boundary_precision = (
        round(generic_group_abstain_ok / generic_group_abstain, 6)
        if generic_group_abstain
        else None
    )
    candidate_sanity = (
        round(abstain_candidate_pin_ok / abstain_candidate_pin_total, 6)
        if abstain_candidate_pin_total
        else None
    )
    return {
        "gold_normalization_errors": gold_errors,
        # Plan-aligned names (directional layer)
        "named_pc_recall": named_pc_recall,
        "party_boundary_precision": party_boundary_precision,
        "candidate_sanity": candidate_sanity,
        # Implementation detail / aliases
        "named_pc_slot_recall": named_pc_recall,
        "party_slot_recall": party_slot,
        "abstain_zero_hub_rate": round(abstain_strict / abstain_total, 6) if abstain_total else None,
        "abstain_candidate_pin_rate": candidate_sanity,
        "generic_group_abstain_precision": party_boundary_precision,
        "generic_group_abstain_rows": generic_group_abstain,
        "manifest_slug_count": len(manifest_slugs),
    }


def _default_runs_root() -> Path:
    return Path(__file__).resolve().parent / "artifacts" / "runs"


def scan_fail_artifacts(
    runs_root: Path,
    *,
    name_substr: str = "_pc--FAIL",
) -> list[Path]:
    paths: list[Path] = []
    root = runs_root.resolve()
    if not root.is_dir():
        return paths
    for p in sorted(root.rglob("sentence_routing_stage_b_hub_routes--*.json")):
        if name_substr in p.name:
            try:
                side = json.loads(p.read_text(encoding="utf-8"))
            except OSError:
                continue
            if side.get("pass") is False:
                paths.append(p)
    return paths


def cmd_scan_artifacts(ns: argparse.Namespace) -> int:
    root = Path(ns.runs_root).resolve() if ns.runs_root else _default_runs_root()
    paths = scan_fail_artifacts(root, name_substr=ns.name_substr)
    totals: Counter[str] = Counter()
    per_file: list[dict[str, Any]] = []
    for p in paths:
        side = json.loads(p.read_text(encoding="utf-8"))
        pairs = classify_sidecar_violations(side)
        c = Counter(b for _, b in pairs)
        totals.update(c)
        per_file.append(
            {
                "path": str(p),
                "scenario_id": side.get("scenario_id"),
                "buckets": dict(c),
            }
        )
    verdict, why = h1_decision_from_counts(totals)
    out = {
        "runs_root": str(root),
        "fail_sidecar_count": len(paths),
        "aggregate_violation_buckets": dict(totals),
        "h1_verdict": verdict,
        "h1_rationale": why,
        "per_file": per_file,
    }
    print(json.dumps(out, indent=2, ensure_ascii=False))
    return 0


def cmd_scorecard(ns: argparse.Namespace) -> int:
    side_path = Path(ns.sidecar).resolve()
    scen_path = Path(ns.scenario_json).resolve()
    side = json.loads(side_path.read_text(encoding="utf-8"))
    scenario = json.loads(scen_path.read_text(encoding="utf-8"))
    vb = side.get("violations") or {}
    vlist = vb.get("stage_b") if isinstance(vb, dict) else []
    pairs = classify_sidecar_violations(side)
    c = Counter(b for _, b in pairs)
    verdict, why = h1_decision_from_counts(c)
    payload = {
        "sidecar": str(side_path),
        "scenario_json": str(scen_path),
        "gates_passed": side.get("pass"),
        "scenario_estimated_cost_usd": side.get("scenario_estimated_cost_usd"),
        "violation_bucket_counts": dict(c),
        "violations_classified": [{"violation": a, "bucket": b} for a, b in pairs],
        "h1_verdict": verdict,
        "h1_rationale": why,
        "directional_scorecard": compute_directional_scorecard(scenario=scenario, sidecar=side),
    }
    print(json.dumps(payload, indent=2, ensure_ascii=False))
    return 0


def cmd_aggregate_summaries(ns: argparse.Namespace) -> int:
    totals: Counter[str] = Counter()
    metas: list[dict[str, Any]] = []
    for raw in ns.cohort_json:
        p = Path(raw).resolve()
        cohort = json.loads(p.read_text(encoding="utf-8"))
        runs = cohort.get("runs") or []
        for r in runs:
            if not isinstance(r, dict):
                continue
            sp = Path(str(r.get("sidecar_json") or "")).resolve()
            if not sp.is_file():
                continue
            side = json.loads(sp.read_text(encoding="utf-8"))
            pairs = classify_sidecar_violations(side)
            totals.update(b for _, b in pairs)
        metas.append(
            {
                "cohort": str(p),
                "scenario_id": cohort.get("scenario_id"),
                "n": cohort.get("n"),
                "pass_rate": cohort.get("pass_rate"),
                "cost_usd": cohort.get("cost_usd"),
            }
        )
    verdict, why = h1_decision_from_counts(totals)
    out = {
        "cohorts": metas,
        "aggregate_violation_buckets": dict(totals),
        "h1_verdict": verdict,
        "h1_rationale": why,
    }
    print(json.dumps(out, indent=2, ensure_ascii=False))
    return 0


def _bucket_for_thresholds(violation: str) -> str:
    v = (violation or "").strip()
    if v.startswith("B0:"):
        return "schema_row_integrity"
    if v.startswith("B1:") and "missing expected hubs" in v:
        return "named_pc_omission"
    if v.startswith("B1:") and "over-route" in v:
        return "party_reference_boundary"
    if v.startswith("B2:") and "hubs > max_assigned_hubs" in v:
        return "party_or_abstain_boundary"
    if v.startswith("B2:") and "needs_new_hub_candidate false" in v:
        return "out_of_manifest_candidate"
    return "other"


def cmd_check_thresholds(ns: argparse.Namespace) -> int:
    thresholds_path = Path(ns.thresholds_json).resolve()
    cfg = json.loads(thresholds_path.read_text(encoding="utf-8"))
    cohort_paths = [Path(p).resolve() for p in (ns.cohort_json or cfg.get("cohort_summaries") or [])]
    if not cohort_paths:
        print(
            json.dumps(
                {
                    "ok": False,
                    "error": "No cohort summaries provided (pass --cohort-json or set cohort_summaries in thresholds json).",
                },
                indent=2,
            )
        )
        return 2

    by_scenario: dict[str, dict[str, Any]] = {}
    global_buckets: Counter[str] = Counter()
    total_cost = 0.0
    for cp in cohort_paths:
        cohort = json.loads(cp.read_text(encoding="utf-8"))
        scenario_id = str(cohort.get("scenario_id") or "")
        pass_rate = float(cohort.get("pass_rate") or 0.0)
        cost_sum = float(((cohort.get("cost_usd") or {}).get("sum")) or 0.0)
        total_cost += cost_sum
        sb = by_scenario.setdefault(
            scenario_id,
            {"pass_rate": pass_rate, "cost_sum": 0.0, "buckets": Counter(), "cohorts": []},
        )
        sb["pass_rate"] = pass_rate
        sb["cost_sum"] = float(sb["cost_sum"]) + cost_sum
        sb["cohorts"].append(str(cp))
        for run in cohort.get("runs") or []:
            sp = Path(str((run or {}).get("sidecar_json") or "")).resolve()
            if not sp.is_file():
                continue
            side = json.loads(sp.read_text(encoding="utf-8"))
            for v in ((side.get("violations") or {}).get("stage_b") or []):
                if not isinstance(v, str):
                    continue
                b = _bucket_for_thresholds(v)
                sb["buckets"][b] += 1
                global_buckets[b] += 1

    targets = dict(cfg.get("targets") or {})
    checks: list[dict[str, Any]] = []

    # Per-scenario bucket caps
    for scenario_id, bucket_caps in (targets.get("scenario_bucket_max") or {}).items():
        caps = dict(bucket_caps or {})
        sb = by_scenario.get(scenario_id, {"buckets": Counter()})
        for bucket, cap in caps.items():
            actual = int(sb["buckets"].get(bucket, 0))
            checks.append(
                {
                    "name": f"{scenario_id}.{bucket}.max",
                    "ok": actual <= int(cap),
                    "actual": actual,
                    "expected_max": int(cap),
                }
            )

    # Global schema guardrail
    schema_cap = targets.get("schema_row_integrity_global_max")
    if schema_cap is not None:
        actual_schema = int(global_buckets.get("schema_row_integrity", 0))
        checks.append(
            {
                "name": "global.schema_row_integrity.max",
                "ok": actual_schema <= int(schema_cap),
                "actual": actual_schema,
                "expected_max": int(schema_cap),
            }
        )

    # C1S2 control guardrail
    c1s2_rate_min = targets.get("c1s2_pass_rate_min")
    if c1s2_rate_min is not None:
        actual_rate = float((by_scenario.get("sentence_routing_c1_session2_pc") or {}).get("pass_rate") or 0.0)
        checks.append(
            {
                "name": "sentence_routing_c1_session2_pc.pass_rate.min",
                "ok": actual_rate >= float(c1s2_rate_min),
                "actual": round(actual_rate, 6),
                "expected_min": float(c1s2_rate_min),
            }
        )

    # Cost guardrail
    base_cost = targets.get("cost_baseline_four_cohort_sum_usd")
    cost_mult = targets.get("four_cohort_cost_sum_max_multiplier")
    if base_cost is not None and cost_mult is not None:
        max_cost = float(base_cost) * float(cost_mult)
        checks.append(
            {
                "name": "global.four_cohort_cost_sum.max",
                "ok": total_cost <= max_cost,
                "actual": round(total_cost, 6),
                "expected_max": round(max_cost, 6),
            }
        )

    ok = all(bool(c.get("ok")) for c in checks) if checks else True
    out = {
        "thresholds_json": str(thresholds_path),
        "cohort_summaries": [str(p) for p in cohort_paths],
        "scenario_results": {
            k: {
                "pass_rate": round(float(v["pass_rate"]), 6),
                "cost_sum": round(float(v["cost_sum"]), 6),
                "buckets": dict(v["buckets"]),
            }
            for k, v in by_scenario.items()
        },
        "global_buckets": dict(global_buckets),
        "global_cost_sum": round(total_cost, 6),
        "checks": checks,
        "ok": ok,
    }
    print(json.dumps(out, indent=2, ensure_ascii=False))
    return 0 if ok else 1


def cmd_summarize_cohort(ns: argparse.Namespace) -> int:
    cohort_path = Path(ns.cohort_json).resolve()
    cohort = json.loads(cohort_path.read_text(encoding="utf-8"))
    runs = cohort.get("runs") or []
    totals: Counter[str] = Counter()
    run_rows: list[dict[str, Any]] = []
    for r in runs:
        if not isinstance(r, dict):
            continue
        sp = Path(str(r.get("sidecar_json") or "")).resolve()
        if not sp.is_file():
            continue
        side = json.loads(sp.read_text(encoding="utf-8"))
        pairs = classify_sidecar_violations(side)
        c = Counter(b for _, b in pairs)
        totals.update(c)
        run_rows.append(
            {
                "run_index": r.get("run_index"),
                "gates_passed": r.get("gates_passed"),
                "cost_usd": r.get("cost_usd"),
                "buckets": dict(c),
                "sidecar": str(sp),
            }
        )
    verdict, why = h1_decision_from_counts(totals)
    out = {
        "cohort_json": str(cohort_path),
        "scenario_id": cohort.get("scenario_id"),
        "n": cohort.get("n"),
        "pass_rate": cohort.get("pass_rate"),
        "cost_usd": cohort.get("cost_usd"),
        "aggregate_violation_buckets_across_runs": dict(totals),
        "h1_verdict": verdict,
        "h1_rationale": why,
        "per_run": run_rows,
    }
    print(json.dumps(out, indent=2, ensure_ascii=False))
    return 0


def main() -> int:
    ap = argparse.ArgumentParser(description="H1 routing evidence — taxonomy + scorecard + cohort summary.")
    sub = ap.add_subparsers(dest="cmd", required=True)

    p_scan = sub.add_parser("scan-artifacts", help="Scan FAIL PC sidecars under artifacts/runs.")
    p_scan.add_argument("--runs-root", type=Path, default=None, help="Default: eval suite artifacts/runs")
    p_scan.add_argument(
        "--name-substr",
        default="_pc--FAIL",
        help="Filename filter substring (default: PC FAIL sidecars).",
    )
    p_scan.set_defaults(func=cmd_scan_artifacts)

    p_sc = sub.add_parser("scorecard", help="Classify violations + directional scorecard for one sidecar.")
    p_sc.add_argument("--sidecar", type=Path, required=True)
    p_sc.add_argument("--scenario-json", type=Path, required=True)
    p_sc.set_defaults(func=cmd_scorecard)

    p_sum = sub.add_parser(
        "summarize-cohort",
        help="Aggregate violation buckets across runs listed in a cohort summary JSON.",
    )
    p_sum.add_argument("cohort_json", type=Path)
    p_sum.set_defaults(func=cmd_summarize_cohort)

    p_agg = sub.add_parser(
        "aggregate-summaries",
        help="Merge violation buckets across multiple cohort summary JSON files (e.g. four PC scenarios).",
    )
    p_agg.add_argument(
        "cohort_json",
        type=Path,
        nargs="+",
        help="Paths to sentence_routing_stage_b_cohort_summary--*.json",
    )
    p_agg.set_defaults(func=cmd_aggregate_summaries)

    p_chk = sub.add_parser(
        "check-thresholds",
        help="Evaluate cohort summaries against a thresholds JSON (Matrix v2.1 automation).",
    )
    p_chk.add_argument(
        "--thresholds-json",
        type=Path,
        default=Path(__file__).resolve().parent / "artifacts" / "h1_thresholds_v2_1.json",
    )
    p_chk.add_argument(
        "--cohort-json",
        type=Path,
        nargs="*",
        help="Optional cohort summaries; defaults to thresholds_json.cohort_summaries.",
    )
    p_chk.set_defaults(func=cmd_check_thresholds)

    ns = ap.parse_args()
    func = getattr(ns, "func", None)
    if func is None:
        ap.print_help()
        return 2
    return int(func(ns))


if __name__ == "__main__":
    raise SystemExit(main())
