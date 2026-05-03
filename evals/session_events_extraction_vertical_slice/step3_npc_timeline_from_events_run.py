"""NPC-only events-to-timeline append slice (timeline-first attachment).

Chains recap-to-events (Stage A) into per-NPC micro-turns that may call
``append_timeline_row`` for ``NPCs/<slug>/timeline.md`` targets only. PCs are out
of scope — grading is filtered to NPC ``expected_appends`` / ``expected_skips`` /
``allowed_npc_slugs`` so TP1–TP5 never score PC behavior.

Unlike the PC-only ``step2_timeline_from_events_run``, NPC **skip** targets may
still receive extracted events as incidental participants; the model must not
append when this turn is marked as a skip target.

Run (from repo root)::

    DUNGEONMIND_PLANNER_ALLOW_WRITES=1 uv run python -m \\
      evals.session_events_extraction_vertical_slice.step3_npc_timeline_from_events_run \\
      --n 5 --model gpt-5.4-mini

Defaults match step2 (Session 20 Stage A gold + timeline_pass_session20 grading).
"""

from __future__ import annotations

import argparse
import json
import os
import statistics
import sys
import time
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

_REPO_ROOT = Path(__file__).resolve().parents[2]
if str(_REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(_REPO_ROOT))

from src.agent.planner import (  # noqa: E402
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

from evals.session_events_extraction_vertical_slice.step1_session_events_run import (  # noqa: E402
    load_scenario as load_stage_a_scenario,
    resolve_corpus_root,
    run_session_events_extraction,
)
from evals.session_events_extraction_vertical_slice.step2_timeline_from_events_run import (  # noqa: E402
    Step2RunSummary,
    _extract_beat_for_slug,
    _recap_evidence_path_from_stage_b_gold,
    _resolve_pre_state_manifest_dict,
    _session_int_from_stage_b_gold,
    filter_events_for_slug,
    ordered_stage_b_timeline_targets,
)
from evals.session_recap_timeline_pass_vertical_slice.grader import (  # noqa: E402
    collect_timeline_pass_violations,
    per_gate_verdict as tp_per_gate_verdict,
)
from evals.session_recap_timeline_pass_vertical_slice.step0_pre_state import (  # noqa: E402
    build_pre_state_corpus,
)

_SLICE_DIR = Path(__file__).resolve().parent
_STAGE_A_GOLD_DEFAULT = _SLICE_DIR / "gold" / "session_events_session20.json"
_TIMELINE_PASS_SLICE_DIR = _REPO_ROOT / "evals" / "session_recap_timeline_pass_vertical_slice"
_TIMELINE_GOLD_DEFAULT = _TIMELINE_PASS_SLICE_DIR / "gold" / "timeline_pass_session20.json"
_ALLOW_WRITES_ENV = "DUNGEONMIND_PLANNER_ALLOW_WRITES"
_RECAP_TO_EVENTS_LABEL = "recap_to_events_extraction"
_NPC_EVENTS_TO_TIMELINE_LABEL = "npc_events_to_timeline_append"


def _is_npc_target(spec: dict[str, Any]) -> bool:
    rel = str(spec.get("timeline_relative_path", "") or "")
    return "/NPCs/" in rel


def _filter_grading_to_npcs(grading: dict[str, Any]) -> dict[str, Any]:
    """Restrict timeline-pass grading to NPC hub paths only."""
    out = dict(grading)
    out["expected_appends"] = [s for s in (grading.get("expected_appends") or []) if _is_npc_target(s)]
    out["expected_skips"] = [s for s in (grading.get("expected_skips") or []) if _is_npc_target(s)]
    npc_slugs: set[str] = set()
    for s in out["expected_appends"] + out["expected_skips"]:
        slug = str(s.get("npc_slug") or "").strip()
        if slug:
            npc_slugs.add(slug)
    if "allowed_npc_slugs" in grading:
        out["allowed_npc_slugs"] = [s for s in (grading.get("allowed_npc_slugs") or []) if s in npc_slugs]
    return out


def _expected_skip_slugs(grading: dict[str, Any]) -> set[str]:
    return {
        str(s.get("npc_slug") or "").strip()
        for s in (grading.get("expected_skips") or [])
        if str(s.get("npc_slug") or "").strip()
    }


def ordered_npc_timeline_targets(grading: dict[str, Any]) -> list[dict[str, Any]]:
    return [t for t in ordered_stage_b_timeline_targets(grading) if _is_npc_target(t)]


def build_npc_stage_b_instruction_suffix(*, session_num: int, recap_evidence_path: str) -> str:
    tick = recap_evidence_path.strip()
    return f"""

**Benchmark micro-turn — NPC timeline from events (NPC-only slice):** Each user message \
labels the turn as **APPEND** or **SKIP** for one NPC slug. The structured events JSON \
(if present) is your only source about Session {session_num}; **do not** call \
`read_corpus_file`, `load_context_markdown`, `get_recap_context`, \
`assemble_recap_draft`, `build_recap_write_payload`, or `write_corpus_file`.

**APPEND turns:** When the user message says **NPC timeline APPEND**, this NPC is an \
**expected_append** target. If there are events for this slug, compose **one** searchable \
timeline beat and call `append_timeline_row` **exactly once** with `` `{tick}` `` as the \
evidence path (three-column table row: session | beat | path). Preserve distinctive proper \
names and vocabulary from the events (places, spells, other NPCs). Multi-event turns compose \
into one sentence.

**SKIP turns:** When the user message says **NPC timeline SKIP**, this NPC is an \
**expected_skip** target for this benchmark. **Do not** call `append_timeline_row`, even \
if the events JSON lists incidental participation — gold expects **no** Session \
{session_num} row for this slug. Reply with `planner_turn_output` JSON only \
(`user_intent`, `message`, `unsure_queue: []`) explaining that you are skipping.

**Session number:** For APPEND turns, pass ``session={session_num}`` to ``append_timeline_row``.

Allowed tools: `append_timeline_row`, `list_npc_hubs`.
Forbidden tools: `read_corpus_file`, `load_context_markdown`, `get_recap_context`, \
`assemble_recap_draft`, `build_recap_write_payload`, `write_corpus_file`.

Reply with `planner_turn_output` JSON (`user_intent`, `message`, `unsure_queue: []`).
"""


def build_npc_append_user_message(
    timeline_rel: str,
    slug: str,
    slug_events: list[dict[str, Any]],
    *,
    session_num: int,
) -> str:
    events_json = json.dumps(slug_events, indent=2, ensure_ascii=False)
    return (
        f"**NPC timeline APPEND micro-turn (events-driven):** Consider only `{timeline_rel}` "
        f"(`npc_slug` `{slug}`).\n\n"
        f"The following structured events from Session {session_num} mention this NPC:\n\n"
        f"```json\n{events_json}\n```\n\n"
        "Call `append_timeline_row` **once** with a beat sentence that composes these events "
        "into one timeline row. Retain distinctive named terms from the events — places, "
        "spells, items, and proper names."
    )


def build_npc_skip_user_message(
    timeline_rel: str,
    slug: str,
    slug_events: list[dict[str, Any]],
    *,
    session_num: int,
) -> str:
    if slug_events:
        events_json = json.dumps(slug_events, indent=2, ensure_ascii=False)
        events_block = (
            f"The extractor attached events mentioning this slug (possibly incidental); "
            f"**you must still SKIP** — no `append_timeline_row` call:\n\n"
            f"```json\n{events_json}\n```\n\n"
        )
    else:
        events_block = "The extractor produced **no** events for this slug.\n\n"
    return (
        f"**NPC timeline SKIP micro-turn:** Consider only `{timeline_rel}` "
        f"(`npc_slug` `{slug}`).\n\n"
        f"{events_block}"
        f"Benchmark gold expects **no** Session {session_num} timeline row for this NPC. "
        "Do **not** call `append_timeline_row`. Reply with `planner_turn_output` only."
    )


def run_stage_b_npc_events_driven_chain(
    *,
    corpus_dir: Path,
    client: Any,
    model_id: str,
    stage_b_scenario: dict[str, Any],
    stage_a_events: list[dict[str, Any]],
    allow_corpus_writes: bool = True,
    quiet: bool = False,
) -> tuple[list[dict[str, Any]], str, float, dict[str, bool], dict[str, dict[str, Any]]]:
    grading_full = stage_b_scenario.get("grading") or {}
    grading_npc = _filter_grading_to_npcs(grading_full)
    skip_slugs = _expected_skip_slugs(grading_npc)
    targets = ordered_npc_timeline_targets(grading_npc)

    session_num = _session_int_from_stage_b_gold(stage_b_scenario)
    recap_evidence = _recap_evidence_path_from_stage_b_gold(stage_b_scenario)
    instr_suffix = build_npc_stage_b_instruction_suffix(
        session_num=session_num,
        recap_evidence_path=recap_evidence,
    )

    instructions_base, fp = load_or_build_planner_instructions(
        corpus_dir,
        cache_root=None,
        include_write_tools=allow_corpus_writes,
    )
    inst_stage_b = f"{instructions_base.rstrip()}{instr_suffix}"

    tools = _planner_tools_responses(
        include_write_tools=allow_corpus_writes,
        autonomous_writes=allow_corpus_writes,
    )
    tool_cost_sink: list[dict[str, Any]] = []
    ref_index = build_corpus_path_ref_index(corpus_dir)
    dispatch = make_tool_dispatcher(
        corpus_dir,
        client,
        model_id,
        statblock_stub=None,
        tool_cost_sink=tool_cost_sink,
        corpus_path_ref_index=ref_index,
        allow_corpus_writes=allow_corpus_writes,
        autonomous_writes=allow_corpus_writes,
    )

    all_details = []
    combined_final_text_parts: list[str] = []
    per_slug_no_event_skip: dict[str, bool] = {}
    per_slug_diagnostics: dict[str, dict[str, Any]] = {}
    slug_turn_idx = 0

    for spec in targets:
        slug = str(spec.get("npc_slug", "") or "").strip()
        rel = str(spec.get("timeline_relative_path", "") or "").strip()
        if not slug or not rel:
            continue

        slug_events = filter_events_for_slug(stage_a_events, slug)
        is_skip = slug in skip_slugs

        if is_skip:
            if not slug_events:
                per_slug_no_event_skip[slug] = True
                per_slug_diagnostics[slug] = {
                    "slug_events_sent": [],
                    "slug_beat_written": None,
                    "slug_model_message": None,
                    "expected_skip": True,
                    "model_invoked": False,
                }
                if not quiet:
                    print(
                        f"[step3-npc] slug={slug} expected_skip no-event (no model call)",
                        file=sys.stderr,
                    )
                continue
            user_line = build_npc_skip_user_message(
                rel, slug, slug_events, session_num=session_num
            )
        else:
            if not slug_events:
                per_slug_no_event_skip[slug] = True
                per_slug_diagnostics[slug] = {
                    "slug_events_sent": [],
                    "slug_beat_written": None,
                    "slug_model_message": None,
                    "expected_skip": False,
                    "model_invoked": False,
                }
                if not quiet:
                    print(
                        f"[step3-npc] slug={slug} expected_append no-event skip "
                        "(recall_to_events produced 0 events)",
                        file=sys.stderr,
                    )
                continue
            user_line = build_npc_append_user_message(
                rel, slug, slug_events, session_num=session_num
            )

        per_slug_no_event_skip[slug] = False

        prev_rid: str | None = (
            all_details[-1].last_response_id if all_details else None
        )
        detail = run_planning_turn_detailed(
            client=client,
            model_id=model_id,
            instructions=inst_stage_b,
            tools=tools,
            corpus_path=corpus_dir,
            user_line=user_line,
            previous_response_id=prev_rid,
            dispatch_tool=dispatch,
            telemetry_context={
                "suite": "session_events_extraction_vertical_slice_stage_b_npc",
                "corpus_fingerprint": fp,
                "turn_index": slug_turn_idx,
                "per_slug": slug,
                "stage": "stage_b_npc_events_driven",
                "expected_skip": is_skip,
            },
            corpus_path_ref_index=ref_index,
            active_skill_id=None,
        )
        all_details.append(detail)
        slug_turn_idx += 1

        beat = _extract_beat_for_slug(detail.tool_trace or [], slug)
        per_slug_diagnostics[slug] = {
            "slug_events_sent": list(slug_events),
            "slug_beat_written": beat,
            "slug_model_message": (detail.final_text or "").strip() or None,
            "expected_skip": is_skip,
            "model_invoked": True,
        }

        if not quiet:
            tools_called = [r.get("tool") for r in (detail.tool_trace or [])]
            print(
                f"[step3-npc] slug={slug} turn={slug_turn_idx} skip={is_skip} tools={tools_called}",
                file=sys.stderr,
            )
        if detail.final_text:
            combined_final_text_parts.append(f"[{slug}] {detail.final_text.strip()}")

    if not all_details:
        return [], "", 0.0, per_slug_no_event_skip, per_slug_diagnostics

    merged = merge_planning_turn_details_chain(all_details)

    statblock_usd = sum(float(x.get("total_usd", 0) or 0) for x in tool_cost_sink)
    tc = dict(merged.telemetry_cost or {})
    planner_usd = float(tc.get("planner_estimated_cost_usd", 0) or 0)
    stage_b_cost = round(planner_usd + statblock_usd, 6)

    combined_tool_trace = list(merged.tool_trace or [])
    combined_final_text = "\n\n".join(combined_final_text_parts)

    return combined_tool_trace, combined_final_text, stage_b_cost, per_slug_no_event_skip, per_slug_diagnostics


def _sanitize_seg(raw: str, *, max_len: int) -> str:
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


def _resolve_step3_runs_root(runs_root: Path | None) -> Path:
    if runs_root is not None:
        return runs_root
    env = os.environ.get("STEP3_NPC_RUNS_ROOT", "").strip()
    if env:
        return Path(env).expanduser().resolve()
    return _SLICE_DIR / "artifacts" / "runs"


def write_step3_run_report(
    *,
    run_index: int | None,
    cohort_size: int | None,
    gates_passed: bool,
    per_gate_verdict_map: dict[str, str],
    violations: dict[str, list[str]],
    grader_telemetry: dict[str, Any],
    stage_a_event_count: int,
    per_slug_no_event_skip: dict[str, bool],
    stage_a_cost_usd: float,
    stage_b_cost_usd: float,
    model_id: str,
    scenario_id: str = "timeline_pass_session20_npc",
    runs_root: Path | None = None,
    utc: datetime | None = None,
    per_slug_diagnostics: dict[str, dict[str, Any]] | None = None,
) -> tuple[Path, Path, Step2RunSummary]:
    when = utc or datetime.now(timezone.utc)
    iso = when.strftime("%Y-%m-%dT%H:%M:%SZ")
    total = round(stage_a_cost_usd + stage_b_cost_usd, 6)
    base_runs = _resolve_step3_runs_root(runs_root)
    day_dir = base_runs / when.strftime("%Y-%m-%d")
    scen = _sanitize_seg(scenario_id, max_len=40)
    mod = _sanitize_seg(model_id, max_len=48)
    gate = "PASS" if gates_passed else "FAIL"
    run_suffix = f"--run{run_index + 1:03d}" if run_index is not None else ""
    compact = when.strftime("%Y%m%dT%H%M%S") + "Z"
    base = f"step3_npc_events--{scen}--{mod}--{gate}--{compact}{run_suffix}"
    primary_md = day_dir / f"{base}.md"
    sidecar_json = day_dir / f"{base}.json"

    violation_counts = {k: len(v) for k, v in violations.items()}
    verdict_str = " ".join(f"{k}={v}" for k, v in sorted(per_gate_verdict_map.items()))
    no_event_skips = sorted(slug for slug, skip in per_slug_no_event_skip.items() if skip)
    viol_lines = "\n".join(
        f"  [{bucket}] {msg}" for bucket, msgs in violations.items() for msg in msgs
    )

    sidecar: dict[str, Any] = {
        "schema": "step3_npc_timeline_from_events_run_report_v1",
        "phase_names": {
            "recap_to_events": _RECAP_TO_EVENTS_LABEL,
            "npc_events_to_timeline": _NPC_EVENTS_TO_TIMELINE_LABEL,
        },
        "iso_utc": iso,
        "scenario_id": scenario_id,
        "model_id": model_id,
        "run_index": run_index,
        "cohort_size": cohort_size,
        "gates_passed": gates_passed,
        "per_gate_verdict": dict(per_gate_verdict_map),
        "stage_a_cost_usd": round(stage_a_cost_usd, 6),
        "stage_b_cost_usd": round(stage_b_cost_usd, 6),
        "recap_to_events_cost_usd": round(stage_a_cost_usd, 6),
        "npc_events_to_timeline_cost_usd": round(stage_b_cost_usd, 6),
        "total_cost_usd": total,
        "stage_a_event_count": stage_a_event_count,
        "recap_to_events_event_count": stage_a_event_count,
        "per_slug_no_event_skip": dict(per_slug_no_event_skip),
        "no_event_skip_slugs": no_event_skips,
        "violation_counts": violation_counts,
        "violations": {k: list(v) for k, v in violations.items()},
        "grader_telemetry": dict(grader_telemetry),
        "per_slug_diagnostics": dict(per_slug_diagnostics or {}),
    }

    _diag = dict(per_slug_diagnostics or {})
    diag_lines: list[str] = []
    for _slug in sorted(_diag):
        _d = _diag[_slug]
        diag_lines.append(f"### {_slug}")
        diag_lines.append(f"- **events_sent:** {len(_d.get('slug_events_sent') or [])}")
        diag_lines.append(f"- **expected_skip:** {_d.get('expected_skip')}")
        diag_lines.append(f"- **model_invoked:** {_d.get('model_invoked')}")
        diag_lines.append(f"- **beat_written:** {json.dumps(_d.get('slug_beat_written'))}")
        diag_lines.append("")
    diag_section = "\n".join(diag_lines) if diag_lines else "(no diagnostics)\n"

    body = (
        f"# NPC events-to-timeline run report — {iso}\n\n"
        f"- **scenario:** `{scenario_id}`\n"
        f"- **model:** `{model_id}`\n"
        f"- **gates:** {'PASS' if gates_passed else 'FAIL'}\n"
        f"- **per_gate:** `{verdict_str}`\n"
        f"- **recap_to_events_event_count:** {stage_a_event_count}\n"
        f"- **recap_to_events_cost_usd:** {stage_a_cost_usd:.6f}\n"
        f"- **npc_events_to_timeline_cost_usd:** {stage_b_cost_usd:.6f}\n"
        f"- **total_cost_usd:** {total:.6f}\n"
        f"- **no_event_skip_slugs:** {no_event_skips}\n\n"
        "## Violations\n\n"
        f"```\n{viol_lines if viol_lines else '(none)'}\n```\n\n"
        "## Per-slug diagnostics\n\n"
        f"{diag_section}\n"
        "## Sidecar JSON\n\n"
        f"```json\n{json.dumps(sidecar, indent=2, ensure_ascii=False, default=str)}\n```\n"
    )

    day_dir.mkdir(parents=True, exist_ok=True)
    primary_md.write_text(body, encoding="utf-8")
    sidecar_json.write_text(
        json.dumps(sidecar, indent=2, ensure_ascii=False, default=str), encoding="utf-8"
    )
    legacy_dir = _SLICE_DIR / "artifacts"
    legacy_dir.mkdir(parents=True, exist_ok=True)
    (legacy_dir / "last_step3_npc_run.md").write_text(body, encoding="utf-8")
    (legacy_dir / "last_step3_npc_run.json").write_text(
        json.dumps(sidecar, indent=2, ensure_ascii=False, default=str), encoding="utf-8"
    )

    summary = Step2RunSummary(
        run_index=run_index if run_index is not None else 0,
        iso_utc=iso,
        gates_passed=gates_passed,
        stage_a_cost_usd=round(stage_a_cost_usd, 6),
        stage_b_cost_usd=round(stage_b_cost_usd, 6),
        total_cost_usd=total,
        stage_a_event_count=stage_a_event_count,
        per_slug_no_event_skip=dict(per_slug_no_event_skip),
        violation_counts=violation_counts,
        per_gate_verdict=dict(per_gate_verdict_map),
        primary_md_path=str(primary_md),
        sidecar_json_path=str(sidecar_json),
        per_slug_diagnostics=dict(_diag),
    )
    return primary_md, sidecar_json, summary


def write_step3_multi_summary(
    summaries: list[Step2RunSummary],
    *,
    model_id: str,
    scenario_id: str,
    runs_root: Path | None = None,
) -> tuple[Path, Path]:
    when = datetime.now(timezone.utc)
    iso_compact = when.strftime("%Y%m%dT%H%M%S") + "Z"
    n = len(summaries)
    mod = _sanitize_seg(model_id, max_len=48)
    base = f"step3_npc_events_summary--{mod}--N{n}--{iso_compact}"
    root = _resolve_step3_runs_root(runs_root)
    day_dir = root / when.strftime("%Y-%m-%d")
    day_dir.mkdir(parents=True, exist_ok=True)
    md_path = day_dir / f"{base}.md"
    json_path = day_dir / f"{base}.json"

    total_costs = [s.total_cost_usd for s in summaries]
    stage_a_costs = [s.stage_a_cost_usd for s in summaries]
    stage_b_costs = [s.stage_b_cost_usd for s in summaries]
    passed_n = sum(1 for s in summaries if s.gates_passed)

    gate_ids = ("TP1", "TP2", "TP3", "TP5")
    gate_pass_counts = {
        g: sum(1 for s in summaries if s.per_gate_verdict.get(g) == "PASS")
        for g in gate_ids
    }

    all_slugs = sorted({slug for s in summaries for slug in s.per_slug_no_event_skip})
    per_slug_skip_counts = {
        slug: sum(1 for s in summaries if s.per_slug_no_event_skip.get(slug, False))
        for slug in all_slugs
    }

    payload: dict[str, Any] = {
        "schema": "step3_npc_timeline_from_events_multi_summary_v1",
        "iso_utc": when.strftime("%Y-%m-%dT%H:%M:%SZ"),
        "scenario_id": scenario_id,
        "model_id": model_id,
        "n": n,
        "passed": passed_n,
        "per_gate_pass_counts": gate_pass_counts,
        "cost_usd": {
            "total_sum": round(sum(total_costs), 6),
            "total_mean": round(statistics.mean(total_costs), 6) if total_costs else 0.0,
            "total_max": round(max(total_costs), 6) if total_costs else 0.0,
            "stage_a_sum": round(sum(stage_a_costs), 6),
            "stage_b_sum": round(sum(stage_b_costs), 6),
            "recap_to_events_sum": round(sum(stage_a_costs), 6),
            "npc_events_to_timeline_sum": round(sum(stage_b_costs), 6),
        },
        "per_slug_skip_counts_across_cohort": per_slug_skip_counts,
        "runs": [
            {
                "run_index": s.run_index,
                "gates_passed": s.gates_passed,
                "per_gate_verdict": s.per_gate_verdict,
                "total_cost_usd": s.total_cost_usd,
                "stage_a_cost_usd": s.stage_a_cost_usd,
                "stage_b_cost_usd": s.stage_b_cost_usd,
                "recap_to_events_cost_usd": s.stage_a_cost_usd,
                "npc_events_to_timeline_cost_usd": s.stage_b_cost_usd,
                "stage_a_event_count": s.stage_a_event_count,
                "recap_to_events_event_count": s.stage_a_event_count,
                "per_slug_no_event_skip": s.per_slug_no_event_skip,
                "sidecar_json": s.sidecar_json_path,
            }
            for s in summaries
        ],
    }

    md_lines = [
        f"# NPC events-to-timeline cohort summary ({n} runs)",
        "",
        f"- **model:** `{model_id}`",
        f"- **scenario:** `{scenario_id}`",
        f"- **TP1 pass rate:** {gate_pass_counts['TP1']}/{n}",
        f"- **overall pass rate:** {passed_n}/{n}",
        f"- **total cost:** ${payload['cost_usd']['total_sum']:.4f}",
        f"- **mean per-run cost:** ${payload['cost_usd']['total_mean']:.4f}",
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
        skip_slugs = sorted(slug for slug, skip in s.per_slug_no_event_skip.items() if skip)
        md_lines.append(
            f"- run {s.run_index + 1}: {'PASS' if s.gates_passed else 'FAIL'} "
            f"| total=${s.total_cost_usd:.4f} "
            f"| events={s.stage_a_event_count} | no_event_skip_slugs={skip_slugs} "
            f"| {verdict_str} | `{s.sidecar_json_path}`"
        )

    md_path.write_text("\n".join(md_lines) + "\n", encoding="utf-8")
    json_path.write_text(
        json.dumps(payload, indent=2, ensure_ascii=False, default=str), encoding="utf-8"
    )
    return md_path, json_path


def _run_single_npc_chained_iteration(
    *,
    client: Any,
    model_id: str,
    stage_a_scenario: dict[str, Any],
    corpus_root: Path,
    stage_b_gold: dict[str, Any],
    allow_corpus_writes: bool = True,
    quiet: bool = False,
    pre_state_manifest: dict[str, Any] | None = None,
    enable_anchor_repair: bool = True,
) -> dict[str, Any]:
    stage_a_result = run_session_events_extraction(
        client=client,
        model_id=model_id,
        scenario=stage_a_scenario,
        corpus_root=corpus_root,
        enable_anchor_repair=enable_anchor_repair,
    )
    stage_a_cost = float(stage_a_result.get("cost_usd") or 0.0)

    if stage_a_result.get("error"):
        print(
            "[step3-npc] INFRASTRUCTURE ERROR — recap_to_events extraction failed: "
            f"{stage_a_result['error']}",
            file=sys.stderr,
        )
        return {
            "infrastructure_error": True,
            "error": str(stage_a_result["error"]),
            "stage_a_cost_usd": stage_a_cost,
        }

    stage_a_events: list[dict[str, Any]] = list(stage_a_result.get("parsed_events") or [])
    stage_b_grading = _filter_grading_to_npcs(stage_b_gold.get("grading") or {})

    manifest = (
        pre_state_manifest
        if pre_state_manifest is not None
        else _resolve_pre_state_manifest_dict(stage_b_gold)
    )
    corpus_dir = build_pre_state_corpus(manifest=manifest)
    tool_trace, final_text, stage_b_cost, per_slug_skip, per_slug_diagnostics = (
        run_stage_b_npc_events_driven_chain(
            corpus_dir=corpus_dir,
            client=client,
            model_id=model_id,
            stage_b_scenario=stage_b_gold,
            stage_a_events=stage_a_events,
            allow_corpus_writes=allow_corpus_writes,
            quiet=quiet,
        )
    )

    violations, telemetry = collect_timeline_pass_violations(
        corpus_dir=corpus_dir,
        tool_trace=tool_trace,
        final_text=final_text,
        grading=stage_b_grading,
    )
    verdict = tp_per_gate_verdict(violations)
    gates_passed = not violations

    return {
        "infrastructure_error": False,
        "stage_a_cost_usd": stage_a_cost,
        "stage_a_event_count": len(stage_a_events),
        "stage_b_cost_usd": stage_b_cost,
        "corpus_dir": corpus_dir,
        "tool_trace": tool_trace,
        "final_text": final_text,
        "per_slug_skip": per_slug_skip,
        "per_slug_diagnostics": per_slug_diagnostics,
        "violations": violations,
        "telemetry": telemetry,
        "verdict": verdict,
        "gates_passed": gates_passed,
    }


def main() -> None:
    parser = argparse.ArgumentParser(description="NPC events-to-timeline benchmark")
    parser.add_argument("--n", type=int, default=1, help="Cohort size (default: 1)")
    parser.add_argument("--model", type=str, default="", help="Model ID")
    parser.add_argument(
        "--scenario-json",
        type=Path,
        default=_STAGE_A_GOLD_DEFAULT,
        help="Path to recap-to-events gold scenario JSON (default: gold/session_events_session20.json)",
    )
    parser.add_argument(
        "--timeline-gold",
        type=Path,
        default=None,
        help="Path to timeline-pass grading JSON (NPC rows filtered at runtime)",
    )
    parser.add_argument("--pre-state-manifest", type=Path, default=None)
    parser.add_argument("--runs-root", type=Path, default=None)
    parser.add_argument("--no-writes", action="store_true")
    parser.add_argument("--disable-anchor-repair", action="store_true")
    parser.add_argument("-q", "--quiet", action="store_true")
    args = parser.parse_args()

    load_dungeonmindbuddy_dotenv()
    api_key = (_load_api_key() or "").strip()
    if not api_key:
        print(
            "OPENAI_API_KEY missing after loading .env / .env.development.", file=sys.stderr
        )
        sys.exit(2)

    os.environ.setdefault(_ALLOW_WRITES_ENV, "1")

    from openai import OpenAI  # noqa: E402

    client = OpenAI()

    stage_a_gold = load_stage_a_scenario(args.scenario_json)
    corpus_root = resolve_corpus_root()

    timeline_gold_path = (args.timeline_gold or _TIMELINE_GOLD_DEFAULT).resolve()
    stage_b_gold = json.loads(timeline_gold_path.read_text(encoding="utf-8"))
    scenario_id = str(stage_b_gold.get("scenario_id") or timeline_gold_path.stem) + "_npc"

    manifest_override: dict[str, Any] | None = None
    if args.pre_state_manifest:
        manifest_override = json.loads(
            args.pre_state_manifest.read_text(encoding="utf-8")
        )

    model_id = _resolve_planner_model((args.model.strip() or None))
    n = max(1, int(args.n))

    if not args.quiet:
        print(f"[step3-npc] n={n} model={model_id}", file=sys.stderr)

    summaries: list[Step2RunSummary] = []
    total_cohort_cost = 0.0
    pass_count = 0
    infra_error_count = 0

    for i in range(n):
        if not args.quiet:
            print(f"[step3-npc] run {i + 1}/{n} starting…", file=sys.stderr)
        t0 = time.monotonic()

        result = _run_single_npc_chained_iteration(
            client=client,
            model_id=model_id,
            stage_a_scenario=stage_a_gold,
            corpus_root=corpus_root,
            stage_b_gold=stage_b_gold,
            allow_corpus_writes=True,
            quiet=args.quiet,
            pre_state_manifest=manifest_override,
            enable_anchor_repair=not bool(args.disable_anchor_repair),
        )

        if result["infrastructure_error"]:
            infra_error_count += 1
            print(
                f"[step3-npc] run {i + 1}/{n} INFRASTRUCTURE_ERROR — {result['error']}",
                file=sys.stderr,
            )
            continue

        stage_a_cost = result["stage_a_cost_usd"]
        stage_b_cost = result["stage_b_cost_usd"]
        stage_a_event_count_run = result["stage_a_event_count"]
        per_slug_skip = result["per_slug_skip"]
        per_slug_diagnostics = result["per_slug_diagnostics"]
        violations = result["violations"]
        verdict = result["verdict"]
        gates_passed = result["gates_passed"]

        if gates_passed:
            pass_count += 1

        elapsed_s = round(time.monotonic() - t0, 2)
        run_cost = round(stage_a_cost + stage_b_cost, 4)
        total_cohort_cost += run_cost

        verdict_str = " ".join(f"{k}={v}" for k, v in sorted(verdict.items()))
        skip_slugs = sorted(slug for slug, skip in per_slug_skip.items() if skip)
        print(
            f"[step3-npc] run {i + 1}/{n} | "
            f"{'PASS' if gates_passed else 'FAIL'} | "
            f"events={stage_a_event_count_run} | "
            f"no_event_skip_slugs={skip_slugs} | "
            f"cost_usd={run_cost:.4f} | "
            f"elapsed={elapsed_s}s | "
            f"{verdict_str}"
        )

        if not args.no_writes:
            _, _, summary = write_step3_run_report(
                run_index=i if n > 1 else None,
                cohort_size=n if n > 1 else None,
                gates_passed=gates_passed,
                per_gate_verdict_map=verdict,
                violations=violations,
                grader_telemetry=result["telemetry"],
                stage_a_event_count=stage_a_event_count_run,
                per_slug_no_event_skip=per_slug_skip,
                stage_a_cost_usd=stage_a_cost,
                stage_b_cost_usd=stage_b_cost,
                model_id=model_id,
                scenario_id=scenario_id,
                runs_root=args.runs_root,
                per_slug_diagnostics=per_slug_diagnostics,
            )
            summaries.append(summary)
            if not args.quiet:
                print(f"[step3-npc] report: {summary.primary_md_path}", file=sys.stderr)
                print(f"[step3-npc] sidecar: {summary.sidecar_json_path}", file=sys.stderr)
        else:
            iso = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
            summaries.append(
                Step2RunSummary(
                    run_index=i,
                    iso_utc=iso,
                    gates_passed=gates_passed,
                    stage_a_cost_usd=round(stage_a_cost, 6),
                    stage_b_cost_usd=round(stage_b_cost, 6),
                    total_cost_usd=round(run_cost, 6),
                    stage_a_event_count=stage_a_event_count_run,
                    per_slug_no_event_skip=dict(per_slug_skip),
                    violation_counts={k: len(v) for k, v in violations.items()},
                    per_gate_verdict=verdict,
                    primary_md_path="",
                    sidecar_json_path="",
                    per_slug_diagnostics=dict(per_slug_diagnostics),
                )
            )

        if total_cohort_cost > 5.0 and i + 1 < n:
            print(
                f"[step3-npc] STOP: cumulative cost ${total_cohort_cost:.2f} exceeds guard.",
                file=sys.stderr,
            )
            break

        effective_runs = (i + 1) - infra_error_count
        if total_cohort_cost > 1.0 and pass_count == 0 and effective_runs >= 2 and i + 1 < n:
            print(
                "[step3-npc] STOP: cumulative cost with 0 passes; skipping remaining runs.",
                file=sys.stderr,
            )
            break

    if n > 1 and summaries and not args.no_writes:
        md_s, json_s = write_step3_multi_summary(
            summaries,
            model_id=model_id,
            scenario_id=scenario_id,
            runs_root=args.runs_root,
        )
        print(f"[step3-npc] cohort summary: {md_s}", file=sys.stderr)
        print(f"[step3-npc] cohort sidecar: {json_s}", file=sys.stderr)

    effective_n = len(summaries)
    print(
        f"[step3-npc] cohort done | pass_rate={pass_count}/{effective_n} "
        f"(infra_errors={infra_error_count}) | "
        f"total_cost_usd=${total_cohort_cost:.4f}"
    )

    if summaries and not all(s.gates_passed for s in summaries):
        sys.exit(1)


if __name__ == "__main__":
    main()
