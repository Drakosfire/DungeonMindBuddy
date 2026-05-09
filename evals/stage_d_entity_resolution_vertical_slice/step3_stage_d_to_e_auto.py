"""Automated Stage D -> promotion -> Stage E scaffold pipeline.

This runner removes manual handoffs for known Stage D scenarios:
1) run deterministic Stage D entity resolution,
2) emit cohort proposals sidecar,
3) build promotion sidecar,
4) run Stage E scaffold (preview-only by default, commit opt-in).
"""

from __future__ import annotations

import argparse
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from evals.stage_d_entity_resolution_vertical_slice.stage_d_run_report import (
    StageDRunSummary,
    write_stage_d_cohort_proposals,
    write_stage_d_run_report,
)
from evals.stage_d_entity_resolution_vertical_slice.step0_stage_d_scenario_autogen import (
    autogen_stage_d_scenarios,
)
from evals.stage_d_entity_resolution_vertical_slice.step1_stage_d_run import (
    _resolve_relative,
    load_events_fixture,
    load_registry_records,
    load_scenario,
    load_stage_c_output,
    run_stage_d,
)
from evals.stage_d_entity_resolution_vertical_slice.step2_stage_e_npc_hub_scaffold import (
    run_stage_e_scaffold,
)
from evals.stage_d_entity_resolution_vertical_slice.stage_e_scaffold_summary import (
    write_stage_e_cohort_summary,
)
from scripts.promote_stage_d_proposals import run_promotion

_SLICE_DIR = Path(__file__).resolve().parent
_DEFAULT_SCENARIO_GLOB = str(_SLICE_DIR / "gold" / "stage_d_*.json")
_DEFAULT_OUT_DIR = _SLICE_DIR / "scaffold"


def discover_scenarios(pattern: str) -> list[Path]:
    p = Path(pattern)
    if p.is_absolute():
        base = Path("/")
        pat = str(p).lstrip("/")
    else:
        base = _SLICE_DIR.parents[1]
        pat = str(p)
    return sorted(base.glob(pat))


def _run_one_scenario(
    *,
    scenario_path: Path,
    runs_root: Path | None,
    promotion_with_llm: bool,
    stage_e_commit: bool,
    quiet: bool,
) -> dict[str, Any]:
    scenario = load_scenario(scenario_path)
    scenario_id = str(scenario.get("scenario_id") or scenario_path.stem)
    inp = scenario.get("input") or {}
    campaign_id = str(inp.get("campaign_id") or "")
    stage_c_output = load_stage_c_output(str(inp.get("stage_c_output_path") or ""))
    events_path = str(inp.get("stage_a_events_path") or "")
    events = load_events_fixture(events_path)
    registry_path_rel = str(inp.get("npc_registry_path") or "")
    registry = load_registry_records(registry_path_rel)

    result = run_stage_d(
        scenario=scenario,
        stage_c_output=stage_c_output,
        events=events,
        registry=registry,
        enable_llm_coreference=False,
    )
    gates_passed = bool(result["all_gates_passed"])

    write_stage_d_run_report(
        scenario_id=scenario_id,
        gates_passed=gates_passed,
        per_gate_verdict=result["per_gate_verdict"],
        violations=result["violations"],
        violation_counts=result["violation_counts"],
        grader_telemetry=result["telemetry"],
        stage_d_output=result["stage_d_output"],
        runner_version=result["runner_version"],
        scenario=scenario,
        runs_root=runs_root,
        run_index=0,
        cohort_size=1,
    )

    summary = StageDRunSummary(
        run_index=0,
        iso_utc=datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        gates_passed=gates_passed,
        resolved_count=int(result["telemetry"].get("resolved_count", 0)),
        proposed_new_records_count=int(result["telemetry"].get("proposed_new_records_count", 0)),
        proposed_aliases_count=int(result["telemetry"].get("proposed_aliases_count", 0)),
        unresolvable_count=int(result["telemetry"].get("unresolvable_count", 0)),
        violation_counts=dict(result["violation_counts"]),
        per_gate_verdict=dict(result["per_gate_verdict"]),
        primary_md_path="",
        sidecar_json_path="",
        extras={
            "grader_telemetry": dict(result["telemetry"]),
            "stage_d_output": dict(result["stage_d_output"]),
        },
    )
    proposals_path = write_stage_d_cohort_proposals(
        [summary],
        scenario_id=scenario_id,
        campaign_id=campaign_id,
        source_events=events,
        source_events_path=events_path,
    )
    if proposals_path is None:
        raise RuntimeError(f"failed to write proposals for scenario={scenario_id}")

    promotion = run_promotion(
        campaign_id=campaign_id,
        proposals_pattern=str(proposals_path),
        per_run_pattern=None,
        registry_path=_resolve_relative(registry_path_rel),
        out_dir=_SLICE_DIR / "promotions" / scenario_id,
        use_llm=promotion_with_llm,
        quiet=quiet,
    )
    promotion_json = Path(promotion["json_path"])
    scaffold = run_stage_e_scaffold(
        promotion_json=promotion_json,
        commit=stage_e_commit,
        out_dir=_SLICE_DIR / "scaffold" / scenario_id,
    )
    return {
        "scenario_id": scenario_id,
        "campaign_id": campaign_id,
        "scenario_path": str(scenario_path),
        "stage_d_gates_passed": bool(gates_passed),
        "stage_d_per_gate_verdict": dict(result["per_gate_verdict"]),
        "proposals_path": str(proposals_path),
        "promotion_json_path": str(promotion_json),
        "stage_e_report_path": str(scaffold.get("report_path") or ""),
        "stage_e_gates_passed": ((scaffold.get("grading") or {}).get("gates_passed")),
        "stage_e_counts": dict(scaffold.get("counts") or {}),
        "promotion_cost_usd": round(float(promotion["cost"].total_usd), 6),
    }


def run_auto_pipeline(
    *,
    scenario_glob: str = _DEFAULT_SCENARIO_GLOB,
    runs_root: Path | None = None,
    promotion_with_llm: bool = False,
    stage_e_commit: bool = False,
    quiet: bool = False,
    out_dir: Path | None = None,
    autogen_stage_d_gold: bool = False,
    autogen_overwrite: bool = False,
    autogen_materialize_missing_stage_c_output: bool = False,
    autogen_stage_c_sidecar_glob: str | None = None,
) -> dict[str, Any]:
    autogen = None
    if autogen_stage_d_gold:
        kwargs: dict[str, Any] = {
            "overwrite": autogen_overwrite,
            "materialize_missing_stage_c_output": autogen_materialize_missing_stage_c_output,
        }
        if autogen_stage_c_sidecar_glob is not None:
            kwargs["stage_c_sidecar_glob"] = autogen_stage_c_sidecar_glob
        autogen = autogen_stage_d_scenarios(**kwargs)
    scenarios = discover_scenarios(scenario_glob)
    if not scenarios:
        raise ValueError(f"no scenario files matched: {scenario_glob}")

    rows: list[dict[str, Any]] = []
    failed: list[dict[str, Any]] = []
    stage_e_report_paths: list[Path] = []
    for scenario_path in scenarios:
        try:
            row = _run_one_scenario(
                scenario_path=scenario_path,
                runs_root=runs_root,
                promotion_with_llm=promotion_with_llm,
                stage_e_commit=stage_e_commit,
                quiet=quiet,
            )
            rows.append(row)
            rp = Path(str(row.get("stage_e_report_path") or ""))
            if rp.is_file():
                stage_e_report_paths.append(rp)
        except Exception as exc:  # noqa: BLE001
            failed.append({"scenario_path": str(scenario_path), "error": str(exc)})

    summary_md = None
    summary_json = None
    if stage_e_report_paths:
        summary_md, summary_json = write_stage_e_cohort_summary(
            report_paths=stage_e_report_paths,
            out_dir=out_dir or _DEFAULT_OUT_DIR,
        )

    payload = {
        "schema": "stage_d_to_e_auto_run_v1",
        "iso_utc": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "scenario_glob": scenario_glob,
        "stage_e_commit": bool(stage_e_commit),
        "promotion_with_llm": bool(promotion_with_llm),
        "runs_total": len(scenarios),
        "runs_succeeded": len(rows),
        "runs_failed": len(failed),
        "rows": rows,
        "failed": failed,
        "stage_e_summary_md": str(summary_md) if summary_md else None,
        "stage_e_summary_json": str(summary_json) if summary_json else None,
        "promotion_cost_usd_total": round(sum(float(r.get("promotion_cost_usd") or 0.0) for r in rows), 6),
        "autogen": autogen,
    }
    return payload


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Auto-run Stage D -> promotion -> Stage E scaffold for all matching scenarios."
    )
    parser.add_argument("--scenario-glob", default=_DEFAULT_SCENARIO_GLOB)
    parser.add_argument("--runs-root", type=Path, default=None)
    parser.add_argument("--promotion-with-llm", action="store_true")
    parser.add_argument("--stage-e-commit", action="store_true")
    parser.add_argument("--autogen-stage-d-gold", action="store_true")
    parser.add_argument("--autogen-overwrite", action="store_true")
    parser.add_argument("--autogen-materialize-missing-stage-c-output", action="store_true")
    parser.add_argument("--autogen-stage-c-sidecar-glob", default=None)
    parser.add_argument("--out-dir", type=Path, default=None)
    parser.add_argument("--quiet", action="store_true")
    args = parser.parse_args()

    payload = run_auto_pipeline(
        scenario_glob=str(args.scenario_glob),
        runs_root=args.runs_root,
        promotion_with_llm=bool(args.promotion_with_llm),
        stage_e_commit=bool(args.stage_e_commit),
        quiet=bool(args.quiet),
        out_dir=args.out_dir,
        autogen_stage_d_gold=bool(args.autogen_stage_d_gold),
        autogen_overwrite=bool(args.autogen_overwrite),
        autogen_materialize_missing_stage_c_output=bool(
            args.autogen_materialize_missing_stage_c_output
        ),
        autogen_stage_c_sidecar_glob=(
            str(args.autogen_stage_c_sidecar_glob)
            if args.autogen_stage_c_sidecar_glob is not None
            else None
        ),
    )
    out_root = args.out_dir or _DEFAULT_OUT_DIR
    out_root.mkdir(parents=True, exist_ok=True)
    stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%S") + "Z"
    out_path = out_root / f"stage_d_to_e_auto_run--{stamp}.json"
    out_path.write_text(json.dumps(payload, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    print(json.dumps({"out_path": str(out_path), "runs_succeeded": payload["runs_succeeded"], "runs_failed": payload["runs_failed"], "promotion_cost_usd_total": payload["promotion_cost_usd_total"]}))


if __name__ == "__main__":
    main()
