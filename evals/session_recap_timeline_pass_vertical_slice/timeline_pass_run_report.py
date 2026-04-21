"""Persist Stage-2 v1 timeline-pass benchmark run reports (markdown + JSON sidecar)."""

from __future__ import annotations

import contextlib
import hashlib
import io
import json
import os
import statistics
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from evals.lysandra_vertical_slice.step1_planner_trace import (
    PlannerStep1Run,
    _sanitize_planner_step1_filename_segment,
)

_SLICE_DIR = Path(__file__).resolve().parent
_RUNS_ROOT_ENV = "TIMELINE_PASS_RUNS_ROOT"
REPORT_SCHEMA_VERSION = "timeline_pass_run_report_v1"
SUMMARY_SCHEMA_VERSION = "timeline_pass_multi_run_summary_v1"


@dataclass
class TimelinePassRunSummary:
    run_index: int
    iso_utc: str
    gates_passed: bool
    scenario_estimated_cost_usd: float
    tool_trace_rows: int
    tool_trace_tools: list[str]
    violation_counts: dict[str, int]
    per_gate_verdict: dict[str, str]
    final_text_chars: int
    primary_md_path: str
    sidecar_json_path: str
    extras: dict[str, Any] = field(default_factory=dict)


@dataclass
class TimelinePassReportPaths:
    primary_md: Path
    sidecar_json: Path
    legacy_md: Path
    legacy_json: Path


def _resolve_runs_root(slice_dir: Path | None, runs_root: Path | None) -> Path:
    root = slice_dir or _SLICE_DIR
    if runs_root is not None:
        return runs_root
    env = os.environ.get(_RUNS_ROOT_ENV, "").strip()
    if env:
        return Path(env).expanduser().resolve()
    return root / "artifacts" / "runs"


def _legacy_dir(slice_dir: Path | None) -> Path:
    return (slice_dir or _SLICE_DIR) / "artifacts"


def _build_artifact_basename(
    *,
    scenario_key: str,
    model_id: str,
    gates_passed: bool,
    utc: datetime,
    run_index: int | None,
    artifact_turn_pack: str = "1turn",
) -> str:
    compact = utc.strftime("%Y%m%dT%H%M%S") + "Z"
    scen = _sanitize_planner_step1_filename_segment(scenario_key, max_len=40)
    mod = _sanitize_planner_step1_filename_segment(model_id, max_len=48)
    gate = "PASS" if gates_passed else "FAIL"
    pack = _sanitize_planner_step1_filename_segment(artifact_turn_pack, max_len=16)
    suffix = f"--run{run_index:03d}" if run_index is not None else ""
    return f"timeline_pass--{scen}--{mod}--{gate}--{pack}--{compact}{suffix}"


def _scenario_estimated_cost_usd(run: PlannerStep1Run) -> float:
    tc = run.detail.telemetry_cost or {}
    raw = tc.get("scenario_estimated_cost_usd", tc.get("planner_estimated_cost_usd", 0))
    try:
        return float(raw or 0)
    except (TypeError, ValueError):
        return 0.0


def _tool_trace_tools(run: PlannerStep1Run) -> list[str]:
    return [str(row.get("tool", "")) for row in (run.detail.tool_trace or [])]


def _violation_counts(run: PlannerStep1Run) -> dict[str, int]:
    return {key: len(rows) for key, rows in (run.result.violations or {}).items()}


def _capture_review_markdown(print_callable: Any, **kwargs: Any) -> str:
    buf = io.StringIO()
    with contextlib.redirect_stdout(buf):
        print_callable(**kwargs)
    return buf.getvalue()


def _final_text_sha16(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()[:16]


def write_timeline_pass_run_report(
    run: PlannerStep1Run,
    *,
    corpus_dir: Path,
    model_id: str,
    review_text: str,
    scenario: dict[str, Any] | None = None,
    runs_root: Path | None = None,
    slice_dir: Path | None = None,
    utc: datetime | None = None,
    run_index: int | None = None,
    cohort_size: int | None = None,
    grader_telemetry: dict[str, Any] | None = None,
    per_gate_verdict: dict[str, str] | None = None,
    artifact_turn_pack: str = "1turn",
) -> tuple[TimelinePassReportPaths, TimelinePassRunSummary]:
    when = utc or datetime.now(timezone.utc)
    iso = when.strftime("%Y-%m-%dT%H:%M:%SZ")
    base_runs = _resolve_runs_root(slice_dir, runs_root)
    day_dir = base_runs / when.strftime("%Y-%m-%d")
    scenario_key = (run.scenario_key or "unknown").strip() or "unknown"
    gate_ok = bool(run.result.passed)
    base = _build_artifact_basename(
        scenario_key=scenario_key,
        model_id=model_id,
        gates_passed=gate_ok,
        utc=when,
        run_index=(run_index + 1) if run_index is not None else None,
        artifact_turn_pack=artifact_turn_pack,
    )
    primary_md = day_dir / f"{base}.md"
    sidecar_json = day_dir / f"{base}.json"
    legacy_dir = _legacy_dir(slice_dir)
    legacy_md = legacy_dir / "last_timeline_pass_run.md"
    legacy_json = legacy_dir / "last_timeline_pass_run.json"

    cost_usd = _scenario_estimated_cost_usd(run)
    tools = _tool_trace_tools(run)
    violation_counts = _violation_counts(run)
    final_text = run.detail.final_text or ""
    final_text_chars = len(final_text)
    last_response_id = str(getattr(run.detail, "last_response_id", "") or "")

    sidecar: dict[str, Any] = {
        "schema": REPORT_SCHEMA_VERSION,
        "iso_utc": iso,
        "scenario_id": run.result.scenario_id,
        "model_id": model_id,
        "run_index": run_index,
        "cohort_size": cohort_size,
        "gates_passed": gate_ok,
        "per_gate_verdict": dict(per_gate_verdict or {}),
        "scenario_estimated_cost_usd": round(cost_usd, 6),
        "tool_trace_rows": len(tools),
        "tool_trace_tools": tools,
        "violation_counts": violation_counts,
        "violations": dict(run.result.violations or {}),
        "grader_telemetry": dict(grader_telemetry or {}),
        "corpus_fingerprint": run.corpus_fingerprint,
        "corpus_dir": str(corpus_dir.resolve()),
        "final_text_sha256_16": _final_text_sha16(final_text),
        "final_text_chars": final_text_chars,
        "primary_response_id": last_response_id,
        "telemetry_cost": dict(run.detail.telemetry_cost or {}),
        "grading": (scenario or {}).get("grading") if scenario else None,
        "artifact_turn_pack": artifact_turn_pack,
    }

    rel_primary = primary_md
    try:
        rel_primary = primary_md.resolve().relative_to((slice_dir or _SLICE_DIR).resolve())
    except ValueError:
        rel_primary = Path(primary_md.name)
    cohort_tag = f" | cohort: {cohort_size} | run_index: {run_index}" if cohort_size else ""
    header = (
        f"<!-- benchmark_artifact: {REPORT_SCHEMA_VERSION} | iso_utc: {iso} "
        f"| scenario: {scenario_key} | model: {model_id} | gates: {'PASS' if gate_ok else 'FAIL'} "
        f"| primary: {rel_primary.as_posix()}{cohort_tag} -->\n"
    )
    sidecar_pretty = json.dumps(sidecar, indent=2, ensure_ascii=False, default=str)
    body = (
        f"{header}\n"
        "## Review (printed)\n\n"
        "```\n"
        f"{review_text.rstrip()}\n"
        "```\n\n"
        "## Sidecar JSON\n\n"
        "```json\n"
        f"{sidecar_pretty}\n"
        "```\n"
    )

    primary_md.parent.mkdir(parents=True, exist_ok=True)
    primary_md.write_text(body, encoding="utf-8")
    sidecar_json.write_text(json.dumps(sidecar, indent=2, ensure_ascii=False, default=str), encoding="utf-8")
    legacy_md.parent.mkdir(parents=True, exist_ok=True)
    legacy_md.write_text(body, encoding="utf-8")
    legacy_json.write_text(json.dumps(sidecar, indent=2, ensure_ascii=False, default=str), encoding="utf-8")

    paths = TimelinePassReportPaths(
        primary_md=primary_md,
        sidecar_json=sidecar_json,
        legacy_md=legacy_md,
        legacy_json=legacy_json,
    )
    summary = TimelinePassRunSummary(
        run_index=run_index if run_index is not None else 0,
        iso_utc=iso,
        gates_passed=gate_ok,
        scenario_estimated_cost_usd=round(cost_usd, 6),
        tool_trace_rows=len(tools),
        tool_trace_tools=tools,
        violation_counts=violation_counts,
        per_gate_verdict=dict(per_gate_verdict or {}),
        final_text_chars=final_text_chars,
        primary_md_path=str(primary_md),
        sidecar_json_path=str(sidecar_json),
        extras={
            "corpus_fingerprint": run.corpus_fingerprint,
            "primary_response_id": last_response_id,
            "grader_telemetry": dict(grader_telemetry or {}),
        },
    )
    return paths, summary


def capture_and_write_timeline_pass_report(
    *,
    print_callable: Any,
    print_kwargs: dict[str, Any],
    run: PlannerStep1Run,
    corpus_dir: Path,
    model_id: str,
    scenario: dict[str, Any] | None = None,
    runs_root: Path | None = None,
    run_index: int | None = None,
    cohort_size: int | None = None,
    grader_telemetry: dict[str, Any] | None = None,
    per_gate_verdict: dict[str, str] | None = None,
    artifact_turn_pack: str = "1turn",
) -> tuple[TimelinePassReportPaths, TimelinePassRunSummary]:
    review = _capture_review_markdown(print_callable, **print_kwargs)
    print(review, end="" if review.endswith("\n") else "\n")
    return write_timeline_pass_run_report(
        run,
        corpus_dir=corpus_dir,
        model_id=model_id,
        review_text=review,
        scenario=scenario,
        runs_root=runs_root,
        run_index=run_index,
        cohort_size=cohort_size,
        grader_telemetry=grader_telemetry,
        per_gate_verdict=per_gate_verdict,
        artifact_turn_pack=artifact_turn_pack,
    )


def write_timeline_pass_multi_summary(
    summaries: list[TimelinePassRunSummary],
    *,
    model_id: str,
    scenario_id: str,
    runs_root: Path | None = None,
) -> tuple[Path, Path]:
    when = datetime.now(timezone.utc)
    iso_compact = when.strftime("%Y%m%dT%H%M%S") + "Z"
    n = len(summaries)
    mod = _sanitize_planner_step1_filename_segment(model_id, max_len=48)
    _ = _sanitize_planner_step1_filename_segment(scenario_id, max_len=40)
    base = f"timeline_pass_summary--{mod}--N{n}--{iso_compact}"
    root = _resolve_runs_root(None, runs_root)
    day_dir = root / when.strftime("%Y-%m-%d")
    day_dir.mkdir(parents=True, exist_ok=True)
    md_path = day_dir / f"{base}.md"
    json_path = day_dir / f"{base}.json"

    costs = [s.scenario_estimated_cost_usd for s in summaries]
    passed_n = sum(1 for s in summaries if s.gates_passed)

    gate_ids = ("TP1", "TP2", "TP3", "TP4", "TP5")
    gate_pass_counts = {
        g: sum(1 for s in summaries if (s.per_gate_verdict.get(g) == "PASS"))
        for g in gate_ids
    }

    payload = {
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
                "sidecar_json": s.sidecar_json_path,
            }
            for s in summaries
        ],
    }
    md_lines = [
        f"# Timeline-pass cohort summary ({n} runs)",
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
            f"| ${s.scenario_estimated_cost_usd:.4f} | {verdict_str} | "
            f"`{s.sidecar_json_path}`"
        )
    md_path.write_text("\n".join(md_lines) + "\n", encoding="utf-8")
    json_path.write_text(
        json.dumps(payload, indent=2, ensure_ascii=False, default=str),
        encoding="utf-8",
    )
    return md_path, json_path
