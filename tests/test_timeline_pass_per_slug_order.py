"""Offline checks for Stage-2 v1 per-slug chain ordering."""

from __future__ import annotations

from pathlib import Path

from evals.session_recap_timeline_pass_vertical_slice.step1_timeline_pass_run import (
    load_scenario,
    ordered_timeline_targets,
    recap_relative_path_from_grading,
)


def test_ordered_timeline_targets_matches_gold_user_message_order() -> None:
    gold_path = (
        Path(__file__).resolve().parents[1]
        / "evals"
        / "session_recap_timeline_pass_vertical_slice"
        / "gold"
        / "timeline_pass_session20.json"
    )
    sc = load_scenario(gold_path)
    grading = sc["grading"]
    targets = ordered_timeline_targets(grading)
    slugs = [str(t.get("npc_slug")) for t in targets]
    assert slugs == [
        "captain_lysandra_ironveil",
        "dustwalker",
        "sara_mirathorn_operator",
        "thrin_branchborn",
        "torbin_jove",
        "caelynn",
        "karsemine",
        "ephanna",
    ]


def test_recap_relative_path_from_grading() -> None:
    assert recap_relative_path_from_grading({"recap_filename": "Session 20 - Recap.md"}) == (
        "Longmont Campaign/Campaign 2/Session Recaps/Session 20 - Recap.md"
    )
