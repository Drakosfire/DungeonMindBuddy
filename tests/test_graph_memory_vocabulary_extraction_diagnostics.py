from __future__ import annotations

import json

import pytest

from src.graph_memory.vocabulary import (
    ContextVocabularyPacket,
    DoNotMergeDecision,
    ExtractedVocabularyEdge,
    ExtractedVocabularyNode,
    VocabularyEntry,
    diagnose_vocabulary_extraction_baseline,
    render_context_vocabulary_packet,
    vocabulary_extraction_diagnostics_to_payload,
)


def _packet(**overrides) -> ContextVocabularyPacket:
    payload = {
        "packet_id": "packet:vocab:test",
        "scope": "campaign",
        "known_names": [],
        "type_hints": {},
        "predicate_hints": {},
        "combat_encounter_hints": [],
    }
    payload.update(overrides)
    return ContextVocabularyPacket(**payload)


def test_known_name_pickup_reports_matched_and_missed_names():
    packet = _packet(known_names=["Mireward", "Mireward Council", "North Gate Defense"])

    result = diagnose_vocabulary_extraction_baseline(
        packet=packet,
        extracted_nodes=[
            ExtractedVocabularyNode(node_id="n1", label="Mireward", entity_kind="place"),
            ExtractedVocabularyNode(node_id="n2", label="North Gate Defense", entity_kind="combat_encounter"),
        ],
    ).diagnostics

    assert result["known_name_pickup"]["matched"] == ["Mireward", "North Gate Defense"]
    assert result["known_name_pickup"]["missed"] == ["Mireward Council"]
    assert result["known_name_pickup"]["pickup_rate"] == 0.667


def test_type_hints_report_matched_mismatched_and_missing():
    packet = _packet(
        type_hints={
            "Mireward": "place",
            "Mireward Council": "collective",
            "North Gate Defense": "combat_encounter",
        }
    )

    result = diagnose_vocabulary_extraction_baseline(
        packet=packet,
        extracted_nodes=[
            ExtractedVocabularyNode(node_id="n1", label="Mireward", entity_kind="place"),
            ExtractedVocabularyNode(node_id="n2", label="Mireward Council", entity_kind="place"),
        ],
    ).diagnostics

    assert {item["label"] for item in result["type_hint_alignment"]["matched"]} == {"Mireward"}
    assert result["type_hint_alignment"]["mismatched"] == [
        {"label": "Mireward Council", "expected": "collective", "actual": ["place"]}
    ]
    assert result["type_hint_alignment"]["missing"] == [
        {"label": "North Gate Defense", "expected": "combat_encounter"}
    ]


def test_combat_encounter_pickup_reports_missed_encounter_without_kind_requirement():
    packet = _packet(combat_encounter_hints=["North Gate Defense", "Warehouse Ambush"])

    result = diagnose_vocabulary_extraction_baseline(
        packet=packet,
        extracted_nodes=[ExtractedVocabularyNode(node_id="n1", label="North Gate Defense")],
    ).diagnostics

    assert result["combat_encounter_pickup"] == {
        "matched": ["North Gate Defense"],
        "missed": ["Warehouse Ambush"],
    }


def test_predicate_hint_pickup_matches_edges_touching_label():
    packet = _packet(predicate_hints={"North Gate Defense": ["occurred_at", "involved", "commanded_by"]})

    result = diagnose_vocabulary_extraction_baseline(
        packet=packet,
        extracted_nodes=[],
        extracted_edges=[
            ExtractedVocabularyEdge(
                edge_id="e1",
                source_label="Questionable Company",
                predicate="involved",
                target_label="North Gate Defense",
            ),
            ExtractedVocabularyEdge(
                edge_id="e2",
                source_label="North Gate Defense",
                predicate="occurred_at",
                target_label="Mireward",
            ),
        ],
    ).diagnostics

    assert result["predicate_hint_pickup"]["matched"] == [
        {"label": "North Gate Defense", "predicate": "involved"},
        {"label": "North Gate Defense", "predicate": "occurred_at"},
    ]
    assert result["predicate_hint_pickup"]["missed"] == [
        {"label": "North Gate Defense", "predicate": "commanded_by"}
    ]


def test_duplicate_labels_and_conflicting_kinds_are_diagnosed():
    result = diagnose_vocabulary_extraction_baseline(
        packet=_packet(),
        extracted_nodes=[
            ExtractedVocabularyNode(node_id="n1", label="Mireward", entity_kind="place"),
            ExtractedVocabularyNode(node_id="n2", label="mireward", entity_kind="collective"),
            ExtractedVocabularyNode(node_id="n3", label="Mireward", entity_kind="place"),
        ],
    ).diagnostics

    assert result["collision_diagnostics"]["duplicate_extracted_labels"] == [
        {"label": "Mireward", "node_ids": ["n1", "n2", "n3"]}
    ]
    assert result["collision_diagnostics"]["conflicting_kind_labels"] == [
        {"label": "Mireward", "kinds": ["collective", "place"]}
    ]
    assert result["summary"]["has_duplicate_label_collisions"] is True
    assert result["summary"]["has_conflicting_kind_collisions"] is True


def test_do_not_merge_diagnostics_are_conservative_with_mapping():
    packet = _packet(
        do_not_merge_hints=[
            DoNotMergeDecision(
                decision_id="dnm:mireward",
                left_vocab_id="vocab:place:mireward",
                right_vocab_id="vocab:collective:mireward",
            )
        ]
    )

    result = diagnose_vocabulary_extraction_baseline(
        packet=packet,
        extracted_nodes=[ExtractedVocabularyNode(node_id="n1", label="Mireward", entity_kind="place")],
        vocab_id_to_label={
            "vocab:place:mireward": "Mireward",
            "vocab:collective:mireward": "Mireward",
        },
    ).diagnostics

    assert result["do_not_merge_diagnostics"]["potentially_collapsed"] == [
        {
            "left_vocab_id": "vocab:place:mireward",
            "right_vocab_id": "vocab:collective:mireward",
            "left_label": "Mireward",
            "right_label": "Mireward",
            "normalized_label": "mireward",
        }
    ]
    assert result["summary"]["has_do_not_merge_collisions"] is True


def test_diagnostics_are_json_serializable_and_quote_free():
    result = diagnose_vocabulary_extraction_baseline(
        packet=_packet(known_names=["Mireward"]),
        extracted_nodes=[ExtractedVocabularyNode(node_id="n1", label="Mireward", entity_kind="place")],
    ).diagnostics

    serialized = json.dumps(result, sort_keys=True)
    restored = json.loads(serialized)

    assert "quote" not in serialized
    assert restored["diagnostics_method"] == "post_extraction_vocabulary_diagnostics_v1"
    assert "known_name_pickup" in restored
    assert "summary" in restored


def test_payload_helper_round_trips_dict_identity():
    result = diagnose_vocabulary_extraction_baseline(packet=_packet(), extracted_nodes=[])

    payload = vocabulary_extraction_diagnostics_to_payload(result)

    assert payload == result.diagnostics


def test_invalid_extracted_records_fail_clearly():
    with pytest.raises(ValueError, match="label"):
        ExtractedVocabularyNode(node_id="n1", label="")

    with pytest.raises(ValueError, match="predicate"):
        ExtractedVocabularyEdge(edge_id="e1", source_label="Mireward", predicate="", target_label="Council")


def test_packet_renderer_integration_propagates_packet_id():
    entry = VocabularyEntry(
        vocab_id="vocab:campaign:mireward",
        canonical_label="Mireward",
        entity_kind="place",
        scope="campaign",
        campaign_id="campaign:mireward",
    )
    packet = render_context_vocabulary_packet(campaign_entries=[entry], packet_seed="diagnostics-test").packet

    result = diagnose_vocabulary_extraction_baseline(
        packet=packet,
        extracted_nodes=[ExtractedVocabularyNode(node_id="n1", label="Mireward", entity_kind="place")],
    ).diagnostics

    assert result["packet_id"] == packet.packet_id
