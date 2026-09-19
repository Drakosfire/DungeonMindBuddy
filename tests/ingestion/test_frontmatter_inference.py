from __future__ import annotations

import asyncio
import inspect
import json
from pathlib import Path
from typing import Any

import pytest
from generationengine import (
    GenerationClient,
    InferenceObservation,
    ObservationState,
    TextRequest,
    TextResult,
)
from pydantic import ValidationError

from src.ingestion.frontmatter_inference import (
    OpenAIFrontmatterInferenceClient,
    ProposedDocumentMetadata,
    _frontmatter_inference_prompt,
    _load_model_id,
    infer_frontmatter_metadata,
    infer_frontmatter_metadata_heuristic,
)

ROOT = Path(__file__).resolve().parents[2]
DOCUMENT_METADATA_SCHEMA = ROOT / "schemas" / "v0.1" / "document_metadata.schema.json"


def _proposal_payload() -> dict[str, Any]:
    return {
        "title": "Battle with The Wolf and Aftermath",
        "document_class": "play",
        "canon_layer": "campaign",
        "campaign_id": "longmont-c1",
        "temporal_scope": "session_specific",
        "session": 8,
        "origin_session": 8,
        "last_updated_session": 8,
        "source_class": "observed_session_recap",
    }


def _queued_structured_result(parsed: dict[str, Any] | None) -> TextResult:
    return TextResult(
        parsed=parsed,
        observation=InferenceObservation(
            latency_ms=0,
            retry_count=0,
            state=ObservationState.COMPLETED,
        ),
    )


class RecordingFrontmatterClient:
    """GE-shaped test double: ``generate_structured`` records requests."""

    def __init__(self, parsed: dict[str, Any] | None = None, *, error: Exception | None = None) -> None:
        self.requests: list[TextRequest] = []
        self.calls = 0
        self._parsed = parsed if parsed is not None else _proposal_payload()
        self._error = error

    async def generate_structured(self, request: TextRequest) -> TextResult:
        self.calls += 1
        self.requests.append(request)
        if self._error is not None:
            raise self._error
        return _queued_structured_result(self._parsed)


def _sample_path() -> Path:
    return Path("/tmp/Longmont Campaign/Campaign 1/Battle with The Wolf and Aftermath.md")


def _sample_text() -> str:
    return "Session 8 recap. The wolf falls."


def test_no_client_uses_heuristic_with_zero_generationengine_calls(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    def _boom() -> GenerationClient:
        raise AssertionError("heuristic path must not construct GenerationEngine")

    monkeypatch.setattr(
        "src.ingestion.frontmatter_inference.GenerationClient.from_env",
        _boom,
    )
    path = _sample_path()
    text = _sample_text()
    metadata = infer_frontmatter_metadata(path=path, text=text)
    expected = infer_frontmatter_metadata_heuristic(path, text)
    assert metadata == expected


def test_generationengine_request_uses_explicit_openai_target() -> None:
    client = RecordingFrontmatterClient()
    adapter = OpenAIFrontmatterInferenceClient(client=client)
    path = _sample_path()
    text = _sample_text()
    infer_frontmatter_metadata(
        path=path,
        text=text,
        openai_client=adapter,
    )
    assert len(client.requests) == 1
    request = client.requests[0]
    assert request.provider == "openai"
    assert request.model == "gpt-5.3-codex"
    assert request.profile is None
    assert request.temperature is None
    assert request.system_prompt is None
    assert request.user_prompt == _frontmatter_inference_prompt(path=path, text=text)
    assert request.json_schema == ProposedDocumentMetadata.model_json_schema()
    assert request.schema_name == "frontmatter_metadata_proposal"


def test_explicit_alternate_model_reaches_generationengine_unchanged() -> None:
    client = RecordingFrontmatterClient()
    adapter = OpenAIFrontmatterInferenceClient(client=client)
    infer_frontmatter_metadata(
        path=_sample_path(),
        text=_sample_text(),
        model="gpt-4o-mini",
        openai_client=adapter,
    )
    assert client.requests[0].model == "gpt-4o-mini"


def test_policy_model_resolution_still_returns_gpt_53_codex() -> None:
    assert _load_model_id() == "gpt-5.3-codex"


def test_prompt_preserves_4000_character_excerpt() -> None:
    client = RecordingFrontmatterClient()
    adapter = OpenAIFrontmatterInferenceClient(client=client)
    text = "A" * 5000
    path = _sample_path()
    infer_frontmatter_metadata(path=path, text=text, openai_client=adapter)
    prompt = client.requests[0].user_prompt
    assert prompt == _frontmatter_inference_prompt(path=path, text=text)
    assert text[:4000] in prompt
    assert text[4000:] not in prompt
    assert prompt.endswith("A" * 4000)


def test_request_schema_is_proposal_shape_not_product_document_schema() -> None:
    client = RecordingFrontmatterClient()
    adapter = OpenAIFrontmatterInferenceClient(client=client)
    infer_frontmatter_metadata(
        path=_sample_path(),
        text=_sample_text(),
        openai_client=adapter,
    )
    schema = client.requests[0].json_schema
    assert schema == ProposedDocumentMetadata.model_json_schema()
    product = json.loads(DOCUMENT_METADATA_SCHEMA.read_text(encoding="utf-8"))
    assert schema != product
    assert "allOf" not in schema
    document_class = schema["properties"]["document_class"]
    canon_layer = schema["properties"]["canon_layer"]
    temporal_scope = schema["properties"]["temporal_scope"]
    source_class = schema["properties"]["source_class"]
    assert "enum" not in document_class
    assert "enum" not in canon_layer
    assert "enum" not in temporal_scope
    assert "enum" not in source_class
    assert product["properties"]["document_class"]["enum"] == [
        "world",
        "play",
        "planning",
        "reference",
    ]
    assert "allOf" in product


def test_parsed_object_is_constructed_via_proposed_document_metadata(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    seen: list[Any] = []
    original = ProposedDocumentMetadata.model_validate

    def _spy(payload: Any, *args: Any, **kwargs: Any) -> ProposedDocumentMetadata:
        seen.append(payload)
        return original(payload, *args, **kwargs)

    monkeypatch.setattr(ProposedDocumentMetadata, "model_validate", _spy)
    client = RecordingFrontmatterClient()
    adapter = OpenAIFrontmatterInferenceClient(client=client)
    metadata = infer_frontmatter_metadata(
        path=_sample_path(),
        text=_sample_text(),
        openai_client=adapter,
    )
    assert seen == [_proposal_payload()]
    assert metadata.title == "Battle with The Wolf and Aftermath"
    assert metadata.document_class == "play"
    assert metadata.canon_layer == "campaign"
    assert metadata.campaign_id == "longmont-c1"
    assert metadata.temporal_scope == "session_specific"
    assert metadata.session == 8
    assert metadata.origin_session == 8
    assert metadata.last_updated_session == 8
    assert metadata.source_class == "observed_session_recap"


def test_proposal_maps_to_document_metadata_like_heuristic_path() -> None:
    client = RecordingFrontmatterClient()
    adapter = OpenAIFrontmatterInferenceClient(client=client)
    metadata = infer_frontmatter_metadata(
        path=_sample_path(),
        text=_sample_text(),
        openai_client=adapter,
    )
    expected = infer_frontmatter_metadata_heuristic(_sample_path(), _sample_text())
    assert metadata == expected


def test_ordinary_synchronous_propose_succeeds_without_running_loop() -> None:
    client = RecordingFrontmatterClient()
    adapter = OpenAIFrontmatterInferenceClient(client=client)
    metadata = adapter.propose(model="gpt-5.3-codex", path=_sample_path(), text=_sample_text())
    assert metadata.document_class == "play"
    assert len(client.requests) == 1


def test_synchronous_propose_succeeds_from_running_event_loop() -> None:
    client = RecordingFrontmatterClient()
    adapter = OpenAIFrontmatterInferenceClient(client=client)

    async def _inside_running_loop() -> Any:
        return adapter.propose(model="gpt-5.3-codex", path=_sample_path(), text=_sample_text())

    metadata = asyncio.run(_inside_running_loop())
    assert metadata.document_class == "play"
    assert len(client.requests) == 1


def test_selected_inference_failure_propagates_and_does_not_fallback() -> None:
    client = RecordingFrontmatterClient(error=RuntimeError("structured generation failed"))
    adapter = OpenAIFrontmatterInferenceClient(client=client)
    with pytest.raises(RuntimeError, match="structured generation failed"):
        infer_frontmatter_metadata(
            path=_sample_path(),
            text=_sample_text(),
            openai_client=adapter,
        )
    assert client.calls == 1


def test_adapter_does_not_retry_generationengine_failures() -> None:
    client = RecordingFrontmatterClient(error=RuntimeError("structured generation failed"))
    adapter = OpenAIFrontmatterInferenceClient(client=client)
    with pytest.raises(RuntimeError, match="structured generation failed"):
        adapter.propose(model="gpt-5.3-codex", path=_sample_path(), text=_sample_text())
    assert client.calls == 1


def test_running_event_loop_raises_original_generationengine_failure() -> None:
    client = RecordingFrontmatterClient(error=RuntimeError("structured generation failed"))
    adapter = OpenAIFrontmatterInferenceClient(client=client)

    async def _inside_running_loop() -> Any:
        return adapter.propose(model="gpt-5.3-codex", path=_sample_path(), text=_sample_text())

    with pytest.raises(RuntimeError, match="structured generation failed"):
        asyncio.run(_inside_running_loop())


def test_invalid_parsed_payload_is_buddy_validation_error() -> None:
    client = RecordingFrontmatterClient(parsed={"title": 1})
    adapter = OpenAIFrontmatterInferenceClient(client=client)
    with pytest.raises(ValidationError):
        adapter.propose(model="gpt-5.3-codex", path=_sample_path(), text=_sample_text())


def test_missing_parsed_object_raises() -> None:
    class _NoneParsed:
        async def generate_structured(self, request: TextRequest) -> Any:
            class _Result:
                parsed = None

            return _Result()

    adapter = OpenAIFrontmatterInferenceClient(client=_NoneParsed())
    with pytest.raises(ValueError, match="no parsed metadata"):
        adapter.propose(model="gpt-5.3-codex", path=_sample_path(), text=_sample_text())


def test_production_client_is_constructed_inside_awaited_context(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    calls: list[int] = []
    fake = RecordingFrontmatterClient()

    def _from_env() -> Any:
        calls.append(id(asyncio.get_running_loop()))
        return fake

    monkeypatch.setattr(
        "src.ingestion.frontmatter_inference.GenerationClient.from_env",
        _from_env,
    )
    adapter = OpenAIFrontmatterInferenceClient()
    assert calls == []
    metadata = adapter.propose(model="gpt-5.3-codex", path=_sample_path(), text=_sample_text())
    assert metadata.document_class == "play"
    assert len(calls) == 1
    metadata = adapter.propose(model="gpt-5.3-codex", path=_sample_path(), text=_sample_text())
    assert metadata.document_class == "play"
    assert len(calls) == 2
    assert calls[0] != 0


def test_injected_seam_is_generationengine_shaped() -> None:
    client = RecordingFrontmatterClient()
    adapter = OpenAIFrontmatterInferenceClient(client=client)
    adapter.propose(model="gpt-5.3-codex", path=_sample_path(), text=_sample_text())
    assert hasattr(client, "generate_structured")
    assert not hasattr(client, "responses")
    source = inspect.getsource(OpenAIFrontmatterInferenceClient)
    assert "generate_structured" in source
    assert "responses.parse" not in source
    assert "responses_parse" not in source
    assert "DungeonMindApiClient" not in source
    module_source = inspect.getsource(inspect.getmodule(OpenAIFrontmatterInferenceClient))
    assert "from openai" not in module_source
    assert "import openai" not in module_source
    assert "DungeonMindApiClient" not in module_source
