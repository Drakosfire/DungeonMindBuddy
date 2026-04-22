"""Persist session-events-extraction benchmark run reports (markdown + JSON sidecar).

Mirrors the shape of evals/session_recap_timeline_pass_vertical_slice/timeline_pass_run_report.py.
"""

from __future__ import annotations

import hashlib
import json
import os
import statistics
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any
import re


_SLICE_DIR = Path(__file__).resolve().parent
_RUNS_ROOT_ENV = "SESSION_EVENTS_RUNS_ROOT"
REPORT_SCHEMA_VERSION = "session_events_run_report_v1"
SUMMARY_SCHEMA_VERSION = "session_events_multi_run_summary_v1"


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
class SessionEventsRunSummary:
    run_index: int
    iso_utc: str
    gates_passed: bool
    scenario_estimated_cost_usd: float
    event_count: int
    violation_counts: dict[str, int]
    per_gate_verdict: dict[str, str]
    primary_md_path: str
    sidecar_json_path: str
    extras: dict[str, Any] = field(default_factory=dict)


@dataclass
class SessionEventsReportPaths:
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
    model_id: str,
    gates_passed: bool,
    utc: datetime,
    run_index: int | None,
) -> str:
    compact = utc.strftime("%Y%m%dT%H%M%S") + "Z"
    scen = _sanitize_filename_segment(scenario_key, max_len=40)
    mod = _sanitize_filename_segment(model_id, max_len=48)
    gate = "PASS" if gates_passed else "FAIL"
    suffix = f"--run{run_index:03d}" if run_index is not None else ""
    return f"session_events--{scen}--{mod}--{gate}--{compact}{suffix}"


def write_session_events_run_report(
    *,
    scenario_id: str,
    model_id: str,
    gates_passed: bool,
    per_gate_verdict: dict[str, str],
    violations: dict[str, list[str]],
    grader_telemetry: dict[str, Any],
    parsed_events: list[dict[str, Any]],
    cost_usd: float,
    usage: dict[str, Any],
    scenario: dict[str, Any] | None = None,
    runs_root: Path | None = None,
    run_index: int | None = None,
    cohort_size: int | None = None,
    utc: datetime | None = None,
) -> tuple[SessionEventsReportPaths, SessionEventsRunSummary]:
    when = utc or datetime.now(timezone.utc)
    iso = when.strftime("%Y-%m-%dT%H:%M:%SZ")
    base_runs = _resolve_runs_root(runs_root)
    day_dir = base_runs / when.strftime("%Y-%m-%d")

    gate_ok = bool(gates_passed)
    base = _build_artifact_basename(
        scenario_key=scenario_id,
        model_id=model_id,
        gates_passed=gate_ok,
        utc=when,
        run_index=(run_index + 1) if run_index is not None else None,
    )
    primary_md = day_dir / f"{base}.md"
    sidecar_json = day_dir / f"{base}.json"
    legacy_dir = _SLICE_DIR / "artifacts"
    legacy_md = legacy_dir / "last_session_events_run.md"
    legacy_json = legacy_dir / "last_session_events_run.json"

    violation_counts = {key: len(rows) for key, rows in violations.items()}
    event_count = int(grader_telemetry.get("event_count", 0))
    cohort_tag = f" | cohort: {cohort_size} | run_index: {run_index}" if cohort_size else ""

    sidecar: dict[str, Any] = {
        "schema": REPORT_SCHEMA_VERSION,
        "iso_utc": iso,
        "scenario_id": scenario_id,
        "model_id": model_id,
        "run_index": run_index,
        "cohort_size": cohort_size,
        "gates_passed": gate_ok,
        "per_gate_verdict": dict(per_gate_verdict),
        "scenario_estimated_cost_usd": round(cost_usd, 6),
        "event_count": event_count,
        "violation_counts": violation_counts,
        "violations": {k: list(v) for k, v in violations.items()},
        "grader_telemetry": dict(grader_telemetry),
        "usage": dict(usage),
        "grading": (scenario or {}).get("grading"),
    }

    rel_primary = primary_md
    try:
        rel_primary = primary_md.resolve().relative_to(_SLICE_DIR.resolve())
    except ValueError:
        rel_primary = Path(primary_md.name)

    header = (
        f"<!-- benchmark_artifact: {REPORT_SCHEMA_VERSION} | iso_utc: {iso} "
        f"| scenario: {scenario_id} | model: {model_id} | gates: {'PASS' if gate_ok else 'FAIL'} "
        f"| primary: {rel_primary.as_posix()}{cohort_tag} -->\n"
    )
    verdict_str = " ".join(f"{k}={v}" for k, v in sorted(per_gate_verdict.items()))
    viol_lines = "\n".join(
        f"  [{bucket}] {msg}"
        for bucket, msgs in violations.items()
        for msg in msgs
    )
    telemetry_str = json.dumps(grader_telemetry, ensure_ascii=False, sort_keys=True, default=str)
    body = (
        f"{header}\n"
        "## Summary\n\n"
        f"- **scenario_id:** `{scenario_id}`\n"
        f"- **model:** `{model_id}`\n"
        f"- **gates:** {'PASS' if gate_ok else 'FAIL'}\n"
        f"- **per_gate:** `{verdict_str}`\n"
        f"- **event_count:** {event_count}\n"
        f"- **cost_usd:** {cost_usd:.6f}\n\n"
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

    paths = SessionEventsReportPaths(
        primary_md=primary_md,
        sidecar_json=sidecar_json,
        legacy_md=legacy_md,
        legacy_json=legacy_json,
    )
    summary = SessionEventsRunSummary(
        run_index=run_index if run_index is not None else 0,
        iso_utc=iso,
        gates_passed=gate_ok,
        scenario_estimated_cost_usd=round(cost_usd, 6),
        event_count=event_count,
        violation_counts=violation_counts,
        per_gate_verdict=dict(per_gate_verdict),
        primary_md_path=str(primary_md),
        sidecar_json_path=str(sidecar_json),
        extras={"grader_telemetry": dict(grader_telemetry)},
    )
    return paths, summary


def write_session_events_multi_summary(
    summaries: list[SessionEventsRunSummary],
    *,
    model_id: str,
    scenario_id: str,
    runs_root: Path | None = None,
) -> tuple[Path, Path]:
    when = datetime.now(timezone.utc)
    iso_compact = when.strftime("%Y%m%dT%H%M%S") + "Z"
    n = len(summaries)
    mod = _sanitize_filename_segment(model_id, max_len=48)
    base = f"session_events_summary--{mod}--N{n}--{iso_compact}"
    root = _resolve_runs_root(runs_root)
    day_dir = root / when.strftime("%Y-%m-%d")
    day_dir.mkdir(parents=True, exist_ok=True)
    md_path = day_dir / f"{base}.md"
    json_path = day_dir / f"{base}.json"

    costs = [s.scenario_estimated_cost_usd for s in summaries]
    passed_n = sum(1 for s in summaries if s.gates_passed)

    gate_ids = ("SE1", "SE2", "SE3", "SE4", "SE5")
    gate_pass_counts = {
        g: sum(1 for s in summaries if s.per_gate_verdict.get(g) == "PASS")
        for g in gate_ids
    }

    payload: dict[str, Any] = {
        "schema": SUMMARY_SCHEMA_VERSION,
        "iso_utc": when.strftime("%Y-%m-%dT%H:%M:%SZ"),
        "scenario_id": scenario_id,
        "model_id": model_id,
        "n": n,
        "passed": passed_n,
        "per_gate_pass_counts": gate_pass_counts,
        "cost_usd": {
            "min": round(min(costs), 6) if costs else 0.0,
            "max": round(max(costs), 6) if costs else 0.0,
            "mean": round(statistics.mean(costs), 6) if costs else 0.0,
            "sum": round(sum(costs), 6),
        },
        "runs": [
            {
                "run_index": s.run_index,
                "gates_passed": s.gates_passed,
                "per_gate_verdict": s.per_gate_verdict,
                "cost_usd": s.scenario_estimated_cost_usd,
                "event_count": s.event_count,
                "sidecar_json": s.sidecar_json_path,
            }
            for s in summaries
        ],
    }

    md_lines = [
        f"# Session-events-extraction cohort summary ({n} runs)",
        "",
        f"- **model:** `{model_id}`",
        f"- **scenario:** `{scenario_id}`",
        f"- **pass rate:** {passed_n}/{n}",
        f"- **cost sum:** ${payload['cost_usd']['sum']:.4f} "
        f"(mean ${payload['cost_usd']['mean']:.4f}, max ${payload['cost_usd']['max']:.4f})",
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
            f"| ${s.scenario_estimated_cost_usd:.4f} | events={s.event_count} "
            f"| {verdict_str} | `{s.sidecar_json_path}`"
        )

    md_path.write_text("\n".join(md_lines) + "\n", encoding="utf-8")
    json_path.write_text(
        json.dumps(payload, indent=2, ensure_ascii=False, default=str),
        encoding="utf-8",
    )
    return md_path, json_path
