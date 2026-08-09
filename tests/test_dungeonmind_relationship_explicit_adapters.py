"""Eldyrwild explicit relationship adapter contract + post-adapter conformance."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import pytest

import graph_memory.kernel as kernel
from apps.live_control_server.config import world_graph_root
from apps.live_control_server.integrations.dungeonmind_kernel.relationship_explicit_adapter_conformance_v1 import (
    RELATIONSHIP_EXPLICIT_ADAPTER_CONFORMANCE_SCHEMA_V1,
    analyze_relationship_explicit_adapter_conformance_v1,
    compact_relationship_explicit_adapter_conformance_report_v1,
    derive_adjudication_explicit_adapter_edge_ids,
    derive_adjudication_remaining_residual_edge_ids,
)
from apps.live_control_server.integrations.dungeonmind_kernel.relationship_explicit_adapters_v1 import (
    RELATIONSHIP_EXPLICIT_ADAPTER_CATALOG_SCHEMA_V1,
    RelationshipExplicitAdapterIntegrityError,
    load_eldyrwild_relationship_explicit_adapter_catalog_v1,
    matches_explicit_adapter_domain_v1,
    resolve_relationship_explicit_adapter_v1,
)
from apps.live_control_server.integrations.dungeonmind_kernel.whole_world_conformance import (
    snapshot_world_graph_tree_digest,
)
from apps.live_control_server.integrations.dungeonmind_kernel.whole_world_conformance_v4 import (
    analyze_exact_buddy_world_revision_v4,
    resolve_buddy_predicate_mapping_v4,
)
from graph_memory.union_supergraph.load import (
    DEFAULT_FIXTURE_PATH,
    load_union_supergraph_store,
)
from graph_memory.union_supergraph.model import UnionSupergraphEdge

WORLD_ID = "explicit-adapters-v1"
CAMPAIGN_ID = "longmont-c2"
ELDYRWILD_WORLD_ID = "eldyrwild"
ELDYRWILD_REVISION_ID = "rev:3413bf6f5044cf2680233f5e37c90dcf"
ELDYRWILD_PAYLOAD_SHA256 = (
    "346c1fbfb3cbbf6d0e5ded1453fdd7760264a5106022e398d6074679799ab0fa"
)

FIXTURES = Path(__file__).resolve().parent / "fixtures" / "dungeonmind_kernel"
ADJUDICATION_FIXTURE_PATH = FIXTURES / "eldyrwild_relationship_residual_adjudication_v1.json"
V4_FIXTURE_PATH = FIXTURES / "eldyrwild_post_v29_conformance_v1.json"
ADAPTER_CONFORMANCE_FIXTURE_PATH = (
    FIXTURES / "eldyrwild_relationship_explicit_adapter_conformance_v1.json"
)

_EXPECTED_REMAINING_BY_PREDICATE = {
    "carries": 4,
    "carries_report_to": 1,
    "contains": 2,
    "controls_comms_with": 2,
    "identified_as": 4,
    "leads": 2,
    "leads_to": 4,
    "located_in": 4,
    "member_of": 1,
    "mission_targets": 1,
    "objective_of": 2,
    "part_of": 2,
    "part_of_group": 1,
    "participates_in": 6,
    "present_at": 1,
    "reports_threat_in": 1,
    "routes_to": 1,
    "same_as": 5,
    "serves": 3,
    "threatens": 1,
    "travels_to": 2,
    "within": 2,
}

_EXPECTED_REMAINING_DISPOSITIONS = {
    "SOURCE_CORRECTION_REQUIRED": 35,
    "COMPOUND_ASSERTION_NOT_SINGLE_RELATIONSHIP": 10,
    "IDENTITY_NOT_RELATIONSHIP": 6,
    "INSUFFICIENT_EVIDENCE": 1,
}

_CONTRIBUTION_SEQ = 0


@pytest.fixture
def seeded_root(tmp_path: Path) -> Path:
    kernel.publish_world_revision(
        tmp_path,
        WORLD_ID,
        load_union_supergraph_store(DEFAULT_FIXTURE_PATH),
        operation_ids=["op:explicit-adapters-v1-baseline"],
    )
    return tmp_path


def _contribution(*assertions: Any):
    global _CONTRIBUTION_SEQ
    _CONTRIBUTION_SEQ += 1
    return kernel.create_graph_contribution(
        world_id=WORLD_ID,
        source_kind="manual_import",
        source_artifact_id="graph-native:explicit-adapters-v1",
        source_revision_id=f"explicit-adapters-v1-{_CONTRIBUTION_SEQ}",
        campaign_scope=CAMPAIGN_ID,
        accepted_assertions=list(assertions),
    )


def _publish_node(root: Path, *, node_id: str, kind: str, role: str) -> str:
    assertion = kernel.build_assertion(
        assertion_kind="node",
        acceptance_state="accepted",
        subject_node_id=node_id,
        label=f"Adapter test {kind}",
        campaign_scope=CAMPAIGN_ID,
        value={"kind": kind, "role": role, "source_domains": ["manual_seed"]},
    )
    result = kernel.merge_contribution_to_revision(
        root, world_id=WORLD_ID, contribution=_contribution(assertion)
    )
    assert result.published and result.revision_id
    return result.revision_id


def _publish_edge(
    root: Path,
    *,
    edge_id: str,
    source_node_id: str,
    target_node_id: str,
    predicate: str,
) -> str:
    assertion = kernel.build_assertion(
        assertion_kind="edge",
        acceptance_state="accepted",
        subject_node_id=source_node_id,
        target_node_id=target_node_id,
        predicate=predicate,
        campaign_scope=CAMPAIGN_ID,
        value={"edge_id": edge_id, "direction": "outbound"},
    )
    result = kernel.merge_contribution_to_revision(
        root, world_id=WORLD_ID, contribution=_contribution(assertion)
    )
    assert result.published and result.revision_id
    return result.revision_id


def _edge(
    *,
    edge_id: str,
    source_node_id: str,
    target_node_id: str,
    predicate: str,
) -> UnionSupergraphEdge:
    return UnionSupergraphEdge(
        edge_id=edge_id,
        source_node_id=source_node_id,
        target_node_id=target_node_id,
        predicate=predicate,
        label=edge_id,
        direction="outbound",
        source_domains=["manual_seed"],
        evidence_ref_ids=[],
        state={},
    )


def _store_with_nodes(kinds: dict[str, str]):
    """Minimal store shape for resolver kind checks (nodes.<id>.kind only)."""
    from types import SimpleNamespace

    nodes = {
        node_id: SimpleNamespace(kind=kind) for node_id, kind in kinds.items()
    }
    return SimpleNamespace(nodes=nodes)


def _load_adjudication() -> dict[str, Any]:
    return json.loads(ADJUDICATION_FIXTURE_PATH.read_text(encoding="utf-8"))


def _adjudication_record(edge_id: str) -> dict[str, Any]:
    payload = _load_adjudication()
    for record in payload["records"]:
        if record["edge_id"] == edge_id:
            return record
    raise AssertionError(f"missing adjudication record {edge_id}")


def test_catalog_identity_matches_adjudication_oracle() -> None:
    catalog = load_eldyrwild_relationship_explicit_adapter_catalog_v1()
    adjudication = _load_adjudication()
    expected_ids = derive_adjudication_explicit_adapter_edge_ids(adjudication)
    assert len(expected_ids) == 3
    assert [r.edge_id for r in catalog.records] == expected_ids
    assert catalog.schema_version == RELATIONSHIP_EXPLICIT_ADAPTER_CATALOG_SCHEMA_V1

    by_id = {r.edge_id: r for r in catalog.records}
    for edge_id in expected_ids:
        adj = _adjudication_record(edge_id)
        row = by_id[edge_id]
        assert row.expected_buddy_predicate == adj["buddy_predicate"]
        assert row.expected_source_node_id == adj["source_node_id"]
        assert row.expected_source_buddy_kind == adj["source_buddy_kind"]
        assert row.expected_target_node_id == adj["target_node_id"]
        assert row.expected_target_buddy_kind == adj["target_buddy_kind"]
        assert row.dungeonmind_term == adj["candidate_dungeonmind_term"]
        assert row.reverse_endpoints == adj["reverse_endpoints"]
        assert row.requires_source_mutation is False
        assert adj["requires_source_mutation"] is False
        assert row.adjudication_reason_code == adj["reason_code"]
        assert row.adjudication_disposition == "EXPLICIT_ADAPTER_CANDIDATE"
        assert row.grounding_evidence_ref_id == adj["grounding_evidence_ref_id"]
        assert row.grounding_excerpt_sha256 == adj["grounding_excerpt_sha256"]


def test_seed_adapter_reverses_to_holds() -> None:
    catalog = load_eldyrwild_relationship_explicit_adapter_catalog_v1()
    store = _store_with_nodes(
        {"item:session17:seed": "item", "pc:stafl": "pc"}
    )
    edge = _edge(
        edge_id="edge:item:session17:seed:located_in:pc:stafl",
        source_node_id="item:session17:seed",
        target_node_id="pc:stafl",
        predicate="located_in",
    )
    resolved = resolve_relationship_explicit_adapter_v1(
        world_id=ELDYRWILD_WORLD_ID,
        revision_id=ELDYRWILD_REVISION_ID,
        graph_payload_sha256=ELDYRWILD_PAYLOAD_SHA256,
        edge=edge,
        store=store,
        catalog=catalog,
    )
    assert resolved is not None
    assert resolved.dungeonmind_term == "dnd5e:holds"
    assert resolved.reverse_endpoints is True
    assert resolved.effective_subject_node_id == "pc:stafl"
    assert resolved.effective_object_node_id == "item:session17:seed"
    assert resolved.effective_subject_dm_kind == "dnd5e:player_character"
    assert resolved.effective_object_dm_kind == "dnd5e:item"


def test_lesandra_adapter_reverses_to_leads() -> None:
    catalog = load_eldyrwild_relationship_explicit_adapter_catalog_v1()
    store = _store_with_nodes(
        {
            "node:cultists_of_longmont": "faction",
            "node:lesandra": "npc",
        }
    )
    edge = _edge(
        edge_id="edge:node:cultists_of_longmont:part_of:node:lesandra:led-by",
        source_node_id="node:cultists_of_longmont",
        target_node_id="node:lesandra",
        predicate="part_of",
    )
    resolved = resolve_relationship_explicit_adapter_v1(
        world_id=ELDYRWILD_WORLD_ID,
        revision_id=ELDYRWILD_REVISION_ID,
        graph_payload_sha256=ELDYRWILD_PAYLOAD_SHA256,
        edge=edge,
        store=store,
        catalog=catalog,
    )
    assert resolved is not None
    assert resolved.dungeonmind_term == "dnd5e:leads"
    assert resolved.reverse_endpoints is True
    assert resolved.effective_subject_node_id == "node:lesandra"
    assert resolved.effective_object_node_id == "node:cultists_of_longmont"
    assert resolved.effective_subject_dm_kind == "dnd5e:npc"
    assert resolved.effective_object_dm_kind == "dnd5e:faction"


def test_pippa_adapter_renames_to_travels_to() -> None:
    catalog = load_eldyrwild_relationship_explicit_adapter_catalog_v1()
    store = _store_with_nodes(
        {"node:pippa": "npc", "loc:stone_bridge": "location"}
    )
    edge = _edge(
        edge_id="edge:node:pippa:leads_to:loc:stone_bridge",
        source_node_id="node:pippa",
        target_node_id="loc:stone_bridge",
        predicate="leads_to",
    )
    resolved = resolve_relationship_explicit_adapter_v1(
        world_id=ELDYRWILD_WORLD_ID,
        revision_id=ELDYRWILD_REVISION_ID,
        graph_payload_sha256=ELDYRWILD_PAYLOAD_SHA256,
        edge=edge,
        store=store,
        catalog=catalog,
    )
    assert resolved is not None
    assert resolved.dungeonmind_term == "dnd5e:travels_to"
    assert resolved.reverse_endpoints is False
    assert resolved.effective_subject_node_id == "node:pippa"
    assert resolved.effective_object_node_id == "loc:stone_bridge"
    assert resolved.effective_subject_dm_kind == "dnd5e:npc"
    assert resolved.effective_object_dm_kind == "dnd5e:location"


def test_different_edge_id_same_predicate_does_not_adapt() -> None:
    catalog = load_eldyrwild_relationship_explicit_adapter_catalog_v1()
    store = _store_with_nodes({"item:other": "item", "pc:other": "pc"})
    edge = _edge(
        edge_id="edge:item:other:located_in:pc:other",
        source_node_id="item:other",
        target_node_id="pc:other",
        predicate="located_in",
    )
    assert (
        resolve_relationship_explicit_adapter_v1(
            world_id=ELDYRWILD_WORLD_ID,
            revision_id=ELDYRWILD_REVISION_ID,
            graph_payload_sha256=ELDYRWILD_PAYLOAD_SHA256,
            edge=edge,
            store=store,
            catalog=catalog,
        )
        is None
    )


@pytest.mark.parametrize(
    ("mutate",),
    [
        ("predicate",),
        ("source",),
        ("target",),
        ("source_kind",),
        ("target_kind",),
    ],
)
def test_catalog_edge_shape_drift_fails_closed(mutate: str) -> None:
    catalog = load_eldyrwild_relationship_explicit_adapter_catalog_v1()
    kinds = {"item:session17:seed": "item", "pc:stafl": "pc"}
    source = "item:session17:seed"
    target = "pc:stafl"
    predicate = "located_in"
    if mutate == "predicate":
        predicate = "carries"
    elif mutate == "source":
        kinds["item:other"] = "item"
        source = "item:other"
    elif mutate == "target":
        kinds["pc:other"] = "pc"
        target = "pc:other"
    elif mutate == "source_kind":
        kinds["item:session17:seed"] = "npc"
    elif mutate == "target_kind":
        kinds["pc:stafl"] = "npc"
    store = _store_with_nodes(kinds)
    edge = _edge(
        edge_id="edge:item:session17:seed:located_in:pc:stafl",
        source_node_id=source,
        target_node_id=target,
        predicate=predicate,
    )
    with pytest.raises(RelationshipExplicitAdapterIntegrityError):
        resolve_relationship_explicit_adapter_v1(
            world_id=ELDYRWILD_WORLD_ID,
            revision_id=ELDYRWILD_REVISION_ID,
            graph_payload_sha256=ELDYRWILD_PAYLOAD_SHA256,
            edge=edge,
            store=store,
            catalog=catalog,
        )


def test_outside_adjudication_domain_returns_none() -> None:
    catalog = load_eldyrwild_relationship_explicit_adapter_catalog_v1()
    store = _store_with_nodes(
        {"item:session17:seed": "item", "pc:stafl": "pc"}
    )
    edge = _edge(
        edge_id="edge:item:session17:seed:located_in:pc:stafl",
        source_node_id="item:session17:seed",
        target_node_id="pc:stafl",
        predicate="located_in",
    )
    assert (
        resolve_relationship_explicit_adapter_v1(
            world_id="other-world",
            revision_id=ELDYRWILD_REVISION_ID,
            graph_payload_sha256=ELDYRWILD_PAYLOAD_SHA256,
            edge=edge,
            store=store,
            catalog=catalog,
        )
        is None
    )
    assert not matches_explicit_adapter_domain_v1(
        world_id="other-world",
        revision_id=ELDYRWILD_REVISION_ID,
        graph_payload_sha256=ELDYRWILD_PAYLOAD_SHA256,
    )


def test_no_global_predicate_mappings_for_adapter_predicates() -> None:
    """located_in/part_of/leads_to must not globally become holds/leads/travels_to."""
    located = resolve_buddy_predicate_mapping_v4("located_in")
    part_of = resolve_buddy_predicate_mapping_v4("part_of")
    leads_to = resolve_buddy_predicate_mapping_v4("leads_to")
    assert located == ("dnd5e:located_in", False)
    assert part_of == ("dnd5e:part_of", False)
    assert leads_to == ("dnd5e:leads_to", False)


def test_synthetic_same_predicate_edges_do_not_inherit_adapters(
    seeded_root: Path,
) -> None:
    _publish_node(seeded_root, node_id="item:a", kind="item", role="item")
    _publish_node(seeded_root, node_id="pc:a", kind="pc", role="pc")
    _publish_node(seeded_root, node_id="faction:a", kind="faction", role="faction")
    _publish_node(seeded_root, node_id="npc:a", kind="npc", role="npc")
    _publish_node(seeded_root, node_id="loc:a", kind="location", role="location")
    _publish_edge(
        seeded_root,
        edge_id="edge:item:a:located_in:pc:a",
        source_node_id="item:a",
        target_node_id="pc:a",
        predicate="located_in",
    )
    _publish_edge(
        seeded_root,
        edge_id="edge:faction:a:part_of:npc:a",
        source_node_id="faction:a",
        target_node_id="npc:a",
        predicate="part_of",
    )
    revision_id = _publish_edge(
        seeded_root,
        edge_id="edge:npc:a:leads_to:loc:a",
        source_node_id="npc:a",
        target_node_id="loc:a",
        predicate="leads_to",
    )
    report = analyze_exact_buddy_world_revision_v4(
        root=seeded_root,
        world_id=WORLD_ID,
        revision_id=revision_id,
    )
    residual = set(report.relationship_residual_edge_ids)
    # None of these synthetic edges should be represented via adapter terms.
    assert "edge:item:a:located_in:pc:a" in residual or any(
        row.buddy_predicate == "located_in" and row.residual_count >= 1
        for row in report.relationship_predicate_inventory
    )
    # Adapter resolver itself returns None outside Eldyrwild domain.
    catalog = load_eldyrwild_relationship_explicit_adapter_catalog_v1()
    store = _store_with_nodes(
        {"item:a": "item", "pc:a": "pc", "faction:a": "faction", "npc:a": "npc", "loc:a": "location"}
    )
    for edge_id, src, tgt, pred in [
        ("edge:item:a:located_in:pc:a", "item:a", "pc:a", "located_in"),
        ("edge:faction:a:part_of:npc:a", "faction:a", "npc:a", "part_of"),
        ("edge:npc:a:leads_to:loc:a", "npc:a", "loc:a", "leads_to"),
    ]:
        assert (
            resolve_relationship_explicit_adapter_v1(
                world_id=WORLD_ID,
                revision_id=revision_id,
                graph_payload_sha256=report.source_graph_payload_sha256,
                edge=_edge(
                    edge_id=edge_id,
                    source_node_id=src,
                    target_node_id=tgt,
                    predicate=pred,
                ),
                store=store,
                catalog=catalog,
            )
            is None
        )


def test_no_forbidden_generic_adapter_behavior() -> None:
    catalog = load_eldyrwild_relationship_explicit_adapter_catalog_v1()
    for record in catalog.records:
        assert record.dungeonmind_term not in {
            "dnd5e:related_to",
            "related_to",
        }
        assert not record.dungeonmind_term.endswith(record.expected_buddy_predicate) or (
            # holds/leads/travels_to are not f"dnd5e:{buddy_predicate}"
            record.dungeonmind_term
            != f"dnd5e:{record.expected_buddy_predicate}"
        )


def test_committed_adapter_conformance_fixture_is_durable_regression_contract() -> None:
    fixture = json.loads(ADAPTER_CONFORMANCE_FIXTURE_PATH.read_text(encoding="utf-8"))
    adjudication = _load_adjudication()
    v4 = json.loads(V4_FIXTURE_PATH.read_text(encoding="utf-8"))

    expected_new = derive_adjudication_explicit_adapter_edge_ids(adjudication)
    expected_remaining = derive_adjudication_remaining_residual_edge_ids(adjudication)

    assert fixture["schema_version"] == RELATIONSHIP_EXPLICIT_ADAPTER_CONFORMANCE_SCHEMA_V1
    assert fixture["world_id"] == ELDYRWILD_WORLD_ID
    assert fixture["source_revision_id"] == ELDYRWILD_REVISION_ID
    assert fixture["source_graph_payload_sha256"] == ELDYRWILD_PAYLOAD_SHA256
    assert fixture["dungeonmind_dependency_ref"] == (
        "2e4fdc51f91c5c2a428500f7c2ece0d6742d04b4"
    )
    assert fixture["world_object_vocabulary_revision"] == "world-object-v4"
    assert fixture["world_object_vocabulary_sha256"] == (
        "552c59a3fa9a20e437294d1a77974c05e37b69ec95e5ea03337a7d010e4d287b"
    )

    assert fixture["base_relationship_semantic_count"] == 346
    assert fixture["base_relationship_represented_count"] == 291
    assert fixture["base_relationship_residual_count"] == 55
    assert fixture["uses_statblock_mechanics_count"] == 2
    assert fixture["adapter_candidate_count"] == 3
    assert fixture["adapter_applied_count"] == 3
    assert fixture["adapter_failed_count"] == 0
    assert fixture["effective_relationship_represented_count"] == 294
    assert fixture["effective_relationship_residual_count"] == 52

    assert fixture["newly_represented_edge_ids"] == expected_new
    assert fixture["remaining_residual_edge_ids"] == expected_remaining

    v4_residual = set(v4["relationship_residual_edge_ids"])
    newly = set(fixture["newly_represented_edge_ids"])
    remaining = set(fixture["remaining_residual_edge_ids"])
    assert v4_residual == newly | remaining
    assert newly.isdisjoint(remaining)
    assert len(newly) == 3
    assert len(remaining) == 52

    # Historical v4 fixture remains at 291/55.
    assert v4["relationship_represented_count"] == 291
    assert v4["relationship_residual_count"] == 55

    by_pred = {row["key"]: row["count"] for row in fixture["remaining_residual_by_predicate"]}
    assert by_pred == _EXPECTED_REMAINING_BY_PREDICATE
    assert sum(by_pred.values()) == 52

    by_disp = {
        row["key"]: row["count"]
        for row in fixture["remaining_residual_disposition_inventory"]
    }
    assert by_disp == _EXPECTED_REMAINING_DISPOSITIONS
    for forbidden in (
        "EXPLICIT_ADAPTER_CANDIDATE",
        "NEW_PREDICATE_CANDIDATE",
        "EXISTING_TERM_ENDPOINT_EXTENSION_CANDIDATE",
    ):
        assert forbidden not in by_disp

    assert fixture["dungeonmind_owned_remaining_count"] == 0
    assert fixture["dungeonmindbuddy_owned_remaining_count"] == 52
    assert fixture["unadjudicated_remaining_count"] == 0


def test_eldyrwild_adapter_conformance_when_present() -> None:
    root = world_graph_root()
    world_root = (root / "graph_memory" / "worlds" / ELDYRWILD_WORLD_ID).resolve()
    if not world_root.exists():
        world_root = (root / "worlds" / ELDYRWILD_WORLD_ID).resolve()
    if not world_root.exists():
        pytest.skip("Eldyrwild world graph not present")

    before = snapshot_world_graph_tree_digest(root, ELDYRWILD_WORLD_ID)
    v4 = analyze_exact_buddy_world_revision_v4(
        root=root,
        world_id=ELDYRWILD_WORLD_ID,
        revision_id=ELDYRWILD_REVISION_ID,
    )
    assert v4.relationship_residual_count == 55
    report = analyze_relationship_explicit_adapter_conformance_v1(
        root=root,
        world_id=ELDYRWILD_WORLD_ID,
        revision_id=ELDYRWILD_REVISION_ID,
        base_report=v4,
        world_graph_digest_before=before,
        world_graph_digest_after=snapshot_world_graph_tree_digest(root, ELDYRWILD_WORLD_ID),
    )
    after = snapshot_world_graph_tree_digest(root, ELDYRWILD_WORLD_ID)
    assert before == after
    assert report.world_graph_digest_before == report.world_graph_digest_after

    compact = compact_relationship_explicit_adapter_conformance_report_v1(report)
    # Digests are runtime-only; strip for fixture equality if fixture omits them.
    committed = json.loads(ADAPTER_CONFORMANCE_FIXTURE_PATH.read_text(encoding="utf-8"))
    compact_cmp = dict(compact)
    committed_cmp = dict(committed)
    compact_cmp.pop("world_graph_digest_before", None)
    compact_cmp.pop("world_graph_digest_after", None)
    committed_cmp.pop("world_graph_digest_before", None)
    committed_cmp.pop("world_graph_digest_after", None)
    assert compact_cmp == committed_cmp

    adjudication = _load_adjudication()
    assert report.newly_represented_edge_ids == derive_adjudication_explicit_adapter_edge_ids(
        adjudication
    )
    assert report.remaining_residual_edge_ids == (
        derive_adjudication_remaining_residual_edge_ids(adjudication)
    )
    assert report.adapter_applied_count == 3
    assert report.effective_relationship_residual_count == 52
