from __future__ import annotations

import json
import sys
from types import SimpleNamespace

import pytest

from src.graph_memory.extraction.preview_candidate_graph_extractor import (
    FixtureCandidateGraphModelClient,
    OpenAICandidateGraphModelClient,
    PreviewCandidateGraphParseError,
    PreviewCandidateGraphExtractionOptions,
    build_preview_candidate_graph_prompt,
    enforce_preview_only_candidate_graph,
    extract_preview_candidate_graph,
    _responses_create_kwargs,
)


def test_sanitizes_preview_only_diagnostics_and_arrays() -> None:
    graph = enforce_preview_only_candidate_graph(
        {
            "candidate_nodes": [{"id": "node:bonogo", "label": "Bonogo", "evidence_refs": ["ev:1"]}, "bad"],
            "candidate_edges": None,
            "session_beats": [{"summary": "A beat", "evidence_refs": ["ev:1"]}],
            "evidence_refs": [{"id": "ev:1", "span_id": "session-22:recap:full_text"}, {"id": "bad"}],
            "diagnostics": {
                "preview_only": False,
                "canon_promotion": True,
                "approved_memory_write": True,
                "corpus_mutation": True,
                "production_retrieval": True,
            },
        }
    )

    assert graph["diagnostics"]["preview_only"] is True
    assert graph["diagnostics"]["canon_promotion"] is False
    assert graph["diagnostics"]["approved_memory_write"] is False
    assert graph["diagnostics"]["corpus_mutation"] is False
    assert graph["diagnostics"]["production_retrieval"] is False
    assert len(graph["candidate_nodes"]) == 1
    assert graph["candidate_edges"] == []
    assert len(graph["evidence_refs"]) == 1


def test_rejects_malformed_non_object_model_output() -> None:
    with pytest.raises(ValueError, match="JSON object"):
        enforce_preview_only_candidate_graph([])  # type: ignore[arg-type]


def test_extract_preview_candidate_graph_uses_fixture_client() -> None:
    raw = json.dumps(
        {
            "candidate_nodes": [],
            "candidate_edges": [],
            "session_beats": [],
            "ignored_or_deferred_candidates": [{"summary": "uncertain spelling"}],
            "source_artifacts": [],
            "evidence_refs": [],
        }
    )
    result = extract_preview_candidate_graph(
        PreviewCandidateGraphExtractionOptions(
            campaign_id="longmont-c2",
            session_id="session-22",
            recap_markdown="Bonogo found a clue.",
            source_span_id="session-22:recap:full_text",
        ),
        client=FixtureCandidateGraphModelClient(raw),
    )

    assert result.raw_model_response == raw
    assert result.candidate_graph["ignored_or_deferred_candidates"] == [{"summary": "uncertain spelling"}]
    assert result.candidate_graph["diagnostics"]["preview_only"] is True


def test_extract_preview_candidate_graph_preserves_invalid_json_response() -> None:
    raw = '{"candidate_nodes": [{"id": "node:bad"}'

    with pytest.raises(PreviewCandidateGraphParseError) as exc_info:
        extract_preview_candidate_graph(
            PreviewCandidateGraphExtractionOptions(
                campaign_id="longmont-c2",
                session_id="session-22",
                recap_markdown="Bonogo found a clue.",
                source_span_id="session-22:recap:full_text",
            ),
            client=FixtureCandidateGraphModelClient(raw),
        )

    assert "candidate graph model returned invalid JSON" in str(exc_info.value)
    assert exc_info.value.raw_model_response == raw


def test_openai_client_reports_incomplete_response(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    raw = '{"candidate_nodes": ['
    captured: dict[str, object] = {}

    class FakeResponse:
        output_text = raw
        status = "incomplete"
        incomplete_details = {"reason": "max_output_tokens"}

        def model_dump_json(self) -> str:
            return "{}"

    class FakeResponses:
        def create(self, **kwargs):  # noqa: ANN003, ANN201
            captured.update(kwargs)
            return FakeResponse()

    class FakeOpenAI:
        def __init__(self):
            self.responses = FakeResponses()

    monkeypatch.setenv("OPENAI_API_KEY", "test-key")
    monkeypatch.setitem(sys.modules, "openai", SimpleNamespace(OpenAI=FakeOpenAI))

    with pytest.raises(PreviewCandidateGraphParseError) as exc_info:
        OpenAICandidateGraphModelClient().extract_candidate_graph(
            "prompt",
            model_id="gpt-5-mini",
        )

    assert "response incomplete: max_output_tokens" in str(exc_info.value)
    assert exc_info.value.raw_model_response == raw
    assert "max_output_tokens" not in captured


def test_prompt_prefers_paragraph_source_span_catalog() -> None:
    prompt = build_preview_candidate_graph_prompt(
        PreviewCandidateGraphExtractionOptions(
            campaign_id="longmont-c2",
            session_id="session-22",
            recap_markdown="The group scouts the Mireward road.",
            source_span_id="session-22:recap:full_text",
            source_span_catalog=[
                {"span_id": "session-22:recap:paragraph:001", "kind": "paragraph", "ordinal": 1, "text_excerpt": "The group scouts the Mireward road."},
                {"span_id": "session-22:recap:full_text", "kind": "full_text", "ordinal": 0},
            ],
        )
    )

    assert "Prefer paragraph span ids" in prompt
    assert "session-22:recap:paragraph:001" in prompt
    assert "full_text" in prompt
    assert '{"id":"ev:1","span_id":"<catalog span id>","text_excerpt":"short supporting excerpt"}' in prompt


def test_responses_payload_uses_strict_schema_without_token_or_temperature_cap() -> None:
    kwargs = _responses_create_kwargs(
        prompt="Extract JSON.",
        model_id="gpt-5-mini",
    )

    assert kwargs["model"] == "gpt-5-mini"
    response_format = kwargs["text"]["format"]
    assert response_format["type"] == "json_schema"
    assert response_format["name"] == "preview_candidate_graph"
    assert response_format["strict"] is True
    assert response_format["schema"]["required"] == [
        "candidate_nodes",
        "candidate_edges",
        "session_beats",
        "ignored_or_deferred_candidates",
        "source_artifacts",
        "evidence_refs",
        "diagnostics",
    ]
    assert response_format["schema"]["additionalProperties"] is False
    assert "temperature" not in kwargs
    assert "max_output_tokens" not in kwargs
