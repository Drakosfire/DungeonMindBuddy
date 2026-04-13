"""Step 1 Lane A — planner ``tool_trace`` gates (Lysandra vertical slice).

Two gold scenarios: **directed** (user names files) vs **autonomous** (human-style ask;
default via ``LYSANDRA_PLANNER_STEP1_SCENARIO``). See ``gold/planner_step1_*.json``.

Reuses ``evals.planner_slice.live_eval`` scenario shape and matchers.

**Review / logging**

- Enable JSON telemetry on stderr: INFO for loggers ``dmb.planner`` and ``dmb.planner.live_eval``
  (``configure_planner_review_logging()`` from ``main()``).
- Larger bodies inside telemetry JSON lines: ``PLANNER_LOG_FULL_IO=1``.
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

import json  # noqa: E402
import logging  # noqa: E402
import os  # noqa: E402
from dataclasses import dataclass, replace  # noqa: E402
from typing import Any  # noqa: E402

from evals.lysandra_vertical_slice.step0_corpus_environment import resolve_corpus_dir  # noqa: E402
from src.bootstrap_env import load_dungeonmindbuddy_dotenv  # noqa: E402
from evals.planner_slice.live_eval import (  # noqa: E402
    LiveEvalResult,
    evaluate_scenario_detail,
    resolve_planner_user_message,
)
from src.agent.planner import (  # noqa: E402
    PlanningTurnDetail,
    _planner_tools_responses,
    _read_corpus_file_impl,
    make_tool_dispatcher,
    run_planning_turn_detailed,
)
from src.agent.planner_cache import load_or_build_planner_instructions  # noqa: E402
from src.agent.planner_telemetry import text_sig  # noqa: E402

_SLICE_DIR = Path(__file__).resolve().parent

_PLANNER_STEP1_SCENARIO_ENV = "LYSANDRA_PLANNER_STEP1_SCENARIO"
_VALID_PLANNER_STEP1_SCENARIOS = frozenset({"directed", "autonomous"})


def default_planner_step1_scenario_key() -> str:
    """``directed`` = path-spelled user ask; ``autonomous`` = human-style ask (default)."""
    raw = os.environ.get(_PLANNER_STEP1_SCENARIO_ENV, "autonomous").strip().lower()
    return raw if raw in _VALID_PLANNER_STEP1_SCENARIOS else "autonomous"


def planner_step1_gold_path(scenario_key: str | None = None) -> Path:
    key = scenario_key if scenario_key is not None else default_planner_step1_scenario_key()
    if key not in _VALID_PLANNER_STEP1_SCENARIOS:
        key = "autonomous"
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


@dataclass
class PlannerStep1Run:
    detail: PlanningTurnDetail
    result: LiveEvalResult
    instructions: str
    user_line: str
    corpus_fingerprint: str


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
    )


def run_planner_step1_turn(
    *,
    corpus_dir: Path,
    client: Any,
    model_id: str,
    cache_root: Path | None = None,
    scenario: dict[str, Any] | None = None,
    scenario_key: str | None = None,
) -> PlannerStep1Run:
    """
    One ``run_planning_turn_detailed`` with the Lane A fixture; score with ``evaluate_scenario_detail``.

    **Scenarios** (see ``gold/planner_step1_directed.json`` vs ``planner_step1_autonomous.json``):

    - ``directed`` — user message names folders/filenames to open (strong smoke, not autonomy).
    - ``autonomous`` — human-style ask; gates require statblock ``.md``, dossier, and some C2 recap.

    Pick with env ``LYSANDRA_PLANNER_STEP1_SCENARIO=directed|autonomous`` (default **autonomous**),
    or pass ``scenario_key``, or pass a full ``scenario`` dict.

    Loads ``.env`` / ``.env.development`` via ``load_dungeonmindbuddy_dotenv()`` so
    ``OPENAI_API_KEY`` does not require shell ``export``.
    """
    load_dungeonmindbuddy_dotenv()
    if scenario is not None:
        sc = scenario
    elif scenario_key is not None:
        sc = load_planner_step1_scenario(scenario_key)
    else:
        sc = load_planner_step1_scenario()
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
        },
    )
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
    return PlannerStep1Run(
        detail=detail,
        result=result,
        instructions=instructions,
        user_line=user_message,
        corpus_fingerprint=fp,
    )


def flatten_live_violations(violations: dict[str, list[str]]) -> list[str]:
    lines: list[str] = []
    for key, rows in sorted(violations.items()):
        for r in rows:
            lines.append(f"{key}: {r}")
    return lines


def print_planner_step1_review(
    run: PlannerStep1Run,
    *,
    corpus_dir: Path,
    model_id: str,
    max_retrieved_body_chars: int = 36_000,
) -> None:
    """Stdout report: turns, token usage per API round, retrieved corpus bodies, final answer."""
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
    print(f"model_id:         {model_id}")
    print(f"gates_passed:     {run.result.passed}")
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
            f"  round[{i}] phase={row.get('phase')!r} "
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

    print(sep)
    print("§ Planner steps (assistant message + tool calls proposed that step)")
    print(sep)
    for rec in d.steps:
        calls = rec.function_calls
        names = [str(c.get("name", "")) for c in calls]
        preview = (rec.assistant_text or "").strip()
        if len(preview) > 6000:
            preview = preview[:3000] + f"\n...[truncated, total {len(rec.assistant_text)} chars]...\n" + preview[-2000:]
        print(f"--- step_index={rec.step_index} response_id={rec.response_id!r} ---")
        print(f"function_calls: {names}")
        for j, c in enumerate(calls):
            args = c.get("arguments") or {}
            if str(c.get("name")) == "read_corpus_file":
                print(f"  call[{j}] read_corpus_file path={args.get('path')!r}")
            else:
                a = json.dumps(args, ensure_ascii=False, default=str)
                if len(a) > 500:
                    a = a[:500] + "..."
                print(f"  call[{j}] {c.get('name')!r} args={a}")
        print("assistant_text:")
        print(preview or "(empty)")
        print()

    print(sep)
    print("§ Corpus text returned into the tool loop (same truncation as planner read_corpus_file)")
    print(sep)
    root = corpus_dir.resolve()
    for ti, row in enumerate(d.tool_trace):
        if str(row.get("tool", "")) != "read_corpus_file":
            print(f"--- tool_trace[{ti}] tool={row.get('tool')!r} (non-read) ---")
            print(json.dumps(row, indent=2, ensure_ascii=False, default=str)[:4000])
            print()
            continue
        path = str((row.get("arguments") or {}).get("path", "")).strip()
        body = _read_corpus_file_impl(root, path) if path else "(no path)"
        excerpt = body if len(body) <= max_retrieved_body_chars else body[: max_retrieved_body_chars // 2] + f"\n...[truncated at {max_retrieved_body_chars} chars for review print]...\n" + body[-(max_retrieved_body_chars // 2) :]
        trace_excerpt = str(row.get("output_excerpt") or "")
        print(f"--- read_corpus_file[{ti}] path={path!r} output_chars={row.get('output_chars')} ---")
        print(
            "--- tool_trace output_excerpt (verbatim; planner keeps first 800 chars only in trace) ---"
        )
        print(trace_excerpt)
        print(
            "--- replayed file body (full string returned to the model for this path; "
            "same cap as planner read_corpus_file, then optional review truncation) ---"
        )
        print(excerpt)
        print()

    print(sep)
    print("§ Final LLM answer (last model message text)")
    print(sep)
    print(d.final_text or "(empty)")
    print(sep)

    if not run.result.passed:
        print("GATE VIOLATIONS:")
        for line in flatten_live_violations(run.result.violations):
            print(line)


def main() -> None:
    """
    CLI from repo root (repo root is auto-added to ``sys.path`` when run as a file):

    ``uv run python evals/lysandra_vertical_slice/step1_planner_trace.py``

    Loads ``OPENAI_API_KEY`` from repo ``.env`` / ``.env.development`` (no ``export`` needed).
    Optional: ``PLANNER_LOG_FULL_IO=1``.
    """
    import os
    import sys

    from openai import OpenAI  # noqa: E402

    from src.agent.planner import _resolve_planner_model  # noqa: E402

    load_dungeonmindbuddy_dotenv()
    configure_planner_review_logging()
    sk = default_planner_step1_scenario_key()
    print(
        f"[scenario] LYSANDRA_PLANNER_STEP1_SCENARIO={sk!r} (gold: {planner_step1_gold_path(sk).name})\n",
        file=sys.stderr,
    )
    print(
        "[logging] dmb.planner + dmb.planner.live_eval at INFO; "
        "set PLANNER_LOG_FULL_IO=1 for larger bodies inside telemetry JSON lines.\n",
        file=sys.stderr,
    )

    if not os.environ.get("OPENAI_API_KEY", "").strip():
        print(
            "OPENAI_API_KEY missing after loading .env / .env.development "
            "(see src/bootstrap_env.py). Add the key to repo .env or export it for CI.",
            file=sys.stderr,
        )
        sys.exit(2)
    root = resolve_corpus_dir()
    if not root.is_dir():
        print(f"corpus missing: {root}", file=sys.stderr)
        sys.exit(2)
    client = OpenAI()
    model_id = _resolve_planner_model(None)
    run = run_planner_step1_turn(corpus_dir=root, client=client, model_id=model_id)
    print_planner_step1_review(run, corpus_dir=root, model_id=model_id)
    if not run.result.passed:
        sys.exit(1)


if __name__ == "__main__":
    main()
