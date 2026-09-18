from __future__ import annotations

import asyncio
from typing import Any

import pytest
from pydantic import ValidationError

from src.live_play.classify_live_turn import (
    TurnClassification,
    _resolve_classifier_model,
    build_live_turn_classifier_sequence_client,
    classify_live_turn,
)
from src.live_play.live_turn_classification_schema import (
    LiveTurnClassificationModel,
    live_turn_classification_json_schema,
)
from src.live_play.live_turn_classifier_client import SequenceLiveTurnClassifierClient
from src.live_play.prompts.live_turn_classifier import LIVE_TURN_CLASSIFIER_INSTRUCTIONS


def _context_lookup() -> TurnClassification:
    return TurnClassification(
        latency_mode="context_lookup",
        event_type="context_question",
        intent="npc_or_scene_context",
    )


def test_classify_live_turn_uses_sequence_client_without_heuristic() -> None:
    client = build_live_turn_classifier_sequence_client([_context_lookup()])
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


def test_generationengine_request_uses_explicit_openai_target(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.delenv("LIVE_TURN_CLASSIFIER_MODEL", raising=False)
    user_text = "Totally novel phrasing the regex would miss?"
    client = build_live_turn_classifier_sequence_client([_context_lookup()])
    classify_live_turn(user_text, client=client, allow_heuristic_fallback=False)
    assert len(client.requests) == 1
    request = client.requests[0]
    assert request.provider == "openai"
    assert request.model == "gpt-5.3-codex"
    assert request.profile is None
    assert request.temperature is None
    assert request.system_prompt == LIVE_TURN_CLASSIFIER_INSTRUCTIONS
    assert request.user_prompt == user_text
    assert request.json_schema == live_turn_classification_json_schema()
    assert request.schema_name == "live_turn_classification"


def test_explicit_model_override_reaches_generationengine_request() -> None:
    client = build_live_turn_classifier_sequence_client([_context_lookup()])
    classify_live_turn(
        "hello?",
        client=client,
        model="gpt-4o-mini",
        allow_heuristic_fallback=False,
    )
    assert client.requests[0].model == "gpt-4o-mini"


def test_env_model_override_reaches_generationengine_request(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("LIVE_TURN_CLASSIFIER_MODEL", "gpt-4o-mini")
    client = build_live_turn_classifier_sequence_client([_context_lookup()])
    classify_live_turn("hello?", client=client, allow_heuristic_fallback=False)
    assert client.requests[0].model == "gpt-4o-mini"


def test_policy_model_resolution_still_returns_gpt_53_codex(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.delenv("LIVE_TURN_CLASSIFIER_MODEL", raising=False)
    assert _resolve_classifier_model(None) == "gpt-5.3-codex"


def test_repair_roll_fields_still_runs_after_generationengine_classification() -> None:
    parsed = LiveTurnClassificationModel(
        latency_mode="fast_live",
        event_type="roll_result",
        intent="resolve_roll_table",
        table_id=None,
        roll=None,
    )
    client = SequenceLiveTurnClassifierClient([parsed])
    result = classify_live_turn(
        "Weather 7.",
        client=client,
        allow_heuristic_fallback=False,
    )
    assert result.event_type == "roll_result"
    assert result.table_id == "T-WX"
    assert result.roll == 7


def test_generationengine_parsed_dict_is_product_validated() -> None:
    class _InvalidParsedClient:
        async def generate_structured(self, request: Any) -> Any:
            class _Result:
                parsed = {"latency_mode": "not-a-mode"}

            return _Result()

    with pytest.raises(RuntimeError, match="Live turn classifier failed") as exc_info:
        classify_live_turn(
            "hello?",
            client=_InvalidParsedClient(),
            allow_heuristic_fallback=False,
        )
    assert isinstance(exc_info.value.__cause__, ValidationError)


def test_classifier_does_not_retry_generationengine_failures() -> None:
    class _CountingFailClient:
        def __init__(self) -> None:
            self.calls = 0

        async def generate_structured(self, request: Any) -> Any:
            self.calls += 1
            raise RuntimeError("structured generation failed")

    client = _CountingFailClient()
    with pytest.raises(RuntimeError, match="Live turn classifier failed"):
        classify_live_turn("hello?", client=client, allow_heuristic_fallback=False)
    assert client.calls == 1


def test_ordinary_synchronous_call_succeeds_without_running_loop() -> None:
    client = build_live_turn_classifier_sequence_client([_context_lookup()])
    result = classify_live_turn(
        "Totally novel phrasing the regex would miss?",
        client=client,
        allow_heuristic_fallback=False,
    )
    assert result.event_type == "context_question"


def test_synchronous_classifier_succeeds_from_running_event_loop() -> None:
    client = build_live_turn_classifier_sequence_client([_context_lookup()])

    async def _inside_running_loop() -> TurnClassification:
        return classify_live_turn(
            "Totally novel phrasing the regex would miss?",
            client=client,
            allow_heuristic_fallback=False,
        )

    result = asyncio.run(_inside_running_loop())
    assert result.latency_mode == "context_lookup"
    assert result.event_type == "context_question"
    assert len(client.requests) == 1


def test_running_event_loop_still_falls_back_on_generationengine_failure() -> None:
    client = SequenceLiveTurnClassifierClient([])

    async def _inside_running_loop() -> TurnClassification:
        return classify_live_turn("Weather 7.", client=client)

    result = asyncio.run(_inside_running_loop())
    assert result.event_type == "roll_result"
    assert result.table_id == "T-WX"
    assert result.roll == 7


def test_running_event_loop_strict_mode_raises_original_failure() -> None:
    client = SequenceLiveTurnClassifierClient([])

    async def _inside_running_loop() -> TurnClassification:
        return classify_live_turn(
            "Weather 7.",
            client=client,
            allow_heuristic_fallback=False,
        )

    with pytest.raises(RuntimeError, match="Live turn classifier failed"):
        asyncio.run(_inside_running_loop())
