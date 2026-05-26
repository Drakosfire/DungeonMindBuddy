from __future__ import annotations

import pytest

from src.live_play.classify_live_turn import (
    TurnClassification,
    build_live_turn_classifier_sequence_client,
    classify_live_turn,
)
from src.live_play.live_turn_classifier_client import SequenceLiveTurnClassifierClient


def test_classify_live_turn_uses_sequence_client_without_heuristic() -> None:
    client = build_live_turn_classifier_sequence_client(
        [
            TurnClassification(
                latency_mode="context_lookup",
                event_type="context_question",
                intent="npc_or_scene_context",
            )
        ]
    )
    result = classify_live_turn(
        "Totally novel phrasing the regex would miss?",
        client=client,
        allow_heuristic_fallback=False,
    )
    assert result.latency_mode == "context_lookup"
    assert result.event_type == "context_question"


def test_default_classifier_falls_back_when_llm_client_fails() -> None:
    client = SequenceLiveTurnClassifierClient([])
    result = classify_live_turn("Weather 7.", client=client)
    assert result.latency_mode == "fast_live"
    assert result.event_type == "roll_result"
    assert result.table_id == "T-WX"
    assert result.roll == 7
    assert result.confidence == "deterministic"


def test_strict_llm_mode_raises_when_client_fails() -> None:
    client = SequenceLiveTurnClassifierClient([])
    with pytest.raises(RuntimeError, match="Live turn classifier failed"):
        classify_live_turn("Weather 7.", client=client, allow_heuristic_fallback=False)
