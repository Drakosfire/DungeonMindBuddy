"""Parity: rehomed D.3A mutation-context / identity values match legacy kernel models."""

from __future__ import annotations

from apps.live_control_server.models import world_graph_identity_models as new_models
from apps.live_control_server.models import world_graph_identity_policy as new_policy
from apps.live_control_server.models.world_graph_mutation_context import (
    MutationObject,
    WorldGraphMutationContext,
    resolve_identity_against_context,
    wire_kind,
)
from graph_memory.kernel import identity_models as old_models
from graph_memory.kernel import identity_policy as old_policy
from graph_memory.world_graph_mutation_context import (
    MutationObject as OldMutationObject,
    WorldGraphMutationContext as OldWorldGraphMutationContext,
    resolve_identity_against_context as old_resolve,
    wire_kind as old_wire_kind,
)


def test_identity_model_json_parity() -> None:
    old = old_models.IdentityCandidate(
        world_id="w",
        candidate_id="c1",
        label="Hester",
        object_kind="npc",
        aliases=["Hester"],
        evidence_ref_ids=["e1"],
    )
    new = new_models.IdentityCandidate(
        world_id="w",
        candidate_id="c1",
        label="Hester",
        object_kind="npc",
        aliases=["Hester"],
        evidence_ref_ids=["e1"],
    )
    assert old.model_dump(mode="json") == new.model_dump(mode="json")
    old_r = old_models.IdentityResolution(
        world_id="w",
        candidate_id="c1",
        outcome="resolved_existing",
        target_node_id="npc_hester",
    )
    new_r = new_models.IdentityResolution(
        world_id="w",
        candidate_id="c1",
        outcome="resolved_existing",
        target_node_id="npc_hester",
    )
    assert old_r.model_dump(mode="json") == new_r.model_dump(mode="json")


def test_identity_policy_parity() -> None:
    assert (
        old_policy.DEFAULT_IDENTITY_RESOLUTION_POLICY.model_dump(mode="json")
        == new_policy.DEFAULT_IDENTITY_RESOLUTION_POLICY.model_dump(mode="json")
    )


def test_wire_kind_and_resolve_parity() -> None:
    assert old_wire_kind("dnd5e:npc") == wire_kind("dnd5e:npc")
    old_ctx = OldWorldGraphMutationContext(
        world_id="w",
        revision_id="rev:1",
        head_revision_id="rev:1",
        objects={
            "npc_hester": OldMutationObject(
                object_id="npc_hester", label="Hester", kind="npc", aliases=("Hester",)
            )
        },
        alias_owners={"Hester": ("npc_hester",)},
    )
    new_ctx = WorldGraphMutationContext(
        world_id="w",
        revision_id="rev:1",
        head_revision_id="rev:1",
        objects={
            "npc_hester": MutationObject(
                object_id="npc_hester", label="Hester", kind="npc", aliases=("Hester",)
            )
        },
        alias_owners={"Hester": ("npc_hester",)},
    )
    old_cand = old_models.IdentityCandidate(
        world_id="w",
        candidate_id="extract:hester",
        label="Hester",
        object_kind="npc",
        aliases=["Hester"],
        evidence_ref_ids=["span:1"],
    )
    new_cand = new_models.IdentityCandidate(
        world_id="w",
        candidate_id="extract:hester",
        label="Hester",
        object_kind="npc",
        aliases=["Hester"],
        evidence_ref_ids=["span:1"],
    )
    old_res = old_resolve(old_ctx, old_cand)
    new_res = resolve_identity_against_context(new_ctx, new_cand)
    assert old_res.model_dump(mode="json") == new_res.model_dump(mode="json")
