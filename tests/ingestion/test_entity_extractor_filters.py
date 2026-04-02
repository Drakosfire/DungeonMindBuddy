from __future__ import annotations

import pytest

from src.ingestion.entity_extractor import (
    _is_plausible_entity_name,
    _relevant_known_entities,
)


def test_rescue_single_token_suppressed_on_non_mirathorn_text() -> None:
    """Regression: 'rescue' is low-signal for Mirathorn junk; non-rescue campaigns may need it.

    This documents current filter behavior so a future corpus-specific split is intentional.
    """
    assert not _is_plausible_entity_name(
        display_name="Rescue",
        entity_type="faction",
        source_text="We deploy the Rescue team to the eastern ridge.",
        known_lookup={},
        mention_count=3,
    )


def test_distinctive_name_passes_same_heuristics() -> None:
    assert _is_plausible_entity_name(
        display_name="Kythwood",
        entity_type="location",
        source_text="The party enters Kythwood before dawn.",
        known_lookup={},
        mention_count=3,
    )


@pytest.mark.parametrize("pronoun", ["his", "her", "He", "THEY", "Him", "it", "them"])
def test_pronouns_rejected(pronoun: str) -> None:
    assert not _is_plausible_entity_name(
        display_name=pronoun,
        entity_type="npc",
        source_text=f"Then {pronoun} attacked the dragon.",
        known_lookup={},
        mention_count=10,
    )


def test_sentence_fragment_rejected() -> None:
    long_name = "Players can choose to pursue or stay to secure the council chamber"
    assert not _is_plausible_entity_name(
        display_name=long_name,
        entity_type="other",
        source_text=f"Some context. {long_name}. More context.",
        known_lookup={},
        mention_count=5,
    )


def test_name_at_length_boundary_accepted() -> None:
    name = "A" * 60
    assert _is_plausible_entity_name(
        display_name=name,
        entity_type="npc",
        source_text=f"The mighty {name} rides forth.",
        known_lookup={},
        mention_count=3,
    )


def test_name_over_length_boundary_rejected() -> None:
    name = "A" * 61
    assert not _is_plausible_entity_name(
        display_name=name,
        entity_type="npc",
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
