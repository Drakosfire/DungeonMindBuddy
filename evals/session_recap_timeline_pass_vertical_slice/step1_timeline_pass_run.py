"""Stage-2 v1 vertical slice: planner reads committed Session 20 recap and performs a *timeline pass*
across six pre-loaded NPC/PC timeline files (4 expected appends, 2 expected skips, plus must-flag
hub proposals for prominent NPCs without a hub).

Run (from repo root)::

    export DUNGEONMIND_PLANNER_ALLOW_WRITES=1
    uv run python -m evals.session_recap_timeline_pass_vertical_slice.step1_timeline_pass_run

Cohort::

    PLANNER_REVIEW_MODE=summary uv run python -m \\
      evals.session_recap_timeline_pass_vertical_slice.step1_timeline_pass_run --n 3 --model gpt-5.4-mini

Per-slug chain (six timeline micro-turns + one hub-proposal turn)::

    PLANNER_REVIEW_MODE=summary uv run python -m \\
      evals.session_recap_timeline_pass_vertical_slice.step1_timeline_pass_run --per-slug --n 1 --model gpt-5.4-mini

Pre-state only::

    uv run python -m evals.session_recap_timeline_pass_vertical_slice.step1_timeline_pass_run --print-root
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
from evals.session_recap_timeline_pass_vertical_slice.grader import (  # noqa: E402
    collect_timeline_pass_violations,
    per_gate_verdict,
)
from evals.session_recap_timeline_pass_vertical_slice.step0_pre_state import (  # noqa: E402
    build_pre_state_corpus,
)
from evals.session_recap_timeline_pass_vertical_slice.timeline_pass_run_report import (  # noqa: E402
    TimelinePassRunSummary,
    capture_and_write_timeline_pass_report,
    write_timeline_pass_multi_summary,
)
from src.agent.planner import (  # noqa: E402
    PlanningTurnDetail,
    _planner_tools_responses,
    _resolve_planner_model,
    build_corpus_path_ref_index,
    make_tool_dispatcher,
    merge_planning_turn_details_chain,
    run_planning_turn_detailed,
)
from src.agent.planner_cache import load_or_build_planner_instructions  # noqa: E402
from src.agent.synthesis import _load_api_key  # noqa: E402
from src.bootstrap_env import load_dungeonmindbuddy_dotenv  # noqa: E402

_SLICE_DIR = Path(__file__).resolve().parent
_GOLD_SCENARIO = _SLICE_DIR / "gold" / "timeline_pass_session20.json"
_ALLOW_WRITES_ENV = "DUNGEONMIND_PLANNER_ALLOW_WRITES"

# Appended after cached planner instructions so we do not fork ``corpus_session_planner.py``.
# Same pattern as v0's append-only suffix; longer because the contract has more moving parts.
_TIMELINE_PASS_INSTRUCTION_SUFFIX = """

**Benchmark turn — autonomous timeline pass (Stage 2 v1):** The Session recap file named in the user message **already exists** and is the source of truth. Do **not** call `get_recap_context`, `assemble_recap_draft`, or `build_recap_write_payload`. Do **not** use `write_corpus_file` for the recap or for timeline tables.

For each NPC/PC `timeline.md` listed in the user message: open both the recap and that timeline with `read_corpus_file` (or `load_context_markdown`), decide whether the recap describes a meaningful Session 20 beat for that NPC, and if **yes** call **`append_timeline_row` twice in this same turn** (preview then commit, identical args + the preview's `confirm_token`). The benchmark operator pre-approved every commit — **a preview-only stop is a failure**. Match the existing markdown table format (three columns: session, beat, backticked recap path like prior rows). For PC paths (e.g. `PCs/caelynn/timeline.md`) you **must** pass `timeline_path` explicitly because the slug-only resolver only finds `NPCs/<slug>/timeline.md`.

**Commit checklist (read literally):** After every `append_timeline_row` preview that returns `ok=true phase=preview`, you MUST immediately re-call `append_timeline_row` with the SAME `npc_slug`, `session`, `beat`, `recap_path`, and `timeline_path`, plus `dry_run=false` and the `confirm_token` from the preview, BEFORE responding to the user. A turn that ends with any preview-only call is a failure. The operator has pre-approved every commit in this turn.

If a listed NPC has **no** meaningful Session 20 beat, **skip** them (do not append) and explain the skip briefly in your final `message`.

If an NPC is **prominent** in the recap but **not** present in the supplied list (no `timeline.md` exists yet), surface them as a hub proposal by appending an entry to `unsure_queue` whose `question` starts with the literal prefix `hub-proposal:` — for example, `hub-proposal: karsemine — combat lead and tracker for Lysandra in Session 20` or `hub-proposal: ephanna — Eldritch Blasts vs swarm, Marla intervention, Tealeaf line in Session 20`. The `hub-proposal:` prefix is required and is matched literally; without it the proposal is not counted. Each item also needs `id` like `hub_proposal_<slug>`, a `default_summary` describing what you'd create, and at least two `alternative_summaries`.

Reply with the strict universal `planner_turn_output` JSON schema (`user_intent`, `message`, `unsure_queue` only — no `recap_write` field).

Optional discovery (read-only): you may call `list_npc_hubs` with `npcs_root: Longmont Campaign/Campaign 2/NPCs` and/or `list_pc_hubs` with `pcs_root: Longmont Campaign/Campaign 2/PCs` to list existing campaign hub folders before proposing new hubs.
"""

# Stable slug order matches `gold/timeline_pass_session20.json` user_message list.
_TIMELINE_PASS_SLUG_ORDER: tuple[str, ...] = (
    "captain_lysandra_ironveil",
    "dustwalker",
    "sara_mirathorn_operator",
    "thrin_branchborn",
    "torbin_jove",
    "caelynn",
)

_TIMELINE_PASS_PER_SLUG_INSTRUCTION_SUFFIX = """

**Benchmark micro-turn — autonomous timeline pass (Stage 2 v1, single subject):** The Session recap path appears in the user message. This micro-turn covers **one** `timeline.md` only — do not call `append_timeline_row` for any other slug here.

If the recap describes a **meaningful Session 20 beat for that subject only**, call **`append_timeline_row` twice in this micro-turn** (preview then commit, identical args + the preview's `confirm_token`). **A preview-only stop when an append is warranted is a failure.** Match the existing markdown table format. For PC paths, pass `timeline_path` explicitly.

**Commit checklist (read literally):** After every `append_timeline_row` preview that returns `ok=true phase=preview`, you MUST immediately re-call `append_timeline_row` with the SAME `npc_slug`, `session`, `beat`, `recap_path`, `timeline_path`, plus `dry_run=false` and the `confirm_token` from the preview, BEFORE emitting your final JSON for this micro-turn. Do **not** paste the token into `message` and ask a human to apply — the benchmark operator pre-approved every commit; you must issue the commit tool call yourself in this same micro-turn.

If there is **no** meaningful Session 20 beat for this subject, **skip** the append and say so briefly in your final `message`.

Do **not** call `assemble_recap_draft`, `build_recap_write_payload`, `get_recap_context`, or `write_corpus_file`. Optional: `list_npc_hubs` / `list_pc_hubs` on `Longmont Campaign/Campaign 2/NPCs` and `Longmont Campaign/Campaign 2/PCs`.

Reply with `planner_turn_output` JSON (`user_intent`, `message`, `unsure_queue` only — use `unsure_queue: []` or `null` on slug micro-turns).
"""

_TIMELINE_PASS_HUB_ONLY_INSTRUCTION_SUFFIX = """

**Benchmark micro-turn — hub proposals only (Stage 2 v1):** The recap path appears in the user message. Do **not** call `append_timeline_row` or `write_corpus_file`. Do **not** call `assemble_recap_draft`, `build_recap_write_payload`, or `get_recap_context`.

For NPCs **prominent** in the recap who **do not** have a timeline file among the six paths already handled in prior micro-turns (`captain_lysandra_ironveil`, `dustwalker`, `sara_mirathorn_operator`, `thrin_branchborn`, `torbin_jove`, `caelynn` under `Longmont Campaign/Campaign 2/`), surface them in `unsure_queue` with each `question` starting with the literal prefix `hub-proposal:` (required for grading). Each item needs `id` like `hub_proposal_<slug>`, `default_summary`, and at least two `alternative_summaries`.

Optional: call `list_npc_hubs` / `list_pc_hubs` on `Longmont Campaign/Campaign 2/NPCs` and `Longmont Campaign/Campaign 2/PCs` to see which campaign hubs already exist.

Reply with `planner_turn_output` JSON only (`user_intent`, `message`, `unsure_queue`).
"""


def ordered_timeline_targets(grading: dict[str, Any]) -> list[dict[str, Any]]:
    """Return append+skip specs in gold scenario order (six slugs)."""
    by_slug: dict[str, dict[str, Any]] = {}
    for spec in grading.get("expected_appends") or []:
        slug = str(spec.get("npc_slug", "") or "").strip()
        if slug:
            by_slug[slug] = dict(spec)
    for spec in grading.get("expected_skips") or []:
        slug = str(spec.get("npc_slug", "") or "").strip()
        if slug:
            by_slug.setdefault(slug, dict(spec))
    out: list[dict[str, Any]] = []
    for slug in _TIMELINE_PASS_SLUG_ORDER:
        if slug in by_slug:
            out.append(by_slug[slug])
    return out


def recap_relative_path_from_grading(grading: dict[str, Any]) -> str:
    fn = str(grading.get("recap_filename") or "Session 20 - Recap.md").strip()
    return f"Longmont Campaign/Campaign 2/Session Recaps/{fn}"


def build_per_slug_user_message(recap_rel: str, slug: str, timeline_rel: str) -> str:
    return (
        f"**Timeline-pass micro-turn:** Recap (source of truth): `{recap_rel}`.\n\n"
        f"Consider **only** `{timeline_rel}` (`npc_slug` `{slug}`).\n\n"
        "Decide whether Session 20 gives this character a meaningful beat; if yes, append one row "
        "via the two-phase `append_timeline_row` contract described in system instructions."
    )


def build_hub_proposal_user_message(recap_rel: str) -> str:
    return (
        f"**Hub-proposal micro-turn:** Recap: `{recap_rel}`.\n\n"
        "Emit `hub-proposal:` `unsure_queue` entries for prominent NPCs from the recap who are **not** "
        "among the six slugs already covered in prior micro-turns (see system instructions). "
        "Do not append timelines in this micro-turn."
    )


def load_scenario(path: Path | None = None) -> dict[str, Any]:
    p = (path or _GOLD_SCENARIO).expanduser().resolve()
    if not p.is_file():
        raise FileNotFoundError(f"missing scenario: {p}")
    return json.loads(p.read_text(encoding="utf-8"))


def run_timeline_pass_turn(
    *,
    corpus_dir: Path,
    client: Any,
    model_id: str,
    cache_root: Path | None = None,
    scenario: dict[str, Any] | None = None,
    allow_corpus_writes: bool = True,
) -> tuple[PlannerStep1Run, dict[str, Any], dict[str, str]]:
    sc = scenario or load_scenario()
    sid = fixture_scenario_id(sc)
    corpus_path = corpus_dir.resolve()

    user_message, input_violations = resolve_planner_user_message(sc, corpus_path)

    if input_violations:
        return (
            _empty_fail(sid, {"input": input_violations}, user_line=user_message),
            {},
            {},
        )
    if not user_message.strip():
        return (
            _empty_fail(sid, {"input": [f"[{sid}] empty user message"]}, user_line=""),
            {},
            {},
        )

    instructions, fp = load_or_build_planner_instructions(
        corpus_path,
        cache_root=cache_root,
        include_write_tools=allow_corpus_writes,
    )
    instructions = f"{instructions.rstrip()}{_TIMELINE_PASS_INSTRUCTION_SUFFIX}"

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
            "suite": "session_recap_timeline_pass_vertical_slice",
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
    gviol, gtelemetry = collect_timeline_pass_violations(
        corpus_dir=corpus_path,
        tool_trace=list(detail.tool_trace or []),
        final_text=str(detail.final_text or ""),
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

    run = PlannerStep1Run(
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
    verdict = per_gate_verdict(merged_violations)
    return run, gtelemetry, verdict


def run_timeline_pass_per_slug_chain(
    *,
    corpus_dir: Path,
    client: Any,
    model_id: str,
    cache_root: Path | None = None,
    scenario: dict[str, Any] | None = None,
    allow_corpus_writes: bool = True,
) -> tuple[PlannerStep1Run, dict[str, Any], dict[str, str]]:
    """Seven chained Responses turns: six single-subject timeline micro-turns + one hub-proposal turn."""
    sc = scenario or load_scenario()
    sid = fixture_scenario_id(sc)
    corpus_path = corpus_dir.resolve()
    grading = sc.get("grading") if isinstance(sc.get("grading"), dict) else {}
    targets = ordered_timeline_targets(grading)
    recap_rel = recap_relative_path_from_grading(grading)

    _user_message, input_violations = resolve_planner_user_message(sc, corpus_path)
    if input_violations:
        return (
            _empty_fail(sid, {"input": input_violations}, user_line="[per_slug_chain]"),
            {},
            {},
        )

    instructions_base, fp = load_or_build_planner_instructions(
        corpus_path,
        cache_root=cache_root,
        include_write_tools=allow_corpus_writes,
    )
    inst_slug = f"{instructions_base.rstrip()}{_TIMELINE_PASS_PER_SLUG_INSTRUCTION_SUFFIX}"
    inst_hub = f"{instructions_base.rstrip()}{_TIMELINE_PASS_HUB_ONLY_INSTRUCTION_SUFFIX}"

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

    details: list[PlanningTurnDetail] = []
    prev_rid: str | None = None
    for i, spec in enumerate(targets):
        slug = str(spec.get("npc_slug", "") or "").strip()
        rel = str(spec.get("timeline_relative_path", "") or "").strip()
        if not slug or not rel:
            return (
                _empty_fail(
                    sid,
                    {"input": [f"[{sid}] per_slug_chain missing slug or path in spec {spec!r}"]},
                    user_line="[per_slug_chain]",
                ),
                {},
                {},
            )
        user_line = build_per_slug_user_message(recap_rel, slug, rel)
        detail = run_planning_turn_detailed(
            client=client,
            model_id=model_id,
            instructions=inst_slug,
            tools=tools,
            corpus_path=corpus_path,
            user_line=user_line,
            previous_response_id=prev_rid,
            dispatch_tool=dispatch,
            telemetry_context={
                "scenario_id": sid,
                "suite": "session_recap_timeline_pass_vertical_slice",
                "corpus_fingerprint": fp,
                "turn_index": i,
                "per_slug_chain": True,
                "per_slug_phase": "timeline_row",
                "per_slug": slug,
            },
            corpus_path_ref_index=ref_index,
            active_skill_id=None,
        )
        details.append(detail)
        prev_rid = detail.last_response_id

    hub_user = build_hub_proposal_user_message(recap_rel)
    detail_hub = run_planning_turn_detailed(
        client=client,
        model_id=model_id,
        instructions=inst_hub,
        tools=tools,
        corpus_path=corpus_path,
        user_line=hub_user,
        previous_response_id=prev_rid,
        dispatch_tool=dispatch,
        telemetry_context={
            "scenario_id": sid,
            "suite": "session_recap_timeline_pass_vertical_slice",
            "corpus_fingerprint": fp,
            "turn_index": len(targets),
            "per_slug_chain": True,
            "per_slug_phase": "hub_proposals",
        },
        corpus_path_ref_index=ref_index,
        active_skill_id=None,
    )
    details.append(detail_hub)

    detail = merge_planning_turn_details_chain(details)

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
    grading_dict = sc.get("grading") or {}
    gviol, gtelemetry = collect_timeline_pass_violations(
        corpus_dir=corpus_path,
        tool_trace=list(detail.tool_trace or []),
        final_text=str(detail.final_text or ""),
        grading=grading_dict if isinstance(grading_dict, dict) else {},
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

    combined_instructions = (
        f"{instructions_base.rstrip()}\n\n"
        f"[per_slug_chain artifact: {len(targets)} timeline micro-turns + 1 hub-proposal micro-turn; "
        "suffixes _TIMELINE_PASS_PER_SLUG_INSTRUCTION_SUFFIX + _TIMELINE_PASS_HUB_ONLY_INSTRUCTION_SUFFIX]"
    )
    run = PlannerStep1Run(
        detail=detail,
        result=final_result,
        instructions=combined_instructions,
        user_line=f"[per_slug_chain x{len(details)}] {recap_rel}",
        corpus_fingerprint=fp,
        post_planner_step2_benchmark_detail=None,
        scenario_key=sid,
        followup_user_line="",
        first_turn_final_text="",
    )
    verdict = per_gate_verdict(merged_violations)
    gtelemetry = dict(gtelemetry or {})
    gtelemetry["per_slug_chain_turns"] = len(details)
    return run, gtelemetry, verdict


def _tool_trace_signature(tool_trace: list[dict[str, Any]]) -> str:
    return ",".join(str(row.get("tool", "") or "") for row in tool_trace)


def print_timeline_pass_review(
    run: PlannerStep1Run,
    *,
    corpus_dir: Path,
    model_id: str,
    review_mode: str = "summary",
    grader_telemetry: dict[str, Any] | None = None,
    per_gate_verdict_map: dict[str, str] | None = None,
) -> None:
    _ = corpus_dir, model_id, review_mode
    print(f"scenario_id={run.result.scenario_id} gates_passed={run.result.passed}")
    if per_gate_verdict_map:
        verdict_str = " ".join(f"{k}={v}" for k, v in sorted(per_gate_verdict_map.items()))
        print(f"per_gate: {verdict_str}")
    if grader_telemetry:
        print(
            "telemetry: "
            + json.dumps(grader_telemetry, ensure_ascii=False, sort_keys=True, default=str)
        )
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
    parser = argparse.ArgumentParser(description="Stage-2 v1 autonomous timeline-pass benchmark")
    parser.add_argument("--print-root", action="store_true", help="Build pre-state corpus and print root path")
    parser.add_argument("--tmp-parent", type=Path, default=None)
    parser.add_argument("--live-corpus", action="store_true", help="Use live repo corpus (debug only)")
    parser.add_argument("--scenario-json", type=Path, default=None)
    parser.add_argument("--model", type=str, default="")
    parser.add_argument("--n", type=int, default=1)
    parser.add_argument(
        "--per-slug",
        action="store_true",
        help=(
            "Chain seven Responses turns: one micro-turn per listed slug (preview→commit when warranted) "
            "plus a final hub-proposal-only micro-turn. Artifact filenames use `--7turn--`."
        ),
    )
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
            f"[timeline-pass] n={n} per_slug={bool(args.per_slug)} allow_writes={allow_writes} "
            f"PLANNER_REVIEW_MODE={review_mode}",
            file=sys.stderr,
        )

    from openai import OpenAI  # noqa: E402

    client = OpenAI()
    model_id = _resolve_planner_model(args.model.strip() or None)

    summaries: list[TimelinePassRunSummary] = []
    total_cost = 0.0
    pass_count = 0
    scenario_id_for_summary = fixture_scenario_id(gold)

    for i in range(n):
        corpus_root = _build_corpus(i)
        if not args.quiet:
            print(f"[timeline-pass] run {i + 1}/{n} corpus_dir={corpus_root}", file=sys.stderr)
        t0 = time.monotonic()
        if args.per_slug:
            run, telemetry, verdict = run_timeline_pass_per_slug_chain(
                corpus_dir=corpus_root,
                client=client,
                model_id=model_id,
                scenario=gold,
                allow_corpus_writes=allow_writes,
            )
        else:
            run, telemetry, verdict = run_timeline_pass_turn(
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
                f"[timeline-pass] run {i + 1} done in {elapsed_s}s cost_usd={cost:.4f} "
                f"passed={run.result.passed} per_gate={verdict}",
                file=sys.stderr,
            )

        paths, summary = capture_and_write_timeline_pass_report(
            print_callable=print_timeline_pass_review,
            print_kwargs={
                "run": run,
                "corpus_dir": corpus_root,
                "model_id": model_id,
                "review_mode": review_mode,
                "grader_telemetry": telemetry,
                "per_gate_verdict_map": verdict,
            },
            run=run,
            corpus_dir=corpus_root,
            model_id=model_id,
            scenario=gold,
            runs_root=args.runs_root,
            run_index=i if n > 1 else None,
            cohort_size=n if n > 1 else None,
            grader_telemetry=telemetry,
            per_gate_verdict=verdict,
            artifact_turn_pack="7turn" if args.per_slug else "1turn",
        )
        summaries.append(summary)
        if not args.quiet:
            print(f"[timeline-pass] report: {paths.primary_md}", file=sys.stderr)
            print(f"[timeline-pass] sidecar: {paths.sidecar_json}", file=sys.stderr)

        # Budget guard: bumped to $1.50 early-stop floor (pass_count<=1 trigger) and
        # $3.00 hard cap warning per slice spec (4 appends per run, higher per-run cost).
        if total_cost > 1.5 and pass_count <= 1 and i + 1 < n:
            print(
                f"[timeline-pass] STOP: cumulative cost ${total_cost:.2f} with only {pass_count} pass(es); "
                "skipping remaining cohort runs per budget guard.",
                file=sys.stderr,
            )
            break

    if total_cost > 3.0:
        print(
            f"[timeline-pass] WARNING: cumulative cost ${total_cost:.2f} exceeded $3.00 cap.",
            file=sys.stderr,
        )

    if n > 1 and summaries:
        md_s, json_s = write_timeline_pass_multi_summary(
            summaries,
            model_id=model_id,
            scenario_id=scenario_id_for_summary,
            runs_root=args.runs_root,
        )
        if not args.quiet:
            print(f"[timeline-pass] cohort summary: {md_s}", file=sys.stderr)
            print(f"[timeline-pass] cohort sidecar: {json_s}", file=sys.stderr)

    if summaries and not all(s.gates_passed for s in summaries):
        sys.exit(1)


if __name__ == "__main__":
    main()
