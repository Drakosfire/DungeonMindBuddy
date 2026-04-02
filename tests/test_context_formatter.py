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
            "entity_type": "location",
            "display_name": "Mirathorn",
        }
    ]
    output = format_projection_context(projection, entities, question="Catch me up")

    assert "Question: Catch me up" in output
    assert "== Entity: Mirathorn (location) ==" in output
    assert "history: Founded over 200 years ago." in output
    assert "[CANON, from: layer=world, source_class=seed_reference, fact=fact_m_hist]" in output


def test_includes_entity_tags_in_header_when_present() -> None:
    projection = _projection_template()
    entities = [
        {
            "entity_id": "ent_mirathorn",
            "entity_type": "other",
            "display_name": "Nameless Goddess",
            "entity_tags": ["deity", "lore_figure"],
        }
    ]
    output = format_projection_context(projection, entities)
    assert "== Entity: Nameless Goddess (other) [deity, lore_figure] ==" in output


def test_includes_entity_type_from_metadata() -> None:
    projection = _projection_template()
    entities = [
        {"entity_id": "ent_mirathorn", "entity_type": "location", "display_name": "Mirathorn"}
    ]
    output = format_projection_context(projection, entities)

    assert "(location)" in output


def test_surfaces_conflicts_in_output() -> None:
    projection = _projection_template()
    entities = [
        {"entity_id": "ent_mirathorn", "entity_type": "location", "display_name": "Mirathorn"}
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
            {"entity_id": entity_id, "entity_type": "other", "display_name": f"Entity {idx}"}
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
    entities = [{"entity_id": "ent_wolf", "entity_type": "npc", "display_name": "the Wolf"}]
    output = format_projection_context(projection, entities)
    assert "[OBSERVED, from: layer=campaign, campaign=longmont-c1, source_class=observed_session_recap, fact=fact_wolf_obs]" in output
