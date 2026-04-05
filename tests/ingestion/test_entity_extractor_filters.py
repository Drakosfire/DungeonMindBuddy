from __future__ import annotations

import pytest

from src.ingestion.entity_extractor import (
    _build_entity_system_prompt,
    _build_entity_user_prompt,
    _build_recap_system_prompt,
    _build_recap_user_prompt,
    _is_plausible_entity_name,
    _relevant_known_entities,
    _resolve_source_profile,
    _SESSION_RECAP_PREFIX,
    _WORLDBUILDING_PREFIX,
)


def test_rescue_single_token_suppressed_on_non_mirathorn_text() -> None:
    """Regression: 'rescue' is low-signal for Mirathorn junk; non-rescue campaigns may need it.

    This documents current filter behavior so a future corpus-specific split is intentional.
    """
    assert not _is_plausible_entity_name(
        display_name="Rescue",
        entity_class="group",
        source_text="We deploy the Rescue team to the eastern ridge.",
        known_lookup={},
        mention_count=3,
    )


def test_distinctive_name_passes_same_heuristics() -> None:
    assert _is_plausible_entity_name(
        display_name="Kythwood",
        entity_class="place",
        source_text="The party enters Kythwood before dawn.",
        known_lookup={},
        mention_count=3,
    )


@pytest.mark.parametrize("pronoun", ["his", "her", "He", "THEY", "Him", "it", "them"])
def test_pronouns_rejected(pronoun: str) -> None:
    assert not _is_plausible_entity_name(
        display_name=pronoun,
        entity_class="actor",
        source_text=f"Then {pronoun} attacked the dragon.",
        known_lookup={},
        mention_count=10,
    )


def test_sentence_fragment_rejected() -> None:
    long_name = "Players can choose to pursue or stay to secure the council chamber"
    assert not _is_plausible_entity_name(
        display_name=long_name,
        entity_class="concept",
        source_text=f"Some context. {long_name}. More context.",
        known_lookup={},
        mention_count=5,
    )


def test_name_at_length_boundary_accepted() -> None:
    name = "A" * 60
    assert _is_plausible_entity_name(
        display_name=name,
        entity_class="actor",
        source_text=f"The mighty {name} rides forth.",
        known_lookup={},
        mention_count=3,
    )


def test_name_over_length_boundary_rejected() -> None:
    name = "A" * 61
    assert not _is_plausible_entity_name(
        display_name=name,
        entity_class="actor",
        source_text=f"The mighty {name} rides forth.",
        known_lookup={},
        mention_count=3,
    )


class TestRelevantKnownEntities:
    def test_filters_to_text_present_entities(self) -> None:
        known = [
            {"entity_id": "ent_mirathorn", "display_name": "Mirathorn", "aliases": ["The City"]},
            {"entity_id": "ent_kythwood", "display_name": "Kythwood", "aliases": []},
            {"entity_id": "ent_merril", "display_name": "Merril Tealeaf", "aliases": ["Merril"]},
        ]
        result = _relevant_known_entities(known, "The guards of Mirathorn patrol the walls.")
        assert len(result) == 1
        assert result[0]["entity_id"] == "ent_mirathorn"

    def test_caps_aliases_to_max(self) -> None:
        known = [
            {
                "entity_id": "ent_x",
                "display_name": "Mirathorn",
                "aliases": ["alias_very_long_one", "al", "alias_medium", "z_longest_alias_name_here"],
            },
        ]
        result = _relevant_known_entities(known, "The city of Mirathorn.")
        assert len(result) == 1
        assert len(result[0]["aliases"]) == 3
        assert result[0]["aliases"] == sorted(known[0]["aliases"], key=len)[:3]

    def test_skips_short_display_names(self) -> None:
        known = [
            {"entity_id": "ent_it", "display_name": "It", "aliases": []},
            {"entity_id": "ent_ok", "display_name": "Ok", "aliases": []},
        ]
        result = _relevant_known_entities(known, "It was Ok to proceed.")
        assert len(result) == 0

    def test_empty_known_returns_empty(self) -> None:
        result = _relevant_known_entities([], "Some text about Mirathorn.")
        assert result == []

    def test_case_insensitive_matching(self) -> None:
        known = [
            {"entity_id": "ent_wolf", "display_name": "The Wolf", "aliases": []},
        ]
        result = _relevant_known_entities(known, "They cornered the wolf in the sewers.")
        assert len(result) == 1


class TestResolveSourceProfile:
    def test_observed_session_recap(self) -> None:
        unit = {"source_class": "observed_session_recap", "canon_layer": "campaign"}
        assert _resolve_source_profile(unit) == "session_recap"

    def test_world_canon_layer(self) -> None:
        unit = {"source_class": "seed_reference", "canon_layer": "world"}
        assert _resolve_source_profile(unit) == "worldbuilding"

    def test_planning_document(self) -> None:
        unit = {"source_class": "planning_document", "canon_layer": "campaign"}
        assert _resolve_source_profile(unit) == "worldbuilding"

    def test_seed_reference_no_canon(self) -> None:
        unit = {"source_class": "seed_reference"}
        assert _resolve_source_profile(unit) == "worldbuilding"

    def test_ledger_or_dossier(self) -> None:
        unit = {"source_class": "ledger_or_dossier", "canon_layer": "campaign"}
        assert _resolve_source_profile(unit) == "npc_dossier"

    def test_empty_unit_defaults_worldbuilding(self) -> None:
        assert _resolve_source_profile({}) == "worldbuilding"

    def test_other_source_class_defaults_worldbuilding(self) -> None:
        unit = {"source_class": "other", "canon_layer": "campaign"}
        assert _resolve_source_profile(unit) == "worldbuilding"

    def test_recap_takes_precedence_over_world_layer(self) -> None:
        unit = {"source_class": "observed_session_recap", "canon_layer": "world"}
        assert _resolve_source_profile(unit) == "session_recap"


class TestBuildPromptProfileDispatch:
    def test_worldbuilding_prompt_contains_prefix(self) -> None:
        unit = {"text": "Mirathorn is a city.", "source_class": "seed_reference", "canon_layer": "world"}
        user = _build_entity_user_prompt(unit, [])
        assert _WORLDBUILDING_PREFIX in user
        assert _SESSION_RECAP_PREFIX not in user
        assert "Source profile: worldbuilding" in user

    def test_session_recap_user_prompt_contains_prefix(self) -> None:
        unit = {"text": "The party fought wolves.", "source_class": "observed_session_recap", "canon_layer": "campaign"}
        user = _build_entity_user_prompt(unit, [])
        assert _SESSION_RECAP_PREFIX in user
        assert _WORLDBUILDING_PREFIX not in user
        assert "Source profile: session_recap" in user

    def test_shared_ontology_present_in_standard_and_recap_system_prompts(self) -> None:
        entity_sys = _build_entity_system_prompt()
        recap_sys = _build_recap_system_prompt()
        for required in ["entity_class must be one of", "Explicit excludes", "decision must be entity or exclude"]:
            assert required in entity_sys, f"Missing '{required}' in entity system prompt"
            assert required in recap_sys, f"Missing '{required}' in recap system prompt"
