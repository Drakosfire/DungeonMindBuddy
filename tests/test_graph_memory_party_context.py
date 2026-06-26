"""Tests for src/graph_memory/party_context.py.

Pins the deterministic party-context construction against the real Longmont
Campaign 2 corpus + ``_party_registry.json`` (PC roster, the new
``session_companion_rosters`` for Thrin/Lysandra), and verifies the node-shape
policy: party members emit resolved-corpus_ref nodes whose
``identity_resolution.canonical_node_key`` is the hub_path, so a party member
dedup-matches its extracted counterpart across sessions.
"""

from __future__ import annotations

from src.graph_memory import identity_resolution as ir
from src.graph_memory import party_context as pc


# --------------------------------------------------------------------------- #
# Roster construction from the registry
# --------------------------------------------------------------------------- #

def test_session_22_roster_pcs_and_companions():
    ctx = pc.build_party_context(22)
    assert ctx.campaign_id == "longmont-c2"
    assert ctx.session == "22"
    assert ctx.party_names == ("Questionable Company",)
    assert not ctx.warnings
    assert {m.slug for m in ctx.pcs()} == {
        "baergrom", "bonogo", "caelynn", "ephanna", "karsemine", "stafl",
    }
    assert {m.slug for m in ctx.companions()} == {
        "thrin_branchborn", "captain_lysandra_ironveil",
    }


def test_companions_are_npc_kind_and_resolve():
    ctx = pc.build_party_context(22)
    for m in ctx.companions():
        assert m.kind == "companion"
        assert m.corpus_ref_type == "npc"
        assert m.hub_resolved
        assert m.hub_rel_path.endswith("/README.md")


def test_pc_player_parsed_from_frontmatter():
    ctx = pc.build_party_context(22)
    players = {m.slug: m.player for m in ctx.pcs()}
    assert players["stafl"] == "Scott"
    assert players["caelynn"] == "Danielle"


def test_session_without_companion_roster_has_no_companions():
    ctx = pc.build_party_context(20)
    assert len(ctx.pcs()) == 6
    assert ctx.companions() == ()


def test_unknown_session_warns_and_is_empty():
    ctx = pc.build_party_context(999)
    assert ctx.members == ()
    assert any("session_pc_rosters" in w for w in ctx.warnings)


# --------------------------------------------------------------------------- #
# Node-shape policy + identity integration
# --------------------------------------------------------------------------- #

def test_seed_node_is_character_with_resolved_corpus_ref():
    ctx = pc.build_party_context(22)
    lys = next(m for m in ctx.members if m.slug == "captain_lysandra_ironveil")
    node = lys.seed_node()
    assert node["node_type"] == pc.PARTY_NODE_SHAPE == "character"
    cr = node["corpus_ref"]
    assert cr["type"] == "npc" and cr["ref_id"] == "captain_lysandra_ironveil"
    assert cr["resolution"] == "resolved"
    assert cr["hub_path"].endswith("captain_lysandra_ironveil/README.md")


def test_party_member_canonical_key_is_hub_path():
    ctx = pc.build_party_context(22)
    thrin = next(m for m in ctx.members if m.slug == "thrin_branchborn")
    key = ir.canonical_node_key(thrin.seed_node())
    assert key[0] == "corpus" and "thrin_branchborn/readme.md" in key[1]


def test_party_anchor_matches_divergently_labelled_extraction():
    # The whole point: an extractor node that resolves the same hub but labels
    # it differently ("Lieutenant L.") still dedup-matches the standing anchor,
    # because resolved corpus identity is decisive in node_match_score.
    ctx = pc.build_party_context(22)
    anchor = next(m for m in ctx.members if m.slug == "captain_lysandra_ironveil").seed_node()
    extracted = {
        "node_id": "character_lysandra",
        "label": "Lieutenant L.",
        "node_type": "character",
        "corpus_ref": dict(anchor["corpus_ref"]),
    }
    assert ir.nodes_match(anchor, extracted)


def test_anchor_hub_paths_cover_all_resolved_members():
    ctx = pc.build_party_context(22)
    anchors = ctx.anchor_hub_paths()
    assert len(anchors) == len([m for m in ctx.members if m.hub_resolved])
    assert any("captain_lysandra_ironveil" in p for p in anchors)
    assert any("thrin_branchborn" in p for p in anchors)


# --------------------------------------------------------------------------- #
# Related-node adjacency (deterministic hub cross-link harvest)
# --------------------------------------------------------------------------- #

def test_related_hub_slugs_harvested_from_readme_crosslinks():
    ctx = pc.build_party_context(22)
    stafl = next(m for m in ctx.pcs() if m.slug == "stafl")
    # Stafl's hub README cross-links Lysandra and Caelynn; self is excluded.
    assert "captain_lysandra_ironveil" in stafl.related_hub_slugs
    assert "stafl" not in stafl.related_hub_slugs
