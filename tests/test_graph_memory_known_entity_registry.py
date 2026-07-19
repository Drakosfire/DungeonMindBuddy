"""Tests for corpus-agnostic known-entity registry loading and roster scoping."""

from __future__ import annotations

from src.graph_memory.extraction.known_entity_registry import (
    KnownEntity,
    KnownEntityRegistry,
    build_known_entity_registry,
    normalize_match_surface,
    resolve_roster_session_key,
)


def test_normalize_match_surface_unicode_case_punctuation() -> None:
    assert normalize_match_surface("Caelynn!") == normalize_match_surface("caelynn")
    assert normalize_match_surface("Baer\u2019grom") == normalize_match_surface("Baer'grom")
    assert normalize_match_surface("  Eph Anna  ") == normalize_match_surface("eph anna")


def test_c2_registry_loads_pcs_and_companions() -> None:
    registry = build_known_entity_registry("longmont-c2", 22)
    slugs = {e.slug for e in registry.entities}
    assert {"baergrom", "bonogo", "caelynn", "ephanna", "karsemine", "stafl"} <= slugs
    assert "thrin_branchborn" in slugs or "captain_lysandra_ironveil" in slugs
    caelynn = registry.by_slug()["caelynn"]
    assert caelynn.kind == "pc"
    assert caelynn.canonical_entity_id.startswith("node:")
    assert caelynn.match_terms


def test_c1_session_3_carries_forward_roster() -> None:
    registry = build_known_entity_registry("longmont-c1", 3)
    assert registry.roster_carry_forward is True
    assert registry.roster_session_key == "1"
    assert {e.slug for e in registry.entities} >= {
        "baergrom",
        "bonogo",
        "caelynn",
        "ephanna",
        "karsemine",
        "stafl",
    }


def test_cross_campaign_same_slug_is_scoped() -> None:
    c1 = build_known_entity_registry("longmont-c1", 1)
    c2 = build_known_entity_registry("longmont-c2", 22)
    assert c1.campaign_id != c2.campaign_id
    c1_caelynn = c1.by_slug()["caelynn"]
    c2_caelynn = c2.by_slug()["caelynn"]
    # Same slug / node_id shape is allowed; campaign hub paths must stay isolated.
    assert c1_caelynn.canonical_entity_id == c2_caelynn.canonical_entity_id == "node:caelynn"
    assert "Campaign 1" in c1_caelynn.hub_rel_path
    assert "Campaign 2" in c2_caelynn.hub_rel_path
    assert c1_caelynn.hub_rel_path != c2_caelynn.hub_rel_path


def test_resolve_roster_session_key_exact_and_carry_forward() -> None:
    registry = {
        "session_pc_rosters": {
            "20": ["baergrom"],
            "22": ["baergrom", "caelynn"],
        }
    }
    assert resolve_roster_session_key(registry, "22") == ("22", False)
    assert resolve_roster_session_key(registry, "21") == ("20", True)
    assert resolve_roster_session_key(registry, "19") == (None, False)


def test_manual_registry_preserves_injected_entities() -> None:
    entity = KnownEntity(
        slug="hero_a",
        kind="pc",
        display_name="Hero A",
        canonical_entity_id="node:hero-a",
        aliases=("HA",),
        hub_rel_path="npcs/hero_a/README.md",
        hub_resolved=True,
        corpus_ref={"type": "character", "ref_id": "hero_a", "resolution": "resolved"},
        match_terms=(("Hero A", "canonical"), ("HA", "alias")),
    )
    registry = KnownEntityRegistry(
        campaign_id="other-corpus",
        session_key="5",
        roster_session_key="5",
        roster_carry_forward=False,
        registry_relpath="other/_party_registry.json",
        entities=(entity,),
    )
    assert registry.by_canonical_id()["node:hero-a"].display_name == "Hero A"
