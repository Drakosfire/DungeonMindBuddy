"""OpenAI Responses API adapter for live-turn classification."""

from __future__ import annotations

from typing import Any

from src.live_play.live_turn_classification_schema import LiveTurnClassificationModel
from src.live_play.prompts.live_turn_classifier import LIVE_TURN_CLASSIFIER_INSTRUCTIONS
from src.llm.api_client import DungeonMindApiClient


class OpenAILiveTurnClassifierClient:
    """Adapter for OpenAI Responses API structured live-turn routing."""

    def __init__(self, *, sdk_client: Any | None = None) -> None:
        if sdk_client is not None:
            self._client = sdk_client
            self._api_client = DungeonMindApiClient.wrap(self._client)
            return
        try:
            from openai import OpenAI  # type: ignore[import-untyped]
        except Exception as exc:  # pragma: no cover
            raise RuntimeError(
                "OpenAI SDK is required for OpenAILiveTurnClassifierClient. Install 'openai'."
            ) from exc
        self._client = OpenAI()
        self._api_client = DungeonMindApiClient.wrap(self._client)

    def classify_turn(self, *, model: str, text: str) -> LiveTurnClassificationModel:
        response = self._api_client.responses_parse(
            action="live_play.classify_turn",
            model=model,
            instructions=LIVE_TURN_CLASSIFIER_INSTRUCTIONS,
            input=[{"role": "user", "content": text}],
            text_format=LiveTurnClassificationModel,
        ).response
        parsed = getattr(response, "output_parsed", None)
        if parsed is None:
            raise ValueError("Live turn classifier returned no output_parsed.")
        if isinstance(parsed, LiveTurnClassificationModel):
            return parsed
        return LiveTurnClassificationModel.model_validate(parsed)


class _FakeClassifierResponse:
    __slots__ = ("output_parsed",)

    def __init__(self, parsed: LiveTurnClassificationModel) -> None:
        self.output_parsed = parsed


class SequenceLiveTurnClassifierClient:
    """Test double: ``responses.parse`` returns queued structured classifications in order."""

    def __init__(self, models: list[LiveTurnClassificationModel]) -> None:
        self._models = list(models)
        self._i = 0
        self.responses = self._Responses(self)

    class _Responses:
        def __init__(self, outer: SequenceLiveTurnClassifierClient) -> None:
            self._outer = outer

        def parse(self, **kwargs: Any) -> _FakeClassifierResponse:
            o = self._outer
            if o._i >= len(o._models):
                raise RuntimeError("SequenceLiveTurnClassifierClient: no more queued responses")
            parsed = o._models[o._i]
            o._i += 1
            return _FakeClassifierResponse(parsed)
