"""NPC voice planner benchmark — same gate shape as Lysandra Step 1, no Lysandra Step 2 merge.

Run: ``uv run python -m evals.npc_voice_vertical_slice.npc_voice_planner_trace --scenario <id>``,
``--list-scenarios``, ``--all``, or ``--all --runs N`` for repeated suite batches with a Markdown + JSON
suite report under ``artifacts/reports/`` (override with ``--suite-report PATH``).
"""

from __future__ import annotations

import argparse
import contextlib
import copy
import io
import json
import os
import sys
from dataclasses import replace
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

_REPO_ROOT = str(Path(__file__).resolve().parents[2])
if _REPO_ROOT not in sys.path:
    sys.path.insert(0, _REPO_ROOT)

from evals.lysandra_vertical_slice.step0_corpus_environment import resolve_corpus_dir  # noqa: E402
from evals.lysandra_vertical_slice.step1_planner_trace import (  # noqa: E402
    PlannerStep1Run,
    STEP2_BENCHMARK_VIOLATIONS_KEY,
    _empty_fail,
    configure_planner_review_logging,
    flatten_live_violations,
    format_clarification_evidence_lines,
    format_context_wiring_lines,
    resolve_review_mode,
)
from evals.planner_slice.live_eval import (  # noqa: E402
    evaluate_scenario_detail,
    resolve_planner_user_message,
)
from src.agent.planner import (  # noqa: E402
    build_corpus_path_ref_index,
    merge_planning_turn_details,
    run_planning_turn_detailed,
    _planner_tools_responses,
    make_tool_dispatcher,
)
from src.agent.planner_cache import load_or_build_planner_instructions  # noqa: E402
from src.agent.planner_telemetry import text_sig  # noqa: E402
from src.bootstrap_env import load_dungeonmindbuddy_dotenv  # noqa: E402
from src.npc_statblock_pipeline.canonical_intent import (  # noqa: E402
    evaluate_step2_post_planner_benchmark as evaluate_step2_post_planner_benchmark_pipeline,
)

_SLICE_DIR = Path(__file__).resolve().parent
_MANIFEST_PATH = _SLICE_DIR / "manifest.json"
_STEP2_NOOP_PATH = _SLICE_DIR / "gold" / "step2_noop.json"
_SCENARIO_ENV = "NPC_VOICE_PLANNER_SCENARIO"
_USER_MESSAGE_ENV = "NPC_VOICE_PLANNER_USER_MESSAGE"
_RUNS_ROOT_ENV = "NPC_VOICE_PLANNER_RUNS_ROOT"

def load_manifest() -> dict[str, Any]:
    data = json.loads(_MANIFEST_PATH.read_text(encoding="utf-8"))
    if not isinstance(data, dict):
        raise ValueError("manifest must be a JSON object")
    rows = data.get("scenarios")
    if not isinstance(rows, list) or not rows:
        raise ValueError("manifest.scenarios must be a non-empty list")
    return data


def list_scenario_ids() -> list[str]:
    m = load_manifest()
    out: list[str] = []
    for row in m["scenarios"]:
        if isinstance(row, dict) and row.get("id"):
            out.append(str(row["id"]))
    return out


def gold_path_for_scenario_id(scenario_id: str) -> Path:
    m = load_manifest()
    for row in m["scenarios"]:
        if not isinstance(row, dict):
            continue
        if str(row.get("id", "")).strip() == scenario_id:
            rel = str(row.get("gold_relpath", "")).strip()
            if not rel or ".." in Path(rel).parts:
                raise ValueError(f"invalid gold_relpath for scenario {scenario_id!r}")
            return (_SLICE_DIR / rel).resolve()
    raise KeyError(f"unknown scenario id: {scenario_id!r}")


def load_scenario_by_id(scenario_id: str) -> dict[str, Any]:
    p = gold_path_for_scenario_id(scenario_id)
    if not p.is_file():
        raise FileNotFoundError(f"gold file missing: {p}")
    return json.loads(p.read_text(encoding="utf-8"))


def load_step2_noop() -> dict[str, Any]:
    return json.loads(_STEP2_NOOP_PATH.read_text(encoding="utf-8"))


def default_scenario_id() -> str:
    raw = os.environ.get(_SCENARIO_ENV, "").strip()
    if raw:
        return raw
    ids = list_scenario_ids()
    return ids[0] if ids else ""


def run_npc_voice_planner_turn(
    *,
    corpus_dir: Path,
    client: Any,
    model_id: str,
    cache_root: Path | None = None,
    scenario: dict[str, Any] | None = None,
    scenario_id: str | None = None,
    user_line_override: str | None = None,
) -> PlannerStep1Run:
    load_dungeonmindbuddy_dotenv()
    sid_key = (scenario_id or "").strip() or default_scenario_id()
    if scenario is not None:
        sc = copy.deepcopy(scenario)
    else:
        sc = copy.deepcopy(load_scenario_by_id(sid_key))
    override = (user_line_override or os.environ.get(_USER_MESSAGE_ENV, "").strip() or None)
    if override:
        sc.setdefault("input", {})["user_message"] = override

    corpus_path = corpus_dir.resolve()
    scenario_stable_id = str(sc.get("id", "npc_voice_planner"))
    user_message, input_violations = resolve_planner_user_message(sc, corpus_path)
    if input_violations:
        return _empty_fail(scenario_stable_id, {"input": input_violations})
    if not user_message.strip():
        return _empty_fail(scenario_stable_id, {"input": [f"[{scenario_stable_id}] empty user message"]})

    instructions, fp = load_or_build_planner_instructions(corpus_path, cache_root=cache_root)
    tools = _planner_tools_responses()
    tool_cost_sink: list[dict[str, Any]] = []
    ref_index = build_corpus_path_ref_index(corpus_path)
    dispatch = make_tool_dispatcher(
        corpus_path,
        client,
        model_id,
        statblock_stub=None,
        tool_cost_sink=tool_cost_sink,
        corpus_path_ref_index=ref_index,
    )

    detail = run_planning_turn_detailed(
        client=client,
        model_id=model_id,
        instructions=instructions,
        tools=tools,
        corpus_path=corpus_path,
        user_line=user_message,
        previous_response_id=None,
        dispatch_tool=dispatch,
        telemetry_context={
            "scenario_id": scenario_stable_id,
            "suite": "npc_voice_vertical_slice_planner",
            "corpus_fingerprint": fp,
            "turn_index": 0,
        },
        corpus_path_ref_index=ref_index,
    )
    first_turn_final_text = (detail.final_text or "").strip()
    followup_user_line = ""
    follow_block = sc.get("followup_turn")
    if isinstance(follow_block, dict):
        follow_msg = str(follow_block.get("user_message", "")).strip()
        if follow_msg and detail.last_response_id:
            followup_user_line = follow_msg
            detail2 = run_planning_turn_detailed(
                client=client,
                model_id=model_id,
                instructions=instructions,
                tools=tools,
                corpus_path=corpus_path,
                user_line=follow_msg,
                previous_response_id=detail.last_response_id,
                dispatch_tool=dispatch,
                telemetry_context={
                    "scenario_id": scenario_stable_id,
                    "suite": "npc_voice_vertical_slice_planner",
                    "corpus_fingerprint": fp,
                    "phase": "followup_user",
                    "turn_index": 1,
                },
                corpus_path_ref_index=ref_index,
            )
            detail = merge_planning_turn_details(detail, detail2)
        else:
            first_turn_final_text = ""
    else:
        first_turn_final_text = ""

    statblock_usd = sum(float(x.get("total_usd", 0) or 0) for x in tool_cost_sink)
    tc = dict(detail.telemetry_cost or {})
    planner_usd = float(tc.get("planner_estimated_cost_usd", 0) or 0)
    tc["statblock_tool_estimated_cost_usd"] = round(statblock_usd, 6)
    tc["scenario_estimated_cost_usd"] = round(planner_usd + statblock_usd, 6)
    detail = replace(detail, telemetry_cost=tc)
    scenario_usd = tc["scenario_estimated_cost_usd"]
    result = evaluate_scenario_detail(
        sc,
        detail,
        estimated_cost_usd=scenario_usd,
        corpus_fingerprint=fp,
    )
    planner_key = str(sc.get("fixture_role") or "").strip().lower() or sid_key
    noop = load_step2_noop()
    b_detail, b_ok, b_v = evaluate_step2_post_planner_benchmark_pipeline(
        user_message=user_message,
        tool_trace=detail.tool_trace,
        planner_scenario_key=planner_key,
        corpus_policy={},
        step2_gold=noop,
        intent_client=client,
    )
    post_planner_step2_benchmark_detail = b_detail if b_detail is not None else None
    if b_v:
        merged = dict(result.violations)
        merged.setdefault(STEP2_BENCHMARK_VIOLATIONS_KEY, []).extend(b_v)
        result = replace(result, passed=result.passed and b_ok, violations=merged)

    return PlannerStep1Run(
        detail=detail,
        result=result,
        instructions=instructions,
        user_line=user_message,
        corpus_fingerprint=fp,
        post_planner_step2_benchmark_detail=post_planner_step2_benchmark_detail,
        scenario_key=sid_key,
        followup_user_line=followup_user_line,
        first_turn_final_text=first_turn_final_text,
    )


def print_npc_voice_planner_review(
    run: PlannerStep1Run,
    *,
    corpus_dir: Path,
    model_id: str,
    review_mode: str = "summary",
) -> str:
    """Emit a compact review (stdout) and return the same text for artifacts."""
    buf = io.StringIO()
    d = run.detail
    sep = "=" * 72
    with contextlib.redirect_stdout(buf):
        print(sep)
        print("NPC VOICE PLANNER — REVIEW")
        print(sep)
        print(f"scenario_id:      {run.result.scenario_id}")
        print(f"scenario_key:     {run.scenario_key}")
        print(f"model_id:         {model_id}")
        print(f"gates_passed:     {run.result.passed}")
        print(f"review_mode:      {review_mode}")
        print(f"corpus_fprint:    {run.corpus_fingerprint}")
        print(f"corpus_dir:       {corpus_dir.resolve()}")
        print(f"hit_tool_limit:   {d.hit_tool_round_limit}")
        print(f"tool_trace rows:  {len(d.tool_trace)}")
        print()
        print(sep)
        print("§ Prompt payload sizes (characters)")
        print(sep)
        print(f"instructions:  {text_sig(run.instructions)}")
        print(f"user_line:     {text_sig(run.user_line)}")
        if run.followup_user_line:
            print(f"followup_user_line: {text_sig(run.followup_user_line)}")
        print()
        print(sep)
        print("§ Token usage (per responses.create completion)")
        print(sep)
        for i, row in enumerate(d.usage_rounds):
            u = row.get("usage") or {}
            print(
                f"  round[{i}] input_tokens={u.get('input_tokens')} "
                f"output_tokens={u.get('output_tokens')} "
                f"cached_tokens={u.get('cached_tokens')}"
            )
        tc = d.telemetry_cost or {}
        print(f"  planner_estimated_cost_usd: {tc.get('planner_estimated_cost_usd')}")
        print(f"  scenario_estimated_cost_usd: {tc.get('scenario_estimated_cost_usd')}")
        print()
        print(sep)
        print("§ Statblock / working-context evidence (tool wire)")
        print(sep)
        for ln in format_context_wiring_lines(d.tool_trace):
            print(ln)
        print(sep)
        print("§ Clarification (turn 0 prose / JSON heuristics)")
        print(sep)
        for ln in format_clarification_evidence_lines(
            d.tool_trace,
            followup_user_line=run.followup_user_line,
            first_turn_final_text=run.first_turn_final_text,
        ):
            print(ln)
        pre_align = getattr(d, "pre_alignment_final_text", None)
        if pre_align is not None:
            align_report = getattr(d, "clarification_alignment", None)
            align_mode = getattr(align_report, "mode", "unknown") if align_report else "unknown"
            print(sep)
            print(
                "§ Final LLM answer (pre-alignment) — legacy capture "
                f"(alignment_mode={align_mode})"
            )
            print(sep)
            print(pre_align or "(empty)")
            print(sep)
        print(sep)
        print("§ Final LLM answer")
        print(sep)
        print(d.final_text or "(empty)")
        print(sep)
        if not run.result.passed:
            print("GATE VIOLATIONS:")
            for line in flatten_live_violations(run.result.violations):
                print(line)
    text = buf.getvalue()
    sys.stdout.write(text)
    return text


def _sanitize_filename_segment(raw: str, *, max_len: int) -> str:
    parts: list[str] = []
    for ch in (raw or "").strip():
        if ch.isalnum() or ch in "._-":
            parts.append(ch)
        elif ch.isspace():
            parts.append("-")
        else:
            parts.append("-")
    s = "".join(parts).lower()
    while "--" in s:
        s = s.replace("--", "-")
    s = s.strip("-") or "unknown"
    return s[:max_len]


def write_npc_voice_run_artifacts(
    markdown_body: str,
    *,
    run: PlannerStep1Run,
    model_id: str,
    utc: datetime | None = None,
    suite_run_index: int | None = None,
) -> tuple[Path, Path]:
    root = _SLICE_DIR
    when = utc or datetime.now(timezone.utc)
    scen = _sanitize_filename_segment(run.scenario_key or "unknown", max_len=48)
    mod = _sanitize_filename_segment(model_id, max_len=48)
    gate_ok = bool(run.result.passed)
    followup = bool((run.followup_user_line or "").strip())
    gate = "PASS" if gate_ok else "FAIL"
    turns = "2turn" if followup else "1turn"
    day = when.strftime("%Y-%m-%d")
    compact = when.strftime("%Y%m%dT%H%M%S") + "Z"
    run_seg = f"run{int(suite_run_index):03d}--" if suite_run_index is not None else ""
    fname = f"npc_voice--{scen}--{mod}--{gate}--{turns}--{run_seg}{compact}.md"
    env_runs = os.environ.get(_RUNS_ROOT_ENV, "").strip()
    base_runs = Path(env_runs).expanduser().resolve() if env_runs else (root / "artifacts" / "runs")
    primary = base_runs / day / fname
    legacy = root / "artifacts" / "last_npc_voice_planner_run.md"
    stamp_line = when.strftime("%Y-%m-%dT%H:%M:%SZ")
    header = (
        f"<!-- benchmark_artifact: npc_voice_planner | iso_utc: {stamp_line} "
        f"| scenario: {scen} | model: {model_id} | gates: {gate} "
        f"| turns: {'2' if followup else '1'} | primary: {primary.name} -->\n\n"
    )
    body = header + markdown_body
    primary.parent.mkdir(parents=True, exist_ok=True)
    primary.write_text(body, encoding="utf-8")
    legacy.parent.mkdir(parents=True, exist_ok=True)
    legacy.write_text(body, encoding="utf-8")
    return primary, legacy


def _default_suite_report_paths(*, utc: datetime | None = None) -> tuple[Path, Path]:
    when = utc or datetime.now(timezone.utc)
    compact = when.strftime("%Y%m%dT%H%M%S") + "Z"
    base = _SLICE_DIR / "artifacts" / "reports"
    stem = base / f"npc_voice_suite--{compact}"
    return stem.with_suffix(".md"), stem.with_suffix(".json")


def _resolve_suite_report_md_path(arg: str) -> Path:
    raw = (arg or "").strip()
    if not raw:
        md, _ = _default_suite_report_paths()
        return md
    p = Path(raw).expanduser()
    return p if p.suffix.lower() == ".md" else p.with_suffix(".md")


def write_npc_voice_suite_report(
    *,
    rows: list[dict[str, Any]],
    out_md: Path,
    model_id: str,
    corpus_fingerprint: str | None,
    corpus_dir: Path,
    runs_n: int,
    mode: str,
    scenario_filter: str | None,
) -> tuple[Path, Path]:
    """
    Write aggregate Markdown + JSON for multi-run (or explicit) suite batches.

    Each ``rows`` entry should include: ``suite_run_index`` (1-based int), ``scenario_id`` (str),
    ``passed`` (bool), ``violations`` (dict), ``scenario_estimated_cost_usd`` (float|None),
    ``artifact_primary`` (str path or None).
    """
    out_md = out_md.resolve()
    out_md.parent.mkdir(parents=True, exist_ok=True)
    out_json = out_md.with_suffix(".json")

    by_scenario: dict[str, list[dict[str, Any]]] = {}
    for r in rows:
        sid = str(r.get("scenario_id", "") or "unknown")
        by_scenario.setdefault(sid, []).append(r)

    manifest_order = list_scenario_ids()
    order_map = {sid: i for i, sid in enumerate(manifest_order)}
    scenario_ids = sorted(by_scenario.keys(), key=lambda s: (order_map.get(s, 999), s))

    lines: list[str] = [
        "# NPC voice planner — suite report",
        "",
        f"- **Generated (UTC):** {datetime.now(timezone.utc).strftime('%Y-%m-%dT%H:%M:%SZ')}",
        f"- **Model:** `{model_id}`",
        f"- **Corpus directory:** `{corpus_dir.resolve()}`",
        f"- **Corpus fingerprint:** `{corpus_fingerprint or ''}`",
        f"- **Mode:** `{mode}`" + (f" (`{scenario_filter}`)" if scenario_filter else ""),
        f"- **Declared runs per scenario block:** {runs_n}",
        f"- **Total cells:** {len(rows)}",
        "",
        "## Per-scenario summary",
        "",
        "| Scenario | Passes | Fails | Pass rate | Failed run # |",
        "|----------|--------|-------|-------------|--------------|",
    ]

    any_fail = False
    total_cost = 0.0
    for sid in scenario_ids:
        cells = by_scenario[sid]
        passes = sum(1 for c in cells if c.get("passed"))
        fails = len(cells) - passes
        rate = f"{passes}/{len(cells)}" if cells else "0/0"
        failed_runs = [int(c["suite_run_index"]) for c in cells if not c.get("passed")]
        any_fail = any_fail or bool(failed_runs)
        fr = ",".join(str(x) for x in sorted(failed_runs)) if failed_runs else "—"
        lines.append(f"| `{sid}` | {passes} | {fails} | {rate} | {fr} |")
        for c in cells:
            v = c.get("scenario_estimated_cost_usd")
            if isinstance(v, (int, float)):
                total_cost += float(v)

    lines.extend(
        [
            "",
            f"- **Σ scenario_estimated_cost_usd (cells):** {round(total_cost, 6)}",
            "",
            "## Run index × scenario",
            "",
            "| Run | Scenario | Pass | Cost (USD) | Artifact |",
            "|-----|----------|------|------------|----------|",
        ]
    )
    for r in sorted(rows, key=lambda x: (int(x.get("suite_run_index", 0)), str(x.get("scenario_id", "")))):
        ri = int(r.get("suite_run_index", 0) or 0)
        sid = str(r.get("scenario_id", ""))
        ok = "yes" if r.get("passed") else "no"
        cost = r.get("scenario_estimated_cost_usd")
        cost_s = f"{float(cost):.6f}" if isinstance(cost, (int, float)) else "—"
        art = str(r.get("artifact_primary") or "—")
        if len(art) > 72:
            art = art[:35] + "…" + art[-34:]
        lines.append(f"| {ri} | `{sid}` | {ok} | {cost_s} | `{art}` |")

    lines.extend(["", "## Violations (failed cells only)", ""])
    fail_rows = [r for r in rows if not r.get("passed")]
    if not fail_rows:
        lines.append("_None._")
    else:
        for r in sorted(fail_rows, key=lambda x: (int(x.get("suite_run_index", 0)), str(x.get("scenario_id", "")))):
            lines.append(
                f"### Run {int(r.get('suite_run_index', 0))} — `{r.get('scenario_id')}`\n\n"
                f"```\n{r.get('violations')!r}\n```\n"
            )

    out_md.write_text("\n".join(lines) + "\n", encoding="utf-8")
    payload = {
        "schema": "npc_voice_suite_report_v1",
        "model_id": model_id,
        "corpus_fingerprint": corpus_fingerprint,
        "corpus_dir": str(corpus_dir.resolve()),
        "runs_n": runs_n,
        "mode": mode,
        "scenario_filter": scenario_filter,
        "rows": rows,
        "summary": {
            "total_cells": len(rows),
            "failed_cells": len(fail_rows),
            "scenario_estimated_cost_usd_sum": round(total_cost, 6),
        },
    }
    out_json.write_text(json.dumps(payload, indent=2, default=str), encoding="utf-8")
    return out_md, out_json


def _parse_args(argv: list[str] | None) -> argparse.Namespace:
    p = argparse.ArgumentParser(description="NPC voice planner live benchmark")
    p.add_argument("--scenario", type=str, default="", help="Scenario id from manifest.json")
    p.add_argument("--list-scenarios", action="store_true", help="Print scenario ids and exit")
    p.add_argument("--all", action="store_true", help="Run every scenario in manifest order")
    p.add_argument(
        "--runs",
        type=int,
        default=1,
        metavar="N",
        help="Repeat the selected scope N times (default 1). When N>1, writes a suite report under "
        "artifacts/reports/ unless --suite-report is set.",
    )
    p.add_argument(
        "--suite-report",
        type=str,
        default="",
        help="Base path for aggregate suite report (.md + .json). May omit extension; .md is added. "
        "When set with --runs 1, still writes this summary.",
    )
    p.add_argument(
        "--verbose",
        action="store_true",
        help="With --runs>1, print full per-run reviews to stdout (default: capture only; one line per cell on stderr).",
    )
    return p.parse_args(argv)


def _execute_one_npc_voice_cell(
    *,
    corpus_dir: Path,
    client: Any,
    model_id: str,
    scenario_id: str,
    review_mode: str,
    suite_run_index: int,
    runs_n: int,
    verbose: bool,
) -> tuple[PlannerStep1Run, str, Path, Path]:
    """Run one benchmark cell; return run, review markdown, primary + legacy artifact paths."""
    run = run_npc_voice_planner_turn(
        corpus_dir=corpus_dir,
        client=client,
        model_id=model_id,
        scenario_id=scenario_id,
    )
    if verbose or runs_n <= 1:
        review = print_npc_voice_planner_review(
            run, corpus_dir=corpus_dir, model_id=model_id, review_mode=review_mode
        )
    else:
        with contextlib.redirect_stdout(io.StringIO()):
            review = print_npc_voice_planner_review(
                run, corpus_dir=corpus_dir, model_id=model_id, review_mode=review_mode
            )
        gate = "PASS" if run.result.passed else "FAIL"
        usd = (run.detail.telemetry_cost or {}).get("scenario_estimated_cost_usd")
        print(
            f"[{gate}] {scenario_id} run {suite_run_index}/{runs_n} scenario_estimated_cost_usd={usd}",
            file=sys.stderr,
        )
    idx = suite_run_index if runs_n > 1 else None
    primary, legacy = write_npc_voice_run_artifacts(
        review, run=run, model_id=model_id, suite_run_index=idx
    )
    return run, review, primary, legacy


def main(argv: list[str] | None = None) -> int:
    from openai import OpenAI  # noqa: E402

    from src.agent.planner import _resolve_planner_model  # noqa: E402
    from src.agent.planner_turn_output_schema import planner_turn_output_schema_enabled  # noqa: E402
    from src.agent.synthesis import _load_api_key  # noqa: E402

    args = _parse_args(argv)
    runs_n = int(args.runs)
    if runs_n < 1:
        print("--runs must be >= 1", file=sys.stderr)
        return 2

    load_dungeonmindbuddy_dotenv()

    if args.list_scenarios:
        for sid in list_scenario_ids():
            print(sid)
        return 0

    configure_planner_review_logging()
    if not (_load_api_key() or "").strip():
        print(
            "OPENAI_API_KEY missing after loading .env / .env.development.",
            file=sys.stderr,
        )
        return 2

    root = resolve_corpus_dir()
    if not root.is_dir():
        print(f"corpus missing: {root}", file=sys.stderr)
        return 2

    client = OpenAI()
    model_id = _resolve_planner_model(None)
    review_mode = resolve_review_mode()
    print(
        f"[logging] PLANNER_REVIEW_MODE={review_mode}; "
        f"PLANNER_TURN_OUTPUT_SCHEMA={'on' if planner_turn_output_schema_enabled() else 'off'}\n",
        file=sys.stderr,
    )

    want_suite_report = runs_n > 1 or bool((args.suite_report or "").strip())
    rows: list[dict[str, Any]] = []
    corpus_fp: str | None = None
    any_cell_failed = False

    def record_row(run: PlannerStep1Run, *, suite_run_index: int, primary: Path) -> None:
        nonlocal corpus_fp, any_cell_failed
        corpus_fp = run.corpus_fingerprint
        if not run.result.passed:
            any_cell_failed = True
        tc = run.detail.telemetry_cost or {}
        rows.append(
            {
                "suite_run_index": suite_run_index,
                "scenario_id": run.scenario_key,
                "passed": bool(run.result.passed),
                "violations": run.result.violations,
                "scenario_estimated_cost_usd": tc.get("scenario_estimated_cost_usd"),
                "artifact_primary": str(primary),
                "info": dict(getattr(run.result, "info", {}) or {}),
            }
        )

    if args.all:
        for run_i in range(1, runs_n + 1):
            print(
                f"\n{'=' * 72}\n# SUITE RUN {run_i}/{runs_n}\n{'=' * 72}\n",
                file=sys.stderr,
            )
            for sid in list_scenario_ids():
                print(f"\n{'#' * 72}\n# SCENARIO: {sid} (run {run_i}/{runs_n})\n{'#' * 72}\n", file=sys.stderr)
                run, _, primary, _ = _execute_one_npc_voice_cell(
                    corpus_dir=root,
                    client=client,
                    model_id=model_id,
                    scenario_id=sid,
                    review_mode=review_mode,
                    suite_run_index=run_i,
                    runs_n=runs_n,
                    verbose=bool(args.verbose),
                )
                record_row(run, suite_run_index=run_i, primary=primary)
                if runs_n <= 1:
                    if not run.result.passed:
                        print(f"[FAIL] {sid}: {run.result.violations}", file=sys.stderr)
                    else:
                        print(f"[PASS] {sid}", file=sys.stderr)
        if want_suite_report:
            out_md = _resolve_suite_report_md_path(args.suite_report)
            md_path, json_path = write_npc_voice_suite_report(
                rows=rows,
                out_md=out_md,
                model_id=model_id,
                corpus_fingerprint=corpus_fp,
                corpus_dir=root,
                runs_n=runs_n,
                mode="all",
                scenario_filter=None,
            )
            print(f"[wrote suite report] {md_path}", file=sys.stderr)
            print(f"[wrote suite report] {json_path}", file=sys.stderr)
        if runs_n > 1:
            n_fail = sum(1 for r in rows if not r["passed"])
            print(
                f"\n[summary] suite_runs={runs_n} cells={len(rows)} failed_cells={n_fail}",
                file=sys.stderr,
            )
        if runs_n <= 1 and any_cell_failed:
            failed = sorted({r["scenario_id"] for r in rows if not r["passed"]})
            print(f"\nSuite failed for: {failed}", file=sys.stderr)
        elif runs_n <= 1:
            print("\nAll scenarios passed.", file=sys.stderr)
        return 1 if any_cell_failed else 0

    scenario_id = (args.scenario or "").strip() or default_scenario_id()
    if not scenario_id:
        print("No scenario id (use --scenario or set NPC_VOICE_PLANNER_SCENARIO).", file=sys.stderr)
        return 2

    for run_i in range(1, runs_n + 1):
        if runs_n > 1:
            print(f"[scenario] {scenario_id!r} run {run_i}/{runs_n}\n", file=sys.stderr)
        else:
            print(f"[scenario] {scenario_id!r}\n", file=sys.stderr)
        run, _, primary, legacy = _execute_one_npc_voice_cell(
            corpus_dir=root,
            client=client,
            model_id=model_id,
            scenario_id=scenario_id,
            review_mode=review_mode,
            suite_run_index=run_i,
            runs_n=runs_n,
            verbose=bool(args.verbose),
        )
        record_row(run, suite_run_index=run_i, primary=primary)
        if runs_n <= 1:
            print(f"[wrote benchmark report to {primary}]", file=sys.stderr)
            print(f"[mirrored latest run to {legacy}]", file=sys.stderr)

    if want_suite_report:
        out_md = _resolve_suite_report_md_path(args.suite_report)
        md_path, json_path = write_npc_voice_suite_report(
            rows=rows,
            out_md=out_md,
            model_id=model_id,
            corpus_fingerprint=corpus_fp,
            corpus_dir=root,
            runs_n=runs_n,
            mode="scenario",
            scenario_filter=scenario_id,
        )
        print(f"[wrote suite report] {md_path}", file=sys.stderr)
        print(f"[wrote suite report] {json_path}", file=sys.stderr)

    if runs_n > 1 and not args.all:
        n_fail = sum(1 for r in rows if not r["passed"])
        print(
            f"\n[summary] scenario={scenario_id!r} suite_runs={runs_n} cells={len(rows)} "
            f"failed_cells={n_fail}",
            file=sys.stderr,
        )

    return 0 if not any_cell_failed else 1


if __name__ == "__main__":
    raise SystemExit(main())
