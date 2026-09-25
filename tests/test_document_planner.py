from __future__ import annotations

import asyncio
from types import SimpleNamespace
from typing import Any

import pytest
from generationengine import TextRequest

import src.agent.document_planner as planner
from src.agent.document_planner import (
    DEFAULT_MODEL,
    DOCUMENT_PLANNER_PROMPT,
    plan_documents,
    plan_documents_async,
)

QUESTION = "Where did the party meet the archivist?"
ROSTER = "[doc_a] Arrival\n\n[doc_b] The Archive"
CANDIDATES = {"doc_a", "doc_b"}


class RecordingGenerationClient:
    def __init__(self, outcome: str | BaseException) -> None:
        self.outcome = outcome
        self.requests: list[TextRequest] = []

    async def generate_text(self, request: TextRequest) -> Any:
        self.requests.append(request)
        if isinstance(self.outcome, BaseException):
            raise self.outcome
        return SimpleNamespace(text=self.outcome)


def expected_user_prompt() -> str:
    return (
        f"GM question: {QUESTION}\n\n"
        f"Documents ({len(CANDIDATES)} total):\n{ROSTER}\n\n"
        "Select document IDs needed to answer. Return JSON only."
    )


def run_plan(*args: Any, **kwargs: Any) -> Any:
    return asyncio.run(plan_documents_async(*args, **kwargs))


def assert_exact_request(request: TextRequest, *, model: str) -> None:
    assert request.system_prompt == DOCUMENT_PLANNER_PROMPT
    assert request.user_prompt == expected_user_prompt()
    assert request.provider == "openai"
    assert request.model == model
    assert request.profile is None
    assert request.temperature == 0.0
    assert request.json_object is True
    assert request.json_schema is None
    assert request.max_output_tokens is None


def test_exact_generationengine_request_and_buddy_parsing() -> None:
    client = RecordingGenerationClient(
        '{"selected_document_ids":["doc_b"],"reasoning":"archive match"}'
    )

    result = run_plan(
        QUESTION,
        ROSTER,
        CANDIDATES,
        generation_client=client,
    )

    assert len(client.requests) == 1
    assert_exact_request(client.requests[0], model=DEFAULT_MODEL)
    assert result.selected_document_ids == ["doc_b"]
    assert result.reasoning == "archive match"
    assert result.model == DEFAULT_MODEL
    assert result.fallback is False


def test_explicit_model_reaches_generationengine_unchanged() -> None:
    client = RecordingGenerationClient(
        '{"selected_document_ids":["doc_a"],"reasoning":"arrival"}'
    )

    run_plan(
        QUESTION,
        ROSTER,
        CANDIDATES,
        model="alternate-model",
        generation_client=client,
    )

    assert_exact_request(client.requests[0], model="alternate-model")


def test_fenced_json_remains_buddy_owned_and_accepted() -> None:
    client = RecordingGenerationClient(
        '```json\n{"selected_document_ids":["doc_a"],"reasoning":"fenced"}\n```'
    )

    result = run_plan(QUESTION, ROSTER, CANDIDATES, generation_client=client)

    assert result.selected_document_ids == ["doc_a"]
    assert result.reasoning == "fenced"
    assert result.fallback is False


def test_out_of_candidate_ids_are_filtered() -> None:
    client = RecordingGenerationClient(
        '{"selected_document_ids":["unknown","doc_b"],"reasoning":"filtered"}'
    )

    result = run_plan(QUESTION, ROSTER, CANDIDATES, generation_client=client)

    assert result.selected_document_ids == ["doc_b"]
    assert result.reasoning == "filtered"
    assert result.fallback is False


def test_empty_valid_selection_preserves_fallback_text() -> None:
    client = RecordingGenerationClient(
        '{"selected_document_ids":["unknown"],"reasoning":"none valid"}'
    )

    result = run_plan(QUESTION, ROSTER, CANDIDATES, generation_client=client)

    assert result.selected_document_ids == ["doc_a", "doc_b"]
    assert result.reasoning == "none valid (empty selection, fell back)"
    assert result.fallback is True


def test_malformed_json_falls_back_to_all_documents() -> None:
    client = RecordingGenerationClient("not json")

    result = run_plan(QUESTION, ROSTER, CANDIDATES, generation_client=client)

    assert result.selected_document_ids == ["doc_a", "doc_b"]
    assert result.reasoning.startswith("planner_error: ")
    assert result.fallback is True


def test_generationengine_failure_falls_back_to_all_documents() -> None:
    client = RecordingGenerationClient(RuntimeError("normalized generation failure"))

    result = run_plan(QUESTION, ROSTER, CANDIDATES, generation_client=client)

    assert result.selected_document_ids == ["doc_a", "doc_b"]
    assert result.reasoning == "planner_error: normalized generation failure"
    assert result.fallback is True


def test_empty_roster_bypasses_credentials_and_generationengine(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    def explode() -> None:
        raise AssertionError("credential loading must not run")

    monkeypatch.setattr(planner, "load_dungeonmindbuddy_dotenv", explode)
    client = RecordingGenerationClient(AssertionError("GE must not run"))

    result = run_plan(QUESTION, "", CANDIDATES, generation_client=client)

    assert result.selected_document_ids == ["doc_a", "doc_b"]
    assert result.reasoning == "empty_roster"
    assert result.duration_ms == 0
    assert result.fallback is True
    assert client.requests == []


def test_missing_key_preserves_fallback_and_never_constructs_ge(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(planner, "load_dungeonmindbuddy_dotenv", lambda: None)
    monkeypatch.delenv("OPENAI_API_KEY", raising=False)

    class ExplodingFactory:
        @classmethod
        def from_env(cls) -> Any:
            raise AssertionError("GE must not be constructed")

    monkeypatch.setattr(planner, "GenerationClient", ExplodingFactory)

    result = run_plan(QUESTION, ROSTER, CANDIDATES)

    assert result.selected_document_ids == ["doc_a", "doc_b"]
    assert result.reasoning == "no_api_key"
    assert result.duration_ms == 0
    assert result.fallback is True


def test_injected_ge_bypasses_credentials(monkeypatch: pytest.MonkeyPatch) -> None:
    def explode() -> None:
        raise AssertionError("credential loading must not run")

    monkeypatch.setattr(planner, "load_dungeonmindbuddy_dotenv", explode)
    monkeypatch.delenv("OPENAI_API_KEY", raising=False)
    client = RecordingGenerationClient(
        '{"selected_document_ids":["doc_a"],"reasoning":"injected"}'
    )

    result = run_plan(QUESTION, ROSTER, CANDIDATES, generation_client=client)

    assert result.selected_document_ids == ["doc_a"]
    assert len(client.requests) == 1


def test_generationengine_configuration_failure_uses_planner_fallback(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(planner, "load_dungeonmindbuddy_dotenv", lambda: None)
    monkeypatch.setenv("OPENAI_API_KEY", "test-key")

    class FailingFactory:
        @classmethod
        def from_env(cls) -> Any:
            raise RuntimeError("normalized configuration failure")

    monkeypatch.setattr(planner, "GenerationClient", FailingFactory)

    result = run_plan(QUESTION, ROSTER, CANDIDATES)

    assert result.selected_document_ids == ["doc_a", "doc_b"]
    assert result.reasoning == "planner_error: normalized configuration failure"
    assert result.fallback is True


def test_production_generation_client_is_invocation_local(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(planner, "load_dungeonmindbuddy_dotenv", lambda: None)
    monkeypatch.setenv("OPENAI_API_KEY", "test-key")
    created: list[RecordingGenerationClient] = []

    class Factory:
        @classmethod
        def from_env(cls) -> RecordingGenerationClient:
            client = RecordingGenerationClient(
                '{"selected_document_ids":["doc_a"],"reasoning":"local"}'
            )
            created.append(client)
            return client

    monkeypatch.setattr(planner, "GenerationClient", Factory)

    run_plan(QUESTION, ROSTER, CANDIDATES)
    run_plan(QUESTION, ROSTER, CANDIDATES)

    assert len(created) == 2
    assert created[0] is not created[1]
    assert [len(client.requests) for client in created] == [1, 1]


def test_sync_wrapper_preserves_asyncio_run_and_generation_client_seam() -> None:
    client = RecordingGenerationClient(
        '{"selected_document_ids":["doc_b"],"reasoning":"sync"}'
    )

    result = plan_documents(QUESTION, ROSTER, CANDIDATES, generation_client=client)

    assert result.selected_document_ids == ["doc_b"]
    assert len(client.requests) == 1
