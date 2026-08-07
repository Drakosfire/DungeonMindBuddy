"""Generalized Buddy world object → DungeonMind v3 conformance bridge proofs."""

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

import graph_memory.kernel as kernel
from apps.live_control_server.integrations.dungeonmind_kernel.world_object_conformance_bridge import (
    ThreatConformanceBridgeError,
    _bridge_buddy_world_object_revision,
    bridge_exact_buddy_threat,
    bridge_exact_buddy_world_object,
    map_buddy_world_object_id,
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
    compute_world_object_statblock_binding_id,
    edge_id_from_binding_id,
    external_statblock_node_id,
)

WORLD_ID = "gen-bridge-world"
CAMPAIGN_ID = "longmont-c2"
THREAT_ID = "threat:gen-bridge"
NPC_ID = "npc:gen-bridge-lysandra"
PC_ID = "pc:gen-bridge-bonogo"
STATBLOCK_ID = "sb_gen01"
STATBLOCK_REV = "rev_gen01"
MECHANICS_PAYLOAD = {
    "name": "Generalized Bridge Subject",
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
_CONTRIBUTION_SEQ = 0


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
        operation_ids=["op:gen-bridge-baseline"],
    )
    return tmp_path


def _contribution(*assertions: Any):
    global _CONTRIBUTION_SEQ
    _CONTRIBUTION_SEQ += 1
    return kernel.create_graph_contribution(
        world_id=WORLD_ID,
        source_kind="manual_import",
        source_artifact_id="graph-native:gen-bridge",
        source_revision_id=f"gen-bridge-{_CONTRIBUTION_SEQ}-{len(assertions)}",
        campaign_scope=CAMPAIGN_ID,
        accepted_assertions=list(assertions),
    )


def _legacy_binding(
    *,
    threat_node_id: str = THREAT_ID,
    role: str = "primary",
    phase_key: str | None = None,
    variant_label: str | None = None,
    revision_id: str = STATBLOCK_REV,
    digest: str = BUDDY_DIGEST,
) -> dict[str, str | None]:
    return {
        "schema": "dmb_threat_statblock_binding_v1",
        "binding_id": compute_binding_id(
            threat_node_id=threat_node_id,
            provider=PROVIDER,
            statblock_id=STATBLOCK_ID,
            revision_id=revision_id,
            contract=CONTRACT,
            contract_version=CONTRACT_VERSION,
            definition_digest=digest,
            role=role,
            phase_key=phase_key,
            variant_label=variant_label,
        ),
        "provider": PROVIDER,
        "statblock_id": STATBLOCK_ID,
        "revision_id": revision_id,
        "contract": CONTRACT,
        "contract_version": CONTRACT_VERSION,
        "definition_digest": digest,
        "role": role,
        "phase_key": phase_key,
        "variant_label": variant_label,
    }


def _generic_binding(
    *,
    world_object_node_id: str,
    world_object_kind: str,
    role: str = "primary",
    phase_key: str | None = None,
    variant_label: str | None = None,
    revision_id: str = STATBLOCK_REV,
    digest: str = BUDDY_DIGEST,
    statblock_id: str = STATBLOCK_ID,
) -> dict[str, str | None]:
    return {
        "schema": "dmb_world_object_statblock_binding_v1",
        "binding_id": compute_world_object_statblock_binding_id(
            world_object_node_id=world_object_node_id,
            world_object_kind=world_object_kind,
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
        "world_object_kind": world_object_kind,
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


def _legacy_binding_value(binding: dict[str, str | None]) -> dict[str, object]:
    return {
        "edge_id": edge_id_from_binding_id(str(binding["binding_id"])),
        "direction": "outbound",
        "threat_statblock_binding": binding,
    }


def _generic_binding_value(binding: dict[str, str | None]) -> dict[str, object]:
    return {
        "edge_id": edge_id_from_binding_id(str(binding["binding_id"])),
        "direction": "outbound",
        "statblock_binding": binding,
    }


def _publish_node(
    root: Path,
    *,
    node_id: str,
    kind: str,
    role: str,
    label: str,
    aliases: list[str] | None = None,
) -> str:
    value: dict[str, object] = {
        "kind": kind,
        "role": role,
        "source_domains": ["manual_seed"],
    }
    if aliases is not None:
        value["aliases"] = aliases
    assertion = kernel.build_assertion(
        assertion_kind="node",
        acceptance_state="accepted",
        subject_node_id=node_id,
        label=label,
        campaign_scope=CAMPAIGN_ID,
        value=value,
    )
    result = kernel.merge_contribution_to_revision(
        root, world_id=WORLD_ID, contribution=_contribution(assertion)
    )
    assert result.published and result.revision_id
    return result.revision_id


def _publish_binding_edges(
    root: Path,
    *,
    source_node_id: str,
    edges: list[tuple[dict[str, str | None], dict[str, object]]],
) -> str:
    assertions: list[Any] = []
    seen_resources: set[str] = set()
    for binding, edge_value in edges:
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
                subject_node_id=source_node_id,
                target_node_id=external_statblock_node_id(resource_id),
                predicate="uses_statblock",
                campaign_scope=CAMPAIGN_ID,
                value=edge_value,
            )
        )
    result = kernel.merge_contribution_to_revision(
        root, world_id=WORLD_ID, contribution=_contribution(*assertions)
    )
    assert result.published and result.revision_id
    return result.revision_id


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


def _semantic_set(result: Any) -> set[tuple[Any, ...]]:
    return {
        (
            item.attachment.role,
            item.attachment.phase_key,
            item.attachment.variant_label,
            item.attachment.binding.resource_ref.resource_id,
            item.attachment.binding.resource_ref.resource_revision,
            item.attachment.binding.resource_ref.payload_sha256,
        )
        for item in result.attachments
    }


def _five_role_generic_bindings(
    *,
    world_object_node_id: str,
    world_object_kind: str,
) -> list[tuple[dict[str, str | None], dict[str, object]]]:
    bindings = [
        _generic_binding(
            world_object_node_id=world_object_node_id,
            world_object_kind=world_object_kind,
            role=role,
            phase_key=phase_key,
            variant_label=variant_label,
        )
        for role, phase_key, variant_label in (
            ("primary", None, None),
            ("alternate", None, None),
            ("phase", "bloodied", None),
            ("encounter_variant", None, "night raid"),
            ("template", None, "elite"),
        )
    ]
    return [(binding, _generic_binding_value(binding)) for binding in bindings]


# ---------------------------------------------------------------------------
# §13 proof matrix (letters B–J; A lives in threat-only bridge tests)
# ---------------------------------------------------------------------------


def test_matrix_b_generic_threat_primary_matches_legacy_semantics(
    seeded_root: Path,
) -> None:
    _publish_node(
        seeded_root,
        node_id=THREAT_ID,
        kind="threat",
        role="threat",
        label="Generic Threat",
    )
    binding = _generic_binding(
        world_object_node_id=THREAT_ID,
        world_object_kind="threat",
    )
    revision_id = _publish_binding_edges(
        seeded_root,
        source_node_id=THREAT_ID,
        edges=[(binding, _generic_binding_value(binding))],
    )
    result = bridge_exact_buddy_world_object(
        root=seeded_root,
        world_id=WORLD_ID,
        revision_id=revision_id,
        node_id=THREAT_ID,
        campaign_id=CAMPAIGN_ID,
    )
    assert result.target_object_kind == "dnd5e:threat"
    assert result.target_object_id == map_buddy_world_object_id(THREAT_ID)
    assert len(result.attachments) == 1
    att = result.attachments[0]
    assert att.source_binding_id == binding["binding_id"]
    assert att.attachment.binding.object_kind == "dnd5e:threat"
    assert att.attachment.binding.resource_ref.provider_id == STATBLOCKS_PROVIDER_ID
    assert (
        att.attachment.binding.resource_ref.resource_schema == STATBLOCKS_RESOURCE_SCHEMA
    )
    assert att.attachment.binding.resource_ref.media_type == STATBLOCKS_MEDIA_TYPE
    assert att.attachment.binding.resource_ref.payload_sha256 == PAYLOAD_DIGEST
    resolver, hydration = _hydrate_first(result)
    assert len(resolver.calls) == 1
    assert canonical_sha256(hydration.mechanics_payload) == PAYLOAD_DIGEST


def test_matrix_c_npc_exact_mechanics_zero_hostility(seeded_root: Path) -> None:
    _publish_node(
        seeded_root,
        node_id=NPC_ID,
        kind="npc",
        role="ally",
        label="Lysandra stand-in",
    )
    binding = _generic_binding(
        world_object_node_id=NPC_ID,
        world_object_kind="npc",
    )
    revision_id = _publish_binding_edges(
        seeded_root,
        source_node_id=NPC_ID,
        edges=[(binding, _generic_binding_value(binding))],
    )
    result = bridge_exact_buddy_world_object(
        root=seeded_root,
        world_id=WORLD_ID,
        revision_id=revision_id,
        node_id=NPC_ID,
    )
    assert result.target_object_kind == "dnd5e:npc"
    assert len(result.attachments) == 1
    predicates = [
        rel.get("predicate")
        for rel in result.target_revision.graph_payload["relationships"]
    ]
    assert "dnd5e:threatens" not in predicates
    _hydrate_first(result)


def test_matrix_d_npc_zero_mechanics(seeded_root: Path) -> None:
    revision_id = _publish_node(
        seeded_root,
        node_id=NPC_ID,
        kind="npc",
        role="ally",
        label="NPC without mechanics",
    )
    result = bridge_exact_buddy_world_object(
        root=seeded_root,
        world_id=WORLD_ID,
        revision_id=revision_id,
        node_id=NPC_ID,
    )
    assert result.target_object_kind == "dnd5e:npc"
    assert result.attachments == ()


def test_matrix_e_npc_hostility_evidence_does_not_change_identity(
    seeded_root: Path,
) -> None:
    _publish_node(
        seeded_root,
        node_id=NPC_ID,
        kind="npc",
        role="ally",
        label="NPC with unrelated edge",
    )
    _publish_node(
        seeded_root,
        node_id="threat:unrelated-hostility-context",
        kind="threat",
        role="threat",
        label="Unrelated hostility context",
    )
    binding = _generic_binding(
        world_object_node_id=NPC_ID,
        world_object_kind="npc",
    )
    unrelated = kernel.build_assertion(
        assertion_kind="edge",
        acceptance_state="accepted",
        subject_node_id=NPC_ID,
        target_node_id="threat:unrelated-hostility-context",
        predicate="related_to",
        campaign_scope=CAMPAIGN_ID,
        value={
            "edge_id": "edge:gen-npc-hostility-context",
            "direction": "outbound",
        },
    )
    resource = kernel.build_assertion(
        assertion_kind="node",
        acceptance_state="accepted",
        subject_node_id=external_statblock_node_id(STATBLOCK_ID),
        label="External statblock",
        campaign_scope=CAMPAIGN_ID,
        value=_resource_value(),
    )
    uses = kernel.build_assertion(
        assertion_kind="edge",
        acceptance_state="accepted",
        subject_node_id=NPC_ID,
        target_node_id=external_statblock_node_id(STATBLOCK_ID),
        predicate="uses_statblock",
        campaign_scope=CAMPAIGN_ID,
        value=_generic_binding_value(binding),
    )
    result = kernel.merge_contribution_to_revision(
        seeded_root,
        world_id=WORLD_ID,
        contribution=_contribution(resource, unrelated, uses),
    )
    assert result.published and result.revision_id
    bridged = bridge_exact_buddy_world_object(
        root=seeded_root,
        world_id=WORLD_ID,
        revision_id=result.revision_id,
        node_id=NPC_ID,
    )
    assert bridged.target_object_kind == "dnd5e:npc"
    assert len(bridged.attachments) == 1
    assert "dnd5e:threatens" not in [
        rel.get("predicate")
        for rel in bridged.target_revision.graph_payload["relationships"]
    ]


def test_matrix_f_npc_five_role_multiplicity_and_reverse_order(
    seeded_root: Path,
) -> None:
    _publish_node(
        seeded_root,
        node_id=NPC_ID,
        kind="npc",
        role="ally",
        label="NPC five-role",
    )
    forward = _five_role_generic_bindings(
        world_object_node_id=NPC_ID,
        world_object_kind="npc",
    )
    revision_forward = _publish_binding_edges(
        seeded_root,
        source_node_id=NPC_ID,
        edges=forward,
    )
    result_forward = bridge_exact_buddy_world_object(
        root=seeded_root,
        world_id=WORLD_ID,
        revision_id=revision_forward,
        node_id=NPC_ID,
    )
    assert len(result_forward.attachments) == 5
    assert len({item.target_binding_id for item in result_forward.attachments}) == 1
    assert len({item.target_attachment_id for item in result_forward.attachments}) == 5
    forward_set = _semantic_set(result_forward)

    root_b = seeded_root.parent / "npc-reverse"
    root_b.mkdir()
    kernel.publish_world_revision(
        root_b,
        WORLD_ID,
        load_union_supergraph_store(DEFAULT_FIXTURE_PATH),
        operation_ids=["op:gen-bridge-npc-reverse"],
    )
    _publish_node(
        root_b,
        node_id=NPC_ID,
        kind="npc",
        role="ally",
        label="NPC five-role reverse",
    )
    reverse = list(reversed(forward))
    revision_reverse = _publish_binding_edges(
        root_b,
        source_node_id=NPC_ID,
        edges=reverse,
    )
    result_reverse = bridge_exact_buddy_world_object(
        root=root_b,
        world_id=WORLD_ID,
        revision_id=revision_reverse,
        node_id=NPC_ID,
    )
    assert _semantic_set(result_reverse) == forward_set


def test_matrix_g_pc_semantic_identity_only(seeded_root: Path) -> None:
    revision_id = _publish_node(
        seeded_root,
        node_id=PC_ID,
        kind="pc",
        role="player_character",
        label="Bonogo stand-in",
        aliases=["Bonogo Alias"],
    )
    result = bridge_exact_buddy_world_object(
        root=seeded_root,
        world_id=WORLD_ID,
        revision_id=revision_id,
        node_id=PC_ID,
    )
    assert result.target_object_kind == "dnd5e:player_character"
    assert result.target_object_id == map_buddy_world_object_id(PC_ID)
    assert result.attachments == ()
    node = result.target_revision.graph_payload["nodes"][0]
    assert node["kind"] == "dnd5e:player_character"
    assert [item["alias"] for item in node["alias_assertions"]] == ["Bonogo Alias"]


def test_matrix_h_mixed_legacy_primary_and_generic_phase(seeded_root: Path) -> None:
    _publish_node(
        seeded_root,
        node_id=THREAT_ID,
        kind="threat",
        role="threat",
        label="Mixed legacy + generic",
    )
    legacy = _legacy_binding(role="primary")
    generic = _generic_binding(
        world_object_node_id=THREAT_ID,
        world_object_kind="threat",
        role="phase",
        phase_key="bloodied",
    )
    revision_id = _publish_binding_edges(
        seeded_root,
        source_node_id=THREAT_ID,
        edges=[
            (legacy, _legacy_binding_value(legacy)),
            (generic, _generic_binding_value(generic)),
        ],
    )
    result = bridge_exact_buddy_world_object(
        root=seeded_root,
        world_id=WORLD_ID,
        revision_id=revision_id,
        node_id=THREAT_ID,
    )
    assert len(result.attachments) == 2
    roles = {item.attachment.role for item in result.attachments}
    assert roles == {"primary", "phase"}


def test_matrix_i_mixed_duplicate_primary_same_resource_fails_closed(
    seeded_root: Path,
) -> None:
    _publish_node(
        seeded_root,
        node_id=THREAT_ID,
        kind="threat",
        role="threat",
        label="Duplicate semantic primary",
    )
    legacy = _legacy_binding(role="primary")
    generic = _generic_binding(
        world_object_node_id=THREAT_ID,
        world_object_kind="threat",
        role="primary",
    )
    revision_id = _publish_binding_edges(
        seeded_root,
        source_node_id=THREAT_ID,
        edges=[
            (legacy, _legacy_binding_value(legacy)),
            (generic, _generic_binding_value(generic)),
        ],
    )
    with pytest.raises(ThreatConformanceBridgeError) as exc:
        bridge_exact_buddy_world_object(
            root=seeded_root,
            world_id=WORLD_ID,
            revision_id=revision_id,
            node_id=THREAT_ID,
        )
    assert exc.value.reason == "duplicate_semantic_attachment"


def test_matrix_j_exact_revision_r1_beats_head_r2(seeded_root: Path) -> None:
    _publish_node(
        seeded_root,
        node_id=THREAT_ID,
        kind="threat",
        role="threat",
        label="Revision pin",
    )
    binding_a = _generic_binding(
        world_object_node_id=THREAT_ID,
        world_object_kind="threat",
        role="primary",
        variant_label="rev-a",
    )
    revision_a = _publish_binding_edges(
        seeded_root,
        source_node_id=THREAT_ID,
        edges=[(binding_a, _generic_binding_value(binding_a))],
    )
    binding_b = _generic_binding(
        world_object_node_id=THREAT_ID,
        world_object_kind="threat",
        role="alternate",
        variant_label="rev-b",
    )
    edge_only = kernel.build_assertion(
        assertion_kind="edge",
        acceptance_state="accepted",
        subject_node_id=THREAT_ID,
        target_node_id=external_statblock_node_id(STATBLOCK_ID),
        predicate="uses_statblock",
        campaign_scope=CAMPAIGN_ID,
        value=_generic_binding_value(binding_b),
    )
    result_b = kernel.merge_contribution_to_revision(
        seeded_root, world_id=WORLD_ID, contribution=_contribution(edge_only)
    )
    assert result_b.published and result_b.revision_id
    assert revision_a != result_b.revision_id

    counters = begin_request_io()
    result = bridge_exact_buddy_world_object(
        root=seeded_root,
        world_id=WORLD_ID,
        revision_id=revision_a,
        node_id=THREAT_ID,
    )
    io = get_request_io()
    assert io is counters
    assert counters.head_json_reads == 0
    assert result.source_revision_id == revision_a
    assert len(result.attachments) == 1
    assert result.attachments[0].attachment.variant_label == "rev-a"


# ---------------------------------------------------------------------------
# §15 bridge adversarial proofs
# ---------------------------------------------------------------------------


@pytest.mark.parametrize("kind", ["creature", "monster", "entity"])
def test_fail_unsupported_kind(seeded_root: Path, kind: str) -> None:
    node_id = f"{kind}:gen-not-bridgeable"
    revision_id = _publish_node(
        seeded_root,
        node_id=node_id,
        kind=kind,
        role="antagonist" if kind != "entity" else "unknown",
        label=f"Unsupported {kind}",
    )
    with pytest.raises(ThreatConformanceBridgeError) as exc:
        bridge_exact_buddy_world_object(
            root=seeded_root,
            world_id=WORLD_ID,
            revision_id=revision_id,
            node_id=node_id,
        )
    assert exc.value.reason == "source_object_kind_not_bridgeable"


def test_fail_pc_mechanics_attachment(seeded_root: Path) -> None:
    revision_id = _publish_node(
        seeded_root,
        node_id=PC_ID,
        kind="pc",
        role="player_character",
        label="PC with forbidden mechanics",
    )
    binding = _generic_binding(
        world_object_node_id=PC_ID,
        world_object_kind="npc",
    )
    resource = kernel.build_assertion(
        assertion_kind="node",
        acceptance_state="accepted",
        subject_node_id=external_statblock_node_id(STATBLOCK_ID),
        label="External statblock",
        campaign_scope=CAMPAIGN_ID,
        value=_resource_value(),
    )
    edge = kernel.build_assertion(
        assertion_kind="edge",
        acceptance_state="accepted",
        subject_node_id=PC_ID,
        target_node_id=external_statblock_node_id(STATBLOCK_ID),
        predicate="uses_statblock",
        campaign_scope=CAMPAIGN_ID,
        value=_generic_binding_value(binding),
    )
    assert kernel.merge_contribution_to_revision(
        seeded_root, world_id=WORLD_ID, contribution=_contribution(resource, edge)
    ).published is False

    manifest, store = _load_verified_pair(seeded_root, revision_id)
    mutated = store.model_copy(deep=True)
    from graph_memory.union_supergraph.statblock_binding import WorldObjectStatblockBindingV1

    forged_binding = WorldObjectStatblockBindingV1.model_validate(binding)
    edge_id = edge_id_from_binding_id(str(binding["binding_id"]))
    template = next(iter(mutated.edges.values()))
    mutated.edges[edge_id] = template.model_copy(
        update={
            "edge_id": edge_id,
            "source_node_id": PC_ID,
            "target_node_id": external_statblock_node_id(STATBLOCK_ID),
            "predicate": "uses_statblock",
            "direction": "outbound",
            "threat_statblock_binding": None,
            "statblock_binding": forged_binding,
        }
    )
    with pytest.raises(ThreatConformanceBridgeError) as exc:
        _bridge_buddy_world_object_revision(
            source_world_id=WORLD_ID,
            source_revision=manifest,
            source_store=mutated,
            world_object_node_id=PC_ID,
        )
    assert exc.value.reason == "pc_mechanics_attachment_forbidden"


def test_fail_duplicate_semantic_attachment_generic_npc(seeded_root: Path) -> None:
    """Duplicate semantic material fails closed (legacy+generic primary on Threat)."""
    _publish_node(
        seeded_root,
        node_id=THREAT_ID,
        kind="threat",
        role="threat",
        label="Duplicate semantic primary",
    )
    legacy = _legacy_binding(role="primary")
    generic = _generic_binding(
        world_object_node_id=THREAT_ID,
        world_object_kind="threat",
        role="primary",
    )
    revision_id = _publish_binding_edges(
        seeded_root,
        source_node_id=THREAT_ID,
        edges=[
            (legacy, _legacy_binding_value(legacy)),
            (generic, _generic_binding_value(generic)),
        ],
    )
    with pytest.raises(ThreatConformanceBridgeError) as exc:
        bridge_exact_buddy_world_object(
            root=seeded_root,
            world_id=WORLD_ID,
            revision_id=revision_id,
            node_id=THREAT_ID,
        )
    assert exc.value.reason == "duplicate_semantic_attachment"


def test_fail_forged_generic_binding_and_edge_ids(seeded_root: Path) -> None:
    _publish_node(
        seeded_root,
        node_id=NPC_ID,
        kind="npc",
        role="ally",
        label="Forged generic binding",
    )
    binding = _generic_binding(
        world_object_node_id=NPC_ID,
        world_object_kind="npc",
    )
    revision_id = _publish_binding_edges(
        seeded_root,
        source_node_id=NPC_ID,
        edges=[(binding, _generic_binding_value(binding))],
    )
    manifest, store = _load_verified_pair(seeded_root, revision_id)
    mutated = store.model_copy(deep=True)
    edge = next(e for e in mutated.edges.values() if e.predicate == "uses_statblock")
    forged = edge.statblock_binding.model_copy(
        update={"binding_id": "world-object-statblock-binding:forged000000000000"}
    )
    mutated.edges[edge.edge_id] = edge.model_copy(update={"statblock_binding": forged})
    with pytest.raises(ThreatConformanceBridgeError) as exc:
        _bridge_buddy_world_object_revision(
            source_world_id=WORLD_ID,
            source_revision=manifest,
            source_store=mutated,
            world_object_node_id=NPC_ID,
        )
    assert exc.value.reason == "forged_buddy_binding_id"

    mutated2 = store.model_copy(deep=True)
    edge2 = next(e for e in mutated2.edges.values() if e.predicate == "uses_statblock")
    mutated2.edges.pop(edge2.edge_id)
    mutated2.edges["edge:forged"] = edge2.model_copy(update={"edge_id": "edge:forged"})
    with pytest.raises(ThreatConformanceBridgeError) as exc2:
        _bridge_buddy_world_object_revision(
            source_world_id=WORLD_ID,
            source_revision=manifest,
            source_store=mutated2,
            world_object_node_id=NPC_ID,
        )
    assert exc2.value.reason == "forged_buddy_edge_id"


def test_bridge_threat_compat_wrapper_still_requires_threat_kind(
    seeded_root: Path,
) -> None:
    revision_id = _publish_node(
        seeded_root,
        node_id=NPC_ID,
        kind="npc",
        role="ally",
        label="Threat wrapper rejects NPC",
    )
    with pytest.raises(ThreatConformanceBridgeError) as exc:
        bridge_exact_buddy_threat(
            root=seeded_root,
            world_id=WORLD_ID,
            revision_id=revision_id,
            threat_node_id=NPC_ID,
        )
    assert exc.value.reason == "source_object_kind_not_bridgeable"


def test_public_bridge_exports_world_object_entrypoint() -> None:
    import inspect

    from apps.live_control_server.integrations import dungeonmind_kernel as bridge_pkg

    assert "bridge_exact_buddy_world_object" in bridge_pkg.__all__
    params = set(inspect.signature(bridge_exact_buddy_world_object).parameters)
    assert {"root", "world_id", "revision_id", "node_id"}.issubset(params)
