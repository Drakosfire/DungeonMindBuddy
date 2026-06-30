from __future__ import annotations

import json

import pytest

from src.graph_memory.vocabulary import (
    EvidenceRef,
    LexicalObservation,
    SourceArtifactRef,
    VocabularyEntry,
    VocabularySeedScopePolicy,
    VocabularySourceSpan,
    build_lexical_observations_from_spans,
    canonical_label_from_observations,
    compile_vocabulary_seed_entries,
    seed_entries_to_artifact_payload,
)


def _observations_from_text(text: str, artifact_id: str = "artifact:test-session") -> list[LexicalObservation]:
    return build_lexical_observations_from_spans(
        [VocabularySourceSpan(source_artifact_id=artifact_id, source_span_ref_id="span:test:001", text=text)]
    ).observations


def test_compiles_campaign_seed_entries_from_lexical_observations():
    observations = _observations_from_text(
        "The party reached Mireward before the North Gate Defense. The Mireward Council watched."
    )

    result = compile_vocabulary_seed_entries(
        observations,
        policy=VocabularySeedScopePolicy(default_scope="campaign", campaign_id="campaign:test", world_id="world:test"),
    )

    assert result.world_entries == []
    by_label = {entry.canonical_label: entry for entry in result.campaign_entries}
    assert {"Mireward", "North Gate Defense", "Mireward Council"} <= set(by_label)
    assert by_label["North Gate Defense"].entity_kind == "combat_encounter"
    assert by_label["Mireward Council"].entity_kind == "collective"
    for entry in result.campaign_entries:
        assert entry.status == "candidate"
        assert entry.authority == "derived_memory"
        assert entry.global_node_id is None
        assert entry.aliases == []
        assert entry.candidate_aliases == []


def test_separates_world_and_campaign_entries_by_source_artifact_domain():
    source_artifacts = [
        SourceArtifactRef(
            source_artifact_id="artifact:world",
            source_domain="worldbuilding",
            scope="world",
            world_id="world:test",
            authority="manual_seed",
        ),
        SourceArtifactRef(
            source_artifact_id="artifact:recap",
            source_domain="recap",
            scope="campaign",
            campaign_id="campaign:test",
            world_id="world:test",
            session_id="session:test-01",
            authority="manual_seed",
        ),
    ]
    observations = _observations_from_text("Mireward waited.", "artifact:world") + _observations_from_text(
        "The North Gate Defense began.", "artifact:recap"
    )

    result = compile_vocabulary_seed_entries(
        observations,
        source_artifacts=source_artifacts,
        policy=VocabularySeedScopePolicy(default_scope="campaign", campaign_id="campaign:test", world_id="world:test"),
    )

    assert [entry.canonical_label for entry in result.world_entries] == ["Mireward"]
    assert [entry.canonical_label for entry in result.campaign_entries] == ["North Gate Defense"]
    assert result.campaign_entries[0].campaign_id == "campaign:test"
    assert result.campaign_entries[0].world_id == "world:test"
    assert result.world_entries[0].world_id == "world:test"


def test_deterministic_vocab_ids():
    observations = _observations_from_text("Mireward waited. The North Gate Defense began.")
    policy = VocabularySeedScopePolicy(default_scope="campaign", campaign_id="campaign:test", world_id="world:test")

    first = compile_vocabulary_seed_entries(observations, policy=policy)
    second = compile_vocabulary_seed_entries(observations, policy=policy)

    assert [entry.vocab_id for entry in first.campaign_entries] == [entry.vocab_id for entry in second.campaign_entries]


def test_groups_duplicate_observations_and_preserves_evidence():
    observations = _observations_from_text("Mireward waited. Mireward watched. The party reached Mireward.")

    result = compile_vocabulary_seed_entries(
        observations,
        policy=VocabularySeedScopePolicy(default_scope="campaign", campaign_id="campaign:test", world_id="world:test"),
    )

    mireward_entries = [entry for entry in result.campaign_entries if entry.canonical_label == "Mireward"]
    assert len(mireward_entries) == 1
    entry = mireward_entries[0]
    assert entry.source_refs == ["artifact:test-session"]
    assert len(entry.evidence_refs) == 1
    assert entry.entity_kind_confidence == 0.75


def test_canonical_label_tie_breaks_by_frequency_then_first_occurrence():
    observations = [
        LexicalObservation(
            observation_id=f"obs:{index}",
            source_artifact_id="artifact:test",
            surface_text=surface,
            normalized_text=surface.lower(),
            evidence_refs=[EvidenceRef(source_artifact_id="artifact:test")],
        )
        for index, surface in enumerate(["Mireward", "Mireward", "Mireward town", "Mireward town"])
    ]

    assert canonical_label_from_observations(observations) == "Mireward"


def test_diagnostics_are_json_serializable_without_source_text():
    full_sentence = "The party reached Mireward before the North Gate Defense."
    result = compile_vocabulary_seed_entries(
        _observations_from_text(full_sentence),
        policy=VocabularySeedScopePolicy(default_scope="campaign", campaign_id="campaign:test", world_id="world:test"),
    )

    restored = json.loads(json.dumps(result.diagnostics))

    assert restored["observation_count"] == 2
    assert "warnings" in restored
    assert full_sentence not in json.dumps(restored)


def test_seed_entries_can_become_artifact_payloads():
    result = compile_vocabulary_seed_entries(
        _observations_from_text("Mireward Council watched Lysandra."),
        policy=VocabularySeedScopePolicy(default_scope="campaign", campaign_id="campaign:test", world_id="world:test"),
    )

    payload = seed_entries_to_artifact_payload(result.campaign_entries)
    restored = [VocabularyEntry.from_dict(item) for item in payload]

    assert restored == result.campaign_entries


def test_policy_validation_fails_clearly():
    with pytest.raises(ValueError, match="default_scope"):
        VocabularySeedScopePolicy(default_scope="bad").validate()


def test_no_alias_or_merge_decisions_are_inferred():
    result = compile_vocabulary_seed_entries(
        _observations_from_text("Mireward Council watched the North Gate Defense."),
        policy=VocabularySeedScopePolicy(default_scope="campaign", campaign_id="campaign:test", world_id="world:test"),
    )

    for entry in result.campaign_entries:
        assert entry.aliases == []
        assert entry.candidate_aliases == []
        assert entry.negative_aliases == []
        assert entry.do_not_merge_with == []
        assert entry.global_node_id is None
        assert entry.candidate_global_node_ids == []
