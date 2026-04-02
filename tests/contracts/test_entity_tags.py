from __future__ import annotations

from src.contracts.entity_tags import normalize_entity_tags


def test_normalize_entity_tags_dedupes_and_snake_cases() -> None:
    assert normalize_entity_tags(["Deity", "  Deity  ", "patron_entity", "Patron Entity"]) == [
        "deity",
        "patron_entity",
    ]


def test_normalize_entity_tags_respects_max() -> None:
    raw = [f"t{i}" for i in range(10)]
    assert len(normalize_entity_tags(raw, max_tags=3)) == 3
