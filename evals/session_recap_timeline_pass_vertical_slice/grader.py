"""Mechanical grader for Stage-2 v1 (autonomous timeline-pass) vertical slice.

Reuses v0 row-level / two-phase helpers from
``evals.session_recap_timeline_append_vertical_slice.grader`` for the per-NPC
hybrid rubric and forbidden-tool check; this module adds:

* TP1 multi-NPC APPEND completeness (preview→commit pair per expected target,
  hybrid row rubric per target)
* TP2 SKIP correctness (no Session-N row landed in skip-target timelines)
* TP3 tool contract aggregated across all expected appends
* TP4 FLAG completeness — must-flag hub proposals appear (case-insensitive
  substring match) in the model's ``unsure_queue``
* TP5 hallucination guard — every commit's ``npc_slug`` must be in the
  scenario ``allowed_npc_slugs``
"""

from __future__ import annotations

import json
import re
from pathlib import Path
from typing import Any

from evals.session_recap_timeline_append_vertical_slice.grader import (
    _commit_outcome,
    _dry_run_arg,
    _iter_tool_trace,
    find_session_table_row,
    grade_timeline_row_hybrid,
    violations_forbid_write_corpus_file,
    violations_forbidden_tool_names,
)


# ---------------------------------------------------------------------------
# Tool-trace helpers (multi-NPC)
# ---------------------------------------------------------------------------


def _appends_by_slug(
    tool_trace: list[dict[str, Any]],
) -> dict[str, list[tuple[int, dict[str, Any], dict[str, Any]]]]:
    """Group ``append_timeline_row`` calls by ``npc_slug`` (preserving order)."""
    out: dict[str, list[tuple[int, dict[str, Any], dict[str, Any]]]] = {}
    for i, name, args, row in _iter_tool_trace(tool_trace):
        if name != "append_timeline_row":
            continue
        slug = str(args.get("npc_slug", "") or "").strip()
        out.setdefault(slug, []).append((i, args, row))
    return out


def violations_two_phase_for_slug(
    slug: str,
    calls: list[tuple[int, dict[str, Any], dict[str, Any]]],
) -> list[str]:
    """Per-slug two-phase contract: preview present, commit present, last commit ok."""
    if not calls:
        return [f"timeline_pass: no append_timeline_row calls for slug {slug!r}"]
    previews = [(i, a, r) for i, a, r in calls if _dry_run_arg(a)]
    commits = [(i, a, r) for i, a, r in calls if not _dry_run_arg(a)]
    hard: list[str] = []
    if not previews:
        hard.append(
            f"timeline_pass[{slug}]: no dry_run=true preview "
            f"(saw {len(calls)} call(s))"
        )
    if not commits:
        hard.append(f"timeline_pass[{slug}]: no dry_run=false commit")
        return hard
    first_idx, first_args, _ = calls[0]
    last_idx, last_args, _ = calls[-1]
    if not _dry_run_arg(first_args):
        hard.append(
            f"timeline_pass[{slug}]: first call at index {first_idx} must be dry_run=true preview"
        )
    if _dry_run_arg(last_args):
        hard.append(
            f"timeline_pass[{slug}]: last call at index {last_idx} must be dry_run=false commit"
        )
    _ci, _ca, last_row = commits[-1]
    outcome = _commit_outcome(last_row)
    if outcome["succeeded"] is False:
        err = (outcome.get("error") or "").strip()
        hard.append(
            f"timeline_pass[{slug}]: last commit did not succeed (server error: {err!r})"
        )
    elif outcome["succeeded"] is None:
        hard.append(
            f"timeline_pass[{slug}]: could not parse last commit response"
        )
    return hard


def violations_hallucination_guard(
    tool_trace: list[dict[str, Any]],
    allowed_slugs: list[str],
) -> list[str]:
    """TP5: commits to a path/slug outside the allowed set are a hard fail."""
    allowed = {str(s).strip().lower() for s in allowed_slugs if str(s).strip()}
    if not allowed:
        return []
    bad: list[str] = []
    for i, name, args, _row in _iter_tool_trace(tool_trace):
        if name != "append_timeline_row":
            continue
        slug = str(args.get("npc_slug", "") or "").strip().lower()
        if not slug:
            bad.append(
                f"timeline_pass: append_timeline_row at index {i} missing npc_slug "
                "(hallucination guard)"
            )
            continue
        if slug not in allowed:
            bad.append(
                f"timeline_pass: append_timeline_row at index {i} uses npc_slug {slug!r} "
                f"not in allowed_npc_slugs={sorted(allowed)!r}"
            )
    return bad


# ---------------------------------------------------------------------------
# unsure_queue parsing (TP4)
# ---------------------------------------------------------------------------


def parse_planner_unsure_queue(final_text: str) -> list[dict[str, Any]] | None:
    """Return the ``unsure_queue`` list from the planner's final JSON (or ``None``)."""
    if not final_text or not final_text.strip():
        return None
    try:
        obj = json.loads(final_text)
    except json.JSONDecodeError:
        return None
    if not isinstance(obj, dict):
        return None
    raw = obj.get("unsure_queue")
    if raw is None:
        return []
    if not isinstance(raw, list):
        return None
    out: list[dict[str, Any]] = []
    for item in raw:
        if isinstance(item, dict):
            out.append(item)
    return out


def _flatten_queue_text(item: dict[str, Any]) -> str:
    parts: list[str] = []
    for key in ("id", "question", "default_summary"):
        val = item.get(key)
        if isinstance(val, str):
            parts.append(val)
    alt = item.get("alternative_summaries")
    if isinstance(alt, list):
        for v in alt:
            if isinstance(v, str):
                parts.append(v)
    return " | ".join(parts).lower()


# TP4 requires the literal `hub-proposal:` prefix at the start of the queue
# entry's `question` field (case-insensitive on the token, colon mandatory).
# Whitespace before the prefix is tolerated so reasonable formatting still
# qualifies. See `Docs/Plans/REPORT-Timeline-Pass-Live-2026-04-21.md` Iteration
# 2 for the rationale (substring matching was both too lenient and too strict).
_HUB_PROPOSAL_PREFIX_RE = re.compile(r"^\s*hub-proposal\s*:", re.IGNORECASE)


def _entry_qualifies_as_hub_proposal(item: dict[str, Any]) -> bool:
    """Return ``True`` only if the queue item's ``question`` field starts with
    the literal ``hub-proposal:`` prefix (case-insensitive on the token)."""
    q = item.get("question")
    if not isinstance(q, str):
        return False
    return bool(_HUB_PROPOSAL_PREFIX_RE.match(q))


def violations_flag_completeness(
    final_text: str,
    must_names: list[str],
) -> tuple[list[str], dict[str, bool]]:
    """TP4: every must-name appears in a properly-prefixed hub-proposal queue item.

    A queue item only counts toward TP4 when its ``question`` field begins with
    the literal ``hub-proposal:`` prefix (see ``_HUB_PROPOSAL_PREFIX_RE``). The
    must-name (slug or surface name, case-insensitive) must appear within the
    same qualifying entry's flattened text (``id`` + ``question`` +
    ``default_summary`` + ``alternative_summaries``).
    """
    queue = parse_planner_unsure_queue(final_text)
    found_map: dict[str, bool] = {n: False for n in must_names}
    if queue is None:
        return (
            [
                "timeline_pass[flags]: final_text is not parseable JSON or "
                "unsure_queue is malformed (cannot evaluate hub proposals)"
            ],
            found_map,
        )
    qualifying = [it for it in queue if _entry_qualifies_as_hub_proposal(it)]
    blob_per_item = [_flatten_queue_text(it) for it in qualifying]
    for name in must_names:
        needle = name.strip().lower()
        if not needle:
            found_map[name] = True
            continue
        if any(needle in b for b in blob_per_item):
            found_map[name] = True
    missing = [n for n, ok in found_map.items() if not ok]
    if missing:
        return (
            [
                "timeline_pass[flags]: missing `hub-proposal:`-prefixed queue "
                "entries for: " + ", ".join(missing)
            ],
            found_map,
        )
    return [], found_map


def soft_flag_telemetry(
    final_text: str,
    soft_names: list[str],
) -> dict[str, bool]:
    """Telemetry-only soft flags. Same prefix contract as TP4 must-flags."""
    queue = parse_planner_unsure_queue(final_text) or []
    qualifying = [it for it in queue if _entry_qualifies_as_hub_proposal(it)]
    blob_per_item = [_flatten_queue_text(it) for it in qualifying]
    out: dict[str, bool] = {}
    for name in soft_names:
        needle = name.strip().lower()
        out[name] = bool(needle) and any(needle in b for b in blob_per_item)
    return out


# ---------------------------------------------------------------------------
# Skip-target check (TP2)
# ---------------------------------------------------------------------------


def violations_skip_targets(
    corpus_dir: Path,
    skips: list[dict[str, Any]],
    session: int,
) -> list[str]:
    """TP2: ensure no ``**{session}**`` row was injected into skip-target timelines."""
    bad: list[str] = []
    for spec in skips or []:
        rel = str(spec.get("timeline_relative_path") or "").strip()
        slug = str(spec.get("npc_slug") or "").strip()
        if not rel:
            continue
        path = corpus_dir / rel.replace("\\", "/").strip("/")
        if not path.is_file():
            bad.append(
                f"timeline_pass[skip][{slug}]: skip-target timeline missing at {rel!r}"
            )
            continue
        body = path.read_text(encoding="utf-8")
        if find_session_table_row(body, session):
            bad.append(
                f"timeline_pass[skip][{slug}]: unexpected Session {session} row landed in {rel!r}"
            )
    return bad


# ---------------------------------------------------------------------------
# APPEND completeness (TP1) — orchestrates per-NPC hybrid rubric + per-NPC two-phase
# ---------------------------------------------------------------------------


def _append_row_violations(
    corpus_dir: Path,
    spec: dict[str, Any],
    session: int,
    recap_filename: str,
) -> list[str]:
    rel = str(spec.get("timeline_relative_path") or "").strip()
    slug = str(spec.get("npc_slug") or "").strip()
    beat_rx = str(spec.get("beat_regex") or "")
    if not rel:
        return [f"timeline_pass[append][{slug}]: scenario missing timeline_relative_path"]
    path = corpus_dir / rel.replace("\\", "/").strip("/")
    if not path.is_file():
        return [f"timeline_pass[append][{slug}]: timeline file missing at {rel!r}"]
    body = path.read_text(encoding="utf-8")
    row_line = find_session_table_row(body, session)
    if not row_line:
        return [f"timeline_pass[append][{slug}]: no row for session {session} in {rel!r}"]
    row_errs = grade_timeline_row_hybrid(
        row_line, session=session, beat_regex=beat_rx, recap_filename=recap_filename
    )
    return [f"timeline_pass[append][{slug}]: {msg}" for msg in row_errs]


# ---------------------------------------------------------------------------
# Top-level orchestration
# ---------------------------------------------------------------------------


def collect_timeline_pass_violations(
    *,
    corpus_dir: Path,
    tool_trace: list[dict[str, Any]],
    final_text: str,
    grading: dict[str, Any],
) -> tuple[dict[str, list[str]], dict[str, Any]]:
    """Return ``(violations, telemetry)`` for the live runner.

    Buckets (gate IDs in parentheses):
      * ``timeline_pass_tool``   — TP3 (forbidden tools) + TP5 (hallucination guard)
      * ``timeline_pass_append`` — TP1 (per-NPC two-phase + hybrid row)
      * ``timeline_pass_skip``   — TP2 (no row in skip-target)
      * ``timeline_pass_flags``  — TP4 (must-flag hub proposals)
    """
    out: dict[str, list[str]] = {}
    telemetry: dict[str, Any] = {}
    session = int(grading.get("session") or 20)
    recap_fn = str(grading.get("recap_filename") or "Session 20 - Recap.md")

    forbid_wcf = bool(grading.get("forbid_write_corpus_file", True))
    forbid_names = list(grading.get("forbid_recap_tools") or [])
    allowed_slugs = list(grading.get("allowed_npc_slugs") or [])
    expected_appends = list(grading.get("expected_appends") or [])
    expected_skips = list(grading.get("expected_skips") or [])
    must_flags = list(grading.get("expected_hub_proposals_must") or [])
    soft_flags = list(grading.get("expected_hub_proposals_soft") or [])

    tool_v: list[str] = []
    tool_v.extend(violations_forbidden_tool_names(tool_trace, forbid_names))
    if forbid_wcf:
        tool_v.extend(violations_forbid_write_corpus_file(tool_trace))
    tool_v.extend(violations_hallucination_guard(tool_trace, allowed_slugs))
    if tool_v:
        out["timeline_pass_tool"] = tool_v

    by_slug = _appends_by_slug(tool_trace)
    expected_slug_set = {
        str(spec.get("npc_slug", "") or "").strip()
        for spec in expected_appends
        if str(spec.get("npc_slug", "") or "").strip()
    }
    append_v: list[str] = []
    per_slug_two_phase: dict[str, list[str]] = {}
    for spec in expected_appends:
        slug = str(spec.get("npc_slug", "") or "").strip()
        if not slug:
            continue
        calls = by_slug.get(slug, [])
        two_phase_errs = violations_two_phase_for_slug(slug, calls)
        per_slug_two_phase[slug] = two_phase_errs
        append_v.extend(two_phase_errs)
        append_v.extend(_append_row_violations(corpus_dir, spec, session, recap_fn))

    if append_v:
        out["timeline_pass_append"] = append_v

    skip_v = violations_skip_targets(corpus_dir, expected_skips, session)
    if skip_v:
        out["timeline_pass_skip"] = skip_v

    flag_v, must_found = violations_flag_completeness(final_text, must_flags)
    if flag_v:
        out["timeline_pass_flags"] = flag_v

    telemetry["per_slug_two_phase_violation_counts"] = {
        slug: len(errs) for slug, errs in per_slug_two_phase.items()
    }
    telemetry["expected_append_slugs"] = sorted(expected_slug_set)
    telemetry["seen_append_slugs"] = sorted(by_slug.keys())
    telemetry["must_flags_found"] = must_found
    telemetry["soft_flags_found"] = soft_flag_telemetry(final_text, soft_flags)
    return out, telemetry


# ---------------------------------------------------------------------------
# Per-gate verdict (used by the runner / report writer)
# ---------------------------------------------------------------------------


def per_gate_verdict(violations: dict[str, list[str]]) -> dict[str, str]:
    """Map TP gate ID → ``"PASS"`` or ``"FAIL"`` based on bucketed violations.

    TP3 and TP5 share the ``timeline_pass_tool`` bucket; we tease them apart
    by message-prefix matching so the report shows independent verdicts.
    """
    tool_msgs = list(violations.get("timeline_pass_tool", []))
    halluc = [m for m in tool_msgs if "hallucination guard" in m or "not in allowed_npc_slugs" in m]
    forbidden = [m for m in tool_msgs if m not in halluc]

    return {
        "TP1": "FAIL" if violations.get("timeline_pass_append") else "PASS",
        "TP2": "FAIL" if violations.get("timeline_pass_skip") else "PASS",
        "TP3": "FAIL" if forbidden else "PASS",
        "TP4": "FAIL" if violations.get("timeline_pass_flags") else "PASS",
        "TP5": "FAIL" if halluc else "PASS",
    }


__all__ = [
    "_appends_by_slug",
    "collect_timeline_pass_violations",
    "parse_planner_unsure_queue",
    "per_gate_verdict",
    "soft_flag_telemetry",
    "violations_flag_completeness",
    "violations_hallucination_guard",
    "violations_skip_targets",
    "violations_two_phase_for_slug",
]
