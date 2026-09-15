"""Exact durable-id continuity for head-pinned identity resolution."""

from __future__ import annotations

from apps.live_control_server.models.world_graph_identity_models import IdentityCandidate
from apps.live_control_server.models.world_graph_mutation_context import (
    MutationObject,
    WorldGraphMutationContext,
    resolve_identity_against_context,
)


def _context_with(*objects: MutationObject) -> WorldGraphMutationContext:
    return WorldGraphMutationContext(
        world_id="dogfood-world",
        revision_id="rev:parent",
        head_revision_id="rev:parent",
        objects={obj.object_id: obj for obj in objects},
    )


def test_exact_durable_id_confirms_existing_despite_label_drift() -> None:
    """Dogfood witness: loc:rivers-edge-pub reappears with a drifted label."""
    context = _context_with(
        MutationObject(
            object_id="loc:rivers-edge-pub",
            label="The River's Edge Pub",
            kind="location",
            aliases=("The River's Edge Pub",),
        ),
        MutationObject(
            object_id="node:the_rivers_edge_pub",
            label="The River's Edge Pub",
            kind="party",
            aliases=("The River's Edge Pub",),
        ),
        MutationObject(
            object_id="obj:rivers-edge-pub",
            label="The River's Edge Pub",
            kind="item",
            aliases=("The River's Edge Pub",),
        ),
    )
    result = resolve_identity_against_context(
        context,
        IdentityCandidate(
            world_id="dogfood-world",
            candidate_id="loc:rivers-edge-pub",
            label="River's Edge Pub",
            object_kind="location",
            aliases=[],
            evidence_ref_ids=["evidence:1"],
            proposed_node_id="loc:rivers-edge-pub",
        ),
    )
    assert result.outcome == "resolved_existing"
    assert result.target_node_id == "loc:rivers-edge-pub"
    assert result.requires_human_review is False


def test_exact_durable_id_beats_cross_kind_alias_collision() -> None:
    context = _context_with(
        MutationObject(
            object_id="loc:stone-bridge",
            label="Stone Bridge",
            kind="location",
            aliases=("Stone Bridge",),
        ),
        MutationObject(
            object_id="node:stone_bridge",
            label="Stone Bridge",
            kind="party",
            aliases=("Stone Bridge",),
        ),
        MutationObject(
            object_id="obj:stone-bridge",
            label="Stone Bridge",
            kind="item",
            aliases=("Stone Bridge",),
        ),
    )
    result = resolve_identity_against_context(
        context,
        IdentityCandidate(
            world_id="dogfood-world",
            candidate_id="loc:stone-bridge",
            label="Stone Bridge",
            object_kind="location",
            aliases=[],
            evidence_ref_ids=["evidence:1"],
            proposed_node_id="loc:stone-bridge",
        ),
    )
    assert result.outcome == "resolved_existing"
    assert result.target_node_id == "loc:stone-bridge"


def test_exact_id_cross_kind_does_not_force_confirm() -> None:
    """Naming a durable id of the wrong kind must not invent resolved_existing."""
    context = _context_with(
        MutationObject(
            object_id="loc:rivers-edge-pub",
            label="The River's Edge Pub",
            kind="location",
        )
    )
    result = resolve_identity_against_context(
        context,
        IdentityCandidate(
            world_id="dogfood-world",
            candidate_id="loc:rivers-edge-pub",
            label="River's Edge Pub",
            object_kind="npc",
            aliases=[],
            evidence_ref_ids=["evidence:1"],
            proposed_node_id="loc:rivers-edge-pub",
        ),
    )
    assert result.outcome != "resolved_existing"
