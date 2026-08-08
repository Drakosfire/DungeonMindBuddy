"""Whole Buddy World Graph → DungeonMind v5 adoption-readiness conformance proofs (v3)."""

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
import apps.live_control_server.integrations.dungeonmind_kernel.whole_world_conformance_v3 as wwc_v3
from apps.live_control_server.integrations.dungeonmind_kernel.whole_world_conformance_v3 import (
    WHOLE_WORLD_CONFORMANCE_REPORT_SCHEMA_V3,
    PredicateDisposition,
    WholeWorldConformanceError,
    analyze_exact_buddy_world_revision_v3,
    build_exact_dungeonmind_adoption_revision_v3,
    compact_whole_world_conformance_report_v3,
    edge_has_reverse_direction_qualifier_v3,
    resolve_buddy_predicate_mapping_v3,
)

WORLD_ID = "whole-world-conformance-v3"
CAMPAIGN_ID = "longmont-c2"
ELDYRWILD_WORLD_ID = "eldyrwild"
ELDYRWILD_REVISION_ID = "rev:3413bf6f5044cf2680233f5e37c90dcf"
ELDYRWILD_PAYLOAD_SHA256 = (
    "346c1fbfb3cbbf6d0e5ded1453fdd7760264a5106022e398d6074679799ab0fa"
)
FIXTURE_PATH = (
    Path(__file__).resolve().parent
    / "fixtures"
    / "dungeonmind_kernel"
    / "eldyrwild_post_v28_conformance_v1.json"
)
_CONTRIBUTION_SEQ = 0

_EXPECTED_RESIDUAL_BY_PREDICATE = {
    "carries": 4,
    "carries_report_to": 1,
    "contains": 2,
    "controls_comms_with": 3,
    "defends_weakened_location": 1,
    "identified_as": 4,
    "leads": 2,
    "leads_to": 5,
    "located_in": 5,
    "member_of": 1,
    "mission_targets": 1,
    "objective_of": 2,
    "part_of": 4,
    "part_of_group": 1,
    "participates_in": 6,
    "present_at": 2,
    "reports_threat_in": 1,
    "routes_to": 1,
    "same_as": 5,
    "serves": 3,
    "threatens": 1,
    "travels_to": 2,
    "within": 2,
}


@pytest.fixture
def seeded_root(tmp_path: Path) -> Path:
    kernel.publish_world_revision(
        tmp_path,
        WORLD_ID,
        load_union_supergraph_store(DEFAULT_FIXTURE_PATH),
        operation_ids=["op:whole-world-v3-baseline"],
    )
    return tmp_path


def _contribution(*assertions: Any):
    global _CONTRIBUTION_SEQ
    _CONTRIBUTION_SEQ += 1
    return kernel.create_graph_contribution(
        world_id=WORLD_ID,
        source_kind="manual_import",
        source_artifact_id="graph-native:whole-world-v3",
        source_revision_id=f"whole-world-v3-{_CONTRIBUTION_SEQ}",
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
    aliases: list[str] | None = None,
    label: str | None = None,
) -> str:
    value: dict[str, Any] = {"kind": kind, "role": role, "source_domains": ["manual_seed"]}
    if aliases is not None:
        value["aliases"] = aliases
    node_label = label or f"Whole world v3 {kind}"
    assertion = kernel.build_assertion(
        assertion_kind="node",
        acceptance_state="accepted",
        subject_node_id=node_id,
        label=node_label,
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


def test_v3_contract_pins_and_target_schema() -> None:
    from dungeonmind.application.graph_snapshot import GRAPH_SCHEMA_V5
    from dungeonmind.application.semantic_profiles import descriptor_sha256
    from dungeonmind.contracts.evidence import EVIDENCE_REF_V2_SCHEMA, SOURCE_ARTIFACT_V2_SCHEMA
    from dungeonmind.contracts.knowledge_assertion import KNOWLEDGE_ASSERTION_METADATA_SCHEMA
    from dungeonmind_dnd.application.world_object_vocabulary import (
        builtin_world_object_v3_vocabulary_ref,
        load_builtin_v3_descriptor,
        load_builtin_world_object_v3_vocabulary,
        vocabulary_sha256,
    )
    from dungeonmind_dnd.application.world_property_vocabulary import (
        builtin_world_property_vocabulary_ref,
        load_builtin_world_property_vocabulary,
        world_property_vocabulary_sha256,
    )

    vocab = load_builtin_world_object_v3_vocabulary()
    ref = builtin_world_object_v3_vocabulary_ref()
    prop = load_builtin_world_property_vocabulary()
    prop_ref = builtin_world_property_vocabulary_ref()
    profile = load_builtin_v3_descriptor()

    assert ref.vocabulary_revision == "world-object-v3"
    assert ref.catalog_sha256 == "d2f08de9ec3def308c8bc6d9d81132e5bbff9bd10b4bd706fc1cb39667b71a19"
    assert vocabulary_sha256(vocab) == ref.catalog_sha256
    assert prop_ref.vocabulary_id == "dungeonmind.dnd5e.world_property"
    assert prop_ref.vocabulary_revision == "world-property-v1"
    assert world_property_vocabulary_sha256(prop) == (
        "b466e3f16ae1aba5814f3386dff86b7017399c6099158d99ef95e9979d7cea7f"
    )
    assert profile.profile_revision == "dnd5e-profile-v3"
    assert descriptor_sha256(profile) == (
        "2199e8fb96e917c22718e6aec59cbbf55a37ee81575e1bcf16ce13fae0393496"
    )
    assert GRAPH_SCHEMA_V5 == "dm_union_graph_v5"
    assert SOURCE_ARTIFACT_V2_SCHEMA == "dm_source_artifact_v2"
    assert EVIDENCE_REF_V2_SCHEMA == "dm_evidence_ref_v2"
    assert KNOWLEDGE_ASSERTION_METADATA_SCHEMA == "dm_knowledge_assertion_metadata_v1"
    assert WHOLE_WORLD_CONFORMANCE_REPORT_SCHEMA_V3 == (
        "dmb_dungeonmind_whole_world_conformance_report_v3"
    )
    assert WHOLE_WORLD_CONFORMANCE_REPORT_SCHEMA == (
        "dmb_dungeonmind_whole_world_conformance_report_v1"
    )


def test_historical_vocabulary_digests_still_load() -> None:
    from dungeonmind_dnd.application.world_object_vocabulary import (
        builtin_world_object_v2_vocabulary_ref,
        builtin_world_object_v3_vocabulary_ref,
        builtin_world_object_vocabulary_ref,
        load_builtin_world_object_v2_vocabulary,
        load_builtin_world_object_v3_vocabulary,
        load_builtin_world_object_vocabulary,
        vocabulary_sha256,
    )
    from dungeonmind_dnd.application.world_property_vocabulary import (
        builtin_world_property_vocabulary_ref,
        load_builtin_world_property_vocabulary,
        world_property_vocabulary_sha256,
    )

    v1 = load_builtin_world_object_vocabulary()
    v1_ref = builtin_world_object_vocabulary_ref()
    assert vocabulary_sha256(v1) == v1_ref.catalog_sha256

    v2 = load_builtin_world_object_v2_vocabulary()
    v2_ref = builtin_world_object_v2_vocabulary_ref()
    assert v2_ref.vocabulary_revision == "world-object-v2"
    assert vocabulary_sha256(v2) == v2_ref.catalog_sha256

    v3 = load_builtin_world_object_v3_vocabulary()
    v3_ref = builtin_world_object_v3_vocabulary_ref()
    assert v3_ref.vocabulary_revision == "world-object-v3"
    assert vocabulary_sha256(v3) == v3_ref.catalog_sha256

    prop = load_builtin_world_property_vocabulary()
    prop_ref = builtin_world_property_vocabulary_ref()
    assert prop_ref.vocabulary_revision == "world-property-v1"
    assert world_property_vocabulary_sha256(prop) == prop_ref.catalog_sha256


def test_v3_adapter_direct_rename_reverse_and_no_fallback(
    seeded_root: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    _publish_node(seeded_root, node_id="npc:a", kind="npc", role="ally")
    _publish_node(seeded_root, node_id="npc:b", kind="npc", role="ally")
    _publish_node(seeded_root, node_id="fac:a", kind="faction", role="organization")
    _publish_node(seeded_root, node_id="loc:a", kind="location", role="city")
    _publish_node(seeded_root, node_id="loc:b", kind="location", role="city")
    _publish_node(seeded_root, node_id="item:a", kind="item", role="object")
    _publish_node(seeded_root, node_id="evt:a", kind="event", role="event")

    _publish_edge(
        seeded_root,
        edge_id="edge:direct-allied",
        source_node_id="npc:a",
        target_node_id="npc:b",
        predicate="allied_with",
    )
    _publish_edge(
        seeded_root,
        edge_id="edge:rename-within",
        source_node_id="npc:a",
        target_node_id="loc:a",
        predicate="within",
    )
    _publish_edge(
        seeded_root,
        edge_id="edge:reverse-belongs",
        source_node_id="item:a",
        target_node_id="npc:a",
        predicate="belongs_to",
    )
    _publish_edge(
        seeded_root,
        edge_id="edge:same",
        source_node_id="npc:a",
        target_node_id="npc:b",
        predicate="same_as",
    )
    revision_id = _publish_edge(
        seeded_root,
        edge_id="edge:unknown-compound",
        source_node_id="npc:a",
        target_node_id="fac:a",
        predicate="does_something_made_up",
    )

    original_load = wwc_v3._load_exact_buddy_revision

    def _load_with_mechanics(*, root: Path, world_id: str, revision_id: str):
        manifest, store = original_load(root=root, world_id=world_id, revision_id=revision_id)
        payload = store.model_dump(mode="python", by_alias=True)
        payload["edges"]["edge:mechanics"] = {
            "edge_id": "edge:mechanics",
            "source_node_id": "npc:a",
            "target_node_id": "item:a",
            "predicate": "uses_statblock",
            "label": "uses_statblock",
            "direction": "outbound",
            "source_domains": ["manual_seed"],
            "session_ids": [],
            "evidence_ref_ids": [],
            "state": {},
            "threat_statblock_binding": {
                "schema": "dmb_threat_statblock_binding_v1",
                "binding_id": "threat-statblock-binding:test-v3",
                "provider": "dungeonmind",
                "statblock_id": "sb_test0001",
                "revision_id": "rev_test0001",
                "contract": "dungeonmind.dungeonbuddy-statblocks",
                "contract_version": "1.0.0",
                "definition_digest": "sha256:" + ("a" * 64),
                "role": "primary",
                "phase_key": None,
                "variant_label": None,
            },
            "statblock_binding": None,
        }
        return manifest, UnionSupergraphStore.model_validate(payload)

    monkeypatch.setattr(wwc_v3, "_load_exact_buddy_revision", _load_with_mechanics)

    report = analyze_exact_buddy_world_revision_v3(
        root=seeded_root,
        world_id=WORLD_ID,
        revision_id=revision_id,
    )
    inv = {row.buddy_predicate: row for row in report.relationship_predicate_inventory}

    assert resolve_buddy_predicate_mapping_v3("allied_with") == ("dnd5e:allied_with", False)
    assert resolve_buddy_predicate_mapping_v3("within") == ("dnd5e:located_in", False)
    assert resolve_buddy_predicate_mapping_v3("belongs_to") == ("dnd5e:owns", True)
    assert resolve_buddy_predicate_mapping_v3("same_as") is None
    assert resolve_buddy_predicate_mapping_v3("does_something_made_up") is None
    assert resolve_buddy_predicate_mapping_v3("uses_statblock") is None

    assert inv["allied_with"].represented_count == 1
    assert inv["allied_with"].endpoint_pairs[0].target_dungeonmind_term == "dnd5e:allied_with"
    assert inv["within"].represented_count == 1
    assert inv["within"].endpoint_pairs[0].target_dungeonmind_term == "dnd5e:located_in"
    belongs = inv["belongs_to"]
    assert belongs.represented_count == 1
    assert belongs.endpoint_pairs[0].target_dungeonmind_term == "dnd5e:owns"
    assert belongs.endpoint_pairs[0].reverse_endpoints is True
    assert inv["same_as"].residual_count == 1
    assert inv["same_as"].endpoint_pairs[0].target_dungeonmind_term is None
    assert inv["uses_statblock"].mechanics_count == 1
    assert inv["does_something_made_up"].residual_count == 1
    assert inv["does_something_made_up"].endpoint_pairs[0].target_dungeonmind_term is None
    for row in report.relationship_predicate_inventory:
        assert row.endpoint_pairs[0].target_dungeonmind_term != "dnd5e:related_to"
        if row.buddy_predicate == "does_something_made_up":
            assert row.endpoint_pairs[0].target_dungeonmind_term != (
                f"dnd5e:{row.buddy_predicate}"
            )


def test_v3_endpoint_admission_rejection(seeded_root: Path) -> None:
    _publish_node(seeded_root, node_id="mystery:a", kind="mystery", role="mystery")
    _publish_node(seeded_root, node_id="loc:a", kind="location", role="city")
    revision_id = _publish_edge(
        seeded_root,
        edge_id="edge:member-bad",
        source_node_id="mystery:a",
        target_node_id="loc:a",
        predicate="member_of",
    )
    report = analyze_exact_buddy_world_revision_v3(
        root=seeded_root,
        world_id=WORLD_ID,
        revision_id=revision_id,
    )
    row = next(
        r for r in report.relationship_predicate_inventory if r.buddy_predicate == "member_of"
    )
    assert row.residual_count >= 1
    assert row.represented_count == 0
    assert any(pair.residual_count >= 1 for pair in row.endpoint_pairs)
    assert any(
        pair.target_dungeonmind_term == "dnd5e:member_of" and pair.residual_count >= 1
        for pair in row.endpoint_pairs
    )


def test_v3_lysandra_exception_and_compound_unresolved(seeded_root: Path) -> None:
    _publish_node(seeded_root, node_id="npc_lysandra", kind="npc", role="ally")
    _publish_node(seeded_root, node_id="node:cultists_of_longmont", kind="group", role="cult")
    _publish_node(seeded_root, node_id="npc:x", kind="npc", role="ally")
    _publish_node(seeded_root, node_id="fac:x", kind="faction", role="organization")
    _publish_edge(
        seeded_root,
        edge_id="edge:npc_lysandra:threatens:node:cultists_of_longmont:is-threatened-by-cultists",
        source_node_id="npc_lysandra",
        target_node_id="node:cultists_of_longmont",
        predicate="threatens",
    )
    revision_id = _publish_edge(
        seeded_root,
        edge_id="edge:controls",
        source_node_id="npc:x",
        target_node_id="fac:x",
        predicate="controls_comms_with",
    )
    report = analyze_exact_buddy_world_revision_v3(
        root=seeded_root,
        world_id=WORLD_ID,
        revision_id=revision_id,
    )
    threatens = next(
        r for r in report.relationship_predicate_inventory if r.buddy_predicate == "threatens"
    )
    assert threatens.residual_count == 1
    assert threatens.represented_count == 0
    controls = next(
        r
        for r in report.relationship_predicate_inventory
        if r.buddy_predicate == "controls_comms_with"
    )
    assert controls.residual_count == 1
    assert controls.endpoint_pairs[0].target_dungeonmind_term is None


def test_v3_role_property_adapters(
    seeded_root: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    revision_id = _publish_node(
        seeded_root, node_id="loc:city", kind="location", role="city"
    )
    _publish_node(
        seeded_root, node_id="party:adv", kind="party", role="adventuring-party"
    )

    original_load = wwc_v3._load_exact_buddy_revision

    def _load_with_external(*, root: Path, world_id: str, revision_id: str):
        manifest, store = original_load(root=root, world_id=world_id, revision_id=revision_id)
        payload = store.model_dump(mode="python", by_alias=True)
        payload["nodes"]["ext:ok"] = {
            "node_id": "ext:ok",
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
        payload["nodes"]["ext:bad"] = {
            "node_id": "ext:bad",
            "label": "Bad external",
            "kind": "external_resource",
            "role": "portrait",
            "source_domains": ["statblock"],
            "evidence_ref_ids": [],
            "state": {},
            "external_resource": {
                "schema": "dmb_external_resource_v1",
                "provider": "dungeonmind",
                "resource_type": "statblock",
                "resource_id": "sb_test0002",
                "contract": "dungeonmind.dungeonbuddy-statblocks",
                "contract_version": "1.0.0",
            },
        }
        return manifest, UnionSupergraphStore.model_validate(payload)

    monkeypatch.setattr(wwc_v3, "_load_exact_buddy_revision", _load_with_external)

    report = analyze_exact_buddy_world_revision_v3(
        root=seeded_root,
        world_id=WORLD_ID,
        revision_id=revision_id,
    )

    role_buckets = [
        bucket
        for bucket in report.mapping_buckets
        if bucket.element_family == "node_field"
        and any("dnd5e:role" in note for note in bucket.notes)
    ]
    assert any(
        bucket.classification.value == "REPRESENTABLE_BY_EXPLICIT_ADAPTER"
        and any("exact string" in note for note in bucket.notes)
        for bucket in role_buckets
    )
    assert any(
        "adventuring-party" in note or "exact string" in note
        for bucket in role_buckets
        for note in bucket.notes
    )
    assert any(
        bucket.classification.value == "BUDDY_OPERATIONAL_ONLY"
        and any("no dnd5e:role emitted" in note for note in bucket.notes)
        for bucket in report.mapping_buckets
        if bucket.element_family == "node_field"
    )
    assert any(
        bucket.classification.value == "DUNGEONMIND_SEMANTIC_CONTRACT_GAP"
        and any("mismatch" in note for note in bucket.notes)
        for bucket in report.mapping_buckets
        if bucket.element_family == "node_field"
    )
    assert any(
        blocker.blocker_class.value == "ATTRIBUTE_ASSERTION"
        for blocker in report.blockers
    )


def test_v3_full_edge_direction_safety_audit_over_automatic_translations() -> None:
    root = world_graph_root()
    world_root = (root / "graph_memory" / "worlds" / ELDYRWILD_WORLD_ID).resolve()
    if not world_root.is_dir():
        world_root = (root / "worlds" / ELDYRWILD_WORLD_ID).resolve()
    if not world_root.is_dir():
        pytest.skip("real Eldyrwild world tree missing (CI without out/)")

    from dungeonmind_dnd.application.world_object_vocabulary import (
        load_builtin_world_object_v3_vocabulary,
    )

    _, store = wwc_v3._load_exact_buddy_revision(
        root=root,
        world_id=ELDYRWILD_WORLD_ID,
        revision_id=ELDYRWILD_REVISION_ID,
    )
    vocabulary = load_builtin_world_object_v3_vocabulary()

    audited = 0
    for edge in store.edges.values():
        mapping = resolve_buddy_predicate_mapping_v3(edge.predicate)
        if mapping is None:
            continue
        if edge.edge_id in wwc_v3._KNOWN_RESIDUAL_EXCEPTION_EDGE_IDS:
            continue
        audited += 1
        if edge_has_reverse_direction_qualifier_v3(
            buddy_predicate=edge.predicate,
            edge_id=edge.edge_id,
        ):
            (
                classification,
                blocker,
                _note,
                disposition,
                _term,
                _reverse,
            ) = wwc_v3._classify_edge_predicate_v3(edge, store, vocabulary)
            assert classification.value == "DUNGEONMIND_SEMANTIC_CONTRACT_GAP"
            assert blocker is not None and blocker.value == "RELATIONSHIP_PREDICATE"
            assert disposition == PredicateDisposition.SEMANTIC_ADJUDICATION_REQUIRED

    assert audited > 0

    # Lysandra exception remains residual even though it is in the exception set.
    lysandra = store.edges[
        "edge:npc_lysandra:threatens:node:cultists_of_longmont:is-threatened-by-cultists"
    ]
    _c, _b, _n, disposition, _t, _r = wwc_v3._classify_edge_predicate_v3(
        lysandra, store, vocabulary
    )
    assert disposition == PredicateDisposition.SEMANTIC_ADJUDICATION_REQUIRED


def test_v3_build_refuses_not_ready(seeded_root: Path) -> None:
    revision_id = _publish_node(seeded_root, node_id="item:refuse", kind="item", role="object")
    with pytest.raises(WholeWorldConformanceError, match="dm_union_graph_v5"):
        build_exact_dungeonmind_adoption_revision_v3(
            root=seeded_root,
            world_id=WORLD_ID,
            revision_id=revision_id,
        )


def test_v3_label_only_materialized_aliases_are_not_evidence_provenance(
    tmp_path: Path,
) -> None:
    """No authored aliases → materialization inserts [label]; must not invent EP blockers."""
    world_id = "whole-world-alias-label-only"
    kernel.publish_world_revision(
        tmp_path,
        world_id,
        kernel.build_empty_technical_baseline_store(
            campaign_id=CAMPAIGN_ID,
            focus_session_id="session-alias-label-only",
        ),
        operation_ids=["op:alias-label-only-baseline"],
    )

    value: dict[str, Any] = {
        "kind": "npc",
        "role": "captain",
        "source_domains": ["manual_seed"],
    }
    assertion = kernel.build_assertion(
        assertion_kind="node",
        acceptance_state="accepted",
        subject_node_id="npc:alias-label-only",
        label="Captain Label Only",
        campaign_scope=CAMPAIGN_ID,
        value=value,
    )
    result = kernel.merge_contribution_to_revision(
        tmp_path,
        world_id=world_id,
        contribution=kernel.create_graph_contribution(
            world_id=world_id,
            source_kind="manual_import",
            source_artifact_id="graph-native:alias-label-only",
            source_revision_id="alias-label-only-1",
            campaign_scope=CAMPAIGN_ID,
            accepted_assertions=[assertion],
        ),
    )
    assert result.published and result.revision_id
    revision_id = result.revision_id

    store = kernel.load_world_graph_revision_with_integrity(
        tmp_path, world_id, revision_id
    )
    node = store.nodes["npc:alias-label-only"]
    assert node.aliases == ["Captain Label Only"]
    assert store.aliases["captain label only"] == "npc:alias-label-only"

    field_class, field_blocker, field_note = wwc_v3._classify_node_aliases_field_v3(node)
    assert field_class.value == "BUDDY_OPERATIONAL_ONLY"
    assert field_blocker is None
    assert "canonical label" in field_note.lower()

    alias_class, alias_blocker, alias_note = wwc_v3._classify_alias_v3(
        "captain label only", "npc:alias-label-only", store
    )
    assert alias_class.value == "BUDDY_OPERATIONAL_ONLY"
    assert alias_blocker is None
    assert "lookup index" in alias_note.lower()

    report = analyze_exact_buddy_world_revision_v3(
        root=tmp_path,
        world_id=world_id,
        revision_id=revision_id,
    )
    evidence_blockers = [
        b for b in report.blockers if b.blocker_class.value == "EVIDENCE_PROVENANCE"
    ]
    assert evidence_blockers == []


def test_v3_substantive_alias_without_assertion_grain_evidence_is_durability_gap(
    tmp_path: Path,
) -> None:
    world_id = "whole-world-alias-substantive"
    kernel.publish_world_revision(
        tmp_path,
        world_id,
        kernel.build_empty_technical_baseline_store(
            campaign_id=CAMPAIGN_ID,
            focus_session_id="session-alias-substantive",
        ),
        operation_ids=["op:alias-substantive-baseline"],
    )
    assertion = kernel.build_assertion(
        assertion_kind="node",
        acceptance_state="accepted",
        subject_node_id="npc:alias-substantive",
        label="Captain Substantive",
        campaign_scope=CAMPAIGN_ID,
        value={
            "kind": "npc",
            "role": "captain",
            "source_domains": ["manual_seed"],
            "aliases": ["Captain Substantive", "Ironveil"],
        },
    )
    result = kernel.merge_contribution_to_revision(
        tmp_path,
        world_id=world_id,
        contribution=kernel.create_graph_contribution(
            world_id=world_id,
            source_kind="manual_import",
            source_artifact_id="graph-native:alias-substantive",
            source_revision_id="alias-substantive-1",
            campaign_scope=CAMPAIGN_ID,
            accepted_assertions=[assertion],
        ),
    )
    assert result.published and result.revision_id

    report = analyze_exact_buddy_world_revision_v3(
        root=tmp_path,
        world_id=world_id,
        revision_id=result.revision_id,
    )
    evidence = next(
        b for b in report.blockers if b.blocker_class.value == "EVIDENCE_PROVENANCE"
    )
    assert evidence.count == 1
    assert evidence.responsible_repo == "DungeonMindBuddy"
    assert "AliasAssertionRecord" in evidence.smallest_next_change
    assert "Canonical-label materialization" in evidence.smallest_next_change
    assert evidence.examples == ["node:npc:alias-substantive:field:aliases"]

    store = kernel.load_world_graph_revision_with_integrity(
        tmp_path, world_id, result.revision_id
    )
    ironveil_class, ironveil_blocker, _note = wwc_v3._classify_alias_v3(
        "ironveil", "npc:alias-substantive", store
    )
    assert ironveil_class.value == "BUDDY_OPERATIONAL_ONLY"
    assert ironveil_blocker is None


def test_v3_non_derivable_store_alias_remains_visible_durability_gap() -> None:
    store = load_union_supergraph_store(DEFAULT_FIXTURE_PATH)
    node_id = next(iter(store.nodes))
    node = store.nodes[node_id]
    # Inject a non-derivable lookup key that is not the label and not in node.aliases.
    ghost_key = "ghost-index-key-not-on-node"
    assert ghost_key not in {(node.label or "").casefold()}
    assert ghost_key not in {alias.casefold() for alias in (node.aliases or [])}
    mutated = store.model_copy(
        update={"aliases": {**dict(store.aliases), ghost_key: node_id}}
    )

    classification, blocker, note = wwc_v3._classify_alias_v3(ghost_key, node_id, mutated)
    assert classification.value == "DUNGEONMIND_DURABILITY_CONTRACT_GAP"
    assert blocker is not None and blocker.value == "EVIDENCE_PROVENANCE"
    assert "non-derivable" in note

    label_key = (node.label or "").casefold()
    classification, blocker, note = wwc_v3._classify_alias_v3(label_key, node_id, mutated)
    assert classification.value == "BUDDY_OPERATIONAL_ONLY"
    assert blocker is None


def test_v3_analyze_is_read_only_for_tmp_world(seeded_root: Path) -> None:
    revision_id = _publish_node(seeded_root, node_id="threat:ro", kind="threat", role="threat")
    before = snapshot_world_graph_tree_digest(seeded_root, WORLD_ID)
    analyze_exact_buddy_world_revision_v3(
        root=seeded_root,
        world_id=WORLD_ID,
        revision_id=revision_id,
    )
    after = snapshot_world_graph_tree_digest(seeded_root, WORLD_ID)
    assert before == after


def test_committed_eldyrwild_v3_fixture_is_durable_regression_contract() -> None:
    assert FIXTURE_PATH.is_file(), "checked-in Eldyrwild v3 fixture must exist"
    fixture = json.loads(FIXTURE_PATH.read_text())

    assert "mapping_buckets" not in fixture
    assert fixture["schema_version"] == WHOLE_WORLD_CONFORMANCE_REPORT_SCHEMA_V3
    assert fixture["dungeonmind_dependency_ref"] == (
        "03ec801db99959153283312b72c13fafe56c54d1"
    )
    assert fixture["target_graph_schema"] == "dm_union_graph_v5"
    assert fixture["source_artifact_schema"] == "dm_source_artifact_v2"
    assert fixture["evidence_schema"] == "dm_evidence_ref_v2"
    assert fixture["assertion_metadata_schema"] == "dm_knowledge_assertion_metadata_v1"
    assert fixture["world_object_vocabulary_revision"] == "world-object-v3"
    assert fixture["world_object_vocabulary_sha256"] == (
        "d2f08de9ec3def308c8bc6d9d81132e5bbff9bd10b4bd706fc1cb39667b71a19"
    )
    assert fixture["world_property_vocabulary_revision"] == "world-property-v1"
    assert fixture["world_property_vocabulary_sha256"] == (
        "b466e3f16ae1aba5814f3386dff86b7017399c6099158d99ef95e9979d7cea7f"
    )
    assert fixture["semantic_profile_revision"] == "dnd5e-profile-v3"
    assert fixture["semantic_profile_descriptor_sha256"] == (
        "2199e8fb96e917c22718e6aec59cbbf55a37ee81575e1bcf16ce13fae0393496"
    )
    assert fixture["source_revision_id"] == ELDYRWILD_REVISION_ID
    assert fixture["source_graph_payload_sha256"] == ELDYRWILD_PAYLOAD_SHA256
    assert fixture["disposition"] == "WHOLE_GRAPH_ADOPTION_NOT_READY"
    assert fixture["unaccounted_durable_elements"] == 0
    assert fixture["relationship_semantic_count"] == 346
    assert fixture["relationship_represented_count"] == 287
    assert fixture["relationship_residual_count"] == 59
    assert fixture["uses_statblock_mechanics_count"] == 2
    assert fixture["role_field_count"] == 438
    assert fixture["role_property_adapter_count"] == 436
    assert fixture["role_external_resource_count"] == 2
    assert fixture["role_residual_count"] == 0

    classification_map = {row["key"]: row["count"] for row in fixture["classification_inventory"]}
    assert classification_map == {
        "BUDDY_OPERATIONAL_ONLY": 3510,
        "DUNGEONMIND_SEMANTIC_CONTRACT_GAP": 59,
        "EXACTLY_REPRESENTABLE": 4333,
        "REPRESENTABLE_BY_EXPLICIT_ADAPTER": 6114,
        "SOURCE_MIGRATION_HISTORY": 4090,
    }
    assert "DUNGEONMIND_DURABILITY_CONTRACT_GAP" not in classification_map
    assert sum(classification_map.values()) == fixture["classified_elements_count"] == 18106

    blocker_map = {row["blocker_class"]: row["count"] for row in fixture["blockers"]}
    assert blocker_map["RELATIONSHIP_PREDICATE"] == 59
    assert "EVIDENCE_PROVENANCE" not in blocker_map
    assert blocker_map["CONTRIBUTION_HISTORY"] == 4090
    assert blocker_map["DURABLE_ADOPTION_BOUNDARY"] == 1
    assert blocker_map["POSTGRES_ADOPTION"] == 1
    for absent in (
        "WORLD_OBJECT_KIND",
        "ATTRIBUTE_ASSERTION",
        "EPISTEMIC_STATE",
        "FICTIONAL_TIME",
        "CAMPAIGN_SCOPE",
        "EVIDENCE_PROVENANCE",
    ):
        assert absent not in blocker_map

    residual_map = {row["key"]: row["count"] for row in fixture["residual_by_predicate"]}
    assert residual_map == _EXPECTED_RESIDUAL_BY_PREDICATE
    assert sum(residual_map.values()) == 59

    pred_rows = fixture["relationship_predicate_inventory"]
    assert sum(row["count"] for row in pred_rows) == 348
    for row in pred_rows:
        assert sum(pair["count"] for pair in row["endpoint_pairs"]) == row["count"]
        assert (
            row["represented_count"] + row["residual_count"] + row["mechanics_count"]
            == row["count"]
        )


def test_eldyrwild_v3_integration_when_present() -> None:
    root = world_graph_root()
    world_root = (root / "graph_memory" / "worlds" / ELDYRWILD_WORLD_ID).resolve()
    if not world_root.is_dir():
        world_root = (root / "worlds" / ELDYRWILD_WORLD_ID).resolve()
    if not world_root.is_dir():
        pytest.skip("real Eldyrwild world tree missing (CI without out/)")

    before = snapshot_world_graph_tree_digest(root, ELDYRWILD_WORLD_ID)
    report = analyze_exact_buddy_world_revision_v3(
        root=root,
        world_id=ELDYRWILD_WORLD_ID,
        revision_id=ELDYRWILD_REVISION_ID,
    )
    after = snapshot_world_graph_tree_digest(root, ELDYRWILD_WORLD_ID)
    assert before == after

    assert report.schema_version == WHOLE_WORLD_CONFORMANCE_REPORT_SCHEMA_V3
    assert report.dungeonmind_dependency_ref == "03ec801db99959153283312b72c13fafe56c54d1"
    assert report.target_graph_schema == "dm_union_graph_v5"
    assert report.world_object_vocabulary_revision == "world-object-v3"
    assert report.world_property_vocabulary_revision == "world-property-v1"
    assert report.source_revision_id == ELDYRWILD_REVISION_ID
    assert report.source_graph_payload_sha256 == ELDYRWILD_PAYLOAD_SHA256
    assert report.disposition == "WHOLE_GRAPH_ADOPTION_NOT_READY"
    assert report.unaccounted_durable_elements == 0
    assert report.relationship_represented_count == 287
    assert report.relationship_residual_count == 59
    assert report.relationship_semantic_count == 346
    assert report.uses_statblock_mechanics_count == 2
    assert report.role_property_adapter_count == 436
    assert report.role_external_resource_count == 2
    assert report.role_residual_count == 0

    residual_map = {row.key: row.count for row in report.residual_by_predicate}
    assert residual_map == _EXPECTED_RESIDUAL_BY_PREDICATE

    classification_map = {row.key: row.count for row in report.classification_inventory}
    assert classification_map == {
        "BUDDY_OPERATIONAL_ONLY": 3510,
        "DUNGEONMIND_SEMANTIC_CONTRACT_GAP": 59,
        "EXACTLY_REPRESENTABLE": 4333,
        "REPRESENTABLE_BY_EXPLICIT_ADAPTER": 6114,
        "SOURCE_MIGRATION_HISTORY": 4090,
    }

    blocker_classes = {blocker.blocker_class.value for blocker in report.blockers}
    assert "WORLD_OBJECT_KIND" not in blocker_classes
    assert "ATTRIBUTE_ASSERTION" not in blocker_classes
    assert "EPISTEMIC_STATE" not in blocker_classes
    assert "FICTIONAL_TIME" not in blocker_classes
    assert "CAMPAIGN_SCOPE" not in blocker_classes
    assert "EVIDENCE_PROVENANCE" not in blocker_classes
    assert "RELATIONSHIP_PREDICATE" in blocker_classes

    fixture = json.loads(FIXTURE_PATH.read_text())
    compact = compact_whole_world_conformance_report_v3(report)
    assert json.dumps(compact, sort_keys=True) == json.dumps(fixture, sort_keys=True)
