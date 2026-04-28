"""Aggregate historical Stage B sidecars: gold-check stability + capture consistency.

Use this to split **stable-pass** gold checks (baseline / smoke) from **edge** checks
(flaky or stable-fail) for faster targeted cohorts.

Run (repo root)::

    uv run python -m evals.sentence_routing_retrieval_falsification.stage_b_gold_stability \\
        --scenario-json evals/sentence_routing_retrieval_falsification/gold/scenario_c2_session20_pc.json \\
        --sidecar-glob 'evals/sentence_routing_retrieval_falsification/artifacts/runs/**/sentence_routing_stage_b_hub_routes--sentence_routing_c2_session20_pc--*.json'

Emit edge-only scenario (flaky gold rows only)::

    uv run python -m evals.sentence_routing_retrieval_falsification.stage_b_gold_stability \\
        --scenario-json .../scenario_c2_session20_pc.json \\
        --sidecar-glob '.../sentence_routing_stage_b_hub_routes--sentence_routing_c2_session20_pc--*.json' \\
        --emit-edge-scenario evals/sentence_routing_retrieval_falsification/gold/scenario_c2_session20_pc_edge_flaky48.json

Aggregate violation line patterns across sidecars::

    uv run python -m evals.sentence_routing_retrieval_falsification.stage_b_gold_stability \\
        --violations-aggregate-only \\
        --sidecar-glob 'evals/.../runs/**/sentence_routing_stage_b_hub_routes--sentence_routing_c2_session20_pc_edge_flaky48--*.json'
"""

from __future__ import annotations

import argparse
import copy
import hashlib
import json
import re
import sys
from collections import Counter, defaultdict
from pathlib import Path
from typing import Any

_REPO = Path(__file__).resolve().parents[2]


def _canonical_gold_fingerprint(gold_routing: dict[str, Any]) -> str:
    """Stable hash of must_route + must_abstain rows (order-preserving)."""
    blob = json.dumps(
        {
            "must_route": gold_routing.get("must_route") or [],
            "must_abstain": gold_routing.get("must_abstain") or [],
        },
        sort_keys=True,
        ensure_ascii=False,
    )
    return hashlib.sha256(blob.encode("utf-8")).hexdigest()[:16]


def _unit_set_signature(sentence_units: list[dict[str, Any]]) -> dict[str, Any]:
    ids = sorted(str(u.get("unit_id") or "") for u in sentence_units if isinstance(u, dict))
    return {
        "sentence_unit_count": len(sentence_units),
        "unit_id_sha16": hashlib.sha256("\n".join(ids).encode("utf-8")).hexdigest()[:16],
        "first_unit_id": ids[0] if ids else "",
        "last_unit_id": ids[-1] if ids else "",
    }


def collect_sidecar_paths(*, sidecar_glob: str, extra_paths: list[Path]) -> list[Path]:
    paths: list[Path] = []
    if sidecar_glob.strip():
        paths.extend(sorted(Path(_REPO).glob(sidecar_glob.strip().lstrip("/"))))
    paths.extend([p.resolve() for p in extra_paths])
    seen: set[str] = set()
    uniq: list[Path] = []
    for p in paths:
        k = str(p)
        if k in seen:
            continue
        seen.add(k)
        uniq.append(p)
    return uniq


def compute_stability_report(
    scenario_path: Path,
    paths: list[Path],
) -> tuple[dict[str, Any], list[str]]:
    """Build stability report dict and consistency warning strings."""
    raw = json.loads(scenario_path.read_text(encoding="utf-8"))
    gold_raw = dict(raw.get("gold_routing") or {})
    scenario_id = str(raw.get("scenario_id") or scenario_path.stem)

    from evals.sentence_routing_retrieval_falsification.grader import (
        iter_stage_b_gold_check_results,
        normalize_gold_routing_matches,
        stage_b_routes_by_id_normalized,
    )
    from evals.sentence_routing_retrieval_falsification.route_schema import (
        HubManifestEntry,
        manifest_slug_set,
        parse_routes_envelope,
    )
    from evals.sentence_routing_retrieval_falsification.session_roster import (
        resolve_session_pc_roster_slugs,
    )

    inp = dict(raw.get("input") or {})
    manifest_raw = list(inp.get("hub_manifest") or [])
    party_expansion = resolve_session_pc_roster_slugs(
        inp=inp, corpus_root=_REPO, manifest_jsonable=manifest_raw
    )

    manifest_objs = [HubManifestEntry.model_validate(x) for x in manifest_raw]
    manifest_slugs = manifest_slug_set(manifest_objs)

    first_units: list[dict[str, Any]] | None = None
    sig0: dict[str, Any] | None = None
    consistency_issues: list[str] = []

    per_check_passes: dict[str, list[bool]] = defaultdict(list)
    per_check_meta: dict[str, dict[str, Any]] = {}

    for p in paths:
        side = json.loads(p.read_text(encoding="utf-8"))
        if str(side.get("scenario_id") or "") != scenario_id:
            consistency_issues.append(f"{p.name}: scenario_id mismatch {side.get('scenario_id')!r} != {scenario_id!r}")
        units = side.get("sentence_units") or []
        if not isinstance(units, list) or not units:
            consistency_issues.append(f"{p.name}: missing sentence_units")
            continue
        if first_units is None:
            first_units = units
            sig0 = _unit_set_signature(units)
        else:
            sig1 = _unit_set_signature(units)
            if sig1 != sig0:
                consistency_issues.append(
                    f"{p.name}: sentence_units signature differs from first sidecar "
                    f"(counts {sig1.get('sentence_unit_count')} vs {sig0.get('sentence_unit_count')}, "
                    f"id_hash {sig1.get('unit_id_sha16')} vs {sig0.get('unit_id_sha16')})"
                )

        gold_norm, gold_errors = normalize_gold_routing_matches(gold_raw, units)
        if gold_errors:
            consistency_issues.append(f"{p.name}: gold normalize errors: {gold_errors[:3]!r}")

        try:
            env = parse_routes_envelope(
                {"schema": "sentence_hub_routes_v1", "routes": side.get("routes") or []},
                manifest_jsonable=manifest_raw,
            )
        except Exception as exc:
            consistency_issues.append(f"{p.name}: routes parse error: {exc}")
            continue

        by_id = stage_b_routes_by_id_normalized(env.routes, manifest_slugs)
        for row in iter_stage_b_gold_check_results(
            by_id, gold_norm, party_expansion_slugs=party_expansion
        ):
            ck = str(row["check_key"])
            per_check_passes[ck].append(bool(row["passed"]))
            if ck not in per_check_meta:
                per_check_meta[ck] = {
                    "gate": row["gate"],
                    "row_index": row["row_index"],
                    "unit_id": row["unit_id"],
                }

    n_runs = len(paths)
    tiers = {"stable_pass": [], "stable_fail": [], "flaky": []}
    for ck, passes in sorted(per_check_passes.items()):
        if len(passes) != n_runs:
            consistency_issues.append(
                f"check {ck}: only {len(passes)} outcomes for {n_runs} sidecars (skipped parses?)"
            )
        s = sum(1 for x in passes if x)
        rate = s / len(passes) if passes else 0.0
        meta = dict(per_check_meta.get(ck, {}))
        meta["check_key"] = ck
        meta["pass_count"] = s
        meta["run_count"] = len(passes)
        meta["pass_rate"] = round(rate, 4)
        if s == len(passes):
            tiers["stable_pass"].append(meta)
        elif s == 0:
            tiers["stable_fail"].append(meta)
        else:
            tiers["flaky"].append(meta)

    gold_fp = _canonical_gold_fingerprint(gold_raw)

    report: dict[str, Any] = {
        "schema": "sentence_routing_stage_b_gold_stability_v1",
        "scenario_id": scenario_id,
        "scenario_path": str(scenario_path.resolve()),
        "gold_routing_fingerprint_sha16": gold_fp,
        "sidecar_count": n_runs,
        "capture_signature_first_sidecar": sig0,
        "consistency_warnings": consistency_issues,
        "tiers": {
            "stable_pass_count": len(tiers["stable_pass"]),
            "stable_fail_count": len(tiers["stable_fail"]),
            "flaky_count": len(tiers["flaky"]),
            "stable_pass_checks": tiers["stable_pass"],
            "stable_fail_checks": tiers["stable_fail"],
            "flaky_checks": sorted(tiers["flaky"], key=lambda x: (str(x.get("gate")), int(x.get("row_index", 0)))),
        },
        "sidecar_paths": [str(p) for p in paths],
    }
    return report, consistency_issues


def emit_edge_flaky_scenario(
    *,
    base_scenario_path: Path,
    flaky_metas: list[dict[str, Any]],
    out_path: Path,
    edge_scenario_id: str,
    historical_sidecar_count: int,
) -> None:
    """Write a scenario JSON with only flaky gold rows (must_route / must_abstain), no fixture_routes."""
    raw = json.loads(base_scenario_path.read_text(encoding="utf-8"))
    gold = dict(raw.get("gold_routing") or {})
    mr_src: list[Any] = list(gold.get("must_route") or [])
    ma_src: list[Any] = list(gold.get("must_abstain") or [])

    mr_pick: list[Any] = []
    ma_pick: list[Any] = []
    source_keys: list[str] = []
    for m in sorted(flaky_metas, key=lambda x: (str(x.get("gate")), int(x.get("row_index", 0)))):
        gate = str(m.get("gate"))
        idx = int(m.get("row_index", -1))
        ck = str(m.get("check_key", ""))
        source_keys.append(ck)
        if gate == "must_route" and 0 <= idx < len(mr_src):
            mr_pick.append(copy.deepcopy(mr_src[idx]))
        elif gate == "must_abstain" and 0 <= idx < len(ma_src):
            ma_pick.append(copy.deepcopy(ma_src[idx]))

    out = copy.deepcopy(raw)
    out["scenario_id"] = edge_scenario_id
    notes = str(out.get("scenario_notes") or "").rstrip()
    tag = (
        f"\n\n**Edge subset (flaky only):** {len(mr_pick)} must_route + {len(ma_pick)} must_abstain rows "
        f"selected from stability analysis over {historical_sidecar_count} historical sidecars vs "
        f"`{base_scenario_path.name}`. Source check_keys: {', '.join(source_keys)}."
    )
    out["scenario_notes"] = (notes + tag).strip()
    gr = dict(out.get("gold_routing") or {})
    gr["must_route"] = mr_pick
    gr["must_abstain"] = ma_pick
    if "soft_limits" in gold:
        gr["soft_limits"] = copy.deepcopy(gold["soft_limits"])
    out["gold_routing"] = gr
    out.pop("fixture_routes", None)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(json.dumps(out, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")


_VIOL_SHAPE_RE = re.compile(r"assigned=\[[^\]]*\]")


def normalize_violation_shape(line: str) -> str:
    """Collapse assigned hub lists for pattern grouping."""
    return _VIOL_SHAPE_RE.sub("assigned=[…]", line)


def aggregate_violation_patterns(paths: list[Path]) -> dict[str, Any]:
    raw_counter: Counter[str] = Counter()
    shape_counter: Counter[str] = Counter()
    prefix_counter: Counter[str] = Counter()
    telem_mr_pass: list[int] = []
    telem_ma_pass: list[int] = []
    telem_b1: list[int] = []
    telem_b2: list[int] = []

    for p in paths:
        side = json.loads(p.read_text(encoding="utf-8"))
        for v in (side.get("violations") or {}).get("stage_b") or []:
            if isinstance(v, str) and v.strip():
                line = v.strip()
                raw_counter[line] += 1
                shape_counter[normalize_violation_shape(line)] += 1
                if line.startswith("B0"):
                    prefix_counter["B0"] += 1
                elif line.startswith("B1:"):
                    prefix_counter["B1"] += 1
                elif line.startswith("B2:"):
                    prefix_counter["B2"] += 1
                else:
                    prefix_counter["other"] += 1
        telem = side.get("telemetry") or {}
        bd = telem.get("stage_b_unit_breakdown") if isinstance(telem, dict) else None
        if isinstance(bd, dict):
            mr = bd.get("must_route") or {}
            ma = bd.get("must_abstain") or {}
            telem_mr_pass.append(int(mr.get("pass", 0)))
            telem_ma_pass.append(int(ma.get("pass", 0)))
            bk = bd.get("violation_failure_buckets") or {}
            telem_b1.append(int(bk.get("b1_missing_expected_hub", 0)))
            telem_b2.append(int(bk.get("b2_over_assigned", 0)))

    return {
        "sidecar_count": len(paths),
        "violation_lines_top_raw": raw_counter.most_common(40),
        "violation_lines_top_shape": shape_counter.most_common(25),
        "violation_prefix_counts": dict(prefix_counter),
        "telemetry_must_route_pass_per_run": telem_mr_pass,
        "telemetry_must_abstain_pass_per_run": telem_ma_pass,
        "telemetry_b1_missing_lines_per_run": telem_b1,
        "telemetry_b2_over_assign_lines_per_run": telem_b2,
    }


def main() -> int:
    parser = argparse.ArgumentParser(description="Stage B gold-check stability across sidecars.")
    parser.add_argument("--scenario-json", type=Path, required=True)
    parser.add_argument("--sidecar-glob", type=str, default="")
    parser.add_argument("sidecar_paths", nargs="*", type=Path)
    parser.add_argument("--json-out", type=Path, default=None)
    parser.add_argument(
        "--emit-edge-scenario",
        type=Path,
        default=None,
        help="Write a new scenario JSON containing only flaky gold rows.",
    )
    parser.add_argument(
        "--edge-scenario-id",
        type=str,
        default="",
        help="scenario_id for emitted edge file (default: <base>_edge_flaky48).",
    )
    parser.add_argument(
        "--violations-aggregate-only",
        action="store_true",
        help="Only aggregate violation patterns from sidecars (no stability tiers).",
    )
    args = parser.parse_args()

    scenario_path = args.scenario_json.resolve()
    paths = collect_sidecar_paths(sidecar_glob=args.sidecar_glob, extra_paths=list(args.sidecar_paths))

    if not paths:
        print("No sidecars: pass --sidecar-glob or positional paths.", file=sys.stderr)
        return 2

    if args.violations_aggregate_only:
        pat = aggregate_violation_patterns(paths)
        out = {
            "schema": "sentence_routing_stage_b_violation_aggregate_v1",
            "scenario_path": str(scenario_path),
            "pattern_report": pat,
            "sidecar_paths": [str(p) for p in paths],
        }
        text = json.dumps(out, indent=2, ensure_ascii=False) + "\n"
        if args.json_out:
            args.json_out.parent.mkdir(parents=True, exist_ok=True)
            args.json_out.write_text(text, encoding="utf-8")
            print(str(args.json_out.resolve()))
        else:
            print(text, end="")
        return 0

    report, consistency_issues = compute_stability_report(scenario_path, paths)

    if args.emit_edge_scenario:
        flaky = report["tiers"]["flaky_checks"]
        if not flaky:
            print("No flaky checks to emit.", file=sys.stderr)
            return 2
        edge_id = (args.edge_scenario_id or "").strip() or f"{report['scenario_id']}_edge_flaky{len(flaky)}"
        out_edge = args.emit_edge_scenario.resolve()
        emit_edge_flaky_scenario(
            base_scenario_path=scenario_path,
            flaky_metas=flaky,
            out_path=out_edge,
            edge_scenario_id=edge_id,
            historical_sidecar_count=int(report.get("sidecar_count") or len(paths)),
        )
        report["emitted_edge_scenario"] = str(out_edge)
        report["emitted_edge_scenario_id"] = edge_id
        print(str(out_edge), file=sys.stderr)

    text = json.dumps(report, indent=2, ensure_ascii=False) + "\n"
    if args.json_out:
        args.json_out.parent.mkdir(parents=True, exist_ok=True)
        args.json_out.write_text(text, encoding="utf-8")
        print(str(args.json_out.resolve()))
    else:
        print(text, end="")

    return 1 if consistency_issues else 0


if __name__ == "__main__":
    raise SystemExit(main())
