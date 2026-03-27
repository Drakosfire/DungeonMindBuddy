from __future__ import annotations

from pathlib import Path

from src.store import FactStore


def _base_record() -> dict[str, str]:
    return {
        "schema_version": "0.1.0",
        "created_at": "2026-03-27T00:00:00Z",
        "updated_at": "2026-03-27T00:00:00Z",
        "record_status": "active",
    }


def _sample_evidence(evidence_id: str = "evid_store_001") -> dict[str, object]:
    return {
        **_base_record(),
        "evidence_id": evidence_id,
        "document_id": "doc_store_test",
        "document_type": "world_reference",
        "document_title": "Store Test",
        "source_class": "seed_reference",
        "canon_layer": "world",
        "campaign_id": None,
        "text": "Mirathorn is prosperous.",
        "section_path": ["Overview"],
        "paragraph_index": 0,
        "source_order_index": 0,
        "line_span": None,
        "char_span": None,
        "inferred_session": None,
        "speaker_or_subject": None,
        "notes": None,
    }


def _sample_entity(entity_id: str, name: str, aliases: list[str]) -> dict[str, object]:
    return {
        **_base_record(),
        "entity_id": entity_id,
        "entity_type": "location",
        "display_name": name,
        "canonical_name": None,
        "aliases": aliases,
        "entity_status": "provisional",
        "merged_into_entity_id": None,
        "source_mention_ids": [f"men_{entity_id}"],
        "review_state": "unreviewed",
        "notes": None,
    }


def _sample_fact(fact_id: str = "fact_store_001") -> dict[str, object]:
    return {
        **_base_record(),
        "fact_id": fact_id,
        "subject_entity_id": "ent_mirathorn",
        "attribute": "operational_status",
        "value": {
            "kind": "state",
            "label": "Prosperous and active",
            "normalized": "prosperous",
        },
        "truth_state": "CANON",
        "source_authority": "seed_prep",
        "evidence_ids": ["evid_store_001"],
    }


def test_store_round_trip_load_and_save(tmp_path: Path) -> None:
    store = FactStore(tmp_path / "store")
    store.add_evidence_units([_sample_evidence()])
    store.add_entities([_sample_entity("ent_mirathorn", "Mirathorn", ["City of Mirathorn"])])
    store.add_facts([_sample_fact()])
    store.save()

    reloaded = FactStore(tmp_path / "store")
    reloaded.load()

    assert len(reloaded.evidence_units) == 1
    assert len(reloaded.entities) == 1
    assert len(reloaded.facts) == 1
    assert reloaded.facts[0]["fact_id"] == "fact_store_001"


def test_entity_dedup_merges_aliases_on_name_overlap(tmp_path: Path) -> None:
    store = FactStore(tmp_path / "store")
    first = _sample_entity("ent_mirathorn", "Mirathorn", ["City of Mirathorn"])
    second = _sample_entity("ent_city_of_mirathorn", "City of Mirathorn", ["Mirathorn City"])

    store.add_entities([first, second])

    assert len(store.entities) == 1
    merged = store.entities[0]
    aliases = set(merged["aliases"])
    assert "Mirathorn" in aliases
    assert "City of Mirathorn" in aliases
    assert "Mirathorn City" in aliases


def test_project_delegates_to_reducer(tmp_path: Path) -> None:
    store = FactStore(tmp_path / "store")
    store.add_evidence_units([_sample_evidence()])
    store.add_facts([_sample_fact()])

    projection = store.project(campaign_id=None)

    assert "entities" in projection
    assert "ent_mirathorn" in projection["entities"]
    attrs = projection["entities"]["ent_mirathorn"]["attributes"]
    assert attrs["operational_status"]["value_normalized"] == "prosperous"
