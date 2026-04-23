"""Stage B vertical slice: per-PC timeline append from events.

Consumes Stage A's parsed events inline and per-PC calls ``append_timeline_row``
to populate the timeline-pass corpus pre-state. Stage B is **PC-only** — NPC
artifact updates (timeline rows + dossier sections) are handled by the separate
forthcoming NPC ingestion slice. The model sees ONLY the events for the PC under
consideration — no recap re-read.

This is the architectural test: events as input, PCs as scope, no recap re-read.
NPC slugs in the timeline-pass gold are filtered out by the runner before the
grader is invoked, so TP1/TP2/TP3/TP5 evaluate strictly against PC behavior.

Run (from repo root)::

    uv run python -m evals.session_events_extraction_vertical_slice.step2_timeline_from_events_run --n 5 --model gpt-5.4-mini

Options::

    --n N               Number of runs in the cohort (default: 1)
    --model MODEL       Model ID (default: resolved via DUNGEONMIND_PLANNER_MODEL env or gpt-5.4-mini)
    --scenario-json     Path to Stage A gold scenario JSON (default: gold/session_events_session20.json)
    --timeline-gold     Path to timeline-pass grading JSON for Stage B (default: …/timeline_pass_session20.json)
    --pre-state-manifest  Override pre-state manifest JSON (default: from timeline gold's ``pre_state_manifest_relative`` or Session 20 default)
    --runs-root         Override artifact runs root directory (default: artifacts/runs/)
    --no-writes         Skip writing run reports to disk
    -q / --quiet        Suppress progress lines on stderr
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
from evals.session_recap_timeline_pass_vertical_slice.grader import (  # noqa: E402
    collect_timeline_pass_violations,
    per_gate_verdict as tp_per_gate_verdict,
)
from evals.session_recap_timeline_pass_vertical_slice.step0_pre_state import (  # noqa: E402
    build_pre_state_corpus,
    load_pre_state_manifest,
)
from evals.session_recap_timeline_pass_vertical_slice.step1_timeline_pass_run import (  # noqa: E402
    _TIMELINE_PASS_SLUG_ORDER,
    ordered_timeline_targets,
)

_SLICE_DIR = Path(__file__).resolve().parent
_STAGE_A_GOLD_DEFAULT = _SLICE_DIR / "gold" / "session_events_session20.json"
_TIMELINE_PASS_SLICE_DIR = _REPO_ROOT / "evals" / "session_recap_timeline_pass_vertical_slice"
_STAGE_B_GOLD_PATH = _TIMELINE_PASS_SLICE_DIR / "gold" / "timeline_pass_session20.json"
_ALLOW_WRITES_ENV = "DUNGEONMIND_PLANNER_ALLOW_WRITES"

# Re-export for tests that want to verify the slug order without importing
# from the timeline-pass slice directly.
STAGE_B_SLUG_ORDER: tuple[str, ...] = _TIMELINE_PASS_SLUG_ORDER


def _is_pc_target(spec: dict[str, Any]) -> bool:
    """True iff the timeline spec lives under a PCs/ hub.

    Stage B is narrowed to PCs only. NPC artifact updates are handled by the
    forthcoming NPC ingestion slice. The signal is ``timeline_relative_path``
    containing ``/PCs/`` (Campaign 1 or Campaign 2). NPC paths use ``/NPCs/``.
    """
    rel = str(spec.get("timeline_relative_path", "") or "")
    return "/PCs/" in rel


def _filter_grading_to_pcs(grading: dict[str, Any]) -> dict[str, Any]:
    """Return a shallow copy of grading with expected_appends/expected_skips/allowed_npc_slugs
    restricted to PC entries.

    Stage B is PC-only. Filtering both the runner targets AND the grader's expected
    sets keeps the cohort honest: TP1/TP2/TP3/TP5 are evaluated against the PCs the
    runner actually invokes, never punishing Stage B for NPCs it intentionally never
    touched.
    """
    out = dict(grading)
    out["expected_appends"] = [s for s in (grading.get("expected_appends") or []) if _is_pc_target(s)]
    out["expected_skips"] = [s for s in (grading.get("expected_skips") or []) if _is_pc_target(s)]
    pc_slugs = {
        str(s.get("npc_slug") or "").strip()
        for s in out["expected_appends"] + out["expected_skips"]
        if s.get("npc_slug")
    }
    if "allowed_npc_slugs" in grading:
        out["allowed_npc_slugs"] = [
            s for s in (grading.get("allowed_npc_slugs") or []) if s in pc_slugs
        ]
    return out


# ---------------------------------------------------------------------------
# Timeline-pass gold helpers (session, recap path, manifest, slug order)
# ---------------------------------------------------------------------------


def _recap_evidence_path_from_stage_b_gold(stage_b_gold: dict[str, Any]) -> str:
    grading = stage_b_gold.get("grading") or {}
    explicit = str(grading.get("recap_evidence_path") or "").strip()
    if explicit:
        return explicit
    fn = str(grading.get("recap_filename") or "Session 20 - Recap.md").strip()
    return f"Longmont Campaign/Campaign 2/Session Recaps/{fn}"


def _session_int_from_stage_b_gold(stage_b_gold: dict[str, Any]) -> int:
    g = stage_b_gold.get("grading") or {}
    try:
        return int(g.get("session", 20))
    except (TypeError, ValueError):
        return 20


def _resolve_pre_state_manifest_dict(stage_b_gold: dict[str, Any]) -> dict[str, Any]:
    rel = str(stage_b_gold.get("pre_state_manifest_relative") or "").strip()
    if rel:
        p = (_TIMELINE_PASS_SLICE_DIR / rel).resolve()
        if not p.is_file():
            raise FileNotFoundError(f"pre_state manifest not found: {p}")
        return json.loads(p.read_text(encoding="utf-8"))
    return load_pre_state_manifest()


def ordered_stage_b_timeline_targets(grading: dict[str, Any]) -> list[dict[str, Any]]:
    """Return append+skip specs in ``grading.timeline_slug_order`` or C2 default order."""
    custom = grading.get("timeline_slug_order")
    if isinstance(custom, list) and custom:
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
        for slug in custom:
            key = str(slug).strip()
            if key in by_slug:
                out.append(by_slug[key])
        return out
    return ordered_timeline_targets(grading)


def build_stage_b_instruction_suffix(*, session_num: int, recap_evidence_path: str) -> str:
    """Planner instruction suffix for one Stage B micro-turn (PC-only, no recap reads)."""
    tick = recap_evidence_path.strip()
    return f"""

**Benchmark micro-turn — PC timeline append from events (Stage B, single PC):** \
This is a per-PC timeline append turn. The events JSON in the user message is your \
ONLY source about what happened in Session {session_num} for this player character.

DO NOT call `read_corpus_file`, `load_context_markdown`, `get_recap_context`, \
`assemble_recap_draft`, `build_recap_write_payload`, or `write_corpus_file`. \
The events JSON in the user message is sufficient — reading the recap is forbidden here.

This micro-turn covers **one** player character's `timeline.md` only — do not call \
`append_timeline_row` for any other slug.

**ROW POLICY (hard rule — PCs are not optional):** This slug is a player character. \
Any session in which the PC participates in **at least one** event warrants a timeline \
row — the timeline is the PC's own session-by-session record of their playthrough, not \
a curated highlights reel. If the user message reached you with events attached, the \
PC was at the table for this beat and you **must** call `append_timeline_row` once. \
Do not deliberate row-worthiness, do not weigh "primary vs background," and do not \
skip rows for PCs whose contribution feels small — that judgment belongs to the NPC \
ingestion slice, not here, and applying it to a PC would corrupt the PC's playthrough \
record. There is no preview or confirm step; the single call commits.

Anchor the beat on event participants, location, and outcomes. Match the three-column \
table format (session | beat | backticked evidence path). Use \
`` `{tick}` `` as the evidence \
path. The slug-only resolver falls back from `NPCs/<slug>/` to `PCs/<slug>/`, so you \
usually do not need `timeline_path` unless multiple campaigns share the same slug.

**Session number:** When calling ``append_timeline_row``, set ``session`` to **{session_num}** \
(the benchmark session this micro-turn grades).

**VOCABULARY CONTRACT (preserve searchable terms — hard rule):** The events JSON above is \
the result of a careful extraction that preserved the recap's distinctive vocabulary \
specifically so the timeline beat you write here remains searchable months from now. When \
composing the beat, **retain the distinctive named terms that appear in the events' \
`outcomes[]` and `event_name` fields verbatim** — weapon names (e.g. `scimitar`), spell \
names (e.g. `Eldritch Blast`, `Thunderwave`), ability names (e.g. `Zephyr Strike`), item \
names, place names, and NPC names. Generic paraphrases such as "weapon" instead of \
"scimitar," "spell" instead of "Eldritch Blast," or "ability" instead of "Zephyr Strike" \
defeat the entire purpose of the timeline.

**MULTI-EVENT COMPOSITION (hard rule):** When this PC appears in **more than one** event \
above, the beat is **one sentence that composes the events together** — *not* a summary \
of "the most important one." Join the events with commas, semicolons, or "then" and \
preserve each event's distinctive named terms. Discarding events to fit a single-event \
summary loses the recall the timeline exists to provide.

**SCENE ANCHOR (hard rule):** When the events describe a shared encounter or named \
scene this PC participated in (an enemy type, a location's threat, a named event), \
include the scene's distinctive anchor term in your beat **even when that term \
appears only in a co-participant's outcome line rather than this PC's personal \
outcome line**. All participants in a shared event see the same `outcomes[]` list \
when that event reaches them, because they are all in that scene together — if any \
outcome bullet (or the `event_name`) across the shared event names the threat, the \
encounter, or the location anchor (e.g. `swarm`, `ambush`, `the storm`, `the stone \
bridge`, the named encounter), that term belongs in your beat alongside the PC's \
personal action. The PC's timeline beat is a record of "where I was and what I did" \
— not just "what I did" — and the "where" matters as much for searchability months \
from now as the weapon, spell, or ability name does. Concretely: if a `red gnat \
swarm` battle event lists Caelynn casting Thunderwave to "split the swarm" and \
Karsemine landing scimitar hits and dashing away, Karsemine's beat must include \
both `scimitar`/`Zephyr Strike` (her personal action) **and** `swarm` (the scene \
anchor naming what was being fought) — not just "fought the red gnats."

The slug given in the user message is the only legal `npc_slug` — do not invent or rename slugs.

Allowed tools: `append_timeline_row`, `list_pc_hubs`.
Forbidden tools: `read_corpus_file`, `load_context_markdown`, `get_recap_context`, \
`assemble_recap_draft`, `build_recap_write_payload`, `write_corpus_file`.

Reply with `planner_turn_output` JSON (`user_intent`, `message`, `unsure_queue: []`).
"""


# ---------------------------------------------------------------------------
# Per-slug helpers
# ---------------------------------------------------------------------------


def filter_events_for_slug(events: list[dict[str, Any]], slug: str) -> list[dict[str, Any]]:
    """Return events where ``slug`` appears exactly in ``participants[]``."""
    return [ev for ev in events if slug in (ev.get("participants") or [])]


def _extract_beat_for_slug(tool_trace: list[dict[str, Any]], slug: str) -> str | None:
    """Return the ``beat`` text from the first ``append_timeline_row`` call for *slug*.

    Scans a single-slug micro-turn's tool trace for an ``append_timeline_row`` whose
    ``npc_slug`` matches *slug* exactly. Returns ``None`` when no matching call is found
    or when the beat arg is empty.
    """
    for entry in (tool_trace or []):
        if entry.get("tool") == "append_timeline_row":
            args = entry.get("arguments") or {}
            if isinstance(args, dict) and str(args.get("npc_slug", "") or "").strip() == slug:
                beat = str(args.get("beat", "") or "").strip()
                return beat or None
    return None


def build_stage_b_per_slug_user_message(
    timeline_rel: str,
    slug: str,
    slug_events: list[dict[str, Any]],
    *,
    session_num: int = 20,
) -> str:
    """Build the per-slug user message for Stage B (PC-only, events-driven, no recap).

    The model receives only the filtered events for this PC, not the full recap.
    Callers must guarantee ``slug_events`` is non-empty — the runner's no-event-skip
    branch handles the empty case before this builder is invoked.
    """
    events_json = json.dumps(slug_events, indent=2, ensure_ascii=False)
    return (
        f"**PC timeline append micro-turn (events-driven):** Consider only `{timeline_rel}` "
        f"(`npc_slug` `{slug}`). This slug is a **player character**.\n\n"
        f"The following structured events from Session {session_num} mention this PC:\n\n"
        f"```json\n{events_json}\n```\n\n"
        "Call `append_timeline_row` **once** with a beat sentence that **composes** these "
        "events into a single sentence, retaining the distinctive named terms verbatim — "
        "weapon names, spell names, ability names, item names, place names, and NPC names. "
        "When the PC has more than one event above, join them with commas, semicolons, or "
        "'then' rather than picking only one. Anchor the beat on event participants, "
        "location, and outcomes. Match the existing markdown table format.\n\n"
        "Do not skip the row. PCs always get a row when the events list is non-empty — "
        "the row-worthiness judgment does not apply to player characters."
    )


# ---------------------------------------------------------------------------
# Run summary + report writer
# ---------------------------------------------------------------------------


@dataclass
class Step2RunSummary:
    run_index: int
    iso_utc: str
    gates_passed: bool
    stage_a_cost_usd: float
    stage_b_cost_usd: float
    total_cost_usd: float
    stage_a_event_count: int
    per_slug_no_event_skip: dict[str, bool]
    violation_counts: dict[str, int]
    per_gate_verdict: dict[str, str]
    primary_md_path: str
    sidecar_json_path: str
    extras: dict[str, Any] = field(default_factory=dict)
    per_slug_diagnostics: dict[str, dict[str, Any]] = field(default_factory=dict)


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


def _resolve_step2_runs_root(runs_root: Path | None) -> Path:
    if runs_root is not None:
        return runs_root
    env = os.environ.get("STEP2_RUNS_ROOT", "").strip()
    if env:
        return Path(env).expanduser().resolve()
    return _SLICE_DIR / "artifacts" / "runs"


def write_step2_run_report(
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
    scenario_id: str = "timeline_pass_session20",
    runs_root: Path | None = None,
    utc: datetime | None = None,
    per_slug_diagnostics: dict[str, dict[str, Any]] | None = None,
) -> tuple[Path, Path, Step2RunSummary]:
    when = utc or datetime.now(timezone.utc)
    iso = when.strftime("%Y-%m-%dT%H:%M:%SZ")
    total = round(stage_a_cost_usd + stage_b_cost_usd, 6)
    base_runs = _resolve_step2_runs_root(runs_root)
    day_dir = base_runs / when.strftime("%Y-%m-%d")
    scen = _sanitize_seg(scenario_id, max_len=40)
    mod = _sanitize_seg(model_id, max_len=48)
    gate = "PASS" if gates_passed else "FAIL"
    run_suffix = f"--run{run_index + 1:03d}" if run_index is not None else ""
    compact = when.strftime("%Y%m%dT%H%M%S") + "Z"
    base = f"step2_events--{scen}--{mod}--{gate}--{compact}{run_suffix}"
    primary_md = day_dir / f"{base}.md"
    sidecar_json = day_dir / f"{base}.json"

    violation_counts = {k: len(v) for k, v in violations.items()}
    verdict_str = " ".join(f"{k}={v}" for k, v in sorted(per_gate_verdict_map.items()))
    no_event_skips = sorted(slug for slug, skip in per_slug_no_event_skip.items() if skip)
    viol_lines = "\n".join(
        f"  [{bucket}] {msg}" for bucket, msgs in violations.items() for msg in msgs
    )

    sidecar: dict[str, Any] = {
        "schema": "step2_timeline_from_events_run_report_v1",
        "iso_utc": iso,
        "scenario_id": scenario_id,
        "model_id": model_id,
        "run_index": run_index,
        "cohort_size": cohort_size,
        "gates_passed": gates_passed,
        "per_gate_verdict": dict(per_gate_verdict_map),
        "stage_a_cost_usd": round(stage_a_cost_usd, 6),
        "stage_b_cost_usd": round(stage_b_cost_usd, 6),
        "total_cost_usd": total,
        "stage_a_event_count": stage_a_event_count,
        "per_slug_no_event_skip": dict(per_slug_no_event_skip),
        "no_event_skip_slugs": no_event_skips,
        "violation_counts": violation_counts,
        "violations": {k: list(v) for k, v in violations.items()},
        "grader_telemetry": dict(grader_telemetry),
        "per_slug_diagnostics": dict(per_slug_diagnostics or {}),
    }

    # Build per-slug diagnostics section for markdown
    _diag = dict(per_slug_diagnostics or {})
    diag_lines: list[str] = []
    for _slug in sorted(_diag):
        _d = _diag[_slug]
        _events_count = len(_d.get("slug_events_sent") or [])
        _beat = _d.get("slug_beat_written")
        _msg = _d.get("slug_model_message") or ""
        _msg_short = (_msg[:200] + "…") if len(_msg) > 200 else _msg
        diag_lines.append(f"### {_slug}")
        diag_lines.append(f"- **events_sent:** {_events_count}")
        diag_lines.append(f"- **beat_written:** {json.dumps(_beat)}")
        diag_lines.append(f"- **model_message:** {json.dumps(_msg_short)}")
        diag_lines.append("")
    diag_section = "\n".join(diag_lines) if diag_lines else "(no diagnostics captured)\n"

    body = (
        f"# Step2 run report — {iso}\n\n"
        f"- **scenario:** `{scenario_id}`\n"
        f"- **model:** `{model_id}`\n"
        f"- **gates:** {'PASS' if gates_passed else 'FAIL'}\n"
        f"- **per_gate:** `{verdict_str}`\n"
        f"- **stage_a_event_count:** {stage_a_event_count}\n"
        f"- **stage_a_cost_usd:** {stage_a_cost_usd:.6f}\n"
        f"- **stage_b_cost_usd:** {stage_b_cost_usd:.6f}\n"
        f"- **total_cost_usd:** {total:.6f}\n"
        f"- **no_event_skips:** {no_event_skips}\n\n"
        "## Violations\n\n"
        f"```\n{viol_lines if viol_lines else '(none)'}\n```\n\n"
        "## Per-slug diagnostics\n\n"
        f"{diag_section}\n"
        "## Grader telemetry\n\n"
        f"```json\n{json.dumps(grader_telemetry, indent=2, ensure_ascii=False, default=str)}\n```\n\n"
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
    (legacy_dir / "last_step2_run.md").write_text(body, encoding="utf-8")
    (legacy_dir / "last_step2_run.json").write_text(
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


def write_step2_multi_summary(
    summaries: list[Step2RunSummary],
    *,
    model_id: str,
    scenario_id: str,
    runs_root: Path | None = None,
) -> tuple[Path, Path]:
    """Write cohort summary markdown + JSON sidecar. Returns (md_path, json_path)."""
    when = datetime.now(timezone.utc)
    iso_compact = when.strftime("%Y%m%dT%H%M%S") + "Z"
    n = len(summaries)
    mod = _sanitize_seg(model_id, max_len=48)
    base = f"step2_events_summary--{mod}--N{n}--{iso_compact}"
    root = _resolve_step2_runs_root(runs_root)
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

    # Per-slug skip counts across the cohort (Stage A recall telemetry)
    all_slugs = sorted({slug for s in summaries for slug in s.per_slug_no_event_skip})
    per_slug_skip_counts = {
        slug: sum(1 for s in summaries if s.per_slug_no_event_skip.get(slug, False))
        for slug in all_slugs
    }

    payload: dict[str, Any] = {
        "schema": "step2_timeline_from_events_multi_summary_v1",
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
                "stage_a_event_count": s.stage_a_event_count,
                "per_slug_no_event_skip": s.per_slug_no_event_skip,
                "sidecar_json": s.sidecar_json_path,
            }
            for s in summaries
        ],
    }

    md_lines = [
        f"# Stage B (events-driven timeline pass) cohort summary ({n} runs)",
        "",
        f"- **model:** `{model_id}`",
        f"- **scenario:** `{scenario_id}`",
        f"- **TP1 pass rate:** {gate_pass_counts['TP1']}/{n}",
        f"- **overall pass rate:** {passed_n}/{n}",
        f"- **total cost:** ${payload['cost_usd']['total_sum']:.4f} "
        f"(Stage A ${payload['cost_usd']['stage_a_sum']:.4f}, "
        f"Stage B ${payload['cost_usd']['stage_b_sum']:.4f})",
        f"- **mean per-run cost:** ${payload['cost_usd']['total_mean']:.4f}",
        "",
        "## Per-gate pass counts",
        "",
    ]
    for g in gate_ids:
        md_lines.append(f"- {g}: {gate_pass_counts[g]}/{n}")

    md_lines.extend(["", "## Per-slug no-event skip counts (Stage A recall)", ""])
    for slug in all_slugs:
        md_lines.append(f"- {slug}: skipped {per_slug_skip_counts[slug]}/{n} runs")

    md_lines.extend(["", "## Runs", ""])
    for s in summaries:
        verdict_str = " ".join(
            f"{g}={s.per_gate_verdict.get(g, '?')}" for g in gate_ids
        )
        skip_slugs = sorted(slug for slug, skip in s.per_slug_no_event_skip.items() if skip)
        md_lines.append(
            f"- run {s.run_index + 1}: {'PASS' if s.gates_passed else 'FAIL'} "
            f"| total=${s.total_cost_usd:.4f} "
            f"(A=${s.stage_a_cost_usd:.4f} B=${s.stage_b_cost_usd:.4f}) "
            f"| events={s.stage_a_event_count} | skips={skip_slugs} "
            f"| {verdict_str} | `{s.sidecar_json_path}`"
        )

    md_path.write_text("\n".join(md_lines) + "\n", encoding="utf-8")
    json_path.write_text(
        json.dumps(payload, indent=2, ensure_ascii=False, default=str), encoding="utf-8"
    )
    return md_path, json_path


# ---------------------------------------------------------------------------
# Core Stage B per-slug chain
# ---------------------------------------------------------------------------


def run_stage_b_events_driven_chain(
    *,
    corpus_dir: Path,
    client: Any,
    model_id: str,
    stage_b_scenario: dict[str, Any],
    stage_a_events: list[dict[str, Any]],
    allow_corpus_writes: bool = True,
    quiet: bool = False,
) -> tuple[list[dict[str, Any]], str, float, dict[str, bool], dict[str, dict[str, Any]]]:
    """Run Stage B per-slug chain.

    Returns:
        (combined_tool_trace, combined_final_text, stage_b_cost_usd,
         per_slug_no_event_skip, per_slug_diagnostics)

    ``per_slug_no_event_skip[slug]`` is ``True`` when Stage A produced zero events for
    that slug (model call skipped entirely) and ``False`` when the model was called.

    ``per_slug_diagnostics[slug]`` contains three fields per slug:
    - ``slug_events_sent``: list of event dicts passed to the model (``[]`` for skip)
    - ``slug_beat_written``: beat text from ``append_timeline_row`` call (``None`` if absent)
    - ``slug_model_message``: model's final ``message`` text (``None`` for no-event skip)
    """
    grading = stage_b_scenario.get("grading") or {}
    targets = ordered_stage_b_timeline_targets(grading)
    targets = [t for t in targets if _is_pc_target(t)]

    session_num = _session_int_from_stage_b_gold(stage_b_scenario)
    recap_evidence = _recap_evidence_path_from_stage_b_gold(stage_b_scenario)
    instr_suffix = build_stage_b_instruction_suffix(
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
        if not slug_events:
            per_slug_no_event_skip[slug] = True
            per_slug_diagnostics[slug] = {
                "slug_events_sent": [],
                "slug_beat_written": None,
                "slug_model_message": None,
            }
            if not quiet:
                print(
                    f"[step2] slug={slug} no-event skip "
                    "(Stage A produced 0 events for this slug)",
                    file=sys.stderr,
                )
            continue

        per_slug_no_event_skip[slug] = False
        user_line = build_stage_b_per_slug_user_message(
            rel, slug, slug_events, session_num=session_num
        )

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
                "suite": "session_events_extraction_vertical_slice_stage_b",
                "corpus_fingerprint": fp,
                "turn_index": slug_turn_idx,
                "per_slug": slug,
                "stage": "stage_b_events_driven",
            },
            corpus_path_ref_index=ref_index,
            active_skill_id=None,
        )
        all_details.append(detail)
        slug_turn_idx += 1

        # Capture per-slug diagnostics from this turn's tool trace
        beat = _extract_beat_for_slug(detail.tool_trace or [], slug)
        per_slug_diagnostics[slug] = {
            "slug_events_sent": list(slug_events),
            "slug_beat_written": beat,
            "slug_model_message": (detail.final_text or "").strip() or None,
        }

        if not quiet:
            tools_called = [r.get("tool") for r in (detail.tool_trace or [])]
            print(
                f"[step2] slug={slug} turn={slug_turn_idx} tools={tools_called}",
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


# ---------------------------------------------------------------------------
# Testable per-iteration helper
# ---------------------------------------------------------------------------


def _run_single_chained_cohort_iteration(
    *,
    client: Any,
    model_id: str,
    stage_a_scenario: dict[str, Any],
    corpus_root: Path,
    stage_b_gold: dict[str, Any],
    allow_corpus_writes: bool = True,
    quiet: bool = False,
    pre_state_manifest: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """Run one Stage A → Stage B cohort iteration without I/O side effects.

    Returns ``{"infrastructure_error": True, "error": msg, "stage_a_cost_usd": ...}``
    if Stage A returns an error (transient API failure, schema error, etc.).
    Stage B is **not** called in that case.

    Otherwise returns a full result dict with ``infrastructure_error: False`` plus
    ``gates_passed``, ``violations``, ``per_slug_diagnostics``, etc.
    """
    stage_a_result = run_session_events_extraction(
        client=client,
        model_id=model_id,
        scenario=stage_a_scenario,
        corpus_root=corpus_root,
    )
    stage_a_cost = float(stage_a_result.get("cost_usd") or 0.0)

    if stage_a_result.get("error"):
        print(
            f"[step2] INFRASTRUCTURE ERROR — Stage A failed: {stage_a_result['error']}",
            file=sys.stderr,
        )
        return {
            "infrastructure_error": True,
            "error": str(stage_a_result["error"]),
            "stage_a_cost_usd": stage_a_cost,
        }

    stage_a_events: list[dict[str, Any]] = list(stage_a_result.get("parsed_events") or [])
    stage_b_grading = _filter_grading_to_pcs(stage_b_gold.get("grading") or {})

    manifest = (
        pre_state_manifest
        if pre_state_manifest is not None
        else _resolve_pre_state_manifest_dict(stage_b_gold)
    )
    corpus_dir = build_pre_state_corpus(manifest=manifest)
    tool_trace, final_text, stage_b_cost, per_slug_skip, per_slug_diagnostics = (
        run_stage_b_events_driven_chain(
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


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Stage B: events-driven timeline pass benchmark"
    )
    parser.add_argument("--n", type=int, default=1, help="Cohort size (default: 1)")
    parser.add_argument("--model", type=str, default="", help="Model ID")
    parser.add_argument(
        "--scenario-json",
        type=Path,
        default=None,
        help="Path to Stage A gold scenario JSON (default: gold/session_events_session20.json)",
    )
    parser.add_argument(
        "--timeline-gold",
        type=Path,
        default=None,
        help=(
            "Path to timeline-pass grading JSON for Stage B (default: "
            "evals/session_recap_timeline_pass_vertical_slice/gold/timeline_pass_session20.json)"
        ),
    )
    parser.add_argument(
        "--pre-state-manifest",
        type=Path,
        default=None,
        help="Override pre-state manifest JSON (default: from timeline gold metadata)",
    )
    parser.add_argument("--runs-root", type=Path, default=None)
    parser.add_argument("--no-writes", action="store_true", help="Skip writing artifacts")
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

    client = OpenAI(api_key=api_key)

    stage_a_gold = load_stage_a_scenario(args.scenario_json)
    corpus_root = resolve_corpus_root()

    timeline_gold_path = (args.timeline_gold or _STAGE_B_GOLD_PATH).resolve()
    stage_b_gold = json.loads(timeline_gold_path.read_text(encoding="utf-8"))
    scenario_id = str(stage_b_gold.get("scenario_id") or timeline_gold_path.stem)

    manifest_override: dict[str, Any] | None = None
    if args.pre_state_manifest:
        manifest_override = json.loads(
            args.pre_state_manifest.read_text(encoding="utf-8")
        )

    model_id = _resolve_planner_model((args.model.strip() or None))
    n = max(1, int(args.n))

    if not args.quiet:
        print(f"[step2] n={n} model={model_id}", file=sys.stderr)

    summaries: list[Step2RunSummary] = []
    total_cohort_cost = 0.0
    pass_count = 0
    infra_error_count = 0

    for i in range(n):
        if not args.quiet:
            print(f"[step2] run {i + 1}/{n} starting…", file=sys.stderr)
        t0 = time.monotonic()

        result = _run_single_chained_cohort_iteration(
            client=client,
            model_id=model_id,
            stage_a_scenario=stage_a_gold,
            corpus_root=corpus_root,
            stage_b_gold=stage_b_gold,
            allow_corpus_writes=True,
            quiet=args.quiet,
            pre_state_manifest=manifest_override,
        )

        if result["infrastructure_error"]:
            infra_error_count += 1
            print(
                f"[step2] run {i + 1}/{n} INFRASTRUCTURE_ERROR — "
                f"Stage A failed: {result['error']} (excluded from denominator)",
                file=sys.stderr,
            )
            continue

        stage_a_cost = result["stage_a_cost_usd"]
        stage_b_cost = result["stage_b_cost_usd"]
        stage_a_event_count_run = result["stage_a_event_count"]
        per_slug_skip = result["per_slug_skip"]
        per_slug_diagnostics = result["per_slug_diagnostics"]
        violations = result["violations"]
        telemetry = result["telemetry"]
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
            f"[step2] run {i + 1}/{n} | "
            f"{'PASS' if gates_passed else 'FAIL'} | "
            f"events={stage_a_event_count_run} | "
            f"skips={skip_slugs} | "
            f"cost_usd={run_cost:.4f} | "
            f"elapsed={elapsed_s}s | "
            f"{verdict_str}"
        )

        if not args.no_writes:
            primary_md, sidecar_json, summary = write_step2_run_report(
                run_index=i if n > 1 else None,
                cohort_size=n if n > 1 else None,
                gates_passed=gates_passed,
                per_gate_verdict_map=verdict,
                violations=violations,
                grader_telemetry=telemetry,
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
                print(f"[step2] report: {primary_md}", file=sys.stderr)
                print(f"[step2] sidecar: {sidecar_json}", file=sys.stderr)
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

        # Absolute budget guard: abort if cumulative cost > $5.00
        if total_cohort_cost > 5.0 and i + 1 < n:
            print(
                f"[step2] STOP: cumulative cost ${total_cohort_cost:.2f} exceeds $5.00 "
                "absolute budget guard; skipping remaining cohort runs.",
                file=sys.stderr,
            )
            break

        # Relative budget guard: stop cohort if cost > $1.00 with 0 passes after run 2
        effective_runs = (i + 1) - infra_error_count
        if total_cohort_cost > 1.0 and pass_count == 0 and effective_runs >= 2 and i + 1 < n:
            print(
                f"[step2] STOP: cumulative cost ${total_cohort_cost:.2f} with 0 passes; "
                "skipping remaining cohort runs per budget guard.",
                file=sys.stderr,
            )
            break

    if n > 1 and summaries and not args.no_writes:
        md_s, json_s = write_step2_multi_summary(
            summaries,
            model_id=model_id,
            scenario_id=scenario_id,
            runs_root=args.runs_root,
        )
        print(f"[step2] cohort summary: {md_s}", file=sys.stderr)
        print(f"[step2] cohort sidecar: {json_s}", file=sys.stderr)

    effective_n = len(summaries)  # infra-error runs excluded from summaries
    print(
        f"[step2] cohort done | pass_rate={pass_count}/{effective_n} "
        f"(infra_errors={infra_error_count}) | "
        f"total_cost_usd=${total_cohort_cost:.4f}"
    )

    if summaries and not all(s.gates_passed for s in summaries):
        sys.exit(1)


if __name__ == "__main__":
    main()
