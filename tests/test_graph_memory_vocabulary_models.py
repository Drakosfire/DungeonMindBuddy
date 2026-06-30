from __future__ import annotations

import json

import pytest

from src.graph_memory.vocabulary import (
    AliasCandidate,
    ContextVocabularyPacket,
    ContainmentHint,
    DoNotMergeDecision,
    EvidenceRef,
    LexicalObservation,
    VocabularyEntry,
)


def _round_trip(model):
    payload = json.loads(json.dumps(model.to_dict()))
    return type(model).from_dict(payload)


def test_evidence_ref_validates_and_serializes():
    evidence = EvidenceRef(
        source_artifact_id="artifact:session-22",
        source_span_ref_id="span:1",
        quote="A short quote.",
        line_start=3,
        line_end=5,
        confidence=0.75,
    )

    assert _round_trip(evidence) == evidence

    with pytest.raises(ValueError, match="line_end"):
        EvidenceRef(source_artifact_id="artifact:session-22", line_start=5, line_end=4)

    with pytest.raises(ValueError, match="confidence"):
        EvidenceRef(source_artifact_id="artifact:session-22", confidence=1.5)


def test_lexical_observation_round_trips_with_evidence_ref():
    observation = LexicalObservation(
        observation_id="obs:1",
        source_artifact_id="artifact:session-22",
        surface_text="The Mirror Court",
        normalized_text="mirror court",
        observed_kind_hint="collective",
        evidence_refs=[EvidenceRef(source_artifact_id="artifact:session-22", source_span_ref_id="span:7")],
        confidence=0.8,
    )

    restored = _round_trip(observation)

    assert restored.surface_text == "The Mirror Court"
    assert restored.normalized_text == "mirror court"
    assert restored.observed_kind_hint == "collective"
    assert restored.evidence_refs == observation.evidence_refs


def test_vocabulary_entry_dedupes_aliases_without_collapsing_alias_lists():
    entry = VocabularyEntry(
        vocab_id="vocab:mirror-court",
        canonical_label="Mirror Court",
        entity_kind="collective",
        scope="campaign",
        campaign_id="campaign:longmont-c2",
        aliases=["Mirror Court", "the Mirror Court", "the Mirror Court", " Mirror Court "],
        candidate_aliases=["court", "court"],
        negative_aliases=["Mirror Lake", "Mirror Lake"],
    )

    assert entry.aliases == ["the Mirror Court"]
    assert entry.candidate_aliases == ["court"]
    assert entry.negative_aliases == ["Mirror Lake"]


def test_vocabulary_entry_rejects_invalid_global_node_state():
    with pytest.raises(ValueError, match="global_node_id"):
        VocabularyEntry(
            vocab_id="vocab:storm",
            canonical_label="Converging hail storm",
            entity_kind="phenomenon",
            scope="campaign",
            campaign_id="campaign:longmont-c2",
            global_node_id="global:storm",
            candidate_global_node_ids=["global:storm"],
        )


def test_alias_candidate_preserves_deduped_risk_flags():
    candidate = AliasCandidate(
        alias_candidate_id="alias:1",
        left_surface="Mireward Reach",
        right_surface="Mireward polity",
        confidence=0.4,
        risk_flags=["place_vs_polity", "place_vs_polity", "cross_type"],
    )

    assert candidate.risk_flags == ["place_vs_polity", "cross_type"]
    assert candidate.status == "candidate"
    assert candidate.status != "accepted"


def test_do_not_merge_decision_can_be_generated_but_unreviewed():
    decision = DoNotMergeDecision(
        decision_id="dnm:1",
        left_vocab_id="vocab:person-frank",
        right_vocab_id="vocab:faction-frank",
        status="needs_review",
        source="generated_collision_warning",
    )

    restored = _round_trip(decision)

    assert restored.reviewed_by is None
    assert restored.status == "needs_review"

    with pytest.raises(ValueError, match="must differ"):
        DoNotMergeDecision(decision_id="dnm:bad", left_vocab_id="vocab:x", right_vocab_id="vocab:x")


def test_context_vocabulary_packet_round_trips_nested_hints_and_dedupes_strings():
    alias_hint = AliasCandidate(alias_candidate_id="alias:accepted", left_surface="Lysandra", right_surface="Captain Lysandra", status="accepted")
    candidate_alias_hint = AliasCandidate(alias_candidate_id="alias:candidate", left_surface="The Guard", right_surface="City Guard")
    do_not_merge_hint = DoNotMergeDecision(decision_id="dnm:1", left_vocab_id="vocab:reach-place", right_vocab_id="vocab:reach-polity")
    containment_hint = ContainmentHint(hint_id="contain:1", child_label="South Gate", parent_label="Mireward")
    packet = ContextVocabularyPacket(
        packet_id="packet:1",
        scope="campaign",
        world_entry_refs=["vocab:world-mireward", "vocab:world-mireward"],
        campaign_entry_refs=["vocab:captain-lysandra"],
        known_names=["Mireward", "Mireward"],
        alias_hints=[alias_hint],
        candidate_alias_hints=[candidate_alias_hint],
        do_not_merge_hints=[do_not_merge_hint],
        containment_hints=[containment_hint],
        type_hints={"The Guard": "collective"},
        predicate_hints={"Mireward": ["located_in", "located_in"]},
        combat_encounter_hints=["warehouse ambush", "warehouse ambush"],
    )

    restored = _round_trip(packet)

    assert restored.world_entry_refs == ["vocab:world-mireward"]
    assert restored.known_names == ["Mireward"]
    assert restored.alias_hints == [alias_hint]
    assert restored.candidate_alias_hints == [candidate_alias_hint]
    assert restored.do_not_merge_hints == [do_not_merge_hint]
    assert restored.containment_hints == [containment_hint]
    assert restored.type_hints == {"The Guard": "collective"}
    assert restored.predicate_hints == {"Mireward": ["located_in"]}
    assert restored.combat_encounter_hints == ["warehouse ambush"]
