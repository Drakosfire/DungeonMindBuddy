from __future__ import annotations

from src.reducer.canon_projection import project_entity_state


def _evidence(
    evidence_id: str,
    *,
    layer: str,
    campaign_id: str | None,
    source_class: str,
) -> dict[str, object]:
    return {
        "schema_version": "0.1.0",
        "created_at": "2026-03-27T00:00:00Z",
        "updated_at": "2026-03-27T00:00:00Z",
        "record_status": "active",
        "evidence_id": evidence_id,
        "document_id": "doc_test",
        "document_type": "world_reference",
        "document_title": "Test",
        "source_class": source_class,
        "canon_layer": layer,
        "campaign_id": campaign_id,
        "text": "test",
        "section_path": ["Session 12"],
        "paragraph_index": 0,
        "source_order_index": 0,
        "line_span": None,
        "char_span": None,
        "inferred_session": 12,
        "speaker_or_subject": None,
        "notes": None,
    }


def _fact(
    fact_id: str,
    value_label: str,
    *,
    evidence_id: str,
    truth_state: str = "OBSERVED",
    session: int | None = None,
    seq: int | None = None,
) -> dict[str, object]:
    return {
        "schema_version": "0.1.0",
        "created_at": "2026-03-27T00:00:00Z",
        "updated_at": "2026-03-27T00:00:00Z",
        "record_status": "active",
        "fact_id": fact_id,
        "subject_entity_id": "ent_the_wolf",
        "attribute": "physical_condition",
        "value": {"kind": "state", "label": value_label, "normalized": None},
        "truth_state": truth_state,
        "source_authority": "observed_recap",
        "evidence_ids": [evidence_id],
        "asserted_in_session": session,
        "sequence_index_within_session": seq,
    }


def test_contradictory_observed_without_temporal_metadata_prefers_terminal_outcome() -> None:
    evidence_units = [
        _evidence(
            "evid_world",
            layer="world",
            campaign_id=None,
            source_class="seed_reference",
        ),
        _evidence(
            "evid_campaign_1",
            layer="campaign",
            campaign_id="longmont-c1",
            source_class="observed_session_recap",
        ),
        _evidence(
            "evid_campaign_2",
            layer="campaign",
            campaign_id="longmont-c1",
            source_class="observed_session_recap",
        ),
    ]
    facts = [
        _fact(
            "fact_the_wolf_physical_condition_f8fe558847d0",
            "Invisible",
            evidence_id="evid_campaign_1",
        ),
        _fact(
            "fact_the_wolf_physical_condition_0bff1a76ba2e",
            "receives a killing blow (dies)",
            evidence_id="evid_campaign_2",
        ),
        _fact(
            "fact_the_wolf_physical_condition_bf103ae53327",
            "Corrupted",
            evidence_id="evid_world",
            truth_state="CANON",
        ),
    ]

    projection = project_entity_state(
        evidence_units=evidence_units,
        facts=facts,
        conflicts=[],
        canon_decisions=[],
        campaign_id="longmont-c1",
    )
    attr = projection["entities"]["ent_the_wolf"]["attributes"]["physical_condition"]
    assert attr["value_label"] == "receives a killing blow (dies)"
    assert attr["source_truth_state"] == "OBSERVED"


def test_temporal_metadata_takes_precedence_when_available() -> None:
    evidence_units = [
        _evidence(
            "evid_campaign_old",
            layer="campaign",
            campaign_id="longmont-c1",
            source_class="observed_session_recap",
        ),
        _evidence(
            "evid_campaign_new",
            layer="campaign",
            campaign_id="longmont-c1",
            source_class="observed_session_recap",
        ),
    ]
    facts = [
        _fact(
            "fact_old",
            "Invisible",
            evidence_id="evid_campaign_old",
            session=11,
            seq=3,
        ),
        _fact(
            "fact_new",
            "Wounded but standing",
            evidence_id="evid_campaign_new",
            session=12,
            seq=1,
        ),
    ]

    projection = project_entity_state(
        evidence_units=evidence_units,
        facts=facts,
        conflicts=[],
        canon_decisions=[],
        campaign_id="longmont-c1",
    )
    attr = projection["entities"]["ent_the_wolf"]["attributes"]["physical_condition"]
    assert attr["selected_fact_id"] == "fact_new"


def test_non_terminal_competing_resolved_by_evidence_ordering_not_fact_id() -> None:
    """Fact IDs are deliberately inverted: zzz_later is the lexicographic winner but
    is linked to the EARLIER evidence (source_order_index=0).  The correct winner
    is aaa_earlier (linked to source_order_index=1) because evidence ordering, not
    fact_id, must determine recency."""
    evidence_units = [
        {
            **_evidence(
                "evid_first",
                layer="campaign",
                campaign_id="longmont-c1",
                source_class="observed_session_recap",
            ),
            "source_order_index": 0,
            "inferred_session": None,
        },
        {
            **_evidence(
                "evid_second",
                layer="campaign",
                campaign_id="longmont-c1",
                source_class="observed_session_recap",
            ),
            "source_order_index": 1,
            "inferred_session": None,
        },
    ]
    facts = [
        _fact(
            "fact_zzz_later_lexically",
            "Invisible",
            evidence_id="evid_first",
        ),
        _fact(
            "fact_aaa_earlier_lexically",
            "Wounded but standing",
            evidence_id="evid_second",
        ),
    ]

    projection = project_entity_state(
        evidence_units=evidence_units,
        facts=facts,
        conflicts=[],
        canon_decisions=[],
        campaign_id="longmont-c1",
    )
    attr = projection["entities"]["ent_the_wolf"]["attributes"]["physical_condition"]
    assert attr["selected_fact_id"] == "fact_aaa_earlier_lexically"


def test_evidence_ordering_fallback_with_session_docs() -> None:
    """When session headings ARE present and facts carry temporal metadata,
    session+seq ordering still takes precedence over evidence source_order_index."""
    evidence_units = [
        _evidence(
            "evid_session11",
            layer="campaign",
            campaign_id="longmont-c1",
            source_class="observed_session_recap",
        ),
        _evidence(
            "evid_session12",
            layer="campaign",
            campaign_id="longmont-c1",
            source_class="observed_session_recap",
        ),
    ]
    facts = [
        _fact(
            "fact_old",
            "Invisible",
            evidence_id="evid_session11",
            session=12,
            seq=5,
        ),
        _fact(
            "fact_new",
            "Wounded",
            evidence_id="evid_session12",
            session=11,
            seq=99,
        ),
    ]

    projection = project_entity_state(
        evidence_units=evidence_units,
        facts=facts,
        conflicts=[],
        canon_decisions=[],
        campaign_id="longmont-c1",
    )
    attr = projection["entities"]["ent_the_wolf"]["attributes"]["physical_condition"]
    assert attr["selected_fact_id"] == "fact_old", "session 12 > session 11 regardless of seq"


def test_death_outcome_beats_fading_corruption_without_temporal_metadata() -> None:
    evidence_units = [
        _evidence(
            "evid_campaign_fades",
            layer="campaign",
            campaign_id="longmont-c1",
            source_class="observed_session_recap",
        ),
        _evidence(
            "evid_campaign_dead",
            layer="campaign",
            campaign_id="longmont-c1",
            source_class="observed_session_recap",
        ),
    ]
    facts = [
        _fact(
            "fact_the_wolf_physical_condition_9563b9aa57b3",
            "oily sheen in eyes fades",
            evidence_id="evid_campaign_fades",
        ),
        _fact(
            "fact_the_wolf_physical_condition_0bff1a76ba2e",
            "receives a killing blow (dies)",
            evidence_id="evid_campaign_dead",
        ),
    ]

    projection = project_entity_state(
        evidence_units=evidence_units,
        facts=facts,
        conflicts=[],
        canon_decisions=[],
        campaign_id="longmont-c1",
    )
    attr = projection["entities"]["ent_the_wolf"]["attributes"]["physical_condition"]
    assert attr["selected_fact_id"] == "fact_the_wolf_physical_condition_0bff1a76ba2e"

