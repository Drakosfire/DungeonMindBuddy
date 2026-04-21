"""Offline tests for Stage-2 timeline-append grader."""

from __future__ import annotations

from pathlib import Path

from evals.session_recap_timeline_append_vertical_slice.grader import (
    collect_timeline_append_violations,
    collect_append_timeline_row_calls,
    find_session_table_row,
    grade_timeline_row_hybrid,
    parse_timeline_row_cells,
    violations_append_timeline_two_phase,
    violations_forbidden_tool_names,
)

_BEAT_RX = (
    "(?is)(?=.*Lysandra)(?=.*(forest|Mossford|camp|rocky|rockie|cult|tower|meat|antidote|charm|disorient|Sara|voice|blueprint))"
)


def test_parse_timeline_row_cells_three_columns() -> None:
    line = "| **20** | Lysandra at camp; forest recedes. | `Session 20 - Recap.md` |"
    a, b, c = parse_timeline_row_cells(line)  # type: ignore[misc]
    assert a == "**20**"
    assert "Lysandra" in b
    assert c == "`Session 20 - Recap.md`"


def test_grade_timeline_row_hybrid_passes() -> None:
    line = (
        "| **20** | Lysandra: **Mossford** defense concludes; rocky-talkie reunion; "
        "later found **charm**ed at camp with tower **blueprint** sketch. "
        "| `Session 20 - Recap.md` |"
    )
    assert not grade_timeline_row_hybrid(line, session=20, beat_regex=_BEAT_RX)


def test_grade_timeline_row_hybrid_recap_full_path_ok() -> None:
    line = (
        "| **20** | Lysandra and Mossford beat. | "
        "`Longmont Campaign/Campaign 2/Session Recaps/Session 20 - Recap.md` |"
    )
    assert not grade_timeline_row_hybrid(line, session=20, beat_regex=_BEAT_RX)


def test_grade_timeline_row_hybrid_missing_lysandra_fails() -> None:
    line = "| **20** | Mossford defense only. | `Session 20 - Recap.md` |"
    errs = grade_timeline_row_hybrid(line, session=20, beat_regex=_BEAT_RX)
    assert errs


def test_two_phase_requires_preview_and_commit() -> None:
    trace = [
        {
            "tool": "append_timeline_row",
            "arguments": {"dry_run": True, "npc_slug": "captain_lysandra_ironveil"},
            "output_excerpt": '{"ok": true, "phase": "preview", "confirm_token": "abc"}',
        },
        {
            "tool": "append_timeline_row",
            "arguments": {"dry_run": False, "npc_slug": "captain_lysandra_ironveil"},
            "output_excerpt": '{"ok": true, "phase": "committed"}',
        },
    ]
    assert not violations_append_timeline_two_phase(trace)


def test_two_phase_missing_commit() -> None:
    trace = [
        {
            "tool": "append_timeline_row",
            "arguments": {"dry_run": True},
            "output_excerpt": '{"ok": true, "phase": "preview", "confirm_token": "abc"}',
        },
    ]
    v = violations_append_timeline_two_phase(trace)
    assert v


def test_forbidden_tools() -> None:
    trace = [
        {"tool": "assemble_recap_draft", "arguments": {}, "output_excerpt": "{}"},
    ]
    v = violations_forbidden_tool_names(trace, ["assemble_recap_draft"])
    assert v


def test_collect_violations_writes_forbidden(tmp_path: Path) -> None:
    tl = tmp_path / "t.md"
    tl.write_text(
        "| Session | beat | Recap |\n|---|---|\n| **20** | Lysandra Mossford | `Session 20 - Recap.md` |\n",
        encoding="utf-8",
    )
    trace = [
        {
            "tool": "append_timeline_row",
            "arguments": {"dry_run": True},
            "output_excerpt": '{"ok": true, "phase": "preview", "confirm_token": "x"}',
        },
        {
            "tool": "append_timeline_row",
            "arguments": {"dry_run": False},
            "output_excerpt": '{"ok": true, "phase": "committed"}',
        },
        {
            "tool": "write_corpus_file",
            "arguments": {"path": "x.md"},
            "output_excerpt": "{}",
        },
    ]
    viol = collect_timeline_append_violations(
        corpus_dir=tmp_path,
        tool_trace=trace,
        grading={
            "timeline_relative_path": "t.md",
            "session": 20,
            "beat_regex": _BEAT_RX,
            "recap_filename": "Session 20 - Recap.md",
            "forbid_write_corpus_file": True,
            "forbid_recap_tools": [],
        },
    )
    assert "timeline_append_tool" in viol
    msgs = " ".join(viol["timeline_append_tool"])
    assert "write_corpus_file" in msgs


def test_find_session_row() -> None:
    text = "header\n| **19** | old | `Session 19 - Recap.md` |\n| **20** | Lysandra | `Session 20 - Recap.md` |\n"
    row = find_session_table_row(text, 20)
    assert row is not None
    assert "**20**" in row


def test_collect_append_timeline_row_calls_order() -> None:
    trace = [
        {"tool": "read_corpus_file", "arguments": {}, "output_excerpt": ""},
        {
            "tool": "append_timeline_row",
            "arguments": {"dry_run": True},
            "output_excerpt": '{"ok": true, "phase": "preview"}',
        },
    ]
    rows = collect_append_timeline_row_calls(trace)
    assert len(rows) == 1
