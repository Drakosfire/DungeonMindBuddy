"""Whole Buddy World Graph → DungeonMind v5 adoption-readiness conformance proofs (v4)."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import pytest

import apps.live_control_server.integrations.dungeonmind_kernel.whole_world_conformance_v4 as wwc_v4
import graph_memory.kernel as kernel
from apps.live_control_server.config import world_graph_root
from apps.live_control_server.integrations.dungeonmind_kernel.whole_world_conformance import (
    snapshot_world_graph_tree_digest,
)
from apps.live_control_server.integrations.dungeonmind_kernel.whole_world_conformance_v4 import (
    WHOLE_WORLD_CONFORMANCE_REPORT_SCHEMA_V4,
    WholeWorldConformanceError,
    _EDGE_SPECIFIC_PREDICATE_OVERRIDES_V4,
    analyze_exact_buddy_world_revision_v4,
    build_exact_dungeonmind_adoption_revision_v4,
    compact_whole_world_conformance_report_v4,
    resolve_buddy_predicate_mapping_v4,
)
from graph_memory.union_supergraph.load import (
    DEFAULT_FIXTURE_PATH,
    load_union_supergraph_store,
)

WORLD_ID = "whole-world-conformance-v4"
CAMPAIGN_ID = "longmont-c2"
ELDYRWILD_WORLD_ID = "eldyrwild"
ELDYRWILD_REVISION_ID = "rev:3413bf6f5044cf2680233f5e37c90dcf"
ELDYRWILD_PAYLOAD_SHA256 = (
    "346c1fbfb3cbbf6d0e5ded1453fdd7760264a5106022e398d6074679799ab0fa"
)
V4_FIXTURE_PATH = (
    Path(__file__).resolve().parent
    / "fixtures"
    / "dungeonmind_kernel"
    / "eldyrwild_post_v29_conformance_v1.json"
)
V3_FIXTURE_PATH = (
    Path(__file__).resolve().parent
    / "fixtures"
    / "dungeonmind_kernel"
    / "eldyrwild_post_v28_conformance_v1.json"
)
ADJUDICATION_FIXTURE_PATH = (
    Path(__file__).resolve().parent
    / "fixtures"
    / "dungeonmind_kernel"
    / "eldyrwild_relationship_residual_adjudication_v1.json"
)
_CONTRIBUTION_SEQ = 0

_EXPECTED_RESIDUAL_BY_PREDICATE = {
    "carries": 4,
    "carries_report_to": 1,
    "contains": 2,
    "controls_comms_with": 2,
    "identified_as": 4,
    "leads": 2,
    "leads_to": 5,
    "located_in": 5,
    "member_of": 1,
    "mission_targets": 1,
    "objective_of": 2,
    "part_of": 3,
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

_APPROVED_OVERRIDE_EDGE_IDS = frozenset(_EDGE_SPECIFIC_PREDICATE_OVERRIDES_V4)


@pytest.fixture
def seeded_root(tmp_path: Path) -> Path:
    kernel.publish_world_revision(
        tmp_path,
        WORLD_ID,
        load_union_supergraph_store(DEFAULT_FIXTURE_PATH),
        operation_ids=["op:whole-world-v4-baseline"],
    )
    return tmp_path


def _contribution(*assertions: Any):
    global _CONTRIBUTION_SEQ
    _CONTRIBUTION_SEQ += 1
    return kernel.create_graph_contribution(
        world_id=WORLD_ID,
        source_kind="manual_import",
        source_artifact_id="graph-native:whole-world-v4",
        source_revision_id=f"whole-world-v4-{_CONTRIBUTION_SEQ}",
        campaign_scope=CAMPAIGN_ID,
        accepted_assertions=list(assertions),
    )


def _publish_node(
    root: Path,
    *,
    node_id: str,
    kind: str,
    role: str,
) -> str:
    assertion = kernel.build_assertion(
        assertion_kind="node",
        acceptance_state="accepted",
        subject_node_id=node_id,
        label=f"Whole world v4 {kind}",
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


def _adjudication_owned_sets() -> tuple[set[str], set[str], set[str]]:
    payload = json.loads(ADJUDICATION_FIXTURE_PATH.read_text(encoding="utf-8"))
    records = payload["records"]
    all_ids = {row["edge_id"] for row in records}
    dm_ids = {
        row["edge_id"] for row in records if row["responsible_repo"] == "DungeonMind"
    }
    buddy_ids = {
        row["edge_id"]
        for row in records
        if row["responsible_repo"] == "DungeonMindBuddy"
    }
    assert len(all_ids) == 59
    assert len(dm_ids) == 4
    assert len(buddy_ids) == 55
    assert dm_ids | buddy_ids == all_ids
    assert dm_ids & buddy_ids == set()
    return all_ids, dm_ids, buddy_ids


def test_v4_contract_pins_and_target_schema() -> None:
    from dungeonmind.application.graph_snapshot import GRAPH_SCHEMA_V5
    from dungeonmind.application.semantic_profiles import descriptor_sha256
    from dungeonmind.contracts.evidence import EVIDENCE_REF_V2_SCHEMA, SOURCE_ARTIFACT_V2_SCHEMA
    from dungeonmind.contracts.knowledge_assertion import KNOWLEDGE_ASSERTION_METADATA_SCHEMA
    from dungeonmind_dnd.application.world_object_vocabulary import (
        builtin_world_object_v4_vocabulary_ref,
        load_builtin_v3_descriptor,
        load_builtin_world_object_v4_vocabulary,
        vocabulary_sha256,
    )
    from dungeonmind_dnd.application.world_property_vocabulary import (
        builtin_world_property_v2_vocabulary_ref,
        load_builtin_world_property_v2_vocabulary,
        world_property_vocabulary_sha256,
    )

    vocab = load_builtin_world_object_v4_vocabulary()
    ref = builtin_world_object_v4_vocabulary_ref()
    prop = load_builtin_world_property_v2_vocabulary()
    prop_ref = builtin_world_property_v2_vocabulary_ref()
    profile = load_builtin_v3_descriptor()

    assert ref.vocabulary_revision == "world-object-v4"
    assert ref.catalog_sha256 == (
        "552c59a3fa9a20e437294d1a77974c05e37b69ec95e5ea03337a7d010e4d287b"
    )
    assert vocabulary_sha256(vocab) == ref.catalog_sha256
    assert prop_ref.vocabulary_revision == "world-property-v2"
    assert world_property_vocabulary_sha256(prop) == (
        "8ad4c223e83ce48cf5cd33a33e10f5be5d48a80ad742784d7c561470b450ab73"
    )
    assert profile.profile_revision == "dnd5e-profile-v3"
    assert descriptor_sha256(profile) == (
        "2199e8fb96e917c22718e6aec59cbbf55a37ee81575e1bcf16ce13fae0393496"
    )
    assert GRAPH_SCHEMA_V5 == "dm_union_graph_v5"
    assert SOURCE_ARTIFACT_V2_SCHEMA == "dm_source_artifact_v2"
    assert EVIDENCE_REF_V2_SCHEMA == "dm_evidence_ref_v2"
    assert KNOWLEDGE_ASSERTION_METADATA_SCHEMA == "dm_knowledge_assertion_metadata_v1"
    assert WHOLE_WORLD_CONFORMANCE_REPORT_SCHEMA_V4 == (
        "dmb_dungeonmind_whole_world_conformance_report_v4"
    )
    assert not hasattr(wwc_v4, "load_latest_whole_world_conformance")
    assert not hasattr(wwc_v4, "analyze_current_buddy_world_revision")


def test_historical_digests_and_v3_fixture_remain_immutable() -> None:
    from dungeonmind_dnd.application.world_object_vocabulary import (
        load_builtin_world_object_v3_vocabulary,
        load_builtin_world_object_vocabulary,
        load_builtin_world_object_v2_vocabulary,
        vocabulary_sha256,
    )
    from dungeonmind_dnd.application.world_property_vocabulary import (
        load_builtin_world_property_vocabulary,
        world_property_vocabulary_sha256,
    )

    assert vocabulary_sha256(load_builtin_world_object_vocabulary()) == (
        "7cc3b285611ed13eb01e0cdc8a963cfa0bea3130abe0ce816204ab67186cb880"
    )
    assert vocabulary_sha256(load_builtin_world_object_v2_vocabulary()) == (
        "a53e2d0ec45878288800ff3d30006d54803db70a17e6680b359a0fa88f2a9922"
    )
    assert vocabulary_sha256(load_builtin_world_object_v3_vocabulary()) == (
        "d2f08de9ec3def308c8bc6d9d81132e5bbff9bd10b4bd706fc1cb39667b71a19"
    )
    assert world_property_vocabulary_sha256(load_builtin_world_property_vocabulary()) == (
        "b466e3f16ae1aba5814f3386dff86b7017399c6099158d99ef95e9979d7cea7f"
    )

    fixture = json.loads(V3_FIXTURE_PATH.read_text(encoding="utf-8"))
    assert fixture["schema_version"] == "dmb_dungeonmind_whole_world_conformance_report_v3"
    assert fixture["dungeonmind_dependency_ref"] == (
        "03ec801db99959153283312b72c13fafe56c54d1"
    )
    assert fixture["world_object_vocabulary_revision"] == "world-object-v3"
    assert fixture["world_property_vocabulary_revision"] == "world-property-v1"
    assert fixture["relationship_represented_count"] == 287
    assert fixture["relationship_residual_count"] == 59


def test_edge_specific_overrides_do_not_fire_outside_adjudication_domain(
    seeded_root: Path,
) -> None:
    """Approved Eldyrwild edge IDs in another world must not inherit overrides."""
    _publish_node(seeded_root, node_id="pc:a", kind="pc", role="player-character")
    _publish_node(seeded_root, node_id="npc:a", kind="npc", role="ally")
    _publish_node(seeded_root, node_id="group:a", kind="group", role="group")
    _publish_node(seeded_root, node_id="faction:a", kind="faction", role="organization")

    approved_comms = "edge:pc:caelynn:controls_comms_with:npc_grobnok"
    other_comms = "edge:pc:a:controls_comms_with:npc:a"
    approved_present = (
        "edge:node:fey_entity:present_at:pc:ephanna:appears-to-ephanna-in-prison"
    )
    other_present = "edge:faction:a:present_at:pc:a"
    approved_protects = (
        "edge:pc:bonogo:defends_weakened_location:node:prisoners_session9:protects"
    )
    other_protects = "edge:pc:a:defends_weakened_location:group:a"

    _publish_edge(
        seeded_root,
        edge_id=approved_comms,
        source_node_id="pc:a",
        target_node_id="npc:a",
        predicate="controls_comms_with",
    )
    _publish_edge(
        seeded_root,
        edge_id=other_comms,
        source_node_id="pc:a",
        target_node_id="npc:a",
        predicate="controls_comms_with",
    )
    _publish_edge(
        seeded_root,
        edge_id=approved_present,
        source_node_id="faction:a",
        target_node_id="pc:a",
        predicate="present_at",
    )
    _publish_edge(
        seeded_root,
        edge_id=other_present,
        source_node_id="faction:a",
        target_node_id="pc:a",
        predicate="present_at",
    )
    _publish_edge(
        seeded_root,
        edge_id=approved_protects,
        source_node_id="pc:a",
        target_node_id="group:a",
        predicate="defends_weakened_location",
    )
    revision_id = _publish_edge(
        seeded_root,
        edge_id=other_protects,
        source_node_id="pc:a",
        target_node_id="group:a",
        predicate="defends_weakened_location",
    )

    report = analyze_exact_buddy_world_revision_v4(
        root=seeded_root,
        world_id=WORLD_ID,
        revision_id=revision_id,
    )
    assert report.source_world_id != "eldyrwild"
    inv = {row.buddy_predicate: row for row in report.relationship_predicate_inventory}

    assert resolve_buddy_predicate_mapping_v4("controls_comms_with") is None
    assert resolve_buddy_predicate_mapping_v4("defends_weakened_location") is None
    assert resolve_buddy_predicate_mapping_v4("present_at") == ("dnd5e:present_at", False)

    # Same approved edge IDs remain residual / ordinary outside the adjudication domain.
    assert inv["controls_comms_with"].represented_count == 0
    assert inv["controls_comms_with"].residual_count == 2
    assert inv["defends_weakened_location"].represented_count == 0
    assert inv["defends_weakened_location"].residual_count == 2
    for pair in inv["controls_comms_with"].endpoint_pairs:
        assert pair.target_dungeonmind_term is None
    for pair in inv["defends_weakened_location"].endpoint_pairs:
        assert pair.target_dungeonmind_term is None

    present_pairs = {
        edge_id: pair
        for pair in inv["present_at"].endpoint_pairs
        for edge_id in pair.representative_edge_ids
    }
    # Ordinary present_at mapping applies; appears_to override must not fire.
    assert present_pairs[approved_present].target_dungeonmind_term == "dnd5e:present_at"
    assert present_pairs[other_present].target_dungeonmind_term == "dnd5e:present_at"
    assert approved_comms not in set(report.relationship_newly_represented_edge_ids)
    assert approved_protects not in set(report.relationship_newly_represented_edge_ids)
    assert approved_present not in set(report.relationship_newly_represented_edge_ids)

    for row in report.relationship_predicate_inventory:
        for pair in row.endpoint_pairs:
            assert pair.target_dungeonmind_term != "dnd5e:related_to"
            assert pair.target_dungeonmind_term != "dnd5e:appears_to"
            assert pair.target_dungeonmind_term != "dnd5e:protects"
            assert pair.target_dungeonmind_term != "dnd5e:communicates_with"


def test_edge_specific_override_requires_adjudication_domain_flag(
    seeded_root: Path,
) -> None:
    """Unit-level: override fires only when adjudication_domain=True."""
    from dungeonmind_dnd.application.world_object_vocabulary import (
        load_builtin_world_object_v4_vocabulary,
    )

    _publish_node(seeded_root, node_id="pc:a", kind="pc", role="player-character")
    _publish_node(seeded_root, node_id="npc:a", kind="npc", role="ally")
    revision_id = _publish_edge(
        seeded_root,
        edge_id="edge:pc:caelynn:controls_comms_with:npc_grobnok",
        source_node_id="pc:a",
        target_node_id="npc:a",
        predicate="controls_comms_with",
    )
    _, store = wwc_v4._load_exact_buddy_revision(
        root=seeded_root,
        world_id=WORLD_ID,
        revision_id=revision_id,
    )
    edge = store.edges["edge:pc:caelynn:controls_comms_with:npc_grobnok"]
    vocab = load_builtin_world_object_v4_vocabulary()

    off = wwc_v4._classify_edge_predicate_v4(
        edge, store, vocab, adjudication_domain=False
    )
    on = wwc_v4._classify_edge_predicate_v4(
        edge, store, vocab, adjudication_domain=True
    )
    assert off[3].value != "EXISTING_EXPLICIT_ADAPTER"
    assert off[4] is None
    assert on[3].value == "EXISTING_EXPLICIT_ADAPTER"
    assert on[4] == "dnd5e:communicates_with"


def test_wolf_part_of_uses_normal_endpoint_admission_not_override() -> None:
    from dungeonmind_dnd.application.world_object_vocabulary import (
        load_builtin_world_object_v4_vocabulary,
    )

    assert (
        "edge:node:wolf:part_of:item:session17:centipede_meat_creature"
        not in _EDGE_SPECIFIC_PREDICATE_OVERRIDES_V4
    )
    assert resolve_buddy_predicate_mapping_v4("part_of") == ("dnd5e:part_of", False)
    vocab = load_builtin_world_object_v4_vocabulary()
    part_of = next(p for p in vocab.predicates if p.term == "dnd5e:part_of")
    assert "dnd5e:npc" in part_of.subject_kinds
    assert "dnd5e:item" in part_of.object_kinds
    assert "dnd5e:group" not in part_of.subject_kinds
    assert "dnd5e:party" not in part_of.object_kinds
    assert "dnd5e:faction" not in part_of.subject_kinds


def test_part_of_rejects_unrelated_residual_shapes(seeded_root: Path) -> None:
    _publish_node(seeded_root, node_id="group:a", kind="group", role="group")
    _publish_node(seeded_root, node_id="loc:a", kind="location", role="city")
    _publish_node(seeded_root, node_id="party:a", kind="party", role="adventuring-party")
    _publish_node(seeded_root, node_id="faction:a", kind="faction", role="organization")
    _publish_node(seeded_root, node_id="npc:a", kind="npc", role="ally")
    _publish_node(seeded_root, node_id="item:a", kind="item", role="object")

    _publish_edge(
        seeded_root,
        edge_id="edge:group-part-loc",
        source_node_id="group:a",
        target_node_id="loc:a",
        predicate="part_of",
    )
    _publish_edge(
        seeded_root,
        edge_id="edge:loc-part-party",
        source_node_id="loc:a",
        target_node_id="party:a",
        predicate="part_of",
    )
    _publish_edge(
        seeded_root,
        edge_id="edge:faction-part-npc",
        source_node_id="faction:a",
        target_node_id="npc:a",
        predicate="part_of",
    )
    revision_id = _publish_edge(
        seeded_root,
        edge_id="edge:npc-part-item",
        source_node_id="npc:a",
        target_node_id="item:a",
        predicate="part_of",
    )
    report = analyze_exact_buddy_world_revision_v4(
        root=seeded_root,
        world_id=WORLD_ID,
        revision_id=revision_id,
    )
    row = next(r for r in report.relationship_predicate_inventory if r.buddy_predicate == "part_of")
    by_edge = {
        edge_id: pair
        for pair in row.endpoint_pairs
        for edge_id in pair.representative_edge_ids
    }
    assert by_edge["edge:npc-part-item"].represented_count == 1
    assert by_edge["edge:group-part-loc"].residual_count == 1
    assert by_edge["edge:loc-part-party"].residual_count == 1
    assert by_edge["edge:faction-part-npc"].residual_count == 1


def test_v4_build_refuses_not_ready(seeded_root: Path) -> None:
    revision_id = _publish_node(seeded_root, node_id="npc:a", kind="npc", role="ally")
    with pytest.raises(WholeWorldConformanceError, match="NOT_READY"):
        build_exact_dungeonmind_adoption_revision_v4(
            root=seeded_root,
            world_id=WORLD_ID,
            revision_id=revision_id,
        )


def test_non_adjudicated_world_marks_residuals_unadjudicated(seeded_root: Path) -> None:
    _publish_node(seeded_root, node_id="npc:a", kind="npc", role="ally")
    _publish_node(seeded_root, node_id="npc:b", kind="npc", role="ally")
    revision_id = _publish_edge(
        seeded_root,
        edge_id="edge:same",
        source_node_id="npc:a",
        target_node_id="npc:b",
        predicate="same_as",
    )
    report = analyze_exact_buddy_world_revision_v4(
        root=seeded_root,
        world_id=WORLD_ID,
        revision_id=revision_id,
    )
    assert report.relationship_residual_count >= 1
    assert report.unadjudicated_relationship_residual_count == report.relationship_residual_count
    assert report.dungeonmindbuddy_owned_relationship_residual_count == 0
    rel = next(
        b for b in report.blockers if b.blocker_class.value == "RELATIONSHIP_PREDICATE"
    )
    assert rel.responsible_repo == "DungeonMind"


def test_committed_eldyrwild_v4_fixture_is_durable_regression_contract() -> None:
    fixture = json.loads(V4_FIXTURE_PATH.read_text(encoding="utf-8"))
    assert fixture["schema_version"] == WHOLE_WORLD_CONFORMANCE_REPORT_SCHEMA_V4
    assert fixture["dungeonmind_dependency_ref"] == (
        "2e4fdc51f91c5c2a428500f7c2ece0d6742d04b4"
    )
    assert fixture["world_object_vocabulary_revision"] == "world-object-v4"
    assert fixture["world_object_vocabulary_sha256"] == (
        "552c59a3fa9a20e437294d1a77974c05e37b69ec95e5ea03337a7d010e4d287b"
    )
    assert fixture["world_property_vocabulary_revision"] == "world-property-v2"
    assert fixture["world_property_vocabulary_sha256"] == (
        "8ad4c223e83ce48cf5cd33a33e10f5be5d48a80ad742784d7c561470b450ab73"
    )
    assert fixture["source_world_id"] == ELDYRWILD_WORLD_ID
    assert fixture["source_revision_id"] == ELDYRWILD_REVISION_ID
    assert fixture["source_graph_payload_sha256"] == ELDYRWILD_PAYLOAD_SHA256
    assert fixture["relationship_semantic_count"] == 346
    assert fixture["relationship_represented_count"] == 291
    assert fixture["relationship_residual_count"] == 55
    assert fixture["uses_statblock_mechanics_count"] == 2
    assert fixture["role_field_count"] == 438
    assert fixture["role_property_adapter_count"] == 436
    assert fixture["role_external_resource_count"] == 2
    assert fixture["role_residual_count"] == 0
    assert fixture["classified_elements_count"] == 18106
    assert fixture["unaccounted_durable_elements"] == 0
    assert fixture["dungeonmind_owned_relationship_residual_count"] == 0
    assert fixture["dungeonmindbuddy_owned_relationship_residual_count"] == 55
    assert fixture["unadjudicated_relationship_residual_count"] == 0
    assert fixture["disposition"] == "WHOLE_GRAPH_ADOPTION_NOT_READY"
    assert "mapping_buckets" not in fixture

    all_ids, dm_ids, buddy_ids = _adjudication_owned_sets()
    newly = set(fixture["relationship_newly_represented_edge_ids"])
    residual = set(fixture["relationship_residual_edge_ids"])
    assert newly == dm_ids
    assert residual == buddy_ids
    assert newly | residual == all_ids
    assert newly & residual == set()
    assert newly - _APPROVED_OVERRIDE_EDGE_IDS == {
        "edge:node:wolf:part_of:item:session17:centipede_meat_creature"
    }

    residual_by = {
        row["key"]: row["count"] for row in fixture["residual_by_predicate"]
    }
    assert residual_by == _EXPECTED_RESIDUAL_BY_PREDICATE
    assert "defends_weakened_location" not in residual_by

    disp = {
        row["key"]: row["count"]
        for row in fixture["relationship_residual_disposition_inventory"]
    }
    assert disp == {
        "SOURCE_CORRECTION_REQUIRED": 35,
        "COMPOUND_ASSERTION_NOT_SINGLE_RELATIONSHIP": 10,
        "IDENTITY_NOT_RELATIONSHIP": 6,
        "EXPLICIT_ADAPTER_CANDIDATE": 3,
        "INSUFFICIENT_EVIDENCE": 1,
    }
    assert "NEW_PREDICATE_CANDIDATE" not in disp
    assert "EXISTING_TERM_ENDPOINT_EXTENSION_CANDIDATE" not in disp

    class_inv = {
        row["key"]: row["count"] for row in fixture["classification_inventory"]
    }
    assert class_inv == {
        "BUDDY_OPERATIONAL_ONLY": 3510,
        "DUNGEONMIND_SEMANTIC_CONTRACT_GAP": 55,
        "EXACTLY_REPRESENTABLE": 4333,
        "REPRESENTABLE_BY_EXPLICIT_ADAPTER": 6118,
        "SOURCE_MIGRATION_HISTORY": 4090,
    }

    blockers = {b["blocker_class"]: b for b in fixture["blockers"]}
    assert set(blockers) == {
        "CONTRIBUTION_HISTORY",
        "DURABLE_ADOPTION_BOUNDARY",
        "POSTGRES_ADOPTION",
        "RELATIONSHIP_PREDICATE",
    }
    assert blockers["RELATIONSHIP_PREDICATE"]["count"] == 55
    assert blockers["RELATIONSHIP_PREDICATE"]["responsible_repo"] == "DungeonMindBuddy"
    assert "Do not widen DungeonMind relationship vocabulary" in (
        blockers["RELATIONSHIP_PREDICATE"]["smallest_next_change"]
    )
    assert blockers["CONTRIBUTION_HISTORY"]["count"] == 4090
    assert blockers["CONTRIBUTION_HISTORY"]["responsible_repo"] == "DungeonMind"
    assert blockers["DURABLE_ADOPTION_BOUNDARY"]["count"] == 1
    assert blockers["DURABLE_ADOPTION_BOUNDARY"]["responsible_repo"] == "DungeonMind"
    assert blockers["POSTGRES_ADOPTION"]["count"] == 1
    assert blockers["POSTGRES_ADOPTION"]["responsible_repo"] == "DungeonMind"


def test_eldyrwild_v4_integration_when_present() -> None:
    root = world_graph_root()
    world_root = (root / "graph_memory" / "worlds" / ELDYRWILD_WORLD_ID).resolve()
    if not world_root.exists():
        world_root = (root / "worlds" / ELDYRWILD_WORLD_ID).resolve()
    if not world_root.exists():
        pytest.skip("Eldyrwild world graph not present")

    before = snapshot_world_graph_tree_digest(root, ELDYRWILD_WORLD_ID)
    report = analyze_exact_buddy_world_revision_v4(
        root=root,
        world_id=ELDYRWILD_WORLD_ID,
        revision_id=ELDYRWILD_REVISION_ID,
    )
    after = snapshot_world_graph_tree_digest(root, ELDYRWILD_WORLD_ID)
    assert before == after

    # Live regeneration must reproduce the committed fixture compact form.
    compact = compact_whole_world_conformance_report_v4(report)
    fixture = json.loads(V4_FIXTURE_PATH.read_text(encoding="utf-8"))
    assert compact == fixture
    assert report.source_revision_id == ELDYRWILD_REVISION_ID
    assert report.source_graph_payload_sha256 == ELDYRWILD_PAYLOAD_SHA256
    assert report.dungeonmind_owned_relationship_residual_count == 0
    assert report.dungeonmindbuddy_owned_relationship_residual_count == 55
    assert report.unadjudicated_relationship_residual_count == 0
    _, dm_ids, buddy_ids = _adjudication_owned_sets()
    assert set(report.relationship_newly_represented_edge_ids) == dm_ids
    assert set(report.relationship_residual_edge_ids) == buddy_ids


def _support_row(
    *,
    assertion_id: str,
    edge_id: str,
    support_state: str,
    active_contribution_ids: list[str] | None = None,
    contribution_id: str = "contribution:support-probe",
) -> dict[str, Any]:
    active = list(active_contribution_ids or [])
    return {
        "assertion_id": assertion_id,
        "assertion_kind": "edge",
        "graph_object_id": edge_id,
        "support_state": support_state,
        "active_contribution_ids": active,
        "introduced_by_contribution_id": contribution_id,
        "evidence_ref_ids": [],
        "source_artifact_ids": [],
        "per_contribution_evidence_ref_ids": {cid: [] for cid in active},
        "per_contribution_source_artifact_ids": {cid: [] for cid in active},
        "superseded_contribution_ids": [],
        "retracted_contribution_ids": [],
        "contradicted_contribution_ids": [],
        "provenance_lineage_version": 1,
    }


def _publish_mutated_store(root: Path, world_id: str, store: Any, op: str) -> str:
    result = kernel.publish_world_revision(
        root,
        world_id,
        store,
        operation_ids=[op],
    )
    return result.revision.revision_id


def test_current_support_matrix_controls_semantic_edge_membership(
    seeded_root: Path,
) -> None:
    """Support-currentness matrix with no edge-id-specific logic."""
    from graph_memory.union_supergraph.model import UnionSupergraphEdge

    root = seeded_root
    head, _rev, store = kernel.open_current_world_graph(root, WORLD_ID)
    assert head.head_revision_id
    store = kernel.load_world_graph_revision(root, WORLD_ID, head.head_revision_id)

    cases = [
        ("edge:matrix:no-support", None),
        (
            "edge:matrix:supported-active",
            _support_row(
                assertion_id="assertion:matrix:supported-active",
                edge_id="edge:matrix:supported-active",
                support_state="supported",
                active_contribution_ids=["contribution:matrix-a"],
            ),
        ),
        (
            "edge:matrix:supported-empty",
            _support_row(
                assertion_id="assertion:matrix:supported-empty",
                edge_id="edge:matrix:supported-empty",
                support_state="supported",
                active_contribution_ids=[],
            ),
        ),
        (
            "edge:matrix:contradicted",
            _support_row(
                assertion_id="assertion:matrix:contradicted",
                edge_id="edge:matrix:contradicted",
                support_state="contradicted",
                active_contribution_ids=[],
            ),
        ),
        (
            "edge:matrix:retracted",
            _support_row(
                assertion_id="assertion:matrix:retracted",
                edge_id="edge:matrix:retracted",
                support_state="retracted",
                active_contribution_ids=[],
            ),
        ),
        (
            "edge:matrix:unsupported",
            _support_row(
                assertion_id="assertion:matrix:unsupported",
                edge_id="edge:matrix:unsupported",
                support_state="unsupported",
                active_contribution_ids=[],
            ),
        ),
        (
            "edge:matrix:mixed",
            [
                _support_row(
                    assertion_id="assertion:matrix:mixed-old",
                    edge_id="edge:matrix:mixed",
                    support_state="contradicted",
                    active_contribution_ids=[],
                    contribution_id="contribution:matrix-old",
                ),
                _support_row(
                    assertion_id="assertion:matrix:mixed-new",
                    edge_id="edge:matrix:mixed",
                    support_state="supported",
                    active_contribution_ids=["contribution:matrix-new"],
                    contribution_id="contribution:matrix-new",
                ),
            ],
        ),
    ]

    # Ensure endpoint nodes exist for threatens classification.
    for node_id, kind in (
        ("npc:matrix-src", "npc"),
        ("npc:matrix-tgt", "npc"),
    ):
        if node_id not in store.nodes:
            from graph_memory.union_supergraph.model import UnionSupergraphNode

            store.nodes[node_id] = UnionSupergraphNode(
                node_id=node_id,
                label=node_id,
                kind=kind,
                role="probe",
                aliases=[],
                source_domains=["manual_seed"],
                evidence_ref_ids=[],
                state={},
            )

    expected_included = {
        "edge:matrix:no-support",
        "edge:matrix:supported-active",
        "edge:matrix:mixed",
    }
    expected_excluded = {
        "edge:matrix:supported-empty",
        "edge:matrix:contradicted",
        "edge:matrix:retracted",
        "edge:matrix:unsupported",
    }

    for edge_id, support in cases:
        store.edges[edge_id] = UnionSupergraphEdge(
            edge_id=edge_id,
            source_node_id="npc:matrix-src",
            target_node_id="npc:matrix-tgt",
            predicate="threatens",
            label="threatens",
            direction="outbound",
            source_domains=["manual_seed"],
            evidence_ref_ids=[],
            state={},
        )
        if support is None:
            continue
        rows = support if isinstance(support, list) else [support]
        for row in rows:
            store.assertion_support[row["assertion_id"]] = row

    rev = _publish_mutated_store(root, WORLD_ID, store, "op:support-matrix")
    report = analyze_exact_buddy_world_revision_v4(
        root=root, world_id=WORLD_ID, revision_id=rev
    )

    residual = set(report.relationship_residual_edge_ids)
    # represented set is not exported directly; infer via inventory counts and
    # residual absence for known admitted threatens edges.
    current_ids = wwc_v4._current_relationship_edge_ids(
        kernel.load_world_graph_revision(root, WORLD_ID, rev)
    )
    assert expected_included <= current_ids
    assert expected_excluded.isdisjoint(current_ids)
    assert expected_excluded.isdisjoint(residual)
    # Mixed edge is counted once, not twice.
    assert sum(1 for eid in current_ids if eid == "edge:matrix:mixed") == 1
    # No Lysandra/special-case constants in helper path.
    assert "lysandra" not in wwc_v4._edge_has_current_semantic_support.__code__.co_names


def test_correction_shaped_support_transition_preserves_semantic_count(
    seeded_root: Path,
) -> None:
    """Contradicted X stays durable history; X′ becomes current represented."""
    root = seeded_root
    world_id = WORLD_ID

    def _node(node_id: str, kind: str):
        return kernel.build_assertion(
            assertion_kind="node",
            acceptance_state="accepted",
            subject_node_id=node_id,
            label=node_id,
            campaign_scope=CAMPAIGN_ID,
            value={"kind": kind, "role": "probe", "source_domains": ["manual_seed"]},
            identity_resolution_outcome="created_new",
        )

    def _edge(
        *,
        edge_id: str,
        source_node_id: str,
        target_node_id: str,
        predicate: str,
        evidence_ref_id: str,
        source_artifact_id: str,
    ):
        return kernel.build_assertion(
            assertion_kind="edge",
            acceptance_state="accepted",
            subject_node_id=source_node_id,
            target_node_id=target_node_id,
            predicate=predicate,
            label=predicate,
            campaign_scope=CAMPAIGN_ID,
            visibility="gm",
            epistemic_kind="fact",
            identity_resolution_outcome="resolved_existing",
            evidence_ref_ids=[evidence_ref_id],
            source_artifact_id=source_artifact_id,
            value={
                "edge_id": edge_id,
                "source_node_id": source_node_id,
                "target_node_id": target_node_id,
                "predicate": predicate,
                "direction": "outbound",
                "source_domains": ["manual_seed"],
                "evidence": [
                    {
                        "evidence_ref_id": evidence_ref_id,
                        "source_artifact_id": source_artifact_id,
                        "source_domain": "manual_seed",
                    }
                ],
            },
        )

    source = kernel.create_graph_contribution(
        world_id=world_id,
        source_kind="manual_import",
        source_artifact_id="artifact:correction-shape:source",
        campaign_scope=CAMPAIGN_ID,
        accepted_assertions=[
            _node("npc:corr-a", "npc"),
            _node("npc:corr-b", "npc"),
            _node("faction:corr-c", "faction"),
            _edge(
                edge_id="edge:corr:x",
                source_node_id="npc:corr-a",
                target_node_id="npc:corr-b",
                predicate="same_as",
                evidence_ref_id="evidence:correction-shape:x",
                source_artifact_id="artifact:correction-shape:source",
            ),
        ],
    )
    published = kernel.merge_contribution_to_revision(
        root, world_id=world_id, contribution=source
    )
    assert published.published is True
    parent = published.revision_id
    assert parent

    x_assertion = next(
        a for a in source.accepted_assertions if a.assertion_kind == "edge"
    )
    before = snapshot_world_graph_tree_digest(root, world_id)
    report_p = analyze_exact_buddy_world_revision_v4(
        root=root, world_id=world_id, revision_id=parent
    )
    assert "edge:corr:x" in report_p.relationship_residual_edge_ids
    s_p = report_p.relationship_semantic_count
    r_p = report_p.relationship_represented_count
    d_p = report_p.relationship_residual_count
    m_p = report_p.uses_statblock_mechanics_count

    replacement = _edge(
        edge_id="edge:corr:xp",
        source_node_id="faction:corr-c",
        target_node_id="npc:corr-a",
        predicate="threatens",
        evidence_ref_id="evidence:correction-shape:xp",
        source_artifact_id="artifact:correction-shape:c",
    )
    correction = kernel.create_edge_assertion_correction_contribution(
        world_id=world_id,
        authored_by="gm-operator",
        target_contribution_id=source.contribution_id,
        target_assertion_id=x_assertion.assertion_id,
        replacement_assertion=replacement,
        source_artifact_id="artifact:correction-shape:c",
        campaign_scope=CAMPAIGN_ID,
    )
    corrected = kernel.correct_edge_assertion_support(
        root,
        world_id=world_id,
        contribution=correction,
        expected_parent_revision_id=parent,
    )
    assert corrected.published is True
    child = corrected.revision_id
    assert child

    report_q = analyze_exact_buddy_world_revision_v4(
        root=root, world_id=world_id, revision_id=child
    )
    after = snapshot_world_graph_tree_digest(root, world_id)
    # Analyzers must not mutate the graph; correction publish did, so digest changes
    # across the mutation itself. Re-snapshot Q and re-analyze to prove analyzer purity.
    before_q = snapshot_world_graph_tree_digest(root, world_id)
    report_q2 = analyze_exact_buddy_world_revision_v4(
        root=root, world_id=world_id, revision_id=child
    )
    after_q = snapshot_world_graph_tree_digest(root, world_id)
    assert before_q == after_q
    assert report_q2.relationship_semantic_count == report_q.relationship_semantic_count

    assert report_q.relationship_semantic_count == s_p
    assert report_q.relationship_represented_count == r_p + 1
    assert report_q.relationship_residual_count == d_p - 1
    assert report_q.uses_statblock_mechanics_count == m_p
    assert "edge:corr:x" not in report_q.relationship_residual_edge_ids
    assert "edge:corr:x" not in report_q.relationship_newly_represented_edge_ids
    assert "edge:corr:xp" not in report_q.relationship_residual_edge_ids

    store_q = kernel.load_world_graph_revision(root, world_id, child)
    assert "edge:corr:x" in store_q.edges
    assert "edge:corr:xp" in store_q.edges
    x_support = next(
        s
        for s in store_q.assertion_support.values()
        if s.get("graph_object_id") == "edge:corr:x"
    )
    assert x_support["support_state"] == "contradicted"
    assert source.contribution_id in (x_support.get("contradicted_contribution_ids") or [])

    # Historical X fields are accounted for but do not create current relationship blockers.
    x_field_items = [
        item
        for item in report_q.classification_inventory
        # classification_inventory is aggregated; inspect blockers instead
    ]
    rel_blockers = [
        b for b in report_q.blockers if b.blocker_class.value == "RELATIONSHIP_PREDICATE"
    ]
    for blocker in rel_blockers:
        assert "edge:corr:x" not in (blocker.examples or [])

    # Non-current edge must not appear as newly represented merely because v4 excluded it.
    assert "edge:corr:x" not in report_q.relationship_newly_represented_edge_ids
    assert before != after  # mutation happened via correction, not analyzer
    del x_field_items  # silence unused if inventory is aggregate-only


def test_historical_eldyrwild_anchor_v4_counts_unchanged_when_present() -> None:
    root = world_graph_root()
    world_root = (root / "graph_memory" / "worlds" / ELDYRWILD_WORLD_ID).resolve()
    if not world_root.exists():
        pytest.skip("Eldyrwild world graph not present")
    before = snapshot_world_graph_tree_digest(root, ELDYRWILD_WORLD_ID)
    report = analyze_exact_buddy_world_revision_v4(
        root=root,
        world_id=ELDYRWILD_WORLD_ID,
        revision_id=ELDYRWILD_REVISION_ID,
    )
    after = snapshot_world_graph_tree_digest(root, ELDYRWILD_WORLD_ID)
    assert before == after
    assert report.relationship_semantic_count == 346
    assert report.relationship_represented_count == 291
    assert report.relationship_residual_count == 55
    assert report.uses_statblock_mechanics_count == 2
