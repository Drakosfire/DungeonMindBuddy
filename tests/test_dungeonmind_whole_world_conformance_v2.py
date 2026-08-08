"""Whole Buddy World Graph → DungeonMind v5 adoption-readiness conformance proofs (v2)."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import pytest

import graph_memory.kernel as kernel
from apps.live_control_server.config import world_graph_root
from apps.live_control_server.integrations.dungeonmind_kernel.whole_world_conformance import (
    WHOLE_WORLD_CONFORMANCE_REPORT_SCHEMA,
    snapshot_world_graph_tree_digest,
)
from graph_memory.union_supergraph.load import (
    DEFAULT_FIXTURE_PATH,
    load_union_supergraph_store,
)
from graph_memory.union_supergraph.model import UnionSupergraphStore
import apps.live_control_server.integrations.dungeonmind_kernel.whole_world_conformance_v2 as wwc_v2
from apps.live_control_server.integrations.dungeonmind_kernel.whole_world_conformance_v2 import (
    WHOLE_WORLD_CONFORMANCE_REPORT_SCHEMA_V2,
    PredicateDisposition,
    WholeWorldConformanceError,
    analyze_exact_buddy_world_revision_v2,
    build_exact_dungeonmind_adoption_revision_v2,
)

WORLD_ID = "whole-world-conformance-v2"
CAMPAIGN_ID = "longmont-c2"
ELDYRWILD_WORLD_ID = "eldyrwild"
ELDYRWILD_REVISION_ID = "rev:3413bf6f5044cf2680233f5e37c90dcf"
ELDYRWILD_PAYLOAD_SHA256 = (
    "346c1fbfb3cbbf6d0e5ded1453fdd7760264a5106022e398d6074679799ab0fa"
)
ELDYRWILD_TREE_DIGEST = (
    "b79f956141424f7ed332d86f3249666c9353e048f2776364bcb09e65edff6a77"
)
FIXTURE_PATH = (
    Path(__file__).resolve().parent
    / "fixtures"
    / "dungeonmind_kernel"
    / "eldyrwild_post_v26_conformance_v1.json"
)
_CONTRIBUTION_SEQ = 0


@pytest.fixture
def seeded_root(tmp_path: Path) -> Path:
    kernel.publish_world_revision(
        tmp_path,
        WORLD_ID,
        load_union_supergraph_store(DEFAULT_FIXTURE_PATH),
        operation_ids=["op:whole-world-v2-baseline"],
    )
    return tmp_path


def _contribution(*assertions: Any):
    global _CONTRIBUTION_SEQ
    _CONTRIBUTION_SEQ += 1
    return kernel.create_graph_contribution(
        world_id=WORLD_ID,
        source_kind="manual_import",
        source_artifact_id="graph-native:whole-world-v2",
        source_revision_id=f"whole-world-v2-{_CONTRIBUTION_SEQ}",
        campaign_scope=CAMPAIGN_ID,
        accepted_assertions=list(assertions),
    )


def _publish_node(
    root: Path,
    *,
    node_id: str,
    kind: str,
    role: str,
    campaign_scope: str | None = CAMPAIGN_ID,
    epistemic_kind: str | None = None,
) -> str:
    value: dict[str, Any] = {"kind": kind, "role": role, "source_domains": ["manual_seed"]}
    assertion = kernel.build_assertion(
        assertion_kind="node",
        acceptance_state="accepted",
        subject_node_id=node_id,
        label=f"Whole world v2 {kind}",
        campaign_scope=campaign_scope,
        epistemic_kind=epistemic_kind,
        value=value,
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
    session_ids: list[str] | None = None,
) -> str:
    value: dict[str, Any] = {"edge_id": edge_id, "direction": "outbound"}
    if session_ids:
        value["session_ids"] = session_ids
    assertion = kernel.build_assertion(
        assertion_kind="edge",
        acceptance_state="accepted",
        subject_node_id=source_node_id,
        target_node_id=target_node_id,
        predicate=predicate,
        campaign_scope=CAMPAIGN_ID,
        value=value,
    )
    result = kernel.merge_contribution_to_revision(
        root, world_id=WORLD_ID, contribution=_contribution(assertion)
    )
    assert result.published and result.revision_id
    return result.revision_id


def test_v2_contract_pins_and_target_schema() -> None:
    from dungeonmind.application.graph_snapshot import GRAPH_SCHEMA_V5
    from dungeonmind.contracts.evidence import EVIDENCE_REF_V2_SCHEMA, SOURCE_ARTIFACT_V2_SCHEMA
    from dungeonmind_dnd.application.world_object_vocabulary import (
        builtin_world_object_v2_vocabulary_ref,
        load_builtin_world_object_v2_vocabulary,
    )

    vocab = load_builtin_world_object_v2_vocabulary()
    ref = builtin_world_object_v2_vocabulary_ref()
    assert ref.vocabulary_revision == "world-object-v2"
    assert ref.catalog_sha256 == "a53e2d0ec45878288800ff3d30006d54803db70a17e6680b359a0fa88f2a9922"
    assert vocab is not None
    assert GRAPH_SCHEMA_V5 == "dm_union_graph_v5"
    assert SOURCE_ARTIFACT_V2_SCHEMA == "dm_source_artifact_v2"
    assert EVIDENCE_REF_V2_SCHEMA == "dm_evidence_ref_v2"
    assert WHOLE_WORLD_CONFORMANCE_REPORT_SCHEMA_V2 == (
        "dmb_dungeonmind_whole_world_conformance_report_v2"
    )
    assert WHOLE_WORLD_CONFORMANCE_REPORT_SCHEMA == (
        "dmb_dungeonmind_whole_world_conformance_report_v1"
    )


def test_v2_kind_adapters_and_unrecognized_kind(
    seeded_root: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    revision_id = _publish_node(seeded_root, node_id="item:v2", kind="item", role="object")
    for kind in ("mystery", "group", "party", "event"):
        _publish_node(seeded_root, node_id=f"{kind}:v2", kind=kind, role=kind)
    revision_id = _publish_node(seeded_root, node_id="bad:v2", kind="not_a_real_kind", role="unknown")

    original_load = wwc_v2._load_exact_buddy_revision

    def _load_with_external_resource(*, root: Path, world_id: str, revision_id: str):
        manifest, store = original_load(root=root, world_id=world_id, revision_id=revision_id)
        payload = store.model_dump(mode="python", by_alias=True)
        payload["nodes"]["ext:v2"] = {
            "node_id": "ext:v2",
            "label": "External statblock",
            "kind": "external_resource",
            "role": "statblock",
            "source_domains": ["statblock"],
            "evidence_ref_ids": [],
            "state": {},
            "external_resource": {
                "schema": "dmb_external_resource_v1",
                "provider": "dungeonmind",
                "resource_type": "statblock",
                "resource_id": "sb_test0001",
                "contract": "dungeonmind.dungeonbuddy-statblocks",
                "contract_version": "1.0.0",
            },
        }
        return manifest, UnionSupergraphStore.model_validate(payload)

    monkeypatch.setattr(wwc_v2, "_load_exact_buddy_revision", _load_with_external_resource)

    report = analyze_exact_buddy_world_revision_v2(
        root=seeded_root,
        world_id=WORLD_ID,
        revision_id=revision_id,
    )
    kind_map = {row.key: row.count for row in report.kind_inventory}
    for kind in ("item", "mystery", "group", "party", "event", "external_resource"):
        assert kind in kind_map

    mapped_buckets = [
        bucket
        for bucket in report.mapping_buckets
        if bucket.element_family == "node_field"
        and bucket.classification.value == "REPRESENTABLE_BY_EXPLICIT_ADAPTER"
        and any("dnd5e:" in note for note in bucket.notes)
    ]
    assert mapped_buckets
    assert report.disposition == "WHOLE_GRAPH_ADOPTION_NOT_READY"
    assert any(
        bucket.classification.value == "DUNGEONMIND_SEMANTIC_CONTRACT_GAP"
        and any("not_a_real_kind" in note for note in bucket.notes)
        for bucket in report.mapping_buckets
        if bucket.element_family == "node_field"
    )


def test_v2_campaign_scope_epistemic_and_session_refs(
    seeded_root: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    revision_id = _publish_node(
        seeded_root,
        node_id="npc:scope",
        kind="npc",
        role="ally",
        campaign_scope=CAMPAIGN_ID,
        epistemic_kind="fact",
    )
    _publish_node(
        seeded_root,
        node_id="npc:derived",
        kind="npc",
        role="ally",
        epistemic_kind="source_derived_candidate",
    )
    original_load = wwc_v2._load_exact_buddy_revision

    def _load_with_empty_scope(*, root: Path, world_id: str, revision_id: str):
        manifest, store = original_load(root=root, world_id=world_id, revision_id=revision_id)
        payload = store.model_dump(mode="python", by_alias=True)
        first_node_id = next(iter(payload["nodes"]))
        payload["nodes"][first_node_id]["state"]["campaign_scope"] = ""
        return manifest, UnionSupergraphStore.model_validate(payload)

    monkeypatch.setattr(wwc_v2, "_load_exact_buddy_revision", _load_with_empty_scope)
    _publish_edge(
        seeded_root,
        edge_id="edge:session",
        source_node_id="npc:scope",
        target_node_id="npc:derived",
        predicate="threatens",
        session_ids=["session:42"],
    )
    revision_id = _publish_edge(
        seeded_root,
        edge_id="edge:session2",
        source_node_id="npc:scope",
        target_node_id="npc:derived",
        predicate="participates_in",
        session_ids=["session:43"],
    )

    report = analyze_exact_buddy_world_revision_v2(
        root=seeded_root,
        world_id=WORLD_ID,
        revision_id=revision_id,
    )
    assert any(
        bucket.element_family == "node_state"
        and bucket.classification.value == "EXACTLY_REPRESENTABLE"
        and any("EpistemicKindV2.fact" in note for note in bucket.notes)
        for bucket in report.mapping_buckets
    )
    assert any(
        bucket.element_family == "node_state"
        and bucket.classification.value == "EXACTLY_REPRESENTABLE"
        and any("source_derived_candidate" in note for note in bucket.notes)
        for bucket in report.mapping_buckets
    )
    assert any(
        bucket.element_family == "edge_session_refs"
        and bucket.classification.value == "REPRESENTABLE_BY_EXPLICIT_ADAPTER"
        and any("session_refs" in note for note in bucket.notes)
        for bucket in report.mapping_buckets
    )
    assert not any(blocker.blocker_class.value == "FICTIONAL_TIME" for blocker in report.blockers)
    assert any(
        bucket.element_family == "node_state"
        and bucket.classification.value == "INVALID_SOURCE"
        and any("empty or malformed campaign_scope" in note for note in bucket.notes)
        for bucket in report.mapping_buckets
    )


def test_v2_null_campaign_scope_is_world_universal(seeded_root: Path) -> None:
    revision_id = _publish_node(
        seeded_root,
        node_id="npc:universal",
        kind="npc",
        role="ally",
        campaign_scope=None,
    )
    report = analyze_exact_buddy_world_revision_v2(
        root=seeded_root,
        world_id=WORLD_ID,
        revision_id=revision_id,
    )
    assert any(
        bucket.element_family == "node_state"
        and bucket.classification.value == "EXACTLY_REPRESENTABLE"
        and any("world-universal" in note for note in bucket.notes)
        for bucket in report.mapping_buckets
    )


def test_v2_provenance_statblock_party_registry_and_authority_visibility(
    seeded_root: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    revision_id = _publish_node(seeded_root, node_id="npc:prov", kind="npc", role="ally")
    original_load = wwc_v2._load_exact_buddy_revision

    def _load_with_provenance(*, root: Path, world_id: str, revision_id: str):
        manifest, store = original_load(root=root, world_id=world_id, revision_id=revision_id)
        payload = store.model_dump(mode="python", by_alias=True)
        payload["source_artifacts"]["artifact:statblock"] = {
            "schema_version": "dmb_source_artifact_v1",
            "source_artifact_id": "artifact:statblock",
            "source_domain": "statblock",
            "campaign_id": CAMPAIGN_ID,
            "uri": "file://statblock",
            "status": "active",
            "authority_state": "reviewed",
            "visibility_state": "player_safe",
        }
        payload["source_artifacts"]["artifact:party"] = {
            "schema_version": "dmb_source_artifact_v1",
            "source_artifact_id": "artifact:party",
            "source_domain": "party_registry",
            "campaign_id": CAMPAIGN_ID,
            "uri": "file://party",
            "status": "active",
        }
        return manifest, UnionSupergraphStore.model_validate(payload)

    monkeypatch.setattr(wwc_v2, "_load_exact_buddy_revision", _load_with_provenance)
    report = analyze_exact_buddy_world_revision_v2(
        root=seeded_root,
        world_id=WORLD_ID,
        revision_id=revision_id,
    )
    statblock_buckets = [
        bucket
        for bucket in report.mapping_buckets
        if bucket.element_family == "source_artifact_field"
        and any("statblock" in note for note in bucket.notes)
    ]
    assert statblock_buckets
    assert all(
        bucket.classification.value != "DUNGEONMIND_SEMANTIC_CONTRACT_GAP"
        for bucket in statblock_buckets
        if any("source_domain_key='statblock'" in note for note in bucket.notes)
    )
    authority_buckets = [
        bucket
        for bucket in report.mapping_buckets
        if bucket.element_family == "source_artifact_field"
        and bucket.classification.value == "EXACTLY_REPRESENTABLE"
        and any("review_state" in note for note in bucket.notes)
    ]
    assert authority_buckets
    visibility_buckets = [
        bucket
        for bucket in report.mapping_buckets
        if bucket.element_family == "source_artifact_field"
        and bucket.classification.value == "REPRESENTABLE_BY_EXPLICIT_ADAPTER"
        and any("source_visibility_state" in note for note in bucket.notes)
    ]
    assert visibility_buckets
    assert not any(
        bucket.element_family == "source_artifact_field"
        and any("Visibility.player" in note for note in bucket.notes)
        for bucket in report.mapping_buckets
    )


def test_v2_relationship_inventory_completeness_and_dispositions(seeded_root: Path) -> None:
    _publish_node(seeded_root, node_id="fac:v2", kind="faction", role="organization")
    _publish_node(seeded_root, node_id="npc:v2", kind="npc", role="ally")
    _publish_node(seeded_root, node_id="loc:v2", kind="location", role="place")
    _publish_node(seeded_root, node_id="threat:v2", kind="threat", role="threat")
    _publish_node(seeded_root, node_id="item:v2", kind="item", role="object")
    _publish_edge(
        seeded_root,
        edge_id="edge:member",
        source_node_id="npc:v2",
        target_node_id="fac:v2",
        predicate="member_of",
    )
    _publish_edge(
        seeded_root,
        edge_id="edge:located",
        source_node_id="threat:v2",
        target_node_id="loc:v2",
        predicate="located_in",
    )
    _publish_edge(
        seeded_root,
        edge_id="edge:attacks",
        source_node_id="threat:v2",
        target_node_id="npc:v2",
        predicate="attacks",
    )
    _publish_edge(
        seeded_root,
        edge_id="edge:contains",
        source_node_id="loc:v2",
        target_node_id="item:v2",
        predicate="contains",
    )
    revision_id = _publish_edge(
        seeded_root,
        edge_id="edge:participates",
        source_node_id="npc:v2",
        target_node_id="fac:v2",
        predicate="participates_in",
    )

    report = analyze_exact_buddy_world_revision_v2(
        root=seeded_root,
        world_id=WORLD_ID,
        revision_id=revision_id,
    )
    inv = {row.buddy_predicate: row for row in report.relationship_predicate_inventory}
    assert sum(row.count for row in report.relationship_predicate_inventory) == sum(
        row.count for row in report.predicate_inventory
    )
    assert inv["member_of"].disposition == PredicateDisposition.EXISTING_EXPLICIT_ADAPTER
    assert inv["member_of"].mapped_dungeonmind_term == "dnd5e:member_of"
    assert inv["located_in"].disposition == PredicateDisposition.SEMANTIC_ADJUDICATION_REQUIRED
    assert inv["attacks"].disposition == PredicateDisposition.SEMANTIC_ADJUDICATION_REQUIRED
    assert inv["contains"].disposition == PredicateDisposition.SEMANTIC_ADJUDICATION_REQUIRED
    assert inv["participates_in"].disposition in {
        PredicateDisposition.EXISTING_EXPLICIT_ADAPTER,
        PredicateDisposition.ENDPOINT_ADMISSION_GAP,
    }


def test_v2_adversarial_forbidden_predicate_mappings(seeded_root: Path) -> None:
    _publish_node(seeded_root, node_id="threat:adv", kind="threat", role="threat")
    _publish_node(seeded_root, node_id="loc:adv", kind="location", role="place")
    _publish_node(seeded_root, node_id="npc:adv", kind="npc", role="ally")
    revision_id = _publish_edge(
        seeded_root,
        edge_id="edge:adv",
        source_node_id="threat:adv",
        target_node_id="loc:adv",
        predicate="located_in",
    )
    _publish_edge(
        seeded_root,
        edge_id="edge:attacks",
        source_node_id="threat:adv",
        target_node_id="npc:adv",
        predicate="attacks",
    )
    _publish_edge(
        seeded_root,
        edge_id="edge:same",
        source_node_id="npc:adv",
        target_node_id="threat:adv",
        predicate="same_as",
    )

    report = analyze_exact_buddy_world_revision_v2(
        root=seeded_root,
        world_id=WORLD_ID,
        revision_id=revision_id,
    )
    for row in report.relationship_predicate_inventory:
        if row.mapped_dungeonmind_term is not None:
            assert row.mapped_dungeonmind_term != f"dnd5e:{row.buddy_predicate}"
        assert row.mapped_dungeonmind_term != "dnd5e:located_in"
        assert row.mapped_dungeonmind_term != "dnd5e:attacks"
        assert row.mapped_dungeonmind_term != "dnd5e:contains"
        if row.buddy_predicate == "located_in":
            assert row.mapped_dungeonmind_term != "dnd5e:located_at"
            assert row.disposition == PredicateDisposition.SEMANTIC_ADJUDICATION_REQUIRED
        if row.buddy_predicate == "attacks":
            assert row.mapped_dungeonmind_term != "dnd5e:threatens"
            assert row.disposition == PredicateDisposition.SEMANTIC_ADJUDICATION_REQUIRED
        if row.buddy_predicate == "same_as":
            assert row.disposition == PredicateDisposition.SEMANTIC_ADJUDICATION_REQUIRED
            assert "identity" in (row.note or "").lower() or "adjudication" in (row.note or "").lower()


def test_v2_exact_revision_pin_does_not_read_head_after_pin(
    seeded_root: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    r1 = _publish_node(seeded_root, node_id="threat:r1", kind="threat", role="threat")
    r2 = _publish_node(seeded_root, node_id="threat:r2", kind="threat", role="threat")

    def _forbidden_head(*_args: Any, **_kwargs: Any) -> Any:
        raise AssertionError("analyze v2 must not consult World Graph head after revision pin")

    monkeypatch.setattr(kernel, "open_world_graph_head", _forbidden_head)

    report = analyze_exact_buddy_world_revision_v2(
        root=seeded_root,
        world_id=WORLD_ID,
        revision_id=r1,
    )
    assert report.source_revision_id == r1
    assert report.source_revision_id != r2


def test_v2_analyze_is_read_only_for_tmp_world(seeded_root: Path) -> None:
    revision_id = _publish_node(seeded_root, node_id="threat:ro", kind="threat", role="threat")
    before = snapshot_world_graph_tree_digest(seeded_root, WORLD_ID)
    analyze_exact_buddy_world_revision_v2(
        root=seeded_root,
        world_id=WORLD_ID,
        revision_id=revision_id,
    )
    after = snapshot_world_graph_tree_digest(seeded_root, WORLD_ID)
    assert before == after


def test_v2_build_refuses_not_ready(seeded_root: Path) -> None:
    revision_id = _publish_node(seeded_root, node_id="item:refuse", kind="item", role="object")
    with pytest.raises(WholeWorldConformanceError, match="dm_union_graph_v5"):
        build_exact_dungeonmind_adoption_revision_v2(
            root=seeded_root,
            world_id=WORLD_ID,
            revision_id=revision_id,
        )


def test_eldyrwild_v2_integration_when_present() -> None:
    root = world_graph_root()
    world_root = (root / "graph_memory" / "worlds" / ELDYRWILD_WORLD_ID).resolve()
    if not world_root.is_dir():
        world_root = (root / "worlds" / ELDYRWILD_WORLD_ID).resolve()
    if not world_root.is_dir():
        pytest.skip("real Eldyrwild world tree missing (CI without out/)")

    head = kernel.open_world_graph_head(root, ELDYRWILD_WORLD_ID)
    assert head is not None
    assert head.head_revision_id == ELDYRWILD_REVISION_ID

    before = snapshot_world_graph_tree_digest(root, ELDYRWILD_WORLD_ID)
    report = analyze_exact_buddy_world_revision_v2(
        root=root,
        world_id=ELDYRWILD_WORLD_ID,
        revision_id=ELDYRWILD_REVISION_ID,
    )
    after = snapshot_world_graph_tree_digest(root, ELDYRWILD_WORLD_ID)
    assert before == after
    assert before == ELDYRWILD_TREE_DIGEST

    assert report.schema_version == WHOLE_WORLD_CONFORMANCE_REPORT_SCHEMA_V2
    assert report.dungeonmind_dependency_ref == "da7c32576c319d1030410eabe5c589ef7e990a9f"
    assert report.target_graph_schema == "dm_union_graph_v5"
    assert report.world_object_vocabulary_revision == "world-object-v2"
    assert report.world_object_vocabulary_sha256 == (
        "a53e2d0ec45878288800ff3d30006d54803db70a17e6680b359a0fa88f2a9922"
    )
    assert report.semantic_profile_descriptor_sha256 == (
        "2199e8fb96e917c22718e6aec59cbbf55a37ee81575e1bcf16ce13fae0393496"
    )
    assert report.source_revision_id == ELDYRWILD_REVISION_ID
    assert report.source_graph_payload_sha256 == ELDYRWILD_PAYLOAD_SHA256
    assert report.inventory["nodes"] == 438
    assert report.inventory["edges"] == 348
    assert report.inventory["evidence"] == 185
    assert report.inventory["source_artifacts"] == 25
    assert report.disposition == "WHOLE_GRAPH_ADOPTION_NOT_READY"
    assert report.unaccounted_durable_elements == 0

    world_object_kind = [
        blocker for blocker in report.blockers if blocker.blocker_class.value == "WORLD_OBJECT_KIND"
    ]
    assert world_object_kind == []

    assert sum(row.count for row in report.relationship_predicate_inventory) == 348
    for row in report.relationship_predicate_inventory:
        pair_sum = sum(pair.count for pair in row.endpoint_pairs)
        assert pair_sum == row.count

    assert report.uses_statblock_mechanics_count >= 1
    uses_rows = [
        row
        for row in report.relationship_predicate_inventory
        if row.buddy_predicate == "uses_statblock"
    ]
    assert uses_rows
    assert uses_rows[0].disposition == PredicateDisposition.MECHANICS_SPECIALIZATION

    if FIXTURE_PATH.is_file():
        fixture = json.loads(FIXTURE_PATH.read_text())
        for key in (
            "disposition",
            "unaccounted_durable_elements",
            "target_graph_schema",
            "dungeonmind_dependency_ref",
            "inventory",
        ):
            assert fixture[key] == report.model_dump(mode="json")[key]

    blocker_classes = {blocker.blocker_class.value for blocker in report.blockers}
    assert "WORLD_OBJECT_KIND" not in blocker_classes
    assert "FICTIONAL_TIME" not in blocker_classes
    assert "EPISTEMIC_STATE" not in blocker_classes
    assert "RELATIONSHIP_PREDICATE" in blocker_classes
    assert "DURABLE_ADOPTION_BOUNDARY" in blocker_classes
