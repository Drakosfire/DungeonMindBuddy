"""Offline tests for Stage-2 v1 (autonomous timeline-pass) grader.

Iteration-6 rewrite: the gate is **count + flat-anchor-words** checked against
rows on disk, not regex against the model's tool trace. The dispatcher now runs
writes through a one-phase loopback, so two-phase enforcement and hub-proposal
flag completeness no longer apply at the grader. TP6 (pre-state shape) lives in
``test_timeline_pass_pre_state.py``.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from evals.session_recap_timeline_pass_vertical_slice.grader import (
    _appends_by_slug,
    _missing_anchor_words,
    collect_timeline_pass_violations,
    find_session_table_rows,
    grade_anchor_words_for_slug,
    per_gate_verdict,
    violations_hallucination_guard,
    violations_skip_targets,
)


# ---------------------------------------------------------------------------
# Anchor-word fixtures (gold-faithful)
# ---------------------------------------------------------------------------


_LYSANDRA_ANCHORS = ["tower", "Caelynn"]
_CAELYNN_ANCHORS = ["swarm", "Lysandra"]
_SARA_ANCHORS = ["Caelynn", "Lysandra"]
_KARSEMINE_ANCHORS = ["scimitar", "swarm"]
_EPHANNA_ANCHORS = ["blast", "swarm"]


def _committed_call(
    slug: str,
    *,
    timeline_path: str | None = None,
) -> list[dict[str, Any]]:
    """One ``append_timeline_row`` tool-trace row that resolved to a commit.

    Mirrors the dispatcher's autonomous-writes loopback: from the trace's
    perspective there is only the single call (the hidden preview→commit
    mechanics live below the dispatcher). The output excerpt mirrors the
    ``phase: "committed"`` shape the writer returns.
    """
    args: dict[str, Any] = {"npc_slug": slug, "session": 20}
    if timeline_path:
        args["timeline_path"] = timeline_path
    return [
        {
            "tool": "append_timeline_row",
            "arguments": args,
            "output_excerpt": json.dumps(
                {"ok": True, "phase": "committed", "path": timeline_path or ""}
            ),
        }
    ]


def _expected_grading() -> dict[str, Any]:
    return {
        "session": 20,
        "recap_filename": "Session 20 - Recap.md",
        "forbid_write_corpus_file": True,
        "forbid_recap_tools": [
            "assemble_recap_draft",
            "build_recap_write_payload",
            "get_recap_context",
        ],
        "allowed_npc_slugs": [
            "captain_lysandra_ironveil",
            "dustwalker",
            "sara_mirathorn_operator",
            "thrin_branchborn",
            "torbin_jove",
            "caelynn",
            "karsemine",
            "ephanna",
        ],
        "expected_appends": [
            {
                "npc_slug": "captain_lysandra_ironveil",
                "timeline_relative_path": "NPCs/captain_lysandra_ironveil/timeline.md",
                "expected_count": 1,
                "anchor_words": list(_LYSANDRA_ANCHORS),
            },
            {
                "npc_slug": "caelynn",
                "timeline_relative_path": "PCs/caelynn/timeline.md",
                "expected_count": 1,
                "anchor_words": list(_CAELYNN_ANCHORS),
            },
            {
                "npc_slug": "sara_mirathorn_operator",
                "timeline_relative_path": "NPCs/sara_mirathorn_operator/timeline.md",
                "expected_count": 1,
                "anchor_words": list(_SARA_ANCHORS),
            },
            {
                "npc_slug": "karsemine",
                "timeline_relative_path": "PCs/karsemine/timeline.md",
                "expected_count": 1,
                "anchor_words": list(_KARSEMINE_ANCHORS),
            },
            {
                "npc_slug": "ephanna",
                "timeline_relative_path": "PCs/ephanna/timeline.md",
                "expected_count": 1,
                "anchor_words": list(_EPHANNA_ANCHORS),
            },
        ],
        "expected_skips": [
            {
                "npc_slug": "dustwalker",
                "timeline_relative_path": "NPCs/dustwalker/timeline.md",
            },
            {
                "npc_slug": "torbin_jove",
                "timeline_relative_path": "NPCs/torbin_jove/timeline.md",
            },
            {
                "npc_slug": "thrin_branchborn",
                "timeline_relative_path": "NPCs/thrin_branchborn/timeline.md",
            },
        ],
    }


def _write_timeline(
    corpus: Path,
    rel: str,
    *,
    session_20_beats: list[str] | None = None,
) -> Path:
    """Write a 3-column timeline at ``rel`` with rows 18, 19, and 0+ Session 20 rows."""
    body = (
        "# timeline\n\n"
        "| Session | Beat | Recap |\n"
        "|---------|------|-------|\n"
        "| **18** | filler beat. | `Session 18 - Recap.md` |\n"
        "| **19** | filler beat. | `Session 19 - Recap.md` |\n"
    )
    for beat in session_20_beats or []:
        body += f"| **20** | {beat} | `Session 20 - Recap.md` |\n"
    path = corpus / rel
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(body, encoding="utf-8")
    return path


def _build_full_pass_corpus(corpus: Path) -> dict[str, Any]:
    """Write all 8 timelines (5 with anchor-rich Session-20 row, 3 without)."""
    grading = _expected_grading()
    _write_timeline(
        corpus,
        "NPCs/captain_lysandra_ironveil/timeline.md",
        session_20_beats=[
            "Lysandra: rescued at the tower-camp by Caelynn; antidote tea breaks the spell."
        ],
    )
    _write_timeline(
        corpus,
        "PCs/caelynn/timeline.md",
        session_20_beats=[
            "Caelynn: tanks the gnat swarm, breaks it with Thunderwave, then brews "
            "antidote tea for Lysandra."
        ],
    )
    _write_timeline(
        corpus,
        "NPCs/sara_mirathorn_operator/timeline.md",
        session_20_beats=[
            "Sara: connects Caelynn to Lysandra, relays the time-slip, transfers toward Tealeaf."
        ],
    )
    _write_timeline(
        corpus,
        "PCs/karsemine/timeline.md",
        session_20_beats=[
            "Karsemine: scimitar flurry on the gnat swarm — four solid hits — then leads tracking."
        ],
    )
    _write_timeline(
        corpus,
        "PCs/ephanna/timeline.md",
        session_20_beats=[
            "Ephanna: Eldritch Blasts knock clusters out of the swarm; Misty Steps clear."
        ],
    )
    _write_timeline(corpus, "NPCs/dustwalker/timeline.md")
    _write_timeline(corpus, "NPCs/torbin_jove/timeline.md")
    _write_timeline(corpus, "NPCs/thrin_branchborn/timeline.md")
    return grading


def _full_pass_tool_trace() -> list[dict[str, Any]]:
    out: list[dict[str, Any]] = []
    out += _committed_call("captain_lysandra_ironveil")
    out += _committed_call("caelynn", timeline_path="PCs/caelynn/timeline.md")
    out += _committed_call("sara_mirathorn_operator")
    out += _committed_call("karsemine", timeline_path="PCs/karsemine/timeline.md")
    out += _committed_call("ephanna", timeline_path="PCs/ephanna/timeline.md")
    return out


def _final_text_empty_unsure_queue() -> str:
    return json.dumps(
        {
            "user_intent": "planning_request",
            "message": "Done.",
            "unsure_queue": [],
        }
    )


# ---------------------------------------------------------------------------
# Per-helper unit tests
# ---------------------------------------------------------------------------


def test_appends_by_slug_groups_calls() -> None:
    trace = _committed_call("captain_lysandra_ironveil") + _committed_call("caelynn")
    grouped = _appends_by_slug(trace)
    assert set(grouped.keys()) == {"captain_lysandra_ironveil", "caelynn"}
    assert len(grouped["captain_lysandra_ironveil"]) == 1
    assert len(grouped["caelynn"]) == 1


def test_find_session_table_rows_collects_all(tmp_path: Path) -> None:
    p = _write_timeline(
        tmp_path,
        "NPCs/x/timeline.md",
        session_20_beats=["first beat", "second beat"],
    )
    rows = find_session_table_rows(p.read_text(encoding="utf-8"), 20)
    assert len(rows) == 2
    assert "first beat" in rows[0]
    assert "second beat" in rows[1]


def test_hallucination_guard_pass() -> None:
    allowed = ["captain_lysandra_ironveil", "dustwalker"]
    trace = _committed_call("captain_lysandra_ironveil")
    assert violations_hallucination_guard(trace, allowed) == []


def test_hallucination_guard_unknown_slug() -> None:
    allowed = ["captain_lysandra_ironveil"]
    trace = _committed_call("invented_npc")
    bad = violations_hallucination_guard(trace, allowed)
    assert any("invented_npc" in m for m in bad)
    assert any("not in allowed_npc_slugs" in m for m in bad)


def test_hallucination_guard_missing_slug_arg() -> None:
    allowed = ["captain_lysandra_ironveil"]
    trace = [
        {
            "tool": "append_timeline_row",
            "arguments": {},
            "output_excerpt": '{"ok": true, "phase": "committed"}',
        },
    ]
    bad = violations_hallucination_guard(trace, allowed)
    assert any("missing npc_slug" in m for m in bad)


def test_skip_targets_clean(tmp_path: Path) -> None:
    _write_timeline(tmp_path, "NPCs/dustwalker/timeline.md")
    _write_timeline(tmp_path, "NPCs/torbin_jove/timeline.md")
    skips = [
        {
            "npc_slug": "dustwalker",
            "timeline_relative_path": "NPCs/dustwalker/timeline.md",
        },
        {
            "npc_slug": "torbin_jove",
            "timeline_relative_path": "NPCs/torbin_jove/timeline.md",
        },
    ]
    assert violations_skip_targets(tmp_path, skips, 20) == []


def test_skip_targets_unexpected_row(tmp_path: Path) -> None:
    _write_timeline(
        tmp_path,
        "NPCs/dustwalker/timeline.md",
        session_20_beats=["Dustwalker: surprise beat."],
    )
    skips = [
        {
            "npc_slug": "dustwalker",
            "timeline_relative_path": "NPCs/dustwalker/timeline.md",
        },
    ]
    bad = violations_skip_targets(tmp_path, skips, 20)
    assert bad and "unexpected Session 20 row" in bad[0]


def test_skip_targets_missing_file(tmp_path: Path) -> None:
    skips = [
        {
            "npc_slug": "dustwalker",
            "timeline_relative_path": "NPCs/dustwalker/timeline.md",
        },
    ]
    bad = violations_skip_targets(tmp_path, skips, 20)
    assert bad and "skip-target timeline missing" in bad[0]


# ---------------------------------------------------------------------------
# Anchor-word grader unit tests
# ---------------------------------------------------------------------------


def test_grade_anchor_words_pass(tmp_path: Path) -> None:
    _write_timeline(
        tmp_path,
        "NPCs/captain_lysandra_ironveil/timeline.md",
        session_20_beats=[
            "Lysandra: rescued at the tower-camp by Caelynn; antidote tea breaks the spell."
        ],
    )
    spec = {
        "npc_slug": "captain_lysandra_ironveil",
        "timeline_relative_path": "NPCs/captain_lysandra_ironveil/timeline.md",
        "expected_count": 1,
        "anchor_words": list(_LYSANDRA_ANCHORS),
    }
    errs, count, missing = grade_anchor_words_for_slug(tmp_path, spec, 20)
    assert errs == []
    assert count == 1
    assert missing == []


def test_grade_anchor_words_missing_one_word_reports_it(tmp_path: Path) -> None:
    _write_timeline(
        tmp_path,
        "NPCs/captain_lysandra_ironveil/timeline.md",
        session_20_beats=[
            # Drop "tower" from the beat text; "Caelynn" is still present.
            "Lysandra: rescued by Caelynn at the dirt-camp; antidote tea breaks the spell."
        ],
    )
    spec = {
        "npc_slug": "captain_lysandra_ironveil",
        "timeline_relative_path": "NPCs/captain_lysandra_ironveil/timeline.md",
        "expected_count": 1,
        "anchor_words": list(_LYSANDRA_ANCHORS),
    }
    errs, count, missing = grade_anchor_words_for_slug(tmp_path, spec, 20)
    assert count == 1
    assert missing == ["tower"]
    assert errs and "tower" in errs[0]
    assert "captain_lysandra_ironveil" in errs[0]


def test_grade_anchor_words_zero_rows_fails(tmp_path: Path) -> None:
    _write_timeline(tmp_path, "NPCs/sara_mirathorn_operator/timeline.md")
    spec = {
        "npc_slug": "sara_mirathorn_operator",
        "timeline_relative_path": "NPCs/sara_mirathorn_operator/timeline.md",
        "expected_count": 1,
        "anchor_words": list(_SARA_ANCHORS),
    }
    errs, count, _missing = grade_anchor_words_for_slug(tmp_path, spec, 20)
    assert count == 0
    assert errs and "expected ≥1 row(s)" in errs[0]


def test_grade_anchor_words_multiple_rows_union_passes(tmp_path: Path) -> None:
    """Anchor words spread across multiple new rows still count as present."""
    _write_timeline(
        tmp_path,
        "NPCs/captain_lysandra_ironveil/timeline.md",
        session_20_beats=[
            "Lysandra: shimmering eyes; rescued by Caelynn.",
            "Lysandra: tower dirt sketch; antidote tea prepared.",
        ],
    )
    spec = {
        "npc_slug": "captain_lysandra_ironveil",
        "timeline_relative_path": "NPCs/captain_lysandra_ironveil/timeline.md",
        "expected_count": 1,
        "anchor_words": list(_LYSANDRA_ANCHORS),
    }
    errs, count, missing = grade_anchor_words_for_slug(tmp_path, spec, 20)
    assert errs == []
    assert count == 2
    assert missing == []


def test_grade_anchor_words_timeline_missing_fails(tmp_path: Path) -> None:
    spec = {
        "npc_slug": "captain_lysandra_ironveil",
        "timeline_relative_path": "NPCs/captain_lysandra_ironveil/timeline.md",
        "expected_count": 1,
        "anchor_words": list(_LYSANDRA_ANCHORS),
    }
    errs, _count, _missing = grade_anchor_words_for_slug(tmp_path, spec, 20)
    assert errs and "timeline file missing" in errs[0]


# ---------------------------------------------------------------------------
# SKIP correctness unit tests (positive + negative pair)
# ---------------------------------------------------------------------------


def test_skip_correctness_zero_new_rows_passes(tmp_path: Path) -> None:
    _write_timeline(tmp_path, "NPCs/dustwalker/timeline.md")
    skips = [
        {
            "npc_slug": "dustwalker",
            "timeline_relative_path": "NPCs/dustwalker/timeline.md",
        }
    ]
    assert violations_skip_targets(tmp_path, skips, 20) == []


def test_skip_correctness_false_commit_fails(tmp_path: Path) -> None:
    _write_timeline(
        tmp_path,
        "NPCs/dustwalker/timeline.md",
        session_20_beats=["Dustwalker: false commit beat."],
    )
    skips = [
        {
            "npc_slug": "dustwalker",
            "timeline_relative_path": "NPCs/dustwalker/timeline.md",
        }
    ]
    bad = violations_skip_targets(tmp_path, skips, 20)
    assert bad and "dustwalker" in bad[0]
    assert "unexpected Session 20 row" in bad[0]


# ---------------------------------------------------------------------------
# Integration: full pass / per-gate verdict
# ---------------------------------------------------------------------------


def test_collect_violations_full_pass(tmp_path: Path) -> None:
    grading = _build_full_pass_corpus(tmp_path)
    trace = _full_pass_tool_trace()
    viol, telemetry = collect_timeline_pass_violations(
        corpus_dir=tmp_path,
        tool_trace=trace,
        final_text=_final_text_empty_unsure_queue(),
        grading=grading,
    )
    assert viol == {}, viol
    assert telemetry["per_slug_new_row_count"] == {
        "captain_lysandra_ironveil": 1,
        "caelynn": 1,
        "sara_mirathorn_operator": 1,
        "karsemine": 1,
        "ephanna": 1,
    }
    assert all(v == [] for v in telemetry["per_slug_anchor_words_missing"].values())
    verdict = per_gate_verdict(viol)
    assert verdict == {"TP1": "PASS", "TP2": "PASS", "TP3": "PASS", "TP5": "PASS"}


def test_collect_violations_caelynn_zero_rows_TP1_only(tmp_path: Path) -> None:
    """Reproduce the historical PC-allowlist blocker symptom: zero Caelynn row."""
    grading = _build_full_pass_corpus(tmp_path)
    _write_timeline(tmp_path, "PCs/caelynn/timeline.md")
    trace = _full_pass_tool_trace()
    viol, telemetry = collect_timeline_pass_violations(
        corpus_dir=tmp_path,
        tool_trace=trace,
        final_text=_final_text_empty_unsure_queue(),
        grading=grading,
    )
    assert "timeline_pass_append" in viol
    msgs = " ".join(viol["timeline_pass_append"])
    assert "caelynn" in msgs
    assert "expected ≥1 row(s)" in msgs
    assert telemetry["per_slug_new_row_count"]["caelynn"] == 0
    verdict = per_gate_verdict(viol)
    assert verdict == {"TP1": "FAIL", "TP2": "PASS", "TP3": "PASS", "TP5": "PASS"}


def test_collect_violations_TP3_write_corpus_file_fails(tmp_path: Path) -> None:
    grading = _build_full_pass_corpus(tmp_path)
    trace = _full_pass_tool_trace() + [
        {
            "tool": "write_corpus_file",
            "arguments": {"path": "Longmont Campaign/Campaign 2/Session Recaps/Session 20 - Recap.md"},
            "output_excerpt": "{}",
        }
    ]
    viol, _telemetry = collect_timeline_pass_violations(
        corpus_dir=tmp_path,
        tool_trace=trace,
        final_text=_final_text_empty_unsure_queue(),
        grading=grading,
    )
    assert "timeline_pass_tool" in viol
    verdict = per_gate_verdict(viol)
    assert verdict["TP3"] == "FAIL"
    assert verdict["TP5"] == "PASS"


def test_collect_violations_TP5_hallucinated_slug(tmp_path: Path) -> None:
    grading = _build_full_pass_corpus(tmp_path)
    trace = _full_pass_tool_trace() + _committed_call("invented_npc")
    viol, _telemetry = collect_timeline_pass_violations(
        corpus_dir=tmp_path,
        tool_trace=trace,
        final_text=_final_text_empty_unsure_queue(),
        grading=grading,
    )
    assert "timeline_pass_tool" in viol
    verdict = per_gate_verdict(viol)
    assert verdict["TP5"] == "FAIL"


def test_collect_violations_TP2_skip_violation(tmp_path: Path) -> None:
    grading = _build_full_pass_corpus(tmp_path)
    _write_timeline(
        tmp_path,
        "NPCs/dustwalker/timeline.md",
        session_20_beats=["Dustwalker: should not be here."],
    )
    trace = _full_pass_tool_trace()
    viol, _telemetry = collect_timeline_pass_violations(
        corpus_dir=tmp_path,
        tool_trace=trace,
        final_text=_final_text_empty_unsure_queue(),
        grading=grading,
    )
    assert "timeline_pass_skip" in viol
    verdict = per_gate_verdict(viol)
    assert verdict["TP2"] == "FAIL"


def test_collect_violations_TP1_anchor_words_missing(tmp_path: Path) -> None:
    grading = _build_full_pass_corpus(tmp_path)
    _write_timeline(
        tmp_path,
        "NPCs/captain_lysandra_ironveil/timeline.md",
        session_20_beats=[
            "Lysandra: a meandering filler line with nothing recognizable."
        ],
    )
    trace = _full_pass_tool_trace()
    viol, telemetry = collect_timeline_pass_violations(
        corpus_dir=tmp_path,
        tool_trace=trace,
        final_text=_final_text_empty_unsure_queue(),
        grading=grading,
    )
    assert "timeline_pass_append" in viol
    msgs = " ".join(viol["timeline_pass_append"])
    assert "captain_lysandra_ironveil" in msgs
    assert "missing anchor words" in msgs
    missing = telemetry["per_slug_anchor_words_missing"]["captain_lysandra_ironveil"]
    assert set(missing) == set(_LYSANDRA_ANCHORS)


def test_collect_violations_TP1_missing_per_npc_row(tmp_path: Path) -> None:
    grading = _build_full_pass_corpus(tmp_path)
    _write_timeline(tmp_path, "NPCs/sara_mirathorn_operator/timeline.md")
    trace = _full_pass_tool_trace()
    viol, telemetry = collect_timeline_pass_violations(
        corpus_dir=tmp_path,
        tool_trace=trace,
        final_text=_final_text_empty_unsure_queue(),
        grading=grading,
    )
    assert "timeline_pass_append" in viol
    msgs = " ".join(viol["timeline_pass_append"])
    assert "sara_mirathorn_operator" in msgs
    assert "expected ≥1 row(s)" in msgs
    assert telemetry["per_slug_new_row_count"]["sara_mirathorn_operator"] == 0


def test_collect_violations_TP3_forbidden_recap_tools(tmp_path: Path) -> None:
    grading = _build_full_pass_corpus(tmp_path)
    for name in ("assemble_recap_draft", "build_recap_write_payload", "get_recap_context"):
        trace = _full_pass_tool_trace() + [
            {"tool": name, "arguments": {}, "output_excerpt": "{}"}
        ]
        viol, _telemetry = collect_timeline_pass_violations(
            corpus_dir=tmp_path,
            tool_trace=trace,
            final_text=_final_text_empty_unsure_queue(),
            grading=grading,
        )
        assert "timeline_pass_tool" in viol, name
        msgs = " ".join(viol["timeline_pass_tool"])
        assert name in msgs
        verdict = per_gate_verdict(viol)
        assert verdict["TP3"] == "FAIL"


def test_missing_anchor_words_normalizes_smart_apostrophe() -> None:
    assert _missing_anchor_words(
        "Wizard\u2019s Tower",
        ["Wizard's Tower"],
    ) == []
    assert _missing_anchor_words(
        "River's Edge",
        ["River\u2019s Edge"],
    ) == []


def test_missing_anchor_words_swarm_accepts_red_gnats_synonym() -> None:
    assert _missing_anchor_words("Karsemine cuts through red gnats at the edge", ["swarm"]) == []
    assert _missing_anchor_words("Karsemine cuts through red-gnats at the edge", ["swarm"]) == []
    assert _missing_anchor_words("A red gnat bites Karsemine.", ["swarm"]) == []
    assert _missing_anchor_words("No combat described here.", ["swarm"]) == ["swarm"]
