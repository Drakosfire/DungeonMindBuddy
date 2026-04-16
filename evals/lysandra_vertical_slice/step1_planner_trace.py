"""Step 1 — agent benchmark: planner ``tool_trace`` gates (Lysandra vertical slice).

Gold scenarios: **directed**, **autonomous**, **stat_check**, **clarify_cr**, **upgrade_prose** (see ``gold/planner_step1_*.json``;
``LYSANDRA_PLANNER_STEP1_SCENARIO`` pins the scenario; **when unset**, the CLI default benchmark is
**upgrade_prose** (natural power-rise ask). After each live turn, optional **Step 2 benchmark**
checks (gold key ``planner_bridge`` — observation only; see ``Docs/Plans/NAMING-benchmark-vs-runtime.md``)
classify the same ``user_message`` and may assert statblock paths in the trace vs
``corpus_policy.canonical_statblock_relpath``.

Reuses ``evals.planner_slice.live_eval`` scenario shape and matchers.

**Review / logging**

- Enable JSON telemetry on stderr: INFO for loggers ``dmb.planner`` and ``dmb.planner.live_eval``
  (``configure_planner_review_logging()`` from ``main()``).
- Larger bodies inside telemetry JSON lines: ``PLANNER_LOG_FULL_IO=1``.
- Human review verbosity: ``PLANNER_REVIEW_MODE=summary|debug|forensics`` (default ``summary``).
- **Default benchmark artifacts:** each run writes a **dated, named** file under
  ``artifacts/runs/YYYY-MM-DD/`` (scenario, model, pass/fail, turn count, UTC timestamp in the
  filename) and mirrors the same body to ``artifacts/last_planner_step1_run.md`` for quick reopen.
- **Two-turn scenarios:** gold ``followup_turn.user_message`` runs a second ``run_planning_turn_detailed`` with ``previous_response_id`` from the first turn (GM answer in voice); gates use merged ``tool_trace`` and the **last** turn's ``final_text``. The review prints **§ Clarification** with turn-0 final prose plus any ``propose_clarification`` tool rows.
- This module prints a human-readable report: prompt sizes, per-API-round token usage
  (``usage.input_tokens`` = billed input for that ``responses.create``, including instructions
  and prior context for that round), planner steps, corpus text returned to the model, and
  the final assistant message.
"""

from __future__ import annotations

import sys
from pathlib import Path

# Runnable as ``python evals/lysandra_vertical_slice/step1_planner_trace.py`` (pytest adds ``.``).
_REPO_ROOT = str(Path(__file__).resolve().parents[2])
if _REPO_ROOT not in sys.path:
    sys.path.insert(0, _REPO_ROOT)

import contextlib  # noqa: E402
import copy  # noqa: E402
import io  # noqa: E402
import json  # noqa: E402
import logging  # noqa: E402
import os  # noqa: E402
from dataclasses import dataclass, replace  # noqa: E402
from datetime import datetime, timezone  # noqa: E402
from typing import Any, Literal  # noqa: E402

from evals.lysandra_vertical_slice.step0_corpus_environment import resolve_corpus_dir  # noqa: E402
from evals.lysandra_vertical_slice.step2_canonical_intent import (  # noqa: E402
    evaluate_step2_post_planner_benchmark,
    load_step2_gold,
)
from src.agent.synthesis import _load_api_key  # noqa: E402
from src.bootstrap_env import load_dungeonmindbuddy_dotenv  # noqa: E402
from evals.planner_slice.live_eval import (  # noqa: E402
    LiveEvalResult,
    evaluate_scenario_detail,
    resolve_planner_user_message,
)
from src.agent.corpus_path_tools import CORPUS_PATH_TOOL_NAMES  # noqa: E402
from src.agent.planner import (  # noqa: E402
    PlanningTurnDetail,
    _planner_tools_responses,
    _read_corpus_file_impl,
    make_tool_dispatcher,
    merge_planning_turn_details,
    run_planning_turn_detailed,
)
from src.agent.planner_cache import load_or_build_planner_instructions  # noqa: E402
from src.agent.planner_telemetry import text_sig  # noqa: E402
from src.agent.skill_pipeline import scenario_key_for_user_line  # noqa: E402

_SLICE_DIR = Path(__file__).resolve().parent

_PLANNER_STEP1_SCENARIO_ENV = "LYSANDRA_PLANNER_STEP1_SCENARIO"
_VALID_PLANNER_STEP1_SCENARIOS = frozenset({"directed", "autonomous", "stat_check", "clarify_cr", "upgrade_prose"})
# Default benchmark when no env / no user override: natural power-rise ask.
_DEFAULT_PLANNER_STEP1_SCENARIO_KEY = "upgrade_prose"
_REVIEW_MODE_ENV = "PLANNER_REVIEW_MODE"

ReviewMode = Literal["summary", "debug", "forensics"]


def resolve_review_mode() -> ReviewMode:
    raw = os.environ.get(_REVIEW_MODE_ENV, "summary").strip().lower()
    if raw == "debug":
        return "debug"
    if raw == "forensics":
        return "forensics"
    return "summary"


def default_planner_step1_scenario_key() -> str:
    """``directed`` / ``autonomous`` / ``stat_check`` / ``clarify_cr`` / ``upgrade_prose``. Default ``upgrade_prose``."""
    raw = os.environ.get(_PLANNER_STEP1_SCENARIO_ENV, _DEFAULT_PLANNER_STEP1_SCENARIO_KEY).strip().lower()
    return raw if raw in _VALID_PLANNER_STEP1_SCENARIOS else _DEFAULT_PLANNER_STEP1_SCENARIO_KEY


def planner_step1_gold_path(scenario_key: str | None = None) -> Path:
    key = scenario_key if scenario_key is not None else default_planner_step1_scenario_key()
    if key not in _VALID_PLANNER_STEP1_SCENARIOS:
        key = _DEFAULT_PLANNER_STEP1_SCENARIO_KEY
    return _SLICE_DIR / "gold" / f"planner_step1_{key}.json"


def load_planner_step1_scenario(scenario_key: str | None = None) -> dict[str, Any]:
    return json.loads(planner_step1_gold_path(scenario_key).read_text(encoding="utf-8"))


def configure_planner_review_logging() -> None:
    """Route ``dmb.planner`` (and live_eval helper) telemetry to the root handler at INFO."""
    if not logging.root.handlers:
        logging.basicConfig(
            level=logging.INFO,
            format="%(asctime)s %(levelname)s %(name)s %(message)s",
        )
    for name in ("dmb.planner", "dmb.planner.live_eval"):
        logging.getLogger(name).setLevel(logging.INFO)
    for noisy in ("httpx", "httpcore", "openai._base_client"):
        logging.getLogger(noisy).setLevel(logging.WARNING)


# Legacy bucket on ``LiveEvalResult.violations`` for Step 2 **benchmark** merges (not runtime control).
STEP2_BENCHMARK_VIOLATIONS_KEY = "step2_bridge"


@dataclass
class PlannerStep1Run:
    detail: PlanningTurnDetail
    result: LiveEvalResult
    instructions: str
    user_line: str
    corpus_fingerprint: str
    #: Step 2 **benchmark** payload after the planner turn (intent echo + trace checks); not used to control the planner.
    post_planner_step2_benchmark_detail: dict[str, Any] | None = None
    #: Gold scenario used for gates (``autonomous``, ``upgrade_prose``, …).
    scenario_key: str = ""
    #: Second user line when gold ``followup_turn`` runs (same OpenAI response thread).
    followup_user_line: str = ""
    #: Assistant ``final_text`` after turn 0 only (before follow-up merge); empty if no follow-up.
    first_turn_final_text: str = ""


def _empty_fail(sid: str, violations: dict[str, list[str]], user_line: str = "") -> PlannerStep1Run:
    detail = PlanningTurnDetail(
        final_text="",
        last_response_id="",
        tool_trace=[],
        steps=[],
        hit_tool_round_limit=False,
    )
    return PlannerStep1Run(
        detail=detail,
        result=LiveEvalResult(sid, False, violations),
        instructions="",
        user_line=user_line,
        corpus_fingerprint="",
        post_planner_step2_benchmark_detail=None,
        scenario_key="",
        followup_user_line="",
        first_turn_final_text="",
    )


def run_planner_step1_turn(
    *,
    corpus_dir: Path,
    client: Any,
    model_id: str,
    cache_root: Path | None = None,
    scenario: dict[str, Any] | None = None,
    scenario_key: str | None = None,
    user_line_override: str | None = None,
) -> PlannerStep1Run:
    """
    One ``run_planning_turn_detailed`` with the **benchmark** gold fixture; score with ``evaluate_scenario_detail``.

    **Scenarios** (``gold/planner_step1_*.json`` — harness gates, not production session routing):

    - ``directed`` — user message names folders/filenames to open (strong smoke, not autonomy).
    - ``autonomous`` — general prep ask; relaxed path gates (see gold ``fixture_note``).
    - ``stat_check`` — mechanical question; gates require opening the statblock file.
    - ``clarify_cr`` — benchmark for meaningful clarifier quality (tool call + question/slot constraints).
    - ``upgrade_prose`` — two-turn power-rise benchmark; gates require ``read_corpus_file`` and CR 6
      in final prose (see gold). Workflow detail lives in the **npc-power-increase** Cursor skill.

    **Scenario selection** (first match wins):

    1. Pass ``scenario`` or ``scenario_key`` (tests / callers).
    2. Else if ``LYSANDRA_PLANNER_STEP1_SCENARIO`` is set to a valid key, use that gold file
       (benchmark / CI). Optional ``user_line_override`` or env ``LYSANDRA_PLANNER_USER_MESSAGE``
       replaces ``input.user_message`` in that gold.
    3. Else if ``user_line_override`` or ``LYSANDRA_PLANNER_USER_MESSAGE`` is set: infer scenario via
       ``scenario_key_for_user_line`` (intent → ``upgrade_prose`` vs ``autonomous``) and load
       that gold, then inject the user message.
    4. Else: load **upgrade_prose** gold (default: natural power-rise ask).

    Loads ``.env`` / ``.env.development`` via ``load_dungeonmindbuddy_dotenv()`` so
    ``OPENAI_API_KEY`` does not require shell ``export``.
    """
    load_dungeonmindbuddy_dotenv()
    env_user = os.environ.get("LYSANDRA_PLANNER_USER_MESSAGE", "").strip()
    override = (user_line_override or env_user or "").strip() or None
    resolved_scenario_key = ""

    if scenario is not None:
        sc = copy.deepcopy(scenario)
        resolved_scenario_key = str(sc.get("fixture_role") or "").strip().lower()
        if override:
            sc.setdefault("input", {})["user_message"] = override
    elif scenario_key is not None:
        sc = copy.deepcopy(load_planner_step1_scenario(scenario_key))
        resolved_scenario_key = scenario_key
        if override:
            sc.setdefault("input", {})["user_message"] = override
    else:
        env_lane = os.environ.get(_PLANNER_STEP1_SCENARIO_ENV, "").strip().lower()
        if env_lane in _VALID_PLANNER_STEP1_SCENARIOS:
            sc = copy.deepcopy(load_planner_step1_scenario(env_lane))
            resolved_scenario_key = env_lane
            if override:
                sc.setdefault("input", {})["user_message"] = override
        elif override:
            resolved_scenario_key = scenario_key_for_user_line(override, client=client)
            sc = copy.deepcopy(load_planner_step1_scenario(resolved_scenario_key))
            sc.setdefault("input", {})["user_message"] = override
        else:
            resolved_scenario_key = _DEFAULT_PLANNER_STEP1_SCENARIO_KEY
            sc = load_planner_step1_scenario(_DEFAULT_PLANNER_STEP1_SCENARIO_KEY)
    corpus_path = corpus_dir.resolve()
    sid = str(sc.get("id", "lysandra_planner_step1"))
    user_message, input_violations = resolve_planner_user_message(sc, corpus_path)
    if input_violations:
        return _empty_fail(sid, {"input": input_violations})
    if not user_message.strip():
        return _empty_fail(sid, {"input": [f"[{sid}] empty user message"]})

    instructions, fp = load_or_build_planner_instructions(corpus_path, cache_root=cache_root)
    tools = _planner_tools_responses()
    tool_cost_sink: list[dict[str, Any]] = []
    dispatch = make_tool_dispatcher(
        corpus_path, client, model_id, statblock_stub=None, tool_cost_sink=tool_cost_sink
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
            "suite": "lysandra_vertical_slice_planner_step1",
            "corpus_fingerprint": fp,
            "turn_index": 0,
        },
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
                    "scenario_id": sid,
                    "suite": "lysandra_vertical_slice_planner_step1",
                    "corpus_fingerprint": fp,
                    "phase": "followup_user",
                    "turn_index": 1,
                },
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
    planner_key = str(sc.get("fixture_role") or "").strip().lower()
    if not planner_key:
        planner_key = resolved_scenario_key or (
            scenario_key if scenario_key is not None else default_planner_step1_scenario_key()
        )
    g2_bridge = load_step2_gold().get("planner_bridge")
    post_planner_step2_benchmark_detail: dict[str, Any] | None = None
    if isinstance(g2_bridge, dict) and g2_bridge:
        b_detail, b_ok, b_v = evaluate_step2_post_planner_benchmark(
            user_message=user_message,
            tool_trace=detail.tool_trace,
            planner_scenario_key=planner_key,
            intent_client=client,
        )
        post_planner_step2_benchmark_detail = b_detail
        if b_v:
            merged = dict(result.violations)
            merged.setdefault(STEP2_BENCHMARK_VIOLATIONS_KEY, []).extend(b_v)
            result = replace(
                result,
                passed=result.passed and b_ok,
                violations=merged,
            )
    return PlannerStep1Run(
        detail=detail,
        result=result,
        instructions=instructions,
        user_line=user_message,
        corpus_fingerprint=fp,
        post_planner_step2_benchmark_detail=post_planner_step2_benchmark_detail,
        scenario_key=resolved_scenario_key,
        followup_user_line=followup_user_line,
        first_turn_final_text=first_turn_final_text,
    )


def flatten_live_violations(violations: dict[str, list[str]]) -> list[str]:
    lines: list[str] = []
    for key, rows in sorted(violations.items()):
        for r in rows:
            lines.append(f"{key}: {r}")
    return lines


_LOAD_CTX_ATTACHED_PREFIX = "[context attached:"
_GEN_SB_ATTACHED_PREFIXES = (
    "[Attached corpus statblock:",
    "[Attached corpus statblock baseline:",
)


def _body_after_load_context_prefix(excerpt: str) -> tuple[bool, str]:
    """Split ``load_context_markdown`` tool output excerpt into (has_marker, body_fragment)."""
    s = excerpt or ""
    if not s.startswith(_LOAD_CTX_ATTACHED_PREFIX):
        return False, s
    parts = s.split("\n\n", 1)
    body = parts[1] if len(parts) > 1 else ""
    return True, body


def format_context_wiring_lines(tool_trace: list[dict[str, Any]]) -> list[str]:
    """
    Human-readable evidence that corpus statblock bytes were returned on the tool wire
    (what the next ``responses.create`` sees as ``function_call_output``), distinct from
    ``read_corpus_file`` discovery reads.
    """
    lines: list[str] = []
    lines.append(
        "Evidence uses stored ``tool_trace`` rows: ``output_excerpt`` is the first 800 chars of "
        "each tool return (same bytes sent to the API in that round)."
    )
    lines.append("")

    loads = [(i, r) for i, r in enumerate(tool_trace) if r.get("tool") == "load_context_markdown"]
    if loads:
        lines.append(f"load_context_markdown: {len(loads)} call(s) (explicit working-context attach)")
        for i, row in loads:
            path = str((row.get("arguments") or {}).get("path", "")).strip()
            excerpt = str(row.get("output_excerpt") or "")
            oc = row.get("output_chars")
            has_m, body_frag = _body_after_load_context_prefix(excerpt)
            first_nonempty = next((ln.strip() for ln in body_frag.splitlines() if ln.strip()), "")
            preview = first_nonempty[:180]
            sig = text_sig(body_frag) if body_frag else {}
            lines.append(
                f"  trace[{i}] path={path!r} output_chars={oc} "
                f"context_attached_prefix_present={has_m}"
            )
            if preview:
                lines.append(f"    first_nonblank_line_preview={preview!r}")
            if sig:
                lines.append(
                    f"    body_sig_from_trace_excerpt_chars={sig.get('chars')} "
                    f"sha256_16={sig.get('sha256_16')!r}"
                )
        lines.append("")
    else:
        lines.append(
            "load_context_markdown: 0 calls — no explicit attach tool in trace; "
            "if the model only used ``read_corpus_file`` on a statblock, the file still "
            "entered that round's outputs, but nothing is labeled ``[context attached: …]``."
        )
        lines.append("")

    stat_reads = [
        (i, r)
        for i, r in enumerate(tool_trace)
        if r.get("tool") == "read_corpus_file"
        and "statblock" in str((r.get("arguments") or {}).get("path", "")).lower()
    ]
    if stat_reads:
        lines.append(
            f"read_corpus_file on paths containing 'statblock': {len(stat_reads)} "
            f"(indices {[i for i, _ in stat_reads]})"
        )
        lines.append("")

    gen_rows = [(i, r) for i, r in enumerate(tool_trace) if r.get("tool") == "generate_statblock"]
    if gen_rows:
        lines.append(f"generate_statblock: {len(gen_rows)} call(s)")
        for i, row in gen_rows:
            args = row.get("arguments") or {}
            src = str(args.get("source_statblock_corpus_path", "") or "").strip()
            excerpt = str(row.get("output_excerpt") or "")
            attach = any(excerpt.startswith(p) for p in _GEN_SB_ATTACHED_PREFIXES)
            lines.append(
                f"  trace[{i}] source_statblock_corpus_path={src!r} "
                f"output_has_attached_baseline_prefix={attach} "
                f"output_chars={row.get('output_chars')}"
            )
        lines.append("")

    return lines


def _heuristic_turn0_asks_target_cr_in_prose(text: str) -> bool:
    """Loose signal: question mark plus CR / challenge phrasing (review only, not a gate)."""
    t = (text or "").lower()
    if "?" not in t:
        return False
    needles = (
        "what cr",
        "which cr",
        "target cr",
        "challenge rating",
        "what level",
        "which challenge",
        "how high",
        "what rating",
    )
    return any(n in t for n in needles)


def format_clarification_evidence_lines(
    tool_trace: list[dict[str, Any]],
    *,
    followup_user_line: str,
    first_turn_final_text: str,
    max_chars: int = 2400,
) -> list[str]:
    """Human-readable clarification: ``propose_clarification`` tool rows + turn 0 final prose."""
    rows = [(i, r) for i, r in enumerate(tool_trace) if r.get("tool") == "propose_clarification"]
    lines: list[str] = []
    lines.append(
        "Use this block to see whether the model surfaced clarification via tool calls "
        "and/or turn-0 prose."
    )
    lines.append("")
    if rows:
        lines.append(f"propose_clarification tool: {len(rows)} call(s) in merged trace")
        for i, row in rows:
            args = row.get("arguments") or {}
            q = str(args.get("question", "") or "").strip()
            slots = args.get("missing_slots")
            lines.append(f"  trace[{i}] question={q!r}")
            lines.append(f"            missing_slots={slots!r}")
    else:
        lines.append("propose_clarification tool: 0 calls in merged trace")
    lines.append("")
    if followup_user_line.strip():
        lines.append("Turn 0 assistant final (before follow-up user line):")
        ft = (first_turn_final_text or "").strip() or "(empty)"
        if len(ft) > max_chars:
            h = max_chars // 2
            ft = (
                ft[:h]
                + f"\n...[truncated, total_chars={len((first_turn_final_text or '').strip())}]...\n"
                + ft[-h:]
            )
        lines.append(ft)
        lines.append("")
        hint = _heuristic_turn0_asks_target_cr_in_prose(first_turn_final_text)
        lines.append(
            f"heuristic_turn0_asks_target_cr_in_prose (has '?' plus CR-ish phrase): {hint}"
        )
    else:
        lines.append("(Single-turn scenario: final answer is only under § Final LLM answer below.)")
    return lines


def _emit_planner_step1_review(
    run: PlannerStep1Run,
    *,
    corpus_dir: Path,
    model_id: str,
    review_mode: ReviewMode = "summary",
    max_retrieved_body_chars: int = 36_000,
) -> None:
    """Emit review lines to the current ``sys.stdout`` (used with ``redirect_stdout`` for capture)."""
    d = run.detail
    ins = run.instructions
    ul = run.user_line
    tools = _planner_tools_responses()
    tools_json = json.dumps(tools, ensure_ascii=False)
    sep = "=" * 72

    print(sep)
    print("LYSANDRA PLANNER STEP 1 — REVIEW")
    print(sep)
    print(f"scenario_id:      {run.result.scenario_id}")
    if run.scenario_key:
        print(f"scenario:         {run.scenario_key}")
    print(f"model_id:         {model_id}")
    print(f"gates_passed:     {run.result.passed}")
    print(f"review_mode:      {review_mode}")
    print(f"corpus_fprint:    {run.corpus_fingerprint}")
    print(f"corpus_dir:       {corpus_dir.resolve()}")
    print(f"hit_tool_limit:   {d.hit_tool_round_limit}")
    print(f"planner_steps:    {len(d.steps)} model response(s) recorded (see § Planner steps)")
    print(f"tool_trace rows:  {len(d.tool_trace)}")
    print()

    print(sep)
    print("§ Prompt payload sizes (characters; not tokens — use usage table for tokens)")
    print(sep)
    print(f"instructions:  {text_sig(ins)}")
    print(f"user_line:     {text_sig(ul)}")
    if run.followup_user_line:
        print(f"followup_user_line: {text_sig(run.followup_user_line)}")
    print(f"tools JSON:    chars={len(tools_json)}")
    print()

    print(sep)
    print(
        "§ Token usage — one row per `responses.create` completion\n"
        "  `input_tokens` = billed prompt size for that call (instructions + user/tool history\n"
        "  visible to the API for that round). Sum across rows ≈ cumulative input billed per call,\n"
        "  not deduplicated across rounds."
    )
    print(sep)
    tot_in = tot_out = tot_cached = 0
    for i, row in enumerate(d.usage_rounds):
        u = row.get("usage") or {}
        it = int(u.get("input_tokens", 0) or 0)
        ot = int(u.get("output_tokens", 0) or 0)
        ct = int(u.get("cached_tokens", 0) or 0)
        tot_in += it
        tot_out += ot
        tot_cached += ct
        print(
            f"  round[{i}] turn_index={row.get('turn_index', 0)} phase={row.get('phase')!r} "
            f"api_response_index={row.get('response_index')} "
            f"latency_ms={row.get('latency_ms')} "
            f"input_tokens={it} output_tokens={ot} cached_tokens={ct} "
            f"response_id={row.get('response_id')!r}"
        )
    tc = d.telemetry_cost or {}
    print()
    print(f"  sum(input_tokens) over rounds above:  {tot_in}")
    print(f"  sum(output_tokens) over rounds:       {tot_out}")
    print(f"  sum(cached_tokens) over rounds:       {tot_cached}")
    print(f"  planner_usage_totals (API cumulative): {tc.get('planner_usage_totals')}")
    print(f"  planner_estimated_cost_usd:           {tc.get('planner_estimated_cost_usd')}")
    print()

    if review_mode in ("debug", "forensics"):
        print(sep)
        print("§ Planner steps (assistant message + tool calls proposed that step)")
        print(sep)
        for rec in d.steps:
            calls = rec.function_calls
            names = [str(c.get("name", "")) for c in calls]
            preview = (rec.assistant_text or "").strip()
            if len(preview) > 3000:
                preview = (
                    preview[:1500]
                    + f"\n...[truncated, total {len(rec.assistant_text)} chars]...\n"
                    + preview[-1000:]
                )
            print(f"--- step_index={rec.step_index} response_id={rec.response_id!r} ---")
            print(f"function_calls: {names}")
            for j, c in enumerate(calls):
                args = c.get("arguments") or {}
                if str(c.get("name")) in CORPUS_PATH_TOOL_NAMES:
                    print(f"  call[{j}] {c.get('name')} path={args.get('path')!r}")
                else:
                    a = json.dumps(args, ensure_ascii=False, default=str)
                    if len(a) > 500:
                        a = a[:500] + "..."
                    print(f"  call[{j}] {c.get('name')!r} args={a}")
            print("assistant_text:")
            print(preview or "(empty)")
            print()

    print(sep)
    if review_mode == "summary":
        print("§ Tool trace summary")
    else:
        print("§ Corpus text returned into the tool loop (read_corpus_file / load_context_markdown)")
    print(sep)
    root = corpus_dir.resolve()
    for ti, row in enumerate(d.tool_trace):
        tname = str(row.get("tool", ""))
        if tname not in CORPUS_PATH_TOOL_NAMES:
            print(f"--- tool_trace[{ti}] tool={row.get('tool')!r} (non-corpus-path) ---")
            if review_mode == "summary":
                print(f"output_chars={row.get('output_chars')}")
                if tname == "generate_statblock":
                    ga = row.get("arguments") or {}
                    src = str(ga.get("source_statblock_corpus_path", "") or "").strip()
                    excerpt = str(row.get("output_excerpt") or "")
                    ap = any(excerpt.startswith(p) for p in _GEN_SB_ATTACHED_PREFIXES)
                    print(
                        f"    source_statblock_corpus_path={src!r} "
                        f"output_has_attached_baseline_prefix={ap}"
                    )
            else:
                print(json.dumps(row, indent=2, ensure_ascii=False, default=str)[:2000])
            print()
            continue
        path = str((row.get("arguments") or {}).get("path", "")).strip()
        trace_excerpt = str(row.get("output_excerpt") or "")
        print(f"--- {tname}[{ti}] path={path!r} output_chars={row.get('output_chars')} ---")
        if review_mode == "summary" and tname == "load_context_markdown":
            has_m, _frag = _body_after_load_context_prefix(trace_excerpt)
            print(f"    (stored excerpt shows [context attached:] prefix: {has_m})")
        if review_mode in ("debug", "forensics"):
            print(
                "--- tool_trace output_excerpt (verbatim; planner keeps first 800 chars only in trace) ---"
            )
            if len(trace_excerpt) > 1000 and review_mode == "debug":
                trace_excerpt = trace_excerpt[:1000] + f"\n...[truncated, total {len(trace_excerpt)} chars]..."
            print(trace_excerpt)
        if review_mode == "forensics":
            body = _read_corpus_file_impl(root, path) if path else "(no path)"
            excerpt = (
                body
                if len(body) <= max_retrieved_body_chars
                else body[: max_retrieved_body_chars // 2]
                + f"\n...[truncated at {max_retrieved_body_chars} chars for review print]...\n"
                + body[-(max_retrieved_body_chars // 2) :]
            )
            print(
                "--- replayed file body (full string returned to the model for this path; "
                "same cap as planner read_corpus_file, then optional review truncation) ---"
            )
            print(excerpt)
        print()

    print(sep)
    print("§ Statblock / working-context evidence (tool wire)")
    print(sep)
    for ln in format_context_wiring_lines(d.tool_trace):
        print(ln)

    print(sep)
    print("§ Clarification (tool + turn 0 prose)")
    print(sep)
    for ln in format_clarification_evidence_lines(
        d.tool_trace,
        followup_user_line=run.followup_user_line,
        first_turn_final_text=run.first_turn_final_text,
    ):
        print(ln)

    print(sep)
    print("§ Final LLM answer (last model message text)")
    print(sep)
    print(d.final_text or "(empty)")
    print(sep)

    if run.post_planner_step2_benchmark_detail and review_mode in ("debug", "forensics"):
        print(sep)
        print(
            "§ Step 2 benchmark (observation only; same user_line as agent turn)\n"
            "  intent_from_planner_user_message + mechanical_statblock_reads_in_trace + canonical path"
        )
        print(sep)
        print(json.dumps(run.post_planner_step2_benchmark_detail, indent=2, ensure_ascii=False))
        print()

    if not run.result.passed:
        print("GATE VIOLATIONS:")
        for line in flatten_live_violations(run.result.violations):
            print(line)


def _sanitize_planner_step1_filename_segment(raw: str, *, max_len: int) -> str:
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


def build_planner_step1_primary_artifact_path(
    *,
    scenario_key: str,
    model_id: str,
    gates_passed: bool,
    followup: bool,
    utc: datetime,
    slice_dir: Path | None = None,
    runs_root: Path | None = None,
) -> Path:
    """
    Path for the dated, uniquely named report (parent dirs may not exist yet).

    ``runs_root`` overrides the default ``<slice>/artifacts/runs`` (e.g. env
    ``LYSANDRA_PLANNER_STEP1_RUNS_ROOT`` expanded to an absolute directory).
    """
    root = slice_dir or _SLICE_DIR
    base_runs = runs_root if runs_root is not None else (root / "artifacts" / "runs")
    day = utc.strftime("%Y-%m-%d")
    compact = utc.strftime("%Y%m%dT%H%M%S") + "Z"
    scen = _sanitize_planner_step1_filename_segment(scenario_key, max_len=40)
    mod = _sanitize_planner_step1_filename_segment(model_id, max_len=48)
    gate = "PASS" if gates_passed else "FAIL"
    turns = "2turn" if followup else "1turn"
    fname = f"step1--{scen}--{mod}--{gate}--{turns}--{compact}.md"
    return base_runs / day / fname


def write_planner_step1_run_artifacts(
    markdown_body: str,
    *,
    run: PlannerStep1Run,
    model_id: str,
    slice_dir: Path | None = None,
    runs_root: Path | None = None,
    utc: datetime | None = None,
) -> tuple[Path, Path]:
    """
    Write the review to (1) ``artifacts/runs/<UTC-date>/step1--…``.md`` and (2) the legacy mirror
    ``artifacts/last_planner_step1_run.md``. Returns ``(primary_path, legacy_last_path)``.

    Optional env ``LYSANDRA_PLANNER_STEP1_RUNS_ROOT``: absolute directory under which dated
    day folders are created (default: ``<slice>/artifacts/runs``). The legacy mirror always lives
    under ``<slice>/artifacts/``.
    """
    root = slice_dir or _SLICE_DIR
    when = utc or datetime.now(timezone.utc)
    scenario_key = (run.scenario_key or "unknown").strip() or "unknown"
    followup = bool((run.followup_user_line or "").strip())
    gate_ok = bool(run.result.passed)
    env_runs = os.environ.get("LYSANDRA_PLANNER_STEP1_RUNS_ROOT", "").strip()
    env_root = Path(env_runs).expanduser().resolve() if env_runs else None
    effective_runs = runs_root if runs_root is not None else env_root
    primary = build_planner_step1_primary_artifact_path(
        scenario_key=scenario_key,
        model_id=model_id,
        gates_passed=gate_ok,
        followup=followup,
        utc=when,
        slice_dir=root,
        runs_root=effective_runs,
    )
    legacy = root / "artifacts" / "last_planner_step1_run.md"
    try:
        rel_primary = primary.resolve().relative_to(root.resolve())
    except ValueError:
        rel_primary = Path(primary.name)
    stamp_line = when.strftime("%Y-%m-%dT%H:%M:%SZ")
    header = (
        f"<!-- benchmark_artifact: lysandra_planner_step1 | iso_utc: {stamp_line} "
        f"| scenario: {scenario_key} | model: {model_id} | gates: {'PASS' if gate_ok else 'FAIL'} "
        f"| turns: {'2' if followup else '1'} | primary: {rel_primary.as_posix()} -->\n\n"
    )
    body = header + markdown_body
    primary.parent.mkdir(parents=True, exist_ok=True)
    primary.write_text(body, encoding="utf-8")
    legacy.parent.mkdir(parents=True, exist_ok=True)
    legacy.write_text(body, encoding="utf-8")
    return primary, legacy


def print_planner_step1_review(
    run: PlannerStep1Run,
    *,
    corpus_dir: Path,
    model_id: str,
    review_mode: ReviewMode = "summary",
    max_retrieved_body_chars: int = 36_000,
) -> str:
    """
    Print the human-readable review to stdout and return the same text so callers can
    pass it to ``write_planner_step1_run_artifacts``.
    """
    buf = io.StringIO()
    with contextlib.redirect_stdout(buf):
        _emit_planner_step1_review(
            run,
            corpus_dir=corpus_dir,
            model_id=model_id,
            review_mode=review_mode,
            max_retrieved_body_chars=max_retrieved_body_chars,
        )
    text = buf.getvalue()
    sys.stdout.write(text)
    return text


def main() -> None:
    """
    CLI from repo root (repo root is auto-added to ``sys.path`` when run as a file):

    ``uv run python evals/lysandra_vertical_slice/step1_planner_trace.py``

    Loads ``OPENAI_API_KEY`` from repo ``.env`` / ``.env.development`` (no ``export`` needed).
    Always writes **benchmark artifacts**: a **dated** file under ``artifacts/runs/<UTC-date>/`` with
    the scenario, model, pass/fail, and turn count in the filename, plus a mirror at
    ``artifacts/last_planner_step1_run.md``. Optional ``LYSANDRA_PLANNER_STEP1_RUNS_ROOT`` sets the
    runs root directory (default: ``<slice>/artifacts/runs``).

    Optional: ``PLANNER_LOG_FULL_IO=1``. Optional: ``LYSANDRA_PLANNER_FINAL_OUT=/path/to/file.md`` also writes the
    model's final answer only to that path.

    **Routing:** with both env vars unset, the default benchmark is **upgrade_prose** (natural power-rise /
    CR bump voice). Omit ``LYSANDRA_PLANNER_STEP1_SCENARIO`` and set ``LYSANDRA_PLANNER_USER_MESSAGE`` to
    intent-route **upgrade_prose** vs **autonomous**. To pin a scenario explicitly, set
    ``LYSANDRA_PLANNER_STEP1_SCENARIO=directed|autonomous|stat_check|clarify_cr|upgrade_prose``.
    """
    from openai import OpenAI  # noqa: E402

    from src.agent.planner import _resolve_planner_model  # noqa: E402
    from src.agent.planner_turn_output_schema import planner_turn_output_schema_enabled  # noqa: E402

    load_dungeonmindbuddy_dotenv()
    configure_planner_review_logging()
    if not (_load_api_key() or "").strip():
        print(
            "OPENAI_API_KEY missing after loading .env / .env.development "
            "(see src/bootstrap_env.py). Add the key to repo .env or export it for CI.",
            file=sys.stderr,
        )
        sys.exit(2)
    explicit = os.environ.get(_PLANNER_STEP1_SCENARIO_ENV, "").strip().lower()
    user_msg = os.environ.get("LYSANDRA_PLANNER_USER_MESSAGE", "").strip()
    if explicit in _VALID_PLANNER_STEP1_SCENARIOS:
        print(
            f"[scenario] explicit LYSANDRA_PLANNER_STEP1_SCENARIO={explicit!r} "
            f"(gold: {planner_step1_gold_path(explicit).name})\n",
            file=sys.stderr,
        )
    elif user_msg:
        inferred = scenario_key_for_user_line(user_msg)
        print(
            f"[scenario] intent-routed scenario_key={inferred!r} "
            f"(gold: {planner_step1_gold_path(inferred).name}; from LYSANDRA_PLANNER_USER_MESSAGE)\n",
            file=sys.stderr,
        )
    else:
        print(
            "[scenario] default upgrade_prose — Lysandra power-rise benchmark "
            "(gold may include ``followup_turn`` for a second user line in the same response thread; "
            "set LYSANDRA_PLANNER_STEP1_SCENARIO=autonomous|stat_check|clarify_cr|directed to pin another scenario; "
            "or LYSANDRA_PLANNER_USER_MESSAGE without SCENARIO to intent-route)\n",
            file=sys.stderr,
        )
    review_mode = resolve_review_mode()
    print(
        "[logging] dmb.planner + dmb.planner.live_eval at INFO; "
        "set PLANNER_LOG_FULL_IO=1 for larger bodies inside telemetry JSON lines; "
        f"PLANNER_REVIEW_MODE={review_mode}; "
        f"PLANNER_TURN_OUTPUT_SCHEMA={'on' if planner_turn_output_schema_enabled() else 'off'} "
        "(API-enforced JSON with user_intent + message on planner turns).\n",
        file=sys.stderr,
    )

    root = resolve_corpus_dir()
    if not root.is_dir():
        print(f"corpus missing: {root}", file=sys.stderr)
        sys.exit(2)
    client = OpenAI()
    model_id = _resolve_planner_model(None)
    run = run_planner_step1_turn(
        corpus_dir=root,
        client=client,
        model_id=model_id,
        user_line_override=os.environ.get("LYSANDRA_PLANNER_USER_MESSAGE", "").strip() or None,
    )
    review_text = print_planner_step1_review(
        run,
        corpus_dir=root,
        model_id=model_id,
        review_mode=review_mode,
    )
    primary, legacy = write_planner_step1_run_artifacts(
        review_text, run=run, model_id=model_id
    )
    print(f"[wrote benchmark report to {primary}]", file=sys.stderr)
    print(f"[mirrored latest run to {legacy}]", file=sys.stderr)
    out_path = os.environ.get("LYSANDRA_PLANNER_FINAL_OUT", "").strip()
    if out_path:
        p = Path(out_path).expanduser()
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_text(run.detail.final_text or "", encoding="utf-8")
        print(f"[wrote final answer to {p}]", file=sys.stderr)
    if not run.result.passed:
        sys.exit(1)


if __name__ == "__main__":
    main()
