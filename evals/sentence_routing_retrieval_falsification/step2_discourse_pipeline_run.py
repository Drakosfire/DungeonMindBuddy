"""Split Stage B cohort runner: B1 discourse state + deterministic B2 hub routing.

This is the benchmark entrypoint for the sibling proving slice. It writes normal B1/B2
per-run sidecars plus a split-pipeline cohort summary that carries combined cost,
pass/fail, and failure-relocation telemetry.
"""

from __future__ import annotations

import argparse
import json
import os
import statistics
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from evals.sentence_routing_retrieval_falsification.step2_route_run import _load_sentence_units
from evals.sentence_routing_retrieval_falsification.step2a_discourse_run import run_discourse_once
from evals.sentence_routing_retrieval_falsification.grader import cohort_aggregate_unit_failure_events
from evals.sentence_routing_retrieval_falsification.step2b_route_from_discourse_run import (
    run_route_from_discourse_once,
)

_SLICE = Path(__file__).resolve().parent
_REPO_ROOT = _SLICE.parents[1]
_DEFAULT_SCENARIO = _SLICE / "gold" / "scenario_discourse_smoke.json"
_ARTIFACTS = _SLICE / "artifacts" / "runs"
_DEFAULT_MODEL = os.environ.get("DUNGEONMIND_PLANNER_MODEL", "gpt-5.4-mini").strip() or "gpt-5.4-mini"

SUMMARY_SCHEMA = "sentence_routing_stage_b_discourse_pipeline_cohort_summary_v1"


def _utc_stamp() -> str:
    return datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")


def _date_folder() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%d")


def _sanitize_filename_segment(raw: str, *, max_len: int = 48) -> str:
    import re

    s = re.sub(r"[^a-zA-Z0-9._-]+", "_", (raw or "").strip())
    s = s.strip("._-") or "model"
    return s[:max_len]


def _cost_summary(costs: list[float]) -> dict[str, float]:
    return {
        "min": round(min(costs), 6) if costs else 0.0,
        "max": round(max(costs), 6) if costs else 0.0,
        "mean": round(statistics.mean(costs), 6) if costs else 0.0,
        "sum": round(sum(costs), 6),
    }


def _write_split_pipeline_summary(
    *,
    records: list[dict[str, Any]],
    model_id: str,
    scenario_id: str,
    no_writes: bool,
) -> tuple[Path | None, Path | None]:
    if no_writes:
        return None, None
    day_dir = _ARTIFACTS / _date_folder()
    day_dir.mkdir(parents=True, exist_ok=True)
    stamp = _utc_stamp()
    model_seg = _sanitize_filename_segment(model_id)
    base = f"sentence_routing_stage_b_discourse_pipeline_summary--{scenario_id}--{model_seg}--N{len(records)}--{stamp}"
    json_path = day_dir / f"{base}.json"
    md_path = day_dir / f"{base}.md"

    costs = [float(r.get("cost_usd") or 0.0) for r in records]
    passed = sum(1 for r in records if r.get("pipeline_passed"))
    payload = {
        "schema": SUMMARY_SCHEMA,
        "pipeline": "stage_b_discourse_v1",
        "iso_utc": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "scenario_id": scenario_id,
        "model_id": model_id,
        "n": len(records),
        "passed": passed,
        "pass_rate": round(passed / len(records), 6) if records else 0.0,
        "cost_usd": _cost_summary(costs),
        "cost_baseline_note": (
            "Split Stage B first cohort; compare against monolithic Stage B cohorts for the same "
            "scenario/model. Flag regression at >=1.5x cohort sum or any single run >=1.5x prior mean."
        ),
        "runs": records,
    }
    ufe_list: list[dict[str, Any] | None] = []
    b1_ufe_list: list[dict[str, Any] | None] = []
    for r in records:
        b1 = r.get("b1") if isinstance(r.get("b1"), dict) else {}
        b1_bd = (
            b1.get("stage_b1_unit_breakdown")
            if isinstance(b1.get("stage_b1_unit_breakdown"), dict)
            else {}
        )
        raw_b1_ufe = b1_bd.get("content_failure_events") if isinstance(b1_bd, dict) else None
        b1_ufe_list.append(raw_b1_ufe if isinstance(raw_b1_ufe, dict) else None)
        b2 = r.get("b2") if isinstance(r.get("b2"), dict) else {}
        bd = b2.get("stage_b_unit_breakdown") if isinstance(b2.get("stage_b_unit_breakdown"), dict) else {}
        raw_ufe = bd.get("unit_failure_events")
        ufe_list.append(raw_ufe if isinstance(raw_ufe, dict) else None)
    payload["cohort_b1_content_failure_events"] = cohort_aggregate_unit_failure_events(
        b1_ufe_list
    )
    payload["cohort_unit_failure_events"] = cohort_aggregate_unit_failure_events(ufe_list)
    json_path.write_text(json.dumps(payload, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")

    costs_obj = payload["cost_usd"]
    md_lines = [
        "# Split Stage B — discourse pipeline cohort",
        "",
        f"- **scenario:** `{scenario_id}`",
        f"- **model:** `{model_id}`",
        f"- **pass rate:** {passed}/{len(records)}",
        f"- **Cost:** sum ${costs_obj['sum']:.4f} | mean ${costs_obj['mean']:.4f} | min ${costs_obj['min']:.4f} | max ${costs_obj['max']:.4f}",
        "",
        "## Cohort — B1 content failure buckets (union across runs)",
        "",
        "Distinct `unit_id` values that failed B1 content expectations in **any** run.",
        "",
    ]
    b1_cufe = payload.get("cohort_b1_content_failure_events") or {}
    b1_c_buckets = b1_cufe.get("by_bucket") if isinstance(b1_cufe, dict) else None
    if not isinstance(b1_cufe, dict) or "by_bucket" not in b1_cufe:
        md_lines.append("- *(no `cohort_b1_content_failure_events` in payload)*")
    elif isinstance(b1_c_buckets, dict) and len(b1_c_buckets) > 0:
        for bname, bobj in sorted(b1_c_buckets.items()):
            if not isinstance(bobj, dict):
                continue
            uids = bobj.get("unit_ids") or []
            cnt = bobj.get("count", len(uids) if isinstance(uids, list) else 0)
            if isinstance(uids, list) and uids:
                md_lines.append(
                    f"- **{bname}** — {cnt} unit(s): " + ", ".join(f"`{u}`" for u in uids)
                )
            else:
                md_lines.append(f"- **{bname}** — {cnt} unit(s)")
        dist = (
            b1_cufe.get("distinct_failure_unit_ids")
            if isinstance(b1_cufe, dict)
            else None
        )
        if isinstance(dist, list) and dist:
            md_lines.append(
                "- **distinct_failure_unit_ids (any B1 content bucket):** "
                + ", ".join(f"`{u}`" for u in dist)
            )
    else:
        md_lines.append(
            "- **Cohort B1 content failure buckets:** none (no B1 content failing `unit_id` in any run)."
        )
    md_lines.extend(
        [
            "",
        "## Cohort — B2 unit failure buckets (union across runs)",
        "",
        "Distinct `unit_id` values that failed B2 gates in **any** run. See each run’s "
        "`b2.stage_b_unit_breakdown.unit_failure_events`.",
        "",
        ]
    )
    cufe = payload.get("cohort_unit_failure_events") or {}
    c_buckets = cufe.get("by_bucket") if isinstance(cufe, dict) else None
    if not isinstance(cufe, dict) or "by_bucket" not in cufe:
        md_lines.append("- *(no `cohort_unit_failure_events` in payload)*")
    elif isinstance(c_buckets, dict) and len(c_buckets) > 0:
        for bname, bobj in sorted(c_buckets.items()):
            if not isinstance(bobj, dict):
                continue
            uids = bobj.get("unit_ids") or []
            cnt = bobj.get("count", len(uids) if isinstance(uids, list) else 0)
            if isinstance(uids, list) and uids:
                md_lines.append(
                    f"- **{bname}** — {cnt} unit(s): " + ", ".join(f"`{u}`" for u in uids)
                )
            else:
                md_lines.append(f"- **{bname}** — {cnt} unit(s)")
        dist = cufe.get("distinct_failure_unit_ids") if isinstance(cufe, dict) else None
        if isinstance(dist, list) and dist:
            md_lines.append(
                "- **distinct_failure_unit_ids (any bucket):** "
                + ", ".join(f"`{u}`" for u in dist)
            )
    else:
        md_lines.append(
            "- **Cohort failure buckets:** none (no B2 failing `unit_id` in any run)."
        )
    md_lines.extend(["", "## Runs", ""])
    for r in records:
        b1 = r.get("b1") if isinstance(r.get("b1"), dict) else {}
        b1_bd = (
            b1.get("stage_b1_unit_breakdown")
            if isinstance(b1.get("stage_b1_unit_breakdown"), dict)
            else {}
        )
        b2 = r.get("b2") if isinstance(r.get("b2"), dict) else {}
        bd = b2.get("stage_b_unit_breakdown") if isinstance(b2.get("stage_b_unit_breakdown"), dict) else {}
        delta = bd.get("b2_delta") if isinstance(bd.get("b2_delta"), dict) else {}
        counts = delta.get("gold_failure_attribution_counts") if isinstance(delta, dict) else {}
        md_lines.append(
            f"- run {int(r.get('run_index', 0)) + 1}: "
            f"{'PASS' if r.get('pipeline_passed') else 'FAIL'} | "
            f"B1={'PASS' if r.get('b1_passed') else 'FAIL'} | "
            f"B2={'PASS' if r.get('b2_passed') else 'FAIL'} | "
            f"${float(r.get('cost_usd') or 0.0):.4f}"
        )
        md_lines.append(f"  - B1 sidecar: `{r.get('b1_sidecar_json')}`")
        md_lines.append(f"  - B2 sidecar: `{r.get('b2_sidecar_json')}`")
        b1_ufe = b1_bd.get("content_failure_events") if isinstance(b1_bd, dict) else {}
        b1_ufeb = b1_ufe.get("by_bucket") if isinstance(b1_ufe, dict) else {}
        if isinstance(b1_ufeb, dict) and b1_ufeb:
            md_lines.append("  - B1 content failure buckets:")
            for bn, bobj in sorted(b1_ufeb.items()):
                if not isinstance(bobj, dict):
                    continue
                uids = bobj.get("unit_ids") or []
                if isinstance(uids, list) and uids:
                    md_lines.append(
                        f"    - `{bn}`: " + ", ".join(f"`{x}`" for x in uids)
                    )
        if isinstance(counts, dict):
            md_lines.append(f"  - B2 delta attribution: `{json.dumps(counts, sort_keys=True)}`")
        ufe = bd.get("unit_failure_events") if isinstance(bd, dict) else {}
        ufeb = ufe.get("by_bucket") if isinstance(ufe, dict) else {}
        if isinstance(ufeb, dict) and ufeb:
            md_lines.append("  - B2 unit failure buckets:")
            for bn, bobj in sorted(ufeb.items()):
                if not isinstance(bobj, dict):
                    continue
                uids = bobj.get("unit_ids") or []
                if isinstance(uids, list) and uids:
                    md_lines.append(
                        f"    - `{bn}`: " + ", ".join(f"`{x}`" for x in uids)
                    )
        ug = bd.get("unit_gate_events") if isinstance(bd, dict) else {}
        if isinstance(ug, dict) and ug.get("must_route"):
            mr = ug.get("must_route") or {}
            ma = ug.get("must_abstain") or {}
            md_lines.append(
                "  - B2 unit gate events: "
                f"must_route pass {mr.get('pass_unit_ids', [])}; fail {mr.get('fail_unit_ids', [])}; "
                f"must_abstain pass {ma.get('pass_unit_ids', [])}; fail {ma.get('fail_unit_ids', [])}."
            )
    md_path.write_text("\n".join(md_lines) + "\n", encoding="utf-8")
    return json_path, md_path


def _load_scenario_inputs(scenario_path: Path, corpus_root: Path, prior_json: Path | None) -> tuple[
    dict[str, Any],
    list[dict[str, Any]],
    list[dict[str, Any]],
    set[str],
    dict[str, Any],
]:
    raw = json.loads(scenario_path.read_text(encoding="utf-8"))
    inp = dict(raw.get("input") or {})
    manifest_raw = list(inp.get("hub_manifest") or [])
    gold_routing = dict(raw.get("gold_routing") or {})

    from evals.sentence_routing_retrieval_falsification.route_schema import (
        HubManifestEntry,
        manifest_slug_set,
        validate_hub_manifest,
    )

    max_entries = int(inp.get("max_manifest_entries") or 64)
    validate_paths = bool(inp.get("validate_manifest_paths", True))
    mviol = validate_hub_manifest(
        manifest_raw,
        corpus_root=corpus_root,
        validate_paths=validate_paths,
        max_manifest_entries=max_entries,
    )
    if mviol:
        raise ValueError(json.dumps({"manifest_violations": mviol}, indent=2))
    manifest_objs = [HubManifestEntry.model_validate(x) for x in manifest_raw]
    manifest_jsonable = [m.model_dump(exclude_none=True) for m in manifest_objs]
    manifest_slugs = manifest_slug_set(manifest_objs)
    units_json = _load_sentence_units(raw, corpus_root, prior_json)
    return raw, units_json, manifest_jsonable, manifest_slugs, gold_routing


def main() -> int:
    parser = argparse.ArgumentParser(description="Split Stage B cohort: B1 discourse -> B2 route.")
    parser.add_argument("--scenario-json", type=Path, default=_DEFAULT_SCENARIO)
    parser.add_argument("--corpus-root", type=Path, default=_REPO_ROOT)
    parser.add_argument("--prior-json", type=Path, default=None)
    parser.add_argument("--model", type=str, default=_DEFAULT_MODEL)
    parser.add_argument("--n", type=int, default=1)
    parser.add_argument("--no-llm", action="store_true")
    parser.add_argument("--no-writes", action="store_true")
    args = parser.parse_args()

    n = max(1, int(args.n))
    scenario_path = args.scenario_json.resolve()
    corpus_root = args.corpus_root.resolve()
    prior_json = args.prior_json.resolve() if args.prior_json else None
    model = str(args.model).strip()

    try:
        raw, units_json, manifest_jsonable, manifest_slugs, gold_routing = _load_scenario_inputs(
            scenario_path,
            corpus_root,
            prior_json,
        )
    except ValueError as exc:
        print(str(exc), file=sys.stderr)
        return 2

    if not args.no_llm:
        from src.agent.synthesis import _load_api_key
        from src.bootstrap_env import load_dungeonmindbuddy_dotenv

        load_dungeonmindbuddy_dotenv()
        if not (_load_api_key() or "").strip():
            print(
                "OPENAI_API_KEY missing after loading .env (see src/bootstrap_env.py). "
                "Use --no-llm for offline fixture runs.",
                file=sys.stderr,
            )
            return 2

    scenario_id = str(raw.get("scenario_id") or scenario_path.stem)
    records: list[dict[str, Any]] = []
    all_pass = True

    for i in range(n):
        try:
            b1_passed, b1_sidecar, b1_cost, b1_path = run_discourse_once(
                raw=raw,
                scenario_path=scenario_path,
                corpus_root=corpus_root,
                units_json=units_json,
                manifest_jsonable=manifest_jsonable,
                manifest_slugs=manifest_slugs,
                model=model,
                no_llm=args.no_llm,
                no_writes=args.no_writes,
            )
            b2_discourse_path = b1_path if b1_path is not None else None
            b2_passed, b2_sidecar, b2_path = run_route_from_discourse_once(
                raw=raw,
                scenario_path=scenario_path,
                corpus_root=corpus_root,
                units_json=units_json,
                manifest_jsonable=manifest_jsonable,
                manifest_slugs=manifest_slugs,
                gold_routing=gold_routing,
                discourse_path=b2_discourse_path,
                no_writes=args.no_writes,
            )
        except ValueError as exc:
            print(str(exc), file=sys.stderr)
            return 2

        pipeline_passed = b1_passed and b2_passed
        all_pass = all_pass and pipeline_passed
        b2_telem = b2_sidecar.get("telemetry") if isinstance(b2_sidecar, dict) else {}
        b2_breakdown = (
            b2_telem.get("stage_b_unit_breakdown")
            if isinstance(b2_telem, dict)
            else None
        )
        records.append(
            {
                "run_index": i,
                "pipeline_passed": pipeline_passed,
                "b1_passed": b1_passed,
                "b2_passed": b2_passed,
                "cost_usd": round(float(b1_cost), 6),
                "b1_sidecar_json": str(b1_path) if b1_path is not None else "",
                "b2_sidecar_json": str(b2_path) if b2_path is not None else "",
                "b1": {
                    "violations": b1_sidecar.get("violations", {}).get("stage_b1", []),
                    "stage_b1_unit_breakdown": b1_sidecar.get("telemetry", {}).get(
                        "stage_b1_unit_breakdown",
                        {},
                    ),
                },
                "b2": {
                    "violations": b2_sidecar.get("violations", {}).get("stage_b", []),
                    "stage_b_unit_breakdown": b2_breakdown or {},
                },
            }
        )

    j_path, m_path = _write_split_pipeline_summary(
        records=records,
        model_id=model,
        scenario_id=scenario_id,
        no_writes=args.no_writes,
    )
    if j_path is not None:
        print(str(j_path), file=sys.stderr)
    if m_path is not None:
        print(str(m_path), file=sys.stderr)
    return 0 if all_pass else 1


if __name__ == "__main__":
    raise SystemExit(main())
