from __future__ import annotations

from pathlib import Path
from typing import Any

import pytest

from src.contracts.schema_validation import validate_many
from src.ingestion.entity_extractor import OpenAIResponsesEntityClient, run_entity_extraction


def _evidence(evidence_id: str, text: str, index: int) -> dict[str, Any]:
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
        "line_span": None,
        "char_span": None,
        "inferred_session": None,
        "speaker_or_subject": None,
        "notes": None,
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
                        "entity_type": "npc",
                        "display_name": "Captain Lysandra Ironveil!",
                        "aliases": ["Lysandra"],
                        "is_new": True,
                    }
                ]
            }
        return {
            "entities": [
                {
                    "entity_type": "faction",
                    "display_name": "Shepherd's Flock",
                    "aliases": ["The Flock"],
                    "is_new": True,
                }
            ]
        }


def test_entity_id_generation_normalizes_display_name(tmp_path: Path) -> None:
    client = _StubExtractorClient()
    entities = run_entity_extraction(
        [_evidence("evid_1", "A hero arrives: Captain Lysandra Ironveil! leads the watch.", 0)],
        cache_dir=tmp_path / "cache",
        openai_client=client,
    )

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
                            "entity_type": "faction",
                            "display_name": "Shepherd's Flock",
                            "aliases": ["The Flock"],
                            "is_new": True,
                        }
                    ]
                }
            return {
                "entities": [
                    {
                        "entity_type": "faction",
                        "display_name": "The Flock",
                        "aliases": ["Shepherd's Flock"],
                        "is_new": True,
                    }
                ]
            }

    entities = run_entity_extraction(
        [
            _evidence("evid_first", "first mention of Shepherd's Flock", 0),
            _evidence("evid_second", "second mention of The Flock", 1),
        ],
        cache_dir=tmp_path / "cache",
        openai_client=OverlapClient(),
    )

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

    assert first == second
    assert client.calls == 1


def test_output_entities_validate_against_schema(tmp_path: Path) -> None:
    entities = run_entity_extraction(
        [_evidence("evid_1", "Mirathorn lies near Lake Mirathorn.", 0)],
        cache_dir=tmp_path / "cache",
    )
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
    class _FakeParsedResponse:
        output_parsed = {
            "entities": [
                {
                    "entity_type": "location",
                    "display_name": "Lake Mirathorn",
                    "aliases": [],
                    "is_new": True,
                }
            ]
        }

    class _FakeResponses:
        def parse(self, **kwargs: Any) -> _FakeParsedResponse:
            assert kwargs["model"] == "gpt-5.3-codex"
            assert kwargs["text_format"] is not None
            return _FakeParsedResponse()

    class _FakeSDKClient:
        responses = _FakeResponses()

    adapter = OpenAIResponsesEntityClient(sdk_client=_FakeSDKClient())
    payload = adapter.extract_entities(
        model="gpt-5.3-codex",
        prompt="extract",
        evidence_unit={},
        known_entities=[],
        prompt_id="test",
    )
    assert payload["entities"][0]["display_name"] == "Lake Mirathorn"


def test_filters_heading_like_junk_but_keeps_named_entities(tmp_path: Path) -> None:
    class NoisyClient:
        def extract_entities(self, **kwargs: Any) -> dict[str, Any]:
            return {
                "entities": [
                    {
                        "entity_type": "other",
                        "display_name": "Description",
                        "aliases": [],
                        "is_new": True,
                    },
                    {
                        "entity_type": "location",
                        "display_name": "Lake Mirathorn",
                        "aliases": [],
                        "is_new": True,
                    },
                ]
            }

    entities = run_entity_extraction(
        [_evidence("evid_1", "Description: Lake Mirathorn sits beneath Stormspire Peaks.", 0)],
        cache_dir=tmp_path / "cache",
        openai_client=NoisyClient(),
    )
    names = {entity["display_name"] for entity in entities}
    assert "Description" not in names
    assert "Lake Mirathorn" in names
