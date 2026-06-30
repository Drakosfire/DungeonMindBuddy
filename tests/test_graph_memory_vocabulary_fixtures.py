from __future__ import annotations

import json
from pathlib import Path

from src.graph_memory.vocabulary import (
    AliasCandidate,
    ContextVocabularyPacket,
    ContainmentHint,
    DoNotMergeDecision,
    LexicalObservation,
    SourceArtifactRef,
    VocabularyEntry,
)

FIXTURE_DIR = Path("evals/graph_memory_layer/examples/vocabulary_contract_fixtures")


def load_json(name: str):
    return json.loads((FIXTURE_DIR / name).read_text(encoding="utf-8"))


def round_trip(model):
    return type(model).from_dict(json.loads(json.dumps(model.to_dict())))


def assert_round_trip(model) -> None:
    restored = round_trip(model)
    assert restored == model
    assert restored.to_dict() == model.to_dict()


def test_manifest_is_internally_consistent():
    manifest = load_json("manifest.json")

    assert manifest["schema"] == "dmb_vocabulary_contract_fixture_manifest_v1"
    assert manifest["authority_class"] == "vocabulary_contract_fixture"
    assert manifest["candidate_graph_comparison"] is False

    for fixture_file in manifest["files"]:
        path = FIXTURE_DIR / fixture_file["path"]
        assert path.exists(), fixture_file["path"]
        payload = load_json(fixture_file["path"])
        count = len(payload) if isinstance(payload, list) else 1
        assert count == fixture_file["count"]


def test_source_artifact_fixtures_round_trip():
    for payload in load_json("source_artifacts.json"):
        model = SourceArtifactRef.from_dict(payload)
        assert_round_trip(model)


def test_lexical_observation_fixtures_round_trip():
    observations = [LexicalObservation.from_dict(payload) for payload in load_json("lexical_observations.json")]

    assert any(observation.observed_kind_hint == "combat_encounter" for observation in observations)
    for observation in observations:
        assert_round_trip(observation)


def test_vocabulary_entry_fixtures_round_trip():
    entries = [VocabularyEntry.from_dict(payload) for payload in load_json("vocabulary_entries.json")]

    assert any(entry.entity_kind == "combat_encounter" for entry in entries)
    assert any(entry.entity_kind == "place" and entry.do_not_merge_with for entry in entries)
    for entry in entries:
        assert_round_trip(entry)


def test_alias_and_do_not_merge_fixtures_preserve_review_state():
    aliases = [AliasCandidate.from_dict(payload) for payload in load_json("alias_candidates.json")]

    assert any(alias.status == "needs_review" for alias in aliases)
    assert any({"cross_type", "place_vs_polity"} & set(alias.risk_flags) for alias in aliases)
    for alias in aliases:
        assert_round_trip(alias)

    decisions = [DoNotMergeDecision.from_dict(payload) for payload in load_json("do_not_merge_decisions.json")]
    assert all(decision.reviewed_by is None for decision in decisions)
    for decision in decisions:
        assert_round_trip(decision)


def test_containment_and_packet_fixtures_round_trip():
    hints = [ContainmentHint.from_dict(payload) for payload in load_json("containment_hints.json")]
    for hint in hints:
        assert_round_trip(hint)

    packet = ContextVocabularyPacket.from_dict(load_json("context_vocabulary_packet.json"))

    assert packet.combat_encounter_hints == ["North Gate Defense"]
    assert packet.type_hints["North Gate Defense"] == "combat_encounter"
    assert packet.do_not_merge_hints
    assert packet.candidate_alias_hints
    assert_round_trip(packet)
