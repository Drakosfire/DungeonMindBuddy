"""Mechanical grader for Stage-2 timeline-append vertical slice (hybrid row + two-phase tools)."""

from __future__ import annotations

import json
import re
from pathlib import Path
from typing import Any

_RECAP_CELL_RE = re.compile(
    r"^`(.*Session 20 - Recap\.md)`\s*$",
    re.IGNORECASE,
)


def _dry_run_arg(args: dict[str, Any]) -> bool:
    v = args.get("dry_run", True)
    if isinstance(v, bool):
        return v
    if isinstance(v, str):
        return v.strip().lower() in ("true", "1", "yes", "on")
    return bool(v)


def _commit_outcome(row: dict[str, Any]) -> dict[str, Any]:
    excerpt = str(row.get("output_excerpt", "") or "").strip()
    if excerpt.startswith("Error:"):
        return {"succeeded": False, "phase": None, "error": excerpt}
    try:
        obj = json.loads(excerpt) if excerpt else {}
    except json.JSONDecodeError:
        return {"succeeded": None, "phase": None, "error": "unparseable"}
    if not isinstance(obj, dict):
        return {"succeeded": None, "phase": None, "error": "not_dict"}
    ok = obj.get("ok")
    phase = obj.get("phase") if isinstance(obj.get("phase"), str) else None
    err = obj.get("error") if isinstance(obj.get("error"), str) else None
    if ok is True and phase == "committed":
        return {"succeeded": True, "phase": phase, "error": None}
    if ok is False:
        return {"succeeded": False, "phase": phase, "error": err or ""}
    return {"succeeded": None, "phase": phase, "error": err}


def _iter_tool_trace(
    tool_trace: list[dict[str, Any]],
) -> list[tuple[int, str, dict[str, Any], dict[str, Any]]]:
    out: list[tuple[int, str, dict[str, Any], dict[str, Any]]] = []
    for i, row in enumerate(tool_trace or []):
        name = str(row.get("tool", "") or "")
        raw = row.get("arguments")
        args = raw if isinstance(raw, dict) else {}
        out.append((i, name, args, row))
    return out


def collect_append_timeline_row_calls(
    tool_trace: list[dict[str, Any]],
) -> list[tuple[int, dict[str, Any], dict[str, Any]]]:
    return [(i, a, r) for i, _n, a, r in _iter_tool_trace(tool_trace) if _n == "append_timeline_row"]


def violations_append_timeline_two_phase(
    tool_trace: list[dict[str, Any]],
    *,
    preview_required: bool = True,
    commit_required: bool = True,
) -> list[str]:
    rows = collect_append_timeline_row_calls(tool_trace)
    if not rows:
        return [
            "timeline_append: no append_timeline_row calls in tool_trace "
            "(expected preview and commit for Lysandra Session 20)."
        ]
    previews = [(i, a, r) for i, a, r in rows if _dry_run_arg(a)]
    commits = [(i, a, r) for i, a, r in rows if not _dry_run_arg(a)]
    hard: list[str] = []
    if preview_required and not previews:
        hard.append(
            "timeline_append: no append_timeline_row dry_run=true preview found "
            f"(saw {len(rows)} call(s))."
        )
    if commit_required:
        if not commits:
            hard.append(
                "timeline_append: no append_timeline_row dry_run=false commit found."
            )
        else:
            first_idx, first_args, _ = rows[0]
            last_idx, last_args, _ = rows[-1]
            if not _dry_run_arg(first_args):
                hard.append(
                    f"timeline_append: first append_timeline_row at index {first_idx} "
                    "must be dry_run=true preview."
                )
            if _dry_run_arg(last_args):
                hard.append(
                    f"timeline_append: last append_timeline_row at index {last_idx} "
                    "must be dry_run=false commit."
                )
            _ci, _ca, last_row = commits[-1]
            outcome = _commit_outcome(last_row)
            if outcome["succeeded"] is False:
                err = (outcome.get("error") or "").strip()
                hard.append(
                    "timeline_append: last append_timeline_row commit did not succeed "
                    f"(server error: {err!r})."
                )
            elif outcome["succeeded"] is None:
                hard.append(
                    "timeline_append: could not parse last append_timeline_row commit response."
                )
    return hard


def violations_forbid_write_corpus_file(tool_trace: list[dict[str, Any]]) -> list[str]:
    """Stage-2 contract: no ``write_corpus_file`` (timeline append uses ``append_timeline_row`` only)."""
    bad: list[str] = []
    for i, name, args, _row in _iter_tool_trace(tool_trace):
        if name != "write_corpus_file":
            continue
        path = str(args.get("path", "") or "")
        bad.append(
            f"timeline_append: write_corpus_file at index {i} for {path!r} is forbidden "
            "(use append_timeline_row for timeline rows; do not rewrite the recap)."
        )
    return bad


def find_session_table_row(text: str, session: int) -> str | None:
    for line in text.splitlines():
        if re.match(rf"^\| \*\*{session}\*\* \|", line.strip()):
            return line
    return None


def parse_timeline_row_cells(line: str) -> tuple[str, str, str] | None:
    """Return (session_cell, beat_cell, recap_cell) or None if not 3+ pipe segments."""
    parts = line.split("|")
    if len(parts) < 4:
        return None
    cells = [p.strip() for p in parts[1:-1]]
    if len(cells) < 3:
        return None
    return cells[0], cells[1], " | ".join(cells[2:]) if len(cells) > 3 else cells[2]


def grade_timeline_row_hybrid(
    line: str,
    *,
    session: int,
    beat_regex: str,
    recap_filename: str = "Session 20 - Recap.md",
) -> list[str]:
    """Hybrid rubric: session cell + recap cell schema; beat non-empty + regex anchors."""
    errs: list[str] = []
    parsed = parse_timeline_row_cells(line)
    if parsed is None:
        return [f"timeline_row: could not parse 3-column table row from: {line!r}"]
    sess_cell, beat_cell, recap_cell = parsed
    want_sess = f"**{session}**"
    if sess_cell.strip() != want_sess:
        errs.append(
            f"timeline_row: session cell expected {want_sess!r}, got {sess_cell!r}"
        )
    if not beat_cell.strip():
        errs.append("timeline_row: beat cell empty")
    else:
        try:
            if not re.search(beat_regex, beat_cell):
                errs.append(
                    f"timeline_row: beat did not match anchor regex (Lysandra + context): {beat_regex!r}"
                )
        except re.error as exc:
            errs.append(f"timeline_row: invalid beat_regex: {exc}")
    m = _RECAP_CELL_RE.match(recap_cell.strip())
    if not m:
        errs.append(
            f"timeline_row: recap cell must be backticked path ending with "
            f"{recap_filename!r}, got {recap_cell!r}"
        )
    elif m.group(1).replace("\\", "/").split("/")[-1].lower() != recap_filename.lower():
        errs.append(
            f"timeline_row: recap basename must be {recap_filename!r}, "
            f"parsed {m.group(1)!r}"
        )
    return errs


def violations_forbidden_tool_names(
    tool_trace: list[dict[str, Any]],
    names: list[str],
) -> list[str]:
    forbidden = {n.strip() for n in names if str(n).strip()}
    if not forbidden:
        return []
    bad: list[str] = []
    for i, name, _args, _row in _iter_tool_trace(tool_trace):
        if name in forbidden:
            bad.append(
                f"timeline_append: tool {name!r} at index {i} is forbidden for this turn."
            )
    return bad


def collect_timeline_append_violations(
    *,
    corpus_dir: Path,
    tool_trace: list[dict[str, Any]],
    grading: dict[str, Any],
) -> dict[str, list[str]]:
    """Return violation buckets compatible with :class:`evals.planner_slice.live_eval.LiveEvalResult`."""
    out: dict[str, list[str]] = {}
    tl_rel = str(grading.get("timeline_relative_path") or "").strip()
    session = int(grading.get("session") or 20)
    beat_rx = str(grading.get("beat_regex") or "")
    recap_fn = str(grading.get("recap_filename") or "Session 20 - Recap.md")
    forbid_wcf = bool(grading.get("forbid_write_corpus_file", True))
    forbid_names = list(grading.get("forbid_recap_tools") or [])

    tool_v = violations_append_timeline_two_phase(tool_trace)
    tool_v.extend(violations_forbidden_tool_names(tool_trace, forbid_names))
    if forbid_wcf:
        tool_v.extend(violations_forbid_write_corpus_file(tool_trace))
    if tool_v:
        out["timeline_append_tool"] = tool_v

    path = corpus_dir / tl_rel.replace("\\", "/").strip("/")
    if not path.is_file():
        out.setdefault("timeline_append_row", []).append(
            f"timeline file missing at {tl_rel!r}"
        )
        return out
    body = path.read_text(encoding="utf-8")
    row_line = find_session_table_row(body, session)
    if not row_line:
        out.setdefault("timeline_append_row", []).append(
            f"no table row for session {session} in {tl_rel}"
        )
        return out
    row_errs = grade_timeline_row_hybrid(
        row_line, session=session, beat_regex=beat_rx, recap_filename=recap_fn
    )
    if row_errs:
        out["timeline_append_row"] = row_errs
    return out
