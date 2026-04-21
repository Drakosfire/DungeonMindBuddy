"""Offline tests for Stage-2 v1 (autonomous timeline-pass) grader.

Synthetic tool traces + scratch corpus dirs cover TP1-TP5 logic without any
LLM calls. TP6 (pre-state shape) lives in ``test_timeline_pass_pre_state.py``.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import pytest

from evals.session_recap_timeline_pass_vertical_slice.grader import (
    _appends_by_slug,
    collect_timeline_pass_violations,
    parse_planner_unsure_queue,
    per_gate_verdict,
    soft_flag_telemetry,
    violations_flag_completeness,
    violations_hallucination_guard,
    violations_skip_targets,
    violations_two_phase_for_slug,
)


# ---------------------------------------------------------------------------
# Test fixtures (gold-faithful)
# ---------------------------------------------------------------------------


_LYSANDRA_RX = (
    "(?is)(?=.*Lysandra)(?=.*(forest|Mossford|camp|rocky|rockie|cult|tower|"
    "meat|antidote|charm|disorient|Sara|voice|blueprint|shimmer))"
)
_CAELYNN_RX = (
    "(?is)(?=.*[Cc]aelynn)(?=.*(Thunderwave|swarm|antidote|tea|bracelet|Marla|"
    "rockie|rocky|Sara|Lysandra|tower|blueprint))"
)
_SARA_RX = (
    "(?is)(?=.*Sara)(?=.*(Lysandra|Caelynn|tainted|jerky|trust|Tealeaf|"
    "transfer|patch|rockie|rocky))"
)
_THRIN_RX = (
    "(?is)(?=.*Thrin)(?=.*(bow|gnat|swarm|Ephanna|watch|town|Lysandra|leave))"
)


def _ok_two_phase(
    slug: str,
    *,
    timeline_path: str | None = None,
) -> list[dict[str, Any]]:
    args_common = {"npc_slug": slug, "session": 20}
    if timeline_path:
        args_common["timeline_path"] = timeline_path
    preview_args = dict(args_common, dry_run=True)
    commit_args = dict(args_common, dry_run=False, confirm_token="ct")
    return [
        {
            "tool": "append_timeline_row",
            "arguments": preview_args,
            "output_excerpt": json.dumps(
                {"ok": True, "phase": "preview", "confirm_token": "ct"}
            ),
        },
        {
            "tool": "append_timeline_row",
            "arguments": commit_args,
            "output_excerpt": json.dumps({"ok": True, "phase": "committed"}),
        },
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
        ],
        "expected_appends": [
            {
                "npc_slug": "captain_lysandra_ironveil",
                "timeline_relative_path": "NPCs/captain_lysandra_ironveil/timeline.md",
                "beat_regex": _LYSANDRA_RX,
            },
            {
                "npc_slug": "caelynn",
                "timeline_relative_path": "PCs/caelynn/timeline.md",
                "beat_regex": _CAELYNN_RX,
            },
            {
                "npc_slug": "sara_mirathorn_operator",
                "timeline_relative_path": "NPCs/sara_mirathorn_operator/timeline.md",
                "beat_regex": _SARA_RX,
            },
            {
                "npc_slug": "thrin_branchborn",
                "timeline_relative_path": "NPCs/thrin_branchborn/timeline.md",
                "beat_regex": _THRIN_RX,
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
        ],
        "expected_hub_proposals_must": ["karsemine", "ephanna", "stafl", "marla"],
        "expected_hub_proposals_soft": ["stuart", "stacey"],
    }


def _write_timeline(
    corpus: Path,
    rel: str,
    *,
    include_session_20_for: str | None = None,
) -> Path:
    """Write a 3-column timeline at ``rel`` with rows 18, 19, and optionally 20."""
    body = (
        "# timeline\n\n"
        "| Session | Beat | Recap |\n"
        "|---------|------|-------|\n"
        "| **18** | filler beat. | `Session 18 - Recap.md` |\n"
        "| **19** | filler beat. | `Session 19 - Recap.md` |\n"
    )
    if include_session_20_for:
        body += (
            f"| **20** | {include_session_20_for} | `Session 20 - Recap.md` |\n"
        )
    path = corpus / rel
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(body, encoding="utf-8")
    return path


def _build_full_pass_corpus(corpus: Path) -> dict[str, Any]:
    """Write all 6 timelines (4 with a Session-20 row matching the regex; 2 without)."""
    grading = _expected_grading()
    # APPEND targets — beat lines crafted to match each per-NPC regex
    _write_timeline(
        corpus,
        "NPCs/captain_lysandra_ironveil/timeline.md",
        include_session_20_for=(
            "Lysandra: shimmer-eyed at camp; tower blueprint sketch; Sara patches her in."
        ),
    )
    _write_timeline(
        corpus,
        "PCs/caelynn/timeline.md",
        include_session_20_for=(
            "Caelynn: Thunderwave splits swarm; tea antidote on Lysandra; bracelet calms Marla."
        ),
    )
    _write_timeline(
        corpus,
        "NPCs/sara_mirathorn_operator/timeline.md",
        include_session_20_for=(
            "Sara patches Lysandra; tainted jerky news; Tealeaf transfer."
        ),
    )
    _write_timeline(
        corpus,
        "NPCs/thrin_branchborn/timeline.md",
        include_session_20_for=(
            "Thrin: bow shots vs gnat swarm; Ephanna keeps watch as party leaves town."
        ),
    )
    # SKIP targets — no Session 20 row
    _write_timeline(corpus, "NPCs/dustwalker/timeline.md")
    _write_timeline(corpus, "NPCs/torbin_jove/timeline.md")
    return grading


def _full_pass_tool_trace() -> list[dict[str, Any]]:
    out: list[dict[str, Any]] = []
    out += _ok_two_phase("captain_lysandra_ironveil")
    out += _ok_two_phase("caelynn", timeline_path="PCs/caelynn/timeline.md")
    out += _ok_two_phase("sara_mirathorn_operator")
    out += _ok_two_phase("thrin_branchborn")
    return out


def _good_unsure_queue_text() -> str:
    queue = [
        {
            "id": "hub_proposal_karsemine",
            "question": "hub-proposal: karsemine — prominent in S20 swarm fight; no NPC hub.",
            "default_summary": "Create empty NPCs/karsemine/{README.md,timeline.md} skeleton.",
            "alternative_summaries": ["Defer until next session.", "Promote seed only."],
        },
        {
            "id": "hub_proposal_ephanna",
            "question": "hub-proposal: ephanna — drives Misty Step + watch on Thrin.",
            "default_summary": "Create empty NPCs/ephanna/{README.md,timeline.md} skeleton.",
            "alternative_summaries": ["Defer.", "Hub seed only."],
        },
        {
            "id": "hub_proposal_stafl",
            "question": "hub-proposal: stafl — directs preparations and finds tainted jerky.",
            "default_summary": "Create empty NPCs/stafl/{README.md,timeline.md} skeleton.",
            "alternative_summaries": ["Defer.", "Hub seed only."],
        },
        {
            "id": "hub_proposal_marla",
            "question": "hub-proposal: marla — Mossford workforce conflict with Bonogo.",
            "default_summary": "Promote Mossford NPCs/marla_brambleback to full hub.",
            "alternative_summaries": ["Leave as seed only.", "Defer."],
        },
    ]
    return json.dumps(
        {
            "user_intent": "planning_request",
            "message": "Done; see queue.",
            "unsure_queue": queue,
        }
    )


# ---------------------------------------------------------------------------
# Per-helper unit tests
# ---------------------------------------------------------------------------


def test_appends_by_slug_groups_calls() -> None:
    trace = _ok_two_phase("captain_lysandra_ironveil") + _ok_two_phase("caelynn")
    grouped = _appends_by_slug(trace)
    assert set(grouped.keys()) == {"captain_lysandra_ironveil", "caelynn"}
    assert len(grouped["captain_lysandra_ironveil"]) == 2
    assert len(grouped["caelynn"]) == 2


def test_two_phase_for_slug_pass() -> None:
    trace = _ok_two_phase("thrin_branchborn")
    grouped = _appends_by_slug(trace)
    errs = violations_two_phase_for_slug(
        "thrin_branchborn", grouped["thrin_branchborn"]
    )
    assert errs == []


def test_two_phase_for_slug_missing_commit() -> None:
    trace = [
        {
            "tool": "append_timeline_row",
            "arguments": {"dry_run": True, "npc_slug": "dustwalker"},
            "output_excerpt": '{"ok": true, "phase": "preview", "confirm_token": "x"}',
        },
    ]
    grouped = _appends_by_slug(trace)
    errs = violations_two_phase_for_slug("dustwalker", grouped["dustwalker"])
    assert any("no dry_run=false commit" in e for e in errs)


def test_two_phase_for_slug_commit_failed() -> None:
    trace = [
        {
            "tool": "append_timeline_row",
            "arguments": {"dry_run": True, "npc_slug": "captain_lysandra_ironveil"},
            "output_excerpt": '{"ok": true, "phase": "preview", "confirm_token": "x"}',
        },
        {
            "tool": "append_timeline_row",
            "arguments": {"dry_run": False, "npc_slug": "captain_lysandra_ironveil"},
            "output_excerpt": '{"ok": false, "phase": "rejected", "error": "append mode is not allowed for this path"}',
        },
    ]
    grouped = _appends_by_slug(trace)
    errs = violations_two_phase_for_slug(
        "captain_lysandra_ironveil", grouped["captain_lysandra_ironveil"]
    )
    assert any("did not succeed" in e for e in errs)


def test_two_phase_no_calls_for_slug() -> None:
    errs = violations_two_phase_for_slug("ghost_npc", [])
    assert any("no append_timeline_row calls" in e for e in errs)


def test_hallucination_guard_pass() -> None:
    allowed = ["captain_lysandra_ironveil", "dustwalker"]
    trace = _ok_two_phase("captain_lysandra_ironveil")
    assert violations_hallucination_guard(trace, allowed) == []


def test_hallucination_guard_unknown_slug() -> None:
    allowed = ["captain_lysandra_ironveil"]
    trace = _ok_two_phase("invented_npc")
    bad = violations_hallucination_guard(trace, allowed)
    assert any("invented_npc" in m for m in bad)
    assert any("not in allowed_npc_slugs" in m for m in bad)


def test_hallucination_guard_missing_slug_arg() -> None:
    allowed = ["captain_lysandra_ironveil"]
    trace = [
        {
            "tool": "append_timeline_row",
            "arguments": {"dry_run": True},
            "output_excerpt": '{"ok": true, "phase": "preview"}',
        },
    ]
    bad = violations_hallucination_guard(trace, allowed)
    assert any("missing npc_slug" in m for m in bad)


def test_parse_planner_unsure_queue_handles_null() -> None:
    txt = json.dumps(
        {"user_intent": "planning_request", "message": "ok", "unsure_queue": None}
    )
    assert parse_planner_unsure_queue(txt) == []


def test_parse_planner_unsure_queue_handles_garbage() -> None:
    assert parse_planner_unsure_queue("not json {") is None
    assert parse_planner_unsure_queue("") is None


def test_flag_completeness_full_pass() -> None:
    txt = _good_unsure_queue_text()
    errs, found = violations_flag_completeness(
        txt, ["karsemine", "ephanna", "stafl", "marla"]
    )
    assert errs == []
    assert all(found.values())


def test_flag_completeness_missing_one() -> None:
    queue = [
        {
            "id": "hub_proposal_karsemine",
            "question": "hub-proposal: karsemine — needed.",
            "default_summary": "create skeleton",
            "alternative_summaries": ["a", "b"],
        }
    ]
    txt = json.dumps(
        {
            "user_intent": "planning_request",
            "message": "x",
            "unsure_queue": queue,
        }
    )
    errs, found = violations_flag_completeness(
        txt, ["karsemine", "ephanna"]
    )
    assert errs and "ephanna" in errs[0]
    assert found["karsemine"] is True
    assert found["ephanna"] is False


def test_flag_completeness_unparseable_final_text() -> None:
    errs, _found = violations_flag_completeness(
        "not json", ["karsemine"]
    )
    assert errs and "not parseable" in errs[0]


def test_soft_flag_telemetry_substring_match() -> None:
    txt = _good_unsure_queue_text()
    out = soft_flag_telemetry(txt, ["stuart", "stacey"])
    assert out == {"stuart": False, "stacey": False}
    queue = json.loads(txt)["unsure_queue"]
    queue.append(
        {
            "id": "hub_proposal_stuart",
            "question": "hub-proposal: stuart — bonogo proxy in S20.",
            "default_summary": "create",
            "alternative_summaries": ["a", "b"],
        }
    )
    new_txt = json.dumps(
        {"user_intent": "planning_request", "message": "x", "unsure_queue": queue}
    )
    out2 = soft_flag_telemetry(new_txt, ["stuart", "stacey"])
    assert out2["stuart"] is True
    assert out2["stacey"] is False


def test_flag_completeness_requires_hub_proposal_prefix() -> None:
    """A bare mention of `karsemine` without the `hub-proposal:` prefix must
    NOT count toward TP4 (regression of the iteration-1 over-permissive substring
    match)."""
    queue = [
        {
            "id": "review_karsemine_actions",
            "question": "Karsemine led the swarm fight; how should we follow up?",
            "default_summary": "Note their actions in S20.",
            "alternative_summaries": ["Skip.", "Add to journal."],
        }
    ]
    txt = json.dumps(
        {
            "user_intent": "planning_request",
            "message": "see queue",
            "unsure_queue": queue,
        }
    )
    errs, found = violations_flag_completeness(txt, ["karsemine"])
    assert errs and "karsemine" in errs[0]
    assert found["karsemine"] is False


def test_flag_completeness_accepts_properly_prefixed_entry() -> None:
    """A queue entry whose `question` starts with `hub-proposal:` and contains
    the must-flag name within its flattened text counts toward TP4."""
    queue = [
        {
            "id": "hub_proposal_karsemine",
            "question": "hub-proposal: karsemine — combat lead in S20.",
            "default_summary": "Create empty NPCs/karsemine/{README.md,timeline.md}.",
            "alternative_summaries": ["Defer.", "Promote seed only."],
        }
    ]
    txt = json.dumps(
        {
            "user_intent": "planning_request",
            "message": "see queue",
            "unsure_queue": queue,
        }
    )
    errs, found = violations_flag_completeness(txt, ["karsemine"])
    assert errs == []
    assert found["karsemine"] is True


def test_flag_completeness_prefix_case_insensitive_and_tolerates_leading_ws() -> None:
    queue = [
        {
            "id": "hub_proposal_ephanna",
            "question": "  Hub-Proposal: ephanna — Eldritch Blast vs swarm.",
            "default_summary": "create",
            "alternative_summaries": ["a", "b"],
        }
    ]
    txt = json.dumps(
        {
            "user_intent": "planning_request",
            "message": "x",
            "unsure_queue": queue,
        }
    )
    errs, found = violations_flag_completeness(txt, ["ephanna"])
    assert errs == []
    assert found["ephanna"] is True


def test_flag_completeness_slug_must_appear_in_qualifying_entry() -> None:
    """A `hub-proposal:`-prefixed entry that doesn't mention the must-flag slug
    cannot satisfy that slug, even if the slug appears in some other (non-prefixed)
    entry."""
    queue = [
        {
            "id": "hub_proposal_ephanna",
            "question": "hub-proposal: ephanna — Eldritch Blasts vs swarm.",
            "default_summary": "create",
            "alternative_summaries": ["a", "b"],
        },
        {
            "id": "follow_up_karsemine",
            "question": "Should we follow up on karsemine next session?",
            "default_summary": "...",
            "alternative_summaries": ["a", "b"],
        },
    ]
    txt = json.dumps(
        {
            "user_intent": "planning_request",
            "message": "x",
            "unsure_queue": queue,
        }
    )
    errs, found = violations_flag_completeness(txt, ["ephanna", "karsemine"])
    assert errs and "karsemine" in errs[0]
    assert found["ephanna"] is True
    assert found["karsemine"] is False


def test_soft_flag_telemetry_requires_hub_proposal_prefix() -> None:
    """Soft flags follow the same prefix contract as must-flags."""
    queue = [
        {
            "id": "review_stuart",
            "question": "Stuart appeared briefly in S20; reach out to him?",
            "default_summary": "...",
            "alternative_summaries": ["a", "b"],
        }
    ]
    txt = json.dumps(
        {"user_intent": "planning_request", "message": "x", "unsure_queue": queue}
    )
    out = soft_flag_telemetry(txt, ["stuart"])
    assert out == {"stuart": False}


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
        include_session_20_for="Dustwalker: surprise beat.",
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
# Integration: full pass / per-gate verdict
# ---------------------------------------------------------------------------


def test_collect_violations_full_pass(tmp_path: Path) -> None:
    grading = _build_full_pass_corpus(tmp_path)
    trace = _full_pass_tool_trace()
    final_text = _good_unsure_queue_text()
    viol, telemetry = collect_timeline_pass_violations(
        corpus_dir=tmp_path,
        tool_trace=trace,
        final_text=final_text,
        grading=grading,
    )
    assert viol == {}, viol
    assert all(telemetry["must_flags_found"].values())
    verdict = per_gate_verdict(viol)
    assert verdict == {"TP1": "PASS", "TP2": "PASS", "TP3": "PASS", "TP4": "PASS", "TP5": "PASS"}


def test_collect_violations_caelynn_commit_fails_TP1_only(tmp_path: Path) -> None:
    """Reproduce the known PC-allowlist blocker: Caelynn commit refused."""
    grading = _build_full_pass_corpus(tmp_path)
    # Strip the Caelynn 20-row to simulate the writer refusing the commit
    p = tmp_path / "PCs/caelynn/timeline.md"
    p.write_text(
        "# timeline\n\n"
        "| Session | Beat | Recap |\n"
        "|---------|------|-------|\n"
        "| **18** | filler. | `Session 18 - Recap.md` |\n"
        "| **19** | filler. | `Session 19 - Recap.md` |\n",
        encoding="utf-8",
    )
    trace = _full_pass_tool_trace()
    # Replace caelynn commit with a server rejection
    for row in trace:
        if (
            row["tool"] == "append_timeline_row"
            and row["arguments"].get("npc_slug") == "caelynn"
            and row["arguments"].get("dry_run") is False
        ):
            row["output_excerpt"] = json.dumps(
                {
                    "ok": False,
                    "phase": "rejected",
                    "error": "append mode is not allowed for this path",
                }
            )
    viol, _telemetry = collect_timeline_pass_violations(
        corpus_dir=tmp_path,
        tool_trace=trace,
        final_text=_good_unsure_queue_text(),
        grading=grading,
    )
    assert "timeline_pass_append" in viol
    msgs = " ".join(viol["timeline_pass_append"])
    assert "caelynn" in msgs
    verdict = per_gate_verdict(viol)
    assert verdict["TP1"] == "FAIL"
    # TP2, TP3, TP4, TP5 should still pass
    assert verdict["TP2"] == "PASS"
    assert verdict["TP3"] == "PASS"
    assert verdict["TP4"] == "PASS"
    assert verdict["TP5"] == "PASS"


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
        final_text=_good_unsure_queue_text(),
        grading=grading,
    )
    assert "timeline_pass_tool" in viol
    verdict = per_gate_verdict(viol)
    assert verdict["TP3"] == "FAIL"
    assert verdict["TP5"] == "PASS"


def test_collect_violations_TP5_hallucinated_slug(tmp_path: Path) -> None:
    grading = _build_full_pass_corpus(tmp_path)
    trace = _full_pass_tool_trace() + _ok_two_phase("invented_npc")
    viol, _telemetry = collect_timeline_pass_violations(
        corpus_dir=tmp_path,
        tool_trace=trace,
        final_text=_good_unsure_queue_text(),
        grading=grading,
    )
    assert "timeline_pass_tool" in viol
    verdict = per_gate_verdict(viol)
    assert verdict["TP5"] == "FAIL"


def test_collect_violations_TP2_skip_violation(tmp_path: Path) -> None:
    grading = _build_full_pass_corpus(tmp_path)
    # Mutate dustwalker to add a session-20 row (skip violation)
    _write_timeline(
        tmp_path,
        "NPCs/dustwalker/timeline.md",
        include_session_20_for="Dustwalker: should not be here.",
    )
    trace = _full_pass_tool_trace()
    viol, _telemetry = collect_timeline_pass_violations(
        corpus_dir=tmp_path,
        tool_trace=trace,
        final_text=_good_unsure_queue_text(),
        grading=grading,
    )
    assert "timeline_pass_skip" in viol
    verdict = per_gate_verdict(viol)
    assert verdict["TP2"] == "FAIL"


def test_collect_violations_TP4_missing_flags(tmp_path: Path) -> None:
    grading = _build_full_pass_corpus(tmp_path)
    trace = _full_pass_tool_trace()
    skinny_text = json.dumps(
        {
            "user_intent": "planning_request",
            "message": "done",
            "unsure_queue": [],
        }
    )
    viol, _telemetry = collect_timeline_pass_violations(
        corpus_dir=tmp_path,
        tool_trace=trace,
        final_text=skinny_text,
        grading=grading,
    )
    assert "timeline_pass_flags" in viol
    verdict = per_gate_verdict(viol)
    assert verdict["TP4"] == "FAIL"


def test_collect_violations_TP1_missing_per_npc_row(tmp_path: Path) -> None:
    grading = _build_full_pass_corpus(tmp_path)
    # Erase Sara's S20 row to mimic dropped commit
    _write_timeline(tmp_path, "NPCs/sara_mirathorn_operator/timeline.md")
    trace = _full_pass_tool_trace()
    viol, _telemetry = collect_timeline_pass_violations(
        corpus_dir=tmp_path,
        tool_trace=trace,
        final_text=_good_unsure_queue_text(),
        grading=grading,
    )
    assert "timeline_pass_append" in viol
    msgs = " ".join(viol["timeline_pass_append"])
    assert "sara_mirathorn_operator" in msgs
    assert "no row for session 20" in msgs


def test_collect_violations_TP1_beat_regex_mismatch(tmp_path: Path) -> None:
    grading = _build_full_pass_corpus(tmp_path)
    # Lysandra row exists but lacks any anchor keyword
    _write_timeline(
        tmp_path,
        "NPCs/captain_lysandra_ironveil/timeline.md",
        include_session_20_for="Lysandra: a meandering filler line with nothing recognizable.",
    )
    trace = _full_pass_tool_trace()
    viol, _telemetry = collect_timeline_pass_violations(
        corpus_dir=tmp_path,
        tool_trace=trace,
        final_text=_good_unsure_queue_text(),
        grading=grading,
    )
    assert "timeline_pass_append" in viol
    msgs = " ".join(viol["timeline_pass_append"])
    assert "captain_lysandra_ironveil" in msgs
    assert "anchor regex" in msgs


@pytest.mark.parametrize("name", ["assemble_recap_draft", "build_recap_write_payload", "get_recap_context"])
def test_collect_violations_TP3_forbidden_recap_tool(tmp_path: Path, name: str) -> None:
    grading = _build_full_pass_corpus(tmp_path)
    trace = _full_pass_tool_trace() + [
        {"tool": name, "arguments": {}, "output_excerpt": "{}"}
    ]
    viol, _telemetry = collect_timeline_pass_violations(
        corpus_dir=tmp_path,
        tool_trace=trace,
        final_text=_good_unsure_queue_text(),
        grading=grading,
    )
    assert "timeline_pass_tool" in viol
    msgs = " ".join(viol["timeline_pass_tool"])
    assert name in msgs
    verdict = per_gate_verdict(viol)
    assert verdict["TP3"] == "FAIL"
