"""Tests for taxonomy-backed predicate catalog."""

from __future__ import annotations

from src.graph_memory import identity_resolution as ir
from src.graph_memory.predicate_catalog import (
    V1_EXACT_PREDICATES,
    catalog_cross_check_issues,
    edge_predicate_family,
    exact_predicate_ids,
    predicate_family_for_type,
    predicate_family_ids,
    predicates_by_family,
    prompt_markdown,
    validate_edge_predicate,
)


def test_catalog_matches_identity_resolution_map():
    assert V1_EXACT_PREDICATES == ir.PREDICATE_FAMILY


def test_every_catalog_family_exists_in_taxonomy_registry():
    assert catalog_cross_check_issues() == []


def test_predicate_family_for_type_uses_registry_or_rel_prefix():
    assert predicate_family_for_type("parent_of") == "kinship"
    assert predicate_family_for_type("recognizes") == "rel:recognizes"


def test_exact_predicate_ids_are_sorted_and_non_empty():
    ids = exact_predicate_ids()
    assert ids == tuple(sorted(ids))
    assert "parent_of" in ids
    assert "associated_with" in ids


def test_predicates_by_family_groups_catalog():
    grouped = predicates_by_family()
    assert "kinship" in grouped
    assert "parent_of" in grouped["kinship"]
    assert "child_of" in grouped["kinship"]


def test_registry_predicate_family_ids_include_kinship():
    assert "kinship" in predicate_family_ids()


def test_validate_edge_predicate_detects_unknown_and_mismatch():
    assert validate_edge_predicate("recognizes", "kinship") == ["unknown_relationship_type"]
    assert validate_edge_predicate("parent_of", "social_relation") == ["relationship_family_mismatch"]
    assert validate_edge_predicate("parent_of", "kinship") == []


def test_edge_predicate_family_prefers_explicit_field():
    edge = {
        "relationship_type": "works_with",
        "predicate_family": "membership",
    }
    assert edge_predicate_family(edge) == "membership"


def test_prompt_markdown_lists_controlled_catalog():
    md = prompt_markdown()
    assert "Controlled edge predicates" in md
    assert "`parent_of`" in md
    assert "Do not invent verbs" in md
    assert "**kinship**" in md


def test_session_23_gold_predicates_are_in_catalog():
    # Idea 2: the v1 catalog must be a superset of the relationship verbs the
    # Session 23 gold fixture uses, otherwise the strict edge-pass enum makes
    # those gold edges impossible to emit (a self-inflicted recall ceiling).
    assert predicate_family_for_type("leads") == "authority"
    assert predicate_family_for_type("threatens") == "threat_relation"
    assert predicate_family_for_type("displaced_from") == "routing"
    ids = exact_predicate_ids()
    for verb in ("leads", "threatens", "displaced_from"):
        assert verb in ids
    # Widened families must still resolve in the taxonomy registry.
    assert catalog_cross_check_issues() == []
