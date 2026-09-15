"""PC representation aliases match without weakening real cross-kind guards."""

from apps.live_control_server.models.world_graph_identity_models import IdentityCandidate
from apps.live_control_server.models.world_graph_mutation_context import (
    MutationObject,
    WorldGraphMutationContext,
    resolve_identity_against_context,
)


def _resolve(*, world_kind: str, candidate_kind: str):
    context = WorldGraphMutationContext(
        world_id="test-world",
        revision_id="rev:parent",
        head_revision_id="rev:parent",
        objects={"node:hero": MutationObject(object_id="node:hero", label="Hero", kind=world_kind)},
    )
    return resolve_identity_against_context(
        context,
        IdentityCandidate(
            world_id="test-world", candidate_id="candidate:hero", label="Hero",
            object_kind=candidate_kind, aliases=["Hero"], evidence_ref_ids=["evidence:1"],
        ),
    )


def test_pc_matches_player_character() -> None:
    result = _resolve(world_kind="player_character", candidate_kind="pc")
    assert result.outcome == "resolved_existing"
    assert result.target_node_id == "node:hero"


def test_player_character_matches_pc() -> None:
    assert _resolve(world_kind="pc", candidate_kind="player_character").outcome == "resolved_existing"


def test_dnd_prefixed_player_character_matches_pc() -> None:
    assert _resolve(world_kind="dnd5e:player_character", candidate_kind="pc").outcome == "resolved_existing"


def test_npc_remains_cross_kind_collision() -> None:
    result = _resolve(world_kind="player_character", candidate_kind="npc")
    assert result.outcome == "blocked_collision"
    assert result.requires_human_review is True
