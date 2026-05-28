"""Session 22 live-turn classifier benchmark (gold in evals/c2_live_prep/gold/)."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import pytest

from src.live_play.classify_live_turn import (
    TurnClassification,
    build_live_turn_classifier_sequence_client,
    classify_live_turn,
    classify_live_turn_heuristic,
)

_GOLD_PATH = (
    Path(__file__).resolve().parents[1]
    / "evals/c2_live_prep/gold/session_22_live_turn_classifier.json"
)


def _load_gold() -> dict[str, Any]:
    return json.loads(_GOLD_PATH.read_text(encoding="utf-8"))


def _heuristic_fixtures() -> list[dict[str, Any]]:
    return [row for row in _load_gold()["fixtures"] if row.get("verify_heuristic", True)]


def _expect_to_turn_classification(expect: dict[str, Any]) -> TurnClassification:
    skill = expect.get("skill_check")
    return TurnClassification(
        latency_mode=expect["latency_mode"],
        event_type=expect["event_type"],
        intent=expect["intent"],
        table_id=expect.get("table_id"),
        roll=expect.get("roll"),
        skill_check=skill,
        confidence="high",
    )


def _routing_fields(result: TurnClassification) -> dict[str, Any]:
    return {
        "latency_mode": result.latency_mode,
        "event_type": result.event_type,
        "table_id": result.table_id,
        "roll": result.roll,
        "skill_check": result.skill_check,
    }


def _routing_expect(expect: dict[str, Any]) -> dict[str, Any]:
    return {
        "latency_mode": expect["latency_mode"],
        "event_type": expect["event_type"],
        "table_id": expect.get("table_id"),
        "roll": expect.get("roll"),
        "skill_check": expect.get("skill_check"),
    }


def _assert_matches(
    result: TurnClassification,
    expect: dict[str, Any],
    *,
    alternates: list[dict[str, Any]] | None = None,
) -> None:
    """Assert handler routing contract; intent is telemetry-only (free-form string)."""
    got = _routing_fields(result)
    candidates = [_routing_expect(expect)] + [
        _routing_expect(alt) for alt in (alternates or [])
    ]
    assert got in candidates, f"routing {got!r} not in {candidates!r}"


@pytest.fixture(scope="module")
def gold_fixtures() -> list[dict[str, Any]]:
    gold = _load_gold()
    fixtures = gold.get("fixtures")
    assert isinstance(fixtures, list) and fixtures, "gold fixtures must be non-empty"
    return fixtures


@pytest.mark.parametrize(
    "fixture",
    _heuristic_fixtures(),
    ids=lambda row: row["id"],
)
def test_heuristic_matches_session_22_gold(fixture: dict[str, Any]) -> None:
    """Regex fallback must match gold on roll/canon/open-loop fixtures (LLM owns the rest)."""
    result = classify_live_turn_heuristic(fixture["user_line"])
    _assert_matches(result, fixture["expect"], alternates=fixture.get("routing_alternates"))


@pytest.mark.parametrize(
    "fixture",
    _load_gold()["fixtures"],
    ids=lambda row: row["id"],
)
def test_sequence_client_matches_session_22_gold(fixture: dict[str, Any]) -> None:
    """Proves the Responses parse path accepts each gold shape (no network)."""
    expected = _expect_to_turn_classification(fixture["expect"])
    client = build_live_turn_classifier_sequence_client([expected])
    result = classify_live_turn(
        fixture["user_line"],
        client=client,
        allow_heuristic_fallback=False,
    )
    _assert_matches(result, fixture["expect"], alternates=fixture.get("routing_alternates"))


def test_gold_file_session_and_source_document() -> None:
    gold = _load_gold()
    assert gold["schema"] == "c2_live_turn_classifier_benchmark_v1"
    assert gold["session"] == 22
    assert gold["campaign_id"] == "longmont-c2"
    assert "session_22_raw_notes.md" in gold["source_document"]
    llm_only = [row["id"] for row in gold["fixtures"] if not row.get("verify_heuristic", True)]
    assert llm_only, "expected at least one LLM-only fixture"
    assert "s22_day1_identify_bottle" in llm_only


@pytest.mark.live_llm
@pytest.mark.parametrize(
    "fixture",
    _load_gold()["fixtures"],
    ids=lambda row: row["id"],
)
def test_live_llm_matches_session_22_gold(fixture: dict[str, Any]) -> None:
    """Optional live cohort: uv run pytest -m live_llm tests/test_live_play_classifier_benchmark_s22.py"""
    from src.agent.synthesis import _load_api_key

    if not (_load_api_key() or "").strip():
        pytest.skip("OPENAI_API_KEY not set")
    result = classify_live_turn(
        fixture["user_line"],
        allow_heuristic_fallback=False,
    )
    _assert_matches(result, fixture["expect"], alternates=fixture.get("routing_alternates"))
