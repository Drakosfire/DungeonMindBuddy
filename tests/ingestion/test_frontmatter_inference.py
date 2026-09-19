from __future__ import annotations

import asyncio
import inspect
import io
import json
from contextlib import redirect_stdout
from pathlib import Path
from typing import Any

import pytest
from generationengine import InferenceObservation, ObservationState, TextRequest, TextResult
from pydantic import ValidationError

from src.cli import DungeonBuddyCLI
from src.ingestion.frontmatter_inference import (
    OpenAIFrontmatterInferenceClient,
    ProposedDocumentMetadata,
    _frontmatter_inference_prompt,
    _load_model_id,
    infer_frontmatter_metadata,
    infer_frontmatter_metadata_heuristic,
)

ROOT = Path(__file__).resolve().parents[2]
PRODUCT_SCHEMA_PATH = ROOT / "schemas" / "v0.1" / "document_metadata.schema.json"

_PROPOSAL = {
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

_PLAY_PATH = Path("/tmp/Longmont Campaign/Campaign 1/Battle with The Wolf and Aftermath.md")
_PLAY_TEXT = "Session 8 recap. The wolf falls."
_WORLD_PATH = Path("/tmp/Elderwyld/Cities/Mirathorn/The City of Mirathorn.md")
_WORLD_TEXT = "Mirathorn overview and city notes."


def _queued_structured_result(parsed: dict[str, Any]) -> TextResult:
    return TextResult(
        parsed=parsed,
        observation=InferenceObservation(
            latency_ms=0,
            retry_count=0,
            state=ObservationState.COMPLETED,
        ),
    )


class RecordingStructuredClient:
    def __init__(self, payloads: list[dict[str, Any]] | None = None) -> None:
        self._payloads = [dict(p) for p in (payloads or [_PROPOSAL])]
        self._i = 0
        self.requests: list[TextRequest] = []

    async def generate_structured(self, request: TextRequest) -> TextResult:
        self.requests.append(request)
        if self._i >= len(self._payloads):
            raise RuntimeError("RecordingStructuredClient: no more queued responses")
        parsed = self._payloads[self._i]
        self._i += 1
        return _queued_structured_result(parsed)


def test_no_client_uses_heuristic_with_zero_generationengine_calls(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    def _boom() -> Any:
        raise AssertionError("no-client path must not construct GenerationEngine")

    monkeypatch.setattr(
        "src.ingestion.frontmatter_inference.GenerationClient.from_env",
        _boom,
    )
    metadata = infer_frontmatter_metadata(path=_WORLD_PATH, text=_WORLD_TEXT)
    expected = infer_frontmatter_metadata_heuristic(_WORLD_PATH, _WORLD_TEXT)
    assert metadata == expected


def test_selected_client_uses_generationengine_and_skips_heuristic(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    def _boom() -> Any:
        raise AssertionError("injected client must not construct GenerationEngine")

    monkeypatch.setattr(
        "src.ingestion.frontmatter_inference.GenerationClient.from_env",
        _boom,
    )
    client = RecordingStructuredClient()
    metadata = infer_frontmatter_metadata(
        path=_PLAY_PATH,
        text=_PLAY_TEXT,
        openai_client=OpenAIFrontmatterInferenceClient(client=client),
    )
    assert metadata.title == _PROPOSAL["title"]
    assert metadata.document_class == "play"
    assert metadata.campaign_id == "longmont-c1"
    assert metadata.session == 8
    assert len(client.requests) == 1


def test_generationengine_request_uses_explicit_openai_target(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    client = RecordingStructuredClient()
    infer_frontmatter_metadata(
        path=_PLAY_PATH,
        text=_PLAY_TEXT,
        openai_client=OpenAIFrontmatterInferenceClient(client=client),
    )
    assert len(client.requests) == 1
    request = client.requests[0]
    assert request.provider == "openai"
    assert request.model == "gpt-5.3-codex"
    assert request.profile is None
    assert request.temperature is None
    assert request.system_prompt is None
    assert request.user_prompt == _frontmatter_inference_prompt(_PLAY_PATH, _PLAY_TEXT)
    assert request.json_schema == ProposedDocumentMetadata.model_json_schema()
    assert request.schema_name == "frontmatter_metadata_proposal"


def test_explicit_alternate_model_reaches_generationengine_unchanged() -> None:
    client = RecordingStructuredClient()
    infer_frontmatter_metadata(
        path=_PLAY_PATH,
        text=_PLAY_TEXT,
        model="gpt-4o-mini",
        openai_client=OpenAIFrontmatterInferenceClient(client=client),
    )
    assert client.requests[0].model == "gpt-4o-mini"


def test_policy_model_resolution_still_returns_gpt_53_codex() -> None:
    assert _load_model_id() == "gpt-5.3-codex"


def test_prompt_preserves_4000_character_excerpt() -> None:
    text = "a" * 5000
    client = RecordingStructuredClient()
    infer_frontmatter_metadata(
        path=_PLAY_PATH,
        text=text,
        openai_client=OpenAIFrontmatterInferenceClient(client=client),
    )
    prompt = client.requests[0].user_prompt
    assert prompt == _frontmatter_inference_prompt(_PLAY_PATH, text)
    assert text[:4000] in prompt
    assert text[4000:] not in prompt
    assert prompt.endswith("a" * 4000)


def test_request_schema_is_proposal_shape_not_product_document_schema() -> None:
    client = RecordingStructuredClient()
    infer_frontmatter_metadata(
        path=_PLAY_PATH,
        text=_PLAY_TEXT,
        openai_client=OpenAIFrontmatterInferenceClient(client=client),
    )
    schema = client.requests[0].json_schema
    product_schema = json.loads(PRODUCT_SCHEMA_PATH.read_text(encoding="utf-8"))
    assert schema == ProposedDocumentMetadata.model_json_schema()
    assert schema != product_schema
    assert "enum" not in schema["properties"]["document_class"]
    assert "enum" not in schema["properties"]["canon_layer"]
    assert "enum" not in schema["properties"]["temporal_scope"]
    assert "enum" not in schema["properties"]["source_class"]
    assert "allOf" not in schema
    assert "if" not in schema
    assert "session_pc_roster" not in schema["properties"]


def test_parsed_object_is_buddy_validated_then_mapped() -> None:
    client = RecordingStructuredClient()
    metadata = OpenAIFrontmatterInferenceClient(client=client).propose(
        model="gpt-5.3-codex",
        path=_PLAY_PATH,
        text=_PLAY_TEXT,
    )
    assert metadata.title == _PROPOSAL["title"]
    assert metadata.document_class == _PROPOSAL["document_class"]
    assert metadata.canon_layer == _PROPOSAL["canon_layer"]
    assert metadata.campaign_id == _PROPOSAL["campaign_id"]
    assert metadata.temporal_scope == _PROPOSAL["temporal_scope"]
    assert metadata.session == _PROPOSAL["session"]
    assert metadata.origin_session == _PROPOSAL["origin_session"]
    assert metadata.last_updated_session == _PROPOSAL["last_updated_session"]
    assert metadata.source_class == _PROPOSAL["source_class"]


def test_incomplete_parsed_object_raises_validation_error() -> None:
    client = RecordingStructuredClient([{"title": "only-title"}])
    with pytest.raises(ValidationError):
        OpenAIFrontmatterInferenceClient(client=client).propose(
            model="gpt-5.3-codex",
            path=_PLAY_PATH,
            text=_PLAY_TEXT,
        )


def test_missing_parsed_output_raises() -> None:
    class _EmptyParsed:
        async def generate_structured(self, request: Any) -> Any:
            class _Result:
                parsed = None

            return _Result()

    with pytest.raises(ValueError, match="no parsed metadata"):
        OpenAIFrontmatterInferenceClient(client=_EmptyParsed()).propose(
            model="gpt-5.3-codex",
            path=_PLAY_PATH,
            text=_PLAY_TEXT,
        )


def test_ordinary_synchronous_propose_succeeds_without_running_loop() -> None:
    client = RecordingStructuredClient()
    metadata = OpenAIFrontmatterInferenceClient(client=client).propose(
        model="gpt-5.3-codex",
        path=_PLAY_PATH,
        text=_PLAY_TEXT,
    )
    assert metadata.document_class == "play"
    assert len(client.requests) == 1


def test_synchronous_propose_succeeds_from_running_event_loop() -> None:
    client = RecordingStructuredClient()

    async def _inside_running_loop() -> Any:
        return OpenAIFrontmatterInferenceClient(client=client).propose(
            model="gpt-5.3-codex",
            path=_PLAY_PATH,
            text=_PLAY_TEXT,
        )

    metadata = asyncio.run(_inside_running_loop())
    assert metadata.document_class == "play"
    assert len(client.requests) == 1


def test_selected_inference_failure_propagates_and_does_not_fallback() -> None:
    class _FailClient:
        async def generate_structured(self, request: Any) -> Any:
            raise RuntimeError("structured generation failed")

    with pytest.raises(RuntimeError, match="structured generation failed"):
        infer_frontmatter_metadata(
            path=_PLAY_PATH,
            text=_PLAY_TEXT,
            openai_client=OpenAIFrontmatterInferenceClient(client=_FailClient()),
        )


def test_adapter_does_not_retry_generationengine_failures() -> None:
    class _CountingFailClient:
        def __init__(self) -> None:
            self.calls = 0

        async def generate_structured(self, request: Any) -> Any:
            self.calls += 1
            raise RuntimeError("structured generation failed")

    client = _CountingFailClient()
    with pytest.raises(RuntimeError, match="structured generation failed"):
        OpenAIFrontmatterInferenceClient(client=client).propose(
            model="gpt-5.3-codex",
            path=_PLAY_PATH,
            text=_PLAY_TEXT,
        )
    assert client.calls == 1


def test_running_event_loop_raises_original_generationengine_failure() -> None:
    class _FailClient:
        async def generate_structured(self, request: Any) -> Any:
            raise RuntimeError("structured generation failed")

    async def _inside_running_loop() -> Any:
        return OpenAIFrontmatterInferenceClient(client=_FailClient()).propose(
            model="gpt-5.3-codex",
            path=_PLAY_PATH,
            text=_PLAY_TEXT,
        )

    with pytest.raises(RuntimeError, match="structured generation failed"):
        asyncio.run(_inside_running_loop())


def test_production_client_is_constructed_inside_awaited_execution(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    seen: list[asyncio.AbstractEventLoop] = []

    class _FakeGE:
        async def generate_structured(self, request: TextRequest) -> TextResult:
            return _queued_structured_result(_PROPOSAL)

    def _from_env() -> _FakeGE:
        seen.append(asyncio.get_running_loop())
        return _FakeGE()

    monkeypatch.setattr(
        "src.ingestion.frontmatter_inference.GenerationClient.from_env",
        _from_env,
    )
    metadata = OpenAIFrontmatterInferenceClient().propose(
        model="gpt-5.3-codex",
        path=_PLAY_PATH,
        text=_PLAY_TEXT,
    )
    assert metadata.document_class == "play"
    assert len(seen) == 1


def test_cli_selects_heuristic_when_openai_api_key_absent(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    captured: dict[str, Any] = {}

    def _fake_infer(**kwargs: Any) -> Any:
        captured.update(kwargs)
        return infer_frontmatter_metadata_heuristic(kwargs["path"], kwargs["text"])

    monkeypatch.delenv("OPENAI_API_KEY", raising=False)
    monkeypatch.setattr("src.cli.infer_frontmatter_metadata", _fake_infer)
    monkeypatch.setattr("builtins.input", lambda _: "n")
    cli = DungeonBuddyCLI(store_dir=tmp_path / "store", verbose=False)
    with redirect_stdout(io.StringIO()):
        confirmed = cli._confirm_inferred_frontmatter(_WORLD_PATH, _WORLD_TEXT)
    assert confirmed is False
    assert captured["openai_client"] is None


def test_cli_selects_inference_adapter_when_openai_api_key_present(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    captured: dict[str, Any] = {}

    def _fake_infer(**kwargs: Any) -> Any:
        captured.update(kwargs)
        return infer_frontmatter_metadata_heuristic(kwargs["path"], kwargs["text"])

    monkeypatch.setenv("OPENAI_API_KEY", "test-key")
    monkeypatch.setattr("src.cli.infer_frontmatter_metadata", _fake_infer)
    monkeypatch.setattr("builtins.input", lambda _: "n")
    cli = DungeonBuddyCLI(store_dir=tmp_path / "store", verbose=False)
    with redirect_stdout(io.StringIO()):
        confirmed = cli._confirm_inferred_frontmatter(_PLAY_PATH, _PLAY_TEXT)
    assert confirmed is False
    assert isinstance(captured["openai_client"], OpenAIFrontmatterInferenceClient)


def test_production_path_no_longer_owns_openai_or_wrapper_telemetry() -> None:
    import src.ingestion.frontmatter_inference as frontmatter_inference

    source = inspect.getsource(OpenAIFrontmatterInferenceClient)
    module_source = inspect.getsource(frontmatter_inference)
    assert "from openai import" not in module_source
    assert "responses.parse" not in source
    assert "responses_parse" not in module_source
    assert "DungeonMindApiClient" not in module_source
    assert "generate_structured" in source
    assert "run_awaitable_sync" in source
