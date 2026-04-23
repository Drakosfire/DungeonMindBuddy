"""Persist Stage D NPC entity-resolution benchmark run reports.

Mirrors ``evals/stage_c_npc_candidates_vertical_slice/stage_c_run_report.py``
in shape; differs in field set (Stage D telemetry tracks resolution counts,
proposed-record counts, unresolvable counts, and per-gate ER1-ER5 verdicts).

Three writers:

* ``write_stage_d_run_report`` — one per-run sidecar (.md + .json) under
  ``artifacts/runs/YYYY-MM-DD/`` plus a ``last_stage_d_run.{md,json}``
  legacy pair under ``artifacts/`` for quick CLI inspection.
* ``write_stage_d_multi_summary`` — cohort-level summary (one per cohort).
* ``write_stage_d_cohort_proposals`` — propose-only sidecar aggregated
  across the cohort, written to ``proposals/<campaign>_stage_d_proposals_
  <ts>.json`` for GM review (mirrors the Stage C precedent at
  ``evals/stage_c_npc_candidates_vertical_slice/proposals/``).
"""

from __future__ import annotations

import json
import os
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


_SLICE_DIR = Path(__file__).resolve().parent
_RUNS_ROOT_ENV = "STAGE_D_RUNS_ROOT"
REPORT_SCHEMA_VERSION = "stage_d_run_report_v1"
SUMMARY_SCHEMA_VERSION = "stage_d_multi_run_summary_v1"
PROPOSALS_SCHEMA_VERSION = "stage_d_cohort_proposals_v1"


def _sanitize_filename_segment(raw: str, *, max_len: int) -> str:
    parts: list[str] = []
    for ch in (raw or "").strip():
        if ch.isalnum() or ch in "._-":
            parts.append(ch)
        else:
            parts.append("-")
    s = "".join(parts).lower()
    while "--" in s:
        s = s.replace("--", "-")
    return s[:max_len].strip("-")


@dataclass
class StageDRunSummary:
    run_index: int
    iso_utc: str
    gates_passed: bool
    resolved_count: int
    proposed_new_records_count: int
    proposed_aliases_count: int
    unresolvable_count: int
    violation_counts: dict[str, int]
    per_gate_verdict: dict[str, str]
    primary_md_path: str
    sidecar_json_path: str
    extras: dict[str, Any] = field(default_factory=dict)


@dataclass
class StageDReportPaths:
    primary_md: Path
    sidecar_json: Path
    legacy_md: Path
    legacy_json: Path


def _resolve_runs_root(runs_root: Path | None) -> Path:
    if runs_root is not None:
        return runs_root
    env = os.environ.get(_RUNS_ROOT_ENV, "").strip()
    if env:
        return Path(env).expanduser().resolve()
    return _SLICE_DIR / "artifacts" / "runs"


def _build_artifact_basename(
    *,
    scenario_key: str,
    gates_passed: bool,
    utc: datetime,
    run_index: int | None,
) -> str:
    compact = utc.strftime("%Y%m%dT%H%M%S") + "Z"
    scen = _sanitize_filename_segment(scenario_key, max_len=40)
    gate = "PASS" if gates_passed else "FAIL"
    suffix = f"--run{run_index:03d}" if run_index is not None else ""
    return f"stage_d--{scen}--deterministic-v0--{gate}--{compact}{suffix}"


def write_stage_d_run_report(
    *,
    scenario_id: str,
    gates_passed: bool,
    per_gate_verdict: dict[str, str],
    violations: list[str],
    violation_counts: dict[str, int],
    grader_telemetry: dict[str, Any],
    stage_d_output: dict[str, Any],
    runner_version: str,
    scenario: dict[str, Any] | None = None,
    runs_root: Path | None = None,
    run_index: int | None = None,
    cohort_size: int | None = None,
    utc: datetime | None = None,
) -> tuple[StageDReportPaths, StageDRunSummary]:
    when = utc or datetime.now(timezone.utc)
    iso = when.strftime("%Y-%m-%dT%H:%M:%SZ")
    base_runs = _resolve_runs_root(runs_root)
    day_dir = base_runs / when.strftime("%Y-%m-%d")

    base = _build_artifact_basename(
        scenario_key=scenario_id,
        gates_passed=gates_passed,
        utc=when,
        run_index=(run_index + 1) if run_index is not None else None,
    )
    primary_md = day_dir / f"{base}.md"
    sidecar_json = day_dir / f"{base}.json"
    legacy_dir = _SLICE_DIR / "artifacts"
    legacy_md = legacy_dir / "last_stage_d_run.md"
    legacy_json = legacy_dir / "last_stage_d_run.json"

    cohort_tag = (
        f" | cohort: {cohort_size} | run_index: {run_index}" if cohort_size else ""
    )

    sidecar: dict[str, Any] = {
        "schema": REPORT_SCHEMA_VERSION,
        "iso_utc": iso,
        "scenario_id": scenario_id,
        "runner_version": runner_version,
        "run_index": run_index,
        "cohort_size": cohort_size,
        "gates_passed": gates_passed,
        "per_gate_verdict": dict(per_gate_verdict),
        "violation_counts": dict(violation_counts),
        "violations": list(violations),
        "grader_telemetry": dict(grader_telemetry),
        "stage_d_output": dict(stage_d_output),
        "grading": (scenario or {}).get("grading"),
    }

    rel_primary = primary_md
    try:
        rel_primary = primary_md.resolve().relative_to(_SLICE_DIR.resolve())
    except ValueError:
        rel_primary = Path(primary_md.name)

    header = (
        f"<!-- benchmark_artifact: {REPORT_SCHEMA_VERSION} | iso_utc: {iso} "
        f"| scenario: {scenario_id} | runner: {runner_version} "
        f"| gates: {'PASS' if gates_passed else 'FAIL'} "
        f"| primary: {rel_primary.as_posix()}{cohort_tag} -->\n"
    )
    verdict_str = " ".join(f"{k}={v}" for k, v in sorted(per_gate_verdict.items()))
    viol_lines = "\n".join(f"  {v}" for v in violations)
    telemetry_str = json.dumps(grader_telemetry, ensure_ascii=False, sort_keys=True, default=str)

    body = (
        f"{header}\n"
        "## Summary\n\n"
        f"- **scenario_id:** `{scenario_id}`\n"
        f"- **runner:** `{runner_version}`\n"
        f"- **gates:** {'PASS' if gates_passed else 'FAIL'}\n"
        f"- **per_gate:** `{verdict_str}`\n"
        f"- **resolved_count:** {grader_telemetry.get('resolved_count', 0)}\n"
        f"- **proposed_new_records_count:** "
        f"{grader_telemetry.get('proposed_new_records_count', 0)}\n"
        f"- **proposed_aliases_count:** "
        f"{grader_telemetry.get('proposed_aliases_count', 0)}\n"
        f"- **unresolvable_count:** {grader_telemetry.get('unresolvable_count', 0)}\n\n"
        "## Violations\n\n"
        f"```\n{viol_lines if viol_lines else '(none)'}\n```\n\n"
        "## Telemetry\n\n"
        f"```json\n{telemetry_str}\n```\n\n"
        "## Sidecar JSON\n\n"
        f"```json\n{json.dumps(sidecar, indent=2, ensure_ascii=False, default=str)}\n```\n"
    )

    primary_md.parent.mkdir(parents=True, exist_ok=True)
    primary_md.write_text(body, encoding="utf-8")
    sidecar_json.write_text(
        json.dumps(sidecar, indent=2, ensure_ascii=False, default=str), encoding="utf-8"
    )
    legacy_dir.mkdir(parents=True, exist_ok=True)
    legacy_md.write_text(body, encoding="utf-8")
    legacy_json.write_text(
        json.dumps(sidecar, indent=2, ensure_ascii=False, default=str), encoding="utf-8"
    )

    paths = StageDReportPaths(
        primary_md=primary_md,
        sidecar_json=sidecar_json,
        legacy_md=legacy_md,
        legacy_json=legacy_json,
    )
    summary = StageDRunSummary(
        run_index=run_index if run_index is not None else 0,
        iso_utc=iso,
        gates_passed=gates_passed,
        resolved_count=int(grader_telemetry.get("resolved_count", 0)),
        proposed_new_records_count=int(
            grader_telemetry.get("proposed_new_records_count", 0)
        ),
        proposed_aliases_count=int(grader_telemetry.get("proposed_aliases_count", 0)),
        unresolvable_count=int(grader_telemetry.get("unresolvable_count", 0)),
        violation_counts=dict(violation_counts),
        per_gate_verdict=dict(per_gate_verdict),
        primary_md_path=str(primary_md),
        sidecar_json_path=str(sidecar_json),
        extras={
            "grader_telemetry": dict(grader_telemetry),
            "stage_d_output": dict(stage_d_output),
        },
    )
    return paths, summary


def write_stage_d_multi_summary(
    summaries: list[StageDRunSummary],
    *,
    scenario_id: str,
    runs_root: Path | None = None,
) -> tuple[Path, Path]:
    when = datetime.now(timezone.utc)
    iso_compact = when.strftime("%Y%m%dT%H%M%S") + "Z"
    n = len(summaries)
    base = f"stage_d_summary--deterministic-v0--N{n}--{iso_compact}"
    root = _resolve_runs_root(runs_root)
    day_dir = root / when.strftime("%Y-%m-%d")
    day_dir.mkdir(parents=True, exist_ok=True)
    md_path = day_dir / f"{base}.md"
    json_path = day_dir / f"{base}.json"

    passed_n = sum(1 for s in summaries if s.gates_passed)
    gate_ids = ("ER1", "ER2", "ER3", "ER4", "ER5")
    gate_pass_counts = {
        g: sum(1 for s in summaries if s.per_gate_verdict.get(g) == "PASS")
        for g in gate_ids
    }

    payload: dict[str, Any] = {
        "schema": SUMMARY_SCHEMA_VERSION,
        "iso_utc": when.strftime("%Y-%m-%dT%H:%M:%SZ"),
        "scenario_id": scenario_id,
        "runner_version": "stage_d_runner_v0_deterministic",
        "n": n,
        "passed": passed_n,
        "per_gate_pass_counts": gate_pass_counts,
        "runs": [
            {
                "run_index": s.run_index,
                "gates_passed": s.gates_passed,
                "per_gate_verdict": s.per_gate_verdict,
                "resolved_count": s.resolved_count,
                "proposed_new_records_count": s.proposed_new_records_count,
                "proposed_aliases_count": s.proposed_aliases_count,
                "unresolvable_count": s.unresolvable_count,
                "sidecar_json": s.sidecar_json_path,
            }
            for s in summaries
        ],
    }

    md_lines = [
        f"# Stage D cohort summary ({n} runs)",
        "",
        f"- **scenario:** `{scenario_id}`",
        "- **runner:** `stage_d_runner_v0_deterministic`",
        f"- **pass rate:** {passed_n}/{n}",
        "",
        "## Per-gate pass counts",
        "",
    ]
    for g in gate_ids:
        md_lines.append(f"- {g}: {gate_pass_counts[g]}/{n}")
    md_lines.extend(["", "## Runs", ""])
    for s in summaries:
        verdict_str = " ".join(
            f"{g}={s.per_gate_verdict.get(g, '?')}" for g in gate_ids
        )
        md_lines.append(
            f"- run {s.run_index + 1}: {'PASS' if s.gates_passed else 'FAIL'} "
            f"| resolved={s.resolved_count} new_records={s.proposed_new_records_count} "
            f"aliases={s.proposed_aliases_count} "
            f"unresolvable={s.unresolvable_count} | {verdict_str} "
            f"| `{s.sidecar_json_path}`"
        )

    md_path.write_text("\n".join(md_lines) + "\n", encoding="utf-8")
    json_path.write_text(
        json.dumps(payload, indent=2, ensure_ascii=False, default=str),
        encoding="utf-8",
    )
    return md_path, json_path


def write_stage_d_cohort_proposals(
    summaries: list[StageDRunSummary],
    *,
    scenario_id: str,
    campaign_id: str,
    proposals_root: Path | None = None,
    source_events: list[dict[str, Any]] | None = None,
    source_events_path: str | None = None,
) -> Path | None:
    """Aggregate Stage D proposals across the cohort into a propose-only sidecar.

    Mirrors the Stage C precedent at
    ``evals/stage_c_npc_candidates_vertical_slice/proposals/c1_registry_proposals_*.json``.
    Stage D's deterministic v0 produces identical output across runs, so the
    sidecar is essentially a snapshot of the (single) deterministic result —
    we still write the cross-run shape so future LLM-augmented Stage D
    versions slot in without changing the proposals contract.
    """
    if not summaries:
        return None

    proposals_dir = proposals_root or (_SLICE_DIR / "proposals")
    proposals_dir.mkdir(parents=True, exist_ok=True)
    when = datetime.now(timezone.utc)
    iso_compact = when.strftime("%Y%m%dT%H%M%S") + "Z"
    out_path = proposals_dir / (
        f"{_sanitize_filename_segment(campaign_id, max_len=40)}"
        f"__{_sanitize_filename_segment(scenario_id, max_len=40)}"
        f"__stage_d_proposals_{iso_compact}.json"
    )

    aggregated_records: dict[str, dict[str, Any]] = {}
    aggregated_aliases: dict[tuple[str, str], dict[str, Any]] = {}
    aggregated_unresolvable: dict[str, dict[str, Any]] = {}

    for s in summaries:
        out = s.extras.get("stage_d_output") or {}
        for rec in out.get("proposed_new_records") or []:
            if not isinstance(rec, dict):
                continue
            slug = str(rec.get("slug") or "").strip().lower()
            if not slug:
                continue
            entry = aggregated_records.setdefault(
                slug,
                {
                    "slug": slug,
                    "display_name": rec.get("display_name", ""),
                    "aliases": list(rec.get("aliases") or []),
                    "status": "candidate",
                    "first_session": rec.get("first_session", 0),
                    "last_session": rec.get("last_session", 0),
                    "hub_path": None,
                    "setting_hub_path": None,
                    "notes": rec.get("notes", ""),
                    "appearance_runs": 0,
                    "sample_run_indices": [],
                },
            )
            entry["appearance_runs"] += 1
            entry["sample_run_indices"].append(s.run_index)

        for rec in out.get("proposed_aliases") or []:
            if not isinstance(rec, dict):
                continue
            tgt = str(rec.get("target_slug") or "").strip().lower()
            txt = str(rec.get("alias_text") or "").strip()
            if not tgt or not txt:
                continue
            key = (tgt, txt.lower())
            entry = aggregated_aliases.setdefault(
                key,
                {
                    "target_slug": tgt,
                    "alias_text": txt,
                    "appearance_runs": 0,
                    "sample_rationale": rec.get("rationale", ""),
                },
            )
            entry["appearance_runs"] += 1

        for rec in out.get("unresolvable") or []:
            if not isinstance(rec, dict):
                continue
            desc = str(rec.get("descriptor") or "").strip()
            if not desc:
                continue
            entry = aggregated_unresolvable.setdefault(
                desc.lower(),
                {
                    "descriptor": desc,
                    "appearance_runs": 0,
                    "sample_reason": rec.get("reason", ""),
                },
            )
            entry["appearance_runs"] += 1

    payload: dict[str, Any] = {
        "schema": PROPOSALS_SCHEMA_VERSION,
        "generated_at": when.isoformat(),
        "campaign_id": campaign_id,
        "scenario_id": scenario_id,
        "runner_version": "stage_d_runner_v0_deterministic",
        "source_run_count": len(summaries),
        "proposed_records": sorted(
            aggregated_records.values(), key=lambda r: r["slug"]
        ),
        "proposed_aliases": sorted(
            aggregated_aliases.values(),
            key=lambda r: (r["target_slug"], r["alias_text"].lower()),
        ),
        "unresolvable": sorted(
            aggregated_unresolvable.values(), key=lambda r: r["descriptor"].lower()
        ),
    }
    # Embed the source events that the cohort consumed so downstream
    # consumers (the promotion CLI and the GM review viewer) can resolve
    # `evidence_event_indices: [1, 4, 5, 6]` to actual event records
    # without re-running Stage D or guessing the events file path.
    if source_events is not None:
        payload["source_events"] = list(source_events)
    if source_events_path:
        payload["source_events_path"] = str(source_events_path)
    out_path.write_text(
        json.dumps(payload, indent=2, ensure_ascii=False, default=str),
        encoding="utf-8",
    )
    return out_path
