"""Unit tests for PC identity normalization and cross-kind protection."""

from __future__ import annotations

from apps.live_control_server.models.world_graph_identity_models import IdentityCandidate
from apps.live_control_server.models.world_graph_mutation_context import (
    MutationObject,
    WorldGraphMutationContext,
    resolve_identity_against_context,
)


def _context(*objects: MutationObject) -> WorldGraphMutationContext:
    obj_map = {obj.object_id: obj for obj in objects}
    return WorldGraphMutationContext(
        world_id="eldyrwild",
        revision_id="rev:test-parent",
        head_revision_id="rev:test-parent",
        objects=obj_map,
    )


def test_positive_equivalence_candidate_pc_world_player_character() -> None:
    """Candidate kind 'pc' matches existing World kind 'player_character' as same-kind."""
    context = _context(
        MutationObject(
            object_id="node:stafl",
            label="Stafl",
            kind="player_character",
        )
    )
    resolution = resolve_identity_against_context(
        context,
        IdentityCandidate(
            world_id="eldyrwild",
            candidate_id="extract:stafl",
            label="Stafl",
            object_kind="pc",
            aliases=["Stafl"],
            evidence_ref_ids=["span:1"],
        ),
    )
    assert resolution.outcome == "resolved_existing"
    assert resolution.target_node_id == "node:stafl"
    assert resolution.requires_human_review is False


def test_positive_equivalence_candidate_player_character_world_pc() -> None:
    """Candidate kind 'player_character' matches existing World kind 'pc' as same-kind."""
    context = _context(
        MutationObject(
            object_id="node:baergrom",
            label="Baergrom",
            kind="pc",
        )
    )
    resolution = resolve_identity_against_context(
        context,
        IdentityCandidate(
            world_id="eldyrwild",
            candidate_id="extract:baergrom",
            label="Baergrom",
            object_kind="player_character",
            aliases=["Baergrom"],
            evidence_ref_ids=["span:1"],
        ),
    )
    assert resolution.outcome == "resolved_existing"
    assert resolution.target_node_id == "node:baergrom"
    assert resolution.requires_human_review is False


def test_positive_equivalence_with_dnd_vocab_prefix_on_world_kind() -> None:
    """Candidate kind 'pc' matches existing World kind 'dnd5e:player_character'."""
    context = _context(
        MutationObject(
            object_id="node:bonogo",
            label="Bonogo",
            kind="dnd5e:player_character",
        )
    )
    resolution = resolve_identity_against_context(
        context,
        IdentityCandidate(
            world_id="eldyrwild",
            candidate_id="extract:bonogo",
            label="Bonogo",
            object_kind="pc",
            aliases=["Bonogo"],
            evidence_ref_ids=["span:1"],
        ),
    )
    assert resolution.outcome == "resolved_existing"
    assert resolution.target_node_id == "node:bonogo"


def test_real_cross_kind_collision_npc_vs_player_character() -> None:
    """Candidate kind 'npc' colliding with World kind 'player_character' remains blocked."""
    context = _context(
        MutationObject(
            object_id="node:stafl",
            label="Stafl",
            kind="player_character",
        )
    )
    resolution = resolve_identity_against_context(
        context,
        IdentityCandidate(
            world_id="eldyrwild",
            candidate_id="extract:stafl-fake",
            label="Stafl",
            object_kind="npc",
            aliases=["Stafl"],
            evidence_ref_ids=["span:1"],
        ),
    )
    assert resolution.outcome == "blocked_collision"
    assert resolution.requires_human_review is True
    assert "node:stafl" in resolution.blocked_by


def test_real_cross_kind_collision_creature_vs_player_character() -> None:
    """Candidate kind 'creature' colliding with World kind 'player_character' remains blocked."""
    context = _context(
        MutationObject(
            object_id="node:baergrom",
            label="Baergrom",
            kind="player_character",
        )
    )
    resolution = resolve_identity_against_context(
        context,
        IdentityCandidate(
            world_id="eldyrwild",
            candidate_id="extract:baergrom-beast",
            label="Baergrom",
            object_kind="creature",
            aliases=["Baergrom"],
            evidence_ref_ids=["span:1"],
        ),
    )
    assert resolution.outcome == "blocked_collision"
    assert resolution.requires_human_review is True
    assert "node:baergrom" in resolution.blocked_by


def test_no_campaign_specific_special_casing_arbitrary_names() -> None:
    """Normalization operates on any arbitrary label, not hard-coded C1 PC names."""
    context = _context(
        MutationObject(
            object_id="node:valeros",
            label="Valeros the Fighter",
            kind="player_character",
        )
    )
    resolution = resolve_identity_against_context(
        context,
        IdentityCandidate(
            world_id="eldyrwild",
            candidate_id="extract:valeros",
            label="Valeros the Fighter",
            object_kind="pc",
            aliases=["Valeros"],
            evidence_ref_ids=["span:1"],
        ),
    )
    assert resolution.outcome == "resolved_existing"
    assert resolution.target_node_id == "node:valeros"
