from __future__ import annotations

from src.contracts.entity_taxonomy import normalize_semantic_facets


def test_normalize_semantic_facets_accepts_controlled_and_domain_tokens() -> None:
    facets = normalize_semantic_facets(
        ["Deity", "ritual", "domain:Eldyrwild Cult", "unknown_token", "deity"]
    )
    assert facets == ["deity", "ritual", "domain:eldyrwild_cult"]


def test_normalize_semantic_facets_respects_max() -> None:
    raw = ["deity", "ritual", "festival", "theme"]
    assert len(normalize_semantic_facets(raw, max_facets=2)) == 2

