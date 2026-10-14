import pytest
from src.graph_memory.extraction.worldbuilding_gazetteer_profile import (
    GAZETTEER_PROFILE, validate_gazetteer_candidate_bounds,
)
from src.graph_memory.extraction.worldbuilding_profile_catalog import PUBLISHABLE_WORLDBUILDING_PROFILES


def test_closed_publication_profiles_preserve_pilot_and_exact_gazetteer_version():
    assert set(PUBLISHABLE_WORLDBUILDING_PROFILES) == {
        "worldbuilding_shepherds_flock_v0@0.1", "worldbuilding_gazetteer_v1@1.0"}
    assert "worldbuilding_gazetteer_v1@2.0" not in PUBLISHABLE_WORLDBUILDING_PROFILES
    assert "worldbuilding_plumbing_v0@0.1" not in PUBLISHABLE_WORLDBUILDING_PROFILES


def test_definition_pass_has_no_played_or_individual_invention():
    definitions = next(p for p in GAZETTEER_PROFILE.node_passes if p.pass_id == "definition_pass")
    assert definitions.allowed_node_types == ("creature", "event")
    for phrase in ["KIND definitions", "not individual", "never a played episode", "defer unplayed"]:
        assert phrase in definitions.instruction
    assert GAZETTEER_PROFILE.beat_pass is None
    assert not GAZETTEER_PROFILE.enable_party_participation_attachment
    assert GAZETTEER_PROFILE.default_semantic_state["canon_state"] == "worldbuilding_draft"


@pytest.mark.parametrize("kind", ["creature", "event"])
def test_named_definitions_are_admitted_with_source_evidence(kind):
    assert not validate_gazetteer_candidate_bounds({"session_id": None, "nodes": [
        {"node_type": kind, "evidence_refs": [{"source_span_ref_id": "span", "anchor_quotes": ["source"]}]}]})


@pytest.mark.parametrize("graph", [
    {"session_id": "session-1"}, {"nodes": [{"node_type": "item", "evidence_refs": [{}]}]},
    {"nodes": [{"node_type": "creature", "evidence_refs": []}]}, {"beats": [{}]},
])
def test_out_of_scope_or_unsupported_candidates_reject(graph):
    assert validate_gazetteer_candidate_bounds(graph)
