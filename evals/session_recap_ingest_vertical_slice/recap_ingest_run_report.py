"""Persist Scope-B recap-ingest run reports to disk (single + multi-run).

Two artifacts per run:

1. ``<runs_root>/<YYYY-MM-DD>/recap_ingest--<scen>--<model>--PASS|FAIL--<turns>--<UTC>[--runNNN].md``
   Full markdown of the printed review (mirrors ``print_recap_ingest_review`` output)
   plus a small structured header for fast grep / diffing.
2. Sidecar ``<same>.json`` with versioned, machine-readable fields used by the multi-run
   aggregator and external graders.

When the harness runs ``--n N`` (N>1) we additionally write a
``recap_ingest_summary--<model>--<UTC>--N<N>.md`` and matching ``.json`` summarising
pass rates, cost spread, and ``recap_write`` payload variance across the cohort.

Mirrors ``last_recap_ingest_run.md`` / ``.json`` for "show me the last run" tooling.
"""

from __future__ import annotations

import contextlib
import hashlib
import io
import json
import os
import statistics
import sys
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from evals.lysandra_vertical_slice.step1_planner_trace import (
    PlannerStep1Run,
    _sanitize_planner_step1_filename_segment,
)
from evals.session_recap_ingest_vertical_slice.scope_b_grader import (
    collect_scope_b_recap_ingest_report_extras,
)

REPORT_SCHEMA_VERSION = "recap_ingest_run_report_v1"
SUMMARY_SCHEMA_VERSION = "recap_ingest_multi_run_summary_v1"

_SLICE_DIR = Path(__file__).resolve().parent
_RUNS_ROOT_ENV = "RECAP_INGEST_RUNS_ROOT"


@dataclass
class RecapIngestReportPaths:
    primary_md: Path
    sidecar_json: Path
    legacy_md: Path
    legacy_json: Path


@dataclass
class RecapIngestRunSummary:
    """One row in the multi-run summary."""

    run_index: int
    iso_utc: str
    gates_passed: bool
    tool_trace_gates_passed: bool | None
    payload_gates_passed: bool | None
    scenario_estimated_cost_usd: float
    tool_trace_rows: int
    tool_trace_tools: list[str]
    violation_counts: dict[str, int]
    recap_write_sha256_16: str | None
    final_text_chars: int
    primary_md_path: str
    sidecar_json_path: str
    extras: dict[str, Any] = field(default_factory=dict)


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
    followup: bool,
    utc: datetime,
    run_index: int | None,
) -> str:
    compact = utc.strftime("%Y%m%dT%H%M%S") + "Z"
    scen = _sanitize_planner_step1_filename_segment(scenario_key, max_len=40)
    mod = _sanitize_planner_step1_filename_segment(model_id, max_len=48)
    gate = "PASS" if gates_passed else "FAIL"
    turns = "2turn" if followup else "1turn"
    suffix = f"--run{run_index:03d}" if run_index is not None else ""
    return f"recap_ingest--{scen}--{mod}--{gate}--{turns}--{compact}{suffix}"


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


def _extract_recap_write_payload(run: PlannerStep1Run) -> dict[str, Any] | None:
    """Pull the ``recap_write`` field out of the planner envelope, if present."""
    text = (run.detail.final_text or "").strip()
    if not text.startswith("{"):
        return None
    try:
        obj = json.loads(text)
    except json.JSONDecodeError:
        return None
    if not isinstance(obj, dict):
        return None
    rw = obj.get("recap_write")
    return rw if isinstance(rw, dict) else None


def _sha256_16(payload: Any) -> str:
    body = json.dumps(payload, ensure_ascii=False, sort_keys=True, default=str).encode("utf-8")
    return hashlib.sha256(body).hexdigest()[:16]


def _capture_review_markdown(print_callable: Any, **kwargs: Any) -> str:
    """Run ``print_callable(**kwargs)`` and return its stdout as a string.

    The caller is expected to also print the buffered text to the real stdout afterwards
    so the user still sees the review in their terminal. We intentionally do not Tee
    here to keep the captured artifact byte-identical to what we render on disk.
    """
    buf = io.StringIO()
    with contextlib.redirect_stdout(buf):
        print_callable(**kwargs)
    return buf.getvalue()


def _markdown_body(
    *,
    review_text: str,
    header: str,
    sidecar: dict[str, Any],
) -> str:
    sidecar_pretty = json.dumps(sidecar, indent=2, ensure_ascii=False, default=str)
    return (
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


def write_recap_ingest_run_report(
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
    recap_context_snapshot: Any | None = None,
) -> tuple[RecapIngestReportPaths, RecapIngestRunSummary]:
    """Write per-run markdown + JSON for a single Scope-B planner turn.

    ``review_text`` is whatever ``print_recap_ingest_review`` produced (typically captured
    via :func:`_capture_review_markdown`). Pass ``run_index`` (0-based) and ``cohort_size``
    when invoked inside a multi-run loop so the basename and sidecar are unambiguous.

    Returns ``(paths, summary)``; ``summary`` is reused by
    :func:`write_recap_ingest_multi_summary`.
    """
    when = utc or datetime.now(timezone.utc)
    iso = when.strftime("%Y-%m-%dT%H:%M:%SZ")
    base_runs = _resolve_runs_root(slice_dir, runs_root)
    day_dir = base_runs / when.strftime("%Y-%m-%d")
    scenario_key = (run.scenario_key or "unknown").strip() or "unknown"
    followup = bool((run.followup_user_line or "").strip())
    gate_ok = bool(run.result.passed)
    base = _build_artifact_basename(
        scenario_key=scenario_key,
        model_id=model_id,
        gates_passed=gate_ok,
        followup=followup,
        utc=when,
        run_index=(run_index + 1) if run_index is not None else None,
    )
    primary_md = day_dir / f"{base}.md"
    sidecar_json = day_dir / f"{base}.json"
    legacy_dir = _legacy_dir(slice_dir)
    legacy_md = legacy_dir / "last_recap_ingest_run.md"
    legacy_json = legacy_dir / "last_recap_ingest_run.json"

    payload = _extract_recap_write_payload(run)
    payload_sha = _sha256_16(payload) if payload is not None else None
    cost_usd = _scenario_estimated_cost_usd(run)
    tools = _tool_trace_tools(run)
    violation_counts = _violation_counts(run)
    final_text_chars = len(run.detail.final_text or "")
    last_response_id = str(getattr(run.detail, "last_response_id", "") or "")
    scope_b_extras: dict[str, Any] = {}
    if scenario is not None:
        try:
            scope_b_extras = collect_scope_b_recap_ingest_report_extras(
                scenario,
                run.detail,
                corpus_dir,
                recap_context_snapshot=recap_context_snapshot,
            )
        except Exception as exc:  # noqa: BLE001 - report writer must never raise
            scope_b_extras = {"scope_b_extras_error": repr(exc)}

    sidecar: dict[str, Any] = {
        "schema": REPORT_SCHEMA_VERSION,
        "iso_utc": iso,
        "scenario_id": run.result.scenario_id,
        "model_id": model_id,
        "run_index": run_index,
        "cohort_size": cohort_size,
        "gates_passed": gate_ok,
        "tool_trace_gates_passed": run.result.tool_trace_gates_passed,
        "payload_gates_passed": run.result.payload_gates_passed,
        "scenario_estimated_cost_usd": round(cost_usd, 6),
        "tool_trace_rows": len(tools),
        "tool_trace_tools": tools,
        "violation_counts": violation_counts,
        "violations": dict(run.result.violations or {}),
        "corpus_fingerprint": run.corpus_fingerprint,
        "corpus_dir": str(corpus_dir.resolve()),
        "recap_write_payload": payload,
        "recap_write_payload_sha256_16": payload_sha,
        "final_text_chars": final_text_chars,
        "primary_response_id": last_response_id,
        "telemetry_cost": dict(run.detail.telemetry_cost or {}),
        "scope_b_extras": scope_b_extras,
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
        f"| tool_trace_gates: {run.result.tool_trace_gates_passed} "
        f"| payload_gates: {run.result.payload_gates_passed} "
        f"| primary: {rel_primary.as_posix()}{cohort_tag} -->\n"
    )
    body = _markdown_body(review_text=review_text, header=header, sidecar=sidecar)

    primary_md.parent.mkdir(parents=True, exist_ok=True)
    primary_md.write_text(body, encoding="utf-8")
    sidecar_json.write_text(json.dumps(sidecar, indent=2, ensure_ascii=False, default=str), encoding="utf-8")
    legacy_md.parent.mkdir(parents=True, exist_ok=True)
    legacy_md.write_text(body, encoding="utf-8")
    legacy_json.write_text(json.dumps(sidecar, indent=2, ensure_ascii=False, default=str), encoding="utf-8")

    paths = RecapIngestReportPaths(
        primary_md=primary_md,
        sidecar_json=sidecar_json,
        legacy_md=legacy_md,
        legacy_json=legacy_json,
    )
    summary = RecapIngestRunSummary(
        run_index=run_index if run_index is not None else 0,
        iso_utc=iso,
        gates_passed=gate_ok,
        tool_trace_gates_passed=run.result.tool_trace_gates_passed,
        payload_gates_passed=run.result.payload_gates_passed,
        scenario_estimated_cost_usd=round(cost_usd, 6),
        tool_trace_rows=len(tools),
        tool_trace_tools=tools,
        violation_counts=violation_counts,
        recap_write_sha256_16=payload_sha,
        final_text_chars=final_text_chars,
        primary_md_path=str(primary_md),
        sidecar_json_path=str(sidecar_json),
        extras={
            "corpus_fingerprint": run.corpus_fingerprint,
            "primary_response_id": last_response_id,
            "scope_b_extras": scope_b_extras,
        },
    )
    return paths, summary


def _aggregate_costs(values: list[float]) -> dict[str, float]:
    if not values:
        return {"min": 0.0, "max": 0.0, "mean": 0.0, "sum": 0.0}
    return {
        "min": round(min(values), 6),
        "max": round(max(values), 6),
        "mean": round(statistics.mean(values), 6),
        "sum": round(sum(values), 6),
    }


def _aggregate_ints(values: list[int]) -> dict[str, float]:
    if not values:
        return {"min": 0, "max": 0, "mean": 0.0}
    return {
        "min": int(min(values)),
        "max": int(max(values)),
        "mean": round(statistics.mean(values), 2),
    }


def _pass_rate(passed: int, total: int) -> str:
    return f"{passed}/{total}"


def write_recap_ingest_multi_summary(
    summaries: list[RecapIngestRunSummary],
    *,
    model_id: str,
    scenario_id: str,
    runs_root: Path | None = None,
    slice_dir: Path | None = None,
    utc: datetime | None = None,
) -> tuple[Path, Path]:
    """Write a markdown + JSON summary aggregating an N-run cohort."""
    if not summaries:
        raise ValueError("no summaries to aggregate")
    when = utc or datetime.now(timezone.utc)
    iso = when.strftime("%Y-%m-%dT%H:%M:%SZ")
    compact = when.strftime("%Y%m%dT%H%M%S") + "Z"
    base_runs = _resolve_runs_root(slice_dir, runs_root)
    day_dir = base_runs / when.strftime("%Y-%m-%d")
    n = len(summaries)
    mod = _sanitize_planner_step1_filename_segment(model_id, max_len=48)
    fname = f"recap_ingest_summary--{mod}--N{n}--{compact}"
    md_path = day_dir / f"{fname}.md"
    json_path = day_dir / f"{fname}.json"

    gates_pass = sum(1 for s in summaries if s.gates_passed)
    tool_pass = sum(1 for s in summaries if s.tool_trace_gates_passed)
    payload_pass = sum(1 for s in summaries if s.payload_gates_passed)
    cost_agg = _aggregate_costs([s.scenario_estimated_cost_usd for s in summaries])
    rows_agg = _aggregate_ints([s.tool_trace_rows for s in summaries])
    distinct_payload_hashes = sorted(
        {s.recap_write_sha256_16 for s in summaries if s.recap_write_sha256_16}
    )
    violation_keys: dict[str, int] = {}
    for s in summaries:
        for key, count in s.violation_counts.items():
            violation_keys[key] = violation_keys.get(key, 0) + count
    distinct_tool_signatures = sorted(
        {",".join(s.tool_trace_tools) for s in summaries}
    )

    preview_runs = 0
    commit_runs = 0
    no_write_runs = 0
    distinct_phase_shapes: dict[str, int] = {}
    soft_obs_total = 0
    for s in summaries:
        sb = s.extras.get("scope_b_extras") if isinstance(s.extras, dict) else None
        sb = sb if isinstance(sb, dict) else {}
        phases = sb.get("write_corpus_file_phases") if isinstance(sb, dict) else None
        if isinstance(phases, dict):
            if int(phases.get("calls", 0) or 0) == 0:
                no_write_runs += 1
            if int(phases.get("previews", 0) or 0) > 0:
                preview_runs += 1
            if int(phases.get("commits", 0) or 0) > 0:
                commit_runs += 1
            shape = str(phases.get("phases", "") or "")
            if shape:
                distinct_phase_shapes[shape] = distinct_phase_shapes.get(shape, 0) + 1
        soft = sb.get("write_corpus_file_soft_observations") if isinstance(sb, dict) else None
        if isinstance(soft, list):
            soft_obs_total += len(soft)

    # Commit-outcome aggregation (BACKLOG §1.0 fix). The cohort answers:
    # of runs that *attempted* a commit (``commit_rate`` denominator), how many
    # actually had the server land bytes vs. refuse the write (e.g. stale
    # confirm_token, allowlist rejection, disabled writes)? This split is what
    # ``gates_passed`` previously hid: a run could attempt a commit, get
    # ``ok=false``, and still pass the call-shape gate.
    commit_attempted = 0
    commit_succeeded = 0
    commit_refused = 0
    commit_unknown = 0
    commit_error_kinds: dict[str, int] = {}
    for s in summaries:
        sb = s.extras.get("scope_b_extras") if isinstance(s.extras, dict) else None
        sb = sb if isinstance(sb, dict) else {}
        outcome = sb.get("write_corpus_file_last_commit_outcome")
        if not isinstance(outcome, dict):
            continue
        commit_attempted += 1
        succeeded = outcome.get("succeeded")
        if succeeded is True:
            commit_succeeded += 1
        elif succeeded is False:
            commit_refused += 1
            err = str(outcome.get("error") or "").strip()
            # Bucket by leading error phrase so cohort summaries surface the
            # *kind* of refusal (stale token vs. allowlist vs. disabled writes)
            # without leaking full diff payloads.
            if err:
                kind = err.split(".")[0][:120]
                commit_error_kinds[kind] = commit_error_kinds.get(kind, 0) + 1
            else:
                commit_error_kinds["<unspecified>"] = (
                    commit_error_kinds.get("<unspecified>", 0) + 1
                )
        else:
            commit_unknown += 1

    # Mechanical-payload comparison stratified by tool adoption (BACKLOG §1.5 / opt b).
    #
    # The cohort answers two questions:
    # * Did the model invoke ``build_recap_write_payload``? (``called`` / ``not_called``)
    # * Among runs where the comparison was applicable (model emitted a parseable
    #   ``recap_write`` AND we had snapshot + raw notes), how many had mechanical
    #   sub-fields byte-equal to the helper's expected output?
    # ``not_applicable`` rows aren't included in the rate denominator (no signal).
    mech_called = 0
    mech_called_match = 0
    mech_called_applicable = 0
    mech_uncalled_match = 0
    mech_uncalled_applicable = 0
    mech_total_applicable = 0
    mech_total_match = 0
    for s in summaries:
        sb = s.extras.get("scope_b_extras") if isinstance(s.extras, dict) else None
        sb = sb if isinstance(sb, dict) else {}
        called = bool(sb.get("build_recap_write_payload_called"))
        match = sb.get("mechanical_fields_match")
        if called:
            mech_called += 1
        if match is None:
            continue
        mech_total_applicable += 1
        if match:
            mech_total_match += 1
        if called:
            mech_called_applicable += 1
            if match:
                mech_called_match += 1
        else:
            mech_uncalled_applicable += 1
            if match:
                mech_uncalled_match += 1

    aggregate: dict[str, Any] = {
        "runs": n,
        "gates_pass_rate": _pass_rate(gates_pass, n),
        "tool_trace_gates_pass_rate": _pass_rate(tool_pass, n),
        "payload_gates_pass_rate": _pass_rate(payload_pass, n),
        "cost_usd": cost_agg,
        "tool_trace_rows": rows_agg,
        "distinct_recap_write_sha256_16": distinct_payload_hashes,
        "violation_counts_total": violation_keys,
        "distinct_tool_trace_signatures": distinct_tool_signatures,
        "write_corpus_file": {
            "preview_rate": _pass_rate(preview_runs, n),
            "commit_rate": _pass_rate(commit_runs, n),
            "no_write_rate": _pass_rate(no_write_runs, n),
            "distinct_phase_shapes": distinct_phase_shapes,
            "soft_observations_total": soft_obs_total,
        },
        "commit_outcome": {
            "attempted_runs": commit_attempted,
            "succeeded_runs": commit_succeeded,
            "refused_runs": commit_refused,
            "unknown_runs": commit_unknown,
            "success_rate_when_attempted": _pass_rate(
                commit_succeeded, commit_attempted
            ),
            "refusal_rate_when_attempted": _pass_rate(
                commit_refused, commit_attempted
            ),
            "refusal_kinds": commit_error_kinds,
        },
        "mechanical_fields": {
            "build_recap_write_payload_called_rate": _pass_rate(mech_called, n),
            "match_rate_overall": _pass_rate(mech_total_match, mech_total_applicable),
            "match_rate_when_called": _pass_rate(
                mech_called_match, mech_called_applicable
            ),
            "match_rate_when_not_called": _pass_rate(
                mech_uncalled_match, mech_uncalled_applicable
            ),
            "applicable_runs": mech_total_applicable,
            "not_applicable_runs": n - mech_total_applicable,
        },
    }

    sidecar: dict[str, Any] = {
        "schema": SUMMARY_SCHEMA_VERSION,
        "iso_utc": iso,
        "model_id": model_id,
        "scenario_id": scenario_id,
        "runs": n,
        "aggregate": aggregate,
        "results": [
            {
                "run_index": s.run_index,
                "iso_utc": s.iso_utc,
                "gates_passed": s.gates_passed,
                "tool_trace_gates_passed": s.tool_trace_gates_passed,
                "payload_gates_passed": s.payload_gates_passed,
                "scenario_estimated_cost_usd": s.scenario_estimated_cost_usd,
                "tool_trace_rows": s.tool_trace_rows,
                "tool_trace_tools": s.tool_trace_tools,
                "violation_counts": s.violation_counts,
                "recap_write_sha256_16": s.recap_write_sha256_16,
                "final_text_chars": s.final_text_chars,
                "primary_md_path": s.primary_md_path,
                "sidecar_json_path": s.sidecar_json_path,
                "extras": s.extras,
            }
            for s in summaries
        ],
    }

    rows = []
    for s in summaries:
        v_repr = ", ".join(f"{k}:{c}" for k, c in sorted(s.violation_counts.items())) or "-"
        rows.append(
            f"| {s.run_index} | {'PASS' if s.gates_passed else 'FAIL'} "
            f"| {s.tool_trace_gates_passed} | {s.payload_gates_passed} "
            f"| {s.scenario_estimated_cost_usd} | {s.tool_trace_rows} "
            f"| {s.recap_write_sha256_16 or '-'} | {v_repr} |"
        )
    table = (
        "| run | gates | tool_trace | payload | cost_usd | trace_rows | recap_write_sha16 | violations |\n"
        "|-----|-------|------------|---------|---------:|-----------:|-------------------|------------|\n"
        + "\n".join(rows)
        + "\n"
    )
    header = (
        f"<!-- benchmark_artifact: {SUMMARY_SCHEMA_VERSION} | iso_utc: {iso} "
        f"| scenario: {scenario_id} | model: {model_id} | runs: {n} "
        f"| gates_pass: {aggregate['gates_pass_rate']} -->\n"
    )
    md_body = (
        f"{header}\n# Scope-B recap-ingest cohort summary (N={n})\n\n"
        f"- **scenario**: `{scenario_id}`\n"
        f"- **model**: `{model_id}`\n"
        f"- **iso_utc**: `{iso}`\n"
        f"- **gates pass rate**: {aggregate['gates_pass_rate']}\n"
        f"- **tool_trace pass rate**: {aggregate['tool_trace_gates_pass_rate']}\n"
        f"- **payload pass rate**: {aggregate['payload_gates_pass_rate']}\n"
        f"- **cost_usd**: min={cost_agg['min']} mean={cost_agg['mean']} max={cost_agg['max']} sum={cost_agg['sum']}\n"
        f"- **tool_trace rows**: min={rows_agg['min']} mean={rows_agg['mean']} max={rows_agg['max']}\n"
        f"- **distinct recap_write payloads (sha256_16)**: "
        f"{len(distinct_payload_hashes)} ({', '.join(distinct_payload_hashes) or '-'})\n"
        f"- **distinct tool_trace signatures**: {len(distinct_tool_signatures)}\n"
        f"- **write_corpus_file**: preview_rate={aggregate['write_corpus_file']['preview_rate']} "
        f"commit_rate={aggregate['write_corpus_file']['commit_rate']} "
        f"no_write_rate={aggregate['write_corpus_file']['no_write_rate']} "
        f"phase_shapes={aggregate['write_corpus_file']['distinct_phase_shapes'] or '-'}\n"
        f"- **commit_outcome** (BACKLOG §1.0): "
        f"attempted={aggregate['commit_outcome']['attempted_runs']}/{n} "
        f"succeeded={aggregate['commit_outcome']['succeeded_runs']} "
        f"refused={aggregate['commit_outcome']['refused_runs']} "
        f"unknown={aggregate['commit_outcome']['unknown_runs']} "
        f"success_rate_when_attempted={aggregate['commit_outcome']['success_rate_when_attempted']} "
        f"refusal_kinds={aggregate['commit_outcome']['refusal_kinds'] or '-'}\n"
        f"- **mechanical_fields**: "
        f"build_recap_write_payload_called_rate="
        f"{aggregate['mechanical_fields']['build_recap_write_payload_called_rate']} "
        f"match_rate_overall={aggregate['mechanical_fields']['match_rate_overall']} "
        f"match_rate_when_called={aggregate['mechanical_fields']['match_rate_when_called']} "
        f"match_rate_when_not_called={aggregate['mechanical_fields']['match_rate_when_not_called']} "
        f"applicable={aggregate['mechanical_fields']['applicable_runs']}/"
        f"{n} (n/a={aggregate['mechanical_fields']['not_applicable_runs']})\n\n"
        "## Per-run table\n\n"
        f"{table}\n"
        "## Aggregate JSON\n\n"
        "```json\n"
        f"{json.dumps(aggregate, indent=2, ensure_ascii=False, default=str)}\n"
        "```\n"
    )

    md_path.parent.mkdir(parents=True, exist_ok=True)
    md_path.write_text(md_body, encoding="utf-8")
    json_path.write_text(
        json.dumps(sidecar, indent=2, ensure_ascii=False, default=str), encoding="utf-8"
    )
    return md_path, json_path


def capture_and_write_recap_ingest_report(
    *,
    print_callable: Any,
    print_kwargs: dict[str, Any],
    run: PlannerStep1Run,
    corpus_dir: Path,
    model_id: str,
    scenario: dict[str, Any] | None = None,
    runs_root: Path | None = None,
    slice_dir: Path | None = None,
    utc: datetime | None = None,
    run_index: int | None = None,
    cohort_size: int | None = None,
    echo_to_stdout: bool = True,
    recap_context_snapshot: Any | None = None,
) -> tuple[RecapIngestReportPaths, RecapIngestRunSummary]:
    """Convenience: capture ``print_callable`` output, persist the report, optionally echo.

    The captured text is what gets embedded in the markdown body and what we re-print to
    the user's terminal (so on-disk and on-screen views are byte-identical).

    Pass ``recap_context_snapshot`` (the same ``RecapContext`` the runner snapshotted
    pre-turn) so the Scope-B extras compute mechanical-payload comparison against
    the frozen session view rather than re-resolving against the post-commit corpus.
    """
    review_text = _capture_review_markdown(print_callable, **print_kwargs)
    if echo_to_stdout:
        sys.stdout.write(review_text)
        sys.stdout.flush()
    return write_recap_ingest_run_report(
        run,
        corpus_dir=corpus_dir,
        model_id=model_id,
        review_text=review_text,
        scenario=scenario,
        runs_root=runs_root,
        slice_dir=slice_dir,
        utc=utc,
        run_index=run_index,
        cohort_size=cohort_size,
        recap_context_snapshot=recap_context_snapshot,
    )
