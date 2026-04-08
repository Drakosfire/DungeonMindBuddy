from __future__ import annotations

from src.agent.evidence_retriever import (
    rank_entities_by_evidence_overlap,
    retrieve_relevant_evidence,
)


def _unit(
    evidence_id: str,
    text: str,
    *,
    document_id: str,
    source_order_index: int,
    canon_layer: str = "campaign",
    campaign_id: str | None = "camp-1",
    inferred_session: int | None = 12,
) -> dict:
    return {
        "evidence_id": evidence_id,
        "text": text,
        "document_id": document_id,
        "source_order_index": source_order_index,
        "canon_layer": canon_layer,
        "campaign_id": campaign_id,
        "inferred_session": inferred_session,
    }


def test_retrieve_relevant_evidence_respects_scope_docs() -> None:
    evidence_units = [
        _unit(
            "evid_alarm_1",
            "Alarm pulses trigger reinforcements in the council room.",
            document_id="doc_session12",
            source_order_index=10,
        ),
        _unit(
            "evid_alarm_2",
            "Alarm pulses were disabled by the party.",
            document_id="doc_session13",
            source_order_index=3,
        ),
    ]
    result = retrieve_relevant_evidence(
        "What alarm pulses affect the fight?",
        evidence_units,
        campaign_id="camp-1",
        scope_document_ids=["doc_session12"],
        top_k=5,
    )
    assert "evid_alarm_1" in result.selected_evidence_ids
    assert "evid_alarm_2" not in result.selected_evidence_ids
    assert result.selected_document_ids == ["doc_session12"]


def test_retrieve_relevant_evidence_neighbor_expansion_by_source_order() -> None:
    evidence_units = [
        _unit(
            "evid_10",
            "Time pressure mechanic starts countdown.",
            document_id="doc_session12",
            source_order_index=10,
        ),
        _unit(
            "evid_11",
            "Countdown advances if council delays.",
            document_id="doc_session12",
            source_order_index=11,
        ),
        _unit(
            "evid_12",
            "Consequences escalate after the countdown.",
            document_id="doc_session12",
            source_order_index=12,
        ),
    ]
    result = retrieve_relevant_evidence(
        "What is the countdown time pressure?",
        evidence_units,
        campaign_id="camp-1",
        top_k=1,
        neighbor_window=1,
        max_neighbors=2,
    )
    assert "evid_10" in result.selected_evidence_ids
    assert "evid_11" in result.selected_evidence_ids


def test_retrieve_relevant_evidence_campaign_filtering() -> None:
    evidence_units = [
        _unit(
            "evid_c1",
            "Illusory walls appear in session 12.",
            document_id="doc_session12",
            source_order_index=8,
            campaign_id="camp-1",
        ),
        _unit(
            "evid_other_campaign",
            "Illusory walls appear in a different campaign.",
            document_id="doc_other",
            source_order_index=2,
            campaign_id="camp-2",
        ),
    ]
    result = retrieve_relevant_evidence(
        "Tell me about illusory walls.",
        evidence_units,
        campaign_id="camp-1",
        top_k=10,
    )
    assert "evid_c1" in result.selected_evidence_ids
    assert "evid_other_campaign" not in result.selected_evidence_ids


def test_rank_entities_by_evidence_overlap_scores() -> None:
    projection = {
        "entities": {
            "ent_room": {
                "attributes": {
                    "defenses": {
                        "provenance_evidence_ids": ["evid_alarm", "evid_runes"]
                    }
                }
            },
            "ent_wolf": {
                "attributes": {
                    "operational_status": {
                        "provenance_evidence_ids": ["evid_wolf_1"]
                    }
                }
            },
        }
    }
    scores = rank_entities_by_evidence_overlap(
        projection,
        {"evid_alarm", "evid_wolf_1"},
    )
    assert "ent_room" in scores
    assert "ent_wolf" in scores
    assert scores["ent_room"] > 0
    assert scores["ent_wolf"] > 0
