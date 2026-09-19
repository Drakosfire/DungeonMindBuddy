"""GenerationEngine adapter for live-turn classification."""

from __future__ import annotations

from typing import Any

from generationengine import (
    GenerationClient,
    InferenceObservation,
    ObservationState,
    TextRequest,
    TextResult,
)

from src.live_play.live_turn_classification_schema import (
    LiveTurnClassificationModel,
    live_turn_classification_json_schema,
)
from src.live_play.prompts.live_turn_classifier import LIVE_TURN_CLASSIFIER_INSTRUCTIONS
from src.llm.generation_sync import run_awaitable_sync

_SCHEMA_NAME = "live_turn_classification"


class OpenAILiveTurnClassifierClient:
    """Synchronous Buddy adapter over GenerationEngine structured generation."""

    def __init__(self, *, client: Any | None = None) -> None:
        self._client = client

    def classify_turn(self, *, model: str, text: str) -> LiveTurnClassificationModel:
        request = TextRequest(
            user_prompt=text,
            system_prompt=LIVE_TURN_CLASSIFIER_INSTRUCTIONS,
            provider="openai",
            model=model,
            temperature=None,
            json_schema=live_turn_classification_json_schema(),
            schema_name=_SCHEMA_NAME,
        )
        result = run_awaitable_sync(lambda: self._generate_structured(request))
        parsed = getattr(result, "parsed", None)
        if parsed is None:
            raise ValueError("Live turn classifier returned no parsed structured output.")
        return LiveTurnClassificationModel.model_validate(parsed)

    async def _generate_structured(self, request: TextRequest) -> Any:
        if self._client is not None:
            return await self._client.generate_structured(request)
        ge_client = GenerationClient.from_env()
        return await ge_client.generate_structured(request)


def _queued_structured_result(parsed: dict[str, Any]) -> TextResult:
    return TextResult(
        parsed=parsed,
        observation=InferenceObservation(
            latency_ms=0,
            retry_count=0,
            state=ObservationState.COMPLETED,
        ),
    )


class SequenceLiveTurnClassifierClient:
    """Test double: ``generate_structured`` returns queued classifications in order."""

    def __init__(self, models: list[LiveTurnClassificationModel]) -> None:
        self._models = list(models)
        self._i = 0
        self.requests: list[TextRequest] = []

    async def generate_structured(self, request: TextRequest) -> TextResult:
        self.requests.append(request)
        if self._i >= len(self._models):
            raise RuntimeError("SequenceLiveTurnClassifierClient: no more queued responses")
        parsed = self._models[self._i]
        self._i += 1
        return _queued_structured_result(parsed.model_dump(mode="json"))
