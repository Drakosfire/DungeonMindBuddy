from __future__ import annotations

import asyncio
import inspect
from collections.abc import Callable
from typing import Any

import pytest
from generationengine import InferenceObservation, ObservationState, TextRequest, TextResult

from src.agent.synthesis import (
    EXTRACTION_PROMPT,
    SYSTEM_PROMPT,
    SYSTEM_PROMPT_WIKI,
    _load_api_key,
    _resolve_model,
    synthesize_answer,
    synthesize_answer_async,
)

_CONTEXT = "== Entity: Mirathorn (location) ==\n  economy: tourism"
_QUESTION = "Catch me up on Mirathorn"
_ANSWER = "Mirathorn is a fortified city with active trade routes."
_EXTRACTED = "1. Mirathorn has active trade routes."


def _text_result(text: str | None) -> TextResult:
    return TextResult(
        text=text,
        observation=InferenceObservation(
            latency_ms=0,
            retry_count=0,
            state=ObservationState.COMPLETED,
        ),
    )


class RecordingGenerationClient:
    def __init__(
        self,
        outcomes: list[str | None | BaseException] | None = None,
        on_request: Callable[[TextRequest, int], None] | None = None,
    ) -> None:
        self.outcomes = list(outcomes if outcomes is not None else [_ANSWER])
        self.on_request = on_request
        self.requests: list[TextRequest] = []

    async def generate_text(self, request: TextRequest) -> TextResult:
        call_index = len(self.requests)
        self.requests.append(request)
        if self.on_request is not None:
            self.on_request(request, call_index)
        outcome = self.outcomes[call_index]
        if isinstance(outcome, BaseException):
            raise outcome
        return _text_result(outcome)


def _synthesize(client: RecordingGenerationClient, **kwargs: Any) -> str:
    return synthesize_answer(
        _CONTEXT,
        _QUESTION,
        model="test-model",
        generation_client=client,
        **kwargs,
    )


def _assert_request_contract(request: TextRequest, *, model: str = "test-model") -> None:
    assert request.provider == "openai"
    assert request.model == model
    assert request.profile is None
    assert request.temperature is None
    assert request.json_schema is None
    assert request.schema_name is None


def test_one_step_uses_exact_generationengine_request_and_returns_text() -> None:
    client = RecordingGenerationClient([f"  {_ANSWER}  "])

    assert _synthesize(client) == _ANSWER

    assert len(client.requests) == 1
    request = client.requests[0]
    _assert_request_contract(request)
    assert request.system_prompt == SYSTEM_PROMPT
    assert request.user_prompt == (
        f"Projection context:\n{_CONTEXT}\n\n"
        f"GM question:\n{_QUESTION}\n\n"
        "Return a grounded answer based only on the context above. "
        "Follow the output contract from the system prompt exactly."
    )


def test_explicit_alternate_model_reaches_generationengine_unchanged() -> None:
    client = RecordingGenerationClient()
    synthesize_answer(
        _CONTEXT,
        _QUESTION,
        model="gpt-4o-mini",
        generation_client=client,
    )
    _assert_request_contract(client.requests[0], model="gpt-4o-mini")


def test_current_model_policy_resolution_remains_buddy_owned() -> None:
    assert _resolve_model(None) == "gpt-5.3-chat-latest"


@pytest.mark.parametrize(
    ("kwargs", "expected_system_fragment", "expected_user_fragment"),
    [
        ({"wiki_mode": True}, SYSTEM_PROMPT_WIKI, "Campaign context (wiki articles"),
        ({"citation_structure": True}, "Answer structure:\n1. TL;DR:", "Projection context:"),
        ({"verbosity": "compact"}, "Verbosity mode: compact.", "Projection context:"),
        ({"verbosity": "verbose"}, "Verbosity mode: verbose.", "Projection context:"),
        ({"synthesis_profile": "mirathorn"}, "Corpus profile: Mirathorn", "Projection context:"),
    ],
)
def test_prompt_modes_cross_generationengine_boundary_unchanged(
    kwargs: dict[str, Any],
    expected_system_fragment: str,
    expected_user_fragment: str,
) -> None:
    client = RecordingGenerationClient()
    _synthesize(client, **kwargs)
    request = client.requests[0]
    assert expected_system_fragment in (request.system_prompt or "")
    assert expected_user_fragment in request.user_prompt
    assert _CONTEXT in request.user_prompt
    assert _QUESTION in request.user_prompt


def test_system_prompt_contains_grounding_requirements() -> None:
    assert "using ONLY the facts provided" in SYSTEM_PROMPT
    assert "Do not invent information" in SYSTEM_PROMPT
    assert "CANON" in SYSTEM_PROMPT
    assert "PREP" in SYSTEM_PROMPT
    assert "OBSERVED" in SYSTEM_PROMPT
    assert 'Start with a "TL;DR:" line' in SYSTEM_PROMPT
    assert "Key Attributes" in SYSTEM_PROMPT
    assert "Do not enumerate attributes that are absent" in SYSTEM_PROMPT


def test_two_step_uses_exact_sequential_requests_and_success_metadata() -> None:
    client = RecordingGenerationClient([_EXTRACTED, _ANSWER])
    metadata: dict[str, Any] = {}
    assert _synthesize(client, two_step=True, synthesis_meta_out=metadata) == _ANSWER

    assert len(client.requests) == 2
    extraction, answer = client.requests
    _assert_request_contract(extraction)
    _assert_request_contract(answer)
    assert extraction.system_prompt == EXTRACTION_PROMPT
    assert extraction.user_prompt == (
        f"Campaign context:\n{_CONTEXT}\n\n"
        "Extract all factual claims as instructed."
    )
    assert answer.system_prompt == SYSTEM_PROMPT
    assert answer.user_prompt == (
        "Extracted factual claims from the campaign context (numbered list):\n"
        f"{_EXTRACTED}\n\n"
        f"GM question:\n{_QUESTION}\n\n"
        "Answer using ONLY these extracted claims; if they contradict, say so. "
        "Follow the output contract from the system prompt exactly."
    )
    assert metadata == {"two_step": True, "extracted_claims": _EXTRACTED}


@pytest.mark.parametrize("empty", [None, "", "   "])
def test_empty_extraction_stops_before_answer_and_writes_no_success_metadata(empty: str | None) -> None:
    client = RecordingGenerationClient([empty])
    metadata: dict[str, Any] = {"existing": "value"}
    with pytest.raises(RuntimeError, match="Extraction step returned an empty response"):
        _synthesize(client, two_step=True, synthesis_meta_out=metadata)
    assert len(client.requests) == 1
    assert metadata == {"existing": "value"}


@pytest.mark.parametrize("empty", [None, "", "   "])
def test_empty_answer_preserves_existing_error(empty: str | None) -> None:
    client = RecordingGenerationClient([empty])
    with pytest.raises(RuntimeError, match="Synthesis model returned an empty response"):
        _synthesize(client)
    assert len(client.requests) == 1


def test_extraction_failure_propagates_without_retry_or_metadata_mutation() -> None:
    client = RecordingGenerationClient([LookupError("generation failed")])
    metadata: dict[str, Any] = {}
    with pytest.raises(LookupError, match="generation failed"):
        _synthesize(client, two_step=True, synthesis_meta_out=metadata)
    assert len(client.requests) == 1
    assert metadata == {}


def test_answer_failure_after_extraction_preserves_metadata_timing() -> None:
    client = RecordingGenerationClient([_EXTRACTED, LookupError("answer failed")])
    metadata: dict[str, Any] = {}
    with pytest.raises(LookupError, match="answer failed"):
        _synthesize(client, two_step=True, synthesis_meta_out=metadata)
    assert len(client.requests) == 2
    assert metadata == {"two_step": True, "extracted_claims": _EXTRACTED}


def test_one_step_marks_metadata_before_answer_failure() -> None:
    metadata: dict[str, Any] = {}

    def _observe_metadata(_request: TextRequest, _index: int) -> None:
        assert metadata == {"two_step": False}

    client = RecordingGenerationClient([LookupError("answer failed")], on_request=_observe_metadata)
    with pytest.raises(LookupError, match="answer failed"):
        _synthesize(client, synthesis_meta_out=metadata)
    assert metadata == {"two_step": False}
    assert len(client.requests) == 1


def test_injected_generation_client_bypasses_real_credentials(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("OPENAI_API_KEY", raising=False)
    assert _synthesize(RecordingGenerationClient()) == _ANSWER


def test_missing_production_credential_fails_before_client_construction(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr("src.agent.synthesis._load_api_key", lambda: None)

    def _boom() -> Any:
        raise AssertionError("GenerationClient must not be constructed")

    monkeypatch.setattr("src.agent.synthesis.GenerationClient.from_env", _boom)
    with pytest.raises(RuntimeError, match="OPENAI_API_KEY is required for synthesis"):
        asyncio.run(synthesize_answer_async(_CONTEXT, _QUESTION, model="test-model"))


def test_production_client_is_constructed_inside_running_coroutine_and_reused(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr("src.agent.synthesis._load_api_key", lambda: "test-key")
    clients: list[RecordingGenerationClient] = []
    loops: list[asyncio.AbstractEventLoop] = []

    def _from_env() -> RecordingGenerationClient:
        loops.append(asyncio.get_running_loop())
        client = RecordingGenerationClient([_EXTRACTED, _ANSWER])
        clients.append(client)
        return client

    monkeypatch.setattr("src.agent.synthesis.GenerationClient.from_env", _from_env)
    assert asyncio.run(
        synthesize_answer_async(_CONTEXT, _QUESTION, model="test-model", two_step=True)
    ) == _ANSWER
    assert len(loops) == 1
    assert len(clients) == 1
    assert len(clients[0].requests) == 2


def test_production_client_is_not_cached_across_invocations(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr("src.agent.synthesis._load_api_key", lambda: "test-key")
    clients: list[RecordingGenerationClient] = []

    def _from_env() -> RecordingGenerationClient:
        client = RecordingGenerationClient()
        clients.append(client)
        return client

    monkeypatch.setattr("src.agent.synthesis.GenerationClient.from_env", _from_env)
    for _ in range(2):
        asyncio.run(synthesize_answer_async(_CONTEXT, _QUESTION, model="test-model"))
    assert len(clients) == 2
    assert clients[0] is not clients[1]
    assert all(len(client.requests) == 1 for client in clients)


def test_load_api_key_compatibility_shim_remains_available(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("OPENAI_API_KEY", "shim-key")
    monkeypatch.setattr("src.agent.synthesis.load_dungeonmindbuddy_dotenv", lambda: None)
    assert _load_api_key() == "shim-key"


def test_synthesis_source_owns_only_generationengine_text_execution() -> None:
    source = inspect.getsource(__import__("src.agent.synthesis", fromlist=["*"]))
    assert "from openai" not in source
    assert "AsyncOpenAI" not in source
    assert "DungeonMindApiClient" not in source
    assert "chat_completions_create" not in source
    assert "_extract_response_text" not in source
    assert ".generate_text(" in source
    assert "def _load_api_key" in source
    assert "asyncio.run(" in source
