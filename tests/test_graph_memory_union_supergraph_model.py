from __future__ import annotations

import copy

import pytest
from pydantic import ValidationError

from graph_memory.union_supergraph.load import (
    DEFAULT_FIXTURE_PATH,
    load_union_supergraph_payload,
    load_union_supergraph_store,
    parse_union_supergraph_store,
)
from graph_memory.union_supergraph.model import UnionSupergraphStore


@pytest.fixture
def fixture() -> dict:
    return load_union_supergraph_payload(DEFAULT_FIXTURE_PATH)


@pytest.fixture
def store(fixture: dict) -> UnionSupergraphStore:
    return parse_union_supergraph_store(fixture)


def test_fixture_parses_as_union_supergraph_store(fixture: dict) -> None:
    store = parse_union_supergraph_store(fixture)

    assert isinstance(store, UnionSupergraphStore)
    assert store.schema == "dmb_union_supergraph_store_v0"
    assert store.campaign_id == "longmont-c2"


def test_model_exposes_top_level_counts(store: UnionSupergraphStore) -> None:
    assert len(store.nodes) == 3
    assert len(store.edges) == 2
    assert len(store.evidence) == 3
    assert len(store.source_artifacts) == 3
    assert len(store.adjacency) == 3


def test_node_model_parses_existing_caelynn_node(store: UnionSupergraphStore) -> None:
    caelynn = store.nodes["pc_caelynn"]

    assert caelynn.node_id == "pc_caelynn"
    assert caelynn.label == "Caelynn"
    assert caelynn.source_domains == ["recap", "worldbuilding"]
    assert "evidence:worldbuilding:caelynn:character-note" in caelynn.evidence_ref_ids
    assert caelynn.state["memory_state"] == "graph_read_model"


def test_edge_model_parses_focus_session_edge(store: UnionSupergraphStore) -> None:
    edge = store.edges["edge:pc_caelynn:participated_in:event_session_23_mireward_gate"]

    assert edge.source_node_id == "pc_caelynn"
    assert edge.target_node_id == "event_session_23_mireward_gate"
    assert edge.predicate == "participated_in"
    assert edge.session_ids == ["session-23"]


def test_evidence_model_parses_recap_and_worldbuilding_evidence(
    store: UnionSupergraphStore,
) -> None:
    recap = store.evidence["evidence:session-23:caelynn:recap-mention"]
    worldbuilding = store.evidence["evidence:worldbuilding:caelynn:character-note"]

    assert recap.source_domain == "recap"
    assert recap.session_id == "session-23"
    assert recap.source_span_ref_id == "spref:session-23:p014"
    assert worldbuilding.source_domain == "worldbuilding"
    assert (
        worldbuilding.locator
        == "worldbuilding/characters/caelynn.md#read-model-example"
    )


def test_adjacency_item_model_exposes_view_relative_direction(
    store: UnionSupergraphStore,
) -> None:
    adjacency = store.adjacency["pc_caelynn"][0]

    assert (
        adjacency.edge_id
        == "edge:pc_caelynn:participated_in:event_session_23_mireward_gate"
    )
    assert adjacency.node_id == "event_session_23_mireward_gate"
    assert adjacency.direction == "outbound"
    assert adjacency.label == "participated in"


def test_model_rejects_adjacency_without_direction(fixture: dict) -> None:
    payload = copy.deepcopy(fixture)
    payload["adjacency"]["pc_caelynn"][0].pop("direction")

    with pytest.raises(ValidationError, match="direction"):
        parse_union_supergraph_store(payload)


def test_diagnostics_model_defaults_or_parses_safety_flags(fixture: dict) -> None:
    store = parse_union_supergraph_store(fixture)
    assert store.diagnostics.corpus_mutation is False
    assert store.diagnostics.production_retrieval is False

    payload = copy.deepcopy(fixture)
    payload["diagnostics"] = {}
    store_with_defaults = parse_union_supergraph_store(payload)
    assert store_with_defaults.diagnostics.canon_promotion is False
    assert store_with_defaults.diagnostics.approved_memory_write is False


def test_load_union_supergraph_store_uses_default_fixture_path() -> None:
    store = load_union_supergraph_store()

    assert store.focus_session_id == "session-23"
    assert "pc_caelynn" in store.nodes


def test_model_rejects_missing_required_top_level_fields(fixture: dict) -> None:
    payload = copy.deepcopy(fixture)
    payload.pop("focus_session_id")

    with pytest.raises(ValidationError, match="focus_session_id"):
        parse_union_supergraph_store(payload)


def test_model_rejects_invalid_basic_types(fixture: dict) -> None:
    payload = copy.deepcopy(fixture)
    payload["nodes"] = []

    with pytest.raises(ValidationError, match="nodes"):
        parse_union_supergraph_store(payload)
