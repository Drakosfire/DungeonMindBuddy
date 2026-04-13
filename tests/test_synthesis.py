from __future__ import annotations

from typing import Any

from src.agent.synthesis import SYSTEM_PROMPT, SYSTEM_PROMPT_WIKI, synthesize_answer


class _FakeResponse:
    class _Choice:
        class _Message:
            def __init__(self, content: str) -> None:
                self.content = content

        def __init__(self, content: str) -> None:
            self.message = self._Message(content)

    def __init__(self, content: str) -> None:
        self.choices = [self._Choice(content)]


class _FakeCompletions:
    def __init__(self) -> None:
        self.calls: list[dict[str, Any]] = []

    def create(self, **kwargs: Any) -> _FakeResponse:
        self.calls.append(kwargs)
        return _FakeResponse("Mirathorn is a fortified city with active trade routes.")


class _FakeChat:
    def __init__(self) -> None:
        self.completions = _FakeCompletions()


class _FakeOpenAIClient:
    def __init__(self) -> None:
        self.chat = _FakeChat()


def test_synthesize_uses_mock_client_and_returns_content() -> None:
    client = _FakeOpenAIClient()
    answer = synthesize_answer(
        "== Entity: Mirathorn (location) ==\n  history: founded long ago",
        "Catch me up on Mirathorn",
        model="test-model",
        openai_client=client,
    )
    assert "Mirathorn" in answer
    assert len(client.chat.completions.calls) == 1


def test_system_prompt_contains_grounding_requirements() -> None:
    assert "using ONLY the facts provided" in SYSTEM_PROMPT
    assert "Do not invent information" in SYSTEM_PROMPT
    assert "CANON" in SYSTEM_PROMPT
    assert "PREP" in SYSTEM_PROMPT
    assert "OBSERVED" in SYSTEM_PROMPT
    assert 'Start with a "TL;DR:" line' in SYSTEM_PROMPT
    assert "Key Attributes" in SYSTEM_PROMPT
    assert "Do not enumerate attributes that are absent" in SYSTEM_PROMPT


def test_formatted_context_and_question_are_sent_to_model() -> None:
    client = _FakeOpenAIClient()
    context = "== Entity: Mirathorn (location) ==\n  economy: tourism"
    question = "Catch me up on Mirathorn"
    synthesize_answer(context, question, model="test-model", openai_client=client)

    call = client.chat.completions.calls[0]
    assert call["model"] == "test-model"
    assert call["messages"][0]["role"] == "system"
    assert SYSTEM_PROMPT.strip() in call["messages"][0]["content"]
    assert "Projection context:" in call["messages"][1]["content"]
    assert context in call["messages"][1]["content"]
    assert question in call["messages"][1]["content"]


def test_synthesize_wiki_mode_uses_wiki_system_prompt() -> None:
    client = _FakeOpenAIClient()
    synthesize_answer(
        "wiki text here",
        "What about the Wolf?",
        model="test-model",
        openai_client=client,
        wiki_mode=True,
    )
    call = client.chat.completions.calls[0]
    assert SYSTEM_PROMPT_WIKI.strip() in call["messages"][0]["content"]
    assert "Campaign context (wiki articles" in call["messages"][1]["content"]


def test_returns_llm_response_content() -> None:
    client = _FakeOpenAIClient()
    answer = synthesize_answer(
        "== Entity: Mirathorn (location) ==\n  defenses: city walls",
        "What are the defenses?",
        model="test-model",
        openai_client=client,
    )
    assert answer == "Mirathorn is a fortified city with active trade routes."
