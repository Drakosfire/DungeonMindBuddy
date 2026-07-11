"""Graph Kernel identity outcome classification tests (PR004)."""

from __future__ import annotations

import copy

import graph_memory.kernel as kernel
from graph_memory.kernel.contracts import (
    ALL_RESERVED_KERNEL_APIS,
    IMPLEMENTED_IN_PR004_IDENTITY,
    RESERVED_FOR_PR005_CONTRIBUTION,
    RESERVED_FOR_PR007_PROJECTION,
)
from graph_memory.kernel.identity_models import IdentityCandidate
from graph_memory.union_supergraph.load import (
    DEFAULT_FIXTURE_PATH,
    load_union_supergraph_payload,
    parse_union_supergraph_store,
)
from graph_memory.union_supergraph.model import UnionSupergraphNode, UnionSupergraphStore


def _base_store() -> UnionSupergraphStore:
    return parse_union_supergraph_store(load_union_supergraph_payload(DEFAULT_FIXTURE_PATH))


def _add_node(store: UnionSupergraphStore, node: UnionSupergraphNode) -> UnionSupergraphStore:
    nodes = dict(store.nodes)
    nodes[node.node_id] = node
    aliases = dict(store.aliases)
    for alias in node.aliases:
        aliases[alias.casefold()] = node.node_id
    aliases[node.label.casefold()] = node.node_id
    adjacency = dict(store.adjacency)
    adjacency.setdefault(node.node_id, [])
    return store.model_copy(update={"nodes": nodes, "aliases": aliases, "adjacency": adjacency})


def _npc(node_id: str, label: str, *aliases: str) -> UnionSupergraphNode:
    return UnionSupergraphNode(
        node_id=node_id,
        label=label,
        kind="npc",
        role="npc",
        aliases=list(aliases) or [label],
        source_domains=["recap"],
        evidence_ref_ids=["evidence:test"],
        state={
            "memory_state": "graph_read_model",
            "identity_canon_state": "canonical",
        },
    )


def test_resolved_existing_for_exact_same_kind_alias() -> None:
    store = _add_node(_base_store(), _npc("npc_willow", "Willow", "Willow"))
    candidate = IdentityCandidate(
        world_id="eldyrwild",
        candidate_id="cand:willow-1",
        label="Willow",
        object_kind="npc",
        aliases=["Willow"],
        evidence_ref_ids=["evidence:session-1:willow"],
    )
    before = copy.deepcopy(store.model_dump(mode="json"))
    resolution = kernel.resolve_identity(store, candidate)
    after = store.model_dump(mode="json")

    assert resolution.outcome == "resolved_existing"
    assert resolution.target_node_id == "npc_willow"
    assert resolution.created_node_id is None
    assert resolution.provisional_node_id is None
    assert resolution.requires_human_review is False
    assert after == before  # pure classifier


def test_created_new_when_no_collision_and_evidence_present() -> None:
    store = _base_store()
    candidate = IdentityCandidate(
        world_id="eldyrwild",
        candidate_id="cand:hester-new",
        label="Hester",
        object_kind="npc",
        aliases=["Hester"],
        evidence_ref_ids=["evidence:session-2:hester"],
        proposed_node_id="npc_hester",
    )
    before_nodes = set(store.nodes)
    resolution = kernel.resolve_identity(store, candidate)

    assert resolution.outcome == "created_new"
    assert resolution.created_node_id == "npc_hester"
    assert resolution.canon_state == "canonical"
    assert resolution.requires_human_review is False
    assert set(store.nodes) == before_nodes  # instructs creation; does not mutate


def test_provisional_new_is_noncanonical() -> None:
    store = _base_store()
    candidate = IdentityCandidate(
        world_id="eldyrwild",
        candidate_id="cand:rumor-figure",
        label="The Veiled One",
        object_kind="npc",
        aliases=["Veiled One"],
        evidence_ref_ids=[],
    )
    resolution = kernel.resolve_identity(store, candidate)

    assert resolution.outcome == "provisional_new"
    assert resolution.provisional_node_id == "provisional:cand:rumor-figure"
    assert resolution.canon_state == "noncanonical_provisional"
    assert any("insufficient evidence" in d.lower() or "provisional" in d.lower() for d in resolution.diagnostics)
    assert "provisional:cand:rumor-figure" not in store.nodes


def test_ambiguous_candidate_does_not_promote() -> None:
    store = _base_store()
    store = _add_node(store, _npc("npc_hester_a", "Hester", "Hester"))
    store = _add_node(store, _npc("npc_hester_b", "Hester Bright", "Hester"))
    candidate = IdentityCandidate(
        world_id="eldyrwild",
        candidate_id="cand:hester-ambig",
        label="Hester",
        object_kind="npc",
        aliases=["Hester"],
        evidence_ref_ids=["evidence:session-3:hester"],
    )
    before = copy.deepcopy(store.model_dump(mode="json"))
    resolution = kernel.resolve_identity(store, candidate)

    assert resolution.outcome == "ambiguous"
    assert resolution.requires_human_review is True
    assert resolution.target_node_id is None
    assert resolution.created_node_id is None
    assert resolution.provisional_node_id is None
    assert store.model_dump(mode="json") == before


def test_blocked_cross_kind_collision() -> None:
    store = _add_node(_base_store(), _npc("npc_willow", "Willow", "Willow"))
    candidate = IdentityCandidate(
        world_id="eldyrwild",
        candidate_id="cand:willow-loc",
        label="Willow",
        object_kind="location",
        aliases=["Willow"],
        evidence_ref_ids=["evidence:world:willow-grove"],
        confidence=0.99,
    )
    resolution = kernel.resolve_identity(store, candidate)

    assert resolution.outcome == "blocked_collision"
    assert "npc_willow" in resolution.blocked_by
    assert resolution.requires_human_review is True
    assert resolution.target_node_id is None
    assert any("cross-kind" in d.lower() for d in resolution.diagnostics)


def test_resolution_confidence_is_not_authority() -> None:
    store = _add_node(_base_store(), _npc("npc_willow", "Willow", "Willow"))
    candidate = IdentityCandidate(
        world_id="eldyrwild",
        candidate_id="cand:willow-loc-confident",
        label="Willow",
        object_kind="location",
        aliases=["Willow"],
        evidence_ref_ids=["evidence:world:willow"],
        confidence=0.999,
    )
    resolution = kernel.classify_identity_outcome(store, candidate)

    assert resolution.outcome == "blocked_collision"
    assert any("not authority" in d.lower() for d in resolution.diagnostics)


def test_provisional_existing_match_does_not_promote_to_canonical() -> None:
    store = _base_store()
    provisional = UnionSupergraphNode(
        node_id="npc_willow_prov",
        label="Willow",
        kind="npc",
        role="npc",
        aliases=["Willow"],
        source_domains=["recap"],
        evidence_ref_ids=[],
        state={
            "memory_state": "graph_read_model",
            "identity_canon_state": "noncanonical_provisional",
        },
    )
    store = _add_node(store, provisional)
    candidate = IdentityCandidate(
        world_id="eldyrwild",
        candidate_id="cand:willow-later",
        label="Willow",
        object_kind="npc",
        aliases=["Willow"],
        evidence_ref_ids=["evidence:session-9:willow"],
        confidence=0.98,
    )
    resolution = kernel.resolve_identity(store, candidate)

    assert resolution.outcome != "resolved_existing"
    assert resolution.outcome == "provisional_new"
    assert resolution.provisional_node_id == "npc_willow_prov"
    assert resolution.target_node_id is None
    assert resolution.created_node_id is None
    assert resolution.canon_state == "noncanonical_provisional"
    assert resolution.requires_human_review is True
    assert any("not promoted" in d.lower() for d in resolution.diagnostics)


def test_rejected_candidate_records_inspectable_decision() -> None:
    store = _base_store()
    candidate = IdentityCandidate(
        world_id="eldyrwild",
        candidate_id="cand:noise",
        label="Background Extra",
        object_kind="npc",
        aliases=["Extra"],
        evidence_ref_ids=["evidence:noise"],
    )
    decision = kernel.build_identity_decision_record(
        world_id="eldyrwild",
        decision_kind="reject_candidate",
        actor="gm:drakosfire",
        reason="Not a durable campaign identity",
        source_candidate_id=candidate.candidate_id,
    )
    updated = kernel.record_identity_decision(store, decision)
    resolution = kernel.resolve_identity(updated, candidate)

    assert resolution.outcome == "rejected"
    assert resolution.created_node_id is None
    assert resolution.target_node_id is None
    assert resolution.decision_id == decision.decision_id
    assert any(d["decision_id"] == decision.decision_id for d in updated.identity_decisions)


def test_human_override_records_replayable_decision() -> None:
    store = _base_store()
    store = _add_node(store, _npc("npc_hester_a", "Hester", "Hester"))
    store = _add_node(store, _npc("npc_hester_b", "Hester Bright", "Hester"))
    candidate = IdentityCandidate(
        world_id="eldyrwild",
        candidate_id="cand:hester-ambig",
        label="Hester",
        object_kind="npc",
        aliases=["Hester"],
        evidence_ref_ids=["evidence:session-3:hester"],
    )
    assert kernel.resolve_identity(store, candidate).outcome == "ambiguous"

    decision = kernel.build_identity_decision_record(
        world_id="eldyrwild",
        decision_kind="human_override",
        actor="gm:drakosfire",
        reason="Hester Bright is the intended match",
        source_candidate_id=candidate.candidate_id,
        target_node_id="npc_hester_b",
        affected_node_ids=["npc_hester_b"],
    )
    updated = kernel.record_identity_decision(store, decision)
    resolution = kernel.resolve_identity(updated, candidate)

    assert resolution.outcome == "human_override"
    assert resolution.target_node_id == "npc_hester_b"
    assert resolution.decision_id == decision.decision_id
    assert decision.actor == "gm:drakosfire"
    assert decision.reason
    round_trip = kernel.IdentityDecisionRecord.model_validate(decision.model_dump(mode="json"))
    assert round_trip.decision_id == decision.decision_id
    assert any(d["decision_id"] == decision.decision_id for d in updated.identity_decisions)


def test_kernel_exports_identity_apis_after_pr004() -> None:
    public_names = set(kernel.__all__)
    for name in IMPLEMENTED_IN_PR004_IDENTITY:
        assert name in public_names
        assert callable(getattr(kernel, name))

    for name in ALL_RESERVED_KERNEL_APIS:
        assert name not in public_names
        assert not hasattr(kernel, name)

    assert set(RESERVED_FOR_PR005_CONTRIBUTION) | set(RESERVED_FOR_PR007_PROJECTION) == set(
        ALL_RESERVED_KERNEL_APIS
    )
