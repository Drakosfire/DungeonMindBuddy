from __future__ import annotations

from src.reducer.canon_projection import attach_scope_relevance_metadata


def _projection_fixture() -> dict:
    return {
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


def _evidence_fixture() -> list[dict]:
    return [
        {"evidence_id": "evid_battle_1", "document_id": "doc_battle_with_the_wolf_and_aftermath"},
        {"evidence_id": "evid_battle_2", "document_id": "doc_battle_with_the_wolf_and_aftermath"},
        {"evidence_id": "evid_notes_1", "document_id": "doc_longmont_campaign_general_notes"},
        {"evidence_id": "evid_notes_2", "document_id": "doc_longmont_campaign_general_notes"},
    ]


def test_attach_scope_relevance_marks_pruning_candidate() -> None:
    enriched = attach_scope_relevance_metadata(
        projection=_projection_fixture(),
        evidence_units=_evidence_fixture(),
        scope_document_ids={"doc_battle_with_the_wolf_and_aftermath"},
        scope_confidence=1.0,
        min_scope_confidence=0.75,
        min_entity_evidence_count=2,
        mentioned_entity_ids=set(),
    )
    wolf = enriched["entities"]["ent_the_wolf"]["scope_relevance"]
    elric = enriched["entities"]["ent_commander_elric_vane"]["scope_relevance"]

    assert wolf["classification"] == "in_scope"
    assert elric["classification"] == "out_of_scope_confident"
    assert elric["pruning_candidate"] is True
    assert "ent_commander_elric_vane" in enriched["scope_relevance"]["pruning_candidates"]


def test_attach_scope_relevance_keeps_unknown_when_scope_low_confidence() -> None:
    enriched = attach_scope_relevance_metadata(
        projection=_projection_fixture(),
        evidence_units=_evidence_fixture(),
        scope_document_ids={"doc_new_world_bootstrap"},
        scope_confidence=0.2,
        min_scope_confidence=0.75,
        min_entity_evidence_count=2,
        mentioned_entity_ids=set(),
    )
    elric = enriched["entities"]["ent_commander_elric_vane"]["scope_relevance"]
    assert elric["classification"] == "unknown_insufficient_signal"
    assert elric["pruning_candidate"] is False
