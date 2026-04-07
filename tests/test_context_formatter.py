from __future__ import annotations

from src.agent.context_formatter import format_projection_context


def _projection_template() -> dict:
    return {
        "campaign_id": None,
        "entities": {
            "ent_mirathorn": {
                "attributes": {
                    "history": {
                        "selected_fact_id": "fact_m_hist",
                        "value_label": "Founded over 200 years ago.",
                        "value_normalized": "founded_200_years",
                        "source_layer": "world",
                        "source_campaign_id": None,
                        "source_class": "seed_reference",
                        "source_truth_state": "CANON",
                        "fact_ids": ["fact_m_hist"],
                        "provenance_evidence_ids": ["evid_1"],
                        "conflict_ids": [],
                    },
                    "geography": {
                        "selected_fact_id": "fact_m_geo",
                        "value_label": "At the base of Stormspire Peaks.",
                        "value_normalized": "stormspire_base",
                        "source_layer": "world",
                        "source_campaign_id": None,
                        "source_class": "seed_reference",
                        "source_truth_state": "CANON",
                        "fact_ids": ["fact_m_geo"],
                        "provenance_evidence_ids": ["evid_2"],
                        "conflict_ids": ["auto_conflict_001"],
                    },
                }
            }
        },
        "conflicts": [],
        "metrics": {"open_conflicts": 1, "resolved_conflicts": 0, "projected_entities": 1},
    }


def test_formats_minimal_projection_shape() -> None:
    projection = _projection_template()
    entities = [
        {
            "entity_id": "ent_mirathorn",
            "entity_class": "place",
            "display_name": "Mirathorn",
        }
    ]
    output = format_projection_context(projection, entities, question="Catch me up")

    assert "Question: Catch me up" in output
    assert "== Entity: Mirathorn (place) ==" in output
    assert "history: Founded over 200 years ago." in output
    assert "[CANON, from: layer=world, source_class=seed_reference, fact=fact_m_hist]" in output


def test_includes_entity_tags_in_header_when_present() -> None:
    projection = _projection_template()
    entities = [
        {
            "entity_id": "ent_mirathorn",
            "entity_class": "concept",
            "display_name": "Nameless Goddess",
            "entity_tags": ["deity", "lore_figure"],
        }
    ]
    output = format_projection_context(projection, entities)
    assert "== Entity: Nameless Goddess (concept) [deity, lore_figure] ==" in output


def test_includes_entity_class_from_metadata() -> None:
    projection = _projection_template()
    entities = [
        {"entity_id": "ent_mirathorn", "entity_class": "place", "display_name": "Mirathorn"}
    ]
    output = format_projection_context(projection, entities)

    assert "(place)" in output


def test_surfaces_conflicts_in_output() -> None:
    projection = _projection_template()
    entities = [
        {"entity_id": "ent_mirathorn", "entity_class": "place", "display_name": "Mirathorn"}
    ]
    output = format_projection_context(projection, entities)

    assert "CONFLICTS:" in output
    assert "geography: 1 competing facts (auto_conflict_001)" in output


def test_handles_empty_projection() -> None:
    output = format_projection_context({"entities": {}}, [])
    assert output == "No projected entities are available for this campaign scope."


def test_respects_entity_cap_with_truncation_note() -> None:
    from src.agent.context_formatter import MAX_ENTITIES

    total = MAX_ENTITIES + 5
    entities_payload: dict[str, dict] = {}
    metadata: list[dict] = []
    for idx in range(total):
        entity_id = f"ent_{idx:04d}"
        entities_payload[entity_id] = {
            "attributes": {
                "history": {
                    "selected_fact_id": f"fact_{idx:04d}",
                    "value_label": f"History {idx}",
                    "value_normalized": None,
                    "source_layer": "world",
                    "source_campaign_id": None,
                    "source_class": "seed_reference",
                    "source_truth_state": "CANON",
                    "fact_ids": [f"fact_{idx:04d}"],
                    "provenance_evidence_ids": [f"evid_{idx:04d}"],
                    "conflict_ids": [],
                }
            }
        }
        metadata.append(
            {"entity_id": entity_id, "entity_class": "concept", "display_name": f"Entity {idx}"}
        )

    projection = {"entities": entities_payload}
    output = format_projection_context(projection, metadata)

    assert output.count("== Entity:") == MAX_ENTITIES
    assert f"Context truncated to top {MAX_ENTITIES} entities by fact count" in output


def test_campaign_truth_state_is_rendered_when_present() -> None:
    projection = {
        "entities": {
            "ent_wolf": {
                "attributes": {
                    "physical_condition": {
                        "selected_fact_id": "fact_wolf_obs",
                        "value_label": "receives a killing blow (dies)",
                        "value_normalized": "dead",
                        "source_layer": "campaign",
                        "source_campaign_id": "longmont-c1",
                        "source_class": "observed_session_recap",
                        "source_truth_state": "OBSERVED",
                        "fact_ids": ["fact_wolf_obs"],
                        "provenance_evidence_ids": ["evid_wolf"],
                        "conflict_ids": [],
                    }
                }
            }
        }
    }
    entities = [{"entity_id": "ent_wolf", "entity_class": "actor", "display_name": "the Wolf"}]
    output = format_projection_context(projection, entities)
    assert "[OBSERVED, from: layer=campaign, campaign=longmont-c1, source_class=observed_session_recap, fact=fact_wolf_obs]" in output


def test_scope_hard_excludes_confident_out_of_scope_entity() -> None:
    projection = {
        "entities": {
            "ent_the_wolf": {
                "attributes": {
                    "role": {
                        "selected_fact_id": "fact_wolf_role",
                        "value_label": "central adversary",
                        "source_layer": "world",
                        "source_truth_state": "CANON",
                        "source_class": "seed_reference",
                        "fact_ids": ["fact_wolf_role"],
                        "provenance_evidence_ids": ["evid_battle_1", "evid_battle_2"],
                        "conflict_ids": [],
                    }
                }
            },
            "ent_commander_elric_vane": {
                "attributes": {
                    "rank_or_title": {
                        "selected_fact_id": "fact_elric_rank",
                        "value_label": "Commander",
                        "source_layer": "campaign",
                        "source_truth_state": "OBSERVED",
                        "source_class": "observed_session_recap",
                        "fact_ids": ["fact_elric_rank"],
                        "provenance_evidence_ids": ["evid_notes_1", "evid_notes_2"],
                        "conflict_ids": [],
                    }
                }
            },
        }
    }
    entities = [
        {"entity_id": "ent_the_wolf", "entity_class": "actor", "display_name": "the Wolf"},
        {
            "entity_id": "ent_commander_elric_vane",
            "entity_class": "actor",
            "display_name": "Commander Elric Vane",
        },
    ]
    evidence_units = [
        {"evidence_id": "evid_battle_1", "document_id": "doc_battle_with_the_wolf_and_aftermath"},
        {"evidence_id": "evid_battle_2", "document_id": "doc_battle_with_the_wolf_and_aftermath"},
        {"evidence_id": "evid_notes_1", "document_id": "doc_longmont_campaign_general_notes"},
        {"evidence_id": "evid_notes_2", "document_id": "doc_longmont_campaign_general_notes"},
    ]
    output = format_projection_context(
        projection,
        entities,
        question="Catch me up on the council room battle",
        evidence_units=evidence_units,
        scope_document_ids={"doc_battle_with_the_wolf_and_aftermath"},
        hard_exclude_out_of_scope=True,
    )
    assert "== Entity: the Wolf (actor) ==" in output
    assert "== Entity: Commander Elric Vane (actor) ==" not in output


def test_scope_keeps_unknown_when_scope_confidence_is_low() -> None:
    projection = {
        "entities": {
            "ent_commander_elric_vane": {
                "attributes": {
                    "rank_or_title": {
                        "selected_fact_id": "fact_elric_rank",
                        "value_label": "Commander",
                        "source_layer": "campaign",
                        "source_truth_state": "OBSERVED",
                        "source_class": "observed_session_recap",
                        "fact_ids": ["fact_elric_rank"],
                        "provenance_evidence_ids": ["evid_notes_1", "evid_notes_2"],
                        "conflict_ids": [],
                    }
                }
            }
        }
    }
    entities = [
        {
            "entity_id": "ent_commander_elric_vane",
            "entity_class": "actor",
            "display_name": "Commander Elric Vane",
        }
    ]
    evidence_units = [
        {"evidence_id": "evid_notes_1", "document_id": "doc_longmont_campaign_general_notes"},
        {"evidence_id": "evid_notes_2", "document_id": "doc_longmont_campaign_general_notes"},
    ]
    output = format_projection_context(
        projection,
        entities,
        question="What matters in this new region?",
        evidence_units=evidence_units,
        scope_document_ids={"doc_new_region_scene_notes"},
        scope_confidence=0.2,
        hard_exclude_out_of_scope=True,
    )
    assert "== Entity: Commander Elric Vane (actor) ==" in output


def test_scope_mention_protects_entity_from_hard_exclusion() -> None:
    projection = {
        "entities": {
            "ent_commander_elric_vane": {
                "attributes": {
                    "rank_or_title": {
                        "selected_fact_id": "fact_elric_rank",
                        "value_label": "Commander",
                        "source_layer": "campaign",
                        "source_truth_state": "OBSERVED",
                        "source_class": "observed_session_recap",
                        "fact_ids": ["fact_elric_rank"],
                        "provenance_evidence_ids": ["evid_notes_1", "evid_notes_2"],
                        "conflict_ids": [],
                    }
                }
            }
        }
    }
    entities = [
        {
            "entity_id": "ent_commander_elric_vane",
            "entity_class": "actor",
            "display_name": "Commander Elric Vane",
            "aliases": ["Elric"],
        }
    ]
    evidence_units = [
        {"evidence_id": "evid_notes_1", "document_id": "doc_longmont_campaign_general_notes"},
        {"evidence_id": "evid_notes_2", "document_id": "doc_longmont_campaign_general_notes"},
    ]
    output = format_projection_context(
        projection,
        entities,
        question="What was Elric doing during this scene?",
        evidence_units=evidence_units,
        scope_document_ids={"doc_battle_with_the_wolf_and_aftermath"},
        hard_exclude_out_of_scope=True,
    )
    assert "== Entity: Commander Elric Vane (actor) ==" in output


def test_scope_annotations_include_classification_when_enabled() -> None:
    projection = {
        "entities": {
            "ent_the_wolf": {
                "attributes": {
                    "role": {
                        "selected_fact_id": "fact_wolf_role",
                        "value_label": "central adversary",
                        "source_layer": "world",
                        "source_truth_state": "CANON",
                        "source_class": "seed_reference",
                        "fact_ids": ["fact_wolf_role"],
                        "provenance_evidence_ids": ["evid_battle_1"],
                        "conflict_ids": [],
                    }
                }
            }
        }
    }
    entities = [{"entity_id": "ent_the_wolf", "entity_class": "actor", "display_name": "the Wolf"}]
    evidence_units = [
        {"evidence_id": "evid_battle_1", "document_id": "doc_battle_with_the_wolf_and_aftermath"}
    ]
    output = format_projection_context(
        projection,
        entities,
        evidence_units=evidence_units,
        scope_document_ids={"doc_battle_with_the_wolf_and_aftermath"},
        include_scope_annotations=True,
    )
    assert "scope_relevance: classification=in_scope" in output
