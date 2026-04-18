"""Smoke tests for session recap ingest eval scaffold."""

from __future__ import annotations

from evals.session_recap_ingest_vertical_slice.step0_pre_state import build_pre_state_corpus
from evals.session_recap_ingest_vertical_slice.step3_unsure_queue_grading import grade_unsure_queue


def test_pre_state_manifest_removes_session_20_recap(tmp_path) -> None:
    root = build_pre_state_corpus(tmp_dir=tmp_path)
    recap = (
        root
        / "Longmont Campaign/Campaign 2/Session Recaps/Session 20 - Recap.md"
    )
    assert not recap.is_file()


def test_grade_unsure_queue_matches_gold_example() -> None:
    items = [
        {
            "id": "tower_blueprint_placement",
            "question": "Place the tower blueprint under Locations or Session Prep?",
            "default_summary": "Create stub under Elderwyld/Locations per convention.",
            "alternative_summaries": [
                "Link only in recap",
                "Session Prep appendix",
                "Defer stub",
            ],
        },
        {
            "id": "mayor_sheriff_names",
            "question": "Canonical mayor and sheriff names or slugs?",
            "default_summary": "Author stub NPC files with TODO names.",
            "alternative_summaries": ["Leave unnamed in recap only", "Ask GM next session"],
        },
        {
            "id": "stuart_surname",
            "question": "Record Stuart surname in the seed or keep given-name-only?",
            "default_summary": "Keep folder slug `stuart` only.",
            "alternative_summaries": ["Add surname in seed", "Defer"],
        },
    ]
    ok, violations = grade_unsure_queue(items)
    assert ok, violations
