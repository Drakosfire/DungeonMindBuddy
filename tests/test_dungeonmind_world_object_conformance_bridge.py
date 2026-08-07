"""Executable Buddy Threat → DungeonMind v3 conformance bridge proofs."""

from __future__ import annotations

import copy
from pathlib import Path
from typing import Any

import pytest
from dungeonmind.contracts.projection import Admissibility
from dungeonmind.domain.canonical import canonical_sha256
from dungeonmind_dnd.application.world_object_mechanics import (
    hydrate_world_object_mechanics,
)
from dungeonmind_dnd.contracts.mechanics_resources import (
    STATBLOCKS_MEDIA_TYPE,
    STATBLOCKS_PROVIDER_ID,
    STATBLOCKS_RESOURCE_SCHEMA,
    DndMechanicsResourceEnvelope,
    DndMechanicsResourceRef,
)
from dungeonmind_dnd.contracts.world_object_mechanics import (
    derive_statblock_mechanics_attachment_id,
)

import graph_memory.kernel as kernel
from apps.live_control_server.integrations import dungeonmind_kernel as bridge_pkg
from apps.live_control_server.integrations.dungeonmind_kernel.world_object_conformance_bridge import (
    ThreatConformanceBridgeError,
    _bridge_buddy_threat_revision,
    bridge_exact_buddy_threat,
    convert_buddy_definition_digest,
    map_buddy_provider_to_dungeonmind_provider_id,
    map_buddy_threat_object_id,
)
from graph_memory.kernel.world_read_runtime import begin_request_io, get_request_io
from graph_memory.union_supergraph.load import (
    DEFAULT_FIXTURE_PATH,
    load_union_supergraph_store,
)
from graph_memory.union_supergraph.statblock_binding import (
    CONTRACT,
    CONTRACT_VERSION,
    PROVIDER,
    compute_binding_id,
    edge_id_from_binding_id,
    external_statblock_node_id,
)

WORLD_ID = "bridge-test-world"
CAMPAIGN_ID = "longmont-c2"
THREAT_ID = "threat:bridge-synthetic"
STATBLOCK_ID = "sb_bridge01"
STATBLOCK_REV = "rev_bridge01"
MECHANICS_PAYLOAD = {
    "name": "Bridge Threat",
    "size": "Medium",
    "type": "humanoid",
    "alignment": "neutral",
    "armor_class": 15,
    "hit_points": 45,
    "speed": {"walk": 30},
    "abilities": {
        "str": 14,
        "dex": 12,
        "con": 13,
        "int": 10,
        "wis": 11,
        "cha": 9,
    },
}
PAYLOAD_DIGEST = canonical_sha256(MECHANICS_PAYLOAD)
BUDDY_DIGEST = f"sha256:{PAYLOAD_DIGEST}"


class _CountingResolver:
    def __init__(self, envelope: DndMechanicsResourceEnvelope) -> None:
        self.envelope = envelope
        self.calls: list[DndMechanicsResourceRef] = []

    def resolve(self, resource_ref: DndMechanicsResourceRef) -> DndMechanicsResourceEnvelope:
        self.calls.append(resource_ref)
        return self.envelope


@pytest.fixture
def seeded_root(tmp_path: Path) -> Path:
    kernel.publish_world_revision(
        tmp_path,
        WORLD_ID,
        load_union_supergraph_store(DEFAULT_FIXTURE_PATH),
        operation_ids=["op:bridge-baseline"],
    )
    return tmp_path


def _binding(
    *,
    threat_node_id: str = THREAT_ID,
    statblock_id: str = STATBLOCK_ID,
    revision_id: str = STATBLOCK_REV,
    digest: str = BUDDY_DIGEST,
    role: str = "primary",
    phase_key: str | None = None,
    variant_label: str | None = None,
) -> dict[str, str | None]:
    return {
        "schema": "dmb_threat_statblock_binding_v1",
        "binding_id": compute_binding_id(
            threat_node_id=threat_node_id,
            provider=PROVIDER,
            statblock_id=statblock_id,
            revision_id=revision_id,
            contract=CONTRACT,
            contract_version=CONTRACT_VERSION,
            definition_digest=digest,
            role=role,
            phase_key=phase_key,
            variant_label=variant_label,
        ),
        "provider": PROVIDER,
        "statblock_id": statblock_id,
        "revision_id": revision_id,
        "contract": CONTRACT,
        "contract_version": CONTRACT_VERSION,
        "definition_digest": digest,
        "role": role,
        "phase_key": phase_key,
        "variant_label": variant_label,
    }


def _resource_value(*, resource_id: str = STATBLOCK_ID) -> dict[str, object]:
    return {
        "kind": "external_resource",
        "role": "statblock",
        "external_resource": {
            "schema": "dmb_external_resource_v1",
            "provider": PROVIDER,
            "resource_type": "statblock",
            "resource_id": resource_id,
            "contract": CONTRACT,
            "contract_version": CONTRACT_VERSION,
        },
    }


def _binding_value(binding: dict[str, str | None]) -> dict[str, object]:
    return {
        "edge_id": edge_id_from_binding_id(str(binding["binding_id"])),
        "direction": "outbound",
        "threat_statblock_binding": binding,
    }


_CONTRIBUTION_SEQ = 0


def _contribution(*assertions: Any):
    global _CONTRIBUTION_SEQ
    _CONTRIBUTION_SEQ += 1
    return kernel.create_graph_contribution(
        world_id=WORLD_ID,
        source_kind="manual_import",
        source_artifact_id="graph-native:bridge",
        source_revision_id=f"bridge-{_CONTRIBUTION_SEQ}-{len(assertions)}",
        campaign_scope=CAMPAIGN_ID,
        accepted_assertions=list(assertions),
    )


def _publish_threat_node(
    root: Path,
    *,
    threat_node_id: str = THREAT_ID,
    kind: str = "threat",
    role: str = "threat",
    label: str = "Bridge Threat",
    aliases: list[str] | None = None,
) -> str:
    value: dict[str, object] = {
        "kind": kind,
        "role": role,
        "source_domains": ["manual_seed"],
    }
    if aliases is not None:
        value["aliases"] = aliases
    threat = kernel.build_assertion(
        assertion_kind="node",
        acceptance_state="accepted",
        subject_node_id=threat_node_id,
        label=label,
        campaign_scope=CAMPAIGN_ID,
        value=value,
    )
    result = kernel.merge_contribution_to_revision(
        root, world_id=WORLD_ID, contribution=_contribution(threat)
    )
    assert result.published and result.revision_id
    return result.revision_id


def _publish_bindings(
    root: Path,
    bindings: list[dict[str, str | None]],
    *,
    threat_node_id: str = THREAT_ID,
) -> str:
    assertions = []
    seen_resources: set[str] = set()
    for binding in bindings:
        resource_id = str(binding["statblock_id"])
        if resource_id not in seen_resources:
            assertions.append(
                kernel.build_assertion(
                    assertion_kind="node",
                    acceptance_state="accepted",
                    subject_node_id=external_statblock_node_id(resource_id),
                    label=f"External {resource_id}",
                    campaign_scope=CAMPAIGN_ID,
                    value=_resource_value(resource_id=resource_id),
                )
            )
            seen_resources.add(resource_id)
        assertions.append(
            kernel.build_assertion(
                assertion_kind="edge",
                acceptance_state="accepted",
                subject_node_id=threat_node_id,
                target_node_id=external_statblock_node_id(resource_id),
                predicate="uses_statblock",
                campaign_scope=CAMPAIGN_ID,
                value=_binding_value(binding),
            )
        )
    result = kernel.merge_contribution_to_revision(
        root, world_id=WORLD_ID, contribution=_contribution(*assertions)
    )
    assert result.published and result.revision_id
    return result.revision_id


def _publish_one(
    root: Path,
    *,
    role: str = "primary",
    phase_key: str | None = None,
    variant_label: str | None = None,
    aliases: list[str] | None = None,
) -> tuple[str, dict[str, str | None]]:
    _publish_threat_node(root, aliases=aliases)
    binding = _binding(role=role, phase_key=phase_key, variant_label=variant_label)
    revision_id = _publish_bindings(root, [binding])
    return revision_id, binding


def _load_verified_pair(root: Path, revision_id: str):
    store = kernel.load_world_graph_revision_with_integrity(root, WORLD_ID, revision_id)
    manifest = kernel.load_world_graph_revision_manifest(root, WORLD_ID, revision_id)
    return manifest, store


def _hydrate_first(result: Any) -> tuple[_CountingResolver, Any]:
    attachment = result.attachments[0].attachment
    resource_ref = attachment.binding.resource_ref
    envelope = DndMechanicsResourceEnvelope(
        resource_ref=resource_ref,
        mechanics_payload=copy.deepcopy(MECHANICS_PAYLOAD),
    )
    resolver = _CountingResolver(envelope)
    from dungeonmind.application.graph_snapshot import UnionGraphV3SnapshotReader
    from dungeonmind.infrastructure.semantic_profiles import StaticSemanticProfileRegistry
    from dungeonmind_dnd.application.world_object_vocabulary import (
        load_builtin_v3_descriptor,
    )

    reader = UnionGraphV3SnapshotReader(
        profile_registry=StaticSemanticProfileRegistry([load_builtin_v3_descriptor()])
    )
    hydration = hydrate_world_object_mechanics(
        attachment.binding,
        admissibility=Admissibility.GM,
        graph_revision=result.target_revision,
        graph_reader=reader,
        resource_resolver=resolver,
    )
    return resolver, hydration


# ---------------------------------------------------------------------------
# Dependency / mapping unit proofs
# ---------------------------------------------------------------------------


def test_dependency_imports_real_dungeonmind_packages() -> None:
    import dungeonmind
    import dungeonmind_dnd
    from dungeonmind.domain.canonical import canonical_sha256 as real_hash
    from dungeonmind_dnd.application.world_object_mechanics import (
        derive_world_object_mechanics_binding,
    )

    assert dungeonmind.__name__ == "dungeonmind"
    assert dungeonmind_dnd.__name__ == "dungeonmind_dnd"
    assert callable(real_hash)
    assert callable(derive_world_object_mechanics_binding)


def test_object_id_mapping_is_injective() -> None:
    a = map_buddy_threat_object_id("threat:authored:aaa")
    b = map_buddy_threat_object_id("threat:authored:bbb")
    assert a == "obj:dmb:threat:authored:aaa"
    assert b == "obj:dmb:threat:authored:bbb"
    assert a != b


def test_object_id_rejects_non_representable_source() -> None:
    with pytest.raises(ThreatConformanceBridgeError) as exc:
        map_buddy_threat_object_id("threat:has space")
    assert exc.value.reason == "source_object_id_not_representable"


def test_provider_and_digest_compatibility_maps() -> None:
    assert (
        map_buddy_provider_to_dungeonmind_provider_id("dungeonmind")
        == STATBLOCKS_PROVIDER_ID
    )
    assert convert_buddy_definition_digest(BUDDY_DIGEST) == PAYLOAD_DIGEST
    with pytest.raises(ThreatConformanceBridgeError) as exc:
        convert_buddy_definition_digest(PAYLOAD_DIGEST)
    assert exc.value.reason == "malformed_definition_digest"
    with pytest.raises(ThreatConformanceBridgeError):
        convert_buddy_definition_digest("sha256:sha256:" + ("a" * 64))
    with pytest.raises(ThreatConformanceBridgeError):
        convert_buddy_definition_digest("sha256:" + ("A" * 64))


# ---------------------------------------------------------------------------
# Conformance matrix A–H
# ---------------------------------------------------------------------------


def test_matrix_a_one_threat_one_binding_hydrates(seeded_root: Path) -> None:
    revision_id, binding = _publish_one(seeded_root)
    result = bridge_exact_buddy_threat(
        root=seeded_root,
        world_id=WORLD_ID,
        revision_id=revision_id,
        threat_node_id=THREAT_ID,
        campaign_id=CAMPAIGN_ID,
    )
    assert result.source_revision_id == revision_id
    assert result.target_object_kind == "dnd5e:threat"
    assert result.target_object_id == map_buddy_threat_object_id(THREAT_ID)
    assert len(result.attachments) == 1
    att = result.attachments[0]
    assert att.source_binding_id == binding["binding_id"]
    assert att.source_edge_id == edge_id_from_binding_id(str(binding["binding_id"]))
    assert att.target_binding_id.startswith("mechbind:")
    assert att.target_attachment_id.startswith("mechattach:")
    assert att.attachment.binding.object_kind == "dnd5e:threat"
    assert att.attachment.binding.resource_ref.provider_id == STATBLOCKS_PROVIDER_ID
    assert (
        att.attachment.binding.resource_ref.resource_schema == STATBLOCKS_RESOURCE_SCHEMA
    )
    assert att.attachment.binding.resource_ref.media_type == STATBLOCKS_MEDIA_TYPE
    assert att.attachment.binding.resource_ref.payload_sha256 == PAYLOAD_DIGEST

    relationships = result.target_revision.graph_payload["relationships"]
    assert relationships == []

    resolver, hydration = _hydrate_first(result)
    assert len(resolver.calls) == 1
    assert resolver.calls[0].resource_id == STATBLOCK_ID
    assert resolver.calls[0].resource_revision == STATBLOCK_REV
    assert canonical_sha256(hydration.mechanics_payload) == PAYLOAD_DIGEST


def test_matrix_b_zero_bindings(seeded_root: Path) -> None:
    revision_id = _publish_threat_node(seeded_root)
    result = bridge_exact_buddy_threat(
        root=seeded_root,
        world_id=WORLD_ID,
        revision_id=revision_id,
        threat_node_id=THREAT_ID,
    )
    assert result.attachments == ()
    assert result.target_object_kind == "dnd5e:threat"
    assert result.target_revision.graph_payload["relationships"] == []


def test_matrix_c_same_resource_primary_and_alternate(seeded_root: Path) -> None:
    _publish_threat_node(seeded_root)
    primary = _binding(role="primary")
    alternate = _binding(role="alternate")
    revision_id = _publish_bindings(seeded_root, [primary, alternate])
    result = bridge_exact_buddy_threat(
        root=seeded_root,
        world_id=WORLD_ID,
        revision_id=revision_id,
        threat_node_id=THREAT_ID,
    )
    assert len(result.attachments) == 2
    binding_ids = {item.target_binding_id for item in result.attachments}
    attachment_ids = {item.target_attachment_id for item in result.attachments}
    assert len(binding_ids) == 1
    assert len(attachment_ids) == 2
    roles = {item.attachment.role for item in result.attachments}
    assert roles == {"primary", "alternate"}


def test_matrix_d_same_resource_two_phases(seeded_root: Path) -> None:
    _publish_threat_node(seeded_root)
    bloodied = _binding(role="phase", phase_key="bloodied")
    enraged = _binding(role="phase", phase_key="enraged")
    revision_id = _publish_bindings(seeded_root, [bloodied, enraged])
    result = bridge_exact_buddy_threat(
        root=seeded_root,
        world_id=WORLD_ID,
        revision_id=revision_id,
        threat_node_id=THREAT_ID,
    )
    phase_keys = {item.attachment.phase_key for item in result.attachments}
    assert phase_keys == {"bloodied", "enraged"}
    assert len({item.target_attachment_id for item in result.attachments}) == 2


def test_matrix_e_buddy_string_grammar_preserved(seeded_root: Path) -> None:
    _publish_threat_node(seeded_root)
    bindings = [
        _binding(role="phase", phase_key=" enraged "),
        _binding(role="encounter_variant", variant_label=""),
        _binding(role="encounter_variant", variant_label=" night raid "),
    ]
    # Distinct roles/labels → distinct Buddy binding ids; encounter_variant twice
    # needs distinct variant_label (already distinct).
    revision_id = _publish_bindings(seeded_root, bindings)
    result = bridge_exact_buddy_threat(
        root=seeded_root,
        world_id=WORLD_ID,
        revision_id=revision_id,
        threat_node_id=THREAT_ID,
    )
    by_source = {item.source_binding_id: item for item in result.attachments}
    phase = by_source[str(bindings[0]["binding_id"])]
    empty = by_source[str(bindings[1]["binding_id"])]
    spaced = by_source[str(bindings[2]["binding_id"])]
    assert phase.attachment.phase_key == " enraged "
    assert empty.attachment.variant_label == ""
    assert spaced.attachment.variant_label == " night raid "
    assert phase.target_attachment_id == derive_statblock_mechanics_attachment_id(
        binding_id=phase.target_binding_id,
        role="phase",
        phase_key=" enraged ",
        variant_label=None,
    )
    assert empty.target_attachment_id == derive_statblock_mechanics_attachment_id(
        binding_id=empty.target_binding_id,
        role="encounter_variant",
        phase_key=None,
        variant_label="",
    )


def test_matrix_f_g_no_hostility_and_no_uses_statblock_predicate(
    seeded_root: Path,
) -> None:
    revision_id, _ = _publish_one(seeded_root)
    result = bridge_exact_buddy_threat(
        root=seeded_root,
        world_id=WORLD_ID,
        revision_id=revision_id,
        threat_node_id=THREAT_ID,
    )
    predicates = [
        rel.get("predicate")
        for rel in result.target_revision.graph_payload["relationships"]
    ]
    assert "dnd5e:threatens" not in predicates
    assert "uses_statblock" not in predicates
    assert result.attachments[0].attachment.binding.object_kind == "dnd5e:threat"
    _hydrate_first(result)  # hostility-independent derive+hydrate


def test_matrix_h_canonical_payload_digest_round_trip(seeded_root: Path) -> None:
    revision_id, binding = _publish_one(seeded_root)
    result = bridge_exact_buddy_threat(
        root=seeded_root,
        world_id=WORLD_ID,
        revision_id=revision_id,
        threat_node_id=THREAT_ID,
    )
    bare = convert_buddy_definition_digest(str(binding["definition_digest"]))
    assert bare == PAYLOAD_DIGEST
    assert (
        result.attachments[0].attachment.binding.resource_ref.payload_sha256
        == PAYLOAD_DIGEST
    )
    assert canonical_sha256(MECHANICS_PAYLOAD) == PAYLOAD_DIGEST


# ---------------------------------------------------------------------------
# Head / exact-revision authority
# ---------------------------------------------------------------------------


def test_bridge_pins_old_revision_and_ignores_newer_head(seeded_root: Path) -> None:
    _publish_threat_node(seeded_root)
    binding_a = _binding(role="primary", variant_label="rev-a")
    revision_a = _publish_bindings(seeded_root, [binding_a])
    # Newer head adds a second binding only (resource already present).
    binding_b = _binding(role="alternate", variant_label="rev-b")
    edge_only = kernel.build_assertion(
        assertion_kind="edge",
        acceptance_state="accepted",
        subject_node_id=THREAT_ID,
        target_node_id=external_statblock_node_id(STATBLOCK_ID),
        predicate="uses_statblock",
        campaign_scope=CAMPAIGN_ID,
        value=_binding_value(binding_b),
    )
    result_b = kernel.merge_contribution_to_revision(
        seeded_root, world_id=WORLD_ID, contribution=_contribution(edge_only)
    )
    assert result_b.published and result_b.revision_id
    revision_b = result_b.revision_id
    assert revision_a != revision_b

    counters = begin_request_io()
    result = bridge_exact_buddy_threat(
        root=seeded_root,
        world_id=WORLD_ID,
        revision_id=revision_a,
        threat_node_id=THREAT_ID,
    )
    io = get_request_io()
    assert io is counters
    assert counters.head_json_reads == 0
    assert result.source_revision_id == revision_a
    assert len(result.attachments) == 1
    assert result.attachments[0].source_binding_id == binding_a["binding_id"]
    assert result.attachments[0].attachment.variant_label == "rev-a"


# ---------------------------------------------------------------------------
# Adversarial fail-closed proofs
# ---------------------------------------------------------------------------


def test_fail_exact_revision_missing(seeded_root: Path) -> None:
    missing = "rev:" + ("0" * 32)
    with pytest.raises(ThreatConformanceBridgeError) as exc:
        bridge_exact_buddy_threat(
            root=seeded_root,
            world_id=WORLD_ID,
            revision_id=missing,
            threat_node_id=THREAT_ID,
        )
    assert exc.value.reason == "exact_revision_missing"


def test_fail_world_mismatch(seeded_root: Path) -> None:
    revision_id, _ = _publish_one(seeded_root)
    manifest, store = _load_verified_pair(seeded_root, revision_id)
    with pytest.raises(ThreatConformanceBridgeError) as exc:
        _bridge_buddy_threat_revision(
            source_world_id="other-world",
            source_revision=manifest,
            source_store=store,
            threat_node_id=THREAT_ID,
        )
    assert exc.value.reason == "world_mismatch"


def test_fail_campaign_mismatch(seeded_root: Path) -> None:
    revision_id, _ = _publish_one(seeded_root)
    with pytest.raises(ThreatConformanceBridgeError) as exc:
        bridge_exact_buddy_threat(
            root=seeded_root,
            world_id=WORLD_ID,
            revision_id=revision_id,
            threat_node_id=THREAT_ID,
            campaign_id="wrong-campaign",
        )
    assert exc.value.reason == "campaign_mismatch"


def test_fail_source_threat_missing(seeded_root: Path) -> None:
    revision_id = _publish_threat_node(seeded_root)
    with pytest.raises(ThreatConformanceBridgeError) as exc:
        bridge_exact_buddy_threat(
            root=seeded_root,
            world_id=WORLD_ID,
            revision_id=revision_id,
            threat_node_id="threat:missing",
        )
    assert exc.value.reason == "source_threat_missing"


@pytest.mark.parametrize("kind", ["creature", "monster", "npc"])
def test_fail_non_threat_kinds(seeded_root: Path, kind: str) -> None:
    node_id = f"{kind}:bridge-not-threat"
    revision_id = _publish_threat_node(
        seeded_root,
        threat_node_id=node_id,
        kind=kind,
        role="antagonist" if kind != "npc" else "npc",
        label=f"Not a threat ({kind})",
    )
    with pytest.raises(ThreatConformanceBridgeError) as exc:
        bridge_exact_buddy_threat(
            root=seeded_root,
            world_id=WORLD_ID,
            revision_id=revision_id,
            threat_node_id=node_id,
        )
    assert exc.value.reason == "source_object_kind_not_bridgeable"


def test_fail_role_inferred_entity_is_not_threat(seeded_root: Path) -> None:
    node_id = "entity:bridge-antagonist"
    revision_id = _publish_threat_node(
        seeded_root,
        threat_node_id=node_id,
        kind="entity",
        role="antagonist",
        label="Role-inferred antagonist",
    )
    with pytest.raises(ThreatConformanceBridgeError) as exc:
        bridge_exact_buddy_threat(
            root=seeded_root,
            world_id=WORLD_ID,
            revision_id=revision_id,
            threat_node_id=node_id,
        )
    assert exc.value.reason == "source_object_kind_not_bridgeable"


def test_fail_forged_binding_and_edge_ids(seeded_root: Path) -> None:
    revision_id, _ = _publish_one(seeded_root)
    manifest, store = _load_verified_pair(seeded_root, revision_id)
    mutated = store.model_copy(deep=True)
    edge = next(e for e in mutated.edges.values() if e.predicate == "uses_statblock")
    forged = edge.threat_statblock_binding.model_copy(
        update={"binding_id": "threat-statblock-binding:forged000000000000"}
    )
    mutated.edges[edge.edge_id] = edge.model_copy(
        update={"threat_statblock_binding": forged}
    )
    with pytest.raises(ThreatConformanceBridgeError) as exc:
        _bridge_buddy_threat_revision(
            source_world_id=WORLD_ID,
            source_revision=manifest,
            source_store=mutated,
            threat_node_id=THREAT_ID,
        )
    assert exc.value.reason == "forged_buddy_binding_id"

    mutated2 = store.model_copy(deep=True)
    edge2 = next(e for e in mutated2.edges.values() if e.predicate == "uses_statblock")
    mutated2.edges.pop(edge2.edge_id)
    mutated2.edges["edge:forged"] = edge2.model_copy(update={"edge_id": "edge:forged"})
    with pytest.raises(ThreatConformanceBridgeError) as exc2:
        _bridge_buddy_threat_revision(
            source_world_id=WORLD_ID,
            source_revision=manifest,
            source_store=mutated2,
            threat_node_id=THREAT_ID,
        )
    assert exc2.value.reason == "forged_buddy_edge_id"


def test_fail_inbound_uses_statblock(seeded_root: Path) -> None:
    revision_id, _ = _publish_one(seeded_root)
    manifest, store = _load_verified_pair(seeded_root, revision_id)
    mutated = store.model_copy(deep=True)
    edge = next(e for e in mutated.edges.values() if e.predicate == "uses_statblock")
    swapped = edge.model_copy(
        update={
            "source_node_id": edge.target_node_id,
            "target_node_id": edge.source_node_id,
        }
    )
    mutated.edges[edge.edge_id] = swapped
    with pytest.raises(ThreatConformanceBridgeError) as exc:
        _bridge_buddy_threat_revision(
            source_world_id=WORLD_ID,
            source_revision=manifest,
            source_store=mutated,
            threat_node_id=THREAT_ID,
        )
    assert exc.value.reason == "inbound_uses_statblock"


def test_fail_missing_binding_payload(seeded_root: Path) -> None:
    revision_id, _ = _publish_one(seeded_root)
    manifest, store = _load_verified_pair(seeded_root, revision_id)
    mutated = store.model_copy(deep=True)
    edge = next(e for e in mutated.edges.values() if e.predicate == "uses_statblock")
    mutated.edges[edge.edge_id] = edge.model_copy(update={"threat_statblock_binding": None})
    with pytest.raises(ThreatConformanceBridgeError) as exc:
        _bridge_buddy_threat_revision(
            source_world_id=WORLD_ID,
            source_revision=manifest,
            source_store=mutated,
            threat_node_id=THREAT_ID,
        )
    assert exc.value.reason == "missing_threat_statblock_binding"


def test_fail_missing_external_resource_node(seeded_root: Path) -> None:
    revision_id, _ = _publish_one(seeded_root)
    manifest, store = _load_verified_pair(seeded_root, revision_id)
    mutated = store.model_copy(deep=True)
    resource_id = external_statblock_node_id(STATBLOCK_ID)
    mutated.nodes.pop(resource_id)
    with pytest.raises(ThreatConformanceBridgeError) as exc:
        _bridge_buddy_threat_revision(
            source_world_id=WORLD_ID,
            source_revision=manifest,
            source_store=mutated,
            threat_node_id=THREAT_ID,
        )
    assert exc.value.reason == "missing_external_resource_node"


def test_fail_wrong_resource_target(seeded_root: Path) -> None:
    revision_id, _ = _publish_one(seeded_root)
    manifest, store = _load_verified_pair(seeded_root, revision_id)
    mutated = store.model_copy(deep=True)
    edge = next(e for e in mutated.edges.values() if e.predicate == "uses_statblock")
    mutated.edges[edge.edge_id] = edge.model_copy(
        update={"target_node_id": "external:dungeonmind:statblock:sb_other"}
    )
    with pytest.raises(ThreatConformanceBridgeError) as exc:
        _bridge_buddy_threat_revision(
            source_world_id=WORLD_ID,
            source_revision=manifest,
            source_store=mutated,
            threat_node_id=THREAT_ID,
        )
    assert exc.value.reason == "wrong_external_resource_target"


def test_fail_malformed_digest_on_source_binding(seeded_root: Path) -> None:
    with pytest.raises(ThreatConformanceBridgeError) as exc:
        convert_buddy_definition_digest("sha256:sha256:" + ("a" * 64))
    assert exc.value.reason == "malformed_definition_digest"
    with pytest.raises(ThreatConformanceBridgeError) as exc2:
        convert_buddy_definition_digest("sha256:" + ("A" * 64))
    assert exc2.value.reason == "malformed_definition_digest"
    del seeded_root


def test_fail_whitespace_only_phase_key() -> None:
    from pydantic import ValidationError

    from graph_memory.union_supergraph.statblock_binding import ThreatStatblockBindingV1

    payload = _binding(role="phase", phase_key="   ")
    with pytest.raises(ValidationError):
        ThreatStatblockBindingV1.model_validate(payload)


def test_fail_non_phase_role_with_phase_key() -> None:
    from pydantic import ValidationError

    from graph_memory.union_supergraph.statblock_binding import ThreatStatblockBindingV1

    payload = _binding(role="primary", phase_key="enraged")
    with pytest.raises(ValidationError):
        ThreatStatblockBindingV1.model_validate(payload)


def test_fail_integrity_corruption(seeded_root: Path) -> None:
    revision_id, _ = _publish_one(seeded_root)
    manifest, _store = _load_verified_pair(seeded_root, revision_id)
    graph_path = (
        seeded_root
        / "graph_memory"
        / "worlds"
        / WORLD_ID
        / manifest.graph_payload_path
    )
    graph_path.write_text(graph_path.read_text(encoding="utf-8") + "\n", encoding="utf-8")
    with pytest.raises(ThreatConformanceBridgeError) as exc:
        bridge_exact_buddy_threat(
            root=seeded_root,
            world_id=WORLD_ID,
            revision_id=revision_id,
            threat_node_id=THREAT_ID,
        )
    assert exc.value.reason == "source_revision_integrity_failure"


def test_fail_malformed_revision_manifest(seeded_root: Path) -> None:
    revision_id, _ = _publish_one(seeded_root)
    manifest, _store = _load_verified_pair(seeded_root, revision_id)
    manifest_path = (
        seeded_root
        / "graph_memory"
        / "worlds"
        / WORLD_ID
        / "revisions"
        / revision_id
        / "revision.json"
    )
    assert manifest.revision_id == revision_id
    manifest_path.write_text("{not-valid-json", encoding="utf-8")
    with pytest.raises(ThreatConformanceBridgeError) as exc:
        bridge_exact_buddy_threat(
            root=seeded_root,
            world_id=WORLD_ID,
            revision_id=revision_id,
            threat_node_id=THREAT_ID,
        )
    assert exc.value.reason == "source_revision_integrity_failure"


def test_public_bridge_accepts_only_exact_revision_identity() -> None:
    """Provenance hole is closed at the public boundary — no manifest+store API."""
    import inspect

    assert "bridge_buddy_threat_revision" not in bridge_pkg.__all__
    assert not hasattr(bridge_pkg, "bridge_buddy_threat_revision")
    assert hasattr(bridge_pkg, "bridge_exact_buddy_threat")

    params = set(inspect.signature(bridge_exact_buddy_threat).parameters)
    assert {"root", "world_id", "revision_id", "threat_node_id"}.issubset(params)
    assert "source_revision" not in params
    assert "source_store" not in params
    assert "manifest" not in params


def test_fail_resolver_wrong_resource_identity(seeded_root: Path) -> None:
    revision_id, _ = _publish_one(seeded_root)
    result = bridge_exact_buddy_threat(
        root=seeded_root,
        world_id=WORLD_ID,
        revision_id=revision_id,
        threat_node_id=THREAT_ID,
    )
    binding = result.attachments[0].attachment.binding
    wrong_ref = binding.resource_ref.model_copy(update={"resource_id": "sb_other01"})
    wrong = DndMechanicsResourceEnvelope(
        resource_ref=wrong_ref,
        mechanics_payload=copy.deepcopy(MECHANICS_PAYLOAD),
    )

    class _Wrong:
        def resolve(self, resource_ref: DndMechanicsResourceRef) -> DndMechanicsResourceEnvelope:
            return wrong

    from dungeonmind.application.graph_snapshot import UnionGraphV3SnapshotReader
    from dungeonmind.infrastructure.semantic_profiles import StaticSemanticProfileRegistry
    from dungeonmind_dnd.application.world_object_vocabulary import (
        load_builtin_v3_descriptor,
    )
    from dungeonmind_dnd.domain.errors import DndWorldObjectMechanicsHydrationError

    reader = UnionGraphV3SnapshotReader(
        profile_registry=StaticSemanticProfileRegistry([load_builtin_v3_descriptor()])
    )
    with pytest.raises(DndWorldObjectMechanicsHydrationError) as exc:
        hydrate_world_object_mechanics(
            binding,
            admissibility=Admissibility.GM,
            graph_revision=result.target_revision,
            graph_reader=reader,
            resource_resolver=_Wrong(),
        )
    assert exc.value.details["reason"] == "resource_identity_mismatch"


def test_fail_resolver_payload_digest_mismatch(seeded_root: Path) -> None:
    revision_id, _ = _publish_one(seeded_root)
    result = bridge_exact_buddy_threat(
        root=seeded_root,
        world_id=WORLD_ID,
        revision_id=revision_id,
        threat_node_id=THREAT_ID,
    )
    binding = result.attachments[0].attachment.binding

    class _WrongPayload:
        def resolve(self, resource_ref: DndMechanicsResourceRef) -> dict[str, Any]:
            return {
                "schema_version": "dmdnd_mechanics_resource_envelope_v1",
                "resource_ref": resource_ref.model_dump(mode="json"),
                "mechanics_payload": {"name": "Wrong payload"},
            }

    from dungeonmind.application.graph_snapshot import UnionGraphV3SnapshotReader
    from dungeonmind.infrastructure.semantic_profiles import StaticSemanticProfileRegistry
    from dungeonmind_dnd.application.world_object_vocabulary import (
        load_builtin_v3_descriptor,
    )
    from dungeonmind_dnd.domain.errors import DndWorldObjectMechanicsHydrationError

    reader = UnionGraphV3SnapshotReader(
        profile_registry=StaticSemanticProfileRegistry([load_builtin_v3_descriptor()])
    )
    with pytest.raises(DndWorldObjectMechanicsHydrationError) as exc:
        hydrate_world_object_mechanics(
            binding,
            admissibility=Admissibility.GM,
            graph_revision=result.target_revision,
            graph_reader=reader,
            resource_resolver=_WrongPayload(),
        )
    assert exc.value.details["reason"] in {
        "resource_payload_digest_mismatch",
        "resource_envelope_reload_validation",
    }


def test_aliases_preserved_exactly(seeded_root: Path) -> None:
    aliases = ["Bridge Alias", " bridge spaced "]
    revision_id, _ = _publish_one(seeded_root, aliases=aliases)
    result = bridge_exact_buddy_threat(
        root=seeded_root,
        world_id=WORLD_ID,
        revision_id=revision_id,
        threat_node_id=THREAT_ID,
    )
    node = result.target_revision.graph_payload["nodes"][0]
    asserted = [item["alias"] for item in node["alias_assertions"]]
    assert asserted == aliases
