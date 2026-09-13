from __future__ import annotations

import json
from typing import Any

import pytest

from src.graph_memory.extraction.category_candidate_graph_extractor import (
    CategoryGraphExtractionError,
)
from src.graph_memory.extraction.deepseek_category_graph_pass_client import (
    DeepSeekCategoryGraphPassClient,
)


class _FakeMessage:
    def __init__(self, content: str) -> None:
        self.content = content


class _FakeChoice:
    def __init__(self, content: str) -> None:
        self.message = _FakeMessage(content)


class _FakeUsage:
    input_tokens = 10
    output_tokens = 5


class _FakeChatResponse:
    def __init__(self, *, content: str, response_id: str = "chatcmpl-test") -> None:
        self.id = response_id
        self.choices = [_FakeChoice(content)]
        self.usage = _FakeUsage()


class _FakeCompletions:
    def __init__(self, responses: list[Any]) -> None:
        self._responses = list(responses)
        self.calls: list[dict[str, Any]] = []

    def create(self, **kwargs: Any) -> Any:
        self.calls.append(dict(kwargs))
        if not self._responses:
            raise RuntimeError("no fake responses left")
        item = self._responses.pop(0)
        if isinstance(item, Exception):
            raise item
        return item


class _FakeChat:
    def __init__(self, responses: list[Any]) -> None:
        self.completions = _FakeCompletions(responses)


class _FakeSDKClient:
    def __init__(self, responses: list[Any]) -> None:
        self.chat = _FakeChat(responses)


def _valid_actor_payload() -> str:
    return json.dumps({"observation_nodes": []})


def test_run_pass_success(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("OPENROUTER_API_KEY", "test-key")
    client = DeepSeekCategoryGraphPassClient(
        sdk_client=_FakeSDKClient([_FakeChatResponse(content=_valid_actor_payload())]),
        max_attempts=3,
    )

    result = client.run_pass(
        "actor_pass",
        model_id="deepseek/deepseek-v4.1-flash",
        instructions="Extract actors.",
        user_content="source packet",
    )

    assert result["parsed"] == {"observation_nodes": []}
    assert result["raw_text"] == _valid_actor_payload()
    assert result["usage"]["input_tokens"] == 10
    assert result["response_id"] == "chatcmpl-test"
    assert result["json_object_attempts"] == 1
    assert result["provider_pin"]["allow_fallbacks"] is False
    assert client._sdk_client.chat.completions.calls[0]["response_format"] == {
        "type": "json_object"
    }


def test_run_pass_retries_then_succeeds(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("OPENROUTER_API_KEY", "test-key")
    client = DeepSeekCategoryGraphPassClient(
        sdk_client=_FakeSDKClient(
            [
                _FakeChatResponse(content="not json"),
                _FakeChatResponse(content=_valid_actor_payload(), response_id="chatcmpl-2"),
            ]
        ),
        max_attempts=5,
    )

    result = client.run_pass(
        "actor_pass",
        model_id="deepseek/deepseek-v4.1-flash",
        instructions="Extract actors.",
        user_content="source packet",
    )

    assert result["parsed"] == {"observation_nodes": []}
    assert result["json_object_attempts"] == 2
    assert result["response_id"] == "chatcmpl-2"
    assert len(client._sdk_client.chat.completions.calls) == 2


def test_run_pass_exhausts_attempts(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("OPENROUTER_API_KEY", "test-key")
    client = DeepSeekCategoryGraphPassClient(
        sdk_client=_FakeSDKClient(
            [
                _FakeChatResponse(content=""),
                _FakeChatResponse(content="still not json"),
                _FakeChatResponse(content="{}"),
            ]
        ),
        max_attempts=3,
    )

    with pytest.raises(CategoryGraphExtractionError, match="missing required keys"):
        client.run_pass(
            "actor_pass",
            model_id="deepseek/deepseek-v4.1-flash",
            instructions="Extract actors.",
            user_content="source packet",
        )

    assert len(client._sdk_client.chat.completions.calls) == 3
