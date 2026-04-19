"""Scope-B step 1: run the corpus planner with writes on against a pre-state corpus.

Builds a tmp corpus via :func:`build_pre_state_corpus`, loads Session 20 raw notes from the
slice fixture, prepends the **recap-write** skill body (minus YAML frontmatter),
and runs one :func:`run_planning_turn_detailed` pass with write tools registered.

Run (from repo root)::

    export DUNGEONMIND_PLANNER_ALLOW_WRITES=1   # optional; this module setdefaults to 1
    # OPENAI_API_KEY: repo .env / .env.development via load_dungeonmindbuddy_dotenv (see lysandra step1)
    uv run python -m evals.session_recap_ingest_vertical_slice.step1_recap_ingest_run

Other flags::

    uv run python -m evals.session_recap_ingest_vertical_slice.step1_recap_ingest_run --print-root
    uv run python -m evals.session_recap_ingest_vertical_slice.step1_recap_ingest_run --live-corpus

Cohort + stderr progress (review text still on stdout; verbosity defaults to ``-vv``,
which dumps each run's full tool_trace + violations + write-phase summary on stderr;
use ``-q`` / ``--quiet`` to suppress, or ``-v`` for the lighter one-line-per-run shape)::

    PLANNER_REVIEW_MODE=summary uv run python -m evals.session_recap_ingest_vertical_slice.step1_recap_ingest_run --n 5

Live in terminal + tee'd to a single combined log (recommended)::

    PYTHONUNBUFFERED=1 PLANNER_REVIEW_MODE=summary uv run python -m \\
      evals.session_recap_ingest_vertical_slice.step1_recap_ingest_run --n 5 2>&1 \\
      | tee /tmp/recap_5x.log

Parallel cohort (workers race on the OpenAI API; ~5x speedup at ``--n 5 --parallel 5``)::

    PYTHONUNBUFFERED=1 PLANNER_REVIEW_MODE=summary uv run python -m \\
      evals.session_recap_ingest_vertical_slice.step1_recap_ingest_run \\
      --n 5 --parallel 5 2>&1 | tee /tmp/recap_5x.log

Detach (child runs in background; **no benchmark output on your tty** unless you follow the log)::

    uv run python -m evals.session_recap_ingest_vertical_slice.step1_recap_ingest_run \\
      --detach --n 5 --detach-log /tmp/recap_5x.log
    tail -f /tmp/recap_5x.log

Same thing, but stream the log to **stdout** in this terminal (like ``tail -f``; Ctrl+C stops only the viewer)::

    uv run python -m evals.session_recap_ingest_vertical_slice.step1_recap_ingest_run \\
      --detach --detach-follow --n 5 --detach-log /tmp/recap_5x.log

Synchronous runs (no ``--detach``) still print the review to **stdout** and progress to **stderr** as before.
"""

from __future__ import annotations

import argparse
import copy
import json
import os
import subprocess
import sys
import threading
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
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
from evals.session_recap_ingest_vertical_slice.recap_ingest_run_report import (  # noqa: E402
    RecapIngestRunSummary,
    capture_and_write_recap_ingest_report,
    write_recap_ingest_multi_summary,
)
from evals.session_recap_ingest_vertical_slice.scope_b_grader import (  # noqa: E402
    collect_scope_b_recap_ingest_report_extras,
    collect_scope_b_recap_ingest_violations,
)
from evals.session_recap_ingest_vertical_slice.step0_pre_state import build_pre_state_corpus  # noqa: E402
from src.agent.planner import (  # noqa: E402
    _resolve_planner_model,
    build_corpus_path_ref_index,
    make_tool_dispatcher,
    merge_planning_turn_details,
    run_planning_turn_detailed,
    _planner_tools_responses,
)
from src.agent.planner_cache import load_or_build_planner_instructions  # noqa: E402
from src.agent.planner_telemetry import maybe_full_text, text_sig  # noqa: E402
from src.agent.recap_context import RecapContextError, resolve_recap_context  # noqa: E402
from src.agent.synthesis import _load_api_key  # noqa: E402
from src.bootstrap_env import load_dungeonmindbuddy_dotenv  # noqa: E402

_SLICE_DIR = Path(__file__).resolve().parent
_GOLD_SCENARIO = _SLICE_DIR / "gold" / "scope_b_session_20.json"
_SKILL_PATH = Path(_REPO_ROOT) / ".cursor/skills/recap-write/SKILL.md"
_ALLOW_WRITES_ENV = "DUNGEONMIND_PLANNER_ALLOW_WRITES"


def load_scope_b_scenario() -> dict[str, Any]:
    if not _GOLD_SCENARIO.is_file():
        raise FileNotFoundError(f"missing gold scenario: {_GOLD_SCENARIO}")
    return json.loads(_GOLD_SCENARIO.read_text(encoding="utf-8"))


def _strip_markdown_frontmatter(text: str) -> str:
    if not text.startswith("---"):
        return text
    parts = text.split("---", 2)
    if len(parts) >= 3:
        return parts[2].lstrip("\n")
    return text


def load_skill_markdown_for_prompt(*, max_chars: int = 24_000) -> str:
    """Load SKILL.md body (no YAML frontmatter) for inclusion in the user message."""
    if not _SKILL_PATH.is_file():
        return (
            "(Skill file not found at `.cursor/skills/recap-write/SKILL.md`; "
            "use the recap-write skill from the repo.)\n"
        )
    body = _strip_markdown_frontmatter(_SKILL_PATH.read_text(encoding="utf-8")).strip()
    if len(body) > max_chars:
        body = body[:max_chars] + "\n\n…(skill excerpt truncated for prompt size)…\n"
    return body


def load_fixture_raw_notes() -> str:
    sc = load_scope_b_scenario()
    rel = str(sc.get("fixture_relpath") or "fixtures/session_20_raw_notes.txt").strip()
    path = (_SLICE_DIR / rel).resolve()
    if not path.is_file():
        raise FileNotFoundError(f"fixture missing: {path}")
    return path.read_text(encoding="utf-8")


def build_recap_ingest_user_message(raw_notes: str, *, raw_notes_corpus_rel: str) -> str:
    skill = load_skill_markdown_for_prompt()
    rel = str(raw_notes_corpus_rel).strip().replace("\\", "/")
    return (
        "You are executing the **recap-write** skill against the "
        "attached campaign corpus. Corpus write tools are enabled: use two-phase "
        "`write_corpus_file` / `append_timeline_row` per the skill.\n\n"
        "**Structured output:** Your final reply MUST conform to the strict "
        "`planner_turn_output_recap_write` schema (the API enforces it). Put GM-facing "
        "prose in `message` and the full `recap_write_v1` object in the dedicated "
        "`recap_write` field — do **not** embed JSON inside `message`. Use empty arrays "
        "for sections with nothing to report; `prep_pointer_proposal` is an object or null.\n\n"
        "The same raw session notes are also available on disk for "
        f"`assemble_recap_draft` at corpus-relative path `{rel}` "
        "(use this path; do not re-type the notes into `write_corpus_file`).\n\n"
        "--- Skill (reference) ---\n\n"
        f"{skill}\n\n"
        "--- Raw session notes ---\n\n"
        f"{raw_notes.strip()}\n"
    )


def run_session_recap_ingest_turn(
    *,
    corpus_dir: Path,
    client: Any,
    model_id: str,
    cache_root: Path | None = None,
    scenario: dict[str, Any] | None = None,
    raw_notes: str | None = None,
    allow_corpus_writes: bool = True,
) -> PlannerStep1Run:
    """One planner turn for Session 20 recap ingest; gates from ``scope_b_session_20.json`` final block."""
    sc = copy.deepcopy(scenario or load_scope_b_scenario())
    notes = raw_notes if raw_notes is not None else load_fixture_raw_notes()
    ingest_rel = str(
        sc.get("ingest_raw_notes_relpath")
        or "Longmont Campaign/Campaign 2/_ingest_staging/session_20_raw_notes.md"
    ).strip()
    staging_path = (corpus_dir / ingest_rel).resolve()
    staging_path.parent.mkdir(parents=True, exist_ok=True)
    staging_path.write_text(notes, encoding="utf-8")

    sc.setdefault("input", {})["user_message"] = build_recap_ingest_user_message(
        notes, raw_notes_corpus_rel=ingest_rel
    )

    corpus_path = corpus_dir.resolve()
    # Snapshot recap context BEFORE any planner turn. The same snapshot drives the
    # dispatch-guard allowlist for both turns and the post-run Scope-B grader, so a
    # turn-1 commit that adds ``Session N - Recap.md`` to the corpus cannot shift
    # ``max(session)`` and rewrite the allowlist mid-scenario (the temporal-coupling
    # bug that surfaced in the first 2-turn cohort: target want=21 got=20, plus
    # spurious off-allowlist reads of Session 17 + the session-N prep doc).
    try:
        pre_turn_recap_context = resolve_recap_context(corpus_path)
    except RecapContextError:
        pre_turn_recap_context = None
    sid = fixture_scenario_id(sc)
    user_message, input_violations = resolve_planner_user_message(sc, corpus_path)
    if input_violations:
        return _empty_fail(sid, {"input": input_violations})
    if not user_message.strip():
        return _empty_fail(sid, {"input": [f"[{sid}] empty user message"]})

    instructions, fp = load_or_build_planner_instructions(
        corpus_path,
        cache_root=cache_root,
        include_write_tools=allow_corpus_writes,
    )
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

    allowlist_extras = list(
        (sc.get("scope_b_grader") or {}).get("read_allowlist_extra") or []
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
            "suite": "session_recap_ingest_vertical_slice",
            "corpus_fingerprint": fp,
            "turn_index": 0,
        },
        corpus_path_ref_index=ref_index,
        active_skill_id="recap-write",
        skill_read_allowlist_extras=allowlist_extras,
        skill_recap_context=pre_turn_recap_context,
    )
    follow_block = sc.get("followup_turn")
    followup_user_line = ""
    first_turn_final_text = (detail.final_text or "").strip()
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
                    "scenario_id": sid,
                    "suite": "session_recap_ingest_vertical_slice",
                    "corpus_fingerprint": fp,
                    "phase": "followup_user",
                    "turn_index": 1,
                },
                corpus_path_ref_index=ref_index,
                active_skill_id="recap-write",
                skill_read_allowlist_extras=allowlist_extras,
                skill_recap_context=pre_turn_recap_context,
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
    scope_v = collect_scope_b_recap_ingest_violations(
        sc,
        detail,
        corpus_path,
        precomputed_recap_context=pre_turn_recap_context,
    )
    is_scope_b = str(sc.get("schema", "")) == "session_recap_ingest_scope_b_v1"
    scope_b_grader_on = (sc.get("scope_b_grader") or {}).get("enabled") is not False
    if is_scope_b and scope_b_grader_on:
        tool_ok = not bool(scope_v.get("scope_b_tool"))
        payload_ok = not bool(scope_v.get("scope_b_payload"))
        if scope_v:
            merged_violations = dict(result.violations)
            for key, rows in scope_v.items():
                merged_violations.setdefault(key, []).extend(rows)
            result = replace(
                result,
                violations=merged_violations,
                passed=result.passed and not scope_v,
                tool_trace_gates_passed=tool_ok,
                payload_gates_passed=payload_ok,
            )
        else:
            result = replace(
                result,
                tool_trace_gates_passed=tool_ok,
                payload_gates_passed=payload_ok,
            )

    return PlannerStep1Run(
        detail=detail,
        result=result,
        instructions=instructions,
        user_line=user_message,
        corpus_fingerprint=fp,
        post_planner_step2_benchmark_detail=None,
        scenario_key=sid,
        followup_user_line=followup_user_line,
        first_turn_final_text=first_turn_final_text,
    )


def _iso_utc_now() -> str:
    return time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())


def _filter_argv_for_detach_child(argv: list[str]) -> list[str]:
    """Strip detach-related flags from CLI argv (not forwarded to the child process)."""
    out: list[str] = []
    i = 0
    while i < len(argv):
        a = argv[i]
        if a in ("--detach", "--background", "--detach-follow"):
            i += 1
            continue
        if a.startswith("--detach-log="):
            i += 1
            continue
        if a == "--detach-log":
            i += 2
            continue
        out.append(a)
        i += 1
    return out


def _spawn_detached_benchmark_child(*, log_path: Path) -> subprocess.Popen[bytes]:
    """Run the same benchmark in a subprocess; return the :class:`subprocess.Popen` handle."""
    filtered = _filter_argv_for_detach_child(sys.argv[1:])
    cmd = [
        sys.executable,
        "-m",
        "evals.session_recap_ingest_vertical_slice.step1_recap_ingest_run",
        *filtered,
    ]
    log_path.parent.mkdir(parents=True, exist_ok=True)
    compact = time.strftime("%Y%m%dT%H%M%SZ", time.gmtime())
    header = (
        f"===== recap-ingest detach child =====\n"
        f"scheduled_utc: {compact}\n"
        f"cmd: {' '.join(cmd)}\n"
        f"cwd: {_REPO_ROOT}\n"
    )
    env = os.environ.copy()
    env.setdefault("PYTHONUNBUFFERED", "1")

    log_f = open(log_path, "wb")  # noqa: SIM115 — closed after Popen dup
    try:
        log_f.write(header.encode("utf-8"))
        log_f.flush()
        proc = subprocess.Popen(
            cmd,
            cwd=_REPO_ROOT,
            stdout=log_f,
            stderr=subprocess.STDOUT,
            env=env,
            start_new_session=True,
        )
    finally:
        log_f.close()
    return proc


def _stream_log_follow(log_path: Path, *, child: subprocess.Popen[bytes]) -> None:
    """Stream a growing log file to stdout (like ``tail -f``).

    Exits when ``child`` terminates and the file has been drained. KeyboardInterrupt
    stops only this viewer; the child keeps running (new session).
    """
    log_path = log_path.resolve()
    deadline = time.monotonic() + 60.0
    while not log_path.exists() and time.monotonic() < deadline:
        time.sleep(0.05)
    if not log_path.exists():
        print(f"[recap-ingest] Log file not found yet: {log_path}", file=sys.stderr, flush=True)
        return
    with open(log_path, encoding="utf-8", errors="replace") as f:
        try:
            while True:
                line = f.readline()
                if line:
                    print(line, end="", flush=True)
                    continue
                if child.poll() is not None:
                    time.sleep(0.05)
                    tail = f.read()
                    if tail:
                        print(tail, end="", flush=True)
                    code = child.returncode
                    print(
                        f"\n[recap-ingest] Child exited with code {code}.",
                        file=sys.stderr,
                        flush=True,
                    )
                    break
                time.sleep(0.12)
        except KeyboardInterrupt:
            print(
                "\n[recap-ingest] Stopped streaming log (child process may still be running).",
                file=sys.stderr,
                flush=True,
            )


def _vlog(verbosity: int, need: int, msg: str) -> None:
    if verbosity >= need:
        print(f"[recap-ingest {_iso_utc_now()}] {msg}", file=sys.stderr, flush=True)


def _dry_run_from_write_args(args: dict[str, Any]) -> bool:
    v = args.get("dry_run", True)
    if isinstance(v, bool):
        return v
    if isinstance(v, str):
        return v.strip().lower() in ("true", "1", "yes", "on")
    return bool(v)


def _tool_trace_signature(tool_trace: list[dict[str, Any]]) -> str:
    return ",".join(str(row.get("tool", "") or "") for row in tool_trace)


def _write_corpus_phases_summary(tool_trace: list[dict[str, Any]]) -> str:
    phases: list[str] = []
    for row in tool_trace:
        if str(row.get("tool", "")) != "write_corpus_file":
            continue
        raw = row.get("arguments")
        args = raw if isinstance(raw, dict) else {}
        phases.append("preview" if _dry_run_from_write_args(args) else "commit")
    if not phases:
        return "none"
    return "→".join(phases)


def _dump_tool_trace_verbose(tool_trace: list[dict[str, Any]], *, max_arg_chars: int = 800) -> None:
    print(f"[recap-ingest {_iso_utc_now()}] § tool_trace ({len(tool_trace)} rows)", file=sys.stderr, flush=True)
    for i, row in enumerate(tool_trace):
        name = str(row.get("tool", ""))
        raw_args = row.get("arguments")
        args = raw_args if isinstance(raw_args, dict) else {}
        arg_s = json.dumps(args, ensure_ascii=False, default=str)
        if len(arg_s) > max_arg_chars:
            arg_s = arg_s[: max_arg_chars - 3] + "..."
        excerpt = str(row.get("output_excerpt", "") or "").replace("\n", " ")
        if len(excerpt) > 240:
            excerpt = excerpt[:237] + "..."
        print(
            f"  [{i}] {name} output_chars={row.get('output_chars')} "
            f"args={arg_s}",
            file=sys.stderr,
            flush=True,
        )
        if excerpt:
            print(f"       excerpt: {excerpt}", file=sys.stderr, flush=True)


def print_recap_ingest_review(
    run: PlannerStep1Run,
    *,
    corpus_dir: Path,
    model_id: str,
    review_mode: str = "summary",
) -> None:
    """Compact review to stdout (mirrors other vertical slices, recap-specific header)."""
    d = run.detail
    sep = "=" * 72
    print(sep)
    print("SESSION RECAP INGEST — PLANNER REVIEW")
    print(sep)
    print(f"scenario_id:      {run.result.scenario_id}")
    print(f"model_id:         {model_id}")
    print(f"gates_passed:     {run.result.passed}")
    if run.result.tool_trace_gates_passed is not None:
        print(f"tool_trace_gates: {run.result.tool_trace_gates_passed}")
    if run.result.payload_gates_passed is not None:
        print(f"payload_gates:    {run.result.payload_gates_passed}")
    print(f"review_mode:      {review_mode}")
    print(f"corpus_fprint:    {run.corpus_fingerprint}")
    print(f"corpus_dir:       {corpus_dir.resolve()}")
    print(f"hit_tool_limit:   {d.hit_tool_round_limit}")
    print(f"tool_trace rows:  {len(d.tool_trace)}")
    print()
    print(sep)
    print("§ Prompt payload sizes")
    print(sep)
    print(f"instructions:  {text_sig(run.instructions)}")
    print(f"user_line:     {text_sig(run.user_line)}")
    print()
    print(sep)
    print("§ Token usage (per round)")
    print(sep)
    for i, row in enumerate(d.usage_rounds):
        u = row.get("usage") or {}
        print(
            f"  round[{i}] input={u.get('input_tokens')} output={u.get('output_tokens')} "
            f"cached={u.get('cached_tokens')}"
        )
    tc = d.telemetry_cost or {}
    print(f"  scenario_estimated_cost_usd: {tc.get('scenario_estimated_cost_usd')}")
    print()
    if not run.result.passed:
        print(sep)
        print("§ Violations")
        print(sep)
        for k, rows in sorted(run.result.violations.items()):
            for r in rows:
                print(f"  {k}: {r}")
        print()
    print(sep)
    print("§ Final assistant text (preview)")
    print(sep)
    print(maybe_full_text(d.final_text))


def main() -> None:
    parser = argparse.ArgumentParser(description="Session recap ingest — planner step 1 (live API).")
    parser.add_argument(
        "--print-root",
        action="store_true",
        help="Copy corpus, apply pre-state manifest, print tmp corpus root and exit.",
    )
    parser.add_argument(
        "--live-corpus",
        action="store_true",
        help="Use live repo corpus/eldyrwild-markdown (no pre-state strip). For debugging only.",
    )
    parser.add_argument(
        "--tmp-parent",
        type=Path,
        default=None,
        help="Optional parent directory for pre-state copy (default: system temp).",
    )
    parser.add_argument(
        "--model",
        type=str,
        default="",
        help="Override planner model id (else MODEL_POLICY / default).",
    )
    parser.add_argument(
        "--no-writes",
        action="store_true",
        help="Disable corpus write tools (overrides env).",
    )
    parser.add_argument(
        "--n",
        type=int,
        default=1,
        help=(
            "Number of turns to run (default 1). When N>1, also writes a "
            "cohort summary alongside per-run reports."
        ),
    )
    parser.add_argument(
        "--parallel",
        "-p",
        type=int,
        default=1,
        metavar="K",
        help=(
            "Run up to K cohort runs concurrently (default 1 = sequential). "
            "Each worker does its own per-run pre-state corpus build + planner turn; "
            "report writing is serialized so stdout review blocks don't garble. "
            "Recommended: K == --n for a 5x cohort (~5x speedup since most wall-time "
            "is spent waiting on the OpenAI API)."
        ),
    )
    parser.add_argument(
        "--runs-root",
        type=Path,
        default=None,
        help=(
            "Override the run-report root directory. Default: "
            "<slice>/artifacts/runs (or env RECAP_INGEST_RUNS_ROOT)."
        ),
    )
    parser.add_argument(
        "-v",
        "--verbose",
        action="count",
        default=None,
        help=(
            "More progress on stderr (timestamps, wall-clock per run, gates, tool signature, "
            "write_corpus_file preview/commit phases). Default is -vv (full tool_trace dump). "
            "Use -q / --quiet to suppress; -v / -vv are accepted for explicit overrides."
        ),
    )
    parser.add_argument(
        "-q",
        "--quiet",
        action="store_true",
        help="Silence stderr progress logging (overrides --verbose).",
    )
    parser.add_argument(
        "--detach",
        "--background",
        action="store_true",
        dest="detach",
        help=(
            "Spawn the same run in a background subprocess (same flags except --detach) "
            "and exit immediately. Logs stdout+stderr to --detach-log (default under /tmp). "
            "Requires OPENAI_API_KEY (same as the synchronous run)."
        ),
    )
    parser.add_argument(
        "--detach-log",
        type=Path,
        default=None,
        metavar="PATH",
        help=(
            "Log file for a detached run. Default: /tmp/recap_ingest_detach_<UTC>.log. "
            "Not used when --detach is absent."
        ),
    )
    parser.add_argument(
        "--detach-follow",
        action="store_true",
        help=(
            "With --detach: keep this terminal open and stream --detach-log to stdout "
            "(like tail -f). Ctrl+C stops streaming only; the benchmark subprocess keeps running. "
            "Without this flag, the parent exits immediately—use tail -f on the log path to observe."
        ),
    )
    args = parser.parse_args()
    if args.quiet:
        verbosity = 0
    elif args.verbose is None:
        # Default to maximum verbosity (full tool_trace dump per run on stderr).
        # The cohort review summaries on stdout are always printed independently.
        verbosity = 2
    else:
        verbosity = int(args.verbose)

    if args.detach and args.print_root:
        print("Cannot combine --detach with --print-root.", file=sys.stderr)
        sys.exit(2)
    if args.detach_follow and not args.detach:
        print("--detach-follow requires --detach.", file=sys.stderr)
        sys.exit(2)

    if args.detach:
        load_dungeonmindbuddy_dotenv()
        if not (_load_api_key() or "").strip():
            print(
                "OPENAI_API_KEY missing after loading .env / .env.development "
                "(see src/bootstrap_env.py). Add the key to repo .env or export it.",
                file=sys.stderr,
            )
            sys.exit(2)
        if args.detach_log is not None:
            log_path = args.detach_log.expanduser()
        else:
            compact = time.strftime("%Y%m%dT%H%M%SZ", time.gmtime())
            log_path = Path("/tmp") / f"recap_ingest_detach_{compact}.log"
        proc = _spawn_detached_benchmark_child(log_path=log_path)
        abs_log = log_path.resolve()
        print(
            f"[recap-ingest] Detached background run (PID {proc.pid}).\n"
            f"[recap-ingest] Log: {abs_log}",
            flush=True,
        )
        if args.detach_follow:
            print(
                "[recap-ingest] Streaming log to stdout (Ctrl+C stops only this viewer)…",
                flush=True,
            )
            _stream_log_follow(abs_log, child=proc)
        else:
            print(f"[recap-ingest] Observe: tail -f {abs_log}", flush=True)
        sys.exit(0)

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
            "OPENAI_API_KEY missing after loading .env / .env.development "
            "(see src/bootstrap_env.py). Add the key to repo .env or export it for CI.",
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

    def _build_corpus_for_run(run_index: int) -> Path:
        """Per-run corpus root.

        - ``--live-corpus``: always the live repo corpus (no isolation between runs;
          intended for single-shot debugging only — a warning is printed for ``--n>1``).
        - ``--tmp-parent`` set: each run gets its own ``<tmp_parent>/run_NNN`` subdir
          so the user can keep all cohort copies side-by-side for forensics.
        - otherwise: each run gets a fresh OS tempdir from ``build_pre_state_corpus``.
        """
        if args.live_corpus:
            return resolve_corpus_dir()
        if args.tmp_parent is not None:
            run_parent = args.tmp_parent / f"run_{run_index + 1:03d}"
            run_parent.mkdir(parents=True, exist_ok=True)
            return build_pre_state_corpus(tmp_dir=run_parent)
        return build_pre_state_corpus()

    initial_corpus_root = _build_corpus_for_run(0)
    if not initial_corpus_root.is_dir():
        print(f"corpus directory missing: {initial_corpus_root}", file=sys.stderr)
        sys.exit(2)

    from openai import OpenAI  # noqa: E402

    configure_planner_review_logging()
    review_mode = resolve_review_mode()
    n = max(1, int(args.n))
    gold = load_scope_b_scenario()
    ingest_rel = str(
        gold.get("ingest_raw_notes_relpath")
        or "Longmont Campaign/Campaign 2/_ingest_staging/session_20_raw_notes.md"
    ).strip()
    two_phase = bool((gold.get("expected_tool_trace") or {}).get("two_phase_commit_required"))
    if args.live_corpus and n > 1:
        print(
            "[recap-ingest] WARNING: --live-corpus + --n>1 disables per-run corpus "
            "isolation; commits from earlier runs will pollute later runs.",
            file=sys.stderr,
        )
    print(
        f"[recap-ingest] corpus_dir[run 1/{n}]={initial_corpus_root}\n"
        f"[recap-ingest] pre_state={'off' if args.live_corpus else 'on'} "
        f"allow_corpus_writes={allow_writes} "
        f"per_run_pre_state={'off' if args.live_corpus else 'on'}\n"
        f"[recap-ingest] PLANNER_REVIEW_MODE={review_mode}\n",
        file=sys.stderr,
    )
    _vlog(
        verbosity,
        1,
        f"cohort n={n} verbose={verbosity} ingest_raw_notes_relpath={ingest_rel!r} "
        f"gold_two_phase_commit_required={two_phase}",
    )

    client = OpenAI()
    model_id = _resolve_planner_model(args.model.strip() or None)
    _vlog(verbosity, 1, f"resolved model_id={model_id!r}")

    cohort_size = n if n > 1 else None
    summaries: list[RecapIngestRunSummary] = []
    last_run: PlannerStep1Run | None = None
    scenario_id_for_summary = ""
    parallel = max(1, min(int(getattr(args, "parallel", 1) or 1), n))

    def _emit_run_report(
        i: int,
        run: PlannerStep1Run,
        corpus_root: Path,
        elapsed_s: float,
    ) -> RecapIngestRunSummary:
        """Per-run logging + report writing. MUST be serialized when ``parallel>1``
        (``capture_and_write_recap_ingest_report`` patches ``sys.stdout`` via
        ``contextlib.redirect_stdout`` to capture the review block, so concurrent
        invocations would interleave/garble each other's stdout)."""
        if n > 1:
            print(f"\n[recap-ingest] === run {i + 1}/{n} ===", file=sys.stderr)
        trace = list(run.detail.tool_trace or [])
        tc = run.detail.telemetry_cost or {}
        cost = tc.get("scenario_estimated_cost_usd", tc.get("planner_estimated_cost_usd"))
        _vlog(
            verbosity,
            1,
            f"run {i + 1}/{n} finished in {elapsed_s}s | gates_passed={run.result.passed} "
            f"tool_trace_gates={run.result.tool_trace_gates_passed} "
            f"payload_gates={run.result.payload_gates_passed} "
            f"cost_usd={cost} trace_rows={len(trace)} "
            f"write_phases={_write_corpus_phases_summary(trace)} "
            f"response_id={getattr(run.detail, 'last_response_id', '')!r}",
        )
        _vlog(verbosity, 1, f"tool_trace_sig: {_tool_trace_signature(trace)}")
        if verbosity >= 1 and not run.result.passed:
            viol = run.result.violations or {}
            for bucket, rows in sorted(viol.items()):
                for line in rows[:12]:
                    _vlog(verbosity, 1, f"violation [{bucket}]: {line}")
                if len(rows) > 12:
                    _vlog(verbosity, 1, f"violation [{bucket}]: … {len(rows) - 12} more")
        if verbosity >= 1:
            try:
                extras = collect_scope_b_recap_ingest_report_extras(gold, run.detail)
            except Exception as exc:  # noqa: BLE001
                extras = {"error": repr(exc)}
            soft_obs = extras.get("write_corpus_file_soft_observations") or []
            for line in soft_obs[:6]:
                _vlog(verbosity, 1, f"soft [scope_b]: {line}")
            if len(soft_obs) > 6:
                _vlog(verbosity, 1, f"soft [scope_b]: … {len(soft_obs) - 6} more")
        if verbosity >= 2:
            _dump_tool_trace_verbose(trace)
        paths, summary = capture_and_write_recap_ingest_report(
            print_callable=print_recap_ingest_review,
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
            cohort_size=cohort_size,
        )
        print(
            f"\n[recap-ingest] report: {paths.primary_md}\n"
            f"[recap-ingest] sidecar: {paths.sidecar_json}",
            file=sys.stderr,
        )
        _vlog(verbosity, 1, f"artifacts written primary={paths.primary_md}")
        return summary

    if parallel <= 1:
        # Sequential path (unchanged behavior).
        for i in range(n):
            # Run 0 already built above (so the early exit for missing corpus fires before
            # any API spend); rebuild for every later run for honest cross-run isolation.
            corpus_root = initial_corpus_root if i == 0 else _build_corpus_for_run(i)
            if i > 0:
                print(
                    f"[recap-ingest] corpus_dir[run {i + 1}/{n}]={corpus_root}",
                    file=sys.stderr,
                )
            _vlog(verbosity, 1, f"--- begin run {i + 1}/{n} corpus={corpus_root} ---")
            t0 = time.monotonic()
            run = run_session_recap_ingest_turn(
                corpus_dir=corpus_root,
                client=client,
                model_id=model_id,
                allow_corpus_writes=allow_writes,
            )
            elapsed_s = round(time.monotonic() - t0, 2)
            last_run = run
            scenario_id_for_summary = run.result.scenario_id or scenario_id_for_summary
            summary = _emit_run_report(i, run, corpus_root, elapsed_s)
            summaries.append(summary)
    else:
        # Parallel path: workers do the API-bound planner turn concurrently; report
        # writing is serialized via a single lock to keep stdout capture coherent.
        # Each worker builds its own per-run pre-state corpus so cross-run isolation
        # is preserved (matches the sequential path's per-run rebuild semantics).
        print(
            f"[recap-ingest] parallel={parallel}/{n} (workers race on the OpenAI API; "
            f"reports flush in completion order)",
            file=sys.stderr,
        )
        _vlog(verbosity, 1, f"--- launching {n} runs with parallel={parallel} ---")
        report_lock = threading.Lock()
        results_by_index: dict[int, RecapIngestRunSummary] = {}
        # Re-use the already-built run-0 corpus for one worker; build fresh for the rest.
        prebuilt_run0_corpus: Path | None = initial_corpus_root
        prebuilt_lock = threading.Lock()

        def _claim_run0_corpus() -> Path | None:
            nonlocal prebuilt_run0_corpus
            with prebuilt_lock:
                claimed = prebuilt_run0_corpus
                prebuilt_run0_corpus = None
                return claimed

        def _worker(i: int) -> tuple[int, PlannerStep1Run, Path, float]:
            corpus_root = _claim_run0_corpus() if i == 0 else _build_corpus_for_run(i)
            if corpus_root is None:
                # Run 0's prebuilt corpus was already claimed (shouldn't happen since
                # only worker i==0 ever calls _claim_run0_corpus); fall back to fresh build.
                corpus_root = _build_corpus_for_run(i)
            print(
                f"[recap-ingest] [run {i + 1}/{n}] corpus={corpus_root}",
                file=sys.stderr,
                flush=True,
            )
            _vlog(verbosity, 1, f"[run {i + 1}/{n}] begin")
            t0 = time.monotonic()
            run = run_session_recap_ingest_turn(
                corpus_dir=corpus_root,
                client=client,
                model_id=model_id,
                allow_corpus_writes=allow_writes,
            )
            elapsed_s = round(time.monotonic() - t0, 2)
            return i, run, corpus_root, elapsed_s

        completed = 0
        with ThreadPoolExecutor(max_workers=parallel, thread_name_prefix="recap-ingest") as exe:
            futures = [exe.submit(_worker, i) for i in range(n)]
            for fut in as_completed(futures):
                try:
                    i, run, corpus_root, elapsed_s = fut.result()
                except Exception as exc:  # noqa: BLE001
                    completed += 1
                    print(
                        f"[recap-ingest] worker raised: {exc!r} ({completed}/{n} completed)",
                        file=sys.stderr,
                        flush=True,
                    )
                    raise
                with report_lock:
                    last_run = run
                    if run.result.scenario_id:
                        scenario_id_for_summary = run.result.scenario_id
                    summary = _emit_run_report(i, run, corpus_root, elapsed_s)
                    results_by_index[i] = summary
                    completed += 1
                    _vlog(
                        verbosity,
                        1,
                        f"[run {i + 1}/{n}] reported ({completed}/{n} done)",
                    )
        # Preserve original run-index order for the cohort summary so per-run keys
        # (e.g. run001..runNNN in the markdown) line up with their per-run filenames.
        summaries = [results_by_index[i] for i in range(n)]

    if n > 1:
        md_summary, json_summary = write_recap_ingest_multi_summary(
            summaries,
            model_id=model_id,
            scenario_id=scenario_id_for_summary or "session_recap_ingest_session_20",
            runs_root=args.runs_root,
        )
        print(
            f"\n[recap-ingest] cohort summary: {md_summary}\n"
            f"[recap-ingest] cohort sidecar:  {json_summary}",
            file=sys.stderr,
        )
        gp = sum(1 for s in summaries if s.gates_passed)
        tt = sum(1 for s in summaries if s.tool_trace_gates_passed)
        pl = sum(1 for s in summaries if s.payload_gates_passed)
        _vlog(
            verbosity,
            1,
            f"cohort done | gates {gp}/{n} tool_trace {tt}/{n} payload {pl}/{n} | "
            f"summary_md={md_summary}",
        )
        all_passed = all(s.gates_passed for s in summaries)
        if not all_passed:
            sys.exit(1)
        return

    if last_run is not None:
        _vlog(
            verbosity,
            1,
            f"single run done | gates_passed={last_run.result.passed} "
            f"tool_trace_gates={last_run.result.tool_trace_gates_passed} "
            f"payload_gates={last_run.result.payload_gates_passed}",
        )
    if last_run is not None and not last_run.result.passed:
        sys.exit(1)


if __name__ == "__main__":
    main()
