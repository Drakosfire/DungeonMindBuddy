"""Unit tests for step3_unsure_queue_grading.py — shape mode and exact mode."""

from __future__ import annotations

from unittest.mock import patch

import pytest

from evals.session_recap_ingest_vertical_slice.step3_unsure_queue_grading import (
    grade_unsure_queue,
)


def _shape_gold(
    *,
    min_total: int = 2,
    max_total: int = 4,
    id_required: bool = True,
    id_pattern: str = r"^[a-z][a-z0-9_]*$",
    question_required: bool = True,
    default_summary_required: bool = True,
    min_alternatives: int = 2,
) -> dict:
    return {
        "schema": "unsure_queue_v1",
        "mode": "shape",
        "min_total_items": min_total,
        "max_total_items": max_total,
        "per_item_shape": {
            "id_required": id_required,
            "id_pattern": id_pattern,
            "question_required": question_required,
            "default_summary_required": default_summary_required,
            "min_alternatives": min_alternatives,
        },
    }


def _valid_item(*, id: str = "some_thing", alts: int = 2) -> dict:
    return {
        "id": id,
        "question": "Where should this go?",
        "default_summary": "Keep it unresolved for now.",
        "alternative_summaries": [f"Option {i}" for i in range(alts)],
    }


# ---------------------------------------------------------------------------
# Shape mode — pass cases
# ---------------------------------------------------------------------------


def test_shape_mode_pass_with_valid_items() -> None:
    gold = _shape_gold()
    items = [_valid_item(id="foo_bar"), _valid_item(id="baz_qux")]
    with patch(
        "evals.session_recap_ingest_vertical_slice.step3_unsure_queue_grading.load_unsure_gold",
        return_value=gold,
    ):
        ok, violations = grade_unsure_queue(items)
    assert ok, violations
    assert violations == []


def test_shape_mode_ignores_expected_items() -> None:
    """expected_items in gold must be ignored in shape mode — no spurious ID violations."""
    gold = _shape_gold()
    gold["expected_items"] = [
        {
            "id": "tower_blueprint_placement",
            "question_must_match": "(?i)tower",
            "default_must_mention": "Locations",
            "alternatives_min_count": 3,
        }
    ]
    items = [_valid_item(id="entirely_different_id"), _valid_item(id="another_id")]
    with patch(
        "evals.session_recap_ingest_vertical_slice.step3_unsure_queue_grading.load_unsure_gold",
        return_value=gold,
    ):
        ok, violations = grade_unsure_queue(items)
    assert ok, violations


# ---------------------------------------------------------------------------
# Shape mode — count failures
# ---------------------------------------------------------------------------


def test_shape_mode_fail_count_below_min() -> None:
    gold = _shape_gold(min_total=2)
    items = [_valid_item()]
    with patch(
        "evals.session_recap_ingest_vertical_slice.step3_unsure_queue_grading.load_unsure_gold",
        return_value=gold,
    ):
        ok, violations = grade_unsure_queue(items)
    assert not ok
    assert any("too few unsure_queue items" in v for v in violations)


def test_shape_mode_fail_count_above_max() -> None:
    gold = _shape_gold(max_total=2)
    items = [_valid_item(id=f"item_{i}") for i in range(3)]
    with patch(
        "evals.session_recap_ingest_vertical_slice.step3_unsure_queue_grading.load_unsure_gold",
        return_value=gold,
    ):
        ok, violations = grade_unsure_queue(items)
    assert not ok
    assert any("too many unsure_queue items" in v for v in violations)


# ---------------------------------------------------------------------------
# Shape mode — structural failures
# ---------------------------------------------------------------------------


def test_shape_mode_fail_missing_id() -> None:
    gold = _shape_gold()
    items = [
        {
            "question": "Where should this go?",
            "default_summary": "Keep unresolved.",
            "alternative_summaries": ["A", "B"],
        },
        _valid_item(id="second_item"),
    ]
    with patch(
        "evals.session_recap_ingest_vertical_slice.step3_unsure_queue_grading.load_unsure_gold",
        return_value=gold,
    ):
        ok, violations = grade_unsure_queue(items)
    assert not ok
    assert any("id is required" in v for v in violations)


def test_shape_mode_fail_bad_id_pattern() -> None:
    gold = _shape_gold()
    items = [
        _valid_item(id="BadCamelCase"),
        _valid_item(id="also_fine"),
    ]
    with patch(
        "evals.session_recap_ingest_vertical_slice.step3_unsure_queue_grading.load_unsure_gold",
        return_value=gold,
    ):
        ok, violations = grade_unsure_queue(items)
    assert not ok
    assert any("does not match pattern" in v for v in violations)


def test_shape_mode_fail_too_few_alternatives() -> None:
    gold = _shape_gold(min_alternatives=2)
    items = [
        _valid_item(id="foo_bar", alts=1),
        _valid_item(id="baz_qux", alts=2),
    ]
    with patch(
        "evals.session_recap_ingest_vertical_slice.step3_unsure_queue_grading.load_unsure_gold",
        return_value=gold,
    ):
        ok, violations = grade_unsure_queue(items)
    assert not ok
    assert any("alternative_summaries" in v for v in violations)


def test_shape_mode_fail_missing_question() -> None:
    gold = _shape_gold()
    items = [
        {"id": "foo_bar", "default_summary": "ok", "alternative_summaries": ["A", "B"]},
        _valid_item(id="baz_qux"),
    ]
    with patch(
        "evals.session_recap_ingest_vertical_slice.step3_unsure_queue_grading.load_unsure_gold",
        return_value=gold,
    ):
        ok, violations = grade_unsure_queue(items)
    assert not ok
    assert any("question is required" in v for v in violations)


def test_shape_mode_fail_missing_default_summary() -> None:
    gold = _shape_gold()
    items = [
        {"id": "foo_bar", "question": "Where?", "alternative_summaries": ["A", "B"]},
        _valid_item(id="baz_qux"),
    ]
    with patch(
        "evals.session_recap_ingest_vertical_slice.step3_unsure_queue_grading.load_unsure_gold",
        return_value=gold,
    ):
        ok, violations = grade_unsure_queue(items)
    assert not ok
    assert any("default_summary is required" in v for v in violations)


# ---------------------------------------------------------------------------
# Exact mode — verify existing behavior is unchanged
# ---------------------------------------------------------------------------


def _exact_gold() -> dict:
    return {
        "schema": "unsure_queue_v1",
        "mode": "exact",
        "min_total_items": 2,
        "max_total_items": 4,
        "expected_items": [
            {
                "id": "tower_blueprint_placement",
                "question_must_match": r"(?i)tower.{0,40}(blueprint|location|placement)",
                "default_must_mention": "Locations",
                "alternatives_min_count": 3,
            },
            {
                "id": "mayor_sheriff_names",
                "question_must_match": r"(?i)(mayor|sheriff).{0,80}(name|slug|canonical)",
                "default_must_mention": "stub",
                "alternatives_min_count": 2,
            },
        ],
    }


def _exact_passing_items() -> list[dict]:
    return [
        {
            "id": "tower_blueprint_placement",
            "question": "Should the tower blueprint location or placement get a canonical home?",
            "default_summary": "Locations: keep the tower blueprint unresolved.",
            "alternative_summaries": ["A", "B", "C"],
        },
        {
            "id": "mayor_sheriff_names",
            "question": "What canonical mayor or sheriff name/slug should this recap use?",
            "default_summary": "Use a stub until the mayor is confirmed.",
            "alternative_summaries": ["Mayor stub.", "Sheriff stub."],
        },
    ]


def test_exact_mode_pass_with_valid_items() -> None:
    gold = _exact_gold()
    with patch(
        "evals.session_recap_ingest_vertical_slice.step3_unsure_queue_grading.load_unsure_gold",
        return_value=gold,
    ):
        ok, violations = grade_unsure_queue(_exact_passing_items())
    assert ok, violations


def test_exact_mode_fail_missing_id() -> None:
    gold = _exact_gold()
    items = [_exact_passing_items()[0]]  # only one item, missing mayor_sheriff_names
    with patch(
        "evals.session_recap_ingest_vertical_slice.step3_unsure_queue_grading.load_unsure_gold",
        return_value=gold,
    ):
        ok, violations = grade_unsure_queue(items)
    assert not ok
    assert any("missing unsure_queue id" in v for v in violations)


def test_exact_mode_fail_question_regex() -> None:
    gold = _exact_gold()
    items = list(_exact_passing_items())
    items[0] = {**items[0], "question": "Unrelated question about something else?"}
    with patch(
        "evals.session_recap_ingest_vertical_slice.step3_unsure_queue_grading.load_unsure_gold",
        return_value=gold,
    ):
        ok, violations = grade_unsure_queue(items)
    assert not ok
    assert any("question did not match" in v for v in violations)


def test_exact_mode_fail_default_must_mention() -> None:
    gold = _exact_gold()
    items = list(_exact_passing_items())
    items[0] = {**items[0], "default_summary": "No mention of the required keyword."}
    with patch(
        "evals.session_recap_ingest_vertical_slice.step3_unsure_queue_grading.load_unsure_gold",
        return_value=gold,
    ):
        ok, violations = grade_unsure_queue(items)
    assert not ok
    assert any("default_summary missing" in v for v in violations)


def test_exact_mode_fail_too_few_alternatives() -> None:
    gold = _exact_gold()
    items = list(_exact_passing_items())
    items[0] = {**items[0], "alternative_summaries": ["Only one."]}
    with patch(
        "evals.session_recap_ingest_vertical_slice.step3_unsure_queue_grading.load_unsure_gold",
        return_value=gold,
    ):
        ok, violations = grade_unsure_queue(items)
    assert not ok
    assert any("alternative_summaries" in v for v in violations)


def test_exact_mode_default_when_mode_absent() -> None:
    """When mode key is absent, exact mode should apply (default back-compat)."""
    gold = _exact_gold()
    del gold["mode"]
    with patch(
        "evals.session_recap_ingest_vertical_slice.step3_unsure_queue_grading.load_unsure_gold",
        return_value=gold,
    ):
        ok, violations = grade_unsure_queue(_exact_passing_items())
    assert ok, violations


def test_exact_mode_null_items_counts_as_empty() -> None:
    gold = _exact_gold()
    with patch(
        "evals.session_recap_ingest_vertical_slice.step3_unsure_queue_grading.load_unsure_gold",
        return_value=gold,
    ):
        ok, violations = grade_unsure_queue(None)
    assert not ok
    assert any("too few unsure_queue items" in v for v in violations)
