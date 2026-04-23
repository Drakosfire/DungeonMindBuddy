"""Mechanical grader for Stage-2 v1 (autonomous timeline-pass) vertical slice.

Iteration-6 rewrite: TP1 is now ``count + flat-anchor-words`` checked against
**rows on disk**, not regex against the model's tool trace. The model writes
through the dispatcher's autonomous-writes loopback (one-phase), so this grader
inspects the post-run corpus instead of reasoning about preview/commit pairs.
TP4 (hub-proposal must-flag completeness) was removed in this iteration —
hub-proposal scope is out of this slice until timelines are reliably passing.

Gates:
* TP1 — every ``expected_appends`` entry has at least ``expected_count`` new
  rows for the target session in its timeline file, and every word in
  ``anchor_words`` appears (case-insensitive substring) at least once across
  the union of those new rows' beat-cell content.
* TP2 — no ``expected_skips`` timeline gained a row for the target session.
* TP3 — the model did not call any forbidden recap-write tools and did not
  call ``write_corpus_file`` for the recap.
* TP5 — every ``append_timeline_row`` call's ``npc_slug`` is in
  ``allowed_npc_slugs``.
* TP6 — pre-state shape (covered by ``tests/test_timeline_pass_pre_state.py``,
  not this module).
"""

from __future__ import annotations

import re
from pathlib import Path
from typing import Any

from evals.session_recap_timeline_append_vertical_slice.grader import (
    _iter_tool_trace,
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
# Row scanning (TP1, TP2)
# ---------------------------------------------------------------------------


_ROW_HEADER_RE = re.compile(r"^\| \*\*(\d+)\*\* \|")


def find_session_table_rows(text: str, session: int) -> list[str]:
    """Return every table row whose first cell is ``**<session>**`` (in order)."""
    rows: list[str] = []
    for raw_line in text.splitlines():
        line = raw_line.strip()
        m = _ROW_HEADER_RE.match(line)
        if not m:
            continue
        if int(m.group(1)) == session:
            rows.append(line)
    return rows


def _parse_beat_cell(line: str) -> str:
    """Return the beat (second) cell from a 3-column table row, or ``""``."""
    parts = line.split("|")
    if len(parts) < 4:
        return ""
    cells = [p.strip() for p in parts[1:-1]]
    if len(cells) < 2:
        return ""
    return cells[1]


def _missing_anchor_words(beat_text: str, anchors: list[str]) -> list[str]:
    """Case-insensitive substring check; U+2019 apostrophes normalize to ASCII '."""
    haystack = beat_text.lower().replace("\u2019", "'")
    missing: list[str] = []
    for word in anchors:
        needle = str(word or "").strip().lower().replace("\u2019", "'")
        if not needle:
            continue
        if needle not in haystack:
            missing.append(str(word))
    return missing


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
        rows = find_session_table_rows(body, session)
        if rows:
            bad.append(
                f"timeline_pass[skip][{slug}]: unexpected Session {session} row landed in {rel!r} "
                f"(found {len(rows)} row(s))"
            )
    return bad


# ---------------------------------------------------------------------------
# APPEND completeness (TP1) — count + flat-anchor-words on rows on disk
# ---------------------------------------------------------------------------


def grade_anchor_words_for_slug(
    corpus_dir: Path,
    spec: dict[str, Any],
    session: int,
) -> tuple[list[str], int, list[str]]:
    """Return ``(violations, new_row_count, missing_anchor_words)`` for one expected target.

    Violations are populated when:
    * the timeline file does not exist
    * fewer than ``expected_count`` new session rows were appended
    * one or more ``anchor_words`` are missing from the union of new rows'
      beat-cell text (case-insensitive substring match)
    """
    rel = str(spec.get("timeline_relative_path") or "").strip()
    slug = str(spec.get("npc_slug") or "").strip()
    expected_count = int(spec.get("expected_count", 1) or 1)
    anchors_raw = spec.get("anchor_words") or []
    anchors = [str(a) for a in anchors_raw if str(a or "").strip()]
    if not rel:
        return (
            [f"timeline_pass[append][{slug}]: scenario missing timeline_relative_path"],
            0,
            list(anchors),
        )
    path = corpus_dir / rel.replace("\\", "/").strip("/")
    if not path.is_file():
        return (
            [f"timeline_pass[append][{slug}]: timeline file missing at {rel!r}"],
            0,
            list(anchors),
        )
    body = path.read_text(encoding="utf-8")
    rows = find_session_table_rows(body, session)
    new_count = len(rows)
    errs: list[str] = []
    if new_count < expected_count:
        errs.append(
            f"timeline_pass[append][{slug}]: expected ≥{expected_count} row(s) for "
            f"session {session} in {rel!r}, found {new_count}"
        )
        return errs, new_count, list(anchors)
    union_beat = " ".join(_parse_beat_cell(line) for line in rows)
    missing = _missing_anchor_words(union_beat, anchors)
    if missing:
        errs.append(
            f"timeline_pass[append][{slug}]: missing anchor words "
            f"{missing!r} in session {session} beat text "
            f"(checked across {new_count} row(s) in {rel!r})"
        )
    return errs, new_count, missing


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
      * ``timeline_pass_append`` — TP1 (count + anchor-words on rows on disk)
      * ``timeline_pass_skip``   — TP2 (no row in skip-target)

    ``final_text`` is unused after the Iteration-6 hub-proposal removal but is
    kept in the signature so callers don't have to change shape; it is logged
    in artifacts via the runner, not graded here.
    """
    _ = final_text
    out: dict[str, list[str]] = {}
    telemetry: dict[str, Any] = {}
    session = int(grading.get("session") or 20)

    forbid_wcf = bool(grading.get("forbid_write_corpus_file", True))
    forbid_names = list(grading.get("forbid_recap_tools") or [])
    allowed_slugs = list(grading.get("allowed_npc_slugs") or [])
    expected_appends = list(grading.get("expected_appends") or [])
    expected_skips = list(grading.get("expected_skips") or [])

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
    per_slug_anchor_words_missing: dict[str, list[str]] = {}
    per_slug_new_row_count: dict[str, int] = {}
    for spec in expected_appends:
        slug = str(spec.get("npc_slug", "") or "").strip()
        if not slug:
            continue
        errs, new_count, missing = grade_anchor_words_for_slug(
            corpus_dir, spec, session
        )
        per_slug_new_row_count[slug] = new_count
        per_slug_anchor_words_missing[slug] = missing
        append_v.extend(errs)

    if append_v:
        out["timeline_pass_append"] = append_v

    skip_v = violations_skip_targets(corpus_dir, expected_skips, session)
    if skip_v:
        out["timeline_pass_skip"] = skip_v

    telemetry["expected_append_slugs"] = sorted(expected_slug_set)
    telemetry["seen_append_slugs"] = sorted(by_slug.keys())
    telemetry["per_slug_new_row_count"] = per_slug_new_row_count
    telemetry["per_slug_anchor_words_missing"] = per_slug_anchor_words_missing
    return out, telemetry


# ---------------------------------------------------------------------------
# Per-gate verdict (used by the runner / report writer)
# ---------------------------------------------------------------------------


def per_gate_verdict(violations: dict[str, list[str]]) -> dict[str, str]:
    """Map TP gate ID → ``"PASS"`` or ``"FAIL"`` based on bucketed violations.

    TP3 and TP5 share the ``timeline_pass_tool`` bucket; we tease them apart by
    message-prefix matching so the report shows independent verdicts. TP4 was
    removed in Iteration 6.
    """
    tool_msgs = list(violations.get("timeline_pass_tool", []))
    halluc = [m for m in tool_msgs if "hallucination guard" in m or "not in allowed_npc_slugs" in m]
    forbidden = [m for m in tool_msgs if m not in halluc]

    return {
        "TP1": "FAIL" if violations.get("timeline_pass_append") else "PASS",
        "TP2": "FAIL" if violations.get("timeline_pass_skip") else "PASS",
        "TP3": "FAIL" if forbidden else "PASS",
        "TP5": "FAIL" if halluc else "PASS",
    }


__all__ = [
    "_appends_by_slug",
    "collect_timeline_pass_violations",
    "find_session_table_rows",
    "grade_anchor_words_for_slug",
    "per_gate_verdict",
    "violations_hallucination_guard",
    "violations_skip_targets",
]
