from __future__ import annotations

from pathlib import Path
from typing import Any

import pytest

from src.contracts.schema_validation import validate_many
from src.ingestion.fact_extractor import (
    OpenAIResponsesFactClient,
    derive_truth_state,
    run_fact_extraction,
)


def _evidence(
    evidence_id: str,
    text: str,
    index: int,
    inferred_session: int | None = None,
    document_session: int | None = None,
) -> dict[str, Any]:
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
        "inferred_session": inferred_session,
        "document_session": document_session,
        "speaker_or_subject": None,
        "notes": None,
    }


def _entity(entity_id: str, display_name: str, entity_type: str = "location") -> dict[str, Any]:
    return {
        "schema_version": "0.1.0",
        "created_at": "2026-03-27T00:00:00Z",
        "updated_at": "2026-03-27T00:00:00Z",
        "record_status": "active",
        "entity_id": entity_id,
        "entity_type": entity_type,
        "display_name": display_name,
        "canonical_name": None,
        "aliases": [display_name],
        "entity_status": "provisional",
        "merged_into_entity_id": None,
        "source_mention_ids": ["men_test_0"],
        "review_state": "unreviewed",
        "entity_tags": [],
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
    )
    assert facts
    validate_many(facts, "fact.schema.json")


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

    assert first == second
    assert client.calls == 1


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
    )

    subject_ids = {f["subject_entity_id"] for f in facts}
    assert "ent_does_not_exist" not in subject_ids
    assert "ent_mirathorn" in subject_ids


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
    )

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
    )

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
    )
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
    )
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


def test_openai_responses_adapter_parses_structured_output() -> None:
    class _FakeParsedResponse:
        output_parsed = {
            "facts": [
                {
                    "fact_id": "fact_test",
                    "subject_entity_id": "ent_test",
                    "attribute": "history",
                    "value": {
                        "kind": "scalar",
                        "label": "An ancient city",
                        "normalized": "ancient_city",
                    },
                }
            ]
        }

    class _FakeResponses:
        def parse(self, **kwargs: Any) -> _FakeParsedResponse:
            assert kwargs["model"] == "test-model"
            assert kwargs["text_format"] is not None
            return _FakeParsedResponse()

    class _FakeSDKClient:
        responses = _FakeResponses()

    adapter = OpenAIResponsesFactClient(sdk_client=_FakeSDKClient())
    payload = adapter.extract_facts(
        model="test-model",
        prompt="extract",
        evidence_unit={},
        entities=[],
        prompt_id="test",
    )
    assert payload["facts"][0]["value"]["label"] == "An ancient city"


def test_world_canon_facts_have_correct_truth_state(tmp_path: Path) -> None:
    facts = run_fact_extraction(
        [_evidence("evid_1", "Geography: near Stormspire Peaks.", 0)],
        entities=ENTITIES,
        canon_layer="world",
        campaign_id=None,
        source_class="seed_reference",
        cache_dir=tmp_path / "cache",
        openai_client=_StubFactClient(),
    )
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
    )
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
    )
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

    assert first == second
    assert client.calls == 1
