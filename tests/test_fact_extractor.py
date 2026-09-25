from __future__ import annotations

import asyncio
import json
from pathlib import Path
from typing import Any

import blake3
import pytest
from generationengine import InferenceObservation, ObservationState, TextRequest, TextResult

from src.contracts.schema_validation import validate_many
from src.ingestion.fact_extractor import (
    AsyncOpenAIResponsesFactClient,
    BatchedFactExtractionResult,
    FactExtractionResult,
    OpenAIResponsesFactClient,
    apply_fact_batch_outputs_to_cache,
    derive_truth_state,
    extract_facts_batch,
    prepare_fact_batch_requests,
    prepare_fact_batch_requests_chunked,
    run_fact_extraction,
)


def _evidence(
    evidence_id: str,
    text: str,
    index: int,
    inferred_session: int | None = None,
    document_session: int | None = None,
) -> dict[str, Any]:
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
        "inferred_session": inferred_session,
        "document_session": document_session,
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


def _entity(entity_id: str, display_name: str, entity_type: str = "location") -> dict[str, Any]:
    entity_class = (
        "actor"
        if entity_type == "npc"
        else "place"
        if entity_type == "location"
        else "group"
        if entity_type == "faction"
        else "object"
        if entity_type == "item"
        else "concept"
    )
    return {
        "schema_version": "0.1.0",
        "created_at": "2026-03-27T00:00:00Z",
        "updated_at": "2026-03-27T00:00:00Z",
        "record_status": "active",
        "entity_id": entity_id,
        "entity_class": entity_class,
        "entity_type": entity_type,
        "entity_kind": entity_class,
        "decision": "entity",
        "exclude_reason": None,
        "display_name": display_name,
        "canonical_name": None,
        "aliases": [display_name],
        "entity_status": "provisional",
        "merged_into_entity_id": None,
        "source_mention_ids": ["men_test_0"],
        "review_state": "unreviewed",
        "entity_tags": [],
        "subtype_facets": [],
        "narrative_tags": [],
        "document_tags": [],
        "notes": None,
    }


def _extra_entity(entity_id: str, display_name: str, entity_type: str = "npc") -> dict[str, Any]:
    return _entity(entity_id=entity_id, display_name=display_name, entity_type=entity_type)


class _StubFactClient:
    def __init__(self) -> None:
        self.calls = 0

    def extract_facts(self, **kwargs: Any) -> dict[str, Any]:
        self.calls += 1
        text = str(kwargs["evidence_unit"]["text"]).lower()
        if "geography" in text:
            return {
                "facts": [
                    {
                        "fact_id": "fact_mirathorn_geography_001",
                        "subject_entity_id": "ent_mirathorn",
                        "attribute": "geography",
                        "value": {
                            "kind": "scalar",
                            "label": "Located at the base of the Stormspire Peaks",
                            "normalized": "stormspire_peaks_base",
                        },
                    }
                ]
            }
        if "economy" in text:
            return {
                "facts": [
                    {
                        "fact_id": "fact_mirathorn_economy_001",
                        "subject_entity_id": "ent_mirathorn",
                        "attribute": "economy",
                        "value": {
                            "kind": "set",
                            "label": "Major industries include brewing and fishing",
                            "normalized": "brewing:fishing",
                            "values": ["brewing", "fishing"],
                        },
                    }
                ]
            }
        if "atmosphere" in text:
            return {
                "facts": [
                    {
                        "fact_id": "fact_mirathorn_atmosphere_001",
                        "subject_entity_id": "ent_mirathorn",
                        "attribute": "atmosphere",
                        "value": {
                            "kind": "interpretive",
                            "label": "Vibrant and bustling marketplace with diverse crowds",
                            "normalized": None,
                            "interpretation_level": "direct_assertion",
                            "strength": "strong",
                        },
                    }
                ]
            }
        return {"facts": []}


ENTITIES = [
    _entity("ent_mirathorn", "Mirathorn"),
    _entity("ent_shepherds_flock", "Shepherd's Flock", "faction"),
]


def test_output_facts_validate_against_schema(tmp_path: Path) -> None:
    facts = run_fact_extraction(
        [_evidence("evid_1", "Geography: near Stormspire Peaks.", 0)],
        entities=ENTITIES,
        canon_layer="world",
        campaign_id=None,
        source_class="seed_reference",
        cache_dir=tmp_path / "cache",
        openai_client=_StubFactClient(),
    )["facts"]
    assert facts
    validate_many(facts, "fact.schema.json")


def test_batch_size_combines_uncached_units_into_one_batched_fact_call(tmp_path: Path) -> None:
    class _BatchedFactAsyncClient:
        def __init__(self) -> None:
            self.batched_calls = 0

        async def extract_facts_batched(self, **kwargs: Any) -> dict[str, Any]:
            self.batched_calls += 1
            return {
                "results": [
                    {
                        "unit_index": 0,
                        "facts": [
                            {
                                "fact_id": "fact_mirathorn_geo_001",
                                "subject_entity_id": "ent_mirathorn",
                                "attribute": "geography",
                                "value": {
                                    "kind": "scalar",
                                    "label": "Near peaks",
                                    "normalized": "near_peaks",
                                },
                            }
                        ],
                    },
                    {
                        "unit_index": 1,
                        "facts": [
                            {
                                "fact_id": "fact_mirathorn_econ_001",
                                "subject_entity_id": "ent_mirathorn",
                                "attribute": "economy",
                                "value": {
                                    "kind": "scalar",
                                    "label": "Brewing trade",
                                    "normalized": "brewing",
                                },
                            }
                        ],
                    },
                ],
                "_usage": {"input_tokens": 8, "output_tokens": 4, "cached_tokens": 0},
            }

        async def extract_facts(self, **kwargs: Any) -> dict[str, Any]:
            raise AssertionError("extract_facts should not run when batch_size > 1")

        async def aclose(self) -> None:
            return None

    client = _BatchedFactAsyncClient()
    out = asyncio.run(
        extract_facts_batch(
            [
                _evidence("evid_geo", "Mirathorn geography: near Stormspire Peaks.", 0),
                _evidence("evid_econ", "Mirathorn economy: brewing is central.", 1),
            ],
            entities=ENTITIES,
            canon_layer="world",
            campaign_id=None,
            source_class="seed_reference",
            cache_dir=tmp_path / "cache",
            openai_client=client,
            allow_heuristic_fallback=False,
            batch_size=2,
            concurrency=4,
        )
    )
    assert client.batched_calls == 1
    assert out["usage"]["api_calls"] == 1
    assert len(out["facts"]) >= 1


def test_truth_state_mapping_world_seed() -> None:
    ts, sa = derive_truth_state("world", "seed_reference")
    assert ts == "CANON"
    assert sa == "seed_prep"


def test_truth_state_mapping_campaign_planning() -> None:
    ts, sa = derive_truth_state("campaign", "planning_document")
    assert ts == "PREP"
    assert sa == "planning_prep"


def test_truth_state_mapping_campaign_observed() -> None:
    ts, sa = derive_truth_state("campaign", "observed_session_recap")
    assert ts == "OBSERVED"
    assert sa == "observed_recap"


def test_truth_state_mapping_campaign_ledger() -> None:
    ts, sa = derive_truth_state("campaign", "ledger_or_dossier")
    assert ts == "OBSERVED"
    assert sa == "observed_recap"


def test_truth_state_mapping_unknown_defaults() -> None:
    ts, sa = derive_truth_state("world", "unknown_class")
    assert ts == "CANON"
    assert sa == "unknown"


def test_cache_hit_skips_second_client_call(tmp_path: Path) -> None:
    client = _StubFactClient()
    evidence = [_evidence("evid_1", "Geography: near Stormspire Peaks.", 0)]
    cache_dir = tmp_path / "cache"

    first = run_fact_extraction(
        evidence,
        entities=ENTITIES,
        canon_layer="world",
        campaign_id=None,
        source_class="seed_reference",
        cache_dir=cache_dir,
        openai_client=client,
    )
    second = run_fact_extraction(
        evidence,
        entities=ENTITIES,
        canon_layer="world",
        campaign_id=None,
        source_class="seed_reference",
        cache_dir=cache_dir,
        openai_client=client,
    )

    assert first["facts"] == second["facts"]
    assert first["usage"]["api_calls"] == 1
    assert second["usage"]["api_calls"] == 0
    assert second["cache_hits"] == 1
    assert client.calls == 1


def test_run_fact_extraction_closes_async_client(tmp_path: Path) -> None:
    class CloseAwareFactClient:
        def __init__(self) -> None:
            self.closed = 0

        async def aclose(self) -> None:
            self.closed += 1

        def extract_facts(self, **kwargs: Any) -> dict[str, Any]:
            return {
                "facts": [
                    {
                        "fact_id": "fact_mirathorn_geography_001",
                        "subject_entity_id": "ent_mirathorn",
                        "attribute": "geography",
                        "value": {
                            "kind": "scalar",
                            "label": "Near Stormspire Peaks",
                            "normalized": "near_stormspire_peaks",
                        },
                    }
                ]
            }

    client = CloseAwareFactClient()
    run_fact_extraction(
        [_evidence("evid_1", "Geography: near Stormspire Peaks.", 0)],
        entities=ENTITIES,
        canon_layer="world",
        campaign_id=None,
        source_class="seed_reference",
        cache_dir=tmp_path / "cache",
        openai_client=client,
    )
    assert client.closed == 1


def test_orphan_subject_entity_id_filtered(tmp_path: Path) -> None:
    class OrphanClient:
        def extract_facts(self, **kwargs: Any) -> dict[str, Any]:
            return {
                "facts": [
                    {
                        "fact_id": "fact_nonexistent_role",
                        "subject_entity_id": "ent_does_not_exist",
                        "attribute": "role",
                        "value": {
                            "kind": "scalar",
                            "label": "Some role",
                            "normalized": "some_role",
                        },
                    },
                    {
                        "fact_id": "fact_mirathorn_history",
                        "subject_entity_id": "ent_mirathorn",
                        "attribute": "history",
                        "value": {
                            "kind": "scalar",
                            "label": "Founded 200 years ago by settlers",
                            "normalized": "founded_200y",
                        },
                    },
                ]
            }

    facts = run_fact_extraction(
        [_evidence("evid_1", "History text here.", 0)],
        entities=ENTITIES,
        canon_layer="world",
        campaign_id=None,
        source_class="seed_reference",
        cache_dir=tmp_path / "cache",
        openai_client=OrphanClient(),
    )["facts"]

    subject_ids = {f["subject_entity_id"] for f in facts}
    assert "ent_does_not_exist" not in subject_ids
    assert "ent_mirathorn" in subject_ids


def test_generic_place_subject_remaps_to_named_place(tmp_path: Path) -> None:
    class GenericPlaceClient:
        def extract_facts(self, **kwargs: Any) -> dict[str, Any]:
            return {
                "facts": [
                    {
                        "fact_id": "fact_city_economy",
                        "subject_entity_id": "ent_the_city",
                        "attribute": "economy",
                        "value": {
                            "kind": "scalar",
                            "label": "Major industries include brewing and fishing",
                            "normalized": "brewing_fishing",
                        },
                    }
                ]
            }

    entities = [
        _entity("ent_mirathorn", "Mirathorn"),
        _entity("ent_the_city", "the city"),
    ]
    facts = run_fact_extraction(
        [_evidence("evid_1", "Mirathorn is a strategic trade hub city.", 0)],
        entities=entities,
        canon_layer="world",
        campaign_id=None,
        source_class="seed_reference",
        cache_dir=tmp_path / "cache",
        openai_client=GenericPlaceClient(),
    )["facts"]

    assert len(facts) == 1
    assert facts[0]["subject_entity_id"] == "ent_mirathorn"


def test_group_variant_subject_remaps_to_parent_group(tmp_path: Path) -> None:
    class GroupVariantClient:
        def extract_facts(self, **kwargs: Any) -> dict[str, Any]:
            return {
                "facts": [
                    {
                        "fact_id": "fact_flock_cultists_goal",
                        "subject_entity_id": "ent_shepherds_flock_cultists",
                        "attribute": "goals",
                        "value": {
                            "kind": "scalar",
                            "label": "They protest the toll as unfair and exclusionary",
                            "normalized": "protest_toll_unfair_exclusionary",
                        },
                    }
                ]
            }

    entities = [
        _entity("ent_shepherds_flock", "Shepherd's Flock", "faction"),
        _entity("ent_shepherds_flock_cultists", "Shepherd's Flock cultists", "faction"),
    ]
    facts = run_fact_extraction(
        [_evidence("evid_1", "The Shepherd's Flock cultists protest at the gate.", 0)],
        entities=entities,
        canon_layer="world",
        campaign_id=None,
        source_class="seed_reference",
        cache_dir=tmp_path / "cache",
        openai_client=GroupVariantClient(),
    )["facts"]

    assert len(facts) == 1
    assert facts[0]["subject_entity_id"] == "ent_shepherds_flock"


def test_group_operational_status_not_remapped_to_place(tmp_path: Path) -> None:
    class GroupStatusClient:
        def extract_facts(self, **kwargs: Any) -> dict[str, Any]:
            return {
                "facts": [
                    {
                        "fact_id": "fact_flock_status",
                        "subject_entity_id": "ent_shepherds_flock",
                        "attribute": "operational_status",
                        "value": {
                            "kind": "scalar",
                            "label": "The flock protests the toll at the gate",
                            "normalized": "flock_protests_toll",
                        },
                    }
                ]
            }

    entities = [
        _entity("ent_mirathorn", "Mirathorn"),
        _entity("ent_shepherds_flock", "Shepherd's Flock", "faction"),
    ]
    facts = run_fact_extraction(
        [_evidence("evid_1", "Mirathorn gates are crowded during the festival.", 0)],
        entities=entities,
        canon_layer="world",
        campaign_id=None,
        source_class="seed_reference",
        cache_dir=tmp_path / "cache",
        openai_client=GroupStatusClient(),
    )["facts"]

    assert len(facts) == 1
    assert facts[0]["subject_entity_id"] == "ent_shepherds_flock"


def test_generic_place_without_local_mention_uses_dominant_place(tmp_path: Path) -> None:
    class GenericHubClient:
        def extract_facts(self, **kwargs: Any) -> dict[str, Any]:
            return {
                "facts": [
                    {
                        "fact_id": "fact_hub_economy",
                        "subject_entity_id": "ent_strategic_trade_hub",
                        "attribute": "economy",
                        "value": {
                            "kind": "scalar",
                            "label": "Major industries include brewing and fishing",
                            "normalized": "brewing_fishing",
                        },
                    }
                ]
            }

    dominant_place = _entity("ent_mirathorn", "Mirathorn")
    dominant_place["source_mention_ids"] = ["men_1", "men_2", "men_3"]
    secondary_place = _entity("ent_strategic_trade_hub", "Strategic Trade Hub")
    secondary_place["source_mention_ids"] = ["men_4"]
    facts = run_fact_extraction(
        [_evidence("evid_1", "Major industries include brewing and fishing.", 0)],
        entities=[dominant_place, secondary_place],
        canon_layer="world",
        campaign_id=None,
        source_class="seed_reference",
        cache_dir=tmp_path / "cache",
        openai_client=GenericHubClient(),
    )["facts"]

    assert len(facts) == 1
    assert facts[0]["subject_entity_id"] == "ent_mirathorn"


def test_duplicate_suppression_merges_evidence_ids(tmp_path: Path) -> None:
    class DupClient:
        def extract_facts(self, **kwargs: Any) -> dict[str, Any]:
            return {
                "facts": [
                    {
                        "fact_id": "fact_mirathorn_geography_001",
                        "subject_entity_id": "ent_mirathorn",
                        "attribute": "geography",
                        "value": {
                            "kind": "scalar",
                            "label": "Near the Stormspire Peaks",
                            "normalized": "stormspire_peaks",
                        },
                    }
                ]
            }

    facts = run_fact_extraction(
        [
            _evidence("evid_1", "Geography mention one.", 0),
            _evidence("evid_2", "Geography mention two.", 1),
        ],
        entities=ENTITIES,
        canon_layer="world",
        campaign_id=None,
        source_class="seed_reference",
        cache_dir=tmp_path / "cache",
        openai_client=DupClient(),
    )["facts"]

    geo_facts = [f for f in facts if f["attribute"] == "geography"]
    assert len(geo_facts) == 1
    assert "evid_1" in geo_facts[0]["evidence_ids"]
    assert "evid_2" in geo_facts[0]["evidence_ids"]


def test_deterministic_fact_id_from_content(tmp_path: Path) -> None:
    client = _StubFactClient()
    facts = run_fact_extraction(
        [_evidence("evid_1", "Geography: near Stormspire Peaks.", 0)],
        entities=ENTITIES,
        canon_layer="world",
        campaign_id=None,
        source_class="seed_reference",
        cache_dir=tmp_path / "cache",
        openai_client=client,
    )["facts"]

    assert len(facts) == 1
    fid = facts[0]["fact_id"]
    assert fid.startswith("fact_mirathorn_geography_")
    assert len(fid) > len("fact_mirathorn_geography_")


def test_disallow_heuristic_fallback_requires_client(tmp_path: Path) -> None:
    with pytest.raises(ValueError, match="Heuristic fallback is disabled"):
        run_fact_extraction(
            [_evidence("evid_1", "Some text.", 0)],
            entities=ENTITIES,
            canon_layer="world",
            campaign_id=None,
            source_class="seed_reference",
            cache_dir=tmp_path / "cache",
            allow_heuristic_fallback=False,
        )


def test_set_value_kind_produces_valid_schema(tmp_path: Path) -> None:
    facts = run_fact_extraction(
        [_evidence("evid_1", "Economy: brewing and fishing.", 0)],
        entities=ENTITIES,
        canon_layer="world",
        campaign_id=None,
        source_class="seed_reference",
        cache_dir=tmp_path / "cache",
        openai_client=_StubFactClient(),
    )["facts"]
    assert facts
    eco_facts = [f for f in facts if f["attribute"] == "economy"]
    assert eco_facts
    assert eco_facts[0]["value"]["kind"] == "set"
    assert "brewing" in eco_facts[0]["value"]["values"]
    validate_many(facts, "fact.schema.json")


def test_interpretive_value_includes_required_fields(tmp_path: Path) -> None:
    facts = run_fact_extraction(
        [_evidence("evid_1", "Atmosphere: vibrant and bustling.", 0)],
        entities=ENTITIES,
        canon_layer="world",
        campaign_id=None,
        source_class="seed_reference",
        cache_dir=tmp_path / "cache",
        openai_client=_StubFactClient(),
    )["facts"]
    assert facts
    atmo_facts = [f for f in facts if f["attribute"] == "atmosphere"]
    assert atmo_facts
    value = atmo_facts[0]["value"]
    assert value["kind"] == "interpretive"
    assert value["interpretation_level"] in {
        "direct_assertion",
        "derived_summary",
        "interpretive_inference",
    }
    assert value["strength"] in {"weak", "moderate", "strong"}
    validate_many(facts, "fact.schema.json")


def test_event_taxonomy_attributes_validate_against_schema(tmp_path: Path) -> None:
    class EventAttrClient:
        def extract_facts(self, **kwargs: Any) -> dict[str, Any]:
            return {
                "facts": [
                    {
                        "fact_id": "fact_mirathorn_event_outcome_001",
                        "subject_entity_id": "ent_mirathorn",
                        "attribute": "event_outcome",
                        "value": {
                            "kind": "state",
                            "label": "Council strike fails to stop cult timeline",
                            "normalized": "strike_fails_stop_cult_timeline",
                        },
                    },
                    {
                        "fact_id": "fact_mirathorn_event_progression_001",
                        "subject_entity_id": "ent_mirathorn",
                        "attribute": "event_progression",
                        "value": {
                            "kind": "scalar",
                            "label": "Deliberation rounds advance the summoning countdown",
                            "normalized": "deliberation_advances_countdown",
                        },
                    },
                ]
            }

    facts = run_fact_extraction(
        [_evidence("evid_1", "Event timeline text.", 0)],
        entities=ENTITIES,
        canon_layer="campaign",
        campaign_id="longmont-c1",
        source_class="observed_session_recap",
        cache_dir=tmp_path / "cache",
        openai_client=EventAttrClient(),
    )["facts"]
    assert facts
    attrs = {fact["attribute"] for fact in facts}
    assert "event_outcome" in attrs
    assert "event_progression" in attrs
    validate_many(facts, "fact.schema.json")


def _fact_parsed_payload() -> dict[str, Any]:
    return {
        "facts": [
            {
                "fact_id": "fact_test",
                "subject_entity_id": "ent_mirathorn",
                "attribute": "history",
                "value": {
                    "kind": "scalar",
                    "label": "An ancient city",
                    "normalized": "ancient_city",
                },
            }
        ]
    }


def _ge_result(
    parsed: dict[str, Any],
    *,
    input_tokens: int | None = 55,
    output_tokens: int | None = 12,
    cached_tokens: int | None = 4,
    provider_attempt_count: int = 2,
) -> TextResult:
    return TextResult(
        text=json.dumps(parsed),
        parsed=parsed,
        observation=InferenceObservation(
            input_tokens=input_tokens,
            output_tokens=output_tokens,
            cached_input_tokens=cached_tokens,
            provider_attempt_count=provider_attempt_count,
            latency_ms=1,
            retry_count=provider_attempt_count - 1,
            state=ObservationState.COMPLETED,
        ),
    )


class _RecordingGenerationClient:
    def __init__(self, results: list[TextResult] | None = None) -> None:
        self.results = list(results or [_ge_result(_fact_parsed_payload())])
        self.requests: list[TextRequest] = []
        self.close_calls = 0

    async def generate_structured(self, request: TextRequest) -> TextResult:
        self.requests.append(request)
        return self.results.pop(0)

    async def aclose(self) -> None:
        self.close_calls += 1


def test_sync_fact_adapter_uses_exact_ge_request_and_maps_usage() -> None:
    created: list[_RecordingGenerationClient] = []

    def factory() -> _RecordingGenerationClient:
        client = _RecordingGenerationClient()
        created.append(client)
        return client

    adapter = OpenAIResponsesFactClient(generation_client_factory=factory)
    payload = adapter.extract_facts(
        model="test-model",
        system_prompt="system instructions",
        user_prompt="extract",
        evidence_unit={},
        entities=[],
        prompt_id="test",
    )

    assert payload["facts"][0]["value"]["label"] == "An ancient city"
    assert payload["_usage"] == {
        "input_tokens": 55,
        "output_tokens": 12,
        "cached_tokens": 4,
        "api_calls": 2,
    }
    assert len(created) == 1
    assert created[0].close_calls == 1
    request = created[0].requests[0]
    assert request.system_prompt == "system instructions"
    assert request.user_prompt == "extract"
    assert request.provider == "openai"
    assert request.model == "test-model"
    assert request.profile is None
    assert request.temperature is None
    assert request.json_object is False
    assert request.max_output_tokens is None
    assert request.schema_name == "fact_extraction"
    assert request.json_schema == FactExtractionResult.model_json_schema()


def test_sync_fact_adapter_constructs_and_closes_one_ge_client_per_bridge_call() -> None:
    created: list[_RecordingGenerationClient] = []

    def factory() -> _RecordingGenerationClient:
        client = _RecordingGenerationClient()
        created.append(client)
        return client

    adapter = OpenAIResponsesFactClient(generation_client_factory=factory)
    for _ in range(2):
        adapter.extract_facts(
            model="test-model",
            system_prompt="system",
            user_prompt="user",
            evidence_unit={},
            entities=[],
            prompt_id="test",
        )

    assert len(created) == 2
    assert created[0] is not created[1]
    assert [client.close_calls for client in created] == [1, 1]


def test_async_batched_adapter_uses_exact_ge_request_and_revalidates_payload() -> None:
    parsed = {
        "results": [
            {
                "facts": [*_fact_parsed_payload()["facts"]],
                "unit_index": 0,
            }
        ]
    }
    client = _RecordingGenerationClient([_ge_result(parsed)])
    adapter = AsyncOpenAIResponsesFactClient(generation_client=client)
    payload = asyncio.run(
        adapter.extract_facts_batched(
            model="alternate-model",
            system_prompt="batch system",
            user_prompt="batch user",
            prompt_id="test",
        )
    )

    assert payload["results"][0]["unit_index"] == 0
    request = client.requests[0]
    assert request.system_prompt == "batch system"
    assert request.user_prompt == "batch user"
    assert request.provider == "openai"
    assert request.model == "alternate-model"
    assert request.profile is None
    assert request.temperature is None
    assert request.json_object is False
    assert request.max_output_tokens is None
    assert request.schema_name == "batched_fact_extraction"
    assert request.json_schema == BatchedFactExtractionResult.model_json_schema()


def test_fact_adapter_revalidates_ge_parsed_payload() -> None:
    client = _RecordingGenerationClient([_ge_result({"facts": [{"invalid": True}]})])
    adapter = AsyncOpenAIResponsesFactClient(generation_client=client)

    with pytest.raises(ValueError):
        asyncio.run(
            adapter.extract_facts(
                model="test-model",
                system_prompt="system instructions",
                user_prompt="extract",
                evidence_unit={},
                entities=[],
                prompt_id="test",
            )
        )


def test_async_adapter_reuses_one_ge_client_concurrently_and_closes_once(
    tmp_path: Path,
) -> None:
    class ConcurrentGenerationClient(_RecordingGenerationClient):
        def __init__(self) -> None:
            super().__init__([])
            self.entered = 0
            self.overlap = asyncio.Event()

        async def generate_structured(self, request: TextRequest) -> TextResult:
            self.requests.append(request)
            self.entered += 1
            if self.entered == 2:
                self.overlap.set()
            await asyncio.wait_for(self.overlap.wait(), timeout=1)
            return _ge_result(
                _fact_parsed_payload(),
                input_tokens=3,
                output_tokens=2,
                cached_tokens=1,
                provider_attempt_count=2,
            )

    client = ConcurrentGenerationClient()
    adapter = AsyncOpenAIResponsesFactClient(generation_client=client)
    result = asyncio.run(
        extract_facts_batch(
            [
                _evidence("evid_a", "Geography: first peaks.", 0),
                _evidence("evid_b", "Geography: second peaks.", 1),
            ],
            entities=ENTITIES,
            canon_layer="world",
            campaign_id=None,
            source_class="seed_reference",
            cache_dir=tmp_path / "cache",
            openai_client=adapter,
            allow_heuristic_fallback=False,
            concurrency=2,
        )
    )

    assert client.entered == 2
    assert client.overlap.is_set()
    assert client.close_calls == 1
    assert len(client.requests) == 2
    assert {request.model for request in client.requests} == {"gpt-5.3-codex"}
    assert result["usage"] == {
        "input_tokens": 6,
        "output_tokens": 4,
        "cached_tokens": 2,
        "api_calls": 4,
    }


def test_async_adapter_constructs_production_ge_inside_active_loop_once(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    created: list[_RecordingGenerationClient] = []
    construction_loops: list[asyncio.AbstractEventLoop] = []

    def from_env() -> _RecordingGenerationClient:
        construction_loops.append(asyncio.get_running_loop())
        client = _RecordingGenerationClient()
        created.append(client)
        return client

    monkeypatch.setattr(
        "src.ingestion.fact_extractor.GenerationClient.from_env",
        classmethod(lambda cls: from_env()),
    )
    adapter = AsyncOpenAIResponsesFactClient()

    result = run_fact_extraction(
        [_evidence("evid_a", "Geography: peaks.", 0)],
        entities=ENTITIES,
        canon_layer="world",
        campaign_id=None,
        source_class="seed_reference",
        cache_dir=tmp_path / "cache",
        openai_client=adapter,
        allow_heuristic_fallback=False,
    )

    assert result["facts"]
    assert len(created) == 1
    assert len(construction_loops) == 1
    assert created[0].close_calls == 1


def test_unknown_ge_usage_zero_fills_tokens_but_preserves_attempt_count(
    tmp_path: Path,
) -> None:
    client = _RecordingGenerationClient(
        [
            _ge_result(
                _fact_parsed_payload(),
                input_tokens=None,
                output_tokens=None,
                cached_tokens=None,
                provider_attempt_count=2,
            )
        ]
    )
    adapter = AsyncOpenAIResponsesFactClient(generation_client=client)

    result = run_fact_extraction(
        [_evidence("evid_a", "Geography: peaks.", 0)],
        entities=ENTITIES,
        canon_layer="world",
        campaign_id=None,
        source_class="seed_reference",
        cache_dir=tmp_path / "cache",
        openai_client=adapter,
        allow_heuristic_fallback=False,
    )

    assert result["usage"] == {
        "input_tokens": 0,
        "output_tokens": 0,
        "cached_tokens": 0,
        "api_calls": 2,
    }


def test_ge_failure_propagates_without_buddy_retry_and_still_closes(
    tmp_path: Path,
) -> None:
    class FailingGenerationClient(_RecordingGenerationClient):
        async def generate_structured(self, request: TextRequest) -> TextResult:
            self.requests.append(request)
            raise RuntimeError("normalized GE failure")

    client = FailingGenerationClient()
    adapter = AsyncOpenAIResponsesFactClient(generation_client=client)

    with pytest.raises(RuntimeError, match="normalized GE failure"):
        run_fact_extraction(
            [_evidence("evid_a", "Geography: peaks.", 0)],
            entities=ENTITIES,
            canon_layer="world",
            campaign_id=None,
            source_class="seed_reference",
            cache_dir=tmp_path / "cache",
            openai_client=adapter,
            allow_heuristic_fallback=False,
        )

    assert len(client.requests) == 1
    assert client.close_calls == 1


def test_concurrent_ge_failure_drains_sibling_before_client_close(
    tmp_path: Path,
) -> None:
    class ConcurrentFailureGenerationClient(_RecordingGenerationClient):
        def __init__(self) -> None:
            super().__init__([])
            self.entered = 0
            self.both_entered = asyncio.Event()
            self.sibling_terminated = asyncio.Event()
            self.closed_after_sibling = False

        async def generate_structured(self, request: TextRequest) -> TextResult:
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
            await super().aclose()

    client = ConcurrentFailureGenerationClient()
    adapter = AsyncOpenAIResponsesFactClient(generation_client=client)

    with pytest.raises(RuntimeError, match="normalized GE failure"):
        run_fact_extraction(
            [
                _evidence("evid_fail", "FAIL_UNIT", 0),
                _evidence("evid_sibling", "Geography: peaks.", 1),
            ],
            entities=ENTITIES,
            canon_layer="world",
            campaign_id=None,
            source_class="seed_reference",
            cache_dir=tmp_path / "cache",
            openai_client=adapter,
            allow_heuristic_fallback=False,
            concurrency=2,
        )

    assert client.entered == 2
    assert client.sibling_terminated.is_set()
    assert client.closed_after_sibling is True
    assert client.close_calls == 1


def test_world_canon_facts_have_correct_truth_state(tmp_path: Path) -> None:
    facts = run_fact_extraction(
        [_evidence("evid_1", "Geography: near Stormspire Peaks.", 0)],
        entities=ENTITIES,
        canon_layer="world",
        campaign_id=None,
        source_class="seed_reference",
        cache_dir=tmp_path / "cache",
        openai_client=_StubFactClient(),
    )["facts"]
    assert facts
    assert all(f["truth_state"] == "CANON" for f in facts)
    assert all(f["source_authority"] == "seed_prep" for f in facts)


def test_temporal_provenance_copied_from_evidence_unit(tmp_path: Path) -> None:
    facts = run_fact_extraction(
        [_evidence("evid_1", "Geography: near Stormspire Peaks.", 7, inferred_session=12)],
        entities=ENTITIES,
        canon_layer="campaign",
        campaign_id="longmont-c1",
        source_class="observed_session_recap",
        cache_dir=tmp_path / "cache",
        openai_client=_StubFactClient(),
    )["facts"]
    assert facts
    assert all(f["asserted_in_session"] == 12 for f in facts)
    assert all(f["sequence_index_within_session"] == 7 for f in facts)


def test_document_session_takes_precedence_for_asserted_session(tmp_path: Path) -> None:
    facts = run_fact_extraction(
        [
            _evidence(
                "evid_1",
                "Geography: near Stormspire Peaks.",
                9,
                inferred_session=3,
                document_session=14,
            )
        ],
        entities=ENTITIES,
        canon_layer="campaign",
        campaign_id="longmont-c1",
        source_class="observed_session_recap",
        cache_dir=tmp_path / "cache",
        openai_client=_StubFactClient(),
    )["facts"]
    assert facts
    assert all(f["asserted_in_session"] == 14 for f in facts)
    assert all(f["sequence_index_within_session"] == 9 for f in facts)


def test_cache_key_scoping_ignores_unrelated_entity_additions(tmp_path: Path) -> None:
    client = _StubFactClient()
    evidence = [_evidence("evid_1", "Mirathorn geography near Stormspire Peaks.", 0)]
    cache_dir = tmp_path / "cache"
    first_entities = [_entity("ent_mirathorn", "Mirathorn")]
    second_entities = [
        _entity("ent_mirathorn", "Mirathorn"),
        _extra_entity("ent_unrelated_npc", "Unrelated NPC"),
    ]

    first = run_fact_extraction(
        evidence,
        entities=first_entities,
        canon_layer="world",
        campaign_id=None,
        source_class="seed_reference",
        cache_dir=cache_dir,
        openai_client=client,
    )
    second = run_fact_extraction(
        evidence,
        entities=second_entities,
        canon_layer="world",
        campaign_id=None,
        source_class="seed_reference",
        cache_dir=cache_dir,
        openai_client=client,
    )

    assert first["facts"] == second["facts"]
    assert first["usage"]["api_calls"] == 1
    assert second["usage"]["api_calls"] == 0
    assert client.calls == 1


def test_usage_accumulates_across_fact_units(tmp_path: Path) -> None:
    class TokenFactStub:
        def extract_facts(self, **kwargs: Any) -> dict[str, Any]:
            return {
                "facts": [
                    {
                        "fact_id": "fact_geo",
                        "subject_entity_id": "ent_mirathorn",
                        "attribute": "geography",
                        "value": {
                            "kind": "scalar",
                            "label": "Near peaks",
                            "normalized": "peaks",
                        },
                    }
                ],
                "_usage": {
                    "input_tokens": 8,
                    "output_tokens": 2,
                    "cached_tokens": 0,
                },
            }

    out = run_fact_extraction(
        [
            _evidence("evid_a", "Geography: peaks one.", 0),
            _evidence("evid_b", "Geography: peaks two.", 1),
        ],
        entities=ENTITIES,
        canon_layer="world",
        campaign_id=None,
        source_class="seed_reference",
        cache_dir=tmp_path / "cache",
        openai_client=TokenFactStub(),
    )
    u = out["usage"]
    assert u["input_tokens"] == 16
    assert u["output_tokens"] == 4
    assert u["api_calls"] == 2


def test_prepare_fact_batch_requests_chunked_cache_key_only_entries(tmp_path: Path) -> None:
    cache_dir = tmp_path / "cache"
    lines, manifest, next_index = prepare_fact_batch_requests_chunked(
        [_evidence("evid_geo", "Mirathorn geography near Stormspire Peaks.", 0)],
        entities=ENTITIES,
        model="test-model",
        batch_size=1,
        cache_dir=cache_dir,
    )
    assert len(lines) == 1
    assert next_index == 1
    entry = manifest[lines[0]["custom_id"]]["entries"][0]
    assert "cache_key" in entry and entry["cache_key"]
    assert "unit" not in entry
    assert "prompt_entity_fp" not in entry


def test_apply_fact_batch_outputs_requires_cache_key_entries(tmp_path: Path) -> None:
    cache_dir = tmp_path / "cache"
    evidence = [_evidence("evid_geo", "Mirathorn geography near Stormspire Peaks.", 0)]
    fact_payload = {
        "results": [
            {
                "unit_index": 0,
                "facts": [
                    {
                        "fact_id": "fact_mirathorn_geography_001",
                        "subject_entity_id": "ent_mirathorn",
                        "attribute": "geography",
                        "value": {
                            "kind": "scalar",
                            "label": "Near Stormspire Peaks",
                            "normalized": "near_stormspire_peaks",
                        },
                    }
                ],
            }
        ]
    }

    lines_new, manifest_new, _ = prepare_fact_batch_requests_chunked(
        evidence,
        entities=ENTITIES,
        model="test-model",
        batch_size=1,
        cache_dir=cache_dir,
    )
    output_rows_new = [
        {
            "custom_id": lines_new[0]["custom_id"],
            "response": {
                "status_code": 200,
                "body": {
                    "usage": {
                        "input_tokens": 11,
                        "output_tokens": 3,
                        "input_tokens_details": {"cached_tokens": 2},
                    },
                    "output": [
                        {
                            "type": "message",
                            "content": [
                                {
                                    "type": "output_text",
                                    "text": json.dumps(fact_payload),
                                }
                            ],
                        }
                    ],
                },
            },
        }
    ]
    failures_new, usage_new = apply_fact_batch_outputs_to_cache(
        output_rows_new,
        manifest_new,
        model_id="test-model",
        cache_dir=cache_dir,
    )
    assert failures_new == []
    assert usage_new["input_tokens"] == 11
    assert usage_new["output_tokens"] == 3
    assert usage_new["cached_tokens"] == 2

    # Missing cache_key entries now fail (no backward-compat path).
    lines_legacy, manifest_legacy = prepare_fact_batch_requests(
        evidence,
        entities=ENTITIES,
        model="test-model",
        batch_size=1,
        cache_dir=tmp_path / "cache_missing_key",
    )
    for spec in manifest_legacy.values():
        for entry in spec["entries"]:
            entry.pop("cache_key", None)
    output_rows_legacy = [
        {
            "custom_id": lines_legacy[0]["custom_id"],
            "response": {
                "status_code": 200,
                "body": {
                    "usage": {
                        "input_tokens": 5,
                        "output_tokens": 2,
                        "input_tokens_details": {"cached_tokens": 0},
                    },
                    "output": [
                        {
                            "type": "message",
                            "content": [
                                {
                                    "type": "output_text",
                                    "text": json.dumps(fact_payload),
                                }
                            ],
                        }
                    ],
                },
            },
        }
    ]
    failures_legacy, usage_legacy = apply_fact_batch_outputs_to_cache(
        output_rows_legacy,
        manifest_legacy,
        model_id="test-model",
        cache_dir=cache_dir,
    )
    assert failures_legacy == [lines_legacy[0]["custom_id"]]
    assert usage_legacy["input_tokens"] == 5
    assert usage_legacy["output_tokens"] == 2
