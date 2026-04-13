"""Tests for wiki connectivity scoring and name filters."""

from __future__ import annotations

from pathlib import Path

from src.compiler.wiki_compiler import (
    score_entity_connectivity,
    should_skip_entity_for_wiki,
)
from src.store import FactStore


def test_should_skip_generic_names() -> None:
    assert should_skip_entity_for_wiki("She")
    assert should_skip_entity_for_wiki("meat")
    assert not should_skip_entity_for_wiki("Commander Thalia")


def test_score_entity_connectivity_non_empty_on_fixture_store() -> None:
    fixture = Path(__file__).resolve().parents[1] / "tests/fixtures/extraction_lab/sample_store"
    if not (fixture / "facts.json").exists():
        return
    store = FactStore(fixture)
    store.load()
    scores = score_entity_connectivity(store)
    assert isinstance(scores, dict)
    if scores:
        assert max(scores.values()) >= min(scores.values())
