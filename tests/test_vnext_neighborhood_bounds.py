from types import SimpleNamespace

from dungeonmind.application.vnext.records import ParsedEntityRefValue, ParsedPublicVisibility, ParsedTimelessTemporalScope

from apps.live_control_server.integrations.dungeonmind.vnext_neighborhood import bound_neighborhood


def test_bounds_keep_seeds_and_cap_sorted_edges_after_filtering():
    def edge(identifier, target):
        return SimpleNamespace(
            assertion_id=identifier,
            subject_entity_id="seed",
            value=ParsedEntityRefValue(entity_id=target),
        )

    result = SimpleNamespace(
        found_seed_entity_ids=("seed",),
        entity_depths=(("seed", 0), ("boundary", 2), ("near", 1)),
        traversal_assertions=(edge("z", "near"), edge("a", "boundary"), edge("b", "near")),
    )
    request = SimpleNamespace(
        seed_node_ids=["missing", "seed", "seed"],
        bounds=SimpleNamespace(max_nodes=2, max_relationships=1),
    )
    bounded = bound_neighborhood(result, request.seed_node_ids, request.bounds)
    assert bounded.node_ids == ("seed", "near")
    assert [edge.assertion_id for edge in bounded.edges] == ["b"]
    assert bounded.nodes_truncated and bounded.relationships_truncated


def test_read_requests_single_admitted_traversal(monkeypatch):
    from dungeonmind.application.vnext.neighborhood import NeighborhoodReadService
    from apps.live_control_server.integrations.dungeonmind.vnext_neighborhood import read_neighborhood

    calls = []
    result = SimpleNamespace(found_seed_entity_ids=(), entity_depths=(), traversal_assertions=())
    context = object()

    def traverse(self, ctx, seeds, depth, *, require_admitted_seeds):
        calls.append((ctx, seeds, depth, require_admitted_seeds))
        return result

    monkeypatch.setattr(NeighborhoodReadService, "get_neighborhood", traverse)
    request = SimpleNamespace(seed_node_ids=["hidden"], max_depth=2,
                              bounds=SimpleNamespace(max_nodes=2, max_relationships=1))
    authorized, bounded = read_neighborhood(context, request.seed_node_ids, request.max_depth, request.bounds)
    assert calls == [(context, ["hidden"], 2, True)]
    assert authorized is result
    assert bounded.node_ids == bounded.edges == ()


def test_relationship_mapping_loads_only_retained_edge_sources():
    from apps.live_control_server.integrations.dungeonmind.vnext_neighborhood import (
        BoundedNeighborhood, map_relationships,
    )

    edge = SimpleNamespace(
        assertion_id="asrt:edge",
        subject_entity_id="seed",
        predicate="dnd5e:located_in",
        value=ParsedEntityRefValue(entity_id="near"),
        metadata=SimpleNamespace(
            evidence_ref_ids=("ev:edge",), domain_metadata=(),
            visibility=ParsedPublicVisibility(),
            scope=(),
            claim_mode="dungeonbuddy.claim:fact", temporal_scope=ParsedTimelessTemporalScope(),
        ),
    )
    result = SimpleNamespace(evidence=(
        SimpleNamespace(evidence_ref_id="ev:edge", source_artifact_id="src:edge"),
        SimpleNamespace(evidence_ref_id="ev:other", source_artifact_id="src:other"),
    ))
    def load(*, artifact_ids, revision_ids):
        assert artifact_ids == ("src:edge",)
        assert revision_ids == ()
        return SimpleNamespace(artifacts_by_id={
            "src:edge": SimpleNamespace(
                domain_metadata=(), source_classification="dungeonbuddy.source:session_recap"
            ),
        })

    context = SimpleNamespace(source_reader=SimpleNamespace(get_provenance_snapshot=load))
    [mapped] = map_relationships(context, result, BoundedNeighborhood(("seed", "near"), (edge,), False, False))
    assert (mapped.source_node_id, mapped.target_node_id) == ("seed", "near")
    assert mapped.evidence_ref_ids == ["ev:edge"]
    assert mapped.source_artifact_ids == ["src:edge"]


def test_native_anchor_selector_preserves_exact_ids():
    import pytest

    from apps.live_control_server.integrations.dungeonmind.vnext_neighborhood import (
        native_anchor_id,
        native_anchor_selection,
    )

    identity = ("asrt:é", "ev:exact")
    encoded = native_anchor_id(*identity)
    assert native_anchor_selection(encoded) == identity
    for malformed in ("classic:abc", encoded + "!", native_anchor_id("", "ev:exact")):
        with pytest.raises(ValueError, match="invalid native neighborhood anchor"):
            native_anchor_selection(malformed)
