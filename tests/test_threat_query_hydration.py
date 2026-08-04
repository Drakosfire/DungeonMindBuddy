"""SBW10a exact Threat query/hydration owning-boundary tests."""
from __future__ import annotations

from pathlib import Path
from typing import Any
from unittest.mock import MagicMock

import pytest

from apps.live_control_server.integrations.dungeonmind_statblocks.errors import (
    downstream_not_found,
    downstream_unavailable,
)
from apps.live_control_server.integrations.dungeonmind_statblocks.models import (
    ExactRevisionResourceV1,
)
from apps.live_control_server.models.threat_query_hydration import (
    ThreatQueryHydrationRequestV1,
)
from apps.live_control_server.services.threat_query_hydration import (
    ThreatQueryHydrationError,
    query_threats_with_hydration,
)
from apps.live_control_server.services.world_graph_projection import (
    WorldGraphProjectionServiceError,
)
from graph_memory.projection.world_projection import (
    WorldGraphProjection,
    WorldGraphProjectionFocus,
    WorldGraphProjectionNodeView,
    WorldGraphProjectionRelationshipView,
    WorldGraphProjectionSnapshot,
    WorldGraphProjectionSummary,
    WorldGraphProjectionTrustBoundary,
    WorldGraphQueryContext,
)
from graph_memory.union_supergraph.statblock_binding import (
    EXTERNAL_RESOURCE_SCHEMA,
    THREAT_STATBLOCK_BINDING_SCHEMA,
    ThreatStatblockBindingV1,
    compute_binding_id,
    edge_id_from_binding_id,
    external_statblock_node_id,
)

WORLD = "world_eldyrwild"
CAMPAIGN = "campaign_eldyrwild"
REVISION = "rev_graph_pin_001"
DIGEST_A = "sha256:" + ("a" * 64)
DIGEST_B = "sha256:" + ("b" * 64)


def _binding(
    *,
    threat_id: str,
    statblock_id: str,
    revision_id: str,
    digest: str,
    role: str = "primary",
    phase_key: str | None = None,
    variant_label: str | None = None,
) -> ThreatStatblockBindingV1:
    binding_id = compute_binding_id(
        threat_node_id=threat_id,
        provider="dungeonmind",
        statblock_id=statblock_id,
        revision_id=revision_id,
        contract="dungeonmind.dungeonbuddy-statblocks",
        contract_version="1.0.0",
        definition_digest=digest,
        role=role,
        phase_key=phase_key,
        variant_label=variant_label,
    )
    return ThreatStatblockBindingV1(
        schema=THREAT_STATBLOCK_BINDING_SCHEMA,
        binding_id=binding_id,
        provider="dungeonmind",
        statblock_id=statblock_id,
        revision_id=revision_id,
        contract="dungeonmind.dungeonbuddy-statblocks",
        contract_version="1.0.0",
        definition_digest=digest,
        role=role,  # type: ignore[arg-type]
        phase_key=phase_key,
        variant_label=variant_label,
    )


def _threat_node(node_id: str, label: str, *, aliases: list[str] | None = None) -> WorldGraphProjectionNodeView:
    return WorldGraphProjectionNodeView(
        node_id=node_id,
        label=label,
        kind="threat",
        role="threat",
        aliases=list(aliases or []),
        summary=f"summary for {label}",
    )


def _resource_node(statblock_id: str) -> WorldGraphProjectionNodeView:
    return WorldGraphProjectionNodeView(
        node_id=external_statblock_node_id(statblock_id),
        label=f"statblock {statblock_id}",
        kind="external_resource",
        role="statblock",
        external_resource={
            "schema": EXTERNAL_RESOURCE_SCHEMA,
            "provider": "dungeonmind",
            "resource_type": "statblock",
            "resource_id": statblock_id,
            "contract": "dungeonmind.dungeonbuddy-statblocks",
            "contract_version": "1.0.0",
        },
    )


def _binding_rel(
    threat_id: str, binding: ThreatStatblockBindingV1
) -> WorldGraphProjectionRelationshipView:
    return WorldGraphProjectionRelationshipView(
        edge_id=edge_id_from_binding_id(binding.binding_id),
        source_node_id=threat_id,
        target_node_id=external_statblock_node_id(binding.statblock_id),
        predicate="uses_statblock",
        label="uses_statblock",
        direction="outgoing",
        threat_statblock_binding=binding,
    )


def _projection(
    *,
    nodes: list[WorldGraphProjectionNodeView],
    relationships: list[WorldGraphProjectionRelationshipView],
    matched_node_ids: list[str],
    match_reasons: dict[str, list[str]] | None = None,
    revision_id: str = REVISION,
    head_revision_id: str | None = None,
    query_context_relationships: list[WorldGraphProjectionRelationshipView] | None = None,
) -> WorldGraphProjection:
    snapshot = WorldGraphProjectionSnapshot(
        world_id=WORLD,
        campaign_id=CAMPAIGN,
        revision_id=revision_id,
        head_revision_id=head_revision_id or revision_id,
        is_head=head_revision_id is None or head_revision_id == revision_id,
        focus=WorldGraphProjectionFocus(kind="none"),
        admissibility="gm",
        scope_mode="campaign",
    )
    query_context = WorldGraphQueryContext(
        snapshot=snapshot,
        revision_id=revision_id,
        query_text="query",
        matched_node_ids=matched_node_ids,
        match_reasons=match_reasons or {},
        nodes=[n for n in nodes if n.node_id in matched_node_ids],
        # May be SEARCH_MAX truncated relative to projection.relationships.
        relationships=(
            list(query_context_relationships)
            if query_context_relationships is not None
            else list(relationships)
        ),
    )
    return WorldGraphProjection(
        schema="dmb_world_graph_projection_v1",
        snapshot=snapshot,
        summary=WorldGraphProjectionSummary(
            node_count=len(nodes),
            relationship_count=len(relationships),
            attribute_count=0,
            evidence_count=0,
            source_artifact_count=0,
        ),
        nodes=nodes,
        relationships=relationships,
        trust_boundary=WorldGraphProjectionTrustBoundary(),
        query_context=query_context,
    )


def _request(**overrides: Any) -> ThreatQueryHydrationRequestV1:
    payload = {
        "schema": "dmb_threat_query_hydration_request_v1",
        "world_id": WORLD,
        "campaign_id": CAMPAIGN,
        "revision_pin": REVISION,
        "query_text": "Float Goat",
        "include_mechanics": True,
    }
    payload.update(overrides)
    return ThreatQueryHydrationRequestV1.model_validate(payload)


def _exact(statblock_id: str, revision_id: str, digest: str) -> ExactRevisionResourceV1:
    return ExactRevisionResourceV1(
        statblock_id=statblock_id,
        revision_id=revision_id,
        definition_digest=digest,
        contract="dungeonmind.dungeonbuddy-statblocks",
        contract_version="1.0.0",
        definition={"name": "fixture"},
    )


def test_duplicate_labels_return_distinct_threat_ids() -> None:
    t1 = _threat_node("threat:float-goat-a", "Float Goat", aliases=["goat"])
    t2 = _threat_node("threat:float-goat-b", "Float Goat", aliases=["float goat"])
    proj = _projection(
        nodes=[t1, t2],
        relationships=[],
        matched_node_ids=[t1.node_id, t2.node_id],
        match_reasons={
            t1.node_id: ["exact_label"],
            t2.node_id: ["exact_alias"],
        },
    )
    client = MagicMock()
    response = query_threats_with_hydration(
        _request(),
        project_fn=lambda *_a, **_k: proj,
        client=client,
    )
    assert response.result_label == "threat_query_hydration_ok"
    assert [h.threat.node_id for h in response.hits] == sorted(
        [t1.node_id, t2.node_id], key=lambda x: x
    ) or len(response.hits) == 2
    ids = {h.threat.node_id for h in response.hits}
    assert ids == {t1.node_id, t2.node_id}
    assert all(h.mechanics_disposition == "no_binding" for h in response.hits)
    client.get_exact_revision.assert_not_called()


def test_alias_hit_preserves_canonical_node_id() -> None:
    threat = _threat_node("threat:mireward-siege", "Siege Beetle", aliases=["insectoid siege"])
    proj = _projection(
        nodes=[threat],
        relationships=[],
        matched_node_ids=[threat.node_id],
        match_reasons={threat.node_id: ["exact_alias"]},
    )
    response = query_threats_with_hydration(
        _request(query_text="insectoid siege"),
        project_fn=lambda *_a, **_k: proj,
        client=MagicMock(),
    )
    assert len(response.hits) == 1
    assert response.hits[0].threat.node_id == "threat:mireward-siege"
    assert "exact_alias" in response.hits[0].match_reasons


def test_zero_one_many_bindings_no_first_win() -> None:
    threat = _threat_node("threat:multi", "Multi Bound")
    b_primary = _binding(
        threat_id=threat.node_id,
        statblock_id="sb_primary01",
        revision_id="rev_primary01",
        digest=DIGEST_A,
        role="primary",
    )
    b_phase = _binding(
        threat_id=threat.node_id,
        statblock_id="sb_phase0001",
        revision_id="rev_phase0001",
        digest=DIGEST_B,
        role="phase",
        phase_key="enraged",
    )
    nodes = [threat, _resource_node("sb_primary01"), _resource_node("sb_phase0001")]
    rels = [_binding_rel(threat.node_id, b_primary), _binding_rel(threat.node_id, b_phase)]
    proj = _projection(nodes=nodes, relationships=rels, matched_node_ids=[threat.node_id])

    def get_exact(statblock_id: str, revision_id: str) -> ExactRevisionResourceV1:
        digest = DIGEST_A if statblock_id == "sb_primary01" else DIGEST_B
        return _exact(statblock_id, revision_id, digest)

    client = MagicMock()
    client.get_exact_revision.side_effect = get_exact
    response = query_threats_with_hydration(
        _request(),
        project_fn=lambda *_a, **_k: proj,
        client=client,
    )
    assert len(response.hits) == 1
    hit = response.hits[0]
    assert len(hit.bindings) == 2
    assert {b.binding_role for b in hit.bindings} == {"primary", "phase"}
    assert all(b.hydration_status == "available" for b in hit.bindings)
    assert hit.mechanics_disposition == "hydrated"
    assert client.get_exact_revision.call_count == 2


def test_server_unavailable_preserves_locator() -> None:
    threat = _threat_node("threat:one", "One")
    binding = _binding(
        threat_id=threat.node_id,
        statblock_id="sb_one000001",
        revision_id="rev_one000001",
        digest=DIGEST_A,
    )
    proj = _projection(
        nodes=[threat, _resource_node("sb_one000001")],
        relationships=[_binding_rel(threat.node_id, binding)],
        matched_node_ids=[threat.node_id],
    )
    client = MagicMock()
    client.get_exact_revision.side_effect = downstream_unavailable("downstream unavailable")
    response = query_threats_with_hydration(
        _request(),
        project_fn=lambda *_a, **_k: proj,
        client=client,
    )
    hit = response.hits[0]
    assert hit.mechanics_disposition == "unavailable"
    assert hit.bindings[0].hydration_status == "unavailable"
    assert hit.bindings[0].statblock_id == "sb_one000001"
    assert hit.bindings[0].revision is None
    assert response.result_label == "threat_query_hydration_partial"


def test_exact_revision_missing() -> None:
    threat = _threat_node("threat:miss", "Missing")
    binding = _binding(
        threat_id=threat.node_id,
        statblock_id="sb_miss00001",
        revision_id="rev_miss00001",
        digest=DIGEST_A,
    )
    proj = _projection(
        nodes=[threat, _resource_node("sb_miss00001")],
        relationships=[_binding_rel(threat.node_id, binding)],
        matched_node_ids=[threat.node_id],
    )
    client = MagicMock()
    client.get_exact_revision.side_effect = downstream_not_found("not found")
    response = query_threats_with_hydration(
        _request(),
        project_fn=lambda *_a, **_k: proj,
        client=client,
    )
    assert response.hits[0].bindings[0].hydration_status == "exact_revision_missing"


def test_definition_digest_mismatch_is_integrity() -> None:
    threat = _threat_node("threat:digest", "Digest")
    binding = _binding(
        threat_id=threat.node_id,
        statblock_id="sb_digest001",
        revision_id="rev_digest001",
        digest=DIGEST_A,
    )
    proj = _projection(
        nodes=[threat, _resource_node("sb_digest001")],
        relationships=[_binding_rel(threat.node_id, binding)],
        matched_node_ids=[threat.node_id],
    )
    client = MagicMock()
    client.get_exact_revision.return_value = _exact(
        "sb_digest001", "rev_digest001", DIGEST_B
    )
    response = query_threats_with_hydration(
        _request(),
        project_fn=lambda *_a, **_k: proj,
        client=client,
    )
    assert response.hits[0].bindings[0].hydration_status == "integrity_failure"
    assert response.hits[0].bindings[0].revision is None


def test_wrong_statblock_id_response_is_integrity() -> None:
    threat = _threat_node("threat:wrong", "Wrong")
    binding = _binding(
        threat_id=threat.node_id,
        statblock_id="sb_wrong0001",
        revision_id="rev_wrong0001",
        digest=DIGEST_A,
    )
    proj = _projection(
        nodes=[threat, _resource_node("sb_wrong0001")],
        relationships=[_binding_rel(threat.node_id, binding)],
        matched_node_ids=[threat.node_id],
    )
    client = MagicMock()
    client.get_exact_revision.return_value = _exact(
        "sb_other0001", "rev_wrong0001", DIGEST_A
    )
    response = query_threats_with_hydration(
        _request(),
        project_fn=lambda *_a, **_k: proj,
        client=client,
    )
    assert response.hits[0].bindings[0].hydration_status == "integrity_failure"


def test_two_threats_share_exact_mechanics() -> None:
    t1 = _threat_node("threat:share-a", "Share A")
    t2 = _threat_node("threat:share-b", "Share B")
    b1 = _binding(
        threat_id=t1.node_id,
        statblock_id="sb_shared001",
        revision_id="rev_shared001",
        digest=DIGEST_A,
    )
    b2 = _binding(
        threat_id=t2.node_id,
        statblock_id="sb_shared001",
        revision_id="rev_shared001",
        digest=DIGEST_A,
    )
    nodes = [t1, t2, _resource_node("sb_shared001")]
    rels = [_binding_rel(t1.node_id, b1), _binding_rel(t2.node_id, b2)]
    proj = _projection(
        nodes=nodes,
        relationships=rels,
        matched_node_ids=[t1.node_id, t2.node_id],
    )
    client = MagicMock()
    client.get_exact_revision.return_value = _exact(
        "sb_shared001", "rev_shared001", DIGEST_A
    )
    response = query_threats_with_hydration(
        _request(),
        project_fn=lambda *_a, **_k: proj,
        client=client,
    )
    assert len(response.hits) == 2
    assert {h.threat.node_id for h in response.hits} == {t1.node_id, t2.node_id}
    for hit in response.hits:
        assert hit.bindings[0].statblock_id == "sb_shared001"
        assert hit.bindings[0].hydration_status == "available"


def test_graph_head_advance_keeps_pin(tmp_path: Path) -> None:
    threat = _threat_node("threat:pin", "Pinned")
    proj = _projection(
        nodes=[threat],
        relationships=[],
        matched_node_ids=[threat.node_id],
        revision_id=REVISION,
        head_revision_id="rev_graph_head_newer",
    )
    seen: list[str | None] = []

    def project_fn(request: Any, *, root: Path | None = None) -> WorldGraphProjection:
        del root
        seen.append(request.revision_pin)
        return proj

    response = query_threats_with_hydration(
        _request(),
        project_fn=project_fn,
        client=MagicMock(),
    )
    assert seen == [REVISION]
    assert response.revision_id == REVISION
    assert response.hits[0].threat.node_id == threat.node_id


def test_projection_unavailable_maps_503() -> None:
    def project_fn(*_a: Any, **_k: Any) -> WorldGraphProjection:
        raise WorldGraphProjectionServiceError(
            "graph unavailable",
            code="projection_unavailable",
            status_code=503,
        )

    with pytest.raises(ThreatQueryHydrationError) as excinfo:
        query_threats_with_hydration(_request(), project_fn=project_fn, client=MagicMock())
    assert excinfo.value.status_code == 503
    assert excinfo.value.result_label == "threat_query_hydration_unavailable"


def test_resource_provider_mismatch_is_integrity() -> None:
    threat = _threat_node("threat:badres", "Bad Resource")
    binding = _binding(
        threat_id=threat.node_id,
        statblock_id="sb_badres001",
        revision_id="rev_badres001",
        digest=DIGEST_A,
    )
    # Same node id as expected target, but wrong provider/resource payload.
    bad_resource = WorldGraphProjectionNodeView(
        node_id=external_statblock_node_id("sb_badres001"),
        label="bad",
        kind="external_resource",
        role="statblock",
        external_resource={
            "schema": EXTERNAL_RESOURCE_SCHEMA,
            "provider": "dungeonmind",
            "resource_type": "statblock",
            "resource_id": "sb_other0001",
            "contract": "dungeonmind.dungeonbuddy-statblocks",
            "contract_version": "1.0.0",
        },
    )
    proj = _projection(
        nodes=[threat, bad_resource],
        relationships=[_binding_rel(threat.node_id, binding)],
        matched_node_ids=[threat.node_id],
    )
    response = query_threats_with_hydration(
        _request(),
        project_fn=lambda *_a, **_k: proj,
        client=MagicMock(),
    )
    assert response.hits[0].bindings[0].hydration_status == "integrity_failure"
    assert "external_resource_identity_mismatch" in (
        response.hits[0].bindings[0].message or ""
    )


def test_deterministic_ordering_across_replay() -> None:
    t_b = _threat_node("threat:b", "Beta")
    t_a = _threat_node("threat:a", "Alpha")
    proj = _projection(
        nodes=[t_b, t_a],
        relationships=[],
        matched_node_ids=[t_b.node_id, t_a.node_id],
    )
    first = query_threats_with_hydration(
        _request(), project_fn=lambda *_a, **_k: proj, client=MagicMock()
    )
    second = query_threats_with_hydration(
        _request(), project_fn=lambda *_a, **_k: proj, client=MagicMock()
    )
    assert [h.threat.node_id for h in first.hits] == [
        h.threat.node_id for h in second.hits
    ]
    assert [h.threat.node_id for h in first.hits] == ["threat:a", "threat:b"]


def test_no_durable_writes(tmp_path: Path) -> None:
    threat = _threat_node("threat:ro", "Readonly")
    proj = _projection(
        nodes=[threat],
        relationships=[],
        matched_node_ids=[threat.node_id],
    )
    before = {p.name: p.stat().st_mtime_ns for p in tmp_path.rglob("*") if p.is_file()}
    query_threats_with_hydration(
        _request(),
        root=tmp_path,
        project_fn=lambda *_a, **_k: proj,
        client=MagicMock(),
    )
    after = {p.name: p.stat().st_mtime_ns for p in tmp_path.rglob("*") if p.is_file()}
    assert before == after


def test_zero_direct_matches_returns_empty_not_all_threats() -> None:
    t1 = _threat_node("threat:a", "Alpha")
    t2 = _threat_node("threat:b", "Beta")
    proj = _projection(
        nodes=[t1, t2],
        relationships=[],
        matched_node_ids=[],
    )
    response = query_threats_with_hydration(
        _request(query_text="nonsense unrelated query"),
        project_fn=lambda *_a, **_k: proj,
        client=MagicMock(),
    )
    assert response.result_label == "threat_query_hydration_empty"
    assert response.hits == []


def test_relationship_discovery_from_matched_non_threat_location() -> None:
    location = WorldGraphProjectionNodeView(
        node_id="location:mireward",
        label="Mireward",
        kind="location",
        role="settlement",
    )
    threat = _threat_node("threat:latchling", "Latchling")
    rel = WorldGraphProjectionRelationshipView(
        edge_id="edge:latchling-located-in-mireward",
        source_node_id=threat.node_id,
        target_node_id=location.node_id,
        predicate="located_in",
        label="located_in",
        direction="outgoing",
    )
    proj = _projection(
        nodes=[location, threat],
        relationships=[rel],
        matched_node_ids=[location.node_id],
        match_reasons={location.node_id: ["exact_label"]},
    )
    response = query_threats_with_hydration(
        _request(query_text="Mireward-connected threats"),
        project_fn=lambda *_a, **_k: proj,
        client=MagicMock(),
    )
    assert len(response.hits) == 1
    assert response.hits[0].threat.node_id == threat.node_id
    assert any(
        r.startswith("related_to_match:location:mireward:located_in")
        for r in response.hits[0].match_reasons
    )


def test_focus_node_discovers_related_threat() -> None:
    capability = WorldGraphProjectionNodeView(
        node_id="capability:siege",
        label="Siege",
        kind="capability",
        role="capability",
    )
    threat = _threat_node("threat:siege-beetle", "Siege Beetle")
    rel = WorldGraphProjectionRelationshipView(
        edge_id="edge:beetle-has-siege",
        source_node_id=threat.node_id,
        target_node_id=capability.node_id,
        predicate="has_capability",
        label="has_capability",
        direction="outgoing",
    )
    proj = _projection(
        nodes=[capability, threat],
        relationships=[rel],
        matched_node_ids=[],
    )
    response = query_threats_with_hydration(
        _request(
            query_text="siege context",
            focus_node_ids=[capability.node_id],
            relationship_predicates=["has_capability"],
        ),
        project_fn=lambda *_a, **_k: proj,
        client=MagicMock(),
    )
    assert len(response.hits) == 1
    assert response.hits[0].threat.node_id == threat.node_id


def test_malformed_uses_statblock_is_integrity_not_no_binding() -> None:
    threat = _threat_node("threat:malformed", "Malformed")
    rel = WorldGraphProjectionRelationshipView(
        edge_id="edge:missing-binding-payload",
        source_node_id=threat.node_id,
        target_node_id=external_statblock_node_id("sb_missing01"),
        predicate="uses_statblock",
        label="uses_statblock",
        direction="outgoing",
        threat_statblock_binding=None,
    )
    proj = _projection(
        nodes=[threat],
        relationships=[rel],
        matched_node_ids=[threat.node_id],
    )
    response = query_threats_with_hydration(
        _request(),
        project_fn=lambda *_a, **_k: proj,
        client=MagicMock(),
    )
    assert len(response.hits) == 1
    hit = response.hits[0]
    assert hit.mechanics_disposition == "integrity_failure"
    assert len(hit.bindings) == 1
    binding = hit.bindings[0]
    assert binding.hydration_status == "integrity_failure"
    assert binding.message == "uses_statblock_binding_missing"
    assert binding.relationship_edge_id == "edge:missing-binding-payload"
    assert binding.binding_id is None
    assert binding.binding_role is None
    assert binding.statblock_id is None
    assert binding.revision_id is None
    assert binding.definition_digest is None
    assert response.result_label == "threat_query_hydration_integrity_failure"


def test_focus_unrelated_to_matched_query_node_discovers_threat() -> None:
    """Focus anchor discovers Threats even when the query match is elsewhere."""
    town_square = WorldGraphProjectionNodeView(
        node_id="location:town-square",
        label="Town Square",
        kind="location",
        role="settlement",
    )
    north_gate = WorldGraphProjectionNodeView(
        node_id="location:north-gate",
        label="North Gate",
        kind="location",
        role="settlement",
    )
    threat = _threat_node("threat:latchling", "Latchling")
    town_rel = WorldGraphProjectionRelationshipView(
        edge_id="edge:npc-at-town-square",
        source_node_id="npc:merchant",
        target_node_id=town_square.node_id,
        predicate="located_in",
        label="located_in",
        direction="outgoing",
    )
    gate_rel = WorldGraphProjectionRelationshipView(
        edge_id="edge:latchling-attacks-north-gate",
        source_node_id=threat.node_id,
        target_node_id=north_gate.node_id,
        predicate="attacks",
        label="attacks",
        direction="outgoing",
    )
    merchant = WorldGraphProjectionNodeView(
        node_id="npc:merchant",
        label="Merchant",
        kind="entity",
        role="civilian",
    )
    proj = _projection(
        nodes=[town_square, north_gate, threat, merchant],
        relationships=[town_rel, gate_rel],
        matched_node_ids=[town_square.node_id],
        match_reasons={town_square.node_id: ["exact_label"]},
    )
    response = query_threats_with_hydration(
        _request(
            query_text="town square",
            focus_node_ids=[north_gate.node_id],
            relationship_predicates=["attacks"],
        ),
        project_fn=lambda *_a, **_k: proj,
        client=MagicMock(),
    )
    assert len(response.hits) == 1
    assert response.hits[0].threat.node_id == threat.node_id
    assert any(
        r.startswith("related_to_match:location:north-gate:attacks")
        for r in response.hits[0].match_reasons
    )


def test_threat_edge_beyond_query_context_relationship_cap_still_discovered() -> None:
    """Discovery must walk projection.relationships, not SEARCH_MAX-capped context."""
    town_square = WorldGraphProjectionNodeView(
        node_id="location:town-square",
        label="Town Square",
        kind="location",
        role="settlement",
    )
    north_gate = WorldGraphProjectionNodeView(
        node_id="location:north-gate",
        label="North Gate",
        kind="location",
        role="settlement",
    )
    threat = _threat_node("threat:latchling", "Latchling")
    filler_rels = [
        WorldGraphProjectionRelationshipView(
            edge_id=f"edge:filler-{i}",
            source_node_id=f"npc:filler-{i}",
            target_node_id=town_square.node_id,
            predicate="located_in",
            label="located_in",
            direction="outgoing",
        )
        for i in range(3)
    ]
    filler_nodes = [
        WorldGraphProjectionNodeView(
            node_id=f"npc:filler-{i}",
            label=f"Filler {i}",
            kind="entity",
            role="civilian",
        )
        for i in range(3)
    ]
    threat_rel = WorldGraphProjectionRelationshipView(
        edge_id="edge:latchling-attacks-north-gate",
        source_node_id=threat.node_id,
        target_node_id=north_gate.node_id,
        predicate="attacks",
        label="attacks",
        direction="outgoing",
    )
    # Full projection includes the Threat edge; capped query context does not.
    full_rels = [*filler_rels, threat_rel]
    capped_context_rels = list(filler_rels)
    proj = _projection(
        nodes=[town_square, north_gate, threat, *filler_nodes],
        relationships=full_rels,
        matched_node_ids=[town_square.node_id],
        match_reasons={town_square.node_id: ["exact_label"]},
        query_context_relationships=capped_context_rels,
    )
    response = query_threats_with_hydration(
        _request(
            query_text="town square",
            focus_node_ids=[north_gate.node_id],
        ),
        project_fn=lambda *_a, **_k: proj,
        client=MagicMock(),
    )
    assert len(response.hits) == 1
    assert response.hits[0].threat.node_id == threat.node_id
    assert any(
        "related_to_match:location:north-gate:attacks" in r
        for r in response.hits[0].match_reasons
    )


def test_include_mechanics_false_is_not_requested_and_aggregates_ok() -> None:
    threat = _threat_node("threat:omit", "Omit Me")
    binding = _binding(
        threat_id=threat.node_id,
        statblock_id="sb_omit00001",
        revision_id="rev_omit00001",
        digest=DIGEST_A,
    )
    proj = _projection(
        nodes=[threat, _resource_node("sb_omit00001")],
        relationships=[_binding_rel(threat.node_id, binding)],
        matched_node_ids=[threat.node_id],
    )
    client = MagicMock()
    response = query_threats_with_hydration(
        _request(include_mechanics=False),
        project_fn=lambda *_a, **_k: proj,
        client=client,
    )
    client.get_exact_revision.assert_not_called()
    assert len(response.hits) == 1
    hit = response.hits[0]
    assert hit.bindings[0].hydration_status == "not_requested"
    assert hit.bindings[0].binding_id == binding.binding_id
    assert hit.bindings[0].statblock_id == "sb_omit00001"
    assert hit.mechanics_disposition == "not_requested"
    assert response.result_label == "threat_query_hydration_ok"


def test_wrong_direction_uses_statblock_is_integrity() -> None:
    threat = _threat_node("threat:dir", "Direction")
    binding = _binding(
        threat_id=threat.node_id,
        statblock_id="sb_dir000001",
        revision_id="rev_dir000001",
        digest=DIGEST_A,
    )
    rel = WorldGraphProjectionRelationshipView(
        edge_id=edge_id_from_binding_id(binding.binding_id),
        source_node_id=threat.node_id,
        target_node_id=external_statblock_node_id(binding.statblock_id),
        predicate="uses_statblock",
        label="uses_statblock",
        direction="incoming",
        threat_statblock_binding=binding,
    )
    proj = _projection(
        nodes=[threat, _resource_node("sb_dir000001")],
        relationships=[rel],
        matched_node_ids=[threat.node_id],
    )
    response = query_threats_with_hydration(
        _request(),
        project_fn=lambda *_a, **_k: proj,
        client=MagicMock(),
    )
    assert response.hits[0].bindings[0].message == "uses_statblock_wrong_direction"
    assert response.result_label == "threat_query_hydration_integrity_failure"


def test_all_integrity_bindings_aggregate_to_integrity_failure() -> None:
    threat = _threat_node("threat:allbad", "All Bad")
    binding = _binding(
        threat_id=threat.node_id,
        statblock_id="sb_allbad001",
        revision_id="rev_allbad001",
        digest=DIGEST_A,
    )
    bad_resource = WorldGraphProjectionNodeView(
        node_id=external_statblock_node_id("sb_allbad001"),
        label="bad",
        kind="external_resource",
        role="statblock",
        external_resource={
            "schema": EXTERNAL_RESOURCE_SCHEMA,
            "provider": "dungeonmind",
            "resource_type": "statblock",
            "resource_id": "sb_other0001",
            "contract": "dungeonmind.dungeonbuddy-statblocks",
            "contract_version": "1.0.0",
        },
    )
    proj = _projection(
        nodes=[threat, bad_resource],
        relationships=[_binding_rel(threat.node_id, binding)],
        matched_node_ids=[threat.node_id],
    )
    response = query_threats_with_hydration(
        _request(),
        project_fn=lambda *_a, **_k: proj,
        client=MagicMock(),
    )
    assert response.hits[0].mechanics_disposition == "integrity_failure"
    assert response.result_label == "threat_query_hydration_integrity_failure"


def test_no_binding_does_not_neutralize_integrity_hit() -> None:
    clean = _threat_node("threat:clean", "Clean")
    bad = _threat_node("threat:bad", "Bad")
    binding = _binding(
        threat_id=bad.node_id,
        statblock_id="sb_neutral01",
        revision_id="rev_neutral01",
        digest=DIGEST_A,
    )
    bad_resource = WorldGraphProjectionNodeView(
        node_id=external_statblock_node_id("sb_neutral01"),
        label="bad",
        kind="external_resource",
        role="statblock",
        external_resource={
            "schema": EXTERNAL_RESOURCE_SCHEMA,
            "provider": "dungeonmind",
            "resource_type": "statblock",
            "resource_id": "sb_other0001",
            "contract": "dungeonmind.dungeonbuddy-statblocks",
            "contract_version": "1.0.0",
        },
    )
    proj = _projection(
        nodes=[clean, bad, bad_resource],
        relationships=[_binding_rel(bad.node_id, binding)],
        matched_node_ids=[clean.node_id, bad.node_id],
    )
    response = query_threats_with_hydration(
        _request(),
        project_fn=lambda *_a, **_k: proj,
        client=MagicMock(),
    )
    assert any(h.mechanics_disposition == "no_binding" for h in response.hits)
    assert any(h.mechanics_disposition == "integrity_failure" for h in response.hits)
    assert response.result_label == "threat_query_hydration_integrity_failure"


def test_client_construction_failure_marks_bindings_unavailable() -> None:
    from apps.live_control_server.integrations.dungeonmind_statblocks.errors import (
        integration_misconfigured,
    )

    threat = _threat_node("threat:cfg", "Config")
    binding = _binding(
        threat_id=threat.node_id,
        statblock_id="sb_cfg000001",
        revision_id="rev_cfg000001",
        digest=DIGEST_A,
    )
    proj = _projection(
        nodes=[threat, _resource_node("sb_cfg000001")],
        relationships=[_binding_rel(threat.node_id, binding)],
        matched_node_ids=[threat.node_id],
    )

    def boom() -> Any:
        raise integration_misconfigured("client misconfigured")

    response = query_threats_with_hydration(
        _request(),
        project_fn=lambda *_a, **_k: proj,
        client=None,
        client_factory=boom,
    )
    assert response.hits[0].threat.node_id == threat.node_id
    assert response.hits[0].bindings[0].hydration_status == "unavailable"
    assert response.hits[0].bindings[0].statblock_id == "sb_cfg000001"
    assert response.result_label == "threat_query_hydration_partial"


def test_empty_query_does_not_construct_client() -> None:
    t1 = _threat_node("threat:a", "Alpha")
    proj = _projection(nodes=[t1], relationships=[], matched_node_ids=[])
    constructed = {"n": 0}

    def boom() -> Any:
        constructed["n"] += 1
        raise AssertionError("client must not be constructed")

    response = query_threats_with_hydration(
        _request(query_text="no matches"),
        project_fn=lambda *_a, **_k: proj,
        client=None,
        client_factory=boom,
    )
    assert constructed["n"] == 0
    assert response.result_label == "threat_query_hydration_empty"
