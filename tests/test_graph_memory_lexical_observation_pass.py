from __future__ import annotations

import json

import pytest

from src.graph_memory.vocabulary import (
    LexicalObservation,
    VocabularySourceSpan,
    build_lexical_observations_from_spans,
    extract_candidate_surfaces,
    infer_observed_kind_hint,
    normalize_observed_text,
    observations_to_artifact_payload,
)


def test_normalize_observed_text_is_deterministic():
    assert normalize_observed_text("  The North Gate Defense  ") == "the north gate defense"
    assert normalize_observed_text("Mireward.") == "mireward"
    assert normalize_observed_text("Mirror-Court") == "mirror-court"


def test_candidate_surfaces_are_conservative_and_ordered():
    text = (
        "The party reached Mireward before the North Gate Defense. "
        "Then the Mireward Council called Questionable Company."
    )

    surfaces = extract_candidate_surfaces(text)

    assert surfaces == ["Mireward", "North Gate Defense", "Mireward Council", "Questionable Company"]
    for rejected in ["The", "Then", "North", "Gate", "Defense"]:
        assert rejected not in surfaces


def test_kind_hints_classify_combat_encounter_collective_and_place():
    assert infer_observed_kind_hint("North Gate Defense") == "combat_encounter"
    assert infer_observed_kind_hint("Mireward Council") == "collective"
    assert infer_observed_kind_hint("Mireward", "The party reached Mireward before the storm.") == "place"


def test_pass_builds_lexical_observations_from_source_spans():
    span = VocabularySourceSpan(
        source_artifact_id="artifact:test-session",
        source_span_ref_id="span:test:001",
        text="The party reached Mireward before the North Gate Defense. The Mireward Council watched.",
        line_start=10,
        line_end=11,
    )

    result = build_lexical_observations_from_spans([span])
    by_normalized = {observation.normalized_text: observation for observation in result.observations}

    assert "mireward" in by_normalized
    assert "north gate defense" in by_normalized
    assert "mireward council" in by_normalized
    assert by_normalized["north gate defense"].observed_kind_hint == "combat_encounter"
    assert by_normalized["mireward council"].observed_kind_hint == "collective"

    for observation in result.observations:
        assert isinstance(observation, LexicalObservation)
        assert len(observation.evidence_refs) == 1
        evidence_ref = observation.evidence_refs[0]
        assert evidence_ref.source_artifact_id == "artifact:test-session"
        assert evidence_ref.source_span_ref_id == "span:test:001"


def test_observation_ids_are_deterministic():
    span = VocabularySourceSpan(
        source_artifact_id="artifact:test-session",
        source_span_ref_id="span:test:001",
        text="The party reached Mireward before the North Gate Defense. The Mireward Council watched.",
    )

    first = build_lexical_observations_from_spans([span])
    second = build_lexical_observations_from_spans([span])

    assert [obs.observation_id for obs in first.observations] == [obs.observation_id for obs in second.observations]


def test_empty_spans_are_skipped_and_diagnosed():
    result = build_lexical_observations_from_spans(
        [VocabularySourceSpan(source_artifact_id="artifact:empty", source_span_ref_id="span:empty", text="  \n  ")]
    )

    assert result.observations == []
    assert result.diagnostics["skipped_empty_span_count"] == 1


def test_diagnostics_are_json_serializable_without_full_source_text():
    full_sentence = "The party reached Mireward before the North Gate Defense."
    result = build_lexical_observations_from_spans(
        [VocabularySourceSpan(source_artifact_id="artifact:test-session", text=full_sentence)]
    )

    restored = json.loads(json.dumps(result.diagnostics))

    assert restored["observation_count"] == 2
    assert "observed_kind_counts" in restored
    assert full_sentence not in json.dumps(restored)


def test_invalid_line_range_fails_clearly():
    with pytest.raises(ValueError, match="line_end"):
        build_lexical_observations_from_spans(
            [VocabularySourceSpan(source_artifact_id="artifact:test-session", text="Mireward", line_start=12, line_end=10)]
        )


def test_observations_can_become_artifact_payloads():
    result = build_lexical_observations_from_spans(
        [VocabularySourceSpan(source_artifact_id="artifact:test-session", text="Mireward Council watched Lysandra.")]
    )

    payload = observations_to_artifact_payload(result.observations)
    restored = [LexicalObservation.from_dict(item) for item in payload]

    assert restored == result.observations
