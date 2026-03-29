from __future__ import annotations

from src.ingestion.entity_extractor import _is_plausible_entity_name


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
