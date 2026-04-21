"""Stage-2 vertical slice: planner reads committed Session 20 recap and appends Lysandra timeline row.

Run (from repo root)::

    export DUNGEONMIND_PLANNER_ALLOW_WRITES=1
    uv run python -m evals.session_recap_timeline_append_vertical_slice.step1_timeline_append_run

Cohort::

    PLANNER_REVIEW_MODE=summary uv run python -m \\
      evals.session_recap_timeline_append_vertical_slice.step1_timeline_append_run --n 3 --model gpt-5.4-mini

Pre-state only::

    uv run python -m evals.session_recap_timeline_append_vertical_slice.step1_timeline_append_run --print-root
"""

from __future__ import annotations

import argparse
import json
import os
import sys
import time
from dataclasses import replace
from pathlib import Path
from typing import Any

_REPO_ROOT = str(Path(__file__).resolve().parents[2])
if _REPO_ROOT not in sys.path:
    sys.path.insert(0, _REPO_ROOT)

from evals.lysandra_vertical_slice.step1_planner_trace import (  # noqa: E402
    PlannerStep1Run,
    _empty_fail,
    configure_planner_review_logging,
    resolve_review_mode,
)
from evals.lysandra_vertical_slice.step0_corpus_environment import resolve_corpus_dir  # noqa: E402
from evals.planner_slice.live_eval import (  # noqa: E402
    evaluate_scenario_detail,
    fixture_scenario_id,
    resolve_planner_user_message,
)
from evals.session_recap_timeline_append_vertical_slice.grader import (  # noqa: E402
    collect_timeline_append_violations,
)
from evals.session_recap_timeline_append_vertical_slice.step0_pre_state import (  # noqa: E402
    build_pre_state_corpus,
)
from evals.session_recap_timeline_append_vertical_slice.timeline_append_run_report import (  # noqa: E402
    TimelineAppendRunSummary,
    capture_and_write_timeline_append_report,
    write_timeline_append_multi_summary,
)
from src.agent.planner import (  # noqa: E402
    _planner_tools_responses,
    _resolve_planner_model,
    build_corpus_path_ref_index,
    make_tool_dispatcher,
    run_planning_turn_detailed,
)
from src.agent.planner_cache import load_or_build_planner_instructions  # noqa: E402
from src.agent.synthesis import _load_api_key  # noqa: E402
from src.bootstrap_env import load_dungeonmindbuddy_dotenv  # noqa: E402

_SLICE_DIR = Path(__file__).resolve().parent
_GOLD_SCENARIO = _SLICE_DIR / "gold" / "timeline_append_lysandra_session20.json"
_ALLOW_WRITES_ENV = "DUNGEONMIND_PLANNER_ALLOW_WRITES"

# Appended after cached planner instructions so we do not fork ``corpus_session_planner.py``.
_TIMELINE_APPEND_INSTRUCTION_SUFFIX = """

**Benchmark turn — recap already on disk (Stage 2):** The Session recap file named in the user message **already exists** and is the source of truth. Do **not** call `get_recap_context`, `assemble_recap_draft`, or `build_recap_write_payload`. Do **not** use `write_corpus_file` for the recap or for timeline tables. For NPC timeline updates use **only** `append_timeline_row`: **preview then commit in the same turn** (`dry_run=true` first, then `dry_run=false` with the same row arguments and the preview `confirm_token`). The benchmark operator pre-approved the commit — **a preview-only stop is a failure**. Open the recap and the NPC `timeline.md` with `read_corpus_file` or `load_context_markdown` so you match the existing markdown table format (three columns: session, beat, backticked recap filename like prior rows). Reply with the universal planner JSON schema (`user_intent`, `message`, `unsure_queue` only — no `recap_write` field).
"""


def load_scenario(path: Path | None = None) -> dict[str, Any]:
    p = (path or _GOLD_SCENARIO).expanduser().resolve()
    if not p.is_file():
        raise FileNotFoundError(f"missing scenario: {p}")
    return json.loads(p.read_text(encoding="utf-8"))


def run_timeline_append_turn(
    *,
    corpus_dir: Path,
    client: Any,
    model_id: str,
    cache_root: Path | None = None,
    scenario: dict[str, Any] | None = None,
    allow_corpus_writes: bool = True,
) -> PlannerStep1Run:
    sc = scenario or load_scenario()
    sid = fixture_scenario_id(sc)
    corpus_path = corpus_dir.resolve()

    user_message, input_violations = resolve_planner_user_message(sc, corpus_path)

    if input_violations:
        return _empty_fail(sid, {"input": input_violations}, user_line=user_message)
    if not user_message.strip():
        return _empty_fail(sid, {"input": [f"[{sid}] empty user message"]}, user_line="")

    instructions, fp = load_or_build_planner_instructions(
        corpus_path,
        cache_root=cache_root,
        include_write_tools=allow_corpus_writes,
    )
    instructions = f"{instructions.rstrip()}{_TIMELINE_APPEND_INSTRUCTION_SUFFIX}"

    tools = _planner_tools_responses(include_write_tools=allow_corpus_writes)
    tool_cost_sink: list[dict[str, Any]] = []
    ref_index = build_corpus_path_ref_index(corpus_path)
    dispatch = make_tool_dispatcher(
        corpus_path,
        client,
        model_id,
        statblock_stub=None,
        tool_cost_sink=tool_cost_sink,
        corpus_path_ref_index=ref_index,
        allow_corpus_writes=allow_corpus_writes,
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
            "scenario_id": sid,
            "suite": "session_recap_timeline_append_vertical_slice",
            "corpus_fingerprint": fp,
            "turn_index": 0,
        },
        corpus_path_ref_index=ref_index,
        active_skill_id=None,
    )

    statblock_usd = sum(float(x.get("total_usd", 0) or 0) for x in tool_cost_sink)
    tc = dict(detail.telemetry_cost or {})
    planner_usd = float(tc.get("planner_estimated_cost_usd", 0) or 0)
    tc["statblock_tool_estimated_cost_usd"] = round(statblock_usd, 6)
    tc["scenario_estimated_cost_usd"] = round(planner_usd + statblock_usd, 6)
    detail = replace(detail, telemetry_cost=tc)
    scenario_usd = tc["scenario_estimated_cost_usd"]

    base_result = evaluate_scenario_detail(
        sc,
        detail,
        estimated_cost_usd=scenario_usd,
        corpus_fingerprint=fp,
    )
    grading = sc.get("grading") or {}
    gviol = collect_timeline_append_violations(
        corpus_dir=corpus_path,
        tool_trace=list(detail.tool_trace or []),
        grading=grading if isinstance(grading, dict) else {},
    )
    merged_violations = dict(base_result.violations)
    for key, rows in gviol.items():
        merged_violations.setdefault(key, []).extend(rows)
    passed = base_result.passed and not gviol
    final_result = replace(
        base_result,
        passed=passed,
        violations=merged_violations,
    )

    return PlannerStep1Run(
        detail=detail,
        result=final_result,
        instructions=instructions,
        user_line=user_message,
        corpus_fingerprint=fp,
        post_planner_step2_benchmark_detail=None,
        scenario_key=sid,
        followup_user_line="",
        first_turn_final_text="",
    )


def _tool_trace_signature(tool_trace: list[dict[str, Any]]) -> str:
    return ",".join(str(row.get("tool", "") or "") for row in tool_trace)


def print_timeline_append_review(
    run: PlannerStep1Run,
    *,
    corpus_dir: Path,
    model_id: str,
    review_mode: str = "summary",
) -> None:
    _ = corpus_dir, model_id, review_mode
    print(f"scenario_id={run.result.scenario_id} gates_passed={run.result.passed}")
    viol = run.result.violations or {}
    if viol:
        print("violations:")
        for bucket, rows in viol.items():
            for line in rows:
                print(f"  [{bucket}] {line}")
    print(f"tool_trace_sig: {_tool_trace_signature(list(run.detail.tool_trace or []))}")
    ft = (run.detail.final_text or "").strip()
    if ft:
        preview = ft[:1200] + ("…" if len(ft) > 1200 else "")
        print("final_text_preview:")
        print(preview)


def main() -> None:
    parser = argparse.ArgumentParser(description="Stage-2 timeline-append benchmark")
    parser.add_argument("--print-root", action="store_true", help="Build pre-state corpus and print root path")
    parser.add_argument("--tmp-parent", type=Path, default=None)
    parser.add_argument("--live-corpus", action="store_true", help="Use live repo corpus (debug only)")
    parser.add_argument("--scenario-json", type=Path, default=None)
    parser.add_argument("--model", type=str, default="")
    parser.add_argument("--n", type=int, default=1)
    parser.add_argument("--runs-root", type=Path, default=None)
    parser.add_argument("--no-writes", action="store_true")
    parser.add_argument("-q", "--quiet", action="store_true")
    args = parser.parse_args()

    if args.print_root:
        if args.tmp_parent is not None:
            args.tmp_parent.mkdir(parents=True, exist_ok=True)
            root = build_pre_state_corpus(tmp_dir=args.tmp_parent)
        else:
            root = build_pre_state_corpus()
        print(root)
        return

    load_dungeonmindbuddy_dotenv()
    if not (_load_api_key() or "").strip():
        print(
            "OPENAI_API_KEY missing after loading .env / .env.development.",
            file=sys.stderr,
        )
        sys.exit(2)

    os.environ.setdefault(_ALLOW_WRITES_ENV, "1")
    allow_writes = not args.no_writes and os.environ.get(_ALLOW_WRITES_ENV, "").strip().lower() in (
        "1",
        "true",
        "yes",
        "on",
    )

    gold = load_scenario(args.scenario_json)
    n = max(1, int(args.n))

    def _build_corpus(i: int) -> Path:
        if args.live_corpus:
            return resolve_corpus_dir()
        if args.tmp_parent is not None:
            run_parent = args.tmp_parent / f"run_{i + 1:03d}"
            run_parent.mkdir(parents=True, exist_ok=True)
            return build_pre_state_corpus(tmp_dir=run_parent)
        return build_pre_state_corpus()

    configure_planner_review_logging()
    review_mode = resolve_review_mode()
    if not args.quiet:
        print(
            f"[timeline-append] n={n} allow_writes={allow_writes} "
            f"PLANNER_REVIEW_MODE={review_mode}",
            file=sys.stderr,
        )

    from openai import OpenAI  # noqa: E402

    client = OpenAI()
    model_id = _resolve_planner_model(args.model.strip() or None)

    summaries: list[TimelineAppendRunSummary] = []
    total_cost = 0.0
    pass_count = 0
    scenario_id_for_summary = fixture_scenario_id(gold)

    for i in range(n):
        corpus_root = _build_corpus(i)
        if not args.quiet:
            print(f"[timeline-append] run {i + 1}/{n} corpus_dir={corpus_root}", file=sys.stderr)
        t0 = time.monotonic()
        run = run_timeline_append_turn(
            corpus_dir=corpus_root,
            client=client,
            model_id=model_id,
            scenario=gold,
            allow_corpus_writes=allow_writes,
        )
        elapsed_s = round(time.monotonic() - t0, 2)
        cost = float((run.detail.telemetry_cost or {}).get("scenario_estimated_cost_usd", 0) or 0)
        total_cost += cost
        if run.result.passed:
            pass_count += 1

        if not args.quiet:
            print(
                f"[timeline-append] run {i + 1} done in {elapsed_s}s cost_usd={cost:.4f} "
                f"passed={run.result.passed}",
                file=sys.stderr,
            )

        paths, summary = capture_and_write_timeline_append_report(
            print_callable=print_timeline_append_review,
            print_kwargs={
                "run": run,
                "corpus_dir": corpus_root,
                "model_id": model_id,
                "review_mode": review_mode,
            },
            run=run,
            corpus_dir=corpus_root,
            model_id=model_id,
            scenario=gold,
            runs_root=args.runs_root,
            run_index=i if n > 1 else None,
            cohort_size=n if n > 1 else None,
        )
        summaries.append(summary)
        if not args.quiet:
            print(f"[timeline-append] report: {paths.primary_md}", file=sys.stderr)
            print(f"[timeline-append] sidecar: {paths.sidecar_json}", file=sys.stderr)

        if total_cost > 1.5 and pass_count <= 1 and i + 1 < n:
            print(
                f"[timeline-append] STOP: cumulative cost ${total_cost:.2f} with only {pass_count} pass(es); "
                "skipping remaining cohort runs per budget guard.",
                file=sys.stderr,
            )
            break

    if total_cost > 2.0:
        print(
            f"[timeline-append] WARNING: cumulative cost ${total_cost:.2f} exceeded $2.00 cap.",
            file=sys.stderr,
        )

    if n > 1 and summaries:
        md_s, json_s = write_timeline_append_multi_summary(
            summaries,
            model_id=model_id,
            scenario_id=scenario_id_for_summary,
            runs_root=args.runs_root,
        )
        if not args.quiet:
            print(f"[timeline-append] cohort summary: {md_s}", file=sys.stderr)
            print(f"[timeline-append] cohort sidecar: {json_s}", file=sys.stderr)

    if summaries and not all(s.gates_passed for s in summaries):
        sys.exit(1)


if __name__ == "__main__":
    main()
