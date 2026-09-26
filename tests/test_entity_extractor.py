from __future__ import annotations

import asyncio
from pathlib import Path
from types import SimpleNamespace
from typing import Any

import blake3
import pytest

from src.contracts.schema_validation import validate_many
from src.ingestion.entity_extractor import (
    AsyncOpenAIResponsesEntityClient,
    OpenAIResponsesEntityClient,
    extract_entities_batch,
    run_entity_extraction,
)


def _evidence(evidence_id: str, text: str, index: int) -> dict[str, Any]:
    legacy_hash = blake3.blake3(text.encode("utf-8")).hexdigest()
    return {
        "schema_version": "0.1.0",
        "created_at": "2026-03-27T00:00:00Z",
        "updated_at": "2026-03-27T00:00:00Z",
        "record_status": "active",
        "evidence_id": evidence_id,
        "document_id": "doc_test",
        "document_type": "world_reference",
        "document_title": "Test Doc",
        "source_class": "seed_reference",
        "canon_layer": "world",
        "campaign_id": None,
        "text": text,
        "section_path": ["Test"],
        "paragraph_index": index,
        "source_order_index": index,
        "line_span": {"start": 1, "end": 1},
        "char_span": None,
        "inferred_session": None,
        "speaker_or_subject": None,
        "notes": None,
        "source_anchors": [
            {
                "source_type": "legacy_unanchored",
                "path": "fixture/test_evidence_unit.md",
                "line_start": 1,
                "line_end": 1,
                "content_hash": legacy_hash,
                "commit_sha": "",
                "agent": None,
                "thread_id": None,
            }
        ],
    }


class _StubExtractorClient:
    def __init__(self) -> None:
        self.calls = 0

    def extract_entities(self, **kwargs: Any) -> dict[str, Any]:
        self.calls += 1
        text = str(kwargs["evidence_unit"]["text"])
        if "hero" in text.lower():
            return {
                "entities": [
                    {
                        "entity_class": "actor",
                        "display_name": "Captain Lysandra Ironveil!",
                        "aliases": ["Lysandra"],
                        "is_new": True,
                    }
                ]
            }
        return {
            "entities": [
                {
                        "entity_class": "group",
                    "display_name": "Shepherd's Flock",
                    "aliases": ["The Flock"],
                    "is_new": True,
                }
            ]
        }


def test_entity_id_generation_normalizes_display_name(tmp_path: Path) -> None:
    client = _StubExtractorClient()
    out = run_entity_extraction(
        [_evidence("evid_1", "A hero arrives: Captain Lysandra Ironveil! leads the watch.", 0)],
        cache_dir=tmp_path / "cache",
        openai_client=client,
    )
    entities = out["entities"]

    assert len(entities) == 1
    assert entities[0]["entity_id"] == "ent_captain_lysandra_ironveil"
    assert entities[0]["display_name"] == "Captain Lysandra Ironveil!"


def test_entity_merge_dedupes_alias_overlap(tmp_path: Path) -> None:
    class OverlapClient:
        def extract_entities(self, **kwargs: Any) -> dict[str, Any]:
            text = str(kwargs["evidence_unit"]["text"])
            if "first" in text:
                return {
                    "entities": [
                        {
                            "entity_class": "group",
                            "display_name": "Shepherd's Flock",
                            "aliases": ["The Flock"],
                            "is_new": True,
                        }
                    ]
                }
            return {
                "entities": [
                    {
                        "entity_class": "group",
                        "display_name": "The Flock",
                        "aliases": ["Shepherd's Flock"],
                        "is_new": True,
                    }
                ]
            }

    out = run_entity_extraction(
        [
            _evidence("evid_first", "first mention of Shepherd's Flock", 0),
            _evidence("evid_second", "second mention of The Flock", 1),
        ],
        cache_dir=tmp_path / "cache",
        openai_client=OverlapClient(),
    )
    entities = out["entities"]

    assert len(entities) == 1
    aliases = set(entities[0]["aliases"])
    assert "Shepherd's Flock" in aliases
    assert "The Flock" in aliases


def test_cache_hit_skips_second_client_call(tmp_path: Path) -> None:
    client = _StubExtractorClient()
    evidence = [_evidence("evid_1", "A hero arrives.", 0)]
    cache_dir = tmp_path / "cache"

    first = run_entity_extraction(
        evidence,
        cache_dir=cache_dir,
        openai_client=client,
    )
    second = run_entity_extraction(
        evidence,
        cache_dir=cache_dir,
        openai_client=client,
    )

    assert first["entities"] == second["entities"]
    assert first["usage"]["api_calls"] == 1
    assert second["usage"]["api_calls"] == 0
    assert second["cache_hits"] == 1
    assert client.calls == 1


def test_batch_size_combines_uncached_units_into_one_batched_call(tmp_path: Path) -> None:
    class _BatchedAsyncClient:
        def __init__(self) -> None:
            self.batched_calls = 0

        async def extract_entities_batched(self, **kwargs: Any) -> dict[str, Any]:
            self.batched_calls += 1
            return {
                "results": [
                    {
                        "unit_index": 0,
                        "entities": [
                            {
                                "entity_class": "place",
                                "display_name": "Alpha Ruins",
                                "aliases": [],
                                "is_new": True,
                            }
                        ],
                    },
                    {
                        "unit_index": 1,
                        "entities": [
                            {
                                "entity_class": "place",
                                "display_name": "Beta Woods",
                                "aliases": [],
                                "is_new": True,
                            }
                        ],
                    },
                ],
                "_usage": {"input_tokens": 10, "output_tokens": 5, "cached_tokens": 0},
            }

        async def extract_entities(self, **kwargs: Any) -> dict[str, Any]:
            raise AssertionError("extract_entities should not run when batch_size > 1")

        async def aclose(self) -> None:
            return None

    client = _BatchedAsyncClient()
    out = asyncio.run(
        extract_entities_batch(
            [
                _evidence("evid_a", "Travelers visit the Alpha Ruins often.", 0),
                _evidence("evid_b", "The Beta Woods are dense.", 1),
            ],
            cache_dir=tmp_path / "cache",
            openai_client=client,
            allow_heuristic_fallback=False,
            batch_size=2,
            concurrency=4,
        )
    )
    assert client.batched_calls == 1
    assert out["usage"]["api_calls"] == 1
    assert len(out["entities"]) == 2


def test_output_entities_validate_against_schema(tmp_path: Path) -> None:
    out = run_entity_extraction(
        [_evidence("evid_1", "Mirathorn lies near Lake Mirathorn.", 0)],
        cache_dir=tmp_path / "cache",
    )
    entities = out["entities"]
    assert entities
    validate_many(entities, "entity.schema.json")


def test_disallow_heuristic_fallback_requires_client(tmp_path: Path) -> None:
    with pytest.raises(ValueError, match="Heuristic fallback is disabled"):
        run_entity_extraction(
            [_evidence("evid_1", "Mirathorn lies near Lake Mirathorn.", 0)],
            cache_dir=tmp_path / "cache",
            allow_heuristic_fallback=False,
        )


def test_openai_responses_adapter_parses_structured_output() -> None:
    class _FakeGenerationClient:
        def __init__(self) -> None:
            self.requests: list[Any] = []
            self.close_calls = 0

        async def generate_structured(self, request: Any) -> Any:
            self.requests.append(request)
            return SimpleNamespace(
                parsed={
                "entities": [
                    {
                    "entity_type": "location",
                    "entity_class": "place",
                    "display_name": "Lake Mirathorn",
                    "aliases": [],
                    "is_new": True,
                    }
                ]
                },
                observation=SimpleNamespace(
                    input_tokens=120,
                    output_tokens=30,
                    cached_input_tokens=7,
                    provider_attempt_count=2,
                ),
            )

        async def aclose(self) -> None:
            self.close_calls += 1

    generation_client = _FakeGenerationClient()
    adapter = OpenAIResponsesEntityClient(
        generation_client_factory=lambda: generation_client
    )
    payload = adapter.extract_entities(
        model="gpt-5.3-codex",
        system_prompt="system instructions",
        user_prompt="extract",
        evidence_unit={},
        known_entities=[],
        prompt_id="test",
    )
    assert payload["entities"][0]["display_name"] == "Lake Mirathorn"
    assert payload["_usage"]["input_tokens"] == 120
    assert payload["_usage"]["output_tokens"] == 30
    assert payload["_usage"]["cached_tokens"] == 7
    assert payload["_usage"]["api_calls"] == 2
    assert generation_client.close_calls == 1
    request = generation_client.requests[0]
    assert request.system_prompt == "system instructions"
    assert request.user_prompt == "extract"
    assert request.provider == "openai"
    assert request.model == "gpt-5.3-codex"
    assert request.profile is None
    assert request.temperature is None
    assert request.json_object is False
    assert request.max_output_tokens is None
    assert request.schema_name == "entity_extraction"


def test_async_batched_adapter_uses_exact_ge_request_and_revalidates() -> None:
    class BatchedGenerationClient:
        def __init__(self) -> None:
            self.requests: list[Any] = []
            self.close_calls = 0

        async def generate_structured(self, request: Any) -> Any:
            self.requests.append(request)
            return SimpleNamespace(
                parsed={"results": [{"unit_index": 0, "entities": []}]},
                observation=SimpleNamespace(
                    input_tokens=None,
                    output_tokens=None,
                    cached_input_tokens=None,
                    provider_attempt_count=2,
                ),
            )

        async def aclose(self) -> None:
            self.close_calls += 1

    generation_client = BatchedGenerationClient()
    adapter = AsyncOpenAIResponsesEntityClient(
        generation_client=generation_client
    )
    payload = asyncio.run(
        adapter.extract_entities_batched(
            model="alternate-model",
            system_prompt="batch system",
            user_prompt="batch user",
            prompt_id="test",
        )
    )

    assert payload["results"][0]["unit_index"] == 0
    assert payload["_usage"] == {
        "input_tokens": 0,
        "output_tokens": 0,
        "cached_tokens": 0,
        "api_calls": 2,
    }
    request = generation_client.requests[0]
    assert request.system_prompt == "batch system"
    assert request.user_prompt == "batch user"
    assert request.provider == "openai"
    assert request.model == "alternate-model"
    assert request.profile is None
    assert request.temperature is None
    assert request.json_object is False
    assert request.max_output_tokens is None
    assert request.schema_name == "batched_entity_extraction"


def test_entity_adapter_revalidates_ge_parsed_payload() -> None:
    class InvalidGenerationClient:
        async def generate_structured(self, request: Any) -> Any:
            return SimpleNamespace(
                parsed={"entities": [{"invalid": True}]},
                observation=SimpleNamespace(
                    input_tokens=1,
                    output_tokens=1,
                    cached_input_tokens=0,
                    provider_attempt_count=1,
                ),
            )

        async def aclose(self) -> None:
            return None

    adapter = AsyncOpenAIResponsesEntityClient(
        generation_client=InvalidGenerationClient()
    )

    with pytest.raises(ValueError):
        asyncio.run(
            adapter.extract_entities(
                model="test-model",
                system_prompt="system",
                user_prompt="user",
                evidence_unit={},
                known_entities=[],
                prompt_id="test",
            )
        )


def test_sync_entity_adapter_constructs_and_closes_per_bridge_call() -> None:
    created: list[Any] = []

    class GenerationClientStub:
        def __init__(self) -> None:
            self.close_calls = 0

        async def generate_structured(self, request: Any) -> Any:
            return SimpleNamespace(
                parsed={"entities": []},
                observation=SimpleNamespace(
                    input_tokens=1,
                    output_tokens=1,
                    cached_input_tokens=0,
                    provider_attempt_count=1,
                ),
            )

        async def aclose(self) -> None:
            self.close_calls += 1

    def factory() -> GenerationClientStub:
        client = GenerationClientStub()
        created.append(client)
        return client

    adapter = OpenAIResponsesEntityClient(generation_client_factory=factory)
    for _ in range(2):
        adapter.extract_entities(
            model="test-model",
            system_prompt="system",
            user_prompt="user",
            evidence_unit={},
            known_entities=[],
            prompt_id="test",
        )

    assert len(created) == 2
    assert [client.close_calls for client in created] == [1, 1]


def test_async_adapter_constructs_production_ge_inside_active_loop_once(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    created: list[Any] = []
    construction_loops: list[asyncio.AbstractEventLoop] = []

    class GenerationClientStub:
        def __init__(self) -> None:
            self.requests: list[Any] = []
            self.close_calls = 0

        async def generate_structured(self, request: Any) -> Any:
            self.requests.append(request)
            return SimpleNamespace(
                parsed={"entities": []},
                observation=SimpleNamespace(
                    input_tokens=1,
                    output_tokens=1,
                    cached_input_tokens=0,
                    provider_attempt_count=1,
                ),
            )

        async def aclose(self) -> None:
            self.close_calls += 1

    def from_env() -> GenerationClientStub:
        construction_loops.append(asyncio.get_running_loop())
        client = GenerationClientStub()
        created.append(client)
        return client

    monkeypatch.setattr(
        "src.ingestion.entity_extractor.GenerationClient.from_env",
        classmethod(lambda cls: from_env()),
    )
    adapter = AsyncOpenAIResponsesEntityClient()

    result = run_entity_extraction(
        [_evidence("evid_a", "Mirathorn is fortified.", 0)],
        cache_dir=tmp_path / "cache",
        openai_client=adapter,
        allow_heuristic_fallback=False,
        model="alternate-model",
    )

    assert result["model_name"] == "alternate-model"
    assert len(created) == 1
    assert len(construction_loops) == 1
    assert created[0].requests[0].model == "alternate-model"
    assert created[0].close_calls == 1


def test_async_adapter_shares_one_ge_client_across_standard_and_recap_calls(
    tmp_path: Path,
) -> None:
    class ConcurrentGenerationClient:
        def __init__(self) -> None:
            self.requests: list[Any] = []
            self.entered = 0
            self.active = 0
            self.max_active = 0
            self.overlap = asyncio.Event()
            self.close_calls = 0

        async def generate_structured(self, request: Any) -> Any:
            self.requests.append(request)
            self.entered += 1
            self.active += 1
            self.max_active = max(self.max_active, self.active)
            if self.entered == 2:
                self.overlap.set()
            try:
                await asyncio.wait_for(self.overlap.wait(), timeout=1)
                parsed = (
                    {"entities": [], "event_records": [], "claims": []}
                    if request.schema_name == "recap_extraction"
                    else {"entities": []}
                )
                return SimpleNamespace(
                    parsed=parsed,
                    observation=SimpleNamespace(
                        input_tokens=3,
                        output_tokens=2,
                        cached_input_tokens=1,
                        provider_attempt_count=2,
                    ),
                )
            finally:
                self.active -= 1

        async def aclose(self) -> None:
            assert self.active == 0
            self.close_calls += 1

    recap = _evidence("evid_recap", "The party reached Mirathorn.", 1)
    recap["document_type"] = "session_recap"
    recap["source_class"] = "observed_session_recap"
    recap["canon_layer"] = "campaign"
    generation_client = ConcurrentGenerationClient()
    adapter = AsyncOpenAIResponsesEntityClient(
        generation_client=generation_client
    )

    result = asyncio.run(
        extract_entities_batch(
            [
                _evidence("evid_standard", "Mirathorn is fortified.", 0),
                recap,
            ],
            cache_dir=tmp_path / "cache",
            openai_client=adapter,
            allow_heuristic_fallback=False,
            concurrency=2,
        )
    )

    assert generation_client.max_active == 2
    assert generation_client.close_calls == 1
    assert {request.schema_name for request in generation_client.requests} == {
        "entity_extraction",
        "recap_extraction",
    }
    assert result["usage"] == {
        "input_tokens": 6,
        "output_tokens": 4,
        "cached_tokens": 2,
        "api_calls": 4,
    }


def test_concurrent_ge_failure_drains_sibling_before_client_close(
    tmp_path: Path,
) -> None:
    class ConcurrentFailureGenerationClient:
        def __init__(self) -> None:
            self.requests: list[Any] = []
            self.entered = 0
            self.both_entered = asyncio.Event()
            self.sibling_terminated = asyncio.Event()
            self.closed_after_sibling = False
            self.close_calls = 0

        async def generate_structured(self, request: Any) -> Any:
            self.requests.append(request)
            self.entered += 1
            if self.entered == 2:
                self.both_entered.set()
            await asyncio.wait_for(self.both_entered.wait(), timeout=1)
            if "FAIL_UNIT" in request.user_prompt:
                raise RuntimeError("normalized GE failure")
            try:
                await asyncio.Future()
            finally:
                self.sibling_terminated.set()

        async def aclose(self) -> None:
            self.closed_after_sibling = self.sibling_terminated.is_set()
            self.close_calls += 1

    generation_client = ConcurrentFailureGenerationClient()
    adapter = AsyncOpenAIResponsesEntityClient(
        generation_client=generation_client
    )

    with pytest.raises(RuntimeError, match="normalized GE failure"):
        asyncio.run(
            extract_entities_batch(
                [
                    _evidence("evid_fail", "FAIL_UNIT", 0),
                    _evidence("evid_sibling", "Mirathorn is fortified.", 1),
                ],
                cache_dir=tmp_path / "cache",
                openai_client=adapter,
                allow_heuristic_fallback=False,
                concurrency=2,
            )
        )

    assert generation_client.entered == 2
    assert generation_client.sibling_terminated.is_set()
    assert generation_client.closed_after_sibling is True
    assert generation_client.close_calls == 1


def test_all_cache_hits_do_not_construct_ge_client(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    evidence = [_evidence("evid_cached", "Mirathorn is fortified.", 0)]
    cache_dir = tmp_path / "cache"
    run_entity_extraction(evidence, cache_dir=cache_dir)

    constructions = 0

    def from_env() -> Any:
        nonlocal constructions
        constructions += 1
        raise AssertionError("cache-hit extraction must not construct GE")

    monkeypatch.setattr(
        "src.ingestion.entity_extractor.GenerationClient.from_env",
        classmethod(lambda cls: from_env()),
    )
    adapter = AsyncOpenAIResponsesEntityClient()
    result = asyncio.run(
        extract_entities_batch(
            evidence,
            cache_dir=cache_dir,
            openai_client=adapter,
            allow_heuristic_fallback=False,
        )
    )

    assert result["cache_hits"] == 1
    assert constructions == 0


def test_filters_heading_like_junk_but_keeps_named_entities(tmp_path: Path) -> None:
    class NoisyClient:
        def extract_entities(self, **kwargs: Any) -> dict[str, Any]:
            return {
                "entities": [
                    {
                        "entity_class": "concept",
                        "display_name": "Description",
                        "aliases": [],
                        "is_new": True,
                    },
                    {
                        "entity_class": "place",
                        "display_name": "Lake Mirathorn",
                        "aliases": [],
                        "is_new": True,
                    },
                ]
            }

    out = run_entity_extraction(
        [_evidence("evid_1", "Description: Lake Mirathorn sits beneath Stormspire Peaks.", 0)],
        cache_dir=tmp_path / "cache",
        openai_client=NoisyClient(),
    )
    entities = out["entities"]
    names = {entity["display_name"] for entity in entities}
    assert "Description" not in names
    assert "Lake Mirathorn" in names


def test_run_entity_extraction_closes_async_client(tmp_path: Path) -> None:
    class CloseAwareClient:
        def __init__(self) -> None:
            self.closed = 0

        async def aclose(self) -> None:
            self.closed += 1

        def extract_entities(self, **kwargs: Any) -> dict[str, Any]:
            return {
                "entities": [
                    {
                        "entity_class": "place",
                        "display_name": "Lake Mirathorn",
                        "aliases": [],
                        "is_new": True,
                    }
                ]
            }

    client = CloseAwareClient()
    run_entity_extraction(
        [_evidence("evid_1", "Lake Mirathorn is calm tonight.", 0)],
        cache_dir=tmp_path / "cache",
        openai_client=client,
    )
    assert client.closed == 1


def test_usage_accumulates_across_units(tmp_path: Path) -> None:
    class TokenStubClient:
        def extract_entities(self, **kwargs: Any) -> dict[str, Any]:
            return {
                "entities": [
                    {
                        "entity_class": "place",
                        "display_name": "Alpha Point",
                        "aliases": [],
                        "is_new": True,
                    }
                ],
                "_usage": {
                    "input_tokens": 10,
                    "output_tokens": 3,
                    "cached_tokens": 1,
                },
            }

    units = [
        _evidence("evid_a", "We visited Alpha Point.", 0),
        _evidence("evid_b", "Alpha Point was quiet.", 1),
        _evidence("evid_c", "Leaving Alpha Point.", 2),
    ]
    out = run_entity_extraction(
        units,
        cache_dir=tmp_path / "cache",
        openai_client=TokenStubClient(),
    )
    u = out["usage"]
    assert u["input_tokens"] == 30
    assert u["output_tokens"] == 9
    assert u["cached_tokens"] == 3
    assert u["api_calls"] == 3
