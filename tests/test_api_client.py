from __future__ import annotations

import asyncio

from src.llm.api_client import DungeonMindApiClient


class _FakeResponses:
    def __init__(self) -> None:
        self.calls: list[dict] = []

    def create(self, **kwargs):
        self.calls.append(dict(kwargs))
        return {"id": "resp_fake"}

    def parse(self, **kwargs):
        self.calls.append({"parse": dict(kwargs)})
        return {"id": "parsed_fake"}


class _FakeChatCompletions:
    def __init__(self) -> None:
        self.calls: list[dict] = []

    def create(self, **kwargs):
        self.calls.append(dict(kwargs))
        return {"id": "chat_fake"}


class _AsyncFakeResponses:
    async def parse(self, **kwargs):
        return {"id": "parsed_async_fake", "kwargs": kwargs}


class _AsyncFakeChatCompletions:
    async def create(self, **kwargs):
        return {"id": "chat_async_fake", "kwargs": kwargs}


class _FakeRawClient:
    def __init__(self) -> None:
        self.responses = _FakeResponses()
        self.chat = type("ChatObj", (), {"completions": _FakeChatCompletions()})()


class _AsyncFakeRawClient:
    def __init__(self) -> None:
        self.responses = _AsyncFakeResponses()
        self.chat = type("ChatObj", (), {"completions": _AsyncFakeChatCompletions()})()


def test_responses_create_records_action_and_forwards_kwargs() -> None:
    raw = _FakeRawClient()
    api = DungeonMindApiClient(raw)
    result = api.responses_create(action="planner.turn.initial_user", model="gpt-test", input=[{"x": 1}])

    assert result.action == "planner.turn.initial_user"
    assert result.elapsed_ms >= 0
    assert result.response == {"id": "resp_fake"}
    assert raw.responses.calls == [{"model": "gpt-test", "input": [{"x": 1}]}]


def test_wrap_is_idempotent_for_wrapper_instances() -> None:
    raw = _FakeRawClient()
    api = DungeonMindApiClient(raw)
    assert DungeonMindApiClient.wrap(api) is api


def test_responses_parse_and_chat_completions_sync() -> None:
    raw = _FakeRawClient()
    api = DungeonMindApiClient(raw)

    parsed = api.responses_parse(action="ingest.parse", model="gpt-x")
    chat = api.chat_completions_create(action="query.plan", model="gpt-y")

    assert parsed.response == {"id": "parsed_fake"}
    assert chat.response == {"id": "chat_fake"}
    assert raw.responses.calls[-1] == {"parse": {"model": "gpt-x"}}
    assert raw.chat.completions.calls[-1] == {"model": "gpt-y"}


def test_responses_parse_and_chat_completions_async() -> None:
    async def _run() -> None:
        raw = _AsyncFakeRawClient()
        api = DungeonMindApiClient(raw)
        parsed = await api.responses_parse_async(action="ingest.parse.async", model="gpt-a")
        chat = await api.chat_completions_create_async(action="query.plan.async", model="gpt-b")
        assert parsed.response["id"] == "parsed_async_fake"
        assert chat.response["id"] == "chat_async_fake"

    asyncio.run(_run())
