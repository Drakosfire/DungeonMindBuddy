#!/usr/bin/env python3
"""Deterministic ablation matrix for natural breadcrumb-query retrieval.

Runs grade-only (no LLM) combinations across:
- tokenizer mode
- expansion allocation mode
- first-pass cap

Outputs JSON (and optional Markdown) with lane-level pass rates plus
expected-evidence deltas vs a baseline deterministic run/report.
"""

from __future__ import annotations

import argparse
import json
from collections import defaultdict
from dataclasses import dataclass
from datetime import date, datetime, timezone
from pathlib import Path
from typing import Any

from evals.sentence_routing_retrieval_falsification.breadcrumb_query_grader import (
    grade_natural_scenario,
    load_gold,
)


@dataclass(frozen=True)
class ScenarioSpec:
    scenario: dict[str, Any]
    lane: str
    high_signal: bool


def _parse_csv(raw: str) -> list[str]:
    return [x.strip() for x in raw.split(",") if x.strip()]


def _parse_int_csv(raw: str) -> list[int]:
    out: list[int] = []
    for x in _parse_csv(raw):
        out.append(int(x))
    return out


def _load_records(path: Path) -> list[dict[str, Any]]:
    return [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines() if line.strip()]


def _prepare_scenarios(gold: dict[str, Any]) -> list[ScenarioSpec]:
    default_campaign = str(gold.get("campaign_id") or "")
    default_qspec = dict(gold.get("default_query_spec") or {})
    out: list[ScenarioSpec] = []
    for s in gold.get("scenarios") or []:
        scen = dict(s)
        scen["campaign_id"] = str(scen.get("campaign_id") or default_campaign)
        merged_qspec = {**default_qspec, **(scen.get("query_spec") or {})}
        merged_qspec["query"] = str(scen["question"])
        scen["query_spec"] = merged_qspec
        out.append(
            ScenarioSpec(
                scenario=scen,
                lane=str(scen.get("benchmark_lane") or "lexical_recall"),
                high_signal=bool(scen.get("high_signal_retrieval_row", False)),
            )
        )
    return out


def _hits_unit_ids(row: dict[str, Any]) -> list[str]:
    return [str(h.get("unit_id") or "") for h in row.get("full_result", {}).get("hits", [])]


def _hits_route_blob(row: dict[str, Any]) -> str:
    parts: list[str] = []
    for h in row.get("full_result", {}).get("hits", []):
        for r in h.get("routes") or []:
            nr = str(r.get("normalized_route") or "")
            if nr:
                parts.append(nr)
    return "\n".join(parts).lower()


def _missing_units(row: dict[str, Any], scenario: dict[str, Any]) -> list[str]:
    expected = [str(x) for x in (scenario.get("expect_unit_id_substrings") or [])]
    uids = _hits_unit_ids(row)
    return [u for u in expected if not any(u in got for got in uids)]


def _missing_routes(row: dict[str, Any], scenario: dict[str, Any]) -> list[str]:
    expected = [str(x) for x in (scenario.get("expect_route_substrings") or [])]
    blob = _hits_route_blob(row)
    return [r for r in expected if r.lower() not in blob]


def _run_combo(
    *,
    records: list[dict[str, Any]],
    scenarios: list[ScenarioSpec],
    tokenizer_mode: str,
    expansion_allocation_mode: str,
    first_pass_cap: int,
) -> dict[str, Any]:
    rows: list[dict[str, Any]] = []
    lane_totals: dict[str, dict[str, int]] = defaultdict(lambda: {"pass": 0, "total": 0})
    for spec in scenarios:
        scen = json.loads(json.dumps(spec.scenario))
        qspec = dict(scen.get("query_spec") or {})
        qspec["tokenizer_mode"] = tokenizer_mode
        qspec["expansion_allocation_mode"] = expansion_allocation_mode
        qspec["expand_first_pass_cap"] = first_pass_cap
        scen["query_spec"] = qspec
        row = grade_natural_scenario(records=records, scenario=scen)
        row["benchmark_lane"] = spec.lane
        row["high_signal_retrieval_row"] = spec.high_signal
        rows.append(row)
        lane_totals[spec.lane]["total"] += 1
        if row.get("ok"):
            lane_totals[spec.lane]["pass"] += 1
    overall_pass = sum(1 for r in rows if r.get("ok"))
    return {
        "config": {
            "tokenizer_mode": tokenizer_mode,
            "expansion_allocation_mode": expansion_allocation_mode,
            "expand_first_pass_cap": first_pass_cap,
        },
        "summary": {
            "pass_count": overall_pass,
            "total": len(rows),
            "pass_rate": (overall_pass / len(rows)) if rows else 0.0,
            "lane_summary": {
                lane: {
                    "pass_count": v["pass"],
                    "total": v["total"],
                    "pass_rate": (v["pass"] / v["total"]) if v["total"] else 0.0,
                }
                for lane, v in sorted(lane_totals.items())
            },
        },
        "rows": rows,
    }


def _index_rows(rows: list[dict[str, Any]]) -> dict[str, dict[str, Any]]:
    return {str(r.get("scenario_id") or ""): r for r in rows}


def _delta_vs_baseline(
    *,
    baseline_rows: dict[str, dict[str, Any]],
    candidate_rows: list[dict[str, Any]],
    scenarios_by_id: dict[str, ScenarioSpec],
) -> dict[str, Any]:
    cidx = _index_rows(candidate_rows)
    fail_to_pass: list[str] = []
    pass_to_fail: list[str] = []
    recovered_units: dict[str, list[str]] = {}
    recovered_routes: dict[str, list[str]] = {}
    new_missing_units: dict[str, list[str]] = {}
    new_missing_routes: dict[str, list[str]] = {}
    high_signal_regressions: list[str] = []
    for sid, crow in cidx.items():
        brow = baseline_rows.get(sid)
        if brow is None:
            continue
        if (not brow.get("ok")) and crow.get("ok"):
            fail_to_pass.append(sid)
        if brow.get("ok") and (not crow.get("ok")):
            pass_to_fail.append(sid)
        spec = scenarios_by_id[sid]
        b_mu = set(_missing_units(brow, spec.scenario))
        c_mu = set(_missing_units(crow, spec.scenario))
        b_mr = set(_missing_routes(brow, spec.scenario))
        c_mr = set(_missing_routes(crow, spec.scenario))
        rec_u = sorted(b_mu - c_mu)
        rec_r = sorted(b_mr - c_mr)
        new_u = sorted(c_mu - b_mu)
        new_r = sorted(c_mr - b_mr)
        if rec_u:
            recovered_units[sid] = rec_u
        if rec_r:
            recovered_routes[sid] = rec_r
        if new_u:
            new_missing_units[sid] = new_u
        if new_r:
            new_missing_routes[sid] = new_r
        if spec.high_signal and brow.get("ok") and (not crow.get("ok")):
            high_signal_regressions.append(sid)
    return {
        "fail_to_pass": sorted(fail_to_pass),
        "pass_to_fail": sorted(pass_to_fail),
        "recovered_expected_units": recovered_units,
        "recovered_expected_routes": recovered_routes,
        "new_missing_expected_units": new_missing_units,
        "new_missing_expected_routes": new_missing_routes,
        "high_signal_regressions": sorted(high_signal_regressions),
    }


def _promotion_gate(
    *,
    baseline_rows: dict[str, dict[str, Any]],
    candidate: dict[str, Any],
    scenarios_by_id: dict[str, ScenarioSpec],
) -> dict[str, Any]:
    deltas = candidate["delta_vs_baseline"]
    rows = _index_rows(candidate["rows"])
    baseline_lane: dict[str, tuple[int, int]] = defaultdict(lambda: (0, 0))
    candidate_lane: dict[str, tuple[int, int]] = defaultdict(lambda: (0, 0))
    for sid, spec in scenarios_by_id.items():
        b = baseline_rows.get(sid)
        c = rows.get(sid)
        if b is None or c is None:
            continue
        bp, bt = baseline_lane[spec.lane]
        cp, ct = candidate_lane[spec.lane]
        baseline_lane[spec.lane] = (bp + int(bool(b.get("ok"))), bt + 1)
        candidate_lane[spec.lane] = (cp + int(bool(c.get("ok"))), ct + 1)
    route_b_pass, route_b_total = baseline_lane.get("route_family_recall", (0, 0))
    route_c_pass, route_c_total = candidate_lane.get("route_family_recall", (0, 0))
    route_improved = False
    if route_b_total and route_c_total:
        route_improved = (route_c_pass / route_c_total) > (route_b_pass / route_b_total)
    planning_present = "planning_open_loop_recall" in candidate["summary"]["lane_summary"]
    no_high_signal_regression = not bool(deltas["high_signal_regressions"])
    passed = no_high_signal_regression and route_improved and planning_present
    return {
        "passed": passed,
        "no_high_signal_regression": no_high_signal_regression,
        "route_family_improved": route_improved,
        "planning_lane_present": planning_present,
        "baseline_route_family": {"pass_count": route_b_pass, "total": route_b_total},
        "candidate_route_family": {"pass_count": route_c_pass, "total": route_c_total},
        "high_signal_regressions": deltas["high_signal_regressions"],
    }


def _markdown_report(
    *,
    baseline_path: Path,
    gold_path: Path,
    matrix: list[dict[str, Any]],
    winner: dict[str, Any] | None,
) -> str:
    lines: list[str] = []
    lines.append("# Breadcrumb query deterministic ablation matrix")
    lines.append("")
    lines.append(f"- Baseline report: `{baseline_path}`")
    lines.append(f"- Gold: `{gold_path}`")
    lines.append(f"- Generated: `{datetime.now(timezone.utc).isoformat()}`")
    lines.append("")
    lines.append("## Matrix summary")
    lines.append("")
    lines.append("| tokenizer | expansion allocation | first-pass cap | pass | lexical | route-family | planning | gate |")
    lines.append("|---|---|---:|---:|---:|---:|---:|---|")
    for item in matrix:
        cfg = item["config"]
        s = item["summary"]
        ls = s["lane_summary"]
        lex = ls.get("lexical_recall", {}).get("pass_count", 0)
        lex_t = ls.get("lexical_recall", {}).get("total", 0)
        rtf = ls.get("route_family_recall", {}).get("pass_count", 0)
        rtf_t = ls.get("route_family_recall", {}).get("total", 0)
        pln = ls.get("planning_open_loop_recall", {}).get("pass_count", 0)
        pln_t = ls.get("planning_open_loop_recall", {}).get("total", 0)
        gate = "PASS" if item["promotion_gate"]["passed"] else "FAIL"
        lines.append(
            f"| `{cfg['tokenizer_mode']}` | `{cfg['expansion_allocation_mode']}` | {cfg['expand_first_pass_cap']} | "
            f"{s['pass_count']}/{s['total']} | {lex}/{lex_t} | {rtf}/{rtf_t} | {pln}/{pln_t} | {gate} |"
        )
    lines.append("")
    lines.append("## Best gate-passing candidate")
    lines.append("")
    if winner is None:
        lines.append("No configuration met the promotion gate.")
    else:
        cfg = winner["config"]
        lines.append(
            f"- `{cfg['tokenizer_mode']}` + `{cfg['expansion_allocation_mode']}` + cap `{cfg['expand_first_pass_cap']}`"
        )
        lines.append(
            f"- Pass count: {winner['summary']['pass_count']}/{winner['summary']['total']}"
        )
        lines.append(
            "- Gate checks: "
            + json.dumps(
                {
                    k: v
                    for k, v in winner["promotion_gate"].items()
                    if k in ("no_high_signal_regression", "route_family_improved", "planning_lane_present")
                },
                sort_keys=True,
            )
        )
        delta = winner["delta_vs_baseline"]
        lines.append(f"- Fail -> pass: {', '.join(delta['fail_to_pass']) if delta['fail_to_pass'] else 'none'}")
        lines.append(f"- Pass -> fail: {', '.join(delta['pass_to_fail']) if delta['pass_to_fail'] else 'none'}")
    lines.append("")
    return "\n".join(lines).rstrip() + "\n"


def main() -> None:
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument(
        "--gold",
        type=Path,
        default=Path("evals/sentence_routing_retrieval_falsification/gold/breadcrumb_query_natural_v1.json"),
    )
    p.add_argument(
        "--baseline-report",
        type=Path,
        required=True,
        help="Deterministic baseline report used for evidence delta and gate comparisons.",
    )
    p.add_argument(
        "--records-jsonl",
        type=Path,
        default=None,
        help="Optional records JSONL override; defaults to baseline_report.records_source.",
    )
    p.add_argument("--tokenizer-modes", type=str, default="default,restrained")
    p.add_argument("--expansion-modes", type=str, default="round_robin,greedy")
    p.add_argument("--first-pass-caps", type=str, default="9,8,7")
    p.add_argument("--output-json", type=Path, default=None)
    p.add_argument("--output-md", type=Path, default=None)
    args = p.parse_args()

    gold = load_gold(args.gold)
    scenarios = _prepare_scenarios(gold)
    scenarios_by_id = {str(s.scenario.get("id") or ""): s for s in scenarios}

    baseline_report = json.loads(args.baseline_report.read_text(encoding="utf-8"))
    records_path = args.records_jsonl or Path(str(baseline_report.get("records_source") or ""))
    if not records_path or not records_path.is_file():
        raise SystemExit(f"records JSONL not found: {records_path}")
    records = _load_records(records_path)

    baseline_rows_raw = list(baseline_report.get("results") or [])
    baseline_rows = _index_rows(baseline_rows_raw)

    tokenizer_modes = _parse_csv(args.tokenizer_modes)
    expansion_modes = _parse_csv(args.expansion_modes)
    first_pass_caps = _parse_int_csv(args.first_pass_caps)

    matrix: list[dict[str, Any]] = []
    for tok in tokenizer_modes:
        for exp_mode in expansion_modes:
            for cap in first_pass_caps:
                item = _run_combo(
                    records=records,
                    scenarios=scenarios,
                    tokenizer_mode=tok,
                    expansion_allocation_mode=exp_mode,
                    first_pass_cap=cap,
                )
                item["delta_vs_baseline"] = _delta_vs_baseline(
                    baseline_rows=baseline_rows,
                    candidate_rows=item["rows"],
                    scenarios_by_id=scenarios_by_id,
                )
                item["promotion_gate"] = _promotion_gate(
                    baseline_rows=baseline_rows,
                    candidate=item,
                    scenarios_by_id=scenarios_by_id,
                )
                matrix.append(item)

    gate_passers = [m for m in matrix if m["promotion_gate"]["passed"]]
    winner: dict[str, Any] | None = None
    if gate_passers:
        winner = sorted(
            gate_passers,
            key=lambda m: (
                -int(m["summary"]["pass_count"]),
                -float(m["summary"]["lane_summary"].get("route_family_recall", {}).get("pass_rate", 0.0)),
            ),
        )[0]

    out_obj = {
        "schema": "breadcrumb_query_deterministic_ablation_v1",
        "generated_at_utc": datetime.now(timezone.utc).isoformat(),
        "baseline_report_path": str(args.baseline_report.resolve()),
        "gold_path": str(args.gold.resolve()),
        "records_jsonl": str(records_path.resolve()),
        "tokenizer_modes": tokenizer_modes,
        "expansion_modes": expansion_modes,
        "first_pass_caps": first_pass_caps,
        "baseline_pass_count": sum(1 for r in baseline_rows_raw if r.get("ok")),
        "baseline_total": len(baseline_rows_raw),
        "matrix": matrix,
        "winner": winner,
    }

    default_json = (
        Path("evals/sentence_routing_retrieval_falsification/artifacts/runs")
        / str(date.today())
        / "breadcrumb_query_deterministic_ablation_matrix.json"
    )
    out_json = args.output_json or default_json
    out_json.parent.mkdir(parents=True, exist_ok=True)
    out_json.write_text(json.dumps(out_obj, indent=2), encoding="utf-8")
    print(json.dumps({"wrote": str(out_json), "winner": winner["config"] if winner else None}, indent=2))

    if args.output_md is not None:
        md = _markdown_report(
            baseline_path=args.baseline_report,
            gold_path=args.gold,
            matrix=matrix,
            winner=winner,
        )
        args.output_md.parent.mkdir(parents=True, exist_ok=True)
        args.output_md.write_text(md, encoding="utf-8")
        print(json.dumps({"wrote_markdown": str(args.output_md)}, indent=2))


if __name__ == "__main__":
    main()

