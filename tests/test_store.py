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


def _sample_entity(
    entity_id: str,
    name: str,
    aliases: list[str],
    entity_type: str = "location",
) -> dict[str, object]:
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
        **_base_record(),
        "entity_id": entity_id,
        "entity_class": entity_class,
        "entity_type": entity_type,
        "entity_kind": entity_class,
        "decision": "entity",
        "exclude_reason": None,
        "display_name": name,
        "canonical_name": None,
        "aliases": aliases,
        "entity_status": "provisional",
        "merged_into_entity_id": None,
        "source_mention_ids": [f"men_{entity_id}"],
        "review_state": "unreviewed",
        "entity_tags": [],
        "subtype_facets": [],
        "narrative_tags": [],
        "document_tags": [],
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
        "asserted_in_session": None,
        "sequence_index_within_session": None,
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


def test_entity_merge_is_blocked_when_types_conflict(tmp_path: Path) -> None:
    store = FactStore(tmp_path / "store")
    wolf = _sample_entity("ent_the_wolf", "the Wolf", ["wolf"], entity_type="npc")
    council_room = _sample_entity(
        "ent_council_room",
        "Council Room",
        ["wolf"],
        entity_type="location",
    )
    store.add_entities([wolf, council_room])
    assert len(store.entities) == 2


def test_compact_deduplicates_facts_and_merges_evidence_ids(tmp_path: Path) -> None:
    store = FactStore(tmp_path / "store")
    store.add_evidence_units([_sample_evidence("evid_1"), _sample_evidence("evid_2")])
    fact1 = _sample_fact("fact_1")
    fact2 = _sample_fact("fact_2")
    fact1["evidence_ids"] = ["evid_1"]
    fact2["evidence_ids"] = ["evid_2"]
    store.add_facts([fact1, fact2])
    stats = store.compact()

    assert stats["facts_before"] == 2
    assert stats["facts_after"] == 1
    assert set(store.facts[0]["evidence_ids"]) == {"evid_1", "evid_2"}


def test_merge_quality_signals_reports_alias_cardinality(tmp_path: Path) -> None:
    store = FactStore(tmp_path / "store")
    store.add_entities(
        [
            _sample_entity("ent_a", "Alpha", ["a1", "a2", "a3", "a4", "a5", "a6", "a7", "a8"]),
            _sample_entity("ent_b", "Beta", ["b1"]),
        ]
    )
    sig = store.merge_quality_signals()
    assert sig["max_alias_count"] == 8
    assert sig["entities_with_alias_count_ge_8"] == 1
    assert sig["top_alias_counts"][0]["entity_id"] == "ent_a"


def test_entity_tags_union_on_merge(tmp_path: Path) -> None:
    store = FactStore(tmp_path / "store")
    a = _sample_entity("ent_alpha", "Alpha Node", [], entity_type="other")
    a["entity_tags"] = ["deity", "lore"]
    b = _sample_entity("ent_alpha_dup", "Alpha Node", [], entity_type="other")
    b["entity_tags"] = ["patron", "deity"]
    store.add_entities([a, b])
    assert len(store.entities) == 1
    tags = store.entities[0]["entity_tags"]
    assert set(tags) == {"deity", "lore", "patron"}


def test_alias_cap_enforced_during_merge(tmp_path: Path) -> None:
    store = FactStore(tmp_path / "store")
    many_aliases = [f"alias_{i}" for i in range(30)]
    first = _sample_entity("ent_mirathorn", "Mirathorn", many_aliases[:15])
    second = _sample_entity("ent_city_m", "Mirathorn", many_aliases[15:])
    store.add_entities([first, second])

    assert len(store.entities) == 1
    assert len(store.entities[0]["aliases"]) == FactStore._MAX_ALIASES_PER_ENTITY
    for alias in store.entities[0]["aliases"]:
        assert len(alias) <= max(len(a) for a in store.entities[0]["aliases"])


def test_ingest_index_persists_across_save_load(tmp_path: Path) -> None:
    store = FactStore(tmp_path / "store")
    store.record_ingest_fingerprint(
        "fingerprint-key",
        {"source_path": "foo.md", "layer": "campaign"},
    )
    store.save()

    reloaded = FactStore(tmp_path / "store")
    reloaded.load()
    assert reloaded.has_ingest_fingerprint("fingerprint-key")


def test_wiki_pages_roundtrip(tmp_path: Path) -> None:
    store = FactStore(tmp_path / "store")
    store.wiki_pages = {"ent_a": "Article about A."}
    store.wiki_manifest = {"ent_a": {"compiled_at": "2026-01-01T00:00:00Z", "fact_hash": "abc"}}
    assert store.has_wiki()

    store.save()
    reloaded = FactStore(tmp_path / "store")
    reloaded.load()
    assert reloaded.has_wiki()
    assert reloaded.wiki_pages["ent_a"] == "Article about A."
    assert reloaded.wiki_manifest["ent_a"]["fact_hash"] == "abc"
