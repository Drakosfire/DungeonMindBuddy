"""Tests for corpus-agnostic known-entity registry loading and roster scoping."""

from __future__ import annotations

from src.graph_memory.extraction.known_entity_registry import (
    KnownEntity,
    KnownEntityRegistry,
    build_known_entity_registry,
    extend_known_entity_registry,
    known_entities_from_world_graph,
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


def _world_graph_fixture() -> dict:
    return {
        "nodes": {
            "loc_mireward_gate": {
                "node_id": "loc_mireward_gate",
                "label": "Mireward Gate",
                "kind": "location",
                "aliases": ["the Gate"],
                "state": {"campaign_scope": "longmont-c2"},
            },
            "npc_edge_survivors": {
                "node_id": "npc_edge_survivors",
                "label": "Edge Survivors",
                "kind": "group",
                "aliases": [],
                "state": {"campaign_scope": "longmont-c2"},
            },
            "thread_weave_distortion": {
                "node_id": "thread_weave_distortion",
                "label": "Weave Distortion",
                "kind": "thread",
                "state": {"campaign_scope": "longmont-c2"},
            },
            "loc_other_campaign": {
                "node_id": "loc_other_campaign",
                "label": "Farhold",
                "kind": "location",
                "state": {"campaign_scope": "longmont-c1"},
            },
            "party_node": {
                "node_id": "node:caelynn",
                "label": "Caelynn",
                "kind": "pc",
                "state": {"campaign_scope": "longmont-c2"},
            },
        },
        "aliases": {
            "Old Gate": "loc_mireward_gate",
        },
    }


def test_world_graph_loader_filters_kinds_and_scopes() -> None:
    entities = known_entities_from_world_graph(
        _world_graph_fixture(),
        campaign_scopes=frozenset({"longmont-c2"}),
    )
    ids = {e.canonical_entity_id for e in entities}
    # Concrete same-campaign kinds kept; thread and other-campaign dropped.
    assert "loc_mireward_gate" in ids
    assert "npc_edge_survivors" in ids
    assert "thread_weave_distortion" not in ids
    assert "loc_other_campaign" not in ids
    # World pc nodes are excluded by default: party anchors own PC identity.
    assert "node:caelynn" not in ids


def test_world_graph_loader_all_kinds_opt_in() -> None:
    entities = known_entities_from_world_graph(
        _world_graph_fixture(),
        include_kinds=None,
        campaign_scopes=frozenset({"longmont-c2"}),
    )
    assert "thread_weave_distortion" in {e.canonical_entity_id for e in entities}


def test_world_graph_loader_aliases_and_identity() -> None:
    entities = known_entities_from_world_graph(_world_graph_fixture())
    by_id = {e.canonical_entity_id: e for e in entities}
    gate = by_id["loc_mireward_gate"]
    assert gate.display_name == "Mireward Gate"
    surfaces = {surface for surface, _ in gate.match_terms}
    # Own label + node aliases + graph-level alias map, no id-derived junk.
    assert "Mireward Gate" in surfaces
    assert "Old Gate" in surfaces
    assert all("loc_mireward_gate" not in s for s in surfaces)
    assert gate.corpus_ref["resolution"] == "world_head"
    survivors = by_id["npc_edge_survivors"]
    assert survivors.slug == "npc_edge_survivors"
    assert survivors.kind == "group"


def test_extend_registry_party_wins_collisions() -> None:
    base = build_known_entity_registry("longmont-c2", 22)
    extras = known_entities_from_world_graph(
        _world_graph_fixture(), include_kinds=None
    )
    extended = extend_known_entity_registry(base, extras)
    ids = extended.by_canonical_id()
    # Party anchor kept its original registry entry, not the world-graph one.
    assert ids["node:caelynn"].hub_resolved is True
    added = set(ids) - {e.canonical_entity_id for e in base.entities}
    assert {"loc_mireward_gate", "npc_edge_survivors"} <= added
    assert extended.diagnostics["extra_entities_offered"] == len(extras)
    assert extended.diagnostics["extra_entities_added"] == len(added)
    assert extended.diagnostics["entity_count"] == len(extended.entities)
