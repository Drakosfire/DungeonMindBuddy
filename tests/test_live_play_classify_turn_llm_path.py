from __future__ import annotations

from src.live_play.classify_live_turn import (
    TurnClassification,
    build_live_turn_classifier_sequence_client,
    classify_live_turn,
)


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
