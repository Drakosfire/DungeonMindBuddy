from __future__ import annotations

import asyncio
from pathlib import Path
from typing import Any
from unittest.mock import AsyncMock, MagicMock

import pytest

from src.contracts.schema_validation import validate_instance
from src.ingestion.entity_extractor import (
    _build_recap_system_prompt,
    _build_recap_user_prompt,
    _call_recap_extractor,
    _SESSION_RECAP_PREFIX,
    AsyncOpenAIResponsesEntityClient,
    OpenAIResponsesEntityClient,
    run_entity_extraction,
)
from src.ingestion.recap_models import ClaimRecord, EventRecord, RecapExtractionResult
from src.store import FactStore


class TestEventRecordModel:
    def test_valid_event(self) -> None:
        ev = EventRecord(
            event_name="Battle of the Bridge",
            event_class="combat",
            participants=["Captain Lysandra", "Wolf Pack"],
            location="Stone Bridge",
            outcomes=["Wolf Pack scattered"],
            time_scope="scene",
            certainty="observed",
        )
        assert ev.event_class == "combat"
        assert len(ev.participants) == 2

    def test_minimal_event(self) -> None:
        ev = EventRecord(event_class="discovery", time_scope="session", certainty="inferred")
        assert ev.event_name is None
        assert ev.participants == []
        assert ev.outcomes == []

    def test_invalid_event_class_rejected(self) -> None:
        with pytest.raises(Exception):
            EventRecord(event_class="invalid_class", time_scope="scene", certainty="observed")

    def test_referenced_slugs_default_empty(self) -> None:
        """Backward compat: existing call sites omitting referenced_slugs get an empty list."""
        ev = EventRecord(event_class="discovery", time_scope="scene", certainty="observed")
        assert ev.referenced_slugs == []

    def test_referenced_slugs_populated_roundtrip(self) -> None:
        """The Kirfan-class case: PCs act, an NPC named in the recap header is preserved
        in referenced_slugs[] without polluting participants[]."""
        ev = EventRecord(
            event_class="discovery",
            time_scope="scene",
            certainty="observed",
            participants=["bonogo", "stafl", "baergrom"],
            referenced_slugs=["kirfan"],
        )
        assert ev.participants == ["bonogo", "stafl", "baergrom"]
        assert ev.referenced_slugs == ["kirfan"]
        dumped = ev.model_dump()
        assert dumped["referenced_slugs"] == ["kirfan"]
        assert "kirfan" not in dumped["participants"]


class TestClaimRecordModel:
    def test_valid_claim(self) -> None:
        cl = ClaimRecord(
            subject="Guard Captain",
            predicate="is suspected of",
            object="cult membership",
            claim_type="suspicion",
            speaker_or_source="narrator",
            certainty="medium",
        )
        assert cl.claim_type == "suspicion"

    def test_invalid_claim_type_rejected(self) -> None:
        with pytest.raises(Exception):
            ClaimRecord(
                subject="A",
                predicate="is",
                object="B",
                claim_type="invalid",
                speaker_or_source="narrator",
                certainty="high",
            )


class TestRecapExtractionResult:
    def test_empty_result(self) -> None:
        r = RecapExtractionResult()
        assert r.entities == []
        assert r.event_records == []
        assert r.claims == []

    def test_full_result(self) -> None:
        r = RecapExtractionResult(
            entities=[],
            event_records=[
                EventRecord(event_class="travel", time_scope="session", certainty="observed")
            ],
            claims=[
                ClaimRecord(
                    subject="X",
                    predicate="knows",
                    object="Y",
                    claim_type="fact",
                    speaker_or_source="narrator",
                    certainty="high",
                )
            ],
        )
        assert len(r.event_records) == 1
        assert len(r.claims) == 1


class TestRecapPromptContent:
    def test_recap_prompt_contains_event_instructions(self) -> None:
        unit = {
            "text": "The party fought wolves.",
            "source_class": "observed_session_recap",
            "canon_layer": "campaign",
        }
        system = _build_recap_system_prompt()
        user = _build_recap_user_prompt(unit, [])
        assert "EVENT RECORDS" in system
        assert "CLAIMS" in system
        assert "event_class" in system
        assert "claim_type" in system
        assert _SESSION_RECAP_PREFIX in user


def _recap_evidence(evidence_id: str, text: str, index: int) -> dict[str, Any]:
    return {
        "schema_version": "0.1.0",
        "created_at": "2026-03-27T00:00:00Z",
        "updated_at": "2026-03-27T00:00:00Z",
        "record_status": "active",
        "evidence_id": evidence_id,
        "document_id": "doc_recap",
        "document_type": "session_recap",
        "document_title": "Session 1 Recap",
        "source_class": "observed_session_recap",
        "canon_layer": "campaign",
        "campaign_id": None,
        "text": text,
        "section_path": ["Recap"],
        "paragraph_index": index,
        "source_order_index": index,
        "line_span": None,
        "char_span": None,
        "inferred_session": 1,
        "speaker_or_subject": None,
        "notes": None,
    }


class TestStubRecapClient:
    def test_recap_extractor_collects_events_and_claims(self, tmp_path: Path) -> None:
        class RecapStubClient:
            def extract_entities(self, **kwargs: Any) -> dict[str, Any]:
                return {
                    "entities": [
                        {
                            "entity_class": "actor",
                            "display_name": "Captain Lysandra",
                            "aliases": [],
                            "is_new": True,
                            "decision": "entity",
                        }
                    ],
                    "event_records": [
                        {
                            "event_name": "Bridge Battle",
                            "event_class": "combat",
                            "participants": ["Captain Lysandra"],
                            "location": "Stone Bridge",
                            "outcomes": ["Victory"],
                            "time_scope": "scene",
                            "certainty": "observed",
                        }
                    ],
                    "claims": [
                        {
                            "subject": "Captain Lysandra",
                            "predicate": "suspects",
                            "object": "cult involvement",
                            "claim_type": "suspicion",
                            "speaker_or_source": "narrator",
                            "certainty": "medium",
                        }
                    ],
                }

        recap_artifacts: dict[str, list[dict[str, Any]]] = {}
        entity_out = run_entity_extraction(
            [_recap_evidence("evid_recap_1", "Captain Lysandra fought at the Stone Bridge.", 0)],
            cache_dir=tmp_path / "cache",
            openai_client=RecapStubClient(),
            recap_artifacts=recap_artifacts,
        )
        entities = entity_out["entities"]
        assert len(entities) == 1
        assert entities[0]["display_name"] == "Captain Lysandra"
        assert len(recap_artifacts.get("event_records", [])) == 1
        assert recap_artifacts["event_records"][0]["event_class"] == "combat"
        assert recap_artifacts["event_records"][0]["evidence_id"] == "evid_recap_1"
        assert len(recap_artifacts.get("claims", [])) == 1
        assert recap_artifacts["claims"][0]["claim_type"] == "suspicion"

    def test_worldbuilding_unit_does_not_produce_recap_artifacts(self, tmp_path: Path) -> None:
        class WorldStubClient:
            def extract_entities(self, **kwargs: Any) -> dict[str, Any]:
                return {
                    "entities": [
                        {
                            "entity_class": "place",
                            "display_name": "Mirathorn",
                            "aliases": [],
                            "is_new": True,
                        }
                    ]
                }

        wb_evidence = {
            "schema_version": "0.1.0",
            "created_at": "2026-03-27T00:00:00Z",
            "updated_at": "2026-03-27T00:00:00Z",
            "record_status": "active",
            "evidence_id": "evid_wb",
            "document_id": "doc_wb",
            "document_type": "world_reference",
            "document_title": "City of Mirathorn",
            "source_class": "seed_reference",
            "canon_layer": "world",
            "campaign_id": None,
            "text": "Mirathorn is a fortified city.",
            "section_path": ["World"],
            "paragraph_index": 0,
            "source_order_index": 0,
            "line_span": None,
            "char_span": None,
            "inferred_session": None,
            "speaker_or_subject": None,
            "notes": None,
        }
        recap_artifacts: dict[str, list[dict[str, Any]]] = {}
        entity_out = run_entity_extraction(
            [wb_evidence],
            cache_dir=tmp_path / "cache",
            openai_client=WorldStubClient(),
            recap_artifacts=recap_artifacts,
        )
        entities = entity_out["entities"]
        assert len(entities) == 1
        assert recap_artifacts.get("event_records", []) == []
        assert recap_artifacts.get("claims", []) == []


class TestExtractRecapOpenAIClient:
    def test_sync_extract_recap_uses_recap_schema(self) -> None:
        """Verify sync client passes RecapExtractionResult as text_format to the SDK."""
        mock_response = MagicMock()
        mock_response.output_parsed = RecapExtractionResult(
            entities=[],
            event_records=[
                EventRecord(event_class="combat", time_scope="scene", certainty="observed")
            ],
            claims=[],
        )
        mock_response.usage = MagicMock(input_tokens=100, output_tokens=50)

        mock_sdk = MagicMock()
        mock_sdk.responses.parse.return_value = mock_response

        client = OpenAIResponsesEntityClient(sdk_client=mock_sdk)
        result = client.extract_recap(
            model="test",
            system_prompt="test",
            user_prompt="test",
            evidence_unit={},
            known_entities=[],
            prompt_id="recap_extraction_v2_prompt_cache",
        )
        call_kwargs = mock_sdk.responses.parse.call_args[1]
        assert call_kwargs["text_format"] is RecapExtractionResult
        assert len(result.get("event_records", [])) == 1
        assert result["_usage"]["input_tokens"] == 100

    def test_async_extract_recap_uses_recap_schema(self) -> None:
        mock_response = MagicMock()
        mock_response.output_parsed = RecapExtractionResult(
            entities=[],
            event_records=[],
            claims=[
                ClaimRecord(
                    subject="A",
                    predicate="b",
                    object="C",
                    claim_type="fact",
                    speaker_or_source="narrator",
                    certainty="high",
                )
            ],
        )
        mock_response.usage = MagicMock(input_tokens=10, output_tokens=20)

        mock_sdk = MagicMock()
        mock_sdk.responses.parse = AsyncMock(return_value=mock_response)

        async def _run() -> None:
            client = AsyncOpenAIResponsesEntityClient(sdk_client=mock_sdk)
            out = await client.extract_recap(
                model="test",
                system_prompt="test",
                user_prompt="test",
                evidence_unit={},
                known_entities=[],
                prompt_id="recap_extraction_v2_prompt_cache",
            )
            assert len(out.get("claims", [])) == 1

        asyncio.run(_run())
        call_kwargs = mock_sdk.responses.parse.call_args[1]
        assert call_kwargs["text_format"] is RecapExtractionResult

    def test_call_recap_extractor_preserves_events_and_claims(self) -> None:
        mock_response = MagicMock()
        mock_response.output_parsed = RecapExtractionResult(
            entities=[],
            event_records=[
                EventRecord(
                    event_name="Bridge Battle",
                    event_class="combat",
                    time_scope="scene",
                    certainty="observed",
                )
            ],
            claims=[
                ClaimRecord(
                    subject="X",
                    predicate="knows",
                    object="Y",
                    claim_type="fact",
                    speaker_or_source="narrator",
                    certainty="high",
                )
            ],
        )
        mock_response.usage = MagicMock(input_tokens=1, output_tokens=2)
        mock_sdk = MagicMock()
        mock_sdk.responses.parse.return_value = mock_response
        client = OpenAIResponsesEntityClient(sdk_client=mock_sdk)

        unit = {
            "text": "The party fought at the bridge.",
            "source_class": "observed_session_recap",
            "canon_layer": "campaign",
        }

        async def _run() -> tuple[RecapExtractionResult, dict[str, int]]:
            return await _call_recap_extractor(
                unit,
                [],
                "test-model",
                client,
                allow_heuristic_fallback=False,
                system_prompt=_build_recap_system_prompt(),
            )

        parsed, usage = asyncio.run(_run())
        assert len(parsed.event_records) == 1
        assert parsed.event_records[0].event_class == "combat"
        assert len(parsed.claims) == 1
        assert parsed.claims[0].claim_type == "fact"
        assert usage["input_tokens"] == 1
        recap_call = mock_sdk.responses.parse.call_args[1]
        assert recap_call["text_format"] is RecapExtractionResult


class TestEventRecordSchemaValidation:
    def test_valid_event_record_passes_schema(self) -> None:
        record = {
            "event_name": "Ambush",
            "event_class": "combat",
            "participants": ["Guard"],
            "location": "Forest Road",
            "outcomes": ["Guard defeated"],
            "time_scope": "scene",
            "certainty": "observed",
            "evidence_id": "evid_1",
        }
        validate_instance(record, "event_record.schema.json")

    def test_minimal_event_record_passes_schema(self) -> None:
        record = {
            "event_name": None,
            "event_class": "discovery",
            "time_scope": "session",
            "certainty": "inferred",
        }
        validate_instance(record, "event_record.schema.json")


class TestClaimSchemaValidation:
    def test_valid_claim_passes_schema(self) -> None:
        record = {
            "subject": "Guard Captain",
            "predicate": "is member of",
            "object": "Shadow Cult",
            "claim_type": "suspicion",
            "speaker_or_source": "narrator",
            "certainty": "medium",
            "evidence_id": "evid_1",
        }
        validate_instance(record, "claim.schema.json")


class TestFactStoreEventRecordsAndClaims:
    def test_add_event_records_persists(self, tmp_path: Path) -> None:
        store = FactStore(tmp_path / "store")
        records = [
            {
                "event_name": "Bridge Battle",
                "event_class": "combat",
                "participants": ["Captain Lysandra"],
                "location": "Stone Bridge",
                "outcomes": ["Victory"],
                "time_scope": "scene",
                "certainty": "observed",
                "evidence_id": "evid_1",
            }
        ]
        store.add_event_records(records)
        assert len(store.event_records) == 1
        store.save()

        store2 = FactStore(tmp_path / "store")
        store2.load()
        assert len(store2.event_records) == 1
        assert store2.event_records[0]["event_class"] == "combat"

    def test_add_claims_persists(self, tmp_path: Path) -> None:
        store = FactStore(tmp_path / "store")
        claims = [
            {
                "subject": "Guard Captain",
                "predicate": "is suspected of",
                "object": "cult membership",
                "claim_type": "suspicion",
                "speaker_or_source": "narrator",
                "certainty": "medium",
                "evidence_id": "evid_1",
            }
        ]
        store.add_claims(claims)
        assert len(store.claims) == 1
        store.save()

        store2 = FactStore(tmp_path / "store")
        store2.load()
        assert len(store2.claims) == 1
        assert store2.claims[0]["claim_type"] == "suspicion"
