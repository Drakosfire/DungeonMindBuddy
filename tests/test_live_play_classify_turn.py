from __future__ import annotations

import pytest

from src.live_play.classify_live_turn import classify_live_turn


def test_weather_7_with_skill_check() -> None:
    result = classify_live_turn("Weather 7. Caelynn Nature 19.")
    assert result.latency_mode == "fast_live"
    assert result.event_type == "roll_result"
    assert result.table_id == "T-WX"
    assert result.roll == 7
    assert result.skill_check == {"actor": "Caelynn", "skill": "Nature", "total": 19}


def test_weather_16_roll_only() -> None:
    result = classify_live_turn("Weather 16.")
    assert result.latency_mode == "fast_live"
    assert result.event_type == "roll_result"
    assert result.table_id == "T-WX"
    assert result.roll == 16


def test_r5_54_roll() -> None:
    result = classify_live_turn("R5 54.")
    assert result.latency_mode == "fast_live"
    assert result.event_type == "roll_result"
    assert result.table_id == "R5"
    assert result.roll == 54


def test_grobnok_open_loop_update() -> None:
    result = classify_live_turn("Grobnok does not call in the morning.")
    assert result.latency_mode == "fast_live"
    assert result.event_type == "open_loop_update"


def test_lysandro_canon_correction() -> None:
    result = classify_live_turn("Lysandro is her father.")
    assert result.latency_mode == "fast_live"
    assert result.event_type == "canon_correction"
    assert result.event_type != "state_note"


def test_caelynn_canon_commit() -> None:
    result = classify_live_turn("Caelynn bottles the puddle water.")
    assert result.latency_mode == "fast_live"
    assert result.event_type == "canon_commit"


def test_lysandra_gate_context_lookup() -> None:
    result = classify_live_turn("What is Lysandra feeling at the gate?")
    assert result.latency_mode == "context_lookup"
    assert result.event_type == "context_question"
    assert result.table_id is None
    assert result.roll is None
